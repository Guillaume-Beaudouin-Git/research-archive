"""
Historical policy/interbank rate differentials per pair, read from the
existing FRED cache (Forex/data/cache/g10_rates_3m.parquet) — NO network
call (cache read directly, bypassing fred_loader's freshness/refetch logic,
since this session is offline-safe by design).

Differential convention: for pair BASE/QUOTE, diff_pp(t) = rate(BASE,t) -
rate(QUOTE,t) in %/year. Positive diff => going long the pair (buy BASE,
sell QUOTE) is the side that should collect carry pre-markup.

T-1 discipline: the monthly FRED series is shifted forward by one full
month before being forward-filled onto the daily calendar, i.e. a rate
observed for month M is only used starting month M+1. This is a
conservative proxy for publication lag (3M interbank/policy rates are
typically known well before month-end in real time, so this materially
UNDER-states, not overstates, information available).
"""
from __future__ import annotations
import pandas as pd
from pathlib import Path

CACHE = Path("<HOME>/Desktop/Algo_claude/Forex/data/cache/g10_rates_3m.parquet")

PAIR_CCY = {
    "AUDJPY": ("AUD", "JPY"),
    "USDJPY": ("USD", "JPY"),
    "USDCHF": ("USD", "CHF"),
    "USDCAD": ("USD", "CAD"),
    "EURUSD": ("EUR", "USD"),
    "AUDUSD": ("AUD", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "NZDUSD": ("NZD", "USD"),
    "GBPJPY": ("GBP", "JPY"),
}


def load_rates_monthly() -> pd.DataFrame:
    df = pd.read_parquet(CACHE)
    df.index = pd.to_datetime(df.index)
    return df


def daily_differential(pair: str, daily_index: pd.DatetimeIndex) -> pd.Series:
    """Daily differential (base - quote, %/yr), T-1 safe, ffill<=3 months."""
    rates = load_rates_monthly()
    base, quote = PAIR_CCY[pair]
    diff_m = (rates[base] - rates[quote]).dropna()
    # publication-lag shift: value known for month M becomes usable at
    # the START of month M+1
    diff_m = diff_m.copy()
    diff_m.index = diff_m.index + pd.offsets.MonthBegin(1)
    diff_m = diff_m.sort_index()
    daily = diff_m.reindex(
        pd.date_range(diff_m.index.min(), daily_index.max(), freq="D"), method="ffill"
    )
    daily = daily.reindex(daily_index, method="ffill")
    return daily.rename(pair)


def all_differentials(pairs: list[str], daily_index: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame({p: daily_differential(p, daily_index) for p in pairs})


if __name__ == "__main__":
    df = load_rates_monthly()
    print(df.tail(10))
    idx = pd.date_range("2007-01-01", "2026-08-28", freq="D", tz="UTC")
    d = all_differentials(list(PAIR_CCY), idx.tz_localize(None))
    print(d.tail(10))
    print("NaN fraction:\n", d.isna().mean())
