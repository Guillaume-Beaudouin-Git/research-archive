"""Assemble out/deltas.csv — the marginal contribution of each of the 6 defects.

Verdict ladder (pre-registration P1-R1):
  RESEARCH_PASS : SR_excess > 0.7 and MaxDD > -25% and WF_pass > 50%
  SURVIVOR      : RESEARCH_PASS and DSR (repaired) passes and bootstrap CI excludes 0
The pre-registration writes "DSR corrigé > 0". Under the repaired (Bailey PSR)
parameterisation the DSR is a PROBABILITY in (0,1), so "> 0" is vacuous; the
conventional 0.95 threshold is applied instead — the STRICTER reading, so the
rule is never loosened by the choice.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
DEFECTS = ["D1_dsr", "D2_clock", "D3_costs", "D4_floor", "D5_swaps", "D6_order"]
DEFECT_LABEL = {
    "D1_dsr": "1 DSR std_sr_trials=1.0",
    "D2_clock": "2 EET labelled UTC",
    "D3_costs": "3 catalogue cost table",
    "D4_floor": "4 ratcheting max-loss floor",
    "D5_swaps": "5 index swap -3.1 bps, side-blind",
    "D6_order": "6 cost blind to order type",
}


def research_pass(d):
    return (d.sharpe_excess > 0.7) & (d.max_dd_pct > -0.25) & (d.wf_pass_rate > 0.50)


def survivor(d):
    return research_pass(d) & d.dsr_passes.astype(bool) & (d.bootstrap_sr_lo95 > 0)


def funnel_strict(d):
    return research_pass(d) & (d.hac_t_excess > 2.5) & d.dsr_passes.astype(bool)


def verdict(d):
    v = pd.Series("REJECT", index=d.index)
    v[research_pass(d)] = "RESEARCH_PASS"
    v[survivor(d)] = "SURVIVOR"
    return v


def build(prefix: str, tier: str, defects) -> pd.DataFrame:
    cfgs = ["base"] + list(defects) + ["ALL"]
    frames = {}
    for c in cfgs:
        p = f"{OUT}/{prefix}{c}.csv"
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p).set_index("id")
        d["verdict"] = verdict(d)
        d["strict"] = funnel_strict(d)
        frames[c] = d
    base = frames["base"]
    rows = []
    for sid in base.index:
        r = {"tier": tier, "id": sid, "name": base.loc[sid, "name"],
             "family": base.loc[sid].get("family", ""),
             "asset_class": base.loc[sid].get("asset_class", ""),
             "order_type": base.loc[sid].get("order_type", ""),
             "n_trades": base.loc[sid, "n_trades"],
             "base_sharpe": base.loc[sid, "sharpe_excess"],
             "base_maxdd": base.loc[sid, "max_dd_pct"],
             "base_wf": base.loc[sid, "wf_pass_rate"],
             "base_p_ftmo": base.loc[sid, "ftmo_p_pass_p1"],
             "base_verdict": base.loc[sid, "verdict"]}
        for c in cfgs[1:]:
            if c not in frames or sid not in frames[c].index:
                r[f"{c}_dSR"] = np.nan
                r[f"{c}_verdict"] = "n/a"
                continue
            g = frames[c].loc[sid]
            r[f"{c}_dSR"] = g["sharpe_excess"] - r["base_sharpe"]
            r[f"{c}_dpFTMO"] = g["ftmo_p_pass_p1"] - r["base_p_ftmo"]
            r[f"{c}_verdict"] = g["verdict"]
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    t1 = build("summary_", "tier1_batch142", DEFECTS)
    t2 = build("tier2_", "tier2_rigorous20",
               [d for d in DEFECTS if d != "D2_clock"])
    df = pd.concat([t1, t2], ignore_index=True)
    df.to_csv(f"{OUT}/marginal_all.csv", index=False)

    vcols = [c for c in df.columns if c.endswith("_verdict") and c != "base_verdict"]

    def _changed(i):
        b = df.loc[i, "base_verdict"]
        for c in vcols:
            v = df.loc[i, c]
            if isinstance(v, str) and v not in (b, "n/a"):
                return True
        return False

    changed = df[[_changed(i) for i in df.index]]
    changed.to_csv(f"{OUT}/deltas.csv", index=False)

    print(f"candidates: {len(df)}   verdict changes: {len(changed)}")
    print("\nbase verdict counts:")
    print(df.base_verdict.value_counts().to_string())
    for c in vcols:
        print(f"\n{c}:")
        print(df[c].value_counts().to_string())
    print("\nmean |dSR| by defect (tier1):")
    for d in DEFECTS:
        col = f"{d}_dSR"
        if col in t1:
            s = t1[col].abs()
            print(f"  {DEFECT_LABEL[d]:<38} mean {s.mean():.4f}  max {s.max():.4f} "
                  f" n_nonzero {(s > 1e-9).sum()}")
    print("\nmean dp(FTMO) by defect (tier1):")
    for d in DEFECTS:
        col = f"{d}_dpFTMO"
        if col in t1:
            print(f"  {DEFECT_LABEL[d]:<38} mean {t1[col].mean():+.4f} "
                  f" max {t1[col].max():+.4f}")


if __name__ == "__main__":
    main()
