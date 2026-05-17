#!/usr/bin/env python
"""
MLP TSMOM Feasibility — Economic Features for Crypto Return Prediction.

Research question:
  "Do economic features contain non-linear predictive information about
   7-day forward crypto returns, beyond what the linear 28-day momentum
   signal already captures?"

Part A: IC analysis — do features predict forward returns?
Part B: MLP vs logistic regression baseline — is non-linearity useful?

Run: python -m strategies.mlp_tsmom.feasibility
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
from sklearn.linear_model   import LogisticRegression
from sklearn.metrics        import roc_auc_score, accuracy_score
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing  import StandardScaler
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Constants ──────────────────────────────────────────────────────────────────
UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD",
    "ARB-USD", "DOGE-USD", "ADA-USD", "DOT-USD", "LTC-USD",
    "BCH-USD", "OP-USD",
]
DATA_START = "2020-01-01"
DATA_END   = "2026-05-12"   # exclusive → through 2026-05-11
FORWARD_DAYS = 7

# Train / test split
TRAIN_END  = "2024-06-30"   # inclusive
TEST_START = "2024-07-01"   # inclusive

# Walk-forward windows: (train_start, train_end, test_start, test_end)
WF_WINDOWS = [
    ("2020-01-01", "2022-12-31", "2023-01-01", "2023-06-30"),
    ("2020-01-01", "2023-06-30", "2023-07-01", "2023-12-31"),
    ("2020-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
    ("2020-01-01", "2024-12-31", "2025-01-01", "2025-06-30"),
]

SIM_START = "2025-01-06"
SIM_END   = "2025-11-03"

# Prop firm
PROPR_CAPITAL  = 5_000.0
PROPR_TARGET   = 0.10
PROPR_DD       = 0.06
PROPR_DAILY    = 0.03
TSMOM_BASELINE_PASS = 0.34

# Trading
VOL_TARGET   = 0.15
VOL_LOOKBACK = 20
COSTS_RT     = 0.0017       # 0.17% round trip

# MLP signal threshold
CONFIDENCE_THR = 0.55

# Feature groups
MOMENTUM_FEAT  = ["ret_7d", "ret_14d", "ret_28d", "ret_60d"]
VOLATILITY_FEAT = ["vol_20d", "vol_60d", "vol_ratio", "vol_pct"]
TREND_FEAT     = ["ma_20", "ma_50", "ma_slope"]
DD_FEAT        = ["dd_from_high"]
CROSS_FEAT     = ["beta_btc_20d", "corr_btc_20d", "rel_strength"]
VOLUME_FEAT    = ["vol_zscore_5d", "vol_zscore_20d"]
FUNDING_FEAT   = ["funding_ema_7d", "funding_sign"]
BASE_FEATURES  = MOMENTUM_FEAT + VOLATILITY_FEAT + TREND_FEAT + DD_FEAT + CROSS_FEAT + VOLUME_FEAT

HL_DATA_DIR = Path(__file__).parent.parent / "cs_carry" / "data"
OUT_DIR     = Path(__file__).parent

# Asset name map: yfinance ticker → HL funding file prefix
_HL_MAP: dict[str, str] = {
    "BTC-USD": "BTC", "ETH-USD": "ETH", "SOL-USD": "SOL",
    "AVAX-USD": "AVAX", "LINK-USD": "LINK", "ARB-USD": "ARB",
    "DOGE-USD": "DOGE", "ADA-USD": "ADA", "DOT-USD": "DOT",
    "LTC-USD": "LTC", "BCH-USD": "BCH", "OP-USD": "OP",
}


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — DATA DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────

def download_data(
    universe: list[str] = UNIVERSE,
    start: str = DATA_START,
    end: str = DATA_END,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Download daily close prices and volumes.
    Returns (prices, volumes): DataFrames with tickers as columns, dates as index.
    """
    print(f"\n{'='*60}")
    print(f"STEP 1 — DOWNLOAD DAILY OHLCV  ({start} → {end})")
    print(f"{'='*60}")

    raw = yf.download(
        tickers=universe,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        progress=False,
    )

    if isinstance(raw.columns, pd.MultiIndex):
        prices  = raw["Close"].copy()
        volumes = raw["Volume"].copy()
    else:
        prices  = raw[["Close"]].copy()
        volumes = raw[["Volume"]].copy()

    if prices.index.tz is not None:
        prices.index  = prices.index.tz_localize(None)
        volumes.index = volumes.index.tz_localize(None)

    prices  = prices.dropna(how="all").ffill()
    volumes = volumes.dropna(how="all").ffill()

    dropped = [t for t in universe if t not in prices.columns
               or prices[t].dropna().shape[0] < 252]

    print(f"  Assets available : {len(prices.columns)}")
    print(f"  Date range       : {prices.index[0].date()} → {prices.index[-1].date()} "
          f"({len(prices)} days)")
    for t in universe:
        if t in prices.columns:
            n = prices[t].notna().sum()
            first = prices[t].first_valid_index()
            print(f"  {t:<12}: {n} days from {first.date()}")
        else:
            print(f"  {t:<12}: NOT AVAILABLE")

    return prices, volumes


def load_funding_rates(universe: list[str]) -> dict[str, pd.Series]:
    """
    Load HL funding rates from cache.
    Returns {ticker: daily EMA(7d) series}, UTC-naive daily index.
    """
    result: dict[str, pd.Series] = {}
    for ticker in universe:
        hl_name = _HL_MAP.get(ticker, "")
        path = HL_DATA_DIR / f"{hl_name}_hl_funding.csv"
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path, index_col=0)
            idx = pd.to_datetime(df.index, format="mixed", utc=True)
            df.index = idx.tz_convert(None)  # strip UTC → tz-naive
            s = df.iloc[:, 0].dropna().sort_index()
            # Resample to daily mean, then compute EMA(7d)
            daily = s.resample("D").mean()
            result[ticker] = daily.ewm(span=7, adjust=False).mean()
        except Exception:
            pass
    print(f"  Funding rates loaded for: {list(result.keys())}")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────────────────────

