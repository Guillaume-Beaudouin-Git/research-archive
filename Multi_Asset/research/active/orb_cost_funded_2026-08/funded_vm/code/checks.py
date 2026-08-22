"""Contrôles ciblés du volet D.

(1) ab_days : le piège documenté dans config_v22.py concerne l'étage CHALLENGE
    (run_phase / run_funnel). On vérifie par INSPECTION DE SOURCE et par
    EXPÉRIENCE que l'étage funded l'ignore : run_funded n'a ni compteur zombie
    ni sortie "abandon". Conséquence : dans ce volet, ab_days est déjà
    implicitement infini — la borne haute de p(funded) recherchée par le
    cahier des charges est donc celle qui est simulée, sans réglage à faire.
(2) sensibilité de marge : Standard (v2.4) vs Swing mesuré (v2.5/v2.8).
"""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(ROOT / "data" / "ftmo_portfolio" / "v22"))
sys.path.insert(0, str(HERE))
import engine_v22 as V          # noqa: E402
import config_v22 as C22        # noqa: E402
E = V.E

src = (ROOT / "data/ftmo_portfolio/v22/engine_v22.py").read_text()
body = src.split("def run_funded")[1]
print("[1] run_funded : 'ab_days' present =", "ab_days" in body,
      "| 'zombie' present =", "zombie" in body,
      "| 'abandon' present =", "abandon" in body)

t0 = time.time()
M = V.load_stack(orb_rt_bps="era")
WT_df, ON_df = E.build_signals()
WT, ON = V.align(M, WT_df, ON_df)
st = np.concatenate([V.starts(M, lo, hi, C22.FUNDED_STEP)
                     for _, lo, hi in C22.FUNDED_WINDOWS])[::4]
print(f"stack [{time.time()-t0:.0f}s], sous-échantillon n={len(st)}")

K = ("wd", "payouts", "life", "busted", "residual")
for vm in (0.85, 1.0):
    a = pd.DataFrame([V.run_funded(M, int(i), WT, ON,
                                   dict(C22.CFG_FUNDED_V28, vm=vm),
                                   horizon=C22.FUNDED_HORIZON,
                                   wd_every=C22.FUNDED_WD_EVERY) for i in st])
    b = pd.DataFrame([V.run_funded(M, int(i), WT, ON,
                                   dict(C22.CFG_FUNDED_V28, vm=vm, ab_days=5,
                                        ab_buf=0.02),
                                   horizon=C22.FUNDED_HORIZON,
                                   wd_every=C22.FUNDED_WD_EVERY) for i in st])
    same = all(np.allclose(a[k].astype(float), b[k].astype(float)) for k in K)
    print(f"[1] ab_days=5 vs absent @ vm{vm} : identique = {same} "
          f"(bust {a.busted.mean():.3f} / {b.busted.mean():.3f})", flush=True)

rows = []
for tag, cfg0 in (("V24 marge Standard 2%", C22.CFG_FUNDED_V24),
                  ("V28 marge Swing mesurée 6.67%", C22.CFG_FUNDED_V28)):
    for vm in (0.70, 0.85, 1.00, 1.20):
        r = pd.DataFrame([V.run_funded(M, int(i), WT, ON, dict(cfg0, vm=vm),
                                       horizon=C22.FUNDED_HORIZON,
                                       wd_every=C22.FUNDED_WD_EVERY) for i in st])
        r["extr"] = r.wd + r.residual
        rows.append(dict(cfg=tag, vm=vm, n=len(r), bust=r.busted.mean(),
                         ev504=0.8 * r.extr.mean(), payouts=r.payouts.mean(),
                         life_med=r.life.median()))
        print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(HERE.parent / "out" / "margin_std_vs_swing.csv", index=False)
print(f"done [{time.time()-t0:.0f}s]")
