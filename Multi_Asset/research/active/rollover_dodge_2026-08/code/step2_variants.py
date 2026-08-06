"""Etape 2 — variantes d'heure d'entree, comparaison APPARIEE (memes dates, meme sortie).

Sortie INVARIANTE entre variantes (US100 15:30, GER40 09:00) : la comparaison est
donc a geometrie de sortie constante (L59). Seule l'ENTREE bouge.

Comptabilite du swap. Rollover FTMO = 00:00 serveur = 23:00 Paris (serveur = Paris+1h,
verifie ts_server 17:14 / ts_paris 16:14). Une entree AVANT 23:00 Paris est ouverte au
rollover -> 1 nuit facturee. Une entree APRES est ouverte apres -> 0 nuit, et la sortie
(15:30 / 09:00 le lendemain) precede largement le rollover suivant.

Mais step0 a montre que le CFD est EN PAUSE de 22:50 a 00:00 Paris : il n'existe aucune
cotation entre les deux. Deux variantes 23:05 sont donc calculees :
  - '2305_PHANTOM' : prix obtenu par ffill a 20 min, c.-a-d. la DERNIERE cotation
    d'avant-pause (~22:49). C'est ce qu'un script naif produit. NON EXECUTABLE : cet
    ordre ne peut pas etre rempli, et s'il repose il sera rempli a la reouverture.
    Cette ligne existe pour montrer le faux PASS, pas pour etre citee.
  - '0005' : la premiere cotation apres la pause. C'est la SEULE facon reelle
    d'etre en position apres le rollover.
"""
from __future__ import annotations
import sys, os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (load_m1, stamps, px_at, hac_t, block_bootstrap_mean, sharpe_ann,
                    ERA_CUT, EXIT, RT_BPS, SWAP_LONG_BPS, SWAP_LIVE_BPS)  # noqa

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")

# nom -> (hh, mm, jour_de_reference, tolerance, nuits_de_swap, executable)
VARIANTS = {
    "1735":         (17, 35, "D", "10min", 1.0, True),    # live GER40
    "2205":         (22,  5, "D", "10min", 1.0, True),    # live US100
    "2235":         (22, 35, "D", "10min", 1.0, True),
    "2245":         (22, 45, "D", "10min", 1.0, True),    # derniere cotation avant pause
    "2305_PHANTOM": (23,  5, "D", "25min", 0.0, False),   # ffill -> prix de ~22:45
    "0005":         (0,   5, "E", "10min", 0.0, True),    # reouverture = vraie esquive
    "0035":         (0,  35, "E", "10min", 0.0, True),
    "0105":         (1,   5, "E", "10min", 0.0, True),
}
LIVE = {"US100": "2205", "GER40": "1735"}
DODGE = "0005"
W = 0.6   # weight_per_leg du spec v2.2


def day_pairs(close):
    days = pd.DatetimeIndex(sorted(set(close.index.normalize().tz_localize(None))))
    days = days[days.dayofweek < 5]
    nxt = pd.Series(days[1:], index=days[:-1]).reindex(days)
    gap = (nxt - pd.Series(days, index=days)).dt.days
    out = pd.DataFrame({"D": days, "E": nxt.values})[gap.between(1, 4).values].copy()
    out["dow_D"] = out["D"].dt.dayofweek
    return out[out["dow_D"].isin([0, 1])].reset_index(drop=True)


def leg_table(sym: str) -> pd.DataFrame:
    df = load_m1(sym)
    close = df["close"]
    dp = day_pairs(close)
    exh, exm = EXIT[sym]
    p_exit = px_at(close, stamps(dp["E"], exh, exm), tol="20min").values
    out = pd.DataFrame({"D": dp["D"].values, "p_exit": p_exit})
    for name, (hh, mm, ref, tol, _, _) in VARIANTS.items():
        base = dp["D"] if ref == "D" else dp["E"]
        out[f"p_{name}"] = px_at(close, stamps(base, hh, mm), tol=tol).values
    for name in VARIANTS:
        out[f"g_{name}"] = np.log(out["p_exit"] / out[f"p_{name}"]) * 1e4
    return out


