"""Evaluation engine — copy of top10_test/framework.py + the defect-1 and
defect-4 switches.

Defect 1 (DSR): the funnel's `deflated_sharpe` compares an ANNUALISED Sharpe to
E[max SR] expressed in units of sigma_SR, having implicitly set sigma_SR = 1.0.
At n_trials = 142 the benchmark is 2.57 "annualised Sharpe", which no daily
strategy can reach -> dsr lands at -12 .. -32 for every candidate. The repaired
path calls the repo-root dsr.py with an explicitly declared trial dispersion.

Defect 4 (floor): FTMO 2-step Max Loss is STATIC at -10% of the INITIAL balance
(rules.md; the EOD-high-watermarked ratchet is the 1-step product, discarded
twice in this repo). The funnel ratchets, which penalises WINNING paths only.
"""
from __future__ import annotations

import math
import sys
import warnings
from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd

sys.path.insert(0, "<HOME>/Desktop/Algo_claude")
from dsr import deflated_sharpe_ratio, estimate_std_sr_trials, DSRCalibrationWarning  # noqa

FTMO_DLL_PCT = 0.05
FTMO_MLL_PCT = 0.10
FTMO_P1_TARGET = 0.10
FTMO_P2_TARGET = 0.05


# ------------------------------------------------- funnel stats, verbatim ---

def hac_tstat(x, lag: int = 6) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < lag + 5:
        return float("nan")
    mean = x.mean()
    c = x - mean
    s = (c ** 2).sum() / n
    for k in range(1, lag + 1):
        w = 1.0 - k / (lag + 1.0)
        s += 2.0 * w * (c[k:] * c[:-k]).sum() / n
    if s <= 0:
        return float("nan")
    se = math.sqrt(s / n)
    return mean / se if se > 0 else float("nan")


