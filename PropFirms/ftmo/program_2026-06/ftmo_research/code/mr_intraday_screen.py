"""
mr_intraday_screen.py — Intraday mean-reversion fade: pre-filter (A cost-gate +
B L24 shape) AND the alpha-vs-beta validator, for FTMO liquid majors.

Key lesson it encodes (proposed L26): a naive vectorized fade screen with
OVERLAPPING forward windows + same-bar entry massively inflates the apparent MR
edge. The truth requires NON-OVERLAPPING trades + a 1-bar execution-delay test.
Run both and compare — the gap *is* the artifact.

Data: panels/m5_indices/m1_panel.parquet (US500/US100/US30/US2000, UTC),
      EURUSD_m1_panel.parquet, GER40_m1_panel.parquet  (OHLC, UTC).
Costs (bps RT, notional): US indices ~1.5, EURUSD ~1.0, GER40 ~1.5.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

BASE = "/sessions/blissful-upbeat-newton/mnt/Algo_claude/data/"


def _sessions_5m(close: pd.Series, h0: int, h1: int, tz: str | None) -> pd.DataFrame:
    """Resample a 1-min close series to 5-min within a [h0,h1) hour window."""
    idx = close.index
    if tz:
        idx = idx.tz_localize("UTC").tz_convert(tz)
        close = pd.Series(close.values, index=idx)
    m = close[(idx.hour >= h0) & (idx.hour < h1)]
    df = m.resample("5min").last().dropna().to_frame("px")
    df["session"] = df.index.normalize()
    g = df.groupby("session")
    df["rm"] = g["px"].transform(lambda x: x.rolling(6, min_periods=6).mean())
    df["dev_bps"] = (df["px"] / df["rm"] - 1) * 1e4
    return df


def screen_overlapping(df: pd.DataFrame, theta: float, cost: float, h: int) -> dict:
    """NAIVE screen: every bar beyond theta is a 'signal', forward windows overlap.
    INFLATES the edge — kept only to demonstrate the artifact vs the validator."""
    g = df.groupby("session")
    fwd = g["px"].shift(-h) / df["px"] - 1
    up = (df["dev_bps"] > theta) & fwd.notna()
    dn = (df["dev_bps"] < -theta) & fwd.notna()
    sg = (-fwd[up]).mean() * 1e4
    lg = (fwd[dn]).mean() * 1e4
    n = int(up.sum() + dn.sum())
    both = ((-fwd[up]).sum() + fwd[dn].sum()) / n * 1e4 if n else np.nan
    return {"n": n, "long": lg, "short": sg, "both_gross": both, "net": both - cost}


def trades_nonoverlap(df: pd.DataFrame, theta: float, cost: float,
                      h: int, delay: int = 0) -> pd.DataFrame:
    """TRUTH: non-overlapping trades. Signal at bar i (dev known at close i),
    enter at i+delay, exit at i+delay+h (same session), then jump past exit.
    delay=1 => realistic next-bar execution; the decisive look-ahead filter."""
    px = df["px"].values
    dev = df["dev_bps"].values
    sess = df["session"].values
    idx = df.index
    n = len(df)
    i = 0
    rows = []
    while i < n - h - delay:
        if not np.isnan(dev[i]) and abs(dev[i]) > theta:
            j = i + delay
            k = j + h
            if k < n and sess[k] == sess[j]:
                side = -np.sign(dev[i])                  # fade
                ret = side * (px[k] / px[j] - 1) * 1e4 - cost
                rows.append((idx[i], int(side), ret))
                i = k
                continue
        i += 1
    return pd.DataFrame(rows, columns=["t", "side", "net_bps"])


def evaluate(name: str, close: pd.Series, theta: float, cost: float,
             h: int = 6, h0: int = 9, h1: int = 16, tz: str | None = None) -> None:
    df = _sessions_5m(close, h0, h1, tz)
    naive = screen_overlapping(df, theta, cost, h)
    d = trades_nonoverlap(df, theta, cost, h)
    d1 = trades_nonoverlap(df, theta, cost, h, delay=1)
    if len(d) < 20:
        print(f"{name} θ{theta}: n={len(d)} too few"); return
    m = d.net_bps.mean(); t = m / d.net_bps.std() * np.sqrt(len(d))
    L = d[d.side > 0].net_bps.mean(); S = d[d.side < 0].net_bps.mean()
    d["yr"] = pd.to_datetime(d.t).dt.year
    yrs = d.groupby("yr").net_bps.mean()
    print(f"{name} θ{theta} h{h*5}m cost{cost}:")
    print(f"   NAIVE overlapping screen : both_gross {naive['both_gross']:+.2f}  net {naive['net']:+.2f} bps  (n_signals {naive['n']})")
    print(f"   TRUTH non-overlap trades : n={len(d)} meanNet {m:+.2f} bps  t={t:+.2f}  WR={(d.net_bps>0).mean():.0%}")
    print(f"     L/S split (L25) : long {L:+.2f} / short {S:+.2f}   regime {int((yrs>0).sum())}/{len(yrs)} yrs+")
    print(f"     1-bar DELAY     : meanNet {d1.net_bps.mean():+.2f} bps  (artifact if it collapses)")


if __name__ == "__main__":
    us = pd.read_parquet(BASE + "panels/m5_indices/m1_panel.parquet")
    us.index = pd.to_datetime(us.index)
    for sym in ("US500", "US100", "US30"):
        for th in (40, 50):
            evaluate(sym, us[(sym, "close")].dropna(), th, 1.5,
                     h0=9, h1=16, tz="America/New_York")
    for f, cost, h0, h1, ths in [("EURUSD_m1_panel.parquet", 1.0, 7, 21, (25, 40)),
                                 ("GER40_m1_panel.parquet", 1.5, 7, 16, (40, 60))]:
        s = pd.read_parquet(BASE + "panels/m5_indices/" + f)
        s.index = pd.to_datetime(s.index)
        for th in ths:
            evaluate(f.split("_")[0], s["close"].dropna(), th, cost, h0=h0, h1=h1)
