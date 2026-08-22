"""
Institutional analytics + figures for #76 Ross Hook. Builds the MTM daily series
(delay+1, full diversified portfolio) and computes the full metric set + charts.
Outputs: results/s076_fig_perf.png, results/s076_fig_risk.png, results/s076_metrics.csv
ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd, json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab, rosshook as rh
RF = lab.RISK_FRAC; CLASS = lab.CLASS
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
cal = pd.DatetimeIndex(sorted(set().union(*[set(df.index) for df in uni.values()])))
MN, HK, TM = 10, 20, 10
DEPLOY = [t for t in uni if CLASS.get(t) in ('indices', 'commodities', 'crypto')]


def daily(instrs, side='both'):
    s = pd.Series(0.0, index=cal); pos = pd.Series(0.0, index=cal)
    for t in instrs:
        tr, dm = rh.simulate_rosshook(uni[t], MN, HK, TM, cost_bps=costs[t], fill='next_open', side=side, daily=True)
        s = s.add(dm.reindex(cal).fillna(0))
        for _, r in tr.iterrows():
            pos.loc[(cal >= r['entry']) & (cal <= r['exit'])] += 1
    return s * RF, pos


def trades(instrs):
    fr = []
    for t in instrs:
        tr = rh.simulate_rosshook(uni[t], MN, HK, TM, cost_bps=costs[t], fill='next_open')
        if len(tr): tr['instr'] = t; fr.append(tr)
    return pd.concat(fr, ignore_index=True)


def perf(s):
    s = s[s.index >= s[s != 0].index.min()].dropna(); n = len(s); yrs = n/252
    cagr = (1+s).prod()**(1/yrs)-1; vol = s.std()*np.sqrt(252)
    sh = s.mean()/s.std()*np.sqrt(252); dn = s[s < 0].std(); so = s.mean()/dn*np.sqrt(252)
    eq = (1+s).cumprod(); dd = eq/eq.cummax()-1; mdd = dd.min()
    und = (dd < 0);
    # longest drawdown duration (days)
    dur = 0; cur = 0
    for v in und:
        cur = cur+1 if v else 0; dur = max(dur, cur)
    return dict(cagr=cagr, vol=vol, sharpe=sh, sortino=so, calmar=cagr/abs(mdd), mdd=mdd,
                skew=s.skew(), kurt=s.kurt(), var95=np.percentile(s, 5), cvar95=s[s <= np.percentile(s, 5)].mean(),
                posd=(s > 0).mean(), ddur=dur, eq=eq, dd=dd, s=s)


P = trades(DEPLOY); r = P['netR'].values
s, pos = daily(DEPLOY); m = perf(s)
mkt = pd.concat([uni[t]['close'].pct_change().reindex(cal) for t in DEPLOY], axis=1).mean(axis=1)
tsmom = pd.concat([(np.sign(uni[t]['close'].shift(1)-uni[t]['close'].shift(253))*uni[t]['close'].pct_change()).reindex(cal) for t in DEPLOY], axis=1).mean(axis=1)


def ab(y, Xs, L=15):
    d = pd.concat([y]+Xs, axis=1).dropna(); yy = d.iloc[:, 0].values
    X = np.column_stack([np.ones(len(d))]+[d.iloc[:, i+1].values for i in range(len(Xs))]); nn = len(d)
    b, *_ = np.linalg.lstsq(X, yy, rcond=None); u = yy-X@b; XtXi = np.linalg.inv(X.T@X); S = (X*u[:, None]).T@(X*u[:, None])
    for k in range(1, L+1):
        w = 1-k/(L+1); G = (X[k:]*u[k:, None]).T@(X[:-k]*u[:-k, None]); S += w*(G+G.T)
    se = np.sqrt(np.diag(XtXi@S@XtXi)); return b, b/se


b2, t2 = ab(s, [mkt, tsmom])
w = r[r > 0]; ls = r[r < 0]
print("=== TRADE METRICS (deployable ex-forex, delay+1) ===")
print(f"N={len(r)} trades/yr={len(r)/(len(s)/252):.0f} win={ (r>0).mean()*100:.1f}% payoff={w.mean()/abs(ls.mean()):.2f} PF={w.sum()/abs(ls.sum()):.2f} expR={r.mean():+.4f} hold={(pd.to_datetime(P['exit'])-pd.to_datetime(P['entry'])).dt.days.mean():.1f}d long%={ (P['dir']>0).mean()*100:.0f}")
print(f"trade R: skew={pd.Series(r).skew():+.2f} kurt={pd.Series(r).kurt():.1f} best={r.max():+.1f} worst={r.min():+.1f}")
print("=== PORTFOLIO (MTM daily) ===")
print(f"CAGR={m['cagr']*100:+.1f}% vol={m['vol']*100:.1f}% Sharpe={m['sharpe']:.2f} Sortino={m['sortino']:.2f} Calmar={m['calmar']:.2f}")
print(f"MaxDD={m['mdd']*100:.1f}% DDdur={m['ddur']}d skew={m['skew']:+.2f} kurt={m['kurt']:.1f} VaR95={m['var95']*100:.2f}% CVaR95={m['cvar95']*100:.2f}% posDays={m['posd']*100:.0f}% exposure={ (pos>0).mean()*100:.0f}%")
print(f"FACTORS: alpha_ann={b2[0]*252:+.4f} t={t2[0]:+.2f} | beta_mkt={b2[1]:+.3f} t={t2[1]:+.2f} | beta_tsmom={b2[2]:+.3f} t={t2[2]:+.2f}")
ann = (1+m['s']).resample('YE').prod()-1
print("ANNUAL:", " ".join(f"{d.year}:{v*100:+.0f}" for d, v in ann.items()))
# per-class & per-period
rows = []
for cls in ['indices', 'commodities', 'crypto']:
    ci = [t for t in DEPLOY if CLASS.get(t) == cls]; sc, _ = daily(ci); pc = P[P['instr'].isin(ci)]
    rows.append([cls, len(pc), pc['netR'].mean(), perf(sc)['sharpe']])
pd.DataFrame(rows, columns=['class', 'n', 'expR', 'mtm_sharpe']).to_csv("../results/s076_metrics.csv", index=False)
print("PER-CLASS:", rows)

# ---------- FIG A: performance ----------
fig, ax = plt.subplots(2, 2, figsize=(13, 8))
bh_eq = (1+mkt.reindex(m['s'].index).fillna(0)).cumprod()
ax[0, 0].plot(m['eq'].index, m['eq'].values, lw=1.4, label=f"Ross Hook (Sh {m['sharpe']:.2f})")
ax[0, 0].plot(bh_eq.index, bh_eq.values, lw=1.0, alpha=.6, label="Buy&Hold (traded)")
ax[0, 0].set_yscale('log'); ax[0, 0].set_title("Equity curve (MTM, log)"); ax[0, 0].legend(fontsize=8)
ax[0, 1].fill_between(m['dd'].index, m['dd'].values*100, 0, color='crimson', alpha=.5); ax[0, 1].set_title(f"Drawdown — max {m['mdd']*100:.1f}%")
ann.index = ann.index.year; ax[1, 0].bar(ann.index.astype(str), ann.values*100, color=['seagreen' if v > 0 else 'indianred' for v in ann.values])
ax[1, 0].set_title("Annual return (%)"); ax[1, 0].tick_params(axis='x', rotation=90, labelsize=6)
roll = m['s'].rolling(252).mean()/m['s'].rolling(252).std()*np.sqrt(252)
ax[1, 1].plot(roll.index, roll.values, lw=1); ax[1, 1].axhline(0, color='k', lw=.6); ax[1, 1].axhline(1, color='g', ls='--', lw=.6); ax[1, 1].set_title("Rolling 12m Sharpe")
plt.tight_layout(); plt.savefig("../results/s076_fig_perf.png", dpi=120); plt.close()

# ---------- FIG B: risk ----------
fig, ax = plt.subplots(2, 2, figsize=(13, 8))
ax[0, 0].hist(r, bins=60, color='steelblue'); ax[0, 0].axvline(0, color='k', lw=.8); ax[0, 0].set_title(f"Trade R distribution (skew {pd.Series(r).skew():+.2f})")
cls_sh = {}
for cls in ['indices', 'commodities', 'crypto']:
    ci = [t for t in DEPLOY if CLASS.get(t) == cls]; sc, _ = daily(ci); cls_sh[cls] = perf(sc)['sharpe']
ax[0, 1].bar(cls_sh.keys(), cls_sh.values(), color=['steelblue', 'seagreen', 'goldenrod']); ax[0, 1].set_title("MTM Sharpe by class")
mo = ((1+m['s']).resample('ME').prod()-1)
hm = mo.groupby([mo.index.year, mo.index.month]).first().unstack()
im = ax[1, 0].imshow(hm.values*100, aspect='auto', cmap='RdYlGn', vmin=-5, vmax=5)
ax[1, 0].set_yticks(range(len(hm.index))); ax[1, 0].set_yticklabels(hm.index, fontsize=6); ax[1, 0].set_xticks(range(12)); ax[1, 0].set_xticklabels(['J','F','M','A','M','J','J','A','S','O','N','D'], fontsize=7)
ax[1, 0].set_title("Monthly returns (%)"); plt.colorbar(im, ax=ax[1, 0], fraction=.04)
ax[1, 1].plot(pos.index, pos.values, lw=.6, color='slategray'); ax[1, 1].set_title(f"Concurrent positions (avg {pos[pos>0].mean():.1f})")
plt.tight_layout(); plt.savefig("../results/s076_fig_risk.png", dpi=120); plt.close()
print("saved figs s076_fig_perf.png / s076_fig_risk.png")
