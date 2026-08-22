"""
orb_core.py — Audit re-implementation of the 3-sleeve ORB core.

The report (CHALLENGE_REPORT_FINAL §4) declares a 3-sleeve core:
    US100  @ 16:30 EET, 30-min OR  (US cash open)
    GER40  @ 16:30 EET, 15-min OR  (Europe reacts to US flow)
    GER40  @ 10:00 EET, 30-min OR  (DAX open)

The released `strategy_orb.py` does NOT implement GER40 @ 16:30 — its SESSION
dict only contains GER40 @ 10:00. We re-implement the 3-sleeve here.

Also exposes:
- daily R per setup (without and with entry-delay)
- daily R series per session-block (AM = GER40-10:00; PM = US100 + GER40-16:30)
- portfolio R (block-capped 1.5%) for daily Sharpe / DD / Monte-Carlo.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1].parent / "panels" / "m5_indices"

# Round-trip costs (index points), spread+slippage
COST_POINTS = {"US100": 3.0, "GER40": 1.5}

# 3-sleeve config: (instrument, open_h, open_m, close_h, or_bars_5m)
SLEEVES = [
    ("US100", 16, 30, 23, 6),    # 30-min OR
    ("GER40", 16, 30, 22, 3),    # 15-min OR (Europe reacts to US)
    ("GER40", 10,  0, 18, 6),    # 30-min OR (DAX open)
]
SLEEVE_NAMES = ["US100_1630_30m", "GER40_1630_15m", "GER40_1000_30m"]


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


def orb_daily_R(symbol: str, open_h: int, open_m: int, close_h: int,
                or_bars: int, cost_mult: float = 1.0,
                delay_bars: int = 0,
                slip_R: float = 0.0) -> pd.Series:
    """
    ORB daily R-multiples for one (symbol, session, OR-window) sleeve.

    delay_bars: 0 = enter at the breakout bar (instant fill at the level);
                k>0 = wait k 5-min bars before entering (delay-test for look-ahead).
                With k>0, entry price = open of bar (or_bars + i + k) if it has been
                breached in the prior k bars; trade is cancelled if stop has been
                touched in the meantime.
    slip_R   : additional slippage applied to both entry and stop, expressed
               as a fraction of 1R (i.e. of the opening-range size).
               Adverse: entry slips against you, stop fills slip past the level.
    """
    df = _load_m5(symbol)
    h, m = df.index.hour, df.index.minute
    df = df[((h > open_h) | ((h == open_h) & (m >= open_m))) & (h < close_h)].copy()
    df["day"] = df.index.date
    cost = COST_POINTS[symbol] * cost_mult
    out = {}
    for day, g in df.groupby("day"):
        H, L, C, O = g["high"].values, g["low"].values, g["close"].values, g["open"].values
        if len(H) < or_bars + 3 + delay_bars:
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
            direction, level, stop_level = 1, or_hi, or_lo
            bi = or_bars + iu
        else:
            direction, level, stop_level = -1, or_lo, or_hi
            bi = or_bars + idn

        # Apply entry delay
        if delay_bars > 0:
            # Check whether the opposite side was hit during the delay
            de = min(bi + delay_bars, len(g))
            interim_h = H[bi:de]
            interim_l = L[bi:de]
            if direction == 1:
                if (interim_l <= stop_level).any():
                    continue  # stopped out during delay -> no trade
            else:
                if (interim_h >= stop_level).any():
                    continue
            entry_bar = bi + delay_bars
            if entry_bar >= len(g):
                continue
            entry = O[entry_bar]
        else:
            entry = level
            entry_bar = bi

        # Adverse entry slippage
        slip_pts = slip_R * risk
        entry = entry + direction * slip_pts
        # Adverse stop slippage (stop fills past the level)
        stop_eff = stop_level - direction * slip_pts

        # Find exit
        fh, fl = H[entry_bar:], L[entry_bar:]
        if direction == 1:
            hit = np.where(fl <= stop_eff)[0]
        else:
            hit = np.where(fh >= stop_eff)[0]
        if len(hit):
            exit_px = stop_eff
        else:
            exit_px = C[-1]
        out[pd.Timestamp(day)] = (direction * (exit_px - entry) - cost) / risk
    return pd.Series(out, name=f"{symbol}_{open_h:02d}{open_m:02d}_{or_bars}")


def build_3sleeve_matrix(lo=None, hi=None, cost_mult=1.0,
                         delay_bars=0, slip_R=0.0) -> pd.DataFrame:
    """Date-indexed matrix of 3-sleeve R-multiples."""
    cols = {}
    for name, (sym, oh, om, ch, ob) in zip(SLEEVE_NAMES, SLEEVES):
        cols[name] = orb_daily_R(sym, oh, om, ch, ob,
                                 cost_mult=cost_mult,
                                 delay_bars=delay_bars,
                                 slip_R=slip_R)
    M = pd.concat(cols, axis=1)
    if lo or hi:
        M = M.loc[lo:hi]
    return M


def block_capped_pnl(M: pd.DataFrame, block_cap_pct: float = 0.015) -> pd.Series:
    """
    Block-capped daily portfolio P&L expressed in % of equity.

    Per the report: "block-cap 1.5%/session-open". The 3-sleeve config has:
        AM block: GER40 @ 10:00         -> 1 sleeve, 1.5% risk
        PM block: US100 @ 16:30, GER40 @ 16:30 -> 2 sleeves, 0.75% each
    Daily P&L (% of equity) = sum of (sleeve risk * sleeve R).
    """
    am_cols = ["GER40_1000_30m"]
    pm_cols = ["US100_1630_30m", "GER40_1630_15m"]
    pnl = pd.Series(0.0, index=M.index)
    # AM: 1 sleeve gets full 1.5%
    am = M[am_cols].fillna(0.0).sum(axis=1)
    pnl = pnl.add(block_cap_pct * am, fill_value=0.0)
    # PM: 2 sleeves share 1.5% (0.75% each)
    pm_risk = block_cap_pct / len(pm_cols)
    for c in pm_cols:
        pnl = pnl.add(pm_risk * M[c].fillna(0.0), fill_value=0.0)
    return pnl


if __name__ == "__main__":
    M = build_3sleeve_matrix(lo="2022", hi="2026")
    print(f"3-sleeve matrix: {M.shape[0]} days, {M.shape[1]} sleeves")
    print()
    print("Per-sleeve mean R:")
    print(M.mean().round(4).to_string())
    print()
    print(f"avg trades/day: {M.notna().sum(1).mean():.2f}")
    print()
    pnl = block_capped_pnl(M)
    print(f"Block-capped daily PnL: mean={pnl.mean()*100:+.4f}%/day  "
          f"std={pnl.std()*100:.4f}%/day  "
          f"daily Sharpe (annualised)={pnl.mean()/pnl.std()*np.sqrt(252):.3f}")
