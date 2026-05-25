"""
trailing_dd_simulator.py — Propfirm survival Monte Carlo simulator.

Models Tradeify Select Flex 25K mechanics exactly:
  - Eval: EOD trailing DD ($1,000), NO lock, 40% consistency cap
  - Funded: EOD trailing DD ($1,000), lock when EOD >= capital + DD_funded + $100

Sources:
  help.tradeify.co/articles/12853921 (eval rules, 2026-05-24 — 403 Forbidden, from session)
  help.tradeify.co/articles/12853966 (funded/flex rules, verbatim: "locks when EOD balance
    exceeds your drawdown amount by $100; floor = $100 above your starting balance")
  help.tradeify.co/articles/10495897 (trailing DD mechanics)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

import numpy as np
from numpy.typing import NDArray

PayoutRegime = Literal["no_payout", "greedy", "optimal"]


@dataclass(frozen=True)
class PropfirmConfig:
    """Tradeify Select Flex 25K canonical configuration.

    All defaults are confirmed from official sources (see module docstring).
    Create a custom instance for other propfirms or historical configs.
    """
    capital: float = 25_000.0
    profit_target: float = 1_500.0
    trailing_dd_eval: float = 1_000.0      # eval EOD trailing DD — confirmed
    trailing_dd_funded: float = 1_000.0    # funded EOD trailing DD — confirmed $1,000 (2026-05-25)
    lock_trigger_excess: float = 100.0     # lock when EOD >= capital+DD_funded+this
    locked_floor_offset: float = 100.0     # locked floor = capital + this = $25,100
    consistency_cap_pct: float = 0.40      # eval only: each day capped at 40%*target
    max_eval_days: int = 180               # no hard limit in rules; use 180 for sim
    funded_days: int = 180
    payout_threshold_days: int = 5         # winning days needed (since last payout)
    win_day_min_pnl: float = 100.0         # min daily PnL to count as winning day
    max_payout: float = 1_250.0            # per-request cap on 25K Select Flex
    payout_pct_of_profit: float = 0.50     # 50% of total profits per payout


@dataclass
class RunResult:
    eval_passed: bool = False
    busted: bool = False
    eval_days: int = 0
    funded_pnl: float = 0.0    # gross trading PnL in funded phase
    total_withdrawn: float = 0.0
    n_payouts: int = 0
    bust_phase: str = ""        # "eval" or "funded"
    funded_locked: bool = False  # whether funded floor ever locked (test aid)


@dataclass
class SimulationResult:
    n_runs: int
    p_eval_pass: float
    p_bust: float
    p_timeout: float
    e_days_to_target: float
    e_funded_pnl_180d: float
    payout_regime: PayoutRegime


def simulate_run(
    daily_pnl: NDArray[np.float64],
    config: PropfirmConfig,
    payout_regime: PayoutRegime = "no_payout",
) -> RunResult:
    """Simulate one propfirm challenge.

    DD is EOD-trailing with intraday enforcement: floor updates once per day at
    day-end from the running EOD equity peak, but is checked continuously intraday.
    A day's loss of `|pnl|` is treated as the maximum intraday drawdown for that day.

    EOD-only approximation validity: this simulator models `daily_pnl` as a single
    net figure and checks bust once per bar. This is exact when daily_pnl equals the
    worst intraday equity swing — which holds for Strategy C (hard SL cap per trade,
    max 1 trade/day). It overestimates survival for strategies with large intraday
    swings that recover by EOD (e.g., mean-reversion, multi-trade days without SL).
    Verify assumption before applying to a new strategy.

    Eval: no lock ever (Tradeify Select Flex: eval accounts do not lock).
    Funded: lock triggers when EOD balance >= capital + DD_funded + lock_trigger_excess
            OR on first payout, whichever comes first.
    """
    consistency_cap = config.consistency_cap_pct * config.profit_target
    lock_threshold = config.capital + config.trailing_dd_funded + config.lock_trigger_excess
    locked_floor = config.capital + config.locked_floor_offset

    result = RunResult()

    # ── EVAL PHASE ──────────────────────────────────────────────────────────
    equity = config.capital
    floor_e = config.capital - config.trailing_dd_eval
    cum_capped = 0.0
    n_eval_days = 0

    for pnl in daily_pnl[: config.max_eval_days]:
        n_eval_days += 1
        equity += pnl

        # Intraday enforcement: bust if equity <= floor before today's EOD update
        if equity <= floor_e:
            result.busted = True
            result.eval_days = n_eval_days
            result.bust_phase = "eval"
            return result

        # EOD: floor trails up with equity peak; NO lock in eval phase
        floor_e = max(floor_e, equity - config.trailing_dd_eval)

        # Consistency-capped profit accumulation (positive days only)
        if pnl > 0:
            cum_capped += min(pnl, consistency_cap)

        if cum_capped >= config.profit_target and equity >= config.capital + config.profit_target:
            result.eval_passed = True
            result.eval_days = n_eval_days
            break

    if not result.eval_passed:
        result.eval_days = n_eval_days
        return result

    # ── FUNDED PHASE ────────────────────────────────────────────────────────
    equity_f = config.capital
    floor_f = config.capital - config.trailing_dd_funded
    locked = False
    winning_days = 0
    gross_pnl = 0.0

    funded_slice = daily_pnl[n_eval_days : n_eval_days + config.funded_days]
    for pnl in funded_slice:
        equity_f += pnl
        gross_pnl += pnl

        current_floor = locked_floor if locked else floor_f
        if equity_f <= current_floor:
            result.busted = True
            result.bust_phase = "funded"
            result.funded_locked = locked
            result.funded_pnl = gross_pnl
            return result

        if not locked:
            floor_f = max(floor_f, equity_f - config.trailing_dd_funded)

        # Lock on EOD threshold
        if not locked and equity_f >= lock_threshold:
            locked = True

        # Winning day tracking (cumulative since last payout)
        if pnl >= config.win_day_min_pnl:
            winning_days += 1

        # Payout logic
        if payout_regime != "no_payout" and winning_days >= config.payout_threshold_days:
            gross_profit = equity_f - config.capital
            if gross_profit > 0:
                current_floor_check = locked_floor if locked else floor_f
                max_safe = equity_f - current_floor_check - 1.0
                payout = min(
                    config.payout_pct_of_profit * gross_profit,
                    config.max_payout,
                    max_safe,
                )
                if payout > 0:
                    do_payout = payout_regime == "greedy" or (
                        payout_regime == "optimal"
                        and payout >= config.win_day_min_pnl * config.payout_threshold_days
                    )
                    if do_payout:
                        result.n_payouts += 1
                        result.total_withdrawn += payout
                        equity_f -= payout
                        gross_pnl -= payout
                        winning_days = 0
                        if not locked:
                            locked = True  # first payout triggers lock

    result.funded_pnl = gross_pnl
    result.funded_locked = locked
    return result


def simulate_n_runs(
    n_runs: int,
    returns_generator: Callable[[], NDArray[np.float64]],
    config: PropfirmConfig | None = None,
    payout_regime: PayoutRegime = "no_payout",
) -> SimulationResult:
    """Monte Carlo simulation of propfirm challenge.

    Args:
        n_runs: Number of simulation paths.
        returns_generator: Returns a daily P&L array in USD (including no-trade days).
                          Must produce at least max_eval_days + funded_days values.
        config: Propfirm config; defaults to Tradeify Select Flex 25K.
        payout_regime: "no_payout" | "greedy" | "optimal".

    Returns:
        SimulationResult with aggregate statistics.
    """
    if config is None:
        config = PropfirmConfig()

    n_pass = n_bust = 0
    days_to_pass: list[int] = []
    funded_pnl_pass: list[float] = []

    for _ in range(n_runs):
        res = simulate_run(returns_generator(), config, payout_regime)
        if res.eval_passed:
            n_pass += 1
            days_to_pass.append(res.eval_days)
            funded_pnl_pass.append(res.funded_pnl)
        elif res.busted:
            n_bust += 1

    return SimulationResult(
        n_runs=n_runs,
        p_eval_pass=n_pass / n_runs,
        p_bust=n_bust / n_runs,
        p_timeout=(n_runs - n_pass - n_bust) / n_runs,
        e_days_to_target=float(np.mean(days_to_pass)) if days_to_pass else float("nan"),
        e_funded_pnl_180d=float(np.mean(funded_pnl_pass)) if funded_pnl_pass else float("nan"),
        payout_regime=payout_regime,
    )


def make_gaussian_generator(
    n_days: int,
    n_contracts: int = 1,
    mu_per_contract: float = 45.0,
    sigma_per_contract: float = 280.0,
    rho: float = -0.05,
    seed: int | None = None,
) -> Callable[[], NDArray[np.float64]]:
    """AR(1) Gaussian generator — general-purpose, NOT calibrated for iter_10.

    For iter_10 survival tests use make_iter10_trade_generator, which respects
    the hard SL cap (bounded daily loss). The Gaussian allows unrealistic
    tail losses that inflate bust probability vs block bootstrap reality.
    """
    rng = np.random.default_rng(seed)
    mu = mu_per_contract * n_contracts
    sigma = sigma_per_contract * n_contracts
    innov_std = sigma * np.sqrt(1.0 - rho ** 2)

    def generate() -> NDArray[np.float64]:
        innovations = rng.normal(0.0, innov_std, size=n_days)
        series = np.empty(n_days)
        series[0] = innovations[0] + mu
        for i in range(1, n_days):
            series[i] = rho * (series[i - 1] - mu) + innovations[i] + mu
        return series

    return generate


def make_iter10_trade_generator(
    n_days: int,
    n_mnq: int = 3,
    seed: int | None = None,
) -> Callable[[], NDArray[np.float64]]:
    """Trade-based daily P&L generator calibrated to iter_10 (N=346, Sharpe 1.52).

    Models Strategy C correctly: max 1 trade per day, hard SL cap, bounded losses.

    Scales iter_10 NQ trade stats to n_mnq MNQ contracts using:
      nq_pts = (nq_pnl + $19 cost) / 20 (NQ point value)
      mnq_pnl = nq_pts × $2 × n_mnq - $2.15 × n_mnq (MNQ cost)

    Per-trade stats (from results.json iter_10):
      avg_winner_nq=$1,571.60, avg_loser_nq=-$421.45, win_rate=27.75%
      trade_freq=45.8% (346 trades / ~756 trading days 2022-2025)

    Reproduces iter_10 MC for 3 MNQ + $1,000 DD (correct config, confirmed 2026-05-25):
      P(pass) ≈ 53.7%, P(bust) ≈ 46.2% (N=20k, seed=42, max_eval_days=180).
      Old figure (66%/27%) used BASELINE_CONFIG (eval_DD=$1,500) — see test file.
    """
    # Scale NQ → n_mnq MNQ
    NQ_COST, NQ_PV = 19.0, 20.0
    MNQ_PV, MNQ_COST = 2.0, 2.15

    def _scale(nq_pnl: float) -> float:
        return (nq_pnl + NQ_COST) / NQ_PV * MNQ_PV * n_mnq - MNQ_COST * n_mnq

    avg_winner = _scale(1_571.60)   # $470.73 for 3 MNQ
    avg_loser = _scale(-421.45)     # -$127.19 for 3 MNQ
    winner_std = abs(avg_winner) * 0.30

    trade_prob = 0.458
    win_prob_cond = 0.2775  # P(win | trade day)

    rng = np.random.default_rng(seed)

    def generate() -> NDArray[np.float64]:
        trade = rng.random(n_days) < trade_prob
        win = trade & (rng.random(n_days) < win_prob_cond)
        lose = trade & ~win

        pnl = np.zeros(n_days)
        n_wins = int(win.sum())
        if n_wins > 0:
            raw_winners = rng.normal(avg_winner, winner_std, size=n_wins)
            pnl[win] = np.clip(raw_winners, avg_loser, None)
        pnl[lose] = avg_loser  # hard SL cap: losses are approximately fixed
        return pnl

    return generate
