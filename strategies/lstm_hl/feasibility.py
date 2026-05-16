"""
strategies/lstm_hl/feasibility.py — LSTM on 4h Hyperliquid Data

Hypothesis (Parente & Rizzuti 2026): LSTM trained on 4h candle features
predicts next-candle direction. Key difference: we add HL-native funding rate
as an extra feature beyond pure TA (tests whether exchange-native data adds edge).

Model architecture (Parente & Rizzuti SHAP-validated):
  13 features × 5 timesteps → LSTM(64) → LSTM(32) → Dense(16) → Dense(3)

Features (per 4h candle):
  bollinger_pos   (close - MA20) / (2·std20)
  rsi_norm        (RSI14 - 50) / 50
  ema_cross_1_21  EMA1 / EMA21 - 1
  ema_cross_21_50 EMA21 / EMA50 - 1
  vol_z           (volume - vol_MA20) / vol_std20
  ret_1bar        log(close / close.shift(1))
  ret_5bar        log(close / close.shift(5))
  ret_20bar       log(close / close.shift(20))
  hour_sin/cos    cyclical encoding of hour
  dow_sin/cos     cyclical encoding of day of week
  funding_rate    8h funding rate from HL API (shifted 1 bar)
  [oi_chg skipped: HL REST API has no historical OI endpoint]

Train:  BTC 2022-01 → 2024-06
Val:    BTC 2024-07 → 2024-12  (early stopping)
Test:   BTC 2025-01 → 2026-05  (OOS, never seen)
Generalization: ETH OOS with BTC-trained model (AUC>0.53 → generic pattern)

Execution: long on BUY, flat on HOLD, never short.
FW=2 candles, hold 8h, cost 0.17% RT.
"""

import os, sys, time, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import requests
from datetime import datetime, timezone
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score, confusion_matrix, ConfusionMatrixDisplay
)

warnings.filterwarnings("ignore")
np.random.seed(42)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
HL_URL   = "https://api.hyperliquid.xyz/info"
INTERVAL = "4h"
COINS    = ["BTC", "ETH"]

START_DT  = datetime(2022, 1, 1, tzinfo=timezone.utc)
END_DT    = datetime(2026, 5, 14, tzinfo=timezone.utc)
START_MS  = int(START_DT.timestamp() * 1000)
END_MS    = int(END_DT.timestamp()   * 1000)
CHUNK_MS  = int(180 * 24 * 3600 * 1000)

TRAIN_END = "2024-07-01"
VAL_END   = "2025-01-01"
TEST_END  = "2026-05-14"

BW       = 5          # backward window (candles)
FW       = 2          # forward window (candles) — hold period
ALPHA_PCT = 85        # percentile for BUY/SELL label threshold
COST_RT  = 0.0017     # 0.17% round-trip
CLASSES  = {0: "SELL", 1: "HOLD", 2: "BUY"}
BUY_CLS  = 2
SELL_CLS = 0

OUT_DIR  = os.path.dirname(os.path.abspath(__file__))

# PyTorch import (optional — sklearn MLPClassifier fallback)
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    TORCH = True
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[LSTM] PyTorch {torch.__version__} available — device: {DEVICE}")
except ImportError:
    TORCH = False
    print("[LSTM] PyTorch not found — using sklearn MLPClassifier fallback")


# ─── DATA FETCHING ────────────────────────────────────────────────────────────

