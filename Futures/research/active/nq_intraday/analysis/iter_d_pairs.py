"""
iter_d_pairs.py — Strategy D: ES/NQ Intraday Pairs Trading
===========================================================
Mean reversion on the log(NQ/ES) spread using hourly bars.

Data constraint note: No 1-min ES data available for 2022-2025.
Using yfinance ES=F + NQ=F hourly data (Dec 2023 → present, ~29 months RTH).
Strategy C overlap: Dec 2023 → Dec 2025 (~24 months) for correlation/portfolio.

Strategy spec:
  Signal:    Rolling z-score of log(NQ/ES) spread (beta-adjusted via OLS)
  Entry:     |z| > entry_z threshold (end-of-bar signal, entry next bar open)
  Direction: z>0 → SHORT NQ + LONG ES  (spread too wide)
             z<0 → LONG NQ  + SHORT ES (spread too narrow)
  Exit:      z crosses zero | |z| > stop_z | 12:00 ET time stop
  Legs:      1 MNQ + 1 MES per trade (simplified dollar-neutral approximation)
  Costs:     $4.30 RT total ($2.15 MNQ + $2.15 MES)
  Data:      6 RTH bars/day (10:00-15:00 ET labels, end-of-hour bars)

n_tests: 147 → 152 (5 new variants iter_D1–D5)

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.analysis.iter_d_pairs
"""
from __future__ import annotations

import datetime
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.tsa.stattools as ts

