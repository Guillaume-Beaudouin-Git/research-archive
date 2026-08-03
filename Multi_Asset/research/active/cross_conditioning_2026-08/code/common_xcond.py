"""Shared loading / statistics layer for the cross-conditioning study.

Reads READ-ONLY from the main working dir (caches are gitignored and therefore
absent from a worktree).  Writes ONLY into a cache directory that is private to
this study and stamped with an owner tag: a sibling agent runs in parallel and
two agents have already overwritten each other in this repo.  Every cache read
asserts the owner stamp AND the column schema before returning.

RAW M1 only.  `overnight_futures_2026-07/code/step3_performance.py` winsorises at
0.5/99.5 inside its constructor; nothing from it is imported here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

RAW = Path("<HOME>/Desktop/Algo_claude/data/deep_history_utc")
OWNER = "cross_conditioning_2026-08"
NS_MIN = np.int64(60_000_000_000)
M1_COLS = ["open", "high", "low", "close", "tick_volume"]

RNG = np.random.default_rng(20260803)
NBOOT, BLOCK = 2000, 10


# ----------------------------------------------------------------- cache guard
def cache_dir() -> Path:
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if d is None:
        raise SystemExit("usage: <script> <private_cache_dir>")
    d.mkdir(parents=True, exist_ok=True)
    stamp = d / "_OWNER.json"
    if stamp.exists():
        got = json.loads(stamp.read_text())
        if got.get("owner") != OWNER:
            raise SystemExit(
                f"REFUSING to share a cache dir: {d} belongs to {got.get('owner')!r}, "
                f"not {OWNER!r}.  Pick a private path."
            )
    else:
        stamp.write_text(json.dumps({"owner": OWNER, "cols": M1_COLS}))
    return d


def read_m1_cache(cache: Path, name: str) -> pd.DataFrame:
    df = pd.read_parquet(cache / f"{name}_M1.parquet")
    missing = [c for c in M1_COLS if c not in df.columns]
    if missing:
        raise AssertionError(f"{name}: cache schema broken, missing {missing}")
    if not isinstance(df.index, pd.DatetimeIndex) or df.index.tz is None:
        raise AssertionError(f"{name}: cache index is not tz-aware UTC")
    return df


def load_m1_raw(name: str) -> pd.DataFrame:
    df = pd.read_csv(
        RAW / f"{name}_M1.csv",
        usecols=["timestamp_utc"] + M1_COLS,
        dtype={c: "float64" for c in M1_COLS[:4]} | {"tick_volume": "float64"},
    )
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    df = df.drop(columns=["timestamp_utc"])
    df.index = ts
    df.index.name = "ts"
    return df.sort_index()


# ---------------------------------------------------------------- statistics
def hac(x, lags: int = 6) -> tuple[float, float, int]:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 30:
        return (np.nan, np.nan, len(x))
    m = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return (float(m.params[0]), float(m.tvalues[0]), len(x))


def hac_slope(y, x, lags: int = 6) -> dict:
    """OLS y ~ a + b*x with HAC(6); returns slope, t, R^2, n."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    ok = np.isfinite(y) & np.isfinite(x)
    y, x = y[ok], x[ok]
    if len(y) < 50:
        return dict(slope=np.nan, t=np.nan, r2=np.nan, n=len(y))
    m = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return dict(slope=float(m.params[1]), t=float(m.tvalues[1]),
                r2=float(m.rsquared), n=len(y))


def _boot_idx(n: int, nboot: int = NBOOT, L: int = BLOCK) -> np.ndarray:
    """Circular block bootstrap index matrix (Politis-Romano).  Never iid."""
    nb = int(np.ceil(n / L))
    starts = RNG.integers(0, n, size=(nboot, nb))
    return (starts[:, :, None] + np.arange(L)[None, None, :]).reshape(nboot, -1)[:, :n] % n


