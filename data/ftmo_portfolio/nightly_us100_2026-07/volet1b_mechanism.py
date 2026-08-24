#!/usr/bin/env python3
"""Volet 1b — PROVE the mono-sleeve failure MECHANISM with numbers (timeout vs bust).

The prior M0c showed mono p(pass) 47% vs full 84% AND mono breaks LESS. The claim
"return-starvation -> fails by timeout" was an INTERPRETATION. This measures it:
  1. Failure decomposition: of FAILING cohorts, fraction bust-driven vs timeout/grind.
  2. Time-to-pass distribution (P1 alone; P1+P2/funded), per config.
  3. Implied daily equity drift (the progression engine).
  4. Median progress at the wall for timeout-failers (near the +10%, or far?).
  5. p(pass) vs HORIZON (91 / 182 / 270 / unbounded) — the 91d wall is the USER's
     economic clock, NOT an FTMO rule. If mono hits ~80% at 182d, the problem is the
     horizon, not the book. DECISIVE for the remedy.

READ-ONLY. Audited engine imported from MAIN dir, NEVER mutated. The diagnostic
funnel below MIRRORS engine.run_funnel (lines 385-413) EXACTLY, only adding
instrumentation; it calls the unmutated engine.run_phase for all accounting.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom"))
import engine as E

LO, HI, STEP = "2014-01-01", "2024-12-31", 10
T1, T2, INIT = E.TARGET1, E.TARGET2, E.INIT

M = E.load_market()
WT_df, ON_df = E.build_signals()
WT, ON = E.align_signals(M, WT_df, ON_df)

def make_M_us100_only(Mbase):
    Mx = dict(Mbase); Mx["days"] = [(px.copy(), b) for (px, b) in Mbase["days"]]
    for px, b in Mx["days"]:
        px[:, 3] = np.nan
    return Mx

# ------- diagnostic funnel: mirrors engine.run_funnel, adds failure reason -------
def funnel_diag(M, i0, WT, ON, cfg, wall=91, gap_bd=3, retry_bd=2):
    start = M["dates"][i0]; i = i0; attempts = 0; n_bust = 0
    t_p1 = None; last_prog = 0.0
    while True:
        if (M["dates"][min(i, M["n"] - 1)] - start).days > wall or i >= M["n"] - 5:
            return dict(funded=False, reason="wall", n_bust=n_bust, t_p1=t_p1,
                        t_fund=None, prog=last_prog, attempts=attempts)
        attempts += 1
        r1 = E.run_phase(M, i, WT, ON, dict(cfg, target=T1, max_cal=wall))
        last_prog = r1["end"] / INIT - 1.0
        if r1["out"] == "pass":
            if t_p1 is None:
                t_p1 = (M["dates"][r1["last"]] - start).days
            j = min(r1["last"] + gap_bd, M["n"] - 1)
            if (M["dates"][j] - start).days > wall:
                return dict(funded=False, reason="wall_after_p1", n_bust=n_bust,
                            t_p1=t_p1, t_fund=None, prog=last_prog, attempts=attempts)
            r2 = E.run_phase(M, j, WT, ON, dict(cfg, target=T2, max_cal=wall,
                                                vm=cfg["vm"] * cfg.get("p2_mult", 1.0)))
            if r2["out"] == "pass":
                t = (M["dates"][r2["last"]] - start).days
                if t <= wall:
                    return dict(funded=True, reason="funded", n_bust=n_bust,
                                t_p1=t_p1, t_fund=t, prog=T1 + T2, attempts=attempts)
                return dict(funded=False, reason="wall", n_bust=n_bust, t_p1=t_p1,
                            t_fund=None, prog=last_prog, attempts=attempts)
            if r2["out"] == "timeout":
                return dict(funded=False, reason="timeout_p2", n_bust=n_bust,
                            t_p1=t_p1, t_fund=None, prog=r2["end"] / INIT - 1.0,
                            attempts=attempts)
            if r2["out"] in ("bust_daily", "bust_floor"):
                n_bust += 1
            i = min(r2["last"] + retry_bd, M["n"] - 1)
        else:
            if r1["out"] == "timeout":
                return dict(funded=False, reason="timeout_p1", n_bust=n_bust,
                            t_p1=t_p1, t_fund=None, prog=r1["end"] / INIT - 1.0,
                            attempts=attempts)
            if r1["out"] in ("bust_daily", "bust_floor"):
                n_bust += 1
            i = min(r1["last"] + retry_bd, M["n"] - 1)

WT_full = WT.copy(); WT_mono = np.zeros_like(WT); M_us100 = make_M_us100_only(M)
CFGS = [("FULL (4 legs)", M, WT_full),
        ("MONO2 (US100+GER40)", M, WT_mono),
        ("MONO1 (US100 only)", M_us100, WT_mono)]

st = E.cohort_starts(M, pd.Timestamp(LO), pd.Timestamp(HI), STEP)
print(f"cohorts: {len(st)}  ({LO}..{HI} step {STEP})   market {M['dates'][0].date()}..{M['dates'][-1].date()}")

# =========== (1)-(4): mechanism at the 91d wall ===========
print("\n" + "=" * 88)
print("MECHANISM @ wall=91d  —  why do failing cohorts fail?")
print("=" * 88)
res91 = {}
for label, Mx, WTx in CFGS:
    rr = [funnel_diag(Mx, int(i0), WTx, ON, E.CFG_V2, wall=91) for i0 in st]
    res91[label] = rr
    n = len(rr)
    passed = [r for r in rr if r["funded"]]
    failed = [r for r in rr if not r["funded"]]
    # failure decomposition
    bust_driven = [r for r in failed if r["n_bust"] >= 1]
    grind = [r for r in failed if r["n_bust"] == 0]           # never busted -> pure timeout/grind
    # time-to-pass
    tp1_all = [r["t_p1"] for r in rr if r["t_p1"] is not None]
    tfund = [r["t_fund"] for r in passed]
    # progress at wall for timeout/grind failers
    grind_prog = [r["prog"] for r in grind]
    med_tp1 = np.median(tp1_all) if tp1_all else np.nan
    drift = (T1 / med_tp1 * 100) if med_tp1 == med_tp1 and med_tp1 > 0 else np.nan
    print(f"\n{label}   p(pass) {len(passed)/n*100:.1f}%   (n={n}, failed={len(failed)})")
    print(f"  FAILURE MODE:  bust-driven {len(bust_driven)/max(1,len(failed))*100:5.1f}%   "
          f"grind/timeout {len(grind)/max(1,len(failed))*100:5.1f}%   "
          f"(of {len(failed)} failures)")
    print(f"  reached P1 at least once: {len(tp1_all)}/{n} ({len(tp1_all)/n*100:.0f}%)   "
          f"median t_P1 {med_tp1:.0f}d  p90 {np.percentile(tp1_all,90):.0f}d" if tp1_all else "  never reached P1")
    if tfund:
        print(f"  time-to-FUNDED (passers): median {np.median(tfund):.0f}d  p90 {np.percentile(tfund,90):.0f}d")
    print(f"  implied daily equity drift (10%/median t_P1): {drift:.3f}%/day")
    if grind_prog:
        gp = np.array(grind_prog) * 100
        print(f"  grind-failers progress at wall: median {np.median(gp):+.1f}%  "
              f"p25 {np.percentile(gp,25):+.1f}%  p75 {np.percentile(gp,75):+.1f}%  "
              f"(target +10%; how far short?)")
    print(f"  mean busts per cohort: {np.mean([r['n_bust'] for r in rr]):.2f}")

# =========== (5): horizon sweep — is 91d the binding constraint? ===========
print("\n" + "=" * 88)
print("HORIZON SWEEP  —  p(pass) vs wall  (91d = user's economic clock, NOT an FTMO rule)")
print("=" * 88)
WALLS = [91, 182, 270, 100000]   # 100000 = unbounded (data-end limited)
hdr = "  ".join(f"{('unbounded' if w>9999 else str(w)+'d'):>10s}" for w in WALLS)
print(f"{'config':22s} {hdr}")
for label, Mx, WTx in CFGS:
    row = []
    for w in WALLS:
        rr = [E.run_funnel(Mx, int(i0), WTx, ON, E.CFG_V2, wall=w) for i0 in st]
        row.append(np.mean([r["funded"] for r in rr]) * 100)
    print(f"{label:22s} " + "  ".join(f"{v:9.1f}%" for v in row))
print("\n[if mono ~80% at 182-270d -> the book is fine, the 91d horizon is the binding "
      "constraint; if it plateaus far below full -> genuine return-starvation]")
