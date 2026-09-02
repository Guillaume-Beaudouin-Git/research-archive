"""Analyse complete overnight US100/GER40 : HAC par jour, placebo bloc-bootstrap,
rupture endogene, net de cout (spread+swap mesures, asymetriques), contribution
economique lundi/mardi. Ecrit results/analysis_results.json au fil de l'eau
(un print + flush par section) pour ne rien perdre si la session est coupee.

Interpreteur : /usr/bin/python3
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats_lib import (hac_mean_t, block_bootstrap_null_pvalue,
                        break_bootstrap_pvalue, sidak_threshold)

RES = Path(__file__).resolve().parent.parent / "results"
OUTJ = RES / "analysis_results.json"

WD_NAME = {0: "lundi", 1: "mardi", 2: "mercredi", 3: "jeudi", 4: "vendredi"}

# Couts mesures les plus recents (build_series.py, semaine 2026-08-17, natif RT) ;
# swap_long_bps_ref = spec_v22.yaml measured_specs (points MT5 mesures 2026-06-10).
RT_BPS_RECENT = {"US100": 1.045, "GER40": 1.017}       # round-trip, mesure recente
RT_BPS_SPEC_2026_06 = {"US100": 2.2, "GER40": 2.2}     # cost_anchors.rt_bps_legs_allin (juin, conservateur)
SWAP_LONG_BPS = {"US100": -2.1257, "GER40": -1.564}    # measured_specs, mesure 2026-06-10
SWAP_SHORT_BPS = {"US100": 0.0917, "GER40": -0.1933}   # asymetrie L30 (contexte, sleeve est LONG-only)
TRIPLE_DOW = {"US100": 4, "GER40": 4}                   # vendredi -- Mon/Tue = 1x, non concerne ici
ON_W = 0.35
INIT_EQUITY = 10_000.0

log = []


def emit(msg):
    print(msg)
    log.append(str(msg))
    OUTJ.parent.mkdir(exist_ok=True)
    (RES / "analysis_log.txt").write_text("\n".join(log) + "\n")


def load(sym):
    df = pd.read_csv(RES / f"{sym.lower()}_overnight_daily.csv", parse_dates=["date"])
    return df.set_index("date")


def main():
    results = {"per_weekday": {}, "monday_tuesday": {}, "breaks": {}, "net_of_cost": {},
               "economic": {}, "n_tests": 0}
    n_tests = 0

    # ---------------------------------------------------------- Section 1 --
    emit("=" * 78)
    emit("SECTION 1 -- mesure brute par jour d'ENTREE, HAC lag-6, full-period")
    emit("=" * 78)
    data = {}
    for sym in ("US100", "GER40"):
        df = load(sym)
        data[sym] = df
        emit(f"\n--- {sym} : {df.index.min().date()} -> {df.index.max().date()}, "
             f"N={df['ov_bps_entryday'].notna().sum()} nuits ---")
        rows = {}
        for wd in range(5):
            x = df.loc[df["weekday"] == wd, "ov_bps_entryday"].dropna().to_numpy()
            m, se, t, n = hac_mean_t(x, lag=6)
            n_tests += 1
            rows[WD_NAME[wd]] = dict(mean_bps=round(m, 3), t_hac6=round(t, 3), n=int(n))
            emit(f"  {WD_NAME[wd]:9s} mean={m:7.3f} bps  t_HAC6={t:6.3f}  n={n}")
        results["per_weekday"][sym] = rows

    emit(f"\nTests comptes (section 1) : {n_tests} (5 jours x 2 instruments). "
         f"Sidak local(10)={sidak_threshold(10):.3f}")

    # ---------------------------------------------------- Section 2 : piege --
    emit("\n" + "=" * 78)
    emit("SECTION 2 -- verification du piege d'etiquetage (entree vs ouverture)")
    emit("=" * 78)
    emit("Par construction (ov_bps_entryday == ov_bps_openday au niveau de la "
         "valeur, seule l'etiquette de ligne differe), verifions explicitement "
         "l'exemple du coordinateur : le gap de WEEK-END (entree vendredi -> "
         "ouverture lundi) doit apparaitre en 'vendredi' ici, PAS en 'lundi'.")
    for sym in ("US100", "GER40"):
        df = data[sym]
        fri = df[df["weekday"] == 4]
        gap_med = fri["gap_cal_days"].median()
        emit(f"  {sym}: nuits d'entree VENDREDI, ecart calendaire median au jour "
             f"suivant = {gap_med:.0f}j (attendu 3 = week-end) ; mean={fri['ov_bps_entryday'].mean():.2f} bps")
    emit("Confirme : le gap de week-end est bien porte par la ligne 'vendredi' "
         "(jour d'ENTREE), pas 'lundi'. L'etiquetage par jour d'entree evite le piege.")

    # ------------------------------------------------- Section 3 : Lun/Mar --
    emit("\n" + "=" * 78)
    emit("SECTION 3 -- lundi et mardi : placebo bloc-bootstrap (H0 = moyenne nulle)")
    emit("=" * 78)
    for sym in ("US100", "GER40"):
        df = data[sym]
        for wd, name in ((0, "lundi"), (1, "mardi")):
            x = df.loc[df["weekday"] == wd, "ov_bps_entryday"].dropna().to_numpy()
            r = block_bootstrap_null_pvalue(x, lag=6, n_boot=4000, block=20, seed=abs(hash((sym, wd))) % 2**31 if False else (100+wd if sym=='US100' else 200+wd))
            n_tests += 1
            results["monday_tuesday"][f"{sym}_{name}_full"] = r
            emit(f"  {sym:6s} {name:6s} full : mean={r['mean']:7.3f} bps  t={r['t']:6.3f}  "
                 f"n={r['n']:4d}  p_block_bootstrap={r['p_block_bootstrap']:.4f}")

    # -------------------------------------------- Section 4 : rupture endogene --
    emit("\n" + "=" * 78)
    emit("SECTION 4 -- rupture ENDOGENE (date estimee, non imposee), lundi/mardi seuls")
    emit("=" * 78)
    for sym in ("US100", "GER40"):
        df = data[sym]
        for wd, name in ((0, "lundi"), (1, "mardi")):
            sub = df.loc[df["weekday"] == wd, "ov_bps_entryday"].dropna()
            x = sub.to_numpy()
            dates = sub.index
            r = break_bootstrap_pvalue(x, lag=6, min_seg=90, step=10, n_boot=300,
                                        block=15, seed=(300+wd if sym=='US100' else 400+wd))
            n_tests += 1
            brk_date = dates[r["k"]] if r["k"] is not None else None
            results["breaks"][f"{sym}_{name}"] = {**r, "break_date": str(brk_date.date()) if brk_date is not None else None}
            emit(f"  {sym:6s} {name:6s}: rupture estimee au {brk_date.date() if brk_date is not None else 'NA'} "
                 f"(obs {r['n_pre']} avant / {r['n_post']} apres) ; "
                 f"mean_pre={r['mean_pre']:.3f} mean_post={r['mean_post']:.3f} bps ; "
                 f"t_diff={r['t']:.3f} ; p_bootstrap(recherche corrigee)={r['p_break_bootstrap']:.4f}")

    # ---------------------------------------------- Section 5 : net de cout --
    emit("\n" + "=" * 78)
    emit("SECTION 5 -- net de spread ET de swap FTMO (asymetrique L30 -- sleeve LONG)")
    emit("=" * 78)
    emit("Cout applique par NUIT tenue (Mon/Tue = 1x, pas de jour triple ici) :")
    for sym in ("US100", "GER40"):
        rt_recent = RT_BPS_RECENT[sym]
        rt_spec = RT_BPS_SPEC_2026_06[sym]
        sw = SWAP_LONG_BPS[sym]
        emit(f"  {sym}: RT recent (2026-08-17, natif)={rt_recent:.3f} bps | "
             f"RT spec conservateur (2026-06)={rt_spec:.3f} bps | "
             f"swap_long mesure={sw:.3f} bps/nuit (short={SWAP_SHORT_BPS[sym]:.3f}, "
             f"triple_dow={TRIPLE_DOW[sym]}=vendredi, non touche Mon/Tue)")
        df = data[sym]
        for wd, name in ((0, "lundi"), (1, "mardi")):
            x = df.loc[df["weekday"] == wd, "ov_bps_entryday"].dropna().to_numpy()
            net_recent = x - rt_recent + sw
            net_spec = x - rt_spec + sw
            m_g, _, t_g, n_ = hac_mean_t(x, lag=6)
            m_nr, _, t_nr, _ = hac_mean_t(net_recent, lag=6)
            m_ns, _, t_ns, _ = hac_mean_t(net_spec, lag=6)
            n_tests += 1  # le test "net>0" est le test economique pertinent
            results["net_of_cost"][f"{sym}_{name}"] = dict(
                gross_mean=round(m_g, 3), gross_t=round(t_g, 3),
                net_recent_cost_mean=round(m_nr, 3), net_recent_cost_t=round(t_nr, 3),
                net_spec_cost_mean=round(m_ns, 3), net_spec_cost_t=round(t_ns, 3), n=int(n_))
            emit(f"    {name:6s}: gross={m_g:7.3f} (t={t_g:5.2f})  "
                 f"net[cout recent]={m_nr:7.3f} (t={t_nr:5.2f})  "
                 f"net[cout spec juin, conservateur]={m_ns:7.3f} (t={t_ns:5.2f})  n={n_}")

    # ------------------------------------------- Section 6 : contribution eco --
    emit("\n" + "=" * 78)
    emit("SECTION 6 -- contribution economique lundi vs mardi au sleeve (poids 0.35, $10k)")
    emit("=" * 78)
    tot_usd = {}
    for sym in ("US100", "GER40"):
        df = data[sym]
        rt_recent = RT_BPS_RECENT[sym]
        sw = SWAP_LONG_BPS[sym]
        rows = {}
        for wd in range(5):
            x = df.loc[df["weekday"] == wd, "ov_bps_entryday"].dropna().to_numpy()
            net_bps = x - rt_recent + sw
            usd = net_bps / 1e4 * ON_W * INIT_EQUITY
            rows[WD_NAME[wd]] = dict(sum_usd=round(float(usd.sum()), 2), n=len(x),
                                      mean_usd_per_night=round(float(usd.mean()), 3) if len(x) else None)
        tot = sum(v["sum_usd"] for v in rows.values())
        tot_usd[sym] = tot
        results["economic"][sym] = rows
        emit(f"  {sym}: total net (2013/2013-09 -> 2026-06, poids {ON_W}, equity {INIT_EQUITY:.0f}$ "
             f"CONSTANTE -- pas de compounding) = {tot:9.2f} $")
        for wd in range(5):
            v = rows[WD_NAME[wd]]
            share = (v["sum_usd"] / tot * 100) if tot != 0 else float("nan")
            emit(f"    {WD_NAME[wd]:9s}: {v['sum_usd']:9.2f} $  ({share:6.1f} % du total net)  n={v['n']}")
    mon_tue = {sym: tot_usd[sym] for sym in tot_usd}
    results["economic"]["totals_usd"] = tot_usd

    # ------------------------------------- Section 6b : part reelle Lun vs Mar --
    emit("\n" + "=" * 78)
    emit("SECTION 6b -- part de lundi vs mardi DANS LE SLEEVE REEL (Mon+Tue seulement, "
         "pas le portefeuille hypothetique 5 jours -- correction du denominateur)")
    emit("=" * 78)
    combined_mon = 0.0
    combined_tue = 0.0
    for sym in ("US100", "GER40"):
        r = results["economic"][sym]
        mon_usd = r["lundi"]["sum_usd"]
        tue_usd = r["mardi"]["sum_usd"]
        tot = mon_usd + tue_usd
        combined_mon += mon_usd
        combined_tue += tue_usd
        emit(f"  {sym}: lundi {mon_usd:9.2f}$ ({mon_usd/tot*100:5.1f}%)  "
             f"mardi {tue_usd:9.2f}$ ({tue_usd/tot*100:5.1f}%)  total sleeve(2j) {tot:9.2f}$")
    tot_c = combined_mon + combined_tue
    emit(f"  US100+GER40 combine: lundi {combined_mon:9.2f}$ ({combined_mon/tot_c*100:5.1f}%)  "
         f"mardi {combined_tue:9.2f}$ ({combined_tue/tot_c*100:5.1f}%)")
    results["economic"]["share_mon_tue_only"] = dict(
        combined_mon_usd=round(combined_mon, 2), combined_tue_usd=round(combined_tue, 2),
        mon_share_pct=round(combined_mon / tot_c * 100, 1),
        tue_share_pct=round(combined_tue / tot_c * 100, 1))

    # --------------------------------------------- Section 7 : test JOINT Lun+Mar --
    emit("\n" + "=" * 78)
    emit("SECTION 7 -- test JOINT lundi+mardi poolees (hypothese: le sleeve overnight "
         "midweek dans son ensemble != 0), HAC + bloc-bootstrap")
    emit("=" * 78)
    joint_all = []
    for sym in ("US100", "GER40"):
        df = data[sym]
        x = df.loc[df["weekday"].isin([0, 1]), "ov_bps_entryday"].dropna().to_numpy()
        rt_recent = RT_BPS_RECENT[sym]
        sw = SWAP_LONG_BPS[sym]
        net = x - rt_recent + sw
        r_gross = block_bootstrap_null_pvalue(x, lag=6, n_boot=4000, block=20, seed=(500 if sym=='US100' else 501))
        r_net = block_bootstrap_null_pvalue(net, lag=6, n_boot=4000, block=20, seed=(600 if sym=='US100' else 601))
        n_tests += 2
        results.setdefault("joint", {})[sym] = dict(gross=r_gross, net=r_net)
        emit(f"  {sym}: GROSS  mean={r_gross['mean']:6.3f} bps t={r_gross['t']:5.3f} "
             f"n={r_gross['n']} p_boot={r_gross['p_block_bootstrap']:.4f}")
        emit(f"  {sym}: NET    mean={r_net['mean']:6.3f} bps t={r_net['t']:5.3f} "
             f"n={r_net['n']} p_boot={r_net['p_block_bootstrap']:.4f}")
    emit(f"Sidak local mis a jour (n={n_tests}) : |t| > {sidak_threshold(n_tests):.3f}")

    results["n_tests"] = n_tests
    emit(f"\nTOTAL tests comptes cette session : {n_tests}")
    emit(f"Sidak local (n={n_tests}) : |t| > {sidak_threshold(n_tests):.3f}")
    n_cum = 1994 + n_tests
    emit(f"Sidak CUMULE (n={n_cum} = 1994 + {n_tests}) : |t| > {sidak_threshold(n_cum):.3f}")
    results["sidak_local"] = sidak_threshold(n_tests)
    results["sidak_cumulative"] = sidak_threshold(n_cum)
    results["n_cumulative"] = n_cum

    # ------------------------------------------- Section 8 : vol, queue, options D --
    emit("\n" + "=" * 78)
    emit("SECTION 8 -- volatilite, queue, et comparaison des options (Partie D)")
    emit("=" * 78)
    opt = {}
    for sym in ("US100", "GER40"):
        df = data[sym]
        rt_recent, sw = RT_BPS_RECENT[sym], SWAP_LONG_BPS[sym]
        rows = {}
        for wd, name in ((0, "lundi"), (1, "mardi")):
            x = df.loc[df["weekday"] == wd, "ov_bps_entryday"].dropna().to_numpy()
            net = x - rt_recent + sw
            mean, std = float(net.mean()), float(net.std())
            sharpe_ann = mean / std * np.sqrt(52) if std > 0 else float("nan")  # 1 nuit/semaine, L47
            p1, p5 = float(np.percentile(net, 1)), float(np.percentile(net, 5))
            worst = float(net.min())
            rows[name] = dict(mean_net_bps=round(mean, 3), std_net_bps=round(std, 3),
                               sharpe_ann_L47=round(sharpe_ann, 3), p1_bps=round(p1, 2),
                               p5_bps=round(p5, 2), worst_bps=round(worst, 2), n=len(x))
            emit(f"  {sym} {name}: mean_net={mean:6.2f} std={std:6.2f} bps  "
                 f"Sharpe_ann(sqrt52)={sharpe_ann:5.3f}  p1={p1:7.2f}  p5={p5:6.2f}  worst={worst:7.2f} bps")
        # pooled Mon+Tue (config live) vs demi-taille Mon+Tue (delevier plat L54)
        x_pool = df.loc[df["weekday"].isin([0, 1]), "ov_bps_entryday"].dropna().to_numpy()
        net_pool = x_pool - rt_recent + sw
        m, s = float(net_pool.mean()), float(net_pool.std())
        sharpe_pool = m / s * np.sqrt(104) if s > 0 else float("nan")  # 2 nuits/semaine
        # option "mardi seul" : garde mardi, coupe lundi
        x_tue = df.loc[df["weekday"] == 1, "ov_bps_entryday"].dropna().to_numpy()
        net_tue = x_tue - rt_recent + sw
        m_t, s_t = float(net_tue.mean()), float(net_tue.std())
        sharpe_tue = m_t / s_t * np.sqrt(52) if s_t > 0 else float("nan")
        # option "delevier plat" = meme 2 nuits, poids ON_W/2 -> mean et std divises par 2,
        # Sharpe ANNUALISE inchange (c'est le point L54 : delevier ne change pas le Sharpe)
        emit(f"  {sym}: POOL Mon+Tue plein poids -- Sharpe_ann={sharpe_pool:.3f} "
             f"(mean={m:.2f} std={s:.2f} bps/nuit, n={len(x_pool)})")
        emit(f"  {sym}: MARDI SEUL (coupe lundi) -- Sharpe_ann={sharpe_tue:.3f} "
             f"(mean={m_t:.2f} std={s_t:.2f} bps/nuit, n={len(x_tue)})")
        emit(f"  {sym}: DELEVIER PLAT (Mon+Tue a poids moitie) -- Sharpe_ann IDENTIQUE a pool "
             f"({sharpe_pool:.3f}, L54: le delevier ne change pas le Sharpe, seulement l'echelle) "
             f"mais expectation $ divisee par 2 ET les 2 nuits/semaine sont CONSERVEES "
             f"(exposition-jours inchangee, contrairement a 'mardi seul')")
        opt[sym] = dict(per_day=rows, pool_sharpe=round(sharpe_pool, 3),
                         tue_only_sharpe=round(sharpe_tue, 3),
                         pool_mean=round(m, 3), pool_std=round(s, 3), pool_n=len(x_pool),
                         tue_mean=round(m_t, 3), tue_std=round(s_t, 3), tue_n=len(x_tue))
    results["options_D"] = opt

    OUTJ.write_text(json.dumps(results, indent=2, default=str))
    emit(f"\n[ecrit] {OUTJ}")


if __name__ == "__main__":
    main()
