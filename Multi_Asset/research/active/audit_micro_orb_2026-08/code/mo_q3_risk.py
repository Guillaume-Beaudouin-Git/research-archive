"""Q3/Q5 — risque apporté par le micro-ORB, et compteur strictement dominant.

Bras (tous sur les 462 cohortes, config v2.2 pinnée ET v2.8 live-fidèle) :
  base        micro-ORB tel que déployé
  pnl_off     le micro marque le jour, P&L et dip mis à ZÉRO  -> isole COMPTAGE / P&L
  l59         P&L du micro re-pricé L59 (sorties stop au vrai open de barre)
  placebo     R du micro décalé circulairement (autocorrélation APPARIÉE, dates cassées)
  micro_off   pas de micro du tout (backstop v2.1 seul, forme étroite)
  token       pas de micro, backstop $1 GÉNÉRALISÉ = compteur idéal sans risque

Deltas appariés par cohorte + block-bootstrap (blocs de 10 cohortes contiguës,
jamais iid).
"""
import numpy as np
import pandas as pd

import mo_common as K
import mo_engine as G

M, WT, ON = K.load()
V, C22, E = K.V, K.C22, K.E
rng = np.random.default_rng(42)
mR_l59 = np.load(K.OUT / "mR_l59.npy")

base_R = M["mR"].copy()
SHIFT = 617                                  # décalage circulaire (jours ouvrés)
plac_R = np.roll(base_R, SHIFT)

ARMS = {
    "base":      lambda c: dict(c),
    "pnl_off":   lambda c: dict(c, micro_pnl_off=True),
    "l59":       lambda c: dict(c, micro_R=mR_l59),
    "placebo":   lambda c: dict(c, micro_R=plac_R),
    "micro_off": lambda c: dict(c, micro_orb=False),
    "token":     lambda c: dict(c, micro_orb=False, backstop_any=True),
}


def run(cfg):
    out = []
    for win, lo, hi in C22.WINDOWS:
        for i0 in V.starts(M, lo, hi, C22.COHORT_STEP):
            r = G.run_funnel(M, int(i0), WT, ON, cfg, wall=C22.WALL)
            out.append((win, int(i0), bool(r["funded"]), r["attempts"], r["t"]))
    return pd.DataFrame(out, columns=["win", "i0", "funded", "att", "t"])


def bootci(delta, B=10, nb=4000):
    d = np.asarray(delta, float)
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
for tag, cfg0 in (("v2.2 (pinnée)", C22.CFG_CHALLENGE),
                  ("v2.8 (live-fidèle)", C22.CFG_CHALLENGE_V28)):
    res = {k: run(f(cfg0)) for k, f in ARMS.items()}
    b = res["base"]
    w(f"\n############ {tag} ############")
    w(f"{'bras':10s} {'p(campagne)':>12s} {'essais':>7s} {'durée méd.':>11s}"
      f" {'Δp vs base':>11s} {'CI95 bloc':>18s}")
    for k, d in res.items():
        dl = (d.funded.to_numpy(float) - b.funded.to_numpy(float)) * 100
        ci = bootci(dl) if k != "base" else (0.0, 0.0)
        tt = d.loc[d.funded, "t"].median()
        w(f"{k:10s} {d.funded.mean()*100:11.2f}% {d.att.mean():7.2f} {tt:10.0f}j"
          f" {dl.mean():+10.2f} [{ci[0]:+6.2f};{ci[1]:+6.2f}]")
    # dominance token vs base (le vrai test Q5)
    dl = (res["token"].funded.to_numpy(float) - b.funded.to_numpy(float)) * 100
    ci = bootci(dl)
    w(f"  >>> Q5 compteur-token vs micro-ORB : Δp {dl.mean():+.2f} pt"
      f" CI95 [{ci[0]:+.2f};{ci[1]:+.2f}] — "
      f"{'DOMINANT (CI exclut 0)' if ci[0] > 0 else 'indistinguable de 0'}")
    dl2 = (b.funded.to_numpy(float) - res["micro_off"].funded.to_numpy(float)) * 100
    ci2 = bootci(dl2)
    w(f"  >>> valeur du COMPTEUR (base vs aucun compteur) : Δp {dl2.mean():+.2f} pt"
      f" CI95 [{ci2[0]:+.2f};{ci2[1]:+.2f}]")

# --- P&L et pire séance du micro -------------------------------------------
w("\n############ P&L du micro (jours où il est effectivement posté) ############")
for tag in ("v22", "v28"):
    D = pd.read_parquet(K.OUT / f"daylog_{tag}.parquet")
    f = D[D.opened_by == "micro"]
    p = f.micro_pnl.astype(float)
    w(f"[{tag}] N={len(p)} poses | P&L moyen ${p.mean():+.3f} | sd ${p.std():.2f}"
      f" | PIRE SÉANCE ${p.min():+.2f} | meilleure ${p.max():+.2f}"
      f" | p1 ${p.quantile(.01):+.2f} | p99 ${p.quantile(.99):+.2f}")
    w(f"       risque posé (0.01 lot x OR) : médiane ${f.micro_risk.median():.2f}"
      f" max ${f.micro_risk.max():.2f} ; excursion de règle 1.31R max"
      f" ${1.31*f.micro_risk.max():.2f}")
    w(f"       P&L cumulé du micro sur toutes les tentatives : ${p.sum():+.0f}"
      f" ({p.sum()/len(D):+.3f} $/jour-tentative) — budget daily $500, floor $1,000")
    # part du budget journalier
    w(f"       pire séance en % du budget daily (-5% = $500) :"
      f" {abs(p.min())/500*100:.2f}%  ; en % du buffer floor ($1,000) :"
      f" {abs(p.min())/1000*100:.2f}%")

txt = "\n".join(L)
print(txt)
(K.OUT / "q3_risk.txt").write_text(txt)
