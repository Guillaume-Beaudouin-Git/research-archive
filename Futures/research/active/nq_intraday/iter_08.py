"""
iter_08.py — Volatility Regime Filter
======================================
Hypothesis: The Jan-Jun 2023 drawdown was caused by low-vol regime (opening ranges
31pt median vs 38pt full-sample, directional accuracy 49.3%). A vol regime filter
skipping low-vol days should eliminate that drawdown without harming other periods.

BUILD ON: iter_05 (A$400 + B1.2%) — current production strategy.

Variants:
  8a — ATR ratio filter: skip if 5d_atr / 63d_median_atr < 0.5
  8b — Tighter threshold: skip if vol_ratio < 0.7
  8c — VIX-based filter: skip if vix_5d_avg < 15
  8d — Combined: 8a (vol_ratio < 0.5) + ETH overnight range pre-check

Gates for Decision A (full-size upgrade):
  Sharpe > 1.0, MaxDD < -20% (rel), WF% >= 75%, PF > 1.20, P(EV<=0) < 0.05,
  N > 50% of iter_05 baseline (284 trades min)

n_tests: 119 + 4 = 123
"""

from __future__ import annotations

import datetime
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[4]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, POINT_VALUE, COST_RT,
    append_result, load_results, print_comparison_table,
)
from Futures.research.active.nq_intraday.iter_05 import (
    build_opening_features, signals_from_features,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

N_TESTS_BASE  = 119
ITER05_PROD   = {"iteration": "iter_05_A$400+B1.2%", "sharpe": 1.213,
                 "max_dd": -0.251, "pf": 1.280, "wf_pct": 67.0, "n_trades": 567}

# iter_05 production params
PROD_GAP      = 0.012
PROD_DSTOP    = 400.0

# Extended WF settings (mirror iter_07)
WF_TRAIN_MO   = 6
WF_TEST_MO    = 3

T_0930 = datetime.time(9, 30)
T_1559 = datetime.time(15, 59)

# 2023 analysis window (tz-naive — strip tz before comparing)
DD_START = pd.Timestamp("2023-01-01")
DD_END   = pd.Timestamp("2023-06-30")


def _strip_tz(ts_series: pd.Series) -> pd.Series:
    """Return tz-naive version of a datetime Series for safe comparison."""
    s = pd.to_datetime(ts_series)
    if s.dt.tz is not None:
        return s.dt.tz_localize(None)
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Vol regime computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_vol_ratio(df: pd.DataFrame) -> pd.Series:
    """
    Returns daily vol_ratio = 5d mean daily ATR / 63d rolling median of 5d ATR.
    Fully causal: all lookbacks are .shift(1) — no look-ahead.

    Index: date (normalized), values: vol_ratio (float, NaN for first ~70 days)
    """
    rth = df[(df.index.time >= T_0930) & (df.index.time <= T_1559)].copy()
    daily_hi   = rth["high"].resample("B").max()
    daily_lo   = rth["low"].resample("B").min()
    daily_cl   = rth["close"].resample("B").last()
    daily_atr  = daily_hi - daily_lo          # simplified ATR (high - low)

    atr_5d     = daily_atr.rolling(5,  min_periods=3).mean().shift(1)
    med_63d    = atr_5d.rolling(63, min_periods=20).median().shift(1)

    vol_ratio  = atr_5d / med_63d
    vol_ratio.name = "vol_ratio"
    return vol_ratio


def fetch_vix(start: str, end: str) -> pd.Series:
    """Download ^VIX daily from yfinance, return 5d rolling mean."""
    try:
        import yfinance as yf
        vix = yf.download("^VIX", start=start, end=end, progress=False)["Close"]
        if isinstance(vix, pd.DataFrame):
            vix = vix.iloc[:, 0]
        vix.index = pd.to_datetime(vix.index).normalize()
        vix_5d = vix.rolling(5, min_periods=3).mean().shift(1)
        vix_5d.name = "vix_5d"
        log.info(f"VIX data loaded: {vix_5d.first_valid_index()} → {vix_5d.index[-1]}, "
                 f"n={vix_5d.notna().sum()}")
        return vix_5d
    except Exception as e:
        log.warning(f"VIX fetch failed: {e}")
        return pd.Series(dtype=float, name="vix_5d")


def enrich_features(feats: pd.DataFrame, vol_ratio: pd.Series,
                    vix_5d: Optional[pd.Series] = None) -> pd.DataFrame:
    """Merge vol_ratio (and optionally vix_5d) into features dataframe."""
    f = feats.copy()
    # Normalise to tz-naive UTC date for merging
    f["date_norm"] = pd.to_datetime(f["date"]).dt.normalize().dt.tz_localize(None)

    # vol_ratio
    vr = vol_ratio.reset_index()
    vr.columns = ["date_norm", "vol_ratio"]
    vr["date_norm"] = pd.to_datetime(vr["date_norm"]).dt.normalize().dt.tz_localize(None)
    f = f.merge(vr, on="date_norm", how="left")

    # VIX
    if vix_5d is not None and not vix_5d.empty:
        vx = vix_5d.reset_index()
        vx.columns = ["date_norm", "vix_5d"]
        vx["date_norm"] = pd.to_datetime(vx["date_norm"]).dt.normalize().dt.tz_localize(None)
        f = f.merge(vx, on="date_norm", how="left")
    else:
        f["vix_5d"] = np.nan

    return f.drop(columns=["date_norm"])


# ─────────────────────────────────────────────────────────────────────────────
# Signal builders — each wraps iter_05 A$400 + B1.2% + adds vol filter
# ─────────────────────────────────────────────────────────────────────────────

def build_iter08_signals(feats_rich: pd.DataFrame,
                         vol_ratio_thresh: Optional[float] = None,
                         vix_thresh: Optional[float] = None,
                         eth_vol_ratio_thresh: Optional[float] = None,
                         label: str = "") -> pd.DataFrame:
    """
    iter_05 A$400 + B1.2% base, then apply vol regime filter.

    vol_ratio_thresh  : skip if vol_ratio < thresh (8a: 0.5, 8b: 0.7)
    vix_thresh        : skip if vix_5d_avg < thresh (8c: 15)
    eth_vol_ratio_thresh: skip if eth_range/eth_avg20 < thresh (8d extra)
    """
    # iter_05 A$400 + B1.2% base
    sigs = signals_from_features(
        feats_rich,
        gap_thresh=PROD_GAP,
        dollar_stop=PROD_DSTOP,
    )
    if sigs.empty:
        return sigs

    # Attach enriched metadata for filtering
    feats_idx = feats_rich.set_index("sig_ts")

    rows_keep = []
    for sig_ts, row in sigs.iterrows():
        if sig_ts not in feats_idx.index:
            rows_keep.append(True)
            continue

        meta = feats_idx.loc[sig_ts]

        # Vol ratio filter
        if vol_ratio_thresh is not None:
            vr = meta.get("vol_ratio", np.nan)
            if np.isfinite(vr) and vr < vol_ratio_thresh:
                rows_keep.append(False)
                continue

        # VIX filter
        if vix_thresh is not None:
            vx = meta.get("vix_5d", np.nan)
            if np.isfinite(vx) and vx < vix_thresh:
                rows_keep.append(False)
                continue

        # ETH overnight range filter (for 8d)
        if eth_vol_ratio_thresh is not None:
            eth_rng = meta.get("eth_range", np.nan)
            eth_avg = meta.get("eth_avg20", np.nan)
            if (np.isfinite(eth_rng) and np.isfinite(eth_avg) and eth_avg > 0):
                eth_ratio = eth_rng / eth_avg
                if eth_ratio < eth_vol_ratio_thresh:
                    rows_keep.append(False)
                    continue

        rows_keep.append(True)

    filtered = sigs[rows_keep].copy()

    n_total  = len(sigs)
    n_kept   = len(filtered)
    n_skip   = n_total - n_kept
    log.info(f"[{label}] Signals: {n_total} → {n_kept} kept, {n_skip} skipped by vol filter "
             f"({n_skip/n_total*100:.1f}%)")
    return filtered


# ─────────────────────────────────────────────────────────────────────────────
# Extended walk-forward (6M train / 3M test, same as iter_07)
# ─────────────────────────────────────────────────────────────────────────────

def extended_wf(engine: NQBacktestEngine, feats_rich: pd.DataFrame,
                vol_ratio_thresh: Optional[float] = None,
                vix_thresh: Optional[float] = None,
                eth_vol_ratio_thresh: Optional[float] = None,
                label: str = "") -> dict:
    """
    Rolling WF: 6M train / 3M OOS, up to 12 windows.
    Uses the same feats_rich with pre-computed vol metrics.
    """
    all_dates = sorted(_strip_tz(feats_rich["date"]).dt.normalize().unique())
    if not all_dates:
        return {}

    start_dt  = all_dates[0]
    end_dt    = all_dates[-1]

    windows   = []
    cursor    = start_dt

    while True:
        train_end = cursor + pd.DateOffset(months=WF_TRAIN_MO)
        test_end  = train_end + pd.DateOffset(months=WF_TEST_MO)
        if test_end > end_dt:
            break

        # OOS signals only (tz-stripped for safe comparison)
        date_naive = _strip_tz(feats_rich["date"]).dt.normalize()
        oos_feats = feats_rich[
            (date_naive > train_end) &
            (date_naive <= test_end)
        ].copy()

        oos_sigs = build_iter08_signals(
            oos_feats,
            vol_ratio_thresh=vol_ratio_thresh,
            vix_thresh=vix_thresh,
            eth_vol_ratio_thresh=eth_vol_ratio_thresh,
            label=f"{label}_wf",
        )

        if len(oos_sigs) < 5:
            cursor += pd.DateOffset(months=3)
            continue

        _, met = engine.run(oos_sigs)
        sh     = met.get("sharpe_daily_hac") or 0
        pf     = met.get("profit_factor")    or 0
        wr     = met.get("win_rate")         or 0
        mdd    = met.get("max_dd_pct")       or 0
        n      = met.get("n_trades", 0)
        pnl    = met.get("total_pnl_usd")     or 0

        windows.append({
            "train_end": train_end.date(),
            "oos_end":   test_end.date(),
            "n":         n,
            "sharpe":    sh,
            "pf":        pf,
            "wr":        wr,
            "mdd":       mdd,
            "pnl":       pnl,
            "positive":  pnl > 0,
        })
        cursor += pd.DateOffset(months=3)

    if not windows:
        return {}

    n_pos   = sum(1 for w in windows if w["positive"])
    n_win   = len(windows)
    pct_pos = n_pos / n_win * 100 if n_win > 0 else 0
    med_sh  = float(np.median([w["sharpe"] for w in windows]))

    return {
        "windows":      windows,
        "n_windows":    n_win,
        "n_positive":   n_pos,
        "pct_positive": pct_pos,
        "median_sharpe":med_sh,
    }


def print_wf_table(wf_result: dict, label: str) -> None:
    windows = wf_result.get("windows", [])
    if not windows:
        print(f"  [{label}] No WF windows.")
        return

    print(f"\n  Walk-forward results ({label}):")
    print(f"  {'#':<3} {'Train→OOS end':<22} {'N':>4} {'Sh_HAC':>8} "
          f"{'PF':>6} {'WR':>6} {'MaxDD':>8} {'PnL$':>9}")
    print("  " + "-" * 78)
    for i, w in enumerate(windows, 1):
        tick = "✓" if w["positive"] else "✗"
        print(f"  {i:<3} → {str(w['oos_end']):<20} "
              f"{w['n']:>4} {w['sharpe']:>8.3f} {w['pf']:>6.3f} "
              f"{w['wr']*100:>5.1f}% {w['mdd']*100:>7.1f}% "
              f"{w['pnl']:>9.0f} {tick}")

    n_pos = wf_result["n_positive"]
    n_win = wf_result["n_windows"]
    pct   = wf_result["pct_positive"]
    med   = wf_result["median_sharpe"]
    verdict = ("ROBUST" if pct >= 75 else "BORDERLINE" if pct >= 60 else "NOT READY")
    print(f"\n  Summary: {n_pos}/{n_win} positive ({pct:.0f}%) → {verdict}  "
          f"Median Sharpe={med:.3f}")


# ─────────────────────────────────────────────────────────────────────────────
# 2023 drawdown period analysis
# ─────────────────────────────────────────────────────────────────────────────

def analyse_2023_window(engine: NQBacktestEngine, feats_rich: pd.DataFrame,
                        sigs_filtered: pd.DataFrame, sigs_baseline: pd.DataFrame,
                        label: str) -> None:
    """
    Compare filtered vs baseline P&L in the Jan-Jun 2023 drawdown window.
    """
    def pnl_in_window(sigs: pd.DataFrame) -> float:
        if sigs.empty:
            return 0.0
        idx_naive = _strip_tz(sigs.index.to_series())
        mask = (idx_naive >= DD_START) & (idx_naive <= DD_END)
        sigs_w = sigs[mask.values]
        if sigs_w.empty:
            return 0.0
        tl, _ = engine.run(sigs_w)
        return float(tl["pnl_usd"].sum()) if not tl.empty else 0.0

    pnl_base     = pnl_in_window(sigs_baseline)
    pnl_filtered = pnl_in_window(sigs_filtered)

    base_naive = _strip_tz(sigs_baseline.index.to_series())
    filt_naive = _strip_tz(sigs_filtered.index.to_series())
    n_base     = ((base_naive >= DD_START) & (base_naive <= DD_END)).sum()
    n_filtered = ((filt_naive >= DD_START) & (filt_naive <= DD_END)).sum()
    n_skipped  = n_base - n_filtered

    print(f"\n  2023 drawdown window (Jan-Jun 2023):")
    print(f"    Baseline  : {n_base} trades, P&L = ${pnl_base:+.0f}")
    print(f"    {label:<10}: {n_filtered} trades ({n_skipped} skipped), P&L = ${pnl_filtered:+.0f}")
    if n_base > 0:
        pct_skip = n_skipped / n_base * 100
        print(f"    Trades skipped in window: {n_skipped}/{n_base} ({pct_skip:.0f}%)")
    eliminated = pnl_filtered > pnl_base
    print(f"    Drawdown addressed: {'YES ✓' if eliminated else 'NO ✗'}")


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation helper
# ─────────────────────────────────────────────────────────────────────────────

def evaluate(engine: NQBacktestEngine, sigs: pd.DataFrame, label: str,
             n_test: int) -> dict:
    if sigs.empty or len(sigs) < 10:
        log.warning(f"[{label}] Too few signals ({len(sigs)}), skipping.")
        return {"iteration": label, "n_trades": 0, "verdict": "SKIP"}

    tl, met = engine.run(sigs)
    boot    = engine.bootstrap_ev(tl)

    sh  = met.get("sharpe_daily_hac") or 0
    pf  = met.get("profit_factor")    or 0
    mdd = met.get("max_dd_pct")       or 0
    n   = met.get("n_trades", 0)
    p   = boot.get("p_ev_zero", 1.0)

    n_min = ITER05_PROD["n_trades"] * 0.50    # must retain >= 50% of baseline
    if sh >= 1.0 and mdd >= -0.20 and pf >= 1.20 and n >= n_min and p < 0.05:
        verdict = "PROPFIRM_PASS"
    elif sh >= 0.7 and mdd >= -0.25 and pf >= 1.15 and n >= n_min:
        verdict = "RESEARCH_PASS"
    elif sh >= 0.5 and pf >= 1.10:
        verdict = "IMPROVE"
    elif sh >= 0.0:
        verdict = "WEAK"
    else:
        verdict = "SKIP"

    result = {
        "iteration": label,
        "n_tests": n_test,
        **met,
        **boot,
        "verdict": verdict,
    }
    append_result(result)
    return result


def print_row(r: dict) -> None:
    ref = ITER05_PROD
    sh  = r.get("sharpe_daily_hac") or 0
    mdd = r.get("max_dd_pct") or 0
    pf  = r.get("profit_factor") or 0
    n   = r.get("n_trades", 0)
    p   = r.get("p_ev_zero") or 1.0
    vd  = r.get("verdict", "?")
    dsh = sh  - ref["sharpe"]
    dmdd= mdd - ref["max_dd"]
    dn  = n   - ref["n_trades"]
    print(f"  {r.get('iteration','?'):<26} Sh={sh:+.3f}({dsh:+.3f})  "
          f"MaxDD={mdd*100:+.1f}%({dmdd*100:+.1f}pp)  "
          f"PF={pf:.3f}  N={n}({dn:+d})  P(EV≤0)={p:.3f}  → {vd}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("=== Iter 08 — Volatility Regime Filter ===")

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)

    log.info("Building opening features...")
    feats = build_opening_features(engine.rth)
    log.info(f"Features: {len(feats)} total  |  VWAP ok: {feats['vwap_ok'].sum()}")

    # Compute vol regime metrics
    log.info("Computing vol ratio (5d ATR / 63d median ATR)...")
    vol_ratio = compute_vol_ratio(df)
    log.info(f"Vol ratio: min={vol_ratio.min():.2f}  median={vol_ratio.median():.2f}  "
             f"max={vol_ratio.max():.2f}  NaN={vol_ratio.isna().sum()}")

    # VIX data
    log.info("Fetching VIX daily data...")
    vix_5d = fetch_vix(
        start=str(df.index.min().date()),
        end=str(df.index.max().date()),
    )

    # Enrich features
    feats_rich = enrich_features(feats, vol_ratio, vix_5d)

    # Vol ratio distribution during 2023 drawdown
    date_norm_tz = _strip_tz(feats_rich["date"]).dt.normalize()
    dd_feats = feats_rich[
        (date_norm_tz >= DD_START) &
        (date_norm_tz <= DD_END)
    ]
    full_vr_med = feats_rich["vol_ratio"].median()
    dd_vr_med   = dd_feats["vol_ratio"].median()
    log.info(f"Vol ratio during Jan-Jun 2023: median={dd_vr_med:.3f}  "
             f"vs full-sample median={full_vr_med:.3f}")

    # Baseline: iter_05 A$400 + B1.2% (no vol filter)
    log.info("Building iter_05 baseline signals (A$400 + B1.2%)...")
    sigs_baseline = build_iter08_signals(feats_rich, label="iter_05_baseline")

    n_test   = N_TESTS_BASE
    results  = []

    # ─────────────────────────────────────────────────────────────────────────
    # VARIANT 8a — ATR ratio < 0.5
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VARIANT 8a — Vol ratio filter: skip if vol_ratio < 0.5")
    print("=" * 80)
    n_test += 1
    sigs_8a = build_iter08_signals(
        feats_rich, vol_ratio_thresh=0.5, label="iter_08_8a"
    )
    r_8a = evaluate(engine, sigs_8a, "iter_08_8a", n_test)
    results.append(r_8a)
    print_row(r_8a)
    analyse_2023_window(engine, feats_rich, sigs_8a, sigs_baseline, "8a")

    # ─────────────────────────────────────────────────────────────────────────
    # VARIANT 8b — ATR ratio < 0.7 (tighter)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VARIANT 8b — Vol ratio filter: skip if vol_ratio < 0.7")
    print("=" * 80)
    n_test += 1
    sigs_8b = build_iter08_signals(
        feats_rich, vol_ratio_thresh=0.7, label="iter_08_8b"
    )
    r_8b = evaluate(engine, sigs_8b, "iter_08_8b", n_test)
    results.append(r_8b)
    print_row(r_8b)
    analyse_2023_window(engine, feats_rich, sigs_8b, sigs_baseline, "8b")

    # ─────────────────────────────────────────────────────────────────────────
    # VARIANT 8c — VIX < 15
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VARIANT 8c — VIX filter: skip if 5d VIX avg < 15")
    print("=" * 80)
    n_test += 1
    if vix_5d.empty:
        print("  VIX data unavailable — SKIP")
        r_8c = {"iteration": "iter_08_8c", "n_trades": 0, "verdict": "SKIP"}
    else:
        sigs_8c = build_iter08_signals(
            feats_rich, vix_thresh=15.0, label="iter_08_8c"
        )
        r_8c = evaluate(engine, sigs_8c, "iter_08_8c", n_test)
        print_row(r_8c)
        analyse_2023_window(engine, feats_rich, sigs_8c, sigs_baseline, "8c")
    results.append(r_8c)

    # ─────────────────────────────────────────────────────────────────────────
    # VARIANT 8d — Combined: vol_ratio < 0.5 + ETH range pre-check
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VARIANT 8d — Combined: vol_ratio < 0.5 AND ETH overnight range < 0.7× avg")
    print("=" * 80)
    n_test += 1
    sigs_8d = build_iter08_signals(
        feats_rich,
        vol_ratio_thresh=0.5,
        eth_vol_ratio_thresh=0.7,
        label="iter_08_8d",
    )
    r_8d = evaluate(engine, sigs_8d, "iter_08_8d", n_test)
    results.append(r_8d)
    print_row(r_8d)
    analyse_2023_window(engine, feats_rich, sigs_8d, sigs_baseline, "8d")

    # ─────────────────────────────────────────────────────────────────────────
    # Extended WF on best variant
    # ─────────────────────────────────────────────────────────────────────────
    best = max(
        [(r, s) for r, s in
         zip(results, [sigs_8a, sigs_8b,
                       sigs_8c if not vix_5d.empty else sigs_8a,
                       sigs_8d])
         if r.get("n_trades", 0) >= ITER05_PROD["n_trades"] * 0.50
            and (r.get("sharpe_daily_hac") or 0) > 0],
        key=lambda x: (x[0].get("sharpe_daily_hac") or 0),
        default=(results[0], sigs_8a),
    )
    best_r, _ = best

    # Identify best variant params for WF
    v_map = {
        "iter_08_8a": dict(vol_ratio_thresh=0.5),
        "iter_08_8b": dict(vol_ratio_thresh=0.7),
        "iter_08_8c": dict(vix_thresh=15.0),
        "iter_08_8d": dict(vol_ratio_thresh=0.5, eth_vol_ratio_thresh=0.7),
    }
    best_params = v_map.get(best_r.get("iteration", "iter_08_8a"), dict(vol_ratio_thresh=0.5))

    print("\n" + "=" * 80)
    print(f"EXTENDED WALK-FORWARD (6M train / 3M test) — best variant: {best_r.get('iteration')}")
    print("=" * 80)
    wf_result = extended_wf(engine, feats_rich, label=best_r.get("iteration", "best"), **best_params)
    print_wf_table(wf_result, best_r.get("iteration", "best"))

    # ─────────────────────────────────────────────────────────────────────────
    # Summary table
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("COMPARISON TABLE — iter_05 reference vs iter_08 variants")
    print("=" * 80)
    print(f"  {'Variant':<26} {'Sharpe':>8} {'MaxDD':>8} {'PF':>6} {'N':>5} "
          f"{'P(EV≤0)':>9} {'Verdict'}")
    print("  " + "-" * 75)

    # Reference row
    ref = ITER05_PROD
    print(f"  {'iter_05_ref (A$400+B1.2%)':<26} {ref['sharpe']:>8.3f} "
          f"{ref['max_dd']*100:>7.1f}% {ref['pf']:>6.3f} {ref['n_trades']:>5} "
          f"{'0.019':>9}  REFERENCE")

    for r in results:
        if r.get("n_trades", 0) == 0:
            print(f"  {r.get('iteration','?'):<26} {'—':>8} {'—':>8} {'—':>6} "
                  f"{'0':>5} {'—':>9}  {r.get('verdict','?')}")
            continue
        sh  = r.get("sharpe_daily_hac") or 0
        mdd = r.get("max_dd_pct") or 0
        pf  = r.get("profit_factor") or 0
        n   = r.get("n_trades", 0)
        p   = r.get("p_ev_zero") or 1.0
        vd  = r.get("verdict", "?")
        dsh = sh - ref["sharpe"]
        dmdd= (mdd - ref["max_dd"]) * 100
        print(f"  {r.get('iteration','?'):<26} {sh:>+8.3f} {mdd*100:>7.1f}% "
              f"{pf:>6.3f} {n:>5} {p:>9.3f}  {vd}  (ΔSh={dsh:+.3f}, ΔMaxDD={dmdd:+.1f}pp)")

    # ─────────────────────────────────────────────────────────────────────────
    # Decision output
    # ─────────────────────────────────────────────────────────────────────────
    best_sh  = best_r.get("sharpe_daily_hac") or 0
    best_mdd = best_r.get("max_dd_pct") or 0
    best_pf  = best_r.get("profit_factor") or 0
    best_n   = best_r.get("n_trades", 0)
    best_p   = best_r.get("p_ev_zero") or 1.0
    wf_pct   = wf_result.get("pct_positive", 0)

    gates_propfirm = (
        best_sh  >= 1.0 and
        best_mdd >= -0.20 and
        best_pf  >= 1.20 and
        best_n   >= ITER05_PROD["n_trades"] * 0.50 and
        best_p   <  0.05 and
        wf_pct   >= 75.0
    )
    gates_improvement = (
        best_sh  >= ITER05_PROD["sharpe"] - 0.05 and
        best_mdd >= ITER05_PROD["max_dd"]
    )

    print("\n" + "=" * 80)
    print("DECISION")
    print("=" * 80)
    print(f"  Best variant  : {best_r.get('iteration','?')}")
    print(f"  Sharpe        : {best_sh:.3f}  (gate: >=1.0)")
    print(f"  MaxDD         : {best_mdd*100:.1f}%  (gate: >=-20%)")
    print(f"  PF            : {best_pf:.3f}  (gate: >=1.20)")
    print(f"  N trades      : {best_n}  (gate: >={int(ITER05_PROD['n_trades']*0.5)})")
    print(f"  P(EV<=0)      : {best_p:.3f}  (gate: <0.05)")
    print(f"  WF% positive  : {wf_pct:.0f}%  (gate: >=75%)")
    print()

    if gates_propfirm:
        print("  DECISION A: iter_08 PROPFIRM READY.")
        print("  → Upgrade to 1.0 contract (5 × /MNQ). Commit and deploy paper trading at full size.")
    elif gates_improvement and wf_pct >= 60:
        print("  DECISION B: Marginal improvement over iter_05.")
        print("  → Stick with Decision B (0.25 contracts). Continue paper trading iter_05,")
        print("    retest live data after 30 trades.")
    else:
        ref_sh  = ITER05_PROD["sharpe"]
        ref_mdd = ITER05_PROD["max_dd"] * 100
        print("  DECISION C: Vol filter does not improve iter_05 meaningfully.")
        print(f"  → iter_05 A$400+B1.2% (Sh={ref_sh:.3f}, MaxDD={ref_mdd:.1f}%) remains final spec.")
        print("  → Accept Decision B (0.25 contracts). Move to Task 2 (Portfolio Framework).")
        print("  → The Jan-Jun 2023 issue may be structural (regime change) and unavoidable.")

    print(f"\nn_tests: {N_TESTS_BASE} → {n_test}")
    print("DO NOT COMMIT yet — await review.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("iter_08 failed")
        sys.exit(1)
