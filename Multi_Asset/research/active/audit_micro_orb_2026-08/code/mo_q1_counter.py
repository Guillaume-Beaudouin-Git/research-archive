"""Q1/Q2/Q4 — le micro-ORB fait-il son travail de COMPTEUR ?

Journalise chaque jour-tentative des 462 cohortes (2 configs : v2.2 pinnée et
v2.8 live-fidèle), puis mesure :
  Q1  distribution du nombre de SÉANCES pour atteindre 4 jours de trading,
      taux d'échec (tentative qui n'atteint jamais 4 alors qu'elle en avait le temps),
      retard imputable au compteur sur les tentatives gagnantes.
  Q2  couplage : jours où le micro était candidat mais supprimé parce qu'une autre
      jambe avait déjà ouvert -> combien de jours de COMPTAGE cela coûte-t-il ?
  Q4  robustesse : jours sans signal ORB, et jours réellement non marqués.
"""
import sys
import numpy as np
import pandas as pd

import mo_common as K
import mo_engine as G

M, WT, ON = K.load()
V, C22, E = K.V, K.C22, K.E
CFGS = dict(v22=C22.CFG_CHALLENGE, v28=C22.CFG_CHALLENGE_V28)


def collect(cfg, tag):
    """Mirroir EXACT de engine_v22.run_funnel, avec journal par phase."""
    rows, phases = [], []
    pid = [0]

    def do_phase(i, ph, tgt, win, i0, att):
        c = dict(cfg, target=tgt, max_cal=C22.WALL)
        if ph == 2:
            c["vm"] = cfg["vm"] * cfg.get("p2_mult", 1.0)
        log = []
        r = G.run_phase(M, i, WT, ON, c, log=log)
        d = pd.DataFrame(log)
        d["pid"] = pid[0]; d["win"] = win; d["phase"] = ph
        rows.append(d)
        phases.append(dict(pid=pid[0], win=win, phase=ph, out=r["out"], used=r["used"],
                           open_days=r["open_days"], micro=r["micro"],
                           cohort=int(i0), att=att))
        pid[0] += 1
        return r

    for win, lo, hi in C22.WINDOWS:
        for i0 in V.starts(M, lo, hi, C22.COHORT_STEP):
            start = M["dates"][int(i0)]
            i = int(i0); att = 0
            while True:
                if (M["dates"][min(i, M["n"] - 1)] - start).days > C22.WALL \
                        or i >= M["n"] - 5:
                    break
                att += 1
                r1 = do_phase(i, 1, E.TARGET1, win, i0, att)
                if r1["out"] == "pass":
                    j = min(r1["last"] + 3, M["n"] - 1)
                    if (M["dates"][j] - start).days > C22.WALL:
                        break
                    r2 = do_phase(j, 2, E.TARGET2, win, i0, att)
                    if r2["out"] == "pass":
                        break
                    if r2["out"] == "timeout":
                        break
                    i = min(r2["last"] + 2, M["n"] - 1)
                else:
                    if r1["out"] == "timeout":
                        break
                    i = min(r1["last"] + 2, M["n"] - 1)
    D = pd.concat(rows, ignore_index=True)
    P = pd.DataFrame(phases)
    D.to_parquet(K.OUT / f"daylog_{tag}.parquet")
    P.to_parquet(K.OUT / f"phases_{tag}.parquet")
    print(f"[{tag}] micro fires total = {int(P.micro.sum())} (ancre #13 v2.2 = 9248)")
    return D, P


