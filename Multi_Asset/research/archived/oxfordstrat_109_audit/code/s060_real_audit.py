"""
AUDIT #60 on REAL FTMO data (addendum to s060_audit.py / AUDIT_DOSSIER_S060.md §11).

Replaces the proxy data where REAL FTMO-grade OHLC exists:
  - indices  : already real (ftmo_panel) in the store -> used as-is
  - gold     : rebuilt from real M1 (deep_history_utc/XAUUSD_M1.csv, 2007+) ->
               real_data/XAUUSD_real_m1daily.parquet
  - crypto   : real M1 in the store -> used as-is
The softs / silver / platinum / palladium / oil sleeve has NO real FTMO OHLC in the
dataset (only close-only ETF proxies + Yahoo continuous futures), so it CANNOT be
validated and is excluded here.

Conclusion (see dossier §11): on real data the per-trade edge is small-but-positive,
but the BETA-HEDGED alpha is NOT statistically significant (t_NW < 1). ftmo_lab UNCHANGED.
Run: python s060_real_audit.py
"""
import os, numpy as np, pandas as pd
import ftmo_lab as lab
from strat_s058_oops import simulate_oops

ATR_STOP, AIX, TM = 6.0, 3.0, 10
HERE = os.path.dirname(os.path.abspath(__file__))
GOLD = os.path.join(HERE, "..", "real_data", "XAUUSD_real_m1daily.parquet")

store = lab.load_universe(); CLASS = lab.CLASS
idxs = [t for t in store if CLASS.get(t) == 'indices']     # real ftmo panels
cry = [t for t in store if CLASS.get(t) == 'crypto']       # real M1
uni = {t: store[t] for t in idxs + cry}
uni['XAUUSD'] = pd.read_parquet(GOLD)                       # REAL gold 2007+
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
cal = pd.DatetimeIndex(sorted(set().union(*[set(df.index) for df in uni.values()])))


def mtm(df, cost_bps, fill='next_open'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close')); A = lab.atr(df, 20).values
    n = len(df); daily = pd.Series(0.0, index=df.index); i = 2
    while i < n - 1:
        if not (o[i] < l[i - 1] and h[i] >= l[i - 1] and np.isfinite(A[i]) and A[i] > 0): i += 1; continue
        lvl = l[i - 1]; eb = i + 1 if fill == 'next_open' else i
        entry = o[eb] if fill == 'next_open' else max(o[i], lvl)
        if eb > n - 1 or not np.isfinite(entry): i += 1; continue
        risk0 = A[i] * ATR_STOP; cR = (cost_bps / 1e4) * abs(entry) / risk0
        xs = entry - A[i] * AIX; last = min(eb + TM, n - 1); xp = xj = None
        for j in range(eb, last + 1):
            if l[j] <= xs: xp, xj = xs, j; break
            if j == last: xp, xj = c[j], j; break
        prev = entry
        for j in range(eb, xj + 1):
            px = c[j] if j < xj else xp; daily.iloc[j] += (px - prev) / risk0; prev = c[j]
        daily.iloc[eb] -= cR; i = xj + 1
    return daily


def trades(ins):
    fr = []
    for t in ins:
        tr = simulate_oops(uni[t], AIX, TM, cost_bps=costs[t], side='long', fill='next_open')
        if len(tr): tr['instr'] = t; fr.append(tr)
    return pd.concat(fr, ignore_index=True) if fr else pd.DataFrame()


def agg(ins):
    s = pd.Series(0.0, index=cal)
    for t in ins: s = s.add(mtm(uni[t], costs[t]).reindex(cal).fillna(0))
    return s * lab.RISK_FRAC


def bh(ins): return pd.concat([uni[t]['close'].pct_change().reindex(cal) for t in ins], axis=1).mean(axis=1)
def shp(s): s = s[s.index >= s[s != 0].index.min()].dropna(); return s.mean() / s.std() * np.sqrt(252) if s.std() > 0 else np.nan


def boot(r, nb=1500, blk=20, sd=0):
    rng = np.random.default_rng(sd); n = len(r); k = int(np.ceil(n / blk))
    o = [r[np.concatenate([np.arange(s, s + blk) for s in rng.integers(0, n - blk, k)])[:n]].mean() for _ in range(nb)]
    return np.percentile(o, [2.5, 97.5])


def ab(y, x, L=15):
    d = pd.concat([y, x], axis=1).dropna(); d = d[d.iloc[:, 1] != 0]; yy, xx, n = d.iloc[:, 0].values, d.iloc[:, 1].values, len(d)
    X = np.column_stack([np.ones(n), xx]); b, *_ = np.linalg.lstsq(X, yy, rcond=None); u = yy - X @ b
    XtXi = np.linalg.inv(X.T @ X); S = (X * u[:, None]).T @ (X * u[:, None])
    for k in range(1, L + 1):
        w = 1 - k / (L + 1); G = (X[k:] * u[k:, None]).T @ (X[:-k] * u[:-k, None]); S += w * (G + G.T)
    cov = XtXi @ S @ XtXi; yh = d.iloc[:, 0] - b[1] * d.iloc[:, 1]
    return b[0] * 252, b[1], b[0] / np.sqrt(cov[0, 0]), yh.mean() / yh.std() * np.sqrt(252)


if __name__ == "__main__":
    pool = trades(idxs + ['XAUUSD'] + cry)
    print("=== #60 on REAL FTMO data (indices ftmo-panel + gold M1 2007+ + crypto) ===")
    print("(A) TRADE-LEVEL expR (delai+1) + block-bootstrap CI:")
    for nm, ins in [('indices (REAL ftmo)', idxs), ('GOLD XAUUSD (REAL M1)', ['XAUUSD']),
                    ('crypto (real)', cry), ('REAL deployable', idxs + ['XAUUSD'] + cry)]:
        p = pool[pool['instr'].isin(ins)]; r = p['netR'].values
        if len(r) < 20: print(f"   {nm:24s}: n={len(r)} (too few)"); continue
        lo, hi = boot(r); print(f"   {nm:24s}: n={len(r)} expR={r.mean():+.4f} CI95[{lo:+.4f},{hi:+.4f}] win={(r>0).mean()*100:.1f}%")
    print("(B/C) MARK-TO-MARKET portfolio + alpha/beta (Newey-West):")
    for nm, ins in [('indices (REAL)', idxs), ('REAL deployable', idxs + ['XAUUSD'] + cry)]:
        y = agg(ins); a, b, t, shh = ab(y, bh(ins))
        print(f"   {nm:16s}: Sharpe={shp(y):.2f} | alpha_ann={a:+.4f} beta={b:+.3f} t_NW={t:+.2f} hedged_Sharpe={shh:.2f}")
    print("\nNOTE: softs/silver/platinum/palladium/oil have NO real FTMO OHLC (proxy only) -> not validatable.")
