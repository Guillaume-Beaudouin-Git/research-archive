"""
XGBoost Cross-Asset Microstructure Feasibility
===============================================
Based on Parente & Rizzuti (Soft Computing 2026):
  Train on large altcoin universe, validate on BTC/ETH only.
  Model learns generic crypto price patterns, not asset-specific ones.

Features (SHAP-validated in paper + HL microstructure additions):
  F1: Bollinger Band position
  F2: RSI-14 normalized to [-1, +1]
  F3-F5: EMA crossovers (1/21, 21/50, 50/100)
  F6: DayOfWeek / 6
  F7: Month / 12
  F8: Funding rate z-score (BTC/ETH only; 0 for training altcoins)
  F9: OI change 7d (set to 0 — no historical cache)
  F10: Vol/OI ratio (set to 0 — no historical cache)

Split:
  TRAIN: 18 altcoins 2020-2023 (model never sees BTC/ETH)
  VAL:   18 altcoins 2024      (early-stopping target)
  TEST:  BTC + ETH  2024-2026  (completely unseen during training)

Note on F8/F9/F10: training assets always have 0 for HL microstructure
(by design — altcoins not available in HL cache). The model learns to
rely on F1-F7 from training. F8 (funding_zscore) is non-zero for BTC/ETH
test set; any signal from F8 is thus unvalidated by training.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dsr import deflated_sharpe_ratio

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT    = Path(__file__).resolve().parents[2]
FUNDING_DIR  = REPO_ROOT / "data" / "funding_carry"
OUT_DIR      = Path(__file__).resolve().parent
OUT_PNG      = OUT_DIR / "feasibility_results.png"

# ── Universe ──────────────────────────────────────────────────────────────────
ALTCOIN_TICKERS = [
    "SOL-USD", "AVAX-USD", "LINK-USD", "DOGE-USD", "ADA-USD",
    "DOT-USD", "LTC-USD", "BCH-USD", "MATIC-USD", "ATOM-USD",
    "UNI-USD", "XLM-USD", "ALGO-USD", "VET-USD", "THETA-USD",
    "FIL-USD", "AAVE-USD", "MKR-USD",
]
BTCETH_TICKERS = ["BTC-USD", "ETH-USD"]
ALL_TICKERS    = ALTCOIN_TICKERS + BTCETH_TICKERS

FEATURE_NAMES = [
    "bollinger_pos", "rsi_norm",
    "ema_cross_fast", "ema_cross_mid", "ema_cross_slow",
    "day_of_week", "month",
    "funding_zscore", "oi_chg_7d", "vol_oi_ratio",
]
N_FEATURES = len(FEATURE_NAMES)

# ── Time splits ───────────────────────────────────────────────────────────────
START       = "2020-01-01"
END         = "2026-05-14"
TRAIN_END   = "2023-12-31"
VAL_START   = "2024-01-01"
VAL_END     = "2024-12-31"
TEST_START  = "2024-01-01"

# ── Signal & portfolio ────────────────────────────────────────────────────────
PROB_THRESH = 0.55
VOL_TGT     = 0.15
VOL_WIN     = 20
COST_RT     = 0.0017
GROSS_CAP   = 0.90
N_TRIALS    = 25     # total strategies tested this session (for DSR)

# ── WF windows (only if Sharpe > 1.0) ────────────────────────────────────────
WF_WINDOWS = [
    ("W1", START,        "2021-12-31", "2022-01-01", "2022-12-31"),
    ("W2", START,        "2022-12-31", "2023-01-01", "2023-12-31"),
    ("W3", START,        "2023-12-31", "2024-01-01", "2024-12-31"),
    ("W4", START,        "2024-12-31", "2025-01-01", "2025-12-31"),
]


# ══════════════════════════════════════════════════════════════════════════════
# 1. DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════

def load_prices() -> pd.DataFrame:
    """Download all tickers, return wide close DataFrame (tz-naive)."""
    raw = yf.download(ALL_TICKERS, start=START, end=END,
                      auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        close = raw[["Close"]]
    close.index = pd.to_datetime(close.index).tz_localize(None)
    # Drop tickers with < 365 days of data
    ok = close.notna().sum() >= 365
    dropped = [c for c in close.columns if not ok[c]]
    if dropped:
        print(f"  [data] Dropped (< 365 days): {dropped}")
    return close[close.columns[ok]].sort_index()


def load_funding_zscore() -> dict[str, pd.Series]:
    """
    Compute funding z-score for BTC and ETH from cached CSVs.
    funding_zscore[T] = (mean_7d[T-1] - mean_30d[T-1]) / std_30d[T-1]
    Shifted 1 day — no look-ahead.
    Returns dict: {'BTC': Series, 'ETH': Series}, daily tz-naive.
    """
    result = {}
    for asset in ["BTC", "ETH"]:
        f = FUNDING_DIR / f"{asset}_funding.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f, parse_dates=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_localize(None)
        df = df.set_index("timestamp").sort_index()
        daily = df["funding_rate_1h"].resample("D").mean().shift(1)
        m7    = daily.rolling(7,  min_periods=4).mean()
        m30   = daily.rolling(30, min_periods=15).mean()
        s30   = daily.rolling(30, min_periods=15).std()
        result[asset] = (m7 - m30) / (s30 + 1e-12)
        result[asset].name = f"{asset}_fz"
    return result


# ══════════════════════════════════════════════════════════════════════════════
# 2. FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════════════════════════

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta   = close.diff()
    gain    = delta.clip(lower=0)
    loss    = (-delta).clip(lower=0)
    avg_g   = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_l   = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    return 100 - 100 / (1 + avg_g / (avg_l + 1e-12))


def _ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean()


def compute_features(close: pd.Series,
                     funding_zscore: pd.Series | None = None) -> pd.DataFrame:
    """
    Compute all 10 features for a single asset's daily close series.
    All shifted by 1 (signal at T uses data ≤ T-1).
    """
    c = close.dropna()

    # F1: Bollinger Band position
    ma20   = c.rolling(20, min_periods=10).mean()
    std20  = c.rolling(20, min_periods=10).std()
    bb_pos = (c - ma20) / (2 * std20 + 1e-12)

    # F2: RSI-14 normalized
    rsi_raw  = _rsi(c, 14)
    rsi_norm = (rsi_raw - 50) / 50

    # F3-F5: EMA crossovers
    e1   = _ema(c, 1)    # = close (span=1)
    e21  = _ema(c, 21)
    e50  = _ema(c, 50)
    e100 = _ema(c, 100)
    ema_fast = e1  / (e21  + 1e-12) - 1
    ema_mid  = e21 / (e50  + 1e-12) - 1
    ema_slow = e50 / (e100 + 1e-12) - 1

    # Combine — shift ALL by 1 (no look-ahead)
    feat = pd.DataFrame({
        "bollinger_pos":  bb_pos.shift(1),
        "rsi_norm":       rsi_norm.shift(1),
        "ema_cross_fast": ema_fast.shift(1),
        "ema_cross_mid":  ema_mid.shift(1),
        "ema_cross_slow": ema_slow.shift(1),
        "day_of_week":    (c.index.dayofweek / 6).astype(float),
        "month":          (c.index.month / 12).astype(float),
    }, index=c.index)

    # F8-F10: HL microstructure (0 if not provided)
    if funding_zscore is not None:
        fz = funding_zscore.reindex(c.index).ffill().fillna(0.0)
    else:
        fz = pd.Series(0.0, index=c.index)
    feat["funding_zscore"] = fz
    feat["oi_chg_7d"]      = 0.0   # no historical OI cache
    feat["vol_oi_ratio"]   = 0.0   # no historical OI cache

    return feat[FEATURE_NAMES]


def compute_target(close: pd.Series, horizon: int = 5) -> pd.Series:
    """
    y[T] = 1 if 5-day forward log return > 0 else 0.
    log_ret.rolling(horizon).sum().shift(-horizon) = sum of returns [T+1..T+5].
    """
    log_ret = np.log(close / close.shift(1))
    fwd     = log_ret.rolling(horizon, min_periods=horizon).sum().shift(-horizon)
    return (fwd > 0).astype(int)


# ══════════════════════════════════════════════════════════════════════════════
# 3. DATASET ASSEMBLY
# ══════════════════════════════════════════════════════════════════════════════

def build_dataset(close: pd.DataFrame,
                  funding: dict[str, pd.Series],
                  tickers: list[str],
                  date_start: str,
                  date_end:   str) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex, list]:
    """
    Stack (asset × day) rows into flat X, y arrays.
    Returns (X, y, dates_index, asset_labels).
    """
    Xs, ys, dates_list, asset_list = [], [], [], []

    for ticker in tickers:
        if ticker not in close.columns:
            continue
        asset_name = ticker.replace("-USD", "")
        c = close[ticker].dropna()
        fz = funding.get(asset_name)   # None for altcoins without HL data

        feat   = compute_features(c, funding_zscore=fz)
        target = compute_target(c)

        df = feat.join(target.rename("y"), how="inner").dropna()
        mask = (df.index >= date_start) & (df.index <= date_end)
        df   = df.loc[mask]

        if len(df) < 30:
            continue

        Xs.append(df[FEATURE_NAMES].values)
        ys.append(df["y"].values)
        dates_list.extend(df.index.tolist())
        asset_list.extend([asset_name] * len(df))

    if not Xs:
        return np.empty((0, N_FEATURES)), np.empty(0), pd.DatetimeIndex([]), []

    X   = np.vstack(Xs)
    y   = np.concatenate(ys)
    idx = pd.DatetimeIndex(dates_list)
    return X, y, idx, asset_list


# ══════════════════════════════════════════════════════════════════════════════
# 4. MODEL
# ══════════════════════════════════════════════════════════════════════════════

def train_model(X_tr: np.ndarray, y_tr: np.ndarray,
                X_val: np.ndarray, y_val: np.ndarray) -> XGBClassifier:
    model = XGBClassifier(
        n_estimators          = 200,
        max_depth             = 3,
        learning_rate         = 0.05,
        subsample             = 0.7,
        colsample_bytree      = 0.7,
        min_child_weight      = 20,
        eval_metric           = "auc",
        early_stopping_rounds = 20,
        random_state          = 42,
        verbosity             = 0,
        use_label_encoder     = False,
    )
    model.fit(
        X_tr, y_tr,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )
    return model


def auc_by_split(model: XGBClassifier, X: np.ndarray, y: np.ndarray,
                 label: str) -> float:
    if len(X) < 10 or y.sum() < 2:
        return np.nan
    proba = model.predict_proba(X)[:, 1]
    auc   = roc_auc_score(y, proba)
    acc   = (proba > 0.5).mean() == y.mean()  # crude accuracy proxy
    print(f"    {label:<35} AUC={auc:.4f}  N={len(X):,}  pos_rate={y.mean():.1%}")
    return auc


# ══════════════════════════════════════════════════════════════════════════════
# 5. PORTFOLIO BACKTEST
# ══════════════════════════════════════════════════════════════════════════════

def build_daily_proba(model: XGBClassifier,
                      close: pd.DataFrame,
                      funding: dict[str, pd.Series],
                      tickers: list[str],
                      date_start: str,
                      date_end:   str) -> pd.DataFrame:
    """
    Daily predict_proba for each ticker in the test period.
    Returns DataFrame: date × ticker (column = proba of y=1).
    """
    records = {}
    for ticker in tickers:
        if ticker not in close.columns:
            continue
        asset_name = ticker.replace("-USD", "")
        c  = close[ticker].dropna()
        fz = funding.get(asset_name)
        feat = compute_features(c, funding_zscore=fz)
        mask = (feat.index >= date_start) & (feat.index <= date_end)
        feat = feat.loc[mask].dropna()
        if len(feat) < 5:
            continue
        records[ticker] = pd.Series(
            model.predict_proba(feat.values)[:, 1],
            index=feat.index,
        )
    return pd.DataFrame(records)


def run_portfolio(close: pd.DataFrame,
                  proba_df: pd.DataFrame,
                  date_start: str,
                  date_end:   str) -> dict:
    """
    Weekly signal (Friday close → Monday execute).
    proba > PROB_THRESH → long at vol target.
    Cost 0.17% RT on position changes (Monday only).
    """
    tickers    = proba_df.columns.tolist()
    trade_days = close.loc[date_start:date_end].index

    # Weekly signal: Friday proba → carry through next week
    proba_w  = proba_df.resample("W-FRI").last()
    # Expand to daily (forward-fill from Monday, shifted +3 calendar days = Mon after Fri)
    all_days = pd.date_range(trade_days[0], trade_days[-1], freq="D")
    proba_d  = proba_w.reindex(all_days).shift(3).ffill()
    proba_d  = proba_d.reindex(trade_days).ffill()

    # Binary long signal per ticker
    long_d = (proba_d > PROB_THRESH).astype(float)

    # Vol scalars
    log_ret = np.log(close / close.shift(1))
    rv = (log_ret.rolling(VOL_WIN, min_periods=10).std() * np.sqrt(365)).shift(1)
    rv_d = rv.reindex(all_days).ffill().reindex(trade_days).ffill()

    pnl_parts = {}
    for ticker in tickers:
        if ticker not in long_d.columns or ticker not in rv_d.columns:
            continue
        sc  = (VOL_TGT / rv_d[ticker].replace(0, np.nan)).clip(0.1, 2.0).fillna(1.0)
        sc  = sc * long_d[ticker] * GROSS_CAP
        ret = log_ret[ticker].reindex(trade_days).fillna(0.0)
        pnl_parts[ticker] = sc * ret

    if not pnl_parts:
        empty = pd.Series(0.0, index=trade_days)
        return dict(sharpe=np.nan, maxdd=np.nan, pnl=empty, pf=np.nan, win_rate=np.nan)

    pnl_gross = pd.DataFrame(pnl_parts).sum(axis=1)

    # Costs: when position vector changes (Monday)
    pos_matrix = pd.DataFrame({
        ticker: (VOL_TGT / rv_d[ticker].replace(0, np.nan)
                 ).clip(0.1, 2.0).fillna(1.0) * long_d[ticker] * GROSS_CAP
        for ticker in pnl_parts
    })
    pos_matrix = pos_matrix.reindex(trade_days).fillna(0)
    is_mon     = pd.Series(trade_days.dayofweek == 0, index=trade_days).astype(float)
    cost_per_ticker = pos_matrix.diff().abs().multiply(is_mon, axis=0) * COST_RT
    cost_total = cost_per_ticker.sum(axis=1)

    pnl_net = pnl_gross - cost_total

    ann  = pnl_net.mean() * 365
    vol  = pnl_net.std() * np.sqrt(365)
    sr   = ann / (vol + 1e-12)
    cum  = (1 + pnl_net).cumprod()
    mdd  = float(((cum - cum.cummax()) / cum.cummax()).min())
    pf   = pnl_net[pnl_net > 0].sum() / (abs(pnl_net[pnl_net < 0].sum()) + 1e-12)
    wr   = float((pnl_net > 0).sum() / max(len(pnl_net), 1))
    return dict(sharpe=sr, maxdd=mdd, pnl=pnl_net, cum=cum, pf=pf, win_rate=wr,
                annual_ret=ann)


def tsmom_on_btceth(close: pd.DataFrame,
                    tickers: list[str],
                    date_start: str,
                    date_end: str,
                    lookback: int = 28) -> dict:
    """TSMOM v3 C1 signal (tanh t-stat, long-only) on BTC/ETH test period."""
    trade_days = close.loc[date_start:date_end].index
    log_ret    = np.log(close / close.shift(1))
    pnls       = {}
    for ticker in tickers:
        if ticker not in close.columns:
            continue
        lr   = log_ret[ticker]
        cum  = lr.rolling(lookback, min_periods=14).sum()
        vol  = lr.rolling(lookback, min_periods=14).std() * np.sqrt(lookback)
        sig  = np.tanh(cum / (vol + 1e-12)).clip(lower=0)   # long-only
        rv   = (lr.rolling(VOL_WIN, min_periods=10).std() * np.sqrt(365)).shift(1)
        sc   = (VOL_TGT / rv.replace(0, np.nan)).clip(0.1, 2.0).fillna(1.0)
        pos  = sig.shift(1) * sc   # shift: no look-ahead
        # Lock to Monday
        pos_m  = pos.copy(); pos_m[pos_m.index.dayofweek != 0] = np.nan
        pos_locked = pos_m.reindex(close.index).ffill()
        ret  = lr.reindex(trade_days).fillna(0)
        pos_d = pos_locked.reindex(trade_days).ffill().fillna(0)
        is_mon = (trade_days.dayofweek == 0).astype(float)
        turn   = pd.Series(pos_d.diff().abs().values, index=trade_days)
        costs  = turn * is_mon * COST_RT
        pnls[ticker] = pos_d * ret - costs

    if not pnls:
        return dict(sharpe=np.nan, pnl=pd.Series(dtype=float))

    pnl = pd.DataFrame(pnls).mean(axis=1)
    ann = pnl.mean() * 365
    vol = pnl.std() * np.sqrt(365)
    sr  = ann / (vol + 1e-12)
    return dict(sharpe=sr, pnl=pnl, cum=(1 + pnl).cumprod())


def bh_btceth(close: pd.DataFrame, tickers: list[str],
              date_start: str, date_end: str) -> dict:
    """Equal-weighted buy-and-hold BTC+ETH."""
    trade_days = close.loc[date_start:date_end].index
    log_ret    = np.log(close / close.shift(1))
    parts      = [log_ret[t].reindex(trade_days).fillna(0) for t in tickers
                  if t in close.columns]
    if not parts:
        return dict(sharpe=np.nan, pnl=pd.Series(dtype=float))
    pnl = pd.concat(parts, axis=1).mean(axis=1)
    ann = pnl.mean() * 365
    vol = pnl.std() * np.sqrt(365)
    sr  = ann / (vol + 1e-12)
    cum = (1 + pnl).cumprod()
    return dict(sharpe=sr, pnl=pnl, cum=cum)


# ══════════════════════════════════════════════════════════════════════════════
# 6. SHAP
# ══════════════════════════════════════════════════════════════════════════════

def compute_shap(model: XGBClassifier,
                 X_test: np.ndarray) -> np.ndarray:
    """Return mean |SHAP| per feature (length = N_FEATURES)."""
    try:
        import shap
        expl = shap.TreeExplainer(model)
        sv   = expl.shap_values(X_test)
        return np.abs(sv).mean(axis=0)
    except Exception as e:
        print(f"    [SHAP] failed ({e}), using model feature_importances_ instead")
        return model.feature_importances_


# ══════════════════════════════════════════════════════════════════════════════
# 7. WALK-FORWARD (only if Sharpe > 1.0)
# ══════════════════════════════════════════════════════════════════════════════

def run_walkforward(close: pd.DataFrame,
                    funding: dict[str, pd.Series]) -> list[dict]:
    results = []
    for label, tr_s, tr_e, oos_s, oos_e in WF_WINDOWS:
        X_tr, y_tr, _, _ = build_dataset(
            close, funding, ALTCOIN_TICKERS, tr_s, tr_e)
        X_val, y_val, _, _ = build_dataset(
            close, funding, ALTCOIN_TICKERS, oos_s, oos_e)
        X_test, y_test, _, _ = build_dataset(
            close, funding, BTCETH_TICKERS, oos_s, oos_e)

        if len(X_tr) < 500 or len(X_val) < 50 or len(X_test) < 10:
            results.append(dict(label=label, auc=np.nan, sharpe=np.nan))
            continue

        m   = train_model(X_tr, y_tr, X_val, y_val)
        auc = roc_auc_score(y_test, m.predict_proba(X_test)[:, 1])
        p   = build_daily_proba(m, close, funding, BTCETH_TICKERS, oos_s, oos_e)
        port= run_portfolio(close, p, oos_s, oos_e)
        results.append(dict(label=label, auc=auc, sharpe=port["sharpe"]))
        print(f"    {label}: OOS {oos_s}→{oos_e}  AUC={auc:.4f}  SR={port['sharpe']:+.2f}")

    return results


# ══════════════════════════════════════════════════════════════════════════════
# 8. PLOTS
# ══════════════════════════════════════════════════════════════════════════════

def make_plots(port: dict,
               tsmom: dict,
               bh:   dict,
               shap_vals: np.ndarray,
               proba_df:  pd.DataFrame,
               auc_test:  float,
               auc_train: float,
               auc_val:   float) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("XGBoost Cross-Asset Microstructure — BTC/ETH OOS 2024-2026",
                 fontsize=13, fontweight="bold")

    # Subplot 1: Equity curves
    ax = axes[0, 0]
    if "cum" in port:
        ax.plot(port["cum"].index, port["cum"].values,
                color="steelblue", linewidth=1.8,
                label=f"XGB (SR={port['sharpe']:+.2f})")
    if "cum" in tsmom:
        ax.plot(tsmom["cum"].index, tsmom["cum"].values,
                color="orange", linewidth=1.2, linestyle="--",
                label=f"TSMOM v3 (SR={tsmom['sharpe']:+.2f})")
    if "cum" in bh:
        ax.plot(bh["cum"].index, bh["cum"].values,
                color="gray", linewidth=1.0, linestyle=":",
                label=f"Buy & Hold (SR={bh['sharpe']:+.2f})")
    ax.axhline(1.0, color="black", linewidth=0.6, linestyle="--")
    ax.set_title("Equity Curve — BTC+ETH Test Period (2024-2026)")
    ax.set_ylabel("NAV (start=1)")
    ax.legend(fontsize=8); ax.tick_params(labelsize=8)

    # Subplot 2: SHAP feature importance
    ax = axes[0, 1]
    order   = np.argsort(shap_vals)[::-1]
    labels  = [FEATURE_NAMES[i] for i in order]
    vals    = shap_vals[order]
    hl_mask = ["funding_zscore", "oi_chg_7d", "vol_oi_ratio"]
    colors  = ["#E53935" if FEATURE_NAMES[i] in hl_mask else "#1565C0"
               for i in order]
    bars    = ax.barh(range(len(labels))[::-1], vals, color=colors, alpha=0.8)
    ax.set_yticks(range(len(labels))[::-1])
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_title("SHAP Feature Importance (blue=TA, red=HL microstructure)")
    ax.set_xlabel("Mean |SHAP|"); ax.tick_params(labelsize=8)
    # Rank annotation for HL features
    for rank, fn in enumerate(labels):
        if fn in hl_mask:
            ax.text(vals[rank] + max(vals) * 0.01, len(labels) - 1 - rank,
                    f"#{rank+1}", va="center", fontsize=7, color="darkred")

    # Subplot 3: Predicted probability distribution
    ax = axes[1, 0]
    if not proba_df.empty:
        all_p = proba_df.values.flatten()
        all_p = all_p[~np.isnan(all_p)]
        ax.hist(all_p, bins=40, color="steelblue", alpha=0.7, edgecolor="white")
        ax.axvline(PROB_THRESH, color="red", linewidth=1.2, linestyle="--",
                   label=f"Long threshold ({PROB_THRESH})")
        ax.axvline(0.5, color="black", linewidth=0.8, linestyle=":")
        long_frac = (all_p > PROB_THRESH).mean()
        ax.set_title(f"Predicted Probability Distribution  (long {long_frac:.0%} of days)")
        ax.set_xlabel("P(up next 5d)"); ax.set_ylabel("Count")
        ax.legend(fontsize=8); ax.tick_params(labelsize=8)

    # Subplot 4: AUC by period
    ax = axes[1, 1]
    auc_labels = ["Train\nAltcoins\n2020-2023", "Val\nAltcoins\n2024",
                  "TEST\nBTC+ETH\n2024-2026"]
    auc_vals   = [auc_train, auc_val, auc_test]
    bar_colors = ["#90CAF9", "#FFCC80",
                  "#4CAF50" if auc_test > 0.55 else "#FF7043"]
    bars = ax.bar(auc_labels, auc_vals, color=bar_colors, alpha=0.85, width=0.4)
    ax.axhline(0.55, color="green", linewidth=1.2, linestyle="--",
               label="AUC=0.55 (DEPLOY)")
    ax.axhline(0.52, color="orange", linewidth=1.0, linestyle=":",
               label="AUC=0.52 (PROMISING)")
    ax.axhline(0.50, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_ylim(0.45, 0.70)
    for bar, v in zip(bars, auc_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.003,
                f"{v:.4f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_title("AUC by Split")
    ax.set_ylabel("ROC-AUC"); ax.legend(fontsize=8); ax.tick_params(labelsize=8)

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  [plot] Saved → {OUT_PNG.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 9. MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 65)
    print("XGB CROSS-ASSET MICROSTRUCTURE FEASIBILITY")
    print("Train: 18 altcoins 2020-2023  |  Test: BTC+ETH 2024-2026")
    print("=" * 65)

    # 1. Data
    print("\n[1] Loading price data ...")
    close = load_prices()
    alt_available  = [t for t in ALTCOIN_TICKERS if t in close.columns]
    btce_available = [t for t in BTCETH_TICKERS  if t in close.columns]
    print(f"    Altcoins: {len(alt_available)}/18   BTC/ETH: {len(btce_available)}/2")

    print("\n[2] Loading HL funding rate z-scores (BTC, ETH) ...")
    funding = load_funding_zscore()
    for asset, s in funding.items():
        print(f"    {asset}: {s.notna().sum()} daily obs")

    # 2. Build datasets
    print("\n[3] Building feature datasets ...")
    X_tr, y_tr, _, _ = build_dataset(
        close, funding, alt_available, START, TRAIN_END)
    X_val, y_val, _, _ = build_dataset(
        close, funding, alt_available, VAL_START, VAL_END)
    X_test, y_test, idx_test, assets_test = build_dataset(
        close, funding, btce_available, TEST_START, END)
    print(f"    Train X: {X_tr.shape}   Val X: {X_val.shape}   Test X: {X_test.shape}")
    print(f"    Train y pos rate: {y_tr.mean():.1%}  "
          f"Val: {y_val.mean():.1%}  Test: {y_test.mean():.1%}")

    if len(X_tr) < 200:
        print("  ABORT: insufficient training data"); return

    # 3. Train
    print("\n[4] Training XGBoost (altcoins train → altcoins val early-stop) ...")
    model = train_model(X_tr, y_tr, X_val, y_val)
    best_iter = model.best_iteration
    print(f"    Best iteration: {best_iter}")

    # 4. AUC evaluation
    print("\n[5] AUC evaluation:")
    auc_tr   = auc_by_split(model, X_tr,   y_tr,   "Train  (altcoins 2020-2023)")
    auc_val  = auc_by_split(model, X_val,  y_val,  "Val    (altcoins 2024)")
    auc_test = auc_by_split(model, X_test, y_test, "TEST   (BTC+ETH 2024-2026) ←")

    # 5. SHAP
    print("\n[6] Computing SHAP feature importance ...")
    shap_vals = compute_shap(model, X_test[:min(500, len(X_test))])
    order = np.argsort(shap_vals)[::-1]
    print("    Top 10 features by SHAP:")
    hl_feats = {"funding_zscore", "oi_chg_7d", "vol_oi_ratio"}
    hl_ranks = []
    for rank, idx_f in enumerate(order):
        fn = FEATURE_NAMES[idx_f]
        tag = "  ← HL microstructure" if fn in hl_feats else ""
        print(f"      #{rank+1:>2}  {fn:<22}  importance={shap_vals[idx_f]:.5f}{tag}")
        if fn in hl_feats:
            hl_ranks.append(rank + 1)
    if hl_ranks:
        avg_hl_rank = np.mean(hl_ranks)
        print(f"    HL microstructure average rank: #{avg_hl_rank:.1f} "
              f"({'adds info' if avg_hl_rank <= 5 else 'marginal'})")

    # 6. Portfolio backtest
    print("\n[7] Building portfolio signal (BTC+ETH test period) ...")
    proba_df = build_daily_proba(
        model, close, funding, btce_available, TEST_START, END)
    port  = run_portfolio(close, proba_df, TEST_START, END)
    tsmom = tsmom_on_btceth(close, btce_available, TEST_START, END)
    bh    = bh_btceth(close, btce_available, TEST_START, END)

    # 7. Correlation with TSMOM
    if "pnl" in port and "pnl" in tsmom:
        idx_c  = port["pnl"].index.intersection(tsmom["pnl"].index)
        if len(idx_c) > 10:
            corr_ts = float(port["pnl"].loc[idx_c].corr(tsmom["pnl"].loc[idx_c]))
        else:
            corr_ts = np.nan
    else:
        corr_ts = np.nan

    # 8. DSR
    print("\n[8] DSR correction ...")
    dsr_result = deflated_sharpe_ratio(
        returns          = port["pnl"].dropna().values,
        n_trials         = N_TRIALS,
        periods_per_year = 365,
    )
    dsr_prob   = dsr_result.get("dsr", np.nan)
    dsr_sr_adj = port["sharpe"] * dsr_prob if not np.isnan(dsr_prob) else np.nan
    print(f"    Observed SR:   {port['sharpe']:+.3f}")
    print(f"    DSR prob:       {dsr_prob:.3f}  (n_trials={N_TRIALS})")
    print(f"    DSR-adj SR:    {dsr_sr_adj:+.3f}" if not np.isnan(dsr_sr_adj) else "    DSR-adj SR:    N/A")

    # 9. Print summary
    def _f(v, fmt="+.2f") -> str:
        return format(v, fmt) if not np.isnan(v or np.nan) else "  N/A"

    print(f"""
  Training set (18 altcoins 2020-2023):
    AUC: {auc_tr:.4f}

  Validation set (18 altcoins 2024):
    AUC: {auc_val:.4f}  ← early-stopping target

  TEST set BTC+ETH (2024-2026, never seen during training):
    AUC:                     {auc_test:.4f}
    Portfolio Sharpe:        {_f(port['sharpe'])}
    MaxDD:                   {port['maxdd']*100:+.1f}%
    Profit Factor:           {_f(port['pf'], '.2f')}
    Win Rate:                {port['win_rate']*100:+.1f}%
    Corr with TSMOM v3:      {_f(corr_ts, '+.3f')}
    DSR prob (n={N_TRIALS}):       {dsr_prob:.3f}
    DSR-adjusted Sharpe:     {_f(dsr_sr_adj)}

  Benchmark (same period):
    TSMOM v3 (BTC+ETH):     {_f(tsmom['sharpe'])}
    Buy & Hold (BTC+ETH):   {_f(bh['sharpe'])}""")

    # 10. Walk-forward (if Sharpe > 1.0)
    wf_results = []
    port_sr = port["sharpe"] or -999
    if not np.isnan(port_sr) and port_sr > 1.0:
        print(f"\n[9] Walk-forward (Sharpe {port_sr:+.2f} > 1.0) ...")
        wf_results = run_walkforward(close, funding)
        print(f"\n  {'Win':<6} {'OOS period':<22} {'AUC':>6} {'SR':>8}")
        for w in wf_results:
            print(f"  {w['label']:<6} "
                  f"{_f(w.get('auc', np.nan), '.4f'):>6}  "
                  f"{_f(w.get('sharpe', np.nan)):>8}")
        n_pos = sum(1 for w in wf_results
                    if not np.isnan(w.get("sharpe", np.nan) or np.nan)
                    and w["sharpe"] > 0)
        print(f"\n  WF: {n_pos}/4 windows positive Sharpe")
    else:
        print(f"\n  [9] WF skipped (Sharpe {_f(port_sr)} ≤ 1.0)")

    # 11. Verdict
    print()
    deploy   = (auc_test > 0.55 and (port["sharpe"] or 0) > 1.0
                and (not np.isnan(corr_ts)) and corr_ts < 0.40
                and dsr_prob > 0.40)
    promising = (auc_test > 0.52 and (port["sharpe"] or 0) > 0.5)

    if deploy:
        verdict = "DEPLOY"
        note = "Proceed to live test as Strategy C."
    elif promising:
        verdict = "PROMISING"
        note = (f"AUC {auc_test:.4f} / SR {_f(port['sharpe'])} marginal. "
                "Test with lower threshold or longer OOS window.")
    else:
        verdict = "SKIP"
        note = (f"AUC {auc_test:.4f} ≤ 0.52 or SR {_f(port['sharpe'])} ≤ 0.5. "
                "Model generalizes poorly to BTC/ETH.")

    print(f"  VERDICT: {verdict}")
    print(f"  {note}")

    # 12. Plots
    print("\n[10] Generating plots ...")
    make_plots(port, tsmom, bh, shap_vals, proba_df, auc_test, auc_tr, auc_val)

    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
