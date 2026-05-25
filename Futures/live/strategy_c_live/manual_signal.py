"""
manual_signal.py — Generate iter_10 signal and send Telegram alert for manual execution.
=========================================================================================
Workflow:
  1. Cron (or launcher) triggers this script at 09:43 ET (15:43 Paris) each weekday.
  2. Script fetches MNQ 1-min bars 09:30-09:43 from yfinance (free tier, ~5-15min delay).
  3. Computes iter_10 signal using confirmed bars only (no lookahead).
  4. Sends Telegram with full trade instructions for manual entry in Tradovate Demo.
  5. Logs signal row to logs/manual_paper_trades.csv for post-session reconciliation.

User clicks manually in Tradovate Demo web interface at 09:46 ET (15:46 Paris).
User fills actual_entry_price / actual_exit_price in CSV after session.

yfinance delay note: free tier for futures (MNQ=F) can have 5-15min latency.
If the signal arrives after 09:47 ET, skip the day and log "data_lag".

Signal keys from compute_signal():
  direction, entry_estimate, tp_price, sl_price, tp_pts, sl_pts,
  opening_range, vwap_at_945, gap_pct (already ×100), signal_strength

Run: /usr/bin/python3 -m Futures.live.strategy_c_live.manual_signal
Test: /usr/bin/python3 -m Futures.live.strategy_c_live.manual_signal --test-telegram
"""
from __future__ import annotations

import csv
import logging
import sys
from datetime import datetime
from datetime import time as dt_time
from pathlib import Path
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[4]))

from Futures.live.strategy_c_live.signal_engine import compute_signal
from Futures.live.strategy_c_live.config import N_CONTRACTS_DEFAULT, ORB_OPEN, ORB_CLOSE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")
CSV_LOG = Path(__file__).parent / "logs" / "manual_paper_trades.csv"

CSV_HEADERS = [
    "date_et", "signal_time_et", "direction", "entry_trigger",
    "tp_target", "sl_target", "time_stop", "gap_pct", "orb_size_pts",
    "vwap_at_signal", "atr_15min",
    # USER FILLS (complete after each trading session)
    "actual_entry_time_et", "actual_entry_price",
    "actual_exit_time_et", "actual_exit_price", "actual_exit_reason",
    "user_notes",
]

_SIGNAL_WINDOW_START = dt_time(9, 43)
_SIGNAL_WINDOW_END   = dt_time(9, 47)


# ─────────────────────────────────────────────────────────────────────────────
# Data fetch
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_bars(symbol: str = "MNQ=F") -> pd.DataFrame:
    """Fetch 2d of 1-min RTH bars from yfinance (free tier).

    Returns DataFrame with lowercase columns and ET-aware DatetimeIndex.
    Raises RuntimeError on empty response.
    """
    try:
        import yfinance as yf
    except ImportError as e:
        raise RuntimeError("yfinance not installed: pip install yfinance") from e

    df = yf.download(symbol, period="2d", interval="1m",
                     prepost=False, progress=False, auto_adjust=True)
    if df.empty:
        raise RuntimeError(f"Empty bars from yfinance for {symbol}")

    # Handle MultiIndex (yfinance >= 0.2 for single ticker)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    df.columns = [c.lower() for c in df.columns]

    # Normalize to ET
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(ET)
    else:
        df.index = df.index.tz_convert(ET)

    # RTH only
    df = df[(df.index.time >= dt_time(9, 30)) & (df.index.time < dt_time(16, 0))]
    return df


# ─────────────────────────────────────────────────────────────────────────────
# ATR helper
# ─────────────────────────────────────────────────────────────────────────────

def _atr15(bars: pd.DataFrame) -> float:
    """High-low range over the 09:30-09:45 ORB window (volatility context)."""
    orb = bars[
        (bars.index.time >= ORB_OPEN) &
        (bars.index.time <= ORB_CLOSE)
    ]
    if orb.empty:
        return 0.0
    return float(orb["high"].max() - orb["low"].min())


# ─────────────────────────────────────────────────────────────────────────────
# Telegram helpers
# ─────────────────────────────────────────────────────────────────────────────

def _telegram_signal(sig: dict, today_str: str, n_contracts: int) -> None:
    from notifier import send
    send(
        f"iter_10 SIGNAL [{today_str}]\n\n"
        f"Direction: {sig['direction']}\n"
        f"Contracts: {n_contracts} MNQ\n"
        f"Entry: market @ 09:46 ET (15:46 Paris)\n"
        f"  Ref price: {sig['entry_estimate']:.2f}\n"
        f"TP: {sig['tp_price']:.2f}  (+{sig['tp_pts']:.0f} pts)\n"
        f"SL: {sig['sl_price']:.2f}  (-{sig['sl_pts']:.0f} pts)\n"
        f"Time stop: 12:30 ET (18:30 Paris)\n\n"
        f"Context:\n"
        f"  Gap: {sig['gap_pct']:+.2f}%\n"
        f"  ORB: {sig['opening_range']:.0f} pts  [{sig['signal_strength']}]\n"
        f"  VWAP: {sig['vwap_at_945']:.2f}\n"
        f"  ATR_15m: {sig.get('atr_15min', 0):.0f} pts\n\n"
        f"ACTION: Open Tradovate Demo now.\n"
        f"Bracket OCO: TP={sig['tp_price']:.2f} / SL={sig['sl_price']:.2f}\n"
        f"Log fill in manual_paper_trades.csv post-session.",
        level="info",
    )


