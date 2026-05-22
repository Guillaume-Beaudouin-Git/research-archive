"""
PHASE 1.5 Task 3 — IC Feasibility: Angle A (London ORB)
========================================================
Signal: Asian range (00:00-07:00 UTC) breakout at London open (07:00 UTC)
  - Asian high: max close in 00:00-07:00 UTC
  - Asian low:  min close in 00:00-07:00 UTC
  - Breakout direction: +1 if 08:00 bar close > Asian high, -1 if < Asian low, 0 otherwise
  - EUR/USD + GBP/USD dual-pair confirmation: same direction on same day

Forward return horizons: 1h, 2h, 4h, session-end (17:00 UTC)
IC metric: Spearman rank correlation (signal vs fwd_ret)
HAC t-stat: Newey-West lag 6, OLS(fwd_ret ~ signal) with HAC
Gate: N_observations > 400, |t-stat HAC| > 1.65 (10% one-sided)

Input: data/raw/dukascopy_{PAIR}_2020_2024.parquet
Output: prints table + saves to _ic_feasibility/results_angle_a.json
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

RAW_DIR = Path(__file__).parents[4] / "data" / "raw"
OUT_DIR  = Path(__file__).parent
RESULT_FILE = OUT_DIR / "results_angle_a.json"

PAIRS = ["EURUSD", "GBPUSD"]
HORIZONS = {"1h": 60, "2h": 120, "4h": 240, "session": None}  # minutes; session=17:00 UTC
ASIAN_START_H = 0
ASIAN_END_H   = 7   # 00:00–07:00 UTC
BREAKOUT_H    = 7   # signal computed at close of 07:00 bar (i.e., 08:00 open)
SIGNAL_H      = 8   # entry at 08:00 UTC open


def hac_tstat(y: np.ndarray, x: np.ndarray, lag: int = 6) -> float:
    """OLS t-stat with Newey-West HAC, lag=6."""
    x2 = sm.add_constant(x)
    res = sm.OLS(y, x2).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return float(res.tvalues[1])


def load_pair(pair: str) -> pd.DataFrame:
    path = RAW_DIR / f"dukascopy_{pair}_2020_2024.parquet"
    if not path.exists():
        print(f"  MISSING: {path}")
        return pd.DataFrame()
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()
    return df


def compute_daily_signals(df: pd.DataFrame) -> pd.DataFrame:
    """For each date, compute Asian range, breakout signal, and forward returns."""
    df["date"] = df.index.normalize()

    rows = []
    for date, day_df in df.groupby("date"):
        day_df = day_df.sort_index()

        # Asian range: 00:00-07:00 UTC (bars from midnight to 07:00)
        asian = day_df.between_time("00:00", "06:59")
        if len(asian) < 30:
            continue
        asian_high = asian["high"].max()
        asian_low  = asian["low"].min()
        asian_range = asian_high - asian_low
        if asian_range < 1e-6:
            continue

        # Get 07:00-08:00 UTC bar (the transition bar)
        london_open = day_df.between_time("07:00", "07:59")
        if london_open.empty:
            continue
        lo_close = london_open["close"].iloc[-1]

        # Breakout signal
        if lo_close > asian_high:
            signal = 1.0
        elif lo_close < asian_low:
            signal = -1.0
        else:
            signal = 0.0

        # Entry price: open of 08:00 bar
        entry_bars = day_df.between_time("08:00", "08:00")
        if entry_bars.empty:
            continue
        entry_price = entry_bars["open"].iloc[0]
        entry_time  = entry_bars.index[0]

        # Forward returns
        fwd = {}
        for label, mins in HORIZONS.items():
            if label == "session":
                # 17:00 UTC close
                session_end = day_df.between_time("16:59", "17:01")
                if session_end.empty:
                    fwd[label] = np.nan
                else:
                    exit_price = session_end["close"].iloc[-1]
                    fwd[label] = (exit_price - entry_price) / entry_price * signal
            else:
                exit_time = entry_time + pd.Timedelta(minutes=mins)
                exit_bar  = day_df[day_df.index >= exit_time]
                if exit_bar.empty:
                    fwd[label] = np.nan
                else:
                    exit_price = exit_bar["close"].iloc[0]
                    fwd[label] = (exit_price - entry_price) / entry_price * signal

        rows.append({
            "date":         date,
            "signal":       signal,
            "asian_range":  asian_range,
            "entry_price":  entry_price,
            **{f"ret_{k}": v for k, v in fwd.items()},
        })

    return pd.DataFrame(rows).set_index("date")


def run_ic_analysis(pair: str) -> dict:
    print(f"\n{'='*60}")
    print(f"Angle A IC — {pair}")
    df = load_pair(pair)
    if df.empty:
        return {"pair": pair, "error": "no_data"}

    signals = compute_daily_signals(df)
    signals = signals[signals["signal"] != 0].dropna(subset=[f"ret_{h}" for h in HORIZONS])
    N = len(signals)
    print(f"  Breakout days (signal≠0): {N}")
    if N < 400:
        print(f"  FAIL: N={N} < 400 gate")
        return {"pair": pair, "N": N, "gate": "FAIL_N"}

    results = {"pair": pair, "N": N, "horizons": {}}
    header = f"{'Horizon':<12} {'IC_spearman':>12} {'t_OLS':>10} {'t_HAC_NW6':>12} {'p_val':>8} {'gate':>8}"
    print(f"\n  {header}")
    print(f"  {'-'*70}")

    for h in HORIZONS:
        col = f"ret_{h}"
        sig = signals["signal"].values
        ret = signals[col].dropna().values
        # Align
        mask = ~np.isnan(signals[col].values)
        sig_m, ret_m = sig[mask], signals[col].values[mask]
        n_h = len(ret_m)
        if n_h < 100:
            print(f"  {h:<12} {'n<100':>12}")
            continue

        ic_spear, _ = stats.spearmanr(sig_m, ret_m)
        t_ols  = hac_tstat(ret_m, sig_m, lag=0)
        t_hac  = hac_tstat(ret_m, sig_m, lag=6)
        pval   = 2 * (1 - stats.norm.cdf(abs(t_hac)))
        gate   = "PASS" if abs(t_hac) > 1.65 and ic_spear > 0 else "WEAK" if abs(t_hac) > 1.0 else "FAIL"

        print(f"  {h:<12} {ic_spear:>+12.4f} {t_ols:>+10.2f} {t_hac:>+12.2f} {pval:>8.4f} {gate:>8}")
        results["horizons"][h] = {
            "n": n_h, "IC_spearman": round(ic_spear, 4),
            "t_OLS": round(t_ols, 3), "t_HAC_NW6": round(t_hac, 3),
            "p_val": round(pval, 4), "gate": gate,
        }

    return results


def run_dual_pair_analysis(eu_signals: pd.DataFrame, gb_signals: pd.DataFrame) -> dict:
    """Task 4: EUR/GBP breakout correlation — P(same direction)."""
    print(f"\n{'='*60}")
    print("Task 4 — EUR/GBP Breakout Correlation")
    common = eu_signals.index.intersection(gb_signals.index)
    eu_sig = eu_signals.loc[common, "signal"]
    gb_sig = gb_signals.loc[common, "signal"]
    both_nonzero = (eu_sig != 0) & (gb_sig != 0)
    eu_s = eu_sig[both_nonzero]
    gb_s = gb_sig[both_nonzero]
    N = len(eu_s)
    same_dir = (eu_s == gb_s).sum()
    p_same = same_dir / N if N > 0 else np.nan

    print(f"  Days both pairs break out: {N}")
    print(f"  Same direction: {same_dir} ({p_same:.1%})")
    print(f"  Opposite direction: {N - same_dir} ({1-p_same:.1%})")

    # IC of confirmed (same dir) vs single pair
    return {"N_both": N, "P_same_direction": round(float(p_same), 4),
            "confirms_remove_pct": round(float(1 - p_same), 4)}


def main():
    all_results = {}
    eu_signals = gb_signals = None

    for pair in PAIRS:
        df = load_pair(pair)
        if df.empty:
            print(f"ERROR: {pair} data not found. Run fetch_data.py first.")
            continue
        signals = compute_daily_signals(df)
        if pair == "EURUSD":
            eu_signals = signals
        else:
            gb_signals = signals
        res = run_ic_analysis(pair)
        all_results[pair] = res

    if eu_signals is not None and gb_signals is not None:
        corr_res = run_dual_pair_analysis(eu_signals, gb_signals)
        all_results["dual_pair_correlation"] = corr_res

    RESULT_FILE.write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\nResults saved → {RESULT_FILE}")


if __name__ == "__main__":
    main()
