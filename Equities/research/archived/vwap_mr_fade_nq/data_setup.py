"""
Data loading and validation for VWAP MR Fade NQ.
Source: data/raw/NQ_1min_2022-12-26_2025-12-11.parquet

Run standalone: python -m Equities.research.active.vwap_mr_fade_nq.data_setup
Prints STOP-POINT 1 diagnostics.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# ── repo paths ────────────────────────────────────────────────────────────────
_REPO = Path(__file__).parents[4]
PARQUET_PATH = _REPO / "data" / "raw" / "NQ_1min_2022-12-26_2025-12-11.parquet"

# ── backtest period (prespec-frozen) ──────────────────────────────────────────
BACKTEST_START = "2023-01-01"
BACKTEST_END   = "2025-12-11"

RTH_START = "09:30"
RTH_END   = "16:00"

# ── signal parameters (prespec-frozen — do not modify post-failure) ───────────
SIGMA_WINDOW  = 30    # bars
Z_ENTRY       = 2.0
Z_TP_EXIT     = 0.5
Z_SL_OFFSET   = 1.0   # SL fires when |Z| > Z_entry + Z_SL_OFFSET (adverse side)
TIME_STOP_MIN = 30

# ── entry windows (2 pre-registered variants → 2 n_tests) ────────────────────
VARIANT_A = ("10:30", "15:00")
VARIANT_B = ("10:00", "15:30")


# ── walk-forward schedule (prespec-frozen) ─────────────────────────────────────
class WFFold(NamedTuple):
    fold:        int
    train_start: str
    train_end:   str
    test_start:  str
    test_end:    str


WALK_FORWARD_FOLDS: list[WFFold] = [
    WFFold(1, "2023-01-01", "2023-12-31", "2024-01-01", "2024-06-30"),
    WFFold(2, "2023-01-01", "2024-06-30", "2024-07-01", "2024-12-31"),
    WFFold(3, "2023-01-01", "2024-12-31", "2025-01-01", "2025-06-30"),
    WFFold(4, "2023-01-01", "2025-06-30", "2025-07-01", "2025-09-30"),
    WFFold(5, "2023-01-01", "2025-09-30", "2025-10-01", "2025-12-11"),
]


# ── data loading ──────────────────────────────────────────────────────────────

def load_nq_rth(
    path:  Path = PARQUET_PATH,
    start: str  = BACKTEST_START,
    end:   str  = BACKTEST_END,
) -> pd.DataFrame:
    """
    Load NQ 1-min RTH bars for the backtest period.

    Filters to 09:31–16:00 ET (drops the 09:30 anchor bar where vwap_rth = 0).
    Returns a tz-aware (US/Eastern) DataFrame.
    """
    df = pd.read_parquet(path)
    if df.index.tz is None:
        raise ValueError("Expected tz-aware index (US/Eastern)")

    rth = df.between_time(RTH_START, RTH_END).copy()
    # 09:30 bar: vwap_rth = 0 (anchor initialisation), not usable for Z-score
    rth = rth[rth.index.time != pd.Timestamp("09:30").time()]
    return rth.loc[start:end]


# ── feature computation ───────────────────────────────────────────────────────

def _session_rolling_std(ser: pd.Series, window: int) -> pd.Series:
    """Rolling std grouped by trading date — prevents cross-session contamination."""
    return ser.groupby(ser.index.date).transform(
        lambda g: g.rolling(window, min_periods=window).std()
    )


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute VWAP deviation Z-score features per prespec.

    Added columns
    -------------
    dev      : close - vwap_rth
    sigma_30 : 30-bar per-session rolling std of dev (NaN for first 29 bars/session)
    Z        : dev / sigma_30  (NaN where sigma_30 is NaN or zero)
    """
    out = df.copy()
    out["dev"]      = out["close"] - out["vwap_rth"]
    out["sigma_30"] = _session_rolling_std(out["dev"], SIGMA_WINDOW)
    out["Z"]        = out["dev"] / out["sigma_30"].replace(0.0, np.nan)
    return out


# ── validation ────────────────────────────────────────────────────────────────

def validate_data(df: pd.DataFrame) -> dict:
    """Data quality metrics."""
    bps = df.groupby(df.index.date).size()
    return {
        "n_sessions":              int(bps.shape[0]),
        "date_start":              str(df.index.min().date()),
        "date_end":                str(df.index.max().date()),
        "total_bars":              len(df),
        "median_bars_per_session": int(bps.median()),
        "min_bars_per_session":    int(bps.min()),
        "sessions_below_380_bars": int((bps < 380).sum()),
        "vwap_zero_count":         int((df["vwap_rth"] == 0).sum()),
        "null_count":              int(df[["close", "vwap_rth"]].isnull().sum().sum()),
    }


