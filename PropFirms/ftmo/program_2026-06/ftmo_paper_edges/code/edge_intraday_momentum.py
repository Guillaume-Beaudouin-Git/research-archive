"""
Edge 1 — Market Intraday Momentum (Gao, Han, Li, Zhou, JFE 2018).
First half-hour return predicts the LAST half-hour return. Intraday-flat (no swap). Index CFDs.
Corrected: true-UTC -> exchange tz (DST-correct), PER-BAR (open->close) returns at the right session
labels, honest RT cost, OOS split, DSR at true N. Committed. -> results/edge_intraday_momentum.txt
"""
import os, math, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from datetime import datetime, timedelta
DEEP = "/sessions/blissful-inspiring-bell/mnt/Algo_claude/data/deep_history_utc"
OUT = os.path.join(os.path.dirname(__file__), "..", "results"); os.makedirs(OUT, exist_ok=True)
MKTS = {  # symbol: (exchange-tz, open HH:MM, close HH:MM, cost_bps_RT)
 "US500": ("US/Eastern", "09:30", "16:00", 1.0),
 "US100": ("US/Eastern", "09:30", "16:00", 1.5),
 "US30":  ("US/Eastern", "09:30", "16:00", 1.0),
 "GER40": ("Europe/Berlin", "09:00", "17:30", 2.0),
}

def load_bars(sym, tz):
    d = pd.read_csv(f"{DEEP}/{sym}_M1.csv", usecols=[0, 1, 4], names=["dt", "open", "close"], header=0)
    d["dt"] = pd.to_datetime(d["dt"]); d = d.set_index("dt")
    d.index = d.index.tz_localize("UTC").tz_convert(tz)
    g = d.resample("30min")
    b = pd.DataFrame({"o": g["open"].first(), "c": g["close"].last()}).dropna()
    b["r"] = np.log(b["c"] / b["o"])              # intra-bar (open->close) return
    b["hm"] = b.index.strftime("%H:%M"); b["d"] = b.index.normalize()
    return b.loc["2014-01-01":"2026-05-29"]

def sh(s, a, b): o = s[(s.index >= a) & (s.index < b)]; return o.mean()/o.std()*np.sqrt(252) if o.std() > 0 else np.nan
def dsr(r, N):
    sr = r.mean()/r.std(); T = len(r); g3 = ((r-r.mean())**3).mean()/r.std()**3; g4 = ((r-r.mean())**4).mean()/r.std()**4-3
    Phi = lambda x: .5*(1+math.erf(x/math.sqrt(2)))
    def iP(p): a=.147; y=2*p-1; ln=math.log(1-y*y); t=2/(math.pi*a)+ln/2; return math.copysign(math.sqrt(math.sqrt(t*t-ln/a)-t), y)
    sb = (0.5772*iP(1-1/N)+(1-.5772)*iP(1-1/(N*math.e)))/math.sqrt(T)
    return Phi((sr-sb)*math.sqrt(T-1)/math.sqrt(1-g3*sr+g4/4*sr**2))

def build(sym):
    tz, op, cl, cost = MKTS[sym]
    last_lbl = (datetime.strptime(cl, "%H:%M") - timedelta(minutes=30)).strftime("%H:%M")
    b = load_bars(sym, tz); rows = []
    for day, g in b.groupby("d"):
        rf = g.loc[g.hm == op, "r"]; rl = g.loc[g.hm == last_lbl, "r"]
        if len(rf) and len(rl) and np.isfinite(rf.iloc[0]) and np.isfinite(rl.iloc[0]):
            rows.append((day, np.sign(rf.iloc[0]) * rl.iloc[0] - cost/1e4))
    s = pd.DataFrame(rows, columns=["d", "net"]).set_index("d")["net"]
    s.index = pd.to_datetime(s.index); return s[s.index.dayofweek < 5]

if __name__ == "__main__":
    out, series = [], {}
    for sym in MKTS:
        try:
            s = build(sym); series[sym] = s; s.to_frame("net").to_parquet(f"{OUT}/im_{sym}.parquet")
            line = f"  {sym:6s} full={sh(s,'2014','2026-06'):+.2f} 22-26={sh(s,'2022','2026-06'):+.2f} OOS={sh(s,'2025','2026-06'):+.2f} DSR@200={dsr(s.values,200):.3f} n={len(s)}"
            print(line, flush=True); out.append(line)
        except Exception as e:
            print(f"  {sym}: ERR {str(e)[:70]}", flush=True)
    if series:
        bk = pd.DataFrame(series).dropna(how="all").fillna(0.0).mean(axis=1)
        l = f"\nBOOK full={sh(bk,'2014','2026-06'):+.2f} 22-26={sh(bk,'2022','2026-06'):+.2f} OOS={sh(bk,'2025','2026-06'):+.2f} DSR@200={dsr(bk.values,200):.3f}"
        print(l, flush=True); out.append(l)
        print("  per-year:", {int(y): round(g.mean()/g.std()*np.sqrt(252),2) for y,g in bk.groupby(bk.index.year)}, flush=True)
        bk.to_frame("net").to_parquet(f"{OUT}/im_book.parquet")
    open(f"{OUT}/edge_intraday_momentum.txt","w").write("\n".join(out))
