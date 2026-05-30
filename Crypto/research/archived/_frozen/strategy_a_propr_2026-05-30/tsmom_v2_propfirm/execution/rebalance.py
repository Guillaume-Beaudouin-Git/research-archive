"""
Weekly rebalance runner for TSMOM v2.

Fetches 40-day price history, computes signals & vol-scaled positions,
diffs against current Propr positions, and executes the required orders.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone

import numpy as np
import yfinance as yf

from ..config import UNIVERSE, VOL_LOOKBACK_DAYS
from ..signal import apply_weekly_rebalance, compute_signal
from ..sizing import compute_positions, compute_vol_scalars
from . import ASSET_MAP, REVERSE_ASSET_MAP, STATE_DB_PATH
from .equity_monitor import EquityMonitor
from .order_executor import (
    close_position,
    flatten_all,
    get_positions,
    place_market_order,
)

logger = logging.getLogger(__name__)

VOL_TARGET: float = 0.15          # 15% annualized vol target for live
DATA_LOOKBACK_DAYS: int = 40      # days of history to download

_CREATE_REBALANCE_LOG = """
CREATE TABLE IF NOT EXISTS rebalance_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL,
    assets_opened   TEXT,
    assets_closed   TEXT,
    equity_before   REAL,
    equity_after    REAL,
    daily_dd_pct    REAL,
    total_dd_pct    REAL,
    dry_run         INTEGER NOT NULL DEFAULT 0
);
"""


def _init_rebalance_db() -> None:
    with sqlite3.connect(STATE_DB_PATH) as conn:
        conn.execute(_CREATE_REBALANCE_LOG)
        conn.commit()


def _log_rebalance(
    assets_opened: list[str],
    assets_closed: list[str],
    equity_before: float,
    equity_after: float,
    daily_dd: float,
    total_dd: float,
    dry_run: bool,
) -> None:
    _init_rebalance_db()
    with sqlite3.connect(STATE_DB_PATH) as conn:
        conn.execute(
            "INSERT INTO rebalance_log"
            " (ts, assets_opened, assets_closed, equity_before, equity_after,"
            "  daily_dd_pct, total_dd_pct, dry_run)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                ",".join(assets_opened),
                ",".join(assets_closed),
                equity_before,
                equity_after,
                daily_dd,
                total_dd,
                int(dry_run),
            ),
        )
        conn.commit()


def _try_send_alert(message: str, level: str = "info") -> None:
    try:
        from notifier import send  # type: ignore[import-not-found]
        send(message, level=level)
    except ImportError:
        logger.warning("Telegram notifier not available — skipping alert")
    except Exception as exc:
        logger.warning("Telegram send failed: %s", exc)


def run_weekly_rebalance(
    account_id: str,
    attempt_id: str,
    api_key: str,
    dry_run: bool = False,
) -> None:
    """
    Execute the weekly TSMOM v2 rebalance.

    Steps
    -----
    1. Guardrail check — flatten and abort if unsafe.
    2. Fetch equity snapshot.
    3. Download 40-day price history for all 14 tickers.
    4. Compute signals and vol-scaled target notionals.
    5. Diff vs current Propr positions.
    6. Execute closes first, then opens.
    7. Log rebalance to challenge_state.db.
    """
    mode_label = "[DRY RUN] " if dry_run else ""
    logger.info("%sStarting weekly rebalance", mode_label)

    monitor = EquityMonitor(attempt_id, account_id, api_key)

    # 1 — Guardrail check
    if not monitor.is_safe():
        status = monitor.get_status()
        msg = (
            f"GUARDRAIL BREACH — Flattening all positions.\n"
            f"  Daily DD : {status['daily_dd']:.2%}\n"
            f"  Total DD : {status['total_dd']:.2%}"
        )
        logger.error(msg)
        _try_send_alert(msg, level="error")
        if not dry_run:
            flatten_all(account_id, api_key)
        return

    # 2 — Equity snapshot
    status_before = monitor.get_status()
    capital = status_before["equity"]
    logger.info("Equity: $%.2f | DailyDD: %.2f%% | TotalDD: %.2f%%",
                capital, status_before["daily_dd"] * 100, status_before["total_dd"] * 100)

    # 3 — Download price history
    logger.info("Downloading %d-day price history for %d tickers...", DATA_LOOKBACK_DAYS, len(UNIVERSE))
    raw = yf.download(
        tickers=UNIVERSE,
        period=f"{DATA_LOOKBACK_DAYS}d",
        interval="1d",
        auto_adjust=True,
        progress=False,
    )
    prices_df = raw["Close"] if "Close" in raw.columns else raw.xs("Close", level=1, axis=1)
    prices_df = prices_df.dropna(how="all")

    if prices_df.shape[0] < VOL_LOOKBACK_DAYS + 5:
        logger.error("Insufficient price data: only %d rows", prices_df.shape[0])
        return

    # 4 — Compute signals and target notionals
    log_returns = prices_df.pct_change().apply(lambda x: np.log(1 + x))
    signal_df = compute_signal(prices_df)
    weekly_signals = apply_weekly_rebalance(signal_df)
    vol_scalars_df = compute_vol_scalars(log_returns, VOL_TARGET, VOL_LOOKBACK_DAYS)
    raw_positions_df = compute_positions(weekly_signals, vol_scalars_df)

    # Latest row gives current target position sizes (dimensionless scalars)
    current_signals = weekly_signals.iloc[-1]
    current_scalars = vol_scalars_df.iloc[-1]
    current_pos_sizes = (current_signals * current_scalars).fillna(0.0)

    # Convert to notional USD: notional_i = capital × position_size_i
    target_notionals: dict[str, float] = {}
    for yf_ticker, pos_size in current_pos_sizes.items():
        if pos_size > 0 and not np.isnan(pos_size) and yf_ticker in ASSET_MAP:
            target_notionals[ASSET_MAP[yf_ticker]] = float(capital * pos_size)

    logger.info("Target positions (%d assets): %s", len(target_notionals),
                {k: f"${v:.0f}" for k, v in target_notionals.items()})

    # Scale down if total notional exceeds 90% of available capital
    total_notional = sum(target_notionals.values())
    available = capital * 0.90
    if total_notional > available:
        scale = available / total_notional
        target_notionals = {k: v * scale for k, v in target_notionals.items()}
        logger.info("Scaled positions by %.2f%% to fit available balance (total $%.0f → $%.0f)",
                    scale * 100, total_notional, sum(target_notionals.values()))

    # 5 — Current positions from Propr
    if dry_run:
        current_positions: dict[str, dict] = {}
    else:
        current_positions = get_positions(account_id, api_key)

    current_notionals: dict[str, float] = {
        asset: pos["notional_value"]
        for asset, pos in current_positions.items()
    }

    # 6 — Compute deltas and separate into closes and opens
    all_assets = set(target_notionals.keys()) | set(current_notionals.keys())
    closes: list[str] = []
    opens: list[tuple[str, float]] = []

    for asset in all_assets:
        target = target_notionals.get(asset, 0.0)
        current = current_notionals.get(asset, 0.0)
        delta = target - current
        if delta <= -10.0:   # meaningful reduction (>$10)
            closes.append(asset)
        elif delta >= 10.0:  # meaningful increase (>$10)
            opens.append((asset, target))

    logger.info("Closes: %s | Opens: %s",
                closes, [(a, f"${n:.0f}") for a, n in opens])

    if dry_run:
        logger.info("[DRY RUN] Would execute: %d closes, %d opens — no orders placed",
                    len(closes), len(opens))
        _log_rebalance(
            assets_opened=[a for a, _ in opens],
            assets_closed=closes,
            equity_before=capital,
            equity_after=capital,
            daily_dd=status_before["daily_dd"],
            total_dd=status_before["total_dd"],
            dry_run=True,
        )
        return

    # Execute closes first (reduces margin usage)
    for asset in closes:
        try:
            close_position(account_id, asset, api_key)
        except Exception as exc:
            logger.error("Failed to close %s: %s", asset, exc)

    # Then opens
    for asset, notional in opens:
        try:
            place_market_order(account_id, asset, "buy", notional, api_key)
        except Exception as exc:
            logger.error("Failed to open %s $%.0f: %s", asset, notional, exc)

    # 7 — Post-rebalance snapshot
    status_after = monitor.get_status()
    _log_rebalance(
        assets_opened=[a for a, _ in opens],
        assets_closed=closes,
        equity_before=capital,
        equity_after=status_after["equity"],
        daily_dd=status_after["daily_dd"],
        total_dd=status_after["total_dd"],
        dry_run=False,
    )

    logger.info(
        "Rebalance complete. Equity: $%.2f → $%.2f | DailyDD: %.2f%% | TotalDD: %.2f%%",
        capital,
        status_after["equity"],
        status_after["daily_dd"] * 100,
        status_after["total_dd"] * 100,
    )
