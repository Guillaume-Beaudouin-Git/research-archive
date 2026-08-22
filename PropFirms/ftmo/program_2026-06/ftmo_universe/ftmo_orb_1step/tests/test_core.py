"""Data-free invariant tests for the FTMO simulator and the DP sizer.
These encode the correctness properties that matter: barrier logic, drawdown rules,
horizon/edge monotonicity, and DP optimality bounds."""
import numpy as np, pandas as pd
import ftmo_sim as F
import dp_sizing as D
import ftmo_1step_real as O

rng = np.random.default_rng(0)
POS = pd.Series(rng.normal(0.06, 1.0, 2000))     # positive-Sharpe synthetic daily R-multiple
ZERO = pd.Series(np.zeros(800))

def test_horizon_monotone():
    r = F.simulate(POS, N=8000, T=252, rho=0.03, seed=1, one_step=True)
    dp = r["day_pass"]
    p21, p42, p252 = (np.mean(dp <= h) for h in (21, 42, 252))
    assert p21 <= p42 <= p252                     # more time can only help
    assert 0.0 <= p252 <= 1.0

def test_zero_returns_neither_pass_nor_bust():
    r = F.simulate(ZERO, N=4000, T=120, rho=0.03, seed=2, one_step=True)
    assert r["passed"].mean() == 0.0              # equity never moves -> never hits +10%
    assert r["busted"].mean() == 0.0              # ...nor the floor

def test_daily_5pct_rule_busts():
    # a series with a -1.4R day at rho=0.04 -> -5.6% day -> must breach the 5% daily limit
    s = pd.Series(np.r_[np.zeros(200), np.full(50, -1.4)])
    r = F.simulate(s, N=4000, T=60, rho=0.04, daily_stop=0.99, seed=3, one_step=True)
    assert r["busted"].mean() > 0.0

def test_positive_edge_beats_zero_edge():
    rp = F.simulate(POS, N=8000, T=252, rho=0.03, seed=4, one_step=True)["passed"].mean()
    rz = F.simulate(ZERO, N=8000, T=252, rho=0.03, seed=4, one_step=True)["passed"].mean()
    assert rp > rz

def test_dp_probabilities_bounded_and_easier_onestep():
    p1, _ = D.solve(POS, T=42, two_step=False)
    p2, _ = D.solve(POS, T=42, two_step=True)
    assert 0.0 <= p2 <= p1 <= 1.0                 # 1-step (one barrier) >= 2-step

def test_dp_more_time_helps():
    p42, _ = D.solve(POS, T=42, two_step=False)
    p84, _ = D.solve(POS, T=84, two_step=False)
    assert p84 + 1e-9 >= p42

def test_dp_policy_validation_runs():
    _, pol = D.solve(POS, T=42, two_step=False)
    v = D.validate(POS, pol, T=42, N=4000)
    assert 0.0 <= v["p"] <= 1.0 and 0.0 <= v["bust"] <= 1.0

def test_1step_best_day_rule_only_reduces_passes():
    # the Best-Day consistency rule is an extra constraint -> can only lower the pass rate
    on = np.mean(O.sim_1step(POS, N=6000, T=42, rho=0.02, best_day_rule=True, seed=1)["dpass"] <= 42)
    off = np.mean(O.sim_1step(POS, N=6000, T=42, rho=0.02, best_day_rule=False, seed=1)["dpass"] <= 42)
    assert on <= off + 1e-9

def test_1step_3pct_daily_rule_busts():
    s = pd.Series(np.r_[np.zeros(200), np.full(50, -1.2)])   # -1.2R at rho=0.03 -> -3.6% day
    r = O.sim_1step(s, N=4000, T=60, rho=0.03, seed=2)
    assert r["bust"] > 0.0
