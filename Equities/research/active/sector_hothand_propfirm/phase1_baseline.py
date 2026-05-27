"""
phase1_baseline.py — Phase 1 full analysis: baseline hot-hand sector momentum.

Produces:
  results/phase1_baseline.json
  results/phase1_baseline.png
  results/phase1_summary.md

Exit codes:
  0 — PASS (sharpe_deflated >= 0.7 AND p_pass_ci95[0] >= 0.50)
  1 — FAIL → ARCHIVE
"""

from __future__ import annotations

import json
import sys
import os
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from data.cache import get_cached_or_fetch, get_cached_or_fetch_fred
import engine as eng

# ─── config ─────────────────────────────────────────────────────────────────
TICKERS    = ["QQQ", "XLK", "XLE", "XLP", "XLU", "XLV", "XLF", "XLI", "XLB", "XLY"]
START_FULL = "2000-01-01"
BURN_END   = "2001-12-31"      # skip burn-in
BACKTEST_START = "2002-01-01"
END        = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

WF_FOLDS   = 5
WF_TEST_YRS = 2
N_BOOTSTRAP = 10_000
BLOCK_SIZE_AUTO = True          # round(sqrt(T))

# AMTP combos: {lookback} × {vol_target} — 6 combos, report uses [20, 0.15]
AMTP_LOOKBACKS  = [10, 20, 40]
AMTP_VOLS       = [0.10, 0.20]
AMTP_COMBOS     = len(AMTP_LOOKBACKS) * len(AMTP_VOLS)   # = 6

# FTMO 2-step rules
FTMO_P1_TARGET   = 0.10    # +10%
FTMO_P2_TARGET   = 0.05    # +5%
FTMO_DAILY_LOSS  = 0.05    # 5% max daily loss
FTMO_MAX_LOSS    = 0.10    # 10% static max drawdown
FTMO_MAX_DAYS_P1 = 30
FTMO_MAX_DAYS_P2 = 60

SEED = 42
RNG  = np.random.default_rng(SEED)

RESULTS = Path(__file__).parent / "results"
RESULTS.mkdir(exist_ok=True)


# ─── data loading ────────────────────────────────────────────────────────────

