"""
nq_orb_backtest.py — Single-sleeve NQ ORB backtest on 2010-2026 data.

Data: data/raw/NQ_1min_databento_2010-2026.parquet
  - 5.1M 1-min bars from 2010-06-07 to 2026-05-29 (UTC)
  - Columns: open, high, low, close, volume, symbol, is_roll_day, is_rth
  - is_rth flag marks regular trading hours (US cash, 09:30-16:00 ET)

Strategy: ORB on NQ at US cash open (09:30 ET)
  - OR = first 30 min after cash open (= first 6 × 5-min bars of RTH)
  - Skip is_roll_day (= front-month roll, ~1.4% of days)
  - 2 execution models:
      EXEC_0 (legacy): same-bar fill at level (or_hi/or_lo)
      EXEC_NEXT_OPEN: detect via close confirmation, enter at next-bar open

Cost: 3 pts/RT (US100 CFD equivalent — the live FTMO instrument).
  NQ futures cost ($2.15 RT ≈ 0.11 pts) would give MUCH better numbers but we
  use CFD cost to bracket the realistic FTMO execution path.

Output: per-trade DataFrame with date, sleeve, R_realised, exec_model, regime tags.
"""
from __future__ import annotations
from pathlib import Path
from functools import lru_cache
import numpy as np
import pandas as pd


DATA_PATH = Path(__file__).resolve().parents[1].parent / "raw" / "NQ_1min_databento_2010-2026.parquet"
COST_POINTS_CFD = 3.0  # US100 CFD round-trip cost
COST_POINTS_FUTURES = 0.11  # NQ futures ($2.15 / $20 per pt)


@lru_cache(maxsize=2)
def load_nq_5min() -> pd.DataFrame:
    """Load NQ 1-min, filter to RTH only, skip roll days, resample to 5-min."""
    df = pd.read_parquet(DATA_PATH)
    df = df[df["is_rth"] & ~df["is_roll_day"]].copy()
    # Resample to 5-min — RTH starts at 13:30 UTC (DST) or 14:30 UTC (non-DST), both align to 5-min boundaries
    df_5m = df.groupby(df.index.date).apply(
        lambda g: g[["open", "high", "low", "close", "volume"]].resample("5min").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        ).dropna()
    )
    # Drop the outer group index
    df_5m = df_5m.reset_index(level=0, drop=True)
    return df_5m


def detect_break_and_compute_R(
    H: np.ndarray, L: np.ndarray, C: np.ndarray, O: np.ndarray,
    or_bars: int = 6,
    exec_model: str = "EXEC_0",
    cost_pts: float = COST_POINTS_CFD,
    slip_pts: float = 0.0,
) -> dict | None:
    """
    Detect breakout and compute R for one day's session.

    EXEC_0: detect via H[bi]>or_hi or L[bi]<or_lo (intra-bar), enter at level (SAME bar)
    EXEC_NEXT_OPEN: detect via C[bi]>or_hi or C[bi]<or_lo (close), enter at O[bi+1]
    """
    if len(H) < or_bars + 3:
        return None
    or_hi = H[:or_bars].max()
    or_lo = L[:or_bars].min()
    or_range = or_hi - or_lo
    if or_range <= 0:
        return None

    # Detect break
    if exec_model == "EXEC_NEXT_OPEN":
        # Use close-based detection (point-in-time, only known at bar close)
        close_post = C[or_bars:]
        up = np.where(close_post > or_hi)[0]
        dn = np.where(close_post < or_lo)[0]
    else:
        # Legacy intra-bar detection
        up = np.where(H[or_bars:] > or_hi)[0]
        dn = np.where(L[or_bars:] < or_lo)[0]
    iu = up[0] if len(up) else 10**9
    idn = dn[0] if len(dn) else 10**9
    if iu == idn == 10**9:
        return None
    if iu <= idn:
        direction, level, stop_level = 1, or_hi, or_lo
        bi = or_bars + iu
    else:
        direction, level, stop_level = -1, or_lo, or_hi
        bi = or_bars + idn

    # Entry
    if exec_model == "EXEC_0":
        entry_bar = bi
        entry = level + direction * slip_pts
        stop_eff = stop_level - direction * slip_pts
    elif exec_model == "EXEC_NEXT_OPEN":
        if bi + 1 >= len(H):
            return None
        entry_bar = bi + 1
        entry = O[bi + 1] + direction * slip_pts
        stop_eff = stop_level - direction * slip_pts
    else:
        raise ValueError(f"Unknown exec_model {exec_model}")

    # Find exit (stop or close)
    fh, fl = H[entry_bar:], L[entry_bar:]
    if direction == 1:
        hit = np.where(fl <= stop_eff)[0]
    else:
        hit = np.where(fh >= stop_eff)[0]
    if len(hit):
        exit_px = stop_eff
        outcome = "STOP"
    else:
        exit_px = C[-1]
        outcome = "TIME_STOP"
    r = (direction * (exit_px - entry) - cost_pts) / or_range
    return {
        "or_hi": or_hi, "or_lo": or_lo, "or_range": or_range,
        "direction": direction, "level": level, "stop_level": stop_level,
        "bi": bi, "ttb_5min": bi - or_bars,  # = iu for long, idn for short, ALWAYS CORRECT
        "entry": entry, "stop_eff": stop_eff,
        "exit_px": exit_px, "outcome": outcome,
        "r_realised": r,
    }


