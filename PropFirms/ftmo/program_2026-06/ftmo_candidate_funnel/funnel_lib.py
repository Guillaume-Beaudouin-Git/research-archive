"""
funnel_lib.py — reusable infra for the FTMO candidate funnel.

Reuses, verbatim:
  - PropFirms/ftmo_alpha_program/engine/cfd_costs.py     (CFDCostModel — real spread x markup)
  - PropFirms/ftmo_alpha_program/engine/ftmo_first_passage.py (combined_pass_prob_empirical)
  - dsr.py (repo root)                                   (deflated_sharpe_ratio — Bailey-LdP)

Adds: daily-cache loaders, an FTMO-commission layer on top of the spread model, a causal
signal library (price MR, trend/TSMOM, seasonality, event-conditioned, vol/regime, X-sectional),
a close-to-close / open-to-close backtester, inverse-vol sleeve combiner, stats, and the
DSR + first-passage wrappers.

Conventions (HARD RULES):
  * Causal: every signal returns the TARGET POSITION for day t using ONLY info <= t-1
    (price features are .shift(1)-ed; calendar/event positions are known in advance).
  * Net daily return: r_t = pos_t * ret_t - 0.5*rt_cost_t*|d pos_t|  (close-to-close), or
    r_t = pos_t*(close_t/open_t-1) - cost  (open-to-close intraday for gap strategies).
  * OOS hold-out = dates >= 2025-01-01, kept separate from IS.
  * Real costs always (markup x feed spread + FTMO commission + slippage), stress at 2x.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
CACHE = REPO / "research" / "ftmo_candidate_funnel" / "cache"
ENGINE = REPO / "PropFirms" / "ftmo_alpha_program" / "engine"
sys.path.insert(0, str(REPO))            # dsr.py
sys.path.insert(0, str(ENGINE))          # cfd_costs.py, ftmo_first_passage.py

import cfd_costs as _cc                   # noqa: E402
from cfd_costs import CFDCostModel        # noqa: E402
from ftmo_first_passage import combined_pass_prob_empirical  # noqa: E402
from dsr import deflated_sharpe_ratio     # noqa: E402

# ── instrument universe & classes ─────────────────────────────────────────────
FX = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","NZDUSD","EURGBP","EURJPY","AUDJPY"]
JPY = ["USDJPY","EURJPY","AUDJPY"]
METAL = ["XAUUSD"]
INDEX = ["US500","US100","US30","GER40"]
CRYPTO = ["BTCUSD"]
ALL_SYMS = FX + METAL + INDEX + CRYPTO

def sym_class(s: str) -> str:
    if s in FX: return "fx"
    if s in METAL: return "xau"
    if s in INDEX: return "idx"
    if s in CRYPTO: return "btc"
    return "?"

# extend cfd_costs.DECIMALS for the FX crosses it doesn't ship with (point size is unambiguous)
for s in JPY:
    _cc.DECIMALS.setdefault(s, 3)
for s in ["AUDUSD","USDCHF","USDCAD","NZDUSD","EURGBP"]:
    _cc.DECIMALS.setdefault(s, 5)

OOS_START = pd.Timestamp("2025-01-01")
PPY = 252                                 # business-day annualisation

# ── cost layer (real spread x markup + FTMO commission + slippage, RT in fraction) ─
MARKUP = 3.0                              # program-standard conservative retail (L23b)
# extra round-trip cost beyond markup*spread, in bps of notional (FTMO commission + slippage)
ADD_BPS_RT = {"fx": 0.9, "xau": 1.3, "idx": 1.0, "btc": 8.5}
BTC_SPREAD_BPS = 2.3                      # BTC feed spread (no MT5 panel); markup applied

def rt_cost_fraction(sym: str, spread_pts, close, stress: float = 1.0):
    """Round-trip cost as a fraction of notional (array-safe). Reuses CFDCostModel for the
    spread x point x markup / price term, then adds FTMO commission + slippage in bps."""
    cls = sym_class(sym)
    add = ADD_BPS_RT[cls] * 1e-4
    if cls == "btc":
        spread_term = BTC_SPREAD_BPS * 1e-4 * MARKUP
        return (spread_term + add) * stress
    cm = CFDCostModel(sym, markup=MARKUP)
    spread_term = cm.rt_cost_return(spread_pts, close)
    return (np.asarray(spread_term) + add) * stress

# ── data ──────────────────────────────────────────────────────────────────────
_DAILY: dict[str, pd.DataFrame] = {}
_ARTIFACTS: dict[str, int] = {}

def load_daily(sym: str, stress: float = 1.0) -> pd.DataFrame:
    """Date-indexed daily frame with o,h,l,c, ret (c2c), oc_ret (open->close), rt_cost (RT frac)."""
    key = f"{sym}|{stress}"
    if key in _DAILY:
        return _DAILY[key]
    df = pd.read_parquet(CACHE / f"{sym}_daily.parquet").set_index("date").sort_index()
    df = df[df["close"] > 0].copy()
    # session cleanup: keep Mon-Fri only so all instruments share a ~252/yr calendar.
    # non-crypto also drop tiny holiday/Sunday-stub bars (<30 M1 bars). BTC CFD on FTMO is
    # weekend-closed, so business-day close-to-close (Fri->Mon) is the FTMO-realistic daily.
    if sym in CRYPTO:
        df = df[df.index.dayofweek < 5].copy()
    else:
        df = df[(df.index.dayofweek < 5) & (df["n_bars"].fillna(0) >= 30)].copy()
    df = df.sort_index()
    df["ret"] = df["close"].pct_change()        # close-to-close across kept sessions
    df["oc_ret"] = df["close"] / df["open"] - 1.0
    # neutralise splice-seam artifacts (MANIFEST: index 2017/18 feed-level jumps over holidays):
    # null any daily return beyond a generous per-class cap. Real tails (2015 CHF, 2020 crash,
    # 2008) sit inside these caps; only impossible >cap jumps (US100 +141%, US500 +66%) are zeroed.
    cap = {"fx": 0.13, "xau": 0.15, "idx": 0.15, "btc": 0.40}[sym_class(sym)]
    n_art = int((df["ret"].abs() > cap).sum() + (df["oc_ret"].abs() > cap).sum())
    df.loc[df["ret"].abs() > cap, "ret"] = 0.0
    df.loc[df["oc_ret"].abs() > cap, "oc_ret"] = 0.0
    _ARTIFACTS[sym] = n_art
    sp = df["spread_med"].to_numpy() if "spread_med" in df else np.zeros(len(df))
    df["rt_cost"] = rt_cost_fraction(sym, sp, df["close"].to_numpy(), stress=stress)
    _DAILY[key] = df
    return df

def close_panel(syms) -> pd.DataFrame:
    return pd.DataFrame({s: load_daily(s)["close"] for s in syms})

def ret_panel(syms) -> pd.DataFrame:
    return pd.DataFrame({s: load_daily(s)["ret"] for s in syms})

# ── events (calendar 2018-2026 only) ──────────────────────────────────────────
_EVENTS: dict[str, pd.DatetimeIndex] = {}

def load_events() -> dict[str, pd.DatetimeIndex]:
    if _EVENTS:
        return _EVENTS
    f = REPO / "data" / "deep_history_utc" / "calendar" / "economic_calendar_2018_2026.csv"
    df = pd.read_csv(f)
    df["dt"] = pd.to_datetime(df["datetime_utc"])
    df["day"] = df["dt"].dt.normalize()
    def pick(cur, pat):
        m = (df["currency"] == cur) & df["event"].str.contains(pat, case=False, regex=True, na=False)
        return pd.DatetimeIndex(sorted(df.loc[m, "day"].unique()))
    _EVENTS["FOMC"] = pick("USD", r"Fed Interest Rate Decision|FOMC Statement|Federal Funds Rate")
    _EVENTS["NFP"]  = pick("USD", r"Non.?Farm Payrolls")
    _EVENTS["CPI"]  = pick("USD", r"^Inflation Rate YoY$")
    _EVENTS["ECB"]  = pick("EUR", r"ECB Interest Rate Decision")
    return _EVENTS

# ── causal signal helpers (return position Series for day t, info <= t-1) ──────
def _z(close: pd.Series, k: int) -> pd.Series:
    m = close.rolling(k).mean()
    s = close.rolling(k).std(ddof=0)
    return (close - m) / s.replace(0, np.nan)

def sig_zfade(df: pd.DataFrame, k: int = 10, cap: float = 2.0) -> pd.Series:
    """Daily continuous mean-reversion: fade the k-day z-score, capped. Trades ~every day."""
    z = _z(df["close"], k)
    pos = (-z / cap).clip(-1, 1)
    return pos.shift(1)

def sig_rsi2(df: pd.DataFrame, lo: float = 10, hi: float = 90) -> pd.Series:
    """Connors RSI(2) reversion: long deeply oversold, short deeply overbought (two-sided)."""
    d = df["close"].diff()
    up = d.clip(lower=0).rolling(2).mean()
    dn = (-d.clip(upper=0)).rolling(2).mean()
    rs = up / dn.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    pos = pd.Series(0.0, index=df.index)
    pos[rsi < lo] = 1.0
    pos[rsi > hi] = -1.0
    return pos.shift(1)

def sig_gap_fade(df: pd.DataFrame) -> pd.Series:
    """Open->close gap fade: at day-t open, fade the overnight gap vs prior close.
    Causal (gap known at the open before the close). Use with mode='oc'."""
    gap = df["open"] / df["close"].shift(1) - 1.0
    return -np.sign(gap)        # position for day t, decided at t's open (no future info)

def sig_tsmom(df: pd.DataFrame, k: int = 100) -> pd.Series:
    """Time-series momentum: sign of trailing k-day return (two-sided)."""
    mom = df["close"] / df["close"].shift(k) - 1.0
    return np.sign(mom).shift(1)

def sig_above_ma(df: pd.DataFrame, k: int = 200) -> pd.Series:
    """Long-only trend filter: +1 when close > k-day MA (beta-ish baseline)."""
    ma = df["close"].rolling(k).mean()
    return (df["close"] > ma).astype(float).shift(1)

def sig_donchian(df: pd.DataFrame, k: int = 20) -> pd.Series:
    """Donchian breakout: +1 on new k-day high, -1 on new k-day low, hold."""
    hh = df["close"].rolling(k).max()
    ll = df["close"].rolling(k).min()
    raw = pd.Series(np.nan, index=df.index)
    raw[df["close"] >= hh] = 1.0
    raw[df["close"] <= ll] = -1.0
    return raw.ffill().fillna(0.0).shift(1)

def sig_turn_of_month(df: pd.DataFrame, n_before: int = 1, n_after: int = 3,
                      direction: float = 1.0) -> pd.Series:
    """Turn-of-month: position on the last n_before and first n_after trading days of months."""
    idx = df.index
    ym = idx.to_period("M")
    pos = pd.Series(0.0, index=idx)
    # rank within month (1..n) and reverse-rank
    g = pd.Series(idx, index=idx).groupby(ym)
    fwd = g.cumcount()                          # 0-based from month start
    size = g.transform("size").to_numpy()
    bwd = size - 1 - fwd.to_numpy()             # 0-based from month end
    pos[(bwd < n_before) | (fwd.to_numpy() < n_after)] = direction
    return pos                                   # deterministic calendar -> already causal

def sig_weekday(df: pd.DataFrame, weekday: int, direction: float = 1.0) -> pd.Series:
    pos = pd.Series(0.0, index=df.index)
    pos[df.index.dayofweek == weekday] = direction
    return pos

def sig_months(df: pd.DataFrame, months: set[int], direction: float = 1.0) -> pd.Series:
    pos = pd.Series(0.0, index=df.index)
    pos[df.index.month.isin(months)] = direction
    return pos

def _trading_day_before(event_days: pd.DatetimeIndex, idx: pd.DatetimeIndex,
                        offset: int = 1) -> pd.DatetimeIndex:
    """Map each event day to the trading day `offset` sessions before it (in idx)."""
    pos = idx.searchsorted(event_days, side="left") - offset
    pos = pos[(pos >= 0) & (pos < len(idx))]
    return idx[np.unique(pos)]

def sig_pre_event(df: pd.DataFrame, event_days: pd.DatetimeIndex, offset: int = 1,
                  hold: int = 1, direction: float = 1.0) -> pd.Series:
    """Long (default) for `hold` sessions ending `offset` days before each event.
    Event dates are known in advance -> causal. Returns position for day t."""
    idx = df.index
    pos = pd.Series(0.0, index=idx)
    anchors = idx.searchsorted(event_days, side="left") - offset
    for a in anchors:
        for h in range(hold):
            j = a - h
            if 0 <= j < len(idx):
                pos.iloc[j] = direction
    return pos

def vol_regime_long_sig(df: pd.DataFrame, k: int = 20) -> pd.Series:
    """F1: long when trailing k-day realised vol is below its 1y median (calm-drift). Causal."""
    rv = df["ret"].rolling(k).std()
    med = rv.rolling(252, min_periods=60).median()
    return (rv < med).astype(float).shift(1)

def sig_post_event(df: pd.DataFrame, event_days: pd.DatetimeIndex, offset: int = 1,
                   hold: int = 1, direction: float = 1.0) -> pd.Series:
    idx = df.index
    pos = pd.Series(0.0, index=idx)
    anchors = idx.searchsorted(event_days, side="left") + (offset - 1)
    for a in anchors:
        for h in range(hold):
            j = a + h
            if 0 <= j < len(idx):
                pos.iloc[j] = direction
    return pos

# ── backtest ──────────────────────────────────────────────────────────────────
def backtest(sym: str, pos: pd.Series, mode: str = "cc", stress: float = 1.0) -> pd.Series:
    """Net daily return series for one instrument given a causal position series.
    mode='cc': realise close-to-close ret; 'oc': realise open->close (gap intraday)."""
    df = load_daily(sym, stress=stress)
    pos = pos.reindex(df.index).fillna(0.0)
    ret = df["oc_ret"] if mode == "oc" else df["ret"]
    gross = pos * ret
    dpos = pos.diff().fillna(pos)             # first day = entry
    cost = 0.5 * df["rt_cost"] * dpos.abs()
    net = (gross - cost).fillna(0.0)
    net.name = sym
    return net

def combine_inv_vol(legs: dict[str, pd.Series], lookback: int = 60) -> pd.Series:
    """Equal-RISK sleeve: inverse-trailing-vol weight each leg's net-return series, then sum.
    Weights use trailing (shifted) vol -> causal. Aligns on the union of dates (0-fill)."""
    R = pd.DataFrame(legs).sort_index()
    R = R[R.index.dayofweek < 5]                # common business-day calendar
    vol = R.rolling(lookback, min_periods=20).std(ddof=0).shift(1)
    w = (1.0 / vol).replace([np.inf, -np.inf], np.nan)
    w = w.div(w.sum(axis=1), axis=0)          # weights sum to 1 each day
    sleeve = (R.fillna(0.0) * w.fillna(0.0)).sum(axis=1)
    return sleeve.fillna(0.0)

def combine_ew(legs: dict[str, pd.Series]) -> pd.Series:
    """Equal-weight average of leg net-return series (for sparse event/seasonal sleeves where
    inverse-vol is unstable). Aligns on union of dates, 0-fill non-trading days."""
    R = pd.DataFrame(legs).sort_index()
    R = R[R.index.dayofweek < 5]
    return R.mean(axis=1).fillna(0.0)

# ── stats / DSR / first-passage ───────────────────────────────────────────────
def split_is_oos(r: pd.Series):
    r = r.dropna()
    return r[r.index < OOS_START], r[r.index >= OOS_START]

def ann_sharpe(r: pd.Series, ppy: int = PPY) -> float:
    r = r.dropna()
    if len(r) < 5 or r.std(ddof=1) < 1e-12:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * np.sqrt(ppy))

def stats(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 5:
        return dict(n=len(r), sharpe=0.0, skew=0.0, exkurt=0.0, hit=0.0, maxdd=0.0,
                    ann_ret=0.0, ann_vol=0.0, years_pos=0, years_tot=0, by_year={})
    x = r.to_numpy()
    mu, sd = x.mean(), x.std(ddof=1)
    z = (x - mu) / (sd if sd > 1e-12 else 1)
    skew = float((z**3).mean())
    exkurt = float((z**4).mean() - 3.0)
    eq = np.cumsum(x)
    dd = float((np.maximum.accumulate(np.concatenate([[0], eq])) [1:] - eq).max())
    by_year = r.groupby(r.index.year).sum()
    return dict(
        n=len(r), sharpe=ann_sharpe(r), skew=skew, exkurt=exkurt,
        hit=float((x > 0).mean()), maxdd=dd, ann_ret=float(mu*PPY), ann_vol=float(sd*np.sqrt(PPY)),
        years_pos=int((by_year > 0).sum()), years_tot=int(len(by_year)),
        by_year={int(y): float(v) for y, v in by_year.items()},
    )

def dsr_oos(oos_returns: pd.Series, n_trials: int, std_sr_trials: float,
            mean_sr_trials: float = 0.0) -> dict:
    """Deflated Sharpe on the untouched OOS series, deflated at the true trial count."""
    return deflated_sharpe_ratio(oos_returns.dropna().to_numpy(), n_trials=n_trials,
                                 periods_per_year=PPY, mean_sr_trials=mean_sr_trials,
                                 std_sr_trials=std_sr_trials)

def p_funded(r: pd.Series, sigma_d: float = 0.01, n_paths: int = 4000,
             max_days: int = 400) -> dict:
    """FTMO 10k 2-step pass probability (color, not the gate). Scales the net-return series
    to a daily-vol target sigma_d, then runs the static-DD first-passage engine."""
    r = r.dropna()
    sd = r.std(ddof=1)
    if sd < 1e-12:
        return {"p_combined": 0.0, "sigma_d": sigma_d, "lev": 0.0}
    lev = sigma_d / sd
    scaled = (r * lev).to_numpy()
    out = combined_pass_prob_empirical(scaled, n_paths=n_paths, max_days=max_days, seed=7)
    return {"p_combined": float(out["p_combined"]),
            "p1": float(out["p1"]["p_pass"]), "p2": float(out["p2"]["p_pass"]),
            "median_sessions": out.get("median_sessions_to_pass"),
            "sigma_d": sigma_d, "lev": float(lev)}
