#!/usr/bin/env python3
"""
Crypto/research/passed/hmm_transitions/feasibility.py

HMM Forward-Algorithm Transition Probabilities — Signals 45–48
===============================================================
Key difference from 6.15 (failed Viterbi approach):
  6.15: state[T] = viterbi(obs[:T+1])  ← NON-CAUSAL, binary gate
  This: alpha[T] = forward(obs[:T])    ← FULLY CAUSAL, continuous [0,1]

Forward algorithm gives the filtered distribution:
  alpha[T, j] ∝ P(state_T=j | obs_0:T)                  (causal posterior)

Transition probability signal:
  P_bull_next[T] = P(state_{T+1}=bull | obs_0:T)
                 = sum_i alpha[T,i] × transmat[i, bull_state]
  ← continuous [0,1], no look-ahead, uses only past observations

HMM parameters fit on 2018-2021 train, then FROZEN.
Forward algorithm runs incrementally on OOS 2022-2026.

Signals:
  S1 — Raw P_bull_next (vol-targeted position size)
  S2 — Probability change (regime momentum: entering/exiting bull)
  S3 — Bear→Bull crossing entry (regime transition event)
  S4 — TSMOM × HMM weight (0.30–1.0 based on bull probability)

Features (2-dim, simpler = more stable HMM than 6.15's 4-dim):
  obs[T,0] = log_ret[T]    = log(close[T]/close[T-1])
  obs[T,1] = vol_ratio[T]  = std(log_ret[T-5:T]) / std(log_ret[T-20:T])

Cost: 0.17% RT, weekly Monday rebalance, vol target 15%.
Walk-forward: 3 windows (refit HMM per window).
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
from scipy import stats
from scipy.stats import multivariate_normal

warnings.filterwarnings("ignore")

# ── Constants ──────────────────────────────────────────────────────────────────

DATA_START   = "2018-01-01"
DATA_END     = "2026-05-14"
TRAIN_END    = "2021-12-31"
OOS_START    = "2022-01-01"

N_STATES     = 2
HMM_ITERS    = 300
HMM_RESTARTS = 5            # random restarts, keep best log-likelihood

VOL_TARGET   = 0.15
VOL_WINDOW   = 20
GROSS_CAP    = 0.90
COST_RT      = 0.0017
COST_OW      = COST_RT / 2
TRADING_DAYS = 365

TSMOM_LB     = 28
FWD_DAYS     = 5

# S3 thresholds: P_bull rises above 0.65 after being below 0.50 for 5 days
S3_ENTRY     = 0.65
S3_PRIOR_LO  = 0.50
S3_LOOKBACK  = 5

OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Data ───────────────────────────────────────────────────────────────────────

def download_data() -> pd.Series:
    print(f"Downloading BTC-USD ({DATA_START} → {DATA_END})...")
    raw = yf.download(
        "BTC-USD", start=DATA_START, end=DATA_END,
        auto_adjust=True, progress=False, interval="1d",
    )
    if raw.index.tz is not None:
        raw.index = raw.index.tz_convert(None)
    c = raw["Close"]
    if isinstance(c, pd.DataFrame):
        c = c.iloc[:, 0]
    c = c.ffill(limit=2)
    c = pd.Series(c.values, index=c.index, name="BTC")
    print(f"  {c.index[0].date()} → {c.index[-1].date()} ({len(c)} days)")
    return c


# ── Features ───────────────────────────────────────────────────────────────────

def build_features(close: pd.Series) -> pd.DataFrame:
    """
    2-feature observation vector (causal, no look-ahead):
      log_ret   = log(close[T] / close[T-1])
      vol_ratio = std(log_ret[T-5:T]) / std(log_ret[T-20:T])

    Returns DataFrame aligned to close.index, NaN where insufficient history.
    """
    lr        = np.log(close / close.shift(1))
    vol5      = lr.rolling(5).std()
    vol20     = lr.rolling(20).std()
    vol_ratio = vol5 / (vol20 + 1e-8)
    return pd.DataFrame({"log_ret": lr, "vol_ratio": vol_ratio}, index=close.index)


# ── HMM Fitting ────────────────────────────────────────────────────────────────

def fit_hmm(obs: np.ndarray) -> GaussianHMM:
    """
    Fit 2-state Gaussian HMM with multiple random restarts.
    Returns best model by log-likelihood.
    """
    best_model  = None
    best_ll     = -np.inf

    for seed in range(HMM_RESTARTS):
        model = GaussianHMM(
            n_components=N_STATES,
            covariance_type="diag",
            n_iter=HMM_ITERS,
            random_state=seed,
        )
        try:
            model.fit(obs)
            ll = model.score(obs)
            if ll > best_ll:
                best_ll    = ll
                best_model = model
        except Exception:
            continue

    if best_model is None:
        raise RuntimeError("HMM fitting failed for all random restarts.")

    return best_model


def bull_state_idx(model: GaussianHMM) -> int:
    """BULL = state with higher mean log_ret (feature 0)."""
    return int(np.argmax(model.means_[:, 0]))


# ── Emission Probability ───────────────────────────────────────────────────────

def emission_probs(model: GaussianHMM, obs_t: np.ndarray) -> np.ndarray:
    """
    P(obs_t | state=s) for each state s.
    Uses numerically stable log-space computation.
    obs_t: (n_features,)
    Returns: (n_states,) relative probabilities (max=1 after log-shift).
    """
    log_probs = np.zeros(N_STATES)
    for s in range(N_STATES):
        cov = np.diag(model.covars_[s])   # diag covariance → diagonal matrix
        log_probs[s] = multivariate_normal.logpdf(obs_t, mean=model.means_[s], cov=cov)

    # Shift by max for numerical stability before exp
    log_probs -= log_probs.max()
    return np.exp(log_probs)


# ── Forward Algorithm ──────────────────────────────────────────────────────────

def run_forward(
    model: GaussianHMM,
    obs: np.ndarray,
    alpha_init: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Fully causal forward algorithm (online filtering).

    At each step T:
      1. Predict: alpha_pred = alpha_{T-1} @ transmat
      2. Update:  alpha_T   = alpha_pred × emit(obs_T), then normalize
      3. Signal:  P_bull_next[T] = (alpha_T @ transmat)[bull_state]

    Parameters
    ----------
    model      : fitted GaussianHMM
    obs        : (T, n_features) observation sequence
    alpha_init : (n_states,) initial filtered distribution.
                 If None, uses startprob × emit(obs[0]) for t=0.

    Returns
    -------
    alpha_seq   : (T, n_states) filtered distributions
    p_bull_next : (T,) P(bull at T+1 | obs_0:T) — the causal signal
    final_alpha : (n_states,) alpha at the last step (for chaining)
    """
    T       = len(obs)
    bs      = bull_state_idx(model)
    transmat = model.transmat_

    alpha_seq   = np.zeros((T, N_STATES))
    p_bull_next = np.zeros(T)

    if alpha_init is None:
        # t=0: start from startprob × emission (standard forward init)
        emit   = emission_probs(model, obs[0])
        alpha  = model.startprob_ * emit
        denom  = alpha.sum()
        alpha  = alpha / denom if denom > 1e-300 else np.full(N_STATES, 1.0 / N_STATES)
        alpha_seq[0]   = alpha
        p_bull_next[0] = (alpha @ transmat)[bs]
        t_start = 1
    else:
        # Continue from given alpha (used for OOS after training)
        alpha   = alpha_init.copy()
        t_start = 0

    for t in range(t_start, T):
        alpha_pred = alpha @ transmat         # predict
        emit       = emission_probs(model, obs[t])
        alpha      = alpha_pred * emit        # update
        denom      = alpha.sum()
        alpha      = (alpha / denom
                      if denom > 1e-300
                      else np.full(N_STATES, 1.0 / N_STATES))
        alpha_seq[t]   = alpha
        p_bull_next[t] = (alpha @ transmat)[bs]

    return alpha_seq, p_bull_next, alpha


