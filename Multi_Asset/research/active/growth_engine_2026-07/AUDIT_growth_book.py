"""
AUDIT_growth_book.py — reproducible trend+bonds growth book for independent audit.
Look-ahead policy: every signal lagged so position at t uses only data through t-1. Spread/vol windows
are causal. Bonds = calendar signal (known in advance). Saves component returns for re-audit.
Run: <venv>/python AUDIT_growth_book.py
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, yfinance as yf
A = np.sqrt(252)
OUT = "<HOME>/Desktop/Algo_claude_research_swapkilled/Multi_Asset/research/active/growth_engine_2026-07"

# ---- Component 1: diversified TSMOM on €12k-tradable micro futures (proxy =F prices) ----
sub = {'RTY=F':'EQ','YM=F':'EQ','CL=F':'EN','NG=F':'EN','HG=F':'MET','GC=F':'MET',
       'ZN=F':'RATES','ZF=F':'RATES','ZB=F':'RATES','6E=F':'FX','6A=F':'FX','6B=F':'FX'}
px = yf.download(list(sub), start='2006-01-01', end='2026-06-01', auto_adjust=True, progress=False)['Close'].ffill()
inst = [c for c in sub if px[c].notna().sum() > 2500]; px = px[inst]; ret = px.pct_change()
vol = ret.rolling(60).std().shift(1) * A                              # LAGGED vol
cl = pd.Series({c: sub[c] for c in inst}); w = pd.Series(0.0, index=inst)
for c in cl.unique():
    m = cl[cl == c].index; w[m] = 1 / cl.nunique() / len(m)          # equal risk per asset-class
raw = sum((px.pct_change(lb) / (ret.rolling(lb).std() * np.sqrt(lb))) for lb in [63, 126, 252]) / 3.0
posn = (np.tanh(raw).shift(1) * (0.10 / vol)).clip(-3, 3)             # signal LAGGED
trend = ((posn.shift(1) * ret - posn.diff().abs() * 1.5e-4) * w).sum(axis=1).dropna()['2008':]

# ---- Component 2: bond month-end (TLT proxy; deploy via ZN/micro-yield futures) ----
tlt = yf.download('TLT', start='2007-01-01', end='2026-06-01', auto_adjust=True, progress=False)['Close']
tlt = tlt['TLT'] if isinstance(tlt, pd.DataFrame) else tlt
rt = tlt.pct_change(); ix = tlt.index; mf = pd.Series(0, index=ix)
for (y, m), g in rt.groupby([ix.year, ix.month]): mf.loc[g.index[-3:]] = 1   # calendar = known in advance
bonds = (rt * mf).dropna()['2008':]

df = pd.concat([trend, bonds], axis=1, keys=['trend', 'bonds']).fillna(0)
df.to_parquet(f"{OUT}/audit_growth_returns.parquet")
def SR(s): s = s.dropna(); return s.mean() / s.std() * A
print(f"trend SR={SR(trend):.2f} ann={trend.mean()*252*100:.1f}%  |  bonds SR={SR(bonds):.2f} ann={bonds.mean()*252*100:.1f}%  |  corr={df['trend'].corr(df['bonds']):.2f}")
book = df['trend'] + df['bonds']
sr = SR(book); mu = book.mean(); sd = book.std(); Lk = mu / sd**2
print(f"COMBINED (1x+1x): SR={sr:.2f} ann={mu*252*100:.1f}% vol={sd*A*100:.1f}% full-Kelly-lev={Lk:.0f}x")

# WF-OOS folds
print("WF-OOS (SR):", {f"{a}-{b}": round(SR(book[a:b]), 2) for a, b in [('2010','2013'),('2014','2017'),('2018','2021'),('2022','2026')]})

def mc_ruin(f, days, npath=5000, seed=7):
    rng = np.random.default_rng(seed); arr = book.values; n = len(arr); ru = 0
    for _ in range(npath):
        idx = []
        while len(idx) < days:
            st = rng.integers(0, n); idx.extend(range(st, min(st + rng.geometric(1/20), n)))
        ru += (np.cumprod(1 + arr[idx[:days]] * f * Lk).min() <= 0.20)
    return ru / npath

print("\nGrowth-vs-ruin frontier:")
for f in [0.25, 0.5, 1.0]:
    g = f * (2 - f) * sr**2 / 2
    print(f"  {f:.2f}-Kelly lev={f*Lk:.0f}x growth~{g*100:.0f}%/yr vol~{f*Lk*sd*A*100:.0f}% 1yr-ruin={mc_ruin(f,252)*100:.0f}% 6mo-ruin={mc_ruin(f,126)*100:.0f}%")
print("saved audit_growth_returns.parquet")
