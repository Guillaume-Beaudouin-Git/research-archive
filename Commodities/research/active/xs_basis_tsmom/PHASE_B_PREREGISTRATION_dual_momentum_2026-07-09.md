# Phase B Pre-Registration — Dual vs Single Momentum (commodity futures)

**Date (pre-registered, before any backtest):** 2026-07-09
**Mission:** `Commodities/research/active/xs_basis_tsmom/`
**Origin:** relevance triage of the 77 purged false-FAIL_A → winner
(`_automation/feasibility/_audit/corpus_77_relevance_triage_2026-07-09.md`).
Source ideas: Quantpedia *"Dual vs Single Momentum in Commodities"* (2026-06-15) +
Quantocracy duplicate (2026-06-17). **This document fixes the spec, grid, and gates
BEFORE seeing any result** — no post-hoc tuning; deviations invalidate the run.

---

## 1. Hypothesis (falsifiable)
On **commodity FUTURES** (24 continuous, NOT ETFs), layering an **absolute time-series
trend filter** on top of a **cross-sectional relative-momentum ranking** ("dual momentum")
yields *more parameter-robust* and *lower-tail-drawdown* risk-adjusted returns than the
cross-sectional ranking alone ("single momentum"). The paper's central, testable claim is
**robustness/DD**, not raw Sharpe.

**Null H0:** dual momentum does NOT improve (a) Sharpe stability across the pre-registered
lookback grid, NOR (b) MaxDD, vs single momentum — after honest futures costs.

## 2. Who is on the other side / mechanism
XS momentum harvests under-reaction / roll-yield persistence in the cross-section of
commodities (Moskowitz-Ooi-Pedersen 2012, Erb-Harvey 2006). The absolute filter removes
the "least-declining in a bear regime" holdings that XS-only is forced to keep — the edge
it *adds* is tail-management, not new directional alpha. Counterparty = producers/hedgers
(convenience-yield term structure) + trend-chasers late in a move.

## 3. Universe & data (Phase A already validated)
- 24 continuous futures, 2005-01 → 2026-05 (BZ from 2007). Source: yfinance =F continuous
  (`data/fetch_continuous.py`), roll-validated (`roll_validation.py`), ADV-filtered
  (rolling 60d ≥ 5000 contracts/day). Phase A report: `results/phase_a_report.txt`.
- **N ≈ 20-24 after ADV filter** → below the N≥30 XS floor (methodology lesson 6). This is
  a KNOWN limitation; treat XS results as **suggestive, not go/no-go**, and lean on the
  two-sided + DSR + OOS gates rather than a single pooled t.
- **Basis leg (S_BASIS) is NOT tested here** — Phase A basis coverage is only 13.4%
  (roll-gap proxy sparse). Dual-momentum needs only PRICE (continuous), so it is testable
  now; S_BASIS waits for `fetch_front_second.py` (separate future step).

## 4. Signals (fixed)
Monthly rebalance, **signal at month-end T-1, execute month-end T** (no look-ahead).
- **S_XS (single):** cross-sectional rank of the L-month total return (skip most-recent
  `s` months). Long the top tercile, short the bottom tercile, **risk-parity within leg**
  (inverse 63d vol), dollar-neutral across legs. Vol-target the book to 10% annual.
- **S_DUAL (dual):** identical XS rank, BUT an asset takes its (long or short) position
  ONLY if it also passes its **own absolute filter**: long allowed only if L-month return
  > 0 (equivalently price > L-month MA); short allowed only if L-month return < 0. Assets
  failing the absolute screen go **flat** (NaN weight, excluded from that month's book).

## 5. Pre-registered parameter grid (FIXED — protects DSR)
- Lookback `L ∈ {3, 6, 9, 12}` months.
- Skip `s ∈ {0, 1}` months.
- Portfolio cut: **tercile only** (top/bottom 1/3). (No quintile sweep — N too small.)
→ **8 (L,s) cells × 2 constructions (XS, DUAL) = 16 configurations.** `n_tests` for this
Phase B = **counted as the DSR trial count 16** (AMTP/DSR applied across all 16). No other
grid will be run; adding cells later = a new pre-registration.

## 6. Costs
- CME Tier-1 futures **0.015% RT** per side of turnover (L11 / CLAUDE.md).
- **Slippage stress:** report base (0.015%) AND a 3× stress (0.045%) — verdict must hold
  at base; note fragility if it flips under stress.
- L11 cost gate is permissive at monthly breadth (~288 bets/yr) — cost is NOT expected to
  be the binding constraint; the **edge** is.

## 7. Decision gates (pre-registered)
Primary (the paper's own claims):
1. **Sharpe-stability:** dispersion (std / range) of net Sharpe across the 8 (L,s) cells is
   **strictly lower** for DUAL than for XS. This is the headline claim.
2. **MaxDD:** DUAL median MaxDD (across cells) is **less negative** than XS.
Supporting (repo methodology — decisive):
3. **Two-sided (L25):** both legs contribute; a DUAL "edge" that is only long-leg = commodity
   beta in disguise → FAIL.
4. **IC / significance:** monthly XS IC, HAC (Newey-West lag 2) t on mean(IC); report t but
   do NOT treat |t|>2.5 as mandatory given N<30 (report honestly).
5. **OOS / regime:** pre-2015 vs post-2015 split (QE→normalization). A DUAL benefit that
   exists ONLY pre-2015 → decayed, FAIL for deployment.
6. **DSR (Bailey-LdP):** deflated Sharpe across the 16 configs; report SR_DSR of the best
   DUAL cell. Below threshold → not deployable.

**Verdict logic:** DEPLOYABLE(personal book) requires 1 AND 2 AND 3 AND 5 AND positive DSR.
Anything less = FALSIFIED-as-sleeve (but the *lesson* — does the TS filter manage tails on
futures? — is logged either way).

## 8. Honest priors (stated before running)
- Commodity XS momentum **decayed post-2015** (README, documented). Base rate of success is
  **low**; I expect a likely FALSIFIED verdict, with the interesting sub-question being
  whether DUAL at least *cuts MaxDD* (tail management) even if it doesn't restore alpha.
- ETF replication is FORBIDDEN here (L5 roll drag; the archived "Commodity TSMOM ETF SR 0.39"
  is that contamination). Futures-continuous only.
- Routing if it survives: **INVEST LONG / personal-book diversifier** (orthogonal to crypto
  A+B). **Not FTMO** (monthly lumpy vs symmetric-barrier, L24).

## 9. Execution plan (next step, not this document)
1. Regenerate the 24 continuous price panel (`fetch_continuous.py`) → cache locally
   (gitignored; do NOT commit the blob).
2. Implement `signals/momentum.py` (S_XS, S_DUAL) + a monthly backtest harness reusing
   `_automation/feasibility/stats/backtest_wf.py` conventions (vol-target, cost, WF).
3. Run the 16 configs, compute gates §7, write `results/PHASE_B_RESULTS_dual_momentum.md`.
4. `n_tests` update proposed (not graved) = +16 DSR trials, per repo convention.

---
*Pre-registered 2026-07-09. Nothing backtested yet; n_tests untouched. Deviations from
§4-§7 after seeing results invalidate the run (data-snooping guard).*
