"""Vérification du fuseau AU TICK des deux sources US100/GER40.

Méthode (L56) : le pic d'activité d'une ouverture de séance est ancré à l'horloge
de l'échange AVEC son DST. On localise le pic d'activité intraday séparément en
hiver (DJF) et en été (JJA) :

  - Si l'index est une horloge européenne DST-suiveuse (CET ou EET), le pic tombe
    au MÊME index-minute été comme hiver.
  - Si l'index est du vrai UTC, le pic SE DÉCALE d'une heure entre les deux.

Puis, pour trancher CET vs EET : position absolue du pic.
  ouverture cash US   09:30 ET = 15:30 CET = 16:30 EET
  ouverture Xetra     09:00 CET           = 10:00 EET

Sorties : out/tz_verify.json + tableau console.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)


def activity_profile(s: pd.Series, months) -> pd.Series:
    """Moyenne de |log-return| par minute-de-jour de l'index, sur les mois donnés."""
    s = s.dropna()
    s = s[s.index.month.isin(months)]
    r = np.log(s).diff().abs()
    mod = s.index.hour * 60 + s.index.minute
    return r.groupby(mod).mean() * 1e4  # bps


def peak_window(prof: pd.Series, lo_min: int, hi_min: int) -> int:
    """Minute-de-jour du max d'activité dans [lo, hi]."""
    sub = prof[(prof.index >= lo_min) & (prof.index <= hi_min)]
    return int(sub.idxmax())


def hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def verify(name: str, s: pd.Series, expect_open_cet: int, search_lo: int, search_hi: int):
    win = activity_profile(s, [12, 1, 2])
    sum_ = activity_profile(s, [6, 7, 8])
    pw, ps = peak_window(win, search_lo, search_hi), peak_window(sum_, search_lo, search_hi)
    # corrélation des profils horaires hiver/été (test L56)
    common = win.index.intersection(sum_.index)
    corr = float(np.corrcoef(win.reindex(common), sum_.reindex(common))[0, 1])
    shift = ps - pw
    offset_vs_cet = pw - expect_open_cet
    return dict(series=name, peak_winter=hhmm(pw), peak_summer=hhmm(ps),
                dst_shift_min=int(shift), profile_corr_winter_summer=round(corr, 4),
                expected_open_cet=hhmm(expect_open_cet),
                implied_offset_vs_cet_min=int(offset_vs_cet),
                verdict=_verdict(shift, offset_vs_cet))


def _verdict(shift, off):
    if abs(shift) >= 45:
        return "HORLOGE UTC (le pic se decale avec le DST)"
    if abs(off) <= 10:
        return "HORLOGE CET/CEST (index == CET)"
    if 50 <= off <= 70:
        return "HORLOGE EET/EEST (index = CET + 1h) -- PIEGE timestamp_utc"
    return f"INDETERMINE (offset {off} min)"


res = []

# ---- source 1 : cache sim (grille M5 sur laquelle la regle daily est verifiee)
m5 = pd.read_parquet(ROOT / "data/ftmo_portfolio/cache/sim_m5_repaired.parquet")
print(f"sim_m5_repaired : {m5.index.min()} -> {m5.index.max()}  tz={m5.index.tz}")
res.append(verify("sim_m5_repaired.US100", m5["US100"], 15 * 60 + 30, 13 * 60, 18 * 60))
res.append(verify("sim_m5_repaired.GER40", m5["GER40"], 9 * 60, 7 * 60, 12 * 60))

# ---- source 2 : deep_history_utc (documente TRUE UTC)
for sym, exp, lo, hi in [("US100", 15 * 60 + 30, 13 * 60, 18 * 60),
                         ("GER40", 9 * 60, 7 * 60, 12 * 60)]:
    df = pd.read_csv(ROOT / f"data/deep_history_utc/{sym}_M1.csv",
                     usecols=["timestamp_utc", "close"],
                     parse_dates=["timestamp_utc"], date_format="%Y.%m.%d %H:%M:%S")
    df = df.set_index("timestamp_utc")["close"]
    df = df[~df.index.duplicated()].sort_index()
    print(f"deep_history_utc/{sym} : {df.index.min()} -> {df.index.max()}  n={len(df):,}")
    res.append(verify(f"deep_history_utc.{sym}", df, exp, lo, hi))

out = pd.DataFrame(res)
pd.set_option("display.width", 200)
print("\n", out.to_string(index=False))
(OUT / "tz_verify.json").write_text(json.dumps(res, indent=2))
print("\n-> out/tz_verify.json")
