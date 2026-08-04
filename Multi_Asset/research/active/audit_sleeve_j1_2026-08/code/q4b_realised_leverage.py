"""Q4b-bis — REALISED J1 leverage inside the audited cleanroom funnel.

`w * vm` is an upper bound: the 60% margin cap scales every leg down. To know the
leverage the sleeve actually carries we monkey-patch (never modify) the cleanroom's
`_target_for_segment` and record notional_J1 / equity at every 22:05 rebalance, then
run the real challenge cohorts.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

CR = "<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/audit_v2_independent/cleanroom"
sys.path.insert(0, CR)
import engine as E  # noqa: E402

LOG = []
_orig = E._target_for_segment


def patched(s, i, M, WT, ON, cfg, bal, pos, avg, px0, i0, vm):
    tgt, opened = _orig(s, i, M, WT, ON, cfg, bal, pos, avg, px0, i0, vm)
    if tgt is not None and s == 4:
        eq = bal + E._mtm(pos, avg, px0)
        if eq > 0:
            LOG.append((M["dates"][i], abs(tgt[1]) / eq, abs(tgt[0]) / eq))
    return tgt, opened


E._target_for_segment = patched

CFG = dict(vm=14.0, p2_mult=1.2, on_w=0.6, orb_risk=0.0, micro_orb=True, breaker=0.3,
           taper=0.02, glide=0.5, pace=1, pace_k=1.0, ab_buf=0.02, ab_days=5,
           margin_cap=0.6, quantize=True, fix_deadlock=True, target=0.10,
           max_cal=91, mrate=E.MRATE_SWING)

M = E.load_market()
WT, ON = E.build_signals()
WTa, ONa = E.align_signals(M, WT, ON)

for cap_tag, cap in [("pre-v2.8 (no leg cap)", None),
                     ("v2.8 leg_lev_cap 12x", [0.0, 12.0, 0.0, 0.0])]:
    LOG.clear()
    cfg = dict(CFG)
    if cap is not None:
        cfg["leg_lev_cap"] = cap
    starts = E.cohort_starts(M, pd.Timestamp("2014-10-01"),
                             M["dates"][-200], step=7)
    for i0 in starts:
        try:
            E.run_phase(M, i0, WTa, ONa, cfg)
        except Exception:
            pass
    df = pd.DataFrame(LOG, columns=["date", "lev_j1", "lev_xau"])
    d = df[df.lev_j1 > 0]
    print(f"\n### realised J1 notional/equity at 22:05 — {cap_tag}")
    print(f"  N rebalances with J1 on = {len(d):,} over {len(starts)} cohorts")
    print("  " + "  ".join(f"p{q}={np.percentile(d.lev_j1, q):.2f}x"
                           for q in (10, 25, 50, 75, 90, 99, 100)))
    print(f"  share >= 12x : {(d.lev_j1 >= 11.99).mean()*100:.1f} %"
          f" | >= 16.8x : {(d.lev_j1 >= 16.8).mean()*100:.1f} %")
    # implied USDJPY move that consumes the whole 5% daily budget
    mv = 0.05 / d.lev_j1
    print("  USDJPY move that eats the FULL daily budget on J1 alone: "
          + "  ".join(f"p{q}={np.percentile(mv, q)*100:.3f}%" for q in (10, 50, 90)))
    d.to_parquet("<SCRATCH>"
                 "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/j1cache/"
                 f"lev_{'cap12' if cap else 'nocap'}.parquet")
