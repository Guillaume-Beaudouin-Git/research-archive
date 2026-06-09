"""Announcement-premium falsification study per HYPOTHESIS.md (frozen 2026-06-10, 88cc29e).

Reads dataset_daily.csv (built by build_dataset.py), evaluates pre-registered gates
K1-K5 + DSR, writes results.json. No parameter was chosen after seeing returns.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

OUT = Path(__file__).resolve().parent

SPREAD_RT_BASE = 8e-4                  # 8 bps round-trip, frozen base
SPREAD_RT_SENS = (6e-4, 10e-4)         # frozen sensitivity, K4 re-stated only
SWAP_LONG_PER_NIGHT = 3.08e-4          # US500 long pays 3.08 bps/night (L30-verified)
HAC_LAGS = 6
N_TRIALS_REGISTRY = 101                # 97 program base + 4 trials here (pooled,FOMC,CPI,NFP)
SE0_PROGRAM_ANN = 0.845                # funnel pre-registered cross-trial SR dispersion
PPY = 252
EULER_GAMMA = 0.5772156649
TYPES = ("FOMC", "CPI", "NFP")
BLOCKS = (("<=2015", None, "2015-12-31"), ("2016-2020", "2016-01-01", "2020-12-31"),
          (">=2021", "2021-01-01", None))


def hac_event_regression(r_excess: pd.Series, dummy: pd.Series) -> dict:
    """OLS r_excess = a + b*dummy with Newey-West lag-6; returns b, t, p, group means."""
    x = sm.add_constant(dummy.astype(float).to_numpy())
    fit = sm.OLS(r_excess.to_numpy(), x, missing="drop").fit(
        cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    return {
        "beta_bps": float(fit.params[1] * 1e4),
        "t_hac": float(fit.tvalues[1]),
        "p_raw": float(fit.pvalues[1]),
        "mean_event_bps": float(r_excess[dummy].mean() * 1e4),
        "mean_nonevent_bps": float(r_excess[~dummy].mean() * 1e4),
        "n_event": int(dummy.sum()),
        "n_total": int(dummy.notna().sum()),
    }


def sidak(p_raw: float, m: int = 4) -> float:
    return float(1.0 - (1.0 - p_raw) ** m)


def ann_sharpe(daily: pd.Series) -> float:
    sd = daily.std(ddof=1)
    return float(daily.mean() / sd * np.sqrt(PPY)) if sd > 1e-12 else 0.0


def deflated_sharpe(daily: pd.Series, n_trials: int, sigma_trials_daily: float) -> dict:
    """Bailey-LdP DSR in daily units (HYPOTHESIS section 7)."""
    r = daily.dropna()
    t_obs = len(r)
    sr_d = float(r.mean() / r.std(ddof=1))
    g3 = float(stats.skew(r))
    g4 = float(stats.kurtosis(r, fisher=False))
    emax = ((1 - EULER_GAMMA) * stats.norm.ppf(1 - 1 / n_trials)
            + EULER_GAMMA * stats.norm.ppf(1 - 1 / (n_trials * np.e)))
    sr0_d = sigma_trials_daily * emax
    denom = np.sqrt(max(1e-12, 1 - g3 * sr_d + (g4 - 1) / 4 * sr_d**2))
    z = (sr_d - sr0_d) * np.sqrt(t_obs - 1) / denom
    return {"sr_ann": round(sr_d * np.sqrt(PPY), 4), "sr0_ann": round(sr0_d * np.sqrt(PPY), 4),
            "dsr": float(stats.norm.cdf(z)), "skew": round(g3, 3), "kurt_raw": round(g4, 2),
            "t_obs": t_obs}


def strategy_net(df: pd.DataFrame, spread_rt: float) -> pd.Series:
    cost = spread_rt + SWAP_LONG_PER_NIGHT * df["nights"]
    return df["is_event"].astype(float) * (df["ret"] - cost)


def main() -> None:
    df = pd.read_csv(OUT / "dataset_daily.csv", parse_dates=["date"])
    df = df.dropna(subset=["ret", "rf"]).reset_index(drop=True)
    df["r_excess"] = df["ret"] - df["rf"]
    years = (df["date"].iloc[-1] - df["date"].iloc[0]).days / 365.25

    res: dict = {"sample": [str(df["date"].iloc[0].date()), str(df["date"].iloc[-1].date())],
                 "n_days": int(len(df)), "years": round(years, 2)}

    # ---------- K1 + per-type table (4 registry trials) ----------
    pooled = hac_event_regression(df["r_excess"], df["is_event"])
    pooled["p_sidak4"] = sidak(pooled["p_raw"])
    res["K1_pooled"] = pooled
    res["per_type"] = {}
    for t in TYPES:
        col = f"is_{t.lower()}"
        others = [f"is_{u.lower()}" for u in TYPES if u != t]
        sub = df[df[col] | ~df[others].any(axis=1)]           # type days vs clean non-event
        r = hac_event_regression(sub["r_excess"], sub[col])
        r["p_sidak4"] = sidak(r["p_raw"])
        res["per_type"][t] = r
    res["K1_pass"] = bool(pooled["t_hac"] >= 2.5)

    # ---------- K2 alpha-vs-beta ----------
    w_bar = df["is_event"].mean()
    strat = strategy_net(df, SPREAD_RT_BASE)
    bench = w_bar * (df["ret"] - SWAP_LONG_PER_NIGHT * df["nights"])
    res["K2"] = {"w_bar": round(float(w_bar), 4),
                 "sr_strategy_net": round(ann_sharpe(strat), 3),
                 "sr_benchmark_net": round(ann_sharpe(bench), 3)}
    res["K2_pass"] = bool(res["K2"]["sr_strategy_net"] > res["K2"]["sr_benchmark_net"])

    # ---------- K3 sub-periods (blocks frozen; empties declared) ----------
    res["K3_blocks"] = {}
    for name, lo, hi in BLOCKS:
        m = pd.Series(True, index=df.index)
        if lo:
            m &= df["date"] >= lo
        if hi:
            m &= df["date"] <= hi
        sub = df[m]
        if len(sub) < 60 or sub["is_event"].sum() < 5:
            res["K3_blocks"][name] = {"status": "EMPTY (no price+calendar overlap)",
                                      "n_days": int(len(sub))}
            continue
        r = hac_event_regression(sub["r_excess"], sub["is_event"])
        r["status"] = "evaluated"
        res["K3_blocks"][name] = r
    recent = res["K3_blocks"][">=2021"]
    sign_ok = np.sign(recent.get("beta_bps", 0)) == np.sign(pooled["beta_bps"])
    res["K3_pass"] = bool(recent.get("status") == "evaluated"
                          and recent["t_hac"] >= 1.0 and sign_ok)

    # ---------- K4 net vs 2x cost drag (+ frozen sensitivities) ----------
    res["K4"] = {}
    for sp in (SPREAD_RT_BASE, *SPREAD_RT_SENS):
        s = strategy_net(df, sp)
        cost_daily = df["is_event"].astype(float) * (sp + SWAP_LONG_PER_NIGHT * df["nights"])
        ann_net = float(s.mean() * PPY)
        ann_cost = float(cost_daily.mean() * PPY)
        res["K4"][f"spread_{sp*1e4:.0f}bps"] = {
            "ann_net_pct": round(ann_net * 100, 2), "ann_cost_pct": round(ann_cost * 100, 2),
            "ann_gross_pct": round((ann_net + ann_cost) * 100, 2),
            "pass": bool(ann_net >= 2 * ann_cost)}
    res["K4_pass"] = res["K4"][f"spread_{SPREAD_RT_BASE*1e4:.0f}bps"]["pass"]

    # ---------- K5 concentration ----------
    contrib = {t: float(df.loc[df[f"is_{t.lower()}"], "r_excess"].sum()) for t in TYPES}
    dominant = max(contrib, key=lambda k: contrib[k])
    rest = df[~df[f"is_{dominant.lower()}"]]
    beta_rest = hac_event_regression(rest["r_excess"], rest["is_event"])
    n_dom = int(df[f"is_{dominant.lower()}"].sum())
    res["K5"] = {"contribution_sum_excess_bps": {k: round(v * 1e4, 1) for k, v in contrib.items()},
                 "dominant_type": dominant, "n_dominant": n_dom,
                 "beta_rest_bps": beta_rest["beta_bps"], "t_rest": beta_rest["t_hac"]}
    res["K5_pass"] = not (beta_rest["beta_bps"] <= 0 and n_dom < 40)

    # ---------- DSR (both frozen conventions) ----------
    res["DSR_program"] = deflated_sharpe(strat, N_TRIALS_REGISTRY,
                                         SE0_PROGRAM_ANN / np.sqrt(PPY))
    sr_d = strat.mean() / strat.std(ddof=1)
    sigma_null = float(np.sqrt((1 + sr_d**2 / 2) / len(strat)))
    res["DSR_within_study"] = deflated_sharpe(strat, N_TRIALS_REGISTRY, sigma_null)
    res["DSR_pass"] = bool(res["DSR_program"]["dsr"] > 0.95)

    # ---------- verdict ----------
    gates = {k: res[f"{k}_pass"] for k in ("K1", "K2", "K3", "K4", "K5")}
    res["gates"] = gates
    res["verdict"] = "GO" if all(gates.values()) and res["DSR_pass"] else "NO-GO"
    res["n_trials_registry"] = {"base": 97, "this_study": 4, "cumulative": N_TRIALS_REGISTRY}

    # context for the report (diagnostics, not gates)
    ev = df[df["is_event"]]
    res["context"] = {
        "event_day_winrate": round(float((ev["ret"] > 0).mean()), 3),
        "mean_nights_event": round(float(ev["nights"].mean()), 2),
        "events_per_year": round(float(len(ev) / years), 1),
        "ann_vol_event_days_pct": round(float(ev["ret"].std(ddof=1) * np.sqrt(PPY) * 100), 1),
        "mean_rf_bps_per_day": round(float(df["rf"].mean() * 1e4), 2),
    }

    (OUT / "results.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
