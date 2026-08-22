# PRE-REGISTRATION (FROZEN before results) — FTMO-compatible strategy profile
**Study:** characterise, quantitatively, the strategy profile compatible with BOTH FTMO stages.
**Date frozen:** 2026-06-20 · **Author:** research session · **Auditor:** separate (to verify post-hoc).
**Nature:** characterisation over SYNTHETIC strategy profiles. No strategy is built; no data is fitted; live book read-only; no deployment.

> This file is frozen prior to running any simulation. Design, axes, grids, metrics, thresholds and directional hypotheses below are fixed. Results live in separate files.

## 1. Account model (encoded exactly from the canonical spec)
Account = **$10,000**. Three distinct barriers (per the locked lessons):
- **Daily barrier (the binding one):** fixed **$500** (5% of initial); the daily floor is recomputed each midnight as `balance_at_midnight − 500`. Breach = intraday equity drops below that level on any day. (`funded-daily-loss-binds-not-the-static-floor`).
- **Max-loss floor:** **static $9,000** (−10% from initial). Breach = equity below $9,000. (Static, not trailing; trailing is a 1-step-challenge thing only.)
- **Challenge target:** **+10% = $11,000**; must be reached before the **91-calendar-day wall** (≈ **63 trading days**), with **≥ 4 trading days** traded.
Funded stage: no target; horizon **252 trading days (1 year)**; barriers = daily $500-mobile + static $9,000.

Rules cross-checked against `Portfolio/risk/propfirm_canonical.py` (FTMO 5% / 10% / 10% target / 4 min days).

## 2. Synthetic strategy-profile parameterisation
A candidate is fully described by these axes (the things we want to filter on):
- **Speed / edge** — annualised Sharpe `SR` of the sleeve, and annualised return `μ_ann` (we vary SR and σ; μ follows).
- **Vol** — annualised vol `σ_ann` (daily `σ_d = σ_ann/√252`). This is the leverage/aggression knob.
- **Presence-in-position `p`** — fraction of trading days the sleeve holds a position (intermittency). On inactive days return = 0 and NO intraday risk. Active-day vol scaled so the sleeve hits `σ_ann`.
- **Daily tail** — Student-t degrees of freedom `ν` on the daily innovation (lower = fatter worst-day tail) and an **intraday adverse-excursion multiplier `m`**: the within-day worst drawdown vs midnight = `max(−r_d, σ_active·m·|z|)`. The daily barrier is checked against this intraday low (NOT the close), because the daily limit is an intraday constraint.
- **Tail-co-occurrence with the book `ρ_tail`** — probability that the candidate's worst days land on the book's worst days (Q2 only).

Daily return generator (per active day): `r_d = μ_active + σ_active · t_ν / sd(t_ν)`; inactive day `r_d = 0`. Cumulative drawdown, realised SR and presence are MEASURED from the simulated series (not assumed).

## 3. Book proxy (for Q2c only)
The existing live book is modelled as a sleeve calibrated to its stated funded behaviour: **rases the floor (min-balance median ≈ $9,058 over a funded window), always-on, full-vol.** We calibrate (μ_book, σ_book, p_book≈1) to reproduce min-balance median ≈ $9,050–9,100, then ADD the candidate and measure joint survival as a function of `ρ_tail`. (Assumption stated; the book's exact OR-trend series is in a parallel session and not imported.)

## 4. Metrics
- **Challenge:** `p_pass` = P(reach +10% before any bust, within 63 trading days, ≥4 days).
- **Funded:** `p_survive` = P(no bust over 252 days); `E[extracted]` = expected total profit extracted (extract all balance above $10,000 each EOD — `extraire-bat-thésauriser`); realised **cumulative drawdown** and **presence** reported.
- **Joint (Q3):** a profile is **FTMO-compatible** iff `p_pass ≥ 0.50` AND `p_survive ≥ 0.80` (1-yr) AND `E[extracted] > 0` materially.

## 5. Sensitivity grids
- **Q1 (challenge):** `σ_ann ∈ {3,5,8,12,18,25}%` × `SR ∈ {0,0.5,1.0,1.5,2.0}` (→ μ); plus tail sweep `ν ∈ {3,6,∞}`, `m ∈ {1.0,2.0}`; presence `p ∈ {0.3,0.6,1.0}`.
- **Q2 (funded):** same `σ_ann × SR` grid → `p_survive`, `E[extracted]`, cum-DD. Presence sweep `p ∈ {0.2,0.4,0.6,0.8,1.0}` at fixed (SR,σ). Tail-co-occurrence `ρ_tail ∈ {0,0.3,0.6,0.9}` for (book+candidate).
- **Q3:** overlay the Q1 and Q2 pass-regions in (SR, σ, p) space → the intersection.

## 6. MC settings
N = 20,000 paths per cell; fixed seed (per cell, derived from a master seed = 20260620); challenge 63 trading days; funded 252; vectorised across paths.

## 7. Pre-registered directional hypotheses (from the locked lessons)
- **H-A:** `p_pass` increases with σ up to a point then falls (too much vol → daily/floor bust). There is an OPTIMAL vol band for the challenge. (`two-FTMO-stages-reward-opposite-axes`.)
- **H-B:** `p_survive` DECREASES with σ monotonically and is governed by cumulative DD, not SR. (`funded-survival-is-drawdown-governed-not-Sharpe`.)
- **H-C:** at fixed (SR, σ), LOWER presence `p` raises `p_survive` (intermittency beats Sharpe for a floor-constrained book). (`container-intermittency-beats-standalone-Sharpe`.)
- **H-D:** the daily barrier (not the static floor) is the dominant bust cause in funded; fatter daily tail (low ν, high m) cuts `p_survive` sharply even at modest σ. (`funded-daily-loss-binds-not-the-static-floor`.)
- **H-E:** the challenge-optimal vol band lies ABOVE the funded-optimal vol band → the intersection is narrow; an FTMO-compatible profile must be **fast-but-low-cumulative-DD**, which requires **high per-active-day edge + low presence** (bursty), not high always-on vol.
- **H-F:** tail-co-occurrence `ρ_tail` with the book sharply reduces joint survival; tail-decorrelation is a hard requirement, distinct from average-correlation.

## 8. What the deliverable must state
The quantified compatible profile `[speed X, vol Y, presence Z, cum-DD W, tail-decorrelation V]` and the family ranking by fit. If the intersection is empty/narrow, say so explicitly (a valid outcome that redirects the search to multi-account architecture).
