## Result Summary: multi_asset_tsmom — Walk-Forward + DSR + Vol Target

### 1. Headline verdict
**FAIL** — binding failures: dsr_full, vt_max_dd

### 2. Walk-forward OOS stats (16 windows, 2010-2025)
| Metric                  | Value     | Gate          | Pass |
|-------------------------|-----------|---------------|------|
| Median OOS Sharpe       | 0.78      | > 0.30        | ✓    |
| % windows Sharpe > 0    | 68.8%       | > 60%         | ✓    |
| % windows alpha > 0     | 81.2%       | > 60%         | ✓    |
| Worst OOS year          | 2016 (Sharpe=-1.64, MaxDD=-5.4%) | - | - |
| Best OOS year           | 2017 (Sharpe=5.04)            | - | - |

### 3. Full-sample stats (raw vs vol-targeted)
| Metric             | Raw       | Vol-targeted | Notes |
|--------------------|-----------|--------------|-------|
| Sharpe             | 0.43      | 0.52         | -     |
| Ann return         | 2.9%      | 5.1%         | -     |
| Ann vol            | 6.8%      | ~10%         | target |
| MaxDD              | -23.1%     | -18.7%        | propfirm: > -10% |
| Alpha (ann)        | 3.6%      | 5.9%         | vs SPY+AGG |
| Beta SPY           | -0.06      | -0.03         | -     |
| Beta AGG           | -0.04      | -0.19         | -     |
| Residual Sharpe    | 0.54      | 0.61         | true edge |

### 4. Crash period stress test (vol-targeted)
| Period       | Window           | Sharpe  | MaxDD   | Cum ret |
|--------------|------------------|---------|---------|---------|
| GFC          | 2008-07 → 2009-06 | 0.52    | -10.7%   | 6.8%    |
| EuroCrisis   | 2011-04 → 2012-01 | -1.18    | -16.0%   | -13.0%    |
| COVID        | 2020-02 → 2020-05 | -1.18    | -0.8%   | -4.4%    |
| Inflation    | 2022-01 → 2022-12 | 0.10    | -7.5%   | 0.6%    |

### 5. Deflated Sharpe Ratio (n_tests = 58)
- Full-sample DSR p-value: 0.631 [pass: < 0.05] ✗
- Median OOS-window DSR p-value: 0.955
- Full-sample SR=0.43, skew=-0.52, kurt=5.58, n=255
- Reference: SR_expected_max uses n_tests=58, Euler–Mascheroni correction (Bailey & López de Prado 2014)

### 6. Gate decision matrix
| Gate                              | Threshold | Value  | Pass |
|-----------------------------------|-----------|--------|------|
| Walk-forward median Sharpe        | > 0.30    | 0.78   | ✓    |
| Walk-forward % positive windows   | > 60%     | 68.8%   | ✓    |
| DSR p-value (full-sample)         | < 0.05    | 0.631   | ✗    |
| Vol-targeted MaxDD                | > -10%    | -18.7%   | ✗    |
| Vol-targeted COVID MaxDD          | > -5%     | -0.8%   | ✓    |
| Residual Sharpe (vol-targeted)    | > 0.40    | 0.61   | ✓    |

### 7. Recommendation
Strategy fails critical validation gates. Do not deploy. Root cause: binding failures: dsr_full, vt_max_dd. Consider alternative sizing, universe expansion, or archive.

### 8. Files written
- walkforward.py (this script)
- walkforward_results.json (machine-readable)
- walkforward_summary.md (this summary)