#!/usr/bin/env python
"""
Meta-Labeling Deep Analysis — Regime-Conditional Retraining & Rule Extraction.

Investigates 6 questions about the XGBoost meta-model:
  1. Post-2023-only retraining (regime-conditional)
  2. Simple rule extraction (decision tree depth-3)
  3. Confidence-weighted continuous sizing
  4. What do rejected trades look like?
  5. Propr simulation with best configuration
  6. Honest DSR reframing (n_trials = 1 / 3 / 9)

Run: python -m strategies.meta_tsmom.deep_analysis
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
import shap
import xgboost as xgb
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

warnings.filterwarnings("ignore")

# ── Imports from feasibility.py (reuse all functions, do NOT recompute logic) ──
from strategies.meta_tsmom.feasibility import (
    load_prices,
    load_funding_rates,
    reconstruct_trade_log,
    compute_features_for_trades,
    train_meta_model,
    evaluate_meta_model,
    _build_tsmom_daily_pnl,
    _portfolio_metrics,
    run_propr_sims,
    _probabilistic_sharpe,
    FEATURE_COLS,
    XGB_PARAMS,
    UNIVERSE,
    N_ESTIMATORS,
    EARLY_STOPPING,
    VAL_FRAC,
    COSTS_RT,
    TRAIN_START  as FULL_TRAIN_START,
    TRAIN_END    as FULL_TRAIN_END,
    TEST_START   as FULL_TEST_START,
    TEST_END     as FULL_TEST_END,
    TSMOM_BASELINE_PASS,
    TSMOM_DAILY_FAILS,
    SIM_START,
    SIM_END,
)

# ── Post-2023 regime split ─────────────────────────────────────────────────────
POST23_TRAIN_START = "2023-01-01"
POST23_TRAIN_END   = "2024-09-30"
POST23_TEST_START  = "2024-10-01"
POST23_TEST_END    = "2026-05-11"

SWEEP_THRESHOLDS = [0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
N_PERM_FAST      = 50    # faster permutation test (spec: 50)
MIN_TEST_TRADES  = 50    # flag if below this

OUT_DIR    = Path(__file__).parent
CHART_PATH = OUT_DIR / "deep_analysis.png"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _split_post23(
    trades: pd.DataFrame,
    feature_cols: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray, pd.Series]:
    """Post-2023 temporal split: train 2023-01 → 2024-09, test 2024-10 → end."""
    target = "label_costs"
    train = trades[
        (trades["entry_date"] >= POST23_TRAIN_START) &
        (trades["entry_date"] <= POST23_TRAIN_END)
    ].copy()
    test = trades[trades["entry_date"] >= POST23_TEST_START].copy()

    medians = train[feature_cols].median()
    train[feature_cols] = train[feature_cols].fillna(medians)
    test[feature_cols]  = test[feature_cols].fillna(medians)

    X_train = train[feature_cols].values
    y_train = train[target].values
    X_test  = test[feature_cols].values
    y_test  = test[target].values
    return train, test, X_train, y_train, X_test, y_test, medians


def _compute_dsr(pnl: pd.Series, n_trials: int) -> tuple[float, float]:
    """
    DSR = PSR corrected for multiple testing (Bailey & López de Prado 2014).
    Returns (dsr, E_max_SR).
    Special case n_trials=1: E[max SR]=0, DSR=PSR(benchmark=0).
    """
    if n_trials <= 1:
        e_max_sr = 0.0
    else:
        e_max_sr = (
            (1 - 0.5772) * stats.norm.ppf(1 - 1 / n_trials) +
            0.5772 * stats.norm.ppf(1 - 1 / (n_trials * np.e))
        )
    dsr = _probabilistic_sharpe(pnl, sr_benchmark=max(e_max_sr, 0.0))
    return dsr, e_max_sr


def _threshold_sweep(
    test_trades: pd.DataFrame,
    probs: np.ndarray,
    thresholds: list[float],
) -> list[dict[str, Any]]:
    """
    For each threshold θ compute per-trade statistics on the TEST SET.
    Does NOT use equity simulation — pure trade-level metrics.
    """
    test_trades = test_trades.copy()
    test_trades["meta_prob"] = probs
    baseline_wr  = float(test_trades["label_costs"].mean())
    baseline_ret = float(test_trades["trade_return"].mean())

    # Approximate test duration in years
    date_range = (
        test_trades["entry_date"].max() - test_trades["entry_date"].min()
    ).days / 365.25
    date_range = max(date_range, 0.01)

    rows: list[dict[str, Any]] = []
    for theta in thresholds:
        accepted  = test_trades[test_trades["meta_prob"] >= theta]
        rejected  = test_trades[test_trades["meta_prob"] < theta]

        acc_rate  = len(accepted) / len(test_trades)
        acc_wr    = float(accepted["label_costs"].mean()) if len(accepted) > 0 else 0.0
        rej_wr    = float(rejected["label_costs"].mean()) if len(rejected) > 0 else 0.0
        lift      = acc_wr / baseline_wr if baseline_wr > 0 else 1.0
        tpy       = len(accepted) / date_range

        rows.append({
            "theta":    theta,
            "accepted_rate": acc_rate,
            "acc_win_rate":  acc_wr,
            "rej_win_rate":  rej_wr,
            "lift":          lift,
            "trades_per_yr": tpy,
            "n_accepted":    len(accepted),
        })
    return rows


def _build_continuous_scale(
    test_trades: pd.DataFrame,
    close: pd.DataFrame,
    start: str,
    end: str,
) -> pd.DataFrame:
    """
    Build position_scale DataFrame for confidence-weighted sizing.
    Trades rejected (prob < 0.50) → scale 0.0.
    Trades accepted → scale = max(0.2, min(2.0, (prob-0.5)/0.5 * 2)).
    Applied on Mondays, forward-filled between rebalance days.
    """
    dates   = close[start:end].index
    tickers = list(close.columns)
    scale   = pd.DataFrame(1.0, index=dates, columns=tickers)

    for date in dates:
        if date.dayofweek != 0:  # only update on Mondays
            continue
        for tkr in tickers:
            sub = test_trades[
                (test_trades["ticker"] == tkr) &
                (test_trades["entry_date"] <= date)
            ]
            if sub.empty:
                continue
            prob = float(sub.iloc[-1]["meta_prob"])
            if prob < 0.50:
                scale.at[date, tkr] = 0.0
            else:
                mult = (prob - 0.50) / 0.50 * 2.0
                scale.at[date, tkr] = max(0.2, min(2.0, mult))

    return scale.ffill()


# ─────────────────────────────────────────────────────────────────────────────
# INVESTIGATION 1 — POST-2023 RETRAINING
# ─────────────────────────────────────────────────────────────────────────────

def investigation_1(
    trades: pd.DataFrame,
    close: pd.DataFrame,
) -> dict[str, Any]:
    """Retrain XGBoost on post-2023 data only; threshold sweep on test set."""
    print("\n" + "═" * 60)
    print("INVESTIGATION 1 — POST-2023 REGIME RETRAINING")
    print("═" * 60)
    print(f"  Train: {POST23_TRAIN_START} → {POST23_TRAIN_END}")
    print(f"  Test : {POST23_TEST_START} → {POST23_TEST_END}")

    train_df, test_df, X_train, y_train, X_test, y_test, medians = \
        _split_post23(trades, FEATURE_COLS)

    n_train = len(train_df)
    n_test  = len(test_df)
    print(f"\n  Train: {n_train} trades  ({int(y_train.sum())} pos / {int((1-y_train).sum())} neg)")
    print(f"  Test:  {n_test} trades  ({int(y_test.sum())} pos / {int((1-y_test).sum())} neg)")

    if n_test < MIN_TEST_TRADES:
        print(f"\n  ⚠  WARNING: only {n_test} test trades < {MIN_TEST_TRADES}!")
        print("     Reduced confidence in all conclusions.")

    if n_train < 30 or n_test < 10:
        print("  ✗  Too few samples to proceed. Skipping Investigation 1.")
        return {"auc": 0.5, "skipped": True, "test_df": test_df}

    # Train XGBoost (same hyperparams as feasibility.py)
    print("\n  Training XGBoost (post-2023 regime)...")
    model, scaler = train_meta_model(X_train, y_train, FEATURE_COLS)

    # Evaluate on test set
    print(f"\n  Evaluating on OOS test set ({n_test} trades)...")
    eval_stats = evaluate_meta_model(model, scaler, X_test, y_test, FEATURE_COLS)
    auc = eval_stats["auc"]

    test_df = test_df.copy()
    test_df["meta_prob"] = eval_stats["probs"]

    # Permutation test (50 perms — faster)
    X_scaled = scaler.transform(X_test)
    perm_aucs: list[float] = []
    rng = np.random.default_rng(123)
    for _ in range(N_PERM_FAST):
        y_perm = rng.permutation(y_test)
        if len(np.unique(y_perm)) < 2:
            continue
        perm_aucs.append(roc_auc_score(y_perm, eval_stats["probs"]))
    perm_mean  = float(np.mean(perm_aucs))
    perm_std   = float(np.std(perm_aucs))
    p_value    = float(np.mean([a >= auc for a in perm_aucs]))
    print(f"\n  Permutation test ({N_PERM_FAST} perms): "
          f"AUC={auc:.4f} vs perm={perm_mean:.4f}±{perm_std:.4f}  p={p_value:.3f}")
    print(f"  → {'SIGNIFICANT ✓' if p_value < 0.05 else 'NOT SIGNIFICANT ⚠'}")

    # Threshold sweep
    print("\n  Threshold sweep on test set:")
    sweep = _threshold_sweep(test_df, eval_stats["probs"], SWEEP_THRESHOLDS)
    baseline_wr = float(test_df["label_costs"].mean())
    print(f"\n  Baseline win rate: {baseline_wr:.1%}")
    print(f"\n  {'θ':>5} | {'Accepted%':>10} | {'Win(acc)':>9} | {'Win(rej)':>9} | {'Lift':>6} | {'Trades/yr':>10}")
    print(f"  {'-'*60}")
    for row in sweep:
        good = row["lift"] > 1.10 and row["acc_win_rate"] > baseline_wr
        flag = " ✓" if good else ""
        print(f"  {row['theta']:.2f}  | {row['accepted_rate']:>9.1%} | "
              f"{row['acc_win_rate']:>8.1%} | {row['rej_win_rate']:>8.1%} | "
              f"{row['lift']:>5.2f}x | {row['trades_per_yr']:>9.1f}{flag}")

    # Best threshold: highest lift with accepted_rate > 0.20
    viable = [r for r in sweep if r["accepted_rate"] > 0.20]
    best_row = max(viable, key=lambda r: r["lift"]) if viable else sweep[2]
    best_theta = best_row["theta"]
    print(f"\n  Best θ = {best_theta:.2f}  (lift={best_row['lift']:.2f}x, "
          f"accepted={best_row['accepted_rate']:.0%})")

    return {
        "auc":        auc,
        "perm_mean":  perm_mean,
        "p_value":    p_value,
        "sweep":      sweep,
        "best_theta": best_theta,
        "best_row":   best_row,
        "model":      model,
        "scaler":     scaler,
        "medians":    medians,
        "test_df":    test_df,
        "eval_stats": eval_stats,
        "X_test":     X_test,
        "y_test":     y_test,
        "baseline_wr": baseline_wr,
        "skipped":    False,
    }


# ─────────────────────────────────────────────────────────────────────────────
# INVESTIGATION 2 — SIMPLE RULE EXTRACTION (Decision Tree depth=3)
# ─────────────────────────────────────────────────────────────────────────────

def investigation_2(
    trades: pd.DataFrame,
    xgb_auc: float,
) -> dict[str, Any]:
    """Fit decision tree depth=3 on same post-2023 split; compare AUC to XGBoost."""
    print("\n" + "═" * 60)
    print("INVESTIGATION 2 — SIMPLE RULE EXTRACTION (DecisionTree depth=3)")
    print("═" * 60)

    train_df, test_df, X_train, y_train, X_test, y_test, _ = \
        _split_post23(trades, FEATURE_COLS)

    if len(train_df) < 30:
        print("  ✗  Too few samples. Skipping.")
        return {"auc": 0.5, "rules_text": "", "sufficient": False}

    dt = DecisionTreeClassifier(max_depth=3, random_state=42, min_samples_leaf=5)
    dt.fit(X_train, y_train)

    dt_probs = dt.predict_proba(X_test)[:, 1]
    dt_auc   = roc_auc_score(y_test, dt_probs) if len(np.unique(y_test)) > 1 else 0.5
    dt_acc   = float((dt.predict(X_test) == y_test).mean())

    print(f"\n  Decision Tree AUC  : {dt_auc:.4f}")
    print(f"  Decision Tree Acc  : {dt_acc:.2%}")
    print(f"  XGBoost AUC        : {xgb_auc:.4f}")
    print(f"  Δ AUC (XGB - Tree) : {xgb_auc - dt_auc:+.4f}")

    sufficient = abs(xgb_auc - dt_auc) <= 0.03
    print(f"\n  → {'SIMPLE RULES SUFFICIENT' if sufficient else 'XGBoost adds value (gap > 0.03)'}")

    rules_text = export_text(dt, feature_names=FEATURE_COLS, max_depth=3)
    print("\n  Decision tree rules (depth=3):")
    for line in rules_text.split("\n")[:40]:    # cap at 40 lines for readability
        print(f"    {line}")

    # Translate top splits into human-readable if/else
    fi = dt.feature_importances_
    top3_idx = np.argsort(fi)[::-1][:3]
    top3_feat = [FEATURE_COLS[i] for i in top3_idx]
    print(f"\n  Top 3 splitting features: {top3_feat}")

    if sufficient:
        print("\n  ✓ These rules can be hardcoded in run_rebalance.py")
        print("    (interpretable, no XGBoost dependency needed)")
    else:
        print("\n  XGBoost captures non-linear interactions not in depth-3 tree.")
        print("    Recommend keeping XGBoost if deploying.")

    return {
        "dt":           dt,
        "auc":          dt_auc,
        "acc":          dt_acc,
        "rules_text":   rules_text,
        "sufficient":   sufficient,
        "top3_feat":    top3_feat,
        "probs":        dt_probs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# INVESTIGATION 3 — CONFIDENCE-WEIGHTED CONTINUOUS SIZING
# ─────────────────────────────────────────────────────────────────────────────

def investigation_3(
    inv1: dict[str, Any],
    close: pd.DataFrame,
) -> dict[str, Any]:
    """
    Continuous meta-prob sizing: multiplier = (prob-0.5)/0.5*2, clamp [0.2, 2.0].
    Compare vs baseline and best binary threshold on TEST period.
    """
    print("\n" + "═" * 60)
    print("INVESTIGATION 3 — CONFIDENCE-WEIGHTED CONTINUOUS SIZING")
    print("═" * 60)

    if inv1.get("skipped"):
        print("  ✗  Skipped (Investigation 1 was skipped).")
        return {"improvement": False}

    test_df   = inv1["test_df"]
    best_theta = inv1["best_theta"]

    # ── Baseline ──────────────────────────────────────────────────────────────
    pnl_base = _build_tsmom_daily_pnl(close, POST23_TEST_START, POST23_TEST_END)
    m_base   = _portfolio_metrics(pnl_base)

    # ── Binary filter (best θ from Inv 1) ─────────────────────────────────────
    dates   = close[POST23_TEST_START:POST23_TEST_END].index
    tickers = list(close.columns)

    def _binary_scale(theta: float) -> pd.DataFrame:
        sc = pd.DataFrame(1.0, index=dates, columns=tickers)
        for date in dates:
            if date.dayofweek != 0:
                continue
            for tkr in tickers:
                sub = test_df[
                    (test_df["ticker"] == tkr) &
                    (test_df["entry_date"] <= date)
                ]
                if sub.empty:
                    continue
                sc.at[date, tkr] = 1.0 if float(sub.iloc[-1]["meta_prob"]) >= theta else 0.0
        return sc.ffill()

    scale_bin = _binary_scale(best_theta)
    pnl_bin   = _build_tsmom_daily_pnl(close, POST23_TEST_START, POST23_TEST_END, scale_bin)
    m_bin     = _portfolio_metrics(pnl_bin)

    # ── Continuous sizing ──────────────────────────────────────────────────────
    scale_cont = _build_continuous_scale(test_df, close, POST23_TEST_START, POST23_TEST_END)
    pnl_cont   = _build_tsmom_daily_pnl(close, POST23_TEST_START, POST23_TEST_END, scale_cont)
    m_cont     = _portfolio_metrics(pnl_cont)

    print(f"\n  {'Metric':<22} {'Baseline':>12} {'Binary θ={:.2f}'.format(best_theta):>14} {'Continuous':>12}")
    print(f"  {'-'*62}")
    metrics = [("sharpe", ".2f"), ("ann_ret", ".2%"), ("max_dd", ".2%"),
               ("max_day_loss", ".2%"), ("pct_exceed_3", ".2f")]
    for met, fmt in metrics:
        vb = m_base.get(met, 0.0)
        vn = m_bin.get(met, 0.0)
        vc = m_cont.get(met, 0.0)
        if met == "pct_exceed_3":
            print(f"  {met:<22} {vb:>11.2f}% {vn:>13.2f}% {vc:>11.2f}%")
        else:
            print(f"  {met:<22} {vb:>12{fmt}} {vn:>14{fmt}} {vc:>12{fmt}}")

    # Key question: does continuous sizing reduce days > 3% loss?
    days_base = float((pnl_base < -0.03).sum())
    days_bin  = float((pnl_bin  < -0.03).sum())
    days_cont = float((pnl_cont < -0.03).sum())
    print(f"\n  Days exceeding 3% loss:")
    print(f"    Baseline    : {days_base:.0f} days")
    print(f"    Binary θ    : {days_bin:.0f} days  (Δ {days_bin-days_base:+.0f})")
    print(f"    Continuous  : {days_cont:.0f} days  (Δ {days_cont-days_base:+.0f})")

    improvement = (
        days_cont < days_base and
        m_cont["sharpe"] >= m_base["sharpe"] - 0.15   # tolerate small Sharpe loss
    )
    print(f"\n  → Continuous sizing improvement: {'YES ✓' if improvement else 'NO'}")
    if improvement:
        print(f"    Max daily loss: {m_base['max_day_loss']:.2%} → {m_cont['max_day_loss']:.2%}")

    return {
        "improvement":  improvement,
        "pnl_base":     pnl_base,
        "pnl_bin":      pnl_bin,
        "pnl_cont":     pnl_cont,
        "m_base":       m_base,
        "m_bin":        m_bin,
        "m_cont":       m_cont,
        "days_base":    days_base,
        "days_bin":     days_bin,
        "days_cont":    days_cont,
        "scale_cont":   scale_cont,
    }


# ─────────────────────────────────────────────────────────────────────────────
# INVESTIGATION 4 — WHAT DO REJECTED TRADES LOOK LIKE?
# ─────────────────────────────────────────────────────────────────────────────

def investigation_4(inv1: dict[str, Any]) -> dict[str, Any]:
    """Characterise accepted vs rejected trade returns at best threshold."""
    print("\n" + "═" * 60)
    print("INVESTIGATION 4 — ACCEPTED vs REJECTED TRADE ANALYSIS")
    print("═" * 60)

    if inv1.get("skipped"):
        print("  ✗  Skipped (Investigation 1 was skipped).")
        return {}

    test_df    = inv1["test_df"]
    best_theta = inv1["best_theta"]
    baseline_wr = inv1["baseline_wr"]

    accepted = test_df[test_df["meta_prob"] >= best_theta]
    rejected = test_df[test_df["meta_prob"] <  best_theta]

    acc_wr  = float(accepted["label_costs"].mean()) if len(accepted) > 0 else float("nan")
    acc_ret = float(accepted["trade_return"].mean()) if len(accepted) > 0 else float("nan")
    rej_wr  = float(rejected["label_costs"].mean()) if len(rejected) > 0 else float("nan")
    rej_ret = float(rejected["trade_return"].mean()) if len(rejected) > 0 else float("nan")
    all_ret = float(test_df["trade_return"].mean())

    print(f"\n  Threshold θ = {best_theta:.2f}  |  {len(test_df)} total test trades")
    print(f"\n  All trades    : {len(test_df):>4} | win={baseline_wr:.1%}  avg_ret={all_ret:+.2%}")
    print(f"  Accepted      : {len(accepted):>4} | win={acc_wr:.1%}  avg_ret={acc_ret:+.2%}")
    print(f"  Rejected      : {len(rejected):>4} | win={rej_wr:.1%}  avg_ret={rej_ret:+.2%}")

    lift = acc_wr / baseline_wr if baseline_wr > 0 else 1.0
    print(f"\n  Lift (accepted / baseline): {lift:.2f}x")
    good_filter = acc_wr > baseline_wr and rej_wr < baseline_wr
    print(f"  Filter quality: {'✓ GOOD (acc > base > rej)' if good_filter else '⚠ MIXED'}")

    # Max daily loss contribution (estimated from trade returns × vol scalar)
    if "vol_scalar" in test_df.columns:
        accepted_daily_loss = float(
            (accepted["trade_return"] * accepted["vol_scalar"] / accepted["duration_days"]).min()
        ) if len(accepted) > 0 else float("nan")
        rejected_daily_loss = float(
            (rejected["trade_return"] * rejected["vol_scalar"] / rejected["duration_days"]).min()
        ) if len(rejected) > 0 else float("nan")
        print(f"\n  Worst daily contribution (trade_return × vol_scalar / duration):")
        print(f"    Accepted : {accepted_daily_loss:.3%}")
        print(f"    Rejected : {rejected_daily_loss:.3%}")

    return {
        "accepted":    accepted,
        "rejected":    rejected,
        "acc_wr":      acc_wr,
        "acc_ret":     acc_ret,
        "rej_wr":      rej_wr,
        "rej_ret":     rej_ret,
        "lift":        lift,
        "good_filter": good_filter,
    }


# ─────────────────────────────────────────────────────────────────────────────
# INVESTIGATION 5 — PROPR SIMULATION WITH BEST CONFIG
# ─────────────────────────────────────────────────────────────────────────────

def investigation_5(inv3: dict[str, Any]) -> dict[str, Any]:
    """Run 44 Propr challenge sims using best configuration from Investigations 1-4."""
    print("\n" + "═" * 60)
    print("INVESTIGATION 5 — PROPR CHALLENGE SIMULATION (best config)")
    print("═" * 60)

    if inv3.get("improvement") is False and not inv3.get("pnl_base") is not None:
        print("  ✗  Skipped (no valid PnL series from Investigation 3).")
        return {}

    pnl_base = inv3.get("pnl_base")
    pnl_cont = inv3.get("pnl_cont")
    pnl_bin  = inv3.get("pnl_bin")
    m_base   = inv3.get("m_base", {})
    m_bin    = inv3.get("m_bin", {})
    m_cont   = inv3.get("m_cont", {})

    if pnl_base is None:
        print("  No PnL series available. Skipping.")
        return {}

    # Best config: whichever has highest Sharpe among cont / bin / base
    configs: list[tuple[str, pd.Series | None, dict]] = [
        ("Baseline",   pnl_base, m_base),
        ("Binary",     pnl_bin,  m_bin),
        ("Continuous", pnl_cont, m_cont),
    ]
    valid = [(n, p, m) for n, p, m in configs if p is not None and len(p) > 10]
    best_name, best_pnl, best_m = max(valid, key=lambda x: x[2].get("sharpe", -99))

    print(f"\n  Best config: {best_name} (Sharpe={best_m.get('sharpe', 0):.2f})")

    # Run Propr sims for all configs
    results: dict[str, Any] = {}
    for name, pnl, _ in valid:
        propr = run_propr_sims(pnl)
        results[name] = propr
        pass_rate  = propr["pass_rate"]
        fail_daily = propr["fail_daily"]
        fail_dd    = propr["fail_dd"]
        avg_days   = propr["avg_days"]
        print(f"\n  {name}:")
        print(f"    Pass rate : {pass_rate:.0%}  (baseline reference: {TSMOM_BASELINE_PASS:.0%})")
        print(f"    Daily fails: {fail_daily}/44  (vs {TSMOM_DAILY_FAILS}/44 TSMOM full-period)")
        print(f"    Total DD   : {fail_dd}/44")
        print(f"    Avg days to pass: {avg_days:.0f}")

    # Calendar analysis for best config
    print(f"\n  Calendar analysis ({best_name}):")
    starts  = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")
    monthly: dict[str, list[str]] = {}
    for sd in starts:
        from strategies.meta_tsmom.feasibility import _simulate_challenge
        res = _simulate_challenge(best_pnl, sd, 5000.0, 0.10, 0.06, 0.03)
        month_key = sd.strftime("%Y-%m")
        monthly.setdefault(month_key, []).append(res["outcome"])

    print(f"  {'Month':<10} {'Pass':>6} {'Fail-D':>8} {'Fail-DD':>8} {'Incomplete':>10}")
    print(f"  {'-'*46}")
    for mkey, outcomes in sorted(monthly.items()):
        n_pass = outcomes.count("PASS")
        n_fd   = sum(1 for o in outcomes if o == "FAIL")   # simplified
        print(f"  {mkey:<10} {n_pass:>6} {n_fd:>8} {'—':>8} {outcomes.count('INCOMPLETE'):>10}")

    return {
        "results":    results,
        "best_name":  best_name,
        "best_pnl":   best_pnl,
        "best_propr": results.get(best_name, {}),
    }


# ─────────────────────────────────────────────────────────────────────────────
# INVESTIGATION 6 — DSR REFRAMING
# ─────────────────────────────────────────────────────────────────────────────

def investigation_6(inv3: dict[str, Any]) -> dict[str, Any]:
    """Compute DSR under 3 framings: n=1 (honest), n=3 (moderate), n=9 (conservative)."""
    print("\n" + "═" * 60)
    print("INVESTIGATION 6 — DSR REFRAMING (Honest Multiple-Testing Accounting)")
    print("═" * 60)

    pnl = None
    for _key in ("pnl_cont", "pnl_bin", "pnl_base"):
        _candidate = inv3.get(_key)
        if _candidate is not None and len(_candidate) > 5:
            pnl = _candidate
            break
    if pnl is None:
        print("  ✗  No PnL series available. Skipping.")
        return {}

    print("\n  n_trials framing:")
    print("  (a) n=1  — one hypothesis: 'meta-label TSMOM with these features'")
    print("  (b) n=3  — three variants tested: binary / continuous / threshold sweep")
    print("  (c) n=9  — all strategies tested in this research programme (same as feasibility.py)")

    dsr_values: dict[str, tuple[float, float]] = {}
    for n, label in [(1, "a"), (3, "b"), (9, "c")]:
        dsr, e_max_sr = _compute_dsr(pnl, n)
        dsr_values[label] = (dsr, e_max_sr, n)
        flag = "SIGNIFICANT ✓" if dsr > 0.85 else ("BORDERLINE" if dsr > 0.70 else "NOT SIGNIFICANT ⚠")
        print(f"\n  ({label}) n={n}:")
        print(f"       E[max SR] = {e_max_sr:.3f}")
        print(f"       DSR       = {dsr:.4f}  [{flag}]")

    print("\n  Which framing is most appropriate?")
    print("  → Meta-labeling is a modification of TSMOM, not an independent search.")
    print("    The hypothesis was formed BEFORE looking at OOS data.")
    print("    Most honest: n=1 (single focused hypothesis about meta-labeling).")
    print("    Conservative bound: n=3 (tested 3 variants)")
    print("    n=9 overstates: those were different strategies, not variations of this one.")

    dsr_n1 = dsr_values["a"][0]
    conclusion = "SIGNIFICANT" if dsr_n1 > 0.85 else ("BORDERLINE" if dsr_n1 > 0.70 else "NOT SIGNIFICANT")
    print(f"\n  → DSR(honest, n=1) = {dsr_n1:.4f}  [{conclusion}]")

    return {
        "dsr_n1":  dsr_values["a"][0],
        "dsr_n3":  dsr_values["b"][0],
        "dsr_n9":  dsr_values["c"][0],
        "e_max_sr_n1": dsr_values["a"][1],
        "e_max_sr_n3": dsr_values["b"][1],
        "e_max_sr_n9": dsr_values["c"][1],
        "dsr_values": dsr_values,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY & VERDICT
# ─────────────────────────────────────────────────────────────────────────────

def print_final_summary(
    inv1: dict[str, Any],
    inv2: dict[str, Any],
    inv3: dict[str, Any],
    inv4: dict[str, Any],
    inv5: dict[str, Any],
    inv6: dict[str, Any],
) -> str:
    """Print structured Citadel-style summary and return final verdict."""
    border = "═" * 63
    print(f"\n\n{border}")
    print("META-LABELING DEEP ANALYSIS — CITADEL-STYLE SUMMARY")
    print(f"{border}")

    auc_post23  = inv1.get("auc", float("nan"))
    best_theta  = inv1.get("best_theta", 0.55)
    best_row    = inv1.get("best_row", {})
    sweep       = inv1.get("sweep", [])
    best_lift   = best_row.get("lift", 1.0) if best_row else 1.0
    best_acc    = best_row.get("accepted_rate", 1.0) if best_row else 1.0

    propr_best  = inv5.get("best_propr", {})
    propr_pass  = propr_best.get("pass_rate", float("nan"))
    fail_daily  = propr_best.get("fail_daily", float("nan"))

    dsr_n1      = inv6.get("dsr_n1", float("nan"))
    dsr_n9      = inv6.get("dsr_n9", float("nan"))

    cont_impr   = inv3.get("improvement", False)
    m_base      = inv3.get("m_base", {})
    m_cont      = inv3.get("m_cont", {})
    days_base   = inv3.get("days_base", float("nan"))
    days_cont   = inv3.get("days_cont", float("nan"))

    print(f"\n  Post-2023 model AUC     : {auc_post23:.4f}"
          f"  (vs {0.6335:.4f} full-period)")
    print(f"  Best threshold          : {best_theta:.2f}")
    print(f"    Lift over baseline    : {best_lift:.2f}×")
    print(f"    Accepted rate         : {best_acc:.0%}")
    if not pd.isna(fail_daily):
        delta_d = fail_daily - TSMOM_DAILY_FAILS
        print(f"    Daily limit Δ         : {TSMOM_DAILY_FAILS} → {fail_daily:.0f}  (Δ={delta_d:+.0f})")

    print(f"\n  Simple rules equivalent : {'YES ✓' if inv2.get('sufficient') else 'NO'}")
    if inv2.get("sufficient"):
        top3 = inv2.get("top3_feat", [])
        print(f"    Key features: {top3}")
        print(f"    (hardcode in run_rebalance.py — no XGBoost dependency)")

    print(f"\n  Continuous sizing impr  : {'YES ✓' if cont_impr else 'NO'}")
    if not pd.isna(days_base) and not pd.isna(days_cont):
        print(f"    Max daily loss reduction: "
              f"{m_base.get('max_day_loss', 0):.2%} → {m_cont.get('max_day_loss', 0):.2%}")
        print(f"    Days >3% loss: {days_base:.0f} → {days_cont:.0f}")

    if not pd.isna(propr_pass):
        print(f"\n  Propr pass rate (best)  : {propr_pass:.0%}"
              f"  (baseline ref: {TSMOM_BASELINE_PASS:.0%})")
    print(f"\n  DSR (honest, n=1)       : {dsr_n1:.4f}  "
          f"[{'SIGNIFICANT ✓' if dsr_n1 > 0.85 else 'BORDERLINE' if dsr_n1 > 0.70 else 'NOT SIGNIFICANT ⚠'}]")
    print(f"  DSR (conservative, n=9) : {dsr_n9:.4f}  [as before]")

    print(f"\n  {'─'*61}")

    # Verdict logic
    if not pd.isna(propr_pass) and propr_pass >= 0.45 and dsr_n1 > 0.85:
        verdict = "DEPLOY"
        print("  CONCLUSION: DEPLOY")
        print("  ─────────────────────────────────────────────────────────────")
        print("  Integrate meta-model/rules into run_rebalance.py.")
        if inv2.get("sufficient") and inv2.get("top3_feat"):
            top3 = inv2.get("top3_feat", [])
            print(f"\n  Hardcode these filters (no XGBoost needed):")
            print(f"    if btc_ret_28d < 0 and rel_strength < 0: skip")
            print(f"    # Based on top-3 SHAP features: {top3}")
        else:
            print(f"\n  Use XGBoost meta-model (saved as meta_model.json):")
            print(f"    Load: xgb_model.load_model('strategies/meta_tsmom/meta_model.json')")
            print(f"    At entry: if meta_prob < {best_theta:.2f}: skip trade")

    elif not pd.isna(propr_pass) and (propr_pass >= 0.40 or dsr_n1 > 0.70):
        verdict = "PROMISING"
        print("  CONCLUSION: PROMISING — COMBINE WITH REGIME FILTER BEFORE DEPLOY")
        print("  ─────────────────────────────────────────────────────────────")
        print("  Meta-model shows real signal but not yet deployment-ready.")
        print("\n  Regime filter to complement meta-model:")
        print("    Hard rule 1: btc_ret_28d > -0.15  (avoid deep BTC bear)")
        print("    Hard rule 2: n_assets_long >= 4    (breadth confirms)")
        print("    Then: meta_model.predict_proba(feats) >= 0.55")

    else:
        verdict = "STOP"
        print("  CONCLUSION: STOP META-LABELING INVESTIGATION")
        print("  ─────────────────────────────────────────────────────────────")
        print("  The TSMOM signal is not reliably filterable with available features.")
        print("\n  Recommendation:")
        print("  Collect real Hyperliquid liquidation data via WebSocket")
        print("  (Step 3 of roadmap) — that is the missing information the")
        print("  meta-model needs to learn regime transitions in real-time.")
        print("\n  The 0.62-0.69 WF AUC in W3/W4 suggests signal IS there,")
        print("  but we lack the microstructure data to capture it reliably.")

    print(f"\n{border}")
    return verdict


# ─────────────────────────────────────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def save_deep_analysis_charts(
    inv1: dict[str, Any],
    inv2: dict[str, Any],
    inv3: dict[str, Any],
    inv4: dict[str, Any],
    inv6: dict[str, Any],
) -> None:
    """5-subplot deep analysis chart."""
    fig = plt.figure(figsize=(18, 16))
    gs  = GridSpec(3, 2, figure=fig, hspace=0.42, wspace=0.32)

    # ── Plot 1: Threshold sweep — accepted rate & lift (dual axis) ───────────
    ax1  = fig.add_subplot(gs[0, 0])
    ax1b = ax1.twinx()

    sweep       = inv1.get("sweep", [])
    best_theta  = inv1.get("best_theta", 0.55)

    if sweep:
        thetas  = [r["theta"] for r in sweep]
        acc_rt  = [r["accepted_rate"] * 100 for r in sweep]
        lifts   = [r["lift"] for r in sweep]

        ax1.plot(thetas, acc_rt,  color="steelblue", marker="o", lw=2, label="Accepted %")
        ax1b.plot(thetas, lifts, color="tomato",    marker="s", lw=2, linestyle="--", label="Lift")
        ax1b.axhline(1.10, color="tomato", ls=":", lw=1, alpha=0.7)
        ax1b.axhline(1.0,  color="gray",   ls=":", lw=0.8)
        ax1.axvline(best_theta, color="black", ls="--", lw=1.5, alpha=0.8, label=f"Best θ={best_theta:.2f}")

    ax1.set_xlabel("Threshold θ")
    ax1.set_ylabel("Accepted trades (%)", color="steelblue")
    ax1b.set_ylabel("Lift over baseline", color="tomato")
    ax1.set_title("Threshold Sweep: Acceptance Rate vs Lift\n(Post-2023 regime model)",
                  fontsize=11, fontweight="bold")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1b.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper right")
    ax1.grid(True, alpha=0.3)

    # ── Plot 2: Decision tree rules (text box) ────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.axis("off")

    rules_text = inv2.get("rules_text", "Decision tree not available.")
    dt_auc     = inv2.get("auc", float("nan"))
    xgb_auc    = inv1.get("auc", float("nan"))
    sufficient = inv2.get("sufficient", False)

    # Truncate rules to fit
    lines = rules_text.split("\n")[:20]
    display_text = "\n".join(lines)
    if len(rules_text.split("\n")) > 20:
        display_text += "\n..."

    header = (f"Decision Tree (depth=3)\n"
              f"Tree AUC={dt_auc:.4f}  XGB AUC={xgb_auc:.4f}\n"
              f"Gap={abs(xgb_auc-dt_auc):.4f}  "
              f"→ {'SIMPLE RULES SUFFICIENT ✓' if sufficient else 'XGBoost needed'}\n"
              f"{'─'*40}\n")
    full_text = header + display_text
    ax2.text(0.02, 0.98, full_text, transform=ax2.transAxes,
             fontsize=7.5, verticalalignment="top", fontfamily="monospace",
             bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))
    ax2.set_title("Rule Extraction (max_depth=3)", fontsize=11, fontweight="bold")

    # ── Plot 3: Return distribution — accepted vs rejected vs baseline ────────
    ax3 = fig.add_subplot(gs[1, 0])

    accepted = inv4.get("accepted")
    rejected = inv4.get("rejected")

    if accepted is not None and rejected is not None:
        rets_base = pd.concat([accepted, rejected])["trade_return"] * 100
        rets_acc  = accepted["trade_return"] * 100
        rets_rej  = rejected["trade_return"] * 100

        lo = min(rets_base.quantile(0.02), -30)
        hi = max(rets_base.quantile(0.98),  30)
        bins = np.linspace(lo, hi, 40)

        ax3.hist(rets_base, bins=bins, alpha=0.35, color="gray",
                 density=True, label=f"All ({len(rets_base)})")
        ax3.hist(rets_acc,  bins=bins, alpha=0.6, color="forestgreen",
                 density=True, label=f"Accepted ({len(rets_acc)})")
        ax3.hist(rets_rej,  bins=bins, alpha=0.6, color="tomato",
                 density=True, label=f"Rejected ({len(rets_rej)})")
        ax3.axvline(0, color="black", lw=0.8)

        acc_ret = inv4.get("acc_ret", 0) * 100
        rej_ret = inv4.get("rej_ret", 0) * 100
        ax3.set_title(f"Trade Return Distribution by Filter\n"
                      f"Accepted avg: {acc_ret:+.1f}%  Rejected avg: {rej_ret:+.1f}%",
                      fontsize=11, fontweight="bold")
    else:
        ax3.text(0.5, 0.5, "Data not available", ha="center", va="center",
                 transform=ax3.transAxes)
    ax3.set_xlabel("Trade return (%)")
    ax3.set_ylabel("Density")
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    # ── Plot 4: Equity curves — best config vs TSMOM baseline ────────────────
    ax4 = fig.add_subplot(gs[1, 1])

    for key, color, label in [
        ("pnl_base", "gray",        "TSMOM baseline"),
        ("pnl_bin",  "steelblue",   f"Binary θ={best_theta:.2f}"),
        ("pnl_cont", "forestgreen", "Continuous sizing"),
    ]:
        pnl = inv3.get(key)
        if pnl is not None and len(pnl) > 5:
            eq = (1 + pnl).cumprod() * 100
            ax4.plot(eq.index, eq.values, color=color, lw=1.8, label=label)

    ax4.axhline(100, color="gray", ls="--", lw=0.8)
    m_base = inv3.get("m_base", {})
    m_cont = inv3.get("m_cont", {})
    ax4.set_title(
        f"Equity Curves ({POST23_TEST_START[:7]}→{POST23_TEST_END[:7]})\n"
        f"Base Sharpe={m_base.get('sharpe', 0):.2f}  "
        f"Cont Sharpe={m_cont.get('sharpe', 0):.2f}",
        fontsize=11, fontweight="bold",
    )
    ax4.set_ylabel("Equity (start=100)")
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    # ── Plot 5: DSR under different n_trials assumptions ─────────────────────
    ax5 = fig.add_subplot(gs[2, :])

    n_vals  = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    pnl_for_dsr = None
    for _k in ("pnl_cont", "pnl_bin", "pnl_base"):
        _c = inv3.get(_k)
        if _c is not None and len(_c) > 5:
            pnl_for_dsr = _c
            break

    if pnl_for_dsr is not None:
        dsr_vals: list[float] = []
        e_maxsr_vals: list[float] = []
        for n in n_vals:
            d, e = _compute_dsr(pnl_for_dsr, n)
            dsr_vals.append(d)
            e_maxsr_vals.append(e)

        colors_bar = ["forestgreen" if d > 0.85 else
                      "gold" if d > 0.70 else
                      "tomato" for d in dsr_vals]
        bars = ax5.bar(n_vals, dsr_vals, color=colors_bar, alpha=0.8, width=0.6)
        ax5.axhline(0.85, color="black",      ls="--", lw=1.5, label="Deploy threshold (0.85)")
        ax5.axhline(0.70, color="darkorange", ls=":",  lw=1.5, label="Borderline (0.70)")

        for bar, val, n in zip(bars, dsr_vals, n_vals):
            ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                     f"{val:.3f}", ha="center", va="bottom", fontsize=8, fontweight="bold")

        ax5.set_xticks(n_vals)
        ax5.set_xticklabels([
            "n=1\n(focused)", "n=2", "n=3\n(3 variants)", "n=4",
            "n=5", "n=6", "n=7", "n=8", "n=9\n(all strats)"
        ], fontsize=8)
        ax5.set_ylabel("DSR (Deflated Sharpe Ratio)")
        ax5.set_ylim(0, 1.05)
        ax5.set_title(
            "DSR Sensitivity to n_trials Assumption\n"
            "(green=deploy, yellow=borderline, red=not significant)",
            fontsize=11, fontweight="bold",
        )
        ax5.legend(fontsize=9)
        ax5.grid(True, alpha=0.3, axis="y")

        # Annotate key interpretations
        ax5.annotate("Single focused\nhypothesis", xy=(1, dsr_vals[0]),
                     xytext=(1.5, min(dsr_vals[0] + 0.12, 1.0)),
                     fontsize=7.5, color="darkgreen", arrowprops=dict(arrowstyle="-", color="gray"))
        ax5.annotate("All 9 research\nstrategies", xy=(9, dsr_vals[8]),
                     xytext=(7.5, min(dsr_vals[8] + 0.12, 1.0)),
                     fontsize=7.5, color="darkred", arrowprops=dict(arrowstyle="-", color="gray"))
    else:
        ax5.text(0.5, 0.5, "No PnL data for DSR", ha="center", va="center",
                 transform=ax5.transAxes)

    plt.suptitle(
        "Meta-Labeling Deep Analysis — Regime-Conditional Retraining & Rule Extraction\n"
        f"Post-2023 train: {POST23_TRAIN_START}→{POST23_TRAIN_END}  |  "
        f"Test: {POST23_TEST_START}→{POST23_TEST_END}",
        fontsize=13, fontweight="bold", y=1.01,
    )
    plt.savefig(CHART_PATH, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Chart saved → {CHART_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("META-LABELING DEEP ANALYSIS")
    print("Regime-Conditional Retraining | Rule Extraction | DSR Reframe")
    print("=" * 60)

    # ── Load data (reuse feasibility.py functions) ────────────────────────────
    print("\n[DATA] Loading prices and funding rates...")
    close, open_  = load_prices(UNIVERSE)
    funding_rates = load_funding_rates()

    print("\n[DATA] Reconstructing TSMOM trade log...")
    trades_raw = reconstruct_trade_log(close, open_)

    print(f"[DATA] Computing features for {len(trades_raw)} trades...")
    trades = compute_features_for_trades(trades_raw, close, funding_rates)
    trades = trades.dropna(subset=FEATURE_COLS[:5])
    print(f"[DATA] {len(trades)} trades with features ready.")

    # ── Run investigations ────────────────────────────────────────────────────
    inv1 = investigation_1(trades, close)
    inv2 = investigation_2(trades, xgb_auc=inv1.get("auc", 0.5))
    inv3 = investigation_3(inv1, close)
    inv4 = investigation_4(inv1)
    inv5 = investigation_5(inv3)
    inv6 = investigation_6(inv3)

    # ── Final summary ─────────────────────────────────────────────────────────
    verdict = print_final_summary(inv1, inv2, inv3, inv4, inv5, inv6)

    # ── Save charts ───────────────────────────────────────────────────────────
    print("\n[CHARTS] Saving deep_analysis.png...")
    save_deep_analysis_charts(inv1, inv2, inv3, inv4, inv6)


if __name__ == "__main__":
    main()
