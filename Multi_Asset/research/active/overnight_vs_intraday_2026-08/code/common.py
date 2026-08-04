"""Chargement M1 true-UTC + utilitaires communs (overnight vs intraday, sleeve v2.2).

LECTURE SEULE sur data/. Caches ecrits dans CACHE_DIR (hors repo).
Interpreteur: /usr/bin/python3 explicite.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
import statsmodels.api as sm

MAIN = "<HOME>/Desktop/Algo_claude"
RAW = os.path.join(MAIN, "data", "deep_history_utc")
CACHE_DIR = "<SCRATCH>"
os.makedirs(CACHE_DIR, exist_ok=True)

TZ = "Europe/Paris"          # = Europe/Prague = CET/CEST, l'horloge du schedule EA
ERA_CUT = pd.Timestamp("2021-01-01")

# cost_denominator_2026-07 §5 : meilleure estimation indices ~0.9 bps RT centre,
# fourchette [1.8 ; 2.9]. Le brief impose 1.8 bps RT mesure -> valeur de reference.
RT_BPS = {"US100": 1.8, "GER40": 1.8}
RT_BPS_SIM = {"US100": 2.2, "GER40": 2.2}       # ce que le sim v22 facture
SWAP_LONG_BPS = {"US100": -2.126, "GER40": -1.564}   # spec_v22.yaml, mesure 2026-06-10

# schedule_cet du spec v2.2 (cleanroom/engine.py:393-405)
SEG = {
    "US100": {"entry": (22, 5), "exit": (15, 30)},
    "GER40": {"entry": (17, 35), "exit": (9, 0)},
}


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


def stamps(dates: pd.DatetimeIndex, hh: int, mm: int) -> pd.DatetimeIndex:
    """Horodatages tz-aware Paris (DST natif) a hh:mm sur les dates fournies."""
    return pd.DatetimeIndex(
        [pd.Timestamp(d.year, d.month, d.day, hh, mm, tz=TZ) for d in dates]
    )


def px_at(close: pd.Series, targets: pd.DatetimeIndex, tol="20min") -> pd.Series:
    """Close de la derniere barre <= target, dans une tolerance. NaN sinon."""
    s = close.reindex(targets, method="ffill", tolerance=pd.Timedelta(tol))
    s.index = targets
    return s


def hac_t(x: np.ndarray, lags: int = 6):
    """Moyenne, t_HAC(Newey-West lag-6), N."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return float(np.mean(x)) if n else np.nan, np.nan, n
    r = sm.OLS(x, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(r.params[0]), float(r.tvalues[0]), n


def block_bootstrap_mean(x: np.ndarray, block: int = 10, n_boot: int = 5000, seed: int = 7):
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


def sharpe_ann(x: np.ndarray, obs_per_year: float) -> float:
    """Sharpe annualise en sqrt(obs/an) (L47), pas sqrt(252)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 10 or np.std(x, ddof=1) == 0:
        return np.nan
    return float(np.mean(x) / np.std(x, ddof=1) * np.sqrt(obs_per_year))
