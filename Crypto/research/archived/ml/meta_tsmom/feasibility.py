#!/usr/bin/env python
"""
Meta-Labeling on TSMOM v2 — XGBoost Trade Filter Feasibility.

Background:
  TSMOM v2 has Sharpe 1.53-1.65 but only 34% Propr challenge pass rate.
  Root cause: 3% daily loss limit — TSMOM enters in mean-reversion regimes.
  MLP feasibility showed that ma_50, dd_from_high, ret_60d, ret_28d, funding
  have IC t-stats of -3.8 to -5.5 for predicting TSMOM *failures*.

Meta-labeling (López de Prado, AFML 2018):
  Primary model: TSMOM signal (unchanged)
  Meta-model: XGBoost → "Will this TSMOM trade be profitable?"
  When meta-model says NO → skip trade (size = 0)
  When meta-model says YES → trade with confidence-scaled size

Run: python -m strategies.meta_tsmom.feasibility
"""
from __future__ import annotations

import json
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
import shap
import xgboost as xgb
import yfinance as yf
from sklearn.metrics import roc_auc_score, accuracy_score, confusion_matrix
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ── Constants ──────────────────────────────────────────────────────────────────
UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD",
    "DOGE-USD", "ADA-USD", "DOT-USD", "LTC-USD", "BCH-USD",
]
# Map ticker to HL funding filename prefix
TICKER_TO_HL: dict[str, str] = {
    "BTC-USD": "BTC", "ETH-USD": "ETH", "SOL-USD": "SOL",
    "AVAX-USD": "AVAX", "LINK-USD": "LINK", "DOGE-USD": "DOGE",
    "ADA-USD": "ADA", "DOT-USD": "DOT", "LTC-USD": "LTC", "BCH-USD": "BCH",
}
HL_FUNDING_DIR = Path(__file__).parent.parent / "cs_carry" / "data"

DATA_START  = "2020-06-01"   # need 90d warmup before 2021-01-01
DATA_END    = "2026-05-12"

TRAIN_START = "2021-01-01"
TRAIN_END   = "2024-06-30"
TEST_START  = "2024-07-01"
TEST_END    = "2026-05-11"

