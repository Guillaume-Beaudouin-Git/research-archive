# Portfolio — sizing, risk, and admission

Portfolio-level code: how much capital a strategy gets, whether it should be admitted to the book
at all, and what the propfirm barriers do to the answer. This is research/tooling code, not the
live execution path — the live book's sizing runs inside `ftmo_live/` (see `docs/ARCHITECTURE.md`).

## Contents

| Directory | Purpose |
|---|---|
| `risk/` | `sizing.py` (ERC / inverse-vol weighting), `correlation.py` (pairwise correlation monitoring), `propfirm_canonical.py` (single source of truth for guardrail percentages — FTMO 5%/10% is canonical, see file for why), `trailing_dd_simulator.py` (Monte Carlo survival simulator, `PropfirmConfig` per firm) |
| `admission/` | `marginal.py` — the current sleeve-admission criterion: ΔSR at ERC weight, significant under block bootstrap, not a ratio gate on the whole book (see docstring for the counter-example that killed the old `1.10 × SR_book` rule). `barrier.py` — translates a Sharpe improvement into probability-of-passing-the-challenge and time-to-funded against the actual barriers (daily -5%, static floor -10%), because Sharpe alone hides path dependence |
| `validation/` | CPCV (Combinatorial Purged Cross-Validation) meta-methodology, `multi_test.py` (deflated Sharpe, Harvey-Liu-BHY), `pipeline.py` (HTML report generator). See `validation/README.md` |
| `reporting/` | Tear sheet / HTML report generation (`tearsheet.py`, `metrics.py`, `plots.py`) |
| `state/` | `portfolio_state.py` — the data structure meant to track all strategies' positions and capital allocation. Partially implemented; check the module docstring's TODO list before assuming a method exists |
| `integration/` | One-off analysis scripts used to combine strategy return streams |

## What decides admission

`admission/marginal.py` is the criterion in force: a candidate sleeve is judged on whether it
raises the book's Sharpe at equal-risk-contribution weight, tested against a block bootstrap (never
iid — trade clusters exist), not on whether it individually clears some fixed Sharpe bar. For a
propfirm challenge specifically, `admission/barrier.py` reports Δp(pass) and Δ time-to-funded, not
ΔSharpe — see `docs/RESEARCH_METHOD.md` and `CLAUDE.md` for why ΔSharpe was abandoned as the
decision variable.

## What not to touch casually

`risk/propfirm_canonical.py` is read as the default guardrail by every strategy that does not
define its own firm-specific limits — changing it changes the assumed risk limit project-wide.
`state/portfolio_state.py` is consumed by other modules; treat its public interface as load-bearing
even though the implementation is incomplete.
