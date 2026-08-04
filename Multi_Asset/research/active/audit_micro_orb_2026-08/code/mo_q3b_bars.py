"""L59 (résolution M5 = celle du ledger) + L60 (barres à fourchette nulle) + L56 (horloge).

- L59 : le ledger raisonne en barres 5-min (`bi`, `ttb_5min`). Le taux de barres de
  stop qui OUVRENT au-delà dépend de la RÉSOLUTION : on le mesure à M1 ET à M5.
- L60 : part de barres high==low (print de règlement, pas un prix) par série/an,
  sur l'instrument du ledger (NQ) ET sur l'instrument RÉELLEMENT tradé (US100.cash).
- L56 : l'OR est défini en heure de PARIS, l'instrument est américain. Paris et
  New York ne changent pas d'heure les mêmes semaines -> mesure du décalage.
"""
import numpy as np
import pandas as pd

import mo_common as K

MAIN = K.MAIN
led = pd.read_parquet(MAIN / "PropFirms/ftmo/program_2026-06/ftmo_research/audit/"
                             "nq_v2_trades.parquet")
px = pd.read_parquet(MAIN / "data/raw/NQ_1min_databento_2010-2026.parquet",
                     columns=["open", "high", "low", "close"])
px.index = px.index.tz_convert("Europe/Paris")

L = []
w = L.append

# ---------------- L59 à M5 -------------------------------------------------
m5 = px.resample("5min").agg(dict(open="first", high="max", low="min", close="last")).dropna()
m5["d"] = m5.index.normalize().tz_localize(None)
m5["hm"] = m5.index.hour * 100 + m5.index.minute
g5 = {d: g for d, g in m5.groupby("d", sort=False)}
res = []
for dt, r in led[led.outcome == "STOP"].iterrows():
    g = g5.get(pd.Timestamp(dt))
    if g is None:
        continue
    wnd = g[(g.hm >= 1600) & (g.hm <= 2200)]
    if len(wnd) == 0:
        continue
    stop, d = float(r.stop_eff), int(r.direction)
    Rden = abs(float(r.entry) - stop)
    cr = np.where(wnd["low"].to_numpy() <= stop)[0] if d > 0 \
        else np.where(wnd["high"].to_numpy() >= stop)[0]
    if len(cr) == 0:
        continue
    op = float(wnd.iloc[cr[0]]["open"])
    gap = (stop - op) if d > 0 else (op - stop)
    res.append(dict(beyond=gap > 0, gapR=max(gap, 0.0) / Rden))
S5 = pd.DataFrame(res)
w("=== L59 — sensibilité à la RÉSOLUTION DE BARRE (sorties STOP) ===")
w(f"  M1 : 1.5% des barres de stop ouvrent au-delà (cf. q3_l59.txt)")
w(f"  M5 (résolution du ledger, N={len(S5)}) : {S5.beyond.mean()*100:.1f}%"
  f" ; dépassement moyen conditionnel {S5.loc[S5.beyond,'gapR'].mean():.3f}R"
  f" ; dépassement moyen inconditionnel {S5.gapR.mean():.4f}R")
w("  => le '25%' de L59 est une valeur de FAMILLE (gap_pattern, barres daily avec"
  " gap overnight), PAS une constante : sur un stop intraday d'index à M1/M5 le"
  " taux est un ordre de grandeur plus bas.")

# ---------------- L60 : barres à fourchette nulle ---------------------------
w("\n=== L60 — part de barres à fourchette NULLE (high==low) ===")
nq = px[(px.index.hour * 100 + px.index.minute >= 1600)
        & (px.index.hour * 100 + px.index.minute <= 2200)]
z = (nq.high == nq.low).groupby(nq.index.year).mean()
w(f"  NQ M1 (fenêtre 16:00-22:00 Paris) global {float((nq.high==nq.low).mean())*100:.2f}%"
  f" ; pire année {z.idxmax()} {z.max()*100:.2f}% ; meilleure {z.idxmin()} {z.min()*100:.2f}%")

u = pd.read_csv(MAIN / "data/deep_history_utc/US100_M1.csv", nrows=None,
                usecols=lambda c: c.lower() in
                ("timestamp_utc", "time", "datetime", "open", "high", "low", "close"))
tc = [c for c in u.columns if c.lower() in ("timestamp_utc", "time", "datetime")][0]
u[tc] = pd.to_datetime(u[tc], utc=True, errors="coerce", format="%Y.%m.%d %H:%M:%S")
u = u.dropna(subset=[tc]).set_index(tc)
u.index = u.index.tz_convert("Europe/Paris")
uw = u[(u.index.hour * 100 + u.index.minute >= 1600)
       & (u.index.hour * 100 + u.index.minute <= 2200)]
zz = (uw.high == uw.low).groupby(uw.index.year).mean()
w(f"  US100.cash M1 (INSTRUMENT RÉEL, deep_history_utc, 16:00-22:00 Paris)"
  f" global {float((uw.high==uw.low).mean())*100:.2f}%")
w("    par an : " + ", ".join(f"{y}:{v*100:.1f}%" for y, v in zz.items()))
w(f"  couverture US100.cash : {u.index.min().date()} -> {u.index.max().date()},"
  f" {len(u):,} barres")

# ---------------- L56 : horloge --------------------------------------------
w("\n=== L56 — horloge : l'OR est en heure de PARIS, l'instrument est américain ===")
idx = px.index
off_par = idx.tz_convert("Europe/Paris").map(lambda t: t.utcoffset().total_seconds() / 3600)
off_ny = idx.tz_convert("America/New_York").map(lambda t: t.utcoffset().total_seconds() / 3600)
delta = pd.Series(np.asarray(off_par) - np.asarray(off_ny), index=idx)
d_day = delta.groupby(idx.normalize()).first()
base = d_day.mode().iloc[0]
mism = d_day[d_day != base]
w(f"  décalage Paris-NY normal : {base:.0f}h ; jours de DÉSYNCHRONISATION DST :"
  f" {len(mism)} / {len(d_day)} = {len(mism)/len(d_day)*100:.1f}%"
  f" (~{len(mism)/ (d_day.index.year.nunique()):.0f} jours/an)")
w(f"  décalages observés ces jours-là : {sorted(set(mism.round(0).astype(int).tolist()))}h"
  " -> l'OR 15:30 Paris tombe une heure À CÔTÉ de l'ouverture cash 09:30 ET.")
if len(mism):
    yrs = mism.groupby(mism.index.year).size()
    w("    jours désynchronisés par an : " + ", ".join(f"{y}:{v}" for y, v in yrs.items()))

txt = "\n".join(L)
print(txt)
(K.OUT / "q3b_bars.txt").write_text(txt)
