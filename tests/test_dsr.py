"""
Tests for the Deflated Sharpe Ratio modules.

Covers the 2026-07 calibration fix: `std_sr_trials` (the cross-sectional std-dev
of the competing trials' Sharpes) used to default silently to 1.0 in ANNUALISED
units in the repo-root `dsr.py`. That value equals the pure sampling noise of a
252-day backtest, so on a 13-year sample it inflated the deflation benchmark by
~3.6x and pushed the DSR >= 0.95 gate to an unreachable observed Sharpe of ~3.38
at n_trials = 321 — a 100% type-II-error filter given the project's realistic
SR band of 0.3-2.0 (CLAUDE.md, lesson L21).

Run:  /usr/bin/python3 -m pytest tests/test_dsr.py -v
"""
from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import norm

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import dsr as root_dsr  # noqa: E402
from _automation.feasibility.stats import dsr as auto_dsr  # noqa: E402


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def synthetic_returns(sharpe_annual: float, n_obs: int, periods_per_year: int = 252,
                      vol_per_period: float = 0.01, seed: int = 0) -> np.ndarray:
    """
    Build a normal return series whose REALISED annualised Sharpe is exactly
    `sharpe_annual`. Standardising the draw removes sampling noise, so the tests
    assert on the calibration, not on the luck of a particular seed.
    """
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n_obs)
    z = (z - z.mean()) / z.std(ddof=1)          # exact mean 0, sd 1
    target_per_period = sharpe_annual / math.sqrt(periods_per_year)
    return vol_per_period * (z + target_per_period)


T_13Y = 13 * 252          # 3276 daily observations
PPY = 252


# --------------------------------------------------------------------------
# (i) the silent default cannot happen any more
# --------------------------------------------------------------------------

def test_no_silent_default_warns_when_dispersion_undeclared():
    """Omitting std_sr_trials must warn loudly instead of assuming 1.0."""
    r = synthetic_returns(1.0, T_13Y, PPY)
    with pytest.warns(root_dsr.DSRCalibrationWarning, match="std_sr_trials was not declared"):
        root_dsr.deflated_sharpe_ratio(r, n_trials=50, periods_per_year=PPY, rf=0.0)


def test_undeclared_fallback_is_noise_floor_not_one():
    """The fallback must be sqrt(ppy/T), never the old hard-coded 1.0."""
    r = synthetic_returns(1.0, T_13Y, PPY)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", root_dsr.DSRCalibrationWarning)
        out = root_dsr.deflated_sharpe_ratio(r, n_trials=50, periods_per_year=PPY, rf=0.0)

    expected = math.sqrt(PPY / T_13Y)
    assert out["std_sr_trials"] == pytest.approx(expected, rel=1e-12)
    assert out["std_sr_trials_source"] == "sampling_noise_floor"
    assert out["std_sr_trials"] < 0.30, "13-year noise floor must be ~0.277, not 1.0"


def test_declared_dispersion_is_recorded_as_provenance():
    """A declared value must be used verbatim and flagged as declared."""
    r = synthetic_returns(1.0, T_13Y, PPY)
    out = root_dsr.deflated_sharpe_ratio(r, n_trials=50, periods_per_year=PPY, rf=0.0,
                                         std_sr_trials=0.42)
    assert out["std_sr_trials"] == pytest.approx(0.42)
    assert out["std_sr_trials_source"] == "declared"


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
def test_invalid_dispersion_rejected(bad):
    r = synthetic_returns(1.0, 1000, PPY)
    with pytest.raises(ValueError, match="finite positive"):
        root_dsr.deflated_sharpe_ratio(r, n_trials=50, periods_per_year=PPY, rf=0.0,
                                       std_sr_trials=bad)
    with pytest.raises(ValueError, match="finite positive"):
        auto_dsr.deflated_sharpe_ratio(1.0, 1000, 0.0, 3.0, n_trials=50, std_sr_trials=bad)


def test_expected_max_sr_has_no_default_dispersion():
    """_expected_max_sr must not be callable without an explicit std_sr."""
    with pytest.raises(TypeError):
        root_dsr._expected_max_sr(50)  # type: ignore[call-arg]


# --------------------------------------------------------------------------
# (ii) the regression that motivated the fix: a real strategy now passes
# --------------------------------------------------------------------------

