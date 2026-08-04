"""L59 — re-pricing HONNÊTE de la SORTIE du micro-ORB (stop-entry / bracket-exit).

Le ledger `nq_v2_trades.parquet` remplit 100% de ses 1,590 sorties STOP au prix
EXACT du stop (verifié : exit_px == stop_eff sur 1590/1590). La série R utilisée
par le sim (`orb_e7_Rera.parquet`) hérite de cette convention (37.8% de R == -1.0
au tick). L59 dit que ~25% des barres de stop OUVRENT au-delà.

Mesure ici, sur les barres M1 CANONIQUES de l'instrument du ledger
(`data/raw/NQ_1min_databento_2010-2026.parquet`, GLBX), et pour chaque trade
stoppé : la première barre qui traverse `stop_eff` ouvre-t-elle déjà au-delà ?
Si oui, le remplissage honnête est l'OPEN de cette barre, pas le stop.

Sortie : `mR_l59.npy` = série R re-pricée, alignée sur M["dates"].
"""
import numpy as np
import pandas as pd

import mo_common as K

MAIN = K.MAIN
LED = MAIN / "PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet"
NQ = MAIN / "data/raw/NQ_1min_databento_2010-2026.parquet"

led = pd.read_parquet(LED)
R7 = pd.read_parquet(K.E.CACHE / "orb_e7_Rera.parquet")["R"]
led["R7"] = R7.values

px = pd.read_parquet(NQ, columns=["open", "high", "low", "close"])
# horloge : le ledger et l'OR sont définis en heure de PARIS ; l'instrument est
# américain. On convertit explicitement (L56) au lieu de supposer un décalage fixe.
px.index = px.index.tz_convert("Europe/Paris")
px["d"] = px.index.normalize().tz_localize(None)
px["hm"] = px.index.hour * 100 + px.index.minute
grp = {d: g for d, g in px.groupby("d", sort=False)}

rows = []
for dt, r in led.iterrows():
    g = grp.get(pd.Timestamp(dt))
    if g is None:
        rows.append(dict(date=dt, ok=False))
        continue
    # fenêtre de vie du trade : de l'entrée possible (16:00) à la clôture RTH (22:00)
    w = g[(g.hm >= 1600) & (g.hm <= 2200)]
    if len(w) == 0:
        rows.append(dict(date=dt, ok=False))
        continue
    stop = float(r.stop_eff)
    entry = float(r.entry)
    d = int(r.direction)
    Rden = abs(entry - stop)
    if d > 0:
        cross = np.where(w["low"].to_numpy() <= stop)[0]
    else:
        cross = np.where(w["high"].to_numpy() >= stop)[0]
    if len(cross) == 0:
        rows.append(dict(date=dt, ok=True, hit=False, gap_pts=0.0, Rden=Rden,
                         outcome=r.outcome))
        continue
    b = w.iloc[cross[0]]
    op = float(b["open"])
    gap = (stop - op) if d > 0 else (op - stop)      # >0 => la barre OUVRE au-delà
    rows.append(dict(date=dt, ok=True, hit=True, gap_pts=max(gap, 0.0), Rden=Rden,
                     opened_beyond=gap > 0, outcome=r.outcome))

X = pd.DataFrame(rows).set_index("date")
X["opened_beyond"] = X.get("opened_beyond", False)
X["opened_beyond"] = X["opened_beyond"].fillna(False).astype(bool)
X["hit"] = X.get("hit", False)
X["hit"] = X["hit"].fillna(False).astype(bool)
X["ok"] = X["ok"].fillna(False).astype(bool)
X["gap_R"] = (X.gap_pts / X.Rden).fillna(0.0)
cov = X.ok.mean()
st = X[X.ok & (X.outcome == "STOP")]
ts = X[X.ok & (X.outcome == "TIME_STOP")]

L = []
w = L.append
w("=== L59 — re-pricing de la SORTIE (barres M1 NQ canoniques) ===")
w(f"couverture M1 du ledger : {cov*100:.1f}% ({int(X.ok.sum())}/{len(X)})")
w(f"\n[sorties STOP, N={len(st)}]")
w(f"  barre de stop qui OUVRE AU-DELÀ du stop : {st.opened_beyond.mean()*100:.1f}%"
  f"   (L59 annonce ~25%)")
w(f"  dépassement en R | conditionnel au gap : moyenne {st.loc[st.opened_beyond,'gap_R'].mean():.3f}R"
  f" p50 {st.loc[st.opened_beyond,'gap_R'].median():.3f} p90 {st.loc[st.opened_beyond,'gap_R'].quantile(.9):.3f}"
  f" p99 {st.loc[st.opened_beyond,'gap_R'].quantile(.99):.3f} max {st.gap_R.max():.3f}")
w(f"  dépassement MOYEN sur toutes les sorties STOP : {st.gap_R.mean():.4f}R")
w(f"\n[sorties TIME_STOP, N={len(ts)} — le stop a-t-il été TOUCHÉ avant 22:00 ?]")
w(f"  stop touché en intraday alors que le ledger sort au time-stop : {ts.hit.mean()*100:.1f}%"
  f"  (>0 = incohérence de chemin, à signaler)")

# --- série R re-pricée ---------------------------------------------------
gapR = X["gap_R"].reindex(led.index).fillna(0.0)
is_stop = (led.outcome == "STOP").to_numpy()
R_l59 = led["R7"].to_numpy(float).copy()
R_l59[is_stop] -= gapR.to_numpy()[is_stop]
led["R_l59"] = R_l59
w("\n[effet sur la série R utilisée par le sim]")
w(f"  R_era      : moyenne {led.R7.mean():+.4f}  sd {led.R7.std():.3f}  min {led.R7.min():.3f}")
w(f"  R_L59      : moyenne {led.R_l59.mean():+.4f}  sd {led.R_l59.std():.3f}  min {led.R_l59.min():.3f}")
w(f"  delta moyen: {led.R_l59.mean()-led.R7.mean():+.4f} R/trade")
sr = lambda x: x.mean() / x.std() * np.sqrt(236.1)
w(f"  Sharpe per-trade annualisé (236 trades/an) : {sr(led.R7):.3f} -> {sr(led.R_l59):.3f}")

R_l59_s = pd.Series(R_l59, index=led.index)
out = R_l59_s.reindex(K.dates()).fillna(0.0).to_numpy(float)
np.save(K.OUT / "mR_l59.npy", out)
txt = "\n".join(L)
print(txt)
(K.OUT / "q3_l59.txt").write_text(txt)
X.to_parquet(K.OUT / "l59_gaps.parquet")
