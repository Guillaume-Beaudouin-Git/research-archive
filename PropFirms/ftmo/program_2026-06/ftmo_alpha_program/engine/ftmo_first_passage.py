"""
ftmo_first_passage.py — symmetric-barrier first-passage engine for FTMO evaluations
====================================================================================

Implements the theoretical core of the Propfirm Alpha Research Program
(white paper, May 2026, §3 + Appendix A) and the *re-parameterised* Monte-Carlo
simulator demanded by Phase 0 of the roadmap:

    static 10% max-DD  +  10%/5% phase targets  +  5% daily-loss floor  +  NO time limit.

Two layers, deliberately separated:

  1. Closed form (Gaussian / arithmetic-Brownian-motion increments).
     P(pass one phase) for a barrier at -B_dd (floor) and +B_tgt (target):

         psi(0) = (1 - e^{2 Sd n_dd}) / (e^{-2 Sd n_tgt} - e^{2 Sd n_dd})

     which, in the symmetric case n_dd = n_tgt = n, collapses to the logistic

         P = 1 / (1 + e^{-2 Sd n})                                   (white paper Eq. 1)

     with  Sd = mu/sigma  (daily Sharpe)  and  n = B/sigma  (vol-units to barrier).

  2. Monte-Carlo simulators that re-derive the same number empirically and then
     extend it to the realistic, non-Gaussian, path-dependent case:
       - `simulate_bm_first_passage`        : fine-grid Euler BM, used to *validate*
         the closed form (Phase-0 gate: "simulator reproduces a known case").
       - `simulate_empirical_phase`         : Politis-Romano stationary block bootstrap
         on a real daily-PnL series, static max-DD + 5% daily floor as absorbing
         barriers, no time limit. Production engine for Phase 2 (mirrors
         _audit/strategy_c_ftmo_account_sweep.py). Fully vectorised/batched.

Why the closed form is *optimistic* for real strategies: it assumes Gaussian
increments. Fat left tails (a trend day that ruins a mean-reversion book) make the
realised crossing probability strictly worse than logistic, because a single outsized
loss can touch -B_dd in one step. That is exactly why the kurtosis gate (Table 2) is
first-order, and why the empirical bootstrap — not the formula — is the binding test.

References
----------
White paper §3, §3.2, §3.4, Table 1, Fig. 1, Appendix A.
CLAUDE.md L24 (distribution-shape-driven, scale-invariant), L22 (MC eval mandatory).
Portfolio/risk/propfirm_canonical.py (5% daily / 10% max-DD canonical).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

# ── FTMO Standard canonical parameters (propfirm_canonical.py) ────────────────
FTMO_MAX_DD_PCT: float = 0.10   # static, from starting balance
FTMO_DAILY_PCT:  float = 0.05   # daily-loss floor (resets each session)
FTMO_P1_TGT_PCT: float = 0.10   # Phase 1 profit target
FTMO_P2_TGT_PCT: float = 0.05   # Phase 2 profit target
TRADING_DAYS_YEAR: int = 252


# ──────────────────────────────────────────────────────────────────────────────
# 1. Closed form
# ──────────────────────────────────────────────────────────────────────────────

def pass_prob_closed_form(daily_sharpe: float, n_dd: float,
                          n_tgt: float | None = None) -> float:
    """
    Probability of touching the +target barrier before the -drawdown barrier,
    for an arithmetic Brownian motion with daily Sharpe `daily_sharpe`.

    Symmetric case (n_tgt == n_dd == n) reduces to the logistic 1/(1+e^{-2 Sd n}).
    Derived in Appendix A from (1/2) sigma^2 psi'' + mu psi' = 0.
    """
    if n_tgt is None:
        n_tgt = n_dd
    Sd = float(daily_sharpe)

    if abs(Sd) < 1e-12:                      # zero-drift random walk → ratio of distances
        return float(n_dd / (n_dd + n_tgt))
    if abs(n_tgt - n_dd) < 1e-12:            # symmetric: numerically stable logistic
        return float(1.0 / (1.0 + np.exp(-2.0 * Sd * n_dd)))

    k_dd = 2.0 * Sd * n_dd
    k_tgt = 2.0 * Sd * n_tgt
    num = 1.0 - np.exp(k_dd)
    den = np.exp(-k_tgt) - np.exp(k_dd)
    return float(num / den)


def combined_pass_prob_closed_form(daily_sharpe: float, sigma_d: float,
                                   max_dd: float = FTMO_MAX_DD_PCT,
                                   p1_tgt: float = FTMO_P1_TGT_PCT,
                                   p2_tgt: float = FTMO_P2_TGT_PCT) -> dict:
    """
    Combined two-phase pass probability under the FTMO Standard structure:
      Phase 1 : symmetric  +p1_tgt / -max_dd  (10% / 10%)
      Phase 2 : asymmetric +p2_tgt / -max_dd  ( 5% / 10%, the easier phase)
    `sigma_d` is per-day equity volatility in fraction-of-balance units.
    """
    n_dd = max_dd / sigma_d
    p1 = pass_prob_closed_form(daily_sharpe, n_dd=n_dd, n_tgt=p1_tgt / sigma_d)
    p2 = pass_prob_closed_form(daily_sharpe, n_dd=n_dd, n_tgt=p2_tgt / sigma_d)
    return {"p1": p1, "p2": p2, "p_combined": p1 * p2,
            "n_dd": n_dd, "n_tgt_p1": p1_tgt / sigma_d, "n_tgt_p2": p2_tgt / sigma_d}


def expected_days_to_target(daily_sharpe: float, n_tgt: float) -> float:
    """Drift-dominated mean first-passage time to the target: E[tau] ~ n/Sd (Appendix A)."""
    if daily_sharpe <= 0:
        return float("inf")
    return float(n_tgt / daily_sharpe)


def annual_to_daily_sharpe(sharpe_annual: float,
                           periods: int = TRADING_DAYS_YEAR) -> float:
    return float(sharpe_annual / np.sqrt(periods))


# ──────────────────────────────────────────────────────────────────────────────
# 2a. Gaussian BM simulator — validates the closed form (vectorised, block-wise)
# ──────────────────────────────────────────────────────────────────────────────

def simulate_bm_first_passage(daily_sharpe: float, sigma_d: float,
                              max_dd: float, target: float,
                              n_paths: int = 40_000, max_days: int | None = None,
                              substeps: int = 10, seed: int = 0,
                              block: int = 500, horizon_cap_days: int = 3000) -> dict:
    """
    Euler simulation of an arithmetic BM with absorbing barriers at -max_dd and
    +target, monitored on a fine sub-daily grid so discrete-monitoring overshoot is
    negligible and the result converges to the continuous-time closed form.
    Processed in time-blocks (vectorised over alive paths) for speed.
    `max_days=None` → run to absorption (capped at `horizon_cap_days`).
    """
    rng = np.random.default_rng(seed)
    mu_step = daily_sharpe * sigma_d / substeps
    sd_step = sigma_d / np.sqrt(substeps)
    horizon_days = max_days if max_days is not None else horizon_cap_days
    n_steps = horizon_days * substeps

    x = np.zeros(n_paths)
    alive = np.ones(n_paths, dtype=bool)
    passed = np.zeros(n_paths, dtype=bool)
    breached = np.zeros(n_paths, dtype=bool)
    hit_step = np.full(n_paths, np.nan)

    done = 0
    while done < n_steps and alive.any():
        b = min(block, n_steps - done)
        g = np.flatnonzero(alive)
        inc = rng.normal(mu_step, sd_step, size=(g.size, b))
        csum = x[g][:, None] + np.cumsum(inc, axis=1)
        up = csum >= target
        dn = csum <= -max_dd
        crossed = up | dn
        any_cross = crossed.any(axis=1)
        first = crossed.argmax(axis=1)
        rows = np.arange(g.size)
        is_up = up[rows, first] & any_cross
        is_dn = any_cross & ~is_up
        passed[g[is_up]] = True
        breached[g[is_dn]] = True
        hit_step[g[any_cross]] = done + first[any_cross] + 1
        # advance survivors to end of block
        surv = ~any_cross
        x[g[surv]] = csum[surv, -1]
        alive[g[any_cross]] = False
        done += b

    hit_day = hit_step / substeps
    return {
        "p_pass": float(passed.mean()),
        "p_breach": float(breached.mean()),
        "p_timeout": float(alive.mean()),
        "median_days_to_pass": float(np.nanmedian(hit_day[passed])) if passed.any() else None,
        "n_paths": n_paths,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 2b. Empirical stationary-block bootstrap — production engine (Phase 2)
# ──────────────────────────────────────────────────────────────────────────────

def stationary_block_indices(T: int, length: int, block_size: float,
                             rng: np.random.Generator) -> np.ndarray:
    """
    Politis-Romano (1994) stationary block bootstrap index sampler (scalar form,
    kept for unit tests). Block lengths ~ Geometric(1/block_size), circular wrap.
    """
    idx = np.empty(length, dtype=np.int64)
    pos = 0
    p = 1.0 / max(1.0, block_size)
    while pos < length:
        block_len = max(1, int(rng.geometric(p)))
        block_len = min(block_len, length - pos)
        start = int(rng.integers(0, T))
        idx[pos:pos + block_len] = (np.arange(start, start + block_len)) % T
        pos += block_len
    return idx


def _stationary_block_matrix(T: int, n_paths: int, length: int,
                             block_size: float, rng: np.random.Generator) -> np.ndarray:
    """
    Vectorised stationary bootstrap: at each step, restart a new block at a uniform
    random position with prob p = 1/block_size, else continue (prev+1 mod T).
    Returns an (n_paths x length) int index matrix into the source series.
    """
    p = 1.0 / max(1.0, block_size)
    restart = rng.random((n_paths, length)) < p
    restart[:, 0] = True
    starts = rng.integers(0, T, size=(n_paths, length))
    idx = np.empty((n_paths, length), dtype=np.int64)
    idx[:, 0] = starts[:, 0]
    for t in range(1, length):                 # ~length iterations, vectorised over paths
        cont = (idx[:, t - 1] + 1) % T
        idx[:, t] = np.where(restart[:, t], starts[:, t], cont)
    return idx


@dataclass
class PhaseResult:
    p_pass: float
    p_breach_dd: float
    p_breach_daily: float
    p_timeout: float
    median_days_to_pass: float | None
    p99_max_dd: float
    n_paths: int


def simulate_empirical_phase(daily_ret: np.ndarray, target: float,
                             max_dd: float = FTMO_MAX_DD_PCT,
                             daily_floor: float = FTMO_DAILY_PCT,
                             n_paths: int = 20_000, max_days: int | None = None,
                             block_size: float | None = None, seed: int = 42,
                             batch: int = 5_000) -> PhaseResult:
    """
    One FTMO phase on an empirical daily-return series (fraction of starting
    balance) via stationary block bootstrap, with absorbing barriers:
      - daily-loss floor : a single day with ret <= -daily_floor  → breach (intraday)
      - static max-DD    : cumulative equity <= -max_dd (from start) → breach (EOD)
      - target           : cumulative equity >= +target → pass (EOD)
    Priority on a tie-day: daily-loss > max-DD/target. No time limit by default.
    """
    daily_ret = np.asarray(daily_ret, dtype=np.float64)
    T = len(daily_ret)
    if block_size is None:
        block_size = max(1.0, round(np.sqrt(T)))
    horizon = max_days if max_days is not None else T
    rng = np.random.default_rng(seed)
    BIG = horizon + 10

    status = np.empty(n_paths, dtype=np.int8)
    days_to_pass = np.zeros(n_paths, dtype=np.int32)
    max_dd_seen = np.zeros(n_paths, dtype=np.float64)
    cols = np.arange(horizon)

    for s0 in range(0, n_paths, batch):
        bs = min(batch, n_paths - s0)
        idx = _stationary_block_matrix(T, bs, horizon, block_size, rng)
        R = daily_ret[idx]                      # (bs, horizon)
        eq = np.cumsum(R, axis=1)

        daily_hit = R <= -daily_floor
        t_daily = np.where(daily_hit.any(1), daily_hit.argmax(1), BIG)
        dd_hit = eq <= -max_dd
        t_dd = np.where(dd_hit.any(1), dd_hit.argmax(1), BIG)
        pass_hit = eq >= target
        t_pass = np.where(pass_hit.any(1), pass_hit.argmax(1), BIG)

        t_eod = np.minimum(t_dd, t_pass)
        eod_is_pass = t_pass <= t_dd
        st = np.full(bs, 3, dtype=np.int8)               # timeout default
        is_daily = (t_daily <= t_eod) & (t_daily < BIG)
        is_eod = (~is_daily) & (t_eod < BIG)
        st[is_daily] = 1
        st[is_eod & eod_is_pass] = 0
        st[is_eod & ~eod_is_pass] = 2
        status[s0:s0 + bs] = st
        days_to_pass[s0:s0 + bs] = np.where(st == 0, t_pass + 1, 0)

        # max drawdown up to absorption day (inclusive)
        run_peak = np.maximum.accumulate(
            np.concatenate([np.zeros((bs, 1)), eq], axis=1), axis=1)[:, 1:]
        dd = run_peak - eq
        t_stop = np.minimum(np.minimum(t_daily, t_eod), horizon - 1)
        mask = cols[None, :] <= t_stop[:, None]
        max_dd_seen[s0:s0 + bs] = np.where(mask, dd, -np.inf).max(axis=1)

    passed = status == 0
    return PhaseResult(
        p_pass=float(passed.mean()),
        p_breach_dd=float((status == 2).mean()),
        p_breach_daily=float((status == 1).mean()),
        p_timeout=float((status == 3).mean()),
        median_days_to_pass=float(np.median(days_to_pass[passed])) if passed.any() else None,
        p99_max_dd=float(np.percentile(max_dd_seen, 99)),
        n_paths=n_paths,
    )


def combined_pass_prob_empirical(daily_ret: np.ndarray, n_paths: int = 20_000,
                                 max_days: int | None = None, seed: int = 42,
                                 max_dd: float = FTMO_MAX_DD_PCT,
                                 daily_floor: float = FTMO_DAILY_PCT,
                                 p1_tgt: float = FTMO_P1_TGT_PCT,
                                 p2_tgt: float = FTMO_P2_TGT_PCT) -> dict:
    """Combined two-phase empirical pass probability with a delta-method 95% CI."""
    p1 = simulate_empirical_phase(daily_ret, p1_tgt, max_dd, daily_floor,
                                  n_paths, max_days, seed=seed)
    p2 = simulate_empirical_phase(daily_ret, p2_tgt, max_dd, daily_floor,
                                  n_paths, max_days, seed=seed + 1)
    p_comb = p1.p_pass * p2.p_pass
    se1 = np.sqrt(p1.p_pass * (1 - p1.p_pass) / n_paths)
    se2 = np.sqrt(p2.p_pass * (1 - p2.p_pass) / n_paths)
    se_comb = np.sqrt((p2.p_pass * se1) ** 2 + (p1.p_pass * se2) ** 2)
    return {
        "p1": asdict(p1), "p2": asdict(p2),
        "p_combined": p_comb,
        "p_combined_ci95": [max(0.0, p_comb - 1.96 * se_comb),
                            min(1.0, p_comb + 1.96 * se_comb)],
        "median_sessions_to_pass": (
            (p1.median_days_to_pass + p2.median_days_to_pass)
            if p1.median_days_to_pass and p2.median_days_to_pass else None),
    }


def tail_dd_gate(daily_ret: np.ndarray, threshold: float = 0.08,
                 window: int = 60, n_paths: int = 20_000, seed: int = 7) -> dict:
    """
    Table-2 tail-DD gate. The white paper frames this as the real drawdown gate
    against the static -10% floor: the probability that equity *excurses to
    -threshold from the starting balance* within `window` sessions (an 8% loss is
    the danger zone before the 10% floor). Gate passes if < 10%.

    We also report peak-to-trough drawdown ≥ threshold for completeness (a stricter,
    path-shape diagnostic), but the gate is on the floor-excursion definition.
    """
    daily_ret = np.asarray(daily_ret, dtype=np.float64)
    T = len(daily_ret)
    block = max(1.0, round(np.sqrt(T)))
    rng = np.random.default_rng(seed)
    idx = _stationary_block_matrix(T, n_paths, window, block, rng)
    eq = np.cumsum(daily_ret[idx], axis=1)
    floor_touch = (eq <= -threshold).any(1)
    run_peak = np.maximum.accumulate(
        np.concatenate([np.zeros((n_paths, 1)), eq], axis=1), axis=1)[:, 1:]
    dd_touch = ((run_peak - eq) >= threshold).any(1)
    return {"p_floor_excursion": float(floor_touch.mean()),
            "p_peak_trough_dd": float(dd_touch.mean()),
            "gate_pass": bool(floor_touch.mean() < 0.10)}
