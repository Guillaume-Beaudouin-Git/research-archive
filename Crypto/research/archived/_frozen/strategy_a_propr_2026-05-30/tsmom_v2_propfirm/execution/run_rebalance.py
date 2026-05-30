#!/usr/bin/env python
"""
TSMOM v2 — weekly rebalance entry point.

Usage:
    PROPR_API_KEY=pk_live_... python -m strategies.tsmom_v2_propfirm.execution.run_rebalance

Cron (print at end of run, do not install automatically):
    5 0 * * 1 cd ~/Desktop/Algo_claude && \
    source "<HOME>/Desktop/Unholy returns/Python3.12.9/myenv/bin/activate" && \
    PROPR_API_KEY=pk_live_XXX python -m \
    strategies.tsmom_v2_propfirm.execution.run_rebalance \
    >> logs/tsmom_v2_cron.log 2>&1
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Logging setup (before any imports that may log) ────────────────────────
_LOG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_LOG_DIR / "tsmom_v2_cron.log"),
    ],
)
logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────────────
ACCOUNT_ID = "urn:prp-account:KBNeHP5eN3mz"
ATTEMPT_ID = "urn:prp-challenge-attempt:YrWnSPahXiz2"

try:
    API_KEY = os.environ["PROPR_API_KEY"]
except KeyError:
    logger.critical("PROPR_API_KEY environment variable is not set. Aborting.")
    sys.exit(1)

import argparse as _argparse
_parser = _argparse.ArgumentParser(description="TSMOM v2 weekly rebalance")
_parser.add_argument("--dry-run", action="store_true", help="Compute signals and log intent, place no orders")
_args, _ = _parser.parse_known_args()
DRY_RUN: bool = _args.dry_run

from . import STATE_DB_PATH
from .equity_monitor import EquityMonitor
from .guardrail_loop import is_kill_switch_set, start_guardrail_loop
from .order_executor import get_positions
from .rebalance import run_weekly_rebalance


def _count_trading_days() -> int:
    """Count rows in rebalance_log as a proxy for trading-days-this-attempt."""
    try:
        with sqlite3.connect(STATE_DB_PATH) as conn:
            row = conn.execute("SELECT COUNT(*) FROM rebalance_log WHERE dry_run = 0").fetchone()
            return int(row[0]) if row else 0
    except Exception:
        return 0


def _try_send_alert(message: str, level: str = "info") -> None:
    try:
        from notifier import send  # type: ignore[import-not-found]
        send(message, level=level)
    except ImportError:
        logger.warning("Telegram notifier not available")
    except Exception as exc:
        logger.warning("Telegram send failed: %s", exc)


def main() -> None:
    logger.info("=" * 60)
    logger.info("TSMOM v2 — Weekly Rebalance  %s UTC",
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    # 1 — Kill-switch check
    if is_kill_switch_set():
        logger.critical("Kill switch is set — aborting. Reset challenge_state.db to resume.")
        sys.exit(1)

    # 2 — Equity safety check
    monitor = EquityMonitor(ATTEMPT_ID, ACCOUNT_ID, API_KEY)
    if not monitor.is_safe():
        status = monitor.get_status()
        logger.critical(
            "Equity not safe before rebalance — aborting. "
            "DailyDD=%.3f%% TotalDD=%.3f%%",
            status["daily_dd"] * 100, status["total_dd"] * 100,
        )
        sys.exit(1)

    # 3 — Start guardrail daemon
    start_guardrail_loop(ACCOUNT_ID, ATTEMPT_ID, API_KEY)
    logger.info("Guardrail loop started.")

    # 4 — Run rebalance
    run_weekly_rebalance(ACCOUNT_ID, ATTEMPT_ID, API_KEY, dry_run=DRY_RUN)

    # 5 — Completion notification
    try:
        status = monitor.get_status()
        positions = get_positions(ACCOUNT_ID, API_KEY)
        open_assets = ", ".join(sorted(positions.keys())) or "none"
        trading_days = _count_trading_days()

        message = (
            f"📊 TSMOM v2 Rebalance Complete\n"
            f"  Equity     : ${status['equity']:.2f} USDC\n"
            f"  Daily DD   : {status['daily_dd']:.2%}\n"
            f"  Total DD   : {status['total_dd']:.2%}\n"
            f"  Open assets: {open_assets}\n"
            f"  Trading days this attempt: {trading_days}"
        )
        logger.info(message)
        _try_send_alert(message, level="info")
    except Exception as exc:
        logger.warning("Post-rebalance summary failed: %s", exc)

    logger.info("Run complete.")
    logger.info(
        "\nCron line for VPS deployment:\n"
        "  5 0 * * 1 cd ~/Desktop/Algo_claude && "
        'source "<HOME>/Desktop/Unholy returns/Python3.12.9/myenv/bin/activate" && '
        "PROPR_API_KEY=pk_live_XXX python -m "
        "strategies.tsmom_v2_propfirm.execution.run_rebalance "
        ">> logs/tsmom_v2_cron.log 2>&1"
    )


if __name__ == "__main__":
    main()
