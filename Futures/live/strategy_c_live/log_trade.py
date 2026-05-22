"""
log_trade.py — Trade logging for Strategy C live / paper trading
================================================================
Extends c_paper_trades.csv with IBKR-specific fill fields.
"""
from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Canonical path for paper trade log
_LOG_DIR = Path(__file__).parents[3] / "Futures" / "research" / "active" / "nq_intraday"
PAPER_LOG = _LOG_DIR / "c_paper_trades.csv"

# Extended schema (original + IBKR fields)
FIELDNAMES = [
    # Original paper log fields
    "date",
    "direction",
    "entry_time",
    "exit_time",
    "exit_reason",
    "entry_price_est",
    "tp_price",
    "sl_price",
    "opening_range_pts",
    "gap_pct",
    "vwap_at_945",
    "signal_strength",
    "tp_pts",
    "sl_pts",
    "n_contracts",
    # IBKR-specific fields
    "actual_entry_price",
    "actual_exit_price",
    "entry_slippage_pts",
    "exit_slippage_pts",
    "ibkr_fill_time_entry",
    "ibkr_fill_time_exit",
    "pnl_usd",
    "account_type",
]


def _ensure_log_exists() -> None:
    """Create log file with header if it doesn't exist."""
    if not PAPER_LOG.exists():
        PAPER_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(PAPER_LOG, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
        log.info("Created paper trade log: %s", PAPER_LOG)


def log_trade(
    trade_date:          str,
    direction:           str,           # 'BUY' or 'SELL'
    entry_time:          str,
    exit_time:           str,
    exit_reason:         str,           # 'tp', 'sl', 'time', 'manual'
    signal:              dict,          # from compute_signal()
    n_contracts:         int,
    actual_entry_price:  Optional[float] = None,
    actual_exit_price:   Optional[float] = None,
    ibkr_fill_time_entry: Optional[str] = None,
    ibkr_fill_time_exit:  Optional[str] = None,
    account_type:        str = 'paper_ibkr',
) -> dict:
    """
    Log a completed trade to c_paper_trades.csv.

    Parameters
    ----------
    trade_date          : 'YYYY-MM-DD'
    direction           : 'BUY' or 'SELL'
    entry_time          : 'HH:MM:SS ET'
    exit_time           : 'HH:MM:SS ET'
    exit_reason         : 'tp' | 'sl' | 'time' | 'manual'
    signal              : dict from compute_signal()
    n_contracts         : number of /MNQ contracts
    actual_entry_price  : filled entry price (None if simulated)
    actual_exit_price   : filled exit price (None if simulated)
    ibkr_fill_time_entry: IBKR fill timestamp string
    ibkr_fill_time_exit : IBKR fill timestamp string
    account_type        : 'paper_ibkr' or 'paper_simulated'
    """
    _ensure_log_exists()

    mnq_pv = 2.0    # $2/pt/MNQ
    mnq_cost = 2.15 # $2.15/RT/MNQ

    # Compute slippage if actual prices known
    entry_slip = None
    exit_slip  = None
    pnl_usd    = None

    if actual_entry_price is not None:
        est = signal.get("entry_estimate", actual_entry_price)
        entry_slip = round(abs(actual_entry_price - est), 2)

    if actual_entry_price is not None and actual_exit_price is not None:
        dir_int = 1 if direction == 'BUY' else -1
        pnl_pts = dir_int * (actual_exit_price - actual_entry_price)
        pnl_usd = round(pnl_pts * mnq_pv * n_contracts - mnq_cost * n_contracts, 2)

        # Exit slippage vs expected price
        if exit_reason == 'tp':
            exp_exit = signal["tp_price"]
        elif exit_reason == 'sl':
            exp_exit = signal["sl_price"]
        else:
            exp_exit = actual_exit_price
        exit_slip = round(abs(actual_exit_price - exp_exit), 2)

    row = {
        "date":               trade_date,
        "direction":          direction,
        "entry_time":         entry_time,
        "exit_time":          exit_time,
        "exit_reason":        exit_reason,
        "entry_price_est":    signal.get("entry_estimate", ""),
        "tp_price":           signal.get("tp_price", ""),
        "sl_price":           signal.get("sl_price", ""),
        "opening_range_pts":  signal.get("opening_range", ""),
        "gap_pct":            signal.get("gap_pct", ""),
        "vwap_at_945":        signal.get("vwap_at_945", ""),
        "signal_strength":    signal.get("signal_strength", ""),
        "tp_pts":             signal.get("tp_pts", ""),
        "sl_pts":             signal.get("sl_pts", ""),
        "n_contracts":        n_contracts,
        "actual_entry_price": actual_entry_price if actual_entry_price is not None else "",
        "actual_exit_price":  actual_exit_price  if actual_exit_price  is not None else "",
        "entry_slippage_pts": entry_slip if entry_slip is not None else "",
        "exit_slippage_pts":  exit_slip  if exit_slip  is not None else "",
        "ibkr_fill_time_entry": ibkr_fill_time_entry or "",
        "ibkr_fill_time_exit":  ibkr_fill_time_exit  or "",
        "pnl_usd":            pnl_usd if pnl_usd is not None else "",
        "account_type":       account_type,
    }

    with open(PAPER_LOG, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)

    log.info(
        "Trade logged: %s %s %d /MNQ | exit=%s | P&L=%s",
        trade_date, direction, n_contracts, exit_reason,
        f"${pnl_usd:+.0f}" if pnl_usd is not None else "pending"
    )
    return row
