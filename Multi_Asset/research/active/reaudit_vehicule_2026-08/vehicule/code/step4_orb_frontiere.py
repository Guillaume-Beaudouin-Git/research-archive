"""ÉTAPE 4 — le cas le plus serré du re-gate : l'ORB.

`orb_cost_funded_2026-08` (2026-08-13) publie une FRONTIÈRE de coût explicite plutôt
qu'un brut par trade : R2 (t_HAC > 2.0) tient tant que le coût RT reste sous
**0.588 bps**, et la moyenne elle-même passe négative à **2.189 bps**. Le coût CFD
mesuré est 1.80 bps -> ORB_KILL.

La question P2 devient arithmétique : le coût MNQ passe-t-il sous 0.588 ?

Le piège à ne pas commettre : facturer le seul tick + commission. L19 mesure sur NQ un
dérapage de base de **4 ticks RT ($2/MNQ)** à l'entrée au marché, jusqu'à 3x sur fills
adverses, et impose de stresser >=1.5x. Et l'ORB est une famille à **stop au repos** :
la pré-registration du programme mesure +2.169 bps sur MT5 pour ce type d'ordre (contre
~0.0-0.1 pour un ordre en séance liquide). Sur MNQ le canal gap est vide
(0/1587 sorties, 11/4013 entrées à 1 tick exactement — `orb_cost_funded` §2), donc le
surcoût de stop y est BORNÉ par le tick, pas par le spread CFD.
"""
from __future__ import annotations

import pandas as pd

from common import COMM_SIDE_FIXED, CONTRACTS, OUT

FRONTIERE_R2 = 0.588        # bps RT — t_HAC = 2.0
BREAKEVEN_MOY = 2.189       # bps RT — la moyenne passe negative
COUT_CFD_MESURE = 1.80

c = CONTRACTS["MNQ"]
notional = c["mult"] * c["px"]
tick_usd = c["tick"]
comm_rt = 2 * COMM_SIDE_FIXED


def bps(usd: float) -> float:
    return usd / notional * 1e4


scen = [
    ("A. tick + commission (hypothèse la plus favorable)", 1, 1.0),
    ("B. L19 base : dérapage 4 ticks RT ($2/MNQ) + commission", 4, 1.0),
    ("C. L19 stress x1.5 (imposé par la leçon)", 4, 1.5),
    ("D. L19 fills adverses x3 (borne haute documentée)", 4, 3.0),
]

rows = []
for nom, ticks, mult in scen:
    slip = ticks * tick_usd * mult
    total_usd = slip + comm_rt
    rt = bps(total_usd)
    rows.append(dict(scenario=nom, ticks_RT=ticks, stress=mult,
                     derapage_usd=round(slip, 2), commission_rt_usd=comm_rt,
                     cout_rt_usd=round(total_usd, 2), cout_rt_bps=round(rt, 3),
                     sous_frontiere_R2=bool(rt < FRONTIERE_R2),
                     marge_vs_frontiere_bps=round(FRONTIERE_R2 - rt, 3)))

df = pd.DataFrame(rows)
df.to_csv(OUT / "orb_frontiere_mnq.csv", index=False)

pd.set_option("display.width", 250)
print(f"MNQ : notionnel ${notional:,.0f} | 1 tick = ${tick_usd:.2f} = {bps(tick_usd):.3f} bps "
      f"| commission RT ${comm_rt:.2f} = {bps(comm_rt):.3f} bps")
print(f"FRONTIÈRE R2 publiée = {FRONTIERE_R2} bps RT | point mort de la moyenne = {BREAKEVEN_MOY} bps")
print(f"coût CFD mesuré (US100) = {COUT_CFD_MESURE} bps -> ORB_KILL\n")
print(df.to_string(index=False))
print(f"\n=> scénarios sous la frontière R2 : {int(df.sous_frontiere_R2.sum())}/{len(df)}")
print("=> R4 (walk-forward 2/5 plis = 40 %) est INDÉPENDANT du véhicule : il ne bouge pas.")
