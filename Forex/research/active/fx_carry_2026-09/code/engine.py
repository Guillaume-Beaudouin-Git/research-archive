"""
Carry-conditional FX backtest engine — standalone, decoupled from the
Dedale pivot/TDI mechanism (already tested and killed in
Forex/research/active/dedale_strategy_2026-08/RAPPORT.md, n=1990, DSR
0.024 at cumulative load). This engine tests ONLY the carry-direction
question: does historical rate-differential direction, real FTMO swap,
real FTMO cost, add anything vs matched placebos?

Signal: T-1. Rebalance every REBALANCE_DAYS trading days. Direction at
each rebalance = sign of the FRED rate differential known as of the
PRIOR trading day's close (rates.py already applies a 1-month
publication-lag shift on top, so this is doubly conservative).
Position held constant between rebalances (buy-and-hold style leg, no
intrabar SL/TP — this is deliberately NOT a replication of Dedale's
pivot system, it isolates the carry-direction filter alone).

Daily vol targeting: position size = TARGET_VOL / realized_vol_20d,
capped at MAX_LEV.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from swaps import swap_bps_per_night, SWAP_TABLE

TARGET_VOL_ANNUAL = 0.10
VOL_WINDOW = 20
MAX_LEV = 3.0
REBALANCE_DAYS = 10  # ~2 calendar weeks, close to Dedale's ~11-day avg hold
TRADING_DAYS_PER_YEAR = 260


def realized_vol(logret: pd.Series, window: int = VOL_WINDOW) -> pd.Series:
    return logret.rolling(window).std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def rebalance_dates(index: pd.DatetimeIndex, every: int = REBALANCE_DAYS) -> pd.DatetimeIndex:
    return index[::every]


def direction_from_diff(diff: pd.Series, rebal_dates: pd.DatetimeIndex) -> pd.Series:
    """Sign of the differential AT each rebalance date, held flat between them.
    diff is already T-1-safe (monthly, shifted 1 month, ffilled)."""
    sig_at_rebal = np.sign(diff.reindex(rebal_dates)).replace(0, 1)
    direction = sig_at_rebal.reindex(diff.index, method="ffill")
    return direction.rename("direction")


def direction_random(index: pd.DatetimeIndex, rebal_dates: pd.DatetimeIndex, rng: np.random.Generator) -> pd.Series:
    draws = rng.choice([-1.0, 1.0], size=len(rebal_dates))
    sig_at_rebal = pd.Series(draws, index=rebal_dates)
    direction = sig_at_rebal.reindex(index, method="ffill")
    return direction.rename("direction")


def _calendar_nights(dates: pd.DatetimeIndex) -> pd.Series:
    """Number of calendar nights bridged between consecutive trading bars,
    with Wednesday-rollover tripling (standard FX broker T+2 convention):
    the night charged on a Wednesday bar counts as 3 (compensates the
    weekend). All other bars count as 1 regardless of the actual calendar
    gap (weekends have no bars to charge individually)."""
    is_wed = dates.weekday == 2
    nights = pd.Series(np.where(is_wed, 3, 1), index=dates, dtype=float)
    return nights


def backtest(
    close: pd.Series,
    pair: str,
    direction: pd.Series,
    cost_bps_rt: float,
    apply_swap: bool = True,
    swap_override_bps: dict[int, float] | None = None,
) -> pd.DataFrame:
    """
    close: daily close price series (index = daily UTC).
    direction: +1/-1 series, same index (already the position BEFORE
        applying vol-targeting; will be lagged by 1 day here to enforce
        signal T-1 / trade T on the price return itself, on top of the
        rebalance-date lag already in `direction`).
    cost_bps_rt: round-trip execution cost in bps of notional, charged
        on direction-flip days (half on entry, half on exit approximated
        as full RT on the day of the flip).
    Returns a DataFrame with columns: pos, logret, price_pnl, swap_pnl,
    cost_pnl, net_pnl (all in return units, i.e. already vol-scaled).
    """
    df = pd.DataFrame(index=close.index)
    df["close"] = close
    df["logret"] = np.log(close).diff()
    vol = realized_vol(df["logret"])
    lev = (TARGET_VOL_ANNUAL / vol).clip(upper=MAX_LEV).fillna(0.0)

    direction = direction.reindex(df.index).ffill().fillna(0.0)
    raw_pos = direction * lev
    # signal T-1 / trade T: today's *decided* position only affects tomorrow's return
    pos = raw_pos.shift(1).fillna(0.0)
    df["pos"] = pos

    df["price_pnl"] = pos * df["logret"]

    if apply_swap:
        nights = _calendar_nights(df.index)
        sign_pos = np.sign(pos.values)
        long_bps, short_bps, _, _ = SWAP_TABLE[pair]
        swap_bps = np.where(sign_pos > 0, long_bps, np.where(sign_pos < 0, short_bps, 0.0))
        df["swap_pnl"] = pos.abs().values * (swap_bps * 1e-4) * nights.values
    else:
        df["swap_pnl"] = 0.0

    flips = (np.sign(pos) != np.sign(pos.shift(1).fillna(0.0)))
    turnover = flips.astype(float) * pos.abs()
    df["cost_pnl"] = -turnover * (cost_bps_rt * 1e-4)

    df["net_pnl"] = df["price_pnl"] + df["swap_pnl"] + df["cost_pnl"]
    return df


def portfolio_return(pair_dfs: dict[str, pd.DataFrame], col: str = "net_pnl") -> pd.Series:
    """Equal-weight average across pairs, aligned on the common index."""
    mat = pd.DataFrame({p: d[col] for p, d in pair_dfs.items()})
    return mat.mean(axis=1, skipna=True)
