"""
Combine the (cost-honest, low-turnover) paper-edges into one book and test end-to-end. Edge 1
(intraday reversal) is excluded: cost-dead. Combine Edge 2 (FOMC long-even) + Edge 3 (overnight fade),
vol-targeted equal-weight. DSR at true N; p(pass) through FTMO vs a loose 1-step firm with outer CIs.
Committed. -> results/run_combine.txt
"""
import os, sys, math, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "..", "propfirm_pass_plan", "code"))
from edge_fomc_cycle import daily_close, fomc_dates, cycle_week, sh, dsr
from edge_overnight_fade import daily_oc, COST, build as build_fade
from barrier_engine import outer_ci
from run_barrier_matrix import FIRMS, firm_dict, T3
OUT = os.path.abspath(os.path.join(HERE, "..", "results"))

def fomc_long_even():
    fo = fomc_dates(); S = {}
    for sym in ["US500", "US100", "US30"]:
        c = daily_close(sym).loc["2018-01-01":"2026-05-29"]; ret = np.log(c / c.shift(1))
        wk = cycle_week(c.index, fo); even = (wk % 2 == 0) & (wk >= 0)
        S[sym] = (ret.where(even, 0.0) - even.astype(float) * 3.3e-4).dropna()
    return pd.DataFrame(S).fillna(0.0).mean(axis=1)

def vt(s, t=0.01): v = s.rolling(63).std().shift(1); return (s * (t / v)).clip(-0.05, 0.05).dropna()

if __name__ == "__main__":
    out = []; line = lambda s: (print(s, flush=True), out.append(s))
    e2 = fomc_long_even()
    e3 = pd.DataFrame({s: build_fade(s, COST[s]) for s in COST}).fillna(0.0).mean(axis=1)
    J = pd.concat([vt(e2), vt(e3)], axis=1).loc["2018":"2026"].dropna(); J.columns = ["FOMC", "FADE"]
    book = J.mean(axis=1)
    line(f"COMBINED paper-edge book (FOMC long-even + overnight fade), vol-targeted:")
    line(f"  full Sharpe={sh(book,'2018','2026-06'):+.2f}  22-26={sh(book,'2022','2026-06'):+.2f}  OOS={sh(book,'2025','2026-06'):+.2f}")
    line(f"  corr(FOMC,FADE)={J.FOMC.corr(J.FADE):+.2f}  DSR@100={dsr(book.values,100):.3f}  DSR@300={dsr(book.values,300):.3f}")
    line(f"  per-year: {dict((int(y),round(g.mean()/g.std()*np.sqrt(252),2)) for y,g in book.groupby(book.index.year))}")
    line("\nend-to-end p(pass<=3mo), outer-resample 90% CI:")
    for fk in ["FTMO_2step", "Gen_1step_static_loose", "Instant_1step_generous"]:
        lo, md, hi = outer_ci(book.values, firm_dict(FIRMS[fk]), T3, nout=18, npaths=3000)
        flag = "CLEARS" if lo > 0.50 else ("straddles" if hi > 0.50 else "below")
        line(f"  {fk:26s} median={md:.3f} 90%CI=[{lo:.3f}, {hi:.3f}] -> {flag} 0.50")
    open(f"{OUT}/run_combine.txt", "w").write("\n".join(out))
