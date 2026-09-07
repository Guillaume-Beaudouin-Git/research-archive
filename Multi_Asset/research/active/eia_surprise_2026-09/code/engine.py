"""Surprise d'inventaires EIA -> pétrole. Spec gelée : ../PREREGISTRATION.md"""
from __future__ import annotations
import numpy as np, pandas as pd, statsmodels.api as sm
from pathlib import Path

R = Path("<HOME>/Desktop/Algo_claude")
B = Path(__file__).resolve().parents[1]
HS = [15, 60, 240]

def hac(x):
    x = np.asarray(x, float)
    if len(x) < 3 or np.std(x) == 0: return np.nan, np.nan
    f = sm.OLS(x, np.ones((len(x), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return float(f.params[0]), float(f.tvalues[0])

cal = pd.read_csv(R/"data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv",
                  parse_dates=["datetime_utc"])
ev = cal[(cal.currency == "USD") &
         (cal.event.astype(str).str.contains("EIA Crude Oil Stocks", case=False, na=False))
         ].dropna(subset=["actual", "forecast"]).copy()
ev["surp"] = ev.actual - ev.forecast
ev = ev.sort_values("datetime_utc").reset_index(drop=True)

px = pd.read_csv(R/"data/deep_history_utc/USOIL_M1.csv",
                 usecols=["timestamp_utc", "close", "spread"])
px["t"] = pd.to_datetime(px["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
px = px.set_index("t").sort_index()
px = px[px.index >= "2017-12-01"]
idx, cl, sp = px.index, px["close"].values, px["spread"].values

rows = []
for ts, s in ev[["datetime_utc", "surp"]].itertuples(index=False):
    j = int(idx.searchsorted(ts, side="right"))          # delai +1 barre
    if j >= len(idx) - max(HS) - 1: continue
    if (idx[j] - ts).total_seconds() > 3600: continue     # entree < 1h apres publication
    r = {"ts": ts, "surp": s, "entry_px": cl[j], "spread_pts": sp[j]}
    for H in HS:
        k = min(j + H, len(idx) - 1)
        if (idx[k] - idx[j]).total_seconds() > H * 60 * 3: r[f"h{H}"] = np.nan; continue
        r[f"h{H}"] = -np.sign(s) * (cl[k] - cl[j]) / cl[j]     # cote = -signe(surprise)
    d = idx[j].normalize() + pd.Timedelta(hours=20, minutes=59)
    k = int(idx.searchsorted(d, side="right")) - 1
    r["hclose"] = -np.sign(s) * (cl[k] - cl[j]) / cl[j] if k > j else np.nan
    rows.append(r)

t = pd.DataFrame(rows).dropna(subset=["h15", "h60", "h240"])
# cout : spread en points -> fraction du prix, aller-retour
t["cost"] = (t["spread_pts"] * 0.001) / t["entry_px"]
cost_bps = t["cost"].median() * 1e4
print(f"n = {len(t)} evenements  |  {t.ts.min().date()} -> {t.ts.max().date()}")
print(f"cout RT median mesure (spread, 1 point = 0.001 USD) : {cost_bps:.2f} bps\n")

print("RESULTAT PRINCIPAL — brut, cote = -signe(surprise)")
print(f"{'horizon':<12}{'n':<6}{'brut bps':<12}{'t_HAC':<10}{'net bps':<11}{'brut/3xcout'}")
res = {}
for lab, col in [("15 min", "h15"), ("60 min", "h60"), ("240 min", "h240"), ("cloture", "hclose")]:
    v = t[col].dropna().values
    m, tt = hac(v)
    net = m - t["cost"].median()
    res[lab] = (m, tt)
    print(f"{lab:<12}{len(v):<6}{m*1e4:+9.2f}   {tt:+7.2f}   {net*1e4:+8.2f}   {m/(3*t['cost'].median()):+8.2f}")

print("\nCONTROLE DE DOSE — reponse par tercile de |surprise| (le diagnostic principal)")
t["absq"] = pd.qcut(t["surp"].abs(), 3, labels=["T1 faible", "T2 moyen", "T3 fort"])
print(f"{'tercile':<12}{'n':<6}{'|surp| med':<13}{'h15 bps':<12}{'h60 bps':<12}{'h240 bps'}")
for q in ["T1 faible", "T2 moyen", "T3 fort"]:
    g = t[t.absq == q]
    print(f"{q:<12}{len(g):<6}{g.surp.abs().median():<13.2f}"
          f"{g.h15.mean()*1e4:+9.2f}   {g.h60.mean()*1e4:+9.2f}   {g.h240.mean()*1e4:+9.2f}")
t.to_csv(B/"results/events.csv", index=False)
