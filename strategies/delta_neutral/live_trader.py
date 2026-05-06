"""
live_trader.py — Delta-Neutral Funding Arbitrage Live Trader (Phase 3)

Strategy:
  Leg A: LONG spot on Binance testnet
  Leg B: SHORT equal notional as perp on Hyperliquid testnet
  Income: HL funding payments every 8h.
  Net directional exposure = 0 by construction.

Rebalance: 8-hourly, cron 10 0,8,16 * * * (00:10, 08:05, 16:05 UTC).
  5-minute offset from 00:05 TSMOM cron to avoid resource contention.

Capital: $50 per asset, max 5 assets simultaneously, $250 total.

ONE-LEGGED POSITION PREVENTION (critical risk control):
  open_pair()  — tries BN spot first, then HL short.
    If BN buy fails  → clean failure, nothing to unwind.
    If HL short fails → immediately market-sell the BN spot.
  close_pair() — tries HL short close first, then BN spot sell.
    If HL close fails → keep BN spot open (preserves hedge), send alert.
    If BN sell fails  → send EMERGENCY alert; state remains open for manual review.

Usage:
    python -m strategies.delta_neutral.live_trader --dry-run
    python -m strategies.delta_neutral.live_trader --live \\
        --bn-key  $BINANCE_TESTNET_API_KEY \\
        --bn-secret $BINANCE_TESTNET_SECRET_KEY \\
        --hl-key  $HYPERLIQUID_TESTNET_KEY
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import notifier
from strategies.delta_neutral.binance_testnet import BinanceTestnetClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ─── STRATEGY PARAMETERS (must match backtest.py) ─────────────────────────────

CARRY_FLOOR_8H    = 0.0034 / (30 * 3)   # per-8h-bar threshold (same as backtest)
CARRY_LOOKBACK_D  = 30                   # trailing window for live carry filter
MAX_ASSETS        = 5                    # cap simultaneous pairs
NOTIONAL_USD      = 50.0                 # USD notional per asset
RECONCILE_TOL     = 0.05                 # 5% spot/perp size mismatch tolerance
MAX_FUNDING_AGE_H = 2                    # HL data staleness limit

# Phase 1 viable universe (MEGA excluded: insufficient Binance spot history)
VIABLE_ASSETS = ["TST", "WLD", "STX", "BIO", "TRUMP", "HMSTR"]

STOP_PATH = REPO_ROOT / "STOP"
STATE_DIR = REPO_ROOT / "data" / "delta_neutral" / "live_state"
LOG_DIR   = REPO_ROOT / "logs"

HL_API = "https://api.hyperliquid.xyz/info"


# ─── HYPERLIQUID CARRY DATA ───────────────────────────────────────────────────

def _hl_post(payload: dict, retries: int = 3) -> list | dict:
    import time as _time
    for attempt in range(retries):
        try:
            r = requests.post(HL_API, json=payload, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            if attempt < retries - 1:
                _time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"HL API failed: {exc}")


def fetch_hl_carry_30d(asset: str) -> float | None:
    """
    Fetch last 30 days of hourly HL funding rates.
    Returns mean per-8h rate (raw mean, not abs — matches backtest carry filter).
    Returns None on failure.
    """
    start_ms = int(
        (datetime.now(timezone.utc) - timedelta(days=CARRY_LOOKBACK_D)).timestamp() * 1000
    )
    try:
        batch = _hl_post({"type": "fundingHistory", "coin": asset, "startTime": start_ms})
    except Exception as exc:
        logger.warning(f"[{asset}] HL funding fetch failed: {exc}")
        return None

    if not batch:
        return None

    # Raw rates (not abs) — only positive mean qualifies (same logic as backtest)
    rates = [float(r["fundingRate"]) for r in batch]
    if not rates:
        return None

    # Mean hourly rate × 8 = mean rate per 8h bar
    return (sum(rates) / len(rates)) * 8


def check_hl_data_freshness(asset: str) -> bool:
    """
    Returns True if HL has funding data within MAX_FUNDING_AGE_H.
    Returns False if the most recent datapoint is older than the limit.
    """
    start_ms = int(
        (datetime.now(timezone.utc) - timedelta(hours=MAX_FUNDING_AGE_H + 1)).timestamp() * 1000
    )
    try:
        batch = _hl_post({"type": "fundingHistory", "coin": asset, "startTime": start_ms})
    except Exception:
        return False

    if not batch:
        return False

    latest_ms = max(int(r.get("time", 0)) for r in batch)
    latest_dt = datetime.fromtimestamp(latest_ms / 1000, tz=timezone.utc)
    age_h     = (datetime.now(timezone.utc) - latest_dt).total_seconds() / 3600
    return age_h <= MAX_FUNDING_AGE_H


# ─── STATE ────────────────────────────────────────────────────────────────────

def _state_path(asset: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{asset}.json"


_FLAT_STATE = {
    "position":         "flat",
    "spot_qty":         0.0,
    "perp_notional":    0.0,
    "entry_time":       None,
    "cumulative_carry": 0.0,
}


def load_state(asset: str) -> dict:
    p = _state_path(asset)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return dict(_FLAT_STATE)


def save_state(asset: str, state: dict) -> None:
    with open(_state_path(asset), "w") as f:
        json.dump(state, f, indent=2)


# ─── KILL SWITCH ─────────────────────────────────────────────────────────────

def check_kill_switch() -> None:
    """Halt immediately if STOP file exists. Exit 0 (intentional stop)."""
    if not STOP_PATH.exists():
        return
    stat      = STOP_PATH.stat()
    mtime_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    reason    = STOP_PATH.read_text().strip()
    reason_str = f" — reason: {reason}" if reason else ""
    msg = (f"HALTED by kill switch "
           f"(created {mtime_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}){reason_str}")
    logger.warning(msg)
    notifier.send(f"[DN KILL SWITCH] {msg}")
    sys.exit(0)


# ─── RECONCILIATION ───────────────────────────────────────────────────────────

def reconcile_position(
    asset: str,
    state: dict,
    bn_client: BinanceTestnetClient,
    hl_client,
) -> bool:
    """
    Verify spot and perp USD notionals are within RECONCILE_TOL.
    Returns True if OK (or position is flat). Returns False + sends alert on mismatch.
    No new positions should be opened if this returns False.
    """
    if state["position"] != "open":
        return True

    try:
        spot_price = bn_client.get_current_price(asset + "USDT")
        spot_value = state["spot_qty"] * spot_price

        hl_pos       = hl_client.get_position(asset)
        perp_size_usd = hl_pos["size"] * spot_price  # coins × price = USD

        if perp_size_usd == 0 and spot_value == 0:
            return True

        if perp_size_usd == 0 or spot_value == 0:
            msg = (f"[{asset}] RECONCILE: one leg missing — "
                   f"spot=${spot_value:.2f} perp=${perp_size_usd:.2f}")
            logger.error(msg)
            notifier.send(f"[DN RECONCILE ERROR] {msg}", level="error")
            return False

        mismatch = abs(spot_value - perp_size_usd) / max(spot_value, perp_size_usd)
        if mismatch > RECONCILE_TOL:
            msg = (f"[{asset}] RECONCILE MISMATCH {mismatch:.1%} > {RECONCILE_TOL:.0%} — "
                   f"spot=${spot_value:.2f} perp=${perp_size_usd:.2f}. No new positions.")
            logger.error(msg)
            notifier.send(f"[DN RECONCILE] {msg}", level="warning")
            return False

        logger.info(f"[{asset}] Reconciliation OK: "
                    f"spot=${spot_value:.2f} perp=${perp_size_usd:.2f} "
                    f"mismatch={mismatch:.2%}")
        return True

    except Exception as exc:
        logger.error(f"[{asset}] Reconciliation error: {exc}")
        notifier.send(f"[DN RECONCILE ERROR] {asset}: {exc}", level="warning")
        return False


# ─── ATOMIC PAIR OPEN ─────────────────────────────────────────────────────────

def open_pair(
    asset: str,
    notional_usd: float,
    bn_client: BinanceTestnetClient,
    hl_client,
    dry_run: bool = False,
) -> dict | None:
    """
    Atomically open delta-neutral pair.

    Execution order:
      1. Binance spot buy (leg A)
      2. Hyperliquid perp short (leg B)

    ONE-LEGGED PREVENTION:
      If BN buy fails  → return None (HL never opened, nothing to unwind).
      If HL short fails → immediately market-sell the BN spot position.
        Alert: "EMERGENCY: one-legged position detected, closing spot leg"

    Returns new state dict on full success, None on any failure.
    """
    symbol = asset + "USDT"

    if dry_run:
        logger.info(f"[{asset}] DRY-RUN: would buy ${notional_usd:.2f} BN spot "
                    f"+ short ${notional_usd:.2f} HL perp")
        return None  # caller handles dry-run display

    # ── Leg A: Binance spot buy ───────────────────────────────────────────────
    bn_result = None
    try:
        bn_result = bn_client.market_buy(symbol, notional_usd)
        logger.info(f"[{asset}] BN spot buy: {bn_result['qty']:.6f} "
                    f"@ {bn_result['avg_price']:.4f}")
    except Exception as exc:
        msg = f"[{asset}] BN spot BUY FAILED: {exc}. Nothing opened."
        logger.error(msg)
        notifier.send(f"[DN ERROR] {msg}", level="error")
        return None

    # ── Leg B: Hyperliquid perp short ────────────────────────────────────────
    try:
        hl_client.open_short(asset, notional_usd)
        logger.info(f"[{asset}] HL perp short opened: ${notional_usd:.2f}")

        return {
            "position":         "open",
            "spot_qty":         bn_result["qty"],
            "perp_notional":    notional_usd,
            "entry_time":       datetime.now(timezone.utc).isoformat(),
            "cumulative_carry": 0.0,
        }

    except Exception as exc:
        # ONE-LEGGED: BN spot is open, HL failed → emergency sell BN spot
        emergency = (f"EMERGENCY: one-legged position detected, closing spot leg "
                     f"({asset} qty={bn_result['qty']:.6f})")
        logger.error(f"[{asset}] HL SHORT FAILED: {exc}. {emergency}")
        notifier.send(emergency, level="error")
        try:
            bn_client.market_sell(symbol, bn_result["qty"])
            logger.info(f"[{asset}] Emergency BN spot sell successful.")
        except Exception as exc2:
            critical = (f"CRITICAL: failed to close one-legged BN spot for {asset}: {exc2}. "
                        f"Manual intervention required.")
            logger.critical(critical)
            notifier.send(f"[DN CRITICAL] {critical}", level="error")
        return None


# ─── ATOMIC PAIR CLOSE ────────────────────────────────────────────────────────

def close_pair(
    asset: str,
    state: dict,
    bn_client: BinanceTestnetClient,
    hl_client,
    dry_run: bool = False,
) -> dict:
    """
    Atomically close delta-neutral pair.

    Execution order:
      1. Close Hyperliquid perp short first (removes hedge)
      2. Sell Binance spot second

    Rationale for HL-first close: if BN sell fails after HL closes, we have
    a one-legged long spot (manageable — no leveraged short exposure). If HL
    fails first, we keep both legs intact (still delta-neutral).

    ONE-LEGGED PREVENTION ON CLOSE:
      If HL close fails → keep BN spot, send alert (both legs still open).
      If BN sell fails after HL close → EMERGENCY alert (one-legged spot long).

    Returns flat state dict on full success, unchanged state on HL failure,
    or partial state (perp_notional=0) on BN failure with emergency alert.
    """
    symbol     = asset + "USDT"
    flat_state = {**_FLAT_STATE, "cumulative_carry": state.get("cumulative_carry", 0.0)}

    if dry_run:
        logger.info(f"[{asset}] DRY-RUN: would close HL short + sell {state['spot_qty']:.6f} BN spot")
        return flat_state

    # ── Leg 1: Close HL perp short ────────────────────────────────────────────
    try:
        hl_client.close_position(asset, side="short")
        logger.info(f"[{asset}] HL perp short closed.")
    except Exception as exc:
        msg = (f"[{asset}] HL CLOSE FAILED: {exc}. "
               f"Keeping BN spot open to preserve delta-neutral hedge.")
        logger.error(msg)
        notifier.send(f"[DN ERROR] {msg}", level="error")
        return state  # both legs intact, position still "open"

    # ── Leg 2: Sell Binance spot ──────────────────────────────────────────────
    try:
        result = bn_client.market_sell(symbol, state["spot_qty"])
        logger.info(f"[{asset}] BN spot sold: {result['qty']:.6f} @ {result['avg_price']:.4f}")
        return flat_state
    except Exception as exc:
        # HL is closed, BN still open → one-legged spot long
        emergency = (f"EMERGENCY: one-legged position detected, closing spot leg — "
                     f"HL {asset} short already closed, BN spot SELL FAILED: {exc}. "
                     f"Manual sell required: {state['spot_qty']:.6f} {asset} on Binance testnet.")
        logger.error(emergency)
        notifier.send(emergency, level="error")
        # Mark perp as flat (closed), spot still held
        return {**state, "perp_notional": 0.0}


# ─── CARRY LOGGING ────────────────────────────────────────────────────────────

def log_carry_csv(asset: str, carry_usd: float, period_start: datetime) -> None:
    """Append one carry payment row to logs/delta_neutral_carry.csv."""
    LOG_DIR.mkdir(exist_ok=True)
    csv_path = LOG_DIR / "delta_neutral_carry.csv"
    header   = not csv_path.exists()
    with open(csv_path, "a") as f:
        if header:
            f.write("timestamp,asset,carry_usd,period_start\n")
        f.write(
            f"{datetime.now(timezone.utc).isoformat()},{asset},"
            f"{carry_usd:.6f},{period_start.isoformat()}\n"
        )


# ─── PER-ASSET EXECUTION ──────────────────────────────────────────────────────

def run_asset(
    asset: str,
    carry_mean_8h: float,
    bn_client: BinanceTestnetClient | None,
    hl_client,
    dry_run: bool,
) -> dict:
    """
    Execute delta-neutral logic for one asset. Returns summary dict.

    Carry decision:
      carry_mean_8h > CARRY_FLOOR_8H AND not open → OPEN
      carry_mean_8h ≤ 0 AND open                  → CLOSE (negative carry)
      otherwise                                     → HOLD
    """
    state   = load_state(asset)
    summary = {
        "asset":         asset,
        "action":        "HOLD",
        "carry_8h":      carry_mean_8h,
        "spot_qty":      state["spot_qty"],
        "carry_earned":  0.0,
        "basis_pct":     None,
    }

    # Reconciliation (live only)
    if not dry_run and bn_client is not None and hl_client is not None:
        if not reconcile_position(asset, state, bn_client, hl_client):
            summary["action"] = "RECONCILE_FAIL"
            return summary

    carry_positive = carry_mean_8h > CARRY_FLOOR_8H
    carry_negative = carry_mean_8h <= 0.0
    currently_open = state["position"] == "open"

    if carry_positive and not currently_open:
        new_state = open_pair(asset, NOTIONAL_USD, bn_client, hl_client, dry_run)
        if dry_run:
            summary["action"] = "DRY_OPEN"
        elif new_state is not None:
            save_state(asset, new_state)
            summary["action"]   = "OPEN"
            summary["spot_qty"] = new_state["spot_qty"]
        else:
            summary["action"] = "OPEN_FAILED"

    elif carry_negative and currently_open:
        # Funding flipped negative — close to stop paying
        new_state = close_pair(asset, state, bn_client, hl_client, dry_run)
        if not dry_run:
            save_state(asset, new_state)
        summary["action"]   = "CLOSE"
        summary["spot_qty"] = 0.0

    else:
        # HOLD — log carry income if live and open
        if not dry_run and currently_open and hl_client is not None:
            try:
                since   = datetime.now(timezone.utc) - timedelta(hours=8)
                records = hl_client.get_funding_paid(asset, since=since)
                carry_usd = sum(float(r.get("funding_usd", 0)) for r in records)
                if carry_usd != 0.0:
                    log_carry_csv(asset, carry_usd, since)
                    state["cumulative_carry"] = state.get("cumulative_carry", 0.0) + carry_usd
                    save_state(asset, state)
                summary["carry_earned"] = carry_usd
            except Exception as fe:
                logger.warning(f"[{asset}] Carry log failed (non-fatal): {fe}")

        # Live basis check
        if not dry_run and currently_open and bn_client is not None and hl_client is not None:
            try:
                spot_px = bn_client.get_current_price(asset + "USDT")
                hl_pos  = hl_client.get_position(asset)
                perp_px = hl_pos.get("entry_price", spot_px)
                basis   = abs(perp_px - spot_px) / spot_px * 100
                summary["basis_pct"] = round(basis, 3)
            except Exception:
                pass

    return summary


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def run(
    dry_run: bool = True,
    bn_api_key: str | None = None,
    bn_secret_key: str | None = None,
    hl_private_key: str | None = None,
) -> None:
    check_kill_switch()

    now_utc = datetime.now(timezone.utc)
    mode    = "DRY-RUN" if dry_run else "LIVE (TESTNET)"
    logger.info(f"=== DELTA NEUTRAL | {mode} | {now_utc.strftime('%Y-%m-%d %H:%M UTC')} ===")

    # ── Build clients ─────────────────────────────────────────────────────────
    bn_client = None
    hl_client = None
    if not dry_run:
        if not bn_api_key or not bn_secret_key:
            logger.error("--bn-key and --bn-secret required for --live")
            sys.exit(1)
        if not hl_private_key:
            logger.error("--hl-key required for --live")
            sys.exit(1)
        bn_client = BinanceTestnetClient(bn_api_key, bn_secret_key)
        from strategies.delta_neutral.hl_perp_client import HLPerpClient
        hl_client = HLPerpClient(private_key=hl_private_key, testnet=True)

    # ── Carry filter ──────────────────────────────────────────────────────────
    logger.info("Fetching 30d HL carry data...")
    carry_data:   dict[str, float] = {}
    stale_assets: list[str]        = []

    for asset in VIABLE_ASSETS:
        if not check_hl_data_freshness(asset):
            stale_assets.append(asset)
            logger.warning(f"[{asset}] Stale HL funding data (>{MAX_FUNDING_AGE_H}h) — skipping")
            continue
        mean_8h = fetch_hl_carry_30d(asset)
        if mean_8h is None:
            logger.warning(f"[{asset}] Could not fetch carry — skipping")
            continue
        carry_data[asset] = mean_8h
        logger.info(f"[{asset}] carry_mean_8h={mean_8h:.6f} "
                    f"({'PASS' if mean_8h > CARRY_FLOOR_8H else 'FAIL'} carry filter)")

    if stale_assets:
        msg = f"Stale HL data for: {stale_assets}"
        notifier.send(f"[DN WARNING] {msg}", level="warning")

    active_assets = [a for a in VIABLE_ASSETS
                     if carry_data.get(a, 0.0) > CARRY_FLOOR_8H][:MAX_ASSETS]
    logger.info(f"Active (carry > floor): {active_assets}")

    # ── Per-asset execution ────────────────────────────────────────────────────
    results: list[dict] = []
    errors:  list[str]  = []

    for asset in VIABLE_ASSETS:
        if asset not in carry_data:
            continue  # stale or failed — skip silently
        try:
            summary = run_asset(
                asset, carry_data[asset], bn_client, hl_client, dry_run
            )
            results.append(summary)
        except Exception as exc:
            logger.error(f"[{asset}] Unhandled exception: {exc}", exc_info=True)
            errors.append(f"{asset}: {type(exc).__name__}: {exc}")
            notifier.send(f"[DN ERROR] {asset}: {exc}", level="error")

    # ── Telegram summary ──────────────────────────────────────────────────────
    n_open    = sum(1 for r in results if load_state(r["asset"])["position"] == "open")
    total_carry = sum(r["carry_earned"] for r in results)

    lines = [
        f"DELTA NEUTRAL | {now_utc.strftime('%Y-%m-%d %H:%M UTC')}",
        f"Active pairs: {n_open}",
        f"Carry earned this period: ${total_carry:.2f}",
    ]
    for r in results:
        ann_pct   = r["carry_8h"] * 3 * 365 * 100
        basis_str = f", basis={r['basis_pct']:.3f}%" if r.get("basis_pct") is not None else ""
        spot_val  = r["spot_qty"] * 1.0  # rough; exact in live mode via reconcile
        lines.append(
            f"  {r['asset']}: spot={r['spot_qty']:.4f} long, "
            f"carry≈{ann_pct:.1f}%/yr, action={r['action']}{basis_str}"
        )
    if results:
        lines.append(
            f"Portfolio: carry=${total_carry:.4f} "
            f"fees=~${sum(NOTIONAL_USD * 0.0042 for r in results if r['action'] in ('OPEN','CLOSE')):.2f}"
        )
    if errors:
        lines.append(f"ERRORS: {'; '.join(errors)}")

    notifier.send("\n".join(lines), level="error" if errors else "info")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    import os

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(
        description="Delta-Neutral live trader — Binance testnet + HL testnet"
    )
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--dry-run", dest="dry_run", action="store_true", default=True)
    grp.add_argument("--live",    dest="dry_run", action="store_false")
    parser.add_argument("--bn-key",    default=None)
    parser.add_argument("--bn-secret", default=None)
    parser.add_argument("--hl-key",    default=None)
    args = parser.parse_args()

    run(
        dry_run       = args.dry_run,
        bn_api_key    = args.bn_key    or os.getenv("BINANCE_TESTNET_API_KEY"),
        bn_secret_key = args.bn_secret or os.getenv("BINANCE_TESTNET_SECRET_KEY"),
        hl_private_key= args.hl_key    or os.getenv("HYPERLIQUID_TESTNET_KEY"),
    )
