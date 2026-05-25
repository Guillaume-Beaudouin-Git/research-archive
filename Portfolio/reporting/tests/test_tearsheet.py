"""
Tests for Portfolio.reporting — tear sheet metrics and HTML generation.

Run from repo root (adapt venv path to your setup):
    python -m pytest Portfolio/reporting/tests/test_tearsheet.py -v
"""
from __future__ import annotations

import math
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_returns(
    n: int = 756,
    mu: float = 0.0005,
    sigma: float = 0.01,
    seed: int = 42,
) -> pd.Series:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-03", periods=n, freq="B")
    return pd.Series(mu + sigma * rng.standard_normal(n), index=dates)


def _zero_rf(index: pd.Index) -> pd.Series:
    """Zero risk-free series — isolates formula verification from FRED dependency."""
    return pd.Series(0.0, index=index)


# ── test_metrics_synthetic_normal ──────────────────────────────────────────────

class TestMetricsSyntheticNormal:
    """
    Verify Sharpe formula and DSR < PSR for N(mu, sigma) returns.
    mu=0.0005 (0.05%/day), sigma=0.01 (1%/day) → population SR ≈ 0.794.

    For formula-correctness we verify the returned value matches the manual
    (sample_mean / sample_std) × sqrt(252) computation to machine precision.
    For statistical convergence we use n=10_000 where SE(SR) ≈ 0.16, making
    a 30% tolerance band reliable (>99.9% pass probability).
    """

    def test_sharpe_formula_matches_manual_computation(self) -> None:
        """hac_sharpe_ratio must return (mu/sigma) × sqrt(252) to float precision."""
        r = _make_returns(n=756, mu=0.0005, sigma=0.01)
        rf = _zero_rf(r.index)

        from Portfolio.reporting.metrics import hac_sharpe_ratio, to_excess_returns

        r_ex = to_excess_returns(r, rf)
        sharpe, t_stat, se = hac_sharpe_ratio(r_ex)

        assert not math.isnan(sharpe), "Sharpe is NaN for valid series"
        assert math.isfinite(t_stat), "t-stat must be finite"

        # Formula identity: returned SR must equal manual computation
        manual = (float(r_ex.mean()) / float(r_ex.std())) * math.sqrt(252)
        assert abs(sharpe - manual) < 1e-9, (
            f"Sharpe {sharpe:.6f} ≠ manual {manual:.6f} — formula error"
        )

    def test_sharpe_converges_to_expected_with_large_n(self) -> None:
        """With n=10_000, sample SR must be within 30% of the population value.

        Population SR = (mu/sigma) × sqrt(252) ≈ 0.794.
        SE(SR) ≈ sqrt(252/10_000) ≈ 0.159; ±30% band is ≈ ±1.9 SE → >97% pass rate.
        """
        mu, sigma = 0.0005, 0.01
        r = _make_returns(n=10_000, mu=mu, sigma=sigma, seed=0)
        rf = _zero_rf(r.index)

        from Portfolio.reporting.metrics import hac_sharpe_ratio, to_excess_returns

        r_ex = to_excess_returns(r, rf)
        sharpe, _, _ = hac_sharpe_ratio(r_ex)

        expected = (mu / sigma) * math.sqrt(252)   # ≈ 0.794
        assert abs(sharpe - expected) / expected < 0.30, (
            f"Sharpe {sharpe:.3f} deviates >30% from expected {expected:.3f}"
        )

    def test_dsr_equals_psr_for_n_trials_1(self) -> None:
        r = _make_returns()
        rf = _zero_rf(r.index)

        from Portfolio.reporting.metrics import compute_psr_dsr, to_excess_returns

        r_ex = to_excess_returns(r, rf)
        res = compute_psr_dsr(r_ex, n_trials=1)

        assert not math.isnan(res["psr"]), "PSR is NaN"
        assert not math.isnan(res["dsr"]), "DSR is NaN"
        assert abs(res["psr"] - res["dsr"]) < 1e-9, (
            f"PSR={res['psr']:.6f} should equal DSR={res['dsr']:.6f} when n_trials=1"
        )

    def test_dsr_lt_psr_for_n_trials_100(self) -> None:
        r = _make_returns()
        rf = _zero_rf(r.index)

        from Portfolio.reporting.metrics import compute_psr_dsr, to_excess_returns

        r_ex = to_excess_returns(r, rf)
        psr = compute_psr_dsr(r_ex, n_trials=1)["psr"]
        dsr = compute_psr_dsr(r_ex, n_trials=100)["dsr"]

        assert dsr < psr, (
            f"DSR(100)={dsr:.4f} should be strictly less than PSR={psr:.4f}"
        )


