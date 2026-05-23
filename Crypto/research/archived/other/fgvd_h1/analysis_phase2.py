"""
FGVD H1 — Phase 2 IC test block.

Tests A, B, C (pre-registered, see HYPOTHESIS.md):
  A: Naive price mean-reversion  = -z(Δprice_7d)
  B: F&G velocity standalone     = z(ΔF&G_7d)
  C: FGVD combined               = z(ΔF&G_7d) - z(Δprice_7d)  ← hypothesis

Decomposition decision rules (D1, D2, D3) evaluated before IC magnitude gates.
Orthogonality check vs TSMOM-28d.
Results saved to data/phase2_results.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ── repo root on path ───────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parents[5]
sys.path.insert(0, str(REPO_ROOT))
# fetch_data is in same directory
sys.path.insert(0, str(Path(__file__).parent))

from fetch_data import build_merged

# ── constants (pre-registered, DO NOT CHANGE) ──────────────────────────────
DELTA_WINDOW = 7          # Δ window for both FG and price
Z_WINDOW = 90             # rolling z-score window
Z_MIN_PERIODS = 30        # minimum obs for z-score
SIGNAL_THRESHOLD = -1.5   # entry threshold (long when signal < threshold)
FORWARD_DAYS = 7          # forward return horizon (calendar days ≈ 7 trading days)
HAC_LAG = 6               # Newey-West lag
TSMOM_LOOKBACK = 28       # Strategy A lookback (from signal.py)
CORR_GATE = 0.5           # orthogonality gate: |ρ| < 0.5

# Decomposition rules (pre-registered)
D1_THRESHOLD = 0.5        # |IC_A| ≥ 0.5 × |IC_C| → price MR dominates
D2_B_THRESHOLD = 0.3      # |IC_B| ≥ 0.3 × |IC_C| → sentiment adds info
D3_B_THRESHOLD = 0.01     # |IC_B| < 0.01 → F&G void
D3_DIFF_THRESHOLD = 0.01  # |IC_C - IC_A| < 0.01 → F&G adds nothing


def rolling_zscore(series: pd.Series, window: int, min_periods: int) -> pd.Series:
    """Rolling z-score: (x - mean) / std over a rolling window."""
    mu = series.rolling(window, min_periods=min_periods).mean()
    sd = series.rolling(window, min_periods=min_periods).std(ddof=1)
    return (series - mu) / sd


def compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Test A, B, C signals on the merged data.

    Parameters
    ----------
    df : merged DataFrame with columns fg, close, log_ret (from fetch_data).

    Returns
    -------
    DataFrame with additional columns:
        delta_fg_7d, delta_price_7d, fg_vel, price_vel,
        sig_a, sig_b, sig_c, fwd_ret_7d.
    All signals at time t use only data through t (no look-ahead).
    The .shift(1) in the IC computation enforces signal T-1 / trade T.
    """
    out = df.copy()

    # ── raw 7-day changes ──────────────────────────────────────────────────
    out["delta_fg_7d"] = out["fg"] - out["fg"].shift(DELTA_WINDOW)
    out["delta_price_7d"] = np.log(out["close"] / out["close"].shift(DELTA_WINDOW))

    # ── z-scored velocities ────────────────────────────────────────────────
    out["fg_vel"] = rolling_zscore(out["delta_fg_7d"], Z_WINDOW, Z_MIN_PERIODS)
    out["price_vel"] = rolling_zscore(out["delta_price_7d"], Z_WINDOW, Z_MIN_PERIODS)

    # ── three signals ──────────────────────────────────────────────────────
    out["sig_a"] = -out["price_vel"]                  # Test A: naive price MR
    out["sig_b"] = out["fg_vel"]                       # Test B: FG standalone
    out["sig_c"] = out["fg_vel"] - out["price_vel"]    # Test C: FGVD combined

    # ── forward return (calendar days) ────────────────────────────────────
    # log_ret at t is the return from t-1 close to t close
    # fwd_ret_7d at t = sum of log_ret from t+1 to t+7 inclusive
    out["fwd_ret_7d"] = (
        out["log_ret"]
        .rolling(FORWARD_DAYS)
        .sum()
        .shift(-FORWARD_DAYS)   # shift back to align with signal at t
    )

    # drop warm-up rows
    out = out.dropna(subset=["sig_a", "sig_b", "sig_c", "fwd_ret_7d"])
    return out


