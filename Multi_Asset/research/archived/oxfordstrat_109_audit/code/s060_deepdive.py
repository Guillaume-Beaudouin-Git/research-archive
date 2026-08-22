"""
DEEP-DIVE #60 — Oops Bullish (gap-down-fade, long-only). Same rigor as the S012
deep-dive, with the S012 LESSON baked in: a Sharpe that "beats always-in buy&hold"
is NOT enough — the decisive test is ALPHA AFTER HEDGING OUT BETA.

Pipeline:
  1. Rebuild long-only trades (reuse s058.simulate_oops side='long').
  2. Turn trades into a DAILY portfolio return series (spread each trade's
     netR*RISK_FRAC over its holding days; sum concurrent positions).
  3. Build traded-classes equal-weight buy&hold DAILY returns on the same calendar.
  4. TEST A (decisive): OLS r_strat = alpha + beta*r_BH. Report annualized alpha,
     beta, t(alpha), R2, and the BETA-HEDGED Sharpe (r_strat - beta*r_BH).
     If hedged Sharpe ~ 0 -> it was beta (S012 outcome). If clearly >0 -> real alpha.
  5. TEST B: exposure (fraction of days in market) + exposure-matched BH.
  6. TEST C: per-class alpha/beta (is the edge crypto-only = 2-asset beta?).
  7. TEST D: sub-period Sharpe (GFC era / mid / 2019+ rally).
  8. TEST E: drawdown timing (when does the -66% happen).
  9. TEST F: fill/cost stress (delay+1, +slippage, close fill).
 10. TEST G: parameter plateau (ATR_Index x Time).
ftmo_lab.py UNCHANGED.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
from strat_s058_oops import simulate_oops, run_point

RISK_FRAC = lab.RISK_FRAC
AIX, TM = 3.0, 10
uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
CLASS = lab.CLASS

# ---- common calendar (union of business days actually present) ----
cal = sorted(set().union(*[set(df.index) for df in uni.values()]))
cal = pd.DatetimeIndex(cal)


def strat_daily(pool):
    """Spread each trade's netR*RISK_FRAC across its holding days -> portfolio daily ret."""
    s = pd.Series(0.0, index=cal)
    ent = pd.to_datetime(pool['entry']).values
    ext = pd.to_datetime(pool['exit']).values
    r = pool['netR'].values
    pos = pd.Series(0, index=cal)
    for k in range(len(pool)):
        win = cal[(cal >= ent[k]) & (cal <= ext[k])]
        if len(win) == 0:
            # same-day trade: put on the entry day
            j = cal.searchsorted(ent[k]);  win = cal[j:j+1] if j < len(cal) else cal[-1:]
        s.loc[win] += (r[k] * RISK_FRAC) / len(win)
        pos.loc[win] += 1
    return s, pos


def bh_daily(instruments):
    rs = [uni[t]['close'].pct_change().reindex(cal) for t in instruments]
    return pd.concat(rs, axis=1).mean(axis=1)


def ols_alpha_beta(y, x):
    """y = a + b x. Return alpha_ann, beta, t_alpha, r2, n."""
    d = pd.concat([y, x], axis=1).dropna()
    d = d[(d.iloc[:, 1] != 0)]            # days the market actually moved
    yy = d.iloc[:, 0].values; xx = d.iloc[:, 1].values
    n = len(yy)
    X = np.column_stack([np.ones(n), xx])
    beta_hat, *_ = np.linalg.lstsq(X, yy, rcond=None)
    resid = yy - X @ beta_hat
    s2 = (resid @ resid) / (n - 2)
    cov = s2 * np.linalg.inv(X.T @ X)
    se_a = np.sqrt(cov[0, 0])
    a, b = beta_hat
    t_a = a / se_a if se_a > 0 else np.nan
    ss = ((yy - yy.mean()) ** 2).sum()
    r2 = 1 - (resid @ resid) / ss if ss > 0 else np.nan
    return a * 252, b, t_a, r2, n


def sharpe(s):
    s = s.dropna()
    return float(s.mean() / s.std() * np.sqrt(252)) if s.std() > 0 else np.nan


