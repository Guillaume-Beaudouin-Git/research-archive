"""
levier2_exit_variants.py — Exit reshaping for ORB baseline (attack L24 profile).

Hypothesis: the tail-lumpy profile (low hit, high skew) gets killed by the
symmetric DD barrier. Test exit variants that raise hit-rate and cut skew,
even at the cost of mean R, and measure the EFFECT ON p(pass) FTMO.

Exit variants tested:
  E0 at_close        baseline (exit at RTH close, no TP)
  E1 tp_1R           fixed TP at 1R
  E2 tp_1_5R         fixed TP at 1.5R (Strategy C iter_10 style)
  E3 tp_2R           fixed TP at 2R
  E4 tp_3R           fixed TP at 3R
  E5 scale_1R_close  scale 50% at 1R, rest runs to close
  E6 scale_2R_close  scale 50% at 2R, rest runs to close
  E7 trail_1R_BE     trailing: lock to entry breakeven after +1R
  E8 trail_2R_1R     trailing: lock to entry+1R after +2R
  E9 time_stop_3h    exit forced after 180 1-min bars (3h)

For each: hit_rate, skew, win/loss, MaxDD, Sharpe, p_funded, regime decomp.
Baseline cost: 2 bp RT. Long-only and short-only versions for L25.
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
                              regime_metrics_and_pfunded)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


EXIT_VARIANTS = [
    ("E0_at_close",       {"kind": "at_close"}),
    ("E1_tp_1R",          {"kind": "tp_R", "tp_R": 1.0}),
    ("E2_tp_1.5R",        {"kind": "tp_R", "tp_R": 1.5}),
    ("E3_tp_2R",          {"kind": "tp_R", "tp_R": 2.0}),
    ("E4_tp_3R",          {"kind": "tp_R", "tp_R": 3.0}),
    ("E5_scale_1R_close", {"kind": "scale_out", "partial_tp_R": 1.0, "partial_frac": 0.5}),
    ("E6_scale_2R_close", {"kind": "scale_out", "partial_tp_R": 2.0, "partial_frac": 0.5}),
    ("E7_trail_1R_BE",    {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0}),
    ("E8_trail_2R_1R",    {"kind": "trailing", "trigger_R": 2.0, "lock_R": 1.0}),
    ("E9_time_stop_3h",   {"kind": "time_stop", "n_bars": 180}),
]


def maxdd_dollar(trades: pd.DataFrame, block_cap_pct: float = 0.005) -> dict:
    """Compute MaxDD using cumulative equity at block_cap_pct sizing per trade."""
    if trades.empty:
        return {"max_dd_pct": float("nan"), "max_dd_dollar": float("nan")}
    daily_R = build_daily_R_series(trades).fillna(0.0)
    eq = (1 + block_cap_pct * daily_R).cumprod()
    peak = eq.cummax()
    dd = (eq - peak) / peak
    return {"max_dd_pct": round(float(dd.min()) * 100, 2),
             "max_dd_dollar": round(float((eq - peak).min()), 4)}


def run_variant(name: str, exit_spec: dict, cost_bps_rt: float = 2.0,
                 direction_filter: str = "all") -> dict:
    sleeve = SLEEVES["NQ"]
    tl = build_orb_trades(sleeve, filter_spec={}, exit_spec=exit_spec,
                           cost_bps_rt=cost_bps_rt)
    if direction_filter == "long":
        tl = tl[tl["direction"] == 1]
    elif direction_filter == "short":
        tl = tl[tl["direction"] == -1]
    m = trade_metrics(tl)
    pf = p_funded(tl)
    dd = maxdd_dollar(tl)
    # Capture top-decile R preservation: % of top-decile-R-baseline retained
    return {
        "variant": name,
        "dir": direction_filter,
        "n": m.get("n", 0),
        "mean_R": m.get("mean_R"),
        "std_R": m.get("std_R"),
        "hit_pct": m.get("hit_pct"),
        "median_R": m.get("median_R"),
        "skew": m.get("skew"),
        "kurt": m.get("kurt"),
        "win_loss_ratio": m.get("win_loss_ratio"),
        "sharpe_pt_ann": m.get("sharpe_per_trade_ann"),
        "max_dd_pct": dd.get("max_dd_pct"),
        "p_phase1_pct": round(pf.get("p_phase1", 0.0) * 100, 2)
            if not pd.isna(pf.get("p_phase1", float("nan"))) else float("nan"),
        "p_funded_pct": round(pf.get("p_funded_pct", 0.0), 2)
            if not pd.isna(pf.get("p_funded_pct", float("nan"))) else float("nan"),
        "n_resolved": pf.get("n_resolved", 0),
        "censored_pct": round(pf.get("censored_pct", 0.0), 1),
        "long_mean_R": m.get("long_mean_R"),
        "short_mean_R": m.get("short_mean_R"),
    }, tl


if __name__ == "__main__":
    print("=" * 110)
    print("LEVIER 2 — Exit variants on NQ 30-min ORB (cost = 2 bp RT)")
    print("Goal: attack L24 lumpy profile, measure effect on p(pass) FTMO")
    print("=" * 110)
    cost_bps = 2.0

    print(f"\n--- ALL trades (long + short) ---")
    rows = []
    trade_logs = {}
    for name, spec in EXIT_VARIANTS:
        log.info(f"  Variant: {name}")
        row, tl = run_variant(name, spec, cost_bps_rt=cost_bps, direction_filter="all")
        rows.append(row)
        trade_logs[name] = tl
    df_all = pd.DataFrame(rows)
    cols = ["variant", "n", "mean_R", "hit_pct", "median_R", "skew",
            "win_loss_ratio", "sharpe_pt_ann", "max_dd_pct",
            "p_phase1_pct", "p_funded_pct", "n_resolved",
            "long_mean_R", "short_mean_R"]
    print(df_all[cols].to_string(index=False))
    df_all.to_csv(ROOT / "levier2_all.csv", index=False)
    print()

    print("=" * 110)
    print(f"L24 profile delta vs baseline E0_at_close")
    print("=" * 110)
    baseline = df_all[df_all["variant"] == "E0_at_close"].iloc[0]
    for _, row in df_all.iterrows():
        if row["variant"] == "E0_at_close":
            continue
        d_hit = row["hit_pct"] - baseline["hit_pct"]
        d_skew = row["skew"] - baseline["skew"]
        d_wl = row["win_loss_ratio"] - baseline["win_loss_ratio"]
        d_dd = row["max_dd_pct"] - baseline["max_dd_pct"]
        d_pf = row["p_funded_pct"] - baseline["p_funded_pct"]
        d_pp1 = row["p_phase1_pct"] - baseline["p_phase1_pct"]
        print(f"  {row['variant']:18s} | Δhit={d_hit:+5.1f}pp | Δskew={d_skew:+5.2f} | "
               f"Δw/l={d_wl:+5.2f} | ΔmDD={d_dd:+5.2f}pp | Δp1={d_pp1:+5.1f}pp | "
               f"**Δp_funded={d_pf:+5.1f}pp** | sharpe_pt={row['sharpe_pt_ann']:5.2f}")
    print()

    # Top-3 by p_funded → regime decomposition + long/short split
    print("=" * 110)
    print("TOP 3 by p_funded — regime decomposition")
    print("=" * 110)
    top3 = df_all.sort_values("p_funded_pct", ascending=False).head(3)["variant"].tolist()
    for v in top3:
        tl = trade_logs[v]
        print(f"\n  [{v}] regime decomposition:")
        reg = regime_metrics_and_pfunded(tl)
        print(reg[["block", "n", "long_n", "short_n", "mean_R", "long_mean_R",
                   "short_mean_R", "hit_pct", "skew",
                   "n_resolved", "p_phase1_pct", "p_funded_pct"]].to_string(index=False))

    # Direction split for top variants
    print()
    print("=" * 110)
    print("L25 SPLIT-BY-DIRECTION — top 3 variants long-only vs short-only")
    print("=" * 110)
    for v in top3:
        spec = [s for n, s in EXIT_VARIANTS if n == v][0]
        row_long, _ = run_variant(v, spec, cost_bps_rt=cost_bps, direction_filter="long")
        row_short, _ = run_variant(v, spec, cost_bps_rt=cost_bps, direction_filter="short")
        print(f"\n  [{v}]:")
        for r in [row_long, row_short]:
            print(f"    {r['dir']:6s}: n={r['n']:>4d} mean_R={r['mean_R']:+.4f} "
                   f"hit={r['hit_pct']:5.1f}% skew={r['skew']:+.2f} "
                   f"p_phase1={r['p_phase1_pct']:5.1f}% p_funded={r['p_funded_pct']:5.1f}%")

    print()
    print("=" * 110)
    print("STRESS — top variant under cost {1.0, 2.0, 3.0, 5.0} bp")
    print("=" * 110)
    best = df_all.sort_values("p_funded_pct", ascending=False).iloc[0]["variant"]
    best_spec = [s for n, s in EXIT_VARIANTS if n == best][0]
    print(f"Best by p_funded: {best}\n")
    stress_rows = []
    for c in [1.0, 2.0, 3.0, 5.0]:
        row, _ = run_variant(best, best_spec, cost_bps_rt=c)
        stress_rows.append({"cost_bps": c, **row})
    sdf = pd.DataFrame(stress_rows)
    print(sdf[["cost_bps", "mean_R", "hit_pct", "skew",
                "p_phase1_pct", "p_funded_pct"]].to_string(index=False))
    sdf.to_csv(ROOT / "levier2_best_stress.csv", index=False)
