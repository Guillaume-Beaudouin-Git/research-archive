"""
XGBoost v2 — Ensemble + Purged Walk-Forward + High-Confidence Filter
=====================================================================

Key fix over v1: stay within the SAME universe (BTC+ETH+SOL+…),
use cross-sectional labels (outperform median), and filter to the top
10-20% most-confident predictions — where the edge is concentrated
(ScienceDirect 2022: accuracy 57-59% on top-10% vs 52-54% overall).

Data:
  10 assets: BTC ETH SOL AVAX LINK DOGE ADA DOT LTC BCH (HL perps + yfinance)
  HL funding: strategies/cs_carry/data/{ASSET}_hl_funding.csv (2024-2026)

Purged walk-forward (4 windows, 4-week purge gap):
  W1: train→2022-12, test 2023
  W2: train→2023-12, test 2024-H1
  W3: train→2024-06, test 2024-H2
  W4: train→2024-12, test 2025

Ensemble: XGBClassifier + LGBMClassifier, average probas.

Confidence filter: trade only top 20% / top 10% most-confident predictions
                   (|proba - 0.5| > 80th / 90th percentile at each date).

DEPLOY: best SR > 1.2 AND AUC(top10%) > 0.55 AND corr(TSMOM) < 0.50 AND DSR > 0.35
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import warnings
warnings.filterwarnings("ignore")

# ── dependency check ──────────────────────────────────────────────────────────
try:
    import lightgbm as lgb
    from lightgbm import LGBMClassifier
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "lightgbm", "--quiet"], check=True)
    import lightgbm as lgb
    from lightgbm import LGBMClassifier

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier
import shap

from dsr import deflated_sharpe_ratio
from strategies.tsmom_v3.backtest import (
    download_data as tsmom_download, compute_pnl as tsmom_compute_pnl,
    VOL_TARGET as TSMOM_VOL,
)
from strategies.tsmom_v3.signal import continuous_signal, build_positions

# ── constants ─────────────────────────────────────────────────────────────────
TICKERS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD",
    "DOGE-USD", "ADA-USD", "DOT-USD", "LTC-USD", "BCH-USD",
]
ASSETS = [t.replace("-USD", "") for t in TICKERS]   # BTC, ETH, …

REPO_ROOT    = Path(__file__).resolve().parents[2]
CARRY_DIR    = REPO_ROOT / "strategies" / "cs_carry" / "data"
DATA_START   = "2020-01-01"
DATA_END     = "2026-05-14"
VOL_TGT      = 0.15
COST_RT      = 0.0017
N_LONG       = 3
N_SHORT      = 3
N_TRIALS_DSR = 30     # all configs tested in this project

FEAT_NAMES = [
    "bollinger_z", "rsi_norm", "ema_cross_1_21", "ema_cross_21_50",
    "ema_cross_50_100", "vol_z", "ret_1w", "ret_4w", "vol_ratio",
    "funding_z", "oi_chg_7d", "vol_oi_ratio",
]

WF_WINDOWS = [
    {"train_end": "2022-12-31", "test_start": "2023-01-01", "test_end": "2023-12-31"},
    {"train_end": "2023-12-31", "test_start": "2024-01-01", "test_end": "2024-06-30"},
    {"train_end": "2024-06-30", "test_start": "2024-07-01", "test_end": "2024-12-31"},
    {"train_end": "2024-12-31", "test_start": "2025-01-01", "test_end": "2025-12-31"},
]
PURGE_WEEKS = 4


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════

def load_prices() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (close, volume, log_ret) — daily, tz-naive."""
    import yfinance as yf
    print(f"[data] Downloading {len(TICKERS)} assets …")
    raw = yf.download(TICKERS, start=DATA_START, end=DATA_END,
                      auto_adjust=True, progress=False)
    close  = raw["Close"].copy()
    volume = raw["Volume"].copy()
    if isinstance(close.columns, pd.MultiIndex):
        close  = close.droplevel(0, axis=1)
        volume = volume.droplevel(0, axis=1)
    # rename to short keys
    close.columns  = [c.replace("-USD", "") for c in close.columns]
    volume.columns = [c.replace("-USD", "") for c in volume.columns]
    close  = close.ffill()
    volume = volume.ffill()
    log_ret = np.log(close / close.shift(1)).clip(-1, 1)
    print(f"  Range: {close.index[0].date()} → {close.index[-1].date()}  "
          f"Assets: {list(close.columns)}")
    return close, volume, log_ret