def _hl_post(payload: dict, timeout: int = 30):
    for attempt in range(3):
        try:
            r = requests.post(HL_URL, json=payload, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def fetch_hl_candles(coin: str) -> pd.DataFrame:
    all_rows: list = []
    t = START_MS
    while t < END_MS:
        chunk_end = min(t + CHUNK_MS, END_MS)
        dt_s = datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        print(f"    {coin} candles [{dt_s}] … ", end="", flush=True)
        rows = _hl_post({
            "type": "candleSnapshot",
            "req": {"coin": coin, "interval": INTERVAL,
                    "startTime": t, "endTime": chunk_end}
        })
        print(len(rows))
        all_rows.extend(rows)
        if not rows:
            t = chunk_end + 1
        else:
            t = int(rows[-1]["T"]) + 1
        time.sleep(0.25)

    if not all_rows:
        return pd.DataFrame()
    df = pd.DataFrame(all_rows)
    df["time"] = pd.to_datetime(df["t"].astype(np.int64), unit="ms", utc=True)
    for col in ["o","c","h","l","v"]:
        df[col] = df[col].astype(float)
    return (df.drop_duplicates(subset=["time"])
              .set_index("time")[["o","c","h","l","v"]]
              .sort_index())


def fetch_funding_history(coin: str) -> pd.Series:
    """
    Pull 8h funding rate history from Hyperliquid.
    Returns a Series indexed by UTC datetime, aligned to 4h candle times.
    Rate is shifted 1 period to prevent look-ahead.
    """
    all_rows: list = []
    t = START_MS
    while t < END_MS:
        chunk_end = min(t + CHUNK_MS, END_MS)
        try:
            rows = _hl_post({
                "type": "fundingHistory",
                "coin": coin,
                "startTime": t,
                "endTime": chunk_end
            })
        except Exception as e:
            print(f"    Funding fetch error: {e}")
            rows = []
        all_rows.extend(rows)
        if not rows:
            t = chunk_end + 1
        else:
            t = int(rows[-1]["time"]) + 1
        time.sleep(0.20)

    if not all_rows:
        return pd.Series(dtype=float, name="funding_rate")

    df_f = pd.DataFrame(all_rows)
    df_f["time"] = pd.to_datetime(df_f["time"].astype(np.int64), unit="ms", utc=True)
    df_f["rate"] = df_f["fundingRate"].astype(float)
    series = df_f.set_index("time")["rate"].sort_index()
    series = series[~series.index.duplicated(keep="last")]
    print(f"    Funding history: {len(series)} records, "
          f"{series.index[0].date()} → {series.index[-1].date()}")
    return series


# ─── FEATURE ENGINEERING ─────────────────────────────────────────────────────

def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def build_features(df: pd.DataFrame, funding_series: pd.Series | None) -> pd.DataFrame:
    c = df["c"]; v = df["v"]

    # TA features
    ma20   = c.rolling(20).mean()
    std20  = c.rolling(20).std()
    boll   = (c - ma20) / (2 * std20.replace(0, np.nan))

    rsi14  = compute_rsi(c, 14)
    rsi_n  = (rsi14 - 50) / 50

    ema1   = c.ewm(span=1,  adjust=False).mean()
    ema21  = c.ewm(span=21, adjust=False).mean()
    ema50  = c.ewm(span=50, adjust=False).mean()
    ec121  = ema1  / ema21.replace(0, np.nan) - 1
    ec2150 = ema21 / ema50.replace(0, np.nan) - 1

    vol_ma  = v.rolling(20).mean()
    vol_std = v.rolling(20).std()
    vol_z   = (v - vol_ma) / vol_std.replace(0, np.nan)

    ret1  = np.log(c / c.shift(1))
    ret5  = np.log(c / c.shift(5))
    ret20 = np.log(c / c.shift(20))

    # Cyclical time encoding
    hour    = df.index.hour.astype(float)
    dow     = df.index.dayofweek.astype(float)
    hr_sin  = np.sin(2 * np.pi * hour / 24)
    hr_cos  = np.cos(2 * np.pi * hour / 24)
    dw_sin  = np.sin(2 * np.pi * dow  / 7)
    dw_cos  = np.cos(2 * np.pi * dow  / 7)

    feat = pd.DataFrame({
        "bollinger_pos":   boll,
        "rsi_norm":        rsi_n,
        "ema_cross_1_21":  ec121,
        "ema_cross_21_50": ec2150,
        "vol_z":           vol_z,
        "ret_1bar":        ret1,
        "ret_5bar":        ret5,
        "ret_20bar":       ret20,
        "hour_sin":        pd.Series(hr_sin, index=df.index),
        "hour_cos":        pd.Series(hr_cos, index=df.index),
        "dow_sin":         pd.Series(dw_sin, index=df.index),
        "dow_cos":         pd.Series(dw_cos, index=df.index),
    }, index=df.index)

    # HL funding rate (8h → forward-fill to 4h, shift 1 to avoid look-ahead)
    if funding_series is not None and len(funding_series) > 0:
        fund_4h = funding_series.reindex(df.index, method="ffill").shift(1)
        feat["funding_rate"] = fund_4h
    else:
        print("    [WARN] No funding data — feature set is 12 (not 13)")

    return feat.dropna()


def compute_targets(close: pd.Series, fw: int = FW) -> pd.Series:
    """log return FW candles ahead; NaN at tail."""
    return np.log(close.shift(-fw) / close)


def make_labels(fwd_ret: pd.Series, alpha: float) -> pd.Series:
    labels = pd.Series(1, index=fwd_ret.index, dtype=int)  # HOLD
    labels[fwd_ret >  alpha] = BUY_CLS
    labels[fwd_ret < -alpha] = SELL_CLS
    return labels


# ─── SEQUENCE CONSTRUCTION ───────────────────────────────────────────────────

def make_sequences(feat: np.ndarray, labels: np.ndarray,
                   bw: int = BW) -> tuple[np.ndarray, np.ndarray]:
    """
    For each index i (bw-1 ≤ i < n): X[i] = feat[i-bw+1:i+1], y[i] = labels[i].
    Labels are the class at candle i (whose forward return uses i+1..i+fw).
    We align labels to the LAST candle in each window.
    """
    n = len(feat)
    X, y = [], []
    for i in range(bw - 1, n):
        X.append(feat[i - bw + 1: i + 1])
        y.append(labels[i])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


# ─── PYTORCH MODEL ────────────────────────────────────────────────────────────

if TORCH:
    class LSTMClassifier(nn.Module):
        def __init__(self, n_feat: int, n_class: int = 3):
            super().__init__()
            self.lstm1 = nn.LSTM(n_feat, 64, batch_first=True)
            self.lstm2 = nn.LSTM(64,     32, batch_first=True)
            self.drop  = nn.Dropout(0.30)
            self.fc1   = nn.Linear(32, 16)
            self.relu  = nn.ReLU()
            self.fc2   = nn.Linear(16, n_class)

        def forward(self, x):
            out1, _    = self.lstm1(x)         # (batch, seq, 64)
            _, (hn, _) = self.lstm2(out1)      # hn: (1, batch, 32)
            h = self.drop(hn[-1])              # (batch, 32)
            return self.fc2(self.relu(self.fc1(h)))

    def train_lstm(X_tr, y_tr, X_val, y_val, n_feat: int,
                   epochs: int = 120, patience: int = 12,
                   lr: float = 1e-3, batch: int = 256):
        model = LSTMClassifier(n_feat).to(DEVICE)

        # Class weights to handle HOLD-dominance
        counts = np.bincount(y_tr, minlength=3).astype(float)
        counts = np.where(counts == 0, 1, counts)
        w = torch.FloatTensor(1.0 / counts / (1.0 / counts).sum()).to(DEVICE)
        crit = nn.CrossEntropyLoss(weight=w)
        opt  = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
        sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, patience=5, factor=0.5)

        Xt = torch.FloatTensor(X_tr).to(DEVICE)
        yt = torch.LongTensor(y_tr).to(DEVICE)
        Xv = torch.FloatTensor(X_val).to(DEVICE)
        yv = torch.LongTensor(y_val).to(DEVICE)

        ds     = TensorDataset(Xt, yt)
        loader = DataLoader(ds, batch_size=batch, shuffle=True)

        best_val   = float("inf")
        best_state = None
        pat_count  = 0

        for epoch in range(1, epochs + 1):
            model.train()
            for xb, yb in loader:
                opt.zero_grad()
                loss = crit(model(xb), yb)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()

            model.eval()
            with torch.no_grad():
                val_loss = crit(model(Xv), yv).item()
            sched.step(val_loss)

            if epoch % 10 == 0:
                print(f"    epoch {epoch:3d}  val_loss={val_loss:.4f}")

            if val_loss < best_val:
                best_val   = val_loss
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
                pat_count  = 0
            else:
                pat_count += 1
                if pat_count >= patience:
                    print(f"    Early stop at epoch {epoch}")
                    break

        model.load_state_dict(best_state)
        return model

    def predict_proba_torch(model, X: np.ndarray) -> np.ndarray:
        model.eval()
        with torch.no_grad():
            logits = model(torch.FloatTensor(X).to(DEVICE))
            proba  = torch.softmax(logits, dim=1).cpu().numpy()
        return proba