def block_bootstrap_sharpe(returns, n_boot: int = 1000, block_len: int = 5,
                           n_per_year: int = 252, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < block_len * 3:
        return {"sr_mean": np.nan, "sr_lo95": np.nan, "sr_hi95": np.nan,
                "sr_std": np.nan, "n_boot": 0}
    n_blocks = max(1, n // block_len + 1)
    st = rng.integers(0, n, size=(n_boot, n_blocks))
    idx = np.clip((st[:, :, None] + np.arange(block_len)[None, None, :])
                  .reshape(n_boot, -1)[:, :n], 0, n - 1)
    boot = r[idx]
    sd = boot.std(ddof=1, axis=1)
    sharpes = (boot.mean(axis=1) / np.where(sd > 0, sd, np.nan)
               * math.sqrt(n_per_year))
    sharpes = sharpes[np.isfinite(sharpes)]
    return {"sr_mean": float(sharpes.mean()),
            "sr_lo95": float(np.percentile(sharpes, 2.5)),
            "sr_hi95": float(np.percentile(sharpes, 97.5)),
            "sr_std": float(sharpes.std(ddof=1)), "n_boot": int(len(sharpes))}


def deflated_sharpe_broken(sr, t_obs, n_trials=1, skew=0.0, kurt=3.0) -> dict:
    """VERBATIM copy of framework.py:118 — the defective version."""
    if t_obs < 30 or not np.isfinite(sr):
        return {"dsr": np.nan, "dsr_threshold": np.nan, "dsr_passes": False}
    emc = 0.5772156649
    thr = math.sqrt(2.0 * math.log(max(2, n_trials))) * (
        1.0 - emc / math.sqrt(2.0 * math.log(max(2, n_trials))))
    sig = math.sqrt((1 - skew * sr + (kurt - 1) / 4.0 * sr * sr) / (t_obs - 1))
    if sig <= 0:
        return {"dsr": np.nan, "dsr_threshold": np.nan, "dsr_passes": False}
    d = (sr - thr) / sig
    return {"dsr": float(d), "dsr_threshold": float(thr), "dsr_passes": bool(d > 0.95)}


def walk_forward_folds(returns: pd.Series, n_folds: int = 5,
                       min_train_years: float = 2.0, n_per_year: int = 252) -> list:
    r = returns.dropna()
    n = len(r)
    min_train = int(min_train_years * n_per_year)
    if n < min_train + n_folds * 50:
        return []
    test_size = max(50, (n - min_train) // n_folds)
    folds = []
    for i in range(n_folds):
        train_end = min_train + i * test_size
        test_end = min(train_end + test_size, n)
        if test_end - train_end < 30:
            break
        srt = _sharpe(r.iloc[:train_end].values, n_per_year)
        srs = _sharpe(r.iloc[train_end:test_end].values, n_per_year)
        folds.append({"fold": i + 1, "sr_train": srt, "sr_test": srs,
                      "sign_consistent": (srt > 0) == (srs > 0)})
    return folds


def _sharpe(r, n_per_year: int = 252) -> float:
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 30:
        return float("nan")
    sd = r.std(ddof=1)
    return float(r.mean() / sd * math.sqrt(n_per_year)) if sd > 0 else float("nan")


def max_drawdown_pct(equity) -> float:
    e = np.asarray(equity, dtype=float)
    if len(e) == 0:
        return 0.0
    hwm = np.maximum.accumulate(e)
    return float(((e - hwm) / hwm).min())


def amtp_bonferroni(t_stats, alpha: float = 0.05) -> list:
    from scipy.stats import norm
    n = len([t for t in t_stats if np.isfinite(t)])
    if n == 0:
        return [np.nan] * len(t_stats)
    return [np.nan if not np.isfinite(t)
            else min(1.0, 2.0 * (1.0 - norm.cdf(abs(t))) * n) for t in t_stats]


def vol_target(returns: pd.Series, target_annual: float = 0.08, lookback: int = 63,
               n_per_year: int = 252, max_lev: float = 5.0) -> pd.Series:
    vol = returns.rolling(lookback, min_periods=20).std(ddof=1) * math.sqrt(n_per_year)
    lev = (target_annual / vol).clip(upper=max_lev).shift(1)
    return returns * lev


def load_rf_daily() -> pd.Series:
    """The funnel's four candidate paths are all absent (verified 2026-08-13), so
    the funnel ran on this flat 2%/yr fallback. Reproduced exactly."""
    idx = pd.date_range("2010-01-01", "2027-01-01", freq="B")
    return pd.Series(0.02 / 252.0, index=idx, name="rf_daily")


# -------------------------------------------------- FTMO MC, floor switch ---

@dataclass
class FTMOResult:
    p_pass_p1: float = 0.0
    p_pass_p1_p2: float = 0.0
    p_bust_dll: float = 0.0
    p_bust_mll: float = 0.0
    median_days_pass_p1: float = float("nan")
    n_runs: int = 0


def _paths(pnl, rng, n_runs, max_days, block_len):
    """Stationary-block paths, (n_runs, max_days). Same construction as the
    funnel's per-run np.concatenate, vectorised."""
    n = len(pnl)
    n_blocks = max_days // block_len + 1
    st = rng.integers(0, n, size=(n_runs, n_blocks))
    idx = (st[:, :, None] + np.arange(block_len)[None, None, :]).reshape(n_runs, -1)
    idx = np.clip(idx, 0, n - 1)
    return pnl[idx][:, :max_days]


def _phase_vec(paths, target, floor_mode):
    """Returns (pass_day int array, -1 if not passed; bust code 0 none/1 dll/2 mll)."""
    n_runs, n_days = paths.shape
    eq = np.ones(n_runs)
    hwm = np.ones(n_runs)
    dll = np.full(n_runs, 1.0 - FTMO_DLL_PCT)
    alive = np.ones(n_runs, dtype=bool)
    bust = np.zeros(n_runs, dtype=np.int8)
    day_pass = np.full(n_runs, -1, dtype=np.int32)
    for d in range(n_days):
        if not alive.any():
            break
        nxt = eq * (1.0 + paths[:, d])
        hit_dll = alive & (nxt < dll)
        bust[hit_dll] = 1
        alive &= ~hit_dll
        mll = (np.maximum(1.0 - FTMO_MLL_PCT, hwm - FTMO_MLL_PCT)
               if floor_mode == "ratchet" else np.full(n_runs, 1.0 - FTMO_MLL_PCT))
        hit_mll = alive & (nxt < mll)
        bust[hit_mll] = 2
        alive &= ~hit_mll
        eq = np.where(alive, nxt, eq)
        hwm = np.maximum(hwm, eq)
        dll = np.where(alive, eq - FTMO_DLL_PCT, dll)
        won = alive & (eq >= 1.0 + target)
        day_pass[won] = d + 1
        alive &= ~won
    return day_pass, bust


def ftmo_montecarlo(daily_pnl_pct: pd.Series, n_runs: int = 2000,
                    max_days_per_phase: int = 365, seed: int = 7,
                    block_len: int = 5, floor_mode: str = "ratchet") -> FTMOResult:
    rng = np.random.default_rng(seed)
    pnl = daily_pnl_pct.dropna().values
    if len(pnl) < 30:
        return FTMOResult(n_runs=0)
    p = _paths(pnl, rng, n_runs, max_days_per_phase, block_len)
    d1, b1 = _phase_vec(p, FTMO_P1_TARGET, floor_mode)
    passed1 = d1 > 0
    p2 = _paths(pnl, rng, n_runs, max_days_per_phase, block_len)
    d2, _ = _phase_vec(p2, FTMO_P2_TARGET, floor_mode)
    passed12 = passed1 & (d2 > 0)
    return FTMOResult(passed1.mean(), passed12.mean(),
                      float((b1 == 1).mean()), float((b1 == 2).mean()),
                      float(np.median(d1[passed1])) if passed1.any() else float("nan"),
                      n_runs)


# ----------------------------------------------------------- result record ---

@dataclass
class Res:
    id: str = ""
    name: str = ""
    family: str = ""
    asset_class: str = ""
    order_type: str = ""
    n_trades: int = 0
    n_days: int = 0
    n_per_year_emp: float = float("nan")
    win_rate: float = 0.0
    mean_bps_per_trade_gross: float = 0.0
    mean_bps_per_trade_net: float = 0.0
    cost_gate_ratio: float = 0.0
    sharpe_excess: float = 0.0
    max_dd_pct: float = 0.0
    hac_t_excess: float = 0.0
    bootstrap_sr_mean: float = 0.0
    bootstrap_sr_lo95: float = 0.0
    bootstrap_sr_hi95: float = 0.0
    dsr: float = float("nan")
    dsr_passes: bool = False
    wf_n_folds: int = 0
    wf_pass_rate: float = 0.0
    ftmo_p_pass_p1: float = 0.0
    ftmo_p_pass_p1_p2: float = 0.0
    ftmo_p_bust: float = 0.0
    ftmo_median_days_p1: float = float("nan")
    amtp_p_value: float = float("nan")
    research_pass: bool = False
    propfirm_pass: bool = False
    notes: str = ""


def evaluate_trades(sid, name, trades_df, rf_daily, n_trials=142,
                    dsr_fixed=False, floor_mode="ratchet",
                    std_sr_trials=None, n_boot=1000, mc_runs=2000,
                    return_series=False):
    res = Res(id=sid, name=name)
    res.n_trades = len(trades_df)
    from strategies_repaired import trades_to_daily_pnl
    if trades_df.empty or len(trades_df) < 20:
        res.notes = f"insufficient n_trades={len(trades_df)}"
        return (res, None) if return_series else res
    dmin = pd.to_datetime(trades_df["exit_date"]).min()
    dmax = pd.to_datetime(trades_df["exit_date"]).max()
    daily_pnl = trades_to_daily_pnl(trades_df, pd.date_range(dmin, dmax, freq="B"))
    bdays = pd.date_range(daily_pnl.index.min(), daily_pnl.index.max(), freq="B")
    daily_pnl = daily_pnl.reindex(bdays).fillna(0.0)
    if int((daily_pnl != 0).sum()) < 20:
        res.notes = "too sparse"
        return (res, None) if return_series else res

    wins = trades_df[trades_df["net_bps"] > 0]
    res.win_rate = len(wins) / len(trades_df)
    res.mean_bps_per_trade_gross = float(trades_df["gross_bps"].mean())
    res.mean_bps_per_trade_net = float(trades_df["net_bps"].mean())
    ct = trades_df["cost_bps"].mean() + abs(trades_df["swap_bps"].mean())
    res.cost_gate_ratio = float(abs(trades_df["gross_bps"].mean()) / ct) if ct > 0 else 0.0

    vt = vol_target(daily_pnl, target_annual=0.08, lookback=63)
    vt = vt.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    res.n_days = len(vt)
    years = (vt.index[-1] - vt.index[0]).days / 365.25
    res.n_per_year_emp = len(vt) / years if years > 0 else float("nan")

    rf = rf_daily.reindex(vt.index).fillna(0.0)
    excess = vt - rf
    res.sharpe_excess = _sharpe(excess.values, 252)
    res.hac_t_excess = hac_tstat(excess.values, lag=6)
    res.max_dd_pct = max_drawdown_pct((1 + vt).cumprod().values)

    bs = block_bootstrap_sharpe(vt.values, n_boot=n_boot, block_len=5)
    res.bootstrap_sr_mean = bs["sr_mean"]
    res.bootstrap_sr_lo95 = bs["sr_lo95"]
    res.bootstrap_sr_hi95 = bs["sr_hi95"]

    sk = float(pd.Series(vt).skew())
    ku = float(pd.Series(vt).kurtosis() + 3)
    if dsr_fixed:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DSRCalibrationWarning)
            out = deflated_sharpe_ratio(excess.values, n_trials=n_trials,
                                        periods_per_year=252, rf=0.0,
                                        std_sr_trials=std_sr_trials)
        res.dsr = out["dsr"]
        res.dsr_passes = bool(out["dsr"] >= 0.95)
    else:
        d = deflated_sharpe_broken(res.sharpe_excess, len(vt), n_trials=n_trials,
                                   skew=sk, kurt=ku)
        res.dsr = d["dsr"]
        res.dsr_passes = d["dsr_passes"]

    wf = walk_forward_folds(excess, n_folds=5, min_train_years=1.5)
    res.wf_n_folds = len(wf)
    if wf:
        res.wf_pass_rate = sum(1 for f in wf if f["sr_test"] > 0) / len(wf)

    mc = ftmo_montecarlo(vt, n_runs=mc_runs, max_days_per_phase=365,
                         floor_mode=floor_mode)
    res.ftmo_p_pass_p1 = mc.p_pass_p1
    res.ftmo_p_pass_p1_p2 = mc.p_pass_p1_p2
    res.ftmo_p_bust = mc.p_bust_dll + mc.p_bust_mll
    res.ftmo_median_days_p1 = mc.median_days_pass_p1

    res.research_pass = bool(res.sharpe_excess > 0.7 and res.max_dd_pct > -0.25
                             and res.wf_pass_rate > 0.50)
    res.propfirm_pass = bool(res.sharpe_excess > 1.0 and res.max_dd_pct > -0.10
                             and res.wf_pass_rate > 0.60)
    return (res, excess) if return_series else res
