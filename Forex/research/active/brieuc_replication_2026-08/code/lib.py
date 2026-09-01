"""
lib.py — moteur commun pour la réplication Algorithm_Brieuc.

Charge M1 vraie UTC (data/deep_history_utc, read-only, chemin absolu), resample,
simule remplissage d'ordres stop/limite et sorties SL/TP (fixe ou trailing) sur le
PATH M1 réel (jamais au prix théorique exact — L59), calcule R-multiples, coûts par
levier réel, Sharpe annualisé en sqrt(trades/an) (L47), walk-forward, découpe de
régime, bootstrap par blocs, placebo apparié, DSR (réutilise dsr.py du dépôt).
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

REPO_ROOT = Path("<HOME>/Desktop/Algo_claude")
DATA_DIR = REPO_ROOT / "data" / "deep_history_utc"
sys.path.insert(0, str(REPO_ROOT))
from dsr import deflated_sharpe_ratio, estimate_std_sr_trials, sampling_noise_floor_sr  # noqa: E402

LONDON_TZ = ZoneInfo("Europe/London")

# ---------------------------------------------------------------------------
# Point-size table (PREREGISTRATION.md §point-size) — "pip" = 10 x _Point
# ---------------------------------------------------------------------------
# pip_correct: unité utilisée par la version CORRIGÉE pour convertir un paramètre
#              numérique du cours (ex 20, 40, 200) en distance de PRIX.
# pip_naive:   unité utilisée par la version NAÏVE (identique sauf indices, où le
#              bug _Point*10 FX-like est reproduit).
POINT_TABLE = {
    "EURUSD": dict(pip_corrected=0.0001, pip_naive=0.0001, digits=5),
    "GBPUSD": dict(pip_corrected=0.0001, pip_naive=0.0001, digits=5),
    "AUDUSD": dict(pip_corrected=0.0001, pip_naive=0.0001, digits=5),
    "USDCHF": dict(pip_corrected=0.0001, pip_naive=0.0001, digits=5),
    "USDCAD": dict(pip_corrected=0.0001, pip_naive=0.0001, digits=5),
    "NZDUSD": dict(pip_corrected=0.0001, pip_naive=0.0001, digits=5),
    "USDJPY": dict(pip_corrected=0.01, pip_naive=0.01, digits=3),
    "XAUUSD": dict(pip_corrected=0.1, pip_naive=0.1, digits=2),
    # Indices : corrigé = 1 point indice natif par unité de paramètre (pas de x10) ;
    # naïf = formule EA appliquée avec l'hypothèse implicite FX-like _Point=0.01.
    "US30": dict(pip_corrected=1.0, pip_naive=0.1, digits=2),
    "US100": dict(pip_corrected=1.0, pip_naive=0.1, digits=2),
    "GER40": dict(pip_corrected=1.0, pip_naive=0.1, digits=2),
}

# Univers ÉTENDU (amendement 2026-08-28, cf. PREREGISTRATION.md §Amendement) : 7 FX majors +
# 3 indices + XAUUSD = 11 instruments. Fenêtres choisies après contrôle L60 (fraction de barres
# à fourchette nulle par année) -- voir code/check_l60_extra.py output loggé dans le rapport.
INSTRUMENTS = {
    "EURUSD": "2008-01-01",
    "GBPUSD": "2008-01-01",
    "AUDUSD": "2008-01-01",
    "USDCHF": "2008-01-01",
    "USDCAD": "2011-01-01",  # L60: >10% barres fourchette nulle avant 2011
    "NZDUSD": "2011-01-01",  # idem
    "USDJPY": "2008-01-01",
    "XAUUSD": "2008-01-01",
    "US30": "2015-01-01",
    "US100": "2015-01-01",
    "GER40": "2015-01-01",
}
ANALYSIS_END = "2026-06-01"

# FVG restreint à ces 4 (scope pré-enregistré + décision de ne pas étendre le calcul à une
# famille déjà morte par fréquence de coût, cf. steer coordinateur 2026-08-28).
FVG_INSTRUMENTS = {"EURUSD", "GBPUSD", "USDJPY", "XAUUSD"}

COST_TIERS = {"gross": 0.0, "eightcap_raw": 0.75, "ftmo_retail": 2.48}  # bps RT


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
CACHE_DIR = Path("<SCRATCH>"
                  "9fd32b98-b3ee-47bf-93c1-b7c5a1ac70a6/scratchpad/m1_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_m1_full(instrument: str) -> pd.DataFrame:
    """Read-only load of the canonical M1 CSV, cached as parquet in the scratchpad
    (never written back into data/deep_history_utc — that estate stays untouched)."""
    cache_path = CACHE_DIR / f"{instrument}_M1.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    path = DATA_DIR / f"{instrument}_M1.csv"
    df = pd.read_csv(path, usecols=["timestamp_utc", "open", "high", "low", "close"])
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    df = df.set_index("timestamp_utc").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df.to_parquet(cache_path)
    return df


def load_m1(instrument: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    df = _load_m1_full(instrument)
    if start is not None:
        df = df[df.index >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        df = df[df.index < pd.Timestamp(end, tz="UTC")]
    return df


def resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    o = df["open"].resample(rule, label="left", closed="left").first()
    h = df["high"].resample(rule, label="left", closed="left").max()
    l = df["low"].resample(rule, label="left", closed="left").min()
    c = df["close"].resample(rule, label="left", closed="left").last()
    out = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}).dropna()
    return out


# ---------------------------------------------------------------------------
# Order fill / exit scanning on the real M1 path (L59: never the exact stop price)
# ---------------------------------------------------------------------------
@dataclass
class Trade:
    instrument: str
    strategy: str
    version: str  # 'naive' | 'corrected'
    variant: str  # '' | 'sens_inverse'
    side: str  # 'long' | 'short'
    signal_time: pd.Timestamp
    entry_trigger: float
    entry_time: pd.Timestamp | None
    entry_fill: float | None
    sl0: float
    tp0: float | None
    exit_time: pd.Timestamp | None
    exit_price: float | None
    exit_reason: str  # 'sl' | 'tp' | 'censored' | 'unfilled' | 'trail_sl'
    ambiguous_bar: bool = False
    gap_through_entry: bool = False
    gap_through_exit: bool = False


def _slice_idx(index: pd.DatetimeIndex, t0: pd.Timestamp, horizon: pd.Timedelta):
    start = index.searchsorted(t0, side="left")
    end = index.searchsorted(t0 + horizon, side="left")
    return start, end


def scan_pending_fill(m1: pd.DataFrame, t0: pd.Timestamp, expiry: pd.Timestamp,
                       trigger: float, order_type: str):
    """order_type in {'buy_stop','sell_stop','buy_limit','sell_limit'}.
    Returns (fill_time, fill_price, gap_through) or (None, None, False) if unfilled.
    """
    idx = m1.index
    start, end = _slice_idx(idx, t0, expiry - t0)
    if start >= end:
        return None, None, False
    o = m1["open"].values[start:end]
    h = m1["high"].values[start:end]
    l = m1["low"].values[start:end]
    if order_type == "buy_stop":
        hit = h >= trigger
    elif order_type == "sell_stop":
        hit = l <= trigger
    elif order_type == "buy_limit":
        hit = l <= trigger
    elif order_type == "sell_limit":
        hit = h >= trigger
    else:
        raise ValueError(order_type)
    if not hit.any():
        return None, None, False
    k = int(np.argmax(hit))
    gap = False
    if order_type in ("buy_stop",):
        fill = trigger if o[k] < trigger else o[k]
        gap = o[k] >= trigger
    elif order_type == "sell_stop":
        fill = trigger if o[k] > trigger else o[k]
        gap = o[k] <= trigger
    elif order_type == "buy_limit":
        fill = trigger if o[k] > trigger else o[k]
        gap = o[k] <= trigger
    elif order_type == "sell_limit":
        fill = trigger if o[k] < trigger else o[k]
        gap = o[k] >= trigger
    return idx[start + k], float(fill), gap


def scan_fixed_exit(m1: pd.DataFrame, t0: pd.Timestamp, side: str, sl: float,
                     tp: float | None, horizon: pd.Timedelta):
    """Fixed SL/TP exit scan on the real M1 path. Returns
    (exit_time, exit_price, reason, ambiguous_bar, gap_through)."""
    idx = m1.index
    start, end = _slice_idx(idx, t0, horizon)
    if start >= end:
        return None, None, "censored", False, False
    o = m1["open"].values[start:end]
    h = m1["high"].values[start:end]
    l = m1["low"].values[start:end]
    if side == "long":
        hit_sl = l <= sl
        hit_tp = (h >= tp) if tp is not None else np.zeros_like(hit_sl)
    else:
        hit_sl = h >= sl
        hit_tp = (l <= tp) if tp is not None else np.zeros_like(hit_sl)
    hit_any = hit_sl | hit_tp
    if not hit_any.any():
        last = end - 1
        return idx[last], float(m1["close"].values[last]), "censored", False, False
    k = int(np.argmax(hit_any))
    amb = bool(hit_sl[k] and hit_tp[k])
    reason = "sl" if (amb or hit_sl[k]) else "tp"  # worst case on ambiguity (L59)
    level = sl if reason == "sl" else tp
    if side == "long":
        if reason == "sl":
            gap = o[k] <= sl
            price = sl if not gap else o[k]
        else:
            gap = o[k] >= tp
            price = tp if not gap else o[k]
    else:
        if reason == "sl":
            gap = o[k] >= sl
            price = sl if not gap else o[k]
        else:
            gap = o[k] <= tp
            price = tp if not gap else o[k]
    return idx[start + k], float(price), reason, amb, bool(gap)


def scan_trailing_exit(m1: pd.DataFrame, t0: pd.Timestamp, side: str, sl0: float,
                        entry_price: float, horizon: pd.Timedelta):
    """Trailing stop, breakeven+1:1 (DailyBreakout), no TP. Trail updates same-bar
    using that bar's own high/low (conservative convention, documented in SPECS.md).
    Returns (exit_time, exit_price, reason, gap_through)."""
    idx = m1.index
    start, end = _slice_idx(idx, t0, horizon)
    if start >= end:
        return None, None, "censored", False
    o = m1["open"].values[start:end]
    h = m1["high"].values[start:end]
    l = m1["low"].values[start:end]
    if side == "long":
        profit_path = np.maximum.accumulate(np.maximum(h - entry_price, 0.0))
        trail = sl0 + profit_path
        breach = l <= trail
    else:
        profit_path = np.maximum.accumulate(np.maximum(entry_price - l, 0.0))
        trail = sl0 - profit_path
        breach = h >= trail
    if not breach.any():
        last = end - 1
        return idx[last], float(m1["close"].values[last]), "censored", False
    k = int(np.argmax(breach))
    lvl = trail[k]
    if side == "long":
        gap = o[k] <= lvl
        price = lvl if not gap else o[k]
    else:
        gap = o[k] >= lvl
        price = lvl if not gap else o[k]
    return idx[start + k], float(price), "trail_sl", bool(gap)


# ---------------------------------------------------------------------------
# R-multiples, cost, Sharpe (L47), stats
# ---------------------------------------------------------------------------
def trade_r_multiple(entry: float, exit_price: float, sl0: float, side: str) -> float:
    stop_dist = abs(entry - sl0)
    if stop_dist <= 0:
        return 0.0
    raw = (exit_price - entry) if side == "long" else (entry - exit_price)
    return raw / stop_dist


def cost_in_r(entry: float, sl0: float, cost_bps: float) -> float:
    stop_dist = abs(entry - sl0)
    if stop_dist <= 0:
        return 0.0
    leverage = entry / stop_dist
    return (cost_bps / 1e4) * leverage


def annualized_sharpe(r_series: np.ndarray, trades_per_year: float) -> float:
    r_series = np.asarray(r_series, dtype=float)
    if len(r_series) < 2 or r_series.std(ddof=1) < 1e-12:
        return 0.0
    return float(r_series.mean() / r_series.std(ddof=1) * math.sqrt(trades_per_year))


def hac_tstat(r_series: np.ndarray, lag: int = 6) -> float:
    """Newey-West HAC t-stat of the mean of r_series (OLS on a constant)."""
    import statsmodels.api as sm
    r_series = np.asarray(r_series, dtype=float)
    n = len(r_series)
    if n < 8:
        return float("nan")
    X = np.ones((n, 1))
    model = sm.OLS(r_series, X).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return float(model.tvalues[0])


def trades_per_year(entry_times: pd.Series, n_years: float) -> float:
    n = len(entry_times)
    return n / n_years if n_years > 0 else 0.0


def walk_forward_folds(trades_df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp,
                        n_folds: int = 5) -> list[pd.DataFrame]:
    edges = pd.date_range(start, end, periods=n_folds + 1)
    folds = []
    for i in range(n_folds):
        lo, hi = edges[i], edges[i + 1]
        folds.append(trades_df[(trades_df["entry_time"] >= lo) & (trades_df["entry_time"] < hi)])
    return folds


def regime_4y_splits(trades_df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp):
    out = {}
    cur = pd.Timestamp(year=start.year, month=1, day=1, tz="UTC")
    while cur < end:
        nxt = cur + pd.DateOffset(years=4)
        seg = trades_df[(trades_df["entry_time"] >= cur) & (trades_df["entry_time"] < nxt)]
        if len(seg) > 0:
            out[f"{cur.year}-{min(nxt.year, end.year)}"] = seg
        cur = nxt
    return out


def block_bootstrap(r_series: np.ndarray, block: int = 20, n_boot: int = 2000,
                     seed: int = 0):
    rng = np.random.default_rng(seed)
    r = np.asarray(r_series, dtype=float)
    n = len(r)
    if n < block * 2:
        block = max(2, n // 3)
    n_blocks = int(np.ceil(n / block))
    means = np.empty(n_boot)
    sharpes = np.empty(n_boot)
    max_start = n - block
    for b in range(n_boot):
        if max_start <= 0:
            sample = rng.choice(r, size=n, replace=True)
        else:
            starts = rng.integers(0, max_start + 1, size=n_blocks)
            chunks = [r[s:s + block] for s in starts]
            sample = np.concatenate(chunks)[:n]
        means[b] = sample.mean()
        sd = sample.std(ddof=1)
        sharpes[b] = sample.mean() / sd if sd > 1e-12 else 0.0
    return means, sharpes


def paired_placebo(r_gross_abs: np.ndarray, cost_r: np.ndarray, n_draws: int = 1000,
                    seed: int = 0):
    """Same construction (same |gross R| and same cost per trade), random long/short
    sign 50/50. Returns array of placebo net-R means (n_draws,) and Sharpes."""
    rng = np.random.default_rng(seed)
    n = len(r_gross_abs)
    means = np.empty(n_draws)
    sharpes = np.empty(n_draws)
    for i in range(n_draws):
        signs = rng.choice([-1.0, 1.0], size=n)
        net = signs * r_gross_abs - cost_r
        means[i] = net.mean()
        sd = net.std(ddof=1)
        sharpes[i] = net.mean() / sd if sd > 1e-12 else 0.0
    return means, sharpes


def dsr_report(r_series: np.ndarray, family_sharpes: list[float], trades_per_yr: float,
                n_trials_override: int | None = None):
    r_series = np.asarray(r_series, dtype=float)
    n = len(r_series)
    if n < 10 or trades_per_yr <= 0:
        return dict(dsr=float("nan"), sharpe=float("nan"), std_sr_trials=float("nan"),
                    n_trials=n_trials_override or max(len(family_sharpes), 1), n_obs=n)
    n_trials = n_trials_override or max(len(family_sharpes), 1)
    if len(family_sharpes) >= 2:
        sd = estimate_std_sr_trials(family_sharpes, periods_per_year=trades_per_yr, n_obs=n, apply_floor=True)
    else:
        sd = sampling_noise_floor_sr(n, periods_per_year=trades_per_yr)
    out = deflated_sharpe_ratio(r_series, n_trials=n_trials, periods_per_year=trades_per_yr,
                                 std_sr_trials=sd, rf=0.0)
    return out