def hac_tstat(signal: pd.Series, target: pd.Series, lag: int) -> tuple[float, float]:
    """Compute Spearman IC and Newey-West HAC t-stat.

    Parameters
    ----------
    signal : signal series (signal at T-1, already shifted for T-1 convention)
    target : forward return series
    lag    : Newey-West lag truncation parameter

    Returns
    -------
    (ic, t_hac) : Spearman rank correlation and HAC t-stat
    """
    # Align and drop NaN
    df = pd.DataFrame({"s": signal, "r": target}).dropna()
    n = len(df)
    if n < 50:
        return float("nan"), float("nan")

    ranks_s = stats.rankdata(df["s"])
    ranks_r = stats.rankdata(df["r"])
    ic = float(np.corrcoef(ranks_s, ranks_r)[0, 1])

    # Demeaned products for long-run variance
    xs = ranks_s - ranks_s.mean()
    xr = ranks_r - ranks_r.mean()
    u = xs * xr  # score products

    # Newey-West long-run variance
    gamma_0 = np.mean(u ** 2)
    lrv = gamma_0
    for k in range(1, lag + 1):
        w = 1.0 - k / (lag + 1)
        gamma_k = np.mean(u[k:] * u[:-k])
        lrv += 2 * w * gamma_k

    se_hac = np.sqrt(lrv / n)
    # t-stat of IC (IC = mean(u) / std — simplified; use direct approach)
    # The IC is E[u] / sqrt(E[u^2]) structure; t-stat = IC * sqrt(n) / sqrt(lrv / gamma_0)
    t_hac = ic * np.sqrt(n) / (np.sqrt(lrv / gamma_0) + 1e-12)
    return ic, float(t_hac)


def event_frequency(signal: pd.Series, threshold: float) -> float:
    """Compute annualized frequency of signal < threshold events."""
    n_years = (signal.index[-1] - signal.index[0]).days / 365.25
    n_events = (signal < threshold).sum()
    return float(n_events / n_years)


def compute_tsmom_z(df: pd.DataFrame) -> pd.Series:
    """Compute Strategy A TSMOM z-score for BTC (for orthogonality check).

    Uses the raw tanh(t-stat) from signal.py — no clipping (include short signal
    for full correlation coverage).
    """
    prices = df[["close"]].rename(columns={"close": "BTC"})
    log_rets = np.log(prices / prices.shift(1))
    cum_ret = log_rets.rolling(TSMOM_LOOKBACK).sum().shift(1)
    vol_l = log_rets.rolling(TSMOM_LOOKBACK).std().shift(1) * np.sqrt(TSMOM_LOOKBACK)
    t_stat = cum_ret / (vol_l + 1e-8)
    tsmom_z = np.tanh(t_stat)
    return tsmom_z["BTC"].reindex(df.index)


