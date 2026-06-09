"""
Audit of the INTRADAY REVERSAL (inverse of Gao momentum). gross |Sharpe|~1.2 is a red flag -> stress
realistic FTMO index cost, fill/window, +bar timing, DSR. Vectorized (pivot), bars loaded once.
Committed. -> results/edge1_reversal_audit.txt
"""
import os, math, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from datetime import datetime, timedelta
import sys; sys.path.insert(0, os.path.dirname(__file__))
from edge_intraday_momentum import load_bars, MKTS, sh, dsr, OUT

BARS, PREP = {}, {}
for sym in MKTS:
    tz, op, cl, _ = MKTS[sym]
    b = load_bars(sym, tz)
    PREP[sym] = (b.pivot_table(index="d", columns="hm", values="o", aggfunc="first"),
                 b.pivot_table(index="d", columns="hm", values="c", aggfunc="first"),
                 b.pivot_table(index="d", columns="hm", values="r", aggfunc="first"))

def build_rev(sym, cost_bps, shift_min=0):
    tz, op, cl, _ = MKTS[sym]
    last0 = (datetime.strptime(cl, "%H:%M") - timedelta(minutes=30)).strftime("%H:%M")
    entry = (datetime.strptime(cl, "%H:%M") - timedelta(minutes=30 + shift_min)).strftime("%H:%M")
    O, C, R = PREP[sym]
    if op not in R.columns or entry not in O.columns or last0 not in C.columns: return pd.Series(dtype=float)
    first_r = R[op]; r_window = np.log(C[last0] / O[entry])
    s = (-np.sign(first_r) * r_window - cost_bps / 1e4).dropna()
    s.index = pd.to_datetime(s.index); return s[s.index.dayofweek < 5]

def book(cost, shift=0):
    S = {sym: build_rev(sym, cost, shift) for sym in MKTS}
    return pd.DataFrame(S).dropna(how="all").fillna(0.0).mean(axis=1)

if __name__ == "__main__":
    out = []
    def line(s): print(s, flush=True); out.append(s)
    line("INTRADAY REVERSAL (book of 4 index CFDs) — cost stress, last-30min entry:")
    for c in (0, 3, 5, 8, 12):
        bk = book(c)
        line(f"  cost {c:2d}bp RT: full={sh(bk,'2014','2026-06'):+.2f} 22-26={sh(bk,'2022','2026-06'):+.2f} "
             f"OOS={sh(bk,'2025','2026-06'):+.2f} DSR@200={dsr(bk.values,200):.3f}")
    line("\nWindow robustness (cost 5bp): hold last N min into the close:")
    for shift in (0, 30, 60):
        bk = book(5, shift); line(f"  last {30+shift}min: full={sh(bk,'2014','2026-06'):+.2f} 22-26={sh(bk,'2022','2026-06'):+.2f} OOS={sh(bk,'2025','2026-06'):+.2f}")
    bk5 = book(5)
    line("\nper-sleeve (cost 5bp): " + " ".join(f"{s}={sh(build_rev(s,5),'2014','2026-06'):+.2f}" for s in MKTS))
    line("per-year (cost 5bp): " + str({int(y): round(g.mean()/g.std()*np.sqrt(252),2) for y,g in bk5.groupby(bk5.index.year)}))
    bk5.to_frame("net").to_parquet(f"{OUT}/rev_book.parquet")
    open(f"{OUT}/edge1_reversal_audit.txt","w").write("\n".join(out))
