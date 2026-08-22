"""
DEEP-DIVE #60 part 2 — robustness checks for the alpha found in part 1, plus the
DEPLOYABLE sleeve (drop forex, which had negative alpha) and a figure.

Skeptical add-ons (S012 discipline):
  - NEWEY-WEST t(alpha): the daily-spread series is autocorrelated (10-day overlap),
    so OLS t is inflated. Recompute alpha t-stat with HAC (Newey-West, L=15) lags.
  - BLOCK BOOTSTRAP of per-trade expR (immune to the spreading method).
  - Deployable sleeve = indices + commodities (+ crypto): daily alpha/beta/Sharpe/DD.
"""
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ftmo_lab as lab
from strat_s058_oops import run_point
from s060_deepdive import strat_daily, bh_daily, sharpe, cal, CLASS

AIX, TM = 3.0, 10
RISK = lab.RISK_FRAC


def nw_t_alpha(y, x, L=15):
    d = pd.concat([y, x], axis=1).dropna(); d = d[d.iloc[:, 1] != 0]
    yy = d.iloc[:, 0].values; xx = d.iloc[:, 1].values; n = len(yy)
    X = np.column_stack([np.ones(n), xx])
    bhat, *_ = np.linalg.lstsq(X, yy, rcond=None)
    u = yy - X @ bhat
    XtX_inv = np.linalg.inv(X.T @ X)
    S = (X * u[:, None]).T @ (X * u[:, None])
    for l in range(1, L + 1):
        w = 1 - l / (L + 1)
        G = (X[l:] * u[l:, None]).T @ (X[:-l] * u[:-l, None])
        S += w * (G + G.T)
    cov = XtX_inv @ S @ XtX_inv
    return bhat[0] * 252, bhat[1], bhat[0] / np.sqrt(cov[0, 0])


def block_boot_expR(r, nboot=2000, block=20, seed=1):
    rng = np.random.default_rng(seed); n = len(r); nb = int(np.ceil(n / block)); out = np.empty(nboot)
    for k in range(nboot):
        starts = rng.integers(0, n - block, nb)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        out[k] = r[idx].mean()
    return np.percentile(out, [2.5, 50, 97.5])


if __name__ == "__main__":
    pool = run_point(AIX, TM, side='long')
    inst = list(pool['instr'].unique())
    sd, pos = strat_daily(pool); bh = bh_daily(inst)

    a, b, t_nw = nw_t_alpha(sd, bh)
    print("=== DEEP-DIVE #60 part 2 ===")
    print(f"[A'] HAC (Newey-West L=15): alpha_ann={a:+.4f} beta={b:+.3f} t_NW(alpha)={t_nw:+.2f}")
    lo, md, hi = block_boot_expR(pool['netR'].values)
    print(f"[boot] per-trade expR 95% CI (block=20): [{lo:+.4f}, {hi:+.4f}] median {md:+.4f}  (net, delai+0)")
    # delay+1 bootstrap (the tradeable one)
    pool_no = run_point(AIX, TM, side='long', fill='next_open')
    lo2, md2, hi2 = block_boot_expR(pool_no['netR'].values)
    print(f"[boot] per-trade expR 95% CI delai+1: [{lo2:+.4f}, {hi2:+.4f}] median {md2:+.4f}")

    # ---- deployable sleeve: drop forex ----
    keep = [t for t in inst if CLASS.get(t) in ('indices', 'commodities', 'crypto')]
    dep = pool[pool['instr'].isin(keep)]
    sdd, posd = strat_daily(dep); bhd = bh_daily(keep)
    ad, bd, td = nw_t_alpha(sdd, bhd)
    md_ = lab.trade_metrics(dep)
    eqd = (1 + sdd).cumprod(); ddd = eqd/eqd.cummax() - 1
    print(f"\n[DEPLOY] indices+commodities+crypto (drop FX): trades={md_['trades']} tradeSh={md_['sharpe']:+.2f} "
          f"portSh={sharpe(sdd):+.2f} alpha_ann={ad:+.4f} beta={bd:+.3f} t_NW={td:+.2f} maxDD(port)={ddd.min()*100:.1f}%")
    dep_no = lab.trade_metrics(run_point(AIX, TM, side='long', fill='next_open'))

    # ---- figure ----
    eq = (1 + sd).cumprod(); dd = eq/eq.cummax() - 1
    bh_eq = (1 + bh.reindex(sd.index).fillna(0)).cumprod()
    fig, ax = plt.subplots(2, 2, figsize=(13, 8))
    ax[0,0].plot(eq.index, eq.values, label=f"Oops Bull (all) Sh {sharpe(sd):.2f}", lw=1.3)
    ax[0,0].plot(eqd.index, eqd.values, label=f"deployable (no FX) Sh {sharpe(sdd):.2f}", lw=1.3)
    ax[0,0].plot(bh_eq.index, bh_eq.values, label=f"buy&hold(traded) Sh {sharpe(bh):.2f}", lw=1.1, alpha=.7)
    ax[0,0].set_yscale('log'); ax[0,0].set_title("Equity (log) — portefeuille diversifie"); ax[0,0].legend(fontsize=8)
    ax[0,1].fill_between(dd.index, dd.values*100, 0, color='crimson', alpha=.5)
    ax[0,1].set_title(f"Drawdown portefeuille — max {dd.min()*100:.1f}% (PAS -66%)"); ax[0,1].set_ylabel("%")
    # per-class hedged sharpe bar
    cls_sh = {}
    for cls in ['indices','commodities','crypto','forex']:
        ci=[t for t in inst if CLASS.get(t)==cls]; pc=pool[pool['instr'].isin(ci)]
        if len(pc)>=30:
            sdc,_=strat_daily(pc); bhc=bh_daily(ci); _,bc,_=nw_t_alpha(sdc,bhc); cls_sh[cls]=sharpe(sdc-bc*bhc)
    ax[1,0].bar(cls_sh.keys(), cls_sh.values(), color=['steelblue','seagreen','goldenrod','indianred'])
    ax[1,0].axhline(0, color='k', lw=.8); ax[1,0].set_title("Sharpe couvert-beta par classe"); ax[1,0].set_ylabel("hedged Sharpe")
    # rolling 1y portfolio sharpe
    roll = sd.rolling(252).mean()/sd.rolling(252).std()*np.sqrt(252)
    ax[1,1].plot(roll.index, roll.values, lw=1); ax[1,1].axhline(0,color='k',lw=.6); ax[1,1].axhline(1,color='g',ls='--',lw=.6)
    ax[1,1].set_title("Sharpe glissant 1 an (portefeuille)")
    plt.tight_layout(); plt.savefig("../results/s060_deepdive.png", dpi=110)
    print("saved ../results/s060_deepdive.png")
