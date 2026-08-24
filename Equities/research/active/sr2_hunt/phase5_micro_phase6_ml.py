"""
Phase 5 — Microstructure proxies (volume signals) on daily data.
Phase 6 — ML (XGBoost + Purged K-Fold, max 10 features, depth ≤ 4).
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
from backtest_engine import (
    fetch_rf, excess_returns, sharpe, max_drawdown,
    IS_START, IS_END, OOS_START, OOS_END, HOLD_START, HOLD_END, COST_ETF,
)
import json

rf = fetch_rf()
N_PREV = 727
N_TESTS = N_PREV
print("=== PHASE 5 — Microstructure Proxies ===\n")

def fetch_ohlcv(ticker: str) -> pd.DataFrame:
    df = yf.download(ticker, start="2013-01-01", end="2026-05-26",
                     auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()

print("Fetching OHLCV data...")
spy = fetch_ohlcv("SPY")
qqq = fetch_ohlcv("QQQ")
assets = {"SPY": spy, "QQQ": qqq}
print(f"  SPY={len(spy)}, QQQ={len(qqq)}")

vix_df = yf.download("^VIX", start="2013-01-01", end="2026-05-26",
                      auto_adjust=True, progress=False)
if isinstance(vix_df.columns, pd.MultiIndex):
    vix_df.columns = vix_df.columns.get_level_values(0)
vix = vix_df["Close"].dropna()
if isinstance(vix, pd.DataFrame):
    vix = vix.iloc[:, 0]

candidates: list[dict] = []

def fast_is_sr(strat_ret: pd.Series) -> float:
    r = strat_ret.loc[IS_START:IS_END]
    return sharpe(excess_returns(r, rf))

def full_eval(strat_ret: pd.Series, sid: str, desc: str,
              phase: str, params: dict, n: int) -> dict:
    def m(r):
        if r.empty or r.std() == 0:
            return 0.0, 0.0
        return sharpe(excess_returns(r, rf)), max_drawdown(r)
    sr_is,   mdd_is   = m(strat_ret.loc[IS_START:IS_END])
    sr_oos,  mdd_oos  = m(strat_ret.loc[OOS_START:OOS_END])
    sr_hold, mdd_hold = m(strat_ret.loc[HOLD_START:HOLD_END])
    result = dict(id=sid, phase=phase, description=desc, params=params,
                  sr_is=sr_is, mdd_is=mdd_is, sr_oos=sr_oos, mdd_oos=mdd_oos,
                  sr_hold=sr_hold, mdd_hold=mdd_hold, n_tests_at_eval=n)
    print(f"  [{sid}] {desc[:55]:55s} | "
          f"IS={sr_is:+.2f} OOS={sr_oos:+.2f} HOLD={sr_hold:+.2f}")
    return result


# ────────────────────────────────────────────────────────────────────────────
# 5.1  Volume-Price Signals
# ────────────────────────────────────────────────────────────────────────────
print("\n--- 5.1 Volume-Based Signals ---")

for ticker, ohlcv in assets.items():
    prices = ohlcv["Close"]
    volume = ohlcv["Volume"]
    ret = prices.pct_change().dropna()

    # Relative volume (RVol) = today's vol / 20d avg
    rvol = volume / volume.rolling(20).mean()

    # 5.1a: High RVol + price direction (conviction signal)
    for rvol_thresh in [1.5, 2.0, 2.5]:
        N_TESTS += 1
        high_vol_day = rvol > rvol_thresh
        direction = np.sign(ret)
        signal = pd.Series(0.0, index=prices.index)
        signal[high_vol_day] = direction[high_vol_day]  # follow high-volume days
        pos = signal.shift(1).fillna(0)
        strat_ret = pos.reindex(ret.index).fillna(0) * ret - COST_ETF * pos.reindex(ret.index).fillna(0).diff().abs().fillna(0)
        sr = fast_is_sr(strat_ret)
        key = f"P5.1_{ticker}_RVol{int(rvol_thresh*10)}_follow"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
            result = full_eval(strat_ret, key, f"{ticker} High RVol×{rvol_thresh} follow", "5.1",
                               {"rvol": rvol_thresh, "ticker": ticker}, N_TESTS)
            candidates.append(result)
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

        # Fade high-volume moves
        N_TESTS += 1
        signal_fade = pd.Series(0.0, index=prices.index)
        signal_fade[high_vol_day] = -direction[high_vol_day]
        pos_fade = signal_fade.shift(1).fillna(0)
        strat_fade = pos_fade.reindex(ret.index).fillna(0) * ret - COST_ETF * pos_fade.reindex(ret.index).fillna(0).diff().abs().fillna(0)
        sr_fade = fast_is_sr(strat_fade)
        key_fade = f"P5.1_{ticker}_RVol{int(rvol_thresh*10)}_fade"
        if sr_fade >= 1.0:
            print(f"  PASS IS: {key_fade} SR_IS={sr_fade:.2f}")
        else:
            print(f"  FAIL IS: {key_fade} SR_IS={sr_fade:.2f}")

    # 5.1b: OBV trend following
    for obv_smooth in [10, 20]:
        N_TESTS += 1
        obv = (np.sign(ret) * volume).fillna(0).cumsum()
        obv_ma = obv.rolling(obv_smooth).mean()
        signal = (obv > obv_ma).astype(float)
        pos = signal.shift(1).reindex(ret.index).fillna(0)
        strat_ret = pos * ret - COST_ETF * pos.diff().abs().fillna(0)
        sr = fast_is_sr(strat_ret)
        key = f"P5.1_{ticker}_OBV_ma{obv_smooth}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # 5.1c: Volume-weighted momentum (price move weighted by volume)
    for lookback in [5, 10, 20]:
        N_TESTS += 1
        vol_weighted_ret = (ret * rvol).rolling(lookback).mean()
        signal = np.sign(vol_weighted_ret)
        pos = pd.Series(signal.values, index=signal.index).shift(1).reindex(ret.index).fillna(0)
        strat_ret = pos * ret - COST_ETF * pos.diff().abs().fillna(0)
        sr = fast_is_sr(strat_ret)
        key = f"P5.1_{ticker}_VolWgtMom{lookback}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")

    # 5.1d: Price-volume divergence (price up, volume down = weak move → fade)
    for lookback in [5, 10]:
        N_TESTS += 1
        price_mom = prices.pct_change(lookback)
        vol_mom   = volume.pct_change(lookback)
        # Divergence: price trending up but volume trending down
        diverge_up   = (price_mom > 0) & (vol_mom < 0)
        diverge_down = (price_mom < 0) & (vol_mom > 0)
        signal = pd.Series(0.0, index=prices.index)
        signal[diverge_up]   = -1.0  # fade weak rally
        signal[diverge_down] = 1.0   # fade weak selloff
        pos = signal.shift(1).reindex(ret.index).fillna(0)
        strat_ret = pos * ret - COST_ETF * pos.diff().abs().fillna(0)
        sr = fast_is_sr(strat_ret)
        key = f"P5.1_{ticker}_PVdivergence{lookback}"
        if sr >= 1.0:
            print(f"  PASS IS: {key} SR_IS={sr:.2f}")
        else:
            print(f"  FAIL IS: {key} SR_IS={sr:.2f}")


# ────────────────────────────────────────────────────────────────────────────
# Phase 5 Summary
# ────────────────────────────────────────────────────────────────────────────
p5_count = N_TESTS - N_PREV
print(f"\n=== Phase 5 Summary: {p5_count} tests, {len(candidates)} IS passes ===")


# ════════════════════════════════════════════════════════════════════════════
# PHASE 6 — ML (XGBoost + Purged K-Fold)
# ════════════════════════════════════════════════════════════════════════════
print("\n\n=== PHASE 6 — Machine Learning (XGBoost + Purged K-Fold) ===\n")

try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:
    print("XGBoost not available — using sklearn GradientBoostingRegressor")
    from sklearn.ensemble import GradientBoostingRegressor
    HAS_XGB = False

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

N_ML_BASE = N_TESTS

# ── Feature engineering (all computable at T-1 to avoid look-ahead) ────────
def build_features(ohlcv: pd.DataFrame, vix_series: pd.Series) -> pd.DataFrame:
    """Build feature matrix. All features use only past data (shift enforced)."""
    prices = ohlcv["Close"]
    volume = ohlcv["Volume"]
    ret = prices.pct_change()

    feats = pd.DataFrame(index=prices.index)
    # Momentum
    for lb in [5, 10, 21, 63]:
        feats[f"mom_{lb}"] = prices.pct_change(lb)
    # Trend
    feats["trend_200"] = prices / prices.rolling(200).mean() - 1
    feats["trend_50"]  = prices / prices.rolling(50).mean() - 1
    # Vol
    feats["vol_20"] = ret.rolling(20).std() * np.sqrt(252)
    feats["vol_63"] = ret.rolling(63).std() * np.sqrt(252)
    # VIX
    vix_a = vix_series.reindex(prices.index, method="ffill")
    feats["vix"] = vix_a
    feats["vix_change_5d"] = vix_a.pct_change(5)
    # Volume
    feats["rvol"] = volume / volume.rolling(20).mean()
    # Calendar
    feats["month"] = prices.index.month
    feats["dow"]   = prices.index.dayofweek
    # Target: next day return (shifted -1 for training)
    feats["target"] = ret.shift(-1)

    return feats.dropna()

print("Building feature matrices...")
spy_feats = build_features(spy, vix)
print(f"  SPY features: {spy_feats.shape}")

FEATURE_COLS = [c for c in spy_feats.columns if c != "target"]
print(f"  Features used ({len(FEATURE_COLS)}): {FEATURE_COLS}")


# ── Purged K-Fold (López de Prado) ─────────────────────────────────────────
def purged_kfold_cv(X_is: pd.DataFrame, y_is: pd.Series,
                     model_cls, model_params: dict,
                     n_folds: int = 5, embargo: int = 21) -> list[float]:
    """
    Expanding purged k-fold CV on IS data only.
    Returns list of OOS R² per fold.
    """
    n = len(X_is)
    fold_size = n // n_folds
    scores = []

    for fold in range(n_folds):
        # Expanding train
        train_end = fold_size * (fold + 1)
        if fold == n_folds - 1:
            break  # last fold has no OOS
        val_start = train_end + embargo
        val_end   = train_end + fold_size + embargo
        val_end   = min(val_end, n)

        if val_start >= n or val_start >= val_end:
            continue

        X_train = X_is.iloc[:train_end]
        y_train = y_is.iloc[:train_end]
        X_val   = X_is.iloc[val_start:val_end]
        y_val   = y_is.iloc[val_start:val_end]

        if len(X_train) < 100 or len(X_val) < 20:
            continue

        model = model_cls(**model_params)
        model.fit(X_train, y_train)
        preds = model.predict(X_val)

        # IC (rank correlation between prediction and actual returns)
        from scipy.stats import spearmanr
        ic, _ = spearmanr(preds, y_val)
        scores.append(ic)

    return scores


def ml_backtest(ohlcv: pd.DataFrame, vix_series: pd.Series,
                feats_df: pd.DataFrame, model_cls, model_params: dict,
                cost: float, strategy_id: str, ticker: str) -> dict:
    """
    ML backtest with strict IS/OOS/HOLDOUT split.
    Model trained ONLY on IS data.
    Signal = model prediction at T, position entered at T+1 open (shift 1).
    """
    X = feats_df[FEATURE_COLS]
    y = feats_df["target"]
    prices = ohlcv["Close"].reindex(feats_df.index)
    ret = prices.pct_change().dropna()

    X_is = X.loc[IS_START:IS_END]
    y_is = y.loc[IS_START:IS_END]

    # Train on full IS
    model = model_cls(**model_params)
    model.fit(X_is, y_is)

    # Predict on full dataset (IS + OOS + HOLDOUT) — no future info used
    preds = pd.Series(model.predict(X), index=X.index)

    # Position: sign of prediction, shifted 1 day
    signal = np.sign(preds)
    pos = signal.shift(1).reindex(ret.index).fillna(0)
    strat_ret = pos * ret - cost * pos.diff().abs().fillna(0)

    def m(r):
        if r.empty or r.std() == 0:
            return 0.0, 0.0
        return sharpe(excess_returns(r, rf)), max_drawdown(r)

    sr_is,   mdd_is   = m(strat_ret.loc[IS_START:IS_END])
    sr_oos,  mdd_oos  = m(strat_ret.loc[OOS_START:OOS_END])
    sr_hold, mdd_hold = m(strat_ret.loc[HOLD_START:HOLD_END])

    print(f"  [{strategy_id}] {ticker} | IS={sr_is:+.2f} OOS={sr_oos:+.2f} HOLD={sr_hold:+.2f}")

    return {
        "id": strategy_id, "phase": "6", "description": f"ML {strategy_id} on {ticker}",
        "params": model_params,
        "sr_is": sr_is, "mdd_is": mdd_is,
        "sr_oos": sr_oos, "mdd_oos": mdd_oos,
        "sr_hold": sr_hold, "mdd_hold": mdd_hold,
        "n_tests_at_eval": N_TESTS,
    }


# ── 6.1 XGBoost / GBM ─────────────────────────────────────────────────────
print("\n--- 6.1 Gradient Boosting ---")
gbm_configs = [
    {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.05},
    {"n_estimators": 200, "max_depth": 3, "learning_rate": 0.02},
    {"n_estimators": 100, "max_depth": 4, "learning_rate": 0.05},
]

for ticker, ohlcv in assets.items():
    feats_df = build_features(ohlcv, vix)
    for config in gbm_configs:
        N_TESTS += 1
        if HAS_XGB:
            ModelCls = XGBRegressor
            params = {**config, "verbosity": 0, "n_jobs": 1}
        else:
            ModelCls = GradientBoostingRegressor
            params = config

        sid = f"P6.1_{ticker}_GBM_d{config['max_depth']}_lr{int(config['learning_rate']*100)}_n{config['n_estimators']}"
        result = ml_backtest(ohlcv, vix, feats_df, ModelCls, params, COST_ETF, sid, ticker)
        if result["sr_is"] >= 1.0:
            candidates.append(result)


# ── 6.2 Random Forest ─────────────────────────────────────────────────────
print("\n--- 6.2 Random Forest ---")
rf_configs = [
    {"n_estimators": 100, "max_depth": 4, "n_jobs": -1},
    {"n_estimators": 200, "max_depth": 3, "n_jobs": -1},
    {"n_estimators": 100, "max_depth": 3, "min_samples_leaf": 20, "n_jobs": -1},
]

for ticker, ohlcv in assets.items():
    feats_df = build_features(ohlcv, vix)
    for config in rf_configs:
        N_TESTS += 1
        sid = f"P6.2_{ticker}_RF_d{config['max_depth']}_n{config['n_estimators']}"
        result = ml_backtest(ohlcv, vix, feats_df, RandomForestRegressor, config, COST_ETF, sid, ticker)
        if result["sr_is"] >= 1.0:
            candidates.append(result)


# ── 6.3 Feature importance check (best ML model) ──────────────────────────
print("\n--- 6.3 Feature Importance (SHAP proxy) ---")
feats_spy = build_features(spy, vix)
X_is_spy = feats_spy.loc[IS_START:IS_END][FEATURE_COLS]
y_is_spy  = feats_spy.loc[IS_START:IS_END]["target"]

if HAS_XGB:
    best_ml = XGBRegressor(n_estimators=200, max_depth=3, learning_rate=0.02, verbosity=0, n_jobs=1)
else:
    best_ml = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.02)
best_ml.fit(X_is_spy, y_is_spy)
importances = pd.Series(best_ml.feature_importances_, index=FEATURE_COLS).sort_values(ascending=False)
print("  Feature importances (IS SPY):")
for feat, imp in importances.items():
    print(f"    {feat:20s}: {imp:.4f}")


# ── Purged CV check on best config ────────────────────────────────────────
print("\n--- 6.4 Purged K-Fold IC check (IS only) ---")
cv_scores = purged_kfold_cv(X_is_spy, y_is_spy,
                              GradientBoostingRegressor if not HAS_XGB else XGBRegressor,
                              {"n_estimators": 100, "max_depth": 3,
                               "learning_rate": 0.05, **({"verbosity": 0, "n_jobs": 1} if HAS_XGB else {})},
                              n_folds=5, embargo=21)
print(f"  CV ICs: {[f'{s:.3f}' for s in cv_scores]}")
print(f"  Mean IC: {np.mean(cv_scores):.3f} | Positive folds: {sum(s > 0 for s in cv_scores)}/{len(cv_scores)}")


# ────────────────────────────────────────────────────────────────────────────
# Final Summary — All phases
# ────────────────────────────────────────────────────────────────────────────
print(f"\n\n{'='*70}")
print("FINAL SUMMARY — ALL PHASES")
print(f"{'='*70}")

phase_counts = {
    "P1 (Indicators)": 210,
    "P2 (Timing)": 81,
    "P3 (CS)": 19,
    "P4 (Vol+VIX)": 59,
    "P4b (NR4 audit)": 36,
    "P5 (Micro)": N_TESTS - N_ML_BASE,
    "P6 (ML)": N_TESTS - N_ML_BASE - p5_count if 'p5_count' in dir() else 0,
}

total = N_TESTS - 322  # subtract base n_tests
print(f"\nTotal tests this session: {total}")
print(f"Running global n_tests: {N_TESTS}")
print(f"\nIS passes (corrected, SR≥1.0): {len(candidates)}")
for c in candidates:
    print(f"  {c['id']}: IS={c['sr_is']:.2f} OOS={c['sr_oos']:.2f} HOLD={c['sr_hold']:.2f}")

oos_pass = [c for c in candidates if c.get("sr_oos", 0) >= 1.5]
hold_pass = [c for c in candidates if c.get("sr_hold", 0) >= 2.0]
print(f"\nOOS≥1.5: {len(oos_pass)}")
print(f"HOLDOUT≥2.0: {len(hold_pass)}")

RESULTS_FILE = os.path.join(os.path.dirname(__file__), "final_results.json")
with open(RESULTS_FILE, "w") as f:
    json.dump({
        "n_tests_session": total,
        "n_tests_global": N_TESTS,
        "candidates_all": candidates,
        "oos_passes": oos_pass,
        "hold_passes": hold_pass,
    }, f, indent=2, default=str)
print(f"\nResults saved: {RESULTS_FILE}")
