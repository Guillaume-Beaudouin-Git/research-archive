"""
MC stress test — Strategy C (Tradeify $25K, 2 MNQ).

4 scenarios with Common Random Numbers (seed=42):
  A — Baseline        : slippage_mult=1.0, vol_mult=1.0
  B — Slippage 1.5×   : slippage_mult=1.5, vol_mult=1.0
  C — Vol 1.2×        : slippage_mult=1.0, vol_mult=1.2
  D — Combined        : slippage_mult=1.5, vol_mult=1.2

Wraps Portfolio/risk/trailing_dd_simulator — does NOT modify it.
Debug logs written to /tmp/mc_stress_test_<scenario>.log.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Callable

import numpy as np
from numpy.typing import NDArray

REPO = Path(__file__).resolve().parents[5]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from Portfolio.risk.trailing_dd_simulator import PropfirmConfig, simulate_n_runs

# ── Run parameters ────────────────────────────────────────────────────────────

N_RUNS = 20_000
SEED = 42
N_DAYS = 400  # max_eval_days(180) + funded_days(180) + buffer
N_MNQ = 2

# iter_10 NQ constants (from trailing_dd_simulator.py)
NQ_COST = 19.0
NQ_PV = 20.0
MNQ_PV = 2.0
MNQ_COST = 2.15

# iter_10 trade distribution (from results.json iter_10, N=346 trades)
AVG_WINNER_NQ = 1_571.60
AVG_LOSER_NQ = -421.45
TRADE_PROB = 0.458
WIN_PROB_COND = 0.2775
WINNER_STD_MULT = 0.30

CONFIG = PropfirmConfig()  # Tradeify Select Flex 25K: DD_eval/funded=$1,000, lock=$26,100

# ── Stress generator ─────────────────────────────────────────────────────────


def _scale(nq_pnl: float, effective_nq_cost: float, n_mnq: int) -> float:
    """Convert NQ net P&L to MNQ net P&L (same formula as trailing_dd_simulator.py)."""
    return (nq_pnl + effective_nq_cost) / NQ_PV * MNQ_PV * n_mnq - MNQ_COST * n_mnq


def make_stress_generator(
    n_days: int,
    n_mnq: int,
    slippage_mult: float = 1.0,
    vol_mult: float = 1.0,
    seed: int | None = None,
) -> Callable[[], NDArray[np.float64]]:
    """
    Stress-parameterised iter_10 generator.

    slippage_mult: subtracts extra NQ cost from per-trade nq_pnl before _scale().
      - 1.5× → extra_slip_nq = (1.5-1.0) × $19 = $9.50 subtracted from each nq_pnl.
      - Effect: both winner and loser worsen by $1.90 in MNQ terms (for 2 MNQ).
    vol_mult: scales final MNQ avg_winner, avg_loser, and winner_std uniformly.
      - Represents wider intraday swings (higher realised volatility scenario).

    CRN: all scenarios use seed=42, so trade/win binary draws are identical across
    scenarios — only payoff magnitudes differ.
    """
    extra_slip_nq = (slippage_mult - 1.0) * NQ_COST  # extra NQ cost per trade

    avg_winner = _scale(AVG_WINNER_NQ - extra_slip_nq, NQ_COST, n_mnq) * vol_mult
    avg_loser = _scale(AVG_LOSER_NQ - extra_slip_nq, NQ_COST, n_mnq) * vol_mult
    winner_std = abs(avg_winner) * WINNER_STD_MULT

    rng = np.random.default_rng(seed)

    def generate() -> NDArray[np.float64]:
        trade = rng.random(n_days) < TRADE_PROB
        win = trade & (rng.random(n_days) < WIN_PROB_COND)
        lose = trade & ~win

        pnl = np.zeros(n_days)
        n_wins = int(win.sum())
        if n_wins > 0:
            raw_winners = rng.normal(avg_winner, winner_std, size=n_wins)
            pnl[win] = np.clip(raw_winners, avg_loser, None)
        pnl[lose] = avg_loser
        return pnl

    return generate


# ── Scenarios ────────────────────────────────────────────────────────────────

SCENARIOS: list[tuple[str, float, float]] = [
    ("A — Baseline",       1.0, 1.0),
    ("B — Slippage 1.5×",  1.5, 1.0),
    ("C — Vol 1.2×",       1.0, 1.2),
    ("D — Combined",       1.5, 1.2),
]


def run_all(n_runs: int) -> list[dict]:
    results: list[dict] = []
    for label, slip, vol in SCENARIOS:
        gen = make_stress_generator(N_DAYS, N_MNQ, slippage_mult=slip, vol_mult=vol, seed=SEED)

        # Base MNQ stats for debug log
        extra = (slip - 1.0) * NQ_COST
        aw = _scale(AVG_WINNER_NQ - extra, NQ_COST, N_MNQ) * vol
        al = _scale(AVG_LOSER_NQ - extra, NQ_COST, N_MNQ) * vol
        ws = abs(aw) * WINNER_STD_MULT

        log_path = Path(f"/tmp/mc_stress_test_{label[:1].lower()}.log")
        log_path.write_text(
            f"scenario={label}\n"
            f"seed={SEED}\n"
            f"n_runs={n_runs}\n"
            f"slippage_mult={slip}\n"
            f"vol_mult={vol}\n"
            f"avg_winner_mnq={aw:.2f}\n"
            f"avg_loser_mnq={al:.2f}\n"
            f"winner_std={ws:.2f}\n"
            f"consistency_cap={CONFIG.consistency_cap_pct * CONFIG.profit_target:.0f}\n",
            encoding="utf-8",
        )

        res = simulate_n_runs(n_runs, gen, config=CONFIG)
        results.append({
            "label": label,
            "p_pass": res.p_eval_pass,
            "p_bust": res.p_bust,
            "p_timeout": res.p_timeout,
            "e_days": res.e_days_to_target,
        })
    return results


# ── Report ───────────────────────────────────────────────────────────────────

_HEADER = (
    "| Scenario              |  P(pass) |  P(bust) | P(timeout) | E[days] |\n"
    "|-----------------------|----------|----------|------------|---------|\n"
)


def _row(r: dict) -> str:
    return (
        f"| {r['label']:<21} "
        f"| {r['p_pass'] * 100:>7.1f}% "
        f"| {r['p_bust'] * 100:>7.1f}% "
        f"| {r['p_timeout'] * 100:>9.1f}% "
        f"| {r['e_days']:>7.1f} |"
    )


def write_report(results: list[dict], n_runs: int, path: Path, elapsed: float) -> None:
    note = f"N={n_runs:,}" if n_runs == N_RUNS else f"N={n_runs:,} (**reduced from {N_RUNS:,} — runtime >{elapsed:.0f}s**)"
    lines = [
        f"# MC Stress Test — Strategy C (Tradeify $25K, {N_MNQ} MNQ)",
        "",
        f"{note} | seed={SEED} | CRN | config: DD_eval=$1,000 DD_funded=$1,000 lock=$26,100",
        "",
        _HEADER.rstrip() + "\n" + "\n".join(_row(r) for r in results),
        "",
        f"_Runtime: {elapsed:.1f}s_",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\nMC stress test — Strategy C, {N_MNQ} MNQ, N={N_RUNS:,}, seed={SEED}")
    print(f"Config: DD_eval=${CONFIG.trailing_dd_eval:.0f} DD_funded=${CONFIG.trailing_dd_funded:.0f} "
          f"lock=${CONFIG.capital + CONFIG.trailing_dd_funded + CONFIG.lock_trigger_excess:.0f}\n")

    for label, slip, vol in SCENARIOS:
        extra = (slip - 1.0) * NQ_COST
        aw = _scale(AVG_WINNER_NQ - extra, NQ_COST, N_MNQ) * vol
        al = _scale(AVG_LOSER_NQ - extra, NQ_COST, N_MNQ) * vol
        print(f"  {label:<21}  avg_winner=${aw:>7.2f}  avg_loser=${al:>7.2f}")
    print()

    t0 = time.perf_counter()
    results = run_all(N_RUNS)
    elapsed = time.perf_counter() - t0

    print(f"  Completed in {elapsed:.1f}s\n")
    print(f"  {'Scenario':<21}  {'P(pass)':>7}  {'P(bust)':>7}  {'P(timeout)':>10}  {'E[days]':>7}")
    print(f"  {'-' * 70}")
    for r in results:
        print(f"  {r['label']:<21}  {r['p_pass']*100:>6.1f}%  {r['p_bust']*100:>6.1f}%  "
              f"{r['p_timeout']*100:>9.1f}%  {r['e_days']:>7.1f}")

    out = Path(__file__).parent / "mc_stress_test_2026-05-25.md"
    write_report(results, N_RUNS, out, elapsed)
    print(f"\n  Report → {out}")
    print(f"  Debug logs → /tmp/mc_stress_test_[a-d].log")
