# Phase 1 — Baseline Results

**Run date:** 2026-05-28  
**Period:** 2002-01-01 → 2026-05-27  
**T:** 6138 trading days

## Key metrics

| Metric | Value |
|--------|-------|
| Sharpe gross | 2.519 |
| Sharpe net | 2.046 |
| **Sharpe deflated (DSR)** | **2.012** |
| Max drawdown | -13.29% |
| Alpha ann | 0.2523 |
| t_HAC (lag-6) | 10.377 |
| AMTP p-val (6 trials, Bonferroni) | 0.0000 |
| Sharpe bootstrap CI 95% | [1.638, 2.455] |
| WF folds passing | 5/5 |
| WF Sharpe OOS | 2.371 |

## FTMO 2-step simulation

| Metric | Value |
|--------|-------|
| P(pass Phase 1) | 0.073 |
| P(pass Phase 2 \| Phase 1) | 0.705 |
| **P(pass both)** | **0.051** |
| **P(pass both) CI 95%** | **[0.047, 0.056]** |
| Median days to pass | 51 |
| Fail: daily loss | 0.0% |
| Fail: max loss | 0.1% |
| Fail: timeout | 92.6% |

## Walk-forward fold detail

| Fold | Test period | Sharpe OOS | MaxDD | t_HAC | Gate |
|------|-------------|------------|-------|-------|------|
| 5 | 2016-05-26→2018-05-25 | 1.826 | -8.48% | 2.609 | ✅ PASS |
| 4 | 2018-05-29→2020-05-26 | 1.06 | -13.29% | 1.381 | ✅ PASS |
| 3 | 2020-05-26→2022-05-26 | 3.98 | -8.41% | 5.648 | ✅ PASS |
| 2 | 2022-05-26→2024-05-24 | 2.666 | -10.67% | 3.572 | ✅ PASS |
| 1 | 2024-05-28→2026-05-26 | 2.362 | -8.42% | 3.201 | ✅ PASS |

## Constitutional checks

| Check | Status |
|-------|--------|
| L1: signal T-1, trade T open | ✅ engine.run() shift(1) on all signals |
| L2: WF ≥5 folds | ✅ 5 folds |
| L8: excess returns vs DTB3 | ✅ rf subtracted daily |
| L8: HAC NW lag-6 | ✅ t_HAC=10.377 |
| L8: AMTP correction | ✅ 6 combos Bonferroni |
| L8: DSR | ✅ sr_deflated=2.012 |
| L10: ≤3 modifications | ✅ 0 mods (baseline only) |

## Verdict

**ARCHIVE — gates failed**

Gate detail: sharpe_deflated=PASS (2.012 ≥ 0.7)  |  p_pass_ci95[0]=FAIL (0.047 < 0.50)