"""Etape 0 — integrite des donnees et des BORNES, avant toute conclusion.

L52 : ne jamais faire confiance au nom d'un champ ; verifier les bornes de segment
      contre des barres M1 independantes (profil d'activite intraday).
L56 : horloge de l'echange avec son DST ; test de falsification hiver-vs-ete dans
      DEUX horloges (CET = horloge du schedule EA, ET = horloge du CME/Nasdaq, UTC).
L60 : part de barres a fourchette nulle, par serie et par annee.
"""
from __future__ import annotations
import sys, os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_m1, stamps, px_at, SEG, TZ, CACHE_DIR  # noqa

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
os.makedirs(OUT, exist_ok=True)


def l60_zero_range(df: pd.DataFrame, sym: str) -> pd.DataFrame:
    zr = (df["high"] == df["low"]).groupby(df.index.year).mean()
    flat = ((df["high"] == df["low"]) & (df["close"] == df["open"])).groupby(df.index.year).mean()
    n = df.groupby(df.index.year).size()
    return pd.DataFrame({"sym": sym, "year": zr.index, "share_zero_range": zr.values,
                         "share_fully_flat": flat.values, "n_bars": n.values})


def hourly_profile(df: pd.DataFrame, tzname: str) -> pd.DataFrame:
    """Profil horaire d'ACTIVITE (|log-ret| moyen par minute) en hiver et en ete."""
    idx = df.index.tz_convert(tzname)
    lr = np.log(df["close"]).diff().abs()
    month = idx.month
    winter = np.isin(month, [12, 1, 2])
    summer = np.isin(month, [6, 7, 8])
    h = idx.hour
    out = {}
    for lab, mask in (("winter", winter), ("summer", summer)):
        s = pd.Series(lr.values[mask]).groupby(h[mask]).mean()
        out[lab] = s.reindex(range(24))
    return pd.DataFrame(out)


def main():
    rows_l60, rows_l56, rows_cov, rows_bnd = [], [], [], []
    for sym in ("US100", "GER40"):
        df = load_m1(sym)
        print(f"[{sym}] {len(df):,} barres  {df.index[0]} -> {df.index[-1]}")
        rows_l60.append(l60_zero_range(df, sym))

        # --- L56 : test de falsification hiver-vs-ete dans 3 horloges -------------
        for tzname in ("Europe/Paris", "America/New_York", "UTC"):
            p = hourly_profile(df, tzname).dropna()
            c = float(np.corrcoef(p["winter"], p["summer"])[0, 1])
            rows_l56.append({"sym": sym, "clock": tzname, "corr_winter_summer": c})
            print(f"  L56 {sym:6s} {tzname:18s} corr(hiver,ete) = {c:.3f}")

        # --- L52 : les bornes tombent-elles sur les evenements attendus ? --------
        # profil minute-par-minute de l'activite autour de chaque borne, horloge CET
        idx = df.index
        lr = np.log(df["close"]).diff().abs()
        minute_of_day = idx.hour * 60 + idx.minute
        prof = pd.Series(lr.values).groupby(minute_of_day).mean()
        # rang du pic d'activite : ou est le maximum de la journee ?
        top = prof.sort_values(ascending=False).head(5)
        print(f"  L52 {sym}: top-5 minutes CET par |ret| moyen -> "
              + ", ".join(f"{m//60:02d}:{m%60:02d}" for m in top.index))
        for lab, (hh, mm) in (("entry", SEG[sym]["entry"]), ("exit", SEG[sym]["exit"])):
            m = hh * 60 + mm
            rows_bnd.append({
                "sym": sym, "boundary": lab, "cet": f"{hh:02d}:{mm:02d}",
                "abs_ret_bps": float(prof.get(m, np.nan) * 1e4),
                "pctile_in_day": float((prof < prof.get(m, np.nan)).mean() * 100),
                "abs_ret_bps_m5_before": float(prof.get(m - 5, np.nan) * 1e4),
                "abs_ret_bps_m5_after": float(prof.get(m + 5, np.nan) * 1e4),
            })

        # --- couverture des barres aux horodatages exacts du schedule ------------
        days = pd.DatetimeIndex(sorted(set(idx.normalize().tz_localize(None))))
        days = days[days.dayofweek < 5]
        for lab, (hh, mm) in (("entry", SEG[sym]["entry"]), ("exit", SEG[sym]["exit"])):
            tg = stamps(days, hh, mm)
            exact = pd.Series(df["close"].reindex(tg).notna().values, index=days)
            tol = px_at(df["close"], tg).notna()
            rows_cov.append({"sym": sym, "boundary": lab, "cet": f"{hh:02d}:{mm:02d}",
                             "n_weekdays": len(days),
                             "share_exact_bar": float(exact.mean()),
                             "share_within_20min": float(np.mean(tol.values))})

    pd.concat(rows_l60).to_csv(os.path.join(OUT, "step0_l60_zero_range.csv"), index=False)
    pd.DataFrame(rows_l56).to_csv(os.path.join(OUT, "step0_l56_clock_falsification.csv"), index=False)
    pd.DataFrame(rows_bnd).to_csv(os.path.join(OUT, "step0_l52_boundaries.csv"), index=False)
    pd.DataFrame(rows_cov).to_csv(os.path.join(OUT, "step0_coverage.csv"), index=False)
    print("\n--- L60 (part de barres high==low) ---")
    print(pd.concat(rows_l60).pivot(index="year", columns="sym", values="share_zero_range").round(4))
    print("\n--- couverture aux bornes ---")
    print(pd.DataFrame(rows_cov).round(4).to_string(index=False))
    print("\n--- L52 bornes ---")
    print(pd.DataFrame(rows_bnd).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
