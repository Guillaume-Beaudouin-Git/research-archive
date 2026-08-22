"""Distribution de la queue gauche a une nuit + conditionnement de regime.

Entrees : out/barrier_L10.6.csv (chemin M5 deja marche), panel_px (daily),
          out/vix.csv (^VIX, ^VIX3M).

Conditionnement, TOUT decale pour etre connu A LA POSE DU RISQUE :
  (i)   vol realisee 20j des jambes, close-to-close, shift(1)
  (ii)  structure par terme VIX/VIX3M, shift(1) -- le print VIX de 16:15 ET est
        POSTERIEUR a l'entree US100 de 22:05 CET (=16:05 ET), donc on ne peut
        utiliser que la cloture de la VEILLE
  (iii) distance au plus haut historique (US100), shift(1)

Sortie : out/tail_stats.json, out/worst20.csv, out/regime_table.csv
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "out"

L_HEAD = 10.6      # levier par jambe, geometrie deployee (0.6 x 14 x 1.2 = 10.08)
E0 = 10_000.0
LIM_BUST, LIM_FLOOR, BRK_LINE = 9_500.0, 9_000.0, 9_650.0

df = pd.read_csv(OUT / "barrier_L10.6.csv", index_col=0, parse_dates=True)

# ---------------------------------------------------------------- regimes
px = pd.read_parquet(ROOT / "data/ftmo_portfolio/cache/panel_px.parquet")[["US100", "GER40"]]
lr = np.log(px).diff()
rv20 = (lr.rolling(20).std() * np.sqrt(252)).shift(1)          # connue a T-1
ath = (px["US100"] / px["US100"].cummax() - 1.0).shift(1)      # <= 0

vix = pd.read_csv(OUT / "vix.csv", index_col=0, parse_dates=True)
vix.columns = [c.strip() for c in vix.columns]
vix = vix.rename(columns={"^VIX": "VIX", "^VIX3M": "VIX3M"})
vix["ts"] = vix["VIX"] / vix["VIX3M"]                          # >1 = backwardation
vixl = vix.shift(1)                                            # cloture de la VEILLE

df["rv20_us100"] = rv20["US100"].reindex(df.index).ffill()
df["rv20_ger40"] = rv20["GER40"].reindex(df.index).ffill()
df["ath_dist"] = ath.reindex(df.index).ffill()
for c in ("VIX", "VIX3M", "ts"):
    df[c] = vixl[c].reindex(df.index).ffill()

# ---------------------------------------------------------------- distributions
def describe(s: pd.Series, label: str) -> dict:
    s = s.dropna()
    return dict(label=label, n=int(len(s)), mean_bps=1e4 * s.mean(),
                std_bps=1e4 * s.std(), skew=float(stats.skew(s)),
                excess_kurt=float(stats.kurtosis(s)),
                min_bps=1e4 * s.min(), max_bps=1e4 * s.max(),
                **{f"p{q}_bps": 1e4 * s.quantile(q / 100)
                   for q in (0.1, 0.5, 1, 2.5, 5, 10, 25, 50, 75, 95, 99)})

dists = [describe(df["us100_ret"], "US100 nuit (entree->sortie)"),
         describe(df["ger40_ret"], "GER40 nuit (entree->sortie)"),
         describe(df["comb_gross"], "COMBINE brut (somme des jambes)"),
         describe(df["comb_net"], "COMBINE net (RT 2.2bps + swap)"),
         describe(df["mae_comb"], "COMBINE MAE (min du chemin M5)"),
         describe(df["worst_m5_jump"], "pire saut M5 unique"),
         describe(df["halt_gap"], "saut du halt 22:45->00:05 (intradable)")]
ddf = pd.DataFrame(dists).set_index("label")
pd.set_option("display.width", 250)
print("=== DISTRIBUTIONS (bps de notionnel par jambe) ===")
print(ddf[["n", "mean_bps", "std_bps", "skew", "excess_kurt", "p0.1_bps", "p1_bps",
           "p5_bps", "p50_bps", "min_bps"]].round(2).to_string())

# ---------------------------------------------------------------- traduction $
print(f"\n=== TRADUCTION EN EQUITE, L = {L_HEAD}x par jambe, E0 = {E0:.0f} ===")
rows = []
for q in (0.1, 0.5, 1, 2.5, 5, 10, 25, 50):
    for col, nm in [("comb_net", "endpoint net"), ("mae_comb", "MAE (chemin M5)")]:
        v = df[col].dropna().quantile(q / 100)
        eq = E0 * (1 + L_HEAD * v)
        rows.append(dict(percentile=f"p{q}", objet=nm, move_pct=100 * v,
                         perte_eur=E0 * L_HEAD * v, equite=eq,
                         pct_equite=100 * L_HEAD * v,
                         franchit_breaker_9650=eq < BRK_LINE,
                         franchit_daily_9500=eq < LIM_BUST,
                         franchit_floor_9000=eq < LIM_FLOOR))
tr = pd.DataFrame(rows)
print(tr.round(3).to_string(index=False))
tr.to_csv(OUT / "translation_L10.6.csv", index=False)

# percentile exact qui touche chaque seuil
print("\n=== PERCENTILE EXACT QUI FRANCHIT CHAQUE SEUIL ===")
thr = {"breaker 9650 (-3.5% equite)": -0.035 / L_HEAD,
       "daily/BUST 9500 (-5% equite)": -0.05 / L_HEAD,
       "plancher 9000 (-10% equite)": -0.10 / L_HEAD}
pct_rows = []
for name, t in thr.items():
    for col, nm in [("comb_net", "endpoint net"), ("mae_comb", "MAE M5")]:
        s = df[col].dropna()
        p = 100 * (s <= t).mean()
        pct_rows.append(dict(seuil=name, mouvement_combine_requis_pct=100 * t,
                             objet=nm, pct_nuits=p,
                             une_nuit_sur=(np.inf if p == 0 else 100 / p)))
pr = pd.DataFrame(pct_rows)
print(pr.round(3).to_string(index=False))
pr.to_csv(OUT / "percentile_thresholds.csv", index=False)

# ---------------------------------------------------------------- pires nuits
w = df.nsmallest(20, "mae_comb")[
    ["dow", "n_legs", "us100_ret", "ger40_ret", "comb_gross", "mae_comb",
     "worst_m5_jump", "halt_gap", "rv20_us100", "ath_dist", "VIX", "ts",
     "min_eq_nostop", "brk_hit", "bust_real", "floor_real"]].copy()
for c in ("us100_ret", "ger40_ret", "comb_gross", "mae_comb", "worst_m5_jump", "halt_gap"):
    w[c] = (1e4 * w[c]).round(1)
for c in ("rv20_us100", "ath_dist"):
    w[c] = (100 * w[c]).round(2)
w["min_eq_nostop"] = w["min_eq_nostop"].round(0)
w["jour"] = w.index.day_name().str[:3]
print("\n=== 20 PIRES NUITS (par MAE combine, bps) ===")
print(w.to_string())
w.to_csv(OUT / "worst20.csv")

# ---------------------------------------------------------------- regimes
print("\n=== CONDITIONNEMENT DE LA QUEUE GAUCHE ===")
reg_out = []
for var, label, bins in [
        ("rv20_us100", "vol realisee 20j US100 (T-1)", None),
        ("ts", "structure VIX/VIX3M (T-1)", [0, 0.85, 0.95, 1.0, 9]),
        ("ath_dist", "distance au plus haut US100 (T-1)", [-1, -0.10, -0.05, -0.02, 0.001])]:
    d = df.dropna(subset=[var, "mae_comb"]).copy()
    if bins is None:
        d["bucket"] = pd.qcut(d[var], 4, labels=["Q1 bas", "Q2", "Q3", "Q4 haut"])
    else:
        d["bucket"] = pd.cut(d[var], bins=bins)
    g = d.groupby("bucket", observed=True).agg(
        n=("mae_comb", "size"),
        mae_moy_bps=("mae_comb", lambda x: 1e4 * x.mean()),
        mae_p5_bps=("mae_comb", lambda x: 1e4 * x.quantile(0.05)),
        mae_p1_bps=("mae_comb", lambda x: 1e4 * x.quantile(0.01)),
        mae_min_bps=("mae_comb", lambda x: 1e4 * x.min()),
        endpoint_moy_bps=("comb_net", lambda x: 1e4 * x.mean()),
        pct_breaker=("brk_hit", lambda x: 100 * x.mean()),
        pct_bust=("bust_real", lambda x: 100 * x.mean()),
        pct_floor=("floor_real", lambda x: 100 * x.mean()))
    print(f"\n-- {label}")
    print(g.round(2).to_string())
    g.insert(0, "variable", label)
    reg_out.append(g)
pd.concat(reg_out).to_csv(OUT / "regime_table.csv")

json.dump({"distributions": dists,
           "thresholds_pct": pr.to_dict("records")},
          open(OUT / "tail_stats.json", "w"), indent=2, default=str)
print("\n-> out/tail_stats.json, worst20.csv, regime_table.csv, percentile_thresholds.csv")