else:
    def train_lstm(X_tr, y_tr, X_val, y_val, n_feat, **kw):
        """sklearn MLPClassifier fallback (flattened sequences)."""
        from sklearn.neural_network import MLPClassifier
        from sklearn.utils.class_weight import compute_class_weight
        Xf_tr  = X_tr.reshape(len(X_tr), -1)
        Xf_val = X_val.reshape(len(X_val), -1)
        cw = compute_class_weight("balanced", classes=np.array([0,1,2]), y=y_tr)
        model = MLPClassifier(
            hidden_layer_sizes=(128, 64, 32, 16),
            activation="relu", max_iter=300,
            early_stopping=True, validation_fraction=0.1,
            n_iter_no_change=15, random_state=42
        )
        model.fit(Xf_tr, y_tr)
        return model

    def predict_proba_torch(model, X: np.ndarray) -> np.ndarray:
        Xf = X.reshape(len(X), -1)
        return model.predict_proba(Xf)


# ─── PERMUTATION FEATURE IMPORTANCE ─────────────────────────────────────────

def permutation_importance(predict_fn, X: np.ndarray, y: np.ndarray,
                            n_repeats: int = 8) -> np.ndarray:
    """Model-agnostic permutation importance on BUY-class AUC."""
    baseline = roc_auc_score((y == BUY_CLS).astype(int),
                              predict_fn(X)[:, BUY_CLS])
    importances = np.zeros(X.shape[-1])
    rng = np.random.default_rng(0)
    for f in range(X.shape[-1]):
        scores = []
        for _ in range(n_repeats):
            Xp = X.copy()
            rng.shuffle(Xp[:, :, f])
            scores.append(roc_auc_score((y == BUY_CLS).astype(int),
                                         predict_fn(Xp)[:, BUY_CLS]))
        importances[f] = baseline - np.mean(scores)
    return importances


