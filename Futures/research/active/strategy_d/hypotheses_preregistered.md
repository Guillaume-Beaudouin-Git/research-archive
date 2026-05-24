# Strategy D Pre-Registration Document

**Pre-registration date**: 2026-05-24  
**Commit hash at pre-registration**: d33e44b8988039083ae51795cf8ef5c52f05219d  
**Author**: Prodige, M1 IEF Université de Rennes 1  
**Status**: PRE-REGISTERED — NO DATA EXPLORED AFTER THIS COMMIT

---

> This document fixes the hypotheses, signal specifications, entry/exit rules,
> costs, gates, and statistical tests for Strategy D candidates BEFORE any backtest
> is run. Any subsequent modification to specs requires:
> 1. New pre-registration document with new commit hash
> 2. Explicit documentation of why specs were changed
> 3. AMTP correction expanding N by the new variants tested
>
> This is the canonical reference. Backtest results files must reference this commit hash.

---

## Section 1 — Hypothèses retenues post Topic 1 pre-flight

### D3 — CL European-session momentum

**Mechanism (lit-grounded)**:
- Wen, Gong, Ma & Xu (2021, Economic Modelling): first half-hour returns positively
  predict last half-hour returns on crude oil (intraday momentum with commodity futures)
- Baltussen, Da, Lammers & Martens (2021, JFE 142(1):377-403): ROD→LH intraday momentum
  confirmed on commodity futures cross-venue; t-stat = 7.29, R² = 1.1% (economically
  significant given leverage)

**Specification**:

| Parameter | Value |
|-----------|-------|
| Period | 2022-2025 (full in-sample + 5-fold WF) |
| Asset | CL (WTI Crude Oil futures) — micro: MCL for sizing |
| Session window | 03:00–04:30 ET (European open momentum) |
| Signal | z-score of last 1h CL return at 03:00 ET vs σ_20d realized |
| Long threshold | z > +0.8 |
| Short threshold | z < -0.8 |
| Entry | 03:05 ET (next 5-min bar after signal) |
| TP | 1.2R |
| SL | min(0.6R, 1.5 × ATR_5min) |
| Time stop | 08:00 ET |
| Position | 2 MCL contracts |
| RT cost | 2 ticks × 2 legs × $1/tick micro = $4 RT |
| N expected | ~252 weekdays × 30% signal frequency = ~75 trades/year |
| Corr gate | |ρ(D3, iter_10)| < 0.20 full sample required |

**Excluded days**: FOMC announcement days (Federal Reserve calendar).

---

### D5 — ZN US-session mean reversion ex-FOMC ex-NFP

**Mechanism (lit-grounded)**:
- Fleming & Remolona (1999, JF 54(5):1901-1915): Treasury liquidity provision mechanism —
  market makers absorb intraday price impact and revert over RTH session
- Della Corte & Kosowski (multiple papers): overnight–intraday reversal documented in
  fixed income; z-score threshold > 1.5 SDev predicts mean reversion within session
- Hartigan (2026, practitioner): 505 ZB RTH sessions reviewed, 92.5% median regression
  ratio toward session open; actionable with FOMC/NFP exclusion

**Specification**:

| Parameter | Value |
|-----------|-------|
| Period | 2022-2025 (full in-sample + 5-fold WF) |
| Asset | ZN (10-Year T-Note futures) — chosen over ZB for cost gate |
| Signal | z-score of ZN price vs 20-period 5-min EMA at 09:30 ET RTH open |
| Long threshold | z < -1.8 (price oversold vs EMA) |
| Short threshold | z > +1.8 (price overbought vs EMA) |
| Entry | 09:31 ET (next 5-min bar) |
| Exit condition | z returns to 0, OR 14:00 ET time stop, OR SL at z = ±2.5 |
| Position | 1 ZN contract |
| RT cost | 2 ticks × 2 legs × $15.625/tick = $62.50 RT |
| N expected | ~252 days × 86% (post-filter) × 30% signal frequency = ~65 trades/year |
| Corr gate | |ρ(D5, iter_10)| < 0.20 full sample required |

**Excluded days**:
- FOMC ± 1 calendar day (Federal Reserve meeting calendar)
- NFP (Non-Farm Payroll) days — first Friday of each month (BLS release schedule)

---

## Section 2 — Hypothèses archivées avec littérature

### D1 — ES afternoon fade 14:00–15:30 ET — ARCHIVED

**Reason**: signal direction backwards. Baltussen et al. (2021, JFE) t=7.29 confirms
intraday momentum (not mean reversion) in the 14:00–16:00 ET window for equity index
futures. Gao, Han, Li & Zhou (2018, JFE 129(2)):R²=1.1% for ROD→LH momentum structure.
Both papers confirm continuation, not fade.

**Burden of re-proposal**: produce peer-reviewed evidence overturning positive
momentum coefficients in 14:00–15:30 ET window for equity index futures.

### D4 — GC Globex breakout 18:00–02:00 ET — ARCHIVED

**Reason**: no peer-reviewed empirical support. Practitioner consensus = range-bound
Asian session for precious metals. Structurally incompatible with Tradeify 16:59 ET
close rule (gold futures trade 18:00 ET – 17:00 ET next day; a strategy requiring
position at 02:00 ET cannot be cleanly closed at 16:59 ET the same day without
structural session misalignment).

**Burden of re-proposal**: peer-reviewed evidence on GC early-Globex directional
breakout regime with documented holding period compatible with RTH propfirm constraints.

