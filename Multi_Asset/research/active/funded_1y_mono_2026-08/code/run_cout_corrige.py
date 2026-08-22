"""Effet de la correction du cout ON : 2.2 bps codes en dur -> 1.045/1.017 mesures.

Le fichier canonique data/ftmo_portfolio/outputs/phase0_rt_cost_bps.csv facture 2.2 bps
a TOUS les indices. Mesure native FTMO (spread_log, 3 seances, n=3278-3280) :
US100 1.045 RT, GER40 1.017 RT. Ratio moyen = 1.031/2.2 = 0.469.

On NE TOUCHE PAS au fichier gele : engine.load_market expose spread_mul (engine.py:98)
qui multiplie exactement cette table. Or et J1 sont a poids zero, donc seuls US100 et
GER40 sont affectes.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(ROOT / "data" / "ftmo_portfolio" / "v22"))
sys.path.insert(0, str(ROOT / "Multi_Asset/research/active/orb_cost_funded_2026-08/funded_vm/code"))
import engine_v22 as V, config_v22 as C22, funded_instr as FI

SPREAD_MUL = 1.031 / 2.2
SPLIT, WD, VM, H = 0.8, 14, 1.00, 504
rows = []
for nom, smul in (("cout_2.2_code_en_dur", 1.0), ("cout_MESURE_1.03", SPREAD_MUL)):
    M = V.load_stack(spread_mul=smul, orb_rt_bps=0.96)
    WT_df, ON_df = V.E.build_signals()
    WT_full, ON = V.align(M, WT_df, ON_df)
    WT = np.zeros_like(WT_full)
    idx = M["dates_idx"]
    cfg = dict(C22.CFG_FUNDED_V28, vm=VM, orb_risk=0.0025)
    for i0 in V.starts(M, idx.min(), idx.max(), 10):
        if i0 + H >= M["n"]:
            continue
        r = FI.run_funded_instr(M, int(i0), WT, ON, cfg, horizon=H, wd_every=WD)
        r.update(variante=nom)
        rows.append(r)
    print("  fait :", nom, " spread_mul=%.3f" % smul, flush=True)

d = pd.DataFrame(rows)
d["net"] = SPLIT * (d.wd + d.residual)
print("\n" + "=" * 84)
print("EFFET DE LA CORRECTION DU COUT ON — 280 cohortes, 2 ans, vm 1.0, ORB a 0.96 bps")
print("=" * 84)
h = "%-24s %5s %8s %9s %9s %9s %8s %9s" % ("variante","N","bust%","net MED","net MOY","p10","p90","payouts")
print(h); print("-" * len(h))
agg = {}
for v, g in d.groupby("variante", sort=False):
    agg[v] = g
    print("%-24s %5d %7.2f%% %9.0f %9.0f %9.0f %9.0f %8.1f" % (
        v, len(g), 100*g.busted.mean(), g.net.median(), g.net.mean(),
        g.net.quantile(.10), g.net.quantile(.90), g.payouts.mean()))
a, b = agg["cout_2.2_code_en_dur"], agg["cout_MESURE_1.03"]
print("\n=== DELTA de la correction ===")
print("  net median : %+.0f $  (%+.1f %%)" % (b.net.median()-a.net.median(),
      100*(b.net.median()/a.net.median()-1)))
print("  net moyen  : %+.0f $  (%+.1f %%)" % (b.net.mean()-a.net.mean(),
      100*(b.net.mean()/a.net.mean()-1)))
print("  bust       : %+.2f pt" % (100*(b.busted.mean()-a.busted.mean())))
print("  retraits   : %+.1f" % (b.payouts.mean()-a.payouts.mean()))
d.to_csv("out/cohortes_cout_corrige.csv.gz", index=False, compression="gzip")