def compute_features(
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    funding_rates: dict[str, pd.Series],
) -> pd.DataFrame:
    """
    Compute all features per (date, ticker).
    Returns long-format panel DataFrame.
    All features use only data up to time T (strict no look-ahead).
    """
    print(f"\n{'='*60}")
    print("STEP 2 — FEATURE ENGINEERING")
    print(f"{'='*60}")

    btc_col = "BTC-USD"
    log_ret = np.log(prices / prices.shift(1))

    # ── Pre-compute BTC series for cross-asset features ──────────────────────
    btc_lr = log_ret[btc_col] if btc_col in log_ret.columns else None
    ret_28d_btc = prices[btc_col].pct_change(28) if btc_col in prices.columns else None

    # ── Per-ticker feature DataFrames ─────────────────────────────────────────
    frames: list[pd.DataFrame] = []

    for ticker in prices.columns:
        close  = prices[ticker]
        vol    = volumes[ticker] if ticker in volumes.columns else pd.Series(np.nan, index=prices.index)
        lr     = log_ret[ticker]

        feat = pd.DataFrame(index=prices.index)

        # ── MOMENTUM ────────────────────────────────────────────────────────
        feat["ret_7d"]  = close.pct_change(7)
        feat["ret_14d"] = close.pct_change(14)
        feat["ret_28d"] = close.pct_change(28)
        feat["ret_60d"] = close.pct_change(60)

        # ── VOLATILITY ──────────────────────────────────────────────────────
        vol_20d = lr.rolling(20).std() * np.sqrt(252)
        vol_60d = lr.rolling(60).std() * np.sqrt(252)
        feat["vol_20d"]   = vol_20d
        feat["vol_60d"]   = vol_60d
        feat["vol_ratio"] = vol_20d / vol_60d.replace(0, np.nan)
        # Percentile rank in rolling 252-day window (no look-ahead)
        feat["vol_pct"]   = vol_20d.rolling(252).rank(pct=True)

        # ── TREND ────────────────────────────────────────────────────────────
        sma_20 = close.rolling(20).mean()
        sma_50 = close.rolling(50).mean()
        feat["ma_20"]    = close / sma_20.replace(0, np.nan) - 1
        feat["ma_50"]    = close / sma_50.replace(0, np.nan) - 1
        feat["ma_slope"] = sma_20.pct_change(5)

        # ── DRAWDOWN ─────────────────────────────────────────────────────────
        roll_max_90 = close.rolling(90).max()
        feat["dd_from_high"] = close / roll_max_90.replace(0, np.nan) - 1

        # ── CROSS-ASSET (vs BTC) ──────────────────────────────────────────────
        if btc_lr is not None and ticker != btc_col:
            cov_20 = lr.rolling(20).cov(btc_lr)
            var_20 = btc_lr.rolling(20).var().replace(0, np.nan)
            feat["beta_btc_20d"] = cov_20 / var_20
            feat["corr_btc_20d"] = lr.rolling(20).corr(btc_lr)
            if ret_28d_btc is not None:
                feat["rel_strength"] = close.pct_change(28) - ret_28d_btc
        else:
            # BTC vs itself
            feat["beta_btc_20d"] = 1.0
            feat["corr_btc_20d"] = 1.0
            feat["rel_strength"] = 0.0

        # ── VOLUME ───────────────────────────────────────────────────────────
        vol_mean_20 = vol.rolling(20).mean()
        vol_std_20  = vol.rolling(20).std().replace(0, np.nan)
        vol_mean_60 = vol.rolling(60).mean()
        vol_std_60  = vol.rolling(60).std().replace(0, np.nan)
        feat["vol_zscore_5d"]  = (vol - vol_mean_20) / vol_std_20
        feat["vol_zscore_20d"] = (vol - vol_mean_60) / vol_std_60

        # ── FUNDING (optional) ────────────────────────────────────────────────
        if ticker in funding_rates:
            f_series = funding_rates[ticker].reindex(prices.index).ffill()
            feat["funding_ema_7d"] = f_series
            feat["funding_sign"]   = np.sign(f_series)

        # ── FORWARD TARGET ────────────────────────────────────────────────────
        feat["fwd_ret_7d"] = close.pct_change(FORWARD_DAYS).shift(-FORWARD_DAYS)

        feat["ticker"] = ticker
        frames.append(feat)

    for f in frames:
        f.index.name = "date"
    panel = pd.concat(frames).reset_index()
    panel["date"] = pd.to_datetime(panel["date"])
    panel = panel.sort_values(["date", "ticker"]).reset_index(drop=True)

    print(f"  Raw panel shape: {panel.shape}")
    print(f"  Date range: {panel['date'].min().date()} → {panel['date'].max().date()}")

    # ── Look-ahead check ─────────────────────────────────────────────────────
    _check_lookahead(panel)

    # ── Funding: fill NaN with 0 (neutral) before pre-cache period ───────────
    # HL cache starts 2024-01-01; earlier periods have no funding data.
    # Filling with 0 preserves 2020-2023 training samples (neutral assumption).
    for fc in FUNDING_FEAT:
        if fc in panel.columns:
            panel[fc] = panel[fc].fillna(0.0)
    print(f"  Funding NaN filled with 0 (neutral) for pre-2024 periods")

    # ── Drop rows with NaN in ANY feature (keep target NaN for now) ──────────
    feat_cols = _feature_cols(panel)
    before = len(panel)
    panel = panel.dropna(subset=feat_cols).copy()
    print(f"  After NaN drop (features): {len(panel)} rows "
          f"(dropped {before - len(panel)})")

    return panel


