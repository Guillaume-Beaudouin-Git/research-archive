"""
Edge 3 — Overnight/intraday reversal (Lou, Polk, Skouras 2019): the overnight gap reverses intraday.
Intraday-flat (no swap); full-day move -> cost is a small fraction (unlike the 30-min reversal).
Fade: short the day if overnight gapped up, long if gapped down; hold open->close. Honest RT cost,
OOS, DSR. Committed. -> results/edge_overnight_fade.txt
"""
import os, math, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
DEEP = "/sessions/blissful-inspiring-bell/mnt/Algo_claude/data/deep_history_utc"
OUT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")); os.makedirs(OUT, exist_ok=True)
COST = {"US500": 1.0, "US100": 1.5, "US30": 1.0, "GER40": 2.0}   # bps RT

def daily_oc(sym):
    d = pd.read_csv(f"{DEEP}/{sym}_M1.csv", usecols=[0, 1, 4], names=["dt", "open", "close"], header=0)
    d["dt"] = pd.to_datetime(d["dt"]); d = d.set_index("dt")
    g = d.resample("1D"); b = pd.DataFrame({"o": g["open"].first(), "c": g["close"].last()}).dropna()
    return b[b.index.dayofweek < 5].loc["2014-01-01":"2026-05-29"]

def sh(s, a, b): o = s[(s.index >= a) & (s.index < b)]; return o.mean()/o.std()*np.sqrt(252) if o.std() > 0 else np.nan
def dsr(r, N):
    r = np.asarray(r); sr = r.mean()/r.std(); T = len(r); g3 = ((r-r.mean())**3).mean()/r.std()**3; g4 = ((r-r.mean())**4).mean()/r.std()**4-3
    Phi = lambda x: .5*(1+math.erf(x/math.sqrt(2)))
    def iP(p): a=.147; y=2*p-1; ln=math.log(1-y*y); t=2/(math.pi*a)+ln/2; return math.copysign(math.sqrt(math.sqrt(t*t-ln/a)-t), y)
    sb = (0.5772*iP(1-1/N)+(1-.5772)*iP(1-1/(N*math.e)))/math.sqrt(T)
    return Phi((sr-sb)*math.sqrt(T-1)/math.sqrt(1-g3*sr+g4/4*sr**2))

def build(sym, cost):
    b = daily_oc(sym)
    gap = np.log(b["o"] / b["c"].shift(1))          # overnight gap (causal: known at open)
    intraday = np.log(b["c"] / b["o"])              # open->close (traded, intraday-flat)
    s = (-np.sign(gap) * intraday - cost / 1e4).dropna()
    return s[s.index.dayofweek < 5]

if __name__ == "__main__":
    out = []; series = {}
    def line(s): print(s, flush=True); out.append(s)
    line("OVERNIGHT-GAP FADE (intraday-flat) — per index, full / 22-26 / OOS, DSR:")
    for sym, c in COST.items():
        s = build(sym, c); series[sym] = s
        line(f"  {sym:6s} full={sh(s,'2014','2026-06'):+.2f} 22-26={sh(s,'2022','2026-06'):+.2f} OOS={sh(s,'2025','2026-06'):+.2f} DSR@200={dsr(s.values,200):.3f}")
    bk = pd.DataFrame(series).dropna(how="all").fillna(0.0).mean(axis=1)
    line(f"\nBOOK full={sh(bk,'2014','2026-06'):+.2f} 22-26={sh(bk,'2022','2026-06'):+.2f} OOS={sh(bk,'2025','2026-06'):+.2f} DSR@200={dsr(bk.values,200):.3f}")
    line("  per-year: " + str({int(y): round(g.mean()/g.std()*np.sqrt(252),2) for y,g in bk.groupby(bk.index.year)}))
    # cost stress
    line("\ncost stress (book):")
    for cc in (0, 3, 5):
        bkc = pd.DataFrame({s: build(s, cc) for s in COST}).dropna(how="all").fillna(0.0).mean(axis=1)
        line(f"  +{cc}bp extra: full={sh(bkc,'2014','2026-06'):+.2f} OOS={sh(bkc,'2025','2026-06'):+.2f}")
    bk.to_frame("net").to_parquet(f"{OUT}/overnight_fade_book.parquet")
    open(f"{OUT}/edge_overnight_fade.txt", "w").write("\n".join(out))
