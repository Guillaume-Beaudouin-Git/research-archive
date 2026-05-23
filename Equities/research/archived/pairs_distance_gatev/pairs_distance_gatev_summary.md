# Result Summary: Pairs Trading Distance Method (Gatev 2006 / Zhu 2024)
*Generated: 2026-05-20 11:34*

## 1. Headline verdict
> Two-tier: **RESEARCH_PASS: NO** | **PROPFIRM_PASS: NO**
> FAIL — does not meet research grade

## 2. Data
- Universe: 96 stocks (SP100 proxy ~2015, survivorship bias present)
- Period: 2011-01-03 → 2026-05-19
- Candidate pairs per formation: ~4,560
- Overlapping strategies: 6 concurrent monthly cohorts

## 3. Performance comparison (3 variants)

| Metric | T20 | T100 | L75 | Zhu 2024 T20 | Zhu 2024 T100 |
|--------|-----|------|-----|--------------|---------------|
| mean_monthly | -0.053 | -0.027 | -0.116 | 0.461 | 0.426 |
| sharpe | -0.529 | -0.441 | -0.503 | 0.814 | 1.177 |
| ann_ret | -2.070 | -1.750 | -2.820 | n/a | n/a |
| maxdd | -12.860 | -10.670 | -29.640 | n/a | n/a |
| worst_month | -1.980 | -2.020 | -4.690 | -6.7 | -3.63 |
| best_month | +3.720 | +3.210 | +5.200 | 24.3 | 7.43 |
| skew | +0.960 | +0.560 | +0.120 | 7.33 | 1.9 |
| time_in_mkt | +100.000 | +100.000 | +100.000 | n/a | n/a |

## 4. Replication match vs Zhu 2024
- T20 monthly ret within ±20%: NO (ours=-0.053% vs Zhu=0.461%)
- T100 monthly ret within ±20%: NO (ours=-0.027% vs Zhu=0.426%)
- Skewness pattern (right-tailed): NO (skew=0.96)

## 5. Factor decomposition (best variant)

| Factor | Coefficient | t_HAC |
|--------|-------------|-------|
| α (alpha, ann %) | -0.02 | -2.235 |
| Mkt-RF | +0.0407 | +3.947 |
| SMB | +0.0157 | +1.142 |
| HML | +0.0662 | +3.166 |
| RMW | +0.0013 | +0.107 |
| CMA | -0.0704 | -2.526 |
| Mom | -0.1024 | -9.843 |

> Critical: negative MOM coefficient would confirm contrarian implementation.
  MOM coeff = -0.10239666975365898 — matches Zhu expectation

## 6. Walk-forward OOS by year (best variant)

| Year | N days | Sharpe | Monthly ret% | MaxDD% |
|------|--------|--------|--------------|--------|
| 2016 | 252 | +0.765 | +0.199% | -2.4% |
| 2017 | 251 | -1.430 | -0.312% | -5.0% |
| 2018 | 251 | -2.087 | -0.606% | -6.9% |
| 2019 | 252 | +0.560 | +0.141% | -3.7% |
| 2020 | 253 | +0.086 | +0.034% | -6.6% |
| 2021 | 252 | -0.800 | -0.179% | -3.9% |
| 2022 | 251 | -0.245 | -0.106% | -4.2% |
| 2023 | 250 | -0.613 | -0.171% | -5.6% |
| 2024 | 252 | -2.756 | -0.684% | -9.0% |
| **% positive** | — | **33%** | — | — |
| **Median Sharpe** | — | **-0.613** | — | — |

## 7. Correlation to live book

| Asset | Correlation |
|-------|-------------|
| BTC-USD | 0.083 |
| ETH-USD | 0.088 |
| SPY | 0.247 |
| TLT | -0.045 |

## 8. Two-tier gate decision

| Gate | Threshold | Value | RESEARCH | PROPFIRM |
|------|-----------|-------|----------|----------|
| Sharpe HAC | R> 0.7 / P> 1.0 | -0.441 | FAIL | FAIL |
| MaxDD | R< -25% / P< -10% | -10.674 | PASS | FAIL |
| Walk-forward % positive | R≥ 50% / P> -5% | +33.333 | FAIL | PASS |
| Alpha t_HAC vs SPY | R> 1.5 / P≥ 60% | -2.505 | FAIL | FAIL |
| AMTP p-value | R< 0.20 / P> 2.0 | +1.000 | FAIL | FAIL |
| Corr to BTC | R< 0.5 / P< 0.10 | +0.083 | PASS | FAIL |

## 9. Bootstrap EV (monthly returns)

- EV/month: -0.1473%  [95% CI -0.2882%, -0.0029%]
- P(EV ≤ 0): 0.9774
- AMTP p=1.0  (research p<0.20: FAIL, propfirm p<0.10: FAIL)

## 10. n_tests counter
- Start: 71
- T20 variant: +1
- T100 variant: +1
- L75 variant: +1
- **End: 74**

## 11. Recommendation
> FAIL — does not meet research grade