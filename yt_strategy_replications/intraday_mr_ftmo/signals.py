"""
Intraday mean-reversion signals (pre-registered). Causal; the 1-bar execution lag
(signal at close t -> enter open t+1) is enforced by engine.backtest, not here.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # reach the engine pkg
from engine import indicators as ind


def _bars_to_session_end(df: pd.DataFrame) -> np.ndarray:
    g = df.groupby("session_date")
    ordinal = g.cumcount().to_numpy()
    size = g["close"].transform("size").to_numpy()
    return size - 1 - ordinal


def zscore_reversal(df: pd.DataFrame, k: int = 20, z0: float = 2.0,
                    s_sl: float = 1.0, s_tp: float = 1.0, H: int = 8):
    """S1: fade an extreme z-score move. Two-sided. Returns (signal, sl_dist, tp_dist)."""
    z = ind.zscore(df["close"], k)
    atr = ind.atr(df["high"], df["low"], df["close"], n=k)
    sig = np.where(z <= -z0, 1.0, np.where(z >= z0, -1.0, 0.0))
    # intraday-flat guarantee: no entry that could cross the session close
    no_entry = _bars_to_session_end(df) <= H
    sig = np.where(no_entry, 0.0, sig)
    sig = np.where(np.isnan(z.to_numpy()), 0.0, sig)
    sl = (s_sl * atr).to_numpy()
    tp = (s_tp * atr).to_numpy()
    return sig, sl, tp


def gap_fade(df: pd.DataFrame, g0: float = 1.0, s_sl: float = 1.0, s_tp: float = 1.0):
    """S2: fade the session-open gap vs the prior session close (indices). One config."""
    first = df.groupby("session_date").head(1).index
    prior_close = df.groupby("session_date")["close"].last().shift(1)
    open_px = df.loc[first, "open"]
    sdate = df.loc[first].index.normalize()
    gap = (open_px.to_numpy() / prior_close.reindex(sdate).to_numpy() - 1.0)
    # daily sigma of gaps (causal): rolling std of gap over 60 sessions, shifted
    gser = pd.Series(gap, index=sdate)
    sig_thr = gser.rolling(60, min_periods=20).std().shift(1)
    fire = np.abs(gser) >= g0 * sig_thr
    direction = np.where(gser > 0, -1.0, 1.0) * fire.to_numpy()  # fade
    sig = pd.Series(0.0, index=df.index)
    sig.loc[first] = direction
    atr = ind.atr(df["high"], df["low"], df["close"], n=20)
    sl = (s_sl * atr).to_numpy()
    tp = (s_tp * atr).to_numpy()
    return sig.to_numpy(), sl, tp


def vol_target_scale(df: pd.DataFrame, k: int = 20, target_vol: float = 0.15,
                     bars_per_year: float = 6552.0, cap: float = 3.0) -> pd.Series:
    """Causal per-bar position scale = clip(target/realized_vol_{t-1}, cap)."""
    r = df["close"].pct_change()
    rv = r.rolling(k, min_periods=k).std(ddof=0) * np.sqrt(bars_per_year)
    scale = (target_vol / rv).shift(1).clip(upper=cap)
    return scale.reindex(df.index)
