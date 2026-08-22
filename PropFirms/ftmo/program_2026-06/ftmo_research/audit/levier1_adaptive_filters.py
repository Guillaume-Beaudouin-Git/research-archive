"""
levier1_adaptive_filters.py — Adaptive filters for 30-min ORB baseline.

Hypothesis: the fixed "rng ≥ 30 pts" filter is regime-conditional (kills
2010-2014, biases LONG-only post-2022). Replace with relative thresholds:
  - rng ≥ K bps of price
  - rng ≥ K × ATR20 (daily ATR over 20 prior sessions)

Compare to:
  - NO_FILTER (already done in baseline)
  - FIXED_30PTS (the legacy iter-10-ish artifact)

For each variant, report:
  - n trades + retention rate by regime bucket
  - LONG/SHORT balance
  - Gross/Net mean_R (+ HAC daily SR)
  - p_phase1, p_funded
  - Effect specifically on 2010-2014 (early years)

Canonical cost: 2 bp RT (FTMO CFD level). Stress: 1 bp / 3 bp.
"""
from __future__ import annotations
from pathlib import Path
import sys
import logging
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from orb_baseline import build_orb_trades, build_daily_R_series, SLEEVES
from orb_baseline_v2 import (trade_metrics, p_funded, REGIMES,
                              regime_metrics_and_pfunded, annual_metrics)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


VARIANTS = [
    ("V0_no_filter", {}),
    ("V1_fixed_30pts", {"kind": "pts", "min_pts": 30.0}),
    ("V2_bps_10", {"kind": "pct", "min_pct": 0.0010}),  # 10 bps OR range
    ("V3_bps_20", {"kind": "pct", "min_pct": 0.0020}),  # 20 bps
    ("V4_bps_30", {"kind": "pct", "min_pct": 0.0030}),  # 30 bps
    ("V5_atr_0.5", {"kind": "atr", "min_mult": 0.5, "atr_days": 20}),
    ("V6_atr_1.0", {"kind": "atr", "min_mult": 1.0, "atr_days": 20}),
]


def run_variant(name: str, filter_spec: dict, cost_bps_rt: float = 2.0) -> dict:
    sleeve = SLEEVES["NQ"]
    tl = build_orb_trades(sleeve, filter_spec=filter_spec,
                           exit_spec={"kind": "at_close"}, cost_bps_rt=cost_bps_rt)
    m = trade_metrics(tl)
    pf = p_funded(tl)
    # 2010-2014 specifically: did adaptive filters revive these years?
    early = tl.loc["2010":"2014"] if not tl.empty else tl
    early_m = trade_metrics(early)
    # 2022-2026 (the favourable regime — does the filter dilute the edge?)
    late = tl.loc["2022":"2026"] if not tl.empty else tl
    late_m = trade_metrics(late)
    return {
        "variant": name,
        "n_total": m.get("n", 0),
        "n_early_10_14": early_m.get("n", 0),
        "n_late_22_26": late_m.get("n", 0),
        "mean_R_full": m.get("mean_R"),
        "long_mean_R": m.get("long_mean_R"),
        "short_mean_R": m.get("short_mean_R"),
        "long_pct": round(m.get("long_n", 0) / max(1, m.get("n", 0)) * 100, 1),
        "short_pct": round(m.get("short_n", 0) / max(1, m.get("n", 0)) * 100, 1),
        "hit_pct": m.get("hit_pct"),
        "skew": m.get("skew"),
        "sharpe_per_trade_ann": m.get("sharpe_per_trade_ann"),
        "p_phase1_pct": round(pf.get("p_phase1", 0.0) * 100, 2)
            if not pd.isna(pf.get("p_phase1", float("nan"))) else float("nan"),
        "p_funded_pct": round(pf.get("p_funded_pct", 0.0), 2)
            if not pd.isna(pf.get("p_funded_pct", float("nan"))) else float("nan"),
        "n_resolved": pf.get("n_resolved", 0),
        "censored_pct": round(pf.get("censored_pct", 0.0), 1),
        "mean_R_early": early_m.get("mean_R"),
        "mean_R_late": late_m.get("mean_R"),
        "early_long_mean_R": early_m.get("long_mean_R"),
        "early_short_mean_R": early_m.get("short_mean_R"),
        "late_long_mean_R": late_m.get("long_mean_R"),
        "late_short_mean_R": late_m.get("short_mean_R"),
    }, tl


if __name__ == "__main__":
    print("=" * 110)
    print("LEVIER 1 — Adaptive filters on NQ 30-min ORB baseline (cost = 2 bp RT)")
    print("=" * 110)
    cost_bps = 2.0
    rows = []
    trade_logs = {}
    for name, fs in VARIANTS:
        log.info(f"  Variant: {name}")
        row, tl = run_variant(name, fs, cost_bps)
        rows.append(row)
        trade_logs[name] = tl
    df = pd.DataFrame(rows)

    print(f"\nSummary (cost = {cost_bps} bp RT):")
    cols = ["variant", "n_total", "n_early_10_14", "n_late_22_26",
            "mean_R_full", "long_mean_R", "short_mean_R", "long_pct",
            "hit_pct", "skew", "p_phase1_pct", "p_funded_pct",
            "n_resolved", "censored_pct"]
    print(df[cols].to_string(index=False))
    df.to_csv(ROOT / "levier1_summary.csv", index=False)
    print()

    # Per-variant regime decomp for the best 2-3 candidates
    print("=" * 110)
    print("REGIME DECOMPOSITION — best candidates (by p_funded)")
    print("=" * 110)
    df_sorted = df.sort_values("p_funded_pct", ascending=False)
    top_variants = df_sorted["variant"].head(4).tolist()
    print(f"Top by p_funded: {top_variants}\n")

    for v in top_variants:
        tl = trade_logs[v]
        print(f"\n  [{v}] regime decomposition:")
        reg = regime_metrics_and_pfunded(tl)
        print(reg[["block", "n", "long_n", "short_n", "mean_R",
                   "long_mean_R", "short_mean_R", "hit_pct", "skew",
                   "n_resolved", "p_phase1_pct", "p_funded_pct"]].to_string(index=False))

    print()
    print("=" * 110)
    print("EFFECT ON EARLY YEARS (2010-2014) — does the adaptive filter revive them?")
    print("=" * 110)
    print(df[["variant", "n_early_10_14", "mean_R_early", "early_long_mean_R",
              "early_short_mean_R"]].to_string(index=False))
    print()

    print("=" * 110)
    print("EFFECT ON LATE YEARS (2022-2026)")
    print("=" * 110)
    print(df[["variant", "n_late_22_26", "mean_R_late", "late_long_mean_R",
              "late_short_mean_R"]].to_string(index=False))
    print()

    print("=" * 110)
    print("COST STRESS — best ranged-filter variant under different costs")
    print("=" * 110)
    best = df_sorted.iloc[0]["variant"]
    fs_best = [fs for name, fs in VARIANTS if name == best][0]
    print(f"Best by p_funded: {best}  spec: {fs_best}\n")
    stress_rows = []
    for c in [0.5, 1.0, 2.0, 3.0, 5.0]:
        row, _ = run_variant(best, fs_best, c)
        stress_rows.append({"cost_bps": c, **row})
    sdf = pd.DataFrame(stress_rows)
    print(sdf[["cost_bps", "n_total", "mean_R_full", "long_mean_R",
                "short_mean_R", "p_phase1_pct", "p_funded_pct"]].to_string(index=False))
    sdf.to_csv(ROOT / "levier1_best_stress.csv", index=False)
