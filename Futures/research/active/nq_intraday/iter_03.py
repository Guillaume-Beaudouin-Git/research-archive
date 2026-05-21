"""
iter_03.py — Range Breakout with ATR Sizing
=============================================
DIFFERENT APPROACH — pure breakout, independent of opening momentum.

HYPOTHESIS: When NQ breaks out of a compressed range (low ATR period)
with above-average volume, the breakout continues. Range compression =
coiled spring (volatility clustering: low vol → high vol expansion).

Signal construction:
  - 30-min ATR: prior 5 days of 30-min bars (10 bars/day × 5 = 50-bar ATR)
  - Each session at 10:00 ET: if current 30-min range < 0.6 × ATR_30min_5d → "compressed"
  - First 30-min bar 10:00-12:00 that closes beyond prior bar high/low by > 0.25 × ATR → breakout
  - TP: 2.0 × ATR, SL: 0.8 × ATR (2.5 RR ratio)
  - Time stop: 14:00 ET

Variants:
  3a: Any breakout bar 10:00-12:00 ET
  3b: 3a + volume > 1.5× session avg volume to that point
  3c: 3b + direction aligns with prior day's trend (close > open → prefer longs)

n_tests: 92 → 95
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

N_TESTS_START = 92

T_0930 = datetime.time(9, 30)
T_1000 = datetime.time(10, 0)
T_1030 = datetime.time(10, 30)   # compression check after opening volatility settles
T_1100 = datetime.time(11, 0)
T_1300 = datetime.time(13, 0)
T_1430 = datetime.time(14, 30)
T_1559 = datetime.time(15, 59)
COMPRESS_THRESH = 0.8             # bar range < 0.8x ATR = "compressed"


# ---------------------------------------------------------------------------
# ATR computation on 30-min bars
# ---------------------------------------------------------------------------

def compute_30min_atr(df_1min: pd.DataFrame, lookback_days: int = 5) -> pd.Series:
    """
    Rolling ATR on 30-min bars from last `lookback_days` trading days.
    Returns Series indexed by 30-min bar timestamp.
    """
    bars_30 = df_1min.resample("30T", label="right", closed="right").agg(
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
    ).dropna(subset=["close"])

    # True range
    tr = (bars_30["high"] - bars_30["low"]).abs()
    # Rolling ATR over lookback_days × 10 bars/day = 50 bars
    n_bars = lookback_days * 10
    atr = tr.rolling(n_bars, min_periods=10).mean().shift(1)
    return atr


# ---------------------------------------------------------------------------
# Signal builder
# ---------------------------------------------------------------------------

def build_signals_breakout(
    df_1min: pd.DataFrame,
    atr_30: pd.Series,
    use_vol_filter: bool = False,
    use_trend_filter: bool = False,
) -> pd.DataFrame:
    """
    For each day, find the first breakout bar between 11:00 and 13:00 ET.

    A breakout requires:
      1. Compression at 10:30 ET: 30-min bar range < COMPRESS_THRESH × ATR
         (checking 10:30, not 10:00, because the open bar always has high vol)
      2. First 30-min bar 11:00-13:00 that closes beyond 10:30 high/low by > 0.25 × ATR
      3. (optional) volume on breakout bar > 1.5× session avg to that point
      4. (optional) direction aligns with prior day trend
    """
    records = []
    dates = sorted(df_1min.index.normalize().unique())

    # Build prior day trend lookup
    day_trend = {}
    for date in dates:
        day = df_1min[df_1min.index.normalize() == date]
        rth = day[(day.index.time >= T_0930) & (day.index.time <= T_1559)]
        if not rth.empty:
            d_open  = float(rth.iloc[0]["open"])
            d_close = float(rth.iloc[-1]["close"])
            day_trend[date] = 1 if d_close >= d_open else -1

    for i, date in enumerate(dates):
        day = df_1min[df_1min.index.normalize() == date]
        rth = day[(day.index.time >= T_0930) & (day.index.time <= T_1559)]
        if rth.empty:
            continue

        # Get 30-min bars for this day
        day_30 = rth.resample("30min", label="right", closed="right").agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
        ).dropna(subset=["open"])

        if len(day_30) < 3:
            continue

        # 10:30 bar (second RTH bar, after opening volatility settles)
        bar_1030 = day_30[day_30.index.time == T_1030]
        if bar_1030.empty:
            continue
        bar_1030_row = bar_1030.iloc[0]
        bar_range_1030 = float(bar_1030_row["high"] - bar_1030_row["low"])

        # ATR for this day (already shifted(1) in compute_30min_atr)
        atr_vals = atr_30[atr_30.index.normalize() == date]
        if atr_vals.empty:
            continue
        atr_val = float(atr_vals.iloc[0])   # use first ATR value of the day
        if not np.isfinite(atr_val) or atr_val <= 0:
            continue

        # Check compression at 10:30
        if bar_range_1030 >= COMPRESS_THRESH * atr_val:
            continue   # not compressed

        # Compression point defines the range to break
        prior_high = float(bar_1030_row["high"])
        prior_low  = float(bar_1030_row["low"])

        # Prior day trend
        prev_date  = dates[i - 1] if i > 0 else None
        prev_trend = day_trend.get(prev_date, 0) if prev_date else 0

        # Scan 11:00 to 13:00 bars for breakout
        search_bars = day_30[
            (day_30.index.time >= T_1100) &
            (day_30.index.time <= T_1300)
        ]

        for bar_ts, bar in search_bars.iterrows():
            bar_close = float(bar["close"])
            bar_high  = float(bar["high"])
            bar_low   = float(bar["low"])
            bar_vol   = int(bar["volume"])

            # Breakout: close beyond 10:30 range by > 0.25 × ATR
            bull_bo = bar_close > prior_high + 0.25 * atr_val
            bear_bo = bar_close < prior_low  - 0.25 * atr_val

            if not (bull_bo or bear_bo):
                prior_high = max(prior_high, bar_high)
                prior_low  = min(prior_low,  bar_low)
                continue

            direction = 1 if bull_bo else -1

            # Volume filter
            if use_vol_filter:
                bars_so_far = rth[rth.index <= bar_ts]
                if len(bars_so_far) > 0:
                    avg_vol_per_bar = bars_so_far["volume"].mean()
                    if avg_vol_per_bar > 0 and bar_vol < 1.5 * avg_vol_per_bar:
                        prior_high = max(prior_high, bar_high)
                        prior_low  = min(prior_low,  bar_low)
                        continue

            # Trend filter
            if use_trend_filter and prev_trend != 0:
                if direction != prev_trend:
                    prior_high = max(prior_high, bar_high)
                    prior_low  = min(prior_low,  bar_low)
                    continue

            exit_time = pd.Timestamp(
                date.year, date.month, date.day,
                T_1430.hour, T_1430.minute, 0,
                tzinfo=bar_ts.tzinfo,
            )
            records.append({
                "signal_ts": bar_ts,
                "direction": direction,
                "tp_points": 2.0 * atr_val,
                "sl_points": 0.8 * atr_val,
                "exit_time": exit_time,
                "atr_val":   atr_val,
                "compression_ratio": round(bar_range_1030 / atr_val, 3),
            })
            break   # max 1 trade per day

    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records).set_index("signal_ts")


# ---------------------------------------------------------------------------
# WF wrappers
# ---------------------------------------------------------------------------

def _make_signal_fn(use_vol_filter, use_trend_filter):
    def signal_fn(df_window: pd.DataFrame, params: dict) -> pd.DataFrame:
        atr_30 = compute_30min_atr(df_window)
        return build_signals_breakout(df_window, atr_30, use_vol_filter, use_trend_filter)
    return signal_fn


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== Iter 03 — Range Breakout + ATR Sizing ===")

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)

    log.info("Computing 30-min ATR...")
    atr_30 = compute_30min_atr(engine.rth)

    VARIANT_DEFS = {
        "3a": dict(use_vol_filter=False, use_trend_filter=False),
        "3b": dict(use_vol_filter=True,  use_trend_filter=False),
        "3c": dict(use_vol_filter=True,  use_trend_filter=True),
    }

    n_test       = N_TESTS_START
    best_sharpe  = -np.inf
    best_variant = None

    for var_id, flags in VARIANT_DEFS.items():
        n_test += 1
        sigs = build_signals_breakout(engine.rth, atr_30, **flags)
        log.info(f"--- Variant {var_id}: {len(sigs)} signals ---")

        if len(sigs) < 10:
            log.warning(f"  Too few signals — skipping {var_id}")
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
            "iteration":       f"iter_{var_id}",
            "n_tests":         n_test,
            "description":     f"Breakout ATR vol={flags['use_vol_filter']} trend={flags['use_trend_filter']}",
            **met,
            **boot,
            "wf_pct_positive": wf.get("wf_pct_positive"),
            "wf_n_windows":    wf.get("n_windows"),
            "verdict":         verdict,
        }
        append_result(result)

        print(f"\n  [iter_{var_id}] vol={flags['use_vol_filter']} trend={flags['use_trend_filter']}")
        print(f"    Signals:  {len(sigs)}")
        print(f"    Trades:   {met.get('n_trades',0)}  |  WR: {met.get('win_rate',0)*100:.1f}%")
        print(f"    AvgTrd:   ${met.get('avg_trade_usd',0):.1f}  |  PF: {pf:.3f}")
        print(f"    Sharpe:   {sh:.3f}  |  MaxDD: {met.get('max_dd_pct',0)*100:.1f}%")
        print(f"    WF%pos:   {wf.get('wf_pct_positive','?')}%  ({wf.get('n_windows',0)} windows)")
        print(f"    P(EV≤0):  {boot.get('p_ev_zero','?')}  |  95%CI: [{boot.get('ci_low','?')}, {boot.get('ci_high','?')}]")
        print(f"    Verdict:  {verdict}")

        if sh > best_sharpe:
            best_sharpe  = sh
            best_variant = var_id

    print(f"\n--- Iter 03 best variant: iter_{best_variant} (Sharpe={best_sharpe:.3f}) ---")

    results = load_results()
    print_comparison_table(results)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("iter_03 failed")
        sys.exit(1)
