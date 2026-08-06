"""Etape 1 — decomposition HORAIRE du gross de la fenetre tenue, horloge Paris/serveur.

Horloge : Europe/Paris (= Prague = serveur - 1h). Justifiee par le test L56 de
step0 (profil d'activite hiver-vs-ete : corr 0.98-0.99 en Paris, 0.49-0.77 en UTC).
C'est aussi l'horloge du schedule EA et celle du rollover serveur.

Fenetres tenues (spec v2.2) :
  US100 : 22:05 (D) -> 15:30 (E)
  GER40 : 17:35 (D) -> 09:00 (E)
Jours d'entree D = lundi + mardi. E = jour ouvre suivant (ecart 1-4 j).

Point de structure trouve en step0 : les deux CFD sont EN PAUSE de 22:50 a 00:00
Paris, toute l'annee. La derniere cotation est ~22:49, la premiere suivante ~00:05.
Le segment 22:45 -> 00:05 n'est donc PAS une heure de marche : c'est un GAP de
halt, encaisse si l'on est porte, mais impossible a trader.
"""
from __future__ import annotations
import sys, os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_m1, stamps, px_at, hac_t, ERA_CUT, EXIT  # noqa

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
os.makedirs(OUT, exist_ok=True)

# grille de checkpoints (hh, mm, day_shift_relatif_a_D, jour_de_reference)
# 'D' = jour d'entree, 'E' = jour de sortie. day_shift s'applique au jour de ref.
GRID = {
    "US100": ([(22, 5, "D", 0), (22, 45, "D", 0), (0, 5, "E", 0), (1, 5, "E", 0),
               (2, 5, "E", 0), (3, 5, "E", 0), (4, 5, "E", 0), (5, 5, "E", 0),
               (6, 5, "E", 0), (7, 5, "E", 0), (8, 5, "E", 0), (9, 5, "E", 0),
               (10, 5, "E", 0), (11, 5, "E", 0), (12, 5, "E", 0), (13, 5, "E", 0),
               (14, 5, "E", 0), (15, 5, "E", 0), (15, 30, "E", 0)]),
    "GER40": ([(17, 35, "D", 0), (18, 35, "D", 0), (19, 35, "D", 0), (20, 35, "D", 0),
               (21, 35, "D", 0), (22, 5, "D", 0), (22, 45, "D", 0), (0, 5, "E", 0),
               (1, 5, "E", 0), (2, 5, "E", 0), (3, 5, "E", 0), (4, 5, "E", 0),
               (5, 5, "E", 0), (6, 5, "E", 0), (7, 5, "E", 0), (8, 5, "E", 0),
               (9, 0, "E", 0)]),
}
# tolerance ffill SERREE : 10 min. Une tolerance de 20 min ferait remonter un
# horodatage de pause (23:05) jusqu'a la derniere cotation d'avant-pause (22:49)
# et fabriquerait un prix d'entree qui n'existe pas. Voir step2.
TOL = "10min"


def day_pairs(close: pd.Series) -> pd.DataFrame:
    days = pd.DatetimeIndex(sorted(set(close.index.normalize().tz_localize(None))))
    days = days[days.dayofweek < 5]
    nxt = pd.Series(days[1:], index=days[:-1]).reindex(days)
    gap = (nxt - pd.Series(days, index=days)).dt.days
    ok = gap.between(1, 4)
    out = pd.DataFrame({"D": days, "E": nxt.values})[ok.values].copy()
    out["dow_D"] = out["D"].dt.dayofweek
    return out[out["dow_D"].isin([0, 1])].reset_index(drop=True)