def report(D, P, tag):
    out = []
    w = out.append
    w(f"\n########## {tag} ##########")
    w(f"tentatives de phase N={len(P)} | jours-tentatives N={len(D)}")

    # --- Q1 : séances pour atteindre 4 jours -------------------------------
    D = D.sort_values(["pid", "di"]).copy()
    D["opened"] = D["opened"].astype(bool)
    D["micro_cand"] = D["micro_cand"].astype(bool)
    D["cum_open"] = D.groupby("pid")["opened"].astype(int).cumsum() if False else D.groupby("pid")["opened"].transform(lambda x: x.astype(int).cumsum())
    hit = D[D.cum_open >= E.MIN_OPEN_DAYS].groupby("pid")["di"].min() + 1  # séances
    P = P.set_index("pid")
    P["sess_to_4"] = hit
    P["reached4"] = P.sess_to_4.notna()
    # temps disponible: une tentative bustée tôt n'est pas un échec de COMPTEUR
    hadtime = P.used >= 10
    w(f"\n[Q1] atteint 4 jours : {P.reached4.mean()*100:.1f}% de toutes les tentatives")
    s = P.loc[P.reached4, "sess_to_4"]
    w(f"     séances pour 4 jours (N={len(s)}) : min {s.min():.0f} | p25 {s.quantile(.25):.0f}"
      f" | MÉDIANE {s.median():.0f} | p75 {s.quantile(.75):.0f} | p90 {s.quantile(.90):.0f}"
      f" | p99 {s.quantile(.99):.0f} | max {s.max():.0f}")
    w("     distribution exacte : " + ", ".join(
        f"{int(k)}j:{v/len(s)*100:.1f}%" for k, v in s.value_counts().sort_index().head(8).items()))
    fail = P[~P.reached4]
    w(f"     n'atteint PAS 4 : {len(fail)} tentatives ; par issue : "
      + ", ".join(f"{k}={v}" for k, v in fail.out.value_counts().items()))
    real = fail[fail.out.isin(["timeout", "abandon"]) & (fail.used >= 20)]
    w(f"     >>> ÉCHEC DE COMPTEUR (survit >=20 séances sans 4 jours) : {len(real)}"
      f" / {len(P)} = {len(real)/len(P)*100:.2f}%")
    w(f"     [contrôle] tentatives survivant >=10 séances : {hadtime.sum()} ;"
      f" dont 4 jours atteints : {P.loc[hadtime,'reached4'].mean()*100:.2f}%")

    # retard imputable au compteur sur les tentatives gagnantes
    psd = P[P.out == "pass"]
    dd = D[D.pid.isin(psd.index)]
    tgt_hit = dd[dd.bal >= dd.target].groupby("pid")["di"].min()
    delay = (psd.sess_to_4 - 1 - tgt_hit).dropna().clip(lower=0)
    w(f"\n[Q1b] tentatives GAGNANTES N={len(psd)} ; retard du compteur (jours où la cible"
      f" était atteinte mais pas les 4 jours) : moyenne {delay.mean():.2f}j,"
      f" médiane {delay.median():.0f}j, p95 {delay.quantile(.95):.0f}j, max {delay.max():.0f}j")
    w(f"      part des tentatives gagnantes retardées >0 : {(delay>0).mean()*100:.2f}%")

    # --- Q2 : couplage -----------------------------------------------------
    cand = D[D.micro_cand]
    fired = D[D.opened_by == "micro"]
    supp = cand[cand.opened_by != "micro"]
    w(f"\n[Q2] jours-candidats micro (signal ORB présent) : {len(cand)}"
      f" ({len(cand)/len(D)*100:.1f}% des jours-tentatives)")
    w(f"     micro POSTÉ : {len(fired)} ({len(fired)/len(cand)*100:.1f}% des candidats)")
    w(f"     micro SUPPRIMÉ (autre jambe déjà ouverte) : {len(supp)}"
      f" ({len(supp)/len(cand)*100:.1f}%)")
    w(f"     dont le jour était DÉJÀ marqué par le livre : {supp.opened.sum()}"
      f" ({supp.opened.mean()*100:.1f}%)  -> jours de comptage PERDUS par la condition :"
      f" {int((~supp.opened).sum())}")
    w("     [qui marque le jour] " + ", ".join(
        f"{k}={v/len(D)*100:.1f}%" for k, v in
        D[D.opened].opened_by.value_counts().items()))

    # --- Q4 : robustesse jours sans signal ---------------------------------
    nosig = D[~D.micro_cand]
    unmarked = D[~D.opened]
    w(f"\n[Q4] jours-tentatives SANS signal ORB : {len(nosig)}"
      f" ({len(nosig)/len(D)*100:.2f}%)")
    w(f"     dont marqués quand même par le livre : {nosig.opened.sum()}"
      f" ({nosig.opened.mean()*100:.1f}%)")
    w(f"     jours NON marqués (compteur n'avance pas) : {len(unmarked)}"
      f" ({len(unmarked)/len(D)*100:.1f}%) ; dont sans signal ORB : "
      f"{int((~unmarked.micro_cand).sum())}"
      f" ({(~unmarked.micro_cand).mean()*100:.1f}% des jours non marqués)")
    w(f"     backstop $1 déclenché : {int((D.opened_by=='backstop').sum())} jours")
    return "\n".join(out), P


txt_all = []
for tag, cfg in CFGS.items():
    D, P = collect(cfg, tag)
    t, P2 = report(D, P, tag)
    print(t, flush=True)
    txt_all.append(t)
(K.OUT / "q1_counter.txt").write_text("\n".join(txt_all))