def evaluate_decomposition_rules(ic_a: float, ic_b: float, ic_c: float) -> dict:
    """Evaluate pre-registered decomposition decision rules D1, D2, D3.

    All ICs are signed (negative = contrarian edge).
    Rules use absolute values as specified in HYPOTHESIS.md.
    """
    abs_a, abs_b, abs_c = abs(ic_a), abs(ic_b), abs(ic_c)

    results = {
        "D1_price_MR_dominates": abs_c > 0 and abs_a >= D1_THRESHOLD * abs_c,
        "D2_combined_signal":    abs_c > 0 and abs_b >= D2_B_THRESHOLD * abs_c and abs_c > max(abs_a, abs_b),
        "D3_fg_void":            abs_b < D3_B_THRESHOLD and abs(ic_c - ic_a) < D3_DIFF_THRESHOLD,
    }

    if results["D3_fg_void"]:
        verdict = "STOP_D3: F&G velocity is noise; FGVD ≈ price MR"
    elif results["D1_price_MR_dominates"]:
        verdict = "STOP_D1: FGVD dominated by price mean-reversion; no incremental sentiment"
    elif results["D2_combined_signal"]:
        verdict = "PROCEED: sentiment velocity adds independent information"
    else:
        verdict = "AMBIGUOUS: decomposition inconclusive — report to user"

    results["verdict"] = verdict
    return results


