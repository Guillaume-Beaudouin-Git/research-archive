"""Autopsy of the high-Sharpe Piste-A cells: are they real reversion or slow relative-drift (beta trap)?
Tests: OOS coint (already failed) + per-year coint + N_eff + trade-level block bootstrap +
beta-orthogonality (L38: regress spread P&L on the two legs' vol-targeted B&H) + honest DSR."""
from __future__ import annotations
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import data as D, stats as st, ftmo_costs as C
from statsmodels.tsa.stattools import adfuller
from run_statarb import rolling_beta, BETA_W, Z_W, HARD_STOP_Z

CELLS = [("US500", "US30", 2.0, 0.5), ("US30", "GER40", 1.5, 0.5), ("US100", "US500", 1.5, 0.5)]


def trade_series(a, b, zin, zout):
    panel = D.close_panel([a, b], "D"); la, lb = np.log(panel[a]), np.log(panel[b])
    beta = rolling_beta(la, lb, BETA_W); spread = la - beta * lb
    z = (spread - spread.rolling(Z_W).mean()) / spread.rolling(Z_W).std()
    dla, dlb = la.diff(), lb.diff(); idx = la.index
    rt = (C.rt_cost_bps(a) + C.rt_cost_bps(b)) / 1e4
    finL = C.pair_financing_bps_night(a, b, +1) / 1e4; finS = C.pair_financing_bps_night(a, b, -1) / 1e4
    trip = np.where(idx.weekday == C.TRIPLE_DOW[a], 3.0, 1.0)
    pos = np.zeros(len(idx)); cur = 0; za = z.values; ba = beta.values
    entry_idx = []; trades = []
    for t in range(len(idx)):
        if np.isnan(za[t]) or np.isnan(ba[t]): pos[t] = 0; cur = 0; continue
        prev = cur
        if cur == 0:
            if za[t] <= -zin: cur = +1
            elif za[t] >= zin: cur = -1
            if cur != 0: entry_idx.append(t)
        else:
            if abs(za[t]) < zout or abs(za[t]) > HARD_STOP_Z:
                trades.append((entry_idx[-1], t, prev)); cur = 0
        pos[t] = cur
    pos = pd.Series(pos, index=idx); posx = pos.shift(1).fillna(0)
    sret = dla - beta.shift(1) * dlb
    gross = posx * sret
    tc = posx.diff().abs().fillna(0) * (rt / 2.0)
    fin = np.where(posx > 0, finL, np.where(posx < 0, finS, 0.0)) * trip
    net = gross - tc + pd.Series(fin, index=idx)   # fin SIGNED (neg=cost) -> ADD
    # per-trade net returns
    tr = []
    for e, x, d in trades:
        tr.append(dict(dir=d, hold=x - e, ret=float(net.iloc[e + 1:x + 1].sum())))
    return net, posx, pd.DataFrame(tr), la, lb, panel


def peryear_coint(la, lb):
    out = {}
    for y, g in pd.DataFrame({"a": la, "b": lb}).groupby(la.index.year):
        if len(g) < 60: continue
        X = np.column_stack([np.ones(len(g)), g["b"].values])
        bb = np.linalg.lstsq(X, g["a"].values, rcond=None)[0]
        res = g["a"].values - (bb[0] + bb[1] * g["b"].values)
        try: out[y] = adfuller(res, maxlag=1, autolag=None)[1]
        except Exception: out[y] = np.nan
    return out


for a, b, zin, zout in CELLS:
    net, posx, tr, la, lb, panel = trade_series(a, b, zin, zout)
    nz = net[net != 0]
    print(f"\n########## {a}/{b}  z_in={zin} z_out={zout} ##########")
    print(f"  n_trades={len(tr)}  avg_hold={tr['hold'].mean():.1f}d  "
          f"net_daily_Sharpe={st.sharpe(nz.values):.3f}  HAC_t(daily)={st.hac_tstat(nz.values):.2f}")
    # N_eff: independent trades, not daily bars
    print(f"  N_eff (independent trades)={len(tr)}  ->  trade-level mean ret & bootstrap:")
    tret = tr["ret"].values
    if len(tret) > 5:
        t_trade = tret.mean() / (tret.std(ddof=1) / np.sqrt(len(tret)))
        print(f"    trade mean={tret.mean()*1e4:+.1f} bps  t(iid over trades)={t_trade:+.2f}  "
              f"block-bootstrap p(mean>0)={st.block_bootstrap_p(tret, block=3, n=5000):.4f}")
    # two-sided by direction
    for d, name in [(+1, "long-spread"), (-1, "short-spread")]:
        sub = tr[tr["dir"] == d]
        if len(sub):
            print(f"    {name}: n={len(sub):>2}  mean={sub['ret'].mean()*1e4:+.1f} bps  "
                  f"total={sub['ret'].sum()*1e4:+.1f} bps  win%={100*(sub['ret']>0).mean():.0f}")
    # per-year cointegration
    pyc = peryear_coint(la, lb); frac = np.mean([p < 0.05 for p in pyc.values()])
    print(f"  per-year coint frac (p<0.05): {frac:.2f}  ({sum(p<0.05 for p in pyc.values())}/{len(pyc)} yrs)")
    # beta-orthogonality (L38): regress trade daily P&L on the two legs' returns
    dla, dlb = la.diff(), lb.diff()
    held = posx != 0
    y = net[held].values
    Xo = np.column_stack([np.ones(held.sum()), dla[held].values, dlb[held].values])
    coef, *_ = np.linalg.lstsq(Xo, y, rcond=None)
    yhat = Xo @ coef; r2 = 1 - np.var(y - yhat) / np.var(y)
    print(f"  beta-orthogonality: spread-P&L R^2 on (dUS_a,dUS_b) = {r2:.3f}  "
          f"(high R^2 => it IS the two legs' directional move)")

# honest DSR across the 96-trial space, evaluated at US500/US30 best
grid = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_grid.csv"))
# recompute per-obs SR proxy from net_sharpe/sqrt(252)
sr_trials = (grid["net_sharpe"] / np.sqrt(252)).values
net, posx, tr, *_ = trade_series("US500", "US30", 2.0, 0.5)
nz = net[net != 0]; sr_obs = nz.mean() / nz.std()
from scipy import stats as sps
dsr, star = st.deflated_sharpe(sr_trials, sr_obs, len(nz),
                               float(sps.skew(nz.values)), float(sps.kurtosis(nz.values, fisher=False)))
print(f"\n=== DSR (N=96 trials) at US500/US30 best: DSR={dsr:.3f}  sr_star(per-obs)={star:.4f}  "
      f"sr_obs(per-obs)={sr_obs:.4f} ===")
print("NOTE: daily HAC t is inflated by ~80-day holds (N_eff = n_trades, not n_days).")
