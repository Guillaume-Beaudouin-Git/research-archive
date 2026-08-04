"""Etape 2 — tableaux : segment x ere, segment x annee, segment x jour de la semaine.

Le tableau de tete est restreint aux jours d'entree REELLEMENT tenus par le sleeve
(lundi + mardi, ON[dayofweek in {0,1}]). Les cinq nuits sont mesurees separement
en §3 : la restriction lundi+mardi n'a jamais ete auditee.
"""
from __future__ import annotations
import sys, os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import hac_t, block_bootstrap_mean, load_m1, ERA_CUT, SWAP_LONG_BPS, RT_BPS  # noqa

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "results")
SEGS = ["tenu", "esquive", "h24"]
DOW = {0: "lundi", 1: "mardi", 2: "mercredi", 3: "jeudi", 4: "vendredi"}


def net(d: pd.DataFrame, seg: str) -> pd.Series:
    return d[seg] + d[f"swap_bps_{seg}"] - d["rt_bps"]


def describe(x: pd.Series, label: dict) -> dict:
    m, t, n = hac_t(x.values)
    lo90, hi90, _, _ = block_bootstrap_mean(x.values, block=10)
    return {**label, "mean_bps": m, "t_hac6": t, "N": n,
            "boot_lo90": lo90, "boot_hi90": hi90,
            "hit_rate": float((x > 0).mean()), "sd_bps": float(x.std(ddof=1))}


