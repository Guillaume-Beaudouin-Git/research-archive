## Methodology Audit: MH+B — Original vs Corrected (All 5 Fixes)

**Fixes applied simultaneously:**
- Fix 1: Daily vol targeting (63-day daily P&L rolling vol × √252)
- Fix 2: Excess returns over RF (FRED DTB3 3-month T-bill)
- Fix 3: Newey-West HAC SE (statsmodels, maxlags=6)
- Fix 4: TSMOM diagnostics (directional accuracy, quintile, convexity)
- Fix 5: DSR renamed → `approx_multi_test_penalty` (simplified BLP approximation)

### 1. Headline metrics comparison

| Metric            | Original MH+B | Corrected MH+B | Change    |
|-------------------|---------------|----------------|-----------|
| Sharpe            | 0.478         | 0.211          | -0.267    |
| Ann ret           | 4.900%        | 1.930%         | -3.0pp    |
| Ann vol           | 10.200%       | 9.150%         | -1.0pp    |
| MaxDD             | -14.500%      | -20.670%       | -6.2pp    |
| Alpha (ann)       | 4.200%        | 2.740%         | -1.5pp    |
| Alpha t-stat      | 1.470         | 1.310          | -0.160    |
| Resid Sharpe      | 0.516         | 0.303          | -0.213    |
| EuroCrisis MaxDD  | -7.100%       | -7.280%        | -0.2pp    |
| COVID MaxDD       | n/a           | -4.920%        | n/a       |
| AMTP p-value      | 0.790         | 0.925          | +0.135    |

### 2. Fix 4 — TSMOM Diagnostics
- **Directional accuracy**: 52.0%  (gate ≥53%: ✗)

- **Quintile analysis** (Q1=lowest signal → Q5=highest):
  - Q1: +0.537% avg fwd return
  - Q2: +0.259% avg fwd return
  - Q3: +0.525% avg fwd return
  - Q4: +0.568% avg fwd return
  - Q5: +0.372% avg fwd return
  - Monotone adjacent pairs: 2/4 (50%)
  - Q5-Q1 spread: -0.165%

- **Convexity test** (coef on |SPY_ret|): β=0.1273  t(HAC)=0.92  Pass (β>0, t>1.64): ✗

### 3. Fix 5 — approx_multi_test_penalty documentation
- n_tests: 64
- AMTP p-value: 0.9249  (FAIL ≥ 0.05)
- **Limitation**: BLP approximation assumes independent tests and i.i.d. strategy returns. Serial correlation in TSMOM returns and correlation across the 64 tested variants means this p-value understates true significance. Treat as conservative lower bound.

### 4. Crash period breakdown (corrected MH+B)
| Period       | Sharpe | MaxDD  | CumRet |
|--------------|--------|--------|--------|
| GFC_2008     |  +0.80 | -12.3% |  16.2% |
| EuroCrisis   |  +0.04 |  -7.3% |  -0.1% |
| COVID_2020   |  -0.78 |  -4.9% |  -3.2% |
| Inflation22  |  +0.24 |  -6.2% |   2.6% |

### 5. Propfirm gate status (corrected metrics)
- ✗ MaxDD > -10%
- ✓ COVID MaxDD > -5%
- ✗ Resid Sharpe > 0.40
- ✗ Dir accuracy ≥ 53%
- ✗ Convexity β > 0 (t>1.64)
- ✗ AMTP p < 0.05 (n=64)

### 6. Verdict
**FAIL** — corrected metrics degrade below research threshold.
Gates passed: 1/6

### 7. n_tests counter: 64 (no new tests in this audit)
### 8. Files written
- methodology_audit.py (this script)
- methodology_audit_summary.md (this summary)