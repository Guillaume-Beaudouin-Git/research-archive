"""Etape 4 — robustesse et geometrie de barriere.

R1. Concentration de regime : le fold 4 (COVID) porte le triple des autres. Que
    reste-t-il hors 2020 ?
R2. La restriction lundi+mardi : lundi est-il encore la bonne nuit post-2021 ?
R3. Sensibilite au cout (0.9 / 1.8 / 2.2 / 2.9 bps RT — fourchette COST_AUDIT).
R4. Geometrie de barriere : au levier DEPLOYE (on_w 0.6 x vm 14 = 8.4x de notionnel
    par jambe), quelle est la pire excursion INTRA-segment de chaque variante ?
    C'est la vraie raison d'etre d'une sortie en journee, si elle en a une.
    L54 : toute condition en drawdown s'evalue au levier DEPLOYE.
"""
from __future__ import annotations
import sys, os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "code"))
from common import (hac_t, block_bootstrap_mean, sharpe_ann, load_m1, stamps,
                    ERA_CUT, SEG, SWAP_LONG_BPS, TZ)  # noqa

OUT = os.path.join(HERE, "results")
SEGS = ["tenu", "esquive", "h24"]
DOW = {0: "lundi", 1: "mardi", 2: "mercredi", 3: "jeudi", 4: "vendredi"}
LEV = 0.6 * 14.0          # on_w x vm : notionnel/equity par jambe, config challenge
DAILY_BUDGET_BPS = 500.0  # FTMO daily loss = 5% du capital initial


def prep():
    d = pd.read_csv(os.path.join(OUT, "step1_segments.csv"), parse_dates=["D", "E"])
    d["era"] = np.where(d["D"] < ERA_CUT, "pre-2021", "post-2021")
    d["year"] = d["D"].dt.year
    for s in SEGS:
        d[f"{s}_net"] = d[s] + d[f"swap_bps_{s}"] - d["rt_bps"]
    return d


def line(x, label):
    v = np.asarray(x, float)
    v = v[np.isfinite(v)]
    m, t, n = hac_t(v)
    lo, hi, _, _ = block_bootstrap_mean(v, block=10)
    return {**label, "mean_bps": m, "t_hac6": t, "N": n,
            "boot_lo90": lo, "boot_hi90": hi}


