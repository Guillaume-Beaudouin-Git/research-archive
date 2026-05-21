"""
iter_02.py — VWAP Momentum Filter
===================================
BUILD ON: iter_1a (TP=1.5R, SL=0.5R) — Sharpe 0.797, PF 1.162, WF 100%

HYPOTHESIS: Opening momentum is stronger when VWAP confirms signal direction.
Price above VWAP + bullish open = institutional long accumulation.
Price below VWAP + bullish open = liquidity vacuum, weaker signal.

Variants:
  2a: Filter A only — VWAP confirmation (price vs VWAP_RTH at signal)
  2b: Filter B only — Volume confirmation (15min vol > 1.2× 20d avg)
  2c: Filter A + Filter B
  2d: Filter A + Filter B + gap sizing (1.5× size if overnight gap aligns)

n_tests: 88 → 92
"""

from __future__ import annotations

import datetime
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[4]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, append_result, load_results, print_comparison_table
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

N_TESTS_START = 88

BASE_PARAMS = {"tp_mult": 1.5, "sl_mult": 0.5}   # iter_1a base

T_0930 = datetime.time(9, 30)
T_0945 = datetime.time(9, 45)
T_1230 = datetime.time(12, 30)


# ---------------------------------------------------------------------------
# Feature builders
# ---------------------------------------------------------------------------

def _opening_features(df_1min: pd.DataFrame) -> pd.DataFrame:
    """
    Per-day features needed for all filters.
    Returns DataFrame indexed by date with columns:
      sig_ts, direction, open_price, close_price, rng,
      vwap_at_signal, vol_15min, prev_day_close, prev_day_open
    """
    records = []
    dates = sorted(df_1min.index.normalize().unique())

    # Build prev-day close/open lookup
    day_open  = {}
    day_close = {}
    for date in dates:
        day = df_1min[df_1min.index.normalize() == date]
        rth = day[(day.index.time >= T_0930) & (day.index.time <= datetime.time(15,59))]
        if not rth.empty:
            day_open[date]  = float(rth.iloc[0]["open"])
            day_close[date] = float(rth.iloc[-1]["close"])

    for i, date in enumerate(dates):
        day = df_1min[df_1min.index.normalize() == date]
        opening = day[(day.index.time >= T_0930) & (day.index.time <= T_0945)]
        if len(opening) < 2:
            continue

        open_p  = float(opening.iloc[0]["open"])
        close_p = float(opening.iloc[-1]["close"])
        rng     = abs(close_p - open_p)
        if rng < 1.0:
            continue

        direction   = 1 if close_p > open_p else -1
        sig_ts      = opening.index[-1]
        vwap_at_sig = float(opening.iloc[-1]["vwap_rth"])
        vol_15min   = int(opening["volume"].sum())

        # Previous day close and open
        prev_date  = dates[i - 1] if i > 0 else None
        prev_close = day_close.get(prev_date, np.nan) if prev_date else np.nan
        prev_open  = day_open.get(prev_date, np.nan)  if prev_date else np.nan

        exit_time = pd.Timestamp(
            date.year, date.month, date.day,
            T_1230.hour, T_1230.minute, 0,
            tzinfo=sig_ts.tzinfo,
        )

        records.append({
            "date":         date,
            "sig_ts":       sig_ts,
            "direction":    direction,
            "open_price":   open_p,
            "close_price":  close_p,
            "rng":          rng,
            "vwap_at_sig":  vwap_at_sig,
            "vol_15min":    vol_15min,
            "prev_close":   prev_close,
            "prev_open":    prev_open,
            "exit_time":    exit_time,
        })

    return pd.DataFrame(records)


def _vol_threshold(feats: pd.DataFrame, window: int = 20) -> pd.Series:
    """Rolling 20-day average of vol_15min."""
    return feats["vol_15min"].rolling(window, min_periods=5).mean().shift(1)


# ---------------------------------------------------------------------------
# Variant filters
# ---------------------------------------------------------------------------

def filter_A(row: pd.Series) -> bool:
    """VWAP confirmation: price at signal is above/below VWAP in signal direction."""
    if row["direction"] == 1:
        return row["close_price"] > row["vwap_at_sig"]
    else:
        return row["close_price"] < row["vwap_at_sig"]


def filter_B(row: pd.Series, vol_avg: float) -> bool:
    """Volume confirmation: first 15min vol > 1.2× rolling 20d avg."""
    if not np.isfinite(vol_avg) or vol_avg <= 0:
        return True   # no history → allow trade
    return row["vol_15min"] > 1.2 * vol_avg


def gap_size_mult(row: pd.Series) -> float:
    """
    1.5 if overnight gap aligns with signal direction, else 1.0.
    Gap direction = sign(today_open - prev_close).
    """
    if not np.isfinite(row["prev_close"]) or row["prev_close"] <= 0:
        return 1.0
    gap = row["open_price"] - row["prev_close"]
    if gap == 0:
        return 1.0
    return 1.5 if np.sign(gap) == row["direction"] else 1.0


# ---------------------------------------------------------------------------
# Signal builder
# ---------------------------------------------------------------------------

