"""Chargement M1 true-UTC + utilitaires (rollover dodge, sleeve overnight v2.2).

LECTURE SEULE sur data/ du repertoire PRINCIPAL (chemins absolus). Caches ecrits
dans CACHE_DIR, propre a cette session (un agent frere tourne en parallele).
Interpreteur: /usr/bin/python3 explicite.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
import statsmodels.api as sm

MAIN = "<HOME>/Desktop/Algo_claude"
RAW = os.path.join(MAIN, "data", "deep_history_utc")
CACHE_DIR = ("<SCRATCH>"
             "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/rollover_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

TZ = "Europe/Paris"            # = Europe/Prague = CET/CEST, l'horloge du schedule EA
TZ_SERVER_OFFSET_H = 1         # serveur FTMO = Paris + 1h (EET), verifie ts_server 17:14 / ts_paris 16:14
ROLLOVER_PARIS = (23, 0)       # 00:00 serveur = 23:00 Paris toute l'annee (meme DST europeen)
ERA_CUT = pd.Timestamp("2021-01-01")

# COST_AUDIT.md (cost_denominator_2026-07) : indices ~1.8 bps RT mesure.
RT_BPS = {"US100": 1.8, "GER40": 1.8}
# spec_v22.yaml measured_specs, ancres 2026-06-10 (bps/nuit, jambe LONGUE)
SWAP_LONG_BPS = {"US100": -2.126, "GER40": -1.564}
# facture LIVE mesure (data/ftmo_portfolio/swaps_billed_live.csv, nuit 2026-08-04)
SWAP_LIVE_BPS = {"US100": -2.125, "GER40": -1.679}
TRIPLE_DOW = 4                 # vendredi, indices (spec_v22 measured_specs)

# schedule_cet du spec v2.2 (cleanroom/engine.py) — la SORTIE, invariante dans ce dossier
EXIT = {"US100": (15, 30), "GER40": (9, 0)}
ENTRY_LIVE = {"US100": (22, 5), "GER40": (17, 35)}


def load_m1(sym: str) -> pd.DataFrame:
    """M1 true-UTC -> tz Europe/Paris. Cache parquet local (hors repo)."""
    cache = os.path.join(CACHE_DIR, f"{sym}_m1_paris.parquet")
    if os.path.exists(cache):
        return pd.read_parquet(cache)
    df = pd.read_csv(
        os.path.join(RAW, f"{sym}_M1.csv"),
        usecols=["timestamp_utc", "open", "high", "low", "close", "tick_volume", "spread"],
    )
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    df = df.drop(columns=["timestamp_utc"])
    df.index = ts.dt.tz_convert(TZ)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_parquet(cache)
    return df


def stamps(dates, hh: int, mm: int, day_shift: int = 0) -> pd.DatetimeIndex:
    """Horodatages tz-aware Paris (DST natif) a hh:mm, decales de day_shift jours."""
    base = [pd.Timestamp(d.year, d.month, d.day, tz=TZ) for d in dates]
    return pd.DatetimeIndex([b + pd.Timedelta(days=day_shift, hours=hh, minutes=mm)
                             for b in base])


def px_at(close: pd.Series, targets: pd.DatetimeIndex, tol="20min") -> pd.Series:
    """Close de la derniere barre <= target, dans une tolerance. NaN sinon."""
    s = close.reindex(targets, method="ffill", tolerance=pd.Timedelta(tol))
    s.index = targets
    return s


def hac_t(x, lags: int = 6):
    """Moyenne, t_HAC(Newey-West lag-6), N."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return (float(np.mean(x)) if n else np.nan), np.nan, n
    r = sm.OLS(x, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(r.params[0]), float(r.tvalues[0]), n


def block_bootstrap_mean(x, block: int = 10, n_boot: int = 5000, seed: int = 7):
    """IC90/IC95 de la moyenne par bootstrap par blocs circulaire (Politis-Romano)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 20:
        return (np.nan,) * 4
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(n_boot, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
    means = x[idx.reshape(n_boot, -1)[:, :n]].mean(axis=1)
    return (float(np.percentile(means, 5)), float(np.percentile(means, 95)),
            float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def sharpe_ann(x, obs_per_year: float) -> float:
    """Sharpe annualise en sqrt(obs/an) (L47), pas sqrt(252)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 10 or np.std(x, ddof=1) == 0:
        return np.nan
    return float(np.mean(x) / np.std(x, ddof=1) * np.sqrt(obs_per_year))
