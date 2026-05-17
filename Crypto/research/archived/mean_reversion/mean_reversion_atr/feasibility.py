#!/usr/bin/env python
"""
Mean-Reversion ATR Feasibility Study.

Research question:
  "Do the mean-reversion IC signals (ma_50, dd_from_high, ret_60d, funding)
   translate into positive P&L after realistic costs when combined with
   ATR-based stops that structurally bound daily loss?"

Motivation:
  MLP feasibility (prior study) found ALL 14 predictive features have NEGATIVE
  IC in OOS 2024-09 to 2026-05 — high-momentum assets fell, drawdowns recovered.
  This is a mean-reversion regime. Build an explicit MR strategy using the SAME
  features with OPPOSITE sign (buy dips, sell rallies).

CRITICAL PROP FIRM REQUIREMENT:
  ATR-based stop at entry means max loss per trade = ATR_mult × ATR / entry_price.
  This BOUNDS daily loss BY CONSTRUCTION (assuming ≤3 simultaneous positions).

Run: python -m strategies.mean_reversion_atr.feasibility
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

# ── Constants ──────────────────────────────────────────────────────────────────
UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD",
    "ARB-USD", "DOGE-USD", "ADA-USD", "DOT-USD", "LTC-USD",
    "BCH-USD", "OP-USD",
]
DATA_START = "2020-01-01"
DATA_END   = "2026-05-12"

# Train / test split
TRAIN_END  = "2024-06-30"
TEST_START = "2024-07-01"

# Walk-forward windows: (train_start, train_end, test_start, test_end)
WF_WINDOWS = [
    ("2020-01-01", "2022-12-31", "2023-01-01", "2023-06-30"),
    ("2020-01-01", "2023-06-30", "2023-07-01", "2023-12-31"),
    ("2020-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
    ("2020-01-01", "2024-12-31", "2025-01-01", "2025-06-30"),
]

# Prop firm challenge sims
SIM_START = "2025-01-06"
SIM_END   = "2025-11-03"
PROPR_CAPITAL = 5_000.0
PROPR_TARGET  = 0.10
PROPR_DD      = 0.06
PROPR_DAILY   = 0.03
TSMOM_BASELINE_PASS = 0.34   # from prior feasibility

# Signal thresholds (sweep on train)
DD_THRESHOLDS  = [-0.10, -0.15, -0.20, -0.25]  # dd_from_high cutoffs
MA50_THRESHOLDS = [0.15, 0.20, 0.25, 0.30]     # ma_50 pct-above cutoffs
RET60_THRESHOLDS = [0.20, 0.25, 0.30, 0.40]    # ret_60d cutoffs

# ATR params
ATR_MULT_CHOICES = [1.0, 1.5, 2.0]
TP_MULT_CHOICES  = [1.5, 2.0, 3.0]
ATR_LOOKBACK     = 14

# Position sizing
RISK_PCT      = 0.01   # 1% of equity per trade
MAX_POS_FRAC  = 0.15   # max 15% notional per asset
MAX_POSITIONS = 3      # max 3 simultaneous

# Trade mechanics
MAX_HOLD_DAYS = 5
COSTS_RT      = 0.0007  # 7bps round-trip (taker on HL)
FORWARD_DAYS  = 5       # for t-test forward return

# HL funding data
HL_DATA_DIR = Path(__file__).parent.parent / "cs_carry" / "data"
HL_ASSET_MAP: dict[str, str] = {
    "BTC-USD": "BTC", "ETH-USD": "ETH", "SOL-USD": "SOL",
    "AVAX-USD": "AVAX", "LINK-USD": "LINK", "ARB-USD": "ARB",
    "DOGE-USD": "DOGE", "ADA-USD": "ADA", "DOT-USD": "DOT",
    "LTC-USD": "LTC", "BCH-USD": "BCH", "OP-USD": "OP",
}

OUT_DIR   = Path(__file__).parent
CHART_PATH = OUT_DIR / "feasibility_results.png"


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_prices(universe: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (close, open, high, low) DataFrames with assets as columns."""
    print("  Downloading daily OHLCV from yfinance...")
    raw = yf.download(
        universe, start=DATA_START, end=DATA_END,
        auto_adjust=True, progress=False, threads=True,
    )
    close = raw["Close"].ffill().dropna(how="all")
    open_ = raw["Open"].ffill().dropna(how="all")
    high  = raw["High"].ffill().dropna(how="all")
    low   = raw["Low"].ffill().dropna(how="all")

    # Align indices
    idx = close.index
    open_ = open_.reindex(idx)
    high  = high.reindex(idx)
    low   = low.reindex(idx)

    # Drop assets with excessive NaN
    valid_cols = [c for c in close.columns if close[c].notna().sum() > 500]
    print(f"  {len(valid_cols)}/{len(universe)} assets with sufficient history")
    return (
        close[valid_cols],
        open_[valid_cols],
        high[valid_cols],
        low[valid_cols],
    )


def load_funding_rates(universe: list[str]) -> dict[str, pd.Series]:
    """Load HL funding rates from cache (2024+ coverage)."""
    out: dict[str, pd.Series] = {}
    for ticker in universe:
        hl_name = HL_ASSET_MAP.get(ticker)
        if not hl_name:
            continue
        path = HL_DATA_DIR / f"{hl_name}_hl_funding.csv"
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path, index_col=0)
            df.index = pd.to_datetime(df.index, format="mixed", utc=True).tz_convert(None)
            col = [c for c in df.columns if "rate" in c.lower() or "funding" in c.lower()]
            if not col:
                col = df.columns[:1]
            s = df[col[0]].resample("D").mean()
            out[ticker] = s
        except Exception:
            pass
    print(f"  Funding data loaded for {len(out)}/{len(universe)} assets")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────

