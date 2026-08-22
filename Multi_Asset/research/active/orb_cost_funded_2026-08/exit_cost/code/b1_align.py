"""b1_align.py — ETAPE OBLIGATOIRE : verifier fuseau + alignement du ledger sur le M1.

Mesurer une traversee de stop sur un desalignement d'horloge ne vaut rien (L52/L56).
On reconstruit donc `or_hi`, `or_lo`, `or_range`, `direction`, `level`, `bi`,
`ttb_5min`, `stop_eff`, `exit_px`, `outcome` a partir des barres M1 canoniques, avec
la logique EXACTE du generateur, et on compare AU TICK (float32 = precision de
stockage du ledger).

Falsificateur d'horloge bon marche : si l'horloge etait mal identifiee, une fenetre
d'OR decalee d'une heure reproduirait aussi bien. On mesure les trois.

Sortie : out/b1_align.txt, out/b1_align_per_trade.parquet
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import b_common as K

led = K.load_ledger()
m1 = K.m1_rth()
m5 = K.to_m5(m1)

L: list[str] = []
w = L.append

w("=" * 96)
w("B1 — VERIFICATION FUSEAU + ALIGNEMENT LEDGER <-> M1 (prealable obligatoire)")
w("=" * 96)
w(f"ledger  : {K.LEDGER}")
w(f"M1      : {K.NQ_M1}")
w(f"N ledger: {len(led)}   {led.index.min().date()} -> {led.index.max().date()}")
w(f"M1 RTH hors roll-day : {len(m1.ts):,} barres ; M5 reconstruites : {len(m5.ts):,}")
w(f"index M1 tz = {m1.ts.tz}")

# --- diagnostic d'horloge ---------------------------------------------------
et = m1.ts.tz_convert("US/Eastern")
hm = et.hour * 100 + et.minute
w("")
w("  Diagnostic d'horloge (L52 : ne jamais faire confiance au nom d'un champ) :")
w(f"    barres RTH converties en US/Eastern : min={hm.min()}  max={hm.max()}"
  "   (attendu 930 -> 1559)")
w(f"    barres hors 09:30-15:59 ET          : {int(((hm < 930) | (hm > 1559)).sum())}")
utc_h = pd.Series(m1.ts.hour).value_counts().sort_index()
w(f"    heures UTC occupees                 : {utc_h.index.tolist()}"
  "   (13-19 ete / 14-20 hiver => l'heure UTC BOUGE, l'heure ET non)")

# --- reconstruction trade par trade ----------------------------------------
rows = []
for dt, r in led.iterrows():
    d = pd.Timestamp(dt)
    rec = {"date": dt, "found": False}
    b = m5.sl(d)
    if b is None:
        rows.append(rec); continue
    i0, i1 = b
    H, Lo, C = m5.h[i0:i1], m5.lo[i0:i1], m5.c[i0:i1]
    if len(H) < K.OR_BARS + 3:
        rows.append(rec); continue
    or_hi = H[:K.OR_BARS].max()
    or_lo = Lo[:K.OR_BARS].min()
    up = np.flatnonzero(H[K.OR_BARS:] > or_hi)
    dn = np.flatnonzero(Lo[K.OR_BARS:] < or_lo)
    iu = up[0] if len(up) else 10 ** 9
    idn = dn[0] if len(dn) else 10 ** 9
    if iu == idn == 10 ** 9:
        rows.append(rec); continue
    if iu <= idn:
        direction, level, stop_eff, bi = 1, or_hi, or_lo, K.OR_BARS + int(iu)
    else:
        direction, level, stop_eff, bi = -1, or_lo, or_hi, K.OR_BARS + int(idn)
    fh, fl = H[bi:], Lo[bi:]
    hit = np.flatnonzero(fl <= stop_eff) if direction == 1 else np.flatnonzero(fh >= stop_eff)
    if len(hit):
        exit_px, outcome, hit_bar = stop_eff, "STOP", bi + int(hit[0])
    else:
        exit_px, outcome, hit_bar = C[-1], "TIME_STOP", len(C) - 1
    rec.update({
        "found": True,
        "rep_or_hi": or_hi, "rep_or_lo": or_lo, "rep_or_range": or_hi - or_lo,
        "rep_direction": direction, "rep_level": level, "rep_stop_eff": stop_eff,
        "rep_bi": bi, "rep_ttb": bi - K.OR_BARS, "rep_exit_px": exit_px,
        "rep_outcome": outcome, "rep_exit_bar": hit_bar, "n_m5_bars": len(C),
        "entry_ts": m5.ts[i0 + bi], "exit_ts": m5.ts[i0 + hit_bar],
        "or_end_ts": m5.ts[i0 + K.OR_BARS - 1], "last_ts": m5.ts[i1 - 1],
    })
    rows.append(rec)

X = pd.DataFrame(rows).set_index("date")
J = led.join(X, how="left")
J["found"] = J["found"].fillna(False).astype(bool)
sub = J[J["found"]]
f32 = lambda s: s.astype("float32")

w("")
w("-" * 96)
w("REPRODUCTION AU TICK (float32 = precision de stockage du ledger)")
w("-" * 96)
w(f"  jours du ledger retrouves dans le M1 : {int(J['found'].sum())}/{len(J)}")
for a, b in [("or_hi", "rep_or_hi"), ("or_lo", "rep_or_lo"), ("or_range", "rep_or_range"),
             ("level", "rep_level"), ("stop_eff", "rep_stop_eff"), ("exit_px", "rep_exit_px")]:
    eq = f32(sub[a]) == f32(sub[b])
    w(f"  {a:>10s} : {int(eq.sum()):>5d}/{len(sub)}  ({eq.mean()*100:6.2f}%)")
for a, b in [("direction", "rep_direction"), ("bi", "rep_bi"),
             ("ttb_5min", "rep_ttb"), ("outcome", "rep_outcome")]:
    eq = sub[a] == sub[b]
    w(f"  {a:>10s} : {int(eq.sum()):>5d}/{len(sub)}  ({eq.mean()*100:6.2f}%)")

core = ((f32(sub["or_hi"]) == f32(sub["rep_or_hi"])) &
        (f32(sub["or_lo"]) == f32(sub["rep_or_lo"])) &
        (sub["direction"] == sub["rep_direction"]) & (sub["bi"] == sub["rep_bi"]))
w("")
w(f"  REPRODUCTION COMPLETE (or_hi & or_lo & direction & bi) : "
  f"{int(core.sum())}/{len(sub)}  ({core.mean()*100:.2f}%)")
bad = sub[~core]
if len(bad):
    w(f"  echecs : {len(bad)} -> {[str(x.date()) for x in bad.index[:10]]}")

# fenetre de vie : heure ET de l'entree et de la derniere barre
w("")
w(f"  heure ET de la barre d'entree   : min={sub['entry_ts'].dt.tz_convert('US/Eastern').dt.strftime('%H:%M').min()}"
  f"  max={sub['entry_ts'].dt.tz_convert('US/Eastern').dt.strftime('%H:%M').max()}")
w(f"  heure ET de la fin de l'OR       : "
  f"{sorted(sub['or_end_ts'].dt.tz_convert('US/Eastern').dt.strftime('%H:%M').unique())}"
  "   (attendu 09:55 = derniere barre 5-min de l'OR 09:30-10:00)")
w(f"  heure ET de la derniere barre    : "
  f"{sorted(sub['last_ts'].dt.tz_convert('US/Eastern').dt.strftime('%H:%M').value_counts().head(3).index.tolist())}")

# ---------------------------------------------------------------------------
# Falsificateur d'horloge
# ---------------------------------------------------------------------------
w("")
w("-" * 96)
w("FALSIFICATEUR D'HORLOGE — reconstruire l'OR sur une fenetre DECALEE")
w("-" * 96)
w("  Si l'horloge etait mal identifiee, la fenetre correcte ne serait pas meilleure")
w("  qu'une fenetre decalee d'une heure. On decale l'OR de -12 / 0 / +12 barres 5-min.")
alls = K.m1_all_session()
m5a = K.to_m5(alls)
rth_first = {}
for d, (i0, i1) in m1.bounds.items():
    rth_first[d] = m1.ts[i0]

for shift in (-12, 0, 12):
    n_ok = n_try = 0
    for dt, r in led.iterrows():
        d = pd.Timestamp(dt)
        b = m5a.sl(d)
        if b is None or d not in rth_first:
            continue
        i0, i1 = b
        t0 = rth_first[d] + pd.Timedelta(minutes=5 * shift)
        k = int(np.searchsorted(m5a.ts.asi8[i0:i1], t0.value, "left"))
        s = i0 + k
        if i1 - s < K.OR_BARS + 3:
            continue
        n_try += 1
        if (np.float32(m5a.h[s:s + K.OR_BARS].max()) == np.float32(r["or_hi"]) and
                np.float32(m5a.lo[s:s + K.OR_BARS].min()) == np.float32(r["or_lo"])):
            n_ok += 1
    w(f"  OR decale de {shift:+3d} barres ({shift*5:+4d} min) : "
      f"or_hi & or_lo reproduits {n_ok}/{n_try} ({100*n_ok/max(n_try,1):6.2f}%)")

J.to_parquet(K.OUT / "b1_align_per_trade.parquet")
txt = "\n".join(L)
print(txt)
(K.OUT / "b1_align.txt").write_text(txt + "\n")