def net_of(gross, sym, nights, swap_tbl, rt_mult=1.0):
    return gross + nights * swap_tbl[sym] - RT_BPS[sym] * rt_mult


def main():
    legs = {s: leg_table(s).set_index("D") for s in ("US100", "GER40")}
    idx_all = legs["US100"].index.intersection(legs["GER40"].index)
    for s in legs:
        legs[s] = legs[s].loc[idx_all]

    def sel(cols_by_leg, era_key):
        """Sous-echantillon APPARIE : lignes ou toutes les colonnes demandees
        existent sur les deux jambes. cols_by_leg = {leg: [gcol, ...]}."""
        m = pd.Series(True, index=idx_all)
        for lg, cs in cols_by_leg.items():
            m &= legs[lg][cs].notna().all(axis=1)
        if era_key == "post-2021":
            m &= pd.Series(idx_all >= ERA_CUT, index=idx_all)
        return idx_all[m.values]

    years_all = (idx_all.max() - idx_all.min()).days / 365.25
    print(f"univers lun+mar, 2 jambes cotees a la sortie : N={len(idx_all)}"
          f"  {idx_all.min().date()} -> {idx_all.max().date()}")
    for v in VARIANTS:
        n1 = sel({"US100": [f"g_{v}"], "GER40": [f"g_{v}"]}, "post-2021")
        print(f"   variant {v:14s} executable={str(VARIANTS[v][5]):5s} "
              f"N_post2021_apparie={len(n1)}")

    rows = []
    for swap_name, swap_tbl in (("ancre_spec", SWAP_LONG_BPS), ("live_mesure", SWAP_LIVE_BPS),
                                ("live_+17pct", {k: v * 1.17 for k, v in SWAP_LIVE_BPS.items()})):
        for v in VARIANTS:
            nights, execu = VARIANTS[v][4], VARIANTS[v][5]
            for e in ("post-2021", "TOTAL"):
                ii = sel({"US100": [f"g_{v}"], "GER40": [f"g_{v}"]}, e)
                gU = legs["US100"].loc[ii, f"g_{v}"].values
                gG = legs["GER40"].loc[ii, f"g_{v}"].values
                nU = net_of(gU, "US100", nights, swap_tbl)
                nG = net_of(gG, "GER40", nights, swap_tbl)
                opy = len(ii) / max(years_all, 1e-9)
                for leg, g, n in (("US100", gU, nU), ("GER40", gG, nG),
                                  ("BOOK", W * (gU + gG), W * (nU + nG))):
                    mg, tg, N = hac_t(g)
                    mn, tn, _ = hac_t(n)
                    lo90, hi90, _, _ = block_bootstrap_mean(n, block=10)
                    rows.append({"swap_hyp": swap_name, "variant": v, "executable": execu,
                                 "leg": leg, "era": e, "N": N,
                                 "gross_bps": mg, "t_gross": tg,
                                 "swap_bps": nights * (W * (swap_tbl["US100"] + swap_tbl["GER40"])
                                                       if leg == "BOOK" else swap_tbl[leg]),
                                 "rt_bps": -(W * 2 * 1.8 if leg == "BOOK" else 1.8),
                                 "net_bps": mn, "t_net": tn,
                                 "sharpe_ann": sharpe_ann(n / 1e4, opy),
                                 "boot_lo90": lo90, "boot_hi90": hi90})
    res = pd.DataFrame(rows)
    res.to_csv(os.path.join(OUT, "step2_variants.csv"), index=False)

    # ---- difference APPARIEE : chaque variante -> le dodge 00:05 ----------------
    drows = []
    for swap_name, swap_tbl in (("ancre_spec", SWAP_LONG_BPS), ("live_mesure", SWAP_LIVE_BPS)):
        for v in VARIANTS:
            if v == DODGE:
                continue
            nights_v = VARIANTS[v][4]
            for e in ("post-2021", "TOTAL"):
                ii = sel({"US100": [f"g_{v}", f"g_{DODGE}"],
                          "GER40": [f"g_{v}", f"g_{DODGE}"]}, e)
                dU = (net_of(legs["US100"].loc[ii, f"g_{DODGE}"].values, "US100", 0.0, swap_tbl)
                      - net_of(legs["US100"].loc[ii, f"g_{v}"].values, "US100", nights_v, swap_tbl))
                dG = (net_of(legs["GER40"].loc[ii, f"g_{DODGE}"].values, "GER40", 0.0, swap_tbl)
                      - net_of(legs["GER40"].loc[ii, f"g_{v}"].values, "GER40", nights_v, swap_tbl))
                for leg, d in (("US100", dU), ("GER40", dG), ("BOOK", W * (dU + dG))):
                    md, td, N = hac_t(d)
                    lo90, hi90, lo95, hi95 = block_bootstrap_mean(d, block=10)
                    drows.append({"swap_hyp": swap_name, "from_variant": v, "to_variant": DODGE,
                                  "executable_from": VARIANTS[v][5], "leg": leg, "era": e,
                                  "N": N, "delta_net_bps": md, "t_hac6": td,
                                  "frac_days_better": float(np.mean(d > 0)),
                                  "boot_lo90": lo90, "boot_hi90": hi90,
                                  "boot_lo95": lo95, "boot_hi95": hi95})
    dif = pd.DataFrame(drows)
    dif.to_csv(os.path.join(OUT, "step2_paired_delta.csv"), index=False)

    # ---- affichage --------------------------------------------------------------
    pd.set_option("display.width", 200)
    for e in ("post-2021", "TOTAL"):
        print(f"\n=== BALAYAGE de l'heure d'entree — BOOK, {e}, swap=ancre_spec ===")
        s = res[(res.leg == "BOOK") & (res.era == e) & (res.swap_hyp == "ancre_spec")]
        print(s[["variant", "executable", "N", "gross_bps", "t_gross", "swap_bps",
                 "rt_bps", "net_bps", "t_net", "boot_lo90", "boot_hi90"]]
              .to_string(index=False, float_format=lambda x: f"{x:7.2f}"))

    print("\n=== TABLE APPARIEE, PAR JAMBE : chaque jambe a son heure LIVE ===")
    for e in ("post-2021", "TOTAL"):
        for swap_name in ("ancre_spec", "live_mesure"):
            print(f"\n-- {e}, swap {swap_name} --")
            for leg in ("US100", "GER40"):
                for r in dif[(dif.leg == leg) & (dif.era == e) & (dif.swap_hyp == swap_name)
                             & (dif.from_variant == LIVE[leg])].itertuples():
                    print(f"  {leg:6s} {LIVE[leg]}->00:05  delta_net = {r.delta_net_bps:+7.2f} bps"
                          f"  t={r.t_hac6:+5.2f}  N={r.N}  jours_ameliores={r.frac_days_better:.0%}"
                          f"  IC90 [{r.boot_lo90:+6.2f} ; {r.boot_hi90:+6.2f}]")
                for r in res[(res.leg == leg) & (res.era == e) & (res.swap_hyp == swap_name)
                             & res.variant.isin([LIVE[leg], DODGE])].itertuples():
                    print(f"        {r.variant:14s} gross {r.gross_bps:6.2f} (t {r.t_gross:5.2f})"
                          f"  swap {r.swap_bps:6.2f}  RT {r.rt_bps:5.2f}"
                          f"  net {r.net_bps:6.2f} (t {r.t_net:5.2f})  N={r.N}")

    print("\n=== Le faux PASS : 2305_PHANTOM vs la reouverture reelle 00:05 ===")
    for leg in ("US100", "GER40"):
        s = res[(res.leg == leg) & (res.era == "post-2021") & (res.swap_hyp == "ancre_spec")
                & res.variant.isin([LIVE[leg], "2245", "2305_PHANTOM", "0005"])]
        print(f"-- {leg} post-2021 --")
        print(s[["variant", "executable", "N", "gross_bps", "t_gross", "swap_bps",
                 "net_bps", "t_net"]].to_string(index=False, float_format=lambda x: f"{x:7.2f}"))


if __name__ == "__main__":
    main()
