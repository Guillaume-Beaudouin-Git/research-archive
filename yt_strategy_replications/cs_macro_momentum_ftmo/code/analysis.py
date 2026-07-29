"""Metrics + FTMO barrier decision metric + the four pre-registered kill rules.

Statistics come from ``yt_strategy_replications/engine/stats.py`` (HAC t, DSR,
Politis-Romano stationary bootstrap, walk-forward folds) and the campaign
probabilities from ``Portfolio/admission/barrier.py`` — both read-only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from Portfolio.admission.barrier import BarrierConfig, simulate_campaign  # noqa: E402
from yt_strategy_replications.engine import stats as S                    # noqa: E402

ANN = 252.0
N_UNIVERSE = 17
BREADTH_REF = 30           # CLAUDE.md hard rule N >= 30
N_FAMILY_TRIALS = 4        # PREREGISTRATION section 8: deflate at N1 = 4, not at the global 321


def metrics(net: pd.Series, n_trials: int = N_FAMILY_TRIALS) -> dict:
    r = net.dropna()
    eq = (1.0 + r).cumprod()
    mdd, _ = S.max_drawdown(eq.to_numpy())
    sr = S.sharpe_ratio(r, ANN)
    mean, t = S.hac_tstat(r, lags=6)
    dsr = S.deflated_sharpe_ratio(r, n_trials=n_trials, periods_per_year=ANN)
    folds = S.fold_metrics(r.to_numpy(), n_folds=5, periods_per_year=ANN)
    years = len(r) / ANN
    return {
        "n_days": int(len(r)),
        "cagr": float(eq.iloc[-1] ** (1 / years) - 1) if years > 0 else np.nan,
        "vol_ann": float(r.std(ddof=1) * np.sqrt(ANN)),
        "sharpe": sr,
        "sharpe_breadth_haircut": sr * np.sqrt(N_UNIVERSE / BREADTH_REF),
        "max_dd": mdd,
        "skew": float(r.skew()),
        "kurtosis": float(r.kurtosis()),
        "hac_t": t,
        "dsr": dsr.get("dsr"),
        "wf_score": folds["wf_score"],
        "fold_sharpes": folds["fold_sharpes"],
        "worst_day": float(r.min()),
        "best_day": float(r.max()),
    }


def campaign(net: pd.Series, n_paths: int = 5000, seed: int = 7,
             mean_block: float = 10.0, scale: float = 1.0) -> dict:
    """Two-phase FTMO campaign on block-bootstrapped paths.

    Walks both phases explicitly with ``barrier._run_phase`` (the canonical
    barrier logic) so that phase-1 probability, conditional phase-2 probability,
    the daily-vs-floor death split *per phase* and the p90 of days-to-funded all
    come out of the same paths. ``simulate_campaign`` is called alongside as a
    cross-check that the walker reproduces the module's own p(pass).
    """
    from Portfolio.admission.barrier import _run_phase
    from Portfolio.admission.marginal import stationary_bootstrap_indices

    cfg = BarrierConfig()
    x = np.asarray(pd.Series(net).dropna().values, float) * float(scale)
    rng = np.random.default_rng(seed)
    horizon = 2 * cfg.horizon_days + 10
    o1c: dict[str, int] = {"pass": 0, "floor": 0, "daily": 0, "timeout": 0}
    o2c: dict[str, int] = {"pass": 0, "floor": 0, "daily": 0, "timeout": 0}
    days: list[int] = []

    for _ in range(n_paths):
        reps = int(np.ceil(horizon / x.size)) + 1
        idx = np.concatenate(
            [stationary_bootstrap_indices(x.size, mean_block, rng) for _ in range(reps)]
        )[:horizon]
        path = x[idx]
        out1, i1 = _run_phase(path, 0, cfg.target_p1, cfg, cfg.min_days_p1, cfg.max_days_p1)
        o1c[out1] += 1
        if out1 != "pass":
            continue
        out2, i2 = _run_phase(path, i1, cfg.target_p2, cfg, cfg.min_days_p2, cfg.max_days_p2)
        o2c[out2] += 1
        if out2 == "pass":
            days.append(i2)

    n = float(n_paths)
    p1 = o1c["pass"] / n
    pg = o2c["pass"] / n
    xc = simulate_campaign(net, cfg, n_paths=min(n_paths, 2000),
                           mean_block=mean_block, seed=seed, scale=scale)
    return {
        "p_pass_global": pg,
        "p_pass_phase1": p1,
        "p_pass_phase2_cond": (pg / p1) if p1 > 0 else np.nan,
        "p_fail_daily_p1": o1c["daily"] / n, "p_fail_floor_p1": o1c["floor"] / n,
        "p_timeout_p1": o1c["timeout"] / n,
        "p_fail_daily_p2": o2c["daily"] / n, "p_fail_floor_p2": o2c["floor"] / n,
        "p_timeout_p2": o2c["timeout"] / n,
        "p_fail_daily": (o1c["daily"] + o2c["daily"]) / n,
        "p_fail_floor": (o1c["floor"] + o2c["floor"]) / n,
        "p_timeout": (o1c["timeout"] + o2c["timeout"]) / n,
        "days_median": float(np.median(days)) if days else float("nan"),
        "days_p90": float(np.percentile(days, 90)) if days else float("nan"),
        "n_paths": n_paths,
        "xcheck_simulate_campaign_p": xc.p_pass,
    }


# ---------------------------------------------------------------- kill rules

def kill_placebo(net: pd.Series, **kw) -> dict:
    """Kill rule 1 — demeaned returns, same barriers, same sizing, same seed."""
    r = net.dropna()
    real = campaign(r, **kw)
    plac = campaign(r - r.mean(), **kw)
    return {"p_real": real["p_pass_global"], "p_placebo": plac["p_pass_global"],
            "beats_placebo": real["p_pass_global"] > plac["p_pass_global"],
            "days_real": real["days_median"], "days_placebo": plac["days_median"]}


def kill_two_sided(short_net: pd.Series) -> dict:
    """Kill rule 2 — L25: a real directional edge is positive on the short leg too.
    Evaluated at ZERO cost, so the verdict is about the signal, not the fee."""
    r = short_net.dropna()
    mean, t = S.hac_tstat(r, lags=6)
    p = S.stationary_bootstrap_pvalue(r.to_numpy(), n_boot=2000, mean_block=20)
    return {"mean_bps_day": float(mean * 1e4), "hac_t": float(t),
            "block_boot_p": float(p), "sharpe": S.sharpe_ratio(r, ANN),
            "significant": bool(t > 1.65 and p < 0.05)}


def kill_beta_orthogonality(net: pd.Series, index_returns: pd.DataFrame) -> dict:
    """Kill rule 3 — L38: regress on a vol-targeted buy-and-hold of the indices.
    R^2 > 30% means the sleeve is timing beta, not a new premium."""
    import statsmodels.api as sm

    bh = index_returns.mean(axis=1)
    vol = bh.rolling(63).std().shift(1) * np.sqrt(ANN)
    bh_vt = (bh * (0.10 / vol)).replace([np.inf, -np.inf], np.nan)
    df = pd.concat([net.rename("y"), bh_vt.rename("x")], axis=1).dropna()
    X = sm.add_constant(df["x"].to_numpy())
    m = sm.OLS(df["y"].to_numpy(), X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return {"beta": float(m.params[1]), "alpha_bps_day": float(m.params[0] * 1e4),
            "alpha_t": float(m.tvalues[0]), "r2": float(m.rsquared),
            "r2_over_30pct": bool(m.rsquared > 0.30), "n": int(len(df))}


def kill_gross_vs_cost(daily: pd.DataFrame, rebalance_days: pd.Series) -> dict:
    """Kill rule 4 — L43: gross per rebalance vs 1.5x the measured p95 cost."""
    grp = rebalance_days.cumsum()
    g = daily["gross"].groupby(grp).sum()
    c = (daily["cost_spread"] + daily["cost_swap"]).groupby(grp).sum()
    g, c = g.iloc[1:-1], c.iloc[1:-1]          # drop partial first/last holding period
    cp95 = float(np.percentile(c, 95))
    gm = float(g.mean())
    return {"gross_mean_bps": gm * 1e4, "cost_mean_bps": float(c.mean()) * 1e4,
            "cost_p95_bps": cp95 * 1e4, "ratio_gross_over_costp95": gm / cp95 if cp95 else np.nan,
            "passes_1p5x": bool(cp95 > 0 and gm / cp95 >= 1.5),
            "n_periods": int(len(g))}
