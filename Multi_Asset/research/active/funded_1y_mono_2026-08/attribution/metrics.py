"""Agrégation mensuelle, métriques et corrélations de l'attribution funded.

Lit `daily_raw.csv` (produit par build_series.py), écrit :
  serie_mensuelle.csv, metriques.csv, correlations.csv, diagnostics.txt

Conventions (justifiées dans RAPPORT.md) :
  - tous les rendements sont en % d'une équité de RÉFÉRENCE constante ($10 000).
    Un compte funded ne compose pas (le buffer ne grandit jamais, les gains sont
    retirés) -> le dénominateur constant est le bon, et il rend l'attribution ADDITIVE.
  - agrégation mensuelle = SOMME arithmétique des rendements journaliers.
  - Sharpe annualisé en sqrt(obs/an) = sqrt(12) au pas mensuel (L47).
  - alpha/beta : régression OLS avec erreurs-types HAC Newey-West lag-6.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

OUT = Path(__file__).resolve().parent
INIT = 10_000.0
W_ON = 0.35

SLEEVES = ["on_us100", "on_ger40", "orb", "portefeuille"]
BENCH = {"on_us100": "bh_us100", "on_ger40": "bh_ger40",
         "orb": "bh_orb", "portefeuille": "bh_portefeuille"}
UNDER = {"on_us100": "und_us100", "on_ger40": "und_ger40",
         "orb": "und_us100", "portefeuille": "und_mix"}


def load_daily() -> pd.DataFrame:
    d = pd.read_csv(OUT / "daily_raw.csv", index_col=0, parse_dates=True)
    # notionnel effectif de l'ORB quand il est en position (varie avec la largeur d'OR)
    w_orb = d.loc[d.orb_live == 1, "orb_w"]
    w_orb = w_orb.replace([np.inf, -np.inf], np.nan)
    d.attrs["w_orb_mean"] = float(w_orb.mean())
    d.attrs["w_orb_median"] = float(w_orb.median())
    # benchmark ORB : US100 buy-and-hold au notionnel MOYEN effectivement porté
    d["bh_orb"] = d.attrs["w_orb_mean"] * d["und_us100"]
    d["bh_orb_net"] = d["bh_orb"] + d.attrs["w_orb_mean"] / W_ON * d["bh_us100_swap"]
    # benchmark portefeuille : somme des trois benchmarks (mêmes notionnels)
    d["bh_portefeuille"] = d["bh_us100"] + d["bh_ger40"] + d["bh_orb"]
    d["bh_portefeuille_net"] = d["bh_us100_net"] + d["bh_ger40_net"] + d["bh_orb_net"]
    # sous-jacent composite du portefeuille, pondéré par les notionnels des jambes
    wtot = W_ON + W_ON + d.attrs["w_orb_mean"]
    d["und_mix"] = ((W_ON * d["und_us100"] + W_ON * d["und_ger40"]
                     + d.attrs["w_orb_mean"] * d["und_us100"]) / wtot)
    return d


def to_monthly(d: pd.DataFrame, cols) -> pd.DataFrame:
    m = d[cols].groupby(d.index.to_period("M")).sum()
    m.index = m.index.astype(str)
    m.index.name = "mois"
    return m


def maxdd(r: pd.Series) -> float:
    eq = (1.0 + r).cumprod()
    return float((eq / eq.cummax() - 1.0).min())


def hac(y: pd.Series, x: pd.Series, lags: int = 6):
    X = sm.add_constant(x.to_numpy(float))
    fit = sm.OLS(y.to_numpy(float), X).fit(cov_type="HAC",
                                           cov_kwds={"maxlags": lags})
    return dict(alpha=float(fit.params[0]), t_alpha=float(fit.tvalues[0]),
                beta=float(fit.params[1]), t_beta=float(fit.tvalues[1]),
                r2=float(fit.rsquared))


def metrics_row(name: str, rm: pd.Series, bm: pd.Series, um: pd.Series,
                rd: pd.Series, window: str, n_trades: int, ppy: float) -> dict:
    n = len(rm)
    mu, sd = rm.mean(), rm.std(ddof=1)
    reg_b = hac(rm, bm)
    reg_u = hac(rm, um)
    # version "à risque égal" : benchmark rescalé à la volatilité de la sleeve
    k = sd / bm.std(ddof=1) if bm.std(ddof=1) > 0 else np.nan
    return {
        "sleeve": name, "fenetre": window, "N_mois": n, "N_trades": n_trades,
        "ret_moy_mois_pct": mu * 100, "ret_moy_mois_usd": mu * INIT,
        "ret_total_pct": rm.sum() * 100, "ret_ann_pct": mu * 12 * 100,
        "vol_mois_pct": sd * 100, "vol_ann_pct": sd * np.sqrt(12) * 100,
        "sharpe_ann_sqrt12": mu / sd * np.sqrt(12) if sd > 0 else np.nan,
        "sharpe_ann_par_trade": (rd[rd != 0].mean() / rd[rd != 0].std(ddof=1)
                                 * np.sqrt(ppy)) if n_trades > 3 else np.nan,
        "hit_rate_mois_pct": (rm > 0).mean() * 100,
        "meilleur_mois_pct": rm.max() * 100, "pire_mois_pct": rm.min() * 100,
        "maxdd_mensuel_pct": maxdd(rm) * 100,
        "maxdd_journalier_pct": maxdd(rd) * 100,
        "skew_mensuel": float(rm.skew()), "skew_journalier": float(rd.skew()),
        "beta_vs_sousjacent": reg_u["beta"], "t_beta_vs_sousjacent": reg_u["t_beta"],
        "corr_vs_sousjacent": float(rm.corr(um)),
        "r2_vs_sousjacent_pct": reg_u["r2"] * 100,
        "beta_vs_bh_notionnel": reg_b["beta"], "corr_vs_bh": float(rm.corr(bm)),
        "r2_vs_bh_pct": reg_b["r2"] * 100,
        "alpha_HAC_mois_pct": reg_b["alpha"] * 100,
        "alpha_HAC_mois_usd": reg_b["alpha"] * INIT,
        "alpha_HAC_ann_pct": reg_b["alpha"] * 12 * 100,
        "t_alpha_HAC6": reg_b["t_alpha"],
        "bh_ret_moy_mois_pct": bm.mean() * 100,
        "bh_vol_mois_pct": bm.std(ddof=1) * 100,
        "bh_sharpe_ann": (bm.mean() / bm.std(ddof=1) * np.sqrt(12)
                          if bm.std(ddof=1) > 0 else np.nan),
        "bh_volmatch_ret_moy_mois_pct": bm.mean() * k * 100 if k == k else np.nan,
        "excedent_vs_bh_pct_mois": (mu - bm.mean()) * 100,
        "excedent_vs_bh_volmatch_pct_mois": (mu - bm.mean() * k) * 100 if k == k else np.nan,
    }


def main():
    d = load_daily()
    cols = (SLEEVES + list(BENCH.values()) + list(UNDER.values())
            + ["bh_us100_net", "bh_ger40_net", "bh_orb_net", "bh_portefeuille_net",
               "on_us100_swapcorr", "on_ger40_swapcorr", "portefeuille_swapcorr",
               "on_us100_gross", "on_ger40_gross", "on_us100_cost", "on_ger40_cost",
               "on_us100_swap_panel", "on_ger40_swap_panel"])
    cols = list(dict.fromkeys(cols))
    M = to_monthly(d, cols)

    # ---------- serie_mensuelle.csv (livrable §1)
    keep = ["on_us100", "on_ger40", "orb", "portefeuille", "bh_us100", "bh_ger40",
            "bh_orb", "bh_portefeuille", "bh_us100_net", "bh_ger40_net",
            "bh_portefeuille_net", "on_us100_swapcorr", "on_ger40_swapcorr",
            "portefeuille_swapcorr", "und_us100", "und_ger40"]
    (M[keep] * 100).round(6).to_csv(OUT / "serie_mensuelle.csv")

    # ---------- metriques.csv (livrable §3)
    windows = {"vie_2013-09_2026-06": (M.index[0], M.index[-1]),
               "2ans_2024-06_2026-05": ("2024-06", "2026-05")}
    ntr = {"on_us100": int(d.on_us100_live.sum()), "on_ger40": int(d.on_ger40_live.sum()),
           "orb": int(d.orb_live.sum())}
    ntr["portefeuille"] = int(((d.on_us100_live + d.on_ger40_live + d.orb_live) > 0).sum())
    rows = []
    for wname, (a, b) in windows.items():
        Mw = M.loc[a:b]
        dw = d.loc[(d.index >= pd.Period(a, "M").start_time)
                   & (d.index <= pd.Period(b, "M").end_time)]
        yrs = len(dw) / 252.0
        for s in SLEEVES:
            nt = int(dw[f"{s}_live"].sum()) if f"{s}_live" in dw else ntr[s]
            if s == "portefeuille":
                nt = int(((dw.on_us100_live + dw.on_ger40_live + dw.orb_live) > 0).sum())
            rows.append(metrics_row(s, Mw[s], Mw[BENCH[s]], Mw[UNDER[s]], dw[s],
                                    wname, nt, nt / yrs))
        # variantes swap corrigé
        for s, sc in (("on_ger40", "on_ger40_swapcorr"), ("on_us100", "on_us100_swapcorr"),
                      ("portefeuille", "portefeuille_swapcorr")):
            nt = int(((dw.on_us100_live + dw.on_ger40_live + dw.orb_live) > 0).sum()) \
                if s == "portefeuille" else int(dw[f"{s}_live"].sum())
            rows.append(metrics_row(sc, Mw[sc], Mw[BENCH[s]], Mw[UNDER[s]], dw[sc],
                                    wname, nt, nt / yrs))
        # sleeves inactives
        for s in ("xauusd_or_INACTIVE", "usdjpy_j1_INACTIVE"):
            rows.append({"sleeve": s, "fenetre": wname, "N_mois": len(Mw),
                         "N_trades": 0, "ret_moy_mois_pct": 0.0,
                         "ret_moy_mois_usd": 0.0, "ret_total_pct": 0.0,
                         "note": "poids ZERO dans la config funded — ne contribue pas"})
    pd.DataFrame(rows).round(6).to_csv(OUT / "metriques.csv", index=False)

    # ---------- correlations.csv (livrable §4)
    cmat = ["on_us100", "on_ger40", "orb", "portefeuille",
            "bh_us100", "bh_ger40", "und_us100", "und_ger40"]
    blocks = []
    for freq, X in (("mensuel_vie", M[cmat]),
                    ("mensuel_2ans", M.loc["2024-06":"2026-05", cmat]),
                    ("journalier_vie", d[cmat])):
        c = X.corr().round(4)
        c.insert(0, "freq", freq)
        c.index.name = "serie"
        blocks.append(c.reset_index())
    pd.concat(blocks).to_csv(OUT / "correlations.csv", index=False)

    # ---------- diagnostics
    lines = []
    P = lines.append
    P(f"seances={len(d)}  {d.index.min().date()} -> {d.index.max().date()}")
    P(f"mois={len(M)}  {M.index[0]} -> {M.index[-1]}")
    P(f"N trades: {ntr}")
    P(f"notionnel ORB en position: moyen={d.attrs['w_orb_mean']:.4f}x  "
      f"median={d.attrs['w_orb_median']:.4f}x  (jambes ON = {W_ON:.2f}x)")
    P(f"jours ON sans jambe GER40 (trous 2018-2021): "
      f"{int((d.is_on_day == 1).sum() - d.on_ger40_live.sum())}")
    P(f"OR range NUL (controle L60): "
      f"{int((d.orb_or_bps == 0).sum())} / {int(d.orb_or_bps.notna().sum())}")
    P("")
    P("--- decomposition par jambe ON (en % d'equite, cumule sur la vie) ---")
    for t in ("us100", "ger40"):
        P(f"on_{t}: gross={d[f'on_{t}_gross'].sum()*100:7.2f}%  "
          f"cout={d[f'on_{t}_cost'].sum()*100:7.2f}%  "
          f"swap_panel={d[f'on_{t}_swap_panel'].sum()*100:7.2f}%  "
          f"swap_mesure={d[f'on_{t}_swap_meas'].sum()*100:7.2f}%  "
          f"net={d[f'on_{t}'].sum()*100:7.2f}%")
    P(f"orb   : net(era-coste)={d['orb'].sum()*100:7.2f}%")
    P("")
    P("--- part du swap dans le gross (L36) ---")
    for t in ("us100", "ger40"):
        g = d[f"on_{t}_gross"].sum()
        P(f"on_{t}: swap/gross = {abs(d[f'on_{t}_swap_panel'].sum())/g*100:5.1f}% (panel) "
          f"/ {abs(d[f'on_{t}_swap_meas'].sum())/g*100:5.1f}% (mesure)  "
          f"cout/gross = {abs(d[f'on_{t}_cost'].sum())/g*100:5.1f}%")
    (OUT / "diagnostics.txt").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
