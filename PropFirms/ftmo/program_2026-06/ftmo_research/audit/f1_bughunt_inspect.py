"""
f1_bughunt_inspect.py — Manual inspection of 20 trades.

For 10 fast-winning (ttb low, R high) and 10 slow-losing (ttb high, R low):
  - Print the bar-by-bar OHLC sequence around the OR + breakout + exit
  - Show OR borders, breakout bar, entry price under each exec model
  - Check whether the entry price is achievable in real time

This is to visually catch any look-ahead in the way trades are constructed.
"""
from __future__ import annotations
from pathlib import Path
from functools import lru_cache
import numpy as np
import pandas as pd


DATA = Path(__file__).resolve().parents[1].parent / "panels" / "m5_indices"
SLEEVES_MAP = {
    "US100_1630_30m": ("US100", 16, 30, 23, 6),
    "GER40_1630_15m": ("GER40", 16, 30, 22, 3),
    "GER40_1000_30m": ("GER40", 10,  0, 18, 6),
}


@lru_cache(maxsize=8)
def _load_m5(symbol: str) -> pd.DataFrame:
    if symbol in ("US100", "US500", "US30", "US2000"):
        df = pd.read_parquet(DATA / "m1_panel.parquet")[symbol].dropna()
    else:
        df = pd.read_parquet(DATA / f"{symbol}_m1_panel.parquet")
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df = df[["open", "high", "low", "close"]].dropna()
    return df.resample("5min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()


def get_day_bars(sleeve: str, date) -> pd.DataFrame:
    symbol, oh, om, ch, or_bars = SLEEVES_MAP[sleeve]
    df = _load_m5(symbol)
    h, m = df.index.hour, df.index.minute
    sess = df[((h > oh) | ((h == oh) & (m >= om))) & (h < ch)].copy()
    day_bars = sess.loc[sess.index.normalize() == pd.Timestamp(date).normalize()]
    return day_bars, or_bars


def inspect(trades: pd.DataFrame, n_fast=10, n_slow=10) -> None:
    # Add a copy to allow sorting
    df = trades.copy()
    # Fast winning: ttb low AND R > 0
    fast_win = df[(df["time_to_break_5min"] == 0) & (df["r_realised"] > 0)].sort_values(
        "r_realised", ascending=False).head(n_fast)
    # Slow losing: ttb high AND R < 0
    slow_lose = df[df["time_to_break_5min"] >= 5].sort_values(
        "r_realised", ascending=True).head(n_slow)

    for label, sub in [("=== FAST WINNERS (ttb=0, big R) ===", fast_win),
                        ("=== SLOW LOSERS (ttb>=5, lowest R) ===", slow_lose)]:
        print(label)
        for d, row in sub.iterrows():
            sleeve = row["sleeve"]
            symbol, oh, om, ch, or_bars = SLEEVES_MAP[sleeve]
            day_bars, _ = get_day_bars(sleeve, d)
            if len(day_bars) < or_bars + 3:
                continue
            or_hi = day_bars["high"].iloc[:or_bars].max()
            or_lo = day_bars["low"].iloc[:or_bars].min()
            or_range = or_hi - or_lo
            ttb = int(row["time_to_break_5min"])
            direction = int(row["breakout_dir"])
            level = or_hi if direction == 1 else or_lo
            stop_level = or_lo if direction == 1 else or_hi
            r_realised = row["r_realised"]
            outcome = row["outcome"]
            # Bar bi
            bi = or_bars + ttb
            print(f"\n  {sleeve} | {d.date()} | dir={direction} | ttb={ttb} | "
                  f"OR=[{or_lo:.1f}, {or_hi:.1f}] range={or_range:.1f} | "
                  f"R={r_realised:+.2f} | outcome={outcome}")
            # Print OR bars + 2 bars before break + break bar + 1 bar after
            window_start = max(0, or_bars - 1)
            window_end = min(len(day_bars), bi + 3)
            ohlc = day_bars.iloc[window_start:window_end]
            print(f"  {'idx':>4} {'time':>5} {'open':>10} {'high':>10} {'low':>10} {'close':>10}  {'tag':<12}")
            for i, (ts, br) in enumerate(ohlc.iterrows(), start=window_start):
                tag = ""
                if i < or_bars:
                    tag = "OR-bar"
                elif i == bi:
                    tag = "BREAK-bar"
                elif i == bi + 1:
                    tag = "ENTRY-bar (delay/next-open)"
                arrow_or_hi = " ⤴" if br["high"] > or_hi else ""
                arrow_or_lo = " ⤵" if br["low"] < or_lo else ""
                arrow = arrow_or_hi if direction == 1 else arrow_or_lo
                print(f"  {i:>4} {ts.strftime('%H:%M'):>5} "
                      f"{br['open']:>10.1f} {br['high']:>10.1f} "
                      f"{br['low']:>10.1f} {br['close']:>10.1f}  {tag}{arrow}")
            # Show the 3 entry prices
            entry_exec0 = level
            entry_next_open = day_bars["open"].iloc[bi + 1] if bi + 1 < len(day_bars) else float("nan")
            print(f"  Entry prices: EXEC_0={entry_exec0:.1f} (= level) | "
                  f"NEXT_OPEN={entry_next_open:.1f} | slip if real next_open = "
                  f"{(entry_next_open - entry_exec0) * direction:+.1f} pts adverse")


if __name__ == "__main__":
    df = pd.read_parquet("trade_dataset.parquet")
    print(f"Loaded {len(df)} trades from buggy dataset")
    print()
    inspect(df, n_fast=8, n_slow=8)