if __name__ == "__main__":
    pool = run_point(AIX, TM, side='long')
    pm = lab.trade_metrics(pool)
    inst = list(pool['instr'].unique())
    print(f"=== DEEP-DIVE #60 Oops Bullish (ATR_Index={AIX} Time={TM}, long-only) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} "
          f"PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")

    sd, pos = strat_daily(pool)
    bh = bh_daily(inst)

    # ---- TEST A: alpha after hedging out beta (DECISIVE) ----
    a_full, b_full, t_full, r2_full, n_full = ols_alpha_beta(sd, bh)
    hedged_full = (sd - b_full * bh)
    print("\n[A] ALPHA/BETA (full)  r_strat = alpha + beta*r_BH(traded)")
    print(f"    alpha_ann={a_full:+.4f}  beta={b_full:+.3f}  t(alpha)={t_full:+.2f}  R2={r2_full:.3f}  n={n_full}")
    print(f"    Sharpe strat={sharpe(sd):+.2f}  |  BETA-HEDGED Sharpe={sharpe(hedged_full):+.2f}  (raw BH Sharpe={sharpe(bh):+.2f})")
    rec = sd[sd.index > '2018-12-31']; bhr = bh[bh.index > '2018-12-31']
    a_r, b_r, t_r, r2_r, n_r = ols_alpha_beta(rec, bhr)
    print(f"    2019+: alpha_ann={a_r:+.4f}  beta={b_r:+.3f}  t(alpha)={t_r:+.2f}  hedged Sharpe={sharpe(rec - b_r*bhr):+.2f}")

    # ---- TEST B: exposure ----
    in_mkt = (pos > 0).mean()
    print(f"\n[B] EXPOSURE: days in market={in_mkt*100:.1f}%  mean concurrent pos={pos[pos>0].mean():.1f}")
    bh_em = bh.copy(); bh_em[pos.reindex(bh.index).fillna(0) == 0] = 0.0   # BH only when strat in mkt
    print(f"    exposure-matched BH Sharpe={sharpe(bh_em):+.2f}  vs strat Sharpe={sharpe(sd):+.2f}")

    # ---- TEST C: per-class alpha/beta ----
    print("\n[C] PER-CLASS (alpha_ann / beta / hedged Sharpe / trades):")
    for cls in ['indices', 'forex', 'commodities', 'crypto']:
        ci = [t for t in inst if CLASS.get(t) == cls]
        if not ci: continue
        pc = pool[pool['instr'].isin(ci)]
        if len(pc) < 30:
            print(f"    {cls:11s}: n={len(pc)} (trop peu)"); continue
        sdc, _ = strat_daily(pc); bhc = bh_daily(ci)
        ac, bc, tc, r2c, nc = ols_alpha_beta(sdc, bhc)
        print(f"    {cls:11s}: alpha={ac:+.4f} beta={bc:+.2f} t={tc:+.2f} hedgedSh={sharpe(sdc-bc*bhc):+.2f} trades={len(pc)}")

    # ---- TEST D: sub-periods ----
    print("\n[D] SUB-PERIODS (entry-date; expR / Sharpe / hedged Sharpe):")
    e = pd.to_datetime(pool['entry'])
    for lab_, lo, hi in [('2007-2012','2007-01-01','2012-12-31'), ('2013-2018','2013-01-01','2018-12-31'),
                         ('2019-2025','2019-01-01','2025-12-31')]:
        sub = pool[(e >= lo) & (e <= hi)]
        if len(sub) < 20: print(f"    {lab_}: n={len(sub)}"); continue
        ms = lab.trade_metrics(sub); ss, _ = strat_daily(sub); bb_ = bh.reindex(ss.index)
        _, bsub, _, _, _ = ols_alpha_beta(ss, bb_)
        print(f"    {lab_}: trades={ms['trades']} expR={ms['expR']:+.4f} Sh={ms['sharpe']:+.2f} hedgedSh={sharpe(ss-bsub*bb_):+.2f}")

    # ---- TEST E: drawdown timing ----
    eq = (1 + sd).cumprod(); dd = eq/eq.cummax() - 1
    trough = dd.idxmin()
    print(f"\n[E] DRAWDOWN: max={dd.min()*100:.1f}% at {trough.date()}  (peak->trough)")
    for yr in [2008, 2011, 2015, 2018, 2020, 2022]:
        seg = dd[(dd.index.year == yr)]
        if len(seg): print(f"    {yr}: min DD intra-year {seg.min()*100:.1f}%")

    # ---- TEST F: fill / cost stress ----
    print("\n[F] FILL / COST STRESS (pooled Sharpe / expR):")
    for tagname, kw in [('stop (natif)', dict(fill='stop')), ('next_open (delai+1)', dict(fill='next_open')),
                        ('close', dict(fill='close'))]:
        m = lab.trade_metrics(run_point(AIX, TM, side='long', **kw))
        print(f"    {tagname:20s}: Sh={m['sharpe']:+.2f} expR={m['expR']:+.4f}")
    # extra slippage on the realistic delay+1 fill
    for extra in [2.0, 5.0]:
        frames = []
        for t, df in uni.items():
            tr = simulate_oops(df, AIX, TM, cost_bps=costs[t] + extra, side='long', fill='next_open')
            if len(tr): tr['instr'] = t; frames.append(tr)
        m = lab.trade_metrics(pd.concat(frames, ignore_index=True))
        print(f"    delai+1 +{extra:.0f}bps slippage : Sh={m['sharpe']:+.2f} expR={m['expR']:+.4f}")

    # ---- TEST G: parameter plateau ----
    print("\n[G] PARAM PLATEAU — Sharpe (ATR_Index x Time):")
    AIs = [1.5, 3.0, 5.0]; TMs = [5, 10, 20]
    sgrid = pd.DataFrame(index=[f"A{x}" for x in AIs], columns=[f"T{x}" for x in TMs], dtype=float)
    for ai in AIs:
        for tm in TMs:
            sgrid.loc[f"A{ai}", f"T{tm}"] = lab.trade_metrics(run_point(ai, tm, side='long'))['sharpe']
    print(sgrid.round(2).to_string())

    pd.DataFrame({'strat': sd, 'bh': bh, 'eq': eq, 'dd': dd}).to_csv("s060_deepdive_daily.csv")
    print("\nsaved s060_deepdive_daily.csv")
