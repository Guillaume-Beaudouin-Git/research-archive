"""Q5 — valeur RÉELLE de la fonction compteur, et attribution du risque aux busts.

Bras supplémentaires :
  no_counter   ni micro-ORB ni backstop $1 -> la contrainte des 4 jours mord seule.
               C'est le SEUL contrefactuel qui mesure « à quoi sert un compteur ».
  token_only   pas de micro, backstop $1 généralisé (compteur idéal, risque nul).

Attribution : sur les jours de BUST, le micro-ORB était-il exposé, et l'écart au
franchissement était-il plus petit que son excursion de règle (1.31 x risque) ?
"""
import numpy as np
import pandas as pd

import mo_common as K
import mo_engine as G

M, WT, ON = K.load()
V, C22, E = K.V, K.C22, K.E
rng = np.random.default_rng(7)


def run(cfg):
    out = []
    for win, lo, hi in C22.WINDOWS:
        for i0 in V.starts(M, lo, hi, C22.COHORT_STEP):
            r = G.run_funnel(M, int(i0), WT, ON, cfg, wall=C22.WALL)
            out.append((win, bool(r["funded"]), r["attempts"], r["t"]))
    return pd.DataFrame(out, columns=["win", "funded", "att", "t"])


def bootci(d, B=10, nb=4000):
    d = np.asarray(d, float)
    n = len(d)
    o = np.empty(nb)
    for b in range(nb):
        ix = []
        while len(ix) < n:
            s = rng.integers(0, n)
            ix.extend(((s + np.arange(B)) % n).tolist())
        o[b] = d[np.array(ix[:n])].mean()
    return np.percentile(o, [2.5, 97.5])


L = []
w = L.append
w("=== Q5 — que vaut la FONCTION compteur, et le micro-ORB est-il le bon support ? ===")
for tag, c0 in (("v2.2 (pinnée)", C22.CFG_CHALLENGE),
                ("v2.8 (live-fidèle)", C22.CFG_CHALLENGE_V28)):
    arms = {
        "base (micro-ORB)": dict(c0),
        "no_counter": dict(c0, micro_orb=False, fix_deadlock=False),
        "backstop_étroit": dict(c0, micro_orb=False),
        "token_généralisé": dict(c0, micro_orb=False, backstop_any=True),
    }
    R = {k: run(v) for k, v in arms.items()}
    b = R["base (micro-ORB)"]
    w(f"\n--- {tag} ---")
    for k, d in R.items():
        dl = (d.funded.to_numpy(float) - b.funded.to_numpy(float)) * 100
        ci = bootci(dl) if k != "base (micro-ORB)" else (0, 0)
        w(f"  {k:18s} p={d.funded.mean()*100:6.2f}%  essais {d.att.mean():.2f}"
          f"  durée méd {d.loc[d.funded,'t'].median():.0f}j"
          f"  Δp vs base {dl.mean():+6.2f} pt  CI95 [{ci[0]:+.2f};{ci[1]:+.2f}]")
    nc = R["no_counter"].funded.mean() * 100
    w(f"  >>> VALEUR DE LA FONCTION COMPTEUR (base - no_counter) :"
      f" {b.funded.mean()*100 - nc:+.2f} pt")

# ---- attribution du risque sur les jours de bust --------------------------
w("\n=== attribution : le micro peut-il contribuer à un franchissement ? ===")
for tag in ("v22", "v28"):
    D = pd.read_parquet(K.OUT / f"daylog_{tag}.parquet")
    bu = D[D.event == "bust"].copy()
    bu["micro_dip"] = bu.micro_dip.astype(float)
    exp = bu[bu.micro_dip > 0]
    w(f"[{tag}] jours de BUST N={len(bu)} ; dont le micro était EXPOSÉ (dip de règle"
      f" actif au moment du franchissement) : {len(exp)} ({len(exp)/max(len(bu),1)*100:.1f}%)")
    if len(exp):
        w(f"        excursion micro sur ces jours : médiane ${exp.micro_dip.median():.2f}"
          f" max ${exp.micro_dip.max():.2f} — à comparer au budget daily $500")
    # P&L micro réalisé le jour du bust (il ne peut pas l'être : il est posté à 22:05)
    w(f"        micro POSTÉ le jour même du bust : {int((bu.opened_by=='micro').sum())}"
      f"  (le micro se dénoue à 22:00, le franchissement est vérifié en M5 avant)")
    # borne dure
    mx = float(D.micro_risk.astype(float).max())
    w(f"        BORNE DURE : risque max posé ${mx:.2f} -> excursion de règle max"
      f" ${1.31*mx:.2f} = {1.31*mx/500*100:.2f}% du budget daily,"
      f" {1.31*mx/1000*100:.2f}% du buffer floor")

txt = "\n".join(L)
print(txt)
(K.OUT / "q5_counter_value.txt").write_text(txt)
