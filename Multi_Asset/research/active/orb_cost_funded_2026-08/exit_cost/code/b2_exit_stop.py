"""b2_exit_stop.py — COEUR DU VOLET B : re-pricer les 1590 sorties STOP (L59).

Le ledger remplit 1590/1590 des sorties STOP au prix EXACT du stop. L59 dit qu'une
part materielle des barres de stop OUVRE deja au-dela : dans ce cas le niveau n'a
jamais ete cote entre la barre precedente et celle-la, et le remplissage honnete est
l'OPEN de la barre, pas le stop.

Protocole (le delay+1 ne certifie que l'ENTREE — on re-price la SORTIE separement) :
  1. le ledger donne `bi` = index de la barre 5-min de cassure -> horodatage d'entree ;
  2. dans cette barre 5-min on localise la barre M1 qui declenche l'ordre stop
     d'ENTREE (premiere M1 avec high > level en long / low < level en short) ;
  3. a partir de cette barre M1 INCLUSE on cherche la premiere barre M1 qui touche
     `stop_eff` (low <= stop en long, high >= stop en short) ;
  4. on mesure : la barre ouvre-t-elle deja au-dela ? de combien ? et quel est le
     remplissage realiste min(open, stop) en long / max(open, stop) en short.

Le meme calcul est refait a la resolution M5 (celle du ledger) : le taux de "barre
ouvrant au-dela" DECROIT avec la finesse de barre, il faut donc dire a quelle
resolution le chiffre est produit.

Controles : trous de donnees M1 (une minute manquante fabriquerait un faux gap),
barres a fourchette nulle (L60), stop touche dans la barre d'entree elle-meme.

Sortie : out/b2_stop_exits.parquet, out/b2_exit_stop.txt
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import b_common as K

led = K.load_ledger()
m1 = K.m1_rth()
m5 = K.to_m5(m1)
m1_i8 = m1.ts.asi8

L: list[str] = []
w = L.append

w("=" * 96)
w("B2 — RE-PRICING DES SORTIES STOP (L59)")
w("=" * 96)
stops = led[led["outcome"] == "STOP"]
w(f"sorties STOP dans le ledger : N={len(stops)}  "
  f"({len(stops)/len(led)*100:.1f} % des {len(led)} trades)")
w(f"exit_px == stop_eff exactement : "
  f"{int((stops['exit_px'].values == stops['stop_eff'].values).sum())}/{len(stops)}")
w(f"r_gross == -1.000000 exactement : "
  f"{int((stops['r_gross'].values == -1.0).sum())}/{len(stops)}")

rows = []
for dt, r in led.iterrows():
    d = pd.Timestamp(dt)
    dd = int(r["direction"])
    stop = float(r["stop_eff"])
    level = float(r["level"])
    rec = {"date": dt, "outcome": r["outcome"], "direction": dd, "entry": float(r["entry"]),
           "stop_eff": stop, "level": level, "or_range": float(r["or_range"]),
           "r_gross": float(r["r_gross"]), "regime_tag": r["regime_tag"], "ok": False}
    b5 = m5.sl(d)
    b1 = m1.sl(d)
    if b5 is None or b1 is None:
        rows.append(rec); continue
    j0, j1 = b5
    i0, i1 = b1
    bi = int(r["bi"])
    if j0 + bi >= j1:
        rows.append(rec); continue
    t5 = m5.ts[j0 + bi]

    # --- barre M1 declenchant l'ENTREE, a l'interieur de la barre 5-min bi ---
    a = i0 + int(np.searchsorted(m1_i8[i0:i1], t5.value, "left"))
    b = i0 + int(np.searchsorted(m1_i8[i0:i1], (t5 + pd.Timedelta(minutes=5)).value, "left"))
    if b <= a:
        rows.append(rec); continue
    seg = np.flatnonzero(m1.h[a:b] > level) if dd > 0 else np.flatnonzero(m1.lo[a:b] < level)
    if len(seg) == 0:
        rows.append(rec); continue
    e = a + int(seg[0])                       # index absolu de la barre M1 d'entree
    rec["ok"] = True
    rec["t_entry_m1"] = m1.ts[e]
    rec["m1_bars_in_life"] = i1 - e

    # --- premiere barre M1 touchant le stop, a partir de l'entree INCLUSE ----
    cross = (np.flatnonzero(m1.lo[e:i1] <= stop) if dd > 0
             else np.flatnonzero(m1.h[e:i1] >= stop))
    rec["m1_hit"] = bool(len(cross))
    if len(cross):
        k = e + int(cross[0])
        op = float(m1.o[k])
        rec["t_stop_m1"] = m1.ts[k]
        rec["stop_bar_open"] = op
        rec["stop_bar_is_entry_bar"] = bool(k == e)
        rec["stop_bar_zero_range"] = bool(m1.h[k] == m1.lo[k])
        rec["prev_close"] = float(m1.c[k - 1]) if k > i0 else np.nan
        rec["gap_minutes"] = (float((m1_i8[k] - m1_i8[k - 1]) / 6e10) if k > i0 else np.nan)
        beyond = (stop - op) if dd > 0 else (op - stop)
        rec["beyond_pts"] = float(beyond)
        rec["opened_beyond"] = bool(beyond > 0)
        rec["fill_m1"] = float(min(op, stop) if dd > 0 else max(op, stop))
        rec["slip_pts_m1"] = float(max(beyond, 0.0))

    # --- meme calcul a la resolution M5 (celle du ledger) --------------------
    s5 = j0 + bi
    cr5 = (np.flatnonzero(m5.lo[s5:j1] <= stop) if dd > 0
           else np.flatnonzero(m5.h[s5:j1] >= stop))
    rec["m5_hit"] = bool(len(cr5))
    if len(cr5):
        k5 = s5 + int(cr5[0])
        op5 = float(m5.o[k5])
        b5v = (stop - op5) if dd > 0 else (op5 - stop)
        rec["beyond_pts_m5"] = float(b5v)
        rec["opened_beyond_m5"] = bool(b5v > 0)
        rec["slip_pts_m5"] = float(max(b5v, 0.0))
    rows.append(rec)

X = pd.DataFrame(rows).set_index("date")
for c in ("ok", "m1_hit", "m5_hit", "opened_beyond", "opened_beyond_m5",
          "stop_bar_is_entry_bar", "stop_bar_zero_range"):
    X[c] = X.get(c, False)
    X[c] = X[c].fillna(False).astype(bool)

# ---------------------------------------------------------------------------
w("")
w("-" * 96)
w("0. COHERENCE M1 <-> LEDGER (une mesure sur un desalignement ne vaut rien)")
w("-" * 96)
w(f"  trades exploitables (barre M1 d'entree localisee) : {int(X.ok.sum())}/{len(X)}")
S = X[X.ok & (X.outcome == "STOP")]
T = X[X.ok & (X.outcome == "TIME_STOP")]
w(f"  STOP du ledger retrouves en M1            : {int(S.m1_hit.sum())}/{len(S)}")
w(f"  TIME_STOP du ledger stoppes a tort en M1  : {int(T.m1_hit.sum())}/{len(T)}"
  "   (doit valoir 0)")
w(f"  STOP du ledger retrouves en M5 reconstruit: {int(S.m5_hit.sum())}/{len(S)}")

H = S[S.m1_hit].copy()
w("")
w("-" * 96)
w("1. LE CHIFFRE DE L59 — part des barres de stop qui OUVRENT AU-DELA du stop")
w("-" * 96)
w(f"  N (sorties STOP exploitables) = {len(H)}")
w(f"  M1  (resolution la plus fine disponible) : {H.opened_beyond.mean()*100:6.2f} %"
  f"   ({int(H.opened_beyond.sum())}/{len(H)})")
H5 = S[S.m5_hit]
w(f"  M5  (resolution du ledger)               : {H5.opened_beyond_m5.mean()*100:6.2f} %"
  f"   ({int(H5.opened_beyond_m5.sum())}/{len(H5)})")
w("")
w("  Reference L59 (famille gap_pattern, barres DAILY a gap overnight) : 25 %.")
w("")
w("  Controles de qualite de la mesure :")
w(f"    barre de stop == barre d'entree (M1)   : {int(H.stop_bar_is_entry_bar.sum())}"
  f" ({H.stop_bar_is_entry_bar.mean()*100:.2f} %)")
w(f"    barre de stop a fourchette NULLE (L60) : {int(H.stop_bar_zero_range.sum())}"
  f" ({H.stop_bar_zero_range.mean()*100:.2f} %)")
gm = H["gap_minutes"].dropna()
w(f"    ecart a la barre M1 precedente > 1 min : {int((gm > 1).sum())}"
  f" ({(gm > 1).mean()*100:.2f} %)  <- un trou de donnee fabriquerait un faux gap")
OB = H[H.opened_beyond]
if len(OB):
    g2 = OB["gap_minutes"].dropna()
    w(f"    parmi les 'ouvre au-dela' : ecart>1min : {int((g2 > 1).sum())}"
      f" ({(g2 > 1).mean()*100:.2f} %)")
    w(f"    parmi les 'ouvre au-dela' : barre d'entree : "
      f"{int(OB.stop_bar_is_entry_bar.sum())} ({OB.stop_bar_is_entry_bar.mean()*100:.2f} %)")

# --- distribution, 3 devises (prereg §2) -----------------------------------
H["beyond_bps"] = H["beyond_pts"] / H["stop_eff"] * 1e4
H["beyond_R"] = H["beyond_pts"] / H["or_range"]
H["slip_R"] = H["slip_pts_m1"] / H["or_range"]
H["slip_bps"] = H["slip_pts_m1"] / H["stop_eff"] * 1e4
H["lev"] = (H["entry"] / (H["entry"] - H["stop_eff"]).abs())

qs = [0.50, 0.75, 0.90, 0.95, 0.99, 1.00]
w("")
w("-" * 96)
w("2. DISTRIBUTION DE LA TRAVERSEE (open - stop, sens defavorable) — 3 devises")
w("-" * 96)
w(f"   (a) CONDITIONNELLE aux barres qui ouvrent au-dela   N={len(OB)}")
if len(OB):
    c = OB
    w(f"       {'quantile':>10s} {'points':>10s} {'bps':>10s} {'R':>10s}")
    for q in qs:
        lab = "max" if q == 1.0 else f"p{int(q*100)}"
        w(f"       {lab:>10s} {c['beyond_pts'].quantile(q):>10.3f} "
          f"{c['beyond_bps'].quantile(q):>10.3f} {c['beyond_R'].quantile(q):>10.4f}")
    w(f"       {'moyenne':>10s} {c['beyond_pts'].mean():>10.3f} "
      f"{c['beyond_bps'].mean():>10.3f} {c['beyond_R'].mean():>10.4f}")
w("")
w(f"   (b) INCONDITIONNELLE sur les {len(H)} sorties STOP (0 si la barre ne gappe pas)")
w(f"       {'quantile':>10s} {'points':>10s} {'bps':>10s} {'R':>10s}")
for q in qs:
    lab = "max" if q == 1.0 else f"p{int(q*100)}"
    w(f"       {lab:>10s} {H['slip_pts_m1'].quantile(q):>10.3f} "
      f"{H['slip_bps'].quantile(q):>10.3f} {H['slip_R'].quantile(q):>10.4f}")
w(f"       {'moyenne':>10s} {H['slip_pts_m1'].mean():>10.3f} "
  f"{H['slip_bps'].mean():>10.3f} {H['slip_R'].mean():>10.4f}")
w("")
w(f"   levier median lev = entry/|entry-stop| sur les STOP : {H['lev'].median():.1f}")
w(f"   cout de sortie STOP moyen dilue sur les {len(led)} trades du ledger : "
  f"{H['slip_R'].sum()/len(led):+.5f} R")

H5b = S[S.m5_hit].copy()
H5b["slip_R_m5"] = H5b["slip_pts_m5"] / H5b["or_range"]
w(f"   [sensibilite de resolution] meme quantite en M5 : "
  f"{H5b['slip_R_m5'].mean():.4f} R par STOP   (M1 : {H['slip_R'].mean():.4f} R)")

# --- decomposition ---------------------------------------------------------
w("")
w("-" * 96)
w("3. OU SE CONCENTRE LA TRAVERSEE")
w("-" * 96)
w("   par annee :")
w(f"     {'annee':>6s} {'N':>5s} {'%ouvre_au_dela':>15s} {'slip_moyen_R':>13s} {'slip_moyen_pts':>15s}")
for y, g in H.groupby(H.index.year):
    w(f"     {y:>6d} {len(g):>5d} {g.opened_beyond.mean()*100:>14.2f}% "
      f"{g['slip_R'].mean():>13.4f} {g['slip_pts_m1'].mean():>15.3f}")
w("")
w("   par regime_tag :")
w(f"     {'tag':>10s} {'N':>5s} {'%ouvre_au_dela':>15s} {'slip_moyen_R':>13s}")
for t, g in H.groupby("regime_tag"):
    w(f"     {t:>10s} {len(g):>5d} {g.opened_beyond.mean()*100:>14.2f}% {g['slip_R'].mean():>13.4f}")
w("")
w("   par direction :")
for dd_, g in H.groupby("direction"):
    w(f"     {'long' if dd_ == 1 else 'short':>10s} {len(g):>5d} "
      f"{g.opened_beyond.mean()*100:>14.2f}% {g['slip_R'].mean():>13.4f}")

X.to_parquet(K.OUT / "b2_stop_exits.parquet")
txt = "\n".join(L)
print(txt)
(K.OUT / "b2_exit_stop.txt").write_text(txt + "\n")