def test_sharpe_1p2_13y_passes_with_realistic_dispersion_but_failed_at_sd_one():
    """
    SR 1.2 over 13 years with 20 trials of realistic dispersion is a genuine
    find under CLAUDE.md L21. It must PASS now, and it must be demonstrable
    that the old sd=1.0 default was what killed it.
    """
    r = synthetic_returns(1.2, T_13Y, PPY)

    family = [0.10, -0.25, 0.44, 0.61, -0.08, 0.33, 0.52, 0.19, -0.31, 0.27,
              0.05, 0.40, -0.12, 0.58, 0.22, 0.36, -0.19, 0.48, 0.14, 1.20]
    sd = root_dsr.estimate_std_sr_trials(family, periods_per_year=PPY, n_obs=T_13Y)
    assert 0.25 < sd < 0.60, f"unrealistic test fixture dispersion {sd}"

    fixed = root_dsr.deflated_sharpe_ratio(r, n_trials=20, periods_per_year=PPY, rf=0.0,
                                           std_sr_trials=sd)
    legacy = root_dsr.deflated_sharpe_ratio(r, n_trials=20, periods_per_year=PPY, rf=0.0,
                                            std_sr_trials=1.0)

    assert fixed["passed"], f"SR 1.2/13y must pass, got DSR={fixed['dsr']:.4f}"
    assert not legacy["passed"], "the old sd=1.0 default should have failed it"
    assert fixed["dsr"] > legacy["dsr"]


def test_type_ii_error_at_n_tests_321_is_repaired():
    """
    At the project's global n_tests=321, the old default demanded SR ~ 3.38 —
    above every band in L21. The honest floor must bring that under 2.0.
    """
    def required_sr(sd_ann, n_trials, T, ppy):
        b_per = sd_ann * root_dsr._expected_max_sr(n_trials, 0.0, 1.0) / math.sqrt(ppy)
        z, sr = norm.ppf(0.95), 0.0
        for _ in range(200):
            sr = b_per + z * math.sqrt(1 + 0.5 * sr ** 2) / math.sqrt(T - 1)
        return sr * math.sqrt(ppy)

    legacy = required_sr(1.0, 321, T_13Y, PPY)
    honest = required_sr(math.sqrt(PPY / T_13Y), 321, T_13Y, PPY)

    assert legacy > 3.3, f"expected the documented ~3.38, got {legacy:.2f}"
    assert honest < 2.0, f"repaired gate still unreachable: {honest:.2f}"


# --------------------------------------------------------------------------
# (iii) a weak strategy must still fail
# --------------------------------------------------------------------------

def test_sharpe_0p3_still_fails():
    """The fix must not turn the gate into a rubber stamp."""
    r = synthetic_returns(0.3, T_13Y, PPY)
    sd = math.sqrt(PPY / T_13Y)
    out = root_dsr.deflated_sharpe_ratio(r, n_trials=20, periods_per_year=PPY, rf=0.0,
                                         std_sr_trials=sd)
    assert not out["passed"], f"SR 0.3 must fail, got DSR={out['dsr']:.4f}"


def test_pure_noise_fails_even_with_one_trial():
    r = synthetic_returns(0.0, T_13Y, PPY)
    out = root_dsr.deflated_sharpe_ratio(r, n_trials=1, periods_per_year=PPY, rf=0.0,
                                         std_sr_trials=math.sqrt(PPY / T_13Y))
    assert out["dsr"] == pytest.approx(0.5, abs=0.02)
    assert not out["passed"]


# --------------------------------------------------------------------------
# (iv) monotonicities
# --------------------------------------------------------------------------

def test_dsr_decreases_with_n_trials():
    r = synthetic_returns(1.2, T_13Y, PPY)
    sd = math.sqrt(PPY / T_13Y)
    vals = [root_dsr.deflated_sharpe_ratio(r, n_trials=n, periods_per_year=PPY, rf=0.0,
                                           std_sr_trials=sd)["dsr"]
            for n in (2, 10, 50, 200, 1000)]
    assert all(a > b for a, b in zip(vals, vals[1:])), vals


def test_dsr_increases_with_sample_length():
    """Same true Sharpe, longer sample -> more evidence -> higher DSR."""
    sd = 0.35
    vals = []
    for years in (2, 5, 10, 20):
        T = years * PPY
        r = synthetic_returns(1.2, T, PPY)
        vals.append(root_dsr.deflated_sharpe_ratio(r, n_trials=20, periods_per_year=PPY,
                                                   rf=0.0, std_sr_trials=sd)["dsr"])
    assert all(a < b for a, b in zip(vals, vals[1:])), vals


