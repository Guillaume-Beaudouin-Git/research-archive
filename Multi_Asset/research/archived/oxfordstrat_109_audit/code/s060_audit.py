"""
AUDIT #60 — CORRECTED metrics (mark-to-market), supersedes the inflated Sharpe in
s060_deepdive.py. See AUDIT_DOSSIER_S060.md.

Key fix: the daily series is built by CLOSE-TO-CLOSE mark-to-market of each open
position (mtm_series), NOT by spreading each trade's R over its holding days.
The spreading smoothed daily vol (1.1% -> real 3.4%) and inflated Sharpe ~3x and
biased beta toward 0. This script recomputes:
  (A) trade-level expR + block-bootstrap CI per class (method-independent),
  (B) mark-to-market portfolio Sharpe/Sortino/Calmar (all / no-FX / indices / commodities),
  (C) mark-to-market alpha/beta vs traded buy&hold (Newey-West t),
  (D) commodity gap-size distribution (roll-artifact check).
ftmo_lab.py UNCHANGED. Run: python s060_audit.py
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
from strat_s058_oops import run_point

ATR_LEN, ATR_STOP = 20, 6.0
AIX, TM = 3.0, 10
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
CLASS = lab.CLASS
cal = pd.DatetimeIndex(sorted(set().union(*[set(df.index) for df in uni.values()])))


def mtm_series(df, atr_index=AIX, time_index=TM, *, atr_stop=ATR_STOP, cost_bps=2.0, fill='next_open'):
    """Close-to-close mark-to-market daily R series for the long-only Oops (no spreading)."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values
    n = len(df); idx = df.index; daily = pd.Series(0.0, index=idx); i = 2
    while i < n - 1:
        if not (o[i] < l[i - 1] and h[i] >= l[i - 1] and np.isfinite(A[i]) and A[i] > 0):
            i += 1; continue
        lvl = l[i - 1]
        if fill == 'stop':       entry = max(o[i], lvl); eb = i
        elif fill == 'next_open': eb = i + 1; entry = o[eb] if eb <= n - 1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry): i += 1; continue
        risk0 = A[i] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        xs = entry - A[i] * atr_index; last = min(eb + time_index, n - 1); xp = xj = None
        for j in range(eb, last + 1):
            if l[j] <= xs: xp, xj = xs, j; break
            if j == last: xp, xj = c[j], j; break
        prev = entry
        for j in range(eb, xj + 1):
            px = c[j] if j < xj else xp
            daily.iloc[j] += (px - prev) / risk0; prev = c[j]
        daily.iloc[eb] -= cost_R; i = xj + 1
    return daily


def agg(instrs, fill='next_open'):
    s = pd.Series(0.0, index=cal)
    for t in instrs:
        s = s.add(mtm_series(uni[t], cost_bps=costs[t], fill=fill).reindex(cal).fillna(0))
    return s * lab.RISK_FRAC


def bh(instrs):
    return pd.concat([uni[t]['close'].pct_change().reindex(cal) for t in instrs], axis=1).mean(axis=1)


def stats(s):
    s = s[s.index >= s[s != 0].index.min()].dropna(); mu, sg = s.mean(), s.std()
    ann = (1 + s).prod() ** (252 / len(s)) - 1; eq = (1 + s).cumprod(); dd = (eq / eq.cummax() - 1).min()
    dn = s[s < 0].std()
    return dict(sh=mu / sg * np.sqrt(252) if sg > 0 else np.nan, so=mu / dn * np.sqrt(252) if dn > 0 else np.nan,
                cal=ann / abs(dd) if dd < 0 else np.nan, ann=ann, vol=sg * np.sqrt(252), mdd=dd, skew=s.skew())