def run_phase2() -> dict:
    """Execute full Phase 2 analysis and return results dict."""
    print("=" * 60)
    print("FGVD H1 — Phase 2 IC Test Block")
    print("=" * 60)

    # ── 1. Load data ───────────────────────────────────────────────────────
    df = build_merged()
    print(f"\nData: {len(df)} daily obs, {df.index.min().date()} → {df.index.max().date()}")

    # ── 2. Compute signals ─────────────────────────────────────────────────
    df = compute_signals(df)
    print(f"After signal computation + NaN drop: {len(df)} obs")

    # ── 3. Signal T-1 convention: shift signals by 1 day ──────────────────
    # Signal at T-1 → forward return starts at T.
    # fwd_ret_7d is already computed as sum(t+1 .. t+7) aligned to t.
    # Applying .shift(1) to signals gives signal(T-1) paired with fwd(T..T+6).
    sig_a = df["sig_a"].shift(1)
    sig_b = df["sig_b"].shift(1)
    sig_c = df["sig_c"].shift(1)
    fwd = df["fwd_ret_7d"]
    tsmom_z = compute_tsmom_z(df)

    # ── 4. IC and HAC t-stats ──────────────────────────────────────────────
    ic_a, t_a = hac_tstat(sig_a, fwd, HAC_LAG)
    ic_b, t_b = hac_tstat(sig_b, fwd, HAC_LAG)
    ic_c, t_c = hac_tstat(sig_c, fwd, HAC_LAG)

    print(f"\n{'Test':<8} {'IC':>8} {'t_HAC':>8}")
    print("-" * 28)
    print(f"{'A (MR)'::<8} {ic_a:>8.4f} {t_a:>8.3f}")
    print(f"{'B (FG)'::<8} {ic_b:>8.4f} {t_b:>8.3f}")
    print(f"{'C (FGVD)'::<8} {ic_c:>8.4f} {t_c:>8.3f}")

    # ── 5. Event frequency at threshold -1.5 ──────────────────────────────
    freq_a = event_frequency(sig_a.dropna(), SIGNAL_THRESHOLD)
    freq_b = event_frequency(sig_b.dropna(), SIGNAL_THRESHOLD)
    freq_c = event_frequency(sig_c.dropna(), SIGNAL_THRESHOLD)

    print(f"\nEvents/year at signal < {SIGNAL_THRESHOLD}:")
    print(f"  A: {freq_a:.1f}  B: {freq_b:.1f}  C: {freq_c:.1f}")

    # ── 6. Orthogonality: corr(FGVD, TSMOM-28d) ───────────────────────────
    common = sig_c.dropna().index.intersection(tsmom_z.dropna().index)
    corr_tsmom = float(np.corrcoef(sig_c.loc[common], tsmom_z.loc[common])[0, 1])
    orth_pass = abs(corr_tsmom) < CORR_GATE
    print(f"\nOrthogonality corr(FGVD, TSMOM-28d): {corr_tsmom:+.4f}  {'PASS' if orth_pass else 'FAIL'}")

    # ── 7. Decomposition rules ─────────────────────────────────────────────
    decomp = evaluate_decomposition_rules(ic_a, ic_b, ic_c)
    print(f"\nDecomposition verdict: {decomp['verdict']}")
    print(f"  D1 (price MR dominates): {decomp['D1_price_MR_dominates']}")
    print(f"  D2 (combined signal):    {decomp['D2_combined_signal']}")
    print(f"  D3 (F&G void):           {decomp['D3_fg_void']}")

    # ── 8. IC magnitude gates (only if PROCEED from decomposition) ─────────
    gate_ic_dir   = ic_c < 0
    gate_ic_mag   = ic_c < -0.05
    gate_t_hac    = t_c < -2.0
    gate_freq     = freq_c >= 20.0
    gate_orth     = orth_pass
    gates_pass    = gate_ic_dir and gate_ic_mag and gate_t_hac and gate_freq and gate_orth

    print(f"\nIC Gates (apply only if PROCEED):")
    print(f"  IC direction  < 0:      {gate_ic_dir}  (IC_C = {ic_c:+.4f})")
    print(f"  IC magnitude < -0.05:   {gate_ic_mag}")
    print(f"  t_HAC < -2.0:           {gate_t_hac}  (t = {t_c:.3f})")
    print(f"  Events/yr ≥ 20:         {gate_freq}  ({freq_c:.1f}/yr)")
    print(f"  |corr_TSMOM| < 0.5:     {gate_orth}  (corr = {corr_tsmom:+.4f})")

    # ── 9. Final verdict ───────────────────────────────────────────────────
    if "STOP" in decomp["verdict"]:
        final_verdict = decomp["verdict"]
    elif "AMBIGUOUS" in decomp["verdict"]:
        final_verdict = "AMBIGUOUS — user decision required"
    elif gates_pass:
        final_verdict = "PHASE 2 PASS — proceed to Phase 3 backtest"
    else:
        failed = []
        if not gate_ic_dir:   failed.append("IC direction wrong")
        if not gate_ic_mag:   failed.append(f"IC too small ({ic_c:.4f})")
        if not gate_t_hac:    failed.append(f"t_HAC too high ({t_c:.3f})")
        if not gate_freq:     failed.append(f"events/yr too low ({freq_c:.1f})")
        if not gate_orth:     failed.append(f"TSMOM corr too high ({corr_tsmom:.4f})")
        final_verdict = f"PHASE 2 FAIL — {', '.join(failed)}"

    print(f"\n{'='*60}")
    print(f"FINAL VERDICT: {final_verdict}")
    print(f"{'='*60}")

    # ── 10. Save results ───────────────────────────────────────────────────
    results = {
        "n_obs": int(len(df)),
        "date_start": str(df.index.min().date()),
        "date_end":   str(df.index.max().date()),
        "test_a": {"ic": round(ic_a, 6), "t_hac": round(t_a, 4), "events_per_year": round(freq_a, 1)},
        "test_b": {"ic": round(ic_b, 6), "t_hac": round(t_b, 4), "events_per_year": round(freq_b, 1)},
        "test_c": {"ic": round(ic_c, 6), "t_hac": round(t_c, 4), "events_per_year": round(freq_c, 1)},
        "corr_tsmom": round(corr_tsmom, 6),
        "orthogonality_pass": orth_pass,
        "decomposition": decomp,
        "gates": {
            "ic_direction": gate_ic_dir,
            "ic_magnitude": gate_ic_mag,
            "t_hac": gate_t_hac,
            "event_frequency": gate_freq,
            "orthogonality": gate_orth,
            "all_pass": gates_pass,
        },
        "final_verdict": final_verdict,
        "n_tests_consumed": 1,
        "n_tests_cumulative": 158,
    }

    out_path = Path(__file__).parent / "data" / "phase2_results.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path.relative_to(Path(__file__).parent)}")
    return results


if __name__ == "__main__":
    run_phase2()
