#!/usr/bin/env python3
"""Volet 1 (nightly-US100 loss distribution + K1a) + M0c (mono-sleeve vs diversified book).

READ-ONLY. Audited cleanroom engine imported from MAIN dir, NEVER mutated — regimes are forced
purely through the INPUTS (WT gold/J1 -> 0 for mono; GER40 price -> NaN -> quantizes to 0 for
US100-only). See PREREG.md §4 (Volet 1, M0c) + §7.

Configs:
  FULL   : 4 legs (gold + J1 + US100 + GER40)         -- diversified book (pre-gate)
  MONO2  : WT gold/J1 = 0 -> US100 + GER40 on_w        -- post-gate (Tue nights, GER40 present)
  MONO1  : + GER40 price NaN -> US100 only             -- loss-night reality (Mon, GER40 skipped)
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom"))
import engine as E

LOSSES = [-354.14, -402.65]      # the two real nightly US100 losses to locate
LO, HI, STEP = "2014-01-01", "2024-12-31", 10

M = E.load_market()
WT_df, ON_df = E.build_signals()
WT, ON = E.align_signals(M, WT_df, ON_df)          # numpy [n x 2] (XAUUSD, USDJPY), ON [n]
print(f"market days: {M['n']}  ({M['dates'][0].date()} .. {M['dates'][-1].date()})")

def make_M_us100_only(Mbase):
    Mx = dict(Mbase)
    Mx["days"] = [(px.copy(), b) for (px, b) in Mbase["days"]]
    for px, b in Mx["days"]:
        px[:, 3] = np.nan                          # GER40 col -> NaN -> _quantize -> 0 (not traded)
    return Mx

def run_config(Mx, WTx, label):
    st = E.cohort_starts(Mx, pd.Timestamp(LO), pd.Timestamp(HI), STEP)
    E.DAY_LOG.clear()
    diag = []
    cfg = dict(E.CFG_V2, day_log=True)
    res = [E.run_funnel(Mx, int(i0), WTx, ON, cfg, wall=91, diag=diag) for i0 in st]
    ppass = float(np.mean([r["funded"] for r in res]))
    dl = pd.DataFrame(E.DAY_LOG)                    # per-day: worst_dpl (worst intraday daily P&L)
    brk = [d for d in diag if d["kind"] == "breaker"]
    return dict(label=label, ncoh=len(res), ppass=ppass, dl=dl, diag=list(diag), brk=brk)

WT_full = WT.copy()
WT_mono = np.zeros_like(WT)                         # gold=0, J1=0
M_us100 = make_M_us100_only(M)

full  = run_config(M,       WT_full, "FULL (4 legs)")
mono2 = run_config(M,       WT_mono, "MONO2 (US100+GER40)")
mono1 = run_config(M_us100, WT_mono, "MONO1 (US100 only)")

# ---------------- M0c: diversification-loss test ----------------
print("\n" + "=" * 78 + "\nM0c — mono-sleeve vs diversified book (cohorts %s..%s step %d)\n" % (LO, HI, STEP) + "=" * 78)
print(f"{'config':22s} {'p(pass)':>8s} {'n_coh':>6s} {'daily worst_dpl:  median':>26s} {'p5':>9s} {'p1':>9s} {'min':>9s} {'breaker/1k-days':>16s}")
def dstats(r):
    w = r["dl"]["worst_dpl"].to_numpy(float); w = w[np.isfinite(w)]
    ndays = len(w)
    return (np.median(w), np.percentile(w, 5), np.percentile(w, 1), w.min(),
            1000.0 * len(r["brk"]) / max(1, ndays), w)
for r in (full, mono2, mono1):
    med, p5, p1, mn, brk_rate, _ = dstats(r)
    print(f"{r['label']:22s} {r['ppass']*100:7.1f}% {r['ncoh']:6d} "
          f"{med:>24.0f}$ {p5:8.0f}$ {p1:8.0f}$ {mn:8.0f}$ {brk_rate:15.2f}")
# downside-vol ratios (M0c threshold: mono >= 1.3x diversified AND dp(pass) >= 5pts)
_, _, p1_full, _, _, wf = dstats(full)
_, _, p1_m2, _, _, wm2 = dstats(mono2)
_, _, p1_m1, _, _, wm1 = dstats(mono1)
sd = lambda w: w[w < 0].std()                      # downside dispersion
print(f"\ndownside-dispersion (std of negative worst_dpl):  FULL {sd(wf):.0f}  "
      f"MONO2 {sd(wm2):.0f} ({sd(wm2)/sd(wf):.2f}x)  MONO1 {sd(wm1):.0f} ({sd(wm1)/sd(wf):.2f}x)")
print(f"Δp(pass): MONO2 {(mono2['ppass']-full['ppass'])*100:+.1f}pt  MONO1 {(mono1['ppass']-full['ppass'])*100:+.1f}pt "
      f"[M0c: vol>=1.3x AND Δp<=-5pt -> diversification-loss material]")

# ---------------- Volet 1: locate the two real losses + K1a ----------------
print("\n" + "=" * 78 + "\nVolet 1 — nightly US100 daily-loss distribution (MONO1 = US100-only) + K1a\n" + "=" * 78)
w = mono1["dl"]["worst_dpl"].to_numpy(float); w = w[np.isfinite(w)]
neg = w[w < 0]
for L in LOSSES:
    pct = 100.0 * np.mean(w <= L)                  # fraction of days at least this bad
    print(f"  loss {L:+.0f}$  ->  {pct:.2f}% of ALL US100-only days are <= it  "
          f"({'tail p1-p5' if pct<5 else 'body p10-p25' if pct<25 else 'common'})")
print(f"  US100-only daily worst_dpl: median {np.median(w):.0f}$  p5 {np.percentile(w,5):.0f}$  "
      f"p1 {np.percentile(w,1):.0f}$  worst {w.min():.0f}$  (n_days {len(w)})")
# K1a: P(two consecutive ON-day US100 entries BOTH lose >= $350), per cohort-day sequence in MONO1
dl = mono1["dl"].copy(); dl["date"] = pd.to_datetime(dl["date"])
dl = dl.sort_values("date"); wd = dl["worst_dpl"].to_numpy(float)
big = wd <= -350.0
pair = np.mean(big[:-1] & big[1:])                 # consecutive-day both-big fraction
n_big = int(big.sum()); n_pairs = int((big[:-1] & big[1:]).sum())
print(f"\n  K1a: days with loss>=$350 = {n_big}/{len(wd)} ({100*np.mean(big):.2f}%); "
      f"consecutive-day pairs both>=$350 = {n_pairs} "
      f"(P={100*pair:.3f}% of adjacent day-pairs)")
print(f"       [K1a threshold: >=10% of the time -> variance ; <1% -> model!=live]  "
      f"NB interpret vs base-rate of consecutive ON-entries")