def ab(y, x, L=15):
    d = pd.concat([y, x], axis=1).dropna(); d = d[d.iloc[:, 1] != 0]
    yy, xx, n = d.iloc[:, 0].values, d.iloc[:, 1].values, len(d)
    X = np.column_stack([np.ones(n), xx]); b, *_ = np.linalg.lstsq(X, yy, rcond=None); u = yy - X @ b
    XtXi = np.linalg.inv(X.T @ X); S = (X * u[:, None]).T @ (X * u[:, None])
    for k in range(1, L + 1):
        w = 1 - k / (L + 1); G = (X[k:] * u[k:, None]).T @ (X[:-k] * u[:-k, None]); S += w * (G + G.T)
    cov = XtXi @ S @ XtXi
    yh = d.iloc[:, 0] - b[1] * d.iloc[:, 1]
    return b[0] * 252, b[1], b[0] / np.sqrt(cov[0, 0]), yh.mean() / yh.std() * np.sqrt(252)


def boot_ci(r, nb=1500, blk=20, seed=0):
    rng = np.random.default_rng(seed); n = len(r); k = int(np.ceil(n / blk))
    out = [r[np.concatenate([np.arange(s, s + blk) for s in rng.integers(0, n - blk, k)])[:n]].mean() for _ in range(nb)]
    return np.percentile(out, [2.5, 97.5])


if __name__ == "__main__":
    allI = list(uni)
    dep = [t for t in allI if CLASS.get(t) in ('indices', 'commodities', 'crypto')]
    idx = [t for t in allI if CLASS.get(t) == 'indices']
    com = [t for t in allI if CLASS.get(t) == 'commodities']

    print("=== (A) TRADE-LEVEL expR + bootstrap CI (delai+1, method-independent) ===")
    pool = run_point(AIX, TM, side='long', fill='next_open')
    for cls in ['indices', 'commodities', 'crypto', 'forex', 'ALL']:
        p = pool if cls == 'ALL' else pool[pool['instr'].isin([t for t in pool['instr'].unique() if CLASS.get(t) == cls])]
        r = p['netR'].values
        if len(r) < 20: print(f"  {cls}: n={len(r)}"); continue
        lo, hi = boot_ci(r); print(f"  {cls:11s}: n={len(r)} expR={r.mean():+.4f} CI95[{lo:+.4f},{hi:+.4f}] win={(r>0).mean()*100:.1f}%")

    print("\n=== (B) MARK-TO-MARKET portfolio metrics (delai+1) ===")
    for nm, ins in [('ALL', allI), ('DEPLOY no-FX', dep), ('INDICES (propres)', idx), ('COMMODITIES (yf)', com)]:
        m = stats(agg(ins)); print(f"  {nm:18s}: Sharpe={m['sh']:.2f} Sortino={m['so']:.2f} Calmar={m['cal']:.2f} ann={m['ann']*100:+.1f}% vol={m['vol']*100:.1f}% maxDD={m['mdd']*100:.1f}% skew={m['skew']:+.2f}")

    print("\n=== (C) MTM alpha/beta vs buy&hold(traded), Newey-West L15 ===")
    for nm, ins in [('DEPLOY no-FX', dep), ('INDICES (propres)', idx)]:
        a, b, t, shh = ab(agg(ins), bh(ins)); print(f"  {nm:18s}: alpha_ann={a:+.4f} beta={b:+.3f} t_NW={t:+.2f} Sharpe_couvert={shh:.2f}")

    print("\n=== (D) Commodity gap-size (roll-artifact check) ===")
    g = []
    for t in com:
        df = uni[t]; o, l = df['open'].values, df['low'].values; A = lab.atr(df, 20).values
        for i in range(2, len(df) - 1):
            if o[i] < l[i - 1] and df['high'].values[i] >= l[i - 1] and np.isfinite(A[i]) and A[i] > 0:
                g.append((l[i - 1] - o[i]) / A[i])
    g = pd.Series(g)
    print(f"  gap (Low[i-1]-Open[i])/ATR: n={len(g)} median={g.median():.2f} p90={g.quantile(.9):.2f} p99={g.quantile(.99):.2f} share>2ATR={(g>2).mean()*100:.1f}% (roll gaps would be large)")
