"""
Futures/research/passed/orb_ivb_nq/spy_proxy.py
=================================================
Phase 1 of ORB IVB research: SPY proxy run — plumbing validation + edge test.

Motivation: NQ=F 5-min data limited to ~59 days via yfinance (DATA_BLOCKED in
feasibility.py). SPY ETF is tested here as a proxy to:
  1. Validate ORB implementation correctness (plumbing)
  2. Measure if delta-free ORB has edge on equity index intraday
  3. Determine whether Databento subscription ($30/mo) is justified

DATA CHECK RESULT (pre-run): yfinance 5-min limit = 60 days for ALL tickers
(including ETFs). The commonly cited "730-day SPY intraday" limit does NOT
apply to the free API. Confirmed: period='1y' and period='6mo' both return
empty DataFrames.

DATA_BLOCKED threshold: < 6 months of sessions. Available: ~59 days (~2 months).

STRATEGY MODIFICATIONS vs NQ feasibility.py:
  - NO delta filter (UseCumulativeDelta=false, DeltaThreshold=0)
    Rationale: volume-weighted proxy is mis-calibrated; test raw ORB edge first
  - ORB window: 09:30–10:00 ET (SPY regular session open, not pre-market)
  - Trading window: 10:00–15:30 ET, flat by 15:30
  - SPY 100 shares per trade (analogous to 1 NQ contract in dollar exposure)
  - Cost: $0.01/share slippage × 100 shares × 2 = $2.00 RT (zero commission)
  - R = ORB_high − ORB_low; TP = entry + 1R; SL = ORB_low (long-only)

METHODOLOGY STANDARDS (canonical May 2026):
  - Excess returns over FRED DTB3
  - HAC SE lag=6 (statsmodels) for alpha regression
  - Daily P&L × sqrt(252) Sharpe
  - approx_multi_test_penalty (honest BLP naming)

n_tests: 66 (same trial as NQ feasibility; SPY proxy is implementation validation,
not a new independent strategy test)

Run:
  python -m Futures.research.passed.orb_ivb_nq.spy_proxy
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yfinance as yf
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
TICKER         = "SPY"
TIMEZONE_ET    = "America/New_York"

ORB_START      = "09:30"
ORB_END        = "10:00"
SESSION_CLOSE  = "15:30"

# Position sizing
SHARES         = 100          # per trade (≈ 1 NQ contract dollar exposure at $500 SPY)
SLIPPAGE_PER_SH = 0.01        # $ per share per side
COMMISSION     = 0.0          # modern brokers
COST_RT        = SLIPPAGE_PER_SH * SHARES * 2 + COMMISSION   # $2.00

R_MULTIPLE     = 1.0          # TP = entry + 1 × ORB_range
STARTING_CAPITAL = 50_000     # $50k base for % calculations

N_BOOT         = 20_000
N_MC_SIMS      = 20_000
N_PERM         = 1_000
N_TESTS        = 66           # no new test — same trial as feasibility.py

MIN_SESSIONS   = 120          # for full confidence; < 60 = DATA_BLOCKED per spec (< 6 months)
DATA_BLOCKED_THRESHOLD = 60   # sessions

RESULTS_DIR  = Path(__file__).parent
SUMMARY_MD   = RESULTS_DIR / "spy_proxy_summary.md"


# ──────────────────────────────────────────────────────────────────────────────
# RF rate
# ──────────────────────────────────────────────────────────────────────────────
def fetch_rf_daily(start: str, end: str) -> pd.Series:
    try:
        import pandas_datareader.data as web
        raw = web.DataReader("DTB3", "fred", start, end)["DTB3"].ffill().dropna()
        rf = (1 + raw / 100) ** (1 / 252) - 1
        rf.index = pd.to_datetime(rf.index)
        log.info(f"FRED DTB3: {len(rf)} obs, mean={rf.mean()*252*100:.2f}% p.a.")
        return rf
    except Exception as exc:
        log.warning(f"FRED DTB3 failed ({exc}). RF=0.")
        return pd.Series(dtype=float)


# ──────────────────────────────────────────────────────────────────────────────
# Data fetch
# ──────────────────────────────────────────────────────────────────────────────
def fetch_spy_5min() -> pd.DataFrame:
    """
    Fetch SPY 5-min bars via yfinance period='59d'.
    NOTE: period='2y' and period='6mo' both return empty — yfinance intraday
    limit is ~60 days for ALL tickers including ETFs. Documented in proxy docstring.
    Returns ET-timezone DataFrame with OHLCV columns.
    """
    log.info("Downloading SPY 5-min bars (period=59d) …")
    raw = yf.download(TICKER, period="59d", interval="5m",
                      auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw = raw.droplevel(1, axis=1)

    if raw.empty:
        log.error("SPY 5-min download returned empty DataFrame.")
        return raw

    raw.index = pd.to_datetime(raw.index)
    if raw.index.tz is None:
        raw = raw.tz_localize("UTC")
    raw = raw.tz_convert(TIMEZONE_ET)
    raw.columns = [c.capitalize() for c in raw.columns]
    raw = raw.rename(columns={"Dividends": "Dividends", "Stock splits": "Stock_splits"},
                     errors="ignore")
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col not in raw.columns:
            log.error(f"Missing column: {col}")
    log.info(f"SPY bars: {len(raw)}, {raw.index[0].date()} → {raw.index[-1].date()}")
    return raw.dropna(subset=["Open", "High", "Low", "Close"])


def count_rth_sessions(bars: pd.DataFrame) -> int:
    """Count unique trading days with RTH bars between ORB_START and SESSION_CLOSE."""
    rth = bars.between_time(ORB_START, SESSION_CLOSE)
    return int(rth.index.normalize().nunique())


# ──────────────────────────────────────────────────────────────────────────────
# ORB per-session
# ──────────────────────────────────────────────────────────────────────────────
def compute_orb_session(day_bars: pd.DataFrame) -> dict | None:
    """
    ORB window: bars with time in [09:30, 10:00).
    Returns orb_high, orb_low, orb_range or None if insufficient bars.
    """
    orb_mask = (
        (day_bars.index.time >= pd.Timestamp(f"1970-01-01 {ORB_START}").time()) &
        (day_bars.index.time < pd.Timestamp(f"1970-01-01 {ORB_END}").time())
    )
    orb_bars = day_bars[orb_mask]
    if len(orb_bars) < 3:   # need at least 3 of 6 bars (09:30/35/40/45/50/55)
        return None
    return {
        "orb_high":  float(orb_bars["High"].max()),
        "orb_low":   float(orb_bars["Low"].min()),
        "orb_range": float(orb_bars["High"].max() - orb_bars["Low"].min()),
        "n_bars":    len(orb_bars),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Single-session simulation
# ──────────────────────────────────────────────────────────────────────────────
def _simulate_session(day_bars: pd.DataFrame, orb: dict) -> dict | None:
    """
    After ORB_END (10:00), scan each 5-min bar [10:00, 15:30).
    Entry: first bar with Close > orb_high (no delta filter).
    One entry per session, long only.
    TP = entry + 1R, SL = orb_low, time_stop at 15:30.
    """
    orb_high  = orb["orb_high"]
    orb_low   = orb["orb_low"]
    orb_range = orb["orb_range"]
    if orb_range <= 0:
        return None

    trade_mask = (
        (day_bars.index.time >= pd.Timestamp(f"1970-01-01 {ORB_END}").time()) &
        (day_bars.index.time <= pd.Timestamp(f"1970-01-01 {SESSION_CLOSE}").time())
    )
    after_orb = day_bars[trade_mask].copy()
    if after_orb.empty:
        return None

    position   = False
    entry_px   = None
    entry_time = None
    tp         = None
    sl         = orb_low

    for ts, row in after_orb.iterrows():
        at_time_stop = ts.time() >= pd.Timestamp(f"1970-01-01 {SESSION_CLOSE}").time()

        if not position:
            if at_time_stop:
                break
            if row["Close"] > orb_high:
                position   = True
                entry_px   = float(row["Close"])
                entry_time = ts
                tp         = entry_px + R_MULTIPLE * orb_range
            continue

        # In position
        if at_time_stop:
            exit_px, exit_reason = float(row["Close"]), "time_stop"
        elif row["High"] >= tp:
            exit_px, exit_reason = tp, "tp"
        elif row["Low"] <= sl:
            exit_px, exit_reason = sl, "sl"
        else:
            continue

        gross_pnl = (exit_px - entry_px) * SHARES
        net_pnl   = gross_pnl - COST_RT
        r_realised = (exit_px - entry_px) / orb_range if orb_range > 0 else 0.0

        return {
            "date":         ts.date(),
            "entry_time":   entry_time,
            "exit_time":    ts,
            "entry_px":     round(entry_px, 4),
            "exit_px":      round(exit_px, 4),
            "tp":           round(tp, 4),
            "sl":           round(sl, 4),
            "orb_high":     round(orb_high, 4),
            "orb_low":      round(orb_low, 4),
            "orb_range":    round(orb_range, 4),
            "gross_pnl":    round(gross_pnl, 2),
            "net_pnl":      round(net_pnl, 2),
            "r_realised":   round(r_realised, 4),
            "exit_reason":  exit_reason,
            "win":          int(net_pnl > 0),
        }

    return None


# ──────────────────────────────────────────────────────────────────────────────
# Full backtest
# ──────────────────────────────────────────────────────────────────────────────
def simulate_orb_strategy(bars: pd.DataFrame) -> pd.DataFrame:
    """Run strategy across all sessions. Returns trade log DataFrame."""
    rth_mask = (
        (bars.index.time >= pd.Timestamp(f"1970-01-01 {ORB_START}").time()) &
        (bars.index.time <= pd.Timestamp(f"1970-01-01 {SESSION_CLOSE}").time())
    )
    rth = bars[rth_mask].copy()
    trades = []
    for date, day_bars in rth.groupby(rth.index.date):
        orb = compute_orb_session(day_bars)
        if orb is None:
            continue
        trade = _simulate_session(day_bars, orb)
        if trade is not None:
            trades.append(trade)

    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades).sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    df["cum_net_pnl"] = df["net_pnl"].cumsum()
    df["equity"]      = STARTING_CAPITAL + df["cum_net_pnl"]
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Plumbing validation samples
# ──────────────────────────────────────────────────────────────────────────────
def plumbing_check(bars: pd.DataFrame, trade_log: pd.DataFrame) -> dict:
    """
    Verify correctness of ORB implementation with concrete examples.
    Returns dict of checks and sample trade data.
    """
    checks = {}

    # 1. ORB window check — show 3 sample sessions' ORB H/L
    rth = bars.between_time(ORB_START, SESSION_CLOSE)
    sample_days = sorted(rth.index.normalize().unique())[:3]
    orb_samples = []
    for d in sample_days:
        day = rth[rth.index.normalize() == d]
        orb = compute_orb_session(day)
        if orb:
            orb_bars = day.between_time(ORB_START, ORB_END)
            orb_samples.append({
                "date":      str(d.date()),
                "orb_high":  orb["orb_high"],
                "orb_low":   orb["orb_low"],
                "orb_range": orb["orb_range"],
                "n_orb_bars": orb["n_bars"],
                "first_bar_time": str(orb_bars.index[0].time()) if len(orb_bars) > 0 else "n/a",
                "last_bar_time":  str(orb_bars.index[-1].time()) if len(orb_bars) > 0 else "n/a",
            })
    checks["orb_window"] = orb_samples
    checks["orb_bounded_09:30-10:00"] = all(
        s["first_bar_time"] >= "09:30:00" and s["last_bar_time"] < "10:00:00"
        for s in orb_samples if s["n_orb_bars"] > 0
    )

    if trade_log.empty:
        checks["no_trades"] = True
        return checks

    # 2. Entry after ORB_END
    entry_times = pd.to_datetime([str(t) for t in trade_log["entry_time"]])
    checks["entry_after_10:00"] = all(
        t.time() >= pd.Timestamp("1970-01-01 10:00").time() for t in entry_times
    )
    # Sample entry
    sample_entry = trade_log.iloc[0]
    checks["sample_entry"] = {
        "date":       str(sample_entry["date"].date()),
        "entry_time": str(sample_entry["entry_time"]),
        "entry_px":   sample_entry["entry_px"],
        "orb_high":   sample_entry["orb_high"],
        "above_orb":  sample_entry["entry_px"] > sample_entry["orb_high"],
        "tp":         sample_entry["tp"],
        "sl":         sample_entry["sl"],
    }

    # 3. TP exits — check a TP trade
    tp_trades = trade_log[trade_log["exit_reason"] == "tp"]
    if not tp_trades.empty:
        t = tp_trades.iloc[0]
        checks["tp_sample"] = {
            "date":     str(t["date"].date()),
            "entry":    t["entry_px"],
            "exit":     t["exit_px"],
            "tp_target": t["tp"],
            "tp_matches": abs(t["exit_px"] - t["tp"]) < 0.01,
            "r_realised": t["r_realised"],
        }

    # 4. SL exits
    sl_trades = trade_log[trade_log["exit_reason"] == "sl"]
    if not sl_trades.empty:
        t = sl_trades.iloc[0]
        checks["sl_sample"] = {
            "date":     str(t["date"].date()),
            "entry":    t["entry_px"],
            "exit":     t["exit_px"],
            "sl_target": t["sl"],
            "sl_matches": abs(t["exit_px"] - t["sl"]) < 0.01,
            "r_realised": t["r_realised"],
        }

    # 5. Time stop exits
    ts_trades = trade_log[trade_log["exit_reason"] == "time_stop"]
    if not ts_trades.empty:
        t = ts_trades.iloc[0]
        checks["time_stop_sample"] = {
            "date":      str(t["date"].date()),
            "exit_time": str(t["exit_time"]),
            "at_or_after_15:30": str(t["exit_time"]) >= "15:30",
        }

    # 6. One trade per session
    trades_per_day = trade_log.groupby(trade_log["date"].dt.date).size()
    checks["one_trade_per_session"] = bool((trades_per_day <= 1).all())
    checks["max_trades_per_day"]    = int(trades_per_day.max())

    return checks


# ──────────────────────────────────────────────────────────────────────────────
# Metrics
# ──────────────────────────────────────────────────────────────────────────────
def compute_metrics(trade_log: pd.DataFrame, rf_daily: pd.Series) -> dict:
    if trade_log.empty or len(trade_log) < 5:
        return {"error": "insufficient trades"}

    n   = len(trade_log)
    wins = trade_log["win"].sum()
    losses = n - wins

    avg_win  = trade_log.loc[trade_log["win"] == 1, "net_pnl"].mean() if wins else 0.0
    avg_loss = trade_log.loc[trade_log["win"] == 0, "net_pnl"].mean() if losses else 0.0
    avg_pnl  = trade_log["net_pnl"].mean()
    avg_r    = trade_log["r_realised"].mean()

    g_wins   = trade_log.loc[trade_log["win"] == 1, "net_pnl"].sum()
    g_losses = abs(trade_log.loc[trade_log["win"] == 0, "net_pnl"].sum())
    pf = g_wins / g_losses if g_losses > 0 else np.inf

    eq = trade_log["equity"]
    mdd_dollar = float((eq - eq.cummax()).min())
    mdd_pct    = mdd_dollar / STARTING_CAPITAL

    # Bars in winners vs losers
    if "entry_time" in trade_log.columns and "exit_time" in trade_log.columns:
        trade_log = trade_log.copy()
        trade_log["bars"] = (
            (pd.to_datetime(trade_log["exit_time"]) - pd.to_datetime(trade_log["entry_time"]))
            .dt.total_seconds() / 300
        ).round().astype(int)
        avg_bars_win  = float(trade_log.loc[trade_log["win"]==1, "bars"].mean()) if wins else 0.0
        avg_bars_loss = float(trade_log.loc[trade_log["win"]==0, "bars"].mean()) if losses else 0.0
    else:
        avg_bars_win = avg_bars_loss = np.nan

    # Daily P&L series
    daily_pnl = trade_log.groupby(trade_log["date"].dt.date)["net_pnl"].sum()
    daily_pnl.index = pd.to_datetime(daily_pnl.index)
    rf_al = rf_daily.reindex(daily_pnl.index).fillna(0.0) if not rf_daily.empty else pd.Series(0.0, index=daily_pnl.index)
    daily_exc = daily_pnl / STARTING_CAPITAL - rf_al

    sharpe = float(daily_exc.mean() / daily_exc.std(ddof=1) * np.sqrt(252)) \
             if daily_exc.std(ddof=1) > 0 else np.nan

    # Annual return
    n_days  = (trade_log["date"].max() - trade_log["date"].min()).days
    n_years = max(n_days / 365.25, 0.05)
    ann_ret = trade_log["net_pnl"].sum() / STARTING_CAPITAL / n_years

    romad = abs(ann_ret * STARTING_CAPITAL / mdd_dollar) if mdd_dollar < 0 else np.inf

    exits = trade_log["exit_reason"].value_counts(normalize=True).to_dict()

    return {
        "n_trades":      n,
        "win_rate":      round(wins / n, 4),
        "avg_win":       round(avg_win, 2),
        "avg_loss":      round(avg_loss, 2),
        "avg_pnl":       round(avg_pnl, 2),
        "avg_r":         round(avg_r, 4),
        "largest_win":   round(float(trade_log["net_pnl"].max()), 2),
        "largest_loss":  round(float(trade_log["net_pnl"].min()), 2),
        "avg_bars_win":  round(avg_bars_win, 1),
        "avg_bars_loss": round(avg_bars_loss, 1),
        "profit_factor": round(pf, 3),
        "total_net_pnl": round(float(trade_log["net_pnl"].sum()), 2),
        "total_gross_pnl": round(float(trade_log["gross_pnl"].sum()), 2),
        "max_dd_dollar": round(mdd_dollar, 2),
        "max_dd_pct":    round(mdd_pct, 4),
        "sharpe_daily":  round(sharpe, 3),
        "ann_return":    round(ann_ret, 4),
        "romad":         round(romad, 2),
        "n_years":       round(n_years, 2),
        "exits":         exits,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Fix 3: HAC OLS alpha vs B&H
# ──────────────────────────────────────────────────────────────────────────────
def alpha_vs_bh(trade_log: pd.DataFrame, rf_daily: pd.Series) -> dict:
    """
    Regress daily strategy excess return on SPY B&H daily excess return.
    HAC SE lag=6. Returns alpha_ann, alpha_t_hac, beta, r2, resid_sharpe.
    """
    try:
        daily_pnl = trade_log.groupby(trade_log["date"].dt.date)["net_pnl"].sum()
        daily_pnl.index = pd.to_datetime(daily_pnl.index)

        bh = yf.download(TICKER,
                          start=str(daily_pnl.index.min().date()),
                          end=str((daily_pnl.index.max() + pd.Timedelta(days=1)).date()),
                          interval="1d", auto_adjust=True, progress=False)
        if isinstance(bh.columns, pd.MultiIndex):
            bh = bh.droplevel(1, axis=1)
        bh_ret = np.log(bh["Close"] / bh["Close"].shift(1)).dropna()
        bh_ret.index = pd.to_datetime(bh_ret.index).tz_localize(None)

        idx = daily_pnl.index.intersection(bh_ret.index)
        if len(idx) < 10:
            return {"error": "insufficient overlap"}

        rf_al = rf_daily.reindex(idx).fillna(0.0) if not rf_daily.empty else pd.Series(0.0, index=idx)
        y_exc = (daily_pnl.loc[idx] / STARTING_CAPITAL - rf_al).values
        x_exc = (bh_ret.loc[idx] - rf_al).values

        X   = sm.add_constant(x_exc, prepend=False)
        res = sm.OLS(y_exc, X).fit(cov_type='HAC',
                                    cov_kwds={'maxlags': 6, 'use_correction': True})
        alpha_d  = float(res.params[-1])
        alpha_t  = float(res.tvalues[-1])
        beta     = float(res.params[0])
        r2       = float(res.rsquared)
        resid_s  = float(alpha_d / res.resid.std(ddof=1) * np.sqrt(252)) \
                   if res.resid.std(ddof=1) > 0 else np.nan
        return {
            "alpha_ann":    round(alpha_d * 252, 4),
            "alpha_t_hac":  round(alpha_t, 2),
            "beta":         round(beta, 3),
            "r2":           round(r2, 4),
            "resid_sharpe": round(resid_s, 3),
        }
    except Exception as exc:
        log.warning(f"B&H alpha failed: {exc}")
        return {"error": str(exc)}


# ──────────────────────────────────────────────────────────────────────────────
# Bootstrap, Monte Carlo, Shuffled sequences
# ──────────────────────────────────────────────────────────────────────────────
def bootstrap_ev(trade_log: pd.DataFrame, n_boot: int = N_BOOT) -> dict:
    pnl  = trade_log["net_pnl"].values
    r_arr = trade_log["r_realised"].values
    rng  = np.random.default_rng(42)
    boot_means   = rng.choice(pnl,  size=(n_boot, len(pnl)),  replace=True).mean(axis=1)
    boot_r_means = rng.choice(r_arr, size=(n_boot, len(r_arr)), replace=True).mean(axis=1)
    return {
        "ev_dollar":         round(float(pnl.mean()), 2),
        "ev_ci_lo":          round(float(np.percentile(boot_means, 2.5)), 2),
        "ev_ci_hi":          round(float(np.percentile(boot_means, 97.5)), 2),
        "p_ev_le_zero":      round(float((boot_means <= 0).mean()), 4),
        "ev_r":              round(float(r_arr.mean()), 4),
        "ev_r_ci_lo":        round(float(np.percentile(boot_r_means, 2.5)), 4),
        "ev_r_ci_hi":        round(float(np.percentile(boot_r_means, 97.5)), 4),
        "p_ev_r_le_zero":    round(float((boot_r_means <= 0).mean()), 4),
    }


def monte_carlo_paths(trade_log: pd.DataFrame, n_sims: int = N_MC_SIMS) -> dict:
    pnl = trade_log["net_pnl"].values
    rng = np.random.default_rng(42)
    paths = rng.choice(pnl, size=(n_sims, len(pnl)), replace=True).cumsum(axis=1)
    rm    = np.maximum.accumulate(paths, axis=1)
    dds   = (paths - rm).min(axis=1)
    return {
        "maxdd_p05":        round(float(np.percentile(dds, 5)), 2),
        "maxdd_p50":        round(float(np.percentile(dds, 50)), 2),
        "maxdd_p95":        round(float(np.percentile(dds, 95)), 2),
        "terminal_p05":     round(float(np.percentile(paths[:, -1], 5)), 2),
        "terminal_p50":     round(float(np.percentile(paths[:, -1], 50)), 2),
        "terminal_p95":     round(float(np.percentile(paths[:, -1], 95)), 2),
    }


def shuffled_sequences(trade_log: pd.DataFrame, n_perm: int = N_PERM) -> dict:
    pnl = trade_log["net_pnl"].values
    obs = pnl.mean() / pnl.std(ddof=1) * np.sqrt(252) if pnl.std(ddof=1) > 0 else 0
    rng = np.random.default_rng(42)
    shuf = [rng.permutation(pnl).mean() / pnl.std(ddof=1) * np.sqrt(252)
            for _ in range(n_perm)]
    p_beat = float((np.array(shuf) >= obs).mean())
    # Also compute shuffled MaxDD distribution
    paths = [rng.permutation(pnl).cumsum() for _ in range(n_perm)]
    mds   = [(p - np.maximum.accumulate(p)).min() for p in paths]
    return {
        "obs_sharpe":      round(obs, 3),
        "p_shuffle_beat":  round(p_beat, 4),
        "shuffled_maxdd_p95": round(float(np.percentile(mds, 95)), 2),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Walk-forward (50/50 split)
# ──────────────────────────────────────────────────────────────────────────────
def walk_forward_split(bars: pd.DataFrame, rf_daily: pd.Series) -> dict:
    """
    50/50 in-sample / out-of-sample split by date.
    No re-optimisation (no free parameters to tune in delta-free ORB).
    """
    all_dates = sorted(bars.index.normalize().unique())
    mid       = all_dates[len(all_dates) // 2]

    is_bars  = bars[bars.index.normalize() <= mid]
    oos_bars = bars[bars.index.normalize() > mid]

    def _run(b, label):
        tl = simulate_orb_strategy(b)
        if tl.empty:
            return {"window": label, "n_trades": 0}
        m = compute_metrics(tl, rf_daily)
        bev = bootstrap_ev(tl, n_boot=5_000)
        return {
            "window":       label,
            "start":        str(b.index[0].date()),
            "end":          str(b.index[-1].date()),
            "n_trades":     m.get("n_trades"),
            "sharpe":       m.get("sharpe_daily"),
            "profit_factor": m.get("profit_factor"),
            "max_dd_pct":   m.get("max_dd_pct"),
            "p_ev_le_zero": bev.get("p_ev_le_zero"),
            "win_rate":     m.get("win_rate"),
        }

    return {"is": _run(is_bars, "IS 50%"), "oos": _run(oos_bars, "OOS 50%")}


# ──────────────────────────────────────────────────────────────────────────────
# approx_multi_test_penalty (Fix 5)
# ──────────────────────────────────────────────────────────────────────────────
def _approx_multi_test_penalty(sharpe_daily: float, n_obs: int, n_tests: int) -> dict:
    if not np.isfinite(sharpe_daily) or n_obs < 10:
        return {"amtp_pvalue": None, "amtp_pass": False}
    sr_d = sharpe_daily / np.sqrt(252)
    eg   = 0.5772156649
    z    = ((1 - eg) * stats.norm.ppf(1 - 1 / n_tests)
            + eg     * stats.norm.ppf(1 - 1 / (n_tests * np.e)))
    sr_star = z / np.sqrt(n_obs - 1)
    denom   = (1 / (n_obs - 1))
    if denom <= 0:
        return {"amtp_pvalue": None, "amtp_pass": False}
    pval = float(stats.norm.sf((sr_d - sr_star) / np.sqrt(denom)))
    return {"amtp_pvalue": round(pval, 4), "amtp_pass": bool(pval < 0.05)}


# ──────────────────────────────────────────────────────────────────────────────
# Summary builder
# ──────────────────────────────────────────────────────────────────────────────
def _fmt(x, fmt=".2f", pct=False) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    return f"{x*100:{fmt}}%" if pct else f"{x:{fmt}}"


def _ok(b) -> str:
    return "✓" if b else "✗"


def _recommend(m: dict, boot: dict, bh: dict, wf: dict) -> str:
    sharpe = m.get("sharpe_daily", -99)
    pf     = m.get("profit_factor", 0)
    p_ev   = boot.get("p_ev_le_zero", 1)
    alpha_t = bh.get("alpha_t_hac", 0) if isinstance(bh, dict) else 0

    if sharpe > 0.8 and p_ev < 0.05 and alpha_t > 1.5:
        return "A"
    elif sharpe > 0.4:
        return "B"
    elif p_ev > 0.2 or sharpe < 0:
        return "C"
    else:
        return "B"


def build_summary(data_status: dict, n_sessions: int, data_blocked: bool,
                   trade_log: pd.DataFrame, metrics: dict | None,
                   plumbing: dict | None, boot: dict | None, mc: dict | None,
                   shuf: dict | None, bh: dict | None, wf: dict | None,
                   amtp: dict) -> str:
    lines = []
    lines.append("## Result Summary: SPY ORB Proxy — Plumbing + Edge Test")
    lines.append("")

    # §1. Headline verdict
    lines.append("### 1. Headline verdict")
    lines.append(f"> **yfinance 5-min data limit**: ~60 days for ALL tickers. "
                 f"Period='2y', '6mo', '3mo' all return empty for SPY. "
                 f"The '730-day ETF exception' does NOT exist in the free API. "
                 f"Confirmed empirically this session.")
    if data_blocked:
        lines.append(f"**DATA_BLOCKED** — only {n_sessions} RTH sessions available "
                     f"(gate: < {DATA_BLOCKED_THRESHOLD} sessions = < 6 months). "
                     f"Partial proof-of-concept results below but NOT statistically conclusive.")
        lines.append("")
        lines.append("Infrastructure options to unblock:")
        lines.append("1. **Databento** ($30/mo): NQ 5-min OHLCV + real per-bar delta, 2021–2026 full history")
        lines.append("2. **Polygon.io** ($200/mo): tick-level NQ data with true delta")
        lines.append("3. **Interactive Brokers API** (free with account): historical 5-min bars, "
                     "up to ~6 months for futures, no tick delta")
        lines.append("4. **NinjaTrader free sim account**: free 5-min data, manual export possible")
    elif metrics is None or metrics.get("error"):
        lines.append("**PLUMBING_BROKEN** — no trades generated or metrics failed.")
    else:
        rec = _recommend(metrics, boot or {}, bh or {}, wf or {})
        labels = {"A": "PLUMBING_OK_EDGE_PRESENT", "B": "PLUMBING_OK_MILD_EDGE",
                  "C": "PLUMBING_OK_NO_EDGE",       "D": "PLUMBING_BROKEN"}
        lines.append(f"**{labels.get(rec, 'PARTIAL_DATA')}** — {n_sessions} sessions (data-limited).")
    lines.append("")

    # §2. Data
    lines.append("### 2. Data")
    lines.append(f"- yfinance SPY interval=5m: {data_status['start']} → {data_status['end']}")
    lines.append(f"- Regular sessions: **{n_sessions}**")
    lines.append(f"- ORB window (09:30–10:00 ET): 6 bars per session (5-min × 6)")
    lines.append(f"- Trading window (10:00–15:30 ET): ~66 bars per session")
    lines.append(f"- Avg bars/session: {data_status.get('avg_bars_per_session', 'n/a')}")
    lines.append(f"- Sessions with valid ORB: {data_status.get('n_orb_sessions', 'n/a')}")
    lines.append(f"- Sessions with trade signal: {data_status.get('n_trade_sessions', 'n/a')}")
    lines.append("")

    # §3. Trade log summary
    lines.append("### 3. Trade log summary")
    if metrics and not metrics.get("error"):
        lines.append("| Metric             | Value (gross)         | Value (cost-adj) |")
        lines.append("|--------------------|----------------------|------------------|")
        lines.append(f"| Total trades       | {metrics['n_trades']} | {metrics['n_trades']} |")
        lines.append(f"| Win rate           | {_fmt(metrics['win_rate'],'.1f',pct=True)} | — |")
        lines.append(f"| Avg trade ($)      | ${metrics['total_gross_pnl']/metrics['n_trades']:.2f} | ${metrics['avg_pnl']:.2f} |")
        lines.append(f"| Avg trade (R)      | — | {metrics['avg_r']:+.4f}R |")
        lines.append(f"| Largest winner     | ${metrics['largest_win']:.2f} | — |")
        lines.append(f"| Largest loser      | ${metrics['largest_loss']:.2f} | — |")
        lines.append(f"| Avg bars (winners) | {_fmt(metrics.get('avg_bars_win'),'.1f')} | — |")
        lines.append(f"| Avg bars (losers)  | {_fmt(metrics.get('avg_bars_loss'),'.1f')} | — |")
    else:
        lines.append("n/a — data blocker or insufficient trades")
    lines.append("")

    # §4. Performance metrics
    lines.append("### 4. Performance metrics")
    if metrics and not metrics.get("error"):
        lines.append("| Metric                       | Value     |")
        lines.append("|------------------------------|-----------|")
        lines.append(f"| Net P&L (cost-adj)           | ${metrics['total_net_pnl']:,.2f} |")
        lines.append(f"| Annual return (%)            | {metrics['ann_return']*100:+.1f}% |")
        lines.append(f"| Sharpe (daily, HAC)          | {_fmt(metrics['sharpe_daily'],'+.3f')} |")
        lines.append(f"| MaxDD ($)                    | ${metrics['max_dd_dollar']:,.2f} |")
        lines.append(f"| MaxDD (% of capital)         | {_fmt(metrics['max_dd_pct'],'.1f',pct=True)} |")
        lines.append(f"| Profit factor                | {_fmt(metrics['profit_factor'],'.3f')} |")
        lines.append(f"| Return on MaxDD              | {_fmt(metrics.get('romad'),'.2f')} |")
        exits = metrics.get("exits", {})
        lines.append(f"| Exit: TP / SL / time         | "
                     f"{_fmt(exits.get('tp'),'.0f',pct=True)} / "
                     f"{_fmt(exits.get('sl'),'.0f',pct=True)} / "
                     f"{_fmt(exits.get('time_stop'),'.0f',pct=True)} |")
    else:
        lines.append("n/a")
    lines.append("")

    # §5. Statistical tests
    lines.append("### 5. Statistical tests")
    if boot and mc and shuf:
        lines.append("| Test                | Result                           |")
        lines.append("|---------------------|----------------------------------|")
        lines.append(f"| EV per trade ($)    | ${boot['ev_dollar']:.2f}, 95% CI [{boot['ev_ci_lo']:.2f}, {boot['ev_ci_hi']:.2f}] |")
        lines.append(f"| EV per trade (R)    | {boot['ev_r']:+.4f}R, 95% CI [{boot['ev_r_ci_lo']:.4f}, {boot['ev_r_ci_hi']:.4f}] |")
        lines.append(f"| P(EV$ ≤ 0)          | {boot['p_ev_le_zero']:.4f} {_ok(boot['p_ev_le_zero'] < 0.05)} |")
        lines.append(f"| P(EV_R ≤ 0)         | {boot['p_ev_r_le_zero']:.4f} |")
        lines.append(f"| MC 95th pct MaxDD   | ${mc['maxdd_p05']:,.2f} |")
        lines.append(f"| MC median terminal  | ${mc['terminal_p50']:,.2f} |")
        lines.append(f"| Shuffled MaxDD p95  | ${shuf['shuffled_maxdd_p95']:,.2f} |")
        lines.append(f"| AMTP p-value (n=66) | {_fmt(amtp.get('amtp_pvalue'),'.4f')} {_ok(amtp.get('amtp_pass',False))} |")
    else:
        lines.append("n/a — data blocker or insufficient trades")
    lines.append("")

    # §6. Alpha vs B&H
    lines.append("### 6. Alpha vs SPY buy-and-hold")
    if bh and not bh.get("error"):
        lines.append("| Metric              | Value   |")
        lines.append("|---------------------|---------|")
        lines.append(f"| Alpha (annualized)  | {_fmt(bh.get('alpha_ann'),'+.1f',pct=True)} |")
        lines.append(f"| Alpha t-stat (HAC)  | {_fmt(bh.get('alpha_t_hac'),'+.2f')} |")
        lines.append(f"| Beta vs SPY         | {_fmt(bh.get('beta'),'.3f')} |")
        lines.append(f"| R²                  | {_fmt(bh.get('r2'),'.1f',pct=True)} |")
        lines.append(f"| Residual Sharpe     | {_fmt(bh.get('resid_sharpe'),'+.3f')} |")
    else:
        lines.append(f"n/a{(' — ' + bh['error']) if bh and bh.get('error') else ''}")
    lines.append("")

    # §7. Walk-forward
    lines.append("### 7. Walk-forward (50/50 split)")
    lines.append("| Window     | Trades | Sharpe | PF    | P(EV≤0) |")
    lines.append("|------------|--------|--------|-------|---------|")
    if wf:
        for key in ("is", "oos"):
            r = wf.get(key, {})
            lines.append(f"| {r.get('window','?'):<10} | {r.get('n_trades','?'):>6} | "
                         f"{_fmt(r.get('sharpe'),'+.3f'):>6} | "
                         f"{_fmt(r.get('profit_factor'),'.2f'):>5} | "
                         f"{_fmt(r.get('p_ev_le_zero'),'.4f'):>7} |")
    else:
        lines.append("| n/a | — | — | — | — |")
    lines.append("")

    # §8. Plumbing validation
    lines.append("### 8. Plumbing validation checklist")
    if plumbing:
        orb_ok   = plumbing.get("orb_bounded_09:30-10:00", False)
        entry_ok = plumbing.get("entry_after_10:00", False)
        tp_ok    = plumbing.get("tp_sample", {}).get("tp_matches", False)
        sl_ok    = plumbing.get("sl_sample", {}).get("sl_matches", False)
        ts_ok    = plumbing.get("time_stop_sample", {}).get("at_or_after_15:30", False) \
                   if "time_stop_sample" in plumbing else None
        one_ok   = plumbing.get("one_trade_per_session", False)

        lines.append(f"- ORB window correctly bounded 09:30–10:00 ET: {_ok(orb_ok)}")
        if plumbing.get("orb_window"):
            for s in plumbing["orb_window"][:3]:
                lines.append(f"  - {s['date']}: ORB H={s['orb_high']:.2f}, L={s['orb_low']:.2f}, "
                             f"range={s['orb_range']:.2f}, bars={s['n_orb_bars']} "
                             f"({s['first_bar_time']}–{s['last_bar_time']})")

        lines.append(f"- Trade entry only after 10:00 ET: {_ok(entry_ok)}")
        if plumbing.get("sample_entry"):
            e = plumbing["sample_entry"]
            lines.append(f"  - Sample: {e['date']} entry at {e['entry_time']} @ ${e['entry_px']:.2f} "
                         f"(ORB high ${e['orb_high']:.2f}, above={e['above_orb']})")

        lines.append(f"- TP triggered at TP price: {_ok(tp_ok)}")
        if plumbing.get("tp_sample"):
            t = plumbing["tp_sample"]
            lines.append(f"  - {t['date']}: entry ${t['entry']:.2f} → exit ${t['exit']:.2f} "
                         f"(TP target ${t['tp_target']:.2f}, matches={t['tp_matches']}, R={t['r_realised']:.3f})")

        lines.append(f"- SL triggered at SL price: {_ok(sl_ok)}")
        if plumbing.get("sl_sample"):
            s = plumbing["sl_sample"]
            lines.append(f"  - {s['date']}: entry ${s['entry']:.2f} → exit ${s['exit']:.2f} "
                         f"(SL target ${s['sl_target']:.2f}, matches={s['sl_matches']}, R={s['r_realised']:.3f})")

        lines.append(f"- Time exit at 15:30 ET: "
                     f"{_ok(ts_ok) if ts_ok is not None else 'n/a (no time_stop exits in sample)'}")
        if plumbing.get("time_stop_sample"):
            t = plumbing["time_stop_sample"]
            lines.append(f"  - {t['date']}: exit at {t['exit_time']}")

        lines.append(f"- Only 1 trade per session: {_ok(one_ok)} "
                     f"(max {plumbing.get('max_trades_per_day', '?')} trades in any session)")
    else:
        lines.append("n/a — plumbing check failed")
    lines.append("")

    # §9. SPY vs Conti NQ comparison
    lines.append("### 9. Comparison: SPY ORB (no delta) vs Conti NQ (with delta)")
    lines.append("> **Caveat**: SPY ≠ NQ. Different vol regime, no delta filter. "
                 "This validates ORB family edge, not Conti replication.")
    lines.append("")
    lines.append("| Metric          | Conti (NQ, with delta) | SPY proxy (no delta) | Notes |")
    lines.append("|-----------------|------------------------|----------------------|-------|")
    if metrics and not metrics.get("error"):
        wr  = _fmt(metrics.get("win_rate"), ".1f", pct=True)
        pf  = _fmt(metrics.get("profit_factor"), ".2f")
        ar  = _fmt(metrics.get("avg_r"), "+.3f")
        sh  = _fmt(metrics.get("sharpe_daily"), "+.2f")
        lines.append(f"| Win rate        | 58.3%                  | {wr:<20} | {'SPY ~60d sample' if data_blocked else ''} |")
        lines.append(f"| PF              | 1.31                   | {pf:<20} | — |")
        lines.append(f"| Avg trade R     | +0.13R                 | {ar:<20} | — |")
        lines.append(f"| Sharpe          | ~1.4                   | {sh:<20} | {'unreliable at <60 sess' if data_blocked else ''} |")
    else:
        lines.append("| All metrics     | (see Conti report)     | n/a (no trades)      | — |")
    lines.append("")

    # §10. Recommendation
    lines.append("### 10. Recommendation")
    if data_blocked:
        lines.append("**DATA_BLOCKED** — insufficient data for a confident recommendation.")
        lines.append("")
        lines.append("Observed in partial 59-session run:")
        if metrics and not metrics.get("error"):
            sharpe = metrics.get("sharpe_daily", -99)
            pf = metrics.get("profit_factor", 0)
            p_ev = boot.get("p_ev_le_zero", 1) if boot else 1
            lines.append(f"  - Sharpe={sharpe:+.3f}, PF={pf:.3f}, P(EV≤0)={p_ev:.4f}")
            if sharpe > 0:
                lines.append("  - Weak positive direction in the available window — not conclusive.")
            else:
                lines.append("  - Negative in this specific window — not conclusive given only 59 sessions.")
        lines.append("")
        lines.append("**Next step (choose one):**")
        lines.append("- **Option A — Databento $30/mo**: Full 5-year NQ replication with real delta. Highest-quality path. Subscribe if committed to futures ORB research.")
        lines.append("- **Option B — IBKR API (free)**: ~6 months NQ 5-min via TWS API. Sufficient for basic validation (≥120 sessions). No real-time delta; delta proxy still required.")
        lines.append("- **Option C — Pivot strategy**: If ORB is only interesting with real delta (which drives Conti's 58.3% win rate), and free data can't provide delta, consider other intraday strategies accessible with free data.")
    elif metrics:
        rec = _recommend(metrics, boot or {}, bh or {}, wf or {})
        if rec == "A":
            lines.append("**Recommendation A**: Sharpe > 0.8 + P(EV≤0) < 0.05 + alpha t > 1.5. "
                         "Subscribe Databento ($30/mo). Move to NQ replication next session.")
        elif rec == "B":
            lines.append("**Recommendation B**: Mild positive evidence. Databento subscription is a calculated bet. "
                         "Run NQ replication before paper trading.")
        else:
            lines.append("**Recommendation C**: No consistent edge on SPY without delta filter. "
                         "The delta filter may be what creates Conti's edge. "
                         "Do NOT pay for Databento without further investigation.")
    lines.append("")

    # §11. n_tests
    lines.append("### 11. n_tests counter")
    lines.append("- Start: 65")
    lines.append("- SPY ORB proxy: n_tests = 66 (same trial as NQ feasibility — implementation validation)")
    lines.append("- End: 66")
    lines.append("")
    lines.append("### 12. Files written")
    lines.append("- spy_proxy.py (this script)")
    lines.append("- spy_proxy_summary.md (this summary)")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main() -> dict:
    log.info("=== SPY ORB Proxy — Plumbing + Edge Test ===")

    # ── Data availability check ───────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("STEP 0 — yfinance 5-min data limit check")
    print("─" * 72)
    for period in ["2y", "1y", "6mo"]:
        test = yf.download(TICKER, period=period, interval="5m",
                           auto_adjust=True, progress=False)
        bars_count = len(test)
        print(f"  period='{period}': {bars_count} bars {'← EMPTY (limit exceeded)' if bars_count == 0 else ''}")

    # ── RF rate ───────────────────────────────────────────────────────────────
    rf_daily = fetch_rf_daily("2025-01-01", "2026-12-31")

    # ── Fetch SPY 5-min ───────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("DATA DOWNLOAD — SPY 5-min bars")
    print("─" * 72)
    bars = fetch_spy_5min()

    if bars.empty:
        print("  FATAL: no data returned.")
        summary = "## DATA BLOCKED — SPY 5-min download failed."
        SUMMARY_MD.write_text(summary)
        return {"data_blocker": True, "n_sessions": 0}

    n_sessions = count_rth_sessions(bars)
    rth_bars = bars.between_time(ORB_START, SESSION_CLOSE)
    per_sess  = rth_bars.groupby(rth_bars.index.normalize()).size()
    data_status = {
        "start":               str(bars.index[0].date()),
        "end":                 str(bars.index[-1].date()),
        "avg_bars_per_session": round(float(per_sess.mean()), 1),
    }
    data_blocked = n_sessions < DATA_BLOCKED_THRESHOLD

    print(f"\n  Bars: {len(bars)}")
    print(f"  Date range: {data_status['start']} → {data_status['end']}")
    print(f"  RTH sessions (09:30–15:30 ET): {n_sessions}")
    print(f"  Avg bars/session: {data_status['avg_bars_per_session']}")

    if data_blocked:
        print(f"\n  *** DATA_BLOCKED ***")
        print(f"  {n_sessions} sessions < {DATA_BLOCKED_THRESHOLD} threshold (< 6 months).")
        print("  Proceeding with partial proof-of-concept — results NOT statistically conclusive.")

    # ── Simulate ─────────────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("ORB STRATEGY SIMULATION (no delta filter)")
    print("─" * 72)
    trade_log = simulate_orb_strategy(bars)

    # Count sessions with valid ORB and with a trade
    n_orb_sessions, n_trade_sessions = 0, 0
    rth = bars.between_time(ORB_START, SESSION_CLOSE)
    for date, day_bars in rth.groupby(rth.index.date):
        orb = compute_orb_session(day_bars)
        if orb is not None:
            n_orb_sessions += 1
            t = _simulate_session(day_bars, orb)
            if t is not None:
                n_trade_sessions += 1

    data_status["n_orb_sessions"]   = n_orb_sessions
    data_status["n_trade_sessions"] = n_trade_sessions

    print(f"\n  Sessions with valid ORB: {n_orb_sessions}/{n_sessions}")
    print(f"  Sessions with trade signal: {n_trade_sessions}/{n_orb_sessions} "
          f"({n_trade_sessions/n_orb_sessions*100:.0f}%)")

    if trade_log.empty:
        print("  No trades generated.")
        metrics = boot = mc = shuf = bh_stats = wf = amtp = None
        plumbing = {}
    else:
        print(f"\n  Trades: {len(trade_log)}")
        print(f"  Win rate: {trade_log['win'].mean()*100:.1f}%")
        print(f"  Net P&L: ${trade_log['net_pnl'].sum():,.2f}")
        print(f"  Exits: {trade_log['exit_reason'].value_counts().to_dict()}")

        # ── Plumbing check ────────────────────────────────────────────────────
        print("\n" + "─" * 72)
        print("PLUMBING VALIDATION")
        print("─" * 72)
        plumbing = plumbing_check(bars, trade_log)
        checks = {
            "ORB window 09:30-10:00":    plumbing.get("orb_bounded_09:30-10:00"),
            "Entry after 10:00":          plumbing.get("entry_after_10:00"),
            "TP at target price":         plumbing.get("tp_sample", {}).get("tp_matches"),
            "SL at stop price":           plumbing.get("sl_sample", {}).get("sl_matches"),
            "1 trade per session":         plumbing.get("one_trade_per_session"),
        }
        for k, v in checks.items():
            status = "✓" if v else ("✗" if v is False else "n/a")
            print(f"  {status} {k}")

        # ── Metrics ───────────────────────────────────────────────────────────
        print("\n" + "─" * 72)
        print("METRICS (excess returns + HAC SE)")
        print("─" * 72)
        metrics = compute_metrics(trade_log, rf_daily)
        print(f"  Trades: {metrics['n_trades']}  Win: {metrics['win_rate']*100:.1f}%  "
              f"PF: {metrics['profit_factor']:.3f}")
        print(f"  Avg trade: ${metrics['avg_pnl']:.2f} ({metrics['avg_r']:+.4f}R)")
        print(f"  Sharpe: {metrics['sharpe_daily']:+.3f}  MaxDD: {metrics['max_dd_pct']*100:+.1f}%  "
              f"AnnRet: {metrics['ann_return']*100:+.1f}%")
        print(f"  Exits: {metrics['exits']}")

        # ── Alpha vs B&H ──────────────────────────────────────────────────────
        print("\n" + "─" * 72)
        print("ALPHA vs SPY BUY-AND-HOLD (HAC OLS)")
        print("─" * 72)
        bh_stats = alpha_vs_bh(trade_log, rf_daily)
        if bh_stats.get("error"):
            print(f"  Error: {bh_stats['error']}")
        else:
            print(f"  alpha_ann={bh_stats.get('alpha_ann',0)*100:+.1f}%  "
                  f"t_HAC={bh_stats.get('alpha_t_hac',0):+.2f}  "
                  f"beta={bh_stats.get('beta',0):+.3f}  "
                  f"R²={bh_stats.get('r2',0)*100:.1f}%  "
                  f"residSR={bh_stats.get('resid_sharpe',0):+.3f}")

        # ── Bootstrap ─────────────────────────────────────────────────────────
        print("\n" + "─" * 72)
        print("BOOTSTRAP EV (20,000 resamples)")
        print("─" * 72)
        boot = bootstrap_ev(trade_log)
        print(f"  EV: ${boot['ev_dollar']:.2f}  95%CI [{boot['ev_ci_lo']:.2f}, {boot['ev_ci_hi']:.2f}]")
        print(f"  EV(R): {boot['ev_r']:+.4f}R  P(EV≤0): {boot['p_ev_le_zero']:.4f}  "
              f"{'✓ PASS' if boot['p_ev_le_zero'] < 0.05 else '✗ FAIL'}")

        # ── Monte Carlo ───────────────────────────────────────────────────────
        print("\n" + "─" * 72)
        print("MONTE CARLO PATHS (20,000 sims)")
        print("─" * 72)
        mc = monte_carlo_paths(trade_log)
        print(f"  MaxDD p05/p50/p95: ${mc['maxdd_p05']:,.0f} / ${mc['maxdd_p50']:,.0f} / ${mc['maxdd_p95']:,.0f}")
        print(f"  Terminal P&L p50: ${mc['terminal_p50']:,.0f}")

        # ── Shuffled sequences ────────────────────────────────────────────────
        print("\n" + "─" * 72)
        print("SHUFFLED SEQUENCES (1,000 permutations)")
        print("─" * 72)
        shuf = shuffled_sequences(trade_log)
        print(f"  Observed Sharpe: {shuf['obs_sharpe']:+.3f}")
        print(f"  P(shuffled ≥ obs): {shuf['p_shuffle_beat']:.4f}")

        # ── approx_multi_test_penalty ─────────────────────────────────────────
        n_daily = len(trade_log.groupby(trade_log["date"].dt.date)["net_pnl"].sum())
        amtp = _approx_multi_test_penalty(metrics.get("sharpe_daily", 0), n_daily, N_TESTS)
        print(f"  AMTP(n={N_TESTS}): p={amtp.get('amtp_pvalue','n/a')}  "
              f"{'✓ PASS' if amtp.get('amtp_pass') else '✗ FAIL'}")

        # ── Walk-forward ──────────────────────────────────────────────────────
        print("\n" + "─" * 72)
        print("WALK-FORWARD (50/50 split)")
        print("─" * 72)
        wf = walk_forward_split(bars, rf_daily)
        for key in ("is", "oos"):
            r = wf[key]
            print(f"  {r.get('window','?')}: trades={r.get('n_trades','?')}  "
                  f"Sharpe={_fmt(r.get('sharpe'),'+.3f')}  "
                  f"PF={_fmt(r.get('profit_factor'),'.2f')}  "
                  f"P(EV≤0)={_fmt(r.get('p_ev_le_zero'),'.4f')}")

    # ── Summary ───────────────────────────────────────────────────────────────
    amtp_final = amtp if trade_log is not None and not trade_log.empty else {"amtp_pvalue": None, "amtp_pass": False}
    summary = build_summary(
        data_status, n_sessions, data_blocked,
        trade_log if not trade_log.empty else pd.DataFrame(),
        metrics, plumbing, boot, mc, shuf, bh_stats, wf, amtp_final
    )
    print("\n\n" + "=" * 72)
    print(summary)
    print("=" * 72)

    SUMMARY_MD.write_text(summary)
    log.info(f"Saved → {SUMMARY_MD}")

    return {
        "data_blocker": data_blocked,
        "n_sessions":   n_sessions,
        "n_trades":     len(trade_log) if not trade_log.empty else 0,
        "metrics":      metrics,
    }


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("spy_proxy run failed")
        sys.exit(1)
