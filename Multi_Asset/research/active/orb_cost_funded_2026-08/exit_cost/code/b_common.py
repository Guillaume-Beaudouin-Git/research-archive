"""b_common.py — chargement partage du ledger ORB v2 et des barres NQ M1/M5.

Reproduit EXACTEMENT le pipeline du generateur du ledger
(`PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_orb_backtest.py`) :

    df = read_parquet(NQ_M1)
    df = df[df.is_rth & ~df.is_roll_day]
    df_5m = df.groupby(df.index.date).apply(resample('5min') OHLCV).dropna()

L'index M1 est en UTC ; `is_rth` marque la session cash US 09:30-16:00 ET.
On ne fait AUCUNE hypothese sur l'horloge : on utilise le meme flag que le
generateur, et l'alignement est verifie au tick par `b1_align.py` (L52/L56).

Perf : les boucles par trade travaillent sur des SLICES NUMPY (`DayBars`), pas sur
des DataFrames par jour — 4013 groupes pandas coutent plusieurs minutes, les
slices numpy quelques secondes. `index.date` (5.1M objets python) est proscrit au
profit de `index.normalize()`.

LECTURE SEULE sur les deux sources.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
LEDGER = MAIN / "PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet"
NQ_M1 = MAIN / "data/raw/NQ_1min_databento_2010-2026.parquet"

OUT = Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(exist_ok=True)

OR_BARS = 6  # 6 barres de 5 min = 30 min d'opening range


@lru_cache(maxsize=1)
def load_ledger() -> pd.DataFrame:
    df = pd.read_parquet(LEDGER)
    df.index = pd.DatetimeIndex(df.index)
    return df


@dataclass
class DayBars:
    """Barres OHLC decoupees par jour, en numpy. `sl(day)` -> (i0, i1) ou None."""
    ts: pd.DatetimeIndex          # horodatages (UTC)
    o: np.ndarray
    h: np.ndarray
    lo: np.ndarray
    c: np.ndarray
    day: np.ndarray               # datetime64[ns] normalise, tz-naive
    bounds: dict                  # pd.Timestamp -> (i0, i1)

    def sl(self, d: pd.Timestamp):
        return self.bounds.get(d)


def _day_bounds(day_vals: np.ndarray) -> dict:
    """Frontieres de jour sur un vecteur trie de dates normalisees."""
    if len(day_vals) == 0:
        return {}
    cuts = np.flatnonzero(day_vals[1:] != day_vals[:-1]) + 1
    starts = np.concatenate([[0], cuts])
    ends = np.concatenate([cuts, [len(day_vals)]])
    return {pd.Timestamp(day_vals[s]): (int(s), int(e)) for s, e in zip(starts, ends)}


def _make_daybars(idx: pd.DatetimeIndex, o, h, lo, c) -> DayBars:
    day = idx.normalize().tz_localize(None).to_numpy()
    return DayBars(ts=idx, o=np.asarray(o, float), h=np.asarray(h, float),
                   lo=np.asarray(lo, float), c=np.asarray(c, float),
                   day=day, bounds=_day_bounds(day))


@lru_cache(maxsize=1)
def _raw() -> pd.DataFrame:
    return pd.read_parquet(NQ_M1, columns=["open", "high", "low", "close",
                                           "is_roll_day", "is_rth"])


@lru_cache(maxsize=1)
def m1_rth() -> DayBars:
    """Barres M1, filtre IDENTIQUE au generateur : `is_rth & ~is_roll_day`."""
    df = _raw()
    m = df["is_rth"].to_numpy() & ~df["is_roll_day"].to_numpy()
    return _make_daybars(df.index[m], df["open"].to_numpy()[m], df["high"].to_numpy()[m],
                         df["low"].to_numpy()[m], df["close"].to_numpy()[m])


@lru_cache(maxsize=1)
def m1_all_session() -> DayBars:
    """Barres M1 de TOUTE la session (hors roll-day), RTH et hors-RTH.

    Sert au falsificateur d'horloge : reconstruire l'OR sur une fenetre decalee
    exige de disposer des barres qui precedent et suivent la RTH.
    """
    df = _raw()
    m = ~df["is_roll_day"].to_numpy()
    return _make_daybars(df.index[m], df["open"].to_numpy()[m], df["high"].to_numpy()[m],
                         df["low"].to_numpy()[m], df["close"].to_numpy()[m])


def to_m5(db: DayBars) -> DayBars:
    """Agrege en barres 5-min, VECTORISE.

    Le generateur fait `groupby(date).apply(resample('5min').agg(...).dropna())`.
    Les bornes 5-min sont alignees sur l'heure : un bucket ne peut pas chevaucher
    deux dates, donc grouper par le label 5-min plancher est EXACTEMENT equivalent
    (`dropna()` du generateur == absence de bucket vide ici).
    """
    lab = db.ts.floor("5min")                     # deja trie => buckets contigus
    key = lab.asi8
    cuts = np.flatnonzero(key[1:] != key[:-1]) + 1
    starts = np.concatenate([[0], cuts])
    ends = np.concatenate([cuts, [len(key)]])
    o = db.o[starts]
    c = db.c[ends - 1]
    h = np.maximum.reduceat(db.h, starts)
    lo = np.minimum.reduceat(db.lo, starts)
    return _make_daybars(lab[starts], o, h, lo, c)


# ---------------------------------------------------------------------------
# Statistiques : HAC, block bootstrap (Politis-Romano), Sharpe L47
# ---------------------------------------------------------------------------

def hac_tstat(x: np.ndarray, lags: int = 6) -> tuple[float, float, float]:
    """t de Newey-West lag-6 de la moyenne. Retourne (mean, se_hac, t)."""
    import statsmodels.api as sm

    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    res = sm.OLS(x, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    mean = float(res.params[0])
    se = float(res.bse[0])
    return mean, se, (float(mean / se) if se > 0 else np.nan)


def stationary_bootstrap_idx(n: int, n_boot: int, mean_block: float,
                             rng: np.random.Generator) -> np.ndarray:
    """Indices du bootstrap stationnaire (Politis-Romano 1994), vectorise.

    Longueur de bloc geometrique de moyenne `mean_block`, index circulaire.
    Construction : a chaque pas on redemarre un bloc avec proba p = 1/mean_block,
    sinon on avance d'un cran dans le bloc courant. iid INTERDIT (constitution).
    """
    p = 1.0 / mean_block
    starts = rng.integers(0, n, size=(n_boot, n))
    newblock = rng.random((n_boot, n)) < p
    newblock[:, 0] = True
    idx = np.empty((n_boot, n), dtype=np.int64)
    cur = starts[:, 0].copy()
    idx[:, 0] = cur
    for t in range(1, n):
        cur = np.where(newblock[:, t], starts[:, t], (cur + 1) % n)
        idx[:, t] = cur
    return idx


def boot_ci(x: np.ndarray, n_boot: int = 5000, mean_block: float = 10.0,
            alpha: float = 0.05, seed: int = 20260812):
    """IC de la moyenne par block bootstrap stationnaire. Retourne (lo, hi, dist)."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    rng = np.random.default_rng(seed)
    idx = stationary_bootstrap_idx(n, n_boot, mean_block, rng)
    dist = x[idx].mean(axis=1)
    lo, hi = np.percentile(dist, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi), dist


def obs_per_year(dates: pd.DatetimeIndex) -> float:
    """L47 : annualiser en sqrt(observations par an), jamais sqrt(252) code en dur."""
    span_years = (dates.max() - dates.min()).days / 365.25
    return len(dates) / span_years


def sharpe_l47(x: np.ndarray, dates: pd.DatetimeIndex) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    ppy = obs_per_year(dates)
    sd = x.std(ddof=1)
    if sd <= 0:
        return float("nan"), ppy
    return float(x.mean() / sd * np.sqrt(ppy)), ppy