def train_and_get_final_alpha(
    model: GaussianHMM,
    obs_train: np.ndarray,
) -> np.ndarray:
    """Run forward algorithm through training data to get final alpha."""
    _, _, final_alpha = run_forward(model, obs_train)
    return final_alpha


# ── Signal Construction ────────────────────────────────────────────────────────

def build_signals(
    p_bull: pd.Series,
    close: pd.Series,
) -> dict[str, pd.Series]:
    """
    Build 4 signals from P_bull_next and close.
    All signals are already causal (p_bull uses obs up to T, predicts T+1).
    The backtest adds another shift(1) — so position at T uses p_bull[T-1].
    """
    # ── S1: Raw probability ────────────────────────────────────────────────────
    s1 = p_bull.clip(0.0, 1.0)

    # ── S2: Probability change — rising probability = entering bull ────────────
    dp = p_bull.diff()
    s2 = dp.clip(0.0, None)   # long when P_bull_next increasing, flat otherwise
    # Normalize to [0, 1] via rolling std
    dp_std = dp.rolling(20).std().shift(1)
    s2_norm = (dp / (dp_std + 1e-8)).apply(np.tanh).clip(0.0, 1.0)
    s2_norm = s2_norm.fillna(0.0)

    # ── S3: Bear→Bull crossing (regime entry) ─────────────────────────────────
    # Long when P_bull_next > 0.65 AND max over prior 5 days was < 0.50
    prior_max = p_bull.shift(1).rolling(S3_LOOKBACK).max()
    crossing  = (p_bull > S3_ENTRY) & (prior_max < S3_PRIOR_LO)
    # Hold position for 5 days after crossing
    s3 = pd.Series(0.0, index=p_bull.index)
    for date in p_bull.index[crossing]:
        idx   = p_bull.index.get_loc(date)
        end   = min(idx + FWD_DAYS, len(s3))
        s3.iloc[idx:end] = 1.0

    # ── S4: TSMOM × HMM weight ────────────────────────────────────────────────
    lr      = np.log(close / close.shift(1))
    cumret  = lr.rolling(TSMOM_LB).sum().shift(1)
    vol_28d = lr.rolling(TSMOM_LB).std().shift(1)
    tsmom   = np.tanh(cumret / (vol_28d * np.sqrt(TSMOM_LB) + 1e-8))
    hmm_wt  = 0.3 + 0.7 * p_bull   # [0.30, 1.00]
    s4      = (tsmom * hmm_wt).clip(0.0, 1.0).fillna(0.0)

    return {
        "S1 Raw P_bull":    s1.fillna(0.0),
        "S2 Prob change":   s2_norm,
        "S3 Regime entry":  s3,
        "S4 TSMOM×HMM":     s4,
    }


