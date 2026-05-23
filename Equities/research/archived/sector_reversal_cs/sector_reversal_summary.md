# Result Summary: Cross-Sectional Sector Reversal
*Generated: 2026-05-20 16:51*

## 1. Headline verdict
> Two-tier: **RESEARCH_PASS: FAIL** | **PROPFIRM_PASS: FAIL**
> Best variant: **V1**

SRV coeff=0.1580 (t=1.020) — POSITIVE ✓ confirms ST reversal premium captured

## 2. Data
- Period: 2005-01-07 → 2026-05-01
- Sectors used: XLK, XLF, XLE, XLV, XLY, XLP, XLI, XLB, XLU, XLRE, XLC (XLRE from 2015-10, XLC from 2018-06)
- Weekly observations: 1113
- n_tests: 78 → 82

## 3. 4-variant comparison

| Metric | V1 (pure) | V2 (filtered) | V3 (VT) | V4 (filter+VT) |
|--------|-----------|---------------|---------|----------------|
| Sharpe HAC | -0.599 | -0.716 | -0.944 | -0.899 |
| Ann return (%) | -9.66 | -11.21 | -10.88 | -10.46 |
| Ann vol (%) | 18.90 | 17.75 | 13.03 | 12.97 |
| MaxDD (%) | -91.47 | -93.61 | -92.11 | -91.81 |
| Worst week (%) | -15.50 | -15.50 | -6.97 | -6.97 |
| Best week (%) | 18.31 | 15.38 | 7.91 | 14.17 |
| Profit factor | 0.813 | 0.773 | 0.727 | 0.728 |
| Hit rate (%) | 51.5 | 50.9 | 51.5 | 50.9 |
| Ann cost drag (%) | 13.01 | 12.86 | 13.01 | 12.86 |

## 4. 6-factor decomposition — V1

| Factor | Coefficient | t_HAC |
|--------|-------------|-------|
| alpha_m | -0.0086 | -3.537 |
| MKT | 0.1382 | 1.561 |
| SMB | -0.0391 | -0.259 |
| HML | -0.0618 | -0.493 |
| MOM | 0.0589 | 0.732 |
| SRV | 0.1580 | 1.020 |
| LRV | 0.3240 | 2.213 |
R² = 0.060

> **SRV loading**: SRV coeff=0.1580 (t=1.020) — POSITIVE ✓ confirms ST reversal premium captured

## 5. Walk-forward by year — V1

| Year | N weeks | Sharpe | Mean ret/wk | MaxDD |
|------|---------|--------|-------------|-------|
| 2008 | 52 | +0.184 | +0.0968%/wk | -24.8% |
| 2009 | 52 | +0.541 | +0.3117%/wk | -18.4% |
| 2010 | 53 | -0.000 | -0.0001%/wk | -9.7% |
| 2011 | 52 | -1.869 | -0.4030%/wk | -26.1% |
| 2012 | 52 | -1.592 | -0.3212%/wk | -20.1% |
| 2013 | 52 | -1.573 | -0.2665%/wk | -13.8% |
| 2014 | 52 | +1.278 | +0.3793%/wk | -8.3% |
| 2015 | 52 | -1.573 | -0.3648%/wk | -22.5% |
| 2016 | 53 | -2.146 | -0.3975%/wk | -23.0% |
| 2017 | 52 | -2.372 | -0.3965%/wk | -19.6% |
| 2018 | 52 | -0.949 | -0.2384%/wk | -19.3% |
| 2019 | 52 | -0.478 | -0.1281%/wk | -13.7% |
| 2020 | 52 | -0.554 | -0.2272%/wk | -24.3% |
| 2021 | 53 | -1.073 | -0.4470%/wk | -35.8% |
| 2022 | 52 | -0.024 | -0.0086%/wk | -16.4% |
| 2023 | 52 | -0.827 | -0.1872%/wk | -13.5% |
| 2024 | 52 | -0.269 | -0.0742%/wk | -14.0% |
| 2025 | 52 | -0.725 | -0.1991%/wk | -15.7% |
| 2026 | 18 | -0.579 | -0.2250%/wk | -12.1% |
| **% positive** | — | **16%** | — | — |
| **Median Sharpe** | — | **-0.725** | — | — |

## 6. Crash period analysis — V1

| Period | Sharpe | MaxDD | Cum ret | Hit rate |
|--------|--------|-------|---------|----------|
| GFC 2008 | +0.184 | -24.8% | -3.34% | 42.3% |
| EuroCrisis 2011 | -1.869 | -26.1% | -19.83% | 40.4% |
| COVID Mar 2020 | +0.083 | -17.1% | -1.17% | 47.6% |
| 2022 inflation | -0.024 | -16.4% | -3.12% | 46.2% |
| 2023 banking | -0.827 | -13.5% | -10.76% | 46.2% |

## 7. Correlation to existing book

| Asset | Correlation |
|-------|-------------|
| SPY | 0.282 |
| TLT | -0.054 |
| BTC-USD | 0.021 |
| EW_sectors | 0.284 |

## 8. Two-tier gate decision — V1

| Gate | Threshold | Value | RESEARCH | PROPFIRM |
|------|-----------|-------|----------|----------|
| Sharpe HAC > 0.7 | 0.7 | -0.599 | FAIL |  |
| MaxDD > -25% | -25.0 | -91.470 | FAIL |  |
| WF% positive > 50% | 50.0 | 15.789 | FAIL |  |
| Alpha t_HAC vs EW sctrs > 1.5 | 1.5 | -3.702 | FAIL |  |
| AMTP p(n=82) < 0.20 | 0.2 | 1.000 | FAIL |  |
| Corr BTC+SPY < 0.5 | 0.5 | 0.282 | PASS |  |
| Sharpe HAC > 1.0 | 1.0 | -0.599 | — | FAIL |
| MaxDD > -10% | -10.0 | -91.470 | — | FAIL |
| Worst week > -5% | -5.0 | -15.498 | — | FAIL |
| WF% positive > 60% | 60.0 | 15.789 | — | FAIL |
| Alpha t_HAC vs EW sctrs > 2.0 | 2.0 | -3.702 | — | FAIL |
| AMTP p(n=82) < 0.10 | 0.1 | 1.000 | — | FAIL |
| Corr BTC+SPY < 0.3 | 0.3 | 0.282 | — | PASS |

- Research: 1/6 gates passed
- Propfirm: 1/7 gates passed

**RESEARCH_PASS: FAIL  |  PROPFIRM_PASS: FAIL**

## 9. Sector attribution — V1

| Sector | #Long | #Short | Net P&L | WR Long | WR Short |
|--------|-------|--------|---------|---------|----------|
| XLRE | 119 | 115 | +52.264% | 58.8% | 40.9% |
| XLF | 258 | 206 | +45.863% | 53.9% | 47.1% |
| XLU | 287 | 287 | +37.145% | 53.3% | 43.9% |
| XLV | 206 | 209 | +16.715% | 51.9% | 44.0% |
| XLY | 188 | 194 | +9.884% | 56.4% | 45.4% |
| XLP | 223 | 194 | +8.488% | 56.5% | 44.3% |
| XLC | 66 | 72 | +7.760% | 54.5% | 41.7% |
| XLI | 133 | 132 | +4.612% | 57.9% | 44.7% |
| XLK | 179 | 236 | +0.763% | 49.7% | 41.1% |
| XLE | 363 | 357 | -19.535% | 57.9% | 44.5% |
| XLB | 204 | 224 | -23.989% | 57.4% | 42.0% |

## 10. n_tests
- Start: 78
- V1–V4: +4
- **End: 82**