def test_dsr_decreases_with_std_sr_trials():
    r = synthetic_returns(1.2, T_13Y, PPY)
    vals = [root_dsr.deflated_sharpe_ratio(r, n_trials=20, periods_per_year=PPY, rf=0.0,
                                           std_sr_trials=sd)["dsr"]
            for sd in (0.10, 0.28, 0.50, 1.00)]
    assert all(a > b for a, b in zip(vals, vals[1:])), vals


def test_benchmark_scales_linearly_in_dispersion():
    """E[max SR] is linear in std_sr with mean_sr = 0 — the reason 1.0 was so costly."""
    a = root_dsr._expected_max_sr(321, 0.0, 1.0)
    b = root_dsr._expected_max_sr(321, 0.0, 0.277)
    assert b == pytest.approx(a * 0.277, rel=1e-12)


# --------------------------------------------------------------------------
# (v) non-regression on the Bailey-Lopez de Prado formula itself
# --------------------------------------------------------------------------

def test_psr_matches_closed_form_for_normal_returns():
    """
    For normal returns Bailey-LdP eq. 3 reduces to
        var(SR_hat) = (1 + SR^2/2) / (T - 1)
    Verifies the (gamma4 - 1)/4 kurtosis coefficient, which the root module had
    wrong (it used excess/4, dropping the 0.5*SR^2 term).
    """
    T = 5000
    r = synthetic_returns(1.0, T, PPY)
    sr_ann = root_dsr._sharpe_ratio(r, PPY, rf=0.0)
    sr_per = sr_ann / math.sqrt(PPY)

    bench_ann = 0.30
    bench_per = bench_ann / math.sqrt(PPY)
    _, _, skew, kurt_x = root_dsr._moments(r)

    var_expected = (1.0 - skew * sr_per + ((kurt_x + 2.0) / 4.0) * sr_per ** 2) / (T - 1)
    expected = float(norm.cdf((sr_per - bench_per) / math.sqrt(var_expected)))

    got = root_dsr.probabilistic_sharpe_ratio(r, bench_ann, PPY, rf=0.0)
    assert got == pytest.approx(expected, rel=1e-10)

    # and the normal-case closed form, ~exact since synthetic_returns is gaussian
    var_normal = (1.0 + 0.5 * sr_per ** 2) / (T - 1)
    assert var_expected == pytest.approx(var_normal, rel=0.05)


def test_expected_max_sr_known_values():
    """
    E[max of n iid N(0,1)] via the Euler-Mascheroni approximation, against
    values recomputed from the closed form in Bailey-LdP eq. 10.
    """
    g = 0.5772156649015328
    for n in (2, 10, 50, 149, 321, 1000):
        want = ((1 - g) * norm.ppf(1 - 1.0 / n) + g * norm.ppf(1 - 1.0 / (n * math.e)))
        assert root_dsr._expected_max_sr(n, 0.0, 1.0) == pytest.approx(want, rel=1e-12)

    # sanity anchors: grows slowly, ~2.9 sigma at 321 trials
    assert root_dsr._expected_max_sr(321, 0.0, 1.0) == pytest.approx(2.9167, abs=1e-3)
    assert root_dsr._expected_max_sr(20, 0.0, 1.0) == pytest.approx(1.9007, abs=1e-3)


def test_expected_max_sr_degenerate_single_trial():
    assert root_dsr._expected_max_sr(1, 0.0, 0.3) == 0.0
    assert root_dsr._expected_max_sr(1, 0.7, 0.3) == 0.7


# --------------------------------------------------------------------------
# estimator behaviour
# --------------------------------------------------------------------------

def test_estimator_returns_observed_dispersion_when_above_floor():
    sharpes = [0.0, 0.5, 1.0, 1.5, 2.0]
    got = root_dsr.estimate_std_sr_trials(sharpes, periods_per_year=PPY, n_obs=T_13Y)
    assert got == pytest.approx(float(np.std(sharpes, ddof=1)))


def test_estimator_clamps_at_noise_floor():
    """A degenerate/clipped family must not claim implausibly tight clustering."""
    sharpes = [1.00, 1.01, 1.02, 0.99]           # sd ~ 0.013, far below the floor
    got = root_dsr.estimate_std_sr_trials(sharpes, periods_per_year=PPY, n_obs=T_13Y)
    assert got == pytest.approx(math.sqrt(PPY / T_13Y))


