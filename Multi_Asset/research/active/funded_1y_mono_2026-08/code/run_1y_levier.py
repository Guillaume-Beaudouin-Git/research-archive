"""Funded 1 an — que reste-t-il quand SEULES les jambes overnight tournent ?

Book MONO = WT (or + J1) mis a ZERO, ORB off, jambes ON seules.
Contraste : book COMPLET (signaux or/J1 actifs) au meme vm.
Horizon 252 jours trades. Retraits /14 jours trades. Split trader 0.8.
Lecture seule sur toutes les sources importees.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(ROOT / "data" / "ftmo_portfolio" / "v22"))
sys.path.insert(0, str(ROOT / "Multi_Asset/research/active/orb_cost_funded_2026-08/funded_vm/code"))
import engine_v22 as V
import config_v22 as C22
import funded_instr as FI

OUT = ROOT / "Multi_Asset/research/active/funded_1y_mono_2026-08/out"
SPLIT, HORIZON, WD = 0.8, 252, 14

M = V.load_stack(orb_rt_bps="era")
WT_df, ON_df = V.E.build_signals()
WT_full, ON = V.align(M, WT_df, ON_df)
WT_mono = np.zeros_like(WT_full)                      # or = 0, J1 = 0
idx = M["dates_idx"]
print(f"panel : {idx.min().date()} -> {idx.max().date()}   n={M['n']}")
print(f"jours ON (lundi+mardi) : {int(ON.sum())}")
print(f"jours ou l'or ou le J1 est non nul : {int((np.abs(WT_full).sum(1) > 0).sum())}")

rows = []
for book, WT in (("MONO_overnight_seul", WT_mono),):
    for vm in (1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 7.0):
        cfg = dict(C22.CFG_FUNDED_V28, vm=float(vm), orb_risk=0.0)
        for i0 in V.starts(M, idx.min(), idx.max(), 10):
            if i0 + HORIZON >= M["n"]:
                continue
            r = FI.run_funded_instr(M, int(i0), WT, ON, cfg,
                                    horizon=HORIZON, wd_every=WD)
            r.update(book=book, vm=vm, start=idx[int(i0)])
            rows.append(r)

d = pd.DataFrame(rows)
d["brut"] = d.wd + d.residual
d["net_trader"] = SPLIT * d.brut
d.to_csv(OUT / "cohortes_1y_levier.csv.gz", index=False, compression="gzip")

print(f"\n{'='*96}\nFUNDED 1 AN (252 jours trades) — {len(d)} cohortes au total\n{'='*96}")
hdr = (f"{'book':<22}{'vm':>5}{'N':>5}{'bust%':>7}{'net MOY':>10}{'net MED':>9}"
       f"{'p10':>8}{'p90':>9}{'P(net>0)':>10}{'payouts':>9}{'vie med':>9}")
print(hdr); print("-"*len(hdr))
agg = []
for (b, vm), g in d.groupby(["book", "vm"], sort=False):
    n = len(g); nb = g.busted.sum()
    row = dict(book=b, vm=vm, n=n, bust_pct=100*nb/n,
               net_moy=g.net_trader.mean(), net_med=g.net_trader.median(),
               p10=g.net_trader.quantile(.10), p90=g.net_trader.quantile(.90),
               p_pos=100*(g.net_trader > 0).mean(),
               payouts=g.payouts.mean(), vie_med=g.life.median())
    agg.append(row)
    print(f"{b:<22}{vm:>5.2f}{n:>5}{row['bust_pct']:>7.1f}{row['net_moy']:>10.0f}"
          f"{row['net_med']:>9.0f}{row['p10']:>8.0f}{row['p90']:>9.0f}"
          f"{row['p_pos']:>9.1f}%{row['payouts']:>9.1f}{row['vie_med']:>9.0f}")
pd.DataFrame(agg).to_csv(OUT / "resume_1y_levier.csv", index=False)

