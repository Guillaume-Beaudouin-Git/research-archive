"""Etape 5 — excursion de BOOK (les deux jambes ensemble), au levier deploye.

Pourquoi cette etape : la barriere FTMO ne voit pas une jambe, elle voit l'equity.
Verifie dans le moteur qui pilote le live (cleanroom/engine.py:249) :

    limit = bal - DAILY_BUDGET          # bal = BALANCE (positions closes)
    eq    = bal + _mtm(pos, avg, px)    # MTM depuis le prix d'ENTREE (avg)

=> la perte latente accumulee depuis l'ENTREE compte contre le budget du jour
   suivant sans aucune remise a zero a minuit. Il n'y a donc PAS d'avantage
   geometrique "le segment overnight enjambe le reset de 00:00 Prague" : la bonne
   metrique de barriere est bien l'excursion depuis l'entree, et c'est elle qu'on
   mesure ici, sur la SOMME des deux jambes.

Grille 5 minutes, jambes ponderees on_w=0.6 x vm=14 (= 8.4x notionnel/equity).
"""
from __future__ import annotations
import sys, os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "code"))
from common import load_m1, stamps, SEG, ERA_CUT, TZ  # noqa

OUT = os.path.join(HERE, "results")
LEV = 0.6 * 14.0
GRID = "5min"


def leg_paths(sym):
    m1 = load_m1(sym)
    s = m1["close"].resample(GRID).last().ffill(limit=12)
    return s


def main():
    seg = pd.read_csv(os.path.join(OUT, "step1_segments.csv"), parse_dates=["D", "E"])
    seg = seg[seg["dow_D"].isin([0, 1])]
    piv_ent = seg.pivot_table(index="D", columns="sym", values="p_ent_D")
    E = seg.groupby("D")["E"].first()
    keep = piv_ent.dropna().index.intersection(E.index)
    piv_ent, E = piv_ent.loc[keep], E.loc[keep]

    px = {s: leg_paths(s) for s in ("US100", "GER40")}
    ent = {s: SEG[s]["entry"] for s in SEG}
    ex = {s: SEG[s]["exit"] for s in SEG}

    rows = []
    for D, Ed in E.items():
        r = {"D": D, "E": Ed}
        # bornes de la fenetre de book : la premiere entree (GER40 17:35) jusqu'a
        # la derniere sortie (US100 15:30 le lendemain) / derniere entree (24h)
        w0 = pd.Timestamp(D.year, D.month, D.day, *ent["GER40"], tz=TZ)
        w1_tenu = pd.Timestamp(Ed.year, Ed.month, Ed.day, *ex["US100"], tz=TZ)
        w1_h24 = pd.Timestamp(Ed.year, Ed.month, Ed.day, *ent["GER40"], tz=TZ)
        for variant, w1 in (("tenu", w1_tenu), ("h24", w1_h24)):
            grid = pd.date_range(w0, w1, freq=GRID, tz=TZ)
            tot = np.zeros(len(grid))
            okall = True
            for s in ("US100", "GER40"):
                p0 = piv_ent.loc[D, s]
                t_in = pd.Timestamp(D.year, D.month, D.day, *ent[s], tz=TZ)
                if variant == "tenu":
                    t_out = pd.Timestamp(Ed.year, Ed.month, Ed.day, *ex[s], tz=TZ)
                else:
                    t_out = w1
                path = px[s].reindex(grid).ffill(limit=3)
                mtm = (np.log(path.values / p0) * 1e4) * 0.6
                live = (grid >= t_in) & (grid <= t_out)
                mtm = np.where(live & np.isfinite(mtm), mtm, 0.0)
                if np.isnan(p0):
                    okall = False
                tot = tot + mtm
            if not okall or len(grid) == 0:
                continue
            r[f"exc_{variant}"] = float(tot.min())     # bps d'equity pre-vm
            r[f"end_{variant}"] = float(tot[-1])
        rows.append(r)

    df = pd.DataFrame(rows).dropna(subset=["exc_tenu", "exc_h24"])
    df["era"] = np.where(df["D"] < ERA_CUT, "pre-2021", "post-2021")
    df.to_csv(os.path.join(OUT, "step5_book_excursion.csv"), index=False)

    out = []
    for era in ("pre-2021", "post-2021", "TOTAL"):
        g = df if era == "TOTAL" else df[df.era == era]
        for v in ("tenu", "h24"):
            x = g[f"exc_{v}"].values * LEV / 100.0        # % d'equity au levier deploye
            out.append({"era": era, "variante": v, "N": len(x),
                        "exc_moy_%eq": x.mean(), "exc_p05_%eq": np.percentile(x, 5),
                        "exc_p01_%eq": np.percentile(x, 1), "exc_pire_%eq": x.min(),
                        "part_evts_exc_lt_-5%": float(np.mean(x < -5.0)),
                        "part_evts_exc_lt_-10%": float(np.mean(x < -10.0))})
    res = pd.DataFrame(out)
    res.to_csv(os.path.join(OUT, "step5_book_excursion_summary.csv"), index=False)
    print("=" * 100)
    print("EXCURSION DE BOOK (2 jambes) au levier deploye 8.4x — % d'equity")
    print("barrieres FTMO : daily -5% (capital initial), floor -10%")
    print("=" * 100)
    print(res.round(2).to_string(index=False))

    print("\n--- difference appariee des excursions (h24 - tenu), meme evenement ---")
    for era in ("pre-2021", "post-2021", "TOTAL"):
        g = df if era == "TOTAL" else df[df.era == era]
        d = (g["exc_h24"] - g["exc_tenu"]).values * LEV / 100.0
        print(f"  {era:10s} moyenne {d.mean():+6.2f} pt d'equity   "
              f"p05 {np.percentile(d, 5):+6.2f}   pire {d.min():+7.2f}   "
              f"part strictement pire {float(np.mean(d < 0)):.1%}")


if __name__ == "__main__":
    main()
