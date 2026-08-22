"""
v2_lib.py — uncovered-space engines for iteration 2. Reuses iter-1 funnel_lib verbatim
(CFDCostModel via F.rt_cost_fraction, dsr, ftmo_first_passage, true-UTC daily cache, stats).

Adds ONLY what iter-1 structurally lacked:
  - intraday 15/30min index loader + intraday-flat mean-reversion backtest (space C),
  - multi-leg (>=3) relative-value builders (space A),
  - causal regime/calendar conditioning of proven edges (space B).
All outputs are causal real-cost DAILY net-return series (for DSR/decorrelation continuity).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

V1 = Path("<HOME>/Desktop/Algo_claude/research/ftmo_candidate_funnel")
sys.path.insert(0, str(V1))
import funnel_lib as F           # iter-1 infra (cost model, dsr, engine, daily cache)

CACHE = Path(__file__).parent / "cache"
INTRADAY_SLIP_BPS = 1.0          # >=1 tick extra slippage for sub-60min (on top of spread x markup + base)
# liquid intraday windows (UTC hour, [lo, hi)); DST wobble accepted for triage
SESSION = {"US500": (14, 21), "US100": (14, 21), "US30": (14, 21), "GER40": (7, 16)}

_INTRA: dict = {}

def load_intraday(sym: str, freq: str, stress: float = 1.0) -> pd.DataFrame:
    key = f"{sym}|{freq}|{stress}"
    if key in _INTRA:
        return _INTRA[key]
    d = pd.read_parquet(CACHE / f"{sym}_{freq}.parquet")
    d["ts"] = pd.to_datetime(d["ts"])
    lo, hi = SESSION[sym]
    d = d[(d["ts"].dt.hour >= lo) & (d["ts"].dt.hour < hi)].copy()
    d["date"] = d["ts"].dt.normalize()
    d = d.sort_values("ts").reset_index(drop=True)
    # intraday bar return, no overnight carry (first bar of each session -> 0)
    d["bar_ret"] = d["close"].pct_change()
    first = d["date"].ne(d["date"].shift(1))
    d.loc[first, "bar_ret"] = 0.0
    d["rt_cost"] = F.rt_cost_fraction(sym, d["spread_med"].to_numpy(), d["close"].to_numpy(),
                                      stress=stress) + INTRADAY_SLIP_BPS * 1e-4 * stress
    _INTRA[key] = d
    return d

def intraday_backtest(sym: str, freq: str, sigfn, stress: float = 1.0, gross_only=False) -> pd.Series:
    """Causal intraday MR -> daily net return. sigfn(d)->per-bar position (already .shift(1)-ed,
    flat on first bar of each session). Flatten overnight (no cross-day carry).
    gross_only=True returns the pre-cost daily series (mechanism diagnostic)."""
    d = load_intraday(sym, freq, stress=stress)
    pos = sigfn(d).reindex(d.index).fillna(0.0)
    first = d["date"].ne(d["date"].shift(1))
    pos = pos.where(~first, 0.0)                         # no position on first session bar
    gross = pos * d["bar_ret"]
    if gross_only:
        daily = gross.groupby(d["date"]).sum()
        daily.index = pd.DatetimeIndex(daily.index); return daily
    dpos = pos.diff()
    dpos = dpos.where(~first, pos)                       # opening trade counts
    last = d["date"].ne(d["date"].shift(-1))
    dpos = dpos + pos.where(last, 0.0)                   # closing trade (flatten EOD) counts
    cost = 0.5 * d["rt_cost"] * dpos.abs()
    net = gross - cost
    daily = net.groupby(d["date"]).sum()
    daily.index = pd.DatetimeIndex(daily.index)
    return daily

def isig_session_fade(eb: int = 2):
    """Low-turnover intraday reversion: ~1h into the session, fade the move from the session open
    and hold to the close (1 round-trip/day -> cost-survivable). Causal (decided at bar eb, traded eb+1+)."""
    def f(d):
        bar_in_day = d.groupby("date").cumcount()
        sess_open = d.groupby("date")["open"].transform("first")
        cumret = d["close"] / sess_open - 1.0
        pos = pd.Series(np.nan, index=d.index)
        pos[bar_in_day == eb] = -np.sign(cumret[bar_in_day == eb])
        pos = pos.groupby(d["date"]).ffill().fillna(0.0)
        return pos.shift(1)
    return f

# intraday signals (per-bar, causal: features .shift(1))
def isig_fade_prev(d: pd.DataFrame) -> pd.Series:
    return -np.sign(d["bar_ret"]).shift(1)

def isig_zfade(k: int = 6, cap: float = 2.0):
    def f(d):
        c = d["close"]
        m = c.rolling(k).mean(); s = c.rolling(k).std(ddof=0)
        z = (c - m) / s.replace(0, np.nan)
        return (-z / cap).clip(-1, 1).shift(1)
    return f

def isig_zfade_bigbar(k: int = 6, cap: float = 2.0, thr: float = 1.0):
    """Fade only after a large bar (|bar_ret| z > thr): selectivity within intraday reversion."""
    def f(d):
        c = d["close"]; z = (c - c.rolling(k).mean()) / c.rolling(k).std(ddof=0).replace(0, np.nan)
        rz = d["bar_ret"] / d["bar_ret"].rolling(20).std(ddof=0).replace(0, np.nan)
        base = (-z / cap).clip(-1, 1)
        return base.where(rz.abs() > thr, 0.0).shift(1)
    return f

# ── multi-leg relative value (>=3 legs), daily, real cost per leg ──────────────
def _legnet(sym: str, pos: pd.Series, stress=1.0) -> pd.Series:
    d = F.load_daily(sym, stress=stress)
    p = pos.reindex(d.index).fillna(0.0)
    gross = p * d["ret"]
    cost = 0.5 * d["rt_cost"] * p.diff().fillna(p).abs()
    return (gross - cost).fillna(0.0)

def xs_reversion(syms, k=5, mom=False, stress=1.0) -> pd.Series:
    """Cross-sectional reversion (mom=False) or momentum (mom=True), dollar-neutral, >=3 legs."""
    C = F.close_panel(syms)
    feat = (C / C.shift(k) - 1.0).shift(1)
    z = feat.sub(feat.mean(axis=1), axis=0).div(feat.std(axis=1).replace(0, np.nan), axis=0)
    pos = (z if mom else -z).clip(-1, 1)
    pos = pos.sub(pos.mean(axis=1), axis=0)             # dollar-neutral
    return pd.DataFrame({s: _legnet(s, pos[s], stress) for s in syms}).sum(axis=1)

def triangular_fx(stress=1.0) -> pd.Series:
    """EURGBP vs synthetic (EURUSD/GBPUSD): fade the triangular residual z-score. 3 legs."""
    eu = np.log(F.load_daily("EURUSD")["close"]); gu = np.log(F.load_daily("GBPUSD")["close"])
    eg = np.log(F.load_daily("EURGBP")["close"])
    resid = (eg - (eu - gu)).dropna()
    z = ((resid - resid.rolling(20).mean()) / resid.rolling(20).std(ddof=0)).shift(1)
    sig = (-z / 2).clip(-1, 1)                           # resid rich -> short EURGBP, long EURUSD short GBPUSD
    legs = {"EURGBP": sig, "EURUSD": -sig, "GBPUSD": sig}
    return pd.DataFrame({s: _legnet(s, legs[s], stress) for s in legs}).sum(axis=1)

def equity_vs_gold(k=10, stress=1.0) -> pd.Series:
    """Equity basket (US500/US100/GER40) vs gold ratio reversion. 4 legs, cross-asset (less
    hedging-rule exposed than index-vs-index). When equity outperformed gold -> short eq / long gold."""
    eq = ["US500", "US100", "GER40"]
    rel = pd.DataFrame({s: np.log(F.load_daily(s)["close"]) for s in eq}).mean(axis=1) \
        - np.log(F.load_daily("XAUUSD")["close"])
    rel = rel.dropna()
    z = ((rel - rel.rolling(k * 2).mean()) / rel.rolling(k * 2).std(ddof=0)).shift(1)
    sig = (-z / 2).clip(-1, 1)
    legs = {**{s: sig / 3 for s in eq}, "XAUUSD": -sig}
    return pd.DataFrame({s: _legnet(s, legs[s], stress) for s in legs}).sum(axis=1)

# ── regime / calendar conditioning of proven edges (space B) ──────────────────
def tsmom_basket_pos(syms, k=200):
    return {s: F.sig_tsmom(F.load_daily(s), k) for s in syms}

def cond_mask_dow(idx, keep_days):           # keep only chosen weekdays
    return pd.Series(np.isin(idx.dayofweek, keep_days).astype(float), index=idx)

def cond_mask_monthend(idx, w=3):
    ym = idx.to_period("M"); g = pd.Series(idx, index=idx).groupby(ym)
    fwd = g.cumcount().to_numpy(); size = g.transform("size").to_numpy(); bwd = size - 1 - fwd
    return pd.Series(((bwd < w) | (fwd < w)).astype(float), index=idx)

def cond_mask_trendstrength(df, k=200, theta=1.0):
    mom = df["close"] / df["close"].shift(k) - 1.0
    vol = df["ret"].rolling(k).std() * np.sqrt(k)
    return ((mom.abs() / vol.replace(0, np.nan)) > theta).astype(float).shift(1)

def conditioned_tsmom(syms, k=200, mask_fn=None, stress=1.0) -> pd.Series:
    legs = {}
    for s in syms:
        d = F.load_daily(s, stress=stress)
        pos = F.sig_tsmom(d, k)
        if mask_fn is not None:
            m = mask_fn(d).reindex(pos.index).fillna(0.0)
            pos = pos * m
        legs[s] = F.backtest(s, pos, stress=stress)
    return F.combine_inv_vol(legs)