def test_estimator_floor_can_be_disabled_without_n_obs():
    sharpes = [1.00, 1.01, 1.02, 0.99]
    got = root_dsr.estimate_std_sr_trials(sharpes, apply_floor=False)
    assert got == pytest.approx(float(np.std(sharpes, ddof=1)))


def test_estimator_requires_n_obs_when_flooring():
    with pytest.raises(ValueError, match="n_obs is required"):
        root_dsr.estimate_std_sr_trials([0.1, 0.9], periods_per_year=PPY)


def test_estimator_rejects_degenerate_family():
    for bad in ([], [1.0], [float("nan"), 1.0]):
        with pytest.raises(ValueError, match=">= 2 finite trial Sharpes"):
            root_dsr.estimate_std_sr_trials(bad, periods_per_year=PPY, n_obs=T_13Y)


def test_estimator_drops_non_finite():
    got = root_dsr.estimate_std_sr_trials([0.0, 1.0, float("nan"), float("inf"), 2.0],
                                          periods_per_year=PPY, n_obs=T_13Y)
    assert got == pytest.approx(float(np.std([0.0, 1.0, 2.0], ddof=1)))


# --------------------------------------------------------------------------
# cross-module consistency — fails loudly if the two copies drift apart again
# --------------------------------------------------------------------------

def test_noise_floor_identical_across_modules():
    for T in (300, 756, 3276, 10000):
        assert (root_dsr.sampling_noise_floor_sr(T, PPY)
                == pytest.approx(auto_dsr.sampling_noise_floor_sr(T, PPY), rel=1e-15))


def test_estimator_identical_across_modules():
    fam = [0.1, -0.3, 0.8, 1.4, 0.25, -0.05, 0.62]
    assert (root_dsr.estimate_std_sr_trials(fam, PPY, T_13Y)
            == pytest.approx(auto_dsr.estimate_std_sr_trials(fam, PPY, T_13Y), rel=1e-15))


def test_automation_module_default_is_sampling_noise_and_is_overridable():
    """
    The automation copy always scaled by the SR standard error, i.e. the noise
    floor — it never had the 1.0 bug. Pin that, and pin the new override path.
    """
    r = synthetic_returns(1.2, T_13Y, PPY)
    stats = auto_dsr.compute_sharpe_stats(__import__("pandas").Series(r))

    default = auto_dsr.deflated_sharpe_ratio(stats["sharpe"], stats["n_observations"],
                                             stats["skewness"], stats["kurtosis"],
                                             n_trials=20)
    assert default["std_sr_trials_source"] == "sampling_noise"
    # ~ sqrt(252/3276) = 0.277, modulo the skew/kurt terms in the standard error
    assert default["std_sr_trials"] == pytest.approx(0.277, abs=0.03)

    wide = auto_dsr.deflated_sharpe_ratio(stats["sharpe"], stats["n_observations"],
                                          stats["skewness"], stats["kurtosis"],
                                          n_trials=20, std_sr_trials=1.0)
    assert wide["std_sr_trials_source"] == "declared"
    assert wide["dsr"] < default["dsr"]
    assert default["verdict"] == "PASS"
    assert wide["verdict"] == "FAIL"


def test_root_and_automation_agree_on_dsr_given_same_dispersion():
    """
    With the kurtosis coefficient fixed in the root module and the same declared
    dispersion, the two implementations must now produce the same DSR.
    """
    import pandas as pd
    r = synthetic_returns(1.1, T_13Y, PPY)
    sd = 0.35

    root_out = root_dsr.deflated_sharpe_ratio(r, n_trials=40, periods_per_year=PPY,
                                              rf=0.0, std_sr_trials=sd)
    stats = auto_dsr.compute_sharpe_stats(pd.Series(r))
    auto_out = auto_dsr.deflated_sharpe_ratio(stats["sharpe"], stats["n_observations"],
                                              stats["skewness"], stats["kurtosis"],
                                              n_trials=40, std_sr_trials=sd)

    assert root_out["sharpe"] == pytest.approx(stats["sharpe"], rel=1e-9)
    assert root_out["dsr"] == pytest.approx(auto_out["dsr"], abs=1e-6)
