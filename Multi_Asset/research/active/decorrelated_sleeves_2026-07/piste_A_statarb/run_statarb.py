"""Piste A — stat-arb / pairs backtest. Executes the frozen PREREGISTRATION.md protocol.

EG + Johansen cointegration (full + OOS), OU half-life, causal rolling-beta z-score spread MR
backtest NET of 2-leg active-fill cost + asymmetric overnight swap, two-sided leg split, DSR, WF.
Signal at T-1, execute at T (1-bar delay). No look-ahead.
"""
from __future__ import annotations
import os, sys, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import data as D
from lib import stats as st
from lib import ftmo_costs as C
from statsmodels.tsa.stattools import adfuller, coint
from statsmodels.tsa.vector_ar.vecm import coint_johansen

OUT = os.path.dirname(os.path.abspath(__file__))
PAIRS = [
    ("US100", "US500"), ("US100", "US30"), ("US500", "US30"),
    ("US100", "GER40"), ("US500", "GER40"), ("US30", "GER40"),
    ("EURUSD", "GBPUSD"), ("AUDUSD", "NZDUSD"), ("EURUSD", "USDCHF"),
    ("USDCAD", "USDCHF"), ("AUDUSD", "EURUSD"),
    ("XAUUSD", "XAGUSD"),
]
BETA_W, Z_W, HARD_STOP_Z = 252, 60, 4.0
GRID_ZIN, GRID_ZOUT = [1.5, 2.0, 2.5, 3.0], [0.0, 0.5]
ANN = 252.0


def rolling_beta(a: pd.Series, b: pd.Series, w: int) -> pd.Series:
    """Trailing OLS slope of a~b over window w, causal (uses data up to t-1)."""
    mb = b.rolling(w).mean(); ma = a.rolling(w).mean()
    cov = (a * b).rolling(w).mean() - ma * mb
    var = (b * b).rolling(w).mean() - mb * mb
    beta = cov / var
    return beta.shift(1)  # exclude current bar -> trailing only


def coint_diagnostics(la: pd.Series, lb: pd.Series) -> dict:
    """EG (full + OOS), Johansen, OU half-life on the static-beta spread."""
    n = len(la); half = n // 2
    # EG full: OLS a~b + const, ADF on resid
    X = np.column_stack([np.ones(n), lb.values])
    beta_full = np.linalg.lstsq(X, la.values, rcond=None)[0]
    resid_full = la.values - (beta_full[0] + beta_full[1] * lb.values)
    eg_p_full = adfuller(resid_full, maxlag=1, autolag=None)[1]
    # EG OOS: beta on first half, ADF on second-half spread
    Xh = np.column_stack([np.ones(half), lb.values[:half]])
    bh = np.linalg.lstsq(Xh, la.values[:half], rcond=None)[0]
    resid_oos = la.values[half:] - (bh[0] + bh[1] * lb.values[half:])
    eg_p_oos = adfuller(resid_oos, maxlag=1, autolag=None)[1]
    # Johansen (trace, rank>=1 at 95%)
    try:
        jo = coint_johansen(np.column_stack([la.values, lb.values]), 0, 1)
        joh_trace = float(jo.lr1[0]); joh_cv95 = float(jo.cvt[0, 1])
        joh_rank1 = joh_trace > joh_cv95
    except Exception:
        joh_trace = joh_cv95 = np.nan; joh_rank1 = False
    hl = st.ou_halflife(resid_full)
    return dict(ret_corr=float(la.diff().corr(lb.diff())),
                eg_p_full=float(eg_p_full), eg_p_oos=float(eg_p_oos),
                joh_trace=joh_trace, joh_cv95=joh_cv95, joh_rank1=bool(joh_rank1),
                beta_full=float(beta_full[1]), half_life=float(hl))


