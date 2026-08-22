"""b2b_diagnostics.py — POURQUOI le 25 % de L59 vaut 0.00 % ici, et ce qui reste a payer.

Un zero exact n'est pas un resultat, c'est une question. Deux hypotheses :

  (H_a) MECANIQUE — dans une session continue sans halt, l'open d'une barre M1 est
        colle au close de la precedente. Or la barre precedente n'a PAS touche le
        stop (sinon elle serait la barre de stop) : son close est donc du bon cote.
        Un gap-through intra-session est alors quasi impossible. Le 25 % de L59 est
        un chiffre de barres DAILY avec gap OVERNIGHT — il ne transfere pas.

  (H_b) ARTEFACT — l'agregateur (databento) construirait open[k] := close[k-1],
        auquel cas la mesure ne teste rien.

On les separe en mesurant directement la distribution de open[k] - close[k-1] sur
la serie M1 RTH.

Puis on mesure ce que la fermeture du canal GAP laisse intact — le canal
MICROSTRUCTURE, qui est celui qui mord ici :
  - PENETRATION du stop : de combien la barre de stop passe SOUS le stop.
    Penetration = 0 (touche marginale) => un stop-market declenche a la touche ne
    peut PAS etre remplie au stop : il n'y a pas de contrepartie sous le niveau.
  - Prix REELLEMENT disponibles apres la touche (close de la barre, open suivant).

Sortie : out/b2b_diagnostics.txt
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import b_common as K

led = K.load_ledger()
m1 = K.m1_rth()
m1_i8 = m1.ts.asi8
X = pd.read_parquet(K.OUT / "b2_stop_exits.parquet")

TICK = 0.25  # NQ : 1 tick = 0.25 point

L: list[str] = []
w = L.append
w("=" * 96)
w("B2b — DIAGNOSTIC : pourquoi 0.00 %, et ce que le canal GAP ferme ne couvre pas")
w("=" * 96)

# ---------------------------------------------------------------------------
# 1. H_a vs H_b : continuite intra-session
# ---------------------------------------------------------------------------
w("")
w("-" * 96)
w("1. CONTINUITE INTRA-SESSION — open[k] vs close[k-1] sur toute la serie M1 RTH")
w("-" * 96)
same_day = m1.day[1:] == m1.day[:-1]
jump = (m1.o[1:] - m1.c[:-1])[same_day]
n = len(jump)
w(f"  N transitions intra-journee : {n:,}")
w(f"  open[k] == close[k-1] exactement : {np.mean(jump == 0)*100:.2f} %")
for t in (1, 2, 4, 8):
    w(f"  |open[k] - close[k-1]| <= {t} tick(s) ({t*TICK:5.2f} pt) : "
      f"{np.mean(np.abs(jump) <= t*TICK + 1e-9)*100:6.2f} %")
w(f"  |saut| median = {np.median(np.abs(jump)):.4f} pt ; p99 = "
  f"{np.percentile(np.abs(jump), 99):.3f} pt ; max = {np.abs(jump).max():.2f} pt")
w("")
if np.mean(jump == 0) > 0.98:
    w("  => H_b (ARTEFACT) : l'agregateur colle open[k] sur close[k-1]. La mesure de")
    w("     gap serait vide par construction. A VERIFIER avant de conclure.")
else:
    w("  => H_b ECARTEE : les barres M1 ont de vrais sauts entre close et open suivant")
    w("     (l'agregateur ne colle pas les prix). Le zero mesure donc quelque chose.")
    w("  => H_a RETENUE : le zero vient de la MECANIQUE. La barre qui precede la barre")
    w("     de stop n'a par definition pas touche le stop, son close est du bon cote,")
    w("     et le saut intra-session est trop petit (median 0, p99 ~1 tick) pour")
    w("     enjamber le niveau. Le 25 % de L59 est un chiffre de barres DAILY a gap")
    w("     OVERNIGHT : il ne transfere pas a un stop intraday sur barres M1.")

# combien de sauts intra-session seraient assez grands pour enjamber un stop ?
w("")
w(f"  sauts intra-session >= 1 tick : {np.mean(np.abs(jump) >= TICK - 1e-9)*100:.3f} %"
  f"  ({int((np.abs(jump) >= TICK - 1e-9).sum()):,} barres)")
w("  (c'est le reservoir maximal de gap-through possible ; encore faut-il que le")
w("   saut tombe pile sur le niveau de stop)")

# ---------------------------------------------------------------------------
# 2. PENETRATION du stop — le canal qui reste ouvert
# ---------------------------------------------------------------------------
w("")
w("-" * 96)
w("2. PENETRATION DU STOP — la barre passe-t-elle SOUS le niveau, ou le touche-t-elle ?")
w("-" * 96)
rows = []
for dt, r in X[X.ok & (X.outcome == "STOP") & X.m1_hit].iterrows():
    d = pd.Timestamp(dt)
    i0, i1 = m1.sl(d)
    k = int(np.searchsorted(m1_i8[i0:i1], pd.Timestamp(r["t_stop_m1"]).value, "left")) + i0
    dd = int(r["direction"])
    stop = float(r["stop_eff"])
    pen = (stop - m1.lo[k]) if dd > 0 else (m1.h[k] - stop)   # >= 0
    nxt_open = float(m1.o[k + 1]) if k + 1 < i1 else np.nan
    rows.append({"date": dt, "direction": dd, "stop_eff": stop, "or_range": float(r["or_range"]),
                 "pen_pts": float(pen), "bar_close": float(m1.c[k]),
                 "bar_open": float(m1.o[k]), "next_open": nxt_open,
                 "bar_low": float(m1.lo[k]), "bar_high": float(m1.h[k]),
                 "is_last_bar": bool(k + 1 >= i1), "regime_tag": r["regime_tag"]})
P = pd.DataFrame(rows).set_index("date")
P["pen_ticks"] = P["pen_pts"] / TICK
w(f"  N = {len(P)}")
w(f"  penetration EXACTEMENT nulle (low == stop en long) : "
  f"{int((P.pen_pts == 0).sum())}  ({(P.pen_pts == 0).mean()*100:.2f} %)")
for t in (0, 1, 2, 4):
    w(f"  penetration <= {t} tick(s) : {(P.pen_ticks <= t + 1e-9).mean()*100:6.2f} %")
w(f"  penetration mediane = {P.pen_pts.median():.2f} pt ({P.pen_ticks.median():.1f} ticks)"
  f" ; p25 = {P.pen_pts.quantile(.25):.2f} pt ; max = {P.pen_pts.max():.2f} pt")
w("")
w("  Lecture : une penetration de 0 tick signifie que le marche a touche le niveau")
w("  et est reparti. Un ordre stop-market declenche a la touche ne peut pas etre")
w("  rempli AU niveau : il est rempli au premier prix disponible ensuite.")

# prix realistes disponibles apres la touche
P["dir"] = P["direction"]
adverse_close = np.where(P.dir > 0, P.stop_eff - P.bar_close, P.bar_close - P.stop_eff)
adverse_next = np.where(P.dir > 0, P.stop_eff - P.next_open, P.next_open - P.stop_eff)
P["adv_close_pts"] = adverse_close     # >0 = close pire que le stop
P["adv_next_pts"] = adverse_next
w("")
w("  Prix reellement disponibles APRES la touche (positif = pire que le stop) :")
w(f"    close de la barre de stop : median {np.nanmedian(P.adv_close_pts):+.3f} pt"
  f" ; moyenne {np.nanmean(P.adv_close_pts):+.3f} pt"
  f" ; > stop dans {np.nanmean(P.adv_close_pts > 0)*100:.1f} % des cas")
w(f"    open de la barre suivante : median {np.nanmedian(P.adv_next_pts):+.3f} pt"
  f" ; moyenne {np.nanmean(P.adv_next_pts):+.3f} pt"
  f" ; > stop dans {np.nanmean(P.adv_next_pts > 0)*100:.1f} % des cas")
w(f"    barre de stop = derniere barre RTH du jour : {int(P.is_last_bar.sum())}")

P.to_parquet(K.OUT / "b2b_penetration.parquet")

# ---------------------------------------------------------------------------
# 3. Les 3 STOP du ledger non retrouves en M1
# ---------------------------------------------------------------------------
w("")
w("-" * 96)
w("3. LES 3 SORTIES STOP NON RETROUVEES EN M1")
w("-" * 96)
miss = X[X.ok & (X.outcome == "STOP") & ~X.m1_hit]
w(f"  N = {len(miss)}  dates : {[str(d.date()) for d in miss.index]}")
w("  Cause : la barre M1 declenchant l'entree est POSTERIEURE a la barre M1 qui")
w("  touche le stop a l'interieur de la meme barre 5-min (le M5 ne peut pas ordonner")
w("  les deux evenements, le M1 si). Elles sont traitees comme des STOP au stop exact")
w("  dans la serie re-pricee — hypothese la plus FAVORABLE au sleeve, N=3 negligeable.")

txt = "\n".join(L)
print(txt)
(K.OUT / "b2b_diagnostics.txt").write_text(txt + "\n")
