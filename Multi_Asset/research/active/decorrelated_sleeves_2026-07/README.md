# Decorrelated-sleeve exploration — stat-arb / range / MR-indices (2026-07-08)

Independent "fresh per brief" feasibility study of three candidate FTMO sleeves. Pre-registration →
net-of-real-cost backtest → two-sided + OOS + deflated-Sharpe → verdict, reconciled with in-repo
precedent only at the end. **Live book untouched; additive folder; no git-HEAD ops; nothing deployed.**

## Verdict: all three FALSIFIED as FTMO sleeves (independently verified). → `synthesis/SYNTHESIS.md`

| piste | verdict | why (one line) | files |
|---|:--:|---|---|
| **A — stat-arb / pairs** | FALSIFIED | 0/12 OOS-cointegrated; ~1.0 Sharpe is 80-day-hold relative drift (beta trap) | `piste_A_statarb/` |
| **B — range trading** | FALSIFIED | detection is look-ahead (causal −0.06 vs oracle +2.66 SR); cost-dead | `piste_B_range/` |
| **C — daily MR on indices** | FALSIFIED | short leg net-negative on all indices = same beta trap as the 15-min version | `piste_C_mr_daily/` |

## Read order
1. `synthesis/SYNTHESIS.md` — bottom line, promise ranking, reconciliation, §4 scorecard, lesson candidate.
2. `synthesis/VERIFICATION.md` — independent recompute (author≠auditor) confirming all three verdicts.
3. `piste_*/PREREGISTRATION.md` — frozen designs (13:52 UTC, before any result).
4. `piste_*/RESULTS.md` — per-piste evidence & mechanism.

## Layout
- `lib/` — shared infra: `ftmo_costs.py` (measured FTMO swap/spread anchors), `data.py` (M1→daily/hourly
  cache), `stats.py` (HAC, DSR, OU half-life, block bootstrap).
- `piste_A_statarb/` — `run_statarb.py`, `autopsy_A.py`, `coint_screen.csv`, `backtest_grid.csv`, `RESULTS.md`.
- `piste_B_range/` — `run_range.py`, `grid_<sym>.csv`, `backtest_grid.csv`, `RESULTS.md`.
- `piste_C_mr_daily/` — `run_mr_daily.py`, `backtest_grid.csv`, `RESULTS.md`.
- `synthesis/` — `SYNTHESIS.md`, `VERIFICATION.md`, `verify.py`.
- `cache/` — resampled daily/hourly pickles (regenerable; gitignore-able).

## Method anchors
Signal at T-1 / trade at T (1-bar delay); two-sided leg split (L25/L27); real FTMO cost = active-fill
spread+slippage+commission + asymmetric measured overnight swap; HAC lag-6; DSR (Bailey-LdP) on the full
trial space; OOS cointegration stability; walk-forward ≥5 folds. Falsification-first: every pre-reg lists
the exact triggers that would kill the hypothesis, declared before results.
