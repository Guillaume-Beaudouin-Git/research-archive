"""
fx_intraday_lib.py — loader + session-table + IC/HAC helpers for the intraday-FX deep-dive.

Reuses the program infra VERBATIM via funnel_lib (which itself reuses cfd_costs.CFDCostModel,
ftmo_first_passage.combined_pass_prob_empirical, and dsr.deflated_sharpe_ratio):
    F.rt_cost_fraction, F.p_funded, F.ann_sharpe, F.stats, F.split_is_oos, F.combine_inv_vol.

Data: Forex/research/active/fx_intraday_deepdive/cache/<sym>_15min.parquet (built by build_intraday_cache.py from
data/deep_history_utc M1, TRUE UTC verified empirically). Bars: ts(UTC, 15-min start), open/high/low/close,
spread_med (M1 median spread in points within the bar), tick_vol, n_m1.

Conventions (HARD RULES honoured):
  * Causal: a London-day-d signal uses ONLY bars with ts <= 07:00 UTC of day d. Entry price is the OPEN of
    a bar with ts >= 07:00 UTC of day d (delay >= 1 bar after the [06:45,07:00) signal bar). No look-ahead.
  * Intraday-flat: enter at the London open, exit by <= 15:00 UTC -> no overnight carry, swap = 0.
  * Net return: gross - 0.5*rt_cost*|dpos| applied on entry and exit legs (one round trip / day / pair).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
FUNNEL = REPO / "research" / "ftmo_candidate_funnel"
sys.path.insert(0, str(FUNNEL))
import funnel_lib as F                      # noqa: E402  (cost model, p_funded, dsr, stats — verbatim)
from dsr import deflated_sharpe_ratio       # noqa: E402

CACHE = Path(__file__).parent / "cache"
PPY = 252
OOS_START = pd.Timestamp("2025-01-01")

# mechanism-driven universe split (frozen in PRE_REGISTRATION.md §2.1)
PRIMARY = ["EURUSD", "GBPUSD", "EURGBP", "USDCHF", "USDCAD"]      # Asian session thin -> predict reversal
CONTRAST = ["USDJPY", "EURJPY", "AUDJPY", "AUDUSD", "NZDUSD"]     # Asia-native -> predict weak/absent
ALL_FX = PRIMARY + CONTRAST

_BARS: dict[str, pd.DataFrame] = {}


def load_bars(sym: str) -> pd.DataFrame:
    """15-min bars, UTC, all sessions (incl. Sunday evening — needed for Monday's Asian window)."""
    if sym in _BARS:
        return _BARS[sym]
    d = pd.read_parquet(CACHE / f"{sym}_15min.parquet")
    d["ts"] = pd.to_datetime(d["ts"])
    d = d.sort_values("ts").reset_index(drop=True)
    d["utc_hour"] = d["ts"].dt.hour.astype(np.int16)
    d["utc_min"] = d["ts"].dt.minute.astype(np.int16)
    d["caldate"] = d["ts"].dt.normalize()
    d["dow"] = d["ts"].dt.dayofweek.astype(np.int8)
    _BARS[sym] = d
    return d


def _anchor(bars: pd.DataFrame, hh: int, mm: int = 0) -> pd.DataFrame:
    """Bars at a given UTC HH:MM, one row per calendar date: open price + median spread + dow."""
    m = bars[(bars["utc_hour"] == hh) & (bars["utc_min"] == mm)]
    return (m[["caldate", "open", "spread_med", "close", "dow"]]
            .rename(columns={"open": "px", "spread_med": "sp"})
            .drop_duplicates("caldate").set_index("caldate").sort_index())


def session_table(sym: str, asian_start_hh: int = 23, open_hh: int = 7,
                  exit_hh: int = 12, delay_bars: int = 1) -> pd.DataFrame:
    """
    Per London-day-d table (index = London-day calendar date, Mon-Fri):
      asian_ret   = log(px(open_hh, d)) - log(px(asian_start_hh, prev evening))   [known at open_hh:00]
      entry_px    = open of the bar (open_hh:00 + delay_bars*15min)               [delay>=1 -> causal]
      exit_px     = open of the bar (exit_hh:00)
      fwd_ret     = log(exit_px) - log(entry_px_at_open)   (IC target uses entry at open_hh:00, delay+1)
      sp_entry/sp_exit = calibrated median spread (points) at entry/exit bars (for cost)
    Overnight anchor aligned with merge_asof (prev evening's asian_start bar; Sun for Monday).
    """
    bars = load_bars(sym)
    london = _anchor(bars, open_hh, 0)                       # 07:00 anchor, Mon-Fri (no Sun 07:00)
    london = london[london.index.dayofweek < 5].copy()
    # overnight start anchor (prev evening): exists Sun-Thu for hh>=21; same-day for hh<12
    asn = _anchor(bars, asian_start_hh, 0)
    if asian_start_hh >= 18:                                 # previous evening -> asof backward (strict)
        left = london.reset_index()[["caldate"]].sort_values("caldate")
        right = asn.reset_index()[["caldate", "px"]].rename(columns={"px": "asian_px"}).sort_values("caldate")
        merged = pd.merge_asof(left, right, on="caldate", direction="backward", allow_exact_matches=False)
        asian_px = merged.set_index("caldate")["asian_px"]
    else:                                                    # same London-day (e.g. 00:00 UTC)
        asian_px = asn["px"].reindex(london.index)

    # delayed entry bars + exit + extra delay anchors
    def bar_open_at(minutes_after_open: int) -> pd.Series:
        hh = open_hh + (minutes_after_open // 60)
        mm = minutes_after_open % 60
        a = _anchor(bars, hh, mm)
        return a["px"].reindex(london.index)

    entry_px = bar_open_at(delay_bars * 15)                  # delay_bars * 15 min after 07:00
    exit_anchor = _anchor(bars, exit_hh, 0)
    exit_px = exit_anchor["px"].reindex(london.index)
    sp_exit = exit_anchor["sp"].reindex(london.index)

    t = pd.DataFrame(index=london.index)
    t["open_px"] = london["px"]                              # px at 07:00 (entry reference for IC, delay+1)
    t["asian_px"] = asian_px
    t["asian_ret"] = np.log(t["open_px"]) - np.log(t["asian_px"])
    t["entry_px"] = entry_px
    t["exit_px"] = exit_px
    t["fwd_ret"] = np.log(t["exit_px"]) - np.log(t["open_px"])      # IC target: 07:00 -> exit
    t["trade_ret"] = np.log(t["exit_px"]) - np.log(t["entry_px"])   # actual delayed-entry trade leg
    t["sp_entry"] = london["sp"]
    t["sp_exit"] = sp_exit
    t["close_px"] = london["close"]
    t = t.dropna(subset=["asian_ret", "fwd_ret"])
    return t


# ── IC / HAC helpers ──────────────────────────────────────────────────────────
import statsmodels.api as sm
from scipy import stats as _ss


def hac_t(x: np.ndarray, y: np.ndarray, maxlags: int = 6) -> dict:
    """OLS y ~ const + x with Newey-West HAC SE. Returns slope, HAC t, n, R^2, pearson, spearman."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 30 or np.std(x) < 1e-15:
        return dict(n=int(len(x)), slope=0.0, t=0.0, r2=0.0, pearson=0.0, spearman=0.0)
    X = sm.add_constant(x)
    res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    pear = float(np.corrcoef(x, y)[0, 1])
    spear = float(_ss.spearmanr(x, y).statistic)
    return dict(n=int(len(x)), slope=float(res.params[1]), t=float(res.tvalues[1]),
                r2=float(res.rsquared), pearson=pear, spearman=spear)


def zscore_causal(s: pd.Series, lookback: int = 60) -> pd.Series:
    """Lagged rolling z (causal): (s - mean_{t-1}) / std_{t-1}. Uses only info < t."""
    mu = s.shift(1).rolling(lookback, min_periods=20).mean()
    sd = s.shift(1).rolling(lookback, min_periods=20).std(ddof=0)
    return (s - mu) / sd.replace(0, np.nan)


def split_is_oos(s: pd.Series):
    s = s.dropna()
    return s[s.index < OOS_START], s[s.index >= OOS_START]