def block_boot_mean(x) -> tuple[float, float, float]:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 30:
        return (np.nan, np.nan, np.nan)
    m = x[_boot_idx(len(x))].mean(axis=1)
    lo, hi = np.percentile(m, [2.5, 97.5])
    return (float(lo), float(hi), float(min(2 * min((m <= 0).mean(), (m >= 0).mean()), 1.0)))


def block_boot_slope_p(y, x) -> float:
    """Two-sided block-bootstrap p for the OLS slope of y on x (pairs resampled
    in blocks, so serial dependence in BOTH series is preserved)."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    ok = np.isfinite(y) & np.isfinite(x)
    y, x = y[ok], x[ok]
    n = len(y)
    if n < 50:
        return np.nan
    idx = _boot_idx(n)
    Y, X = y[idx], x[idx]
    xm = X.mean(axis=1, keepdims=True)
    ym = Y.mean(axis=1, keepdims=True)
    num = ((X - xm) * (Y - ym)).sum(axis=1)
    den = ((X - xm) ** 2).sum(axis=1)
    b = np.where(den > 0, num / np.where(den > 0, den, 1.0), np.nan)
    b = b[np.isfinite(b)]
    if len(b) < 100:
        return np.nan
    return float(min(2 * min((b <= 0).mean(), (b >= 0).mean()), 1.0))


def causal_rank(s: pd.Series, win: int = 250, minp: int = 100) -> np.ndarray:
    """Percentile of the current value inside the TRAILING window, current value
    excluded.  Strictly causal: nothing from day t enters day t's own rank."""
    v = np.asarray(s, float)
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        past = v[max(0, i - win):i]
        past = past[np.isfinite(past)]
        if len(past) >= minp and np.isfinite(v[i]):
            out[i] = float((past < v[i]).mean())
    return out


def quintile_table(state, r, q: int = 5) -> pd.DataFrame:
    ok = np.isfinite(state) & np.isfinite(r)
    s, y = np.asarray(state, float)[ok], np.asarray(r, float)[ok]
    b = pd.qcut(pd.Series(s), q, labels=False, duplicates="drop")
    g = pd.DataFrame({"b": b, "r": y}).groupby("b")["r"]
    out = pd.DataFrame({"n": g.size(), "mean": g.mean()})
    out["t_hac"] = [hac(y[b.to_numpy() == k])[1] for k in out.index]
    return out


def monotone_transitions(vals, increasing: bool) -> int:
    v = np.asarray(vals, float)
    d = np.diff(v)
    return int((d > 0).sum() if increasing else (d < 0).sum())


def walk_forward(dates, r, nfolds: int = 5) -> tuple[int, int, list]:
    """Expanding-window folds over TIME (never a single split).  Returns
    (#positive folds, #folds, per-fold means).  Folds are the 5 equal calendar
    slices of the decisional sample; the count is of OUT-OF-SAMPLE slices."""
    d = pd.Series(np.asarray(r, float), index=pd.DatetimeIndex(dates)).dropna()
    if len(d) < 5 * 20:
        return (0, 0, [])
    edges = np.linspace(0, len(d), nfolds + 1).astype(int)
    means = [float(d.iloc[edges[k]:edges[k + 1]].mean()) for k in range(nfolds)]
    return (int(np.sum(np.array(means) > 0)), nfolds, means)


def price_at(vals, keys, t, mode: str, tol_min: int):
    """Nearest print at/before ('last') or at/after ('first') t, within tolerance."""
    tol = np.int64(tol_min) * NS_MIN
    if mode == "last":
        i = np.searchsorted(keys, t, side="right") - 1
        ok = (i >= 0) & (t - keys[np.clip(i, 0, len(keys) - 1)] <= tol)
    else:
        i = np.searchsorted(keys, t, side="left")
        ok = (i < len(keys)) & (keys[np.clip(i, 0, len(keys) - 1)] - t <= tol)
    out = vals[np.clip(i, 0, len(keys) - 1)].astype(float)
    out[~ok] = np.nan
    return out
