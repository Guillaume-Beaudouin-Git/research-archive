"""
WS-B — honest sleeve harvest, CORRECTED methodology (true-UTC verified data, standard close-to-close
intraday MTM, honest costs, OOS split, DSR at true N, outer-resample CIs). Committed runner.
Builds the index intraday-reversion book (the only family that looked real) on true-UTC deep_history,
then runs it end-to-end through the WS-A firm barriers. -> results/wsB_book.txt
"""
import os, math, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import sys; sys.path.insert(0, os.path.dirname(__file__))
from barrier_engine import sim_challenge, best_p, outer_ci
from run_barrier_matrix import FIRMS, firm_dict, T3

CACHE = "/sessions/blissful-inspiring-bell/mnt/outputs/ftmo_quest/cache"   # true-UTC deep m5 caches

def banded_rev(sym, hours, freq="60min", z_entry=2.0, z_exit=0.5, w=16, cost_rt=0.0003, dstop=0.02):
    d = pd.read_parquet(f"{CACHE}/{sym}_m5deep.parquet")
    if d.index.tz: d.index = d.index.tz_localize(None)
    d = d.loc["2022-01-01":"2026-05-29"]
    o = d["open"].resample(freq).first(); c = d["close"].resample(freq).last()
    b = pd.DataFrame({"c": c}).dropna(); b = b[(b.index.hour >= hours[0]) & (b.index.hour < hours[1])]
    lp = np.log(b["c"]); z = (lp - lp.rolling(w).mean()) / lp.rolling(w).std()
    day = b.index.normalize(); raw = pd.Series(np.nan, index=b.index)
    raw[z < -z_entry] = 1.0; raw[z > z_entry] = -1.0; raw[z.abs() < z_exit] = 0.0
    pos = raw.groupby(day).ffill().fillna(0.0)
    last = pd.Series(day).shift(-1).values != day; pos[last] = 0.0; pos = pos.shift(1).fillna(0.0)
    ret = lp.diff(); net = pos * ret - pos.diff().abs().fillna(0) * cost_rt / 2
    dd = net.groupby(day).sum(); dd = dd[dd.index.dayofweek < 5].clip(lower=-dstop)
    v = dd.rolling(63).std().shift(1); return (dd * (0.01 / v)).clip(-0.05, 0.05).dropna()

def sh(s, a, b): o = s[(s.index >= a) & (s.index < b)]; return o.mean()/o.std()*np.sqrt(252) if o.std() > 0 else np.nan
def dsr(r, N):
    sr = r.mean()/r.std(); T = len(r); g3 = ((r-r.mean())**3).mean()/r.std()**3; g4 = ((r-r.mean())**4).mean()/r.std()**4-3
    Phi = lambda x: .5*(1+math.erf(x/math.sqrt(2)))
    def iP(p): a=.147; y=2*p-1; ln=math.log(1-y*y); t=2/(math.pi*a)+ln/2; return math.copysign(math.sqrt(math.sqrt(t*t-ln/a)-t), y)
    sb = (0.5772*iP(1-1/N)+(1-.5772)*iP(1-1/(N*math.e)))/math.sqrt(T)
    return Phi((sr-sb)*math.sqrt(T-1)/math.sqrt(1-g3*sr+g4/4*sr**2))

if __name__ == "__main__":
    SL = {"US30": (13, 21), "US500": (13, 21), "US100": (13, 21), "GER40": (7, 16)}
    series = {k: banded_rev(k, h) for k, h in SL.items()}
    print("Index intraday-reversion sleeves (true-UTC), full / OOS Sharpe:", flush=True)
    for k, s in series.items():
        print(f"  {k:6s} full={sh(s,'2022','2026-06'):+.2f} OOS={sh(s,'2025','2026-06'):+.2f}", flush=True)
    df = pd.DataFrame(series).dropna(how="all").fillna(0.0)
    print(f"\n  pairwise corr:\n{df.corr().round(2).to_string()}", flush=True)
    book = df.mean(axis=1); book = book[book.index.dayofweek < 5]
    book.to_frame("book").to_parquet(f"{CACHE}/wsB_index_book.parquet")
    bk = ((book - book.mean())/book.std()).pow(4).mean()-3
    print(f"\nINDEX-MR BOOK: full Sharpe={sh(book,'2022','2026-06'):+.2f} OOS={sh(book,'2025','2026-06'):+.2f} kurt={bk:.1f}", flush=True)
    print(f"  per-year: {dict((int(y),round(g.mean()/g.std()*np.sqrt(252),2)) for y,g in book.groupby(book.index.year))}", flush=True)
    print(f"  DSR @N=200: {dsr(book.values,200):.3f}  @N=500: {dsr(book.values,500):.3f}", flush=True)
    print("\nEND-TO-END: honest book through firm barriers (outer-resample 90% CI):", flush=True)
    for fk in ["FTMO_2step", "Gen_1step_static_loose", "Instant_1step_generous"]:
        lo, md, hi = outer_ci(book.values, firm_dict(FIRMS[fk]), T3, nout=20, npaths=3000)
        flag = "CLEARS" if lo > 0.50 else ("straddles" if hi > 0.50 else "below")
        print(f"  {fk:26s} p(pass<=3mo) median={md:.3f} 90%CI=[{lo:.3f}, {hi:.3f}] -> {flag} 0.50", flush=True)
