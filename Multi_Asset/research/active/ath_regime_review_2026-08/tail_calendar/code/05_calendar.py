"""VOLET B — calendrier d'evenements a date connue, croise avec les fenetres du sleeve.

1. Mesure l'AMPLITUDE HISTORIQUE du mouvement d'indice par type d'evenement, depuis
   les donnees du repo (calendrier 2018-2026 + panel M5 CET) : |move| de US100 et
   GER40 sur [release, release+60min].
2. Etablit le motif de publication (jour du mois / jour de semaine) pour les
   evenements dont la date forward n'est pas confirmee par une source primaire.
3. Croise le calendrier forward avec les fenetres de detention.

Fenetres du sleeve (CET), jours d'entree = lundi et mardi UNIQUEMENT :
   US100 : entree 22:05 J    -> sortie 15:30 J+1
   GER40 : entree 17:35 J    -> sortie 09:00 J+1

ATTENTION FUSEAU : le calendrier du repo est en datetime_utc (vrai UTC) ; le panel
M5 est en CET (verifie au tick, 01_tz_verify.py). Conversion explicite via
Europe/Paris — le DST est donc traite, pas suppose.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "out"

GER_IN, GER_OUT = (17, 35), (9, 0)
US_IN, US_OUT = (22, 5), (15, 30)


# ---------------------------------------------------------------- 1. amplitudes
def historical_impact():
    cal = pd.read_csv(ROOT / "data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv",
                      parse_dates=["datetime_utc"])
    cal = cal[cal.impact == "HIGH"]
    m5 = pd.read_parquet(ROOT / "data/ftmo_portfolio/cache/sim_m5_repaired.parquet")[["US100", "GER40"]]
    # panel M5 = CET ; on convertit l'heure UTC de l'evenement en CET (DST gere)
    cet = (cal.datetime_utc.dt.tz_localize("UTC").dt.tz_convert("Europe/Paris")
           .dt.tz_localize(None))
    cal = cal.assign(dt_cet=cet)

    targets = {
        "CPI US": ("US", "Inflation Rate"),
        "NFP US": ("US", "Non Farm Payrolls"),
        "PPI US": ("US", "PPI"),
        "PCE US": ("US", "PCE Price Index"),
        "FOMC decision": ("US", "Fed Interest Rate Decision"),
        "FOMC minutes": ("US", "FOMC Minutes"),
        "BCE decision": ("EU", "ECB Interest Rate Decision"),
        "ZEW DE": ("DE", "ZEW Economic Sentiment"),
        "Ifo DE": ("DE", "Ifo Business Climate"),
        "HICP flash EZ": ("EU", "Inflation Rate YoY Flash"),
    }
    rows = []
    for label, (ctry, pat) in targets.items():
        sub = cal[(cal.country == ctry) & cal.event.str.contains(pat, case=False, na=False)]
        if sub.empty:
            continue
        recs = []
        for t in sub.dt_cet:
            for leg in ("US100", "GER40"):
                w = m5[leg].loc[t - pd.Timedelta(minutes=10): t + pd.Timedelta(minutes=60)].dropna()
                if len(w) < 4:
                    continue
                recs.append(dict(leg=leg, move=abs(w.iloc[-1] / w.iloc[0] - 1.0),
                                 rng=(w.max() - w.min()) / w.iloc[0]))
        if not recs:
            continue
        r = pd.DataFrame(recs)
        for leg, g in r.groupby("leg"):
            rows.append(dict(evenement=label, jambe=leg, n=len(g),
                             move_median_bps=1e4 * g["move"].median(),
                             move_p90_bps=1e4 * g["move"].quantile(0.90),
                             amplitude_p90_bps=1e4 * g["rng"].quantile(0.90),
                             amplitude_max_bps=1e4 * g["rng"].max()))
        # motif de publication (pour dater les evenements non confirmes)
        dom = sub.dt_cet.dt.day
        rows[-1]["_dow"] = sub.dt_cet.dt.dayofweek.mode().iloc[0]
        rows[-1]["_dom_med"] = int(dom.median())
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "event_impact_historical.csv", index=False)
    print("=== AMPLITUDE HISTORIQUE PAR TYPE D'EVENEMENT (repo, 2018-2026) ===")
    print("    |move| = |close(T+60min)/close(T-10min)-1| ; amplitude = (max-min)/open")
    print(df.drop(columns=[c for c in df.columns if c.startswith("_")]).round(1).to_string(index=False))
    return df


def zew_pattern():
    cal = pd.read_csv(ROOT / "data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv",
                      parse_dates=["datetime_utc"])
    z = cal[(cal.country == "DE") & cal.event.str.contains("ZEW", na=False)
            & (cal.impact == "HIGH")].copy()
    z["dow"] = z.datetime_utc.dt.dayofweek
    z["nth_tue"] = (z.datetime_utc.dt.day - 1) // 7 + 1
    print("\n=== MOTIF DE PUBLICATION ZEW (repo 2018-2026) ===")
    print(" jour de semaine :", z.dow.value_counts().to_dict(), " (1 = mardi)")
    print(" n-ieme du mois  :", z.nth_tue.value_counts().sort_index().to_dict())
    print(" heure UTC       :", z.datetime_utc.dt.strftime("%H:%M").value_counts().head(3).to_dict())
    return z


# ---------------------------------------------------------------- 3. croisement
def windows(start, end):
    """Fenetres de detention (CET) sur la periode, entrees lundi/mardi seulement."""
    out = []
    for d in pd.date_range(start, end, freq="D"):
        if d.dayofweek not in (0, 1):
            continue
        nxt = d + pd.Timedelta(days=1)
        out.append(("GER40", d.replace(hour=GER_IN[0], minute=GER_IN[1]),
                    nxt.replace(hour=GER_OUT[0], minute=GER_OUT[1])))
        out.append(("US100", d.replace(hour=US_IN[0], minute=US_IN[1]),
                    nxt.replace(hour=US_OUT[0], minute=US_OUT[1])))
    return out


def exposure(ts_cet, wins):
    return sorted({leg for leg, a, b in wins if a <= ts_cet <= b})


def main():
    imp = historical_impact()
    zew_pattern()

    wins = windows("2026-08-09", "2026-09-23")
    ev = pd.read_csv(HERE / "events_raw.csv", parse_dates=["datetime_cet"], date_format="%Y-%m-%d %H:%M")
    ev["jour"] = ev.datetime_cet.dt.day_name().str[:3]
    ev["jambe_exposee"] = ev.datetime_cet.apply(lambda t: "+".join(exposure(t, wins)) or "—")
    ev["expose"] = ev.jambe_exposee != "—"

    # rattache l'amplitude historique mesuree
    med = {(r.evenement, r.jambe): (r.move_median_bps, r.move_p90_bps)
           for r in imp.itertuples()}
    def amp(r):
        legs = [l for l in r.jambe_exposee.split("+") if l in ("US100", "GER40")]
        if not legs or pd.isna(r.cle_impact):
            return ""
        vals = [med.get((r.cle_impact, l)) for l in legs]
        vals = [v for v in vals if v]
        if not vals:
            return ""
        return " ; ".join(f"{l} med {v[0]:.0f} / p90 {v[1]:.0f} bps"
                          for l, v in zip(legs, vals))
    ev["amplitude_historique_60min"] = ev.apply(amp, axis=1)

    cols = ["date", "heure_cet", "jour", "evenement", "zone", "statut_date",
            "jambe_exposee", "amplitude_historique_60min", "source"]
    ev["date"] = ev.datetime_cet.dt.strftime("%Y-%m-%d")
    ev["heure_cet"] = ev.datetime_cet.dt.strftime("%H:%M")
    ev = ev.sort_values("datetime_cet")
    ev[cols].to_csv(OUT / "calendrier_2026-08-09_2026-09-20.csv", index=False)
    pd.set_option("display.width", 300)
    pd.set_option("display.max_colwidth", 60)
    print("\n=== CALENDRIER CROISE AVEC LES FENETRES DU SLEEVE ===")
    print(ev[cols].to_string(index=False))
    n = ev.expose.sum()
    print(f"\nevenements DANS une fenetre de detention : {n} / {len(ev)}")
    print("-> out/calendrier_2026-08-09_2026-09-20.csv")


if __name__ == "__main__":
    main()
