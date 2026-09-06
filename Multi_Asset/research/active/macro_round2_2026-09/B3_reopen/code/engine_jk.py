"""B3 re-ouverture — drift post-FOMC, surprise decomposee (Jarocinski-Karadi).

Un seul axe change vs le moteur gele `data/personal_book/post_fomc_drift/code/engine.py` :
la mesure de surprise. Rendements, calendrier, seuil (en bps), horizons, cout et regles
d'entree/sortie sont repris a l'identique.

Spec gelee : ../PREREGISTRATION.md (commit 40465436).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm

BASE = Path(__file__).resolve().parents[1]
REPO = Path("<HOME>/Desktop/Algo_claude")
FROZEN = REPO / "data/personal_book/post_fomc_drift"

X_BPS = 5.0          # seuil, identique au gel (transpose en points de pourcentage : 0.05)
TOL = 1e-9
HS = (5, 10, 20)     # horizons du gel
COST_RT = 1e-4       # 1 bp round-trip par evenement, tier futures
REGIMES = (("pre2015", None, "2014-12-31"),
           ("2015_2021", "2015-01-01", "2021-12-31"),
           ("post2022", "2022-01-01", None))


def load_frozen_csv(name: str) -> pd.Series:
    df = pd.read_csv(FROZEN / f"data_cache/{name}.csv", na_values=["."])
    df.columns = ["date", "v"]
    df["date"] = pd.to_datetime(df["date"])
    return pd.to_numeric(df.set_index("date")["v"], errors="coerce").dropna().sort_index()


def hac_t(x: np.ndarray) -> tuple[float, float]:
    """Moyenne et t HAC(lag-6) contre zero — regle maison, identique au gel."""
    x = np.asarray(x, float)
    if len(x) < 3 or np.std(x) == 0:
        return (float(np.mean(x)) if len(x) else np.nan), np.nan
    fit = sm.OLS(x, np.ones((len(x), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return float(fit.params[0]), float(fit.tvalues[0])


def mde_80(x: np.ndarray) -> float:
    """Effet minimum detectable a 80 % de puissance (L65) : 2.80 * sigma / sqrt(n)."""
    x = np.asarray(x, float)
    if len(x) < 2:
        return np.nan
    z = norm.ppf(0.975) + norm.ppf(0.80)
    return float(z * np.std(x, ddof=1) / math.sqrt(len(x)))


def main() -> None:
    panel = (pd.read_csv(REPO / "data/panels/macro_etf_panel.csv", parse_dates=["Date"])
             .set_index("Date").sort_index())
    pxi = panel.index
    ief = np.log(panel["IEF"]).diff()
    rf = load_frozen_csv("DTB3").reindex(pxi).ffill() / 100.0 / 252.0
    xs_v = (ief - rf).values

    ev = (pd.read_csv(FROZEN / "data_cache/fomc_events.csv", parse_dates=["date"])
          .sort_values("date").reset_index(drop=True))

    jk = pd.read_csv(BASE / "data/shocks_fed_jk_t.csv")
    jk["date"] = pd.to_datetime(jk["start"]).dt.normalize()
    jk = jk.groupby("date", as_index=False)[["pc1", "MP_pm", "CBI_pm",
                                             "MP_median", "CBI_median"]].sum()

    # --- mapping evenement -> barre de prix, identique au gel ---
    recs = []
    for d in ev["date"]:
        k = int(pxi.searchsorted(d))
        if k + 1 >= len(pxi):
            continue
        recs.append({"date": d, "entry_pos": k + 1})
    eva = (pd.DataFrame(recs).drop_duplicates(subset="entry_pos", keep="first")
           .reset_index(drop=True))
    eva = eva.merge(jk, on="date", how="left")
    next_entry = eva["entry_pos"].shift(-1)

    matched = int(eva["pc1"].notna().sum())
    diag = {"n_events_ledger": int(len(ev)), "n_events_mapped": int(len(eva)),
            "n_matched_jk": matched, "n_unmatched": int(len(eva) - matched),
            "jk_first": str(jk["date"].min().date()), "jk_last": str(jk["date"].max().date()),
            "common_window": f"{eva.loc[eva['pc1'].notna(),'date'].min().date()}"
                             f" -> {eva.loc[eva['pc1'].notna(),'date'].max().date()}"}

    out: dict = {"diagnostics": diag, "components": {}}

    for comp, label in (("MP_pm", "politique_monetaire"), ("CBI_pm", "information"),
                        ("MP_median", "politique_monetaire_ROBUSTESSE"),
                        ("CBI_median", "information_ROBUSTESSE")):
        res_h = {}
        for H in HS:
            e = eva.copy()
            s = e[comp] * 100.0                      # points de % -> bps
            e["traded"] = s.abs() >= X_BPS - TOL
            e["side"] = np.where(e["traded"], -np.sign(s), 0.0)
            e["exit_pos"] = np.minimum(e["entry_pos"] + H,
                                       next_entry.fillna(np.inf)).astype(float)
            e = e[e["exit_pos"] <= len(pxi) - 1].copy()
            e["exit_pos"] = e["exit_pos"].astype(int)
            e["gross"] = [sd * float(np.nansum(xs_v[a + 1: b + 1]))
                          for sd, a, b in zip(e["side"], e["entry_pos"], e["exit_pos"])]
            e["net"] = np.where(e["traded"], e["gross"] - COST_RT, 0.0)

            t = e[e["traded"]].sort_values("entry_pos").reset_index(drop=True)
            g_mean, g_t = hac_t(t["gross"].values)
            n_mean, n_t = hac_t(t["net"].values)

            legs = {}
            for lab, sgn in (("hawkish_short", -1.0), ("dovish_long", 1.0)):
                ln = t.loc[t["side"] == sgn, "net"].values
                m, tt = hac_t(ln)
                legs[lab] = {"n": int(len(ln)), "mean_net_bps": m * 1e4 if len(ln) else np.nan,
                             "t_hac": tt}

            regimes = {}
            for lab, a, b in REGIMES:
                m_ = pd.Series(True, index=t.index)
                if a: m_ &= t["date"] >= a
                if b: m_ &= t["date"] <= b
                rn = t.loc[m_, "net"].values
                m, tt = hac_t(rn) if len(rn) else (np.nan, np.nan)
                regimes[lab] = {"n": int(len(rn)),
                                "mean_net_bps": m * 1e4 if len(rn) else np.nan,
                                "t_hac": tt,
                                "mde80_bps": mde_80(rn) * 1e4 if len(rn) > 1 else np.nan,
                                "binding": bool(len(rn) >= 10)}

            res_h[f"H{H}"] = {
                "n_traded": int(len(t)),
                "mean_gross_bps": g_mean * 1e4, "t_gross": g_t,
                "mean_net_bps": n_mean * 1e4, "t_net": n_t,
                "mde80_net_bps": mde_80(t["net"].values) * 1e4,
                "legs": legs, "regimes": regimes,
            }
        out["components"][label] = res_h

    (BASE / "results").mkdir(exist_ok=True)
    with open(BASE / "results/results_jk.json", "w") as f:
        json.dump(out, f, indent=2, default=float)

    # ---------------- rapport lisible ----------------
    print(f"Ledger {diag['n_events_ledger']} evts | mappes {diag['n_events_mapped']} | "
          f"apparies JK {diag['n_matched_jk']} | fenetre {diag['common_window']}")
    for label in ("politique_monetaire", "information"):
        print(f"\n=== {label.upper()} ===")
        for H in HS:
            r = out["components"][label][f"H{H}"]
            print(f"  H={H:<3} n={r['n_traded']:<4} "
                  f"gross {r['mean_gross_bps']:+7.2f} bps (t {r['t_gross']:+5.2f})   "
                  f"net {r['mean_net_bps']:+7.2f} bps (t {r['t_net']:+5.2f})   "
                  f"MDE80 {r['mde80_net_bps']:6.2f}")
    print("\n=== SIGNE PAR SOUS-PERIODE (net bps, H=10) ===")
    for label in ("politique_monetaire", "information"):
        r = out["components"][label]["H10"]["regimes"]
        cells = "  ".join(
            f"{k}: {r[k]['mean_net_bps']:+7.1f} (n={r[k]['n']:>2}, t {r[k]['t_hac']:+5.2f})"
            for k in ("pre2015", "2015_2021", "post2022"))
        print(f"  {label:<22} {cells}")
    print("\n=== ROBUSTESSE (restriction de signe, diagnostic seulement) ===")
    for label in ("politique_monetaire_ROBUSTESSE", "information_ROBUSTESSE"):
        r = out["components"][label]["H10"]
        print(f"  {label:<34} H=10 n={r['n_traded']:<4} net {r['mean_net_bps']:+7.2f} "
              f"bps (t {r['t_net']:+5.2f})")


if __name__ == "__main__":
    main()