sys.path.insert(0, str(Path(__file__).parents[5]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, POINT_VALUE, COST_RT, append_result,
)
from Futures.research.active.nq_intraday.iter_05 import (
    build_opening_features, signals_from_features,
)
from Futures.research.active.nq_intraday.analysis.propfirm_compat_v2 import (
    _stationary_block_paths, _simulate_tradeify_eval,
    build_daily_pnl, scale_pnl, TV_TRAILING_DD, TV_EVAL_TARGET,
    TV_INITIAL, MC_PATHS, MC_SEED, TV_SIZING,
    _simulate_tradeify_prelock, _simulate_tradeify_postlock,
    TV_LOCK_BALANCE, TV_LOCKED_FLOOR,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

N_TESTS_START = 147
EVAL_DAYS_90  = 90

# Micro contract specs
MNQ_PV   = 2.0    # $2 per NQ point
MES_PV   = 5.0    # $5 per ES point (MES = 1/10 of full ES at $50/pt)
PAIR_COST_RT = 4.30  # $2.15 MNQ + $2.15 MES

# Gate thresholds (Strategy D solo)
GATE_SHARPE   = 1.0
GATE_WF       = 60.0
GATE_PF       = 1.3
GATE_MDD      = -0.10
GATE_WR       = 0.50
GATE_TPD      = 1.0   # trades per day
GATE_CORR     = 0.30  # max corr with Strategy C
GATE_AMTP     = 0.05

# RTH window
RTH_START = datetime.time(9, 30)   # bar filter: include bars from 10:00 (end label)
RTH_END   = datetime.time(15, 30)  # bar filter: include bars up to 15:00 (end label)
TIME_STOP = datetime.time(12, 0)   # time stop: exit at or after 12:00 bar open

# 5 combos (lookback in hours, entry_z, stop_z)
VARIANTS = [
    {"name": "iter_D1", "lookback_h": 12, "entry_z": 1.5, "stop_z": 3.0,
     "rationale": "12h lookback (~2 RTH days), aggressive entry 1.5σ"},
    {"name": "iter_D2", "lookback_h": 12, "entry_z": 2.0, "stop_z": 3.5,
     "rationale": "12h lookback, cautious entry 2.0σ"},
    {"name": "iter_D3", "lookback_h": 24, "entry_z": 1.5, "stop_z": 3.0,
     "rationale": "24h lookback (~4 RTH days), aggressive entry 1.5σ"},
    {"name": "iter_D4", "lookback_h": 24, "entry_z": 2.0, "stop_z": 3.5,
     "rationale": "24h lookback, cautious entry 2.0σ"},
    {"name": "iter_D5", "lookback_h": 6,  "entry_z": 2.0, "stop_z": 3.0,
     "rationale": "6h lookback (~1 RTH day), medium threshold — intraday reversion"},
]


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_pairs_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fetch ES=F and NQ=F hourly from yfinance (730d = ~29 months available).
    Returns (es_rth, nq_rth): RTH-filtered DataFrames, ET timezone, aligned.
    yfinance labels hourly bars at the END of the period.
    RTH filter: keep bars labeled 10:00-15:00 ET (= last 6 RTH hours).
    """
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo
    import yfinance as yf

    ET = ZoneInfo("America/New_York")

    def _fetch(ticker: str) -> pd.DataFrame:
        df = yf.download(ticker, period="730d", interval="1h",
                         progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() for c in df.columns]
        df.index = df.index.tz_convert("America/New_York")
        # yfinance hourly bars: bar labeled 10:00 = 9:00-10:00 period
        # RTH window 9:30-16:00: bars at 10:00,11:00,12:00,13:00,14:00,15:00
        rth = df[(df.index.time >= datetime.time(10, 0)) &
                 (df.index.time <= datetime.time(15, 0))]
        return rth[["open", "high", "low", "close", "volume"]].copy()

    es = _fetch("ES=F")
    nq = _fetch("NQ=F")

    # Align on common timestamps
    common = es.index.intersection(nq.index)
    return es.loc[common], nq.loc[common]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Cointegration test
# ─────────────────────────────────────────────────────────────────────────────

def step1_cointegration(es: pd.DataFrame, nq: pd.DataFrame) -> dict:
    print("\n" + "═" * 70)
    print("STEP 1 — Engle-Granger Cointegration Test (ES/NQ log-spread)")
    print("═" * 70)

    log_es = np.log(es["close"])
    log_nq = np.log(nq["close"])

    # Full sample OLS: log(NQ) = α + β × log(ES) + ε
    X = sm.add_constant(log_es)
    ols = sm.OLS(log_nq, X).fit()
    alpha = float(ols.params.iloc[0])
    beta  = float(ols.params.iloc[1])
    residuals = log_nq - (alpha + beta * log_es)

    print(f"\n  OLS: log(NQ) = {alpha:.4f} + {beta:.4f} × log(ES)")
    print(f"  R² = {ols.rsquared:.4f}")

    # Engle-Granger ADF on residuals
    eg_result = ts.adfuller(residuals.dropna(), autolag='AIC', regression='c')
    eg_pval   = float(eg_result[1])
    eg_stat   = float(eg_result[0])
    eg_crit   = eg_result[4]

    print(f"\n  Engle-Granger ADF on residuals:")
    print(f"    ADF stat  = {eg_stat:.4f}")
    print(f"    p-value   = {eg_pval:.4f}")
    print(f"    Crit 1%   = {eg_crit['1%']:.4f}")
    print(f"    Crit 5%   = {eg_crit['5%']:.4f}")

    cointegrated = eg_pval < 0.05
    print(f"\n  → Cointegration: {'CONFIRMED (p<0.05)' if cointegrated else 'REJECTED (p>=0.05)'}")

    # Half-life of mean reversion
    res_lag  = residuals.shift(1)
    delta    = residuals - res_lag
    mask     = res_lag.notna() & delta.notna()
    X_hl     = sm.add_constant(res_lag[mask])
    ols_hl   = sm.OLS(delta[mask], X_hl).fit()
    phi      = float(ols_hl.params.iloc[1])   # AR coefficient on lagged residual
    if phi < 0 and phi > -1:
        half_life = -np.log(2) / np.log(1 + phi)
        print(f"\n  Half-life of mean reversion: {half_life:.1f} hours "
              f"(≈{half_life/6:.1f} RTH days)")
    else:
        half_life = np.nan
        print(f"\n  Half-life: non-stationary (φ={phi:.4f})")

    # Regime stability: split sample
    mid_date = residuals.index[len(residuals)//2]
    for label, mask_r in [("Early half", residuals.index < mid_date),
                           ("Late half",  residuals.index >= mid_date)]:
        r_sub  = residuals[mask_r].dropna()
        eg_sub = ts.adfuller(r_sub, autolag='AIC', regression='c')
        print(f"\n  {label} ({r_sub.index[0].date()} → {r_sub.index[-1].date()}):")
        print(f"    ADF p={eg_sub[1]:.4f}  "
              f"{'✓ cointegrated' if eg_sub[1]<0.05 else '✗ not cointegrated'}")

    # Spread stats
    spread_std    = float(residuals.std())
    spread_mean   = float(residuals.mean())
    spread_kurt   = float(residuals.kurtosis())
    print(f"\n  Spread (log residual): mean={spread_mean:.6f}, std={spread_std:.6f}, "
          f"kurt={spread_kurt:.2f}")
    print(f"  In NQ-point equiv: 1σ ≈ {np.exp(spread_std)-1:.2%} "
          f"→ ~{(np.exp(spread_std)-1)*nq['close'].mean():.0f} pts")

    return {
        "cointegrated": cointegrated,
        "eg_pval":      eg_pval,
        "eg_stat":      eg_stat,
        "beta":         beta,
        "alpha":        alpha,
        "residuals":    residuals,
        "half_life_h":  half_life,
        "spread_std":   spread_std,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2/3 — Pairs backtest engine
# ─────────────────────────────────────────────────────────────────────────────

def build_z_score(
    es: pd.DataFrame,
    nq: pd.DataFrame,
    beta:     float,
    alpha:    float,
    lookback: int,
) -> pd.Series:
    """Rolling z-score of log(NQ) - alpha - beta × log(ES)."""
    spread = np.log(nq["close"]) - alpha - beta * np.log(es["close"])
    mu     = spread.rolling(lookback, min_periods=lookback//2).mean()
    sigma  = spread.rolling(lookback, min_periods=lookback//2).std()
    z      = (spread - mu) / sigma.replace(0, np.nan)
    return z


def run_pairs_backtest(
    es:       pd.DataFrame,
    nq:       pd.DataFrame,
    z:        pd.Series,
    beta:     float,
    entry_z:  float,
    stop_z:   float,
) -> pd.DataFrame:
    """
    Bar-by-bar pairs backtest.
    Signal at bar close → entry at NEXT bar open.
    Exit at first: z crosses zero | |z| > stop_z | time stop (12:00 label).

    Returns trade_log DataFrame.
    """
    trades = []
    in_trade   = False
    direction  = 0    # +1 = long NQ/short ES, -1 = short NQ/long ES
    entry_nq   = entry_es = entry_ts = None
    bars       = list(zip(z.index, z.values, nq["open"].values,
                          nq["close"].values, es["open"].values, es["close"].values))

    i = 0
    while i < len(bars):
        ts_bar, z_val, nq_o, nq_c, es_o, es_c = bars[i]

        if not in_trade:
            # Check for entry signal: signal fires at bar close, enter next bar
            if i + 1 < len(bars) and np.isfinite(z_val):
                # Check same-day continuity (no overnight entry)
                next_ts = bars[i + 1][0]
                if ts_bar.date() == next_ts.date() and next_ts.time() > TIME_STOP:
                    # No room for a full trade today (next bar is already past stop)
                    i += 1
                    continue

                if abs(z_val) >= entry_z:
                    direction  = -1 if z_val > 0 else +1
                    # Enter next bar at open
                    i += 1
                    if i >= len(bars):
                        break
                    ts_e, z_e, nq_o_e, nq_c_e, es_o_e, es_c_e = bars[i]
                    # Don't enter after time stop on same day
                    if ts_e.time() > TIME_STOP:
                        i += 1
                        continue
                    entry_ts  = ts_e
                    entry_nq  = nq_o_e
                    entry_es  = es_o_e
                    entry_z_val = z_e
                    in_trade  = True
        else:
            # In trade — check exit conditions
            exit_now   = False
            exit_reason = ""
            exit_nq    = nq_c
            exit_es    = es_c

            # Time stop: exit at OPEN of bar >= 12:00
            if ts_bar.time() >= TIME_STOP:
                exit_nq    = nq_o
                exit_es    = es_o
                exit_now   = True
                exit_reason = "time"

            # Stop loss: |z| >= stop_z
            elif np.isfinite(z_val) and abs(z_val) >= stop_z:
                exit_nq    = nq_c
                exit_es    = es_c
                exit_now   = True
                exit_reason = "sl"

            # Mean reversion: z crossed zero (changed sign relative to direction)
            elif np.isfinite(z_val) and direction * z_val <= 0:
                exit_nq    = nq_c
                exit_es    = es_c
                exit_now   = True
                exit_reason = "mr"  # mean-reversion exit

            # End of day without time stop — force close at last bar
            elif i + 1 < len(bars) and bars[i + 1][0].date() != ts_bar.date():
                exit_nq    = nq_c
                exit_es    = es_c
                exit_now   = True
                exit_reason = "eod"

            if exit_now:
                # Compute P&L
                # direction: +1 = long NQ, short ES; -1 = short NQ, long ES
                pnl_nq = direction * (exit_nq - entry_nq) * MNQ_PV
                pnl_es = -direction * (exit_es - entry_es) * MES_PV
                pnl    = pnl_nq + pnl_es - PAIR_COST_RT

                trades.append({
                    "entry_ts":    entry_ts,
                    "exit_ts":     ts_bar,
                    "direction":   direction,
                    "entry_nq":    entry_nq,
                    "entry_es":    entry_es,
                    "exit_nq":     exit_nq,
                    "exit_es":     exit_es,
                    "entry_z":     entry_z_val if 'entry_z_val' in dir() else np.nan,
                    "exit_z":      z_val,
                    "exit_reason": exit_reason,
                    "pnl_nq":      round(pnl_nq, 2),
                    "pnl_es":      round(pnl_es, 2),
                    "pnl_usd":     round(pnl, 2),
                })
                in_trade  = False
                direction = 0

        i += 1

    return pd.DataFrame(trades)


def pairs_metrics(tl: pd.DataFrame) -> dict:
    """Compute metrics from pairs trade log."""
    if tl.empty or len(tl) < 5:
        return {"n_trades": len(tl), "verdict": "INSUFFICIENT"}

    tl = tl.copy()
    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()

    n        = len(tl)
    winners  = tl[tl["pnl_usd"] > 0]
    losers   = tl[tl["pnl_usd"] <= 0]
    win_rate = len(winners) / n
    avg_w    = winners["pnl_usd"].mean() if len(winners) > 0 else 0
    avg_l    = losers["pnl_usd"].mean()  if len(losers)  > 0 else 0
    gross_w  = winners["pnl_usd"].sum()
    gross_l  = abs(losers["pnl_usd"].sum())
    pf       = gross_w / gross_l if gross_l > 0 else np.nan

    # Date range → trades per day
    all_dates = pd.bdate_range(tl["date"].min(), tl["date"].max())
    n_days    = len(all_dates)
    tpd       = n / n_days if n_days > 0 else 0

    # Daily P&L → Sharpe HAC
    daily = tl.groupby("date")["pnl_usd"].sum()
    daily = daily.reindex(pd.DatetimeIndex(all_dates).normalize(), fill_value=0.0)
    sh    = _sharpe_hac(daily)

    # Drawdown
    cum  = daily.cumsum()
    dd   = (cum - cum.cummax()) / max(cum.cummax().max(), 1.0)
    mdd  = float(dd.min())

    # P(EV≤0) bootstrap
    pnls = tl["pnl_usd"].values
    rng  = np.random.default_rng(42)
    boot = np.array([rng.choice(pnls, size=len(pnls), replace=True).mean()
                     for _ in range(5000)])
    p_ev = float((boot <= 0).mean())

    # Exit reason breakdown
    exit_counts = tl["exit_reason"].value_counts().to_dict()

    return {
        "n_trades":        int(n),
        "win_rate":        round(win_rate, 4),
        "avg_trade_usd":   round(float(tl["pnl_usd"].mean()), 2),
        "avg_winner_usd":  round(float(avg_w), 2),
        "avg_loser_usd":   round(float(avg_l), 2),
        "profit_factor":   round(float(pf), 4) if np.isfinite(pf) else None,
        "sharpe_daily_hac":round(float(sh), 4) if np.isfinite(sh) else None,
        "max_dd_pct":      round(float(mdd), 4),
        "total_pnl_usd":   round(float(tl["pnl_usd"].sum()), 2),
        "trades_per_day":  round(float(tpd), 3),
        "exit_mr_pct":     round(exit_counts.get("mr", 0) / n, 3),
        "exit_sl_pct":     round(exit_counts.get("sl", 0) / n, 3),
        "exit_time_pct":   round((exit_counts.get("time", 0) + exit_counts.get("eod", 0)) / n, 3),
        "p_ev_zero":       round(p_ev, 4),
        "daily_pnl":       daily,
    }


def _sharpe_hac(daily: pd.Series) -> float:
    """HAC-adjusted annualized Sharpe on daily P&L series."""
    r = daily.dropna()
    n = len(r)
    if n < 10:
        return np.nan
    mean = float(r.mean())
    std  = float(r.std(ddof=1))
    if std < 1e-9:
        return np.nan
    if n < 48:
        return mean / std * np.sqrt(252)
    reg  = sm.OLS(r, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    lrv  = float(reg.cov_params().iloc[0, 0]) * n
    hac_std = np.sqrt(max(lrv, 1e-24))
    if hac_std < 1e-12:
        return np.nan
    return mean / hac_std * np.sqrt(252)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Walk-forward
# ─────────────────────────────────────────────────────────────────────────────

def walk_forward_pairs(
    es:       pd.DataFrame,
    nq:       pd.DataFrame,
    cfg:      dict,
    train_months: int = 6,
    test_months:  int = 3,
    max_windows:  int = 9,
) -> dict:
    """Anchored walk-forward: growing train, fixed test window."""
    all_dates = pd.Series(
        pd.to_datetime(es.index.normalize().unique())
    ).sort_values()
    start_date = all_dates.iloc[0]

    windows = []
    n_win   = 0

    while n_win < max_windows:
        train_end = start_date + pd.DateOffset(months=train_months + n_win * test_months)
        oos_end   = train_end  + pd.DateOffset(months=test_months)

        if oos_end > all_dates.iloc[-1] + pd.DateOffset(days=10):
            break

        mask_oos = (es.index >= train_end) & (es.index < oos_end)
        if mask_oos.sum() < 30:
            n_win += 1
            continue

        es_oos  = es[mask_oos]
        nq_oos  = nq[mask_oos]

        # Fit OLS on ALL data up to train_end (expanding window)
        mask_train = es.index < train_end
        log_es_tr  = np.log(es[mask_train]["close"])
        log_nq_tr  = np.log(nq[mask_train]["close"])
        if len(log_es_tr) < 30:
            n_win += 1
            continue

        X_tr     = sm.add_constant(log_es_tr)
        ols_tr   = sm.OLS(log_nq_tr, X_tr).fit()
        alpha_tr = float(ols_tr.params.iloc[0])
        beta_tr  = float(ols_tr.params.iloc[1])

        # Compute z-score on OOS using train-fitted parameters
        z_oos = build_z_score(es_oos, nq_oos, beta_tr, alpha_tr, cfg["lookback_h"])

        try:
            tl_oos = run_pairs_backtest(
                es_oos, nq_oos, z_oos, beta_tr,
                cfg["entry_z"], cfg["stop_z"]
            )
            met = pairs_metrics(tl_oos)
            pnl_tot = met.get("total_pnl_usd", 0)
            n_tr    = met.get("n_trades", 0)
        except Exception as e:
            log.warning("WF window %d failed: %s", n_win + 1, e)
            n_win += 1
            continue

        windows.append({
            "oos_start": str(train_end.date()),
            "oos_end":   str(oos_end.date()),
            "n_trades":  n_tr,
            "total_pnl": pnl_tot,
            "sharpe":    met.get("sharpe_daily_hac"),
            "win_rate":  met.get("win_rate", 0),
            "positive":  pnl_tot > 0,
        })
        n_win += 1

    if not windows:
        return {"n_windows": 0, "wf_pct_positive": np.nan, "windows": []}

    n_pos   = sum(w["positive"] for w in windows)
    pct_pos = float(n_pos / len(windows)) * 100
    sh_vals = [w["sharpe"] for w in windows if w.get("sharpe") is not None]
    med_sh  = float(np.median(sh_vals)) if sh_vals else np.nan
    total_pnl = sum(w["total_pnl"] for w in windows)

    return {
        "n_windows":       len(windows),
        "wf_pct_positive": round(pct_pos, 1),
        "median_sharpe":   round(med_sh, 3) if np.isfinite(med_sh) else None,
        "total_oos_pnl":   round(total_pnl, 0),
        "windows":         windows,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Correlation with Strategy C
# ─────────────────────────────────────────────────────────────────────────────

def strategy_c_daily_pnl() -> pd.Series:
    """Reconstruct Strategy C (iter_10) daily P&L from NQ Kaggle data."""
    df      = load_nq_1min()
    engine  = NQBacktestEngine(df)
    feats   = build_opening_features(engine.rth)
    feats_f = feats[feats["rng"] >= 30.0].copy()
    sigs    = signals_from_features(feats_f, gap_thresh=0.012, dollar_stop=400.0)
    tl, _   = engine.run(sigs)

    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()
    daily_c    = tl.groupby("date")["pnl_usd"].sum()
    all_dates  = pd.bdate_range(tl["date"].min(), tl["date"].max())
    daily_c    = daily_c.reindex(pd.DatetimeIndex(all_dates).normalize(), fill_value=0.0)
    return daily_c


def step5_correlation(
    daily_d: pd.Series,
    daily_c: pd.Series,
    vix_regime: Optional[pd.Series] = None,
) -> dict:
    """Compute Pearson + Spearman correlation, conditional on VIX if available."""
    print("\n" + "═" * 70)
    print("STEP 5 — Correlation: Strategy D vs Strategy C")
    print("═" * 70)

    # Align on common dates
    common = daily_d.index.intersection(daily_c.index)
    d_al   = daily_d.loc[common]
    c_al   = daily_c.loc[common]

    pearson  = float(d_al.corr(c_al))
    from scipy.stats import spearmanr
    spear, sp = spearmanr(d_al.values, c_al.values)

    print(f"\n  Overlap: {len(common)} days ({common[0].date()} → {common[-1].date()})")
    print(f"  Pearson  corr(C,D) = {pearson:+.4f}")
    print(f"  Spearman corr(C,D) = {spear:+.4f}  (p={sp:.4f})")

    corr_gate = abs(pearson) <= GATE_CORR
    print(f"  Gate |ρ| ≤ {GATE_CORR}: {'PASS' if corr_gate else 'FAIL'}")

    result = {
        "overlap_days":   len(common),
        "pearson":        round(pearson, 4),
        "spearman":       round(float(spear), 4),
        "corr_gate_pass": corr_gate,
    }

    # Conditional: high-vol vs low-vol days (C trading days only)
    c_nonzero = c_al[c_al != 0]
    if len(c_nonzero) >= 20:
        # High-vol = days where |C P&L| > median(|C P&L|)
        med_abs = c_nonzero.abs().median()
        hv_mask = c_al.abs() > med_abs
        lv_mask = (c_al.abs() <= med_abs) & (c_al != 0)

        for label, mask in [("C high-|P&L| days", hv_mask),
                             ("C low-|P&L| days",  lv_mask),
                             ("C zero-trade days",  c_al == 0)]:
            sub_d = d_al[mask]
            sub_c = c_al[mask]
            if len(sub_d) >= 10:
                r_sub = float(sub_d.corr(sub_c))
                print(f"  Conditional {label} (N={mask.sum()}): ρ={r_sub:+.4f}")
                result[f"corr_{label[:4].strip().replace(' ','_')}"] = round(r_sub, 4)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Portfolio simulation C+D under Tradeify rules
# ─────────────────────────────────────────────────────────────────────────────

def step6_portfolio(
    daily_c: pd.Series,
    daily_d: pd.Series,
    w_c:     float = 0.5,   # ERC weight for C (simple 50/50 as starting point)
    w_d:     float = 0.5,
) -> dict:
    """
    Combined C+D portfolio under Tradeify rules.
    ERC weight computed from 60-day rolling vol.
    Scale combined to 3 MNQ total exposure for eval phase.
    """
    print("\n" + "═" * 70)
    print("STEP 6 — Portfolio C+D under Tradeify Rules")
    print("═" * 70)

    # Align
    common  = daily_c.index.intersection(daily_d.index)
    c_al    = daily_c.loc[common]
    d_al    = daily_d.loc[common]

    # ERC sizing: vol-parity weights on rolling 60-day vol
    # Scale both series to per-unit (normalized to $1 risk)
    vol_c   = c_al.rolling(60, min_periods=20).std().fillna(c_al.std())
    vol_d   = d_al.rolling(60, min_periods=20).std().fillna(d_al.std())

    # Vol-parity: each strategy gets same risk contribution
    # w_i ∝ 1 / vol_i (scale to sum to 1)
    inv_c = 1.0 / vol_c.replace(0, np.nan)
    inv_d = 1.0 / vol_d.replace(0, np.nan)
    total = (inv_c + inv_d).replace(0, np.nan)
    w_c_erc = (inv_c / total).fillna(0.5)
    w_d_erc = (inv_d / total).fillna(0.5)

    # Combined daily P&L at natural scale (no sizing yet)
    combined = w_c_erc * c_al + w_d_erc * d_al

    # Scale combined to Tradeify eval sizing (3 MNQ total target)
    # Strategy C at 3 MNQ: daily_c is already in NQ-contract dollars
    # Scale factor: make combined portfolio have same expected total dollar vol
    vol_combined = combined.std()
    vol_c_3mnq   = c_al.std()  # C at 1 NQ contract scale
    scale_to_3mnq = vol_c_3mnq / vol_combined if vol_combined > 0 else 1.0

    combined_scaled = combined * scale_to_3mnq

    sh_port  = _sharpe_hac(combined_scaled)
    daily_mn = combined_scaled.mean()
    cum_port = combined_scaled.cumsum()
    dd_port  = (cum_port - cum_port.cummax()) / max(cum_port.cummax().max(), 1.0)
    mdd_port = float(dd_port.min())

    print(f"\n  Combined period: {common[0].date()} → {common[-1].date()} ({len(common)} days)")
    print(f"  C weight (avg ERC): {w_c_erc.mean():.2%}, D weight: {w_d_erc.mean():.2%}")
    print(f"  Portfolio Sharpe (HAC): {sh_port:.4f}" if np.isfinite(sh_port) else "  Portfolio Sharpe: N/A")
    print(f"  Portfolio MaxDD: {mdd_port*100:.1f}%")
    print(f"  E[daily]: ${daily_mn:.1f}")

    # Tradeify 90-day eval bootstrap
    pnl_port = combined_scaled.values.astype(float)
    avg_bl   = max(5, int(np.sqrt(len(pnl_port))))
    rng_p    = np.random.default_rng(MC_SEED + 99)

    paths_90 = _stationary_block_paths(pnl_port, MC_PATHS, 90, avg_bl, rng_p)
    r_eval   = _simulate_tradeify_eval(paths_90, TV_TRAILING_DD, TV_EVAL_TARGET, 90)

    paths_30 = _stationary_block_paths(pnl_port, MC_PATHS, 30, avg_bl, rng_p)
    r_30     = _simulate_tradeify_eval(paths_30, TV_TRAILING_DD, TV_EVAL_TARGET, 30)

    # E[monthly net] at 4 MNQ post-eval sizing
    combined_4mnq = combined * scale_to_3mnq * (4.0 / 3.0)  # scale to 4 MNQ
    daily_4mnq    = combined_4mnq.mean()
    e_monthly_4mnq = daily_4mnq * 21 * 0.90  # 90% profit split

    print(f"\n  Tradeify eval (90d, 3 MNQ equiv):")
    print(f"    P(pass eval)  = {r_eval['p_pass']:.1f}%")
    print(f"    P(bust eval)  = {r_eval['p_bust']:.1f}%")
    print(f"    Median days   = {r_eval['med_days']:.0f}")
    print(f"\n  Tradeify eval (30d, for reference):")
    print(f"    P(pass 30d)   = {r_30['p_pass']:.1f}%")
    print(f"\n  E[monthly net post-lock @4MNQ] = ${e_monthly_4mnq:,.0f}")

    return {
        "sharpe_port":     round(sh_port, 4) if np.isfinite(sh_port) else None,
        "mdd_port":        round(mdd_port, 4),
        "e_daily_3mnq":    round(float(daily_mn), 2),
        "p_pass_eval_90d": r_eval["p_pass"],
        "p_bust_eval_90d": r_eval["p_bust"],
        "p_pass_eval_30d": r_30["p_pass"],
        "e_monthly_4mnq":  round(float(e_monthly_4mnq), 0),
        "scale_factor":    round(float(scale_to_3mnq), 4),
        "w_c_avg":         round(float(w_c_erc.mean()), 4),
        "w_d_avg":         round(float(w_d_erc.mean()), 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# AMTP BH adjustment
# ─────────────────────────────────────────────────────────────────────────────

def bh_adjust(p_values: list[float]) -> list[float]:
    n     = len(p_values)
    order = np.argsort(p_values)
    adj   = np.empty(n)
    for rank, idx in enumerate(order, 1):
        adj[idx] = p_values[idx] * n / rank
    for i in range(n - 2, -1, -1):
        adj[order[i]] = min(adj[order[i]], adj[order[i + 1]])
    return [min(1.0, v) for v in adj]


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 80)
    print("STRATEGY D — ES/NQ Intraday Pairs Trading")
    print(f"n_tests: {N_TESTS_START} → {N_TESTS_START + len(VARIANTS)}")
    print("DATA: ES=F + NQ=F hourly (yfinance, Dec 2023 → present)")
    print("NOTE: 1-min ES data 2022-2025 not available free; using hourly")
    print("=" * 80)

    # ── Load data ─────────────────────────────────────────────────────────
    print("\n  Loading ES=F + NQ=F hourly data from yfinance...")
    es, nq = load_pairs_data()
    dates  = pd.Series(es.index.normalize().unique())
    print(f"  ES: {len(es)} RTH bars | NQ: {len(nq)} RTH bars | "
          f"{len(dates)} days | {len(es)/len(dates):.1f} bars/day")
    print(f"  Range: {es.index[0].date()} → {es.index[-1].date()}")

    # ── STEP 1: Cointegration ─────────────────────────────────────────────
    coint = step1_cointegration(es, nq)

    if not coint["cointegrated"]:
        print(f"\n  *** KILL SWITCH TRIGGERED ***")
        print(f"  Engle-Granger p={coint['eg_pval']:.4f} >= 0.05")
        print(f"  ES/NQ cointegration REJECTED on {es.index[0].date()} → {es.index[-1].date()}")
        print(f"  Recommend alternatives: RTY/NQ, YM/ES, or different spread frequency")
        print(f"\n  D_BEST: N/A | Sharpe=N/A | WF=N/A | corr(C,D)=N/A")
        print(f"  PORTFOLIO C+D: N/A")
        print(f"  Verdict_D=KILL_SWITCH | Verdict_Portfolio=N/A")
        print(f"  Recommendation: ABANDON_D (cointegration failed)")
        return

    beta  = coint["beta"]
    alpha = coint["alpha"]
    hl    = coint["half_life_h"]
    print(f"\n  Hedge ratio β={beta:.4f}, half-life={hl:.1f}h "
          f"(≈{hl/6:.1f} RTH days)")
    print(f"  Lookback choices (≈2× half-life): {hl*2:.0f}h")
    print(f"  Using pre-specified lookbacks: 6h, 12h, 24h (research plan)")

    # ── Compute z-scores for all variants ─────────────────────────────────
    z_cache: dict[int, pd.Series] = {}
    for cfg in VARIANTS:
        lb = cfg["lookback_h"]
        if lb not in z_cache:
            z_cache[lb] = build_z_score(es, nq, beta, alpha, lb)

    # ── STEP 3: Backtest each variant ─────────────────────────────────────
    print("\n" + "═" * 70)
    print("STEPS 3-4 — Backtest + Walk-Forward (all variants)")
    print("═" * 70)

    n_test   = N_TESTS_START
    results  = []
    best_met: dict = {}
    best_tl:  pd.DataFrame = pd.DataFrame()

    for cfg in VARIANTS:
        n_test += 1
        z = z_cache[cfg["lookback_h"]]

        print(f"\n  [{n_test}] {cfg['name']} — {cfg['rationale']}")
        print(f"  lookback={cfg['lookback_h']}h  entry_z={cfg['entry_z']}  stop_z={cfg['stop_z']}")

        # Full backtest
        tl  = run_pairs_backtest(es, nq, z, beta, cfg["entry_z"], cfg["stop_z"])
        met = pairs_metrics(tl)

        sh  = met.get("sharpe_daily_hac") or 0
        mdd = met.get("max_dd_pct") or 0
        pf  = met.get("profit_factor") or 0
        n   = met.get("n_trades", 0)
        wr  = met.get("win_rate", 0)
        tpd = met.get("trades_per_day", 0)
        p_ev= met.get("p_ev_zero", 1.0)

        print(f"  Full: N={n}, Sh={sh:.4f}, MaxDD={mdd*100:.1f}%, "
              f"PF={pf:.4f}, WR={wr:.1%}, TPD={tpd:.2f}")
        print(f"  AvgTrade=${met.get('avg_trade_usd',0):.1f}, "
              f"MR={met.get('exit_mr_pct',0):.0%}, "
              f"SL={met.get('exit_sl_pct',0):.0%}, "
              f"TIME={met.get('exit_time_pct',0):.0%}")

        # Walk-forward
        wf     = walk_forward_pairs(es, nq, cfg)
        wf_pct = wf.get("wf_pct_positive") or 0
        n_win  = wf.get("n_windows", 0)

        print(f"  WF: {n_win} windows, {wf_pct:.0f}% positive, "
              f"median Sharpe={wf.get('median_sharpe')}")

        # WF window detail
        for j, w in enumerate(wf.get("windows", []), 1):
            mark = "✓" if w["positive"] else "✗"
            sh_s = f"{w['sharpe']:.3f}" if w.get("sharpe") else "N/A"
            print(f"    W{j}: {w['oos_start']}→{w['oos_end']} "
                  f"N={w['n_trades']} Sh={sh_s} P&L=${w['total_pnl']:.0f} {mark}")

        # Verdict
        gates = {
            "sh":   sh   >= GATE_SHARPE,
            "wf":   wf_pct >= GATE_WF,
            "pf":   pf   >= GATE_PF,
            "mdd":  mdd  >= GATE_MDD,
            "wr":   wr   >= GATE_WR,
            "tpd":  tpd  >= GATE_TPD,
        }
        if all(gates.values()) and p_ev < GATE_AMTP:
            verdict = "PROPFIRM_PASS"
        elif sh >= 1.0 and mdd >= -0.15 and pf >= 1.2:
            verdict = "RESEARCH_PASS"
        elif sh >= 0.7:
            verdict = "IMPROVE"
        else:
            verdict = "WEAK"

        print(f"  Gates: " + " ".join(
            f"{k}={'✓' if v else '✗'}" for k, v in gates.items()))
        print(f"  → {verdict}")

        # Track best by Sharpe for correlation/portfolio
        if not best_tl.empty:
            if (met.get("sharpe_daily_hac") or 0) > (best_met.get("sharpe_daily_hac") or 0):
                best_met = met
                best_tl  = tl
        else:
            best_met = met
            best_tl  = tl

        result = {
            "iteration":       cfg["name"],
            "n_tests":         n_test,
            "description":     cfg["rationale"],
            **{k: v for k, v in met.items() if k != "daily_pnl"},
            "wf_pct_positive": wf_pct,
            "wf_n_windows":    n_win,
            "wf_median_sharpe":wf.get("median_sharpe"),
            "gates":           gates,
            "verdict":         verdict,
        }
        results.append(result)
        append_result(result)

    # ── AMTP BH adjustment ────────────────────────────────────────────────
    p_raw = [r.get("p_ev_zero", 1.0) for r in results]
    p_bh  = bh_adjust(p_raw)
    for r, p_adj in zip(results, p_bh):
        r["p_bh_adjusted"] = round(p_adj, 4)

    # ── STEP 5: Correlation ────────────────────────────────────────────────
    print("\n  Loading Strategy C daily P&L (iter_10)...")
    daily_c = strategy_c_daily_pnl()

    best_daily_d = best_met.get("daily_pnl", pd.Series())
    corr_result  = step5_correlation(best_daily_d, daily_c)

    # ── STEP 6: Portfolio C+D ─────────────────────────────────────────────
    port_result = step6_portfolio(daily_c, best_daily_d)

    # ── Summary table ─────────────────────────────────────────────────────
    print("\n" + "═" * 100)
    print("STRATEGY D RESULTS SUMMARY")
    print(f"{'Variant':<12} {'N':>5} {'TPD':>5} {'WR':>6} {'Sh':>7} "
          f"{'MDD':>7} {'PF':>6} {'WF%':>6} {'p_BH':>7} {'Verdict'}")
    print("─" * 100)
    for r, p_bh_v in zip(results, p_bh):
        sh  = r.get("sharpe_daily_hac") or 0
        mdd = r.get("max_dd_pct") or 0
        pf  = r.get("profit_factor") or 0
        wf  = r.get("wf_pct_positive") or 0
        n   = r.get("n_trades", 0)
        wr  = r.get("win_rate", 0)
        tpd = r.get("trades_per_day", 0)
        vd  = r.get("verdict", "?")
        print(f"  {r['iteration']:<10} {n:>5} {tpd:>5.2f} {wr:>5.1%} "
              f"{sh:>7.4f} {mdd*100:>6.1f}% {pf:>6.3f} "
              f"{wf:>5.0f}% {p_bh_v:>7.4f} {vd}")
    print("─" * 100)
    print("═" * 100)

    # ── Final verdict ─────────────────────────────────────────────────────
    best_d   = max(results, key=lambda r: r.get("sharpe_daily_hac") or 0)
    best_sh  = best_d.get("sharpe_daily_hac") or 0
    best_wf  = best_d.get("wf_pct_positive") or 0
    best_vd  = best_d.get("verdict", "?")
    best_n   = best_d.get("iteration", "?")
    corr_val = corr_result.get("pearson", np.nan)
    p_bh_best = best_d.get("p_bh_adjusted", 1.0)

    port_sh  = port_result.get("sharpe_port") or 0
    port_mdd = port_result.get("mdd_port") or 0
    port_p90 = port_result.get("p_pass_eval_90d", 0)
    port_em  = port_result.get("e_monthly_4mnq", 0)

    # Portfolio gates
    port_gates = {
        "sharpe":  port_sh  >= 1.7,
        "p_eval":  port_p90 >= 50.0,
        "mdd":     port_mdd >= -0.10,
        "monthly": port_em  >= 1000.0,
    }
    port_verdict = "PROPFIRM_PASS" if all(port_gates.values()) else "RESEARCH_PASS" \
        if port_sh >= 1.3 and port_p90 >= 30 else "FAIL"

    corr_ok = abs(corr_val) <= GATE_CORR if np.isfinite(corr_val) else False

    if best_vd == "PROPFIRM_PASS" and corr_ok and port_verdict == "PROPFIRM_PASS":
        recommendation = "DEPLOY"
    elif best_vd in ("PROPFIRM_PASS", "RESEARCH_PASS") and corr_ok:
        recommendation = "RESEARCH_MORE"
    else:
        recommendation = "ABANDON_D"

    print(f"\n  n_tests: {N_TESTS_START} → {n_test}")
    print(f"\n  D_BEST: {best_n} | Sharpe={best_sh:.4f} | WF={best_wf:.0f}% | "
          f"corr(C,D)={corr_val:+.4f}")
    print(f"  PORTFOLIO C+D: Sharpe={port_sh:.4f} | MaxDD={port_mdd*100:.1f}% | "
          f"P(eval 90d @ ERC)={port_p90:.1f}%")
    print(f"  Verdict_D={best_vd} | Verdict_Portfolio={port_verdict}")
    print(f"  Recommendation: {recommendation}")
    print()
    print(f"  D_BEST: {best_n} | Sharpe={best_sh:.2f} | WF={best_wf:.0f}% | "
          f"corr(C,D)={corr_val:+.4f}")
    print(f"  PORTFOLIO C+D: Sharpe={port_sh:.2f} | MaxDD={port_mdd*100:.1f}% | "
          f"P(eval 90d @ ERC)={port_p90:.1f}%")
    print(f"  Verdict_D={best_vd} | Verdict_Portfolio={port_verdict}")
    print(f"  Recommendation: {recommendation}")

    # Gate detail
    print(f"\n  Portfolio gate detail:")
    gate_labels = {
        "sharpe":  f"Portfolio Sharpe ≥ 1.7",
        "p_eval":  f"P(eval 90d) ≥ 50%",
        "mdd":     f"MaxDD ≥ -10%",
        "monthly": f"E[monthly @4MNQ] ≥ $1,000",
    }
    gate_vals = {
        "sharpe":  f"{port_sh:.4f}",
        "p_eval":  f"{port_p90:.1f}%",
        "mdd":     f"{port_mdd*100:.1f}%",
        "monthly": f"${port_em:,.0f}",
    }
    for k, label in gate_labels.items():
        mark = "PASS" if port_gates[k] else "FAIL"
        print(f"    [{mark}] {label:<35}  actual={gate_vals[k]}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("iter_d_pairs failed")
        sys.exit(1)
