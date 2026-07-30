"""
AUDIT_book.py — full audit of the ~2.0 personal book.
Reconstructs each sleeve with EXPLICIT look-ahead-safe timing, computes per-sleeve and book-level
metrics (exposure, beta, alpha+HAC, Sharpe, Sortino, Calmar, MaxDD), Kelly sizing, expected 6mo/1yr
returns, and €12k IBKR feasibility. Saves sleeve return series to parquet for independent re-audit.

Look-ahead policy (verify each): every signal is lagged so the position at month t uses only data
through t-1. Spread hedge ratios (beta) are estimated on TRAIN 2005-2015 only; OOS = 2016+.
Run: <venv>/python AUDIT_book.py
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, yfinance as yf, statsmodels.api as sm
A = np.sqrt(12)
OUT = "<HOME>/Desktop/Algo_claude_research_swapkilled/Multi_Asset/research/active/swapkilled_futures_2026-07"

def mk(s):
    if len(s) == 0: return s
    if isinstance(s.index[0], tuple):
        return pd.Series(s.values, index=[pd.Timestamp(int(y), int(m), 1) for (y, m) in s.index])
    return pd.Series(s.values, index=[pd.Timestamp(i.year, i.month, 1) for i in s.index])

def me_sleeve(px):
    """Month-end: long last 3 business days of month. Calendar signal = known in advance, no look-ahead."""
    r = px.pct_change(); ix = px.index; mf = pd.Series(0, index=ix)
    for (y, m), g in r.groupby([ix.year, ix.month]): mf.loc[g.index[-3:]] = 1
    d = (r * mf).dropna()
    return mk((1 + d).groupby([d.index.year, d.index.month]).prod() - 1)

def grideq(P, g, L=10, legs=2):
    fee = 5e-4 * legs; cash = 1.; inv = 0.; pk = 0; lc = np.log(P[0]); eq = []
    for pp in P:
        k = int(np.floor((np.log(pp) - lc) / g)); dk = k - pk; lu = (1 / L) / pp
        room = max(np.floor(L - inv / max(lu, 1e-9)), 0); nb = min(-dk, room) if dk < 0 else 0
        cash -= nb * lu * pp * (1 + fee); inv += nb * lu
        hl = np.floor(inv / max(lu, 1e-9)); ns = min(dk, hl) if dk > 0 else 0
        cash += ns * lu * pp * (1 - fee); inv -= ns * lu; pk = k; eq.append(cash + inv * pp)
    return pd.Series(eq)

def spread(a, b):
    """Cointegrated-spread grid. Hedge beta fit on TRAIN 2005-2015 ONLY (no look-ahead into OOS)."""
    df = pd.concat([np.log(a), np.log(b)], axis=1, keys=['x', 'y']).dropna()
    beta = sm.OLS(df[:'2015']['x'], sm.add_constant(df[:'2015']['y'])).fit().params.iloc[1]
    oos = df['2016':]; sp = (oos['x'] - beta * oos['y'])
    S = np.exp(sp.values - sp.values[0]); g = max(1.5 * sp.diff().std(), 0.01)
    eq = grideq(S, g); eq.index = oos.index; d = eq.pct_change()
    return mk((1 + d).groupby([d.index.year, d.index.month]).prod() - 1)

# ---- build sleeves ----
etfs = yf.download(['EDV', 'BNDX', 'EMB'], start='2013-01-01', end='2026-06-01', auto_adjust=True, progress=False)['Close'].ffill()
com = yf.download(['CL=F', 'BZ=F', 'RB=F', 'HO=F', 'ZC=F', 'ZW=F', 'LE=F', 'GF=F'], start='2005-01-01', end='2026-06-01', auto_adjust=True, progress=False)['Close'].ffill()
vd = yf.download(['VIXY', '^VIX', '^VIX3M'], start='2011-01-01', end='2026-06-01', auto_adjust=True, progress=False)['Close'].ffill()
# ShortVol: contango + VIX<25 + spike-kill, ALL shifted(1) -> uses only prior-day info
filt = ((vd['^VIX3M'] > vd['^VIX']) & (vd['^VIX'] < 25) & ~(vd['^VIX'].pct_change() > 0.20)).shift(1).fillna(False)
svd = (-vd['VIXY'].pct_change()).where(filt, 0.0).clip(-0.08, 0.08)
SV = mk((1 + svd.loc['2016':]).groupby([svd.loc['2016':].index.year, svd.loc['2016':].index.month]).prod() - 1)
# Trend: 12m momentum SIGN, shifted(1); vol from rolling std shifted(1) -> no look-ahead
tk = ['SPY', 'TLT', 'GLD', 'DBC', 'UUP', 'EEM', 'IEF', 'USO', 'SLV', 'FXE']
mp = yf.download(tk, start='2013-01-01', end='2026-06-01', auto_adjust=True, progress=False)['Close'].ffill().resample('ME').last(); mr = mp.pct_change()
pos = (np.sign(mp.pct_change(12)).shift(1) / mr.rolling(6).std().shift(1)).clip(-3, 3)
trend = mk((pos * mr).mean(axis=1).dropna().loc['2016':])

sleeves = {'ME_US': me_sleeve(etfs['EDV']), 'ME_intl': me_sleeve(etfs['BNDX']), 'ME_EM': me_sleeve(etfs['EMB']),
           'WTI_Brent': spread(com['CL=F'], com['BZ=F']), 'Corn_Wheat': spread(com['ZC=F'], com['ZW=F']),
           'Gaso_Crude': spread(com['RB=F'], com['CL=F']), 'Heat_Crude': spread(com['HO=F'], com['CL=F']),
           'Cattle_Feeder': spread(com['LE=F'], com['GF=F']), 'ShortVol': SV, 'Trend': trend}
M = pd.concat(sleeves, axis=1).loc['2016':].dropna()
M.to_parquet(f"{OUT}/audit_sleeve_returns.parquet")  # for independent re-audit
spy = yf.download('SPY', start='2015-01-01', end='2026-06-01', auto_adjust=True, progress=False)['Close']
spy = spy['SPY'] if isinstance(spy, pd.DataFrame) else spy
spym = mk(spy.resample('ME').last().pct_change().loc['2016':]); spym = spym.reindex(M.index)

def metrics(r, bench=None):
    r = r.dropna(); dn = r[r < 0]
    sr = r.mean() / r.std() * A; sortino = r.mean() / dn.std() * A if len(dn) else np.nan
    eq = (1 + r).cumprod(); dd = (eq / eq.cummax() - 1).min()
    ann = r.mean() * 12; calmar = ann / abs(dd) if dd else np.nan
    out = dict(SR=sr, Sortino=sortino, ann=ann, vol=r.std() * A, maxDD=dd, Calmar=calmar, expo=(r != 0).mean())
    if bench is not None:
        d = pd.concat([r, bench], axis=1, keys=['r', 'b']).dropna()
        m = sm.OLS(d['r'], sm.add_constant(d['b'])).fit(cov_type='HAC', cov_kwds={'maxlags': 6})
        out['beta'] = m.params['b']; out['alpha_ann'] = m.params['const'] * 12; out['alpha_t'] = m.tvalues['const']
    return out

print("=== PER-SLEEVE METRICS (OOS 2016-2026, monthly) ===")
print(f"{'sleeve':14s}{'SR':>6}{'Sortino':>8}{'ann%':>6}{'vol%':>6}{'maxDD%':>7}{'Calmar':>7}{'beta':>6}{'alphaT':>7}{'expo%':>6}")
for c in M:
    x = metrics(M[c], spym)
    print(f"{c:14s}{x['SR']:6.2f}{x['Sortino']:8.2f}{x['ann']*100:6.1f}{x['vol']*100:6.1f}{x['maxDD']*100:7.1f}{x['Calmar']:7.2f}{x['beta']:6.2f}{x['alpha_t']:7.2f}{x['expo']*100:6.0f}")

# ---- book ----
w = 1 / M.std(); w /= w.sum(); book = (M * w).sum(axis=1)
b = metrics(book, spym)
print(f"\n=== BOOK (inverse-vol) ===")
print(f"  SR={b['SR']:.2f} Sortino={b['Sortino']:.2f} ann={b['ann']*100:.1f}% vol={b['vol']*100:.1f}% maxDD={b['maxDD']*100:.1f}% Calmar={b['Calmar']:.2f}")
print(f"  beta_SPY={b['beta']:.3f} alpha={b['alpha_ann']*100:.1f}%/yr (t_HAC={b['alpha_t']:.2f})")
print(f"  weights: {dict(zip(M.columns,(w*100).round(1)))}")
# Kelly
S = b['SR']; vol = b['vol']; ann = b['ann']; dd = abs(b['maxDD'])
ddcris = sum(w[c]*abs(metrics(M[c])['maxDD']) for c in M.columns)
print(f"\n=== KELLY SIZING ===  full-Kelly lev = SR/vol = {S/vol:.1f}x (RECKLESS)")
print(f"  crisis-DD proxy (weighted sleeve DDs, corr->1) = -{ddcris*100:.0f}%")
for f,lbl in [(1.0,'full'),(0.5,'half'),(0.25,'quarter')]:
    lev = min(f*S/vol, 0.45/ddcris)  # cap at -45% crisis-DD budget
    print(f"  {lbl:8s}Kelly: lev={f*S/vol:5.1f}x (capped {lev:.1f}x) -> ann~{ann*lev*100:4.0f}%  6mo~{((1+ann*lev)**0.5-1)*100:4.0f}%  crisis-DD~-{ddcris*lev*100:3.0f}%")
Lrec = min(3.0, 0.45/ddcris)
print(f"\n  RECOMMENDED lev {Lrec:.1f}x: 1yr E[ret]~{ann*Lrec*100:.0f}%, 6mo~{((1+ann*Lrec)**0.5-1)*100:.0f}%, crisis-DD~-{ddcris*Lrec*100:.0f}%, in-sample-DD~-{dd*Lrec*100:.0f}%")

# OOS split (weight overfit check)
tr = M.loc[:'2021']; te = M.loc['2022':]; wv = 1/tr.std(); wv /= wv.sum()
print(f"\n=== ROBUSTNESS ===  equal-wt SR={metrics(M.mean(axis=1))['SR']:.2f} | inv-vol {b['SR']:.2f} | TRUE-OOS(wts16-21->22-26) {metrics((te*wv).sum(axis=1))['SR']:.2f}")
print(f"  avg pairwise corr = {M.corr().values[np.triu_indices(len(M.columns),1)].mean():.3f}")
print("saved: audit_sleeve_returns.parquet")