def main():
    d = prep()
    sl = d[d["dow_D"].isin([0, 1])]

    # ---------------- R1 : hors 2020 -----------------------------------------
    print("=" * 100)
    print("R1 — CONCENTRATION DE REGIME : que reste-t-il hors 2020 ?")
    print("=" * 100)
    rows = []
    for sym, g in sl.groupby("sym"):
        for tag, gg in (("full", g), ("hors 2020", g[g.year != 2020]),
                        ("post-2021", g[g.era == "post-2021"]),
                        ("post-2021 (=hors 2020)", g[g.era == "post-2021"])):
            for s in SEGS:
                rows.append(line(gg[f"{s}_net"], {"sym": sym, "echantillon": tag,
                                                  "strategy": s}))
    r1 = pd.DataFrame(rows).drop_duplicates(subset=["sym", "echantillon", "strategy"])
    r1.to_csv(os.path.join(OUT, "step4_ex2020.csv"), index=False)
    print(r1.pivot_table(index=["sym", "strategy"], columns="echantillon",
                         values=["mean_bps", "t_hac6"]).round(2).to_string())

    # ---------------- R2 : lundi vs mardi -------------------------------------
    print("\n" + "=" * 100)
    print("R2 — LA RESTRICTION lundi+mardi : chaque nuit, TENU net, par ere")
    print("=" * 100)
    rows = []
    for (sym, dw), g in d.groupby(["sym", "dow_D"]):
        for era in ("pre-2021", "post-2021"):
            gg = g[g.era == era]
            rows.append(line(gg["tenu_net"], {"sym": sym, "nuit": DOW[dw],
                                              "dow_i": dw, "era": era}))
    r2 = pd.DataFrame(rows).sort_values(["sym", "era", "dow_i"])
    r2.to_csv(os.path.join(OUT, "step4_dow.csv"), index=False)
    print(r2.pivot_table(index=["sym", "dow_i", "nuit"], columns="era",
                         values=["mean_bps", "t_hac6", "N"]).round(2).to_string())

    # test formel : lundi post-2021 differe-t-il de mardi post-2021 ?
    print("\n  test appariE lundi vs mardi, post-2021 (TENU net) :")
    for sym in ("US100", "GER40"):
        g = d[(d["sym"] == sym) & (d.era == "post-2021")]
        lun = g[g.dow_D == 0]["tenu_net"].values
        mar = g[g.dow_D == 1]["tenu_net"].values
        ml, tl, nl = hac_t(lun)
        mm, tm, nm = hac_t(mar)
        # difference de moyennes, ecart-type combine (series non appariees en date)
        se = np.sqrt(np.var(lun, ddof=1) / len(lun) + np.var(mar, ddof=1) / len(mar))
        print(f"   {sym}: lundi {ml:+6.2f} (t {tl:+5.2f}, N {nl})  "
              f"mardi {mm:+6.2f} (t {tm:+5.2f}, N {nm})  "
              f"ecart {mm-ml:+6.2f} bps, t_ecart {(mm-ml)/se:+5.2f}")

    # ---------------- R3 : sensibilite au cout --------------------------------
    print("\n" + "=" * 100)
    print("R3 — SENSIBILITE AU COUT (fourchette COST_AUDIT indices : 0.9 a 2.9 bps RT)")
    print("=" * 100)
    rows = []
    for rt in (0.9, 1.8, 2.2, 2.9):
        for era in ("pre-2021", "post-2021", "TOTAL"):
            g = sl if era == "TOTAL" else sl[sl.era == era]
            piv = {}
            for s in SEGS:
                w = g.copy()
                w["v"] = w[s] + w[f"swap_bps_{s}"] - rt
                piv[s] = w.pivot_table(index="D", columns="sym", values="v")
            for s in SEGS:
                book = (0.6 * piv[s]["US100"] + 0.6 * piv[s]["GER40"]).dropna()
                rows.append(line(book.values, {"rt_bps": rt, "era": era, "strategy": s}))
    r3 = pd.DataFrame(rows)
    r3.to_csv(os.path.join(OUT, "step4_cost_sensitivity.csv"), index=False)
    print(r3.pivot_table(index=["strategy", "era"], columns="rt_bps",
                         values=["mean_bps", "t_hac6"]).round(2).to_string())

    # ---------------- R4 : geometrie de barriere ------------------------------
    print("\n" + "=" * 100)
    print(f"R4 — GEOMETRIE DE BARRIERE au levier DEPLOYE ({LEV:.1f}x notionnel/equity "
          f"par jambe, budget daily {DAILY_BUDGET_BPS:.0f} bps d'equity)")
    print("=" * 100)
    rows = []
    for sym in ("US100", "GER40"):
        m1 = load_m1(sym)
        low, close = m1["low"], m1["close"]
        idx = m1.index.values
        ent_h, ent_m = SEG[sym]["entry"]
        ex_h, ex_m = SEG[sym]["exit"]
        g = d[(d["sym"] == sym) & (d["dow_D"].isin([0, 1]))].copy()
        t_ent_D = stamps(pd.DatetimeIndex(g["D"]), ent_h, ent_m).values
        t_ex_E = stamps(pd.DatetimeIndex(g["E"]), ex_h, ex_m).values
        t_ent_E = stamps(pd.DatetimeIndex(g["E"]), ent_h, ent_m).values
        lo_v = low.values

        def worst(t0, t1, p0):
            a = np.searchsorted(idx, t0, side="left")
            b = np.searchsorted(idx, t1, side="right")
            out = np.full(len(a), np.nan)
            for i, (x, y) in enumerate(zip(a, b)):
                if y > x:
                    out[i] = np.log(lo_v[x:y].min() / p0[i]) * 1e4
            return out

        p0 = g["p_ent_D"].values
        g["exc_tenu"] = worst(t_ent_D, t_ex_E, p0)
        g["exc_h24"] = worst(t_ent_D, t_ent_E, p0)
        g["exc_esquive"] = worst(t_ex_E, t_ent_E, g["p_ex_E"].values)
        for s in SEGS:
            v = g[f"exc_{s}"].dropna().values
            r = g[f"{s}_net"].dropna().values
            rows.append({
                "sym": sym, "strategy": s, "N": len(v),
                "excursion_moy_bps": v.mean(), "excursion_p05_bps": np.percentile(v, 5),
                "excursion_p01_bps": np.percentile(v, 1), "excursion_min_bps": v.min(),
                "ret_p01_bps": np.percentile(r, 1), "ret_min_bps": r.min(),
                "skew": float(pd.Series(r).skew()), "kurt": float(pd.Series(r).kurt()),
                # au levier deploye : part des evenements ou la seule jambe consomme
                # tout le budget daily
                "pct_excursion_gt_budget": float(np.mean(v * LEV < -DAILY_BUDGET_BPS)),
                "pire_excursion_pct_equity": v.min() * LEV / 100.0,
            })
        g.to_csv(os.path.join(OUT, f"step4_excursions_{sym}.csv"), index=False)
    r4 = pd.DataFrame(rows)
    r4.to_csv(os.path.join(OUT, "step4_barrier_geometry.csv"), index=False)
    print(r4.round(2).to_string(index=False))
    print("\n  NB: excursion mesuree sur les LOW M1 depuis le prix d'entree (L59 : la "
          "sortie doit etre re-pricee separement ; ici on ne modelise aucun stop).")


if __name__ == "__main__":
    main()
