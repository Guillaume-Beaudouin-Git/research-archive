"""
breakout_phase4_delay_top.py — Final test: does the top edge survive delay-1?

Phase 1-3 showed PDH_PDL is the top candidate (+0.26R, DSR 4.57 under EXEC_0).
Phase 1 showed short delay-1 collapses (-0.027). Let me confirm the TOTAL collapse
under delay-1 across all top candidates.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from breakout_deepdive import (
    load_nq_5min, extract_all_trades, compute_metrics,
    signal_orb, signal_donchian, signal_pdh_pdl, signal_bollinger,
    VARIANTS, _get_per_day_bars,
)
from breakout_phase2_depth import extract_with_exits


if __name__ == "__main__":
    # Re-extract all trades for top candidates, with full delay-1 stats
    candidates = [
        ("PDH_PDL", signal_pdh_pdl, {}, True),
        ("ORB_15min", signal_orb, {"or_bars": 3}, False),
        ("ORB_30min", signal_orb, {"or_bars": 6}, False),
        ("Bollinger_20_2sigma", signal_bollinger, {"period": 20, "sigma": 2.0}, False),
        ("Donchian_20", signal_donchian, {"lookback": 20}, False),
    ]

    print("=" * 110)
    print("PHASE 4 — Delay-1 sensitivity on top candidates (the structural test)")
    print("=" * 110)
    print()
    print(f"{'Variant':>25} | {'EXEC_0 total':>12} | {'EXEC_0 short':>12} | {'EXEC_0 long':>11} | "
          f"{'delay1 total':>12} | {'delay1 short':>12} | {'delay1 long':>11}")
    print("-" * 110)

    rows = []
    for vname, vfn, vkwargs, needs_prior in candidates:
        df = extract_all_trades(vfn, vkwargs, vname, cost_bps=1.0,
                                  needs_prior_data=needs_prior)
        if df.empty:
            continue
        m0 = compute_metrics(df, r_col="r_net_exec0")
        m1 = compute_metrics(df, r_col="r_net_exec1")
        rows.append({
            "variant": vname,
            "exec0_total": m0["mean_R_total"], "exec0_short": m0["mean_R_short"],
            "exec0_long": m0["mean_R_long"],
            "exec0_t_total": m0["t_stat_total"], "exec0_t_short": m0["t_stat_short"],
            "exec0_t_long": m0["t_stat_long"],
            "delay1_total": m1["mean_R_total"], "delay1_short": m1["mean_R_short"],
            "delay1_long": m1["mean_R_long"],
            "delay1_t_total": m1["t_stat_total"], "delay1_t_short": m1["t_stat_short"],
            "delay1_t_long": m1["t_stat_long"],
            "n_total": m0["n_total"],
            "delay_collapse_total": m0["mean_R_total"] - m1["mean_R_total"],
            "delay_collapse_short": m0["mean_R_short"] - m1["mean_R_short"],
        })
        print(f"{vname:>25} | {m0['mean_R_total']:+12.3f} | {m0['mean_R_short']:+12.3f} | "
              f"{m0['mean_R_long']:+11.3f} | {m1['mean_R_total']:+12.3f} | "
              f"{m1['mean_R_short']:+12.3f} | {m1['mean_R_long']:+11.3f}")

    df_summary = pd.DataFrame(rows)
    df_summary.to_csv("breakout_phase4_delay_top.csv", index=False)
    print()
    print("=" * 110)
    print("Δ delay collapse (EXEC_0 mean R - delay-1 mean R)")
    print("=" * 110)
    print(f"{'Variant':>25} | {'Δ total':>10} | {'Δ short':>10} | {'Δ long':>10}")
    print("-" * 70)
    for r in rows:
        d_total = r["exec0_total"] - r["delay1_total"]
        d_short = r["exec0_short"] - r["delay1_short"]
        d_long = r["exec0_long"] - r["delay1_long"]
        print(f"{r['variant']:>25} | {d_total:+10.3f} | {d_short:+10.3f} | {d_long:+10.3f}")

    print()
    print("=" * 110)
    print("VERDICT — does any variant SURVIVE delay-1 (=true alpha vs same-bar artifact)?")
    print("=" * 110)
    for r in rows:
        passes = (r["delay1_short"] >= -0.02) and (r["delay1_t_short"] > -1)
        flag = "✓ SURVIVES" if passes else "✗ ARTIFACT"
        print(f"  {r['variant']:>25}: delay-1 short = {r['delay1_short']:+.3f} (t={r['delay1_t_short']:+.2f}) → {flag}")