def load_funding_weekly() -> pd.DataFrame:
    """
    Load hourly HL funding from cs_carry/data, resample to W-FRI mean,
    then build funding_z = (mean_7d - mean_30d) / std_30d.
    Returns wide DataFrame (week × asset), 0.0 where data missing.
    """
    weekly_series: dict[str, pd.Series] = {}
    for asset in ASSETS:
        path = CARRY_DIR / f"{asset}_hl_funding.csv"
        if not path.exists():
            weekly_series[asset] = pd.Series(dtype=float, name=asset)
            continue
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index, format="mixed", utc=True).tz_localize(None)
        s = df.iloc[:, 0].sort_index()  # first column = funding rate
        # weekly mean
        w = s.resample("W-FRI").mean()
        # funding_z: rolling 7-week mean vs 30-week mean, normalized
        m7  = w.rolling(7,  min_periods=3).mean()
        m30 = w.rolling(30, min_periods=10).mean()
        s30 = w.rolling(30, min_periods=10).std()
        fz  = (m7 - m30) / (s30 + 1e-12)
        weekly_series[asset] = fz
    result = pd.DataFrame(weekly_series).sort_index()
    # fill NaN (pre-2024 and missing) with 0
    result = result.fillna(0.0)
    print(f"[data] Funding z-scores: {result.shape}, "
          f"{result.index[0].date()} → {result.index[-1].date()}")
    return result


# ══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════════════════════════

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    ag    = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    al    = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    return 100 - 100 / (1 + ag / (al + 1e-12))


def compute_features_asset(
    close:  pd.Series,
    volume: pd.Series,
    log_ret: pd.Series,
    funding_z: pd.Series,
) -> pd.DataFrame:
    """
    Compute 12 daily features for one asset, then resample to W-FRI.
    All features use shift(1) for no look-ahead.
    Returns DataFrame indexed by W-FRI dates.
    """
    c = close.copy()

    # F1: Bollinger z
    ma20   = c.rolling(20, min_periods=10).mean()
    std20  = c.rolling(20, min_periods=10).std()
    boll   = (c - ma20) / (2 * std20 + 1e-12)

    # F2: RSI-14 normalized
    rsi_raw  = _rsi(c, 14)
    rsi_norm = (rsi_raw - 50) / 50

    # F3–F5: EMA crossovers
    e1   = c.ewm(span=1,   min_periods=1,   adjust=False).mean()
    e21  = c.ewm(span=21,  min_periods=10,  adjust=False).mean()
    e50  = c.ewm(span=50,  min_periods=25,  adjust=False).mean()
    e100 = c.ewm(span=100, min_periods=50,  adjust=False).mean()
    cross_1_21   = e1  / (e21  + 1e-12) - 1
    cross_21_50  = e21 / (e50  + 1e-12) - 1
    cross_50_100 = e50 / (e100 + 1e-12) - 1

    # F6: Volume z-score
    vol_ma20  = volume.rolling(20, min_periods=10).mean()
    vol_std20 = volume.rolling(20, min_periods=10).std()
    vol_z     = (volume - vol_ma20) / (vol_std20 + 1e-12)

    # F7: 1-week return
    ret_1w = log_ret.rolling(5, min_periods=3).sum()

    # F8: 4-week return
    ret_4w = log_ret.rolling(20, min_periods=10).sum()

    # F9: vol ratio (short-term / long-term vol regime)
    std5d  = log_ret.rolling(5,  min_periods=3).std()
    std20d = log_ret.rolling(20, min_periods=10).std()
    vol_ratio = std5d / (std20d + 1e-12)

    # Stack daily
    daily = pd.DataFrame({
        "bollinger_z":     boll,
        "rsi_norm":        rsi_norm,
        "ema_cross_1_21":  cross_1_21,
        "ema_cross_21_50": cross_21_50,
        "ema_cross_50_100":cross_50_100,
        "vol_z":           vol_z,
        "ret_1w":          ret_1w,
        "ret_4w":          ret_4w,
        "vol_ratio":       vol_ratio,
    })

    # Resample to W-FRI (last value of week), then shift(1)
    weekly = daily.resample("W-FRI").last().shift(1)

    # F10: funding_z (already weekly, just align)
    fz_aligned = funding_z.reindex(weekly.index, fill_value=0.0)
    weekly["funding_z"]    = fz_aligned.values
    weekly["oi_chg_7d"]    = 0.0
    weekly["vol_oi_ratio"] = 0.0

    return weekly[FEAT_NAMES]


