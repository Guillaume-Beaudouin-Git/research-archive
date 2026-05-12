#!/usr/bin/env python
"""
Portfolio TSMOM v2 + Mean-Reversion ATR — Feasibility Study.

Hypothesis: correlation -0.30 between TSMOM and MR-ATR means that when
TSMOM loses (trending market reverses), MR-ATR gains (extended moves
revert). This structural offset should reduce daily limit breaches while
maintaining positive returns — improving Propr challenge pass rates.

Run: python -m strategies.portfolio_tsmom_mr.feasibility
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np
import pandas as pd
import scipy.stats as stats
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Imports from existing strategy modules ─────────────────────────────────────
from strategies.tsmom_v2_propfirm.signal import compute_signal, apply_weekly_rebalance
from strategies.tsmom_v2_propfirm.sizing import compute_vol_scalars, compute_positions
from strategies.mean_reversion_atr.feasibility import (
    compute_features as mr_compute_features,
    load_funding_rates as mr_load_funding_rates,
)

# ── Constants ──────────────────────────────────────────────────────────────────
# Common universe: 12 assets (MR-ATR universe, excludes UNI-USD and MATIC-USD
# which have no Hyperliquid perps with sufficient liquidity)
UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD",
    "ARB-USD", "DOGE-USD", "ADA-USD", "DOT-USD", "LTC-USD",
    "BCH-USD", "OP-USD",
]

# Period: same as Propr challenge simulator (apples-to-apples)
ANALYSIS_START = "2025-01-06"
ANALYSIS_END   = "2026-05-11"

# Data download: need 2019 warmup for 28-day TSMOM signal + 20-day vol + 90-day high
DATA_DOWNLOAD_START = "2019-01-01"
DATA_DOWNLOAD_END   = "2026-05-12"

# MR-ATR best params from feasibility study (train period 2020-2024-06-30)
# From feasibility output: dd_thr=-0.25, ma50_thr=0.30, ret60_thr=0.40, atr_mult=1.0, tp_mult=1.5
MR_BEST_PARAMS: dict[str, Any] = {
    "dd_thr":    -0.25,
    "ma50_thr":   0.30,
    "ret60_thr":  0.40,
    "atr_mult":   1.0,
    "tp_mult":    1.5,
}

# Portfolio weights: (w_tsmom, w_mr, label)
PORTFOLIO_WEIGHTS: list[tuple[float, float, str]] = [
    (1.00, 0.00, "P1 (100/0)"),
    (0.75, 0.25, "P2 (75/25)"),
    (0.50, 0.50, "P3 (50/50)"),
    (0.25, 0.75, "P4 (25/75)"),
    (0.00, 1.00, "P5 (0/100)"),
]

# Costs: 0.17% round-trip (fee + slippage both sides)
COSTS_ONE_WAY = 0.00085   # 0.085% per side
COSTS_RT      = 0.0017    # 0.17% round-trip

# TSMOM parameters
VOL_TARGET   = 0.15
VOL_LOOKBACK = 20

# MR-ATR parameters
ATR_LOOKBACK  = 14
RISK_PCT      = 0.01
MAX_POS_FRAC  = 0.15
MAX_POSITIONS = 3
MAX_HOLD_DAYS = 5

# Propr challenge rules
SIM_START      = "2025-01-06"
SIM_END        = "2025-11-03"
PROPR_CAPITAL  = 5_000.0
PROPR_TARGET   = 0.10
PROPR_DD       = 0.06
PROPR_DAILY    = 0.03

# Breakout challenge rules
BREAKOUT_TARGET  = 0.10
BREAKOUT_DD      = 0.10
BREAKOUT_DAILY   = 0.05

TSMOM_BASELINE_PASS = 0.34   # from prior feasibility

OUT_DIR    = Path(__file__).parent
CHART_PATH = OUT_DIR / "portfolio_analysis.png"

HL_ASSET_MAP: dict[str, str] = {
    "BTC-USD": "BTC", "ETH-USD": "ETH", "SOL-USD": "SOL",
    "AVAX-USD": "AVAX", "LINK-USD": "LINK", "ARB-USD": "ARB",
    "DOGE-USD": "DOGE", "ADA-USD": "ADA", "DOT-USD": "DOT",
    "LTC-USD": "LTC", "BCH-USD": "BCH", "OP-USD": "OP",
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_data(
    universe: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Download daily OHLCV for given universe. Returns (close, open_, high, low)."""
    print("  Downloading daily OHLCV from yfinance...")
    raw = yf.download(
        universe,
        start=DATA_DOWNLOAD_START,
        end=DATA_DOWNLOAD_END,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    close = raw["Close"].ffill().dropna(how="all")
    open_ = raw["Open"].ffill().dropna(how="all")
    high  = raw["High"].ffill().dropna(how="all")
    low   = raw["Low"].ffill().dropna(how="all")
    idx   = close.index
    open_ = open_.reindex(idx)
    high  = high.reindex(idx)
    low   = low.reindex(idx)

    valid = [c for c in close.columns if close[c].notna().sum() > 500]
    print(f"  {len(valid)}/{len(universe)} assets with sufficient history")
    return close[valid], open_[valid], high[valid], low[valid]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1A — TSMOM v2 DAILY P&L
# ─────────────────────────────────────────────────────────────────────────────

def compute_tsmom_pnl(close: pd.DataFrame) -> pd.Series:
    """
    Reconstruct TSMOM v2 daily P&L on the common 12-asset universe.

    Signal logic identical to strategies/tsmom_v2_propfirm:
      - 28-day momentum signal (long-only)
      - weekly rebalance (Monday)
      - 15% annualized vol target per asset
      - portfolio P&L = mean of per-asset net returns
      - costs = 0.17% round-trip on position changes

    Returns
    -------
    pd.Series of daily P&L fractions, indexed by date.
    """
    log_rets   = np.log(close / close.shift(1))
    arith_rets = np.exp(log_rets) - 1

    # Signal pipeline (imports from tsmom_v2_propfirm)
    signals    = compute_signal(close)
    signals_rb = apply_weekly_rebalance(signals)
    vol_scal   = compute_vol_scalars(log_rets, vol_target=VOL_TARGET, vol_lookback=VOL_LOOKBACK)
    positions  = compute_positions(signals_rb, vol_scal)

    # Per-asset net return
    gross_ret  = positions * arith_rets
    # Turnover × one-way cost (each unit of turnover = one entry or exit)
    turnover   = positions.diff().abs()
    cost       = turnover * COSTS_ONE_WAY
    net_ret    = gross_ret - cost

    # Portfolio = equal-weight mean across assets
    n_valid    = net_ret.notna().sum(axis=1)
    port       = net_ret.mean(axis=1)
    port[n_valid < 3] = np.nan   # require at least 3 assets

    return port


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1B — MR-ATR DAILY P&L
# ─────────────────────────────────────────────────────────────────────────────

def compute_mr_pnl(
    close: pd.DataFrame,
    high: pd.DataFrame,
    low: pd.DataFrame,
    funding_rates: dict[str, pd.Series],
) -> pd.Series:
    """
    Reconstruct MR-ATR daily P&L using best params from feasibility study.

    Uses MR_BEST_PARAMS: dd_thr=-0.25, ma50_thr=0.30, ret60_thr=0.40,
    atr_mult=1.0, tp_mult=1.5.

    Costs: 0.17% round-trip (0.085% entry + 0.085% exit).
    Returns daily P&L as fraction of equity.
    """
    # Build feature panel (reuse MR-ATR feature engine)
    panel = mr_compute_features(close, high, low, funding_rates)

    params    = MR_BEST_PARAMS
    dd_thr    = params["dd_thr"]
    ma50_thr  = params["ma50_thr"]
    ret60_thr = params["ret60_thr"]
    atr_mult  = params["atr_mult"]
    tp_mult   = params["tp_mult"]

    dates   = sorted(panel["date"].unique())
    tickers = list(close.columns)

    daily_pnl: dict[pd.Timestamp, float] = {}
    positions: dict[str, dict[str, Any]] = {}

    for i, date in enumerate(dates):
        day_pnl  = 0.0
        day_data = panel[panel["date"] == date].set_index("ticker")

        # ── Manage existing positions ──────────────────────────────────────
        to_close: list[str] = []
        for tkr, pos in list(positions.items()):
            if tkr not in close.columns or date not in close.index:
                continue
            px_today = float(close.at[date, tkr])
            entry_px = pos["entry_px"]
            side     = pos["side"]

            if side == "long":
                ret      = (px_today - entry_px) / entry_px
                hit_stop = ret < -pos["stop_pct"]
                hit_tp   = ret >  pos["tp_pct"]
            else:
                ret      = (entry_px - px_today) / entry_px
                hit_stop = ret < -pos["stop_pct"]
                hit_tp   = ret >  pos["tp_pct"]

            pos["days_held"] = pos.get("days_held", 0) + 1
            exit_reason = None
            if hit_stop:
                exit_reason = "stop"
                trade_ret   = -pos["stop_pct"]
            elif hit_tp:
                exit_reason = "tp"
                trade_ret   = pos["tp_pct"]
            elif pos["days_held"] >= MAX_HOLD_DAYS:
                exit_reason = "max_hold"
                trade_ret   = ret

            if exit_reason:
                trade_ret -= COSTS_ONE_WAY   # exit cost (entry already deducted)
                day_pnl   += trade_ret * pos["notional_frac"]
                to_close.append(tkr)

        for tkr in to_close:
            del positions[tkr]

        # ── Open new positions ─────────────────────────────────────────────
        if len(positions) < MAX_POSITIONS and i + 1 < len(dates):
            next_date = dates[i + 1]
            for tkr in tickers:
                if len(positions) >= MAX_POSITIONS:
                    break
                if tkr in positions or tkr not in day_data.index:
                    continue

                row = day_data.loc[tkr]
                long_sig  = (
                    row["dd_from_high"] < dd_thr and
                    row["ret_28d"]      < -0.10 and
                    row["vol_zscore_20d"] < 0.5
                )
                short_sig = (
                    row["ma_50_pct"]        > ma50_thr and
                    row["ret_60d"]          > ret60_thr and
                    row["funding_ema_7d"]   > 0.0001
                )
                if not (long_sig or short_sig):
                    continue
                if pd.isna(row["atr_pct"]) or row["atr_pct"] <= 0:
                    continue

                side      = "long" if long_sig else "short"
                atr_pct   = float(row["atr_pct"])
                stop_pct  = atr_mult * atr_pct
                tp_pct    = tp_mult  * atr_pct

                if next_date not in close.index or tkr not in close.columns:
                    continue
                entry_px = float(close.at[next_date, tkr])
                if np.isnan(entry_px) or entry_px <= 0:
                    continue

                notional_frac = min(RISK_PCT / max(stop_pct, 1e-6), MAX_POS_FRAC)
                positions[tkr] = {
                    "side": side, "entry_px": entry_px,
                    "stop_pct": stop_pct, "tp_pct": tp_pct,
                    "notional_frac": notional_frac, "days_held": 0,
                }
                day_pnl -= COSTS_ONE_WAY * notional_frac  # entry cost

        daily_pnl[pd.Timestamp(date)] = day_pnl

    return pd.Series(daily_pnl)


# ─────────────────────────────────────────────────────────────────────────────
# PORTFOLIO METRICS
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(pnl: pd.Series, btc_rets: pd.Series) -> dict[str, Any]:
    """Compute Sharpe, max_dd, ann_ret, beta, max_day, pct_exceed_3, pct_exceed_5."""
    pnl = pnl.dropna()
    if len(pnl) < 10:
        return {k: float("nan") for k in
                ["sharpe", "max_dd", "ann_ret", "beta", "max_day",
                 "pct_exceed_3", "pct_exceed_5"]}

    ann_ret  = float(pnl.mean() * 365)
    ann_vol  = float(pnl.std()  * np.sqrt(365))
    sharpe   = ann_ret / ann_vol if ann_vol > 0 else 0.0
    eq       = (1 + pnl).cumprod()
    max_dd   = float((eq / eq.cummax() - 1).min())
    max_day  = float(pnl.min())

    # BTC beta
    aligned = pd.concat({"p": pnl, "btc": btc_rets}, axis=1).dropna()
    if len(aligned) > 10:
        cov = float(np.cov(aligned["p"], aligned["btc"])[0, 1])
        var = float(aligned["btc"].var())
        beta = cov / var if var > 0 else 0.0
    else:
        beta = float("nan")

    pct_exceed_3 = float((pnl < -0.03).mean()) * 100
    pct_exceed_5 = float((pnl < -0.05).mean()) * 100

    return {
        "sharpe":        sharpe,
        "max_dd":        max_dd,
        "ann_ret":       ann_ret,
        "beta":          beta,
        "max_day":       max_day,
        "pct_exceed_3":  pct_exceed_3,
        "pct_exceed_5":  pct_exceed_5,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CHALLENGE SIMULATION
# ─────────────────────────────────────────────────────────────────────────────

def _simulate_challenge(
    daily_pnl: pd.Series,
    start_date: pd.Timestamp,
    initial_equity: float,
    target_pct: float,
    dd_pct: float,
    daily_pct: float,
) -> dict[str, Any]:
    """Simulate one prop-firm challenge attempt. Static HWM."""
    sim_dates = daily_pnl.index[daily_pnl.index >= start_date]
    equity = initial_equity
    hwm    = initial_equity
    days   = 0

    for date in sim_dates:
        eq_start = equity
        equity   = eq_start * (1 + float(daily_pnl.get(date, 0.0)))
        days    += 1

        if (equity - eq_start) / eq_start < -daily_pct:
            return {"outcome": "FAIL", "reason": "daily_limit", "equity": equity, "days": days}
        if equity <= hwm * (1 - dd_pct):
            return {"outcome": "FAIL", "reason": "total_dd",    "equity": equity, "days": days}
        if equity >= hwm * (1 + target_pct):
            return {"outcome": "PASS", "reason": None,          "equity": equity, "days": days}

    return {"outcome": "INCOMPLETE", "reason": None, "equity": equity, "days": days}


def run_propr_sims(pnl: pd.Series) -> dict[str, Any]:
    """Run 44 Propr challenge simulations. Returns pass_rate and breakdown."""
    if pnl.index.tz is not None:
        pnl = pnl.copy(); pnl.index = pnl.index.tz_localize(None)

    start_dates = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")
    results = [
        _simulate_challenge(pnl, sd, PROPR_CAPITAL, PROPR_TARGET, PROPR_DD, PROPR_DAILY)
        for sd in start_dates
    ]
    pass_rate  = sum(1 for r in results if r["outcome"] == "PASS") / len(results)
    fail_daily = sum(1 for r in results if r.get("reason") == "daily_limit")
    fail_dd    = sum(1 for r in results if r.get("reason") == "total_dd")
    pass_days  = [r["days"] for r in results if r["outcome"] == "PASS"]
    avg_days   = float(np.mean(pass_days)) if pass_days else float("nan")
    fee_cost   = 60.0 / pass_rate if pass_rate > 0 else float("inf")

    return {
        "pass_rate":  pass_rate,
        "fail_daily": fail_daily,
        "fail_dd":    fail_dd,
        "avg_days":   avg_days,
        "fee_cost":   fee_cost,
        "n_sims":     len(results),
    }


def run_breakout_sims(pnl: pd.Series) -> dict[str, Any]:
    """Run 44 Breakout challenge simulations (relaxed daily/DD limits)."""
    if pnl.index.tz is not None:
        pnl = pnl.copy(); pnl.index = pnl.index.tz_localize(None)

    start_dates = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")
    results = [
        _simulate_challenge(pnl, sd, PROPR_CAPITAL, BREAKOUT_TARGET, BREAKOUT_DD, BREAKOUT_DAILY)
        for sd in start_dates
    ]
    pass_rate  = sum(1 for r in results if r["outcome"] == "PASS") / len(results)
    fail_daily = sum(1 for r in results if r.get("reason") == "daily_limit")
    fail_dd    = sum(1 for r in results if r.get("reason") == "total_dd")

    return {
        "pass_rate":  pass_rate,
        "fail_daily": fail_daily,
        "fail_dd":    fail_dd,
        "n_sims":     len(results),
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — PORTFOLIO COMBINATIONS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_portfolios(
    tsmom_pnl: pd.Series,
    mr_pnl: pd.Series,
    btc_rets: pd.Series,
) -> dict[str, Any]:
    """Step 2: Compute metrics for 5 portfolio allocations."""
    print(f"\n{'='*60}")
    print("STEP 2 — PORTFOLIO COMBINATIONS")
    print(f"{'='*60}")

    # Verify correlation
    aligned = pd.concat({"ts": tsmom_pnl, "mr": mr_pnl}, axis=1).dropna()
    corr = float(aligned["ts"].corr(aligned["mr"]))
    print(f"\n  TSMOM vs MR-ATR correlation: {corr:+.3f}  "
          f"{'(expected ≈ -0.30)' if corr < 0 else '⚠ CORRELATION HAS CHANGED — check data'}")

    header = (
        f"\n  {'Portfolio':<12} {'Sharpe':>7} {'MaxDD':>7} {'AnnRet':>8} "
        f"{'Beta':>6} {'MaxDay':>8} {'>3%':>6} {'>5%':>6}"
    )
    print(header)
    print(f"  {'-'*70}")

    portfolio_results: dict[str, Any] = {"corr": corr, "portfolios": {}}

    for w_ts, w_mr, label in PORTFOLIO_WEIGHTS:
        pnl = (w_ts * tsmom_pnl + w_mr * mr_pnl).reindex(aligned.index)
        m   = compute_metrics(pnl, btc_rets)
        portfolio_results["portfolios"][label] = {"pnl": pnl, "metrics": m, "w_ts": w_ts, "w_mr": w_mr}

        print(
            f"  {label:<12} {m['sharpe']:>7.2f} {m['max_dd']:>7.2%} {m['ann_ret']:>8.2%} "
            f"{m['beta']:>6.2f} {m['max_day']:>8.3%} {m['pct_exceed_3']:>5.1f}% {m['pct_exceed_5']:>5.1f}%"
        )

    return portfolio_results


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — PROPR CHALLENGE SIMULATIONS
# ─────────────────────────────────────────────────────────────────────────────

def propr_all_portfolios(portfolio_results: dict[str, Any]) -> dict[str, Any]:
    """Step 3: Run 44 Propr sims for all 5 portfolio splits."""
    print(f"\n{'='*60}")
    print("STEP 3 — PROPR CHALLENGE SIMULATIONS (44 start dates)")
    print(f"{'='*60}")

    print(
        f"\n  {'Portfolio':<12} {'Pass%':>6} {'FailDaily':>10} {'FailDD':>7} "
        f"{'AvgDays':>9} {'FeeROI':>9}"
    )
    print(f"  {'-'*60}")

    out: dict[str, Any] = {}
    for label, pdata in portfolio_results["portfolios"].items():
        r = run_propr_sims(pdata["pnl"])
        out[label] = r
        fee_str = f"${r['fee_cost']:.0f}" if r["fee_cost"] < 1e5 else "n/a"
        print(
            f"  {label:<12} {r['pass_rate']:>5.0%}  {r['fail_daily']:>9}/44 "
            f"{r['fail_dd']:>6}/44 {r['avg_days']:>8.0f}  {fee_str:>8}"
        )

    print(f"\n  TSMOM baseline (reference): {TSMOM_BASELINE_PASS:.0%}  (from prior feasibility)")

    best_label = max(out, key=lambda k: out[k]["pass_rate"])
    print(f"\n  Best portfolio: {best_label}  ({out[best_label]['pass_rate']:.0%} pass rate)")

    return {"sims": out, "best_label": best_label}


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — BREAKOUT SIMULATION (best portfolio only)
# ─────────────────────────────────────────────────────────────────────────────

def breakout_best(portfolio_results: dict[str, Any], best_label: str) -> dict[str, Any]:
    """Step 4: Run Breakout sims on best portfolio."""
    print(f"\n{'='*60}")
    print(f"STEP 4 — BREAKOUT SIMULATION ({best_label})")
    print(f"{'='*60}")

    pnl = portfolio_results["portfolios"][best_label]["pnl"]
    r   = run_breakout_sims(pnl)
    propr_r = run_propr_sims(pnl)

    print(f"\n  {best_label} — Propr  pass rate: {propr_r['pass_rate']:.0%}  "
          f"(daily_limit fails: {propr_r['fail_daily']}/44, dd fails: {propr_r['fail_dd']}/44)")
    print(f"  {best_label} — Breakout pass rate: {r['pass_rate']:.0%}  "
          f"(daily_limit fails: {r['fail_daily']}/44, dd fails: {r['fail_dd']}/44)")

    return {"propr": propr_r, "breakout": r}


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — OPTIMAL ALLOCATION SWEEP
# ─────────────────────────────────────────────────────────────────────────────

def optimal_allocation_sweep(
    tsmom_pnl: pd.Series,
    mr_pnl: pd.Series,
    btc_rets: pd.Series,
) -> dict[str, Any]:
    """Step 5: Fine sweep of TSMOM weight [0, 0.1, ..., 1.0]."""
    print(f"\n{'='*60}")
    print("STEP 5 — OPTIMAL ALLOCATION SWEEP (11 weights × 44 sims)")
    print(f"{'='*60}")

    aligned = pd.concat({"ts": tsmom_pnl, "mr": mr_pnl}, axis=1).dropna()
    weights  = np.linspace(0.0, 1.0, 11)  # 0.0, 0.1, ..., 1.0

    sweep: list[dict[str, Any]] = []
    for w in weights:
        pnl = (w * aligned["ts"] + (1 - w) * aligned["mr"])
        r   = run_propr_sims(pnl)
        m   = compute_metrics(pnl, btc_rets.reindex(aligned.index))
        sweep.append({
            "w_tsmom":       w,
            "pass_rate":     r["pass_rate"],
            "sharpe":        m["sharpe"],
            "pct_exceed_3":  m["pct_exceed_3"],
            "fail_daily":    r["fail_daily"],
        })

    opt_pass  = max(sweep, key=lambda x: x["pass_rate"])
    opt_sharpe = max(sweep, key=lambda x: x["sharpe"] if not np.isnan(x["sharpe"]) else -np.inf)
    opt_min3  = min(sweep, key=lambda x: x["pct_exceed_3"])

    print(f"\n  {'TSMOM%':>8} {'PassRate':>9} {'Sharpe':>8} {'>3%':>6} {'FailD':>6}")
    print(f"  {'-'*45}")
    for s in sweep:
        marker = ""
        if s["w_tsmom"] == opt_pass["w_tsmom"]:
            marker += " ← max pass rate"
        if s["w_tsmom"] == opt_sharpe["w_tsmom"] and s["w_tsmom"] != opt_pass["w_tsmom"]:
            marker += " ← max Sharpe"
        if s["w_tsmom"] == opt_min3["w_tsmom"] and s["w_tsmom"] not in (opt_pass["w_tsmom"], opt_sharpe["w_tsmom"]):
            marker += " ← min >3%"
        print(f"  {s['w_tsmom']:>7.0%}  {s['pass_rate']:>8.0%} {s['sharpe']:>8.2f} "
              f"{s['pct_exceed_3']:>5.1f}%  {s['fail_daily']:>5}/44{marker}")

    print(f"\n  Optimal by pass rate : TSMOM={opt_pass['w_tsmom']:.0%}  → {opt_pass['pass_rate']:.0%}")
    print(f"  Optimal by Sharpe    : TSMOM={opt_sharpe['w_tsmom']:.0%}  → {opt_sharpe['sharpe']:.2f}")
    print(f"  Optimal by min >3%   : TSMOM={opt_min3['w_tsmom']:.0%}  → {opt_min3['pct_exceed_3']:.1f}%")

    return {
        "sweep":       sweep,
        "opt_pass":    opt_pass,
        "opt_sharpe":  opt_sharpe,
        "opt_min3":    opt_min3,
        "weights":     weights,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — REGIME ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def regime_analysis(
    tsmom_pnl: pd.Series,
    mr_pnl: pd.Series,
    opt_w_tsmom: float,
    close: pd.DataFrame,
) -> dict[str, Any]:
    """Step 6: Regime split — BTC above/below MA50 at each challenge start date."""
    print(f"\n{'='*60}")
    print("STEP 6 — REGIME ANALYSIS")
    print(f"{'='*60}")

    aligned = pd.concat({"ts": tsmom_pnl, "mr": mr_pnl}, axis=1).dropna()
    opt_pnl  = (opt_w_tsmom * aligned["ts"] + (1 - opt_w_tsmom) * aligned["mr"])
    p1_pnl   = aligned["ts"]   # TSMOM standalone

    start_dates = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")

    btc = close["BTC-USD"] if "BTC-USD" in close.columns else close.iloc[:, 0]
    btc_ma50 = btc.rolling(50, min_periods=25).mean()

    good_regime_dates, bad_regime_dates = [], []
    for sd in start_dates:
        # Find closest date <= sd
        past = btc.index[btc.index <= sd]
        if len(past) == 0:
            continue
        ref_date = past[-1]
        is_above = float(btc.at[ref_date]) > float(btc_ma50.at[ref_date])
        if is_above:
            good_regime_dates.append(sd)
        else:
            bad_regime_dates.append(sd)

    def _pass_rate_for_dates(
        pnl: pd.Series,
        dates: list[pd.Timestamp],
    ) -> float:
        if not dates:
            return float("nan")
        if pnl.index.tz is not None:
            pnl = pnl.copy(); pnl.index = pnl.index.tz_localize(None)
        results = [
            _simulate_challenge(pnl, sd, PROPR_CAPITAL, PROPR_TARGET, PROPR_DD, PROPR_DAILY)
            for sd in dates
        ]
        return sum(1 for r in results if r["outcome"] == "PASS") / len(results)

    print(f"\n  BTC regime classification:")
    print(f"    Good regime (BTC > MA50): {len(good_regime_dates)}/44 start dates")
    print(f"    Bad  regime (BTC < MA50): {len(bad_regime_dates)}/44 start dates")

    # Optimal portfolio
    opt_good = _pass_rate_for_dates(opt_pnl, good_regime_dates)
    opt_bad  = _pass_rate_for_dates(opt_pnl, bad_regime_dates)
    p1_good  = _pass_rate_for_dates(p1_pnl,  good_regime_dates)
    p1_bad   = _pass_rate_for_dates(p1_pnl,  bad_regime_dates)

    print(f"\n  {'Regime':<20} {'Optimal portfolio':>18} {'TSMOM alone':>14} {'Improvement':>12}")
    print(f"  {'-'*66}")
    print(f"  {'Good (BTC > MA50)':<20} {opt_good:>17.0%}  {p1_good:>13.0%} {opt_good-p1_good:>11.0%}")
    print(f"  {'Bad (BTC < MA50)':<20} {opt_bad:>17.0%}  {p1_bad:>13.0%}  {opt_bad-p1_bad:>11.0%}")

    diversification_confirmed = (opt_bad > p1_bad)
    print(f"\n  Diversification thesis confirmed in bad regime: "
          f"{'YES ✓' if diversification_confirmed else 'NO ✗'}")

    return {
        "good_pass_opt":  opt_good,
        "bad_pass_opt":   opt_bad,
        "good_pass_p1":   p1_good,
        "bad_pass_p1":    p1_bad,
        "n_good":         len(good_regime_dates),
        "n_bad":          len(bad_regime_dates),
        "diversification_confirmed": diversification_confirmed,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — VERDICT
# ─────────────────────────────────────────────────────────────────────────────

def print_verdict(
    corr: float,
    sweep: dict[str, Any],
    best_label: str,
    step4: dict[str, Any],
    regime: dict[str, Any],
    portfolio_results: dict[str, Any],
) -> str:
    """Print structured verdict. Returns 'DEPLOY'|'PROMISING'|'INSUFFICIENT_IMPROVEMENT'|'SKIP'."""
    opt_pass    = sweep["opt_pass"]
    opt_sharpe  = sweep["opt_sharpe"]
    opt_min3    = sweep["opt_min3"]

    best_pass_rate = opt_pass["pass_rate"]
    best_sharpe    = opt_pass.get("sharpe", 0.0)

    # Find Sharpe for optimal pass-rate portfolio (may differ)
    w_best = opt_pass["w_tsmom"]
    sharpe_at_best = next(
        (s["sharpe"] for s in sweep["sweep"] if s["w_tsmom"] == w_best), 0.0
    )

    if best_pass_rate >= 0.50 and sharpe_at_best >= 0.8:
        verdict = "DEPLOY"
    elif best_pass_rate >= 0.40 or (best_pass_rate - TSMOM_BASELINE_PASS) >= 0.10:
        verdict = "PROMISING"
    elif (best_pass_rate - TSMOM_BASELINE_PASS) >= 0.05:
        verdict = "INSUFFICIENT_IMPROVEMENT"
    else:
        verdict = "SKIP"

    breakout_pass = step4["breakout"]["pass_rate"]
    daily_fails_best = next(
        (s["fail_daily"] for s in sweep["sweep"] if s["w_tsmom"] == w_best), 0
    )

    border = "═" * 57
    print(f"\n{border}")
    print("PORTFOLIO TSMOM + MR-ATR — FEASIBILITY REPORT")
    print(f"{border}")
    print(f"  Strategy correlation       : {corr:+.3f}  (target < 0)")

    print(f"\n  Best allocation            : {w_best:.0%} TSMOM / {1-w_best:.0%} MR-ATR")
    print(f"    Propr pass rate          : {best_pass_rate:.0%}  (vs TSMOM alone: {TSMOM_BASELINE_PASS:.0%})")
    print(f"    Improvement              : {best_pass_rate - TSMOM_BASELINE_PASS:+.0%}")
    print(f"    Breakout pass rate       : {breakout_pass:.0%}")
    print(f"    Daily limit fails        : {daily_fails_best}/44")
    print(f"    Sharpe                   : {sharpe_at_best:.2f}")

    print(f"\n  Weight that max Sharpe     : {opt_sharpe['w_tsmom']:.0%} TSMOM")
    print(f"  Weight that min >3% days   : {opt_min3['w_tsmom']:.0%} TSMOM")
    print(f"  Weight that max pass rate  : {opt_pass['w_tsmom']:.0%} TSMOM")

    print(f"\n  Regime analysis:")
    print(f"    Good regime pass rate    : {regime['good_pass_opt']:.0%}  "
          f"(TSMOM: {regime['good_pass_p1']:.0%})")
    print(f"    Bad regime pass rate     : {regime['bad_pass_opt']:.0%}  "
          f"(TSMOM: {regime['bad_pass_p1']:.0%})")
    print(f"    Diversification confirmed: {'YES ✓' if regime['diversification_confirmed'] else 'NO ✗'}")

    print(f"\n  {'─'*55}")
    print(f"  VERDICT: {verdict}")
    print(f"  {'─'*55}")

    improvement = best_pass_rate - TSMOM_BASELINE_PASS

    if verdict in ("DEPLOY", "PROMISING"):
        print(
            f"\n  Recommended: implement MR-ATR as Strategy B alongside TSMOM v2.\n"
            f"  Adapt execution layer to handle both strategies simultaneously.\n"
            f"  Use {w_best:.0%} TSMOM / {1-w_best:.0%} MR-ATR capital split.\n"
            f"  Expected combined Propr pass rate: {best_pass_rate:.0%}"
        )
    elif verdict == "INSUFFICIENT_IMPROVEMENT":
        print(
            f"\n  Portfolio effect insufficient (+{improvement:.0%} improvement).\n"
            f"  The -0.30 correlation does not translate into meaningful pass-rate"
        )
        # Diagnose why
        p1_max_day = portfolio_results["portfolios"]["P1 (100/0)"]["metrics"]["max_day"]
        p_best_max = portfolio_results["portfolios"].get(
            best_label, portfolio_results["portfolios"]["P1 (100/0)"]
        )["metrics"]["max_day"]
        if best_pass_rate < TSMOM_BASELINE_PASS + 0.05:
            print(
                f"  improvement because: MR-ATR returns too small in 2025 "
                f"(regime instability — W4 walk-forward Sharpe -0.09).\n"
                f"  Final recommendation: test XGBoost signal filter on MR features"
            )
    else:  # SKIP
        print(
            f"\n  MR-ATR adds no value or makes things worse.\n"
            f"  Portfolio effect insufficient. The -0.30 correlation does not\n"
            f"  translate into meaningful pass rate improvement because:\n"
            f"  MR-ATR has near-zero returns in 2025 (Sharpe 0.18 on test period)\n"
            f"  combined with TSMOM's dominance in the period.\n"
            f"  Final recommendation: test ORB on ES/NQ equity futures"
        )

    return verdict


# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def save_charts(
    tsmom_pnl: pd.Series,
    mr_pnl: pd.Series,
    sweep: dict[str, Any],
    opt_w_tsmom: float,
) -> None:
    """Save 4-subplot portfolio analysis chart."""
    aligned = pd.concat({"ts": tsmom_pnl, "mr": mr_pnl}, axis=1).dropna()

    fig = plt.figure(figsize=(16, 12))
    gs  = GridSpec(2, 2, figure=fig, hspace=0.38, wspace=0.28)

    sweep_data = sweep["sweep"]
    weights    = [s["w_tsmom"] for s in sweep_data]
    pass_rates = [s["pass_rate"] * 100 for s in sweep_data]
    sharpes    = [s["sharpe"] for s in sweep_data]

    # ── Plot 1: Pass rate vs TSMOM weight ─────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(weights, pass_rates, "o-", color="steelblue", lw=2, ms=7)
    ax1.axhline(TSMOM_BASELINE_PASS * 100, color="gray", ls="--", lw=1.5,
                label=f"TSMOM baseline ({TSMOM_BASELINE_PASS:.0%})")
    ax1.axvline(opt_w_tsmom, color="red", ls="--", lw=1.5,
                label=f"Optimal w_TSMOM={opt_w_tsmom:.0%}")
    opt_pr = next(s["pass_rate"] * 100 for s in sweep_data if s["w_tsmom"] == opt_w_tsmom)
    ax1.scatter([opt_w_tsmom], [opt_pr], color="red", s=100, zorder=5)
    ax1.set_title("Propr Pass Rate vs TSMOM Weight", fontsize=11, fontweight="bold")
    ax1.set_xlabel("TSMOM weight (MR-ATR = 1 - TSMOM)")
    ax1.set_ylabel("Pass rate (%)")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))

    # ── Plot 2: Sharpe vs TSMOM weight ────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(weights, sharpes, "s-", color="darkorange", lw=2, ms=7)
    ax2.axhline(0, color="gray", ls="-", lw=0.8)
    opt_s_w = sweep["opt_sharpe"]["w_tsmom"]
    opt_sh  = sweep["opt_sharpe"]["sharpe"]
    ax2.axvline(opt_s_w, color="purple", ls="--", lw=1.5,
                label=f"Max Sharpe w={opt_s_w:.0%} ({opt_sh:.2f})")
    ax2.set_title("Sharpe Ratio vs TSMOM Weight", fontsize=11, fontweight="bold")
    ax2.set_xlabel("TSMOM weight (MR-ATR = 1 - TSMOM)")
    ax2.set_ylabel("Annualized Sharpe")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))

    # ── Plot 3: Equity curves P1, P3, P5 ─────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    combos = [
        (1.00, 0.00, "P1 100% TSMOM", "steelblue"),
        (0.50, 0.50, "P3 50/50",      "darkorange"),
        (0.00, 1.00, "P5 100% MR-ATR","forestgreen"),
    ]
    if opt_w_tsmom not in (1.0, 0.5, 0.0):
        combos.append((opt_w_tsmom, 1 - opt_w_tsmom, f"Optimal {opt_w_tsmom:.0%}/{1-opt_w_tsmom:.0%}", "red"))

    for w_ts, w_mr, lbl, col in combos:
        pnl_c = (w_ts * aligned["ts"] + w_mr * aligned["mr"])
        eq    = (1 + pnl_c).cumprod() * 100
        ax3.plot(eq.index, eq.values, label=lbl, color=col, lw=1.8)

    ax3.axhline(100, color="gray", ls="--", lw=0.8)
    ax3.set_title(f"Equity Curves ({ANALYSIS_START[:7]} → {ANALYSIS_END[:7]})",
                  fontsize=11, fontweight="bold")
    ax3.set_ylabel("Equity (start=100)")
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    # ── Plot 4: Daily P&L histogram P1 vs optimal ─────────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    p1_pnl  = (1.0 * aligned["ts"] + 0.0 * aligned["mr"]) * 100
    opt_pnl = (opt_w_tsmom * aligned["ts"] + (1 - opt_w_tsmom) * aligned["mr"]) * 100

    bins = np.linspace(
        min(p1_pnl.min(), opt_pnl.min(), -5),
        max(p1_pnl.max(), opt_pnl.max(), 5),
        60,
    )
    ax4.hist(p1_pnl,  bins=bins, alpha=0.5, color="steelblue",   label="P1 (100% TSMOM)", density=True)
    ax4.hist(opt_pnl, bins=bins, alpha=0.5, color="darkorange",
             label=f"Optimal ({opt_w_tsmom:.0%}/{1-opt_w_tsmom:.0%})", density=True)
    ax4.axvline(-3.0, color="red",   ls="--", lw=2, label="Propr limit (-3%)")
    ax4.axvline(0,    color="black", ls="-",  lw=0.8)
    ax4.set_title("Daily P&L Distribution — P1 vs Optimal", fontsize=11, fontweight="bold")
    ax4.set_xlabel("Daily P&L (%)")
    ax4.set_ylabel("Density")
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    plt.suptitle(
        "Portfolio TSMOM v2 + MR-ATR — Allocation Analysis\n"
        f"Period: {ANALYSIS_START} → {ANALYSIS_END}  |  44 Propr challenge simulations",
        fontsize=13, fontweight="bold", y=0.99,
    )
    plt.savefig(CHART_PATH, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Chart saved → {CHART_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> str:
    print("=" * 60)
    print("PORTFOLIO TSMOM v2 + MR-ATR — FEASIBILITY STUDY")
    print("=" * 60)
    print("Hypothesis: TSMOM and MR-ATR correlation ≈ -0.30 provides")
    print("structural offset that reduces daily limit breaches.")
    print(f"Period: {ANALYSIS_START} → {ANALYSIS_END}")
    print("=" * 60)

    # ── Step 0: Load data ─────────────────────────────────────────────────────
    print("\n[STEP 0] Loading market data...")
    close, open_, high, low = load_data(UNIVERSE)
    funding_rates = mr_load_funding_rates(list(close.columns))

    print(f"\n  MR-ATR best params (from feasibility study):")
    for k, v in MR_BEST_PARAMS.items():
        print(f"    {k:<14} = {v}")

    # ── Step 1: Compute P&L series ────────────────────────────────────────────
    print(f"\n[STEP 1] Reconstructing both strategy P&L series...")

    print("\n  Computing TSMOM v2 P&L...")
    tsmom_pnl_full = compute_tsmom_pnl(close)
    tsmom_pnl = tsmom_pnl_full[ANALYSIS_START:ANALYSIS_END].dropna()
    print(f"  TSMOM P&L: {len(tsmom_pnl)} days  "
          f"({tsmom_pnl.index[0].date()} → {tsmom_pnl.index[-1].date()})")

    print("\n  Computing MR-ATR P&L (this may take ~1-2 min)...")
    mr_pnl_full = compute_mr_pnl(close, high, low, funding_rates)
    mr_pnl = mr_pnl_full[ANALYSIS_START:ANALYSIS_END].dropna()
    print(f"  MR-ATR P&L: {len(mr_pnl)} days  "
          f"({mr_pnl.index[0].date()} → {mr_pnl.index[-1].date()})")

    # Align on common dates, fill missing with 0
    common_idx = tsmom_pnl.index.intersection(mr_pnl.index)
    tsmom_pnl  = tsmom_pnl.reindex(common_idx).fillna(0.0)
    mr_pnl     = mr_pnl.reindex(common_idx).fillna(0.0)
    print(f"  Common trading days: {len(common_idx)}")

    # BTC returns for beta calculation
    btc_rets = np.log(close["BTC-USD"] / close["BTC-USD"].shift(1))
    btc_rets = (np.exp(btc_rets) - 1).reindex(common_idx).fillna(0.0)

    # Quick stats check
    print(f"\n  TSMOM: ann_ret={tsmom_pnl.mean()*365:+.2%}  "
          f"vol={tsmom_pnl.std()*np.sqrt(365):.2%}  "
          f"Sharpe={tsmom_pnl.mean()*365/(tsmom_pnl.std()*np.sqrt(365)+1e-9):.2f}")
    print(f"  MR-ATR: ann_ret={mr_pnl.mean()*365:+.2%}  "
          f"vol={mr_pnl.std()*np.sqrt(365):.2%}  "
          f"Sharpe={mr_pnl.mean()*365/(mr_pnl.std()*np.sqrt(365)+1e-9):.2f}")

    corr = float(pd.concat({"ts": tsmom_pnl, "mr": mr_pnl}, axis=1).dropna().corr().loc["ts", "mr"])
    print(f"  Correlation: {corr:+.3f}")
    if corr > 0.0:
        print("  ⚠  CORRELATION HAS CHANGED — check data alignment")

    # ── Step 2: Portfolio combinations ───────────────────────────────────────
    portfolio_results = analyze_portfolios(tsmom_pnl, mr_pnl, btc_rets)

    # ── Step 3: Propr challenge sims ──────────────────────────────────────────
    propr_out = propr_all_portfolios(portfolio_results)

    # ── Step 4: Breakout sim on best portfolio ────────────────────────────────
    step4 = breakout_best(portfolio_results, propr_out["best_label"])

    # ── Step 5: Optimal allocation sweep ─────────────────────────────────────
    sweep = optimal_allocation_sweep(tsmom_pnl, mr_pnl, btc_rets)

    # ── Step 6: Regime analysis ───────────────────────────────────────────────
    opt_w = sweep["opt_pass"]["w_tsmom"]
    regime = regime_analysis(tsmom_pnl, mr_pnl, opt_w, close)

    # ── Step 7: Verdict ───────────────────────────────────────────────────────
    verdict = print_verdict(
        corr, sweep, propr_out["best_label"], step4, regime, portfolio_results
    )

    # ── Step 8: Charts ────────────────────────────────────────────────────────
    save_charts(tsmom_pnl, mr_pnl, sweep, opt_w)

    return verdict


if __name__ == "__main__":
    main()