# ── test_zero_returns ──────────────────────────────────────────────────────────

class TestZeroReturns:
    """
    Zero return series must not crash and must give Sharpe = 0 or NaN
    (std=0 edge case), never a nonsensical positive value.
    """

    def test_no_crash_and_valid_sharpe(self) -> None:
        dates = pd.date_range("2022-01-03", periods=500, freq="B")
        r = pd.Series(0.0, index=dates)

        from Portfolio.reporting.metrics import compute_all_metrics

        metrics = compute_all_metrics(
            returns=r,
            benchmark=None,
            n_trials=1,
            rf=_zero_rf(dates),
        )
        sharpe = metrics["sharpe_hac"]
        assert sharpe == 0.0 or math.isnan(sharpe), (
            f"Expected 0 or NaN for zero returns, got {sharpe}"
        )

    def test_required_keys_present(self) -> None:
        dates = pd.date_range("2022-01-03", periods=300, freq="B")
        r = pd.Series(0.0, index=dates)

        from Portfolio.reporting.metrics import compute_all_metrics

        metrics = compute_all_metrics(
            returns=r, benchmark=None, n_trials=1, rf=_zero_rf(dates),
        )
        required = [
            "max_dd", "calmar", "psr", "dsr", "cvar_95", "sortino",
            "skewness", "excess_kurtosis", "_equity", "_dd",
        ]
        for k in required:
            assert k in metrics, f"Missing key: {k}"


# ── test_hac_vs_naive ──────────────────────────────────────────────────────────

class TestHACvsNaive:
    """
    HAC SE must exceed the naive (iid) SE on AR(1) returns with ρ=0.3.
    Positive autocorrelation inflates the variance of the mean estimator;
    HAC correctly accounts for this while naive OLS does not.
    """

    def test_hac_se_greater_than_naive(self) -> None:
        rng = np.random.default_rng(42)
        n = 800
        dates = pd.date_range("2022-01-03", periods=n, freq="B")

        # AR(1) with ρ=0.3
        eps = rng.standard_normal(n) * 0.01
        r = np.zeros(n)
        r[0] = eps[0]
        for i in range(1, n):
            r[i] = 0.3 * r[i - 1] + eps[i]
        r_series = pd.Series(r + 0.0005, index=dates)

        from Portfolio.reporting.metrics import hac_sharpe_ratio

        _, _, se_hac = hac_sharpe_ratio(r_series, lag=6)
        assert not math.isnan(se_hac), "HAC SE is NaN"

        # Naive SE of the annualised SR ≈ sqrt(252/n)
        naive_se_sr = math.sqrt(252 / n)
        assert se_hac > naive_se_sr, (
            f"HAC SE {se_hac:.4f} should exceed naive SE {naive_se_sr:.4f} "
            f"for AR(1) ρ=0.3 returns (n={n})"
        )


# ── test_dsr_decreases_with_trials ────────────────────────────────────────────

class TestDSRDecreasesWithTrials:
    """
    DSR is monotone decreasing in n_trials.
    As n_trials grows, the SR threshold (expected max Sharpe from n random strategies)
    rises, so P(true SR > threshold) can only decrease.
    """

    @pytest.mark.parametrize("n_list", [
        [1, 5, 20, 100],
        [1, 50, 321],
    ])
    def test_dsr_monotone(self, n_list: list[int]) -> None:
        r = _make_returns(mu=0.0004, sigma=0.01, seed=99)
        rf = _zero_rf(r.index)

        from Portfolio.reporting.metrics import compute_psr_dsr, to_excess_returns

        r_ex = to_excess_returns(r, rf)
        prev = 1.0
        for n in n_list:
            result = compute_psr_dsr(r_ex, n_trials=n)
            dsr = result["dsr"]
            assert not math.isnan(dsr), f"DSR is NaN for n_trials={n}"
            assert dsr <= prev + 1e-9, (
                f"DSR not monotone: DSR({n})={dsr:.4f} > previous={prev:.4f}"
            )
            prev = dsr


# ── test_html_output_exists ───────────────────────────────────────────────────