def compute_tsmom(close: pd.Series) -> pd.Series:
    lr      = np.log(close / close.shift(1))
    cumret  = lr.rolling(TSMOM_LB).sum().shift(1)
    vol_28d = lr.rolling(TSMOM_LB).std().shift(1)
    return np.tanh(cumret / (vol_28d * np.sqrt(TSMOM_LB) + 1e-8)).clip(0.0, 1.0).fillna(0.0)


# ── Backtest ───────────────────────────────────────────────────────────────────

def backtest(close: pd.Series, signal: pd.Series, label: str = "") -> dict[str, Any]:
    """Single-asset BTC backtest, vol-targeted, weekly Monday rebalance."""
    lr      = np.log(close / close.shift(1))
    ann_vol = lr.rolling(VOL_WINDOW).std().shift(1) * np.sqrt(TRADING_DAYS)
    scalar  = (VOL_TARGET / ann_vol.replace(0.0, np.nan)).clip(0.1, 2.0)

    raw_pos = (signal * scalar).fillna(0.0)

    is_mon  = raw_pos.index.dayofweek == 0
    pos_wk  = raw_pos.copy()
    pos_wk[~is_mon] = np.nan
    pos_wk  = pos_wk.ffill().fillna(0.0).clip(-GROSS_CAP, GROSS_CAP)

    arith    = close.pct_change()
    held     = pos_wk.shift(1).fillna(0.0)
    gpnl     = held * arith
    is_mon_s = pd.Series(is_mon.astype(float), index=pos_wk.index)
    costs    = pos_wk.diff().abs() * COST_OW * is_mon_s
    net      = (gpnl - costs).dropna()

    sharpe  = float((net.mean() / net.std()) * np.sqrt(TRADING_DAYS)) if net.std() > 0 else 0.0
    eq      = (1 + net).cumprod()
    max_dd  = float(((eq - eq.cummax()) / eq.cummax()).min())
    ann_ret = float(net.mean() * TRADING_DAYS)
    pneg    = float(abs(net[net < 0].sum()))
    pf      = float(net[net > 0].sum()) / pneg if pneg > 0 else np.inf

    return dict(label=label, sharpe=sharpe, ann_return=ann_ret, max_dd=max_dd,
                profit_factor=pf, net_rets=net, equity=eq)


def sub_sharpe(net: pd.Series, s: str, e: str) -> float:
    sub = net.loc[s:e]
    if len(sub) < 20 or sub.std() == 0:
        return float("nan")
    return float((sub.mean() / sub.std()) * np.sqrt(TRADING_DAYS))


def signal_corr(sig: pd.Series, tsmom: pd.Series) -> float:
    mask = sig.notna() & tsmom.notna() & (sig.index == tsmom.index.intersection(sig.index))
    idx  = sig.index.intersection(tsmom.index)
    if len(idx) < 60:
        return float("nan")
    return float(sig.loc[idx].corr(tsmom.loc[idx]))


# ── IC Test ────────────────────────────────────────────────────────────────────