def extract_trades(
    or_bars: int = 6,
    exec_model: str = "EXEC_0",
    cost_pts: float = COST_POINTS_CFD,
    slip_pts: float = 0.0,
    lo: str | None = None,
    hi: str | None = None,
) -> pd.DataFrame:
    """Extract all trades on NQ 2010-2026 under given execution model."""
    df_5m = load_nq_5min()
    rows = []
    # Group by UTC date (use date of index)
    for day, g in df_5m.groupby(df_5m.index.date):
        H = g["high"].values
        L = g["low"].values
        C = g["close"].values
        O = g["open"].values
        if len(H) < or_bars + 3:
            continue
        res = detect_break_and_compute_R(H, L, C, O, or_bars, exec_model, cost_pts, slip_pts)
        if res is None:
            continue
        res["date"] = pd.Timestamp(day)
        rows.append(res)
    df_out = pd.DataFrame(rows).set_index("date")
    if lo or hi:
        df_out = df_out.loc[lo:hi]
    return df_out


def add_regime_tags(df: pd.DataFrame) -> pd.DataFrame:
    """Tag each trade with a regime label."""
    df = df.copy()
    df["regime"] = "unknown"
    df.loc["2010-06-07":"2012-12-31", "regime"] = "2010-12_recovery"
    df.loc["2013-01-01":"2014-12-31", "regime"] = "2013-14_qe_trend"
    df.loc["2015-01-01":"2016-06-30", "regime"] = "2015-16_china_chop"
    df.loc["2016-07-01":"2017-12-31", "regime"] = "2016H2-17_trend"
    df.loc["2018-01-01":"2018-12-31", "regime"] = "2018_vol_shock"
    df.loc["2019-01-01":"2019-12-31", "regime"] = "2019_dovish_pivot"
    df.loc["2020-01-01":"2020-12-31", "regime"] = "2020_covid"
    df.loc["2021-01-01":"2021-12-31", "regime"] = "2021_recovery"
    df.loc["2022-01-01":"2022-12-31", "regime"] = "2022_bear"
    df.loc["2023-01-01":"2023-12-31", "regime"] = "2023_chop"
    df.loc["2024-01-01":"2026-05-29", "regime"] = "2024-26_bull"
    return df


if __name__ == "__main__":
    print("=" * 90)
    print("NQ ORB backtest sanity check — 2010-2026, single sleeve (US cash open)")
    print("=" * 90)
    df_5m = load_nq_5min()
    print(f"\nLoaded {len(df_5m):,} 5-min RTH bars across {df_5m.index.nunique() if hasattr(df_5m.index, 'nunique') else 'unknown'} days")
    print(f"Date range: {df_5m.index.min()} -> {df_5m.index.max()}")
    print(f"Sample bars per day at start: {df_5m.groupby(df_5m.index.date).size().iloc[:5].to_list()}")
    print(f"Sample bars per day later   : {df_5m.groupby(df_5m.index.date).size().iloc[-5:].to_list()}")
    print()

    # Quick test extraction
    for model in ["EXEC_0", "EXEC_NEXT_OPEN"]:
        print(f"--- {model} (cost=3 pts CFD) ---")
        df_trades = extract_trades(or_bars=6, exec_model=model, cost_pts=COST_POINTS_CFD)
        df_trades = add_regime_tags(df_trades)
        print(f"  Total trades: {len(df_trades)}")
        print(f"  Date range: {df_trades.index.min().date()} -> {df_trades.index.max().date()}")
        print(f"  Mean R: {df_trades['r_realised'].mean():+.4f}")
        print(f"  Median R: {df_trades['r_realised'].median():+.4f}")
        print(f"  Hit rate: {(df_trades['r_realised'] > 0).mean()*100:.2f}%")
        print(f"  Mean R by regime:")
        for reg, sub in df_trades.groupby("regime"):
            print(f"    {reg:<25s}: n={len(sub):>4d}, meanR={sub['r_realised'].mean():+.3f}, "
                  f"hit={(sub['r_realised']>0).mean()*100:.1f}%")
        df_trades.to_parquet(f"nq_trades_{model}.parquet")
        print()
