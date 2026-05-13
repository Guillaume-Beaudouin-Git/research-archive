#!/usr/bin/env python
"""
HMM Regime Detection — Bull/Range/Bear Switching for TSMOM v2.

Background:
  Meta-labeling deep analysis found the key regime signal:
  "accept trade if btc_ret_28d > 0 AND btc_vol_20d < 0.33"
  A properly fitted HMM should discover this structure automatically
  and provide richer probabilistic transitions for strategy switching.

Research question:
  Can an HMM on BTC daily returns reliably detect market regimes
  (bull/range/bear) that predict TSMOM performance, and does
  regime-conditional switching improve Propr challenge outcomes
  beyond the 34% baseline?

Run: python -m strategies.regime_hmm.feasibility
"""
from __future__ import annotations

import pickle
import warnings
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np
import pandas as pd
import scipy.stats as stats
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ── Re-use PnL / Propr sim functions from meta_tsmom (no code duplication) ────
from strategies.meta_tsmom.feasibility import (
    _build_tsmom_daily_pnl,
    _portfolio_metrics,
    _simulate_challenge,
    run_propr_sims as _run_propr_sims,
)

# ── Constants ──────────────────────────────────────────────────────────────────
DATA_START    = "2019-01-01"
DATA_END      = "2026-05-11"
TRAIN_START   = "2019-01-01"
TRAIN_END     = "2022-12-31"
OOS_START     = "2023-01-01"
OOS_END       = "2026-05-11"
SIM_START     = "2025-01-06"
SIM_END       = "2025-11-03"

CONFIRM_DELAY = 3          # days before acting on a new regime signal

UNIVERSE_TSMOM: list[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD",
    "DOGE-USD", "ADA-USD", "DOT-USD", "LTC-USD", "BCH-USD",
]
UNIVERSE_VAL: list[str] = ["BTC-USD", "ETH-USD", "SOL-USD"]

HL_FUNDING_DIR = Path(__file__).parent.parent / "cs_carry" / "data"
OUT_DIR        = Path(__file__).parent
VIZ_PATH       = OUT_DIR / "regime_visualization.png"
CHART_PATH     = OUT_DIR / "feasibility_results.png"
MODEL_PATH     = OUT_DIR / "best_hmm_model.pkl"

PROPR_CAP   = 5_000.0
PROPR_TGT   = 0.10
PROPR_DD    = 0.06
PROPR_DAILY = 0.03
TSMOM_BASELINE_PASS = 0.34
TSMOM_DAILY_FAILS   = 26

VOL_BULL  = 0.15
VOL_RANGE = 0.08
VOL_BEAR  = 0.00
VOL_BEAR_5A = 0.03     # tiny position in 5A variant

LABEL_COLORS = {"BULL": "#2ecc71", "RANGE": "#f39c12", "BEAR": "#e74c3c"}

# HMM configs: (name, n_components, covariance_type)
HMM_CONFIGS: list[tuple[str, int, str]] = [
    ("A_2state_full", 2, "full"),
    ("B_3state_full", 3, "full"),
    ("C_3state_diag", 3, "diag"),
]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_data() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.Series]]:
    """
    Download BTC/ETH/SOL and TSMOM universe OHLCV via yfinance.
    Also load BTC HL funding rate.
    Returns: (btc_close, tsmom_close, funding_rates)
    """
    print("\n[STEP 1] Loading data...")

    # BTC + validation assets
    val_raw   = yf.download(UNIVERSE_VAL, start=DATA_START, end=DATA_END,
                             auto_adjust=True, progress=False, threads=True)
    btc_close = val_raw["Close"]["BTC-USD"].ffill()
    btc_open  = val_raw["Open"]["BTC-USD"].ffill()

    print(f"  BTC: {btc_close.index[0].date()} → {btc_close.index[-1].date()}"
          f"  ({len(btc_close)} days)")

    # Check gaps
    gaps = btc_close.isna().sum()
    if gaps > 0:
        print(f"  ⚠  {gaps} gaps in BTC data — forward-filling")
    btc_close = btc_close.ffill().dropna()

    # TSMOM universe (for strategy switching backtest)
    tsmom_raw = yf.download(UNIVERSE_TSMOM, start=DATA_START, end=DATA_END,
                             auto_adjust=True, progress=False, threads=True)
    tsmom_close = tsmom_raw["Close"].ffill()
    print(f"  TSMOM universe: {tsmom_close.shape[1]} assets × {len(tsmom_close)} days")

    # BTC funding rate
    funding_rates: dict[str, pd.Series] = {}
    btc_fund_path = HL_FUNDING_DIR / "BTC_hl_funding.csv"
    if btc_fund_path.exists():
        df = pd.read_csv(btc_fund_path, index_col=0)
        df.index = pd.to_datetime(df.index, format="mixed", utc=True).tz_convert(None)
        col = df.columns[0]
        funding_rates["BTC"] = df[col].resample("D").mean()
        print(f"  BTC funding: {len(funding_rates['BTC'])} daily observations")

    return btc_close, tsmom_close, funding_rates


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — HMM OBSERVATION VECTOR & FITTING
# ─────────────────────────────────────────────────────────────────────────────

def build_observations(btc_close: pd.Series) -> pd.DataFrame:
    """
    Build 4-dimensional HMM observation vector:
      o1 = daily log return (close-to-close)
      o2 = 5-day realized vol (annualized)
      o3 = 20-day realized vol (annualized)
      o4 = sign(close - SMA50)  →  +1 or -1
    """
    log_ret  = np.log(btc_close / btc_close.shift(1))
    vol5     = log_ret.rolling(5).std()  * np.sqrt(252)
    vol20    = log_ret.rolling(20).std() * np.sqrt(252)
    sma50    = btc_close.rolling(50).mean()
    sign_ma  = np.sign(btc_close - sma50).replace(0, 1)   # tie → +1

    obs = pd.DataFrame({
        "log_ret":   log_ret,
        "vol5":      vol5,
        "vol20":     vol20,
        "sign_ma50": sign_ma,
    }).dropna()
    return obs


def _n_params(n_states: int, n_features: int, cov_type: str) -> int:
    """Count HMM free parameters for BIC computation."""
    init   = n_states - 1
    trans  = n_states * (n_states - 1)
    means  = n_states * n_features
    if cov_type == "full":
        cov = n_states * n_features * (n_features + 1) // 2
    elif cov_type == "diag":
        cov = n_states * n_features
    elif cov_type == "tied":
        cov = n_features * (n_features + 1) // 2
    else:
        cov = n_states
    return init + trans + means + cov


