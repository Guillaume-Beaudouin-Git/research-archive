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

        # Get 07:00-07:59 UTC bars (London open transition)
        london_open = day_df.between_time("07:00", "07:59")
        if london_open.empty:
            continue
        lo_close   = london_open["close"].iloc[-1]
        lo_high    = london_open["high"].max()
        lo_low     = london_open["low"].min()

        # Signal variant 1: close-based (close of 07:59 bar vs Asian range)
        if lo_close > asian_high:
            signal = 1.0
        elif lo_close < asian_low:
            signal = -1.0
        else:
            signal = 0.0

        # Signal variant 2: high/low-based (did price TRADE through range?)
        broke_high = lo_high > asian_high
        broke_low  = lo_low  < asian_low
        if broke_high and not broke_low:
            signal_hl = 1.0
        elif broke_low and not broke_high:
            signal_hl = -1.0
        else:
            signal_hl = 0.0  # no break OR whipsaw (both sides)

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
            "signal_hl":    signal_hl,
            "asian_range":  asian_range,
            "entry_price":  entry_price,
            **{f"ret_{k}": v for k, v in fwd.items()},
        })

    return pd.DataFrame(rows).set_index("date")


def run_ic_for_signal(signals: pd.DataFrame, sig_col: str, label: str) -> dict:
    """Run IC analysis for one signal variant across all horizons, with per-year breakdown."""
    active = signals[signals[sig_col] != 0]
    N = len(active)
    n_gate = "OK" if N >= 400 else "WARN_N"
    print(f"\n  [{label}] N breakout days: {N} [{n_gate}]")
    if N < 30:
        return {"N": N, "gate": "FAIL_N", "horizons": {}}

    # ── pooled IC across all horizons ──────────────────────────────────────
    print(f"\n  POOLED (all years):")
    header = f"  {'Horizon':<12} {'IC_spearman':>12} {'t_HAC_NW6':>12} {'mean_signed_ret':>16} {'p_val':>8} {'gate':>8}"
    print(header)
    print(f"  {'-'*75}")
    res_h = {}
    for h in HORIZONS:
        col = f"ret_{h}"
        mask = (active[sig_col] != 0) & (~active[col].isna())
        sub  = active[mask]
        n_h  = len(sub)
        if n_h < 50:
            print(f"  {h:<12} {'n<50':>12}")
            continue
        sig_v = sub[sig_col].values
        ret_v = sub[col].values
        ic, _        = stats.spearmanr(sig_v, ret_v)
        t_hac        = hac_tstat(ret_v, sig_v, lag=6)
        mean_sret    = float(np.mean(ret_v))   # signed return in signal direction
        pval         = 2 * (1 - stats.norm.cdf(abs(t_hac)))
        gate         = "PASS" if abs(t_hac) > 1.65 and ic > 0 else "WEAK" if abs(t_hac) > 1.0 else "FAIL"
        dir_note     = "(reversal)" if ic < 0 and abs(t_hac) > 1.0 else ""
        print(f"  {h:<12} {ic:>+12.4f} {t_hac:>+12.2f} {mean_sret:>+16.6f} {pval:>8.4f} {gate:>8}  {dir_note}")
        res_h[h] = {
            "n": n_h,
            "IC_spearman": round(ic, 4),
            "t_HAC_NW6":   round(t_hac, 3),
            "mean_signed_ret": round(mean_sret, 6),
            "p_val":       round(pval, 4),
            "gate":        gate,
        }

    # ── per-year breakdown for 1h horizon ─────────────────────────────────
    h1_col = "ret_1h"
    if h1_col in active.columns:
        print(f"\n  PER-YEAR breakdown (1h horizon — COVID-regime check):")
        yrs_header = f"  {'Year':<8} {'N':>6} {'IC':>8} {'t_HAC':>8} {'mean_sret':>12} {'hit_rate':>10}"
        print(yrs_header)
        print(f"  {'-'*55}")
        yr_results = {}
        for yr, grp in active.groupby(active.index.year):
            sub = grp.dropna(subset=[h1_col])
            n_yr = len(sub)
            if n_yr < 10:
                print(f"  {yr:<8} {'n<10':>6}")
                continue
            sv = sub[sig_col].values
            rv = sub[h1_col].values
            ic_yr, _ = stats.spearmanr(sv, rv)
            t_yr     = hac_tstat(rv, sv, lag=min(4, n_yr // 5)) if n_yr >= 10 else np.nan
            msret_yr = float(np.mean(rv))
            hit_yr   = float(np.mean(rv > 0))
            yr_results[str(yr)] = {
                "n": n_yr, "IC": round(ic_yr, 4),
                "t_HAC": round(t_yr, 3) if not np.isnan(t_yr) else None,
                "mean_signed_ret": round(msret_yr, 6),
                "hit_rate": round(hit_yr, 4),
            }
            print(f"  {yr:<8} {n_yr:>6} {ic_yr:>+8.4f} {t_yr:>+8.2f} {msret_yr:>+12.6f} {hit_yr:>10.1%}")
    else:
        yr_results = {}

    return {"N": N, "n_gate": n_gate, "horizons": res_h, "per_year_1h": yr_results}


def run_ic_analysis(pair: str) -> dict:
    print(f"\n{'='*60}")
    print(f"Angle A IC — {pair}")
    df = load_pair(pair)
    if df.empty:
        return {"pair": pair, "error": "no_data"}

    signals = compute_daily_signals(df)
    print(f"  Total trading days: {len(signals)}")

    res_close = run_ic_for_signal(signals, "signal",    "close-based")
    res_hl    = run_ic_for_signal(signals, "signal_hl", "high/low-based")

    return {"pair": pair, "close_based": res_close, "hl_based": res_hl}


def run_dual_pair_analysis(eu_signals: pd.DataFrame, gb_signals: pd.DataFrame) -> dict:
    """Task 4: EUR/GBP breakout correlation — P(same direction), both signal variants."""
    print(f"\n{'='*60}")
    print("Task 4 — EUR/GBP Breakout Correlation")
    common = eu_signals.index.intersection(gb_signals.index)
    results = {}
    for sig_col in ("signal", "signal_hl"):
        eu_sig = eu_signals.loc[common, sig_col]
        gb_sig = gb_signals.loc[common, sig_col]
        both = (eu_sig != 0) & (gb_sig != 0)
        eu_s, gb_s = eu_sig[both], gb_sig[both]
        N = len(eu_s)
        same_dir = (eu_s == gb_s).sum()
        p_same = same_dir / N if N > 0 else np.nan
        label = "close" if sig_col == "signal" else "hl"
        print(f"  [{label}] Both break out: {N} | Same dir: {same_dir} ({p_same:.1%})")
        results[label] = {"N_both": N, "P_same_direction": round(float(p_same), 4) if not np.isnan(p_same) else None}
    return results


def main():
    all_results = {}
    pair_signals: dict[str, pd.DataFrame] = {}

    for pair in PAIRS:
        df = load_pair(pair)
        if df.empty:
            print(f"ERROR: {pair} data not found. Run fetch_data.py first.")
            continue
        signals = compute_daily_signals(df)
        pair_signals[pair] = signals
        res = run_ic_analysis(pair)
        all_results[pair] = res

    if "EURUSD" in pair_signals and "GBPUSD" in pair_signals:
        corr_res = run_dual_pair_analysis(pair_signals["EURUSD"], pair_signals["GBPUSD"])
        all_results["dual_pair_correlation"] = corr_res

    RESULT_FILE.write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\nResults saved → {RESULT_FILE}")


if __name__ == "__main__":
    main()
