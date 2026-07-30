"""Tests for Portfolio.admission — marginal sleeve admission criterion."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from Portfolio.admission.barrier import (
    BarrierConfig,
    pass_probability_delta,
    simulate_campaign,
)
from Portfolio.admission.marginal import (
    admit,
    bootstrap_delta_sharpe,
    calendar_sharpe,
    conditional_sleeve_series,
    delta_sharpe,
    erc_hurdle_sharpe,
    erc_two_sleeve_sharpe,
    erc_weights,
    hrp_weights,
    marginal_hurdle_sharpe,
    portfolio_sharpe,
    stationary_bootstrap_indices,
)

PPY = 252.0


def _series(mu_ann: float, vol_ann: float, n: int, seed: int, name: str,
            common: np.ndarray | None = None, beta: float = 0.0) -> pd.Series:
    """Daily gaussian sleeve with a controllable common component."""
    rng = np.random.default_rng(seed)
    idio = rng.normal(0.0, 1.0, n)
    z = idio if common is None else beta * common + np.sqrt(max(1 - beta**2, 0.0)) * idio
    z = (z - z.mean()) / z.std(ddof=1)
    r = mu_ann / PPY + z * vol_ann / np.sqrt(PPY)
    idx = pd.bdate_range("2015-01-01", periods=n)
    return pd.Series(r, index=idx, name=name)


# ── closed forms ─────────────────────────────────────────────────────────────

def test_erc_two_sleeve_matches_the_motivating_example():
    """0.9 and 0.5 uncorrelated combine to ~0.99 — the case the ratio gate kills."""
    assert erc_two_sleeve_sharpe(0.9, 0.5, 0.0) == pytest.approx(1.4 / np.sqrt(2), rel=1e-12)
    assert erc_two_sleeve_sharpe(0.9, 0.5, 0.0) == pytest.approx(0.9899, abs=1e-4)


def test_legacy_ratio_gate_rejects_an_accretive_diversifier():
    """Regression guard on the defect this module exists to fix."""
    s_book, s_cand, rho = 0.9, 0.5, 0.0
    combined = erc_two_sleeve_sharpe(s_book, s_cand, rho)
    assert combined > s_book                      # genuinely accretive: 0.99 > 0.90
    assert combined < 1.10 * s_book               # yet the legacy gate rejects it
    assert s_cand > marginal_hurdle_sharpe(s_book, rho)   # marginal criterion admits it


def test_marginal_hurdle_is_rho_times_book_sharpe():
    assert marginal_hurdle_sharpe(1.2, 0.5) == pytest.approx(0.6)
    assert marginal_hurdle_sharpe(1.2, 0.0) == pytest.approx(0.0)
    assert marginal_hurdle_sharpe(1.2, -0.3) == pytest.approx(-0.36)


def test_marginal_hurdle_agrees_with_numerical_derivative():
    """s_c > rho s_b must coincide with d SR/dx > 0 at x = 0."""
    s_b, sig_b, sig_c, rho = 1.0, 0.10, 0.04, 0.4
    hurdle = marginal_hurdle_sharpe(s_b, rho)
    for s_c in (hurdle - 0.15, hurdle + 0.15):
        mu_b, mu_c = s_b * sig_b, s_c * sig_c
        x = 1e-6
        def sr(xx: float) -> float:
            mu = mu_b + xx * mu_c
            var = sig_b**2 + 2 * xx * rho * sig_b * sig_c + xx**2 * sig_c**2
            return mu / np.sqrt(var)
        deriv = (sr(x) - sr(0.0)) / x
        assert np.sign(deriv) == np.sign(s_c - hurdle)


def test_erc_hurdle_is_strictly_harder_than_marginal_when_rho_small():
    s_b = 1.0
    for rho in (-0.2, 0.0, 0.2):
        assert erc_hurdle_sharpe(s_b, rho) > marginal_hurdle_sharpe(s_b, rho)


def test_erc_hurdle_is_the_breakeven_of_the_closed_form():
    s_b, rho = 1.1, 0.25
    h = erc_hurdle_sharpe(s_b, rho)
    assert erc_two_sleeve_sharpe(s_b, h, rho) == pytest.approx(s_b, rel=1e-12)


def test_negative_correlation_makes_any_positive_sleeve_accretive_at_the_margin():
    """With rho < 0 the marginal hurdle is negative — but ERC is a *finite*
    allocation, so a near-zero-Sharpe sleeve still dilutes at equal risk share.
    The two hurdles answer different questions and must not be conflated."""
    s_b, rho = 1.0, -0.25
    assert marginal_hurdle_sharpe(s_b, rho) < 0
    erc_h = erc_hurdle_sharpe(s_b, rho)
    assert erc_h > 0
    assert erc_two_sleeve_sharpe(s_b, 0.05, rho) < s_b          # too weak for ERC
    assert erc_two_sleeve_sharpe(s_b, erc_h + 0.05, rho) > s_b  # clears ERC hurdle


def test_erc_two_sleeve_rejects_degenerate_rho():
    with pytest.raises(ValueError):
        erc_two_sleeve_sharpe(1.0, 1.0, -1.0)


# ── weights ──────────────────────────────────────────────────────────────────

def test_erc_weights_are_inverse_vol_and_sum_to_one():
    a = _series(0.10, 0.20, 600, 1, "a")
    b = _series(0.05, 0.05, 600, 2, "b")
    w = erc_weights(pd.concat([a, b], axis=1))
    assert w.sum() == pytest.approx(1.0)
    assert w["b"] > w["a"]
    assert w["a"] * a.std(ddof=1) == pytest.approx(w["b"] * b.std(ddof=1), rel=1e-9)


def test_erc_weights_reject_zero_variance_sleeve():
    df = pd.DataFrame({"a": np.random.default_rng(0).normal(size=100), "dead": np.zeros(100)})
    with pytest.raises(ValueError):
        erc_weights(df)


def test_hrp_weights_valid_and_fall_back_below_three_sleeves():
    cols = [_series(0.08, 0.10 + 0.02 * i, 800, 10 + i, f"s{i}") for i in range(4)]
    df = pd.concat(cols, axis=1)
    w = hrp_weights(df)
    assert w.sum() == pytest.approx(1.0)
    assert (w > 0).all()
    two = df[["s0", "s1"]]
    pd.testing.assert_series_equal(hrp_weights(two), erc_weights(two))


def test_portfolio_sharpe_of_two_uncorrelated_sleeves_matches_closed_form():
    n = 6000
    a = _series(0.10, 0.10, n, 3, "a")   # SR 1.0
    b = _series(0.03, 0.06, n, 4, "b")   # SR 0.5
    df = pd.concat([a, b], axis=1)
    rho = float(df.corr().iloc[0, 1])
    sr_a = a.mean() / a.std(ddof=1) * np.sqrt(PPY)
    sr_b = b.mean() / b.std(ddof=1) * np.sqrt(PPY)
    assert portfolio_sharpe(df, periods_per_year=PPY) == pytest.approx(
        erc_two_sleeve_sharpe(sr_a, sr_b, rho), rel=1e-9
    )


# ── Delta SR on realised panels ──────────────────────────────────────────────

def test_delta_sharpe_positive_for_uncorrelated_low_sharpe_diversifier():
    n = 4000
    book = _series(0.09, 0.10, n, 5, "book")     # SR ~0.9
    cand = _series(0.03, 0.06, n, 6, "cand")     # SR ~0.5, rho ~0
    d = delta_sharpe(book, cand, periods_per_year=PPY)
    assert d > 0.05


def test_delta_sharpe_negative_for_a_correlated_worse_sleeve():
    n = 4000
    rng = np.random.default_rng(7)
    common = rng.normal(size=n)
    book = _series(0.12, 0.10, n, 8, "book", common=common, beta=0.95)
    cand = _series(0.01, 0.10, n, 9, "cand", common=common, beta=0.95)
    assert delta_sharpe(book, cand, periods_per_year=PPY) < 0


def test_delta_sharpe_requires_overlap():
    a = _series(0.1, 0.1, 100, 1, "book")
    b = _series(0.1, 0.1, 100, 2, "cand")
    b.index = b.index + pd.Timedelta(days=5000)
    with pytest.raises(ValueError):
        delta_sharpe(a, b)


# ── conditionally-active sleeves ─────────────────────────────────────────────

def test_calendar_sharpe_scales_with_sqrt_activity():
    assert calendar_sharpe(1.5, 1.0) == pytest.approx(1.5)
    assert calendar_sharpe(1.5, 0.25) == pytest.approx(0.75)
    assert calendar_sharpe(1.5, 0.13) == pytest.approx(1.5 * np.sqrt(0.13))


def test_calendar_sharpe_rejects_invalid_activity():
    for a in (0.0, -0.1, 1.5):
        with pytest.raises(ValueError):
            calendar_sharpe(1.0, a)


def test_calendar_sharpe_matches_an_explicitly_gated_series():
    n = 8000
    rng = np.random.default_rng(11)
    idx = pd.bdate_range("2000-01-03", periods=n)
    active = rng.random(n) < 0.13
    raw = _series(0.20, 0.12, n, 12, "c")
    raw.index = idx
    gated = conditional_sleeve_series(raw[active], idx)
    sr_active = raw[active].mean() / raw[active].std(ddof=1) * np.sqrt(PPY)
    sr_cal = gated.mean() / gated.std(ddof=1) * np.sqrt(PPY)
    assert sr_cal == pytest.approx(calendar_sharpe(sr_active, active.mean()), rel=0.10)


def test_complementary_gating_gives_non_positive_correlation():
    """A sleeve that trades only when the book is flat cannot be positively
    correlated with it — so its hurdle rho*s_b is <= 0."""
    n = 4000
    idx = pd.bdate_range("2005-01-03", periods=n)
    rng = np.random.default_rng(13)
    book_on = rng.random(n) < 0.87
    book = conditional_sleeve_series(
        pd.Series(rng.normal(0.0008, 0.01, n), index=idx, name="book")[book_on], idx)
    cand = conditional_sleeve_series(
        pd.Series(rng.normal(0.0015, 0.01, n), index=idx, name="cand")[~book_on], idx)
    rho = float(pd.concat([book, cand], axis=1).corr().iloc[0, 1])
    assert rho <= 0.0
    assert marginal_hurdle_sharpe(1.0, rho) <= 0.0
    assert delta_sharpe(book, cand, periods_per_year=PPY) > 0


def test_conditional_sleeve_series_pads_with_flat_days():
    idx = pd.bdate_range("2020-01-01", periods=10)
    active = pd.Series([0.01, -0.02], index=[idx[2], idx[7]], name="c")
    out = conditional_sleeve_series(active, idx)
    assert len(out) == 10
    assert out.iloc[0] == 0.0
    assert out.loc[idx[2]] == 0.01


# ── bootstrap / significance ─────────────────────────────────────────────────

def test_stationary_bootstrap_indices_shape_and_range():
    rng = np.random.default_rng(0)
    idx = stationary_bootstrap_indices(500, 10.0, rng)
    assert idx.shape == (500,)
    assert idx.min() >= 0 and idx.max() < 500


def test_stationary_bootstrap_preserves_serial_dependence():
    """A block resample of an AR(1) keeps most of its lag-1 autocorrelation;
    an IID resample destroys it. This is why the project bans IID here."""
    n = 4000
    rng = np.random.default_rng(2)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = 0.7 * x[t - 1] + rng.normal()
    ac = lambda v: float(np.corrcoef(v[:-1], v[1:])[0, 1])
    blocked = ac(x[stationary_bootstrap_indices(n, 40.0, rng)])
    iid = ac(x[rng.integers(0, n, n)])
    assert blocked > 0.5
    assert abs(iid) < 0.1


def test_bootstrap_delta_sharpe_brackets_the_point_estimate():
    n = 2000
    book = _series(0.09, 0.10, n, 21, "book")
    cand = _series(0.03, 0.06, n, 22, "cand")
    boot = bootstrap_delta_sharpe(book, cand, periods_per_year=PPY, n_boot=200, seed=1)
    point = delta_sharpe(book, cand, periods_per_year=PPY)
    lo, hi = np.percentile(boot, [1, 99])
    assert lo <= point <= hi
    assert boot.shape == (200,)


# ── the gate ─────────────────────────────────────────────────────────────────

def test_admit_passes_a_real_uncorrelated_diversifier():
    n = 6000
    book = _series(0.09, 0.10, n, 31, "book")
    cand = _series(0.075, 0.06, n, 32, "cand")
    res = admit(book, cand, periods_per_year=PPY, n_boot=400, seed=3)
    assert res.verdict == "PASS"
    assert res.delta_sharpe > 0
    assert res.p_value < res.alpha_effective
    assert set(res.weights) == {"book", "cand"}


def test_a_modest_diversifier_is_underpowered_on_a_realistic_sample():
    """Honest power check: ~12 years of daily data still cannot certify a
    +0.22 Sharpe improvement at 95%. The gate must say MARGINAL, not PASS —
    and must report the Delta SR the sample could actually have detected."""
    n = 3000
    book = _series(0.09, 0.10, n, 31, "book")
    cand = _series(0.04, 0.06, n, 32, "cand")
    res = admit(book, cand, periods_per_year=PPY, n_boot=400, seed=3)
    assert res.verdict == "MARGINAL"
    assert 0 < res.delta_sharpe < res.detectable_delta_sharpe
    assert any("UNDERPOWERED" in note for note in res.notes)


def test_admit_fails_a_dominated_correlated_sleeve():
    n = 3000
    rng = np.random.default_rng(33)
    common = rng.normal(size=n)
    book = _series(0.12, 0.10, n, 34, "book", common=common, beta=0.95)
    cand = _series(0.00, 0.10, n, 35, "cand", common=common, beta=0.95)
    res = admit(book, cand, periods_per_year=PPY, n_boot=300, seed=4)
    assert res.verdict == "FAIL"
    assert res.delta_sharpe < 0


def test_admit_returns_marginal_when_improvement_is_inside_the_noise():
    """Short sample, tiny edge -> positive Delta SR that must NOT be a PASS."""
    n = 120
    book = _series(0.09, 0.10, n, 41, "book")
    cand = _series(0.005, 0.06, n, 42, "cand")
    res = admit(book, cand, periods_per_year=PPY, n_boot=300, seed=5, min_obs=250)
    assert res.verdict in {"MARGINAL", "FAIL"}
    if res.verdict == "MARGINAL":
        assert res.delta_sharpe > 0 and res.p_value > res.alpha_effective
    assert any("n=120" in note for note in res.notes)


def test_admit_tightens_alpha_with_multiple_trials():
    n = 3000
    book = _series(0.09, 0.10, n, 51, "book")
    cand = _series(0.04, 0.06, n, 52, "cand")
    one = admit(book, cand, periods_per_year=PPY, n_boot=200, seed=6, n_trials=1)
    many = admit(book, cand, periods_per_year=PPY, n_boot=200, seed=6, n_trials=50)
    assert many.alpha_effective < one.alpha_effective
    assert many.alpha_effective == pytest.approx(1 - 0.95 ** (1 / 50))


def test_admit_flags_a_conditionally_active_candidate():
    n = 1500
    idx = pd.bdate_range("2010-01-04", periods=n)
    book = _series(0.09, 0.10, n, 61, "book")
    book.index = idx
    raw = _series(0.25, 0.12, n, 62, "cand")
    raw.index = idx
    mask = np.random.default_rng(63).random(n) < 0.13
    cand = conditional_sleeve_series(raw[mask], idx)
    res = admit(book, cand, periods_per_year=PPY, n_boot=200, seed=7)
    assert any("flat on" in note for note in res.notes)


def test_admit_accepts_a_multi_sleeve_book_dataframe():
    n = 2500
    df = pd.concat([_series(0.09, 0.10, n, 71, "s1"), _series(0.06, 0.08, n, 72, "s2")], axis=1)
    cand = _series(0.04, 0.05, n, 73, "cand")
    res = admit(df, cand, periods_per_year=PPY, n_boot=200, seed=8)
    assert set(res.weights) == {"s1", "s2", "cand"}
    assert res.n_obs == n


# ── barrier / p(pass) ────────────────────────────────────────────────────────

def test_barrier_config_validates():
    with pytest.raises(ValueError):
        BarrierConfig(daily_stop=0.0)


def test_simulate_campaign_probabilities_are_a_partition():
    r = _series(0.30, 0.15, 800, 81, "book")
    res = simulate_campaign(r, BarrierConfig(), n_paths=300, seed=9)
    total = res.p_pass + res.p_fail_floor + res.p_fail_daily + res.p_timeout
    assert total == pytest.approx(1.0)
    assert 0.0 <= res.p_pass <= 1.0


def test_simulate_campaign_needs_enough_observations():
    with pytest.raises(ValueError):
        simulate_campaign(np.zeros(5))


def test_better_book_has_higher_pass_probability():
    good = _series(0.40, 0.15, 800, 91, "good")
    bad = _series(0.02, 0.15, 800, 92, "bad")
    cfg = BarrierConfig()
    p_good = simulate_campaign(good, cfg, n_paths=400, seed=10).p_pass
    p_bad = simulate_campaign(bad, cfg, n_paths=400, seed=10).p_pass
    assert p_good > p_bad


def test_daily_stop_binds_on_a_fat_left_tail_at_equal_sharpe():
    """Two books, same Sharpe, different daily skew -> different p(pass).
    Demonstrates why Sharpe alone cannot rank propfirm candidates."""
    n, cfg = 1500, BarrierConfig()
    rng = np.random.default_rng(101)
    smooth = rng.normal(0.0, 1.0, n)
    lumpy = rng.standard_t(2.5, n)
    def norm(x: np.ndarray) -> pd.Series:
        z = (x - x.mean()) / x.std(ddof=1)
        return pd.Series(0.30 / PPY + z * 0.15 / np.sqrt(PPY),
                         index=pd.bdate_range("2012-01-02", periods=n))
    s_smooth, s_lumpy = norm(smooth), norm(lumpy)
    sr = lambda s: s.mean() / s.std(ddof=1) * np.sqrt(PPY)
    assert sr(s_smooth) == pytest.approx(sr(s_lumpy), rel=1e-9)
    r_smooth = simulate_campaign(s_smooth, cfg, n_paths=500, seed=11)
    r_lumpy = simulate_campaign(s_lumpy, cfg, n_paths=500, seed=11)
    assert r_lumpy.p_fail_daily > r_smooth.p_fail_daily


def test_pass_probability_delta_is_paired_and_reports_days():
    n = 1200
    book = _series(0.08, 0.14, n, 111, "book")
    cand = _series(0.06, 0.10, n, 112, "cand")
    out = pass_probability_delta(book, cand, n_paths=400, seed=12)
    assert out["delta_p_pass"] == pytest.approx(out["p_pass_combined"] - out["p_pass_book"])
    assert "delta_median_days" in out
    assert out["delta_p_pass"] > 0


def test_vol_normalisation_removes_the_erc_delevering_artefact():
    """Without re-levering, ERC halves the incumbent's exposure and the combined
    book can look worse on p(pass) even when it is strictly better per unit of
    risk. The default must isolate diversification, not de-leveraging."""
    n = 1200
    book = _series(0.08, 0.14, n, 111, "book")
    cand = _series(0.06, 0.10, n, 112, "cand")
    norm = pass_probability_delta(book, cand, n_paths=400, seed=12, normalize_vol=True)
    raw = pass_probability_delta(book, cand, n_paths=400, seed=12, normalize_vol=False)
    assert norm["delta_p_pass"] > raw["delta_p_pass"]


def test_pass_probability_delta_without_candidate_is_a_baseline():
    book = _series(0.20, 0.12, 900, 121, "book")
    out = pass_probability_delta(book, None, n_paths=200, seed=13)
    assert out["delta_p_pass"] == 0.0
    assert 0.0 <= out["p_pass_book"] <= 1.0


@pytest.mark.slow
def test_delta_p_pass_is_stable_across_seeds_at_high_path_count():
    """MC noise must not be able to flip an admission verdict.

    At the default path count Delta p(pass) carries roughly +/-1pt of standard
    error; this pins the estimate across independent seeds so a real +4pt effect
    can never be an artefact of the draw. Slow by construction — it exists to
    calibrate how many paths the fast tests need, not to be run on every edit.
    """
    n = 1200
    book = _series(0.08, 0.14, n, 111, "book")
    cand = _series(0.06, 0.10, n, 112, "cand")
    deltas = [
        pass_probability_delta(book, cand, n_paths=8000, seed=s)["delta_p_pass"]
        for s in (0, 1, 2)
    ]
    assert min(deltas) > 0.0
    assert max(deltas) - min(deltas) < 0.03


def test_flat_filling_sleeve_beats_its_solo_sharpe_on_p_pass():
    """The case the ratio gate mis-prices: a sleeve active only while the book
    is idle has a modest calendar Sharpe but removes dead calendar time, which
    is what a first-passage target rewards."""
    n = 2000
    idx = pd.bdate_range("2008-01-02", periods=n)
    rng = np.random.default_rng(131)
    on = rng.random(n) < 0.60                     # book idle 40% of days
    book = conditional_sleeve_series(
        pd.Series(rng.normal(0.0012, 0.011, n), index=idx, name="book")[on], idx)
    cand = conditional_sleeve_series(
        pd.Series(rng.normal(0.0012, 0.011, n), index=idx, name="cand")[~on], idx)
    sr = lambda s: s.mean() / s.std(ddof=1) * np.sqrt(PPY)
    assert sr(cand) < sr(book)                    # solo it looks worse
    out = pass_probability_delta(book, cand, n_paths=400, seed=14, scale=3.0)
    assert out["delta_p_pass"] > 0
    assert out["delta_median_days"] < 0           # and it gets funded sooner