---

## Section 3 — Hypothèse différée

### D2 — NQ overnight gap fade — DEFERRED

**Reason**: unconditional overnight gap fade is -EV (Lou, Polk & Skouras, 2019, NBER
Working Paper). Conditional version (Monday + gap ≥ 1% + day-of-week filter) exceeds
max 3-modification budget per L10 relative to iter_10 base hypothesis. Parked for
future session as iter_X with independent modification count.

---

## Section 4 — Méthodologie de backtest (mandatory, no deviation)

**Data sources**:
- CL / MCL: yfinance `CL=F` 5-min (730-day limit for calibration), Databento for full
  2022-2025 sample
- ZN: yfinance `ZN=F` 5-min + daily; Databento fallback for full sample
- RF: FRED DTB3 daily

**Cost application**: as specified in Section 1 per instrument (D3: $4 RT, D5: $62.50 RT)

**Statistical methodology**:
- Excess returns: subtract FRED DTB3 daily from all strategy returns
- HAC SE: Newey-West lag-6; extend to lag-12 if ρ_1 > 0.30
- Daily vol targeting: 63d rolling σ × √252 (sampled daily)
- Walk-forward: 5 anchored expanding folds (end dates: 2022-12-31, 2023-12-31,
  2024-06-30, 2024-12-31, 2025-12-31)
- AMTP correction: Benjamini-Hochberg at α = 0.10 with N = 5 candidates
  (D1, D2, D3, D4, D5 — archived/deferred counted for honest N)

**Prohibited post-hoc changes** (requires new pre-registration):
- Signal threshold adjustment (±0.8 D3, ±1.8 D5)
- Time window adjustment (±30 min entry/exit)
- Adding or removing exclusion days
- Changing instrument from CL → CLQ or ZN → ZF

---

## Section 5 — Gates pass/fail (specified in advance)

All gates must be evaluated before looking at funded simulation.

| Gate | Threshold | Required |
|------|-----------|----------|
| IC HAC t-stat | > 2.5 | Mandatory per hypothesis |
| Sharpe (post-cost, WF) | > 1.0 | PROPFIRM_PASS |
| MaxDD (account-relative) | < -10% | PROPFIRM_PASS |
| WF survival | > 60% of folds positive | PROPFIRM_PASS |
| Alpha t-stat | > 2.0 | PROPFIRM_PASS |
| Worst calendar month | > -5% | PROPFIRM_PASS |
| Correlation vs iter_10 (full sample) | < 0.20 | Mandatory |
| Correlation vs iter_10 (60d rolling median) | < 0.30 | Mandatory |
| AMTP BH-adjusted p | < 0.10 | Mandatory |
| P(eval pass∞, propfirm sim) | > 60% | PROPFIRM_SURVIVAL_PASS (L22) |
| CapViol% (analytical) | < 5% | PROPFIRM_SURVIVAL_PASS |
| P(bust funded 180d) | < 30% | PROPFIRM_SURVIVAL_PASS |

**Propfirm survival simulation**: run trailing_dd_simulator.py with SELECT_FLEX config
(PropFirms/tradeify/rules.md canonical). Must use calibrated trade-based generator
(not Gaussian — see L22).

---

## Section 6 — Deployment decision matrix

| Outcome | Action |
|---------|--------|
| Both D3 and D5 pass all gates | Deploy D5 first (stronger mechanism support); paper D3 in parallel 30 days |
| Only D5 passes all gates | Deploy D5 standalone; archive D3 |
| Only D3 passes all gates | Paper trade D3 60 days before live; no D5 |
| Neither passes all gates | Archive both; document in CLAUDE.md L-series |
| Correlation D3 vs iter_10 > 0.20 | Archive D3 regardless of other metrics |
| Worst calendar month D5 < -5% | Tighten z-threshold from 1.8 → 2.0, re-run (max 1 modification remaining) |
| P(eval pass∞) < 60% after gate | Archive — propfirm structural mismatch |
| CapViol% > 5% and winner-cap not implemented | Archive — consistency rule risk |

---

## Section 7 — Auto-archival triggers

If after backtest any of the following apply, archive immediately (no further iterations):

- AMTP BH-adjusted p > 0.10 → deferred to next research cycle, NOT deployed
- Sharpe < 1.0 → archived with reason
- MaxDD (account) > -10% → archived with reason
- Correlation vs iter_10 > 0.20 → archived (insufficient portfolio diversification)
- P(eval pass∞) < 60% under propfirm sim → archived (structural propfirm mismatch)
- CapViol% > 5% and `strat_c_winner_cap_feature` not implemented → archived

Modification budget: **3 modifications total** per hypothesis (L10). Budget starts fresh
from this pre-registration — prior NQ D-series iterations do NOT count against D3/D5 CL/ZN.

---

## Section 8 — Portfolio context

Target: Strategy D must contribute to portfolio Sharpe improvement threshold.

| Condition | Required |
|-----------|----------|
| Standalone Sharpe (D alone) | > 1.0 (PROPFIRM_PASS minimum) |
| Correlation D vs C (iter_10) | < 0.20 at full sample (portfolio diversification) |

D3+D5 portfolio ERC allocation and combined Sharpe to be computed post-backtest
if both hypotheses pass individually.

---

_Pre-registration created: 2026-05-24 | Commit: d33e44b8988039083ae51795cf8ef5c52f05219d_
_No backtest data was explored before writing this document._