class TestHTMLOutput:
    """
    generate_tearsheet must produce a valid, non-trivial HTML file.
    """

    def test_file_created_and_large_enough(self) -> None:
        r = _make_returns(n=600, mu=0.0005, sigma=0.01, seed=7)

        from Portfolio.reporting.tearsheet import generate_tearsheet

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "test_sheet.html"
            result = generate_tearsheet(
                returns=r,
                strategy_name="Synthetic Test Strategy",
                output_path=out,
                n_trials=10,
                rf=_zero_rf(r.index),
                metadata={"Asset": "Synthetic", "Test": "True"},
            )
            assert result.exists(), "HTML file was not created"
            size_kb = result.stat().st_size / 1024
            assert size_kb > 10, (
                f"HTML file only {size_kb:.1f} KB — likely truncated or missing plots"
            )

    def test_html_has_required_elements(self) -> None:
        r = _make_returns(n=400, mu=0.0006, sigma=0.012, seed=13)

        from Portfolio.reporting.tearsheet import generate_tearsheet

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "sheet.html"
            result = generate_tearsheet(
                returns=r,
                strategy_name="Embedded Element Test",
                output_path=out,
                n_trials=1,
                rf=_zero_rf(r.index),
            )
            content = result.read_text(encoding="utf-8")
            assert "<!DOCTYPE html>" in content or "<html" in content.lower(), \
                "Missing HTML doctype/tag"
            assert "data:image/png;base64," in content, \
                "No embedded PNG plots found"
            assert "Sharpe" in content, "Missing Sharpe metric in output"
            assert "RESEARCH" in content, "Missing gate badges"

    def test_benchmark_section_present_when_provided(self) -> None:
        r = _make_returns(n=500, mu=0.0005, sigma=0.01, seed=3)
        bm = _make_returns(n=500, mu=0.0003, sigma=0.015, seed=77)
        bm.index = r.index

        from Portfolio.reporting.tearsheet import generate_tearsheet

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "with_bm.html"
            result = generate_tearsheet(
                returns=r,
                strategy_name="Benchmark Section Test",
                output_path=out,
                benchmark=bm,
                n_trials=1,
                rf=_zero_rf(r.index),
            )
            content = result.read_text(encoding="utf-8")
            # When benchmark is provided, excess equity plot should appear
            assert "Excess" in content or "Benchmark" in content, \
                "Expected benchmark section in HTML"


# ── test_l14_proxy_display ────────────────────────────────────────────────────

class TestL14ProxyDisplay:
    """
    L14 proxy SR flag: dual display activates correctly and is absent by default.

    Per CLAUDE.md §L14: testnet Sharpe is inadmissible for portfolio optimisation
    until N≥250 live daily returns accumulate. The apply_l14_proxy flag surfaces
    both the raw HAC backtest Sharpe and the conservative proxy used for ERC sizing.
    """

    def test_l14_proxy_dual_display(self) -> None:
        """With apply_l14_proxy=True, HTML must contain raw SR label, proxy value,
        the L14 PROXY ACTIVE badge, and the methodology note; internal flags must
        not leak to the header meta line."""
        r = _make_returns(n=600, mu=0.0010, sigma=0.005, seed=42)

        from Portfolio.reporting.tearsheet import generate_tearsheet

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "l14_proxy.html"
            result = generate_tearsheet(
                returns=r,
                strategy_name="L14 Proxy Test",
                output_path=out,
                n_trials=1,
                rf=_zero_rf(r.index),
                metadata={"Type": "testnet carry", "apply_l14_proxy": True, "proxy_sr": 2.0},
            )
            content = result.read_text(encoding="utf-8")

            assert "L14 PROXY ACTIVE" in content, "L14 badge missing"
            assert "raw backtest" in content, "Raw backtest label missing from Sharpe card"
            assert "L14 proxy" in content, "L14 proxy sub-label missing from Sharpe card"
            assert "2.00" in content, "Proxy SR value 2.00 not found"
            assert "mainnet" in content, "L14 methodology note missing"
            # Internal flags must not appear verbatim in the rendered HTML
            assert "apply_l14_proxy" not in content, "Internal flag leaked to HTML output"
            assert "proxy_sr" not in content, "Internal flag leaked to HTML output"

    def test_l14_proxy_absent_by_default(self) -> None:
        """Without apply_l14_proxy, standard single Sharpe card renders and
        no L14 artefacts appear (regression guard)."""
        r = _make_returns(n=400, mu=0.0005, sigma=0.01, seed=7)

        from Portfolio.reporting.tearsheet import generate_tearsheet

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "no_l14.html"
            result = generate_tearsheet(
                returns=r,
                strategy_name="Standard Strategy",
                output_path=out,
                n_trials=1,
                rf=_zero_rf(r.index),
            )
            content = result.read_text(encoding="utf-8")

            assert "L14 PROXY ACTIVE" not in content, "L14 badge appeared without flag"
            assert "raw backtest" not in content, "Raw backtest label appeared without flag"
            assert "L14 proxy" not in content, "L14 proxy label appeared without flag"
            assert "Sharpe (HAC lag-6, excess)" in content, \
                "Standard Sharpe label missing in default rendering"