def checkpoint_prices(sym: str) -> pd.DataFrame:
    close = load_m1(sym)["close"]
    dp = day_pairs(close)
    cols = {}
    for hh, mm, ref, shift in GRID[sym]:
        base = dp["D"] if ref == "D" else dp["E"]
        # un horodatage apres minuit rattache au jour de reference J s'ecrit J+0
        # (la grille encode deja le bon jour de reference : 00:05 est sur E)
        tg = stamps(base, hh, mm, day_shift=shift)
        cols[f"{ref}_{hh:02d}{mm:02d}"] = px_at(close, tg, tol=TOL).values
    px = pd.DataFrame(cols)
    px["D"] = dp["D"].values
    px["dow_D"] = dp["dow_D"].values
    return px


def main():
    rows, cum_rows = [], []
    for sym in ("US100", "GER40"):
        px = checkpoint_prices(sym)
        names = [f"{ref}_{hh:02d}{mm:02d}" for hh, mm, ref, _ in GRID[sym]]
        px = px.dropna(subset=names).reset_index(drop=True)
        era = np.where(px["D"] < ERA_CUT, "pre-2021", "post-2021")
        entry = names[0]
        tot = np.log(px[names[-1]] / px[entry]) * 1e4
        print(f"\n[{sym}] N complet = {len(px)}  ({(era=='post-2021').sum()} post-2021)"
              f"  gross total tenu = {tot.mean():.2f} bps")

        for e in ("post-2021", "pre-2021", "TOTAL"):
            m = np.ones(len(px), bool) if e == "TOTAL" else (era == e)
            sub = px[m]
            g_tot = np.log(sub[names[-1]] / sub[entry]).values * 1e4
            mt, tt, nt = hac_t(g_tot)
            for a, b in zip(names[:-1], names[1:]):
                seg = np.log(sub[b] / sub[a]).values * 1e4
                mm_, t_, n_ = hac_t(seg)
                is_halt = (a.endswith("2245") and b.endswith("0005"))
                rows.append({"sym": sym, "era": e, "seg": f"{a}->{b}",
                             "is_halt_gap": is_halt, "mean_bps": mm_, "t_hac6": t_,
                             "N": n_, "share_of_total_pct": 100 * mm_ / mt if mt else np.nan})
                cum = np.log(sub[b] / sub[entry]).values * 1e4
                mc, tc, _ = hac_t(cum)
                cum_rows.append({"sym": sym, "era": e, "upto": b, "cum_mean_bps": mc,
                                 "cum_t_hac6": tc, "cum_share_pct": 100 * mc / mt if mt else np.nan})
            rows.append({"sym": sym, "era": e, "seg": "TOTAL_TENU", "is_halt_gap": False,
                         "mean_bps": mt, "t_hac6": tt, "N": nt, "share_of_total_pct": 100.0})

    seg = pd.DataFrame(rows); cum = pd.DataFrame(cum_rows)
    seg.to_csv(os.path.join(OUT, "step1_hourly_segments.csv"), index=False)
    cum.to_csv(os.path.join(OUT, "step1_hourly_cumulative.csv"), index=False)

    for sym in ("US100", "GER40"):
        for e in ("post-2021", "TOTAL"):
            print(f"\n=== {sym} / {e} — gross par segment (bps) et cumule ===")
            s = seg[(seg.sym == sym) & (seg.era == e)]
            c = cum[(cum.sym == sym) & (cum.era == e)].set_index("upto")
            for r in s.itertuples():
                if r.seg == "TOTAL_TENU":
                    print(f"  {'TOTAL':>16}  {r.mean_bps:7.2f} bps  t={r.t_hac6:5.2f}  N={r.N}")
                    continue
                cc = c.loc[r.seg.split('->')[1]]
                tag = "  <-- GAP DE HALT (non tradable)" if r.is_halt_gap else ""
                print(f"  {r.seg:>16}  {r.mean_bps:7.2f} bps  t={r.t_hac6:5.2f}"
                      f"   | cum {cc.cum_mean_bps:7.2f} ({cc.cum_share_pct:5.1f}%)"
                      f" t={cc.cum_t_hac6:5.2f}{tag}")


if __name__ == "__main__":
    main()
