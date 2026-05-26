"""
CPCV validation suite — 8 tests (minimum required per session spec).

Run from repo root:
    python -m pytest Portfolio/validation/tests/test_cpcv.py -v

All tests use synthetic return series to avoid network calls.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
import pytest

from Portfolio.validation.cpcv import run_cpcv
from Portfolio.validation.multi_test import deflated_sharpe, harvey_liu_bhy
from Portfolio.validation.pipeline import generate_cpcv_report


# ── Synthetic data helpers ─────────────────────────────────────────────────────

def _random_returns(n: int = 1000, mu: float = 0.0, sigma: float = 0.01, seed: int = 42) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.Series(rng.normal(mu, sigma, n), index=idx)


def _strong_edge_returns(n: int = 1000, daily_mu: float = 0.002, sigma: float = 0.005, seed: int = 42) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.Series(daily_mu + rng.normal(0, sigma, n), index=idx)


def _slice_fn(returns: pd.Series):
    """Naive backtest_fn: Sharpe on test slice (no excess returns, for speed)."""
    def fn(train_idx: np.ndarray, test_idx: np.ndarray) -> float:
        r = returns.iloc[test_idx]
        if len(r) < 5 or float(r.std()) == 0:
            return 0.0
        return float((r.mean() / r.std()) * math.sqrt(252))
    return fn


# ── Distribution tests ─────────────────────────────────────────────────────────

class TestCpcvDistribution:

    def test_synthetic_no_edge_distribution_centered_zero(self):
        """Random returns → CPCV mean Sharpe should be near zero."""
        r = _random_returns(n=1000, mu=0.0)
        result = run_cpcv(r, _slice_fn(r), verbose=False)
        assert abs(result["mean"]) < 0.5, (
            f"Expected |mean SR| < 0.5 for zero-edge random returns, got {result['mean']:.3f}"
        )

    def test_synthetic_strong_edge_positive_mean(self):
        """High-SR returns → CPCV mean > 0.5 across paths."""
        r = _strong_edge_returns(n=1000, daily_mu=0.002, sigma=0.005)
        result = run_cpcv(r, _slice_fn(r), verbose=False)
        assert result["mean"] > 0.5, (
            f"Expected mean SR > 0.5 for strong-edge returns, got {result['mean']:.3f}"
        )

    def test_n_paths_meets_target(self):
        """Auto-selected folds must produce ≥ target_n_paths paths."""
        r = _random_returns(n=1000)
        result = run_cpcv(r, _slice_fn(r), target_n_paths=20, verbose=False)
        assert result["n_paths"] >= 20, (
            f"Expected ≥20 paths, got {result['n_paths']}"
        )

    def test_purging_respects_label_horizon(self):
        """With purge_size=28, no training bar should be within 28 bars of any test bar.

        Uses a tracking fn that measures min(|train_i - test_j|) per split via
        binary search (O(|test| × log|train|)) and asserts the global minimum ≥ 28.
        """
        PURGE = 28
        r = _random_returns(n=400)
        min_gaps: list[int] = []

        def tracking_fn(train_idx: np.ndarray, test_idx: np.ndarray) -> float:
            if len(train_idx) == 0 or len(test_idx) == 0:
                return 0.0
            train_s = np.sort(train_idx)
            for t in test_idx:
                pos = int(np.searchsorted(train_s, t))
                candidates: list[int] = []
                if pos < len(train_s):
                    candidates.append(abs(int(train_s[pos]) - int(t)))
                if pos > 0:
                    candidates.append(abs(int(train_s[pos - 1]) - int(t)))
                if candidates:
                    min_gaps.append(min(candidates))
            return 0.0

        run_cpcv(r, tracking_fn, purge_size=PURGE, verbose=False)
        assert len(min_gaps) > 0, "No train/test gaps recorded — check tracking_fn"
        assert min(min_gaps) >= PURGE, (
            f"Purge violated: min gap={min(min_gaps)}, expected ≥{PURGE}"
        )

    def test_embargo_size_correct(self):
        """With embargo_pct=0.01 and T=1000, result['embargo_size'] ≥ 10."""
        r = _random_returns(n=1000)
        result = run_cpcv(r, _slice_fn(r), embargo_pct=0.01, verbose=False)
        expected_min = max(1, int(0.01 * 1000))
        assert result["embargo_size"] >= expected_min, (
            f"embargo_size={result['embargo_size']}, expected ≥{expected_min}"
        )

    def test_output_keys_present(self):
        """Result dict must contain all required keys."""
        r = _random_returns(n=600)
        result = run_cpcv(r, _slice_fn(r), verbose=False)
        required = {
            "sharpes", "mean", "std", "median", "ci_5_95",
            "n_paths", "n_folds", "n_test_folds", "purge_size",
            "embargo_size", "config",
        }
        missing = required - result.keys()
        assert not missing, f"Missing keys: {missing}"


# ── Multiple-testing tests ─────────────────────────────────────────────────────

class TestMultiTest:

    def test_dsr_decreases_with_n_trials(self):
        """DSR(n_trials=1) must be strictly greater than DSR(n_trials=100)."""
        r = _strong_edge_returns(n=500, daily_mu=0.001, sigma=0.008)
        sr_daily = float(r.mean() / r.std())
        dsr_1 = deflated_sharpe(sr_daily, n_trials=1, T=len(r))
        dsr_100 = deflated_sharpe(sr_daily, n_trials=100, T=len(r))
        assert dsr_1 > dsr_100, (
            f"Expected DSR(n=1)={dsr_1:.4f} > DSR(n=100)={dsr_100:.4f}"
        )

    def test_harvey_liu_bhy_reduces_false_discoveries(self):
        """BHY on 10 uniform p-values should produce ≤ 2 rejections at α=0.05."""
        rng = np.random.default_rng(0)
        pvals = rng.uniform(0, 1, 10).tolist()
        result = harvey_liu_bhy(pvals, alpha=0.05)
        assert "reject" in result and "qvalues" in result and "n_reject" in result
        assert result["n_reject"] <= 2, (
            f"BHY yielded {result['n_reject']} rejections on uniform p-values; expected ≤2"
        )


# ── Pipeline / HTML output ─────────────────────────────────────────────────────

class TestPipelineOutput:

    def test_report_html_output_exists(self, tmp_path):
        """generate_cpcv_report() must write an HTML file > 10 KB."""
        r = _strong_edge_returns(n=1000)
        out = tmp_path / "test_cpcv_report.html"
        generate_cpcv_report(
            returns=r,
            strategy_name="Test Strategy — Synthetic",
            backtest_fn=_slice_fn(r),
            n_trials=10,
            output_path=str(out),
            wf_baseline_sharpe=1.5,
        )
        assert out.exists(), "HTML report file not written"
        size_kb = out.stat().st_size / 1024
        assert size_kb > 10.0, f"HTML report suspiciously small: {size_kb:.1f} KB"
