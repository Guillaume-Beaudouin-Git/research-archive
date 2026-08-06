"""Robustness battery on the cells that came closest, in BOTH formulations.

Nothing here is a promotion. The battery exists so that a t-stat is never quoted
naked. Five orthogonal filters, each of which has already caught something in
this repo:

  P1  autocorrelation-matched placebo (sprint 2026-08-04, law 1) -- the side
      series is rotated circularly inside its own era, which preserves its
      persistence and its long/short mix and destroys only the alignment. Slow
      macro states are step functions; their effective N is the number of
      REGIMES, not the number of days, and a HAC lag-6 t cannot see that.
  P2  L38 orthogonality vs a vol-targeted buy-and-hold of the same instrument.
  P3  block bootstrap (never iid).
  P4  expanding walk-forward, 5 folds -- ORTHOGONAL to DSR (statarb 2026-08-03).
  P5  DSR with rf=0 and a declared trial dispersion.

Plus the power calculation the mission asks for, reported BEFORE any conclusion.
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")
from exog_lib import (COST_RT_BPS, GROSSMAP, MECHANISM_SIGN, POST2021,  # noqa: E402
                      SWAP_BPS, block_bootstrap_p, build_exog_panel, hac_t,
                      load_daily_panel, walk_forward)
from dsr import deflated_sharpe_ratio  # noqa: E402

from f1_held import fwd_return_bps, sides_from_rank, trailing_rank  # noqa: E402
from f2_intraday import SHAPES, hourly_local, shape_returns  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..")

# n_tests actually consumed by this study, declared for the deflation.
N_TESTS_F1 = 83          # post-2021 F1 cells that returned a result
N_TESTS_F2 = 92          # post-2021 F2 cells
N_TESTS = N_TESTS_F1 + N_TESTS_F2

# Cells promoted to the battery: the top of each formulation, declared here so
# the selection is visible rather than implicit.
CELLS = [
    ("F1", "XAUUSD", "E2_slope", 1, "quintile"),
    ("F1", "XAUUSD", "E2_slope", 5, "quintile"),
    ("F1", "USDJPY", "E4_d_dollar", 1, "median"),
    ("F2", "USDJPY", "E6_us_jpy_diff", "C_afternoon_15_17", "quintile"),
    ("F2", "USDJPY", "E6_us_jpy_diff", "C_afternoon_15_17", "median"),
    ("F2", "XAUUSD", "E5b_vix_level", "C_afternoon_15_17", "quintile"),
    ("F2", "USDJPY", "E6b_d_us_jpy_diff", "B_us_session_09_16", "quintile"),
]


def mean_run_length(side: np.ndarray) -> float:
    """Average number of consecutive days the side stays constant.

    This is the number that decides whether N is the sample size or a fiction.
    """
    s = np.asarray(side)
    if len(s) == 0:
        return np.nan
    changes = int((s[1:] != s[:-1]).sum())
    return len(s) / (changes + 1)


def placebo_matched(side: np.ndarray, r: np.ndarray, n_rot: int = 400,
                    seed: int = 11) -> dict:
    """Circular rotation of the side series inside its own sample.

    Preserves autocorrelation AND long/short mix; destroys alignment only.
    """
    rng = np.random.default_rng(seed)
    n = len(side)
    obs_mean = float(np.nanmean(side * r))
    _, obs_t = hac_t(side * r)
    ks = rng.choice(np.arange(int(n * 0.05), int(n * 0.95)), size=min(n_rot, n // 2),
                    replace=False)
    means, ts = [], []
    for k in ks:
        sr = np.roll(side, k)
        m, t = hac_t(sr * r)
        means.append(m)
        ts.append(t)
    means, ts = np.array(means), np.array(ts)
    return {
        "obs_mean_bps": round(obs_mean, 3),
        "obs_t": round(obs_t, 2),
        "placebo_mean_p50": round(float(np.nanmedian(means)), 3),
        "placebo_mean_p95": round(float(np.nanpercentile(means, 95)), 3),
        "placebo_abs_t_p50": round(float(np.nanmedian(np.abs(ts))), 2),
        "placebo_abs_t_p95": round(float(np.nanpercentile(np.abs(ts), 95)), 2),
        "p_placebo": round(float((np.abs(ts) >= abs(obs_t)).mean()), 4),
        "n_rotations": len(ks),
    }


def orthogonality(pnl: pd.Series, trade_ret: pd.Series) -> dict:
    """L38: regress the sleeve P&L on a vol-targeted ALWAYS-LONG version of the
    SAME trade shape.

    The regressor must be the cell's own return series, not the instrument's
    daily close-to-close: for a forward-H return indexed on the ENTRY date, the
    daily series is misaligned by one day and the R2 collapses to ~0 for purely
    mechanical reasons. This is the J1 audit's duty-cycle-vs-beta test.
    """
    vol = trade_ret.rolling(63).std()
    bh = (trade_ret / vol).replace([np.inf, -np.inf], np.nan)
    df = pd.concat([pnl.rename("y"), bh.rename("x")], axis=1).dropna()
    if len(df) < 100:
        return {"beta": np.nan, "R2_vs_buyhold": np.nan, "alpha_bps": np.nan, "t_alpha": np.nan}
    X = sm.add_constant(df["x"].to_numpy())
    res = sm.OLS(df["y"].to_numpy(), X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return {"beta": round(float(res.params[1]), 4),
            "R2_vs_buyhold": round(float(res.rsquared), 4),
            "alpha_bps": round(float(res.params[0]), 3),
            "t_alpha": round(float(res.tvalues[0]), 2)}


def build_cell(spec):
    """Return (dates, side, r_trade_bps, r_uncond_bps, cost, swap_per_trade, inst)."""
    kind, inst, pred, key, form = spec
    exog = build_exog_panel(shift_days=1)
    mech = MECHANISM_SIGN[inst][pred]
    if kind == "F1":
        H = key
        px, _ = load_daily_panel()
        p = px[inst].dropna()
        p = p[p.index >= "2007-01-01"]
        fr = fwd_return_bps(p, H)
        x = exog[pred].reindex(p.index).ffill(limit=5)
        side = sides_from_rank(trailing_rank(x), mech, form)
        df = pd.DataFrame({"side": side, "r": fr}).dropna()
        df = df.iloc[::H]
        swap = lambda s: H * SWAP_BPS[inst]["long" if s > 0 else "short"]
    else:
        hi, ho = SHAPES[key]
        d = hourly_local(inst)
        sh = shape_returns(d, hi, ho)
        x = exog[pred].reindex(sh.index).ffill(limit=5)
        side = sides_from_rank(trailing_rank(x), mech, form)
        df = pd.DataFrame({"side": side, "r": sh["r_bps"]}).dropna()
        swap = lambda s: 0.0
    return df, swap, inst


def main() -> None:
    warnings.simplefilter("ignore")
    px, _ = load_daily_panel()
    rows, pl_rows = [], []
    for spec in CELLS:
        kind, inst, pred, key, form = spec
        df, swapfn, _ = build_cell(spec)
        for era, m in [("post2021", df.index >= POST2021), ("pre2021", df.index < POST2021)]:
            sub = df[m]
            act = sub[sub["side"] != 0]
            if len(act) < 50:
                continue
            side = act["side"].to_numpy()
            r = act["r"].to_numpy()
            y = side * r
            yrs = (sub.index.max() - sub.index.min()).days / 365.25
            g, t = hac_t(y)
            m_all = float(sub["r"].mean())
            base = float(side.mean()) * m_all
            exc = y - base
            e, te = hac_t(exc)
            swap = np.array([swapfn(s) for s in side])
            cost = COST_RT_BPS[inst]
            net = y + swap - cost

            # --- power: minimum detectable per-trade effect at |t| = 2.5 -------
            sd = float(np.std(y, ddof=1))
            mde = 2.5 * sd / np.sqrt(len(y))

            pl = placebo_matched(side, r) if era == "post2021" else {}
            wf = walk_forward(act.index, net, n_folds=5)
            pb = block_bootstrap_p(exc, block=10)
            # DSR on the NET per-trade series, rf=0 (dsr.py default is already 0)
            ppy = len(y) / yrs
            try:
                d = deflated_sharpe_ratio(net, n_trials=N_TESTS, periods_per_year=ppy,
                                          rf=0.0, std_sr_trials=0.5)
                dsr, shp = round(d["dsr"], 4), round(d["sharpe"], 3)
            except Exception:
                dsr, shp = np.nan, np.nan

            # --- L38 on the daily P&L (F1 H=1 and F2 only; both are daily) -----
            pnl = pd.Series(net, index=act.index)
            orth = orthogonality(pnl, sub["r"])
            # duty cycle: the J1 audit's comparison point for beta
            orth["duty_cycle"] = round(float((side > 0).mean()), 3)

            rows.append(dict(
                formulation=kind, inst=inst, predictor=pred, key=str(key), form=form,
                era=era, N=len(y), freq_per_year=round(len(y) / yrs, 1),
                mean_run_len_days=round(mean_run_length(side), 1),
                gross_bps=round(g, 3), t_gross=round(t, 2),
                excess_bps=round(e, 3), t_excess=round(te, 2),
                net_bps=round(float(net.mean()), 3),
                net_ann_bps=round(float(net.mean()) * len(y) / yrs, 1),
                sd_per_trade_bps=round(sd, 1),
                MDE_bps_at_t2p5=round(mde, 2),
                powered=("YES" if abs(e) > mde else "UNDERPOWERED"),
                p_block_bootstrap=pb,
                wf_folds_pos=wf["folds_pos"], wf_fold_means=str(wf["fold_means"]),
                sharpe_net=shp, DSR=dsr, n_trials=N_TESTS,
                **{f"placebo_{k}": v for k, v in pl.items()},
                **orth))
    res = pd.DataFrame(rows)
    res.to_csv(f"{OUT}/robustness_battery.csv", index=False)
    pd.set_option("display.width", 300)
    pd.set_option("display.max_columns", 60)
    show = ["formulation", "inst", "predictor", "key", "form", "era", "N",
            "mean_run_len_days", "excess_bps", "t_excess", "MDE_bps_at_t2p5",
            "powered", "net_ann_bps", "p_block_bootstrap", "wf_folds_pos",
            "sharpe_net", "DSR", "R2_vs_buyhold", "beta", "duty_cycle"]
    print(res[show].to_string(index=False))
    print("\n--- P1 autocorrelation-matched placebo (post-2021) ---")
    pc = [c for c in res.columns if c.startswith("placebo_")]
    print(res[res.era == "post2021"][["inst", "predictor", "key", "form",
                                      "mean_run_len_days"] + pc].to_string(index=False))


if __name__ == "__main__":
    main()
