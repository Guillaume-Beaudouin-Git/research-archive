"""backwardation_oil engine — pre-registered rule per HYPOTHESIS.md (commit 41f034f).

Rule (frozen): long USOIL/UKOIL iff annualized front basis B_ann > 5%/yr, evaluated at the
last trading day of each week (T-1), position applied at the close of the first trading day
of the next week (T), held to the next application. Long-only, binary, no vol targeting.

Net P&L: ret(t) = pos(t-1)*[price_ret(t) + swap_yield(t)] - half_spread*|trade(t)|
  swap_yield(t) = (B_ann(t-1) - markup_ann)/365 * nights(t), nights=3 after a Friday.
  markup_ann calibrated once: today's curve basis minus today's measured long-swap yield.

Gates K1-K5, DSR (canonical root dsr.py, rf=0, PPY=252), stationary-bootstrap SR CI.
Usage: engine.py [--duka]  (--duka adds the Dukascopy daily-return cross-validation, slow IO)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CACHE = HERE / "cache"
sys.path.insert(0, str(ROOT))
from dsr import deflated_sharpe_ratio  # noqa: E402  (canonical Bailey-LdP module)

# ---- frozen constants (HYPOTHESIS.md) ----
THETA = 0.05
HALF_SPREAD = 3.5e-4          # 7 bps round trip
RET_CAP = 0.20                # program convention (cap |ret|, Apr-2020 negative prices)
SWAP_PTS = {"USOIL": 36.55, "UKOIL": 27.62}
POINT = 1e-3                  # digits = 3
NIGHTS_PER_YEAR = 364.0       # 7 accrual-nights/week
PPY = 252
N_TRIALS = (3, 5, 111)
STD_SR_TRIALS = 0.845         # funnel convention (annualized cross-trial SR dispersion)
K1_LO, K1_HI = "2020-02-01", "2020-04-30"
ERAS = [("pre2014", None, "2013-12-31"), ("2014_2020", "2014-01-01", "2020-12-31"),
        ("2021_2023", "2021-01-01", "2023-12-31"), ("2024plus", "2024-01-01", None)]
RNG = np.random.default_rng(20260610)


def load_eia(stem: str) -> pd.Series:
    return pd.read_parquet(CACHE / f"{stem}.parquet").iloc[:, 0]


def load_yf(name: str) -> pd.Series:
    s = pd.read_parquet(ROOT / "data" / "raw" / name)["close"].astype(float)
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s[~s.index.duplicated(keep="last")].sort_index()


def ann_sharpe(r: pd.Series) -> float:
    r = r.dropna()
    sd = r.std(ddof=1)
    return float(r.mean() / sd * np.sqrt(PPY)) if sd > 1e-14 else 0.0


def hac_t(r: pd.Series) -> float:
    r = r.dropna()
    m = sm.OLS(r.values, np.ones(len(r))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return float(m.tvalues[0])


def max_dd_additive(r: pd.Series) -> float:
    eq = r.cumsum()
    return float((eq - eq.cummax()).min())


def stationary_bootstrap_sr(r: pd.Series, n_draws: int = 1000, mean_block: int = 21) -> dict:
    x = r.dropna().values
    n = len(x)
    p = 1.0 / mean_block
    srs = np.empty(n_draws)
    for d in range(n_draws):
        idx = np.empty(n, dtype=int)
        i = RNG.integers(n)
        for t in range(n):
            idx[t] = i
            i = RNG.integers(n) if RNG.random() < p else (i + 1) % n
        b = x[idx]
        sd = b.std(ddof=1)
        srs[d] = b.mean() / sd * np.sqrt(PPY) if sd > 1e-14 else 0.0
    return {"q05": float(np.quantile(srs, 0.05)), "q50": float(np.quantile(srs, 0.50)),
            "q95": float(np.quantile(srs, 0.95))}


def build_leg(px: pd.Series, basis: pd.Series, swap_pts: float, markup_ann: float) -> pd.DataFrame:
    """Daily frame with positions, net strategy returns and always-long benchmark."""
    df = pd.DataFrame({"px": px}).dropna()
    df["b"] = basis.reindex(df.index).ffill(limit=5)
    df = df.loc[df["b"].notna()]
    df["ret"] = df["px"].pct_change().clip(-RET_CAP, RET_CAP)

    # weekly schedule: eval at last trading day of week, apply at first td of next week (close)
    wk = df.index.to_period("W")
    eval_days = df.groupby(wk).tail(1).index
    first_tds = df.groupby(wk).head(1).index.values
    target_at_eval = (df.loc[eval_days, "b"] > THETA).astype(float)
    applied = pd.Series(np.nan, index=df.index)
    for e, tgt in target_at_eval.items():
        j = np.searchsorted(first_tds, np.datetime64(e), side="right")
        if j < len(first_tds):
            applied.loc[first_tds[j]] = tgt
    df["T"] = applied.ffill().fillna(0.0)          # held target AFTER the application close
    df["pos"] = df["T"].shift(1).fillna(0.0)       # position earning day-t's return
    df["trade"] = df["T"].diff().abs().fillna(df["T"].iloc[0]).fillna(0.0)

    prev_wd = pd.Series(df.index, index=df.index).shift(1).dt.weekday
    df["nights"] = np.where(prev_wd == 4, 3.0, 1.0)
    df.loc[df.index[0], "nights"] = 0.0
    df["swap_yield"] = (df["b"].shift(1) - markup_ann) / 365.0 * df["nights"]

    df["hold_ret"] = df["ret"] + df["swap_yield"]                  # holdable daily net-of-swap return
    df["strat"] = df["pos"] * df["hold_ret"] - HALF_SPREAD * df["trade"]
    df["bench"] = df["hold_ret"]                                   # always-long, same cost model
    df.loc[df.index[0], "bench"] = df["hold_ret"].iloc[0] - HALF_SPREAD
    return df.iloc[1:]                                             # drop seed row


def leg_metrics(df: pd.DataFrame, name: str) -> dict:
    strat, bench = df["strat"], df["bench"]
    tim = float(df["pos"].mean())
    out = {
        "name": name,
        "sample": [str(df.index[0].date()), str(df.index[-1].date())],
        "n_days": int(len(df)),
        "time_in_market": tim,
        "n_round_trips": float(df["trade"].sum() / 2.0),
        "sr_net": ann_sharpe(strat),
        "hac_t": hac_t(strat),
        "ann_ret": float(strat.mean() * PPY),
        "max_dd_additive": max_dd_additive(strat),
        "sr_bench_always_long": ann_sharpe(bench),
        "ann_ret_bench": float(bench.mean() * PPY),
        "ann_ret_bench_tim_scaled": float(bench.mean() * PPY * tim),
        "swap_contrib_ann": float((df["pos"] * df["swap_yield"]).mean() * PPY),
        "spread_drag_ann": float((HALF_SPREAD * df["trade"]).mean() * PPY),
    }
    out["delta_sr_vs_beta"] = out["sr_net"] - out["sr_bench_always_long"]

    # conditional diagnostic: holdable return regressed on lagged in-regime indicator (HAC-6)
    ind = (df["b"].shift(1) > THETA).astype(float)
    X = sm.add_constant(ind.values)
    m = sm.OLS(df["hold_ret"].values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    out["regime_diff_daily"] = float(m.params[1])
    out["regime_diff_t"] = float(m.tvalues[1])

    # K1 window
    w = df.loc[K1_LO:K1_HI]
    out["k1_long_days"] = int((w["pos"] > 0).sum())
    out["k1_window_days"] = int(len(w))

    # K4 eras (sum of net daily returns, additive convention)
    eras = {}
    for ename, lo, hi in ERAS:
        seg = strat.loc[(slice(lo, hi))]
        eras[ename] = float(seg.sum())
    out["era_pnl"] = eras
    total = strat.sum()
    out["share_2021_2023"] = float(eras["2021_2023"] / total) if abs(total) > 1e-12 else None
    pre = df.loc[: "2013-12-31"]
    out["pre2014_inregime_pnl"] = float(pre.loc[pre["pos"] > 0, "strat"].sum())
    out["pre2014_inregime_days"] = int((pre["pos"] > 0).sum())
    return out


def main() -> None:
    # ---- data ----
    rclc1, rclc2, rbrte = load_eia("rclc1"), load_eia("rclc2"), load_eia("rbrte")
    px_us = load_yf("yf_CL=F_1d_ff0ed52b6e.parquet")
    px_uk = load_yf("yf_BZ=F_1d_7cbdc6a885.parquet")
    b_us = ((rclc1 / rclc2 - 1.0) * 12.0).dropna()
    b_uk = ((rbrte / px_uk - 1.0) * 12.0).dropna()

    # ---- markup calibration (today's curve vs today's measured swap) ----
    curve = json.loads((CACHE / "curve_now.json").read_text())
    p_us_now = curve["wti_front_cont"]["close"]
    b_us_now = curve["wti_basis_ann_now"]
    swap_ann_us_now = SWAP_PTS["USOIL"] * POINT * NIGHTS_PER_YEAR / p_us_now
    markup_us = b_us_now - swap_ann_us_now
    flag_markup_floor_us = markup_us < 0
    markup_us = max(markup_us, 0.0)

    t0_uk = b_uk.index[-1]
    p_uk_now = float(px_uk.loc[t0_uk])
    b_uk_now = float(b_uk.iloc[-1])
    swap_ann_uk_now = SWAP_PTS["UKOIL"] * POINT * NIGHTS_PER_YEAR / p_uk_now
    markup_uk = b_uk_now - swap_ann_uk_now
    flag_markup_floor_uk = markup_uk < 0
    markup_uk = max(markup_uk, 0.0)

    # alt calibration at last EIA date (2024-04) — sensitivity only
    t0_alt = b_us.index[-1]
    p_alt = float(px_us.reindex([t0_alt], method="ffill").iloc[0])
    markup_us_alt = max(float(b_us.loc[t0_alt]) - SWAP_PTS["USOIL"] * POINT * NIGHTS_PER_YEAR / p_alt, 0.0)

    # ---- legs ----
    us = build_leg(px_us, b_us, SWAP_PTS["USOIL"], markup_us)
    uk = build_leg(px_uk, b_uk, SWAP_PTS["UKOIL"], markup_uk)
    res_us = leg_metrics(us, "USOIL_primary")
    res_uk = leg_metrics(uk, "UKOIL_secondary")

    common = us.index.intersection(uk.index)
    sleeve = 0.5 * us.loc[common, "strat"] + 0.5 * uk.loc[common, "strat"]
    res_sleeve = {
        "name": "sleeve_50_50", "sample": [str(common[0].date()), str(common[-1].date())],
        "sr_net": ann_sharpe(sleeve), "hac_t": hac_t(sleeve),
        "ann_ret": float(sleeve.mean() * PPY), "max_dd_additive": max_dd_additive(sleeve),
    }

    # ---- sensitivities (markup x0.5 / x1.5 / alt-2024 calibration; spread x0.5 / x2) ----
    sens = {}
    for tag, mk in [("markup_x0.5", markup_us * 0.5), ("markup_x1.5", markup_us * 1.5),
                    ("markup_calib_2024-04", markup_us_alt)]:
        sens[tag] = ann_sharpe(build_leg(px_us, b_us, SWAP_PTS["USOIL"], mk)["strat"].iloc[1:])
    base = build_leg(px_us, b_us, SWAP_PTS["USOIL"], markup_us)
    for tag, mult in [("spread_x0.5", 0.5), ("spread_x2", 2.0)]:
        adj = base["strat"] + HALF_SPREAD * base["trade"] * (1.0 - mult)
        sens[tag] = ann_sharpe(adj)

    # ---- gates on the USOIL primary ----
    k1_pass = res_us["k1_long_days"] == 0
    k2_pass = res_us["delta_sr_vs_beta"] >= 0.20
    k3_standalone = res_us["sr_net"] >= 0.5
    k3_sleeve_ok = res_us["sr_net"] >= 0.3
    k4_single_episode = (res_us["share_2021_2023"] is not None and res_us["share_2021_2023"] > 0.80) \
        or res_us["pre2014_inregime_pnl"] <= 0.0

    # ---- K5 swap audit ----
    swap_bps_night_specs = SWAP_PTS["USOIL"] * POINT / p_us_now * 1e4
    swap_bps_night_model = (b_us_now - markup_us) / 365.0 * 1e4
    full_weeks = us.groupby(us.index.to_period("W"))["nights"].agg(["sum", "count"])
    week7 = full_weeks[full_weeks["count"] == 5]["sum"]
    k5 = {
        "swap_long_bps_night_specs_convention": swap_bps_night_specs,
        "swap_long_bps_night_model_at_calib": swap_bps_night_model,
        "rel_diff": abs(swap_bps_night_model - swap_bps_night_specs * 365.0 / NIGHTS_PER_YEAR)
                    / max(swap_bps_night_specs, 1e-9),
        "sign_long_credit_in_backwardation": bool(swap_bps_night_model > 0),
        "median_nights_full_week": float(week7.median()) if len(week7) else None,
        "pass": None,
    }
    k5["pass"] = bool(k5["rel_diff"] < 0.10 and k5["sign_long_credit_in_backwardation"]
                      and k5["median_nights_full_week"] == 7.0)

    # ---- DSR + bootstrap on primary ----
    dsr = {f"N{n}": deflated_sharpe_ratio(us["strat"].dropna().values, n_trials=n,
                                          periods_per_year=PPY, rf=0.0,
                                          std_sr_trials=STD_SR_TRIALS)["dsr"] for n in N_TRIALS}
    boot = stationary_bootstrap_sr(us["strat"])

    verdict = "GO"
    if not k1_pass or not k2_pass or not k3_standalone:
        verdict = "NO-GO" if (res_us["sr_net"] >= 0.3 and k3_sleeve_ok) else "NO-GO (not even sleeve)"
    if not k1_pass:
        verdict = "NO-GO (K1 tail)"
    elif verdict == "GO" and k4_single_episode:
        verdict = "WATCHLIST (K4 single-episode)"

    results = {
        "frozen_commit": "41f034f", "run_date": "2026-06-10",
        "calibration": {
            "curve_date": curve["wti_f1"]["date"], "wti_f1": curve["wti_f1"]["close"],
            "wti_f2": curve["wti_f2"]["close"], "b_ann_now_usoil": b_us_now,
            "p_usoil_now": p_us_now, "swap_long_ann_now_usoil": swap_ann_us_now,
            "markup_ann_usoil": markup_us, "markup_floored_usoil": flag_markup_floor_us,
            "b_ann_now_ukoil": b_uk_now, "t0_ukoil": str(t0_uk.date()),
            "swap_long_ann_now_ukoil": swap_ann_uk_now, "markup_ann_ukoil": markup_uk,
            "markup_floored_ukoil": flag_markup_floor_uk,
            "markup_usoil_alt_2024_04": markup_us_alt,
        },
        "usoil_primary": res_us, "ukoil_secondary": res_uk, "sleeve_50_50": res_sleeve,
        "sensitivity_sr_usoil": sens,
        "gates": {"K1_flat_feb_apr_2020": k1_pass, "K2_delta_sr_ge_0.20": k2_pass,
                  "K3_sr_ge_0.5_standalone": k3_standalone, "K3_sr_ge_0.3_sleeve": k3_sleeve_ok,
                  "K4_single_episode_flag": k4_single_episode, "K5_swap_audit": k5},
        "dsr_probabilistic_usoil": dsr,
        "bootstrap_sr_usoil": boot,
        "verdict_primary": verdict,
    }

    us.loc[K1_LO:K1_HI, ["px", "b", "pos"]].to_csv(HERE / "k1_window_2020.csv")
    us[["px", "b", "pos", "ret", "swap_yield", "strat", "bench"]].to_csv(HERE / "usoil_daily.csv")
    uk[["px", "b", "pos", "ret", "swap_yield", "strat", "bench"]].to_csv(HERE / "ukoil_daily.csv")
    (HERE / "results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))

    if "--duka" in sys.argv:
        for sym, yf_px in [("USOIL", px_us), ("UKOIL", px_uk)]:
            d = pd.read_csv(ROOT / "data" / "deep_history_utc" / f"{sym}_M1.csv",
                            usecols=["timestamp_utc", "close"])
            d["timestamp_utc"] = pd.to_datetime(d["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
            daily = d.set_index("timestamp_utc")["close"].resample("1D").last().dropna()
            daily.index = daily.index.normalize()
            a = yf_px.pct_change().clip(-RET_CAP, RET_CAP)
            b = daily.pct_change().clip(-RET_CAP, RET_CAP)
            j = pd.concat([a, b], axis=1, keys=["yf", "duka"]).dropna()
            print(f"DUKA-VALIDATION {sym}: n={len(j)}, corr={j['yf'].corr(j['duka']):.4f}, "
                  f"overlap {j.index[0].date()} -> {j.index[-1].date()}")


if __name__ == "__main__":
    main()