def _telegram_no_trade(today_str: str, reason: str) -> None:
    from notifier import send
    send(f"iter_10 [{today_str}]: NO TRADE\n{reason}", level="info")


def _telegram_test() -> None:
    from notifier import send
    send(
        "iter_10 manual signal pipeline test\n"
        "Setup phase — no real trade.\n"
        "Telegram delivery confirmed.",
        level="info",
    )
    log.info("Test Telegram sent.")


# ─────────────────────────────────────────────────────────────────────────────
# CSV log
# ─────────────────────────────────────────────────────────────────────────────

def _append_csv(row: dict) -> None:
    CSV_LOG.parent.mkdir(parents=True, exist_ok=True)
    is_new = not CSV_LOG.exists()
    with open(CSV_LOG, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def _log_signal(sig: dict, today_str: str, signal_time: str) -> None:
    _append_csv({
        "date_et":           today_str,
        "signal_time_et":    signal_time,
        "direction":         sig["direction"],
        "entry_trigger":     f"{sig['entry_estimate']:.2f}",
        "tp_target":         f"{sig['tp_price']:.2f}",
        "sl_target":         f"{sig['sl_price']:.2f}",
        "time_stop":         "12:30",
        "gap_pct":           f"{sig['gap_pct']:.4f}",
        "orb_size_pts":      f"{sig['opening_range']:.2f}",
        "vwap_at_signal":    f"{sig['vwap_at_945']:.2f}",
        "atr_15min":         f"{sig.get('atr_15min', 0.0):.2f}",
        "actual_entry_time_et":  "",
        "actual_entry_price":    "",
        "actual_exit_time_et":   "",
        "actual_exit_price":     "",
        "actual_exit_reason":    "",
        "user_notes":            "",
    })


def _log_no_trade(
    today_str: str,
    signal_time: str,
    reason: str,
    sig: Optional[dict] = None,
) -> None:
    row: dict = {h: "" for h in CSV_HEADERS}
    row["date_et"]        = today_str
    row["signal_time_et"] = signal_time
    row["direction"]      = "NO_TRADE"
    row["user_notes"]     = reason
    if sig:
        row["gap_pct"]     = f"{sig.get('gap_pct', 0.0):.4f}"
        row["orb_size_pts"] = f"{sig.get('opening_range', 0.0):.2f}"
    _append_csv(row)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def generate_signal_and_alert() -> None:
    now_et     = datetime.now(ET)
    today_str  = now_et.strftime("%Y-%m-%d")
    time_str   = now_et.strftime("%H:%M:%S")

    if now_et.weekday() >= 5:
        log.info("Weekend — no signal generation.")
        return

    if not (_SIGNAL_WINDOW_START <= now_et.time() <= _SIGNAL_WINDOW_END):
        log.info(
            "Outside signal window %s-%s ET (%s) — skipping.",
            _SIGNAL_WINDOW_START, _SIGNAL_WINDOW_END, time_str,
        )
        return

    try:
        bars = _fetch_bars()
    except Exception as e:
        log.error("Data fetch failed: %s", e)
        _telegram_no_trade(today_str, f"Data fetch error: {e}")
        _log_no_trade(today_str, time_str, f"data_fetch_error: {e}")
        return

    today_bars = bars[bars.index.date == now_et.date()]
    if len(today_bars) < 13:
        msg = f"Insufficient bars ({len(today_bars)}/13 min). Possible yfinance lag or delayed open."
        log.warning(msg)
        _telegram_no_trade(today_str, msg)
        _log_no_trade(today_str, time_str, "data_lag")
        return

    atr15 = _atr15(today_bars)
    sig   = compute_signal(bars)

    if sig is None:
        log.info("No signal — filters not passed.")
        _telegram_no_trade(today_str, "Filters not passed (gap/ORB/VWAP). Sit out today.")
        _log_no_trade(today_str, time_str, "filters_not_passed")
        return

    sig["atr_15min"] = atr15
    n_contracts = N_CONTRACTS_DEFAULT

    _telegram_signal(sig, today_str, n_contracts)
    _log_signal(sig, today_str, time_str)

    log.info(
        "Signal sent: %s @ ref %.2f | TP=%.2f SL=%.2f | ORB=%.0f gap=%+.2f%%",
        sig["direction"], sig["entry_estimate"],
        sig["tp_price"], sig["sl_price"],
        sig["opening_range"], sig["gap_pct"],
    )


if __name__ == "__main__":
    if "--test-telegram" in sys.argv:
        _telegram_test()
    else:
        generate_signal_and_alert()
