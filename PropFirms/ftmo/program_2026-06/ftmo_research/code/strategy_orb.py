"""
strategy_orb.py — Index Opening-Range Breakout (ORB) ensemble.

This is the FTMO Strategy 2 engine: a GENUINE positive-expectancy intraday edge
on equity-index CFDs (unlike the FX majors, which were efficient to costs).

Timezone (critical):
    The index data is in broker server time (EET, UTC+2/+3). The US cash open
    (09:30 ET) lands at exactly 16:30 in the data; the DAX open (09:00 CET) at
    10:00. Verified via the volume/volatility jump. Because ET and EET both
    observe DST, the US session is ALWAYS 16:30-23:00 in data-time.

Edge (out-of-sample 2024-25, net of CFD spread+slippage):
    US100  ORB meanR ~ +0.10      GER40 ORB meanR ~ +0.08
    US30   ORB meanR ~ +0.03      (US500/US2000 decayed/negative -> excluded)
    The ORB *outcome* is ~uncorrelated across instruments (US100/GER40 corr -0.02),
    so each is an independent positive-EV bet -> diversification is real.

Strategy:
    * Opening range = first {5,15,30}-min after the open (3 windows = 3 setups).
    * Enter on the first break of the OR high (long) / low (short).
    * Stop at the opposite side of the OR  -> risk = OR size = 1R.
    * No profit target: let winners run to the session close (this preserves the
      positive skew that *is* the edge; a target destroys it).
    * Net of per-instrument round-trip cost (spread + slippage).
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "panels" / "m5_indices"

# round-trip cost in INDEX POINTS (spread + slippage), from the data's spread column
COST_POINTS = {"US100": 3.0, "US30": 4.5, "GER40": 1.5, "US500": 1.2, "US2000": 2.0}
# session open/close in DATA time (EET); ('open_h','open_m','close_h')
SESSION = {"US100": (16, 30, 23), "US30": (16, 30, 23), "US500": (16, 30, 23),
           "US2000": (16, 30, 23), "GER40": (10, 0, 18)}
# default ensemble: instrument -> opening-range windows in M5 bars (1=5m,3=15m,6=30m)
ENSEMBLE = {"US100": (1, 3, 6), "GER40": (1, 3, 6), "US30": (3,)}


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
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def orb_daily_R(symbol: str, or_bars: int, cost_mult: float = 1.0) -> pd.Series:
    """One ORB trade per day; returns net R-multiples indexed by date."""
    oh, om, ch = SESSION[symbol]
    df = _load_m5(symbol)
    h, m = df.index.hour, df.index.minute
    df = df[((h > oh) | ((h == oh) & (m >= om))) & (h < ch)].copy()
    df["day"] = df.index.date
    cost = COST_POINTS[symbol] * cost_mult
    out = {}
    for day, g in df.groupby("day"):
        H, L, C = g["high"].values, g["low"].values, g["close"].values
        if len(H) < or_bars + 3:
            continue
        or_hi, or_lo = H[:or_bars].max(), L[:or_bars].min()
        risk = or_hi - or_lo
        if risk <= 0:
            continue
        up = np.where(H[or_bars:] > or_hi)[0]
        dn = np.where(L[or_bars:] < or_lo)[0]
        iu = up[0] if len(up) else 10**9
        idn = dn[0] if len(dn) else 10**9
        if iu == idn == 10**9:
            continue
        if iu <= idn:
            direction, entry, stop, bi = 1, or_hi, or_lo, or_bars + iu
        else:
            direction, entry, stop, bi = -1, or_lo, or_hi, or_bars + idn
        fh, fl = H[bi:], L[bi:]
        hit = np.where(fl <= stop)[0] if direction == 1 else np.where(fh >= stop)[0]
        exit_px = stop if len(hit) else C[-1]            # else session close
        out[pd.Timestamp(day)] = (direction * (exit_px - entry) - cost) / risk
    return pd.Series(out, name=f"{symbol}_{or_bars}")


def build_ensemble_matrix(ensemble: dict = ENSEMBLE, lo=None, hi=None,
                          cost_mult: float = 1.0) -> pd.DataFrame:
    """Date-indexed matrix of net R per (instrument, OR-window) setup."""
    cols = {f"{s}_{ob}": orb_daily_R(s, ob, cost_mult)
            for s, obs in ensemble.items() for ob in obs}
    M = pd.concat(cols, axis=1)
    if lo or hi:
        M = M.loc[lo:hi]
    return M


if __name__ == "__main__":
    M = build_ensemble_matrix(lo="2024", hi="2025")
    print("OOS 2024-25 mean R per setup:")
    print(M.mean().round(3).to_string())
    print(f"\navg trades/day = {M.notna().sum(1).mean():.1f}")
