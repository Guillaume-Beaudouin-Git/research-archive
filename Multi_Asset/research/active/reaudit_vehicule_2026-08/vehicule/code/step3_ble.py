"""ÉTAPE 3bis — E011 blé/mai : la SEULE famille tuée sur le coût qui n'ait JAMAIS été
re-mesurée sur le contrat futures, et dont la donnée est au dépôt.

Kill d'origine (session_E2, CFD) : swap grain ~-115 bps/mois ramène +241 bps brut
(t 1.69) à +126 bps net (t 0.89). Sur ZW/MZW il n'y a PAS de swap : le portage est
dans la base, transigé au roll. Le re-gate P2-R2 donne 27x. La question est donc :
que reste-t-il quand le coût n'est plus le facteur liant ?

Spec GELÉE, héritée telle quelle, aucun réglage : LONG le mois de MAI, plat sinon.
Le placebo est le contrôle de SÉLECTION-DE-MOIS (12 mois), exécuté comme un placebo
apparié (L49) avec le contrôle de baseline inconditionnelle de L58.

Données : `data/raw/yf_ZW=F_1d_4ca92cfdb4.parquet` (2005-01 -> 2026-07), LECTURE SEULE.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import REPO
from common import ACCOUNT_USD, OUT, block_bootstrap_mean, contract_specs, hac_t

PX = REPO / "data/raw/yf_ZW=F_1d_4ca92cfdb4.parquet"

px = pd.read_parquet(PX)["close"].astype(float).sort_index()
px = px[px > 0]
ret = np.log(px).diff().dropna()          # rendement log quotidien du continu ZW
ret = ret[ret.index.year <= 2026]

print(f"ZW=F : N_jours={len(ret)}  {ret.index[0].date()} -> {ret.index[-1].date()}")
obs_per_year = len(ret) / ((ret.index[-1] - ret.index[0]).days / 365.25)
print(f"observations/an mesuré = {obs_per_year:.1f}  (annualisation en sqrt de CE nombre, L47)")

# ------------------------------------------------------------- rendement mensuel
grp = ret.groupby([ret.index.year, ret.index.month])
mois = grp.sum()                       # somme des log-rendements = rendement du mois
mois.index.names = ["an", "mois"]
n_jours_mois = grp.size()

rows = []
for m in range(1, 13):
    x = mois.xs(m, level="mois").values * 1e4      # en bps
    rows.append(dict(mois=m, n_evts=len(x), moyenne_bps=x.mean(), med_bps=np.median(x),
                     t_simple=x.mean() / (x.std(ddof=1) / np.sqrt(len(x))),
                     t_hac6=hac_t(x), skew=pd.Series(x).skew(),
                     frac_pos=float((x > 0).mean())))
prof = pd.DataFrame(rows)
prof.to_csv(OUT / "ble_profil_mensuel.csv", index=False)
print("\n=== Profil mensuel ZW=F (log-rendement du mois, bps) ===")
print(prof.round(3).to_string(index=False))

mai = mois.xs(5, level="mois").values * 1e4
N = len(mai)
print(f"\n=== MAI : N={N} événements ===")
print(f"moyenne {mai.mean():.1f} bps | médiane {np.median(mai):.1f} | t simple {rows[4]['t_simple']:.3f} "
      f"| t_HAC6 {hac_t(mai):.3f} | skew {pd.Series(mai).skew():.3f} | frac>0 {(mai>0).mean():.3f}")

# ------------------------------------------------- bootstrap par blocs (iid interdit)
bs = block_bootstrap_mean(mai, n_boot=5000, mean_block=3)
lo, hi = np.percentile(bs, [2.5, 97.5])
print(f"IC95 block-bootstrap (bloc moyen 3 évts) : [{lo:.1f}, {hi:.1f}] bps  "
      f"-> {'CONTIENT ZÉRO' if lo <= 0 <= hi else 'exclut zéro'}")

# ------------------------------------- PLACEBO apparié = sélection-de-mois (L49/L58)
pool = np.array([r["moyenne_bps"] for r in rows if r["mois"] != 5])
uncond = mois.values.mean() * 1e4        # espérance INCONDITIONNELLE de la forme de trade
print("\n=== PLACEBO de sélection-de-mois (L49) + contrôle de baseline L58 ===")
print(f"pool des 11 autres mois : moyenne {pool.mean():.1f} bps | p50 {np.median(pool):.1f} "
      f"| p95 {np.percentile(pool,95):.1f} | max {pool.max():.1f}")
print(f"espérance INCONDITIONNELLE d'un mois quelconque : {uncond:.1f} bps")
# L58 : la baseline correcte n'est PAS l'inconditionnelle brute — retirer mai du pool
# déplace mécaniquement la moyenne du pool (effet leave-one-out). La baseline attendue
# est donc (12 * inconditionnelle - mai) / 11. Comparer au brut fabriquerait un faux
# « placebo biaisé ».
attendu = (12 * uncond - mai.mean()) / 11
print(f"baseline ATTENDUE du pool (leave-one-out de mai) : {attendu:.2f} bps")
ecart = abs(pool.mean() - attendu)
print(f"contrôle L58 : |moyenne du pool - baseline attendue| = {ecart:.2f} bps "
      f"-> {'placebo NON biaisé' if ecart < 2 else 'PLACEBO BIAISÉ'}")
rang = float((pool >= mai.mean()).sum())
print(f"mai ({mai.mean():.1f}) vs pool : {int(rang)}/11 mois font AUSSI BIEN ou mieux "
      f"-> p empirique = {(rang+1)/12:.3f}")
best = prof.loc[prof.moyenne_bps.idxmax()]
print(f"meilleur mois de la série = mois {int(best.mois)} ({best.moyenne_bps:.1f} bps) "
      f"-> mai est-il le meilleur ? {'OUI' if int(best.mois)==5 else 'NON'}")

# ----------------------------------------------- walk-forward expanding >= 5 plis
K = 5
folds = np.array_split(np.arange(N), K)
wf = []
for k in range(K):
    te = folds[k]
    wf.append(dict(fold=k + 1, n=len(te), moyenne_bps=mai[te].mean(), pos=bool(mai[te].mean() > 0)))
wfd = pd.DataFrame(wf)
print(f"\n=== Walk-forward {K} plis (découpage chronologique) ===")
print(wfd.round(2).to_string(index=False))
print(f"plis positifs : {int(wfd.pos.sum())}/{K} = {100*wfd.pos.mean():.0f} %  (RESEARCH_PASS exige > 50 %)")

# ----------------------------------------------- L57 : coût, skew, queue 1 séance
sp = contract_specs().set_index("contract")
mai_daily = ret[ret.index.month == 5]
for code in ("ZW", "MZW"):
    s = sp.loc[code]
    notional = float(s.notional_usd)
    lev = notional / ACCOUNT_USD
    pire = float(mai_daily.min()) * lev * 100
    pire2 = float(np.percentile(mai_daily, 1)) * lev * 100
    net = mai.mean() - float(s.rt_bps_base)
    print(f"\n--- {code} ({s.desc}) ---")
    print(f"  marge {s.margin_usd:.0f} $ = {s.margin_pct_account:.1f} % du compte | "
          f"notionnel {notional:.0f} $ = {lev:.2f}x le compte")
    print(f"  coût RT {s.rt_bps_base:.2f} bps (dont {s.fixed_share_pct:.0f} % de frais FIXE) | "
          f"p95 2-ticks {s.rt_bps_stress_2tick:.2f}")
    print(f"  brut {mai.mean():.1f} bps -> NET {net:.1f} bps | ratio brut/coût_p95 = "
          f"{mai.mean()/float(s.rt_bps_stress_2tick):.1f}")
    print(f"  L57 à LOT FIXE : skew des rendements de mai {mai_daily.skew():.3f} | "
          f"PIRE SÉANCE {pire:.1f} % du compte | p1 des séances {pire2:.1f} %")

pd.DataFrame(dict(an=sorted(set(mois.xs(5, level='mois').index)), mai_bps=mai)).to_csv(
    OUT / "ble_mai_par_an.csv", index=False)
wfd.to_csv(OUT / "ble_walkforward.csv", index=False)
