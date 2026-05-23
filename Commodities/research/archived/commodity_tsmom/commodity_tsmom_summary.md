# Result Summary: Commodity TSMOM (Hurst-Ooi-Pedersen 2017 framework)
*Generated: 2026-05-20 11:50*

## 1. Headline verdict
> Two-tier: **RESEARCH_PASS: FAIL** | **PROPFIRM_PASS: FAIL**
> Best variant: **A1**

## 2. Data status
- Universe attempted: 12 tickers
- Surviving assets (12): GLD, SLV, CPER, PPLT, USO, UNG, BNO, DBA, CORN, WEAT, SOYB, DBB
- Dropped (0): none
- Period: 2010-02-28 → 2026-04-30
- n_tests: 74 → 78

## 3. 4-variant comparison

| Metric | A1 (single, no VT) | A2 (single + VT) | B1 (multi, no VT) | B2 (multi + VT) |
|--------|-------------------|-----------------|------------------|----------------|
| Sharpe HAC | 0.391 | 0.390 | 0.344 | 0.338 |
| Ann return (%) | 1.33 | 2.56 | 0.92 | 1.80 |
| Ann vol (%) | 3.41 | 6.39 | 2.68 | 5.04 |
| MaxDD (%) | -6.49 | -11.95 | -5.84 | -11.42 |
| Worst month (%) | -4.52 | -9.04 | -3.32 | -4.01 |
| Best month (%) | 3.24 | 5.96 | 4.61 | 9.23 |
| Profit factor | 1.392 | 1.400 | 1.344 | 1.351 |

## 4. Alpha decomposition — A1 (best variant)

| Benchmark | Alpha (ann %/yr) | t_HAC | Beta | R² |
|-----------|-----------------|-------|------|----|
| SPY | 0.012%/yr | 1.373 | 0.0098 | 0.002 |
| DBC | 0.013%/yr | 1.592 | 0.0078 | 0.002 |
| TLT | 0.013%/yr | 1.574 | 0.0034 | 0.000 |
| BTC-USD | 0.013%/yr | 1.447 | 0.0014 | 0.001 |

## 5. TSMOM diagnostics — A1

- Aggregate directional accuracy: **51.0%** (gate: >53%)
- Best asset: CORN (56.7%)
- Worst asset: PPLT (40.4%)
- Convexity coefficient (|SPY|): -0.0464  t_HAC=-1.186

### Quintile bucket analysis (signal → forward return)

| Quintile | Mean fwd return |
|----------|----------------|
| Q1 | 0.0484% |
| Q2 | -0.7554% |
| Q3 | -0.3117% |
| Q4 | 0.0953% |
| Q5 | 0.8248% |

## 6. Walk-forward OOS by year — A1

| Year | N months | Sharpe | Monthly ret | MaxDD |
|------|----------|--------|-------------|-------|
| 2010 | 11 | +1.659 | +0.288% | -1.6% |
| 2011 | 12 | +0.029 | +0.016% | -4.5% |
| 2012 | 12 | -0.803 | -0.131% | -3.3% |
| 2013 | 12 | +1.628 | +0.164% | -0.6% |
| 2014 | 12 | +0.614 | +0.146% | -1.7% |
| 2015 | 12 | +1.326 | +0.401% | -1.5% |
| 2016 | 12 | -1.038 | -0.204% | -4.1% |
| 2017 | 12 | -0.066 | -0.008% | -0.8% |
| 2018 | 12 | -0.148 | -0.023% | -1.3% |
| 2019 | 12 | -1.014 | -0.181% | -1.2% |
| 2020 | 12 | +0.551 | +0.216% | -4.5% |
| 2021 | 12 | +1.480 | +0.637% | -1.8% |
| 2022 | 12 | -0.108 | -0.046% | -6.5% |
| 2023 | 12 | +0.143 | +0.021% | -1.5% |
| 2024 | 12 | +0.379 | +0.055% | -0.9% |
| 2025 | 12 | +1.489 | +0.407% | -0.9% |
| **% positive** | — | **62%** | — | — |
| **Median Sharpe** | — | **0.261** | — | — |

## 7. Crash period analysis — A1

| Period | Sharpe | MaxDD | Cum ret |
|--------|--------|-------|---------|
| Commodity bust 2014-16 | +0.458 | -4.1% | +4.06% |
| COVID Mar 2020 |   n/a | -2.5% | +1.58% |
| 2022 inflation surge | -0.108 | -6.5% | -0.67% |
| 2023 banking crisis | +0.143 | -1.5% | +0.24% |

## 8. Correlation to existing book — A1

| Asset | Correlation |
|-------|-------------|
| SPY | 0.038 |
| DBC | 0.037 |
| TLT | 0.010 |
| BTC-USD | 0.025 |

## 9. Bootstrap EV & AMTP

- Monthly EV: **0.1108%**  CI=[-0.0280%, 0.2454%]  P(EV≤0)=0.0588
- AMTP: n=78, p=0.8077  research (<0.20): FAIL  propfirm (<0.10): FAIL

## 10. Two-tier gate decision — A1

| Gate | Threshold | Value | RESEARCH | PROPFIRM |
|------|-----------|-------|----------|----------|
| Sharpe HAC > 0.7 | 0.7 | 0.391 | FAIL |  |
| MaxDD > -25% | -25.0 | -6.486 | PASS |  |
| WF% positive > 50% | 50.0 | 62.500 | PASS |  |
| Alpha t_HAC vs DBC > 1.5 | 1.5 | 1.592 | PASS |  |
| AMTP p(n=78) < 0.20 | 0.2 | 0.808 | FAIL |  |
| Corr BTC+SPY < 0.5 | 0.5 | 0.038 | PASS |  |
| Sharpe HAC > 1.0 | 1.0 | 0.391 | — | FAIL |
| MaxDD > -10% | -10.0 | -6.486 | — | PASS |
| Worst month > -5% | -5.0 | -4.520 | — | PASS |
| WF% positive > 60% | 60.0 | 62.500 | — | PASS |
| Alpha t_HAC vs DBC > 2.0 | 2.0 | 1.592 | — | FAIL |
| AMTP p(n=78) < 0.10 | 0.1 | 0.808 | — | FAIL |
| Corr BTC+SPY < 0.3 | 0.3 | 0.038 | — | PASS |

- Research gates passed: 4/6
- Propfirm gates passed: 4/7

**RESEARCH_PASS: FAIL  |  PROPFIRM_PASS: FAIL**

## 11. Per-asset attribution — A1

| Asset | Trades | Win rate | Avg ret/trade | Total contrib |
|-------|--------|----------|---------------|---------------|
| BNO | 178 | 54.5% | 0.0304% | +5.416% |
| USO | 195 | 48.7% | 0.0209% | +4.084% |
| SLV | 195 | 54.9% | 0.0201% | +3.922% |
| CORN | 178 | 58.4% | 0.0187% | +3.334% |
| GLD | 195 | 53.8% | 0.0090% | +1.761% |
| UNG | 195 | 56.4% | 0.0081% | +1.576% |
| WEAT | 163 | 51.5% | 0.0081% | +1.324% |
| SOYB | 163 | 52.1% | 0.0052% | +0.840% |
| DBB | 195 | 48.2% | 0.0032% | +0.615% |
| DBA | 195 | 54.4% | 0.0022% | +0.434% |
| CPER | 161 | 47.2% | -0.0018% | -0.291% |
| PPLT | 183 | 41.5% | -0.0052% | -0.960% |

## 12. n_tests counter
- Start: 74
- A1 variant: +1
- A2 variant: +1
- B1 variant: +1
- B2 variant: +1
- **End: 78**