# Walk-forward windows
WF_WINDOWS: list[tuple[str, str, str, str]] = [
    ("2021-01-01", "2022-12-31", "2023-01-01", "2023-06-30"),
    ("2021-01-01", "2023-06-30", "2023-07-01", "2023-12-31"),
    ("2021-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
    ("2021-01-01", "2024-12-31", "2025-01-01", "2025-06-30"),
]

# Prop firm challenge
SIM_START   = "2025-01-06"
SIM_END     = "2025-11-03"
PROPR_CAP   = 5_000.0
PROPR_TGT   = 0.10
PROPR_DD    = 0.06
PROPR_DAILY = 0.03
TSMOM_BASELINE_PASS = 0.34
TSMOM_DAILY_FAILS   = 26    # from prior feasibility

# TSMOM v2 parameters
LOOKBACK_DAYS   = 28
VOL_LOOKBACK    = 20
VOL_TARGET      = 0.15
VOL_SCALAR_MIN  = 0.1
VOL_SCALAR_MAX  = 2.0
COSTS_RT        = 0.0017   # 0.17% round-trip

# XGBoost hyperparameters (fixed — no tuning on test set)
XGB_PARAMS: dict[str, Any] = {
    "objective":        "binary:logistic",
    "eval_metric":      "auc",
    "max_depth":        4,
    "learning_rate":    0.05,
    "subsample":        0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "gamma":            1.0,
    "seed":             42,
}
N_ESTIMATORS    = 500
EARLY_STOPPING  = 50
VAL_FRAC        = 0.20

# Meta-model thresholds to test
THRESHOLDS = [0.45, 0.50, 0.55, 0.60, 0.65]
MIN_TRADES  = 300
N_TRIALS    = 9   # total strategies tested before this one

OUT_DIR    = Path(__file__).parent
MODEL_PATH = OUT_DIR / "meta_model.json"
CHART_PATH = OUT_DIR / "feasibility_results.png"


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — RECONSTRUCT TSMOM TRADE LOG
# ─────────────────────────────────────────────────────────────────────────────

def load_prices(universe: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Download daily OHLCV. Returns (close, open_)."""
    print("  Downloading OHLCV from yfinance...")
    raw = yf.download(universe, start=DATA_START, end=DATA_END,
                      auto_adjust=True, progress=False, threads=True)
    close = raw["Close"].ffill().dropna(how="all")
    open_ = raw["Open"].ffill().dropna(how="all")
    open_ = open_.reindex(close.index)
    print(f"  Downloaded: {close.shape[1]} assets × {len(close)} days")
    return close, open_


def load_funding_rates() -> dict[str, pd.Series]:
    """Load HL funding rates for all assets in universe."""
    funding: dict[str, pd.Series] = {}
    for ticker, hl_name in TICKER_TO_HL.items():
        path = HL_FUNDING_DIR / f"{hl_name}_hl_funding.csv"
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path, index_col=0)
            df.index = pd.to_datetime(df.index, format="mixed", utc=True).tz_convert(None)
            col = df.columns[0]
            s = df[col].resample("D").mean()
            funding[ticker] = s
        except Exception:
            pass
    return funding


def reconstruct_trade_log(
    close: pd.DataFrame,
    open_: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build trade-level log from TSMOM daily signal transitions.

    A trade = one continuous LONG period: signal changes 0→1 (entry) to 1→0 (exit).
    Entry price  = open of day AFTER signal change.
    Exit price   = open of day AFTER exit signal.
    Label        = 1 if trade_return > COSTS_RT (profitable after costs), else 0.
    """
    records: list[dict[str, Any]] = []

    for ticker in close.columns:
        px = close[ticker].dropna()
        op = open_[ticker].reindex(px.index).ffill()

        # Daily signal: 1 if close > close[28d ago]
        ret_28d = px / px.shift(LOOKBACK_DAYS) - 1
        signal  = (ret_28d > 0).astype(int)
        signal[ret_28d.isna()] = 0

        transitions = signal.diff().fillna(0)
        entry_dates = signal.index[transitions == 1].tolist()
        exit_dates  = signal.index[transitions == -1].tolist()

        # Pair entries and exits (skip unpaired)
        for entry_t in entry_dates:
            # Next exit after this entry
            valid_exits = [e for e in exit_dates if e > entry_t]
            exit_t = valid_exits[0] if valid_exits else None

            # Entry price = open of entry_t + 1
            idx_arr    = px.index.tolist()
            entry_idx  = idx_arr.index(entry_t) if entry_t in idx_arr else None
            if entry_idx is None or entry_idx + 1 >= len(idx_arr):
                continue
            next_entry_date = idx_arr[entry_idx + 1]
            entry_price     = float(op.at[next_entry_date]) if next_entry_date in op.index else np.nan

            if exit_t is None:
                # Trade still open at end of data — use last available close
                exit_price = float(px.iloc[-1])
                exit_date  = px.index[-1]
            else:
                exit_idx = idx_arr.index(exit_t) if exit_t in idx_arr else None
                if exit_idx is None or exit_idx + 1 >= len(idx_arr):
                    exit_price = float(px.at[exit_t])
                    exit_date  = exit_t
                else:
                    next_exit_date = idx_arr[exit_idx + 1]
                    exit_price     = float(op.at[next_exit_date]) if next_exit_date in op.index else float(px.at[exit_t])
                    exit_date      = next_exit_date

            if np.isnan(entry_price) or entry_price <= 0 or np.isnan(exit_price) or exit_price <= 0:
                continue

            trade_return = (exit_price - entry_price) / entry_price
            label        = int(trade_return > 0)
            label_costs  = int(trade_return > COSTS_RT)

            # Vol scalar at entry_t
            log_rets = np.log(px / px.shift(1))
            past     = log_rets.loc[:entry_t].tail(VOL_LOOKBACK)
            if len(past) < 10:
                continue
            ann_vol     = float(past.std() * np.sqrt(365))
            vol_scalar  = float(np.clip(VOL_TARGET / max(ann_vol, 1e-6), VOL_SCALAR_MIN, VOL_SCALAR_MAX))

            records.append({
                "ticker":        ticker,
                "entry_date":    entry_t,
                "exit_date":     exit_date,
                "entry_price":   entry_price,
                "exit_price":    exit_price,
                "trade_return":  trade_return,
                "vol_scalar":    vol_scalar,
                "trade_pnl":     trade_return * vol_scalar,
                "label":         label,
                "label_costs":   label_costs,
                "duration_days": (exit_date - entry_t).days,
            })

    df = pd.DataFrame(records)
    if df.empty:
        return df
    df = df.sort_values("entry_date").reset_index(drop=True)

    # Filter to study period
    df = df[(df["entry_date"] >= TRAIN_START)]
    return df


def print_trade_log_stats(trades: pd.DataFrame) -> None:
    """Print trade log validation stats."""
    n_total  = len(trades)
    win_rate = float(trades["label_costs"].mean())
    print(f"\n  Total trades (2021-2026): {n_total}")
    print(f"  Win rate (after {COSTS_RT:.2%} costs): {win_rate:.1%}")

    if n_total < MIN_TRADES:
        print(f"\n  ⚠  WARNING: only {n_total} trades < {MIN_TRADES} minimum.")
        print("     Proceeding with reduced confidence — meta-model may be noisy.")

    print(f"\n  {'Asset':<12} {'Trades':>7} {'Win%':>7} {'AvgRet':>9} {'AvgDur':>8}")
    print(f"  {'-'*50}")
    for t in trades["ticker"].unique():
        sub = trades[trades["ticker"] == t]
        print(f"  {t:<12} {len(sub):>7}  {sub['label_costs'].mean():>6.1%}  "
              f"{sub['trade_return'].mean():>8.2%}  {sub['duration_days'].mean():>7.1f}d")

    print(f"\n  {'Year':<6} {'Trades':>7} {'Win%':>7}")
    print(f"  {'-'*22}")
    for yr in sorted(trades["entry_date"].dt.year.unique()):
        sub = trades[trades["entry_date"].dt.year == yr]
        print(f"  {yr:<6} {len(sub):>7}  {sub['label_costs'].mean():>6.1%}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────────────────────

def compute_features_for_trades(
    trades: pd.DataFrame,
    close: pd.DataFrame,
    funding_rates: dict[str, pd.Series],
) -> pd.DataFrame:
    """
    Compute all regime/vol/cross-asset/funding features at trade entry date T.
    All features use ONLY data available at market close on day T (no look-ahead).
    """
    feat_rows: list[dict[str, Any]] = []
    btc_close = close.get("BTC-USD", close.iloc[:, 0])

    # Consecutive signal tracker (per asset)
    consec: dict[str, int] = {t: 0 for t in close.columns}
    last_trade: dict[str, pd.Timestamp | None] = {t: None for t in close.columns}

    for _, row in trades.iterrows():
        ticker = row["ticker"]
        T      = row["entry_date"]
        px     = close.get(ticker, close.iloc[:, 0]).loc[:T]

        if len(px) < 90:
            feat_rows.append({"trade_idx": row.name})
            continue

        # ── Regime features ──────────────────────────────────────────────
        ma50 = px.tail(50).mean()
        ma20 = px.tail(20).mean()
        cur  = float(px.iloc[-1])

        ma_50_dev   = cur / ma50 - 1 if ma50 > 0 else 0.0
        ma_20_dev   = cur / ma20 - 1 if ma20 > 0 else 0.0
        high90      = float(px.tail(90).max())
        dd_from_high = (cur - high90) / high90 if high90 > 0 else 0.0

        def _ret(n: int) -> float:
            if len(px) < n + 1:
                return 0.0
            return float(px.iloc[-1] / px.iloc[-1 - n] - 1)

        ret_28d = _ret(28)
        ret_60d = _ret(60)
        ret_14d = _ret(14)
        ret_7d  = _ret(7)

        # ── Volatility features ──────────────────────────────────────────
        log_r    = np.log(px / px.shift(1)).dropna()
        vol_20d  = float(log_r.tail(20).std() * np.sqrt(252)) if len(log_r) >= 20 else np.nan
        vol_60d  = float(log_r.tail(60).std() * np.sqrt(252)) if len(log_r) >= 60 else np.nan
        vol_ratio = vol_20d / vol_60d if (vol_60d and vol_60d > 0) else np.nan

        # Vol percentile rank (last 252d)
        if len(log_r) >= 252 and not np.isnan(vol_20d):
            vol_history = log_r.rolling(20).std().dropna().tail(252) * np.sqrt(252)
            vol_pct = float((vol_history < vol_20d).mean())
        else:
            vol_pct = np.nan

        # ── Cross-asset context ──────────────────────────────────────────
        btc_px    = btc_close.loc[:T]
        btc_r28   = float(btc_px.iloc[-1] / btc_px.iloc[-29] - 1) if len(btc_px) > 29 else 0.0
        btc_log   = np.log(btc_px / btc_px.shift(1)).dropna()
        btc_vol   = float(btc_log.tail(20).std() * np.sqrt(252)) if len(btc_log) >= 20 else np.nan
        rel_str   = ret_28d - btc_r28

        # ── Funding features ─────────────────────────────────────────────
        fund_7d    = 0.0
        fund_sign  = 0.0
        if ticker in funding_rates:
            fs = funding_rates[ticker].loc[:T].dropna()
            if len(fs) >= 7:
                fund_7d   = float(fs.tail(7).mean())
                fund_sign = float(np.sign(fund_7d))

        # ── Market structure features ────────────────────────────────────
        # Consecutive periods with TSMOM=1 before this trade
        prev_consec = consec.get(ticker, 0)
        consec[ticker] = prev_consec + 1

        # Days since last trade on this asset
        last_t = last_trade.get(ticker)
        days_since = (T - last_t).days if last_t is not None else 365
        last_trade[ticker] = T

        # Number of assets with TSMOM=1 at T (cross-asset breadth)
        n_long = 0
        for other in close.columns:
            other_px = close[other].loc[:T]
            if len(other_px) >= LOOKBACK_DAYS + 1:
                n_long += int(other_px.iloc[-1] > other_px.iloc[-LOOKBACK_DAYS - 1])

        feat_rows.append({
            "trade_idx":          row.name,
            "ma_50_dev":          ma_50_dev,
            "ma_20_dev":          ma_20_dev,
            "dd_from_high":       dd_from_high,
            "ret_28d":            ret_28d,
            "ret_60d":            ret_60d,
            "ret_14d":            ret_14d,
            "ret_7d":             ret_7d,
            "vol_20d":            vol_20d,
            "vol_60d":            vol_60d,
            "vol_ratio":          vol_ratio,
            "vol_pct":            vol_pct,
            "btc_ret_28d":        btc_r28,
            "btc_vol_20d":        btc_vol,
            "rel_strength":       rel_str,
            "funding_ema_7d":     fund_7d,
            "funding_sign":       fund_sign,
            "consecutive_signals": prev_consec,
            "days_since_last":    days_since,
            "n_assets_long":      n_long,
        })

    feat_df = pd.DataFrame(feat_rows).set_index("trade_idx")
    # Merge back with trades
    result  = trades.join(feat_df)
    return result


FEATURE_COLS: list[str] = [
    "ma_50_dev", "ma_20_dev", "dd_from_high",
    "ret_28d", "ret_60d", "ret_14d", "ret_7d",
    "vol_20d", "vol_60d", "vol_ratio", "vol_pct",
    "btc_ret_28d", "btc_vol_20d", "rel_strength",
    "funding_ema_7d", "funding_sign",
    "consecutive_signals", "days_since_last", "n_assets_long",
]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — TRAIN/TEST SPLIT
# ─────────────────────────────────────────────────────────────────────────────

def split_trades(
    trades: pd.DataFrame,
    feature_cols: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Strict temporal split by trade entry date."""
    target = "label_costs"
    train = trades[trades["entry_date"] <= TRAIN_END].copy()
    test  = trades[trades["entry_date"] >= TEST_START].copy()

    # Fill NaN with train medians
    medians = train[feature_cols].median()
    train[feature_cols] = train[feature_cols].fillna(medians)
    test[feature_cols]  = test[feature_cols].fillna(medians)

    X_train = train[feature_cols].values
    y_train = train[target].values
    X_test  = test[feature_cols].values
    y_test  = test[target].values

    pos_train = y_train.mean()
    pos_test  = y_test.mean()

    print(f"\n  Train: {len(train)} trades  ({int(y_train.sum())} pos / {int((1-y_train).sum())} neg)  →  {pos_train:.1%} positive")
    print(f"  Test:  {len(test)} trades   ({int(y_test.sum())} pos / {int((1-y_test).sum())} neg)  →  {pos_test:.1%} positive")
    print(f"  Class balance — Train: {pos_train:.1%}, Test: {pos_test:.1%}")

    imbalance = abs(pos_train - 0.5)
    if imbalance > 0.10:
        print(f"  ⚠  Imbalance > 60/40 — will use scale_pos_weight in XGBoost")

    return train, test, X_train, y_train, X_test, y_test, medians


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — META-MODEL TRAINING
# ─────────────────────────────────────────────────────────────────────────────

def train_meta_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    feature_cols: list[str],
) -> tuple[xgb.XGBClassifier, StandardScaler]:
    """Train XGBoost meta-model with early stopping on 20% validation holdout."""
    # Scale features
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    # Validation split (last 20% chronologically — no shuffling)
    n_val    = int(len(X_scaled) * VAL_FRAC)
    X_tr     = X_scaled[:-n_val]
    y_tr     = y_train[:-n_val]
    X_val    = X_scaled[-n_val:]
    y_val    = y_train[-n_val:]

    # Class imbalance
    n_pos = y_train.sum()
    n_neg = len(y_train) - n_pos
    scale_pos = float(n_neg / max(n_pos, 1))

    params = {**XGB_PARAMS, "scale_pos_weight": scale_pos}

    model = xgb.XGBClassifier(
        n_estimators=N_ESTIMATORS,
        early_stopping_rounds=EARLY_STOPPING,
        verbosity=0,
        **params,
    )
    model.fit(
        X_tr, y_tr,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    best_round = model.best_iteration + 1
    print(f"  Best round: {best_round}/{N_ESTIMATORS}  (early stopped at {EARLY_STOPPING} rounds patience)")

    # Train AUC
    train_probs = model.predict_proba(X_scaled)[:, 1]
    train_auc   = roc_auc_score(y_train, train_probs)
    print(f"  Train AUC: {train_auc:.4f}")

    return model, scaler


def evaluate_meta_model(
    model: xgb.XGBClassifier,
    scaler: StandardScaler,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_cols: list[str],
) -> dict[str, Any]:
    """Evaluate on OOS test set; compute SHAP values."""
    X_scaled = scaler.transform(X_test)
    probs    = model.predict_proba(X_scaled)[:, 1]
    preds    = (probs >= 0.50).astype(int)

    auc   = roc_auc_score(y_test, probs)
    acc   = accuracy_score(y_test, preds)
    cm    = confusion_matrix(y_test, preds)
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
    prec  = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec   = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    print(f"\n  OOS Test AUC      : {auc:.4f}")
    print(f"  OOS Accuracy      : {acc:.2%}")
    print(f"  OOS Precision     : {prec:.2%}")
    print(f"  OOS Recall        : {rec:.2%}")
    print(f"  Confusion matrix  : TP={tp} FP={fp} TN={tn} FN={fn}")

    # SHAP values
    explainer  = shap.TreeExplainer(model)
    shap_vals  = explainer.shap_values(X_scaled)
    mean_shap  = np.abs(shap_vals).mean(axis=0)
    shap_order = np.argsort(mean_shap)[::-1]

    print(f"\n  Top 5 features (mean |SHAP|):")
    for i in range(min(5, len(feature_cols))):
        idx = shap_order[i]
        print(f"    {i+1}. {feature_cols[idx]:<22} SHAP = {mean_shap[idx]:.4f}")

    return {
        "auc":        auc,
        "acc":        acc,
        "precision":  prec,
        "recall":     rec,
        "probs":      probs,
        "shap_vals":  shap_vals,
        "mean_shap":  mean_shap,
        "shap_order": shap_order,
        "feature_cols": feature_cols,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — WALK-FORWARD VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def walk_forward_validation(
    trades: pd.DataFrame,
    feature_cols: list[str],
) -> dict[str, Any]:
    """4-window expanding walk-forward: AUC + accepted win rate."""
    print(f"\n  {'Win':<4} {'Train':<25} {'Test':<22} {'AUC':>7} {'Accept%':>9} {'WinRate':>9}")
    print(f"  {'-'*75}")

    results: list[dict[str, Any]] = []
    unstable = False

    for i, (tr_s, tr_e, te_s, te_e) in enumerate(WF_WINDOWS):
        tr_data = trades[(trades["entry_date"] >= tr_s) & (trades["entry_date"] <= tr_e)].copy()
        te_data = trades[(trades["entry_date"] >= te_s) & (trades["entry_date"] <= te_e)].copy()

        if len(tr_data) < 50 or len(te_data) < 10:
            print(f"  W{i+1:<3} skipped (train={len(tr_data)}, test={len(te_data)})")
            continue

        med = tr_data[feature_cols].median()
        tr_data[feature_cols] = tr_data[feature_cols].fillna(med)
        te_data[feature_cols] = te_data[feature_cols].fillna(med)

        X_tr = tr_data[feature_cols].values
        y_tr = tr_data["label_costs"].values
        X_te = te_data[feature_cols].values
        y_te = te_data["label_costs"].values

        sc = StandardScaler()
        X_tr_s = sc.fit_transform(X_tr)
        X_te_s = sc.transform(X_te)

        n_pos = y_tr.sum()
        n_neg = len(y_tr) - n_pos
        spw   = float(n_neg / max(n_pos, 1))

        m = xgb.XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
            gamma=1.0, scale_pos_weight=spw,
            objective="binary:logistic", eval_metric="auc",
            verbosity=0, seed=42,
        )
        m.fit(X_tr_s, y_tr, verbose=False)

        probs   = m.predict_proba(X_te_s)[:, 1]
        auc     = roc_auc_score(y_te, probs) if len(np.unique(y_te)) > 1 else 0.5
        accept  = (probs >= 0.50).mean()
        wr_acc  = float(y_te[probs >= 0.50].mean()) if (probs >= 0.50).any() else 0.0

        flag = " ← UNSTABLE" if auc < 0.55 else ""
        if auc < 0.55:
            unstable = True

        print(f"  W{i+1:<3} {tr_s}→{tr_e}  {te_s}→{te_e}  "
              f"{auc:>7.4f} {accept:>8.1%} {wr_acc:>8.1%}{flag}")
        results.append({"window": i+1, "auc": auc, "accept": accept, "win_rate": wr_acc})

    n_pass = sum(1 for r in results if r["auc"] >= 0.55)
    n_total = len(results)
    avg_auc = float(np.mean([r["auc"] for r in results])) if results else 0.0

    print(f"\n  Walk-forward: {n_pass}/{n_total} windows with AUC ≥ 0.55")
    print(f"  Avg AUC: {avg_auc:.4f}  {'⚠ UNSTABLE' if unstable else 'stable'}")

    return {
        "windows":  results,
        "n_pass":   n_pass,
        "n_total":  n_total,
        "avg_auc":  avg_auc,
        "unstable": unstable,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — TRADING SIMULATION WITH META-FILTER
# ─────────────────────────────────────────────────────────────────────────────

def _build_tsmom_daily_pnl(
    close: pd.DataFrame,
    start: str,
    end: str,
    position_scale: pd.DataFrame | None = None,   # date × ticker override
) -> pd.Series:
    """
    Build daily P&L for TSMOM v2 on given period.
    position_scale: if provided, multiply vol-targeted position by this factor per (date, ticker).
    """
    log_rets = np.log(close / close.shift(1))
    arith    = np.exp(log_rets) - 1

    # Daily signal (28d momentum, long-only)
    signal = (close > close.shift(LOOKBACK_DAYS)).astype(float)
    signal[close.shift(LOOKBACK_DAYS).isna()] = np.nan

    # Weekly rebalance (Monday)
    is_monday = pd.Series(close.index.dayofweek == 0, index=close.index)
    signal_rb = signal.where(is_monday).ffill()

    # Vol scalar
    ann_vol    = log_rets.rolling(VOL_LOOKBACK).std() * np.sqrt(365)
    vol_scalar = (VOL_TARGET / ann_vol).shift(1).clip(VOL_SCALAR_MIN, VOL_SCALAR_MAX)

    positions  = signal_rb * vol_scalar

    if position_scale is not None:
        positions = positions * position_scale

    # Per-asset net returns
    gross_ret = positions * arith
    turnover  = positions.diff().abs()
    cost      = turnover * (COSTS_RT / 2)
    net_ret   = gross_ret - cost

    n_valid   = net_ret.notna().sum(axis=1)
    port      = net_ret.mean(axis=1)
    port[n_valid < 3] = np.nan

    return port[start:end].dropna()


def run_meta_simulation(
    trades: pd.DataFrame,
    test_trades: pd.DataFrame,
    model: xgb.XGBClassifier,
    scaler: StandardScaler,
    medians: pd.Series,
    feature_cols: list[str],
    close: pd.DataFrame,
    probs: np.ndarray,
) -> dict[str, Any]:
    """
    Step 6: Simulate 3 meta-filter variants on test set.
    """
    test_trades = test_trades.copy()
    test_trades["meta_prob"] = probs

    # Build (date, ticker) → meta_prob lookup for weekly rebalance application
    # For each Monday, apply meta-prob from most recent preceding trade entry
    # If no preceding trade: default prob = 0.5 (neutral)
    prob_lookup: dict[tuple[pd.Timestamp, str], float] = {}
    for _, row in test_trades.iterrows():
        prob_lookup[(pd.Timestamp(row["entry_date"]), row["ticker"])] = float(row["meta_prob"])

    # Build position_scale DataFrame for each variant
    dates  = close[TEST_START:TEST_END].index
    tickers = list(close.columns)

    # For each Monday, for each ticker with TSMOM=1:
    # find the most recent trade entry for that ticker ≤ Monday
    # use its meta_prob

    def _get_meta_scale(date: pd.Timestamp, ticker: str, variant: str, theta: float = 0.55) -> float:
        # Find most recent test trade for this ticker with entry_date <= date
        sub = test_trades[(test_trades["ticker"] == ticker) &
                          (test_trades["entry_date"] <= date)]
        if sub.empty:
            return 1.0  # no info → full size
        prob = float(sub.iloc[-1]["meta_prob"])

        if variant == "A":
            return 1.0 if prob >= theta else 0.0
        elif variant == "B":
            return min(prob * 2.0, 1.5)
        elif variant == "C":
            return 1.0 if prob >= theta else 0.0
        return 1.0

    # Build scale matrices
    def _build_scale(variant: str, theta: float = 0.55) -> pd.DataFrame:
        scale = pd.DataFrame(1.0, index=dates, columns=tickers)
        for date in dates:
            if date.dayofweek != 0:   # only on Mondays
                continue
            for tkr in tickers:
                scale.at[date, tkr] = _get_meta_scale(date, tkr, variant, theta)
        # Forward-fill non-Monday days
        return scale.replace(0.0, 0.0).ffill()

    results: dict[str, Any] = {}

    # Baseline TSMOM
    pnl_base = _build_tsmom_daily_pnl(close, TEST_START, TEST_END)
    results["baseline"] = _portfolio_metrics(pnl_base)
    results["baseline"]["pnl"] = pnl_base

    for variant in ["A", "B"]:
        scale = _build_scale(variant)
        pnl   = _build_tsmom_daily_pnl(close, TEST_START, TEST_END, scale)
        results[variant] = _portfolio_metrics(pnl)
        results[variant]["pnl"] = pnl

    # Variant C: threshold sweep
    c_best_sharpe = -np.inf
    c_best_theta  = 0.55
    c_sweep: list[dict[str, Any]] = []
    for theta in THRESHOLDS:
        scale = _build_scale("C", theta)
        pnl   = _build_tsmom_daily_pnl(close, TEST_START, TEST_END, scale)
        m     = _portfolio_metrics(pnl)
        # acceptance rate
        acc_rate = (test_trades["meta_prob"] >= theta).mean()
        c_sweep.append({"theta": theta, "accept": acc_rate, **m})
        if m["sharpe"] > c_best_sharpe:
            c_best_sharpe = m["sharpe"]
            c_best_theta  = theta

    scale = _build_scale("C", c_best_theta)
    pnl_c = _build_tsmom_daily_pnl(close, TEST_START, TEST_END, scale)
    results["C"] = _portfolio_metrics(pnl_c)
    results["C"]["pnl"] = pnl_c
    results["C"]["best_theta"] = c_best_theta
    results["C_sweep"] = c_sweep

    # Acceptance rates
    results["A"]["accept"] = (test_trades["meta_prob"] >= 0.55).mean()
    results["B"]["accept"] = 1.0
    results["C"]["accept"] = (test_trades["meta_prob"] >= c_best_theta).mean()
    results["baseline"]["accept"] = 1.0

    # Win rates per variant from trade log
    for v_key, theta in [("A", 0.55), ("B", None), ("C", c_best_theta)]:
        if v_key == "B":
            results[v_key]["win_rate"] = float(test_trades["label_costs"].mean())
        else:
            accepted = test_trades[test_trades["meta_prob"] >= theta]
            results[v_key]["win_rate"] = float(accepted["label_costs"].mean()) if len(accepted) > 0 else 0.0

    print(f"\n  {'Metric':<22} {'Baseline':>10} {'Meta-A':>9} {'Meta-B':>9} {'Meta-C':>9}")
    print(f"  {'-'*62}")
    for met, fmt in [("sharpe", ".2f"), ("max_dd", ".2%"), ("ann_ret", ".2%"),
                     ("win_rate", ".1%"), ("accept", ".1%"), ("max_day_loss", ".3%"),
                     ("pct_exceed_3", ".1f")]:
        row = "  " + f"{met:<22}"
        for v in ["baseline", "A", "B", "C"]:
            val = results[v].get(met, 0.0)
            if fmt == ".1f":
                row += f" {val:>8.1f}%"
            else:
                row += f" {val:>9{fmt}}"
        print(row)

    return results


def _portfolio_metrics(pnl: pd.Series) -> dict[str, Any]:
    pnl = pnl.dropna()
    if len(pnl) < 5:
        return {"sharpe": 0.0, "max_dd": 0.0, "ann_ret": 0.0,
                "max_day_loss": 0.0, "pct_exceed_3": 0.0}
    ann_ret = float(pnl.mean() * 365)
    ann_vol = float(pnl.std() * np.sqrt(365))
    sharpe  = ann_ret / ann_vol if ann_vol > 0 else 0.0
    eq      = (1 + pnl).cumprod()
    max_dd  = float((eq / eq.cummax() - 1).min())
    max_day = float(pnl.min())
    pct_3   = float((pnl < -0.03).mean()) * 100
    return {
        "sharpe":       sharpe,
        "ann_ret":      ann_ret,
        "ann_vol":      ann_vol,
        "max_dd":       max_dd,
        "max_day_loss": max_day,
        "pct_exceed_3": pct_3,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — PROPR CHALLENGE SIMULATION
# ─────────────────────────────────────────────────────────────────────────────

def _simulate_challenge(
    pnl: pd.Series,
    start: pd.Timestamp,
    equity: float,
    target: float,
    dd: float,
    daily: float,
) -> dict[str, Any]:
    """Simulate one Propr challenge. Static HWM."""
    if pnl.index.tz is not None:
        pnl = pnl.copy(); pnl.index = pnl.index.tz_localize(None)
    dates  = pnl.index[pnl.index >= start]
    eq     = equity
    hwm    = equity
    days   = 0
    for d in dates:
        eq_s = eq
        eq   = eq_s * (1 + float(pnl.get(d, 0.0)))
        days += 1
        if (eq - eq_s) / eq_s < -daily:
            return {"outcome": "FAIL", "reason": "daily_limit", "days": days}
        if eq <= hwm * (1 - dd):
            return {"outcome": "FAIL", "reason": "total_dd", "days": days}
        if eq >= hwm * (1 + target):
            return {"outcome": "PASS", "reason": None, "days": days}
    return {"outcome": "INCOMPLETE", "reason": None, "days": days}


def run_propr_sims(pnl: pd.Series) -> dict[str, Any]:
    """44 Propr challenge simulations."""
    starts   = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")
    results  = [_simulate_challenge(pnl, sd, PROPR_CAP, PROPR_TGT, PROPR_DD, PROPR_DAILY)
                for sd in starts]
    pass_rate = sum(1 for r in results if r["outcome"] == "PASS") / len(results)
    fail_d    = sum(1 for r in results if r.get("reason") == "daily_limit")
    fail_dd   = sum(1 for r in results if r.get("reason") == "total_dd")
    pass_days = [r["days"] for r in results if r["outcome"] == "PASS"]
    avg_days  = float(np.mean(pass_days)) if pass_days else float("nan")
    return {
        "pass_rate":  pass_rate,
        "fail_daily": fail_d,
        "fail_dd":    fail_dd,
        "avg_days":   avg_days,
        "n_sims":     len(results),
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — OVERFITTING CHECKS
# ─────────────────────────────────────────────────────────────────────────────

def _probabilistic_sharpe(pnl: pd.Series, sr_benchmark: float = 0.0) -> float:
    """PSR: probability that true Sharpe > sr_benchmark."""
    pnl  = pnl.dropna()
    T    = len(pnl)
    if T < 10:
        return 0.5
    sr   = float(pnl.mean() / pnl.std() * np.sqrt(365))
    skew = float(stats.skew(pnl))
    kurt = float(stats.kurtosis(pnl))
    denom = np.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr ** 2)
    z     = (sr - sr_benchmark) * np.sqrt(T) / max(denom, 1e-6)
    return float(stats.norm.cdf(z))


def overfitting_checks(
    model: xgb.XGBClassifier,
    scaler: StandardScaler,
    X_test: np.ndarray,
    y_test: np.ndarray,
    sim_pnl: pd.Series,
    feature_cols: list[str],
    n_permutations: int = 100,
) -> dict[str, Any]:
    """DSR, permutation test, feature stability."""
    print(f"\n  n_trials = {N_TRIALS} (strategies tested before this one)")

    # 1. PSR and DSR
    psr = _probabilistic_sharpe(sim_pnl)
    # E[max Sharpe] under n_trials using MinBias correction (Bailey & López de Prado 2014)
    E_max_SR = (1 - 0.5772) * stats.norm.ppf(1 - 1/N_TRIALS) + \
               0.5772 * stats.norm.ppf(1 - 1/(N_TRIALS * np.e))
    # DSR = PSR(E_max_SR)
    dsr = _probabilistic_sharpe(sim_pnl, sr_benchmark=max(E_max_SR, 0))
    dsr_ok = dsr >= 0.90

    print(f"  PSR = {psr:.4f},  DSR = {dsr:.4f}  "
          f"[{'OK ✓' if dsr_ok else 'WARNING ⚠'}]")
    print(f"  (E[max SR] with {N_TRIALS} trials = {E_max_SR:.3f})")

    # 2. Permutation test: shuffle labels 100 times
    X_scaled = scaler.transform(X_test)
    real_auc = roc_auc_score(y_test, model.predict_proba(X_scaled)[:, 1])
    perm_aucs: list[float] = []
    rng = np.random.default_rng(42)
    for _ in range(n_permutations):
        y_perm = rng.permutation(y_test)
        if len(np.unique(y_perm)) < 2:
            continue
        probs = model.predict_proba(X_scaled)[:, 1]
        perm_aucs.append(roc_auc_score(y_perm, probs))

    perm_mean = float(np.mean(perm_aucs))
    perm_std  = float(np.std(perm_aucs))
    p_value   = float(np.mean([a >= real_auc for a in perm_aucs]))
    sig_ok    = p_value < 0.05

    print(f"  Real AUC = {real_auc:.4f},  Permuted AUC = {perm_mean:.4f} ± {perm_std:.4f}")
    print(f"  p-value = {p_value:.4f}  "
          f"[{'SIGNIFICANT ✓' if sig_ok else 'NOT SIGNIFICANT ⚠'}]")

    # 3. Feature stability: top-5 features on first vs second half of test
    n_half = len(X_test) // 2
    explainer = shap.TreeExplainer(model)

    top5_h1: set[str] = set()
    top5_h2: set[str] = set()

    for half_idx, top5_ref in [(slice(None, n_half), top5_h1),
                               (slice(n_half, None),  top5_h2)]:
        X_h = X_scaled[half_idx]
        if len(X_h) < 5:
            continue
        sv = explainer.shap_values(X_h)
        order = np.argsort(np.abs(sv).mean(axis=0))[::-1]
        for k in range(min(5, len(feature_cols))):
            top5_ref.add(feature_cols[order[k]])

    overlap = len(top5_h1 & top5_h2)
    stable  = overlap >= 3

    print(f"  Feature stability: top-5 overlap = {overlap}/5  "
          f"[{'STABLE ✓' if stable else 'UNSTABLE ⚠'}]")
    if top5_h1:
        print(f"    H1 top-5: {sorted(top5_h1)}")
    if top5_h2:
        print(f"    H2 top-5: {sorted(top5_h2)}")

    return {
        "psr":        psr,
        "dsr":        dsr,
        "dsr_ok":     dsr_ok,
        "perm_mean":  perm_mean,
        "perm_std":   perm_std,
        "p_value":    p_value,
        "sig_ok":     sig_ok,
        "overlap":    overlap,
        "stable":     stable,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 9 — VERDICT
# ─────────────────────────────────────────────────────────────────────────────

def print_verdict(
    trade_stats: dict[str, Any],
    eval_stats: dict[str, Any],
    wf_stats: dict[str, Any],
    sim_stats: dict[str, Any],
    propr_stats: dict[str, Any],
    ofit_stats: dict[str, Any],
) -> str:
    """Print structured verdict report."""
    auc        = eval_stats["auc"]
    wf_pass    = wf_stats["n_pass"]
    wf_total   = wf_stats["n_total"]
    dsr_ok     = ofit_stats["dsr_ok"]
    sig_ok     = ofit_stats["sig_ok"]
    propr_pass = propr_stats["pass_rate"]

    # Find best variant
    best_v  = max(["A", "B", "C"], key=lambda v: sim_stats.get(v, {}).get("sharpe", 0.0))
    best_s  = sim_stats[best_v]["sharpe"]
    base_s  = sim_stats["baseline"]["sharpe"]

    # Verdict logic
    if auc > 0.58 and dsr_ok and sig_ok and propr_pass >= 0.45:
        verdict = "DEPLOY"
    elif auc > 0.55 and (propr_pass >= 0.40 or propr_pass > TSMOM_BASELINE_PASS + 0.05):
        verdict = "PROMISING"
    elif 0.52 <= auc <= 0.55:
        verdict = "WEAK"
    else:
        verdict = "SKIP"

    shap_order = eval_stats["shap_order"]
    fc         = eval_stats["feature_cols"]
    mean_shap  = eval_stats["mean_shap"]

    border = "═" * 60
    print(f"\n{border}")
    print("META-LABELING TSMOM FEASIBILITY REPORT")
    print(f"{border}")
    print(f"  Total trades in sample        : {trade_stats['n_total']}"
          f"  (train: {trade_stats['n_train']}, test: {trade_stats['n_test']})")
    print(f"  TSMOM baseline win rate       : {trade_stats['win_rate']:.1%}")
    print(f"  Meta-model AUC (OOS test)     : {auc:.4f}")
    print(f"  Walk-forward: {wf_pass}/{wf_total} windows AUC ≥ 0.55")

    print(f"\n  Top 3 features (SHAP):")
    for k in range(min(3, len(fc))):
        i = shap_order[k]
        print(f"    {k+1}. {fc[i]:<22} SHAP = {mean_shap[i]:.4f}")

    print(f"\n  DSR check                     : {ofit_stats['dsr']:.4f}  "
          f"[{'OK' if dsr_ok else 'WARNING'}]")
    print(f"  Permutation p-value           : {ofit_stats['p_value']:.4f}  "
          f"[{'SIGNIFICANT' if sig_ok else 'NOT SIGNIFICANT'}]")

    best_meta = sim_stats[best_v]
    print(f"\n  Best variant                  : {best_v}  "
          f"(threshold = {best_meta.get('best_theta', 0.55):.2f})")
    print(f"    Acceptance rate             : {best_meta.get('accept', 1.0):.1%}")
    print(f"    OOS Sharpe (meta-filtered)  : {best_s:.2f}  (vs baseline: {base_s:.2f})")
    print(f"    Max daily loss              : {best_meta['max_day_loss']:.2%}")
    print(f"    Days > 3% loss              : {best_meta['pct_exceed_3']:.1f}")

    print(f"\n  Propr pass rate (meta)        : {propr_pass:.0%}  (vs TSMOM: {TSMOM_BASELINE_PASS:.0%})")
    print(f"  Daily limit fails             : {propr_stats['fail_daily']}/44  "
          f"(vs {TSMOM_DAILY_FAILS}/44)")

    print(f"\n  {'─'*58}")
    print(f"  VERDICT: {verdict}")
    print(f"  {'─'*58}")

    if verdict in ("DEPLOY", "PROMISING"):
        print(
            f"\n  Recommended: integrate meta-model into TSMOM v2 live system.\n"
            f"  Model saved: {MODEL_PATH}\n"
            f"\n  Code change for run_rebalance.py:\n"
            f"    ```python\n"
            f"    from strategies.meta_tsmom.feasibility import (\n"
            f"        load_meta_model, compute_features_for_rebalance\n"
            f"    )\n"
            f"    meta_model, meta_scaler, meta_medians = load_meta_model()\n"
            f"    # In rebalance loop, before placing orders:\n"
            f"    for asset in pending_long_entries:\n"
            f"        feats = compute_features_for_rebalance(asset, close, funding)\n"
            f"        prob = meta_model.predict_proba([feats])[0][1]\n"
            f"        if prob < 0.55:  # Meta-A variant\n"
            f"            skip_asset(asset)  # do not enter\n"
            f"    ```"
        )
    elif verdict == "WEAK":
        print(
            f"\n  Meta-model adds marginal value (AUC {auc:.2f}).\n"
            f"  Consider combining with regime filter before deploying.\n"
            f"  Next step: add vol_ratio and breadth filter as hard rules\n"
            f"  (n_assets_long > 6 AND vol_ratio < 1.2) before meta-model."
        )
    else:
        reasons = []
        if auc < 0.52:
            reasons.append("AUC < 0.52: meta-model near random on test set")
        if not dsr_ok:
            reasons.append("DSR < 0.90: possible multiple-testing overfit")
        if not sig_ok:
            reasons.append("permutation p-value > 0.05: not statistically significant")
        if trade_stats["n_total"] < MIN_TRADES:
            reasons.append(f"too few trades ({trade_stats['n_total']}) — "
                           "dataset too small for reliable XGBoost")
        reason_str = "; ".join(reasons) if reasons else "regime shift too abrupt for XGBoost to learn"
        print(
            f"\n  Meta-labeling does not add reliable value.\n"
            f"  Root cause: {reason_str}"
        )

    return verdict


# ─────────────────────────────────────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def save_charts(
    eval_stats: dict[str, Any],
    sim_stats: dict[str, Any],
    test_trades: pd.DataFrame,
    best_variant: str,
) -> None:
    """Save 4-subplot feasibility chart."""
    fig = plt.figure(figsize=(16, 14))
    gs  = GridSpec(2, 2, figure=fig, hspace=0.38, wspace=0.30)

    fc        = eval_stats["feature_cols"]
    mean_shap = eval_stats["mean_shap"]
    order     = eval_stats["shap_order"]

    # ── Plot 1: SHAP feature importance ──────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    top_n = min(15, len(fc))
    top_idx = order[:top_n][::-1]  # reverse for horizontal bar (bottom→top = best)
    top_names  = [fc[i] for i in top_idx]
    top_shap   = [mean_shap[i] for i in top_idx]
    colors = ["steelblue" if v > 0 else "tomato" for v in top_shap]
    ax1.barh(range(top_n), top_shap, color=colors, alpha=0.8)
    ax1.set_yticks(range(top_n))
    ax1.set_yticklabels(top_names, fontsize=9)
    ax1.set_title("SHAP Feature Importance (test set)", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Mean |SHAP|")
    ax1.grid(True, alpha=0.3, axis="x")

    # ── Plot 2: Meta-prob distribution (accepted vs rejected) ─────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    probs     = eval_stats["probs"]
    y_test_   = test_trades["label_costs"].values
    bins = np.linspace(0, 1, 30)
    ax2.hist(probs[y_test_ == 1], bins=bins, alpha=0.6, color="forestgreen",
             label="Profitable trades (label=1)", density=True)
    ax2.hist(probs[y_test_ == 0], bins=bins, alpha=0.6, color="tomato",
             label="Unprofitable trades (label=0)", density=True)
    ax2.axvline(0.55, color="black", ls="--", lw=1.5, label="Threshold=0.55")
    ax2.set_title(f"Meta-Model Probability Distribution\n"
                  f"AUC = {eval_stats['auc']:.4f}", fontsize=11, fontweight="bold")
    ax2.set_xlabel("P(trade profitable)")
    ax2.set_ylabel("Density")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # ── Plot 3: Equity curves ─────────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    for v, col, lbl in [
        ("baseline", "gray",       "TSMOM baseline"),
        ("A",        "steelblue",  "Meta-A (binary 0.55)"),
        (best_variant, "red",      f"Best (Meta-{best_variant})"),
    ]:
        if v == best_variant and v == "A":
            continue  # don't plot twice
        if sim_stats.get(v) and not sim_stats[v]["pnl"].empty:
            pnl = sim_stats[v]["pnl"]
            eq  = (1 + pnl).cumprod() * 100
            ax3.plot(eq.index, eq.values, color=col, lw=1.8, label=lbl)
    ax3.axhline(100, color="gray", ls="--", lw=0.8)
    s_base = sim_stats["baseline"]["sharpe"]
    s_best = sim_stats[best_variant]["sharpe"]
    ax3.set_title(f"Equity Curves (test {TEST_START[:7]}→{TEST_END[:7]})\n"
                  f"Baseline Sharpe={s_base:.2f}  Meta-{best_variant} Sharpe={s_best:.2f}",
                  fontsize=11, fontweight="bold")
    ax3.set_ylabel("Equity (start=100)")
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    # ── Plot 4: Daily P&L histogram ───────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    pnl_b = sim_stats["baseline"]["pnl"].dropna() * 100
    pnl_m = sim_stats[best_variant]["pnl"].dropna() * 100
    lo    = min(pnl_b.min(), pnl_m.min(), -5)
    hi    = max(pnl_b.max(), pnl_m.max(), 5)
    bins  = np.linspace(lo, hi, 60)
    ax4.hist(pnl_b, bins=bins, alpha=0.5, color="gray",     label="TSMOM baseline", density=True)
    ax4.hist(pnl_m, bins=bins, alpha=0.6, color="steelblue",
             label=f"Meta-{best_variant}", density=True)
    ax4.axvline(-3.0, color="red",   ls="--", lw=2, label="Propr limit (-3%)")
    ax4.axvline(0,    color="black", ls="-",  lw=0.8)
    b_pct3 = (pnl_b < -3).mean() * 100
    m_pct3 = (pnl_m < -3).mean() * 100
    ax4.set_title(f"Daily P&L Distribution\n"
                  f"Baseline >3% loss: {b_pct3:.1f}% days  |  Meta: {m_pct3:.1f}%",
                  fontsize=11, fontweight="bold")
    ax4.set_xlabel("Daily P&L (%)")
    ax4.set_ylabel("Density")
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    plt.suptitle(
        "Meta-Labeling on TSMOM v2 — XGBoost Trade Filter\n"
        f"Train: {TRAIN_START}→{TRAIN_END}  |  Test: {TEST_START}→{TEST_END}",
        fontsize=13, fontweight="bold", y=0.99,
    )
    plt.savefig(CHART_PATH, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Chart saved → {CHART_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("META-LABELING TSMOM — XGBoost TRADE FILTER FEASIBILITY")
    print("=" * 60)
    print("Meta-labeling (López de Prado 2018): XGBoost predicts")
    print("'Will this TSMOM trade be profitable?' at entry time.")
    print(f"Train: {TRAIN_START}→{TRAIN_END}  |  Test: {TEST_START}→{TEST_END}")
    print("=" * 60)

    # ── Step 0: Load data ─────────────────────────────────────────────────────
    print("\n[STEP 0] Loading data...")
    close, open_ = load_prices(UNIVERSE)
    funding_rates = load_funding_rates()
    print(f"  Funding available for: {list(funding_rates.keys())}")

    # ── Step 1: Trade log ─────────────────────────────────────────────────────
    print(f"\n[STEP 1] Reconstructing TSMOM trade log ({TRAIN_START}→{TEST_END})...")
    trades_raw = reconstruct_trade_log(close, open_)
    if trades_raw.empty:
        print("ERROR: No trades found. Check data download.")
        return

    print_trade_log_stats(trades_raw)

    # ── Step 2: Feature engineering ───────────────────────────────────────────
    print(f"\n[STEP 2] Computing features for {len(trades_raw)} trades...")
    trades = compute_features_for_trades(trades_raw, close, funding_rates)

    # Drop rows with all-NaN features
    trades = trades.dropna(subset=FEATURE_COLS[:5])   # require at least 5 core features
    print(f"  {len(trades)} trades after feature computation")

    # ── Step 3: Split ─────────────────────────────────────────────────────────
    print(f"\n[STEP 3] Train/test split (strictly by trade entry date)...")
    result = split_trades(trades, FEATURE_COLS)
    train_df, test_df, X_train, y_train, X_test, y_test, medians = result

    trade_stats = {
        "n_total":  len(trades),
        "n_train":  len(train_df),
        "n_test":   len(test_df),
        "win_rate": float(trades["label_costs"].mean()),
    }

    # ── Step 4: Train meta-model ──────────────────────────────────────────────
    print(f"\n[STEP 4] Training XGBoost meta-model (train set only)...")
    model, scaler = train_meta_model(X_train, y_train, FEATURE_COLS)

    print(f"\n  Evaluating on OOS test set ({len(test_df)} trades)...")
    eval_stats = evaluate_meta_model(model, scaler, X_test, y_test, FEATURE_COLS)
    eval_stats["probs_train"] = model.predict_proba(scaler.transform(X_train))[:, 1]

    # Attach probs to test_df
    test_df = test_df.copy()
    test_df["meta_prob"] = eval_stats["probs"]

    # ── Step 5: Walk-forward ──────────────────────────────────────────────────
    print(f"\n[STEP 5] Walk-forward validation (4 windows)...")
    wf_stats = walk_forward_validation(trades, FEATURE_COLS)

    # ── Step 6: Simulation ────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 6 — TRADING SIMULATION WITH META-FILTER (test set)")
    print(f"{'='*60}")
    sim_stats = run_meta_simulation(
        trades, test_df, model, scaler, medians, FEATURE_COLS, close, eval_stats["probs"]
    )

    # ── Step 7: Propr challenge sims ──────────────────────────────────────────
    best_v = max(["A", "B", "C"], key=lambda v: sim_stats.get(v, {}).get("sharpe", 0.0))
    print(f"\n{'='*60}")
    print(f"STEP 7 — PROPR CHALLENGE SIMULATION (best variant: Meta-{best_v})")
    print(f"{'='*60}")
    best_pnl = sim_stats[best_v]["pnl"]
    propr_stats = run_propr_sims(best_pnl)
    print(f"\n  Meta-{best_v} Propr pass rate : {propr_stats['pass_rate']:.0%}  "
          f"(vs TSMOM baseline: {TSMOM_BASELINE_PASS:.0%})")
    print(f"  Daily limit fails           : {propr_stats['fail_daily']}/44  "
          f"(vs {TSMOM_DAILY_FAILS}/44 baseline)")
    print(f"  Total DD fails              : {propr_stats['fail_dd']}/44")
    print(f"  Avg days to pass            : {propr_stats['avg_days']:.0f}")

    # ── Step 8: Overfitting checks ────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 8 — OVERFITTING CHECKS (False Strategy Theorem)")
    print(f"{'='*60}")
    ofit_stats = overfitting_checks(
        model, scaler, X_test, y_test, best_pnl, FEATURE_COLS
    )

    # ── Step 9: Verdict ───────────────────────────────────────────────────────
    verdict = print_verdict(
        trade_stats, eval_stats, wf_stats, sim_stats, propr_stats, ofit_stats
    )

    # ── Save model if AUC > 0.55 ──────────────────────────────────────────────
    if eval_stats["auc"] > 0.55:
        model.save_model(str(MODEL_PATH))
        # Save metadata for run_rebalance.py integration
        meta = {
            "auc":       eval_stats["auc"],
            "verdict":   verdict,
            "best_variant": best_v,
            "threshold": float(sim_stats[best_v].get("best_theta", 0.55)),
            "feature_cols": FEATURE_COLS,
            "medians":   medians.to_dict(),
            "scaler_mean": scaler.mean_.tolist(),
            "scaler_std":  scaler.scale_.tolist(),
        }
        with open(OUT_DIR / "meta_model_meta.json", "w") as f:
            json.dump(meta, f, indent=2)
        print(f"\n  Model saved → {MODEL_PATH}")
    else:
        print("\n  Model NOT saved (AUC ≤ 0.55)")

    # ── Charts ────────────────────────────────────────────────────────────────
    save_charts(eval_stats, sim_stats, test_df, best_v)


if __name__ == "__main__":
    main()
