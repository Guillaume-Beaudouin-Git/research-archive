"""Book REELLEMENT DEPLOYE = jambes ON + ORB (FU_ORB_RISK=0.0025), vm=1.0.

Corrige une erreur de perimetre : `run_1y.py` et `run_vie.py` forcent orb_risk=0.0,
donc leurs chiffres ($201/an, $1195 sur 5 ans, bust 0.0%) decrivent un book SANS ORB.
Le binaire deploye a FU_ORB_RISK=0.0025 => l'ORB poste ses stops des l'armement.

Ce script mesure la contribution de l'ORB a coût VARIABLE, dont le coût mesure en
live sur le compte FTMO le 2026-08-17 (spread US100 aller-retour = 0.964 bps).

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
SPLIT, WD, VM = 0.8, 14, 1.00
ORB_RISK_DEPLOYE = 0.0025

# hypotheses de coût ORB, aller-retour bps
COUTS = [
    ("ORB_OFF",        None),   # baseline = ce que run_1y/run_vie ont simule
    ("era",           "era"),   # hypothese du ledger de branches (2632 vs 1262)
    ("0.96_mesure",    0.96),   # spread FTMO mesure en LIVE le 2026-08-17
    ("2.17_allin",     2.17),   # tout-compris stop-entry mesure (n=12, fills.csv)
    ("3.00_pessim",    3.00),   # au-dela de la frontiere de mort connue (2-3 bps)
]

rows = []
for horizon, label in ((252, "1an"), (1260, "5ans")):
    for nom, cout in COUTS:
        M = V.load_stack(orb_rt_bps=("era" if cout is None else cout))
        WT_df, ON_df = V.E.build_signals()
        WT_full, ON = V.align(M, WT_df, ON_df)
        WT_mono = np.zeros_like(WT_full)          # or = 0, J1 = 0 (regime actuel)
        idx = M["dates_idx"]
        cfg = dict(C22.CFG_FUNDED_V28, vm=VM,
                   orb_risk=(0.0 if cout is None else ORB_RISK_DEPLOYE))
        for i0 in V.starts(M, idx.min(), idx.max(), 10):
            if i0 + horizon >= M["n"]:
                continue
            r = FI.run_funded_instr(M, int(i0), WT_mono, ON, cfg,
                                    horizon=horizon, wd_every=WD)
            r.update(scenario=nom, horizon=label, start=idx[int(i0)])
            rows.append(r)
        print(f"  fait : {label:5} {nom}", flush=True)

d = pd.DataFrame(rows)
d["brut"] = d.wd + d.residual
d["net_trader"] = SPLIT * d.brut
d.to_csv(OUT / "cohortes_deploye.csv.gz", index=False, compression="gzip")

agg = []
for (h, s), g in d.groupby(["horizon", "scenario"], sort=False):
    n = len(g)
    agg.append(dict(horizon=h, scenario=s, n=n,
                    bust_pct=100 * g.busted.sum() / n,
                    net_med=g.net_trader.median(),
                    net_moy=g.net_trader.mean(),
                    p10=g.net_trader.quantile(.10),
                    p90=g.net_trader.quantile(.90),
                    p_pos=100 * (g.net_trader > 0).mean(),
                    payouts=g.payouts.mean(),
                    bust_daily_pct=100 * (g.bust_kind == "daily").sum() / max(g.busted.sum(), 1)))
a = pd.DataFrame(agg)
a.to_csv(OUT / "resume_deploye.csv", index=False)

print("\n" + "=" * 104)
print("BOOK DEPLOYE (jambes ON + ORB) vs ORB OFF — vm 1.0, WT=0 (or & J1 en regime actuel)")
print("=" * 104)
hdr = (f"{'horizon':<8}{'scenario':<14}{'N':>5}{'bust%':>8}{'net MED':>10}{'net MOY':>10}"
       f"{'p10':>9}{'p90':>10}{'P(>0)':>9}{'payouts':>9}{'bust=daily%':>13}")
print(hdr); print("-" * len(hdr))
for _, r in a.iterrows():
    print(f"{r.horizon:<8}{r.scenario:<14}{r.n:>5}{r.bust_pct:>8.1f}{r.net_med:>10.0f}"
          f"{r.net_moy:>10.0f}{r.p10:>9.0f}{r.p90:>10.0f}{r.p_pos:>8.1f}%"
          f"{r.payouts:>9.1f}{r.bust_daily_pct:>12.0f}%")

print("\n=== CONTRIBUTION DE L'ORB (delta vs ORB_OFF, meme horizon) ===")
for h in ("1an", "5ans"):
    base = a[(a.horizon == h) & (a.scenario == "ORB_OFF")].iloc[0]
    print(f"\n  {h} — baseline ORB_OFF : net med ${base.net_med:.0f}, bust {base.bust_pct:.1f} %")
    for _, r in a[(a.horizon == h) & (a.scenario != "ORB_OFF")].iterrows():
        print(f"    {r.scenario:<14} delta_net_med = {r.net_med - base.net_med:+7.0f} $"
              f"   delta_bust = {r.bust_pct - base.bust_pct:+6.1f} pt"
              f"   delta_p10 = {r.p10 - base.p10:+7.0f} $")