def ic_test(signal: pd.Series, close: pd.Series, label: str = "") -> dict[str, Any]:
    """IC = Spearman rank_corr(signal[T], 5d fwd log_ret) on OOS."""
    fwd_ret = np.log(close / close.shift(1)).rolling(FWD_DAYS).sum().shift(-FWD_DAYS)
    idx = signal.index.intersection(fwd_ret.index)
    idx = idx[:-FWD_DAYS]
    sv  = signal.loc[idx].values
    fv  = fwd_ret.loc[idx].values
    mask = np.isfinite(sv) & np.isfinite(fv)
    if mask.sum() < 30:
        return dict(label=label, ic=float("nan"), t_stat=float("nan"), n=0)
    sv, fv = sv[mask], fv[mask]
    ic, _  = stats.spearmanr(sv, fv)
    n      = len(sv)
    t_stat = ic * np.sqrt(n) / np.sqrt(max(1 - ic**2, 1e-10))
    return dict(label=label, ic=float(ic), t_stat=float(t_stat), n=n)


# ── Regime Transition Analysis ─────────────────────────────────────────────────

def transition_analysis(p_bull: pd.Series, close: pd.Series) -> dict[str, Any]:
    """
    Bear→Bull crossings: P_bull_next crosses UP through 0.5.
    Compute mean 5-day log return after crossing vs random days.
    t-stat: is the crossing day special?
    """
    lr         = np.log(close / close.shift(1))
    fwd_5d     = lr.rolling(FWD_DAYS).sum().shift(-FWD_DAYS)
    crossings  = (p_bull > 0.5) & (p_bull.shift(1) <= 0.5)
    cross_dates = p_bull.index[crossings]

    fwd_at_cross = fwd_5d.reindex(cross_dates).dropna()
    fwd_baseline = fwd_5d.dropna()

    if len(fwd_at_cross) < 5:
        return dict(n_crossings=len(cross_dates), mean_cross=float("nan"),
                    mean_base=float("nan"), t_stat=float("nan"))

    t_stat, _ = stats.ttest_ind(fwd_at_cross.values, fwd_baseline.values)

    return dict(
        n_crossings=int(len(cross_dates)),
        mean_cross=float(fwd_at_cross.mean()),
        mean_base=float(fwd_baseline.mean()),
        t_stat=float(t_stat),
        cross_dates=cross_dates,
    )


# ── Walk-Forward (refit HMM each window) ──────────────────────────────────────

def walk_forward(close: pd.Series, feat: pd.DataFrame) -> dict[str, list]:
    """
    3 expanding-window folds, refit HMM each time.
    W1: train 2018-2020, test 2021-2022
    W2: train 2018-2022, test 2023-2024
    W3: train 2018-2023, test 2025-2026
    """
    folds = [
        ("2018-01-01", "2020-12-31", "2021-01-01", "2022-12-31"),
        ("2018-01-01", "2022-12-31", "2023-01-01", "2024-12-31"),
        ("2018-01-01", "2023-12-31", "2025-01-01", "2026-05-14"),
    ]

    sig_labels = ["S1 Raw P_bull", "S2 Prob change", "S3 Regime entry", "S4 TSMOM×HMM"]
    results: dict[str, list] = {lb: [] for lb in sig_labels}

    for i, (tr_s, tr_e, oos_s, oos_e) in enumerate(folds, 1):
        print(f"\n  W{i}: train {tr_s[:4]}–{tr_e[:4]}, test {oos_s[:4]}–{oos_e[:4]}")

        # Build obs arrays
        feat_train = feat.loc[tr_s:tr_e].dropna()
        feat_oos   = feat.loc[oos_s:oos_e].dropna()
        obs_train  = feat_train.values
        obs_oos    = feat_oos.values

        if len(obs_train) < 200 or len(obs_oos) < 30:
            for lb in sig_labels:
                results[lb].append(dict(fold=i, sharpe=float("nan"), max_dd=float("nan")))
            continue

        # Fit HMM on train, get final alpha
        try:
            model_wf = fit_hmm(obs_train)
        except Exception as e:
            print(f"    HMM fit failed: {e}")
            for lb in sig_labels:
                results[lb].append(dict(fold=i, sharpe=float("nan"), max_dd=float("nan")))
            continue

        final_alpha = train_and_get_final_alpha(model_wf, obs_train)

        # Forward algorithm on OOS
        _, p_bull_oos, _ = run_forward(model_wf, obs_oos, alpha_init=final_alpha)
        p_bull_s = pd.Series(p_bull_oos, index=feat_oos.index, name="p_bull")

        # Align with close for OOS period
        close_oos = close.loc[oos_s:oos_e]
        p_bull_aligned = p_bull_s.reindex(close_oos.index).ffill().fillna(0.5)

        # Build signals
        sigs_wf = build_signals(p_bull_aligned, close_oos)
        sigs_wf["TSMOM v3"] = compute_tsmom(close_oos)

        for lb in sig_labels:
            sig = sigs_wf.get(lb, pd.Series(0.0, index=close_oos.index))
            bt  = backtest(close_oos, sig, label=f"W{i}")
            results[lb].append(dict(fold=i, sharpe=bt["sharpe"], max_dd=bt["max_dd"]))
            print(f"    {lb:<18}: Sh={bt['sharpe']:+.2f}")

    return results