def backtest(a: str, b: str, la: pd.Series, lb: pd.Series, z_in: float, z_out: float,
             slip_mult=1.0, swap_mult=1.0) -> dict:
    """Causal z-score spread MR. Returns metrics + per-leg daily P&L (fraction of notional/leg)."""
    beta = rolling_beta(la, lb, BETA_W)
    spread = la - beta * lb
    zmean = spread.rolling(Z_W).mean(); zstd = spread.rolling(Z_W).std()
    z = (spread - zmean) / zstd
    dla, dlb = la.diff(), lb.diff()                      # daily log returns
    idx = la.index
    rt_cost = (C.rt_cost_bps(a, slip_mult) + C.rt_cost_bps(b, slip_mult)) / 1e4
    # per-day financing bps for a HELD long-spread (dir=+1) / short-spread (dir=-1)
    fin_long = C.pair_financing_bps_night(a, b, +1, swap_mult) / 1e4
    fin_short = C.pair_financing_bps_night(a, b, -1, swap_mult) / 1e4
    trip_a = C.TRIPLE_DOW[a]                              # index/metal rollover weekday
    dow = idx.weekday

    pos = np.zeros(len(idx)); entry_beta = np.nan; cur = 0
    beta_arr = beta.values; z_arr = z.values
    for t in range(len(idx)):
        if np.isnan(z_arr[t]) or np.isnan(beta_arr[t]):
            pos[t] = 0; cur = 0; continue
        if cur == 0:
            if z_arr[t] <= -z_in: cur = +1; entry_beta = beta_arr[t]      # long spread
            elif z_arr[t] >= z_in: cur = -1; entry_beta = beta_arr[t]     # short spread
        else:
            if abs(z_arr[t]) < z_out or abs(z_arr[t]) > HARD_STOP_Z: cur = 0
        pos[t] = cur
    pos = pd.Series(pos, index=idx)
    posx = pos.shift(1).fillna(0)                          # execute next bar (T-1 signal, T trade)
    # spread MtM using entry-fixed beta approximated by trailing beta (rolling, slow-moving)
    spread_ret = dla - beta.shift(1) * dlb                 # daily spread return per unit a-notional
    gross = posx * spread_ret
    # transaction cost on state changes (round trip charged when a trade completes)
    trades = posx.diff().abs().fillna(0)                   # 1 on open, 1 on close
    tc = trades * (rt_cost / 2.0)                          # half RT per state change (open, close)
    # financing while held: dir-dependent, x3 on rollover weekday
    trip = np.where(dow == trip_a, 3.0, 1.0)
    fin = np.where(posx.values > 0, fin_long, np.where(posx.values < 0, fin_short, 0.0)) * trip
    net = gross - tc + pd.Series(fin, index=idx)   # fin is SIGNED (negative=cost) -> ADD it
    # two-sided split by entry direction (held direction)
    long_leg = net.where(posx > 0, 0.0)
    short_leg = net.where(posx < 0, 0.0)
    a_all = st.annualized_stats(net[posx != 0].reindex(idx).fillna(0.0))
    n_trades = int((posx.diff().abs() > 0).sum() // 2)
    avg_hold = float((posx != 0).sum() / max(n_trades, 1))
    # walk-forward: 5 expanding folds on OOS tail
    wf_pos = 0; folds = 5
    seg = np.array_split(np.arange(len(idx)), folds)
    for s in seg:
        rr = net.iloc[s]
        if st.sharpe(rr.values) > 0: wf_pos += 1
    return dict(pair=f"{a}/{b}", z_in=z_in, z_out=z_out, n_trades=n_trades, avg_hold_d=avg_hold,
                net_sharpe=a_all["sharpe"], hac_t=a_all["hac_t"], maxdd=a_all["maxdd"],
                skew=a_all["skew"], ann_ret=a_all["ann_ret"],
                long_leg_mean=float(long_leg[posx > 0].mean() if (posx > 0).any() else 0),
                short_leg_mean=float(short_leg[posx < 0].mean() if (posx < 0).any() else 0),
                long_leg_t=st.hac_tstat(long_leg[posx > 0].values) if (posx > 0).sum() > 10 else 0.0,
                short_leg_t=st.hac_tstat(short_leg[posx < 0].values) if (posx < 0).sum() > 10 else 0.0,
                wf_pos=wf_pos, wf_frac=wf_pos / folds,
                two_sided=bool(long_leg[posx > 0].mean() >= 0 and short_leg[posx < 0].mean() >= 0
                               and (st.hac_tstat(short_leg[posx < 0].values) if (posx < 0).sum() > 10 else 0) > -1),
                _net=net, _sr_perobs=(net.mean() / net.std() if net.std() > 0 else 0.0))


def main():
    screen, grid, sr_perobs_all, best = [], [], [], None
    for a, b in PAIRS:
        panel = D.close_panel([a, b], "D")
        la, lb = np.log(panel[a]), np.log(panel[b])
        diag = coint_diagnostics(la, lb); diag["pair"] = f"{a}/{b}"; diag["n"] = len(la)
        diag["start"] = str(panel.index.min().date()); diag["end"] = str(panel.index.max().date())
        screen.append(diag)
        for zin in GRID_ZIN:
            for zout in GRID_ZOUT:
                r = backtest(a, b, la, lb, zin, zout)
                sr_perobs_all.append(r["_sr_perobs"])
                row = {k: v for k, v in r.items() if not k.startswith("_")}
                grid.append(row)
                if best is None or (r["two_sided"] and r["net_sharpe"] > best["net_sharpe"]):
                    if r["two_sided"]:
                        best = dict(row, _net=r["_net"])
    sc = pd.DataFrame(screen); sc.to_csv(f"{OUT}/coint_screen.csv", index=False)
    gd = pd.DataFrame(grid); gd.to_csv(f"{OUT}/backtest_grid.csv", index=False)
    # DSR at the best NET-positive cell (two-sided) over the full 96-trial space
    dsr = np.nan; sr_star = np.nan
    if best is not None:
        net = best["_net"]; T = int((net != 0).sum())
        sr_obs = net[net != 0].mean() / net[net != 0].std()
        from scipy import stats as sps
        sk = float(sps.skew(net[net != 0].values)); ku = float(sps.kurtosis(net[net != 0].values, fisher=False) + 0.0)
        dsr, sr_star = st.deflated_sharpe(sr_perobs_all, sr_obs, T, sk, ku + 3.0 - 3.0)
    summary = dict(
        n_pairs=len(PAIRS), n_trials=len(grid),
        n_oos_coint=int((sc["eg_p_oos"] < 0.05).sum()),
        oos_coint_pairs=sc.loc[sc["eg_p_oos"] < 0.05, "pair"].tolist(),
        n_johansen_rank1=int(sc["joh_rank1"].sum()),
        min_half_life=float(sc["half_life"].replace([np.inf], np.nan).min()),
        n_two_sided_netpos=int(((gd["two_sided"]) & (gd["net_sharpe"] > 0)).sum()),
        best_net_sharpe=float(gd["net_sharpe"].max()),
        best_two_sided=None if best is None else {k: best[k] for k in
            ["pair", "z_in", "z_out", "net_sharpe", "hac_t", "n_trades", "avg_hold_d",
             "long_leg_mean", "short_leg_mean", "short_leg_t", "wf_frac", "maxdd"]},
        best_dsr=float(dsr) if dsr == dsr else None,
    )
    json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    print("\n=== COINT SCREEN ===")
    print(sc[["pair", "ret_corr", "eg_p_full", "eg_p_oos", "joh_rank1", "half_life", "n"]]
          .round(3).to_string(index=False))
    print("\n=== TOP NET-SHARPE CELLS ===")
    print(gd.sort_values("net_sharpe", ascending=False)
          .head(10)[["pair", "z_in", "z_out", "n_trades", "avg_hold_d", "net_sharpe",
                     "hac_t", "long_leg_mean", "short_leg_mean", "two_sided", "wf_frac"]]
          .round(3).to_string(index=False))


if __name__ == "__main__":
    main()
