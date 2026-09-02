"""Reconstruction independante de la jambe overnight US100/GER40, ancree
en heure d'echange AVEC DST (America/New_York pour US100, Europe/Berlin
pour GER40), nuit etiquetee par le jour d'ENTREE (jour de la cloture tenue),
PAS le jour d'ouverture -- c'est le piege signale par le coordinateur (une
nuit etiquetee par l'ouverture fait passer le gap de week-end pour du
"lundi" et gonfle artificiellement le mercredi).

Source : M1 OHLC vrai-UTC, cache local
`/private/tmp/.../scratchpad/m1_cache/{US100,GER40}_M1.parquet`
(identique a data/deep_history_utc/{sym}_M1.csv, verifie infra).

Sessions cash retenues (coherentes avec le sleeve LIVE, build_series.py) :
  US100 : 09:30-16:00 America/New_York (NASDAQ-100 cash)
  GER40 : 09:00-17:30 Europe/Berlin   (Xetra)
Le sleeve deploye entre a la cloture (+5 min) et sort a l'ouverture suivante
(cf `funded_1y_mono_2026-08/attribution/build_series.py` : US100 2205->1530
Paris, GER40 1735->0900 Paris -- ce sont exactement ces deux horaires en
heure d'echange native, +5 min).

Interpreteur : /usr/bin/python3
"""
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path("<SCRATCH>"
             "9fd32b98-b3ee-47bf-93c1-b7c5a1ac70a6/scratchpad/m1_cache")
OUT = Path(__file__).resolve().parent.parent / "results"

SESSIONS = {
    "US100": dict(tz="America/New_York", open="09:30", close="16:00"),
    "GER40": dict(tz="Europe/Berlin", open="09:00", close="17:30"),
}


def load_m1(sym: str) -> pd.DataFrame:
    df = pd.read_parquet(CACHE / f"{sym}_M1.parquet")
    return df.sort_index()


def to_local(df: pd.DataFrame, tz: str) -> pd.DataFrame:
    out = df.copy()
    out.index = out.index.tz_convert(tz)
    return out


def session_prices(df_local: pd.DataFrame, open_hm: str, close_hm: str) -> pd.DataFrame:
    """Un enregistrement par jour calendaire local : premier prix a/apres
    `open_hm`, dernier prix a/avant `close_hm`, + range de la derniere
    demi-heure et TWAP de la derniere demi-heure (proxy Partie C)."""
    idx = df_local.index
    hm = idx.hour * 60 + idx.minute
    oh, om = map(int, open_hm.split(":"))
    ch, cm = map(int, close_hm.split(":"))
    o_min, c_min = oh * 60 + om, ch * 60 + cm

    day = pd.Series(idx.date, index=idx)
    rows = []
    for d, g in df_local.groupby(day):
        ghm = (g.index.hour * 60 + g.index.minute).to_numpy()
        # open: premiere barre >= o_min (tolerance 15 min pour jours ecourtes)
        j_open = np.searchsorted(ghm, o_min, side="left")
        # close: derniere barre <= c_min
        j_close = np.searchsorted(ghm, c_min, side="right") - 1
        if j_open >= len(ghm) or j_close < 0 or j_open > j_close:
            continue
        if abs(ghm[j_open] - o_min) > 20 or abs(ghm[j_close] - c_min) > 20:
            # session tronquee/decalee (ferie partiel, trou de donnees) -> skip
            continue
        px_open = float(g["open"].to_numpy()[j_open])
        px_close = float(g["close"].to_numpy()[j_close])
        # derniere demi-heure avant close : proxy de dispersion (Partie C)
        last30_mask = (ghm > c_min - 30) & (ghm <= c_min)
        seg = g.iloc[last30_mask] if last30_mask.any() else g.iloc[[j_close]]
        hi30 = float(seg["high"].max())
        lo30 = float(seg["low"].min())
        twap30 = float(seg["close"].mean())
        rows.append(dict(date=pd.Timestamp(d), px_open=px_open, px_close=px_close,
                          range30_bps=(hi30 - lo30) / px_close * 1e4,
                          twap_dev_bps=(px_close - twap30) / px_close * 1e4,
                          n_bars=len(g)))
    return pd.DataFrame(rows).set_index("date").sort_index()


def build(sym: str) -> pd.DataFrame:
    cfg = SESSIONS[sym]
    raw = load_m1(sym)
    loc = to_local(raw, cfg["tz"])
    S = session_prices(loc, cfg["open"], cfg["close"])
    S["weekday"] = S.index.dayofweek  # 0=lundi ... 4=vendredi (jour d'ENTREE = jour courant)
    S["next_open"] = S["px_open"].shift(-1)
    S["next_date"] = S.index.to_series().shift(-1)
    S["gap_cal_days"] = (S["next_date"] - S.index.to_series()).dt.days
    S["ov_bps_entryday"] = (S["next_open"] / S["px_close"] - 1.0) * 1e4
    # convention alternative (piege) : etiquette par le jour d'OUVERTURE (t+1)
    S["ov_bps_openday"] = S["ov_bps_entryday"]  # meme nombre, autre etiquette de ligne
    # guard anti-artefact (roll/ferie/tick errone), coherent avec fix_overnight.py (|.|<800bps)
    S.loc[S["ov_bps_entryday"].abs() > 800, ["ov_bps_entryday"]] = np.nan
    return S


if __name__ == "__main__":
    for sym in ("US100", "GER40"):
        S = build(sym)
        S.to_csv(OUT / f"{sym.lower()}_overnight_daily.csv", float_format="%.6g")
        n = S["ov_bps_entryday"].notna().sum()
        print(f"{sym}: {len(S)} sessions cash, {n} nuits mesurees, "
              f"{S.index.min().date()} -> {S.index.max().date()}")
        print(S.groupby("weekday")["ov_bps_entryday"].agg(["mean", "count"]).round(3))
        print()