def main():
    d = pd.read_csv(os.path.join(OUT, "step1_segments.csv"), parse_dates=["D", "E"])
    d["era"] = np.where(d["D"] < ERA_CUT, "pre-2021", "post-2021")
    d["year"] = d["D"].dt.year
    for s in SEGS:
        d[f"{s}_net"] = net(d, s)

    sleeve = d[d["dow_D"].isin([0, 1])].copy()      # lundi + mardi = ON du spec

    # ---- 1. tableau de tete : 3 lignes x 2 eres, par instrument -----------------
    rows = []
    for sym, g in sleeve.groupby("sym"):
        for era in ("pre-2021", "post-2021", "TOTAL"):
            gg = g if era == "TOTAL" else g[g["era"] == era]
            for s in SEGS:
                rows.append(describe(gg[s], {"sym": sym, "era": era, "segment": s, "basis": "gross"}))
                rows.append(describe(gg[f"{s}_net"], {"sym": sym, "era": era, "segment": s, "basis": "net"}))
    head = pd.DataFrame(rows)
    head.to_csv(os.path.join(OUT, "step2_head_era.csv"), index=False)

    print("=" * 100)
    print("TABLEAU DE TETE — jours d'entree lundi+mardi (le sleeve deploye)")
    print("=" * 100)
    for basis in ("gross", "net"):
        print(f"\n--- {basis.upper()} (bps par evenement) ---")
        p = head[head["basis"] == basis].pivot_table(
            index=["sym", "segment"], columns="era",
            values=["mean_bps", "t_hac6", "N"])
        p = p.reindex(columns=["pre-2021", "post-2021", "TOTAL"], level=1)
        print(p.round(2).to_string())

    # ---- 2. par annee ----------------------------------------------------------
    rows = []
    for (sym, yr), g in sleeve.groupby(["sym", "year"]):
        for s in SEGS:
            rows.append(describe(g[s], {"sym": sym, "year": yr, "segment": s, "basis": "gross"}))
            rows.append(describe(g[f"{s}_net"], {"sym": sym, "year": yr, "segment": s, "basis": "net"}))
    yr_tab = pd.DataFrame(rows)
    yr_tab.to_csv(os.path.join(OUT, "step2_by_year.csv"), index=False)
    print("\n--- GROSS par annee, moyenne bps (lundi+mardi) ---")
    print(yr_tab[yr_tab.basis == "gross"].pivot_table(
        index="year", columns=["sym", "segment"], values="mean_bps").round(2).to_string())

    # ---- 3. les CINQ nuits separement (la restriction jamais auditee) ----------
    rows = []
    for (sym, dw), g in d.groupby(["sym", "dow_D"]):
        for era in ("pre-2021", "post-2021", "TOTAL"):
            gg = g if era == "TOTAL" else g[g["era"] == era]
            if len(gg) < 20:
                continue
            for s in SEGS:
                rows.append(describe(gg[f"{s}_net"],
                                     {"sym": sym, "dow": DOW[dw], "dow_i": dw,
                                      "era": era, "segment": s, "basis": "net"}))
                rows.append(describe(gg[s],
                                     {"sym": sym, "dow": DOW[dw], "dow_i": dw,
                                      "era": era, "segment": s, "basis": "gross"}))
    dow_tab = pd.DataFrame(rows).sort_values(["sym", "segment", "dow_i"])
    dow_tab.to_csv(os.path.join(OUT, "step2_by_dow.csv"), index=False)
    print("\n--- TENU net par nuit d'entree (bps) ---")
    t = dow_tab[(dow_tab.segment == "tenu") & (dow_tab.basis == "net")]
    print(t.pivot_table(index=["sym", "dow_i", "dow"], columns="era",
                        values=["mean_bps", "t_hac6", "N"]).round(2).to_string())

    # ---- 4. desalignement DST CET/ET (L56 applique a la PRODUCTION) ------------
    rows = []
    for (sym, mis), g in sleeve.groupby(["sym", "dst_mismatch"]):
        rows.append(describe(g["tenu"], {"sym": sym, "dst_mismatch": bool(mis),
                                         "segment": "tenu", "basis": "gross"}))
    dst = pd.DataFrame(rows)
    dst.to_csv(os.path.join(OUT, "step2_dst_mismatch.csv"), index=False)
    print("\n--- L56 : semaines ou 22:05 CET n'est PAS 16:05 ET (decalage DST) ---")
    print(dst.round(2).to_string(index=False))

    # ---- 5. L56 corollaire : part du GAP de halt CFD dans le segment tenu ------
    rows = []
    for sym in ("US100", "GER40"):
        m1 = load_m1(sym)["close"]
        idx = m1.index
        key = pd.Series(idx.normalize().tz_localize(None), index=idx)
        before = m1[(idx.hour == 22) | ((idx.hour == 21) & (idx.minute >= 30))]
        after = m1[(idx.hour == 23) | ((idx.hour == 0) & (idx.minute <= 30))]
        lb = before.groupby(before.index.normalize().tz_localize(None)).last()
        # la premiere barre apres 23:00 appartient au meme jour calendaire si h==23
        aidx = after.index
        aday = pd.DatetimeIndex(np.where(aidx.hour == 23, aidx.normalize(),
                                         aidx.normalize() - pd.Timedelta(days=1))).tz_localize(None)
        fa = pd.Series(after.values, index=aday).groupby(level=0).first()
        gap = (np.log(fa / lb) * 1e4).dropna()
        g = sleeve[sleeve["sym"] == sym].set_index("D")
        j = g.join(gap.rename("halt_gap"), how="inner").dropna(subset=["halt_gap"])
        rows.append({"sym": sym, "N": len(j),
                     "mean_tenu_bps": j["tenu"].mean(),
                     "mean_halt_gap_bps": j["halt_gap"].mean(),
                     "share_of_tenu": j["halt_gap"].mean() / j["tenu"].mean()
                     if j["tenu"].mean() != 0 else np.nan,
                     "share_abs": j["halt_gap"].abs().sum() / j["tenu"].abs().sum()})
    hg = pd.DataFrame(rows)
    hg.to_csv(os.path.join(OUT, "step2_halt_gap.csv"), index=False)
    print("\n--- L56 corollaire : part du gap de halt CFD (23:00 CET) dans le TENU ---")
    print(hg.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
