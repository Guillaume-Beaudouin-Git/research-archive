"""EXPLORATOIRE (hors grille pré-enregistrée) — localiser le cliff EV<0.
Point (c): EV ne passe jamais négatif en balayant vm car le cap marge 60% borne le
livre (vm=∞ => épinglé à 60%). Le SEUL moyen d'être « plus agressif » que vm=∞ est de
RELEVER le cap. On balaie margin_cap à vm=∞ pour trouver où EV<0. Réutilise SWF.run_arm.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG / "v222_swing_fit"))
sys.path.insert(0, str(PKG / "v22"))
import config_v22 as C22                            # noqa: E402
import engine_v22 as V                              # noqa: E402
import run_swing_fit as SWF                         # noqa: E402

E = V.E
LEGS = ["XAUUSD", "USDJPY", "US100", "GER40"]
SWF.TAB = HERE / "tables"
SWING = np.array([C22.MARGIN_RATES_SWING[s] for s in LEGS])

M, M_swc, WT, ON = SWF.build()
rows = []
for cap in [0.60, 0.80, 1.00, 1.30, 1.60, 2.00, 2.50]:
    name = f"cap{int(cap*100)}_vminf"
    r, _ = SWF.run_arm(name, M_swc, WT, ON,
                       dict(C22.CFG_CHALLENGE, vm=1e6, margin_cap=cap))
    rows.append(dict(margin_cap=cap, p91=r["p91"], attempts=r["attempts"],
                     bust_daily=r["att_bust_daily"], bust_floor=r["att_bust_floor"],
                     abandon=r["att_abandon"], ev91=r["ev91"]))
    print(f"cap {cap:.2f} -> p91 {r['p91']:.1f} att {r['attempts']:.2f} "
          f"bust_d/f {r['att_bust_daily']:.1f}/{r['att_bust_floor']:.1f} EV {r['ev91']:+.0f}",
          flush=True)
df = pd.DataFrame(rows)
df.to_csv(HERE / "tables" / "cap_cliff.csv", index=False)
neg = df[df.ev91 < 0]
print("\nEV<0 cliff:", "aucun jusqu'à cap 2.5" if neg.empty
      else f"cap {neg.iloc[0]['margin_cap']}")
print(df.to_string(index=False))