def build_signals_v2(feats: pd.DataFrame, vol_avgs: pd.Series,
                     use_A: bool, use_B: bool, use_gap: bool) -> pd.DataFrame:
    records = []
    for idx, row in feats.iterrows():
        vol_avg = float(vol_avgs.iloc[idx]) if idx < len(vol_avgs) else np.nan

        # Apply filters
        if use_A and not filter_A(row):
            continue
        if use_B and not filter_B(row, vol_avg):
            continue

        size_mult = gap_size_mult(row) if use_gap else 1.0

        records.append({
            "signal_ts": row["sig_ts"],
            "direction": row["direction"],
            "tp_points": row["rng"] * BASE_PARAMS["tp_mult"],
            "sl_points": row["rng"] * BASE_PARAMS["sl_mult"],
            "exit_time": row["exit_time"],
            "size_mult": size_mult,
        })

    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records).set_index("signal_ts")


# ---------------------------------------------------------------------------
# WF wrapper
# ---------------------------------------------------------------------------

def _make_signal_fn(use_A, use_B, use_gap):
    def signal_fn(df_window: pd.DataFrame, params: dict) -> pd.DataFrame:
        feats    = _opening_features(df_window)
        if feats.empty:
            return pd.DataFrame()
        vol_avgs = _vol_threshold(feats)
        sigs     = build_signals_v2(feats, vol_avgs, use_A, use_B, use_gap)
        return sigs
    return signal_fn


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== Iter 02 — VWAP Momentum Filter ===")

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)

    feats    = _opening_features(engine.rth)
    vol_avgs = _vol_threshold(feats)

    log.info(f"Total opening features: {len(feats)}")

    # Baseline for comparison (iter_1a — no filters)
    base_sigs = build_signals_v2(feats, vol_avgs,
                                 use_A=False, use_B=False, use_gap=False)

    VARIANT_DEFS = {
        "2a": dict(use_A=True,  use_B=False, use_gap=False),
        "2b": dict(use_A=False, use_B=True,  use_gap=False),
        "2c": dict(use_A=True,  use_B=True,  use_gap=False),
        "2d": dict(use_A=True,  use_B=True,  use_gap=True),
    }

    n_test    = N_TESTS_START
    n_base    = len(base_sigs)
    best_sharpe  = -np.inf
    best_variant = None

    for var_id, flags in VARIANT_DEFS.items():
        n_test += 1
        sigs = build_signals_v2(feats, vol_avgs, **flags)
        retain_pct = len(sigs) / n_base * 100 if n_base > 0 else 0
        log.info(f"--- Variant {var_id}: {len(sigs)} signals ({retain_pct:.0f}% of base) ---")

        if len(sigs) < 20:
            log.warning(f"  Too few signals ({len(sigs)}) — skipping variant {var_id}")
            continue

        trade_log, met = engine.run(sigs)
        boot = engine.bootstrap_ev(trade_log)

        sig_fn = _make_signal_fn(**flags)
        wf     = engine.walk_forward(sig_fn, {}, train_months=12, test_months=6)

        sh = met.get("sharpe_daily_hac") or 0
        pf = met.get("profit_factor")    or 0
        if sh >= 1.0 and pf >= 1.20:
            verdict = "STRONG"
        elif sh >= 0.5 and pf >= 1.10:
            verdict = "IMPROVE"
        elif sh >= 0.0 and pf >= 0.95:
            verdict = "WEAK"
        else:
            verdict = "SKIP"

        result = {
            "iteration":        f"iter_{var_id}",
            "n_tests":          n_test,
            "description":      f"VWAP filter A={flags['use_A']} B={flags['use_B']} gap={flags['use_gap']}",
            "signals_retained_pct": round(retain_pct, 1),
            **met,
            **boot,
            "wf_pct_positive":  wf.get("wf_pct_positive"),
            "wf_n_windows":     wf.get("n_windows"),
            "verdict":          verdict,
        }
        append_result(result)

        print(f"\n  [iter_{var_id}] A={flags['use_A']} B={flags['use_B']} gap={flags['use_gap']}")
        print(f"    Signals:  {len(sigs)} ({retain_pct:.0f}% retained)")
        print(f"    Trades:   {met.get('n_trades',0)}  |  WR: {met.get('win_rate',0)*100:.1f}%")
        print(f"    AvgTrd:   ${met.get('avg_trade_usd',0):.1f}  |  PF: {pf:.3f}")
        print(f"    Sharpe:   {sh:.3f}  |  MaxDD: {met.get('max_dd_pct',0)*100:.1f}%")
        print(f"    WF%pos:   {wf.get('wf_pct_positive','?')}%  ({wf.get('n_windows',0)} windows)")
        print(f"    P(EV≤0):  {boot.get('p_ev_zero','?')}  |  95%CI: [{boot.get('ci_low','?')}, {boot.get('ci_high','?')}]")
        print(f"    Verdict:  {verdict}")

        if sh > best_sharpe:
            best_sharpe  = sh
            best_variant = var_id

    print(f"\n--- Iter 02 best variant: iter_{best_variant} (Sharpe={best_sharpe:.3f}) ---")

    results = load_results()
    print_comparison_table(results)

    # Stopping rule check
    if best_sharpe >= 0.5:
        best_results = [r for r in results if r.get("iteration") == f"iter_{best_variant}"]
        pf_best = (best_results[0].get("profit_factor") or 0) if best_results else 0
        if pf_best >= 1.10:
            print(f"\nSTRONG signal: Sharpe={best_sharpe:.3f}, PF={pf_best:.3f}. Continue to iter_03 and iter_04.")
        else:
            print(f"\nModerate signal. Continue to iter_03 (breakout).")
    else:
        print(f"\nNo improvement over baseline in iter_02. Check iter_03 for independent signal.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("iter_02 failed")
        sys.exit(1)