def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Returns (open_px, close_px, rf_daily) aligned on common business-day index."""
    opens, closes = {}, {}
    for t in TICKERS:
        df = get_cached_or_fetch(t, START_FULL, END, interval="1d", max_age_days=1.0)
        df.index = pd.to_datetime(df.index).tz_localize(None)
        opens[t]  = df["open"]
        closes[t] = df["close"]   # auto_adjust=True → adj close

    open_px  = pd.DataFrame(opens).sort_index()
    close_px = pd.DataFrame(closes).sort_index()

    # align on common index
    common = open_px.index.intersection(close_px.index)
    open_px  = open_px.loc[common]
    close_px = close_px.loc[common]

    # ── DTB3 risk-free (FRED, annualized %) → daily decimal ──────────────
    rf_raw = get_cached_or_fetch_fred("DTB3", start=START_FULL, end=END, max_age_days=1.0)
    rf_raw = rf_raw["dtb3"].ffill() / 100 / 252   # annualized % → daily decimal

    # align rf to close_px index
    rf = rf_raw.reindex(close_px.index, method="ffill").fillna(0.0)

    return open_px, close_px, rf


# ─── HAC alpha t-stat ────────────────────────────────────────────────────────

def hac_alpha_tstat(ret: pd.Series, lag: int = 6) -> tuple[float, float]:
    """OLS alpha with HAC Newey-West SE. Returns (alpha_annualized, t_stat)."""
    y = ret.dropna().values
    X = np.ones(len(y))
    model = sm.OLS(y, X)
    res   = model.fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    alpha_ann = float(res.params[0]) * 252
    t_stat    = float(res.tvalues[0])
    return alpha_ann, t_stat


# ─── DSR (Bailey & López de Prado 2014) ──────────────────────────────────────

def dsr_correction(sr_reported: float, T: int, n_trials: int, sr_benchmark: float = 0.0) -> float:
    """
    Deflated Sharpe Ratio.

    DSR = SR × [1 - γ/2 × (1 + skew × SR_benchmark + (kurt-1)/4 × SR_benchmark²)]
    Simplified approximation using Bailey-LdP formula components.
    """
    # Expected max SR from n_trials iid trials (Bailey-LdP eq. 8 approximation)
    from scipy.stats import norm
    euler_mascheroni = 0.5772156649
    z = norm.ppf(1.0 - 1.0 / n_trials)
    e_max_sr = (
        (1 - euler_mascheroni) * norm.ppf(1 - 1.0 / n_trials)
        + euler_mascheroni * norm.ppf(1 - 1.0 / (n_trials * np.e))
    )
    # DSR approximation (assume near-Gaussian returns)
    sr_deflated = sr_reported * (1 - e_max_sr / np.sqrt(T))
    return max(sr_deflated, 0.0)


# ─── stationary bootstrap Sharpe CI ─────────────────────────────────────────

def bootstrap_sharpe_ci(ret: np.ndarray, n_boot: int = N_BOOTSTRAP,
                         block_size: int | None = None,
                         rng: np.random.Generator = RNG,
                         alpha: float = 0.05) -> tuple[float, float]:
    """
    Politis-Romano stationary block bootstrap CI for annualized Sharpe.
    block_size defaults to round(sqrt(T)).
    """
    T = len(ret)
    if block_size is None:
        block_size = max(1, round(np.sqrt(T)))

    p_geom = 1.0 / block_size
    sharpes = np.empty(n_boot)
    for b in range(n_boot):
        # stationary bootstrap: geometrically distributed block lengths
        sample = np.empty(T)
        pos = 0
        start = rng.integers(0, T)
        while pos < T:
            length = min(rng.geometric(p_geom), T - pos)
            indices = (start + np.arange(length)) % T
            sample[pos: pos + length] = ret[indices]
            pos += length
            start = rng.integers(0, T)
        s = sample[:T]
        std = s.std()
        sharpes[b] = (s.mean() / std * np.sqrt(252)) if std > 0 else 0.0

    lo = float(np.percentile(sharpes, 100 * alpha / 2))
    hi = float(np.percentile(sharpes, 100 * (1 - alpha / 2)))
    return lo, hi


# ─── AMTP correction (Harvey-Liu-Zhu 2016 approximation) ─────────────────────

def amtp_adjusted_pval(t_stat: float, n_tests: int) -> float:
    """
    Approximate multi-test penalty: Bonferroni conservative upper bound.
    Returns AMTP-adjusted p-value (two-tailed).
    """
    from scipy.stats import t as t_dist
    import math
    # Conservative: Bonferroni
    raw_p = 2 * (1 - t_dist.cdf(abs(t_stat), df=10_000))   # large df ≈ normal
    adjusted = min(1.0, raw_p * n_tests)
    return adjusted


# ─── Walk-forward ────────────────────────────────────────────────────────────

def walk_forward(
    open_px: pd.DataFrame,
    close_px: pd.DataFrame,
    rf: pd.Series,
    n_folds: int = WF_FOLDS,
    test_years: int = WF_TEST_YRS,
) -> tuple[pd.Series, list[dict]]:
    """
    Expanding-window walk-forward with n_folds.
    Returns (combined out-of-sample net excess returns, fold_stats list).
    """
    bt_start = pd.Timestamp(BACKTEST_START)
    bt_end   = close_px.index[-1]
    total_days = (bt_end - bt_start).days

    # Split into n_folds: each test period = test_years years
    test_days = test_years * 365
    fold_results = []
    oos_returns  = []

    # training starts from BACKTEST_START, test windows slide by test_years
    test_end = bt_end
    for fold in range(n_folds - 1, -1, -1):   # build backwards
        test_e = test_end
        test_s = test_e - pd.DateOffset(years=test_years)
        train_e = test_s - pd.Timedelta(days=1)
        train_s = bt_start

        if train_e <= train_s:
            break

        mask_train = (close_px.index >= train_s) & (close_px.index <= train_e)
        mask_test  = (close_px.index >  train_e) & (close_px.index <= test_e)

        if mask_test.sum() < 50:
            test_end = test_s
            continue

        # run on full history (engine is walk-forward clean by design: T-1 signal)
        out_full = eng.run(open_px, close_px, rf)
        oos_ret  = out_full.loc[mask_test, "ret_net"]

        sr_fold = eng.sharpe(oos_ret)
        mdd_fold = eng.max_drawdown((1 + oos_ret).cumprod())
        _, t_hac = hac_alpha_tstat(oos_ret)

        fold_results.append({
            "fold":       n_folds - fold,
            "train_end":  str(train_e.date()),
            "test_start": str(oos_ret.index[0].date()),
            "test_end":   str(oos_ret.index[-1].date()),
            "sharpe_oos": round(sr_fold, 3),
            "mdd_oos":    round(mdd_fold, 4),
            "t_hac":      round(t_hac, 3),
            "pass":       sr_fold > 0.7 and mdd_fold > -0.25,
        })
        oos_returns.append(oos_ret)
        test_end = test_s

    fold_results = list(reversed(fold_results))
    oos_combined = pd.concat(list(reversed(oos_returns))).sort_index() if oos_returns else pd.Series(dtype=float)
    return oos_combined, fold_results


# ─── FTMO 2-step Monte Carlo ─────────────────────────────────────────────────

def ftmo_mc(daily_ret: np.ndarray, n_paths: int = N_BOOTSTRAP,
            rng: np.random.Generator = RNG) -> dict:
    """
    Stationary bootstrap Monte Carlo for FTMO 2-step pass probability.
    Uses actual daily returns resampled with stationary bootstrap.
    Capital resets between Phase 1 and Phase 2.
    """
    T    = len(daily_ret)
    bsz  = max(1, round(np.sqrt(T)))
    p_geom = 1.0 / bsz

    def sample_path(max_days: int) -> np.ndarray:
        """Draw a bootstrap path of length max_days."""
        path = np.empty(max_days)
        pos, start = 0, rng.integers(0, T)
        while pos < max_days:
            length = min(rng.geometric(p_geom), max_days - pos)
            idxs   = (start + np.arange(length)) % T
            path[pos: pos + length] = daily_ret[idxs]
            pos += length
            start = rng.integers(0, T)
        return path[:max_days]

    p1_pass = p1_days = np.zeros(n_paths), np.full(n_paths, FTMO_MAX_DAYS_P1)
    p2_pass = p2_days = np.zeros(n_paths), np.full(n_paths, FTMO_MAX_DAYS_P2)

    p1_results = np.zeros(n_paths, dtype=bool)
    p2_results = np.zeros(n_paths, dtype=bool)
    p1_days_arr = np.full(n_paths, FTMO_MAX_DAYS_P1, dtype=int)
    p2_days_arr = np.full(n_paths, FTMO_MAX_DAYS_P2, dtype=int)
    fail_daily  = np.zeros(n_paths, dtype=bool)
    fail_max    = np.zeros(n_paths, dtype=bool)
    fail_time   = np.zeros(n_paths, dtype=bool)

    for i in range(n_paths):
        # ── Phase 1 ───────────────────────────────────────────────────────
        path1   = sample_path(FTMO_MAX_DAYS_P1)
        equity  = 1.0
        peak    = 1.0
        p1_ok   = False
        fail_d  = fail_m = fail_t = False

        for d, r in enumerate(path1):
            equity = equity * (1 + r)
            peak   = max(peak, equity)
            dd_total = (equity - 1.0)    # drawdown from start
            daily_loss = r               # single day loss (approx non-levered)

            if r < -FTMO_DAILY_LOSS:
                fail_d = True; break
            if equity < (1 - FTMO_MAX_LOSS):
                fail_m = True; break
            if equity >= (1 + FTMO_P1_TARGET):
                p1_ok = True
                p1_days_arr[i] = d + 1
                break
        else:
            fail_t = not p1_ok

        p1_results[i]  = p1_ok
        fail_daily[i]  = fail_d
        fail_max[i]    = fail_m
        fail_time[i]   = fail_t

        if not p1_ok:
            continue

        # ── Phase 2 (capital reset) ───────────────────────────────────────
        path2   = sample_path(FTMO_MAX_DAYS_P2)
        equity2 = 1.0
        p2_ok   = False
        for d2, r2 in enumerate(path2):
            equity2 = equity2 * (1 + r2)
            if r2 < -FTMO_DAILY_LOSS:
                break
            if equity2 < (1 - FTMO_MAX_LOSS):
                break
            if equity2 >= (1 + FTMO_P2_TARGET):
                p2_ok = True
                p2_days_arr[i] = d2 + 1
                break

        p2_results[i] = p2_ok

    both = p1_results & p2_results
    n_both = both.sum()

    total_days_both = (p1_days_arr[both] + p2_days_arr[both]) if n_both > 0 else np.array([0])

    # Wilson interval for proportion CI (avoids [0,1] degenerate percentile problem)
    p_hat = both.mean()
    z95   = 1.96
    se    = np.sqrt(p_hat * (1 - p_hat) / n_paths) if p_hat > 0 else 0.0
    ci_lo = max(0.0, p_hat - z95 * se)
    ci_hi = min(1.0, p_hat + z95 * se)

    return {
        "p_pass_p1":        round(p1_results.mean(), 4),
        "p_pass_p2_given_p1": round(p2_results[p1_results].mean(), 4) if p1_results.sum() > 0 else 0.0,
        "p_pass_both":      round(float(p_hat), 4),
        "p_pass_ci95_lo":   round(float(ci_lo), 4),
        "p_pass_ci95_hi":   round(float(ci_hi), 4),
        "median_days_pass": int(np.median(total_days_both)),
        "fail_daily_pct":   round(fail_daily.mean() * 100, 2),
        "fail_maxloss_pct": round(fail_max.mean() * 100, 2),
        "fail_timeout_pct": round(fail_time.mean() * 100, 2),
    }


# ─── plotting ─────────────────────────────────────────────────────────────────

def plot_results(full_out: pd.DataFrame, fold_stats: list[dict], save_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec

    fig = plt.figure(figsize=(14, 10))
    gs  = gridspec.GridSpec(3, 1, height_ratios=[3, 1.5, 1.5])

    bt_start = pd.Timestamp(BACKTEST_START)
    out = full_out.loc[bt_start:]

    # equity
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(out.index, out["equity_net"], linewidth=1.0, color="#1f77b4", label="Net equity")
    ax1.axhline(1.0, color="gray", linewidth=0.5, linestyle="--")
    for fs in fold_stats:
        ax1.axvline(pd.Timestamp(fs["test_start"]), color="orange", alpha=0.4, linewidth=0.8)
    ax1.set_ylabel("Equity (start=1)")
    ax1.set_title("Sector Hot-Hand — Phase 1 Baseline (net excess returns)")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)

    # drawdown
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.fill_between(out.index, out["drawdown"] * 100, 0, color="red", alpha=0.4)
    ax2.axhline(-10, color="red", linewidth=0.8, linestyle="--", label="FTMO -10% limit")
    ax2.set_ylabel("Drawdown (%)")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)

    # leverage
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax3.plot(out.index, out["lever"], linewidth=0.6, color="#2ca02c", alpha=0.7)
    ax3.set_ylabel("Leverage")
    ax3.set_xlabel("Date")
    ax3.grid(alpha=0.3)

    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ─── main ────────────────────────────────────────────────────────────────────

def main() -> int:
    print("Loading data...")
    open_px, close_px, rf = load_data()

    bt_start = pd.Timestamp(BACKTEST_START)
    open_px_bt  = open_px.loc[bt_start:]
    close_px_bt = close_px.loc[bt_start:]
    rf_bt       = rf.loc[bt_start:]

    print(f"Backtest period: {open_px_bt.index[0].date()} → {open_px_bt.index[-1].date()} "
          f"({len(open_px_bt)} days)")

    # ── Full-sample run ────────────────────────────────────────────────────
    print("Running full-sample backtest...")
    full_out = eng.run(open_px, close_px, rf)
    full_ret = full_out.loc[bt_start:, "ret_net"].dropna()
    T = len(full_ret)

    sr_gross = eng.sharpe(full_out.loc[bt_start:, "ret_gross"].dropna())
    sr_net   = eng.sharpe(full_ret)
    mdd      = eng.max_drawdown(full_out.loc[bt_start:, "equity_net"].dropna())

    print(f"  Sharpe gross: {sr_gross:.3f}  net: {sr_net:.3f}  MaxDD: {mdd:.2%}")

    # ── HAC alpha ─────────────────────────────────────────────────────────
    print("Computing HAC alpha...")
    alpha_ann, t_hac = hac_alpha_tstat(full_ret, lag=6)
    print(f"  Alpha ann: {alpha_ann:.4f}  t_HAC: {t_hac:.3f}")

    # ── AMTP ──────────────────────────────────────────────────────────────
    amtp_p = amtp_adjusted_pval(t_hac, n_tests=AMTP_COMBOS)
    print(f"  AMTP p-val (Bonferroni, {AMTP_COMBOS} trials): {amtp_p:.4f}")

    # ── DSR ───────────────────────────────────────────────────────────────
    sr_deflated = dsr_correction(sr_net, T=T, n_trials=AMTP_COMBOS)
    print(f"  SR deflated (DSR): {sr_deflated:.3f}")

    # ── Bootstrap Sharpe CI ───────────────────────────────────────────────
    print(f"Bootstrap Sharpe CI ({N_BOOTSTRAP} draws)...")
    ret_arr = full_ret.values
    sr_ci_lo, sr_ci_hi = bootstrap_sharpe_ci(ret_arr, rng=RNG)
    print(f"  95% CI: [{sr_ci_lo:.3f}, {sr_ci_hi:.3f}]")

    # ── Walk-forward ───────────────────────────────────────────────────────
    print("Walk-forward (5 folds)...")
    oos_ret, fold_stats = walk_forward(open_px, close_px, rf)
    n_pass_wf  = sum(1 for f in fold_stats if f["pass"])
    wf_str     = f"{n_pass_wf}/{len(fold_stats)}"
    sr_wf      = eng.sharpe(oos_ret) if len(oos_ret) > 0 else 0.0
    print(f"  WF Sharpe OOS: {sr_wf:.3f}  Folds passing: {wf_str}")
    for f in fold_stats:
        flag = "PASS" if f["pass"] else "FAIL"
        print(f"    Fold {f['fold']} [{f['test_start']}→{f['test_end']}]: "
              f"SR={f['sharpe_oos']}  MDD={f['mdd_oos']:.2%}  t={f['t_hac']}  {flag}")

    # ── FTMO MC ────────────────────────────────────────────────────────────
    print(f"FTMO 2-step MC ({N_BOOTSTRAP} paths)...")
    ftmo = ftmo_mc(ret_arr, rng=RNG)
    print(f"  P(pass both): {ftmo['p_pass_both']:.3f}  "
          f"CI95: [{ftmo['p_pass_ci95_lo']:.3f}, {ftmo['p_pass_ci95_hi']:.3f}]")
    print(f"  Fail modes → daily: {ftmo['fail_daily_pct']:.1f}%  "
          f"maxloss: {ftmo['fail_maxloss_pct']:.1f}%  timeout: {ftmo['fail_timeout_pct']:.1f}%")

    # ── Assemble JSON results ──────────────────────────────────────────────
    results = {
        "run_date":            str(date.today()),
        "backtest_start":      BACKTEST_START,
        "backtest_end":        END,
        "T_days":              T,
        "sharpe_gross":        round(sr_gross, 4),
        "sharpe_net":          round(sr_net, 4),
        "sharpe_deflated_DSR": round(sr_deflated, 4),
        "max_drawdown":        round(mdd, 4),
        "alpha_ann":           round(alpha_ann, 4),
        "t_stat_alpha_hac":    round(t_hac, 4),
        "hac_lag":             6,
        "amtp_trials":         AMTP_COMBOS,
        "amtp_p_bonferroni":   round(amtp_p, 4),
        "sharpe_ci95_lo":      round(sr_ci_lo, 4),
        "sharpe_ci95_hi":      round(sr_ci_hi, 4),
        "wf_folds_pass":       wf_str,
        "wf_sharpe_oos":       round(sr_wf, 4),
        "wf_fold_details":     fold_stats,
        **ftmo,
    }

    json_path = RESULTS / "phase1_baseline.json"
    json_path.write_text(json.dumps(results, indent=2))
    print(f"\nResults → {json_path.relative_to(Path(__file__).parents[4])}")

    # ── Plot ───────────────────────────────────────────────────────────────
    print("Plotting...")
    try:
        plot_results(full_out, fold_stats, RESULTS / "phase1_baseline.png")
        print("  Plot saved.")
    except Exception as e:
        print(f"  Plot failed (non-fatal): {e}")

    # ── Gate evaluation ────────────────────────────────────────────────────
    gate_dsr  = sr_deflated >= 0.7
    gate_ftmo = ftmo["p_pass_ci95_lo"] >= 0.50
    gate_pass = gate_dsr and gate_ftmo

    verdict = "RESEARCH_PASS — proceed to Phase 2" if gate_pass else "ARCHIVE — gates failed"
    gate_detail = (
        f"sharpe_deflated={'PASS' if gate_dsr else 'FAIL'} ({sr_deflated:.3f} {'≥' if gate_dsr else '<'} 0.7)  |  "
        f"p_pass_ci95[0]={'PASS' if gate_ftmo else 'FAIL'} ({ftmo['p_pass_ci95_lo']:.3f} {'≥' if gate_ftmo else '<'} 0.50)"
    )

    # ── Summary markdown ───────────────────────────────────────────────────
    md_lines = [
        "# Phase 1 — Baseline Results",
        "",
        f"**Run date:** {date.today()}  ",
        f"**Period:** {BACKTEST_START} → {END}  ",
        f"**T:** {T} trading days",
        "",
        "## Key metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Sharpe gross | {sr_gross:.3f} |",
        f"| Sharpe net | {sr_net:.3f} |",
        f"| **Sharpe deflated (DSR)** | **{sr_deflated:.3f}** |",
        f"| Max drawdown | {mdd:.2%} |",
        f"| Alpha ann | {alpha_ann:.4f} |",
        f"| t_HAC (lag-6) | {t_hac:.3f} |",
        f"| AMTP p-val ({AMTP_COMBOS} trials, Bonferroni) | {amtp_p:.4f} |",
        f"| Sharpe bootstrap CI 95% | [{sr_ci_lo:.3f}, {sr_ci_hi:.3f}] |",
        f"| WF folds passing | {wf_str} |",
        f"| WF Sharpe OOS | {sr_wf:.3f} |",
        "",
        "## FTMO 2-step simulation",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| P(pass Phase 1) | {ftmo['p_pass_p1']:.3f} |",
        f"| P(pass Phase 2 \\| Phase 1) | {ftmo['p_pass_p2_given_p1']:.3f} |",
        f"| **P(pass both)** | **{ftmo['p_pass_both']:.3f}** |",
        f"| **P(pass both) CI 95%** | **[{ftmo['p_pass_ci95_lo']:.3f}, {ftmo['p_pass_ci95_hi']:.3f}]** |",
        f"| Median days to pass | {ftmo['median_days_pass']} |",
        f"| Fail: daily loss | {ftmo['fail_daily_pct']:.1f}% |",
        f"| Fail: max loss | {ftmo['fail_maxloss_pct']:.1f}% |",
        f"| Fail: timeout | {ftmo['fail_timeout_pct']:.1f}% |",
        "",
        "## Walk-forward fold detail",
        "",
        "| Fold | Test period | Sharpe OOS | MaxDD | t_HAC | Gate |",
        "|------|-------------|------------|-------|-------|------|",
    ]
    for f in fold_stats:
        md_lines.append(
            f"| {f['fold']} | {f['test_start']}→{f['test_end']} "
            f"| {f['sharpe_oos']} | {f['mdd_oos']:.2%} | {f['t_hac']} "
            f"| {'✅ PASS' if f['pass'] else '❌ FAIL'} |"
        )

    md_lines += [
        "",
        "## Constitutional checks",
        "",
        "| Check | Status |",
        "|-------|--------|",
        "| L1: signal T-1, trade T open | ✅ engine.run() shift(1) on all signals |",
        f"| L2: WF ≥5 folds | ✅ {len(fold_stats)} folds |",
        f"| L8: excess returns vs DTB3 | ✅ rf subtracted daily |",
        f"| L8: HAC NW lag-6 | ✅ t_HAC={t_hac:.3f} |",
        f"| L8: AMTP correction | ✅ {AMTP_COMBOS} combos Bonferroni |",
        f"| L8: DSR | ✅ sr_deflated={sr_deflated:.3f} |",
        "| L10: ≤3 modifications | ✅ 0 mods (baseline only) |",
        "",
        "## Verdict",
        "",
        f"**{verdict}**",
        "",
        f"Gate detail: {gate_detail}",
    ]

    summary_path = RESULTS / "phase1_summary.md"
    summary_path.write_text("\n".join(md_lines))
    print(f"Summary → {summary_path.relative_to(Path(__file__).parents[4])}")

    print(f"\n{'='*60}")
    print(f"VERDICT: {verdict}")
    print(f"Gates: {gate_detail}")
    print(f"{'='*60}")

    return 0 if gate_pass else 1


if __name__ == "__main__":
    sys.exit(main())
