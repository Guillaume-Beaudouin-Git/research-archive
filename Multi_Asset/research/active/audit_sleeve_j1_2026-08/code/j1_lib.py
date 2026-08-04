"""J1 sleeve reconstruction — byte-faithful to cleanroom engine.build_signals().

Read-only against the main working dir's gitignored caches (absolute paths).
"""
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

MAIN = Path("<HOME>/Desktop/Algo_claude")
CACHE = MAIN / "data" / "ftmo_portfolio" / "cache"
AOUT = MAIN / "data" / "ftmo_portfolio" / "outputs"

RT_BPS_USDJPY_ALLIN = 1.86      # spec_v22 cost_anchors.rt_bps_legs_allin
VM_DEPLOYED = 14.0
LEG_LEV_CAP = 12.0


def load_panels():
    px = pd.read_parquet(CACHE / "panel_px.parquet")
    rets = pd.read_parquet(CACHE / "panel_rets.parquet")
    sL = pd.read_parquet(CACHE / "panel_swapL.parquet")
    sS = pd.read_parquet(CACHE / "panel_swapS.parquet")
    mu = pd.read_parquet(CACHE / "panel_mult.parquet")
    rt = pd.read_csv(AOUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0]
    return px, rets, sL, sS, mu, rt


def _rv(ret, window=60):
    """Identical to engine._rv."""
    return ret.rolling(window, min_periods=max(20, window // 3)).std() * np.sqrt(252)


def j1_weights(px, rets, side="long"):
    """Reproduce engine.build_signals() J1 block. side in {long, short, uncond}.

    long   : w = 1{mom>0} * volscale        (THE DEPLOYED SLEEVE)
    short  : w = -1{mom<0} * volscale       (DISJOINT leg, L25)
    uncond : w = volscale                   (always-long benchmark, L38/L58)
    """
    pj = px["USDJPY"].dropna()
    mom = pj.shift(21) / pj.shift(252) - 1.0
    rvj = _rv(rets["USDJPY"]).clip(lower=1e-4)
    vs = (0.10 / rvj).clip(upper=5.0)
    mom = mom.reindex(rvj.index)
    if side == "long":
        s = (mom > 0).astype(float)
    elif side == "short":
        s = -(mom < 0).astype(float)
    elif side == "uncond":
        s = pd.Series(1.0, index=rvj.index)
    else:
        raise ValueError(side)
    return (s * vs).shift(1).clip(-1.5, 1.5)


def sleeve_returns(px, rets, sL, sS, mu, side="long", cost_rt_bps=0.0, swaps=True):
    """Daily sleeve return at RESEARCH scale (weight as produced, no vm)."""
    w = j1_weights(px, rets, side)
    r = rets["USDJPY"]
    gross = (w * r).fillna(0.0)
    out = gross.copy()
    if cost_rt_bps:
        out = out - (w.diff().abs() * (cost_rt_bps / 2.0 / 1e4)).fillna(0.0)
    if swaps:
        bps = np.where(w > 0, sL["USDJPY"], np.where(w < 0, sS["USDJPY"], 0.0))
        out = out + (w.abs() * pd.Series(bps, index=w.index) / 1e4
                     * mu["USDJPY"]).fillna(0.0)
    return gross.rename("gross"), out.rename("net"), w.rename("w")


# ------------------------------------------------------------------ stats
def sharpe(r, ppy=252):
    r = pd.Series(r).dropna()
    sd = r.std(ddof=1)
    return float(r.mean() / sd * np.sqrt(ppy)) if sd > 0 else float("nan")


def t_hac(r, lags=6):
    r = pd.Series(r).dropna()
    X = np.ones((len(r), 1))
    m = sm.OLS(r.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(m.tvalues[0])


def hac_reg(y, X, lags=6):
    """OLS with HAC(lags). X = DataFrame of regressors (const added)."""
    d = pd.concat([y.rename("y"), X], axis=1).dropna()
    Xc = sm.add_constant(d.drop(columns="y"))
    m = sm.OLS(d["y"].values, Xc.values).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return m, Xc.columns.tolist(), d


def block_bootstrap_ci(r, stat, n=2000, mean_block=10.0, seed=0, ppy=252):
    """Stationary (Politis-Romano) block bootstrap CI of `stat`."""
    rng = np.random.default_rng(seed)
    r = np.asarray(pd.Series(r).dropna().values, float)
    n_obs = len(r)
    p = 1.0 / mean_block
    out = []
    for _ in range(n):
        idx = np.empty(n_obs, dtype=int)
        i = rng.integers(n_obs)
        for k in range(n_obs):
            idx[k] = i
            if rng.random() < p:
                i = rng.integers(n_obs)
            else:
                i = (i + 1) % n_obs
        out.append(stat(r[idx]))
    out = np.asarray(out, float)
    return float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))
