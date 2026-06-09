"""
test_engine.py — unit tests for the FTMO first-passage engine.
Run: pytest -q  (from the ftmo_alpha_program directory)
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.ftmo_first_passage import (
    pass_prob_closed_form, simulate_bm_first_passage, combined_pass_prob_closed_form,
    combined_pass_prob_empirical, annual_to_daily_sharpe, FTMO_MAX_DD_PCT, FTMO_P1_TGT_PCT,
)


@pytest.mark.parametrize("Sd,n", [(0.03, 5), (0.072, 10), (0.12, 20), (0.05, 8)])
def test_symmetric_is_logistic(Sd, n):
    assert abs(pass_prob_closed_form(Sd, n) - 1.0 / (1.0 + np.exp(-2 * Sd * n))) < 1e-12


def test_zero_drift_is_distance_ratio():
    # zero-drift random walk: P(up first) = n_dd/(n_dd+n_tgt)
    assert abs(pass_prob_closed_form(0.0, n_dd=10, n_tgt=5) - 10 / 15) < 1e-9


def test_closer_target_is_easier():
    # Phase 2 (n_tgt=5) must beat symmetric (n_tgt=10) at the same floor
    Sd = 0.06
    assert pass_prob_closed_form(Sd, n_dd=10, n_tgt=5) > pass_prob_closed_form(Sd, n_dd=10, n_tgt=10)


@pytest.mark.parametrize("sa,sigma", [(0.95, 0.01), (1.43, 0.005), (1.90, 0.02)])
def test_mc_reproduces_closed_form(sa, sigma):
    Sd = annual_to_daily_sharpe(sa)
    cf = pass_prob_closed_form(Sd, FTMO_MAX_DD_PCT / sigma)
    mc = simulate_bm_first_passage(Sd, sigma, FTMO_MAX_DD_PCT, FTMO_P1_TGT_PCT,
                                   n_paths=40_000, substeps=20, seed=3)["p_pass"]
    assert abs(mc - cf) < 0.015


def test_pass_prob_monotonic_in_sharpe():
    p = [combined_pass_prob_closed_form(annual_to_daily_sharpe(sa), 0.01)["p_combined"]
         for sa in (0.5, 1.0, 1.5, 2.0)]
    assert all(p[i] < p[i + 1] for i in range(len(p) - 1))


def test_lower_vol_raises_pass_prob_at_fixed_sharpe():
    Sd = annual_to_daily_sharpe(1.2)
    assert (combined_pass_prob_closed_form(Sd, 0.005)["p_combined"]
            > combined_pass_prob_closed_form(Sd, 0.02)["p_combined"])


def test_empirical_is_conservative_vs_closed_form():
    # The discrete *daily* empirical evaluation is, by construction, modestly MORE
    # conservative than the continuous-time closed-form idealisation (discrete
    # monitoring cannot exploit intra-day barrier dynamics). On a Gaussian series
    # the gap is small (~0.03/phase) and in the conservative direction — a property
    # we assert rather than a tight equality.
    rng = np.random.default_rng(0)
    sigma, Sd = 0.01, annual_to_daily_sharpe(1.3)
    daily = rng.normal(Sd * sigma, sigma, size=1500)
    emp = combined_pass_prob_empirical(daily, n_paths=12000, max_days=600, seed=1)["p_combined"]
    cf = combined_pass_prob_closed_form(Sd, sigma)["p_combined"]
    assert emp <= cf + 0.02            # not optimistic vs the idealisation
    assert (cf - emp) < 0.20           # but in the same ballpark


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
