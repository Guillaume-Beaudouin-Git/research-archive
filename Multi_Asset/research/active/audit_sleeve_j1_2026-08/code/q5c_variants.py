"""Q5-ter — does the 12-1 GATE earn its keep, and how much p(campaign) does the tail cost?

Same paired 405 cohorts. Two questions:
  (a) replace the 12-1 gate by the UNCONDITIONAL always-long vol-targeted weight
      (identical vol targeting, identical cap, no signal). If it matches or beats the
      deployed sleeve, the signal is decoration.
  (b) leg-cap sensitivity 18.05 (margin cap only) / 12 (v2.8) / 8 / 6 / 4 — the price
      in p(campaign) of buying tail room.
"""
import sys
import numpy as np
import pandas as pd

CR = "<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/audit_v2_independent/cleanroom"
sys.path.insert(0, CR)
sys.path.insert(0, "<HOME>/Desktop/Algo_claude_audit_j1/"
                   "Multi_Asset/research/active/audit_sleeve_j1_2026-08/code")
import engine as E  # noqa: E402
from j1_lib import load_panels, j1_weights  # noqa: E402

BASE = dict(vm=14.0, p2_mult=1.2, on_w=0.6, orb_risk=0.0, micro_orb=True, breaker=0.3,
            taper=0.02, glide=0.5, pace=1, pace_k=1.0, ab_buf=0.02, ab_days=5,
            margin_cap=0.6, quantize=True, fix_deadlock=True, mrate=E.MRATE_SWING)

M = E.load_market()
WT, ON = E.build_signals()
ONa = ON.reindex(M["dates"]).fillna(0.0).to_numpy(float)
starts = E.cohort_starts(M, pd.Timestamp("2014-10-01"), M["dates"][-200], step=7)
px, rets, sL, sS, mu, rt = load_panels()
W_UNCOND = j1_weights(px, rets, "uncond").reindex(WT.index).fillna(0.0)


def campaign(wt_df, cap):
    cfg = dict(BASE)
    cfg["leg_lev_cap"] = [0.0, cap, 0.0, 0.0] if cap else None
    WTa = wt_df.reindex(M["dates"]).fillna(0.0).to_numpy(float)
    ok, ts = [], []
    for i0 in starts:
        r = E.run_funnel(M, i0, WTa, ONa, cfg)
        ok.append(r["funded"])
        if r["funded"]:
            ts.append(r["t"])
    ok = np.asarray(ok, float)
    return ok, (float(np.median(ts)) if ts else np.nan)


ref_ok, ref_med = campaign(WT, 12.0)
off_ok, off_med = campaign(WT.assign(USDJPY=0.0), 12.0)
print(f"reference (12-1 gate, cap 12x): p {ref_ok.mean()*100:.2f} %  median {ref_med:.0f} d")
print(f"J1 OFF                        : p {off_ok.mean()*100:.2f} %  median {off_med:.0f} d\n")

print("### (a) 12-1 GATE vs UNCONDITIONAL always-long (cap 12x)")
u_ok, u_med = campaign(WT.assign(USDJPY=W_UNCOND), 12.0)
dd = ref_ok - u_ok
se = dd.std(ddof=1) / np.sqrt(len(dd))
print(f"  unconditional long : p {u_ok.mean()*100:.2f} %  median {u_med:.0f} d")
print(f"  gate - uncond      = {(ref_ok.mean()-u_ok.mean())*100:+.2f} pt  "
      f"CI95 [{(dd.mean()-1.96*se)*100:+.2f}, {(dd.mean()+1.96*se)*100:+.2f}]")

print("\n### (b) leg-cap sensitivity (12-1 gate)")
for cap in (None, 18.05, 12.0, 8.0, 6.0, 4.0):
    ok, med = campaign(WT, cap)
    dd = ok - ref_ok
    se = dd.std(ddof=1) / np.sqrt(len(dd))
    lab = "no cap (margin 60% only)" if cap is None else f"{cap:g}x"
    print(f"  cap {lab:<24} p {ok.mean()*100:6.2f} %  median {med:.0f} d  "
          f"vs 12x {dd.mean()*100:+6.2f} pt  CI95 "
          f"[{(dd.mean()-1.96*se)*100:+.2f},{(dd.mean()+1.96*se)*100:+.2f}]")