def build_feature_panel(
    close:    pd.DataFrame,
    volume:   pd.DataFrame,
    log_ret:  pd.DataFrame,
    funding:  pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """
    Returns dict: asset → DataFrame(week × 12 features), weekly W-FRI.
    """
    panels = {}
    for asset in ASSETS:
        if asset not in close.columns:
            continue
        fz = funding[asset] if asset in funding.columns else pd.Series(dtype=float)
        panels[asset] = compute_features_asset(
            close[asset], volume[asset], log_ret[asset], fz
        )
    print(f"[feat] Feature panel: {len(panels)} assets, "
          f"{next(iter(panels.values())).shape[0]} weekly obs each")
    return panels


def build_target(log_ret: pd.DataFrame) -> pd.DataFrame:
    """
    Cross-sectional binary target: y[i,T] = 1 if asset i's next-week
    5-day return > median across all assets.
    Returns wide DataFrame (week × asset), weekly W-FRI.
    """
    fwd_5d  = log_ret.rolling(5, min_periods=3).sum().shift(-5)
    fwd_w   = fwd_5d.resample("W-FRI").last()
    fwd_w.columns = [c.replace("-USD", "") for c in fwd_w.columns
                     if "-USD" in c] or fwd_w.columns.tolist()
    fwd_w   = fwd_w[[a for a in ASSETS if a in fwd_w.columns]]
    median  = fwd_w.median(axis=1)
    y       = (fwd_w.gt(median, axis=0)).astype(int)
    print(f"[target] Cross-sectional target: shape {y.shape}, "
          f"pos_rate {y.stack().mean():.3f}")
    return y


def cs_zscore_panel(feat_panel: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """
    At each weekly date T, zscore each feature across the 10 assets.
    Modifies feat_panel in-place and returns it.
    """
    # Collect all assets' data into a 3D structure: date × asset × feature
    dates   = next(iter(feat_panel.values())).index
    normed  = {a: feat_panel[a].copy() for a in feat_panel}
    for feat in FEAT_NAMES:
        # Build (date × asset) matrix for this feature
        mat = pd.DataFrame(
            {a: feat_panel[a][feat] for a in feat_panel if feat in feat_panel[a].columns},
            index=dates,
        )
        # zscore across assets at each date (axis=1)
        z = mat.subtract(mat.mean(axis=1), axis=0).divide(mat.std(axis=1) + 1e-8, axis=0)
        for a in feat_panel:
            if feat in feat_panel[a].columns:
                normed[a][feat] = z[a]
    return normed


# ══════════════════════════════════════════════════════════════════════════════
# DATASET STACKING
# ══════════════════════════════════════════════════════════════════════════════

def stack_dataset(
    feat_panel: dict[str, pd.DataFrame],
    target:     pd.DataFrame,
    date_start: str,
    date_end:   str,
    purge_after: str | None = None,
) -> tuple[np.ndarray, np.ndarray, pd.MultiIndex]:
    """
    Stack (asset, week) rows into X, y arrays for the given date range.
    purge_after: exclude rows with date > purge_after (for train purging).
    """
    rows_x, rows_y, rows_idx = [], [], []
    t0 = pd.Timestamp(date_start)
    t1 = pd.Timestamp(date_end)
    tp = pd.Timestamp(purge_after) if purge_after else None

    for asset in ASSETS:
        if asset not in feat_panel or asset not in target.columns:
            continue
        feat = feat_panel[asset]
        tgt  = target[asset]
        mask = (feat.index >= t0) & (feat.index <= t1)
        if tp is not None:
            mask = mask & (feat.index <= tp)
        f = feat.loc[mask].copy()
        y = tgt.reindex(f.index)
        valid = y.notna() & f.notna().all(axis=1)
        f, y = f.loc[valid], y.loc[valid]
        for dt in f.index:
            rows_x.append(f.loc[dt].values)
            rows_y.append(int(y.loc[dt]))
            rows_idx.append((dt, asset))

    if not rows_x:
        return np.empty((0, len(FEAT_NAMES))), np.empty(0), pd.MultiIndex.from_tuples([])

    X   = np.array(rows_x, dtype=np.float32)
    y   = np.array(rows_y, dtype=np.int32)
    idx = pd.MultiIndex.from_tuples(rows_idx, names=["date", "asset"])
    return X, y, idx


# ══════════════════════════════════════════════════════════════════════════════
# WALK-FORWARD TRAINING + PREDICTION
# ══════════════════════════════════════════════════════════════════════════════

def train_window(
    X_tr: np.ndarray,
    y_tr: np.ndarray,
    X_te: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Fits XGB + LGBM on train, predicts probas on test.
    Returns (proba_xgb, proba_lgbm, proba_ensemble).
    """
    params = dict(
        n_estimators=150, max_depth=3, learning_rate=0.05,
        subsample=0.7, colsample_bytree=0.7, min_child_weight=15,
    )
    xgb = XGBClassifier(**params, random_state=42,
                        eval_metric="logloss", verbosity=0)
    xgb.fit(X_tr, y_tr)
    p_xgb = xgb.predict_proba(X_te)[:, 1]

    lgbm = LGBMClassifier(**params, random_state=123, verbose=-1)
    lgbm.fit(X_tr, y_tr)
    p_lgbm = lgbm.predict_proba(X_te)[:, 1]

    p_ens = 0.5 * p_xgb + 0.5 * p_lgbm
    return p_xgb, p_lgbm, p_ens, xgb, lgbm


def run_purged_walkforward(
    feat_panel: dict[str, pd.DataFrame],
    target:     pd.DataFrame,
) -> tuple[pd.DataFrame, object, object]:
    """
    Run all 4 WF windows.
    Returns:
      pred_df: DataFrame columns [date, asset, proba_xgb, proba_lgbm, proba_ens, y_true]
      last_xgb, last_lgbm: models from final window (for SHAP)
    """
    all_rows = []
    last_xgb = last_lgbm = None
    last_X_te = None

    for w in WF_WINDOWS:
        te_s = w["test_start"]
        te_e = w["test_end"]
        tr_e = w["train_end"]

        # Purge: train data ends PURGE_WEEKS before test_start
        purge_cutoff = pd.Timestamp(te_s) - pd.Timedelta(weeks=PURGE_WEEKS)
        X_tr, y_tr, idx_tr = stack_dataset(
            feat_panel, target,
            DATA_START, tr_e,
            purge_after=purge_cutoff.strftime("%Y-%m-%d"),
        )
        X_te, y_te, idx_te = stack_dataset(feat_panel, target, te_s, te_e)

        if len(X_tr) < 50 or len(X_te) < 5:
            print(f"  W[{tr_e}→{te_s}:{te_e}] skip: "
                  f"train={len(X_tr)} test={len(X_te)}")
            continue

        print(f"  W[train→{tr_e}, test {te_s}→{te_e}]  "
              f"train={len(X_tr)} test={len(X_te)}", end=" ... ")

        p_xgb, p_lgbm, p_ens, xgb_m, lgbm_m = train_window(X_tr, y_tr, X_te)

        auc_all = roc_auc_score(y_te, p_ens)
        # Top-20% confidence AUC
        conf = np.abs(p_ens - 0.5)
        mask20 = conf >= np.percentile(conf, 80)
        auc20  = roc_auc_score(y_te[mask20], p_ens[mask20]) if mask20.sum() >= 5 else np.nan
        print(f"AUC(all)={auc_all:.4f}  AUC(top20%)={auc20:.4f}")

        for i, (dt, asset) in enumerate(idx_te):
            all_rows.append({
                "date": dt, "asset": asset,
                "proba_xgb":  float(p_xgb[i]),
                "proba_lgbm": float(p_lgbm[i]),
                "proba_ens":  float(p_ens[i]),
                "y_true":     int(y_te[i]),
            })

        last_xgb   = xgb_m
        last_lgbm  = lgbm_m
        last_X_te  = X_te

    pred_df = pd.DataFrame(all_rows)
    return pred_df, last_xgb, last_lgbm, last_X_te


# ══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO CONSTRUCTION
# ══════════════════════════════════════════════════════════════════════════════

def apply_confidence_filter(
    date_preds: pd.DataFrame,
    percentile_cutoff: float,
) -> pd.DataFrame:
    """
    Filter to rows where confidence > percentile_cutoff-th pct of that date's confidences.
    percentile_cutoff=80 → top 20%; =90 → top 10%.
    """
    if percentile_cutoff == 0:
        return date_preds
    conf = (date_preds["proba_ens"] - 0.5).abs()
    thr  = np.percentile(conf, percentile_cutoff)
    return date_preds[conf > thr]


def build_portfolio(
    pred_df:     pd.DataFrame,
    close:       pd.DataFrame,
    log_ret:     pd.DataFrame,
    proba_col:   str,
    conf_pct:    float,   # 0=ALL, 80=TOP20, 90=TOP10
    long_short:  bool = False,
) -> pd.Series:
    """
    Weekly portfolio from predictions.
    Returns daily P&L series.
    """
    pred_df = pred_df.copy()
    pred_df["confidence"] = (pred_df[proba_col] - 0.5).abs()

    # Weekly vol for vol-scaling (from daily log_ret)
    vol_daily = log_ret.rolling(20, min_periods=10).std() * np.sqrt(252)
    vol_w = vol_daily.resample("W-FRI").last()

    dates = sorted(pred_df["date"].unique())
    positions: dict[str, pd.Series] = {}    # asset → weekly position

    pos_df = pd.DataFrame(0.0, index=vol_w.index, columns=ASSETS)

    for dt in dates:
        day_preds = pred_df[pred_df["date"] == dt].copy()
        # Confidence filter
        conf = day_preds["confidence"]
        if conf_pct > 0 and len(conf) > 1:
            thr = np.percentile(conf, conf_pct)
            day_preds = day_preds[conf > thr]

        if day_preds.empty:
            continue

        long_preds = day_preds[day_preds[proba_col] > 0.5].nlargest(N_LONG, proba_col)
        short_preds = pd.DataFrame()
        if long_short:
            short_preds = day_preds[day_preds[proba_col] < 0.5].nsmallest(N_SHORT, proba_col)

        if dt not in pos_df.index:
            continue

        # Zero out then fill
        pos_df.loc[dt] = 0.0

        for _, row in long_preds.iterrows():
            asset = row["asset"]
            if asset in ASSETS and asset in vol_w.columns:
                v = vol_w.loc[dt, asset] if dt in vol_w.index else np.nan
                if not np.isnan(v) and v > 0:
                    pos_df.loc[dt, asset] += VOL_TGT / v

        if long_short:
            for _, row in short_preds.iterrows():
                asset = row["asset"]
                if asset in ASSETS and asset in vol_w.columns:
                    v = vol_w.loc[dt, asset] if dt in vol_w.index else np.nan
                    if not np.isnan(v) and v > 0:
                        pos_df.loc[dt, asset] -= VOL_TGT / v

    # Forward-fill positions (hold until next signal)
    pos_df = pos_df.reindex(vol_w.index).ffill().fillna(0.0)

    # Align to daily close returns
    pos_daily = pos_df.reindex(log_ret.index).ffill().fillna(0.0)
    arith = close.pct_change().fillna(0.0)
    arith.columns = [c.replace("-USD", "") for c in arith.columns
                     if "-USD" in c] or arith.columns.tolist()
    arith = arith[[a for a in ASSETS if a in arith.columns]]

    held = pos_daily.shift(1).fillna(0.0)

    # Align
    common_cols = [a for a in ASSETS if a in held.columns and a in arith.columns]
    gross = (held[common_cols] * arith[common_cols]).sum(axis=1)

    # Cost on Monday rebalances
    is_mon = pd.Series(log_ret.index.dayofweek == 0, index=log_ret.index).astype(float)
    turn   = pos_daily[common_cols].diff().abs()
    costs  = (turn * COST_RT * is_mon.values.reshape(-1, 1)).sum(axis=1)

    return (gross - costs).rename(f"pnl_cf{int(conf_pct)}")


def _sharpe(r: pd.Series, ann: int = 252) -> float:
    r = r.dropna()
    if len(r) < 10 or r.std() == 0:
        return np.nan
    return float(r.mean() / r.std() * np.sqrt(ann))


def _maxdd(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) < 2:
        return np.nan
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


# ══════════════════════════════════════════════════════════════════════════════
# SHAP ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def compute_shap(model: XGBClassifier, X_test: np.ndarray) -> np.ndarray:
    """Returns mean |SHAP| per feature."""
    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X_test)
    if isinstance(sv, list):
        sv = sv[1]
    return np.abs(sv).mean(axis=0)


# ══════════════════════════════════════════════════════════════════════════════
# TSMOM COMPARISON
# ══════════════════════════════════════════════════════════════════════════════

def load_tsmom_daily() -> pd.Series:
    """Load TSMOM v3 C1 daily returns."""
    close, log_ret = tsmom_download()
    pos = build_positions(continuous_signal(log_ret, 28), log_ret, TSMOM_VOL)
    pnl = tsmom_compute_pnl(close, pos)
    pnl.name = "tsmom_c1"
    return pnl


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE
# ══════════════════════════════════════════════════════════════════════════════

def make_figure(
    sharpe_table: dict,   # config → {ALL, TOP20, TOP10}
    shap_vals:    np.ndarray,
    best_pnl:     pd.Series,
    tsmom_pnl:    pd.Series,
    auc_per_window: list[dict],
    out_path:     str,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("XGBoost v2 — Ensemble + Purged WF + Confidence Filter",
                 fontsize=13, fontweight="bold")

    # [0,0] Sharpe by threshold
    ax = axes[0, 0]
    configs   = ["XGBoost", "LightGBM", "Ensemble"]
    thresholds = ["ALL", "TOP20%", "TOP10%"]
    x      = np.arange(len(thresholds))
    width  = 0.25
    colors = ["#3498db", "#e67e22", "#2ecc71"]
    for i, cfg in enumerate(configs):
        vals = [sharpe_table.get(cfg, {}).get(t, np.nan) for t in thresholds]
        bars = ax.bar(x + i * width, vals, width, label=cfg, color=colors[i], alpha=0.8)
    ax.set_xticks(x + width)
    ax.set_xticklabels(thresholds)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axhline(1.2, color="red", linestyle="--", linewidth=0.8, label="Deploy threshold")
    ax.set_title("Sharpe vs Confidence Threshold")
    ax.set_ylabel("Sharpe Ratio")
    ax.legend(fontsize=8)

    # [0,1] SHAP
    ax = axes[0, 1]
    if shap_vals is not None and len(shap_vals) == len(FEAT_NAMES):
        order = np.argsort(shap_vals)[::-1]
        ax.barh([FEAT_NAMES[i] for i in order], [shap_vals[i] for i in order],
                color="#9b59b6", alpha=0.8)
        ax.axvline(0, color="black", linewidth=0.5)
        ax.set_title("SHAP Feature Importance (XGB, W4 test)")
        ax.set_xlabel("Mean |SHAP value|")
    else:
        ax.text(0.5, 0.5, "SHAP N/A", ha="center", va="center",
                transform=ax.transAxes)
        ax.set_title("SHAP Feature Importance")

    # [1,0] OOS equity curve
    ax = axes[1, 0]
    if best_pnl is not None and len(best_pnl.dropna()) > 0:
        common = best_pnl.index.intersection(tsmom_pnl.index)
        if len(common) > 0:
            b = best_pnl.reindex(common).fillna(0)
            t = tsmom_pnl.reindex(common).fillna(0)
            ax.plot((1 + b).cumprod(), label=f"XGB v2 best (SR={_sharpe(b):.2f})",
                    color="#2ecc71", linewidth=1.5)
            ax.plot((1 + t).cumprod(), label=f"TSMOM v3 (SR={_sharpe(t):.2f})",
                    color="#3498db", linewidth=1.5, linestyle="--")
            ax.legend(fontsize=9)
    ax.set_title("OOS Equity Curve — Best Config vs TSMOM v3")
    ax.set_ylabel("Cumulative Return")
    ax.axhline(1, color="black", linewidth=0.5)

    # [1,1] AUC per window
    ax = axes[1, 1]
    if auc_per_window:
        labels = [f"W{i+1}" for i in range(len(auc_per_window))]
        auc_all = [d.get("auc_all", np.nan) for d in auc_per_window]
        auc_20  = [d.get("auc_top20", np.nan) for d in auc_per_window]
        ax.plot(labels, auc_all, "o-", label="AUC (all)",  color="#3498db")
        ax.plot(labels, auc_20,  "s--", label="AUC (top20%)", color="#e67e22")
        ax.axhline(0.5, color="black", linewidth=0.8, linestyle=":")
        ax.axhline(0.55, color="red", linewidth=0.8, linestyle="--", label="0.55 target")
        ax.set_ylim(0.40, 0.70)
        ax.set_title("AUC per Walk-Forward Window")
        ax.set_ylabel("AUC")
        ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()
    print(f"[plot] Saved → {out_path}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 70)
    print("XGBoost v2 — ENSEMBLE + PURGED WF + HIGH-CONFIDENCE FILTER")
    print("=" * 70)

    # 1. Load data
    close, volume, log_ret = load_prices()
    funding = load_funding_weekly()

    # Rename log_ret columns to short keys
    log_ret.columns = [c.replace("-USD", "") for c in log_ret.columns
                       if "-USD" in c] or log_ret.columns.tolist()
    close_short = close.copy()
    close_short.columns = [c.replace("-USD", "") for c in close_short.columns
                           if "-USD" in c] or close_short.columns.tolist()
    volume_short = volume.copy()
    volume_short.columns = [c.replace("-USD", "") for c in volume_short.columns
                            if "-USD" in c] or volume_short.columns.tolist()

    # 2. Features + cross-sectional normalization
    print("\n[2] Building features …")
    feat_panel = build_feature_panel(close_short, volume_short, log_ret, funding)
    feat_panel = cs_zscore_panel(feat_panel)

    # 3. Target
    print("\n[3] Building cross-sectional target …")
    target = build_target(log_ret)

    # 4. Walk-forward
    print("\n[4] Purged walk-forward …")
    pred_df, last_xgb, last_lgbm, last_X_te = run_purged_walkforward(feat_panel, target)

    if pred_df.empty:
        print("\nFATAL: no predictions generated")
        return

    # 5. AUC summary
    print("\n[5] AUC summary …")
    auc_per_window = []
    for i, w in enumerate(WF_WINDOWS):
        mask = (pred_df["date"] >= w["test_start"]) & (pred_df["date"] <= w["test_end"])
        sub  = pred_df[mask]
        if len(sub) < 5:
            auc_per_window.append({"auc_all": np.nan, "auc_top20": np.nan})
            continue
        a_all = roc_auc_score(sub["y_true"], sub["proba_ens"])
        conf  = (sub["proba_ens"] - 0.5).abs()
        m20   = conf >= np.percentile(conf, 80)
        a20   = roc_auc_score(sub.loc[m20, "y_true"], sub.loc[m20, "proba_ens"]) \
                if m20.sum() >= 5 else np.nan
        auc_per_window.append({"auc_all": a_all, "auc_top20": a20})
        print(f"  W{i+1} [{w['test_start']}→{w['test_end']}]:  "
              f"AUC(all)={a_all:.4f}  AUC(top20%)={a20:.4f}")

    auc_overall_all = roc_auc_score(pred_df["y_true"], pred_df["proba_ens"])
    conf_all = (pred_df["proba_ens"] - 0.5).abs()
    m20_all  = conf_all >= np.percentile(conf_all, 80)
    m10_all  = conf_all >= np.percentile(conf_all, 90)
    auc_20_all = roc_auc_score(pred_df.loc[m20_all, "y_true"], pred_df.loc[m20_all, "proba_ens"])
    auc_10_all = roc_auc_score(pred_df.loc[m10_all, "y_true"], pred_df.loc[m10_all, "proba_ens"])
    print(f"\n  Pooled AUC  — all: {auc_overall_all:.4f}  "
          f"top20%: {auc_20_all:.4f}  top10%: {auc_10_all:.4f}")

    # 6. SHAP
    print("\n[6] SHAP analysis …")
    shap_vals = None
    if last_xgb is not None and last_X_te is not None and len(last_X_te) > 0:
        try:
            shap_vals = compute_shap(last_xgb, last_X_te)
            print("  Top 5 features by SHAP:")
            order = np.argsort(shap_vals)[::-1]
            for rank, idx in enumerate(order[:5]):
                marker = " ← HL microstructure" if FEAT_NAMES[idx] == "funding_z" else ""
                print(f"    #{rank+1}  {FEAT_NAMES[idx]:<22} {shap_vals[idx]:.5f}{marker}")
        except Exception as e:
            print(f"  SHAP failed: {e}")

    # 7. Portfolio backtests
    print("\n[7] Portfolio backtests …")
    oos_start = pred_df["date"].min()
    oos_end   = pred_df["date"].max()
    log_ret_oos  = log_ret.loc[str(oos_start.date()):str(oos_end.date())]
    close_oos    = close_short.loc[str(oos_start.date()):str(oos_end.date())]

    sharpe_table: dict[str, dict] = {}
    all_pnls: dict[tuple, pd.Series] = {}

    for proba_col, cfg_name in [
        ("proba_xgb", "XGBoost"),
        ("proba_lgbm", "LightGBM"),
        ("proba_ens",  "Ensemble"),
    ]:
        sharpe_table[cfg_name] = {}
        for cf_label, cf_pct in [("ALL", 0), ("TOP20%", 80), ("TOP10%", 90)]:
            pnl = build_portfolio(pred_df, close_oos, log_ret_oos,
                                  proba_col=proba_col, conf_pct=cf_pct)
            sh  = _sharpe(pnl)
            sharpe_table[cfg_name][cf_label] = sh
            all_pnls[(cfg_name, cf_label)] = pnl

    # Print table
    print(f"\n  {'Config':<14} {'AUC':>6} {'Sh(ALL)':>9} {'Sh(20%)':>9} {'Sh(10%)':>9}")
    print("  " + "─" * 50)
    for cfg in ["XGBoost", "LightGBM", "Ensemble"]:
        auc_s = f"{auc_overall_all:.4f}" if cfg == "Ensemble" else "  N/A"
        sh_all = sharpe_table[cfg].get("ALL",    np.nan)
        sh_20  = sharpe_table[cfg].get("TOP20%", np.nan)
        sh_10  = sharpe_table[cfg].get("TOP10%", np.nan)
        print(f"  {cfg:<14} {auc_s:>6} "
              f"{sh_all:>9.3f} {sh_20:>9.3f} {sh_10:>9.3f}")

    # Best config
    best_sh  = -np.inf
    best_key = None
    for k, pnl in all_pnls.items():
        sh = _sharpe(pnl)
        if not np.isnan(sh) and sh > best_sh:
            best_sh  = sh
            best_key = k

    best_pnl = all_pnls[best_key] if best_key else pd.Series(dtype=float)

    # 8. TSMOM comparison
    print("\n[8] TSMOM v3 comparison …")
    tsmom_pnl = load_tsmom_daily()
    oos_pnl   = best_pnl.reindex(tsmom_pnl.index).fillna(0)
    corr_tsmom = float(oos_pnl.corr(tsmom_pnl.reindex(oos_pnl.index).fillna(0)))
    print(f"  Corr(best XGB v2, TSMOM v3): {corr_tsmom:+.4f}")

    # 9. DSR
    print("\n[9] DSR correction …")
    dsr = deflated_sharpe_ratio(
        best_pnl.dropna().values,
        n_trials=N_TRIALS_DSR,
        periods_per_year=252,
    )
    print(f"  Observed SR     : {dsr['sharpe']:.3f}")
    print(f"  E[max SR] bench : {dsr['sr_benchmark']:.3f}  (n={N_TRIALS_DSR})")
    print(f"  DSR probability : {dsr['dsr']:.3f}  "
          f"({'PASS' if dsr['passed'] else 'FAIL'})")

    # 10. Verdict
    print("\n" + "=" * 70)
    auc_top10 = auc_10_all
    deploy = (best_sh > 1.2 and auc_top10 > 0.55
              and abs(corr_tsmom) < 0.50 and dsr["dsr"] > 0.35)
    promising = (not deploy and (best_sh > 0.8 or auc_top10 > auc_overall_all + 0.01))

    print(f"  Best config          : {best_key}")
    print(f"  Best OOS Sharpe      : {best_sh:.3f}")
    print(f"  AUC (pooled, all)    : {auc_overall_all:.4f}")
    print(f"  AUC (top 10%)        : {auc_top10:.4f}")
    print(f"  Confidence improves  : {auc_top10 > auc_overall_all + 0.005}")
    print(f"  Corr TSMOM v3        : {corr_tsmom:+.4f}")
    print(f"  DSR (n={N_TRIALS_DSR})         : {dsr['dsr']:.3f}")

    print(f"\n  Gate 1 — SR > 1.2          : {'✓' if best_sh > 1.2 else '✗'} ({best_sh:.3f})")
    print(f"  Gate 2 — AUC(top10%) > 0.55: {'✓' if auc_top10 > 0.55 else '✗'} ({auc_top10:.4f})")
    print(f"  Gate 3 — corr < 0.50       : {'✓' if abs(corr_tsmom) < 0.50 else '✗'} ({abs(corr_tsmom):.4f})")
    print(f"  Gate 4 — DSR > 0.35        : {'✓' if dsr['dsr'] > 0.35 else '✗'} ({dsr['dsr']:.3f})")

    if deploy:
        verdict = "DEPLOY as Strategy C"
    elif promising:
        verdict = "PROMISING"
    else:
        verdict = "SKIP"
    print(f"\n  VERDICT: {verdict}")
    print("=" * 70)

    # 11. Figure
    print("\n[10] Generating figure …")
    out_path = str(Path(__file__).parent / "feasibility_v2_results.png")
    make_figure(
        sharpe_table    = sharpe_table,
        shap_vals       = shap_vals,
        best_pnl        = best_pnl,
        tsmom_pnl       = tsmom_pnl,
        auc_per_window  = auc_per_window,
        out_path        = out_path,
    )


if __name__ == "__main__":
    main()
