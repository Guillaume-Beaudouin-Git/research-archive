"""
Edge 2 — FOMC cycle (Cieslak, Morse, Vissing-Jorgensen, JF 2019): equity excess returns concentrated
in EVEN weeks of the FOMC cycle (w0,2,4) vs odd weeks. Low turnover (~weekly) -> cost negligible.
Window 2018-2026 is OUT-OF-SAMPLE vs the paper (1994-2016) -> tests persistence/decay. Long index in
even weeks; also long-even/short-odd. Honest swap on held nights. DSR at true N. Committed.
-> results/edge_fomc_cycle.txt
"""
import os, math, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
DEEP = "/sessions/blissful-inspiring-bell/mnt/Algo_claude/data/deep_history_utc"
CAL = "/sessions/blissful-inspiring-bell/mnt/Algo_claude/data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv"
OUT = os.path.join(os.path.dirname(__file__), "..", "results"); os.makedirs(OUT, exist_ok=True)
SWAP_BP = 3.3   # index long swap, bps/night

def daily_close(sym):
    d = pd.read_csv(f"{DEEP}/{sym}_M1.csv", usecols=[0, 4], names=["dt", "close"], header=0)
    d["dt"] = pd.to_datetime(d["dt"]); c = d.set_index("dt")["close"].resample("1D").last().dropna()
    return c[c.index.dayofweek < 5]

def fomc_dates():
    cal = pd.read_csv(CAL, usecols=["datetime_utc", "currency", "event"])
    cal["dt"] = pd.to_datetime(cal["datetime_utc"])
    f = cal[(cal.currency == "USD") & cal.event.str.contains("Fed Interest Rate Decision", case=False, na=False)]
    return pd.to_datetime(sorted(f["dt"].dt.normalize().unique()))

def cycle_week(idx, fomc):
    fo = fomc.values.astype("datetime64[ns]"); out = np.full(len(idx), -99)
    for i, t in enumerate(idx.values.astype("datetime64[ns]")):
        prev = fo[fo <= t]
        if len(prev):
            days = (t - prev[-1]) / np.timedelta64(1, "D"); out[i] = int(days // 7)
    return pd.Series(out, index=idx)

def sh(s, a, b): o = s[(s.index >= a) & (s.index < b)]; return o.mean()/o.std()*np.sqrt(252) if o.std() > 0 else np.nan
def dsr(r, N):
    r = np.asarray(r); sr = r.mean()/r.std(); T = len(r); g3 = ((r-r.mean())**3).mean()/r.std()**3; g4 = ((r-r.mean())**4).mean()/r.std()**4-3
    Phi = lambda x: .5*(1+math.erf(x/math.sqrt(2)))
    def iP(p): a=.147; y=2*p-1; ln=math.log(1-y*y); t=2/(math.pi*a)+ln/2; return math.copysign(math.sqrt(math.sqrt(t*t-ln/a)-t), y)
    sb = (0.5772*iP(1-1/N)+(1-.5772)*iP(1-1/(N*math.e)))/math.sqrt(T)
    return Phi((sr-sb)*math.sqrt(T-1)/math.sqrt(1-g3*sr+g4/4*sr**2))

if __name__ == "__main__":
    fomc = fomc_dates(); out = []
    def line(s): print(s, flush=True); out.append(s)
    line(f"FOMC dates 2018-26: n={len(fomc)}  (mean gap {np.diff(fomc.values).astype('timedelta64[D]').astype(int).mean():.0f}d)")
    long_series, ls_series = {}, {}
    for sym in ["US500", "US100", "US30"]:
        c = daily_close(sym).loc["2018-01-01":"2026-05-29"]; ret = np.log(c / c.shift(1))
        wk = cycle_week(c.index, fomc); even = (wk % 2 == 0) & (wk >= 0)
        sw = SWAP_BP / 1e4
        long_even = (ret.where(even, 0.0) - even.astype(float) * sw)          # long index in even weeks
        ls = (np.where(even, ret, -ret) - sw)                                  # long even / short odd
        ls = pd.Series(ls, index=ret.index)
        long_series[sym] = long_even.dropna(); ls_series[sym] = ls.dropna()
        line(f"  {sym}: long-even full={sh(long_even,'2018','2026-06'):+.2f} OOS={sh(long_even,'2025','2026-06'):+.2f} | "
             f"long/short full={sh(ls,'2018','2026-06'):+.2f} OOS={sh(ls,'2025','2026-06'):+.2f}")
    for name, d in [("LONG-EVEN book", long_series), ("LONG/SHORT book", ls_series)]:
        bk = pd.DataFrame(d).dropna(how="all").fillna(0.0).mean(axis=1)
        line(f"\n{name}: full={sh(bk,'2018','2026-06'):+.2f} 22-26={sh(bk,'2022','2026-06'):+.2f} OOS={sh(bk,'2025','2026-06'):+.2f} DSR@100={dsr(bk.values,100):.3f}")
        line("  per-year: " + str({int(y): round(g.mean()/g.std()*np.sqrt(252),2) for y,g in bk.groupby(bk.index.year)}))
        bk.to_frame("net").to_parquet(f"{OUT}/fomc_{name.split()[0].lower()}.parquet")
    open(f"{OUT}/edge_fomc_cycle.txt","w").write("\n".join(out))
