"""B3 — extension de vehicule (DGS10) et test sur holdout 1990-2003.
Spec gelee : ../PREREGISTRATION_HOLDOUT.md (commit b0848b31)."""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm
from scipy.stats import norm

BASE = Path(__file__).resolve().parents[1]
HS = (5, 10, 20)
TRADE_RATE = 0.374          # taux de trade de l'etude d'origine
DUR = 7.5                   # duration IEF, mesure secondaire seulement
COST_RT_BPS = 1.0


def hac_t(x):
    x = np.asarray(x, float)
    if len(x) < 3 or np.std(x) == 0:
        return (float(np.mean(x)) if len(x) else np.nan), np.nan
    f = sm.OLS(x, np.ones((len(x), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return float(f.params[0]), float(f.tvalues[0])


def mde80(x):
    x = np.asarray(x, float)
    if len(x) < 2:
        return np.nan
    return float((norm.ppf(.975) + norm.ppf(.80)) * np.std(x, ddof=1) / math.sqrt(len(x)))


def load_yield(name):
    d = pd.read_csv(BASE / f"data/{name}.csv", na_values=["."])
    d.columns = ["date", "v"]
    d["date"] = pd.to_datetime(d["date"])
    return pd.to_numeric(d.set_index("date")["v"], errors="coerce").dropna().sort_index()


def main():
    y = load_yield("DGS10_long")
    yi = y.index
    jk = pd.read_csv(BASE / "data/shocks_fed_jk_t.csv")
    jk["date"] = pd.to_datetime(jk["start"]).dt.normalize()
    jk = jk.groupby("date", as_index=False)[["MP_pm"]].sum()
    jk["shock_bps"] = jk["MP_pm"] * 100.0

    # entree T+1 : premiere observation de rendement STRICTEMENT apres l'annonce
    rows = []
    for d, s in jk[["date", "shock_bps"]].itertuples(index=False):
        j = int(yi.searchsorted(d, side="right"))
        if j >= len(yi):
            continue
        rows.append({"date": d, "shock_bps": s, "pos": j})
    ev = pd.DataFrame(rows).drop_duplicates("pos", keep="first").reset_index(drop=True)
    nx = ev["pos"].shift(-1)

    samples = {"holdout_1990_2003": (None, "2003-12-31"),
               "vu_2004_2024": ("2004-01-01", None),
               "poole_1990_2024": (None, None)}
    out = {}
    yv = y.values

    for sname, (a, b) in samples.items():
        m = pd.Series(True, index=ev.index)
        if a: m &= ev["date"] >= a
        if b: m &= ev["date"] <= b
        e0 = ev[m].copy()
        thr = float(e0["shock_bps"].abs().quantile(1 - TRADE_RATE))
        res = {"n_events": int(len(e0)), "threshold_bps": thr}
        for H in HS:
            e = e0.copy()
            e["tr"] = e["shock_bps"].abs() >= thr - 1e-12
            e["xp"] = np.minimum(e["pos"] + H, nx.reindex(e.index).fillna(np.inf)).astype(float)
            e = e[e["xp"] <= len(yi) - 1].copy()
            e["xp"] = e["xp"].astype(int)
            dy = (yv[e["xp"].values] - yv[e["pos"].values]) * 100.0     # bps de rendement
            e["signed_drift"] = np.sign(e["shock_bps"]) * dy
            t = e[e["tr"]]
            nt = e[~e["tr"]]
            mn, tt = hac_t(t["signed_drift"].values)
            md = mde80(t["signed_drift"].values)
            mn_nt, tt_nt = hac_t(nt["signed_drift"].values)
            res[f"H{H}"] = {
                "n_traded": int(len(t)),
                "drift_bps": mn, "t_hac": tt, "mde80_bps": md,
                "ratio_effet_mde": (mn / md) if md and not np.isnan(md) else np.nan,
                "pnl_proxy_bps": mn * DUR - COST_RT_BPS,
                "controle_non_trades_bps": mn_nt, "controle_t": tt_nt,
                "n_non_trades": int(len(nt)),
            }
        out[sname] = res

    (BASE / "results").mkdir(exist_ok=True)
    json.dump(out, open(BASE / "results/results_holdout.json", "w"), indent=2, default=float)

    for sname in samples:
        r = out[sname]
        star = "  <<< TEST PRIMAIRE" if sname == "holdout_1990_2003" else ""
        print(f"\n=== {sname}  (n_evts {r['n_events']}, seuil {r['threshold_bps']:.2f} bps){star}")
        print(f"  {'H':<4}{'n':<5}{'drift bps':<12}{'t_HAC':<9}{'MDE80':<9}"
              f"{'eff/MDE':<10}{'non-trades (ctrl)':<20}")
        for H in HS:
            h = r[f"H{H}"]
            print(f"  {H:<4}{h['n_traded']:<5}{h['drift_bps']:+9.2f}   {h['t_hac']:+7.2f}  "
                  f"{h['mde80_bps']:7.2f}  {h['ratio_effet_mde']:+8.2f}  "
                  f"{h['controle_non_trades_bps']:+7.2f} (t {h['controle_t']:+5.2f}, n={h['n_non_trades']})")


if __name__ == "__main__":
    main()
