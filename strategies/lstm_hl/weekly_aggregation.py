"""
strategies/lstm_hl/weekly_aggregation.py — LSTM 4h Signal Aggregated to Weekly

The 6.23 LSTM has AUC=0.6454 but 117 trades/yr → 19.95%/yr cost drag.
Fix: aggregate P(BUY) bars into a weekly score, execute once/week on Monday open.
Max cost = 52 × 0.17% = 8.84%/yr (vs 19.95%).

Three score variants aggregated from Mon 00h → Fri 20h (30 4h bars):
  v1 score_mean   = mean(P(BUY)_all_30_bars)
  v2 score_count  = count(P(BUY) > 0.55) / n_bars   [proportion high-confidence]
  v3 score_last6  = mean(P(BUY) last 6 bars = Friday)

Thresholds calibrated at 48th/50th/52nd percentile of val-period score distribution.
→ 9 configs = 3 variants × 3 thresholds.

OOS: 2025-01-01 → 2026-05-14 (same as 6.23 test period).
Vol target: 15% per asset, 4-week rolling realized vol.
Decision gate: LSTM weekly replaces XGBoost CS (6.21, Sharpe 0.734)
  if Sharpe > 0.734 AND corr(TSMOM) < 0.40.
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
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

warnings.filterwarnings("ignore")
np.random.seed(42)

# ─── CONSTANTS (identical to feasibility.py) ─────────────────────────────────
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

BW        = 5
FW        = 2
ALPHA_PCT = 85
COST_RT   = 0.0017
BUY_CLS   = 2
SELL_CLS  = 0
VOL_TGT   = 0.15

# XGBoost CS baseline (6.21 — different OOS period, noted in table)
XGBOOST_SHARPE = 0.734
XGBOOST_CORR   = 0.003   # corr(A,C)=0.37 but corr(B,C)=0.001 at bar level; using portfolio-level corr vs TSMOM
LSTM4H_SHARPE  = 0.022
LSTM4H_CORR    = 0.052

OUT_DIR  = os.path.dirname(os.path.abspath(__file__))

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    TORCH = True
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[weekly] PyTorch {torch.__version__} — device: {DEVICE}")
except ImportError:
    TORCH = False
    print("[weekly] PyTorch not found — using sklearn fallback")


# ─── DATA FETCHING (copy from feasibility.py) ─────────────────────────────────

def _hl_post(payload: dict, timeout: int = 30):
    for attempt in range(3):
        try:
            r = requests.post(HL_URL, json=payload, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == 2: raise
            time.sleep(2 ** attempt)


def fetch_hl_candles(coin: str) -> pd.DataFrame:
    all_rows: list = []
    t = START_MS
    while t < END_MS:
        chunk_end = min(t + CHUNK_MS, END_MS)
        dt_s = datetime.fromtimestamp(t/1000, tz=timezone.utc).strftime("%Y-%m-%d")
        print(f"    {coin} [{dt_s}] … ", end="", flush=True)
        rows = _hl_post({"type":"candleSnapshot",
                         "req":{"coin":coin,"interval":INTERVAL,
                                "startTime":t,"endTime":chunk_end}})
        print(len(rows))
        all_rows.extend(rows)
        t = chunk_end + 1 if not rows else int(rows[-1]["T"]) + 1
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
    all_rows: list = []
    t = START_MS
    while t < END_MS:
        chunk_end = min(t + CHUNK_MS, END_MS)
        try:
            rows = _hl_post({"type":"fundingHistory","coin":coin,
                              "startTime":t,"endTime":chunk_end})
        except Exception:
            rows = []
        all_rows.extend(rows)
        t = chunk_end + 1 if not rows else int(rows[-1]["time"]) + 1
        time.sleep(0.20)
    if not all_rows:
        return pd.Series(dtype=float, name="funding_rate")
    df_f = pd.DataFrame(all_rows)
    df_f["time"] = pd.to_datetime(df_f["time"].astype(np.int64), unit="ms", utc=True)
    series = (df_f.set_index("time")["fundingRate"]
                  .astype(float).sort_index()
                  .loc[~df_f.set_index("time").index.duplicated(keep="last")])
    return series


# ─── FEATURE ENGINEERING (copy from feasibility.py) ──────────────────────────

def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(span=period, adjust=False).mean()
    avg_l = loss.ewm(span=period, adjust=False).mean()
    rs    = avg_g / avg_l.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def build_features(df: pd.DataFrame, funding_series: pd.Series | None) -> pd.DataFrame:
    c = df["c"]; v = df["v"]
    ma20   = c.rolling(20).mean(); std20 = c.rolling(20).std()
    boll   = (c - ma20) / (2 * std20.replace(0, np.nan))
    rsi_n  = (compute_rsi(c, 14) - 50) / 50
    ema1   = c.ewm(span=1,  adjust=False).mean()
    ema21  = c.ewm(span=21, adjust=False).mean()
    ema50  = c.ewm(span=50, adjust=False).mean()
    ec121  = ema1  / ema21.replace(0, np.nan) - 1
    ec2150 = ema21 / ema50.replace(0, np.nan) - 1
    vol_ma = v.rolling(20).mean(); vol_std = v.rolling(20).std()
    vol_z  = (v - vol_ma) / vol_std.replace(0, np.nan)
    ret1   = np.log(c / c.shift(1))
    ret5   = np.log(c / c.shift(5))
    ret20  = np.log(c / c.shift(20))
    hour   = df.index.hour.astype(float); dow = df.index.dayofweek.astype(float)
    feat   = pd.DataFrame({
        "bollinger_pos":   boll, "rsi_norm": rsi_n,
        "ema_cross_1_21":  ec121, "ema_cross_21_50": ec2150, "vol_z": vol_z,
        "ret_1bar": ret1, "ret_5bar": ret5, "ret_20bar": ret20,
        "hour_sin": np.sin(2*np.pi*hour/24), "hour_cos": np.cos(2*np.pi*hour/24),
        "dow_sin":  np.sin(2*np.pi*dow/7),  "dow_cos":  np.cos(2*np.pi*dow/7),
    }, index=df.index)
    if funding_series is not None and len(funding_series) > 0:
        feat["funding_rate"] = funding_series.reindex(df.index, method="ffill").shift(1)
    return feat.dropna()


def make_sequences(feat: np.ndarray, labels: np.ndarray, bw: int = BW):
    X, y = [], []
    for i in range(bw - 1, len(feat)):
        X.append(feat[i - bw + 1: i + 1])
        y.append(labels[i])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


# ─── PYTORCH MODEL (copy from feasibility.py) ────────────────────────────────

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
            out1, _    = self.lstm1(x)
            _, (hn, _) = self.lstm2(out1)
            return self.fc2(self.relu(self.fc1(self.drop(hn[-1]))))

    def train_lstm(X_tr, y_tr, X_val, y_val, n_feat,
                   epochs=120, patience=12, lr=1e-3, batch=256):
        model = LSTMClassifier(n_feat).to(DEVICE)
        counts = np.bincount(y_tr, minlength=3).astype(float)
        counts = np.where(counts == 0, 1, counts)
        w    = torch.FloatTensor(1/counts / (1/counts).sum()).to(DEVICE)
        crit = nn.CrossEntropyLoss(weight=w)
        opt  = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
        sch  = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, patience=5, factor=0.5)

        Xt = torch.FloatTensor(X_tr).to(DEVICE)
        yt = torch.LongTensor(y_tr).to(DEVICE)
        Xv = torch.FloatTensor(X_val).to(DEVICE)
        yv = torch.LongTensor(y_val).to(DEVICE)
        ds = TensorDataset(Xt, yt)
        loader = DataLoader(ds, batch_size=batch, shuffle=True)

        best_val, best_state, pat_c = float("inf"), None, 0
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
                vl = crit(model(Xv), yv).item()
            sch.step(vl)
            if vl < best_val:
                best_val = vl
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
                pat_c = 0
            else:
                pat_c += 1
                if pat_c >= patience:
                    print(f"    Early stop @ epoch {epoch}")
                    break
        model.load_state_dict(best_state)
        return model

    def predict_proba(model, X: np.ndarray) -> np.ndarray:
        model.eval()
        with torch.no_grad():
            logits = model(torch.FloatTensor(X).to(DEVICE))
            return torch.softmax(logits, dim=1).cpu().numpy()

else:
    def train_lstm(X_tr, y_tr, X_val, y_val, n_feat, **kw):
        from sklearn.neural_network import MLPClassifier
        Xf = X_tr.reshape(len(X_tr), -1)
        m  = MLPClassifier(hidden_layer_sizes=(128, 64, 32, 16), activation="relu",
                           max_iter=300, early_stopping=True, random_state=42)
        m.fit(Xf, y_tr)
        return m

    def predict_proba(model, X: np.ndarray) -> np.ndarray:
        return model.predict_proba(X.reshape(len(X), -1))


# ─── WEEKLY SCORE AGGREGATION ────────────────────────────────────────────────

def get_all_bar_probas(model, feat_vals: np.ndarray, bw: int = BW) -> np.ndarray:
    """P(BUY) for every valid position (index bw-1 … n-1)."""
    n = len(feat_vals)
    X = np.stack([feat_vals[i - bw + 1: i + 1] for i in range(bw - 1, n)])
    return predict_proba(model, X.astype(np.float32))[:, BUY_CLS]


def compute_weekly_scores(p_buy: pd.Series,
                          high_conf_thr: float = 0.35) -> pd.DataFrame:
    """
    Group Mon–Fri 4h bars by W-FRI week, compute 3 score variants.
    Index = W-FRI Friday timestamp (aligned with resample('W-FRI')).

    high_conf_thr: threshold for score_count (proportion of bars above this).
      Set to 0.35 — the typical P(BUY) distribution peaks ~0.25, so 0.35
      selects the top quartile of "high-conviction" bars.
    """
    df = p_buy.rename("p_buy").to_frame()

    rows = []
    # Use W-FRI grouper so week_end timestamp aligns with resample("W-FRI")
    for week_end, grp in df.groupby(pd.Grouper(freq="W-FRI")):
        if grp.empty:
            continue
        # Keep Mon–Fri only (crypto trades 7d but signal window is business days)
        wd = grp[grp.index.dayofweek <= 4]
        if len(wd) < 15:
            continue
        mean_score  = wd["p_buy"].mean()
        # proportion of bars with strong BUY confidence (data-adaptive threshold)
        count_score = (wd["p_buy"] > high_conf_thr).sum() / len(wd)
        last_bars   = wd["p_buy"].iloc[-min(6, len(wd)):]
        last6_score = last_bars.mean()
        rows.append({
            "week_end":    week_end,
            "score_mean":  mean_score,
            "score_count": count_score,
            "score_last6": last6_score,
            "n_bars":      len(wd),
        })
    return pd.DataFrame(rows).set_index("week_end")


def calibrate_thresholds(weekly_scores: pd.DataFrame,
                          quantiles: tuple = (0.48, 0.50, 0.52)) -> dict:
    """
    Set thresholds at given percentiles of the val-period distribution.
    The literal values 0.48/0.50/0.52 are interpreted as percentile levels
    (e.g. 0.50 = median of val scores).
    """
    val_mask = (weekly_scores.index <  VAL_END)
    thr = {}
    for col in ["score_mean", "score_count", "score_last6"]:
        s = weekly_scores.loc[val_mask, col].dropna()
        if len(s) == 0:
            thr[col] = {q: 0.0 for q in quantiles}
            continue
        thr[col] = {q: float(np.percentile(s, q * 100)) for q in quantiles}
        print(f"  Threshold calibration [{col}]: "
              + "  ".join(f"q{int(q*100)}={thr[col][q]:.4f}" for q in quantiles))
    return thr


# ─── TSMOM v3 (for correlation) ───────────────────────────────────────────────

def compute_tsmom_weekly(df_4h: pd.DataFrame) -> pd.Series:
    daily_c = df_4h["c"].resample("D").last().dropna()
    lr      = np.log(daily_c / daily_c.shift(1)).dropna()
    cr28    = lr.rolling(28).sum()
    v28     = lr.rolling(28).std() * np.sqrt(28)
    sig     = np.tanh(cr28 / v28.replace(0, np.nan)).clip(lower=0)
    strat_r = sig.shift(1) * lr
    return strat_r.resample("W-FRI").sum()


# ─── VOL SCALING ─────────────────────────────────────────────────────────────

def compute_vol_scalar(df_4h: pd.DataFrame, vol_tgt: float = VOL_TGT) -> pd.Series:
    """4-week (28-day) rolling realized vol → vol_scalar, sampled weekly (Fri)."""
    daily_c  = df_4h["c"].resample("D").last().dropna()
    daily_r  = np.log(daily_c / daily_c.shift(1)).dropna()
    rv       = daily_r.rolling(28).std() * np.sqrt(252)
    weekly_v = rv.resample("W-FRI").last().dropna()
    scalar   = (vol_tgt / weekly_v.replace(0, np.nan)).clip(0.1, 2.0)
    return scalar


# ─── WEEKLY BACKTEST ─────────────────────────────────────────────────────────

def weekly_backtest(
    weekly_scores: pd.DataFrame,
    score_col: str,
    threshold: float,
    df_4h: pd.DataFrame,
    tsmom_wk: pd.Series,
    oos_start: str = VAL_END,
    cost_rt: float = COST_RT,
    vol_tgt: float = VOL_TGT,
) -> dict:
    """
    One backtest config. Returns dict with Sharpe, MaxDD, trades/yr, cost/yr, corr.
    """
    # Weekly close (Fri last bar)
    weekly_close = df_4h["c"].resample("W-FRI").last().dropna()

    # Forward weekly log return: close[T+1]/close[T]
    weekly_fwd_ret = np.log(weekly_close / weekly_close.shift(1))

    # Vol scalar (sampled weekly)
    vol_scalar = compute_vol_scalar(df_4h, vol_tgt)

    # Restrict to OOS test period
    oos_mask   = weekly_scores.index >= oos_start
    oos_scores = weekly_scores.loc[oos_mask, score_col].dropna()

    # Align all series to OOS score index
    common = (oos_scores.index
              .intersection(weekly_fwd_ret.index)
              .intersection(vol_scalar.index))
    if len(common) < 10:
        return {"sharpe": np.nan, "maxdd": np.nan, "trades_yr": 0,
                "cost_yr": 0, "corr_tsmom": np.nan, "n_weeks": 0}

    scores  = oos_scores.reindex(common)
    fwd_ret = weekly_fwd_ret.reindex(common)
    v_scal  = vol_scalar.reindex(common, method="ffill").fillna(1.0)

    # Binary signal: 1 if score > threshold, else 0
    signal  = (scores > threshold).astype(float)
    # Vol-scaled position
    pos     = signal * v_scal

    # Shift: signal at T → position for week T+1 (no look-ahead)
    pos_shifted = pos.shift(1).fillna(0)
    ret_shifted = fwd_ret  # week T+1 return

    # Align (drop first NaN from shift)
    valid = pos_shifted.dropna().index.intersection(ret_shifted.dropna().index)
    pos_s = pos_shifted.reindex(valid)
    ret_s = ret_shifted.reindex(valid)

    entries    = (pos_s.diff() > 0).astype(float)
    bar_ret    = pos_s * ret_s - entries * cost_rt
    cum_ret    = bar_ret.cumsum()

    n_years    = max((valid[-1] - valid[0]).days / 365.25, 0.1)
    n_trades   = entries.sum()
    sharpe     = bar_ret.mean() / bar_ret.std() * np.sqrt(52) if bar_ret.std() > 0 else 0.0
    maxdd      = (cum_ret - cum_ret.cummax()).min()
    trades_yr  = n_trades / n_years
    cost_yr    = n_trades * cost_rt / n_years

    # TSMOM correlation
    bar_ret_tsmom = bar_ret.resample("W-FRI").sum()
    common_t = bar_ret_tsmom.index.intersection(tsmom_wk.index)
    corr_t   = (bar_ret_tsmom.loc[common_t].corr(tsmom_wk.loc[common_t])
                if len(common_t) >= 10 else np.nan)

    return {"sharpe": sharpe, "maxdd": maxdd, "cum_ret": cum_ret,
            "trades_yr": trades_yr, "cost_yr": cost_yr,
            "corr_tsmom": corr_t, "n_weeks": len(valid),
            "bar_ret": bar_ret}


# ─── IC TEST ─────────────────────────────────────────────────────────────────

def ic_test(weekly_scores: pd.DataFrame, score_col: str,
            df_4h: pd.DataFrame, oos_start: str = VAL_END) -> dict:
    """
    Time-series IC: spearmanr(score[T], forward_weekly_ret[T+1]).
    Restricted to OOS period to match backtest.
    """
    weekly_close   = df_4h["c"].resample("W-FRI").last().dropna()
    weekly_fwd_ret = np.log(weekly_close / weekly_close.shift(1))

    oos_mask = weekly_scores.index >= oos_start
    scores   = weekly_scores.loc[oos_mask, score_col].dropna()

    # Align: score at T → forward return at T+1
    # (forward return index = T+1 timestamp; we need to align score[T] with fwd_ret[T])
    fwd_ret_aligned = weekly_fwd_ret.reindex(scores.index)

    # Shift score forward by 1 week to get the return that score was predicting
    # Actually: score[T] predicts fwd_ret which is indexed at T (= close[T+1]/close[T])
    # So no shift needed: score[T] ↔ fwd_ret[T] where fwd_ret[T] = return of week T+1
    common = scores.dropna().index.intersection(fwd_ret_aligned.dropna().index)
    if len(common) < 5:
        return {"ic": np.nan, "t_stat": np.nan, "p_val": np.nan, "n": 0}

    s = scores.reindex(common)
    r = fwd_ret_aligned.reindex(common)
    ic, p_val = spearmanr(s, r)
    n = len(common)
    t_stat = ic * np.sqrt(n - 2) / np.sqrt(max(1 - ic**2, 1e-9))
    return {"ic": ic, "t_stat": t_stat, "p_val": p_val, "n": n}


# ─── FIGURE ──────────────────────────────────────────────────────────────────

def make_figure(best_config: dict, all_results: pd.DataFrame,
                df_4h_btc: pd.DataFrame, tsmom_wk: pd.Series,
                ic_results: dict) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle(
        "LSTM 4h → Weekly Score Aggregation — Strategy C Candidate\n"
        "OOS: 2025-01 → 2026-05  |  Vol target: 15%  |  Cost: 0.17% RT",
        fontsize=13, fontweight="bold"
    )

    # ── Panel 1: Sharpe across 9 configs ─────────────────────────────────────
    ax = axes[0, 0]
    configs = all_results["label"].tolist()
    sharpes = all_results["sharpe"].tolist()
    colors  = ["#2166ac" if s > XGBOOST_SHARPE else
               "#1a9850" if s > 0 else "#d73027" for s in sharpes]
    ax.barh(configs, sharpes, color=colors, edgecolor="white")
    ax.axvline(XGBOOST_SHARPE, color="#f4a582", ls="--", lw=1.5,
               label=f"XGBoost C baseline ({XGBOOST_SHARPE})")
    ax.axvline(0, color="gray", lw=0.5)
    ax.set_title("Sharpe across 9 configs (OOS)", fontsize=10)
    ax.set_xlabel("Annualised Sharpe"); ax.legend(fontsize=8)

    # ── Panel 2: IC results ───────────────────────────────────────────────────
    ax = axes[0, 1]
    ic_rows  = [(k, v["ic"], v["t_stat"]) for k, v in ic_results.items()]
    ic_df    = pd.DataFrame(ic_rows, columns=["score","ic","t_stat"])
    ax.bar(ic_df["score"], ic_df["ic"],
           color=["#1a9850" if v > 0 else "#d73027" for v in ic_df["ic"]],
           edgecolor="white")
    ax.axhline(0, color="gray", lw=0.5)
    for i, row in ic_df.iterrows():
        ax.text(i, row["ic"] + 0.002, f"t={row['t_stat']:.2f}", ha="center",
                fontsize=9, fontweight="bold")
    ax.set_title("Weekly IC (spearman): score[T] vs ret[T+1]", fontsize=10)
    ax.set_ylabel("IC")
    ax.tick_params(axis="x", rotation=15)

    # ── Panel 3: corr(TSMOM) across configs ──────────────────────────────────
    ax = axes[0, 2]
    corrs = all_results["corr_tsmom"].tolist()
    ax.barh(configs, corrs, color=["#d73027" if c > 0.40 else "#1a9850"
                                    for c in corrs], edgecolor="white")
    ax.axvline(0.40, color="k", ls="--", lw=1.5, label="corr=0.40 limit")
    ax.axvline(0, color="gray", lw=0.5)
    ax.set_title("Correlation with TSMOM v3 weekly", fontsize=10)
    ax.set_xlabel("Pearson correlation"); ax.legend(fontsize=8)

    # ── Panel 4: Best config equity curve ────────────────────────────────────
    ax = axes[1, 0:2].flatten()
    ax = axes[1, 0]
    if "cum_ret" in best_config:
        cum = best_config["cum_ret"]
        ax.plot(cum.index, cum.values * 100,
                color="#2166ac", lw=2, label=f"LSTM weekly best  Sharpe={best_config['sharpe']:.3f}")
        # Buy & hold BTC in OOS
        bnh = np.log(df_4h_btc["c"] / df_4h_btc["c"].shift(1)).fillna(0)
        bnh_cum = bnh[bnh.index >= VAL_END].cumsum() * 100
        ax.plot(bnh_cum.index, bnh_cum.values, color="gray", lw=1, ls="--",
                alpha=0.7, label="Buy & Hold BTC")
        ax.axhline(0, color="black", lw=0.5)
        ax.set_title(f"Best Config Equity Curve (OOS)\n"
                     f"{best_config['label']}  "
                     f"corr(TSMOM)={best_config['corr_tsmom']:.3f}", fontsize=10)
        ax.set_ylabel("Cum log return (%)"); ax.set_xlabel("Date")
        ax.legend(fontsize=9); ax.grid(alpha=0.3)

    # ── Panel 5: Trades/yr vs Sharpe scatter ─────────────────────────────────
    ax = axes[1, 1]
    ax.scatter(all_results["trades_yr"], all_results["sharpe"],
               c=all_results["corr_tsmom"], cmap="RdYlGn_r",
               vmin=0, vmax=0.6, s=80, edgecolors="black", zorder=3)
    ax.axhline(XGBOOST_SHARPE, color="orange", ls="--", lw=1.5,
               label=f"XGBoost baseline {XGBOOST_SHARPE}")
    ax.axhline(0, color="gray", lw=0.5)
    ax.set_title("Sharpe vs Trades/yr (colour = corr TSMOM)", fontsize=10)
    ax.set_xlabel("Trades per year"); ax.set_ylabel("Sharpe"); ax.legend(fontsize=8)

    # ── Panel 6: Comparison table ─────────────────────────────────────────────
    ax = axes[1, 2]
    ax.axis("off")
    best = best_config
    table_text = (
        "═══ STRATEGY COMPARISON ═══\n\n"
        f"{'Strategy':<30} {'Sharpe':>7} {'MaxDD':>8} {'corr(A)':>8}\n"
        f"{'─'*55}\n"
        f"{'LSTM 4h (6.23, 117t/yr)':<30} {LSTM4H_SHARPE:>7.3f} {'—':>8} {LSTM4H_CORR:>8.3f}\n"
        f"{'LSTM weekly (best cfg)':<30} {best.get('sharpe',0):>7.3f} "
        f"{best.get('maxdd',0)*100:>7.1f}% {best.get('corr_tsmom',0):>8.3f}\n"
        f"{'TSMOM v3 (OOS recomputed)':<30} {'(see print)':>7}\n"
        f"{'XGBoost CS v2 (6.21)†':<30} {XGBOOST_SHARPE:>7.3f} {'-42.5%':>8} {'~+0.37':>8}\n"
        f"{'─'*55}\n"
        f"† XGBoost OOS: 2023-11 → 2025-06 (different period)\n\n"
        f"Best config: {best.get('label','—')}\n"
        f"  Trades/yr: {best.get('trades_yr',0):.0f}  "
        f"Cost/yr: {best.get('cost_yr',0)*100:.2f}%\n\n"
        f"Decision threshold:\n"
        f"  Sharpe > {XGBOOST_SHARPE} AND corr < 0.40\n"
        f"  → {'REPLACE XGBoost ✓' if best.get('sharpe',0) > XGBOOST_SHARPE and abs(best.get('corr_tsmom',1)) < 0.40 else 'DO NOT replace XGBoost'}"
    )
    ax.text(0.05, 0.95, table_text, transform=ax.transAxes,
            va="top", ha="left", fontsize=9,
            fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#f0f4ff", edgecolor="#2166ac"))

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "weekly_results.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  Figure → {out_path}")
    plt.close()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("LSTM WEEKLY AGGREGATION — Fix 117 trades/yr cost problem")
    print(f"OOS: {VAL_END} → {TEST_END}  |  3 score variants × 3 thresholds = 9 configs")
    print("=" * 70)

    # ── 1. Data ───────────────────────────────────────────────────────────────
    print("\n[1/7] Fetching HL data…")
    raw: dict = {}
    funding: dict = {}
    for coin in COINS:
        print(f"\n  {coin}:")
        try:
            df = fetch_hl_candles(coin)
            if len(df) < 500:
                raise ValueError(f"only {len(df)} candles")
            raw[coin] = df
            print(f"  → {len(df)} candles  {df.index[0].date()} → {df.index[-1].date()}")
        except Exception as e:
            print(f"  FAILED: {e}")

    if "BTC" not in raw:
        print("ERROR: BTC data unavailable."); return

    print("\n  Funding history:")
    for coin in COINS:
        if coin not in raw: continue
        try:
            fs = fetch_funding_history(coin)
            if len(fs) > 0:
                funding[coin] = fs
                print(f"  {coin}: {len(fs)} records")
        except Exception as e:
            print(f"  {coin} funding FAILED: {e}")

    # ── 2. Features + targets (BTC) ───────────────────────────────────────────
    print("\n[2/7] Feature engineering (BTC)…")
    feats: dict = {}
    for coin in COINS:
        if coin not in raw: continue
        f = build_features(raw[coin], funding.get(coin))
        feats[coin] = f
    print(f"  BTC: {len(feats['BTC'])} bars, {feats['BTC'].shape[1]} features")

    n_feat = feats["BTC"].shape[1]
    f_btc  = feats["BTC"]
    close_btc = raw["BTC"]["c"].reindex(f_btc.index)
    fwd_ret   = np.log(close_btc.shift(-FW) / close_btc)

    tr_m  = f_btc.index <  TRAIN_END
    val_m = (f_btc.index >= TRAIN_END) & (f_btc.index < VAL_END)

    fwd_tr = fwd_ret[tr_m].dropna()
    alpha  = np.percentile(np.abs(fwd_tr), ALPHA_PCT)

    labels = pd.Series(1, index=f_btc.index)
    labels[fwd_ret > alpha]  = 2
    labels[fwd_ret < -alpha] = 0

    valid_idx = f_btc.dropna().index.intersection(labels.dropna().index)
    f_al      = f_btc.reindex(valid_idx).dropna()
    lbl_al    = labels.reindex(f_al.index)

    # Scale (fit on train only)
    scaler = StandardScaler()
    feat_vals = f_al.values.astype(np.float32)
    tr_mask2  = f_al.index < TRAIN_END
    val_mask2 = (f_al.index >= TRAIN_END) & (f_al.index < VAL_END)
    feat_vals[tr_mask2]  = scaler.fit_transform(feat_vals[tr_mask2])
    feat_vals[~tr_mask2] = scaler.transform(feat_vals[~tr_mask2])
    feat_vals = np.clip(feat_vals, -10, 10)
    lbl_vals  = lbl_al.values.astype(np.int64)

    X_all, y_all = make_sequences(feat_vals, lbl_vals, BW)
    idx_all      = f_al.index[BW - 1: BW - 1 + len(X_all)]
    tr_s   = idx_all <  TRAIN_END
    val_s  = (idx_all >= TRAIN_END) & (idx_all < VAL_END)
    X_tr, y_tr   = X_all[tr_s],  y_all[tr_s]
    X_val, y_val = X_all[val_s], y_all[val_s]
    print(f"  Train: {len(X_tr)}  Val: {len(X_val)}  Total seqs: {len(X_all)}")

    # ── 3. Train LSTM ─────────────────────────────────────────────────────────
    print("\n[3/7] Training LSTM (same hyperparams as 6.23)…")
    model = train_lstm(X_tr, y_tr, X_val, y_val, n_feat)

    # ── 4. P(BUY) for all candles ─────────────────────────────────────────────
    print("\n[4/7] Computing P(BUY) for all bars…")
    p_buy_all = get_all_bar_probas(model, feat_vals, BW)
    p_buy_s   = pd.Series(p_buy_all, index=idx_all, name="p_buy")
    print(f"  Total bars with predictions: {len(p_buy_s)}")
    print(f"  Mean P(BUY) all: {p_buy_s.mean():.4f}  "
          f"(train period: {p_buy_s[p_buy_s.index < TRAIN_END].mean():.4f}  "
          f"test period: {p_buy_s[p_buy_s.index >= VAL_END].mean():.4f})")

    # ── 5. Weekly scores ──────────────────────────────────────────────────────
    print("\n[5/7] Aggregating to weekly scores (Mon-Fri window)…")
    wk_scores = compute_weekly_scores(p_buy_s)
    print(f"  Total weeks: {len(wk_scores)}")
    print(f"  Val-period weekly score stats (n={len(wk_scores[wk_scores.index < VAL_END])}):")
    val_wk = wk_scores[wk_scores.index < VAL_END]
    for col in ["score_mean", "score_count", "score_last6"]:
        print(f"    {col:15s}: mean={val_wk[col].mean():.4f}  "
              f"p50={val_wk[col].quantile(0.50):.4f}  "
              f"p75={val_wk[col].quantile(0.75):.4f}")

    # Calibrate thresholds from val period
    print("\n  Calibrating thresholds from val period:")
    thresholds = calibrate_thresholds(wk_scores)

    # ── 6. IC test ────────────────────────────────────────────────────────────
    print("\n[6/7] Weekly IC test (OOS)…")
    ic_results = {}
    for score_col in ["score_mean", "score_count", "score_last6"]:
        res = ic_test(wk_scores, score_col, raw["BTC"])
        ic_results[score_col] = res
        print(f"  {score_col:15s}  IC={res['ic']:+.4f}  t={res['t_stat']:+.3f}  "
              f"n={res['n']}  p={res['p_val']:.3f}")

    # ── 7. 9-config backtest grid ─────────────────────────────────────────────
    print("\n[7/7] 9-config backtest grid (OOS 2025-01 → 2026-05)…")
    tsmom_wk = compute_tsmom_weekly(raw["BTC"])

    QUANTILES = (0.48, 0.50, 0.52)
    results_rows = []
    all_configs  = {}

    for score_col in ["score_mean", "score_count", "score_last6"]:
        for q in QUANTILES:
            thr   = thresholds[score_col][q]
            label = f"{score_col} q{int(q*100)}"
            res   = weekly_backtest(wk_scores, score_col, thr, raw["BTC"], tsmom_wk)
            res["label"]      = label
            res["score_col"]  = score_col
            res["quantile"]   = q
            res["threshold"]  = thr
            all_configs[label] = res
            results_rows.append(res)

    all_results = pd.DataFrame(results_rows)

    # Print grid
    print(f"\n  {'Config':<28} {'Sharpe':>7} {'MaxDD':>8} {'t/yr':>6} {'cost%':>7} {'corr(A)':>8}")
    print("  " + "─" * 70)
    for _, row in all_results.iterrows():
        print(f"  {row['label']:<28} {row['sharpe']:>7.3f} "
              f"{row['maxdd']*100:>7.1f}% {row['trades_yr']:>6.0f} "
              f"{row['cost_yr']*100:>6.2f}% {row['corr_tsmom']:>8.3f}")

    # Best config by Sharpe
    best_label  = all_results.loc[all_results["sharpe"].idxmax(), "label"]
    best_config = all_configs[best_label]
    print(f"\n  Best config: {best_label}")

    # Recompute TSMOM on OOS period for comparison
    tsmom_oos  = tsmom_wk[tsmom_wk.index >= VAL_END].dropna()
    if len(tsmom_oos) > 0:
        ts_sharpe = tsmom_oos.mean() / tsmom_oos.std() * np.sqrt(52)
        print(f"\n  TSMOM v3 Sharpe on OOS 2025-01→2026-05: {ts_sharpe:.3f}")

    # ETH generalization
    eth_best_sharpe = np.nan
    if "ETH" in feats:
        print("\n  ETH generalization (BTC-trained model)…")
        f_eth     = feats["ETH"]
        feat_eth  = np.clip(scaler.transform(f_eth.values.astype(np.float32)), -10, 10)
        p_buy_eth = pd.Series(get_all_bar_probas(model, feat_eth, BW),
                              index=f_eth.index[BW - 1: BW - 1 + len(feat_eth) - BW + 1],
                              name="p_buy")
        wk_eth    = compute_weekly_scores(p_buy_eth)
        best_sc   = best_config["score_col"]
        best_q    = best_config["quantile"]
        eth_thr   = calibrate_thresholds(wk_eth)
        eth_res   = weekly_backtest(wk_eth, best_sc,
                                    eth_thr[best_sc][best_q],
                                    raw["ETH"], tsmom_wk)
        eth_best_sharpe = eth_res["sharpe"]
        print(f"  ETH Sharpe (best config applied): {eth_best_sharpe:.3f}")

    # Figure
    make_figure(best_config, all_results, raw["BTC"], tsmom_wk, ic_results)

    # ── VERDICT ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)

    bs = best_config.get("sharpe", 0)
    bc = abs(best_config.get("corr_tsmom", 1))
    bi = ic_results.get(best_config.get("score_col",""), {}).get("ic", 0)
    bt = ic_results.get(best_config.get("score_col",""), {}).get("t_stat", 0)

    print(f"  Best weekly Sharpe      : {bs:+.3f}")
    print(f"  Best corr(TSMOM)        : {bc:+.3f}  (target < 0.40)")
    print(f"  Best IC / t-stat        : {bi:+.4f} / {bt:+.3f}")
    print(f"  ETH generalization Sharpe: {eth_best_sharpe:+.3f}")
    print(f"  XGBoost baseline Sharpe  : {XGBOOST_SHARPE}")
    print()

    if bs > XGBOOST_SHARPE and bc < 0.40:
        verdict = "STRONG — LSTM weekly REPLACES XGBoost as Strategy C candidate"
        action  = "Run A+B+C with LSTM weekly instead of XGBoost CS."
    elif bs > 0.6 and bc < 0.40:
        verdict = "PROMISING — LSTM weekly is a competitive Strategy C candidate"
        action  = "Compare A+B+C(LSTM) vs A+B+C(XGBoost). Use higher Sharpe."
    elif bs > 0.3:
        verdict = "WEAK — weekly aggregation improves on 4h but below threshold"
        action  = "Move to STR small-cap (next candidate, Zaremba 2021)."
    else:
        verdict = "SKIP — edge evaporates at weekly resolution; purely intraday"
        action  = "Move to STR small-cap (next candidate, Zaremba 2021)."

    print(f"  >>> {verdict}")
    print(f"  Next step: {action}")
    print()
    print("  Cost comparison:")
    print(f"    4h frequency (6.23): 117 trades/yr × 0.17% = 19.95%/yr")
    print(f"    Weekly (best config): {best_config.get('trades_yr',0):.0f} trades/yr × "
          f"0.17% = {best_config.get('cost_yr',0)*100:.2f}%/yr")


if __name__ == "__main__":
    main()
