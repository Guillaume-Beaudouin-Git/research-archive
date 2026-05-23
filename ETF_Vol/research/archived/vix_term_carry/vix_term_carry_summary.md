## Result Summary: VIX Term Structure Carry -- Feasibility

### 1. Headline verdict
> **Best variant (Vol-Targeted)**: MARGINAL -- borderline positive; needs more OOS data

### 2. Data status
- VIXY history: 2011-01-04 -> 2026-05-19
- ^VIX history:  2011-01-04 -> 2026-05-19
- ^VIX3M history: 2011-01-04 -> 2026-05-19
- Trading days (aligned): 3866
- Regime distribution: 92.2% contango, 7.7% backwardation, 63.3% deep contango (>10%)

### 3. Performance comparison: 3 variants

| Metric              | Variant A (raw) | Variant B (VT) | Variant C (VT+stop) |
|---------------------|-----------------|----------------|---------------------|
| Net P&L (% capital) | +1688.3         | +113.9         | +104.2              |
| Annual return       | +20.64          | +5.07          | +4.75               |
| Annual vol          | 34.61           | 7.52           | 7.48                |
| Sharpe (HAC)        | +0.674          | +0.498         | +0.460              |
| MaxDD               | -54.2           | -15.9          | -17.1               |
| Win rate (daily)    | 57.3            | 57.3           | 56.7                |
| Profit factor       | 1.149           | 1.144          | 1.137               |
| Worst single day    | -17.84          | -5.17          | -5.17               |
| Best single day     | 26.46           | 3.32           | 3.32                |
| Avg turnover/day    | 0.0905          | 0.0234         | 0.0234              |
| Annual cost drag    | 0.4561          | 0.118          | 0.1179              |

### 4. Alpha decomposition (best variant = Vol-Targeted)

| Benchmark           | Alpha (ann%) | t_HAC | Beta  | R2    |
|---------------------|--------------|-------|-------|-------|
| SPY B&H             | +1.53        | +0.767 | 0.1514 | 11.8  |
| Short-VIXY naive    | +1.29        | +0.711 | 0.0585 | 29.5  |
| VIX spot            | +6.21        | +3.920 | -0.0305 | 28.8  |

Residual Sharpe vs short-VIXY naive (timing value): +0.711 t-stat

### 5. Crash period stress test (Vol-Targeted variant)

| Period           | Cum return | MaxDD  | Sharpe | Notes |
|------------------|------------|--------|--------|-------|
| Feb 2018 XIV     | +0.8% | -1.3% | +1.039 | XIV inverse ETN collapsed 90% same day |
| COVID Mar 2020   | +7.6% | -1.5% | +4.650 | VIX spiked to 85 (all-time high) |
| 2022 inflation   | +5.9% | -5.3% | +0.828 | rising rates, vol regime shift |
| 2023 banking     | +1.4% | -2.5% | +1.020 | SVB collapse; VIX brief spike to 26 |

### 6. Walk-forward (Vol-Targeted variant, expanding IS window)

| OOS year | N days | Sharpe | MaxDD%  | PF    | Ann ret% |
|----------|--------|--------|---------|-------|----------|
| 2019     | 252    | +0.386 | -6.1    | 1.128 | +4.5     |
| 2020     | 253    | +1.312 | -4.1    | 1.294 | +10.3    |
| 2021     | 252    | -0.172 | -5.5    | 0.968 | -1.5     |
| 2022     | 251    | +0.552 | -5.3    | 1.168 | +6.0     |
| 2023     | 250    | +0.877 | -4.3    | 1.309 | +11.3    |
| 2024     | 252    | -1.925 | -13.3   | 0.760 | -9.9     |
| 2025     | 250    | +0.061 | -5.3    | 1.135 | +4.2     |
| **% positive** | -- | 71% | -- | -- | -- |

### 7. Regime decomposition (Vol-Targeted variant)

| Regime              | % days | Avg daily ret | Hit rate |
|---------------------|--------|---------------|----------|
| Deep backwardation (<-5%) | 2.7%   | +0.165%        | 62.3%      |
| Mild backwardation (0 to -5%) | 5.0%   | -0.225%        | 26.7%      |
| Mild contango (0-10%) | 28.9%   | -0.133%        | 45.3%      |
| Deep contango (>10%) | 63.3%   | +0.104%        | 65.0%      |

### 8. Propfirm gate decision (best variant = Vol-Targeted)

| Gate                       | Threshold | Value      | Pass |
|----------------------------|-----------|------------|------|
| Sharpe HAC (VT)            | > 1.0     | +0.498     | FAIL |
| MaxDD (% of capital)       | > -10%    | -15.9%         | FAIL |
| Worst single day           | > -5%     | -5.17%        | FAIL |
| Walk-forward % positive    | > 60%     | 71%          | PASS |
| Alpha t_HAC vs short-VIXY  | > 1.5     | +0.711     | FAIL |
| AMTP p-value (n=71)      | < 0.10    | 0.6741     | FAIL |

### 9. Correlation to existing live book

| Asset / Strategy            | Correlation |
|-----------------------------|-------------|
| BTC-USD (daily ret)         | +0.084      |
| ETH-USD (daily ret)         | +0.169      |
| BTC TSMOM proxy (sign(BTC ret)) | -0.036      |
| SPY (daily ret)             | +0.344      |

> Portfolio diversification: MODERATE (corr < 0.3 to all assets: False)

### 10. Recommendation

> FAIL. Archive VIX term structure carry. Try next candidate:
> - Sector momentum (SPY sector ETFs)
> - Commodity TSMOM (DJP, GLD, USO)
> - Pairs trading (SPY/QQQ, GLD/SLV)

### 11. Bootstrap EV (Vol-Targeted variant)

- EV/day (%): 0.0208%  [95% CI 0.0058%, 0.0357%]
- P(EV <= 0): 0.0034

### 12. n_tests counter

- Start: 68
- Variant A (raw): n_tests = 69
- Variant B (vol-targeted): n_tests = 70
- Variant C (VT+stop): n_tests = 71
- **End: 71**