# ── STOP-POINT 1 diagnostics ──────────────────────────────────────────────────

def diagnose() -> None:
    """STOP-POINT 1 — print full data diagnostics and prespec sanity checks."""
    print(f"\n{'='*62}")
    print("  STOP-POINT 1 — VWAP MR Fade NQ — Data Diagnostics")
    print(f"{'='*62}")

    # 1. Data quality
    print(f"\n[1] Loading {BACKTEST_START} → {BACKTEST_END} RTH bars ...")
    df = load_nq_rth()
    stats = validate_data(df)
    for k, v in stats.items():
        warn = ""
        if k in ("vwap_zero_count", "null_count") and v > 0:
            warn = "  ✗ WARN"
        if k == "sessions_below_380_bars" and v == 0:
            warn = "  ✓"
        print(f"    {k}: {v}{warn}")

    # 2. VWAP anchor integrity
    print(f"\n[2] VWAP anchoring (09:31 first-bar of each session):")
    first_vwap = df.groupby(df.index.date)["vwap_rth"].first()
    n_zero = int((first_vwap == 0).sum())
    n_ok   = len(first_vwap) - n_zero
    print(f"    09:31 vwap_rth = 0 (unexpected): {n_zero} {'✓' if n_zero == 0 else '✗ WARN'}")
    print(f"    09:31 vwap_rth > 0 (correct):    {n_ok}")

    # 3. Z-score features
    print(f"\n[3] Z-score feature statistics:")
    df_feat = prepare_features(df)
    for tag, (t_start, t_end) in [("VARIANT_A", VARIANT_A), ("VARIANT_B", VARIANT_B)]:
        win  = df_feat.between_time(t_start, t_end)
        n_tot   = len(win)
        n_valid = int(win["Z"].notna().sum())
        n_sig   = int((win["Z"].abs() > Z_ENTRY).sum())
        nan_pct = (n_tot - n_valid) / n_tot * 100
        hit_pct = n_sig / n_valid * 100 if n_valid > 0 else 0.0
        print(f"    {tag} ({t_start}–{t_end}):")
        print(f"      bars: {n_tot:,} | Z valid: {n_valid:,} (NaN: {nan_pct:.1f}%)")
        print(f"      |Z|>{Z_ENTRY} trigger bars: {n_sig:,}  ({hit_pct:.2f}% of valid)")

    # 4. Walk-forward fold bar counts
    print(f"\n[4] Walk-forward folds:")
    for fold in WALK_FORWARD_FOLDS:
        train = df.loc[fold.train_start:fold.train_end]
        test  = df.loc[fold.test_start:fold.test_end]
        print(f"    Fold {fold.fold}:  train [{fold.train_start}→{fold.train_end}] "
              f"{len(train):,} bars  |  test [{fold.test_start}→{fold.test_end}] "
              f"{len(test):,} bars")

    # 5. GEX proxy distribution (H3 sanity)
    print(f"\n[5] GEX proxy (abs_move_first30) distribution:")
    t_931  = pd.Timestamp("09:31").time()
    t_1000 = pd.Timestamp("10:00").time()
    open_931  = df[df.index.time == t_931].groupby(df.index.date)["open"].first()
    close_1000 = df[df.index.time == t_1000].groupby(df.index.date)["close"].last()
    common    = open_931.index.intersection(close_1000.index)
    abs_move  = ((close_1000[common] - open_931[common]) / open_931[common]).abs() * 100
    total     = len(abs_move)
    mr_n      = int((abs_move < 0.30).sum())
    trend_n   = int((abs_move > 0.50).sum())
    print(f"    n_sessions: {total}")
    print(f"    MR-favorable   (abs_move < 0.30%): {mr_n} ({mr_n/total*100:.1f}%)")
    print(f"    Trend-favorable (abs_move > 0.50%): {trend_n} ({trend_n/total*100:.1f}%)")
    print(f"    p25/p50/p75: "
          f"{abs_move.quantile(0.25):.3f}% / "
          f"{abs_move.quantile(0.50):.3f}% / "
          f"{abs_move.quantile(0.75):.3f}%")

    print(f"\n{'='*62}")
    print("  STOP-POINT 1 complete — proceed to feasibility.py")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    diagnose()