# ─── EQUITY CURVE ─────────────────────────────────────────────────────────────

def simulate_long_only(close: pd.Series,
                       pred_labels: pd.Series,
                       fw: int = FW,
                       cost_rt: float = COST_RT
                       ) -> tuple[pd.Series, float, pd.Series]:
    """
    BUY signal at T → hold from T+1 to T+fw (inclusive).
    Entry cost charged once per new position entry.
    Returns (cum_log_ret, annualised_sharpe, bar_ret).
    """
    n   = len(close)
    ret = np.log(close / close.shift(1)).fillna(0).values
    pos = np.zeros(n)

    for i in range(n - fw):
        if pred_labels.iat[i] == BUY_CLS:
            pos[i + 1: i + fw + 1] = np.maximum(pos[i + 1: i + fw + 1], 1.0)

    pos    = pd.Series(pos, index=close.index)
    entry  = (pos.diff() > 0).astype(float)
    bar_r  = pd.Series(pos.values * ret, index=close.index) - entry * cost_rt
    cum_r  = bar_r.cumsum()
    sharpe = (
        bar_r.mean() / bar_r.std() * np.sqrt(365.25 * 6)
        if bar_r.std() > 0 else 0.0
    )
    return cum_r, sharpe, bar_r


# ─── TSMOM v3 WEEKLY RETURNS ──────────────────────────────────────────────────

def compute_tsmom_weekly(df_4h: pd.DataFrame) -> pd.Series:
    daily_c = df_4h["c"].resample("D").last().dropna()
    lr      = np.log(daily_c / daily_c.shift(1)).dropna()
    cr28    = lr.rolling(28).sum()
    v28     = lr.rolling(28).std() * np.sqrt(28)
    sig     = np.tanh(cr28 / v28.replace(0, np.nan)).clip(lower=0)
    strat_r = sig.shift(1) * lr
    return strat_r.resample("W-MON").sum()


# ─── FIGURES ─────────────────────────────────────────────────────────────────

