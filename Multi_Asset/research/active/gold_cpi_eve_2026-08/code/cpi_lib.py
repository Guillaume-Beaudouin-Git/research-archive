"""Shared plumbing for the extended-sample CPI-eve test.

Everything here is COPIED VERBATIM from
`Multi_Asset/research/active/exogenous_predictors_2026-08/code/exog_lib.py`
(cost table, swap table, hac_t, block_bootstrap_p, walk_forward) so that the
frozen spec is bit-for-bit the one that produced the N=65 candidate. The ONLY
new code is the BLS calendar loader.

Read-only on every path under the main working dir. Interpreter /usr/bin/python3.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import statsmodels.api as sm

MAIN = "<HOME>/Desktop/Algo_claude"
CACHE = os.environ.get(
    "CPI_CACHE",
    "<SCRATCH>"
    "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad",
)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, ".."))

# ---- FROZEN from exog_lib (do not touch) -------------------------------------
COST_RT_BPS = {"XAUUSD": 1.84, "USDJPY": 1.50}
COST_RT_TAIL_BPS = {"XAUUSD": 3.88, "USDJPY": 3.00}
SWAP_BPS = {
    "XAUUSD": {"long": -1.518, "short": -0.336},
    "USDJPY": {"long": +0.060, "short": -1.267},
}
POST2021 = pd.Timestamp("2021-01-01")
N_TRIALS = 80          # pre-registered: 76 calendar cells swept 2026-08-06 + 4 here


def load_daily_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    px = pd.read_parquet(f"{MAIN}/data/ftmo_portfolio/cache/panel_px.parquet")
    rets = pd.read_parquet(f"{MAIN}/data/ftmo_portfolio/cache/panel_rets.parquet")
    return px, rets


def hac_t(y: np.ndarray, lags: int = 6) -> tuple[float, float]:
    """(mean, HAC t-stat) against zero. Newey-West lag-6. VERBATIM from exog_lib."""
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    if len(y) < 20:
        return (float(np.mean(y)) if len(y) else np.nan, np.nan)
    X = np.ones((len(y), 1))
    res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(res.params[0]), float(res.tvalues[0])


def block_bootstrap_p(y: np.ndarray, block: int = 10, n_boot: int = 5000,
                      seed: int = 7) -> float:
    """VERBATIM from exog_lib."""
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    n = len(y)
    if n < 30:
        return np.nan
    rng = np.random.default_rng(seed)
    obs = float(np.mean(y))
    yc = y - obs
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(n_boot, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
    samp = yc[idx.reshape(n_boot, -1)[:, :n]]
    means = samp.mean(axis=1)
    return float((np.abs(means) >= abs(obs)).mean())


def walk_forward(dates: pd.DatetimeIndex, y: np.ndarray, n_folds: int = 5) -> dict:
    """VERBATIM from exog_lib. Contiguous chronological OOS blocks, no parameter fit."""
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(y)
    y, dates = y[ok], dates[ok]
    n = len(y)
    if n < n_folds * 20:
        return {"folds_pos": np.nan, "n_folds": 0, "fold_means": []}
    edges = np.linspace(0, n, n_folds + 1).astype(int)
    means = [float(np.mean(y[edges[i]:edges[i + 1]])) for i in range(n_folds)]
    return {
        "folds_pos": int(sum(m > 0 for m in means)),
        "n_folds": n_folds,
        "fold_means": [round(m, 3) for m in means],
    }


def expanding_walk_forward(dates: pd.DatetimeIndex, y: np.ndarray,
                           n_folds: int = 5, warmup: float = 0.3) -> dict:
    """Expanding-window variant: train on [0, k), score the next block.

    There is no parameter to fit (the sign is pre-registered), so the expanding
    window only controls WHEN the fold is scored. Reported alongside the frozen
    contiguous version so neither reading is cherry-picked.
    """
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(y)
    y, dates = y[ok], dates[ok]
    n = len(y)
    start = int(n * warmup)
    edges = np.linspace(start, n, n_folds + 1).astype(int)
    means, tr = [], []
    for i in range(n_folds):
        oos = y[edges[i]:edges[i + 1]]
        means.append(float(np.mean(oos)))
        tr.append(float(np.mean(y[:edges[i]])))
    return {"folds_pos": int(sum(m > 0 for m in means)),
            "n_folds": n_folds,
            "fold_means": [round(m, 3) for m in means],
            "train_means": [round(m, 3) for m in tr],
            "fold_starts": [str(dates[e].date()) for e in edges[:-1]],
            "fold_n": [int(edges[i + 1] - edges[i]) for i in range(n_folds)]}


# ---- BLS calendars (the only NEW code) ---------------------------------------
def bls_dates(kind: str = "cpi") -> pd.DatetimeIndex:
    """Real BLS release dates, parsed from the archived news-release filenames.

    kind in {"cpi", "ppi", "empsit"}. Cached in the session scratchpad; the
    fetch itself lives in `fetch_bls_dates.py` so this module never touches the
    network.
    """
    f = f"{CACHE}/bls_{kind}_dates.csv"
    return pd.DatetimeIndex(pd.read_csv(f, parse_dates=["date"])["date"])


def fomc_dates() -> pd.DatetimeIndex:
    f = f"{MAIN}/data/personal_book/post_fomc_drift/data_cache/fomc_events.csv"
    d = pd.read_csv(f)
    col = [c for c in d.columns if "date" in c.lower()][0]
    return pd.DatetimeIndex(sorted(pd.to_datetime(d[col]).unique()))


# ---- the frozen trade --------------------------------------------------------
def frozen_returns(inst: str = "XAUUSD") -> pd.Series:
    """r_t = 1e4 * (log P_{t+1} - log P_t). Booked on the ENTRY date. Frozen."""
    px, _ = load_daily_panel()
    p = px[inst].dropna()
    return (np.log(p).diff() * 1e4).shift(-1).dropna()


def eve_of(events: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Entry dates = event date minus ONE CALENDAR DAY. Frozen (cpi_candidate.py:45)."""
    return pd.DatetimeIndex([d - pd.Timedelta(days=1) for d in events])