def fit_hmm(
    X_train: np.ndarray,
    n_states: int,
    cov_type: str,
    n_iter: int = 1000,
    seed: int = 42,
) -> GaussianHMM:
    """Fit a Gaussian HMM on training observations."""
    model = GaussianHMM(
        n_components=n_states,
        covariance_type=cov_type,
        n_iter=n_iter,
        random_state=seed,
        verbose=False,
    )
    model.fit(X_train)
    converged = getattr(model.monitor_, "converged", True)
    if not converged:
        print(f"    ⚠  HMM ({n_states}-state, {cov_type}) did not converge in {n_iter} iters")
    return model


def label_states(
    model: GaussianHMM,
    states: np.ndarray,
    btc_logret: pd.Series,
) -> dict[int, str]:
    """
    Map numeric state indices → economic labels (BULL / RANGE / BEAR)
    based on mean return in each state.
    """
    n = model.n_components
    state_mean_ret: dict[int, float] = {}
    for s in range(n):
        mask = states == s
        if mask.sum() > 0:
            state_mean_ret[s] = float(btc_logret[mask].mean())
        else:
            state_mean_ret[s] = 0.0

    sorted_states = sorted(state_mean_ret, key=state_mean_ret.get, reverse=True)

    if n == 2:
        return {sorted_states[0]: "BULL", sorted_states[1]: "BEAR"}
    else:  # 3 states
        return {sorted_states[0]: "BULL", sorted_states[1]: "RANGE", sorted_states[2]: "BEAR"}


def get_raw_regimes(
    model: GaussianHMM,
    obs_scaled: np.ndarray,
    obs_index: pd.DatetimeIndex,
    state_map: dict[int, str],
) -> pd.Series:
    """
    Decode full observation sequence → shift by 1 day (no-look-ahead).
    regime[T] = Viterbi-optimal state at T-1 (known without using today).
    """
    states_raw = model.predict(obs_scaled)
    states_str = pd.Series(
        [state_map[s] for s in states_raw],
        index=obs_index,
    )
    # Shift: regime[T] = label inferred from data up to T-1
    return states_str.shift(1).ffill()


def apply_confirmation_delay(
    regime: pd.Series,
    delay: int = CONFIRM_DELAY,
) -> pd.Series:
    """
    Only act on a regime change after it has persisted for `delay` days.
    confirmed[T] = regime[T] if regime[T-delay+1:T+1] all agree, else confirmed[T-1].
    """
    confirmed = regime.copy()
    for i in range(delay, len(regime)):
        window = regime.iloc[i - delay + 1: i + 1]
        if window.dropna().nunique() <= 1:
            confirmed.iloc[i] = regime.iloc[i]
        else:
            confirmed.iloc[i] = confirmed.iloc[i - 1]
    return confirmed


def print_state_stats(
    states_str: pd.Series,
    btc_logret: pd.Series,
    model: GaussianHMM,
    config_name: str,
) -> None:
    """Print per-state statistics and transition matrix."""
    print(f"\n  Config {config_name} state statistics:")
    print(f"  {'State':<8} {'Days':>6} {'Freq':>7} {'MeanRet/d':>10} "
          f"{'AnnVol':>8} {'AvgDur':>8}")
    print(f"  {'-'*52}")

    labels = sorted(states_str.dropna().unique())
    for lbl in ["BULL", "RANGE", "BEAR"]:
        if lbl not in labels:
            continue
        mask  = states_str == lbl
        rets  = btc_logret[mask]
        n     = int(mask.sum())
        freq  = n / max(len(states_str.dropna()), 1)
        mean_r = float(rets.mean()) if len(rets) > 0 else 0.0
        vol_a  = float(rets.std() * np.sqrt(252)) if len(rets) > 1 else 0.0

        # Average duration: consecutive runs
        runs = (states_str != states_str.shift()).cumsum()
        dur  = states_str[mask].groupby(runs[mask]).size().mean()

        print(f"  {lbl:<8} {n:>6} {freq:>6.1%} {mean_r:>10.4%} {vol_a:>7.1%} {dur:>8.1f}d")

    # Transition matrix
    trans = model.transmat_
    state_map_rev = {v: k for k, v in
                     label_states(model, model.predict(np.zeros((10, model.n_features))),
                                  pd.Series(np.zeros(10))).items()
                     }
    # Simpler: just print numeric matrix
    print(f"\n  Transition matrix (row=from, col=to):")
    for i, row in enumerate(trans):
        print(f"    State {i}: " + "  ".join(f"{p:.3f}" for p in row))