def make_figure(
    df_test, cum_lstm, sharpe_lstm, cum_bnh,
    y_test, y_pred, proba_test,
    feat_names, importances,
    cum_eth, sharpe_eth,
    tsmom_corr,
    n_trades_yr, cost_drag_yr
) -> None:

    fig = plt.figure(figsize=(20, 18))
    fig.suptitle(
        "LSTM 4h HL Data — Strategy C Feasibility\n"
        "Parente & Rizzuti (2026) methodology + HL funding rate feature",
        fontsize=14, fontweight="bold", y=0.998
    )
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.50, wspace=0.38)

    # ── Panel 1: Confusion matrix (OOS BTC) ──────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    cm   = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])
    disp = ConfusionMatrixDisplay(cm, display_labels=["SELL","HOLD","BUY"])
    disp.plot(ax=ax1, colorbar=False, cmap="Blues")
    ax1.set_title("Confusion Matrix (BTC OOS 2025-26)", fontsize=10)

    # ── Panel 2: AUC curve for BUY class ─────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    from sklearn.metrics import roc_curve
    fpr, tpr, _ = roc_curve((y_test == BUY_CLS).astype(int), proba_test[:, BUY_CLS])
    auc_buy     = roc_auc_score((y_test == BUY_CLS).astype(int), proba_test[:, BUY_CLS])
    ax2.plot(fpr, tpr, color="#2166ac", lw=2, label=f"BUY AUC = {auc_buy:.3f}")
    ax2.plot([0,1],[0,1], "k--", lw=1)
    ax2.set_xlabel("FPR"); ax2.set_ylabel("TPR")
    ax2.set_title("ROC — BUY class (OOS BTC 2025-26)", fontsize=10)
    ax2.legend(fontsize=10); ax2.grid(alpha=0.3)

    # ── Panel 3: Feature importance ──────────────────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    if importances is not None and len(importances) == len(feat_names):
        idx = np.argsort(importances)
        ax3.barh([feat_names[i] for i in idx],
                 [importances[i] for i in idx],
                 color=["#2166ac" if v >= 0 else "#d73027"
                        for v in [importances[i] for i in idx]])
        ax3.axvline(0, color="gray", lw=0.5)
        ax3.set_title("Permutation Importance (BUY-AUC drop)", fontsize=10)
        ax3.set_xlabel("AUC drop when feature is shuffled")
    else:
        ax3.text(0.5, 0.5, "Importance N/A", ha="center", va="center")
        ax3.set_title("Feature Importance")

    # ── Panel 4: BTC equity curve OOS ────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, :2])
    ax4.plot(cum_lstm.index, cum_lstm.values * 100,
             color="#2166ac", lw=2,
             label=f"LSTM long-only BTC  Sharpe={sharpe_lstm:.2f}  "
                   f"corr(TSMOM)={tsmom_corr:.2f}  "
                   f"{n_trades_yr:.0f}trades/yr  costdrag={cost_drag_yr*100:.2f}%/yr")
    ax4.plot(cum_bnh.index, cum_bnh.values * 100,
             color="gray", lw=1.5, ls="--", label="Buy & Hold BTC")
    ax4.axhline(0, color="black", lw=0.5)
    ax4.set_title("Equity Curve — LSTM long-only vs Buy & Hold (OOS 2025-26)", fontsize=11)
    ax4.set_ylabel("Cumulative log return (%)"); ax4.set_xlabel("Date")
    ax4.legend(fontsize=8); ax4.grid(alpha=0.3)

    # ── Panel 5: ETH generalization ──────────────────────────────────────────
    ax5 = fig.add_subplot(gs[1, 2])
    if cum_eth is not None:
        ax5.plot(cum_eth.index, cum_eth.values * 100,
                 color="#4dac26", lw=2, label=f"LSTM (BTC-trained) on ETH  Sharpe={sharpe_eth:.2f}")
        ax5.axhline(0, color="black", lw=0.5)
        ax5.set_title("ETH Generalization (BTC-trained model)", fontsize=10)
        ax5.set_ylabel("Cum log return (%)"); ax5.set_xlabel("Date")
        ax5.legend(fontsize=9); ax5.grid(alpha=0.3)
    else:
        ax5.text(0.5, 0.5, "ETH data unavailable", ha="center", va="center")
        ax5.set_title("ETH Generalization")

    # ── Panel 6: Class distribution ──────────────────────────────────────────
    ax6 = fig.add_subplot(gs[2, 0])
    cls_counts = pd.Series(y_test).value_counts().sort_index()
    bars = ax6.bar([CLASSES[k] for k in cls_counts.index],
                   cls_counts.values, color=["#d73027","#f7f7f7","#2166ac"],
                   edgecolor="black")
    ax6.set_title("OOS Test Label Distribution (BTC)", fontsize=10)
    ax6.set_ylabel("Count")
    for bar, cnt in zip(bars, cls_counts.values):
        ax6.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                 str(cnt), ha="center", va="bottom", fontsize=9)

    # ── Panel 7: Training loss (placeholder or actual) ───────────────────────
    ax7 = fig.add_subplot(gs[2, 1:])
    ax7.text(0.5, 0.5,
             f"BTC OOS 2025-26 summary\n\n"
             f"BUY-class AUC : {roc_auc_score((y_test==BUY_CLS).astype(int), proba_test[:,BUY_CLS]):.3f}\n"
             f"Sharpe LSTM   : {sharpe_lstm:+.3f}\n"
             f"Sharpe ETH    : {sharpe_eth:+.3f}\n"
             f"corr(TSMOM)   : {tsmom_corr:+.3f}\n"
             f"Trades/year   : {n_trades_yr:.0f}\n"
             f"Cost drag/yr  : {cost_drag_yr*100:.2f}%",
             ha="center", va="center", fontsize=13,
             bbox=dict(boxstyle="round,pad=0.8", facecolor="#f0f4ff", edgecolor="#2166ac"))
    ax7.axis("off")
    ax7.set_title("Summary Statistics", fontsize=10)

    out_path = os.path.join(OUT_DIR, "feasibility_results.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  Figure → {out_path}")
    plt.close()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("LSTM 4h HL DATA — Strategy C Feasibility Study")
    print(f"Train: 2022-01 → {TRAIN_END} | Val: → {VAL_END} | Test: → {TEST_END}")
    print(f"Model: {'PyTorch LSTM' if TORCH else 'sklearn MLP (fallback)'}")
    print("=" * 70)

    # ── 1. Fetch data ─────────────────────────────────────────────────────────
    print("\n[1/7] Fetching 4h OHLCV from Hyperliquid…")
    raw: dict = {}
    for coin in COINS:
        print(f"\n  {coin}:")
        try:
            df = fetch_hl_candles(coin)
            if df.empty or len(df) < 500:
                raise ValueError(f"only {len(df)} candles")
            raw[coin] = df
            print(f"  → {len(df)} candles  "
                  f"{df.index[0].date()} → {df.index[-1].date()}")
        except Exception as e:
            print(f"  FAILED: {e}")

    if "BTC" not in raw:
        print("ERROR: BTC data unavailable. Exiting."); return

    # ── 2. Funding rates ──────────────────────────────────────────────────────
    print("\n[2/7] Fetching funding rate history from Hyperliquid…")
    funding: dict = {}
    for coin in ["BTC", "ETH"]:
        if coin not in raw:
            continue
        try:
            fs = fetch_funding_history(coin)
            if len(fs) > 0:
                funding[coin] = fs
        except Exception as e:
            print(f"  Funding fetch failed for {coin}: {e}")

    # ── 3. Feature engineering ────────────────────────────────────────────────
    print("\n[3/7] Building features (13 per candle)…")
    feats: dict = {}
    for coin in COINS:
        if coin not in raw:
            continue
        fund_s = funding.get(coin)
        f = build_features(raw[coin], fund_s)
        # Align feature index with price close
        feats[coin] = f
        print(f"  {coin}: {len(f)} bars, {f.shape[1]} features: {list(f.columns)}")

    feat_names = list(feats["BTC"].columns)
    n_feat     = len(feat_names)

    # ── 4. Targets + sequences (BTC) ─────────────────────────────────────────
    print("\n[4/7] Computing targets and sequences (BTC)…")
    df_btc = raw["BTC"]
    f_btc  = feats["BTC"]

    # Align close to feature index
    close_btc = df_btc["c"].reindex(f_btc.index)
    fwd_ret   = compute_targets(close_btc, FW)

    # Split indices
    tr_mask  = f_btc.index <  TRAIN_END
    val_mask = (f_btc.index >= TRAIN_END) & (f_btc.index < VAL_END)
    te_mask  = f_btc.index >= VAL_END

    # Compute alpha on TRAINING forward returns only (no look-ahead)
    fwd_tr   = fwd_ret[tr_mask].dropna()
    alpha    = np.percentile(np.abs(fwd_tr), ALPHA_PCT)
    print(f"  Alpha (85th pct |fwd_ret| in train): {alpha*100:.4f}%")

    labels = make_labels(fwd_ret, alpha).dropna()
    # Align all series to label index (valid fwd return exists)
    valid_idx = labels.index
    f_aligned = f_btc.reindex(valid_idx).dropna()
    valid_idx = f_aligned.index
    labels    = labels.reindex(valid_idx)
    close_al  = close_btc.reindex(valid_idx)

    tr_mask2  = valid_idx <  TRAIN_END
    val_mask2 = (valid_idx >= TRAIN_END) & (valid_idx < VAL_END)
    te_mask2  = valid_idx >= VAL_END

    print(f"  Train: {tr_mask2.sum():5d}  Val: {val_mask2.sum():5d}  "
          f"Test: {te_mask2.sum():5d} bars")
    print(f"  Class dist (train): "
          + " ".join(f"{CLASSES[c]}={np.mean(labels[tr_mask2]==c)*100:.1f}%"
                     for c in [0,1,2]))

    # Scale features (fit on train only)
    scaler    = StandardScaler()
    feat_vals = f_aligned.values.astype(np.float32)
    feat_vals[tr_mask2]  = scaler.fit_transform(feat_vals[tr_mask2])
    feat_vals[~tr_mask2] = scaler.transform(feat_vals[~tr_mask2])
    feat_vals = np.clip(feat_vals, -10, 10)

    lbl_vals = labels.values.astype(np.int64)

    X_all, y_all = make_sequences(feat_vals, lbl_vals, BW)
    # Shift indices to match last candle of each window
    idx_all = valid_idx[BW - 1:]
    # Trim to match X_all length
    n_seq   = len(X_all)
    idx_all = idx_all[:n_seq]

    tr_s  = idx_all <  TRAIN_END
    val_s = (idx_all >= TRAIN_END) & (idx_all < VAL_END)
    te_s  = idx_all >= VAL_END

    X_tr, y_tr   = X_all[tr_s],  y_all[tr_s]
    X_val, y_val = X_all[val_s], y_all[val_s]
    X_te, y_te   = X_all[te_s],  y_all[te_s]
    idx_te       = idx_all[te_s]

    print(f"  Sequences — Train: {len(X_tr)}  Val: {len(X_val)}  Test: {len(X_te)}")

    # ── 5. Train model ────────────────────────────────────────────────────────
    print(f"\n[5/7] Training {'LSTM' if TORCH else 'MLP'}…")
    model = train_lstm(X_tr, y_tr, X_val, y_val, n_feat)

    # OOS BTC predictions
    proba_te  = predict_proba_torch(model, X_te)
    y_pred_te = proba_te.argmax(axis=1)

    # Metrics
    auc_buy = roc_auc_score((y_te == BUY_CLS).astype(int), proba_te[:, BUY_CLS])
    cm = confusion_matrix(y_te, y_pred_te, labels=[0,1,2])
    acc_buy  = cm[2,2] / max(cm[2,:].sum(), 1)
    acc_sell = cm[0,0] / max(cm[0,:].sum(), 1)
    acc_hold = cm[1,1] / max(cm[1,:].sum(), 1)
    print(f"  OOS BTC AUC (BUY class): {auc_buy:.4f}")
    print(f"  OOS BTC confusion matrix (SELL/HOLD/BUY accuracy): "
          f"{acc_sell:.2f} / {acc_hold:.2f} / {acc_buy:.2f}")

    # ── 6. ETH generalization ─────────────────────────────────────────────────
    print("\n[6/7] ETH generalization (BTC-trained model)…")
    cum_eth, sharpe_eth, auc_eth = None, 0.0, 0.0

    if "ETH" in feats:
        f_eth    = feats["ETH"]
        close_eth = raw["ETH"]["c"].reindex(f_eth.index)
        fwd_eth   = compute_targets(close_eth, FW)

        # ETH labels use same alpha from BTC training
        lbl_eth_s = make_labels(fwd_eth, alpha).dropna()
        f_eth_s   = f_eth.reindex(lbl_eth_s.index).dropna()
        lbl_eth_s = lbl_eth_s.reindex(f_eth_s.index)
        close_eth_s = close_eth.reindex(f_eth_s.index)

        # Scale using BTC scaler
        feat_eth  = scaler.transform(f_eth_s.values.astype(np.float32))
        feat_eth  = np.clip(feat_eth, -10, 10)
        lbl_eth_a = lbl_eth_s.values.astype(np.int64)

        X_eth, y_eth = make_sequences(feat_eth, lbl_eth_a, BW)
        idx_eth      = f_eth_s.index[BW - 1: BW - 1 + len(X_eth)]

        te_eth_mask  = idx_eth >= VAL_END
        X_eth_te     = X_eth[te_eth_mask]
        y_eth_te     = y_eth[te_eth_mask]
        idx_eth_te   = idx_eth[te_eth_mask]

        if len(X_eth_te) > 50:
            proba_eth  = predict_proba_torch(model, X_eth_te)
            y_pred_eth = proba_eth.argmax(axis=1)
            auc_eth    = roc_auc_score((y_eth_te == BUY_CLS).astype(int),
                                       proba_eth[:, BUY_CLS])
            print(f"  ETH OOS AUC (BUY class): {auc_eth:.4f}  "
                  f"({'GENERIC PATTERN ✓' if auc_eth > 0.53 else 'no generalization'})")

            pred_eth_s  = pd.Series(y_pred_eth, index=idx_eth_te)
            close_eth_te = close_eth_s.reindex(idx_eth_te)
            cum_eth, sharpe_eth, _ = simulate_long_only(close_eth_te, pred_eth_s)
            print(f"  ETH Sharpe (long-only, OOS): {sharpe_eth:.3f}")

    # ── 7. BTC equity curve + analysis ───────────────────────────────────────
    print("\n[7/7] Equity curve and analysis (BTC OOS)…")
    pred_btc_s = pd.Series(y_pred_te, index=idx_te)
    close_te   = close_al.reindex(idx_te)
    cum_lstm, sharpe_lstm, bar_ret = simulate_long_only(close_te, pred_btc_s)
    cum_bnh = np.log(close_te / close_te.shift(1)).fillna(0).cumsum()

    n_years     = max((idx_te[-1] - idx_te[0]).days / 365.25, 0.01)
    entries     = (pred_btc_s == BUY_CLS).astype(float).diff() > 0
    n_trades_yr = entries.sum() / n_years
    cost_yr     = entries.sum() * COST_RT / n_years

    print(f"  BTC OOS Sharpe (long-only): {sharpe_lstm:.3f}")
    print(f"  Trades/year: {n_trades_yr:.0f}  "
          f"Annual cost drag: {cost_yr*100:.2f}%")

    # TSMOM correlation
    tsmom_wk  = compute_tsmom_weekly(raw["BTC"])
    bar_wk    = bar_ret.resample("W-MON").sum()
    common    = bar_wk.index.intersection(tsmom_wk.index)
    tsmom_corr = bar_wk.loc[common].corr(tsmom_wk.loc[common]) if len(common) > 20 else np.nan
    print(f"  Corr(LSTM, TSMOM weekly): {tsmom_corr:.3f}")

    # Permutation feature importance
    print("  Computing permutation feature importance…")
    try:
        importances = permutation_importance(
            lambda X: predict_proba_torch(model, X),
            X_te, y_te, n_repeats=6
        )
        top5 = sorted(zip(feat_names, importances), key=lambda x: -x[1])[:5]
        print("  Top-5 features (AUC drop):")
        for name, imp in top5:
            marker = " ← HL-native!" if name == "funding_rate" else ""
            print(f"    {name:22s}  {imp:+.4f}{marker}")
    except Exception as e:
        print(f"  Importance failed: {e}")
        importances = None

    # Figure
    make_figure(
        close_te, cum_lstm, sharpe_lstm, cum_bnh,
        y_te, y_pred_te, proba_te,
        feat_names, importances,
        cum_eth, sharpe_eth,
        tsmom_corr if not np.isnan(tsmom_corr) else 0.0,
        n_trades_yr, cost_yr
    )

    # ── Verdict ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    print(f"  BUY-class AUC  (OOS BTC) : {auc_buy:.4f}  "
          f"(>0.53 = signal, >0.55 = meaningful)")
    print(f"  BUY-class AUC  (OOS ETH) : {auc_eth:.4f}  "
          f"(>0.53 = generic pattern)")
    print(f"  Sharpe LSTM BTC (long-only): {sharpe_lstm:+.3f}")
    print(f"  Sharpe LSTM ETH (long-only): {sharpe_eth:+.3f}")
    print(f"  Corr vs TSMOM v3 weekly  : {tsmom_corr:+.3f}  "
          f"(target <0.40)")
    print(f"  Trades/year / cost drag  : {n_trades_yr:.0f} / "
          f"{cost_yr*100:.2f}%/yr")

    corr_ok  = abs(tsmom_corr) < 0.40 if not np.isnan(tsmom_corr) else False
    eth_gen  = auc_eth > 0.53

    if sharpe_lstm > 1.2 and corr_ok:
        verdict = "STRONG — add to A+B+C combination test"
    elif sharpe_lstm > 0.6 and corr_ok:
        verdict = "PROMISING — consider A+B+C combination"
    elif sharpe_lstm > 0.3 or (auc_buy > 0.55 and corr_ok):
        verdict = "WEAK — signal exists but too weak vs costs"
    else:
        verdict = "SKIP — no exploitable edge in OOS"

    print(f"\n  ETH generalization: {'YES (AUC>0.53)' if eth_gen else 'NO'}")
    print(f"\n  >>> {verdict}")
    print()
    print("  Long-only constraint maintained throughout (no shorts).")
    print("  Cost model: 0.17% RT, FW=2 candles (8h hold), Propr-grade fees.")


if __name__ == "__main__":
    main()
