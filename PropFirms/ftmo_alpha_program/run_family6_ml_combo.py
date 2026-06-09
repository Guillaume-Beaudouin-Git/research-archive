"""
run_family6_ml_combo.py — Family-6: ML feature-combination sprint (FTMO)
=========================================================================

Tests whether the UNION of causal price-derived features admits a non-linear
combination with robust GROSS-OOS edge that no single indicator captured.
Definitive test of the "price-transformation space" for FTMO suitability.

Universe : EURUSD, US500, GER40, XAUUSD — intraday M15, liquid hours.
IS       : 2022-01-01 → 2024-12-31 (all choices: features, model, hyperparams, threshold).
Hold-out : 2025-01-01 → 2026-05-29 (sealed; touched ONCE for the final verdict).

Methodology (sprint protocol):
  Step 0 — causal features + ONC clustering (silhouette + |corr|≥0.8 forced merges)
  Step 1 — labels (intraday-flat forward log-return at H=1 bar) + CPCV (purge+embargo)
  Step 2 — simple-first model (logistic L2 → shallow LightGBM); GROSS OOS Sharpe = decisive
  Step 3 — gates: PBO < 0.5, DSR ≥ 0.95, cost L11 (gross > 3× cost drag),
           daily kurt < 3, tail-DD < 10%, hold-out net Sharpe sign-stability, FTMO MC vs 70%
  Step 4 — feature importance (collapse check: single-feature dominance ⇒ null)

Outputs:
  results/family6_ml_combo.json
  _audit/family6_ml_feature_combo_2026-05.md (separate file, written from JSON)
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))

from strategy.ml_features import (FEATURE_NAMES, FeatureSpec, InstrumentSpec,  # noqa: E402
                                  build_panel)
from strategy.onc_clustering import onc, summarise_onc                          # noqa: E402
from strategy.ml_pipeline import (build_lgbm, build_logistic,                   # noqa: E402
                                  cpcv_oos_sharpe_distribution,
                                  walk_forward_returns_matrix,
                                  backtest_predictions, position_from_proba)
from strategy.pbo import probability_of_backtest_overfitting                    # noqa: E402
from engine.ftmo_first_passage import (combined_pass_prob_empirical, tail_dd_gate,  # noqa: E402
                                       annual_to_daily_sharpe,
                                       combined_pass_prob_closed_form)
from engine.cfd_costs import CFDCostModel                                       # noqa: E402
sys.path.insert(0, str(REPO))
from dsr import deflated_sharpe_ratio                                           # noqa: E402

RES = HERE / "results"
RES.mkdir(exist_ok=True)

IS_START, IS_END = "2022-01-01", "2024-12-31"
HOLD_START, HOLD_END = "2025-01-01", "2026-05-29"

UNIVERSE = [
    InstrumentSpec("EURUSD", hours=(7, 20),  freq="15min", label_h=1),
    InstrumentSpec("XAUUSD", hours=(7, 20),  freq="15min", label_h=1),
    InstrumentSpec("US500",  hours=(13, 21), freq="15min", label_h=1),
    InstrumentSpec("GER40",  hours=(7, 20),  freq="15min", label_h=1),
]


def bars_per_year(spec: InstrumentSpec) -> int:
    hrs = spec.hours[1] - spec.hours[0]
    return int(hrs * 4 * 252)


# ─────────────────────────────────────────────────────────────────────────────
# Per-instrument pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_instrument(spec: InstrumentSpec) -> dict:
    print(f"\n=== {spec.symbol} {spec.freq} hours={spec.hours} ===")
    t0 = time.time()
    full = build_panel(spec, start=IS_START, end=HOLD_END).dropna()
    is_df = full.loc[IS_START:IS_END].copy()
    ho_df = full.loc[HOLD_START:HOLD_END].copy()
    print(f"  loaded: {time.time()-t0:.1f}s | IS {len(is_df):>6} | HO {len(ho_df):>5}")

    # ── Step 0: ONC clustering on IS features ────────────────────────────────
    corr = is_df[FEATURE_NAMES].corr()
    onc_res = onc(corr, hard_merge_threshold=0.8, min_k=2, max_k=9)
    reps = onc_res.representatives
    print(summarise_onc(onc_res))
    print(f"  → {len(reps)} representative features: {reps}")

    X_is = is_df[reps].values
    y_is = (is_df["y_fwd_1"].values > 0).astype(int)
    yfwd_is = is_df["y_fwd_1"].values
    bpy = bars_per_year(spec)

    # ── Step 1+2: DECISIVE diagnostic — CPCV gross OOS Sharpe ──────────────
    print("  [CPCV] logistic L2 ...")
    t = time.time()
    cpcv_log = cpcv_oos_sharpe_distribution(
        X_is, y_is, yfwd_is, is_df.index,
        model_factory=lambda: build_logistic(C=1.0),
        bars_per_year=bpy, target_n_paths=20, target_train_size=5000,
        verbose=False)
    print(f"    done {time.time()-t:.1f}s — mean={cpcv_log.mean:.3f} "
          f"median={cpcv_log.median:.3f} CI5-95=[{cpcv_log.ci_5_95[0]:.2f},{cpcv_log.ci_5_95[1]:.2f}]")

    print("  [CPCV] LightGBM depth=3 ...")
    t = time.time()
    cpcv_gbm = cpcv_oos_sharpe_distribution(
        X_is, y_is, yfwd_is, is_df.index,
        model_factory=lambda: build_lgbm(max_depth=3, num_leaves=7,
                                         min_child_samples=400, learning_rate=0.05,
                                         n_estimators=150, reg_lambda=1.0),
        bars_per_year=bpy, target_n_paths=20, target_train_size=5000,
        verbose=False)
    print(f"    done {time.time()-t:.1f}s — mean={cpcv_gbm.mean:.3f} "
          f"median={cpcv_gbm.median:.3f} CI5-95=[{cpcv_gbm.ci_5_95[0]:.2f},{cpcv_gbm.ci_5_95[1]:.2f}]")

    # ── PBO via walk-forward over K variants on IS ───────────────────────────
    variants = [
        ("logreg_C0.01",    lambda: build_logistic(C=0.01), 0.0),
        ("logreg_C0.1",     lambda: build_logistic(C=0.1),  0.0),
        ("logreg_C1.0",     lambda: build_logistic(C=1.0),  0.0),
        ("logreg_C10",      lambda: build_logistic(C=10.0), 0.0),
        ("gbm_d3_lr0.03",   lambda: build_lgbm(max_depth=3, learning_rate=0.03,
                                               n_estimators=200, min_child_samples=400), 0.0),
        ("gbm_d3_lr0.05",   lambda: build_lgbm(max_depth=3, learning_rate=0.05,
                                               n_estimators=150, min_child_samples=400), 0.0),
        ("gbm_d2_lr0.05",   lambda: build_lgbm(max_depth=2, learning_rate=0.05,
                                               n_estimators=150, min_child_samples=400), 0.0),
        ("gbm_d3_lr0.05_thr0.05", lambda: build_lgbm(max_depth=3, learning_rate=0.05,
                                                     n_estimators=150, min_child_samples=400), 0.05),
    ]
    print(f"  [WF] {len(variants)} variants, 5 folds ...")
    t = time.time()
    wf = walk_forward_returns_matrix(
        X_is, y_is, yfwd_is, variants, bars_per_year=bpy, n_folds=5, purge_size=5)
    print(f"    done {time.time()-t:.1f}s — per-variant Sharpes:")
    for n, s in zip(wf.variant_names, wf.sharpes_per_variant):
        print(f"      {n:<26s} {s:>+7.3f}")
    pbo = probability_of_backtest_overfitting(wf.returns_matrix, S=16)
    print(f"    PBO = {pbo.pbo:.3f} (gate < 0.5 = {pbo.pbo < 0.5}; ideal < 0.2)")

    # ── Pick the BEST variant from IS (objectively on IS WF Sharpe) ─────────
    best_k = int(np.argmax(wf.sharpes_per_variant))
    best_name = wf.variant_names[best_k]
    best_factory, best_thresh = variants[best_k][1], variants[best_k][2]
    print(f"  → BEST IS variant: {best_name} (WF Sharpe {wf.sharpes_per_variant[best_k]:+.3f})")

    # ── Cost gate + per-variant net (using full IS retrain) ─────────────────
    cost_model = CFDCostModel(spec.symbol, markup=3.0)
    is_close = is_df["close"]
    is_spread = is_df["spread"]
    # IS gross/cost from the best variant (in-fold sums of WF returns)
    is_gross_ann = wf.sharpes_per_variant[best_k] * 0.0  # placeholder; compute properly below
    is_gross_daily_var = pd.Series(wf.returns_matrix[:, best_k]).groupby(
        np.arange(len(wf.returns_matrix)) // (bpy // 252)
    ).sum()  # rough daily aggregation (WF is contiguous OOS)

    # ── ONCE: full IS retrain → hold-out (sealed) ──────────────────────────
    print("  [SEALED HOLD-OUT] retrain on full IS, predict 2025-2026-05 ...")
    t = time.time()
    model = best_factory()
    model.fit(X_is, y_is)
    X_ho = ho_df[reps].values
    p_up_ho = model.predict_proba(X_ho)[:, 1]
    bt_ho = backtest_predictions(
        proba_up=pd.Series(p_up_ho, index=ho_df.index),
        y_fwd=ho_df["y_fwd_1"], close=ho_df["close"], spread=ho_df["spread"],
        symbol=spec.symbol, threshold=best_thresh, markup=3.0,
        bars_per_year=bpy)
    print(f"    done {time.time()-t:.1f}s — HO net Sharpe={bt_ho.metrics['ann_sharpe']:.3f}, "
          f"gross={bt_ho.metrics['ann_return_gross']*100:.1f}%/yr, cost={bt_ho.metrics['ann_cost_drag']*100:.1f}%/yr")

    # Also backtest on IS for per-year stability + cost-gate IS view
    p_up_is = model.predict_proba(X_is)[:, 1]  # NB: training fit — IS view for cost ratio only
    bt_is = backtest_predictions(
        proba_up=pd.Series(p_up_is, index=is_df.index),
        y_fwd=is_df["y_fwd_1"], close=is_df["close"], spread=is_df["spread"],
        symbol=spec.symbol, threshold=best_thresh, markup=3.0,
        bars_per_year=bpy)
    is_gross_ann = bt_is.metrics["ann_return_gross"]
    is_cost_ann = bt_is.metrics["ann_cost_drag"]
    is_cost_ratio = is_gross_ann / max(1e-9, is_cost_ann)

    # ── Walk-forward gross daily (best variant) for IS metrics ──────────────
    # rebuild a date-indexed gross OOS bar series for the best variant
    # We need to know which bars of IS belong to walk-forward OOS folds; rebuild.
    # Simpler: re-derive bar dates per fold via the same partition.
    T_is = len(X_is)
    fold_size = T_is // (5 + 1)
    init_train_end = fold_size
    oos_bar_idx_lists = []
    for f in range(5):
        tr_end = init_train_end + f * fold_size
        te_start = tr_end + 5
        te_end = min(te_start + fold_size, T_is)
        if te_end - te_start >= 50:
            oos_bar_idx_lists.append(np.arange(te_start, te_end))
    oos_idx = np.concatenate(oos_bar_idx_lists)
    oos_bar_dates = is_df.index[oos_idx]
    oos_bar_gross = wf.returns_matrix[:len(oos_idx), best_k]
    oos_gross_daily = pd.Series(oos_bar_gross, index=oos_bar_dates)\
        .groupby(lambda d: d.normalize()).sum()

    # ── DSR on hold-out net daily (the publishable Sharpe) ──────────────────
    n_trials_honest = onc_res.n_clusters * len(variants)  # clusters × hyperparam variants
    dsr_ho = deflated_sharpe_ratio(
        bt_ho.daily_net.values, n_trials=n_trials_honest,
        periods_per_year=252, rf=0.02, mean_sr_trials=0.0, std_sr_trials=1.0)
    print(f"  DSR (HO net, n_trials={n_trials_honest}): {dsr_ho['dsr']:.3f}  passed={dsr_ho['passed']}")

    # ── Distribution gates on HO daily net ──────────────────────────────────
    kurt = bt_ho.metrics["excess_kurtosis"]
    print(f"  excess_kurtosis HO net = {kurt:.2f} (gate < 3 = {kurt < 3})")
    tail_ho = tail_dd_gate(bt_ho.daily_net.values, threshold=0.08, window=60,
                           n_paths=20000, seed=7)
    print(f"  tail-DD P(touch -8%/60d) = {tail_ho['p_floor_excursion']*100:.1f}% "
          f"(gate < 10% = {tail_ho['gate_pass']})")

    # ── FTMO Monte-Carlo (honest, daily series scaled to σd≈1%) ─────────────
    # vol-scale the HO net daily series to σd=1% before MC (matches Phase 2 protocol)
    rho_daily = bt_ho.daily_net.values
    sd = rho_daily.std(ddof=1) or 1e-9
    target_sd = 0.01
    rho_scaled = rho_daily * (target_sd / sd)
    ftmo = combined_pass_prob_empirical(rho_scaled, n_paths=20000, max_days=None, seed=42)
    print(f"  FTMO P(pass) combined = {ftmo['p_combined']*100:.1f}% "
          f"CI95=[{ftmo['p_combined_ci95'][0]*100:.1f}%, {ftmo['p_combined_ci95'][1]*100:.1f}%]")

    # ── Closed-form sanity (uses the HO net daily Sharpe @ σd=1%) ───────────
    sd_daily = bt_ho.metrics["daily_sharpe"]
    cf = combined_pass_prob_closed_form(sd_daily, sigma_d=0.01)
    print(f"  Closed-form @ σd=1%: P1={cf['p1']*100:.1f}%, P2={cf['p2']*100:.1f}%, "
          f"comb={cf['p_combined']*100:.1f}%")

    # ── Per-year sign-flip (HO) ─────────────────────────────────────────────
    per_year = bt_ho.daily_net.groupby(bt_ho.daily_net.index.year).apply(
        lambda r: float(r.mean() / r.std(ddof=1) * np.sqrt(252)) if r.std(ddof=1) > 0 else 0.0)
    print(f"  per-year Sharpe HO: {dict(per_year.round(3))}")

    # ── Feature importance (collapse check) — logistic coefs + GBM gain ─────
    import_log = {}
    try:
        logit = build_logistic(C=1.0)
        logit.fit(X_is, y_is)
        coefs = dict(zip(reps, logit.named_steps["clf"].coef_[0].tolist()))
        import_log = {k: abs(v) for k, v in coefs.items()}
    except Exception:
        pass
    import_gbm = {}
    try:
        gbm = build_lgbm(max_depth=3, learning_rate=0.05, n_estimators=150,
                         min_child_samples=400)
        gbm.fit(X_is, y_is)
        gains = gbm.booster_.feature_importance(importance_type="gain")
        import_gbm = dict(zip(reps, [float(g) for g in gains]))
    except Exception:
        pass
    print(f"  feature importance (logreg |coef|): {import_log}")
    print(f"  feature importance (gbm gain): {import_gbm}")

    return {
        "symbol": spec.symbol,
        "freq": spec.freq,
        "hours": list(spec.hours),
        "bars_per_year": bpy,
        "n_is": int(len(is_df)),
        "n_ho": int(len(ho_df)),
        "onc": {
            "n_clusters": onc_res.n_clusters,
            "silhouette": onc_res.silhouette,
            "members": {str(k): v for k, v in onc_res.members.items()},
            "representatives": reps,
            "hard_merges_count": len(onc_res.hard_merged),
        },
        "cpcv_logistic": {
            "mean": cpcv_log.mean, "median": cpcv_log.median, "std": cpcv_log.std,
            "ci_5_95": list(cpcv_log.ci_5_95), "n_paths": cpcv_log.n_paths,
            "n_folds": cpcv_log.n_folds, "n_test_folds": cpcv_log.n_test_folds,
            "purge_size": cpcv_log.purge_size, "embargo_size": cpcv_log.embargo_size,
            "sharpes": cpcv_log.sharpes.tolist(),
        },
        "cpcv_gbm": {
            "mean": cpcv_gbm.mean, "median": cpcv_gbm.median, "std": cpcv_gbm.std,
            "ci_5_95": list(cpcv_gbm.ci_5_95), "n_paths": cpcv_gbm.n_paths,
            "sharpes": cpcv_gbm.sharpes.tolist(),
        },
        "wf_variants": {
            "names": wf.variant_names,
            "sharpes": wf.sharpes_per_variant.tolist(),
            "n_folds": wf.n_folds,
        },
        "pbo": {
            "pbo": pbo.pbo,
            "n_variants": pbo.n_variants,
            "n_combinations": pbo.n_combinations,
            "n_slices": pbo.n_slices,
        },
        "best_variant": best_name,
        "best_variant_is_sharpe_wf": float(wf.sharpes_per_variant[best_k]),
        "cost_gate": {
            "is_gross_ann": float(is_gross_ann),
            "is_cost_ann": float(is_cost_ann),
            "is_cost_ratio": float(is_cost_ratio),
            "is_cost_gate_pass": bool(is_cost_ratio > 3.0),
        },
        "holdout": {
            "ann_sharpe_net": bt_ho.metrics["ann_sharpe"],
            "daily_sharpe": bt_ho.metrics["daily_sharpe"],
            "ann_return_net": bt_ho.metrics["ann_return_net"],
            "ann_return_gross": bt_ho.metrics["ann_return_gross"],
            "ann_cost_drag": bt_ho.metrics["ann_cost_drag"],
            "win_rate_daily": bt_ho.metrics["win_rate_daily"],
            "excess_kurtosis": kurt,
            "skew": bt_ho.metrics["skew"],
            "max_dd": bt_ho.metrics["max_dd"],
            "n_days": bt_ho.metrics["n_days"],
            "avg_daily_turnover": bt_ho.metrics["avg_daily_turnover"],
            "per_year_sharpe": {str(int(y)): float(s) for y, s in per_year.items()},
        },
        "dsr_holdout": {
            "dsr": dsr_ho["dsr"],
            "passed": dsr_ho["passed"],
            "n_trials": n_trials_honest,
            "sharpe": dsr_ho["sharpe"],
            "sr_benchmark": dsr_ho["sr_benchmark"],
        },
        "tail_dd_holdout": tail_ho,
        "ftmo_mc": ftmo,
        "ftmo_closed_form_sigma1pct": cf,
        "feature_importance": {
            "logreg_abs_coef": import_log,
            "gbm_gain": import_gbm,
        },
    }


def main():
    print("FTMO Family-6 ML feature-combo sprint")
    print(f"IS  : {IS_START} → {IS_END}")
    print(f"HO  : {HOLD_START} → {HOLD_END} (sealed; touched once)")
    print()
    out = {"universe": [s.symbol for s in UNIVERSE], "instruments": {}}
    for spec in UNIVERSE:
        try:
            out["instruments"][spec.symbol] = run_instrument(spec)
        except Exception as e:
            print(f"  ERROR on {spec.symbol}: {e!r}")
            out["instruments"][spec.symbol] = {"error": repr(e)}
    p = RES / "family6_ml_combo.json"
    p.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote {p}")


if __name__ == "__main__":
    main()