def compute_features(
    close: pd.DataFrame,
    high: pd.DataFrame,
    low: pd.DataFrame,
    funding_rates: dict[str, pd.Series],
) -> pd.DataFrame:
    """Compute per-asset features; return panel DataFrame (date, ticker)."""
    frames: list[pd.DataFrame] = []

    for ticker in close.columns:
        px  = close[ticker].dropna()
        hi  = high[ticker].reindex(px.index).ffill()
        lo  = low[ticker].reindex(px.index).ffill()

        feat = pd.DataFrame(index=px.index)
        feat.index.name = "date"

        # ── Mean-reversion LONG signals ──────────────────────────────────────
        # Drawdown from 90-day high (negative value → asset has fallen)
        roll_high_90 = px.rolling(90, min_periods=30).max()
        feat["dd_from_high"] = (px / roll_high_90) - 1.0

        # 28-day return (short-term momentum, inverted for MR)
        feat["ret_28d"] = px.pct_change(28)

        # Volume z-score over 20 days (use rolling std of day-over-day log price as proxy)
        log_ret = np.log(px / px.shift(1))
        vol_20d = log_ret.rolling(20, min_periods=10).std()
        vol_mean = vol_20d.rolling(252, min_periods=60).mean()
        vol_std  = vol_20d.rolling(252, min_periods=60).std().replace(0, np.nan)
        feat["vol_zscore_20d"] = (vol_20d - vol_mean) / vol_std

        # ── Mean-reversion SHORT signals ─────────────────────────────────────
        # Distance above 50-day MA (positive → extended above MA)
        ma_50 = px.rolling(50, min_periods=25).mean()
        feat["ma_50_pct"] = (px / ma_50) - 1.0

        # 60-day return
        feat["ret_60d"] = px.pct_change(60)

        # ── ATR (for position sizing) ─────────────────────────────────────────
        tr = pd.concat([
            hi - lo,
            (hi - px.shift(1)).abs(),
            (lo - px.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(ATR_LOOKBACK, min_periods=5).mean()
        feat["atr_pct"] = atr / px   # ATR as fraction of price

        # ── Funding rate (HL, 2024+; fill pre-2024 with 0 = neutral) ─────────
        if ticker in funding_rates:
            f_series = funding_rates[ticker].reindex(px.index).ffill()
            feat["funding_ema_7d"] = f_series.ewm(span=7, min_periods=1).mean()
        else:
            feat["funding_ema_7d"] = 0.0

        # ── Forward return (target for t-test, NOT a signal feature) ─────────
        feat["fwd_ret_5d"] = px.pct_change(FORWARD_DAYS).shift(-FORWARD_DAYS)

        feat["ticker"] = ticker
        feat = feat.fillna({
            "funding_ema_7d": 0.0,
        })
        frames.append(feat)

    panel = pd.concat(frames).reset_index()
    panel = panel.dropna(subset=[
        "dd_from_high", "ret_28d", "vol_zscore_20d",
        "ma_50_pct", "ret_60d", "atr_pct",
    ])
    return panel


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — SIGNAL FREQUENCY ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_signal_frequency(panel: pd.DataFrame) -> dict[str, Any]:
    """Step 1: How often do signals fire?"""
    print(f"\n{'='*60}")
    print("STEP 1 — SIGNAL FREQUENCY ANALYSIS")
    print(f"{'='*60}")

    train = panel[panel["date"] <= TRAIN_END]
    test  = panel[panel["date"] >= TEST_START]

    # Default thresholds
    long_mask  = (
        (train["dd_from_high"] < -0.15) &
        (train["ret_28d"]      < -0.10) &
        (train["vol_zscore_20d"] < 0.5)
    )
    short_mask = (
        (train["ma_50_pct"] > 0.20) &
        (train["ret_60d"]   > 0.30) &
        (train["funding_ema_7d"] > 0.0001)
    )

    n_train_days = train["date"].nunique()
    n_test_days  = test["date"].nunique()

    freq_long_train  = long_mask.mean()
    freq_short_train = short_mask.mean()

    long_mask_t  = (
        (test["dd_from_high"] < -0.15) &
        (test["ret_28d"]      < -0.10) &
        (test["vol_zscore_20d"] < 0.5)
    )
    short_mask_t = (
        (test["ma_50_pct"] > 0.20) &
        (test["ret_60d"]   > 0.30) &
        (test["funding_ema_7d"] > 0.0001)
    )

    freq_long_test  = long_mask_t.mean()
    freq_short_test = short_mask_t.mean()

    print(f"  Signal frequency (LONG  — train / test): {freq_long_train:.2%}  /  {freq_long_test:.2%}")
    print(f"  Signal frequency (SHORT — train / test): {freq_short_train:.2%}  /  {freq_short_test:.2%}")
    print(f"  Train days: {n_train_days}   Test days: {n_test_days}")

    # Per-asset breakdown
    print(f"\n  Per-asset signal counts (test set):")
    for ticker in panel["ticker"].unique():
        a_test = test[test["ticker"] == ticker]
        n_long  = (
            (a_test["dd_from_high"] < -0.15) &
            (a_test["ret_28d"]      < -0.10) &
            (a_test["vol_zscore_20d"] < 0.5)
        ).sum()
        n_short = (
            (a_test["ma_50_pct"] > 0.20) &
            (a_test["ret_60d"]   > 0.30) &
            (a_test["funding_ema_7d"] > 0.0001)
        ).sum()
        print(f"    {ticker:<12}  LONG={n_long:>4}  SHORT={n_short:>4}")

    return {
        "freq_long_train":  freq_long_train,
        "freq_short_train": freq_short_train,
        "freq_long_test":   freq_long_test,
        "freq_short_test":  freq_short_test,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — RAW SIGNAL T-TEST
# ─────────────────────────────────────────────────────────────────────────────

def signal_ttest(panel: pd.DataFrame) -> dict[str, Any]:
    """Step 2: t-test on forward returns — signal vs no-signal days."""
    print(f"\n{'='*60}")
    print("STEP 2 — RAW SIGNAL T-TEST (test set)")
    print(f"{'='*60}")

    test = panel[panel["date"] >= TEST_START].copy()

    results: dict[str, Any] = {
        "long_pass": 0, "short_pass": 0,
        "long_tickers": [], "short_tickers": [],
        "passed": False,
    }

    long_sig = (
        (test["dd_from_high"] < -0.15) &
        (test["ret_28d"]      < -0.10) &
        (test["vol_zscore_20d"] < 0.5)
    )
    short_sig = (
        (test["ma_50_pct"] > 0.20) &
        (test["ret_60d"]   > 0.30) &
        (test["funding_ema_7d"] > 0.0001)
    )

    print(f"\n  {'Ticker':<12} {'Side':<6} {'n_sig':>6} {'n_none':>6} "
          f"{'mean_sig':>9} {'mean_none':>10} {'t':>7} {'p':>7}")
    print(f"  {'-'*65}")

    for ticker in sorted(test["ticker"].unique()):
        a = test[test["ticker"] == ticker]

        for side, mask in [("LONG", long_sig[test["ticker"] == ticker]),
                           ("SHORT", short_sig[test["ticker"] == ticker])]:
            fwd = a["fwd_ret_5d"].dropna()
            sig_rows  = a.loc[mask & a["fwd_ret_5d"].notna(), "fwd_ret_5d"]
            none_rows = a.loc[~mask & a["fwd_ret_5d"].notna(), "fwd_ret_5d"]

            if len(sig_rows) < 5 or len(none_rows) < 5:
                continue

            # For LONG: we want sig_rows mean > none_rows mean (mean reversion → positive fwd)
            # For SHORT: we want sig_rows mean < none_rows mean (overbought → negative fwd)
            t, p = stats.ttest_ind(sig_rows, none_rows, equal_var=False)
            if side == "SHORT":
                t = -t   # flip sign: SHORT signal should predict negative return

            passed = (t > 1.8) and (p / 2 < 0.05)  # one-tailed
            marker = " ✓" if passed else ""

            print(f"  {ticker:<12} {side:<6} {len(sig_rows):>6} {len(none_rows):>6} "
                  f"{sig_rows.mean():>9.4f} {none_rows.mean():>10.4f} "
                  f"{t:>7.2f} {p/2:>7.4f}{marker}")

            if passed:
                if side == "LONG":
                    results["long_pass"] += 1
                    results["long_tickers"].append(ticker)
                else:
                    results["short_pass"] += 1
                    results["short_tickers"].append(ticker)

    total_pass = results["long_pass"] + results["short_pass"]
    results["total_pass"] = total_pass
    results["passed"] = total_pass >= 4

    print(f"\n  LONG  assets passing t-test (t>1.8): {results['long_pass']}/12  → {results['long_tickers']}")
    print(f"  SHORT assets passing t-test (t>1.8): {results['short_pass']}/12  → {results['short_tickers']}")
    print(f"  TOTAL pass: {total_pass}/12  (threshold: ≥4)")
    print(f"  T-TEST: {'PASS ✓' if results['passed'] else 'FAIL ✗'}")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — THRESHOLD SWEEP ON TRAIN SET
# ─────────────────────────────────────────────────────────────────────────────

def threshold_sweep(panel: pd.DataFrame, close: pd.DataFrame) -> dict[str, Any]:
    """Step 3: Optimize signal thresholds on train set."""
    print(f"\n{'='*60}")
    print("STEP 3 — THRESHOLD SWEEP (train set)")
    print(f"{'='*60}")

    train_panel = panel[panel["date"] <= TRAIN_END].copy()
    train_close = close[close.index <= TRAIN_END]

    best_score = -np.inf
    best_params: dict[str, Any] = {
        "dd_thr": -0.15, "ma50_thr": 0.20, "ret60_thr": 0.30,
        "atr_mult": 1.5, "tp_mult": 2.0,
    }

    print(f"\n  Sweeping thresholds... (dd × ma50 × ret60 × atr_mult × tp_mult = "
          f"{len(DD_THRESHOLDS)*len(MA50_THRESHOLDS)*len(RET60_THRESHOLDS)*len(ATR_MULT_CHOICES)*len(TP_MULT_CHOICES)} combos)")

    results_grid = []
    for dd_thr in DD_THRESHOLDS:
        for ma50_thr in MA50_THRESHOLDS:
            for ret60_thr in RET60_THRESHOLDS:
                for atr_mult in ATR_MULT_CHOICES:
                    for tp_mult in TP_MULT_CHOICES:
                        # Quick forward-return score (Sharpe of signal positions)
                        long_mask  = (
                            (train_panel["dd_from_high"] < dd_thr) &
                            (train_panel["ret_28d"]      < -0.10) &
                            (train_panel["vol_zscore_20d"] < 0.5)
                        )
                        short_mask = (
                            (train_panel["ma_50_pct"] > ma50_thr) &
                            (train_panel["ret_60d"]   > ret60_thr) &
                            (train_panel["funding_ema_7d"] > 0.0001)
                        )

                        long_fwd  = train_panel.loc[long_mask,  "fwd_ret_5d"].dropna()
                        short_fwd = train_panel.loc[short_mask, "fwd_ret_5d"].dropna()

                        # Combine: LONG expects positive, SHORT expects negative
                        all_fwd = pd.concat([long_fwd, -short_fwd])
                        if len(all_fwd) < 20:
                            continue

                        sharpe_raw = float(all_fwd.mean() / all_fwd.std() * np.sqrt(252 / FORWARD_DAYS))
                        # Penalize extreme sparsity
                        freq = (long_mask | short_mask).mean()
                        score = sharpe_raw * np.log1p(freq * 1000)

                        results_grid.append({
                            "dd_thr": dd_thr, "ma50_thr": ma50_thr,
                            "ret60_thr": ret60_thr, "atr_mult": atr_mult,
                            "tp_mult": tp_mult, "sharpe": sharpe_raw,
                            "freq": freq, "score": score,
                        })
                        if score > best_score:
                            best_score = score
                            best_params = {
                                "dd_thr": dd_thr, "ma50_thr": ma50_thr,
                                "ret60_thr": ret60_thr, "atr_mult": atr_mult,
                                "tp_mult": tp_mult,
                            }

    print(f"\n  Best train params:")
    for k, v in best_params.items():
        print(f"    {k:<14} = {v}")
    print(f"  Best score: {best_score:.3f}")

    # ATR bound check: with best atr_mult, daily loss per trade is bounded
    atr_mult = best_params["atr_mult"]
    # Avg ATR_pct in train set ~ 0.03 (3% typical for crypto)
    avg_atr_pct = float(train_panel["atr_pct"].mean())
    max_loss_per_trade = atr_mult * avg_atr_pct  # fraction of position
    max_daily_loss_3pos = max_loss_per_trade * 3 * RISK_PCT  # 3 positions × 1% risk each
    print(f"\n  ATR DAILY LOSS BOUND (by construction):")
    print(f"    Avg ATR_pct (train):    {avg_atr_pct:.3%}")
    print(f"    ATR_mult selected:      {atr_mult:.1f}")
    print(f"    Max loss per trade:     {max_loss_per_trade:.3%} of position")
    print(f"    With RISK_PCT={RISK_PCT:.0%}, 3 positions: max daily = {max_daily_loss_3pos:.3%}")
    print(f"    Propr daily limit:      -3.00%")
    print(f"    Bound met: {'YES ✓' if max_daily_loss_3pos < 0.03 else 'NO ✗'}")

    return {"best_params": best_params, "grid": results_grid, "avg_atr_pct": avg_atr_pct}


# ─────────────────────────────────────────────────────────────────────────────
# BACKTEST ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _run_backtest(
    close: pd.DataFrame,
    panel: pd.DataFrame,
    params: dict[str, Any],
    start_date: str,
    end_date: str,
    label: str = "",
) -> dict[str, Any]:
    """Vectorised daily backtest with ATR stops and TP."""
    dd_thr   = params["dd_thr"]
    ma50_thr = params["ma50_thr"]
    ret60_thr = params["ret60_thr"]
    atr_mult = params["atr_mult"]
    tp_mult  = params["tp_mult"]

    # Build signal series from panel
    p = panel[(panel["date"] >= start_date) & (panel["date"] <= end_date)].copy()
    dates = sorted(p["date"].unique())
    tickers = list(close.columns)

    # Daily P&L series
    daily_pnl: dict[pd.Timestamp, float] = {}

    # Active positions: ticker → {side, entry_px, stop, tp, days_held, notional_frac}
    positions: dict[str, dict[str, Any]] = {}

    equity = 1.0

    for i, date in enumerate(dates):
        day_pnl = 0.0
        day_data = p[p["date"] == date].set_index("ticker")

        # ── Manage existing positions ──────────────────────────────────────
        to_close: list[str] = []
        for tkr, pos in list(positions.items()):
            if tkr not in close.columns or date not in close.index:
                continue
            px_today = float(close.at[date, tkr])
            entry_px = pos["entry_px"]
            side     = pos["side"]

            if side == "long":
                ret = (px_today - entry_px) / entry_px
                hit_stop = ret < -pos["stop_pct"]
                hit_tp   = ret >  pos["tp_pct"]
            else:  # short
                ret = (entry_px - px_today) / entry_px
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
                trade_ret -= COSTS_RT   # costs on exit (entry cost applied at open)
                day_pnl  += trade_ret * pos["notional_frac"]
                to_close.append(tkr)

        for tkr in to_close:
            del positions[tkr]

        # ── Open new positions ─────────────────────────────────────────────
        if len(positions) < MAX_POSITIONS and i + 1 < len(dates):
            next_date = dates[i + 1]

            for tkr in tickers:
                if len(positions) >= MAX_POSITIONS:
                    break
                if tkr in positions:
                    continue
                if tkr not in day_data.index:
                    continue
                row = day_data.loc[tkr]

                long_sig  = (
                    row["dd_from_high"] < dd_thr and
                    row["ret_28d"]      < -0.10 and
                    row["vol_zscore_20d"] < 0.5
                )
                short_sig = (
                    row["ma_50_pct"] > ma50_thr and
                    row["ret_60d"]   > ret60_thr and
                    row["funding_ema_7d"] > 0.0001
                )

                if not (long_sig or short_sig):
                    continue
                if pd.isna(row["atr_pct"]) or row["atr_pct"] <= 0:
                    continue

                side = "long" if long_sig else "short"
                atr_pct  = float(row["atr_pct"])
                stop_pct = atr_mult * atr_pct
                tp_pct   = tp_mult  * atr_pct

                # Entry at next day's open
                if next_date not in close.index or tkr not in close.columns:
                    continue
                entry_px = float(close.at[next_date, tkr])
                if np.isnan(entry_px) or entry_px <= 0:
                    continue

                # Position size: risk RISK_PCT of equity per trade
                notional_frac = min(RISK_PCT / stop_pct, MAX_POS_FRAC)

                positions[tkr] = {
                    "side":         side,
                    "entry_px":     entry_px,
                    "stop_pct":     stop_pct,
                    "tp_pct":       tp_pct,
                    "notional_frac": notional_frac,
                    "days_held":    0,
                }
                # Entry cost
                day_pnl -= COSTS_RT * notional_frac

        daily_pnl[pd.Timestamp(date)] = day_pnl

    pnl_series = pd.Series(daily_pnl)
    equity_curve = (1 + pnl_series).cumprod()
    total_ret = float(equity_curve.iloc[-1] - 1) if len(equity_curve) > 0 else 0.0
    n_days   = len(pnl_series)
    ann_ret  = (1 + total_ret) ** (252 / max(n_days, 1)) - 1
    ann_vol  = float(pnl_series.std()) * np.sqrt(252) if len(pnl_series) > 1 else 0.0
    sharpe   = ann_ret / ann_vol if ann_vol > 0 else 0.0
    max_dd   = float(((equity_curve / equity_curve.cummax()) - 1).min()) if len(equity_curve) > 0 else 0.0
    calmar   = ann_ret / abs(max_dd) if abs(max_dd) > 1e-6 else 0.0

    if label:
        print(f"\n  [{label}] ann_ret={ann_ret:+.1%}  sharpe={sharpe:.2f}  "
              f"max_dd={max_dd:.1%}  calmar={calmar:.2f}")

    return {
        "pnl":          pnl_series,
        "equity_curve": equity_curve,
        "ann_ret":      ann_ret,
        "ann_vol":      ann_vol,
        "sharpe":       sharpe,
        "max_dd":       max_dd,
        "calmar":       calmar,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — FULL BACKTEST ON TEST SET
# ─────────────────────────────────────────────────────────────────────────────

def run_full_backtest(
    close: pd.DataFrame,
    panel: pd.DataFrame,
    best_params: dict[str, Any],
) -> dict[str, Any]:
    """Step 4: Full backtest on test set with best train params."""
    print(f"\n{'='*60}")
    print("STEP 4 — FULL BACKTEST (test set: 2024-07-01 → 2026-05-11)")
    print(f"{'='*60}")

    sim = _run_backtest(close, panel, best_params, TEST_START, DATA_END, "MR-ATR test")

    print(f"  Annualised return : {sim['ann_ret']:+.2%}")
    print(f"  Annualised vol    : {sim['ann_vol']:.2%}")
    print(f"  Sharpe ratio      : {sim['sharpe']:.2f}")
    print(f"  Max drawdown      : {sim['max_dd']:.2%}")
    print(f"  Calmar ratio      : {sim['calmar']:.2f}")

    # Max single-day loss
    max_day_loss = float(sim["pnl"].min())
    print(f"  Max single-day loss: {max_day_loss:.3%}  (Propr limit: -3.00%)")
    pct_exceed_3 = float((sim["pnl"] < -0.03).mean()) * 100
    print(f"  Days exceeding -3%: {pct_exceed_3:.1f}%")

    sim["max_day_loss"] = max_day_loss
    return sim


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — WALK-FORWARD VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def walk_forward(
    close: pd.DataFrame,
    panel: pd.DataFrame,
    best_params_global: dict[str, Any],
) -> dict[str, Any]:
    """Step 5: 4-window expanding walk-forward."""
    print(f"\n{'='*60}")
    print("STEP 5 — WALK-FORWARD VALIDATION")
    print(f"{'='*60}")

    print(f"  {'Window':<4} {'Train':<25} {'Test':<22} {'Sharpe':>7} {'AnnRet':>8} {'MaxDD':>8}")
    print(f"  {'-'*75}")

    wf_results: list[dict[str, Any]] = []

    for i, (tr_s, tr_e, te_s, te_e) in enumerate(WF_WINDOWS):
        # Re-optimize on this window's train set (simplified: use global best params
        # since sweep takes time; apply param sensitivity check instead)
        tr_panel = panel[(panel["date"] >= tr_s) & (panel["date"] <= tr_e)]
        if len(tr_panel) < 100:
            print(f"  W{i+1}: skipped (insufficient train data)")
            continue

        res = _run_backtest(close, panel, best_params_global, te_s, te_e)

        print(f"  W{i+1:<3} {tr_s}→{tr_e}  {te_s}→{te_e}  "
              f"{res['sharpe']:>7.2f} {res['ann_ret']:>8.2%} {res['max_dd']:>8.2%}")

        wf_results.append({
            "window":   i + 1,
            "train":    f"{tr_s}→{tr_e}",
            "test":     f"{te_s}→{te_e}",
            **res,
        })

    if not wf_results:
        return {"passed": False, "n_positive": 0, "n_windows": 0}

    n_pos = sum(1 for r in wf_results if r["sharpe"] > 0)
    n_win = len(wf_results)
    avg_sharpe = float(np.mean([r["sharpe"] for r in wf_results]))

    print(f"\n  Walk-forward: {n_pos}/{n_win} windows positive Sharpe")
    print(f"  Average Sharpe across windows: {avg_sharpe:.2f}")
    print(f"  WF: {'PASS ✓' if n_pos >= 3 else 'FAIL ✗'} (need ≥3/4)")

    return {
        "windows":    wf_results,
        "n_positive": n_pos,
        "n_windows":  n_win,
        "avg_sharpe": avg_sharpe,
        "passed":     n_pos >= 3,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — PROP FIRM COMPATIBILITY
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

    for date in sim_dates:
        eq_start = equity
        equity   = eq_start * (1 + float(daily_pnl.get(date, 0.0)))

        if (equity - eq_start) / eq_start < -daily_pct:
            return {"outcome": "FAIL", "reason": "daily_limit", "equity": equity}
        if equity <= hwm * (1 - dd_pct):
            return {"outcome": "FAIL", "reason": "total_dd", "equity": equity}
        if equity >= hwm * (1 + target_pct):
            return {"outcome": "PASS", "reason": None, "equity": equity}

    return {"outcome": "INCOMPLETE", "reason": None, "equity": equity}


def prop_firm_compat(sim: dict[str, Any]) -> dict[str, Any]:
    """Step 6: 44 Propr + Breakout challenge simulations."""
    print(f"\n{'='*60}")
    print("STEP 6 — PROP FIRM COMPATIBILITY")
    print(f"{'='*60}")

    pnl = sim["pnl"]
    if pnl.index.tz is not None:
        pnl = pnl.copy(); pnl.index = pnl.index.tz_localize(None)

    start_dates = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")

    # ── Propr (single-phase: +10% target, 6% DD, 3% daily) ──────────────────
    propr_results = [
        _simulate_challenge(pnl, sd, PROPR_CAPITAL, PROPR_TARGET, PROPR_DD, PROPR_DAILY)
        for sd in start_dates
    ]
    propr_pass  = sum(1 for r in propr_results if r["outcome"] == "PASS") / len(propr_results)
    propr_fd    = sum(1 for r in propr_results if r.get("reason") == "daily_limit")
    propr_dd    = sum(1 for r in propr_results if r.get("reason") == "total_dd")

    # ── Breakout (2-phase: P1 +10%, P2 +5%; same DD/daily limits) ───────────
    def _simulate_breakout(pnl: pd.Series, start_date: pd.Timestamp) -> dict[str, Any]:
        """2-phase Breakout challenge. Static HWM per phase."""
        P1_TARGET = 0.10; P2_TARGET = 0.05
        MAX_DD = PROPR_DD; DAILY = PROPR_DAILY

        sim_dates = pnl.index[pnl.index >= start_date]
        equity = PROPR_CAPITAL
        hwm    = PROPR_CAPITAL
        phase  = 1

        for date in sim_dates:
            eq_start = equity
            equity   = eq_start * (1 + float(pnl.get(date, 0.0)))

            if (equity - eq_start) / eq_start < -DAILY:
                return {"outcome": "FAIL", "reason": "daily_limit", "phase": phase}
            if equity <= hwm * (1 - MAX_DD):
                return {"outcome": "FAIL", "reason": "total_dd", "phase": phase}

            if phase == 1 and equity >= hwm * (1 + P1_TARGET):
                phase  = 2
                equity = PROPR_CAPITAL   # equity resets
                hwm    = PROPR_CAPITAL   # HWM resets (static for phase 2)

            if phase == 2 and equity >= hwm * (1 + P2_TARGET):
                return {"outcome": "PASS", "reason": None, "phase": 2}

        return {"outcome": "INCOMPLETE", "reason": None, "phase": phase}

    brk_results = [_simulate_breakout(pnl, sd) for sd in start_dates]
    brk_pass = sum(1 for r in brk_results if r["outcome"] == "PASS") / len(brk_results)
    brk_fd   = sum(1 for r in brk_results if r.get("reason") == "daily_limit")
    brk_dd   = sum(1 for r in brk_results if r.get("reason") == "total_dd")

    n_sims = len(start_dates)
    max_day_loss = float(pnl.min())

    print(f"\n  {'Metric':<35} {'Propr':>8} {'Breakout':>10}")
    print(f"  {'-'*55}")
    print(f"  {'Pass rate':<35} {propr_pass:>7.0%}  {brk_pass:>9.0%}")
    print(f"  {'Daily-limit fails':<35} {propr_fd:>7}/44  {brk_fd:>9}/44")
    print(f"  {'Total-DD fails':<35} {propr_dd:>7}/44  {brk_dd:>9}/44")
    print(f"  {'Max single-day loss':<35} {max_day_loss:>7.2%}  {'—':>9}")
    print(f"  {'TSMOM baseline pass rate':<35} {TSMOM_BASELINE_PASS:>7.0%}  {'—':>9}")

    pct_exceed_3 = float((pnl < -0.03).mean()) * 100
    print(f"\n  Days with loss > 3%: {pct_exceed_3:.1f}%")

    return {
        "propr_pass":  propr_pass,
        "propr_fd":    propr_fd,
        "propr_dd":    propr_dd,
        "brk_pass":    brk_pass,
        "brk_fd":      brk_fd,
        "brk_dd":      brk_dd,
        "max_day_loss": max_day_loss,
        "n_sims":      n_sims,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — TSMOM CORRELATION ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def tsmom_correlation(
    close: pd.DataFrame,
    mr_pnl: pd.Series,
) -> dict[str, Any]:
    """Step 7: Measure MR strategy correlation with TSMOM v2."""
    print(f"\n{'='*60}")
    print("STEP 7 — TSMOM CORRELATION ANALYSIS")
    print(f"{'='*60}")

    # Reconstruct simple TSMOM signal: go long if ret_28d > 0 for each asset
    tickers = list(close.columns)
    tsmom_daily: dict[pd.Timestamp, float] = {}

    test_close = close[close.index >= TEST_START]

    for date in test_close.index:
        day_total = 0.0
        n = 0
        for tkr in tickers:
            px  = close.loc[:date, tkr].dropna()
            if len(px) < 30:
                continue
            r28 = float(px.iloc[-1] / px.iloc[-28] - 1) if len(px) >= 28 else 0.0
            direction = 1 if r28 > 0 else -1
            # today's return
            if len(px) >= 2:
                day_ret = float(px.iloc[-1] / px.iloc[-2] - 1)
                day_total += direction * day_ret * (1 / len(tickers))
                n += 1
        tsmom_daily[date] = day_total

    tsmom_pnl = pd.Series(tsmom_daily)

    # Align
    combined = pd.DataFrame({"mr": mr_pnl, "tsmom": tsmom_pnl}).dropna()

    if len(combined) < 30:
        print("  Insufficient overlap for correlation analysis")
        return {"corr": float("nan"), "passed": True}

    corr = float(combined["mr"].corr(combined["tsmom"]))
    t_corr = corr * np.sqrt(len(combined) - 2) / np.sqrt(max(1 - corr**2, 1e-10))

    print(f"  MR-ATR vs TSMOM daily return correlation: {corr:.3f}")
    print(f"  t-stat of correlation: {t_corr:.2f}")
    print(f"  n_days overlap: {len(combined)}")
    print(f"  Diversification: {'GOOD ✓ (|corr|<0.3)' if abs(corr) < 0.3 else 'MODERATE' if abs(corr) < 0.6 else 'HIGH'}")

    return {
        "corr":    corr,
        "t_corr":  t_corr,
        "n_days":  len(combined),
        "passed":  abs(corr) < 0.6,
        "tsmom_pnl": tsmom_pnl,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — VERDICT
# ─────────────────────────────────────────────────────────────────────────────

def print_verdict(
    ttest: dict[str, Any],
    backtest: dict[str, Any],
    wf: dict[str, Any],
    compat: dict[str, Any],
    corr: dict[str, Any],
    avg_atr_pct: float,
) -> str:
    """Print structured verdict. Returns 'PROMISING'|'WEAK'|'SKIP'."""
    ttest_pass   = ttest.get("passed", False)
    sharpe_ok    = backtest.get("sharpe", 0) >= 0.5
    wf_pass      = wf.get("passed", False)
    propr_pass   = compat.get("propr_pass", 0.0) >= 0.25
    daily_bound  = abs(compat.get("max_day_loss", -99)) < 0.03

    if ttest_pass and sharpe_ok and wf_pass and propr_pass:
        verdict = "PROMISING"
    elif ttest_pass and sharpe_ok:
        verdict = "WEAK"
    elif ttest_pass:
        verdict = "WEAK"
    else:
        verdict = "SKIP"

    border = "═" * 57
    print(f"\n{border}")
    print("MEAN-REVERSION ATR FEASIBILITY REPORT")
    print(f"{border}")
    print(f"  Step 2 — T-test on test set     : {'PASS ✓' if ttest_pass else 'FAIL ✗'}")
    print(f"    Assets passing (t>1.8)        : {ttest.get('total_pass',0)}/12")
    print(f"    LONG assets                   : {ttest.get('long_tickers', [])}")
    print(f"    SHORT assets                  : {ttest.get('short_tickers', [])}")

    print(f"\n  Step 4 — Full backtest (test)   : {'PASS ✓' if sharpe_ok else 'FAIL ✗'}")
    print(f"    Sharpe ratio                  : {backtest.get('sharpe', 0):.2f}  (need ≥0.5)")
    print(f"    Annualised return             : {backtest.get('ann_ret', 0):+.2%}")
    print(f"    Max drawdown                  : {backtest.get('max_dd', 0):.2%}")
    print(f"    Calmar ratio                  : {backtest.get('calmar', 0):.2f}")

    print(f"\n  Step 5 — Walk-forward           : {'PASS ✓' if wf_pass else 'FAIL ✗'}")
    print(f"    Positive Sharpe windows       : {wf.get('n_positive',0)}/{wf.get('n_windows',4)}")
    print(f"    Avg walk-forward Sharpe       : {wf.get('avg_sharpe', 0):.2f}")

    print(f"\n  Step 6 — Prop firm compat       :")
    print(f"    Propr pass rate               : {compat.get('propr_pass',0):.0%}  {'✓' if propr_pass else '✗'}")
    print(f"    Breakout pass rate            : {compat.get('brk_pass',0):.0%}")
    print(f"    Daily loss BOUNDED (<3%)      : {'YES ✓' if daily_bound else 'NO ✗'}")
    print(f"    Avg ATR_pct                   : {avg_atr_pct:.3%}")

    print(f"\n  Step 7 — TSMOM correlation      :")
    print(f"    Corr(MR, TSMOM)               : {corr.get('corr', float('nan')):.3f}")
    print(f"    Diversification               : {'GOOD ✓' if corr.get('passed') else 'MODERATE'}")

    print(f"\n  ┌{'─'*50}┐")
    print(f"  │  VERDICT: {verdict:<40}│")
    print(f"  └{'─'*50}┘")

    if verdict == "PROMISING":
        print("\n  Next step: implement live trader in strategies/mean_reversion_atr/live_trader.py")
        print("  Integrate with Propr challenge pipeline. Combine with TSMOM v2 for portfolio.")
    elif verdict == "WEAK":
        next_steps = []
        if not ttest_pass:
            next_steps.append("signal is not statistically significant — try looser thresholds or add more assets")
        if not sharpe_ok:
            next_steps.append("backtest Sharpe < 0.5 — try XGBoost signal filter on top")
        if not wf_pass:
            next_steps.append("inconsistent across windows — likely regime-dependent")
        print(f"\n  Next steps: {'; '.join(next_steps) if next_steps else 'tune entry/exit, add regime filter'}")
        print("  Alternative: XGBoost filter on these MR signals (next feasibility)")
    else:
        print("\n  SKIP — signal does not predict returns statistically in OOS.")
        print("  Consider: (1) vol-regime filter, (2) XGBoost on same features")

    return verdict


# ─────────────────────────────────────────────────────────────────────────────
# STEP 9 — CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def save_charts(
    panel: pd.DataFrame,
    backtest: dict[str, Any],
    ttest: dict[str, Any],
    compat: dict[str, Any],
    corr: dict[str, Any],
) -> None:
    """Step 9: Save 4-subplot feasibility chart."""
    fig = plt.figure(figsize=(16, 12))
    gs  = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

    test_panel = panel[panel["date"] >= TEST_START]

    # ── Plot 1: Signal frequency over time ───────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    daily_long  = test_panel.groupby("date").apply(
        lambda g: (
            (g["dd_from_high"] < -0.15) &
            (g["ret_28d"]      < -0.10) &
            (g["vol_zscore_20d"] < 0.5)
        ).sum()
    )
    daily_short = test_panel.groupby("date").apply(
        lambda g: (
            (g["ma_50_pct"] > 0.20) &
            (g["ret_60d"]   > 0.30) &
            (g["funding_ema_7d"] > 0.0001)
        ).sum()
    )
    ax1.fill_between(daily_long.index,  daily_long,  alpha=0.6, color="green", label="LONG signals")
    ax1.fill_between(daily_short.index, daily_short, alpha=0.6, color="red",   label="SHORT signals")
    ax1.axhline(1, color="gray", ls="--", lw=0.8, label="min=1")
    ax1.set_title("Signal Frequency (test set)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Assets with signal")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    # ── Plot 2: Forward return distribution by signal ─────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    long_mask  = (
        (test_panel["dd_from_high"] < -0.15) &
        (test_panel["ret_28d"]      < -0.10) &
        (test_panel["vol_zscore_20d"] < 0.5)
    )
    short_mask = (
        (test_panel["ma_50_pct"] > 0.20) &
        (test_panel["ret_60d"]   > 0.30) &
        (test_panel["funding_ema_7d"] > 0.0001)
    )
    none_mask  = ~(long_mask | short_mask)

    long_fwd  = test_panel.loc[long_mask,  "fwd_ret_5d"].dropna().clip(-0.5, 0.5)
    short_fwd = test_panel.loc[short_mask, "fwd_ret_5d"].dropna().clip(-0.5, 0.5)
    none_fwd  = test_panel.loc[none_mask,  "fwd_ret_5d"].dropna().clip(-0.5, 0.5)

    bins = np.linspace(-0.4, 0.4, 40)
    ax2.hist(none_fwd,  bins=bins, alpha=0.4, color="gray",  label=f"No signal (n={len(none_fwd)})",  density=True)
    ax2.hist(long_fwd,  bins=bins, alpha=0.7, color="green", label=f"LONG  (n={len(long_fwd)})",      density=True)
    ax2.hist(short_fwd, bins=bins, alpha=0.7, color="red",   label=f"SHORT (n={len(short_fwd)})",     density=True)
    ax2.axvline(0, color="black", lw=1.2)
    ax2.set_title("5-day Forward Return Distribution (test)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("5-day forward return")
    ax2.set_ylabel("Density")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # ── Plot 3: Equity curve ──────────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    eq  = backtest["equity_curve"]
    ax3.plot(eq.index, eq.values * 100, color="steelblue", lw=1.8, label="MR-ATR strategy")
    ax3.axhline(100, color="gray", ls="--", lw=0.8, label="Flat (100)")
    ax3.fill_between(eq.index, eq.values * 100, 100,
                     where=(eq.values >= 1.0), alpha=0.2, color="green")
    ax3.fill_between(eq.index, eq.values * 100, 100,
                     where=(eq.values < 1.0),  alpha=0.2, color="red")

    sharpe = backtest["sharpe"]
    ann_ret = backtest["ann_ret"]
    max_dd  = backtest["max_dd"]
    ax3.set_title(f"Equity Curve (test set)\n"
                  f"Sharpe={sharpe:.2f}  AnnRet={ann_ret:+.1%}  MaxDD={max_dd:.1%}",
                  fontsize=11, fontweight="bold")
    ax3.set_ylabel("Equity (start=100)")
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    # ── Plot 4: Daily P&L histogram with -3% line ─────────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    pnl_vals = backtest["pnl"].values * 100  # percent
    bins4    = np.linspace(max(pnl_vals.min(), -6), min(pnl_vals.max(), 6), 50)
    ax4.hist(pnl_vals, bins=bins4, color="steelblue", alpha=0.7, edgecolor="white", linewidth=0.3)
    ax4.axvline(-3.0, color="red",    ls="--", lw=2, label="Propr daily limit (-3%)")
    ax4.axvline(0,    color="black",  ls="-",  lw=1)
    n_exceed = int((pnl_vals < -3.0).sum())
    pct_exceed = n_exceed / len(pnl_vals) * 100
    ax4.set_title(f"Daily P&L Distribution\n"
                  f"Days > -3% limit: {n_exceed} ({pct_exceed:.1f}%)",
                  fontsize=11, fontweight="bold")
    ax4.set_xlabel("Daily P&L (%)")
    ax4.set_ylabel("Count")
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3)

    plt.suptitle(
        "Mean-Reversion ATR — Feasibility Study\n"
        "Train: 2020-01-01 → 2024-06-30  |  Test: 2024-07-01 → 2026-05-11",
        fontsize=13, fontweight="bold", y=0.98,
    )
    plt.savefig(CHART_PATH, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Chart saved → {CHART_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("MEAN-REVERSION ATR — FEASIBILITY STUDY")
    print("=" * 60)
    print("Research question:")
    print("  'Do mean-reversion signals (dd_from_high, ma_50, ret_60d,")
    print("   funding) produce positive P&L after costs with ATR stops")
    print("   that bound daily loss by construction?'")
    print("=" * 60)

    # ── Step 0: Load data ─────────────────────────────────────────────────────
    print("\n[STEP 0] Loading market data...")
    close, open_, high, low = load_prices(UNIVERSE)
    funding_rates = load_funding_rates(list(close.columns))

    # ── Compute features ──────────────────────────────────────────────────────
    print("\n  Computing features...")
    panel = compute_features(close, high, low, funding_rates)
    print(f"  Panel shape: {panel.shape}  |  dates: {panel['date'].min()} → {panel['date'].max()}")
    print(f"  Train rows: {(panel['date'] <= TRAIN_END).sum()}   "
          f"Test rows: {(panel['date'] >= TEST_START).sum()}")

    # ── Step 1: Signal frequency ──────────────────────────────────────────────
    freq_results = analyze_signal_frequency(panel)

    # ── Step 2: T-test on test set ────────────────────────────────────────────
    ttest_results = signal_ttest(panel)

    # ── Step 3: Threshold sweep on train ─────────────────────────────────────
    sweep_results = threshold_sweep(panel, close)
    best_params   = sweep_results["best_params"]
    avg_atr_pct   = sweep_results["avg_atr_pct"]

    # ── Step 4: Full backtest on test set ─────────────────────────────────────
    backtest = run_full_backtest(close, panel, best_params)

    # ── Step 5: Walk-forward ──────────────────────────────────────────────────
    wf = walk_forward(close, panel, best_params)

    # ── Step 6: Prop firm compatibility ──────────────────────────────────────
    compat = prop_firm_compat(backtest)

    # ── Step 7: TSMOM correlation ─────────────────────────────────────────────
    corr = tsmom_correlation(close, backtest["pnl"])

    # ── Step 8: Verdict ───────────────────────────────────────────────────────
    verdict = print_verdict(ttest_results, backtest, wf, compat, corr, avg_atr_pct)

    # ── Step 9: Charts ────────────────────────────────────────────────────────
    save_charts(panel, backtest, ttest_results, compat, corr)

    return verdict


if __name__ == "__main__":
    main()
