"""
hypothesis_tests.py — Part B: Pre-Specified Hypothesis Tests
=============================================================
k = 6 hypotheses. Bonferroni threshold: p* = 0.05 / 6 = 0.0083.
All hypotheses are pre-specified before looking at data.
Only modifications with PASS here will be implemented in signal_refinements.py.

Tests:
  H1 — DOW effect:       Tue/Wed vs Mon/Fri trade-level P&L  (Mann-Whitney U)
  H2 — VIX level:        VIX>20 vs VIX<15 P&L               (Mann-Whitney U)
  H3 — Opening range:    Medium vs extreme range P&L         (Kruskal-Wallis)
  H4 — 5d trend align:   Aligned vs Counter P&L              (Mann-Whitney U)
  H5 — Long/Short:       Long vs Short trade P&L             (t-test, HAC-adj)
  H6 — ORB width:        30-min vs 15-min opening range      (bootstrap)

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.analysis.hypothesis_tests
"""
from __future__ import annotations

import datetime
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as ss
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).parents[5]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import NQBacktestEngine, POINT_VALUE, COST_RT
from Futures.research.active.nq_intraday.iter_05 import (
    build_opening_features, signals_from_features,
)
from Futures.research.active.nq_intraday.analysis.conditional_analysis import (
    build_context, load_vix,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

K           = 6
P_ALPHA     = 0.05
P_STAR      = P_ALPHA / K           # Bonferroni threshold = 0.0083
STRATEGY_GAP  = 0.012
STRATEGY_STOP = 400.0
N_BOOT      = 20_000
RNG_SEED    = 42

T_0930 = datetime.time(9, 30)
T_1000 = datetime.time(10, 0)
T_1300 = datetime.time(13, 0)
T_1559 = datetime.time(15, 59)


# ─────────────────────────────────────────────────────────────────────────────
# HAC-adjusted t-test (two-sample)
# ─────────────────────────────────────────────────────────────────────────────

def hac_ttest_2sample(a: np.ndarray, b: np.ndarray) -> float:
    """
    HAC-adjusted two-sample t-test: tests H0: mean(a) = mean(b).
    Converts to a difference series and applies OLS + HAC covariance.
    Returns p-value (two-tailed).
    """
    diff = np.concatenate([a, -b])
    n = len(diff)
    if n < 20:
        return float(ss.ttest_ind(a, b).pvalue)
    reg = sm.OLS(diff, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    t_stat = float(reg.tvalues[0])
    # p-value: two-tailed from t with df=n-1
    p = 2 * (1 - ss.t.cdf(abs(t_stat), df=n - 1))
    return float(p)


# ─────────────────────────────────────────────────────────────────────────────
# 30-minute ORB variant
# ─────────────────────────────────────────────────────────────────────────────

def build_opening_features_30min(rth: pd.DataFrame) -> pd.DataFrame:
    """
    Opening range breakout using 09:30-10:00 window (30 min = 6 × 5-min equivalent).
    Same VWAP filter, same gap/ETH variables reused from 1-min data.
    """
    records = []
    dates = sorted(rth.index.normalize().unique())

    rth_all = rth[(rth.index.time >= T_0930) & (rth.index.time <= T_1559)]
    daily_rth_open  = rth_all["open"].resample("B").first().dropna()
    daily_rth_close = rth_all["close"].resample("B").last().dropna()

    pre_rth = rth[(rth.index.time >= datetime.time(8, 0)) & (rth.index.time < T_0930)]
    eth_range_daily = (
        pre_rth["high"].resample("B").max() -
        pre_rth["low"].resample("B").min()
    ).dropna()
    eth_range_avg20 = eth_range_daily.rolling(20, min_periods=5).mean().shift(1)

    for i, date in enumerate(dates):
        day = rth[rth.index.normalize() == date]
        # 30-min window: 09:30 → 10:00 inclusive
        opening = day[(day.index.time >= T_0930) & (day.index.time <= T_1000)]
        if len(opening) < 6:       # need at least 6 bars (09:31-10:00)
            continue

        open_p  = float(opening.iloc[0]["open"])
        close_p = float(opening.iloc[-1]["close"])
        rng     = abs(close_p - open_p)
        if rng < 1.0:
            continue

        direction   = 1 if close_p > open_p else -1
        sig_ts      = opening.index[-1]
        vwap_at_sig = float(opening.iloc[-1]["vwap_rth"])

        vwap_ok = (direction == 1 and close_p > vwap_at_sig) or \
                  (direction == -1 and close_p < vwap_at_sig)

        prev_date  = dates[i - 1] if i > 0 else None
        prev_close = float(daily_rth_close.get(prev_date, np.nan)) if prev_date else np.nan
        today_open = float(daily_rth_open.get(date, np.nan))
        gap_pct    = (today_open - prev_close) / prev_close \
                     if np.isfinite(prev_close) and prev_close > 0 else np.nan

        eth_rng  = float(eth_range_daily.get(date, np.nan))
        eth_avg  = float(eth_range_avg20.get(date, np.nan))
        eth_hi_vol = (eth_rng > 2.0 * eth_avg) \
                     if (np.isfinite(eth_rng) and np.isfinite(eth_avg) and eth_avg > 0) \
                     else False

        # Time stop at 13:00 (3h window vs 2.75h for 15-min)
        exit_time = pd.Timestamp(
            date.year, date.month, date.day, 13, 0, 0, tzinfo=sig_ts.tzinfo
        )

        records.append({
            "date":        date,
            "dow":         date.day_name(),
            "sig_ts":      sig_ts,
            "direction":   direction,
            "open_price":  open_p,
            "close_price": close_p,
            "rng":         rng,
            "vwap_at_sig": vwap_at_sig,
            "vwap_ok":     vwap_ok,
            "gap_pct":     gap_pct,
            "eth_range":   eth_rng,
            "eth_avg20":   eth_avg,
            "eth_hi_vol":  eth_hi_vol,
            "exit_time":   exit_time,
        })

    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# Result printer
# ─────────────────────────────────────────────────────────────────────────────

def print_result(h: str, desc: str, stat: float, pval: float,
                 group_a: tuple, group_b: tuple,
                 extra: str = "") -> dict:
    """
    group_a / group_b: (label, n, mean_pnl)
    """
    verdict = "PASS" if pval < P_STAR else "FAIL"
    marker  = " ***" if verdict == "PASS" else ""

    print(f"\n  {h}: {desc}")
    print(f"    {group_a[0]:<30} N={group_a[1]:>4}  mean=${group_a[2]:>8.1f}")
    print(f"    {group_b[0]:<30} N={group_b[1]:>4}  mean=${group_b[2]:>8.1f}")
    print(f"    Δmean = ${group_a[2]-group_b[2]:+.1f}  |  "
          f"stat={stat:.4f}  p={pval:.4f}  p*={P_STAR:.4f}  →  {verdict}{marker}")
    if extra:
        print(f"    {extra}")

    return {"hypothesis": h, "p_value": pval, "stat": stat, "verdict": verdict}


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> list:
    print("=" * 80)
    print("PART B — HYPOTHESIS TESTS  |  k=6  |  p*=0.05/6=0.0083  (Bonferroni)")
    print("=" * 80)
    print(f"\n  Bonferroni correction: k={K}  p*={P_STAR:.4f}")
    print(f"  Test: trade-level P&L distributions (USD) unless noted\n")

    # Load data
    df     = load_nq_1min()
    engine = NQBacktestEngine(df)
    feats  = build_opening_features(engine.rth)
    sigs   = signals_from_features(feats, gap_thresh=STRATEGY_GAP,
                                    dollar_stop=STRATEGY_STOP)
    tl_raw, _ = engine.run(sigs)
    vix = load_vix()
    tl  = build_context(tl_raw, feats, engine.rth, vix)
    tl["trend_label"] = tl["trend_aligned"].map(
        {True: "Aligned", False: "Counter", None: "Unknown"}
    ).fillna("Unknown")

    results = []

    # ── H1: Day of Week — Tue/Wed vs Mon/Fri ─────────────────────────────
    print("-" * 80)
    print("H1 — Day of week: Tue+Wed vs Mon+Fri")

    gooddow = tl[tl["dow"].isin(["Tuesday", "Wednesday"])]["pnl_usd"].values
    baddow  = tl[tl["dow"].isin(["Monday", "Friday"])]["pnl_usd"].values

    stat1, pval1 = ss.mannwhitneyu(gooddow, baddow, alternative="greater")
    r1 = print_result(
        "H1", "Tue+Wed > Mon+Fri (one-sided Mann-Whitney U)",
        stat1, pval1,
        (f"Tue+Wed (N={len(gooddow)})", len(gooddow), float(gooddow.mean())),
        (f"Mon+Fri (N={len(baddow)})",  len(baddow),  float(baddow.mean())),
        extra=f"Mon avg=${tl[tl['dow']=='Monday']['pnl_usd'].mean():.1f}  "
              f"Fri avg=${tl[tl['dow']=='Friday']['pnl_usd'].mean():.1f}  "
              f"Tue avg=${tl[tl['dow']=='Tuesday']['pnl_usd'].mean():.1f}  "
              f"Wed avg=${tl[tl['dow']=='Wednesday']['pnl_usd'].mean():.1f}"
    )
    results.append(r1)

    # ── H2: VIX level — High vs Low ──────────────────────────────────────
    print("\n" + "-" * 80)
    print("H2 — VIX regime: Medium (15-20) > High (>20)")

    med_vix  = tl[tl["vix_regime"] == "Medium"]["pnl_usd"].values
    high_vix = tl[tl["vix_regime"] == "High"]["pnl_usd"].values

    if len(high_vix) >= 10 and len(med_vix) >= 10:
        stat2, pval2 = ss.mannwhitneyu(med_vix, high_vix, alternative="greater")
        r2 = print_result(
            "H2", "Medium VIX > High VIX P&L (one-sided Mann-Whitney U)",
            stat2, pval2,
            (f"Medium VIX 15-20 (N={len(med_vix)})",  len(med_vix),  float(med_vix.mean())),
            (f"High VIX >20 (N={len(high_vix)})", len(high_vix), float(high_vix.mean())),
            extra=f"Low VIX avg=${tl[tl['vix_regime']=='Low']['pnl_usd'].mean():.1f} (N={len(tl[tl['vix_regime']=='Low'])})"
        )
    else:
        print(f"  H2: SKIP — insufficient data (Med={len(med_vix)}, High={len(high_vix)})")
        r2 = {"hypothesis": "H2", "p_value": 1.0, "stat": 0, "verdict": "SKIP"}
    results.append(r2)

    # ── H3: Opening range size — Q2+Q3 vs Q1+Q4 ─────────────────────────
    print("\n" + "-" * 80)
    print("H3 — Opening range: Q2+Q3 (medium) vs Q1+Q4 (extreme) — Kruskal-Wallis")

    q1   = tl[tl["rng_quartile"] == "Q1 (small)"]["pnl_usd"].values
    q2   = tl[tl["rng_quartile"] == "Q2"]["pnl_usd"].values
    q3   = tl[tl["rng_quartile"] == "Q3"]["pnl_usd"].values
    q4   = tl[tl["rng_quartile"] == "Q4 (large)"]["pnl_usd"].values
    med_rng    = np.concatenate([q2, q3])
    extreme_rng = np.concatenate([q1, q4])

    stat3_kw, pval3_kw = ss.kruskal(q1, q2, q3, q4)
    # Also test Q3 vs Q1 (most extreme contrast)
    stat3_mw, pval3_mw = ss.mannwhitneyu(q3, q1, alternative="greater")

    r3 = print_result(
        "H3", "4-group Kruskal-Wallis across range quartiles",
        stat3_kw, pval3_kw,
        (f"Q2+Q3 medium range (N={len(med_rng)})",    len(med_rng),    float(med_rng.mean())),
        (f"Q1+Q4 extreme range (N={len(extreme_rng)})", len(extreme_rng), float(extreme_rng.mean())),
        extra=f"Kruskal-Wallis 4-group: stat={stat3_kw:.3f} p={pval3_kw:.4f} | "
              f"Q3 vs Q1 Mann-Whitney: stat={stat3_mw:.0f} p={pval3_mw:.4f} | "
              f"Q1=${q1.mean():.0f}  Q2=${q2.mean():.0f}  Q3=${q3.mean():.0f}  Q4=${q4.mean():.0f}"
    )
    results.append(r3)

    # ── H4: 5-day trend alignment ─────────────────────────────────────────
    print("\n" + "-" * 80)
    print("H4 — 5-day trend alignment: Aligned vs Counter")

    aligned = tl[tl["trend_label"] == "Aligned"]["pnl_usd"].values
    counter = tl[tl["trend_label"] == "Counter"]["pnl_usd"].values

    stat4, pval4 = ss.mannwhitneyu(aligned, counter, alternative="greater")
    r4 = print_result(
        "H4", "Trend-aligned > trend-counter P&L (one-sided Mann-Whitney U)",
        stat4, pval4,
        (f"Trend-aligned (N={len(aligned)})", len(aligned), float(aligned.mean())),
        (f"Trend-counter (N={len(counter)})", len(counter), float(counter.mean())),
    )
    results.append(r4)

    # ── H5: Long vs Short asymmetry ───────────────────────────────────────
    print("\n" + "-" * 80)
    print("H5 — Long vs Short: Long P&L > Short P&L (HAC t-test)")

    longs  = tl[tl["direction"] == 1]["pnl_usd"].values
    shorts = tl[tl["direction"] == -1]["pnl_usd"].values

    pval5 = hac_ttest_2sample(longs, shorts)
    stat5 = float(np.mean(longs) - np.mean(shorts))   # effect size = Δmean
    r5 = print_result(
        "H5", "Long P&L > Short P&L (HAC-adjusted t-test, two-sample diff)",
        stat5, pval5,
        (f"Long (N={len(longs)})",  len(longs),  float(longs.mean())),
        (f"Short (N={len(shorts)})", len(shorts), float(shorts.mean())),
        extra=f"Δmean=${stat5:.1f}  |  Long WR={len(longs[longs>0])/len(longs)*100:.1f}%  "
              f"Short WR={len(shorts[shorts>0])/len(shorts)*100:.1f}%"
    )
    results.append(r5)

    # ── H6: 30-min ORB vs 15-min ORB ─────────────────────────────────────
    print("\n" + "-" * 80)
    print("H6 — 30-min ORB vs 15-min ORB: bootstrap mean P&L comparison")

    feats_30 = build_opening_features_30min(engine.rth)
    sigs_30  = signals_from_features(feats_30, gap_thresh=STRATEGY_GAP,
                                      dollar_stop=STRATEGY_STOP)
    tl_30, met_30 = engine.run(sigs_30)

    pnl_15 = tl_raw["pnl_usd"].values
    pnl_30 = tl_30["pnl_usd"].values if len(tl_30) > 0 else np.array([])

    # Bootstrap: mean(30min) - mean(15min) distribution
    rng_gen = np.random.default_rng(RNG_SEED)
    if len(pnl_30) >= 20 and len(pnl_15) >= 20:
        boot_diff = np.array([
            rng_gen.choice(pnl_30, size=len(pnl_30), replace=True).mean() -
            rng_gen.choice(pnl_15, size=len(pnl_15), replace=True).mean()
            for _ in range(N_BOOT)
        ])
        # p-value: fraction of bootstrap diffs <= 0 (H0: 30min <= 15min)
        pval6 = float((boot_diff <= 0).mean())
        stat6 = float(np.mean(pnl_30) - np.mean(pnl_15))

        ci_lo, ci_hi = np.percentile(boot_diff, [2.5, 97.5])
        sh_30 = met_30.get("sharpe_daily_hac", np.nan) or np.nan

        r6 = print_result(
            "H6", "30-min ORB > 15-min ORB (bootstrap one-sided p-value)",
            stat6, pval6,
            (f"30-min ORB (N={len(pnl_30)})", len(pnl_30), float(np.mean(pnl_30))),
            (f"15-min ORB (N={len(pnl_15)})", len(pnl_15), float(np.mean(pnl_15))),
            extra=f"Bootstrap 95% CI of Δmean: [{ci_lo:.1f}, {ci_hi:.1f}]  |  "
                  f"30-min Sharpe={sh_30:.3f}  15-min Sharpe={met_30.get('sharpe_daily_hac', 0) or 0:.3f}"
        )
    else:
        print(f"  H6: SKIP — 30-min variant has {len(pnl_30)} trades (need ≥20)")
        r6 = {"hypothesis": "H6", "p_value": 1.0, "stat": 0, "verdict": "SKIP"}
    results.append(r6)

    # ── SUMMARY TABLE ─────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print(f"  SUMMARY TABLE  (p* = {P_STAR:.4f}  after Bonferroni k={K})")
    print("=" * 80)
    print(f"  {'Hyp':<6} {'Description':<42} {'p-value':>9} {'Verdict':>8}")
    print(f"  {'-'*70}")

    h_labels = {
        "H1": "DOW: Tue+Wed vs Mon+Fri (MW)",
        "H2": "VIX: Medium vs High (MW)",
        "H3": "Range: Kruskal-Wallis 4 quartiles",
        "H4": "Trend 5d: Aligned vs Counter (MW)",
        "H5": "Direction: Long vs Short (HAC t)",
        "H6": "ORB width: 30-min vs 15-min (boot)",
    }
    passing = []
    for r in results:
        h    = r["hypothesis"]
        pval = r["p_value"]
        vd   = r["verdict"]
        mark = " ***" if vd == "PASS" else ""
        print(f"  {h:<6} {h_labels.get(h,''):<42} {pval:>9.4f} {vd:>8}{mark}")
        if vd == "PASS":
            passing.append(h)

    print(f"\n  Passing hypotheses (p < {P_STAR:.4f}): {passing if passing else 'None'}")
    print(f"  These are the ONLY modifications eligible for signal_refinements.py")
    print(f"  Maximum modifications to implement: 3")
    print("=" * 80)

    return results


if __name__ == "__main__":
    results = main()