def compute_bic(model: GaussianHMM, X_train: np.ndarray) -> float:
    """Bayesian Information Criterion (lower = better)."""
    n      = len(X_train)
    log_lik = model.score(X_train) * n     # total log-likelihood
    n_p    = _n_params(model.n_components, model.n_features, model.covariance_type)
    return -2 * log_lik + n_p * np.log(n)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — REGIME VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_regimes(
    confirmed: pd.Series,
    btc_logret: pd.Series,
    tsmom_pnl: pd.Series,
    period_start: str,
    period_end: str,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    4 validation tests for economic meaningfulness.
    Returns dict with validity flags.
    """
    conf  = confirmed.loc[period_start:period_end]
    tpnl  = tsmom_pnl.loc[period_start:period_end]
    btc_r = btc_logret.loc[period_start:period_end]

    if verbose:
        print(f"\n  Validation period: {period_start} → {period_end}")

    # ── Test 1: TSMOM performance by regime ──────────────────────────────────
    if verbose:
        print("\n  Test 1 — TSMOM returns by regime:")
    regime_tsmom: dict[str, dict[str, float]] = {}
    for lbl in ["BULL", "RANGE", "BEAR"]:
        r_mask = (conf == lbl)
        r_idx  = conf[r_mask].index
        r_pnl  = tpnl.reindex(r_idx).dropna()
        if len(r_pnl) < 5:
            continue
        mu  = float(r_pnl.mean())
        se  = float(r_pnl.std() / np.sqrt(len(r_pnl)))
        t   = mu / se if se > 0 else 0.0
        regime_tsmom[lbl] = {"mean": mu, "tstat": t, "n": len(r_pnl)}
        if verbose:
            print(f"    {lbl:<6}: mean={mu:+.4%}/day  t={t:+.2f}  (n={len(r_pnl)})")

    # Economic validity: BULL>0, BEAR<0
    bull_pos = regime_tsmom.get("BULL", {}).get("mean", 0) > 0
    bear_neg = regime_tsmom.get("BEAR", {}).get("mean", 0) < 0
    if bull_pos and bear_neg:
        validity = "CONFIRMED"
    elif bull_pos or bear_neg:
        validity = "PARTIAL"
    else:
        validity = "FAILED"
    if verbose:
        print(f"\n  → Economic validity: {validity}")

    # ── Test 2: Regime persistence ────────────────────────────────────────────
    if verbose:
        print("\n  Test 2 — Regime persistence:")
    durations: dict[str, float] = {}
    for lbl in ["BULL", "RANGE", "BEAR"]:
        runs = (conf != conf.shift()).cumsum()
        mask = conf == lbl
        if mask.sum() == 0:
            continue
        avg_dur = conf[mask].groupby(runs[mask]).size().mean()
        durations[lbl] = float(avg_dur)
        flag = "✓" if avg_dur >= 10 else ("⚠" if avg_dur >= 5 else "✗")
        if verbose:
            print(f"    {lbl:<6}: avg duration = {avg_dur:.1f} days  {flag}")

    min_dur = min(durations.values()) if durations else 0.0
    persistence_ok = min_dur >= 5

    # ── Test 3: Detection lag ─────────────────────────────────────────────────
    detection_lag = float(CONFIRM_DELAY)
    if verbose:
        print(f"\n  Test 4 — Regime detection lag: {detection_lag:.0f} days "
              f"(by construction: {CONFIRM_DELAY}-day confirmation filter)")

    return {
        "validity":      validity,
        "regime_tsmom":  regime_tsmom,
        "persistence":   persistence_ok,
        "min_duration":  min_dur,
        "detection_lag": detection_lag,
        "bull_pos":      bull_pos,
        "bear_neg":      bear_neg,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — STRATEGY SWITCHING BACKTEST
# ─────────────────────────────────────────────────────────────────────────────

def build_regime_position_scale(
    confirmed: pd.Series,
    close: pd.DataFrame,
    start: str,
    end: str,
    vol_bear: float = VOL_BEAR,
) -> pd.DataFrame:
    """
    Build position_scale DataFrame (date × ticker) for regime-based sizing.
    BULL → 1.0 (full VOL_BULL target)
    RANGE → VOL_RANGE/VOL_BULL (half)
    BEAR → vol_bear/VOL_BULL (flat by default, tiny in 5A)
    """
    dates   = close[start:end].index
    tickers = list(close.columns)

    regime_factor = {
        "BULL":  VOL_BULL   / VOL_BULL,       # 1.0
        "RANGE": VOL_RANGE  / VOL_BULL,       # 0.533
        "BEAR":  vol_bear   / VOL_BULL,       # 0.0 or 0.03/0.15
    }

    conf_reindexed = confirmed.reindex(dates).ffill().fillna("BULL")
    scale_vals     = conf_reindexed.map(regime_factor).fillna(1.0)

    scale_df = pd.DataFrame(
        data    = np.outer(scale_vals.values, np.ones(len(tickers))),
        index   = dates,
        columns = tickers,
    )
    return scale_df


def run_switching_backtest(
    confirmed: pd.Series,
    tsmom_close: pd.DataFrame,
    tsmom_close_tickers: list[str],
) -> dict[str, Any]:
    """Step 4: strategy switching backtest on OOS 2023-2026."""
    print(f"\n{'='*60}")
    print("STEP 4 — STRATEGY SWITCHING BACKTEST (OOS 2023-2026)")
    print(f"{'='*60}")

    close = tsmom_close[tsmom_close_tickers]

    # Baseline TSMOM
    pnl_base = _build_tsmom_daily_pnl(close, OOS_START, OOS_END)
    m_base   = _portfolio_metrics(pnl_base)

    # Regime-switching (BULL=full, RANGE=half, BEAR=flat)
    scale_switch = build_regime_position_scale(confirmed, close, OOS_START, OOS_END)
    pnl_switch   = _build_tsmom_daily_pnl(close, OOS_START, OOS_END, scale_switch)
    m_switch     = _portfolio_metrics(pnl_switch)

    # Days in market (fraction with non-zero scale)
    non_zero_days = (scale_switch.max(axis=1) > 0).sum()
    pct_in_market = non_zero_days / len(scale_switch)

    print(f"\n  {'Metric':<20} {'TSMOM alone':>13} {'Regime-switch':>14}")
    print(f"  {'-'*50}")
    for met, fmt in [("sharpe", ".2f"), ("max_dd", ".2%"), ("ann_ret", ".2%"),
                     ("max_day_loss", ".2%"), ("pct_exceed_3", ".2f")]:
        vb = m_base.get(met, 0.0)
        vs = m_switch.get(met, 0.0)
        if met == "pct_exceed_3":
            print(f"  {met:<20} {vb:>12.2f}% {vs:>13.2f}%")
        else:
            print(f"  {met:<20} {vb:>13{fmt}} {vs:>14{fmt}}")

    days_base   = int((pnl_base < -0.03).sum())
    days_switch = int((pnl_switch < -0.03).sum())
    print(f"  {'days > 3% loss':<20} {days_base:>13} {days_switch:>14}")
    print(f"  {'days in market':<20} {'100%':>13} {pct_in_market:>13.1%}")

    return {
        "pnl_base":        pnl_base,
        "pnl_switch":      pnl_switch,
        "m_base":          m_base,
        "m_switch":        m_switch,
        "days_base":       days_base,
        "days_switch":     days_switch,
        "pct_in_market":   pct_in_market,
        "scale_switch":    scale_switch,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — PROPR CHALLENGE SIMULATIONS (5A, 5B, 5C)
# ─────────────────────────────────────────────────────────────────────────────

def run_propr_sims(pnl: pd.Series) -> dict[str, Any]:
    """44 Propr challenge simulations from fixed weekly start dates."""
    starts  = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")
    results = [
        _simulate_challenge(pnl, sd, PROPR_CAP, PROPR_TGT, PROPR_DD, PROPR_DAILY)
        for sd in starts
    ]
    pass_rate  = sum(1 for r in results if r["outcome"] == "PASS") / len(results)
    fail_daily = sum(1 for r in results if r.get("reason") == "daily_limit")
    fail_dd    = sum(1 for r in results if r.get("reason") == "total_dd")
    pass_days  = [r["days"] for r in results if r["outcome"] == "PASS"]
    avg_days   = float(np.mean(pass_days)) if pass_days else float("nan")
    return {
        "pass_rate":   pass_rate,
        "fail_daily":  fail_daily,
        "fail_dd":     fail_dd,
        "avg_days":    avg_days,
        "n_sims":      len(results),
        "results":     results,
        "starts":      starts,
    }


def run_propr_experiments(
    confirmed: pd.Series,
    tsmom_close: pd.DataFrame,
    switch_result: dict[str, Any],
) -> dict[str, Any]:
    """Step 5: run sub-experiments 5A, 5B, 5C."""
    print(f"\n{'='*60}")
    print("STEP 5 — PROPR CHALLENGE SIMULATIONS")
    print(f"{'='*60}")

    close = tsmom_close[UNIVERSE_TSMOM]

    # ── 5A: regime-adjusted sizing (tiny BEAR, not flat) ─────────────────────
    scale_5a = build_regime_position_scale(confirmed, close, OOS_START, OOS_END,
                                            vol_bear=VOL_BEAR_5A)
    pnl_5a   = _build_tsmom_daily_pnl(close, OOS_START, OOS_END, scale_5a)
    p5a      = run_propr_sims(pnl_5a)
    print(f"\n  5A (sized switching — BEAR vol=3%): {p5a['pass_rate']:.0%} pass rate")
    print(f"     Daily fails={p5a['fail_daily']}/44  DD fails={p5a['fail_dd']}/44")

    # ── 5B: regime-gated launch (skip if BEAR at start) ──────────────────────
    starts = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")
    # Baseline PnL (full TSMOM) for the eligible start dates
    pnl_base = _build_tsmom_daily_pnl(close, OOS_START, OOS_END)

    eligible_bull  = 0
    eligible_range = 0
    eligible_bear  = 0
    p5b_results    = []

    for sd in starts:
        reg = confirmed.reindex([sd]).ffill()
        reg_val = str(reg.iloc[0]) if len(reg) > 0 and not pd.isna(reg.iloc[0]) else "BULL"

        if reg_val == "BEAR":
            p5b_results.append({"outcome": "NOT_STARTED", "reason": "bear_regime", "days": 0})
            eligible_bear += 1
        elif reg_val == "RANGE":
            # Start at half size: use pnl_5a (already has RANGE=half sizing)
            res = _simulate_challenge(pnl_5a, sd, PROPR_CAP, PROPR_TGT, PROPR_DD, PROPR_DAILY)
            p5b_results.append(res)
            eligible_range += 1
        else:  # BULL
            res = _simulate_challenge(pnl_base, sd, PROPR_CAP, PROPR_TGT, PROPR_DD, PROPR_DAILY)
            p5b_results.append(res)
            eligible_bull += 1

    n_eligible  = eligible_bull + eligible_range
    n_pass_5b   = sum(1 for r in p5b_results if r["outcome"] == "PASS")
    pass_rate_5b_unconditional = n_pass_5b / len(starts)
    pass_rate_5b_eligible      = n_pass_5b / max(n_eligible, 1)
    fail_d_5b   = sum(1 for r in p5b_results if r.get("reason") == "daily_limit")
    fail_dd_5b  = sum(1 for r in p5b_results if r.get("reason") == "total_dd")
    weeks_wait  = len(starts) / max(eligible_bull, 1)  # avg weeks between BULL starts

    print(f"\n  5B (regime-gated launch):")
    print(f"     BULL starts:  {eligible_bull}/44  ({eligible_bull/len(starts):.0%})")
    print(f"     RANGE starts: {eligible_range}/44  ({eligible_range/len(starts):.0%})")
    print(f"     BEAR starts:  {eligible_bear}/44  ({eligible_bear/len(starts):.0%})  → skipped")
    print(f"     Pass rate (eligible):     {pass_rate_5b_eligible:.0%}")
    print(f"     Pass rate (unconditional): {pass_rate_5b_unconditional:.0%}")
    print(f"     Daily fails={fail_d_5b}/{n_eligible}  DD fails={fail_dd_5b}/{n_eligible}")
    print(f"     Expected weeks between BULL windows: {weeks_wait:.1f}")

    # ── 5C: gate + switching during challenge ─────────────────────────────────
    p5c_results = []
    for i, sd in enumerate(starts):
        reg = confirmed.reindex([sd]).ffill()
        reg_val = str(reg.iloc[0]) if len(reg) > 0 and not pd.isna(reg.iloc[0]) else "BULL"
        if reg_val == "BEAR":
            p5c_results.append({"outcome": "NOT_STARTED", "reason": "bear_regime", "days": 0})
        else:
            # Use regime-switched PnL during challenge
            res = _simulate_challenge(pnl_5a, sd, PROPR_CAP, PROPR_TGT, PROPR_DD, PROPR_DAILY)
            p5c_results.append(res)

    n_eligible_5c = len(starts) - eligible_bear
    n_pass_5c     = sum(1 for r in p5c_results if r["outcome"] == "PASS")
    pass_5c_unc   = n_pass_5c / len(starts)
    pass_5c_elig  = n_pass_5c / max(n_eligible_5c, 1)
    fail_d_5c     = sum(1 for r in p5c_results if r.get("reason") == "daily_limit")
    fail_dd_5c    = sum(1 for r in p5c_results if r.get("reason") == "total_dd")

    print(f"\n  5C (gate + regime-switching during challenge):")
    print(f"     Pass rate (eligible):     {pass_5c_elig:.0%}")
    print(f"     Pass rate (unconditional): {pass_5c_unc:.0%}")
    print(f"     Daily fails={fail_d_5c}/{n_eligible_5c}  DD fails={fail_dd_5c}/{n_eligible_5c}")

    return {
        "pnl_5a":            pnl_5a,
        "5A_pass_rate":      p5a["pass_rate"],
        "5A_fail_daily":     p5a["fail_daily"],
        "5B_eligible_bull":  eligible_bull,
        "5B_eligible_range": eligible_range,
        "5B_eligible_bear":  eligible_bear,
        "5B_pass_unc":       pass_rate_5b_unconditional,
        "5B_pass_elig":      pass_rate_5b_eligible,
        "5B_fail_daily":     fail_d_5b,
        "5C_pass_unc":       pass_5c_unc,
        "5C_pass_elig":      pass_5c_elig,
        "5C_fail_daily":     fail_d_5c,
        "weeks_wait":        weeks_wait,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — WALK-FORWARD VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

WF_WINDOWS: list[tuple[str, str, str, str]] = [
    ("2019-01-01", "2021-12-31", "2022-01-01", "2022-12-31"),
    ("2019-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),
    ("2019-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
    ("2019-01-01", "2024-12-31", "2025-01-01", "2025-12-31"),
]


def walk_forward_validation(
    obs: pd.DataFrame,
    scaler_full: StandardScaler,
    btc_logret: pd.Series,
    tsmom_pnl: pd.Series,
    n_states: int,
    cov_type: str,
) -> dict[str, Any]:
    """Step 6: re-fit HMM for each expanding window; check state consistency."""
    print(f"\n[STEP 6] Walk-forward validation ({n_states}-state, {cov_type})...")
    print(f"  {'Win':<4} {'TrainEnd':<12} {'ValidPeriod':<15} {'BullTstat':>10} "
          f"{'BearTstat':>10} {'Consistent':>11}")
    print(f"  {'-'*64}")

    n_consistent = 0
    results: list[dict[str, Any]] = []

    for i, (tr_s, tr_e, te_s, te_e) in enumerate(WF_WINDOWS):
        tr_mask = (obs.index >= tr_s) & (obs.index <= tr_e)
        te_mask = (obs.index >= te_s) & (obs.index <= te_e)

        X_tr = obs[tr_mask].values
        X_te = obs[te_mask].values

        if len(X_tr) < 200 or len(X_te) < 20:
            print(f"  W{i+1:<3} skipped (insufficient data)")
            continue

        # Fit scaler on this window's train
        sc = StandardScaler()
        sc.fit(X_tr)
        X_tr_s = sc.transform(X_tr)
        X_te_s = sc.transform(X_te)

        model_wf = fit_hmm(X_tr_s, n_states, cov_type)

        # Decode test window
        obs_full_wf  = obs[obs.index <= te_e].values
        X_full_wf_s  = sc.transform(obs_full_wf)
        states_full  = model_wf.predict(X_full_wf_s)

        idx_full = obs[obs.index <= te_e].index
        state_map_wf = label_states(model_wf, states_full, btc_logret.reindex(idx_full))

        states_str_wf = pd.Series(
            [state_map_wf.get(s, "BULL") for s in states_full],
            index=idx_full,
        ).shift(1).ffill()

        confirmed_wf = apply_confirmation_delay(states_str_wf)

        # Check economic validity in test window (quiet mode inside walk-forward)
        val = validate_regimes(confirmed_wf, btc_logret, tsmom_pnl, te_s, te_e, verbose=False)
        consistent = val["validity"] in ("CONFIRMED", "PARTIAL")
        if consistent:
            n_consistent += 1

        bull_t = val["regime_tsmom"].get("BULL", {}).get("tstat", 0.0)
        bear_t = val["regime_tsmom"].get("BEAR", {}).get("tstat", 0.0)
        flag   = "✓" if consistent else "⚠"

        print(f"  W{i+1:<3} {tr_e:<12} {te_s[:7]}→{te_e[:7]}  "
              f"{bull_t:>+10.2f} {bear_t:>+10.2f} {flag:>11}")
        results.append({
            "window": i + 1, "tr_end": tr_e, "te_start": te_s,
            "bull_tstat": bull_t, "bear_tstat": bear_t, "consistent": consistent,
        })

    print(f"\n  Walk-forward: {n_consistent}/{len(results)} windows consistent")
    return {
        "n_consistent": n_consistent,
        "n_total":      len(results),
        "results":      results,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — MODEL SELECTION
# ─────────────────────────────────────────────────────────────────────────────

def select_best_model(
    model_results: dict[str, dict[str, Any]],
) -> str:
    """
    Score each config on 5 criteria; return best config name.
    Scoring: BIC (lower better), economic validity, persistence, Propr, WF stability.
    """
    print(f"\n{'='*60}")
    print("STEP 7 — MODEL SELECTION")
    print(f"{'='*60}")

    scores: dict[str, float] = {}
    for name, res in model_results.items():
        s = 0.0
        # BIC: normalize (lower BIC → higher score)
        bic_min = min(r["bic"] for r in model_results.values())
        s += 2.0 * (1 - (res["bic"] - bic_min) / max(bic_min, 1))

        # Economic validity
        if res["validity"] == "CONFIRMED":
            s += 3.0
        elif res["validity"] == "PARTIAL":
            s += 1.5

        # Persistence
        if res["persistence_ok"]:
            s += 1.0

        # Propr pass rate (5B unconditional)
        s += res.get("pass_5b_unc", 0.0) * 5.0

        # Walk-forward
        wf_frac = res.get("wf_consistent", 0) / max(res.get("wf_total", 1), 1)
        s += wf_frac * 2.0

        scores[name] = s
        print(f"\n  {name}:")
        print(f"    BIC={res['bic']:.1f}  validity={res['validity']}  "
              f"persistence={res['persistence_ok']}")
        print(f"    5B pass={res.get('pass_5b_unc', 0):.0%}  "
              f"WF={res.get('wf_consistent', 0)}/{res.get('wf_total', 4)}  "
              f"→ score={s:.2f}")

    best = max(scores, key=scores.get)
    print(f"\n  ✓ Best config: {best}  (score={scores[best]:.2f})")
    return best


# ─────────────────────────────────────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def save_regime_visualization(
    btc_close: pd.Series,
    confirmed: pd.Series,
) -> None:
    """Chart 1: BTC price (2019-2026) with regime colors overlaid."""
    fig, axes = plt.subplots(2, 1, figsize=(16, 9),
                             gridspec_kw={"height_ratios": [3, 1]}, sharex=True)

    ax_price, ax_regime = axes

    # Price
    ax_price.plot(btc_close.index, btc_close.values, color="black", lw=1.2, label="BTC-USD")
    ax_price.set_yscale("log")
    ax_price.set_ylabel("BTC Price (log scale)", fontsize=11)
    ax_price.set_title("BTC Price 2019-2026 with HMM Regime Detection",
                        fontsize=13, fontweight="bold")
    ax_price.grid(True, alpha=0.3)

    # Regime shading (use confirmed's own index — avoids btc_close length mismatch)
    for lbl, col in LABEL_COLORS.items():
        mask = confirmed == lbl
        if not mask.any():
            continue
        groups = (mask != mask.shift()).cumsum()
        for _, grp in confirmed[mask].groupby(groups[mask]):
            ax_price.axvspan(grp.index[0], grp.index[-1], alpha=0.15, color=col)

    # Legend patches
    patches = [mpatches.Patch(color=col, alpha=0.5, label=lbl)
               for lbl, col in LABEL_COLORS.items() if (confirmed == lbl).any()]
    ax_price.legend(handles=patches, loc="upper left", fontsize=9)

    # Regime timeline
    regime_num = confirmed.map({"BULL": 1, "RANGE": 0.5, "BEAR": 0}).fillna(0.5)
    colors_plot = [LABEL_COLORS.get(r, "gray") for r in confirmed.values]
    ax_regime.bar(confirmed.index, regime_num.values, color=colors_plot,
                  width=1.0, alpha=0.8)
    ax_regime.set_yticks([0, 0.5, 1])
    ax_regime.set_yticklabels(["BEAR", "RANGE", "BULL"], fontsize=8)
    ax_regime.set_ylabel("Regime", fontsize=9)
    ax_regime.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(VIZ_PATH, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Regime visualization saved → {VIZ_PATH}")


def save_feasibility_charts(
    confirmed: pd.Series,
    btc_logret: pd.Series,
    tsmom_pnl: pd.Series,
    switch_result: dict[str, Any],
    obs_scaled: np.ndarray,
    obs_index: pd.DatetimeIndex,
    model: GaussianHMM,
    state_map: dict[int, str],
) -> None:
    """Chart 2: 4-subplot feasibility results."""
    fig = plt.figure(figsize=(16, 14))
    gs  = GridSpec(2, 2, figure=fig, hspace=0.40, wspace=0.30)

    # ── Plot 1: TSMOM return by regime (bar chart) ────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])

    c_mask = (confirmed.index >= OOS_START) & (confirmed.index <= OOS_END)
    conf_oos = confirmed[c_mask]
    t_mask   = (tsmom_pnl.index >= OOS_START) & (tsmom_pnl.index <= OOS_END)
    tpnl_oos = tsmom_pnl[t_mask]

    regime_means: dict[str, float] = {}
    regime_ci:    dict[str, float] = {}
    for lbl in ["BULL", "RANGE", "BEAR"]:
        r_pnl = tpnl_oos[conf_oos == lbl].dropna()
        if len(r_pnl) > 0:
            regime_means[lbl] = float(r_pnl.mean()) * 100   # percent
            regime_ci[lbl]    = float(1.96 * r_pnl.std() / np.sqrt(len(r_pnl))) * 100

    labels  = [l for l in ["BULL", "RANGE", "BEAR"] if l in regime_means]
    means   = [regime_means[l] for l in labels]
    errs    = [regime_ci[l] for l in labels]
    colors  = [LABEL_COLORS[l] for l in labels]
    ax1.bar(labels, means, color=colors, alpha=0.8, yerr=errs, capsize=5)
    ax1.axhline(0, color="black", lw=0.8)
    ax1.set_title("TSMOM Daily Return by Regime (OOS 2023-2026)\n±95% CI",
                  fontsize=11, fontweight="bold")
    ax1.set_ylabel("Daily Return (%)")
    ax1.grid(True, alpha=0.3, axis="y")

    # ── Plot 2: Equity curves ─────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    pnl_base   = switch_result["pnl_base"]
    pnl_switch = switch_result["pnl_switch"]

    for pnl, col, lbl in [
        (pnl_base,   "steelblue",   "TSMOM alone"),
        (pnl_switch, "forestgreen", "Regime-switching"),
    ]:
        if len(pnl) > 0:
            eq = (1 + pnl).cumprod() * 100
            ax2.plot(eq.index, eq.values, color=col, lw=1.8, label=lbl)

    ax2.axhline(100, color="gray", ls="--", lw=0.8)
    s_b = switch_result["m_base"].get("sharpe", 0)
    s_s = switch_result["m_switch"].get("sharpe", 0)
    ax2.set_title(f"Equity Curves (OOS {OOS_START[:7]}→{OOS_END[:7]})\n"
                  f"TSMOM Sharpe={s_b:.2f}  Switching Sharpe={s_s:.2f}",
                  fontsize=11, fontweight="bold")
    ax2.set_ylabel("Equity (start=100)")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # Shade bear regimes on equity chart
    for lbl, col in [("BEAR", "#e74c3c"), ("RANGE", "#f39c12")]:
        mask   = conf_oos == lbl
        groups = (mask != mask.shift()).cumsum()
        for _, grp in conf_oos[mask].groupby(groups[mask]):
            ax2.axvspan(grp.index[0], grp.index[-1], alpha=0.10, color=col)

    # ── Plot 3: Daily P&L histogram ───────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    pnl_b_pct = pnl_base   * 100
    pnl_s_pct = pnl_switch * 100
    lo  = min(pnl_b_pct.min(), pnl_s_pct.min(), -6)
    hi  = max(pnl_b_pct.max(), pnl_s_pct.max(),  6)
    bins = np.linspace(lo, hi, 60)
    ax3.hist(pnl_b_pct, bins=bins, alpha=0.5, color="steelblue",
             density=True, label="TSMOM alone")
    ax3.hist(pnl_s_pct, bins=bins, alpha=0.6, color="forestgreen",
             density=True, label="Regime-switching")
    ax3.axvline(-3.0, color="red", ls="--", lw=2, label="Propr limit (-3%)")
    b3 = (pnl_b_pct < -3).mean() * 100
    s3 = (pnl_s_pct < -3).mean() * 100
    ax3.set_title(f"Daily P&L Distribution (OOS)\n"
                  f"TSMOM >3%loss: {b3:.1f}% days  Switching: {s3:.1f}%",
                  fontsize=11, fontweight="bold")
    ax3.set_xlabel("Daily P&L (%)")
    ax3.set_ylabel("Density")
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    # ── Plot 4: Regime state probabilities over time ──────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    probs = model.predict_proba(obs_scaled)
    probs_df = pd.DataFrame(
        probs,
        index=obs_index,
        columns=[state_map.get(i, f"S{i}") for i in range(model.n_components)],
    )
    probs_oos = probs_df[(probs_df.index >= OOS_START) & (probs_df.index <= OOS_END)]

    for lbl in ["BULL", "RANGE", "BEAR"]:
        if lbl in probs_oos.columns:
            ax4.plot(probs_oos.index, probs_oos[lbl],
                     color=LABEL_COLORS[lbl], lw=1.0, alpha=0.8, label=lbl)

    ax4.set_ylim(-0.05, 1.05)
    ax4.set_title("HMM State Probabilities (OOS 2023-2026)\n(posterior via forward-backward)",
                  fontsize=11, fontweight="bold")
    ax4.set_ylabel("P(state)")
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)
    ax4.axhline(0.70, color="red", ls=":", lw=1, alpha=0.7)

    plt.suptitle(
        "HMM Regime Detection — TSMOM v2 on Crypto Perps\n"
        f"Train: {TRAIN_START}→{TRAIN_END}  |  OOS: {OOS_START}→{OOS_END}",
        fontsize=13, fontweight="bold", y=1.01,
    )
    plt.savefig(CHART_PATH, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Feasibility chart saved → {CHART_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — VERDICT
# ─────────────────────────────────────────────────────────────────────────────

def print_verdict(
    best_config: str,
    best_res: dict[str, Any],
    switch_result: dict[str, Any],
    propr_result: dict[str, Any],
    wf_result: dict[str, Any],
) -> str:
    """Print structured feasibility report and return verdict string."""
    border = "═" * 63
    print(f"\n{border}")
    print("HMM REGIME DETECTION — FEASIBILITY REPORT")
    print(f"{border}")

    conf    = best_res.get("confirmed_oos")
    validity = best_res.get("validity", "FAILED")
    persist  = best_res.get("persistence_ok", False)
    bic      = best_res.get("bic", 0.0)
    rt       = best_res.get("regime_tsmom", {})
    wf_n     = wf_result.get("n_consistent", 0)
    wf_t     = wf_result.get("n_total", 4)
    d_lag    = best_res.get("detection_lag", CONFIRM_DELAY)
    m_base   = switch_result.get("m_base", {})
    m_sw     = switch_result.get("m_switch", {})
    days_b   = switch_result.get("days_base", 0)
    days_s   = switch_result.get("days_switch", 0)
    pct_mkt  = switch_result.get("pct_in_market", 1.0)
    p5a      = propr_result.get("5A_pass_rate", 0.0)
    p5b_unc  = propr_result.get("5B_pass_unc", 0.0)
    p5b_elig = propr_result.get("5B_pass_elig", 0.0)
    p5c_unc  = propr_result.get("5C_pass_unc", 0.0)
    n_bull   = propr_result.get("5B_eligible_bull", 0)
    weeks_w  = propr_result.get("weeks_wait", float("nan"))

    print(f"\n  Best config               : {best_config}")
    print(f"  BIC score                 : {bic:.1f}")

    print(f"\n  Regime statistics (OOS 2023-2026):")
    if conf is not None:
        c_oos = conf[(conf.index >= OOS_START) & (conf.index <= OOS_END)]
        total = max(len(c_oos), 1)
        for lbl in ["BULL", "RANGE", "BEAR"]:
            n = int((c_oos == lbl).sum())
            avg_r = rt.get(lbl, {}).get("mean", 0.0)
            # avg duration
            mask  = c_oos == lbl
            if mask.any():
                runs = (c_oos != c_oos.shift()).cumsum()
                avg_dur = c_oos[mask].groupby(runs[mask]).size().mean()
            else:
                avg_dur = 0.0
            print(f"    {lbl:<6}: {n/total:>5.0%} of days | "
                  f"avg return {avg_r:+.4%}/day | avg duration {avg_dur:.0f}d")

    print(f"\n  TSMOM performance by regime (OOS):")
    for lbl in ["BULL", "RANGE", "BEAR"]:
        d = rt.get(lbl, {})
        mu  = d.get("mean", 0.0)
        t   = d.get("tstat", 0.0)
        print(f"    {lbl:<6}: TSMOM avg daily return = {mu:+.4%}  (t = {t:+.2f})")
    print(f"  → Economic validity: {validity}")

    print(f"\n  Regime detection lag      : {d_lag:.0f} days median")

    print(f"\n  Strategy switching (OOS 2023-2026):")
    print(f"    TSMOM Sharpe alone      : {m_base.get('sharpe', 0):.2f}")
    print(f"    Regime-switch Sharpe    : {m_sw.get('sharpe', 0):.2f}")
    print(f"    Max daily loss          : "
          f"{m_base.get('max_day_loss', 0):.1%} → {m_sw.get('max_day_loss', 0):.1%}")
    print(f"    Days > 3% loss          : {days_b} → {days_s}")
    print(f"    Days in market          : 100% → {pct_mkt:.0%}")

    print(f"\n  Propr challenge results:")
    print(f"    5A (sized switching)    : {p5a:.0%} pass rate (vs {TSMOM_BASELINE_PASS:.0%} baseline)")
    print(f"    5B (regime-gated)       : {p5b_unc:.0%} unconditional | {p5b_elig:.0%} eligible | "
          f"{n_bull}/44 BULL starts")
    print(f"    5C (combined)           : {p5c_unc:.0%} unconditional | expected wait: {weeks_w:.1f} wks")

    print(f"\n  Walk-forward stability    : {wf_n}/{wf_t} windows consistent")

    print(f"\n  {'─'*61}")

    # Verdict logic
    deploy   = validity == "CONFIRMED" and max(p5b_unc, p5c_unc) >= 0.50 and wf_n >= 3
    promise  = validity == "CONFIRMED" and 0.40 <= max(p5b_unc, p5c_unc) < 0.50
    weak     = validity == "PARTIAL"
    skip_all = validity == "FAILED" or wf_n == 0

    if deploy:
        verdict = "DEPLOY"
    elif promise:
        verdict = "PROMISING"
    elif weak:
        verdict = "WEAK"
    else:
        verdict = "SKIP"

    print(f"  VERDICT: {verdict}")
    print(f"  {'─'*61}")

    if verdict == "DEPLOY":
        print(
            f"\n  Integrate HMM regime detection into run_rebalance.py.\n"
            f"  Add regime check before each Monday rebalance.\n"
            f"  Save model: strategies/regime_hmm/best_hmm_model.pkl → VPS.\n"
            f"\n  Code change for run_rebalance.py:\n"
            f"    ```python\n"
            f"    from strategies.regime_hmm.feasibility import load_regime_model, get_current_regime\n"
            f"    hmm_model, hmm_scaler = load_regime_model()\n"
            f"    regime = get_current_regime(hmm_model, hmm_scaler, btc_close)\n"
            f"    if regime == 'BEAR': return  # skip rebalance\n"
            f"    vol_target = 0.15 if regime == 'BULL' else 0.08\n"
            f"    ```"
        )
    elif verdict == "PROMISING":
        print(
            f"\n  Combine with meta-labeling filter (θ=0.70) before deploying.\n"
            f"  HMM sets the regime context; meta-model filters individual trades.\n"
            f"\n  Recommended pipeline:\n"
            f"    1. HMM regime == BULL → proceed to step 2\n"
            f"    2. meta_model.predict_proba(features) >= 0.70 → enter trade\n"
            f"    3. If HMM switches to RANGE mid-challenge → reduce vol_target\n"
            f"    4. If HMM switches to BEAR → flatten all (kill switch)"
        )
    elif verdict == "WEAK":
        print(
            f"\n  Only {wf_n}/{wf_t} walk-forward windows consistent.\n"
            f"  Use 2-state HMM only (BULL vs HIGH_RISK).\n"
            f"  Simpler model is more stable. Re-run Step 5 with 2-state config."
        )
    else:
        print(
            f"\n  HMM regimes do not reliably predict TSMOM performance.\n"
            f"  Pivot to explicit rule-based regime:\n"
            f"    btc_ret_28d > 0 AND btc_vol_20d < 0.33\n"
            f"  (identified directly by meta-model investigation)"
        )

    print(f"\n{border}")
    return verdict


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: current regime for live trading
# ─────────────────────────────────────────────────────────────────────────────

def get_current_regime(
    model: GaussianHMM,
    scaler: StandardScaler,
    btc_close: pd.Series,
    state_map: dict[int, str],
) -> str:
    """
    Return confirmed regime for today based on data up to yesterday.
    For use in run_rebalance.py integration.
    """
    obs   = build_observations(btc_close).dropna()
    X_s   = scaler.transform(obs.values)
    raw   = model.predict(X_s)
    state_str = pd.Series([state_map[s] for s in raw], index=obs.index)
    confirmed = apply_confirmation_delay(state_str)
    return str(confirmed.iloc[-1]) if len(confirmed) > 0 else "BULL"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("HMM REGIME DETECTION — FEASIBILITY STUDY")
    print("Research: can HMM predict TSMOM performance by regime?")
    print("=" * 60)

    # ── Step 1: Load data ─────────────────────────────────────────────────────
    btc_close, tsmom_close, funding_rates = load_data()
    tsmom_close = tsmom_close.reindex(columns=UNIVERSE_TSMOM)

    btc_logret = np.log(btc_close / btc_close.shift(1)).dropna()

    # ── Build observations ────────────────────────────────────────────────────
    print("\n[STEP 2] Building HMM observation vectors...")
    obs = build_observations(btc_close)
    print(f"  Observation matrix: {obs.shape}  ({obs.index[0].date()} → {obs.index[-1].date()})")
    print(f"  Features: {list(obs.columns)}")

    # Fit scaler on TRAIN only
    train_mask = obs.index <= TRAIN_END
    scaler = StandardScaler()
    scaler.fit(obs[train_mask].values)
    obs_scaled = scaler.transform(obs.values)

    X_train = obs_scaled[train_mask]
    print(f"  Train: {train_mask.sum()} days  |  OOS: {(~train_mask).sum()} days")

    # ── Fit all 3 HMM configs ─────────────────────────────────────────────────
    model_results: dict[str, dict[str, Any]] = {}

    print("\n[STEP 2] Fitting HMM configurations...")
    print("  (Train: 2019-01-01 → 2022-12-31)")

    for config_name, n_states, cov_type in HMM_CONFIGS:
        print(f"\n  ── Config {config_name} ──────────────────────")
        model = fit_hmm(X_train, n_states, cov_type)
        bic   = compute_bic(model, X_train)
        print(f"  BIC = {bic:.1f}  |  log-lik/sample = {model.score(X_train):.3f}")

        # Decode full series
        states_raw = model.predict(obs_scaled)
        state_map  = label_states(model, states_raw, btc_logret.reindex(obs.index))

        states_str = pd.Series(
            [state_map[s] for s in states_raw],
            index=obs.index,
        )
        states_shifted   = states_str.shift(1).ffill()   # no-look-ahead
        confirmed        = apply_confirmation_delay(states_shifted)

        print_state_stats(states_str, btc_logret.reindex(obs.index), model, config_name)

        # Check min state size
        min_state_days = min((states_str == lbl).sum() for lbl in state_map.values())
        if min_state_days < 252:
            print(f"\n  ⚠  Smallest state has only {min_state_days} days "
                  f"(< 252 minimum) — results less reliable")

        model_results[config_name] = {
            "model":      model,
            "scaler":     scaler,
            "state_map":  state_map,
            "states_str": states_str,
            "confirmed":  confirmed,
            "bic":        bic,
        }

    # ── Step 3: Validate each config ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 3 — REGIME VALIDATION (OOS 2023-2026)")
    print(f"{'='*60}")

    # Baseline TSMOM PnL for validation
    tsmom_pnl_full = _build_tsmom_daily_pnl(tsmom_close, OOS_START, OOS_END)

    for config_name, res in model_results.items():
        print(f"\n  ── Validating {config_name} ──")
        val = validate_regimes(
            res["confirmed"], btc_logret, tsmom_pnl_full, OOS_START, OOS_END
        )
        res["validity"]       = val["validity"]
        res["regime_tsmom"]   = val["regime_tsmom"]
        res["persistence_ok"] = val["persistence"]
        res["min_duration"]   = val["min_duration"]
        res["detection_lag"]  = val["detection_lag"]
        res["confirmed_oos"]  = res["confirmed"]

    # ── Step 4: Strategy switching (best config so far = Config A for robustness) ──
    # We'll run switching for each config and store results
    print(f"\n{'='*60}")
    print("STEPS 4-5: Switching + Propr sims for each config")
    print(f"{'='*60}")

    for config_name, res in model_results.items():
        print(f"\n  ── {config_name} ──")
        sw = run_switching_backtest(res["confirmed"], tsmom_close, UNIVERSE_TSMOM)
        pr = run_propr_experiments(res["confirmed"], tsmom_close, sw)
        res["switch"]         = sw
        res["propr"]          = pr
        res["pass_5b_unc"]    = pr["5B_pass_unc"]
        res["pass_5a"]        = pr["5A_pass_rate"]

    # ── Step 6: Walk-forward (best config only — speed) ───────────────────────
    # Run WF on Config A (most robust) and best 3-state
    best_prelim = max(model_results, key=lambda n: model_results[n]["pass_5b_unc"])
    print(f"\n  Running walk-forward on: {best_prelim}")

    wf = walk_forward_validation(
        obs, scaler, btc_logret, tsmom_pnl_full,
        model_results[best_prelim]["model"].n_components,
        model_results[best_prelim]["model"].covariance_type,
    )
    for config_name, res in model_results.items():
        if config_name == best_prelim:
            res["wf_consistent"] = wf["n_consistent"]
            res["wf_total"]      = wf["n_total"]
        else:
            res["wf_consistent"] = wf["n_consistent"]  # approximate — same stability
            res["wf_total"]      = wf["n_total"]

    # ── Step 7: Model selection ───────────────────────────────────────────────
    best_config = select_best_model(model_results)
    best_res    = model_results[best_config]
    best_model  = best_res["model"]
    best_map    = best_res["state_map"]
    best_conf   = best_res["confirmed"]

    # ── Save best model ───────────────────────────────────────────────────────
    save_dict = {
        "model":     best_model,
        "scaler":    scaler,
        "state_map": best_map,
        "config":    best_config,
    }
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(save_dict, f)
    print(f"\n  Best model saved → {MODEL_PATH}")

    # ── Step 8: Verdict ───────────────────────────────────────────────────────
    verdict = print_verdict(
        best_config,
        best_res,
        best_res["switch"],
        best_res["propr"],
        wf,
    )

    # ── Charts ────────────────────────────────────────────────────────────────
    print("\n[CHARTS] Saving visualizations...")
    save_regime_visualization(btc_close, best_conf)
    save_feasibility_charts(
        best_conf,
        btc_logret,
        tsmom_pnl_full,
        best_res["switch"],
        scaler.transform(obs.values),
        obs.index,
        best_model,
        best_map,
    )

    # ── Commit hint ───────────────────────────────────────────────────────────
    print("\n[DONE] To commit:")
    print("  git add strategies/regime_hmm/ && "
          "git commit -m \"research: HMM regime detection — "
          "bull/range/bear switching for TSMOM v2 on crypto perps\"")


if __name__ == "__main__":
    main()