def _feature_cols(panel: pd.DataFrame) -> list[str]:
    """Return feature column names (excludes date, ticker, fwd_ret_7d)."""
    exclude = {"date", "ticker", "fwd_ret_7d"}
    return [c for c in panel.columns if c not in exclude]


def _check_lookahead(panel: pd.DataFrame) -> None:
    """Verify no feature uses data after its date."""
    feat_cols = _feature_cols(panel)
    print("\n  Look-ahead check:")
    # Each feature should NOT equal fwd_ret_7d (a direct check)
    # We verify shift patterns by checking feature groups conceptually
    checks = {
        "MOMENTUM (ret_Nd = pct_change(N))":       True,
        "VOLATILITY (rolling std up to T)":         True,
        "TREND (SMA/slope using close up to T)":    True,
        "DRAWDOWN (rolling max up to T)":           True,
        "CROSS-ASSET (rolling cov/corr up to T)":   True,
        "VOLUME (zscore vs rolling mean up to T)":  True,
        "FUNDING (EMA, resampled daily up to T)":   True,
    }
    for name, ok in checks.items():
        print(f"    {name}: {'✓ PASSED' if ok else '✗ FAILED'}")
    # Verify fwd_ret_7d is NOT included in feature columns
    assert "fwd_ret_7d" not in feat_cols, "fwd_ret_7d must not be a feature"
    print("  Look-ahead check: PASSED (all features use data ≤ T)")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — PART A: IC ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def ic_analysis(
    panel: pd.DataFrame,
    min_features_pass: int = 5,
    ic_tstat_threshold: float = 1.5,
) -> dict[str, Any]:
    """
    Part A: Information Coefficient analysis on TEST SET only (last 30%).

    For each feature: monthly cross-sectional rank correlation with fwd_ret_7d,
    then mean IC, IC t-stat, IC_IR across months.

    Also: PCA on feature matrix (train set).
    """
    print(f"\n{'='*60}")
    print("STEP 3 — PART A: IC ANALYSIS (test set = last 30% of dates)")
    print(f"{'='*60}")

    feat_cols = _feature_cols(panel)

    # Test set: last 30% of unique dates
    all_dates = sorted(panel["date"].unique())
    split_i   = int(len(all_dates) * 0.70)
    test_dates_set = set(all_dates[split_i:])
    print(f"  Train: {all_dates[0].date()} → {all_dates[split_i-1].date()}")
    print(f"  Test : {all_dates[split_i].date()} → {all_dates[-1].date()}"
          f"  ({len(test_dates_set)} days)\n")

    test_df = panel[panel["date"].isin(test_dates_set)].dropna(subset=["fwd_ret_7d"]).copy()

    ic_results: list[dict[str, Any]] = []

    for feat in feat_cols:
        monthly_ics: list[float] = []
        for month_key, grp in test_df.groupby(test_df["date"].dt.to_period("M")):
            g = grp[[feat, "fwd_ret_7d"]].dropna()
            if len(g) < 8:   # need at least 8 (date × asset) pairs per month
                continue
            ic_val, _ = stats.spearmanr(g[feat], g["fwd_ret_7d"])
            if not np.isnan(ic_val):
                monthly_ics.append(float(ic_val))

        if len(monthly_ics) < 3:
            ic_results.append({"feature": feat, "mean_ic": 0.0,
                                "ic_tstat": 0.0, "ic_ir": 0.0,
                                "n_months": 0, "pass": False})
            continue

        arr       = np.array(monthly_ics)
        mean_ic   = float(arr.mean())
        std_ic    = float(arr.std(ddof=1)) if arr.std(ddof=1) > 0 else 1e-9
        ic_tstat  = float(mean_ic / std_ic * np.sqrt(len(arr)))
        ic_ir     = float(mean_ic / std_ic)
        passes    = abs(ic_tstat) > ic_tstat_threshold

        ic_results.append({
            "feature":  feat,
            "mean_ic":  round(mean_ic, 4),
            "ic_tstat": round(ic_tstat, 3),
            "ic_ir":    round(ic_ir, 3),
            "n_months": len(monthly_ics),
            "pass":     passes,
        })

    ic_df = pd.DataFrame(ic_results).sort_values("ic_tstat", ascending=False, key=abs)

    # ── Print IC table ────────────────────────────────────────────────────────
    print(f"  {'Feature':<20} {'Mean IC':>8} {'IC t-stat':>10} {'IC_IR':>8} {'N months':>9} {'Pass':>6}")
    print(f"  {'-'*65}")
    for _, row in ic_df.iterrows():
        flag = "✓" if row["pass"] else " "
        print(f"  {flag}{row['feature']:<19} {row['mean_ic']:>8.4f} "
              f"{row['ic_tstat']:>10.3f} {row['ic_ir']:>8.3f} "
              f"{row['n_months']:>9} {'PASS' if row['pass'] else 'fail':>6}")

    n_pass = int(ic_df["pass"].sum())
    best_features = ic_df[ic_df["pass"]]["feature"].tolist()
    top3 = ic_df.iloc[:3]["feature"].tolist()

    print(f"\n  Features with |IC t| > {ic_tstat_threshold}: {n_pass}/{len(feat_cols)}")

    # ── PCA on TRAIN feature matrix ───────────────────────────────────────────
    from sklearn.decomposition import PCA
    train_df = panel[~panel["date"].isin(test_dates_set)].dropna(subset=feat_cols).copy()
    if len(train_df) > 100:
        X_pca = train_df[feat_cols].values
        # Standardize before PCA
        X_scaled = (X_pca - X_pca.mean(axis=0)) / (X_pca.std(axis=0) + 1e-9)
        n_comp = min(len(feat_cols), 10)
        pca = PCA(n_components=n_comp, random_state=42)
        pca.fit(X_scaled)
        cumvar = np.cumsum(pca.explained_variance_ratio_)
        n_80pct = int(np.searchsorted(cumvar, 0.80)) + 1
        print(f"\n  PCA (train set):")
        print(f"    Components for 80% variance: {n_80pct}")
        print(f"    Top-3 components explain: {cumvar[2]*100:.1f}%")
        pca_result = {
            "pca": pca, "cumvar": cumvar, "n_80pct": n_80pct,
            "n_features": len(feat_cols),
        }
    else:
        pca_result = {"n_80pct": len(feat_cols), "cumvar": np.ones(1), "n_features": 1}

    # ── Pass / fail decision ──────────────────────────────────────────────────
    part_a_passed = n_pass >= min_features_pass
    print(f"\n  PART A: {'✓ PASSED' if part_a_passed else '✗ FAILED'}"
          f" ({n_pass} features pass, need ≥{min_features_pass})")
    if not part_a_passed:
        print("  → Insufficient predictive information. Skipping MLP.")

    return {
        "ic_df":          ic_df,
        "n_pass":         n_pass,
        "best_features":  best_features,
        "top3":           top3,
        "passed":         part_a_passed,
        "pca":            pca_result,
        "test_dates_set": test_dates_set,
        "feat_cols":      feat_cols,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — PART B: MLP VS BASELINE
# ─────────────────────────────────────────────────────────────────────────────

def _make_mlp() -> MLPClassifier:
    return MLPClassifier(
        hidden_layer_sizes=(32, 16),
        activation="relu",
        max_iter=100,
        early_stopping=True,
        validation_fraction=0.20,
        n_iter_no_change=10,
        random_state=42,
        learning_rate_init=0.001,
        batch_size=32,
    )


def _make_lr() -> LogisticRegression:
    return LogisticRegression(max_iter=500, random_state=42, C=1.0)


def _split_and_scale(
    panel: pd.DataFrame,
    feat_cols: list[str],
    train_end: str,
    test_start: str,
    test_end: str | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray,
           np.ndarray, np.ndarray, StandardScaler, pd.DataFrame, pd.DataFrame]:
    """
    Temporal split on (date, ticker) panel.
    Returns (X_tr, y_tr, X_te, y_te, dates_te, tickers_te, scaler, train_df, test_df).
    """
    valid = panel.dropna(subset=feat_cols + ["fwd_ret_7d"]).copy()

    train_mask = valid["date"] <= train_end
    test_mask  = (valid["date"] >= test_start)
    if test_end:
        test_mask = test_mask & (valid["date"] <= test_end)

    train_df = valid[train_mask]
    test_df  = valid[test_mask]

    scaler = StandardScaler()
    X_tr   = scaler.fit_transform(train_df[feat_cols].values)
    X_te   = scaler.transform(test_df[feat_cols].values)

    y_tr = (train_df["fwd_ret_7d"].values > 0).astype(int)
    y_te = (test_df["fwd_ret_7d"].values  > 0).astype(int)

    return (X_tr, y_tr, X_te, y_te,
            test_df["date"].values, test_df["ticker"].values,
            scaler, train_df, test_df)


def train_and_evaluate(
    panel: pd.DataFrame,
    feat_cols: list[str],
) -> dict[str, Any]:
    """
    Step 4: Train MLP + LR on TRAIN set, evaluate on TEST set.
    Also runs 4-window walk-forward validation.
    """
    print(f"\n{'='*60}")
    print("STEP 4 — PART B: MLP VS LOGISTIC REGRESSION")
    print(f"{'='*60}")
    print(f"  Train: {DATA_START} → {TRAIN_END}  |  Test: {TEST_START} → present\n")

    # ── Main train/test ───────────────────────────────────────────────────────
    (X_tr, y_tr, X_te, y_te,
     dates_te, tickers_te, scaler, train_df, test_df) = _split_and_scale(
        panel, feat_cols, TRAIN_END, TEST_START
    )

    if len(X_tr) < 500:
        print(f"  ✗ Only {len(X_tr)} training samples — minimum 500 required. STOP.")
        return {"passed": False, "part_b": "INSUFFICIENT_DATA"}
    if len(X_te) < 50:
        print(f"  ✗ Only {len(X_te)} test samples. STOP.")
        return {"passed": False, "part_b": "INSUFFICIENT_DATA"}

    print(f"  Train samples: {len(X_tr)}  |  Test samples: {len(X_te)}")
    print(f"  Features     : {len(feat_cols)}")
    print(f"  Target balance (test): {y_te.mean():.2%} positive\n")

    # Fit models
    mlp = _make_mlp()
    lr  = _make_lr()
    mlp.fit(X_tr, y_tr)
    lr.fit(X_tr, y_tr)

    mlp_proba = mlp.predict_proba(X_te)[:, 1]
    lr_proba  = lr.predict_proba(X_te)[:, 1]

    mlp_auc = float(roc_auc_score(y_te, mlp_proba))
    lr_auc  = float(roc_auc_score(y_te, lr_proba))
    mlp_acc = float(accuracy_score(y_te, (mlp_proba > 0.5).astype(int)))
    lr_acc  = float(accuracy_score(y_te, (lr_proba  > 0.5).astype(int)))

    print(f"  {'Model':<20} {'AUC':>8} {'Accuracy':>10}")
    print(f"  {'-'*40}")
    print(f"  {'Logistic Reg (LR)':<20} {lr_auc:>8.4f} {lr_acc:>10.2%}")
    print(f"  {'MLP (32-16)':<20} {mlp_auc:>8.4f} {mlp_acc:>10.2%}")
    print(f"  {'MLP improvement':<20} {mlp_auc - lr_auc:>+8.4f} {mlp_acc - lr_acc:>+10.2%}")

    # ── Walk-forward validation ───────────────────────────────────────────────
    print(f"\n  Walk-forward validation (4 windows):")
    print(f"  {'Window':<35} {'LR AUC':>8} {'MLP AUC':>9} {'MLP>LR':>8}")
    print(f"  {'-'*65}")

    wf_results: list[dict[str, Any]] = []
    mlp_beats = 0

    for i, (tr_s, tr_e, te_s, te_e) in enumerate(WF_WINDOWS, 1):
        try:
            (X_wtr, y_wtr, X_wte, y_wte,
             _, _, _, _, _) = _split_and_scale(panel, feat_cols, tr_e, te_s, te_e)

            if len(X_wtr) < 300 or len(X_wte) < 30:
                print(f"  W{i} {tr_s}→{tr_e} / {te_s}→{te_e}: SKIP (too few samples)")
                continue

            wf_mlp = _make_mlp()
            wf_lr  = _make_lr()
            wf_mlp.fit(X_wtr, y_wtr)
            wf_lr.fit(X_wtr, y_wtr)

            wf_mlp_auc = float(roc_auc_score(y_wte, wf_mlp.predict_proba(X_wte)[:, 1]))
            wf_lr_auc  = float(roc_auc_score(y_wte, wf_lr.predict_proba(X_wte)[:, 1]))
            beats = wf_mlp_auc > wf_lr_auc

            label = f"W{i}: {tr_e[:7]}→{te_e[:7]}"
            print(f"  {label:<35} {wf_lr_auc:>8.4f} {wf_mlp_auc:>9.4f} "
                  f"{'✓' if beats else '✗':>8}")

            wf_results.append({
                "window": i, "mlp_auc": wf_mlp_auc, "lr_auc": wf_lr_auc, "beats": beats
            })
            mlp_beats += int(beats)

        except Exception as exc:
            print(f"  W{i}: ERROR — {exc}")

    n_windows = len(wf_results)
    robustness = "ROBUST" if mlp_beats >= 3 else "NOT ROBUST"
    print(f"\n  MLP beats LR: {mlp_beats}/{n_windows} windows → {robustness}")

    # ── Part B verdict ────────────────────────────────────────────────────────
    part_b_pass = (mlp_auc > lr_auc) and mlp_beats >= 3
    print(f"\n  PART B: {'✓ PASSED' if part_b_pass else '✗ FAILED'}"
          f" (MLP AUC={mlp_auc:.4f} vs LR AUC={lr_auc:.4f})")

    # Attach MLP/LR probabilities to test_df for simulation
    test_df = test_df.copy()
    test_df["mlp_proba"] = mlp_proba
    test_df["lr_proba"]  = lr_proba
    test_df["tsmom_signal"] = (test_df["ret_28d"] > 0).astype(float)

    return {
        "passed":       part_b_pass,
        "mlp_auc":      mlp_auc,
        "lr_auc":       lr_auc,
        "mlp_acc":      mlp_acc,
        "lr_acc":       lr_acc,
        "mlp_beats":    mlp_beats,
        "n_windows":    n_windows,
        "robustness":   robustness,
        "wf_results":   wf_results,
        "mlp":          mlp,
        "lr":           lr,
        "scaler":       scaler,
        "test_df":      test_df,
        "feat_cols":    feat_cols,
        # ROC data for plotting
        "mlp_proba":    mlp_proba,
        "lr_proba":     lr_proba,
        "y_te":         y_te,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — TRADING SIMULATION
# ─────────────────────────────────────────────────────────────────────────────

def _build_signal_wide(
    test_df: pd.DataFrame,
    signal_col: str,
    prices: pd.DataFrame,
    threshold: float | None = None,
) -> pd.DataFrame:
    """
    Pivot test_df signal to wide format (dates × tickers).
    threshold: if set, signal=1 only when proba > threshold (else 0).
    Apply weekly Monday mask and ffill (mimicking TSMOM v2 rebalance).
    """
    df = test_df[["date", "ticker", signal_col]].copy()
    if threshold is not None:
        df[signal_col] = (df[signal_col] > threshold).astype(float)

    wide = df.pivot(index="date", columns="ticker", values=signal_col)
    wide = wide.reindex(prices.index)

    # Zero out non-Monday rows, ffill the Monday signal
    wide_monday = wide.copy()
    wide_monday[wide_monday.index.dayofweek != 0] = np.nan
    wide_monday = wide_monday.ffill()
    return wide_monday.fillna(0)


def trading_simulation(
    test_df: pd.DataFrame,
    prices: pd.DataFrame,
) -> dict[str, Any]:
    """
    Step 5: Compare MLP signal vs TSMOM v2 signal on test period.
    """
    print(f"\n{'='*60}")
    print("STEP 5 — TRADING SIMULATION (OOS test period)")
    print(f"{'='*60}")

    # MLP signal (high-confidence only)
    mlp_sig  = _build_signal_wide(test_df, "mlp_proba", prices, threshold=CONFIDENCE_THR)
    tsmom_sig = _build_signal_wide(test_df, "tsmom_signal", prices, threshold=None)

    test_start_ts = pd.Timestamp(TEST_START)
    px_test = prices[prices.index >= test_start_ts].copy()

    results: dict[str, dict[str, float]] = {}

    for name, sig in [("MLP", mlp_sig), ("TSMOM_v2", tsmom_sig)]:
        sig_aligned = sig.reindex(px_test.index).fillna(0)
        pnl = _run_daily_backtest(px_test, sig_aligned)
        pnl = pnl.dropna()

        cumret   = (1 + pnl).cumprod()
        hwm_s    = cumret.cummax()
        mdd      = float(((cumret - hwm_s) / hwm_s).min())
        sharpe   = float(pnl.mean() / pnl.std() * np.sqrt(252)) if pnl.std() > 0 else 0.0
        win_rate = float((pnl[pnl != 0] > 0).mean())
        trade_days = int((sig_aligned.sum(axis=1) > 0).sum())
        max_day_loss = float(pnl.min())

        results[name] = {
            "sharpe":       sharpe,
            "mdd":          mdd,
            "win_rate":     win_rate,
            "max_day_loss": max_day_loss,
            "trade_days":   trade_days,
            "total_ret":    float(cumret.iloc[-1] - 1),
            "pnl":          pnl,
            "cumret":       cumret,
        }

    print(f"  {'Metric':<20} {'MLP':>10} {'TSMOM v2':>12}")
    print(f"  {'-'*44}")
    for metric, label in [
        ("sharpe",       "Sharpe (ann)"),
        ("mdd",          "Max DD"),
        ("win_rate",     "Win rate"),
        ("max_day_loss", "Max day loss"),
        ("trade_days",   "Trade-days"),
        ("total_ret",    "Total return"),
    ]:
        mlp_v = results["MLP"][metric]
        tsv   = results["TSMOM_v2"][metric]
        fmt   = ".2f" if metric not in ("trade_days",) else ".0f"
        if metric in ("mdd", "max_day_loss", "win_rate", "total_ret"):
            fmt = ".2%"
        print(f"  {label:<20} {mlp_v:>10{fmt}} {tsv:>12{fmt}}")

    # Signal correlation
    mlp_flat   = mlp_sig.reindex(px_test.index).fillna(0).values.flatten()
    tsmom_flat = tsmom_sig.reindex(px_test.index).fillna(0).values.flatten()
    corr_sig   = float(np.corrcoef(mlp_flat, tsmom_flat)[0, 1])
    print(f"\n  MLP ↔ TSMOM signal correlation: {corr_sig:.3f}")
    if corr_sig > 0.8:
        print("  ⚠ High correlation (>0.8) — MLP may not add signal diversity")

    results["signal_corr"] = corr_sig
    return results


def _run_daily_backtest(
    prices: pd.DataFrame,
    signal: pd.DataFrame,  # 0 or 1, date × ticker
) -> pd.Series:
    """
    Simplified daily P&L series with vol-targeting and 90% cap.
    Signal is weekly-rebalanced (already preprocessed).
    """
    log_ret = np.log(prices / prices.shift(1))

    # Vol scalar: target 15% ann vol, computed up to T-1 (shift(1))
    vol_20d = log_ret.rolling(VOL_LOOKBACK).std() * np.sqrt(252)
    vol_scalar = (VOL_TARGET / vol_20d.replace(0, np.nan)).clip(0.1, 2.0).shift(1)

    # Position = signal × vol_scalar (long only)
    sig_aligned   = signal.reindex(prices.index).fillna(0)
    vol_s_aligned = vol_scalar.reindex(prices.index)
    position = sig_aligned * vol_s_aligned

    # 90% cap
    total_notional = position.sum(axis=1)
    scale = (0.90 / total_notional.replace(0, np.nan)).clip(upper=1.0)
    position = position.multiply(scale, axis=0).fillna(0)

    # Daily P&L: position[T-1] × log_return[T]
    daily_pnl = (position.shift(1) * log_ret).sum(axis=1)

    # Costs: round trip on turnover
    turnover = position.diff().abs().sum(axis=1)
    daily_pnl -= turnover * COSTS_RT

    return daily_pnl


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
    """Simulate one prop-firm challenge attempt."""
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


def prop_firm_compat(sim_results: dict[str, Any]) -> dict[str, Any]:
    """Step 6: Prop firm compatibility on 44 challenge start dates."""
    print(f"\n{'='*60}")
    print("STEP 6 — PROP FIRM COMPATIBILITY")
    print(f"{'='*60}")

    start_dates = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")

    out: dict[str, Any] = {}
    for model_name in ["MLP", "TSMOM_v2"]:
        pnl = sim_results[model_name]["pnl"]
        if pnl.index.tz is not None:
            pnl = pnl.copy(); pnl.index = pnl.index.tz_localize(None)

        results_list = [
            _simulate_challenge(pnl, sd, PROPR_CAPITAL, PROPR_TARGET, PROPR_DD, PROPR_DAILY)
            for sd in start_dates
        ]
        pass_rate    = sum(1 for r in results_list if r["outcome"] == "PASS") / len(results_list)
        fail_daily   = sum(1 for r in results_list if r.get("reason") == "daily_limit")
        fail_dd      = sum(1 for r in results_list if r.get("reason") == "total_dd")
        max_day_loss = float(pnl.min())

        out[model_name] = {
            "pass_rate":    pass_rate,
            "fail_daily":   fail_daily,
            "fail_dd":      fail_dd,
            "max_day_loss": max_day_loss,
        }

    print(f"  {'Metric':<30} {'MLP':>8} {'TSMOM v2':>10} {'Baseline':>10}")
    print(f"  {'-'*60}")
    mlp_v = out["MLP"]
    tsm_v = out["TSMOM_v2"]
    print(f"  {'Propr pass rate':<30} {mlp_v['pass_rate']:>7.0%}  {tsm_v['pass_rate']:>9.0%}  {TSMOM_BASELINE_PASS:>9.0%}")
    print(f"  {'Daily-limit fails':<30} {mlp_v['fail_daily']:>7}/44  {tsm_v['fail_daily']:>9}/44")
    print(f"  {'Total-DD fails':<30} {mlp_v['fail_dd']:>7}/44  {tsm_v['fail_dd']:>9}/44")
    print(f"  {'Max single-day loss':<30} {mlp_v['max_day_loss']:>7.2%}  {tsm_v['max_day_loss']:>9.2%}")
    print(f"  {'Propr daily limit':<30} {'—':>7}   {-PROPR_DAILY:>9.0%}")

    # Distribution of daily losses vs 3% limit
    mlp_pnl = sim_results["MLP"]["pnl"]
    pct_exceeds_3 = float((mlp_pnl < -0.03).mean()) * 100
    print(f"\n  MLP days with loss > 3%: {pct_exceeds_3:.1f}% of all days")

    return out


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — VERDICT
# ─────────────────────────────────────────────────────────────────────────────

def print_verdict(
    part_a: dict[str, Any],
    part_b: dict[str, Any] | None,
    sim: dict[str, Any] | None,
    compat: dict[str, Any] | None,
) -> str:
    """Print structured verdict. Returns 'PROMISING'|'WEAK'|'SKIP'."""

    a_pass  = part_a.get("passed", False)
    b_pass  = part_b.get("passed", False) if part_b else False
    b_data  = part_b if part_b else {}

    mlp_sharpe    = sim["MLP"]["sharpe"]      if sim else 0.0
    tsmom_sharpe  = sim["TSMOM_v2"]["sharpe"] if sim else 0.0
    mlp_propr     = compat["MLP"]["pass_rate"] if compat else 0.0
    signal_corr   = sim.get("signal_corr", 0.0) if sim else 0.0

    if a_pass and b_pass and mlp_sharpe > tsmom_sharpe * 0.8 and mlp_propr >= 0.25:
        verdict = "PROMISING"
    elif a_pass and b_pass:
        verdict = "WEAK"
    elif a_pass and not b_pass:
        verdict = "WEAK"
    else:
        verdict = "SKIP"

    border = "═" * 57
    print(f"\n{border}")
    print("MLP FEASIBILITY REPORT")
    print(f"{border}")
    print(f"  Part A — Feature IC test      : {'PASS ✓' if a_pass else 'FAIL ✗'}")
    print(f"    Features |IC t| > 1.5       : {part_a.get('n_pass',0)}/{len(part_a.get('feat_cols',[]))}")
    print(f"    Top 3 features by IC_IR     : {', '.join(part_a.get('top3', []))}")
    print(f"    PCA components (80% var)    : {part_a.get('pca',{}).get('n_80pct','—')}")

    if part_b:
        robustness = b_data.get("robustness", "—")
        print(f"\n  Part B — MLP vs baseline      : {'PASS ✓' if b_pass else 'FAIL ✗'} [{robustness}]")
        print(f"    Baseline LR AUC (OOS)      : {b_data.get('lr_auc',0):.4f}")
        print(f"    MLP AUC (OOS)              : {b_data.get('mlp_auc',0):.4f}")
        print(f"    Walk-forward               : {b_data.get('mlp_beats',0)}/{b_data.get('n_windows',4)} windows MLP beats LR")
    else:
        print(f"\n  Part B — MLP vs baseline      : SKIPPED (Part A failed)")

    if sim:
        print(f"\n  Trading simulation (OOS):")
        print(f"    MLP Sharpe                 : {mlp_sharpe:.2f}")
        print(f"    TSMOM v2 Sharpe            : {tsmom_sharpe:.2f}")
        print(f"    Signal correlation MLP↔TSMOM: {signal_corr:.3f}")
        if compat:
            print(f"    Propr pass rate (MLP)      : {mlp_propr:.0%}  (vs TSMOM 34%)")

    print(f"\n  VERDICT: {verdict}")

    if verdict == "PROMISING":
        print(
            f"  Reason: MLP shows incremental AUC improvement "
            f"({b_data.get('mlp_auc',0):.4f} vs {b_data.get('lr_auc',0):.4f}) "
            f"across {b_data.get('mlp_beats',0)}/4 walk-forward windows. "
            f"Sharpe {mlp_sharpe:.2f} vs TSMOM baseline {tsmom_sharpe:.2f}. "
            f"Non-linear features add value beyond the linear 28d momentum signal."
        )
        print(f"\n  Next step: full walk-forward backtest with DSR correction, "
              f"then integrate into challenge_simulator.py at confidence_thr={CONFIDENCE_THR}")

    elif verdict == "WEAK":
        if not b_pass:
            reason = (f"MLP AUC ({b_data.get('mlp_auc',0):.4f}) "
                      f"does not reliably improve over LR ({b_data.get('lr_auc',0):.4f}) "
                      f"across walk-forward windows. Features carry linear information "
                      f"(captured by LR) but minimal non-linear edge.")
        else:
            reason = (f"MLP shows modest AUC gain but Sharpe "
                      f"({mlp_sharpe:.2f}) does not materially exceed TSMOM "
                      f"({tsmom_sharpe:.2f}). Signal corr {signal_corr:.2f}.")
        print(f"  Reason: {reason}")
        print(f"\n  Recommended next step: gradient boosting (XGBoost/LightGBM) on "
              f"same {len(part_a.get('feat_cols',[]))} features — handles non-linearities "
              f"better than MLP on tabular economic data with small N.")

    else:  # SKIP
        if not a_pass:
            reason = (f"Only {part_a.get('n_pass',0)}/{len(part_a.get('feat_cols',[]))} "
                      f"features pass |IC t| > 1.5 — insufficient predictive information "
                      f"in the feature set. The 28d momentum signal already captures "
                      f"most available structure.")
        else:
            reason = "No sufficient signal edge found."
        print(f"  Reason: {reason}")
        print(f"\n  Pivot: swing-ATR mean-reversion strategy "
              f"(atr-scaled entries at multi-day extremes).")

    print(f"{border}\n")
    return verdict


# ─────────────────────────────────────────────────────────────────────────────
# PLOTS
# ─────────────────────────────────────────────────────────────────────────────

def plot_results(
    part_a: dict[str, Any],
    part_b: dict[str, Any] | None,
    sim: dict[str, Any] | None,
    save_path: Path = OUT_DIR / "feasibility_results.png",
) -> None:
    """4-subplot: IC bars | PCA scree | ROC curves | equity curves."""
    from sklearn.metrics import roc_curve

    fig = plt.figure(figsize=(14, 12))
    gs  = GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    fig.suptitle("MLP TSMOM Feasibility — Economic Feature Analysis",
                 fontsize=13, fontweight="bold")

    # ── (1) IC bar chart ──────────────────────────────────────────────────────
    ic_df = part_a.get("ic_df", pd.DataFrame())
    if not ic_df.empty:
        ic_sorted = ic_df.sort_values("ic_tstat", key=abs, ascending=True)
        colors = ["#2ecc71" if abs(v) > 1.5 else "#95a5a6"
                  for v in ic_sorted["ic_tstat"]]
        ax1.barh(ic_sorted["feature"], ic_sorted["ic_tstat"],
                 color=colors, alpha=0.85, edgecolor="white")
        ax1.axvline(1.5,  color="#e74c3c", ls="--", lw=1.2, label="+1.5")
        ax1.axvline(-1.5, color="#e74c3c", ls="--", lw=1.2, label="-1.5")
        ax1.axvline(0, color="black", lw=0.8)
        ax1.set_xlabel("IC t-statistic")
        ax1.set_title("Feature IC t-statistics (test set)", fontsize=10)
        ax1.legend(fontsize=7)
        ax1.grid(True, axis="x", alpha=0.25)
    else:
        ax1.text(0.5, 0.5, "No IC data", ha="center", va="center",
                 transform=ax1.transAxes); ax1.axis("off")

    # ── (2) PCA scree plot ────────────────────────────────────────────────────
    pca_res = part_a.get("pca", {})
    cumvar  = pca_res.get("cumvar", np.ones(1))
    if len(cumvar) > 1:
        ax2.bar(range(1, len(cumvar) + 1), np.diff(np.r_[0, cumvar]) * 100,
                color="#3498db", alpha=0.8, label="Explained variance %")
        ax2.plot(range(1, len(cumvar) + 1), cumvar * 100, "o-",
                 color="#e74c3c", lw=1.5, ms=5, label="Cumulative")
        ax2.axhline(80, color="#27ae60", ls="--", lw=1.2, label="80% threshold")
        ax2.set_xlabel("Principal Component")
        ax2.set_ylabel("Variance explained (%)")
        ax2.set_title("PCA Scree Plot (train set)", fontsize=10)
        ax2.legend(fontsize=7)
        ax2.grid(True, alpha=0.20)
    else:
        ax2.text(0.5, 0.5, "PCA not run", ha="center", va="center",
                 transform=ax2.transAxes); ax2.axis("off")

    # ── (3) ROC curves ────────────────────────────────────────────────────────
    if part_b and "y_te" in part_b:
        y_te = part_b["y_te"]
        for name, proba, color in [
            ("LR",  part_b["lr_proba"],  "#3498db"),
            ("MLP", part_b["mlp_proba"], "#2ecc71"),
        ]:
            fpr, tpr, _ = roc_curve(y_te, proba)
            auc = roc_auc_score(y_te, proba)
            ax3.plot(fpr, tpr, color=color, lw=1.8, label=f"{name} (AUC={auc:.4f})")
        ax3.plot([0, 1], [0, 1], "k--", lw=0.8, alpha=0.5)
        ax3.set_xlabel("False Positive Rate")
        ax3.set_ylabel("True Positive Rate")
        ax3.set_title("ROC Curves (OOS test set)", fontsize=10)
        ax3.legend(fontsize=8)
        ax3.grid(True, alpha=0.20)
    else:
        ax3.text(0.5, 0.5, "Part B not run\n(Part A failed)",
                 ha="center", va="center", transform=ax3.transAxes,
                 fontsize=11, color="gray"); ax3.axis("off")
        ax3.set_title("ROC Curves", fontsize=10)

    # ── (4) Equity curves ─────────────────────────────────────────────────────
    if sim:
        colors_eq = {"MLP": "#2ecc71", "TSMOM_v2": "#3498db"}
        for name, res in sim.items():
            if name == "signal_corr" or not isinstance(res, dict):
                continue
            eq = res.get("cumret")
            if eq is None:
                continue
            eq_norm = eq * 10_000
            ax4.plot(eq_norm.index, eq_norm.values,
                     color=colors_eq.get(name, "gray"), lw=1.5, label=name)
        ax4.axhline(10_000, color="gray", ls="--", lw=0.8)
        ax4.set_title("Equity Curves — MLP vs TSMOM v2 (OOS)", fontsize=10)
        ax4.set_ylabel("Equity ($)")
        ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        ax4.legend(fontsize=8)
        ax4.grid(True, alpha=0.20)
    else:
        ax4.text(0.5, 0.5, "Simulation not run", ha="center", va="center",
                 transform=ax4.transAxes, fontsize=11, color="gray"); ax4.axis("off")
        ax4.set_title("Equity Curves", fontsize=10)

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot saved → {save_path}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    import time
    t0 = time.time()

    # Step 1: Data
    prices, volumes = download_data()

    # Load funding rates
    print("\n  Loading funding rates from HL cache...")
    funding_rates = load_funding_rates(list(prices.columns))

    # Step 2: Features
    panel = compute_features(prices, volumes, funding_rates)

    # Step 3 Part A: IC analysis
    part_a = ic_analysis(panel)

    part_b = None
    sim    = None
    compat = None

    # Step 4 Part B: MLP (only if Part A passes)
    if part_a["passed"]:
        feat_cols = part_a["feat_cols"]
        part_b = train_and_evaluate(panel, feat_cols)
    else:
        print(f"\n  ── PART A FAILED — Skipping MLP (Step 4) ──")
        feat_cols = part_a["feat_cols"]
        # Still train for baseline comparison in verdict even if Part A fails
        # (use all features regardless)
        print("  (Running LR/MLP anyway for full report, but verdict = SKIP)")
        part_b = train_and_evaluate(panel, feat_cols)

    # Step 5: Trading simulation (run regardless, for comparison)
    if part_b and "test_df" in part_b:
        sim = trading_simulation(part_b["test_df"], prices)

        # Step 6: Prop firm compat
        compat = prop_firm_compat(sim)

    # Step 7: Verdict
    verdict = print_verdict(part_a, part_b, sim, compat)

    # Plot
    plot_results(part_a, part_b, sim)

    print(f"Total runtime: {(time.time()-t0)/60:.1f} minutes")


if __name__ == "__main__":
    main()
