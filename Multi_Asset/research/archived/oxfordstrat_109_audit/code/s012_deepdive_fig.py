"""Figure for the S012 deep-dive: champions (indices LONG dip-buy) + low-vol thesis."""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab
import s012_deepdive as dd

uni, INDICES = dd.uni, dd.INDICES
US = ['US30', 'US500', 'US100', 'US2000']
RISK = lab.RISK_FRAC

P = {
    "baseline all/both": dd.run_variant(list(uni)),
    "C0 indices/LONG": dd.run_variant(INDICES, side='long'),
    "C2 indices/LONG vol<=0.66": dd.run_variant(INDICES, side='long', vol_max=0.66),
    "C4 US-idx/LONG vol<=0.5": dd.run_variant(US, side='long', vol_max=0.5),
    "C5 indices/BOTH vol<=0.5": dd.run_variant(INDICES, vol_max=0.5),
}
COL = {"baseline all/both": '#999', "C0 indices/LONG": '#1f77b4', "C2 indices/LONG vol<=0.66": '#d62728',
       "C4 US-idx/LONG vol<=0.5": '#9467bd', "C5 indices/BOTH vol<=0.5": '#2ca02c'}

fig, ax = plt.subplots(2, 2, figsize=(14, 9))
# A) compounded equity (1% risk/trade, by exit date)
for lbl, p in P.items():
    if not len(p): continue
    q = p.sort_values('exit'); eq = (1 + RISK * pd.Series(q['netR'].values,
        index=pd.to_datetime(q['exit']))).cumprod()
    eq = eq.groupby(eq.index).last()
    ax[0, 0].plot(eq.index, eq.values, label=lbl, color=COL[lbl], lw=1.6)
ax[0, 0].set_title("A) Compounded equity (1% risk/trade, after costs)"); ax[0, 0].legend(fontsize=8)
ax[0, 0].grid(alpha=.3); ax[0, 0].set_yscale('log')
# B) walk-forward block Sharpe: C0 vs C2 (low-vol) vs C5
blocks = [(2000, 2006), (2006, 2012), (2012, 2018), (2018, 2024), (2024, 2030)]
labs = [f"{a}-{str(b-1)[2:]}" for a, b in blocks]
def blk_sh(p):
    e = pd.to_datetime(p['entry']); out = []
    for a, b in blocks:
        s = p[(e >= pd.Timestamp(f"{a}-01-01")) & (e < pd.Timestamp(f"{b}-01-01"))]
        out.append(lab.trade_metrics(s)['sharpe'] if len(s) > 3 else np.nan)
    return out
x = np.arange(len(blocks)); w = .26
ax[0, 1].bar(x - w, blk_sh(P["C0 indices/LONG"]), w, label='C0 indices/LONG', color='#1f77b4')
ax[0, 1].bar(x, blk_sh(P["C2 indices/LONG vol<=0.66"]), w, label='C2 +low-vol', color='#d62728')
ax[0, 1].bar(x + w, blk_sh(P["C5 indices/BOTH vol<=0.5"]), w, label='C5 both+low-vol', color='#2ca02c')
ax[0, 1].axhline(0.5, color='g', ls='--', lw=.8); ax[0, 1].axhline(0, color='k', lw=.8)
ax[0, 1].set_xticks(x); ax[0, 1].set_xticklabels(labs, fontsize=8)
ax[0, 1].set_title("B) Walk-forward Sharpe — low-vol filter rescues 2018-23"); ax[0, 1].legend(fontsize=8); ax[0, 1].grid(alpha=.3)
# C) edge by vol regime (indices long) — the mechanism
bl = dd.run_variant(INDICES, side='long')
buck = [("low\n<0.33", 0, .33), ("mid\n.33-.66", .33, .66), ("high\n>0.66", .66, 1.01)]
ev = []
for _, lo, hi in buck:
    sub = bl[(bl['volp'] >= lo) & (bl['volp'] < hi)]
    ev.append(lab.trade_metrics(sub)['expR'])
ax[1, 0].bar([b[0] for b in buck], ev, color=['#2ca02c', '#ff7f0e', '#d62728'])
ax[1, 0].axhline(0, color='k', lw=.8); ax[1, 0].set_ylabel("net expR (R/trade)")
ax[1, 0].set_title("C) Dip-buy edge by vol regime — strongest in LOW vol"); ax[1, 0].grid(alpha=.3)
# D) per-index recent 2019+ expR (C0)
champ = P["C0 indices/LONG"]; rec = champ[pd.to_datetime(champ['entry']) > pd.Timestamp('2018-12-31')]
per = {t: lab.trade_metrics(rec[rec['instr'] == t])['expR'] for t in INDICES if len(rec[rec['instr'] == t]) >= 5}
per = dict(sorted(per.items(), key=lambda kv: kv[1], reverse=True))
ax[1, 1].bar(list(per), list(per.values()), color=['#2ca02c' if v > 0 else '#d62728' for v in per.values()])
ax[1, 1].axhline(0, color='k', lw=.8); ax[1, 1].set_title("D) Per-index recent (2019+) expR — champion C0")
ax[1, 1].tick_params(axis='x', labelrotation=45, labelsize=8); ax[1, 1].grid(alpha=.3)
fig.suptitle("S012 Bollinger %b — deep dive: indices LONG dip-buy + low-vol filter (FTMO, net of costs)", fontweight='bold')
fig.tight_layout(); fig.savefig("s012_deepdive.png", dpi=120)
print("saved s012_deepdive.png")