# ── Plot ───────────────────────────────────────────────────────────────────────

def plot_results(
    close: pd.Series,
    p_bull: pd.Series,
    all_bts: dict[str, dict],
    trans_info: dict,
    wf_results: dict,
    p_bull_oos: pd.Series,
    save_path: Path,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle(
        "HMM Forward-Algorithm Transition Probabilities — Signals 45–48\n"
        "Causal P(bull_next): forward algorithm, not Viterbi (6.15 fix)",
        fontsize=13, fontweight="bold",
    )
    COL = {
        "S1 Raw P_bull":   "#2c3e50",
        "S2 Prob change":  "#e74c3c",
        "S3 Regime entry": "#27ae60",
        "S4 TSMOM×HMM":    "#8e44ad",
        "TSMOM v3":        "#3498db",
    }

    # ── Panel 1: P_bull_next vs BTC price ─────────────────────────────────────
    ax = axes[0, 0]
    ax2 = ax.twinx()
    c_plot = close.loc[OOS_START:]
    c_norm = (c_plot - c_plot.min()) / (c_plot.max() - c_plot.min() + 1e-8)
    p_plot = p_bull_oos.reindex(c_plot.index).ffill()

    ax.plot(c_norm.index, c_norm.values, color="#e67e22", lw=1.2, alpha=0.7, label="BTC price (norm.)")
    ax2.plot(p_plot.index, p_plot.values, color="#2c3e50", lw=1.5, label="P_bull_next")
    ax2.axhline(0.5, color="gray", lw=0.8, ls="--", alpha=0.6)
    ax2.fill_between(p_plot.index, 0.5, p_plot.values,
                     where=p_plot.values > 0.5, alpha=0.15, color="#27ae60")
    ax2.fill_between(p_plot.index, p_plot.values, 0.5,
                     where=p_plot.values < 0.5, alpha=0.15, color="#e74c3c")
    ax.set_title("Panel 1 — P_bull_next vs BTC Price (OOS 2022–2026)", fontsize=10)
    ax.set_ylabel("Price (normalized)", color="#e67e22")
    ax2.set_ylabel("P(bull at T+1 | obs_0:T)", color="#2c3e50")
    ax2.set_ylim(-0.05, 1.05)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)

    # ── Panel 2: Equity curves ─────────────────────────────────────────────────
    ax = axes[0, 1]
    for label, bt in all_bts.items():
        eq = bt["equity"]
        ls = "--" if label == "TSMOM v3" else "-"
        lw = 1.5 if label == "TSMOM v3" else 2.0
        ax.plot(eq.index, eq.values, color=COL.get(label, "gray"),
                ls=ls, lw=lw, label=f"{label} (Sh={bt['sharpe']:.2f})")
    ax.axhline(1.0, color="gray", lw=0.7, ls=":")
    ax.set_title("Panel 2 — Equity Curves (OOS: 2022–2026)", fontsize=10)
    ax.set_ylabel("Cumulative Return (base 1.0)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # ── Panel 3: Mean return by P_bull_next decile ────────────────────────────
    ax = axes[1, 0]
    # Use full OOS period
    common_idx = p_bull_oos.dropna().index.intersection(close.index)
    fwd_5d = (np.log(close / close.shift(1)).rolling(FWD_DAYS).sum().shift(-FWD_DAYS)
              .reindex(common_idx))
    pb     = p_bull_oos.reindex(common_idx)

    valid  = fwd_5d.notna() & pb.notna()
    pb_v   = pb[valid].values
    fv_v   = fwd_5d[valid].values

    n_deciles = 10
    decile_labels = [f"D{i+1}" for i in range(n_deciles)]
    decile_means  = []
    decile_tstats = []

    for d in range(n_deciles):
        lo, hi = np.percentile(pb_v, [d * 10, (d + 1) * 10])
        mask = (pb_v >= lo) & (pb_v <= hi)
        if mask.sum() < 5:
            decile_means.append(0.0)
            decile_tstats.append(0.0)
            continue
        rets  = fv_v[mask]
        dm    = float(np.mean(rets))
        dt, _ = stats.ttest_1samp(rets, 0)
        decile_means.append(dm * 100)
        decile_tstats.append(float(dt))

    bar_colors = ["#27ae60" if t > 1.5 else ("#e74c3c" if t < -1.5 else "#95a5a6")
                  for t in decile_tstats]
    ax.bar(range(n_deciles), decile_means, color=bar_colors, alpha=0.85)
    ax.axhline(0, color="gray", lw=0.7)
    for i, (m, t) in enumerate(zip(decile_means, decile_tstats)):
        ax.text(i, m + np.sign(m) * 0.05,
                f"{t:.1f}", ha="center", va="bottom" if m >= 0 else "top", fontsize=7)
    ax.set_xticks(range(n_deciles))
    ax.set_xticklabels(decile_labels, fontsize=8)
    ax.set_xlabel("P_bull_next decile (D1=low, D10=high)")
    ax.set_ylabel("Mean 5d log-return (%)")
    ax.set_title("Panel 3 — Mean 5d Return by P_bull_next Decile\n"
                 "(green=t>1.5 · red=t<-1.5)", fontsize=10)
    ax.grid(alpha=0.3, axis="y")

    # ── Panel 4: Walk-forward Sharpe ──────────────────────────────────────────
    ax = axes[1, 1]
    fold_lbls  = ["W1\n2021-22", "W2\n2023-24", "W3\n2025-26"]
    sig_labels = list(wf_results.keys())
    x = np.arange(3)
    n_sigs = len(sig_labels)
    width  = 0.2

    for i, lb in enumerate(sig_labels):
        wf = wf_results[lb]
        sharpes = [r.get("sharpe", float("nan")) for r in wf]
        sharpes = [s if not np.isnan(s) else 0.0 for s in sharpes]
        offset  = (i - n_sigs / 2.0 + 0.5) * width
        ax.bar(x + offset, sharpes, width=width, color=COL.get(lb, "gray"),
               alpha=0.85, label=lb)

    ax.axhline(0, color="gray", lw=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(fold_lbls, fontsize=9)
    ax.set_ylabel("OOS Sharpe")
    ax.set_title("Panel 4 — Walk-Forward Sharpe (3 windows, HMM refit per window)", fontsize=10)
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved → {save_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 65)
    print("HMM FORWARD PROBABILITIES — SIGNALS 45–48")
    print("Causal: forward algorithm, not Viterbi")
    print("=" * 65)

    # ── 1. Data & Features ────────────────────────────────────────────────────
    close = download_data()
    feat  = build_features(close)
    print(f"  Features shape: {feat.dropna().shape}  "
          f"(NaN rows dropped: {feat.isna().any(axis=1).sum()})")

    # ── 2. Fit HMM on train period ────────────────────────────────────────────
    print(f"\nFitting HMM on train ({DATA_START} → {TRAIN_END})...")
    feat_train = feat.loc[DATA_START:TRAIN_END].dropna()
    obs_train  = feat_train.values
    model      = fit_hmm(obs_train)
    bs         = bull_state_idx(model)
    print(f"  Log-likelihood: {model.score(obs_train):.1f}")
    print(f"  BULL state: {bs}  (mean log_ret={model.means_[bs, 0]:.5f})")
    bear = 1 - bs
    print(f"  BEAR state: {bear}  (mean log_ret={model.means_[bear, 0]:.5f})")
    print(f"  Transition matrix:\n    BULL→BULL={model.transmat_[bs, bs]:.3f}  "
          f"BULL→BEAR={model.transmat_[bs, bear]:.3f}")
    print(f"    BEAR→BULL={model.transmat_[bear, bs]:.3f}  "
          f"BEAR→BEAR={model.transmat_[bear, bear]:.3f}")

    # ── 3. Forward algorithm: through train, then continue on OOS ─────────────
    print(f"\nRunning forward algorithm through training data...")
    final_alpha = train_and_get_final_alpha(model, obs_train)
    print(f"  End-of-train alpha: BULL={final_alpha[bs]:.3f}  BEAR={final_alpha[bear]:.3f}")

    # OOS forward pass (causal, starting from final training alpha)
    print(f"\nRunning forward algorithm on OOS ({OOS_START} → {DATA_END})...")
    feat_oos  = feat.loc[OOS_START:DATA_END].dropna()
    obs_oos   = feat_oos.values
    _, p_bull_oos_arr, _ = run_forward(model, obs_oos, alpha_init=final_alpha)
    p_bull_oos = pd.Series(p_bull_oos_arr, index=feat_oos.index, name="p_bull_next")

    # Align to full close index (reindex + ffill for any missing days)
    p_bull_aligned = p_bull_oos.reindex(close.loc[OOS_START:].index).ffill().fillna(0.5)
    print(f"  P_bull_next: mean={p_bull_aligned.mean():.3f}  "
          f"std={p_bull_aligned.std():.3f}  "
          f"min={p_bull_aligned.min():.3f}  max={p_bull_aligned.max():.3f}")

    # ── 4. Build signals ──────────────────────────────────────────────────────
    print("\nBuilding signals...")
    close_oos = close.loc[OOS_START:]
    signals   = build_signals(p_bull_aligned, close_oos)
    tsmom_sig = compute_tsmom(close_oos)
    signals["TSMOM v3"] = tsmom_sig

    # ── 5. OOS backtests ──────────────────────────────────────────────────────
    print(f"\nOOS backtests ({OOS_START} → {DATA_END})...")
    all_bts: dict[str, dict] = {}
    for label, sig in signals.items():
        bt = backtest(close_oos, sig, label=label)
        all_bts[label] = bt
        pf_s = f"{bt['profit_factor']:.2f}" if not np.isinf(bt["profit_factor"]) else "∞"
        print(f"  {label:<20}: Sh={bt['sharpe']:+.2f}  MaxDD={bt['max_dd']:.1%}  PF={pf_s}")

    # Sub-period Sharpe
    print(f"\n  {'Signal':<20}  {'2022':>6}  {'2023':>6}  {'2024+':>6}")
    for label, bt in all_bts.items():
        s22 = sub_sharpe(bt["net_rets"], "2022-01-01", "2022-12-31")
        s23 = sub_sharpe(bt["net_rets"], "2023-01-01", "2023-12-31")
        s24 = sub_sharpe(bt["net_rets"], "2024-01-01", DATA_END)
        print(f"  {label:<20}  {s22:>+6.2f}  {s23:>+6.2f}  {s24:>+6.2f}")

    # ── 6. IC Test ────────────────────────────────────────────────────────────
    print(f"\nIC tests (P_bull_next → {FWD_DAYS}-day forward return, OOS period):")
    ic_results: dict[str, dict] = {}
    for label, sig in {lb: v for lb, v in signals.items() if lb != "TSMOM v3"}.items():
        r = ic_test(sig.loc[OOS_START:], close_oos, label)
        ic_results[label] = r
        flag = " ★" if r["t_stat"] > 2.0 else (" ·" if r["t_stat"] > 1.5 else "  ")
        print(f"  {label:<20}: IC={r['ic']:.4f}  t={r['t_stat']:.2f}{flag}  n={r['n']}")

    # Direct IC on P_bull_next itself
    r_raw = ic_test(p_bull_aligned, close_oos, "P_bull_next (raw)")
    flag  = " ★" if r_raw["t_stat"] > 2.0 else (" ·" if r_raw["t_stat"] > 1.5 else "  ")
    print(f"  {'P_bull_next (raw)':<20}: IC={r_raw['ic']:.4f}  "
          f"t={r_raw['t_stat']:.2f}{flag}  n={r_raw['n']}")

    # ── 7. Regime transition analysis ─────────────────────────────────────────
    print("\nRegime transition analysis (bear→bull crossing at P_bull=0.5):")
    trans = transition_analysis(p_bull_aligned, close_oos)
    print(f"  Crossings found   : {trans['n_crossings']}")
    if not np.isnan(trans["t_stat"]):
        print(f"  Mean fwd 5d return at crossing : {trans['mean_cross']*100:+.3f}%")
        print(f"  Mean fwd 5d return baseline    : {trans['mean_base']*100:+.3f}%")
        print(f"  t-stat vs baseline             : {trans['t_stat']:+.2f}  "
              f"({'★ crossing special' if abs(trans['t_stat']) > 2.0 else 'no significant lift'})")

    # ── 8. Correlation with TSMOM ─────────────────────────────────────────────
    print("\nCorrelation with TSMOM v3:")
    for label, sig in {lb: v for lb, v in signals.items() if lb != "TSMOM v3"}.items():
        idx = sig.index.intersection(tsmom_sig.index)
        if len(idx) > 60:
            c = float(sig.loc[idx].corr(tsmom_sig.loc[idx]))
            print(f"  {label:<20}: {c:+.3f}  "
                  f"{'→ new info' if c < 0.85 else '→ similar to TSMOM'}")

    # ── 9. Walk-forward (refit HMM) ───────────────────────────────────────────
    print("\nWalk-forward (3 windows, HMM refit per window):")
    wf_results = walk_forward(close, feat)

    # ── 10. Results table ─────────────────────────────────────────────────────
    print(f"\n{'═'*80}")
    print("RESULTS TABLE  (OOS 2022-2026, BTC only, weekly rebalance)")
    print(f"{'─'*80}")
    print(f"  {'Signal':<20}  {'Sharpe':>6}  {'MaxDD':>7}  {'ProfFt':>7}  {'corrTSMOM':>10}")
    print(f"  {'-'*20}  {'-'*6}  {'-'*7}  {'-'*7}  {'-'*10}")
    for label, bt in all_bts.items():
        pf   = bt["profit_factor"]
        pf_s = f"{pf:.2f}" if not np.isinf(pf) else "∞"
        idx  = bt["net_rets"].index.intersection(tsmom_sig.index)
        c    = (float(bt["net_rets"].loc[idx].corr(
                    backtest(close_oos, tsmom_sig)["net_rets"].loc[idx]))
                if len(idx) > 60 else float("nan"))
        c_s  = f"{c:.3f}" if not np.isnan(c) else "  n/a"
        bm   = " ← baseline" if label == "TSMOM v3" else ""
        print(f"  {label:<20}  {bt['sharpe']:>+6.2f}  {bt['max_dd']:>7.1%}  "
              f"{pf_s:>7}  {c_s:>10}{bm}")
    print(f"  (TSMOM v3 baseline OOS Sharpe historical: 1.33)")
    print(f"{'═'*80}")

    # ── 11. Plot ──────────────────────────────────────────────────────────────
    plot_results(
        close, p_bull_aligned, all_bts, trans, wf_results, p_bull_aligned,
        OUT_DIR / "feasibility_results.png",
    )

    # ── 12. Verdict ───────────────────────────────────────────────────────────
    sh_s4      = all_bts["S4 TSMOM×HMM"]["sharpe"]
    sh_s3      = all_bts["S3 Regime entry"]["sharpe"]
    sh_tsmom   = all_bts["TSMOM v3"]["sharpe"]
    ic_s1_t    = r_raw["t_stat"]
    wf_s4_pos  = sum(1 for r in wf_results["S4 TSMOM×HMM"] if not np.isnan(r["sharpe"]) and r["sharpe"] > 0)

    idx4 = all_bts["S4 TSMOM×HMM"]["net_rets"].index.intersection(tsmom_sig.index)
    corr_s4 = (float(all_bts["S4 TSMOM×HMM"]["net_rets"].loc[idx4].corr(
                   backtest(close_oos, tsmom_sig)["net_rets"].loc[idx4]))
               if len(idx4) > 60 else float("nan"))

    deploy_s4 = sh_s4 > 1.5 and wf_s4_pos >= 2
    promising = sh_s3 > 0.8 or (ic_s1_t > 1.5)

    print(f"\n{'═'*65}")
    print("VERDICT — HMM Forward Probabilities (Signals 45–48)")
    print(f"{'═'*65}")
    print(f"  P_bull_next IC t-stat : {ic_s1_t:+.2f}  "
          f"{'★ predictive' if ic_s1_t > 2.0 else ('· marginal' if ic_s1_t > 1.5 else 'not significant')}")
    print(f"  S4 (TSMOM×HMM) Sharpe : {sh_s4:+.2f}  (need > 1.5, baseline {sh_tsmom:.2f})")
    print(f"  S4 walk-forward       : {wf_s4_pos}/3  (need ≥ 2)")
    print(f"  S3 regime entry Sh    : {sh_s3:+.2f}  (need > 0.8)")
    print(f"  Crossing t-stat       : {trans['t_stat']:+.2f}  "
          f"({'★ crossings are special' if abs(trans.get('t_stat', 0)) > 2.0 else 'no lift'})")

    if deploy_s4:
        print(f"\n→ DEPLOY: S4 (TSMOM×HMM) as TSMOM overlay.")
        print(f"  Sh={sh_s4:.2f} > 1.5, WF {wf_s4_pos}/3.")
    elif promising:
        reasons = []
        if sh_s3 > 0.8:
            reasons.append(f"S3 regime entry Sh={sh_s3:.2f} > 0.8")
        if ic_s1_t > 1.5:
            reasons.append(f"IC t={ic_s1_t:.2f} > 1.5 (P_bull is predictive)")
        print(f"\n→ PROMISING: {'; '.join(reasons)}")
        print(f"  Sharpe doesn't meet DEPLOY threshold but signal is real.")
        print(f"  Consider: S3 as a TSMOM pre-filter (skip new entries in bear regime).")
    else:
        print(f"\n→ SKIP — IC not significant (t={ic_s1_t:.2f} < 1.5) OR")
        print(f"  forward probabilities don't improve over TSMOM baseline.")
        print(f"  Core finding: HMM identifies regime structure but transitions")
        print(f"  at daily frequency are too noisy to time entries profitably.")
        print(f"  Signal 45–48: SKIP")

    print(f"{'═'*65}")


if __name__ == "__main__":
    main()
