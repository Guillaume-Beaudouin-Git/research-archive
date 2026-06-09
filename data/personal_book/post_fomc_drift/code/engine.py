"""Post-FOMC drift falsification engine — implements HYPOTHESIS.md (frozen 2026-06-10) verbatim.

Frozen parameters: x = 5 bps on FOMC-day d(DGS2); H in {5,10,20} panel business days;
entry close T+1; exit min(entry+H, next event entry) [supersession => non-overlap];
IEF log adjusted-close returns (B1 convention, macro_etf_panel.csv) excess of DTB3/252;
cost 1.0 bp RT per event; gates K1/K2/K3/K5 binding, K4 flag; DSR at N_trials=101.

Outputs (results/): results.json, events_H{5,10,20}.csv, summary.txt
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import kurtosis as _kurt
from scipy.stats import norm
from scipy.stats import skew as _skew

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]
RES = BASE / "results"
RES.mkdir(exist_ok=True)

X_BPS = 5.0
TOL = 1e-9
HS = (5, 10, 20)
COST_RT = 1e-4  # 1 bp round-trip per event (futures tier, frozen section 4)
N_TRIALS = 101  # 97 prior + 4 session trials (frozen section 6)
GAMMA_E = 0.5772156649015329
REGIMES = (
    ("pre2015", None, pd.Timestamp("2014-12-31")),
    ("2015-2021", pd.Timestamp("2015-01-01"), pd.Timestamp("2021-12-31")),
    ("2022+", pd.Timestamp("2022-01-01"), None),
)


def load_fred(name: str) -> pd.Series:
    df = pd.read_csv(BASE / f"data_cache/{name}.csv", na_values=["."])
    df.columns = ["date", "v"]
    df["date"] = pd.to_datetime(df["date"])
    return pd.to_numeric(df.set_index("date")["v"], errors="coerce").dropna().sort_index()


def hac_t(x: np.ndarray) -> tuple[float, float]:
    """Mean and HAC(lag-6) t-stat of a series against zero (house rule)."""
    x = np.asarray(x, float)
    if len(x) < 3 or np.std(x) == 0:
        return float(np.mean(x)) if len(x) else np.nan, np.nan
    fit = sm.OLS(x, np.ones((len(x), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return float(fit.params[0]), float(fit.tvalues[0])


def dsr(net: np.ndarray, n_trials: int) -> dict:
    """Deflated Sharpe Ratio (Bailey-LdP 2014), canonical weights:
    SR0 = sqrt(1/T) * ((1-g)*Z(1-1/N) + g*Z(1-1/(N*e))), g = Euler-Mascheroni on the
    LARGER quantile (corrects the swapped weights in edge_fomc_cycle.py::dsr)."""
    r = np.asarray(net, float)
    T = len(r)
    sr = r.mean() / r.std(ddof=1)
    g3 = float(_skew(r))
    g4 = float(_kurt(r, fisher=False))
    sr0 = math.sqrt(1.0 / T) * (
        (1 - GAMMA_E) * norm.ppf(1 - 1 / n_trials)
        + GAMMA_E * norm.ppf(1 - 1 / (n_trials * math.e))
    )
    denom = math.sqrt(max(1 - g3 * sr + (g4 - 1) / 4 * sr**2, 1e-12))
    val = float(norm.cdf((sr - sr0) * math.sqrt(T - 1) / denom))
    return {"sr_event": float(sr), "sr0_event": float(sr0), "dsr": val,
            "skew": g3, "kurt_raw": g4, "T": T, "n_trials": n_trials}


def main() -> None:
    # ---------------- data (sources frozen section 3) ----------------
    y2 = load_fred("DGS2")
    y10 = load_fred("DGS10")
    panel = (
        pd.read_csv(REPO / "data/panels/macro_etf_panel.csv", parse_dates=["Date"])
        .set_index("Date")
        .sort_index()
    )
    ief = np.log(panel["IEF"]).diff()
    tlt = np.log(panel["TLT"]).diff()
    rf = load_fred("DTB3").reindex(panel.index).ffill() / 100.0 / 252.0
    xs = (ief - rf).rename("xs")  # daily excess log return, futures P&L proxy
    pxi = panel.index

    ev = (
        pd.read_csv(BASE / "data_cache/fomc_events.csv", parse_dates=["date"])
        .sort_values("date")
        .reset_index(drop=True)
    )

    # ---------------- event mapping ----------------
    y2i = y2.index
    recs, n_drop_y2, n_drop_px = [], 0, 0
    for d, src in ev[["date", "source"]].itertuples(index=False):
        j = int(y2i.searchsorted(d))
        if j >= len(y2i) or j == 0 or pd.isna(y2.iloc[j]) or pd.isna(y2.iloc[j - 1]):
            n_drop_y2 += 1
            continue
        k = int(pxi.searchsorted(d))
        if k + 1 >= len(pxi):
            n_drop_px += 1
            continue
        d2y = (y2.iloc[j] - y2.iloc[j - 1]) * 100.0
        recs.append({"date": d, "source": src, "e_yld": y2i[j], "e_px": pxi[k],
                     "entry_pos": k + 1, "d2y_bps": float(d2y)})
    eva = pd.DataFrame(recs).drop_duplicates(subset="e_px", keep="first").reset_index(drop=True)
    eva["entry"] = pxi[eva["entry_pos"]]
    eva["gap_bd"] = eva["entry_pos"].diff()
    eva["emergency"] = eva["gap_bd"] < 20
    eva["traded"] = eva["d2y_bps"].abs() >= X_BPS - TOL
    eva["side"] = np.where(eva["traded"], -np.sign(eva["d2y_bps"]), 0.0)
    next_entry = eva["entry_pos"].shift(-1)

    xs_v = xs.values
    out_all = {}
    shared_diag = {
        "n_events_listed": int(len(ev)),
        "n_events_mapped": int(len(eva)),
        "n_dropped_missing_dgs2": n_drop_y2,
        "n_dropped_no_panel": n_drop_px,
        "n_traded": int(eva["traded"].sum()),
        "n_flat": int((~eva["traded"]).sum()),
        "ief_vs_minus_dy10_corr": float(
            pd.concat([ief, -(y10.diff().reindex(pxi))], axis=1).dropna().corr().iloc[0, 1]
        ),
        "sample_first_event": str(eva["date"].min().date()),
        "sample_last_event": str(eva["date"].max().date()),
    }

    # B1 month-end bond rally daily series — exact replication of skew_phase2_B1.py
    dend = panel.groupby(pxi.to_period("M")).cumcount(ascending=False) + 1
    b1_daily = tlt.where(dend.values <= 3, 0.0).fillna(0.0)

    for H in HS:
        e = eva.copy()
        e["exit_pos_raw"] = e["entry_pos"] + H
        e["exit_pos"] = np.minimum(e["exit_pos_raw"], next_entry.fillna(np.inf)).astype(float)
        complete = e["exit_pos"] <= len(pxi) - 1
        n_incomplete = int((~complete).sum())
        e = e[complete].copy()
        e["exit_pos"] = e["exit_pos"].astype(int)
        e["truncated"] = e["exit_pos"] < e["exit_pos_raw"]
        e["exit"] = pxi[e["exit_pos"]]
        e["gross"] = [
            s * float(np.nansum(xs_v[a + 1 : b + 1]))
            for s, a, b in zip(e["side"], e["entry_pos"], e["exit_pos"])
        ]
        e["net"] = np.where(e["traded"], e["gross"] - COST_RT, 0.0)

        t = e[e["traded"]].copy().sort_values("entry_pos").reset_index(drop=True)
        net = t["net"].values

        # K1 — pooled HAC t (windows non-overlapping by construction)
        mean_net, t_pooled = hac_t(net)
        k1 = {"mean_net_bps": mean_net * 1e4, "t_hac": t_pooled, "pass": bool(t_pooled >= 2.5)}

        # K2 — two-sided legs (L25)
        legs = {}
        for lab, sgn in (("hawkish_short", -1.0), ("dovish_long", 1.0)):
            ln = t.loc[t["side"] == sgn, "net"].values
            m, tt = hac_t(ln)
            legs[lab] = {"n": int(len(ln)), "mean_net_bps": m * 1e4, "t_hac": tt,
                         "hit": float((ln > 0).mean()) if len(ln) else np.nan}
        k2_pass = bool(
            legs["hawkish_short"]["mean_net_bps"] > 0 and legs["dovish_long"]["mean_net_bps"] > 0
        )

        # K3 — regimes (L31); binding only for buckets with >=10 traded events
        regimes, k3_binding = {}, []
        for lab, a, b in REGIMES:
            mask = pd.Series(True, index=t.index)
            if a is not None:
                mask &= t["date"] >= a
            if b is not None:
                mask &= t["date"] <= b
            rn = t.loc[mask, "net"].values
            m, tt = hac_t(rn) if len(rn) else (np.nan, np.nan)
            regimes[lab] = {"n": int(len(rn)), "mean_net_bps": (m * 1e4) if len(rn) else np.nan,
                            "t_hac": tt, "binding": bool(len(rn) >= 10)}
            if len(rn) >= 10:
                k3_binding.append(m > 0)
        k3_pass = bool(all(k3_binding)) if k3_binding else False

        # K5 — surprise-size tercile monotonicity (rank-based qcut, deterministic)
        t["tercile"] = pd.qcut(t["d2y_bps"].abs().rank(method="first"), 3,
                               labels=["T1", "T2", "T3"])
        terc = {
            lab: {"n": int((t["tercile"] == lab).sum()),
                  "mean_net_bps": float(t.loc[t["tercile"] == lab, "net"].mean() * 1e4),
                  "abs_d2y_range": [float(t.loc[t["tercile"] == lab, "d2y_bps"].abs().min()),
                                    float(t.loc[t["tercile"] == lab, "d2y_bps"].abs().max())]}
            for lab in ("T1", "T2", "T3")
        }
        m1, m2, m3 = (terc[l]["mean_net_bps"] for l in ("T1", "T2", "T3"))
        k5_pass = bool(m1 <= m2 <= m3 and m3 > m1)

        # K4 — correlation flag vs B1 month-end rally (daily, zeros on flat days)
        s_daily = pd.Series(0.0, index=pxi)
        for sgn, a, b in zip(t["side"], t["entry_pos"], t["exit_pos"]):
            s_daily.iloc[a + 1 : b + 1] = sgn * xs_v[a + 1 : b + 1]
        common = pd.concat([s_daily, b1_daily], axis=1).dropna()
        k4_corr = float(common.corr().iloc[0, 1])
        k4 = {"corr_vs_b1_month_end": k4_corr, "flag_not_diversifier": bool(k4_corr > 0.4)}

        # DSR at the updated cumulative trial count
        dsr_d = dsr(net, N_TRIALS)
        yrs = (t["date"].max() - t["date"].min()).days / 365.25
        dsr_d["events_per_year"] = float(len(t) / yrs)
        dsr_d["sr_annualized"] = float(dsr_d["sr_event"] * math.sqrt(len(t) / yrs))

        # supplementary: 5-fold chronological consistency (non-binding)
        folds = [
            {"n": int(len(f)), "mean_net_bps": float(np.mean(f) * 1e4),
             "first": str(t["date"].iloc[i0].date())}
            for f, i0 in (
                (chunk["net"].values, chunk.index[0])
                for chunk in np.array_split(t, 5)
            )
        ]
        n_pos_folds = int(sum(f["mean_net_bps"] > 0 for f in folds))

        # supplementary: calendar-only (literally prescribed source) consistency line
        cal_net = t.loc[t["source"] == "calendar", "net"].values
        cal_m, cal_t = hac_t(cal_net) if len(cal_net) > 2 else (np.nan, np.nan)

        per_regime_leg = {
            rlab: {
                leg: float(
                    t.loc[
                        (t["side"] == sgn)
                        & ((t["date"] >= (a or pd.Timestamp("1900-01-01"))))
                        & ((t["date"] <= (b or pd.Timestamp("2100-01-01")))),
                        "net",
                    ].mean()
                    * 1e4
                )
                for leg, sgn in (("hawkish_short", -1.0), ("dovish_long", 1.0))
            }
            for rlab, a, b in REGIMES
        }

        out_all[f"H{H}"] = {
            "n_traded": int(len(t)),
            "n_incomplete_dropped": n_incomplete,
            "n_truncated": int(t["truncated"].sum()),
            "K1_pooled": k1,
            "K2_legs": {**legs, "pass": k2_pass},
            "K3_regimes": {**regimes, "pass": k3_pass},
            "K4_flag": k4,
            "K5_terciles": {**terc, "pass": k5_pass},
            "DSR": dsr_d,
            "dist": {"hit": float((net > 0).mean()), "skew": float(_skew(net)),
                     "p5_bps": float(np.percentile(net, 5) * 1e4),
                     "p95_bps": float(np.percentile(net, 95) * 1e4),
                     "mean_gross_bps": float(t["gross"].mean() * 1e4)},
            "folds": {"detail": folds, "n_positive": n_pos_folds},
            "calendar_only_2018plus": {"n": int(len(cal_net)), "mean_net_bps": cal_m * 1e4 if cal_net is not None and len(cal_net) > 2 else np.nan, "t_hac": cal_t},
            "per_regime_leg_mean_net_bps": per_regime_leg,
            "all_binding_pass": bool(k1["pass"] and k2_pass and k3_pass and k5_pass),
        }

        cols = ["date", "source", "e_px", "entry", "exit", "d2y_bps", "side", "traded",
                "truncated", "emergency", "gross", "net", "tercile"]
        full = e.merge(t[["date", "tercile"]], on="date", how="left")
        full[cols].to_csv(RES / f"events_H{H}.csv", index=False)

    # ---------------- verdict (frozen section 7) ----------------
    passing = [h for h in out_all if out_all[h]["all_binding_pass"]]
    best = max(passing, key=lambda h: out_all[h]["DSR"]["dsr"]) if passing else None
    verdict = {
        "mechanism": "GO" if passing else "NO-GO",
        "passing_H": passing,
        "best_H": best,
        "deployable": bool(best and out_all[best]["DSR"]["dsr"] > 0.95),
    }
    res = {"params": {"x_bps": X_BPS, "HS": list(HS), "cost_rt": COST_RT,
                      "n_trials": N_TRIALS, "instrument": "IEF (panel adj close, log, excess DTB3)"},
           "shared": shared_diag, "per_H": out_all, "verdict": verdict}
    (RES / "results.json").write_text(json.dumps(res, indent=1, default=str))

    lines = [f"POST-FOMC DRIFT — verdict: {verdict['mechanism']}"
             f" | passing H: {passing or 'none'} | deployable: {verdict['deployable']}"]
    lines.append(f"events listed {shared_diag['n_events_listed']} mapped {shared_diag['n_events_mapped']}"
                 f" traded {shared_diag['n_traded']} flat {shared_diag['n_flat']}"
                 f" | IEF~-d(DGS10) corr {shared_diag['ief_vs_minus_dy10_corr']:.3f}")
    for H in HS:
        o = out_all[f"H{H}"]
        k1, k2, k3, k5 = o["K1_pooled"], o["K2_legs"], o["K3_regimes"], o["K5_terciles"]
        k3s = " ".join(
            "{}:{:+.0f}".format(r, k3[r]["mean_net_bps"]) for r in ("pre2015", "2015-2021", "2022+")
        )
        lines.append(
            f"H={H:2d} n={o['n_traded']:3d} | K1 {k1['mean_net_bps']:+6.1f}bps t={k1['t_hac']:+5.2f} {'P' if k1['pass'] else 'F'}"
            f" | K2 hawk {k2['hawkish_short']['mean_net_bps']:+6.1f} dove {k2['dovish_long']['mean_net_bps']:+6.1f} {'P' if k2['pass'] else 'F'}"
            f" | K3 {k3s} {'P' if k3['pass'] else 'F'}"
            f" | K5 {k5['T1']['mean_net_bps']:+.0f}/{k5['T2']['mean_net_bps']:+.0f}/{k5['T3']['mean_net_bps']:+.0f} {'P' if k5['pass'] else 'F'}"
            f" | K4corr {o['K4_flag']['corr_vs_b1_month_end']:+.3f}"
            f" | DSR {o['DSR']['dsr']:.3f} | folds+ {o['folds']['n_positive']}/5"
        )
    (RES / "summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
