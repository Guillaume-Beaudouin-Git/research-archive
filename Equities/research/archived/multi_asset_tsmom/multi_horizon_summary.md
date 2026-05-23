## Result Summary: multi_asset_tsmom — Multi-Horizon Signal

### 1. Headline verdict
**PASS_RESEARCH_ONLY — best MaxDD -14.5%, propfirm MaxDD gate (> −10%) still not cleared**

### 2. Comparison vs baseline
| Variant                          | Sharpe | Ann ret | Ann vol | MaxDD  | Alpha | β_SPY | R²  | Resid SR | DSR p | EuroCrisis MaxDD |
|----------------------------------|--------|---------|---------|--------|-------|-------|-----|----------|-------|------------------|
| 12M-only (baseline VT, ref)      | 0.43   | 2.9%    | 6.8%    | -23.1% | 3.6%  | -0.06 | 1.71% | 0.54         | 0.631 | -16.0%             |
| 12M + Overlay B (ref)            | 0.62   | 5.3%    | n/a     | -14.0% | n/a   | n/a   | n/a | 0.52         | n/a   | -12.8%           |
| Multi-horizon (1+3+12M), VT only | 0.33   | 2.9%    | 8.8%    | -17.7% | 3.6%  | -0.01 | 1.1% | 0.42         | 0.792 | -7.4%             |
| Multi-horizon + Overlay B        | 0.48   | 3.6%    | 7.5%    | -14.5% | 4.0%  | -0.04 | 0.5% | 0.53         | 0.569 | -7.1%             |

### 3. Crash period MaxDD per variant
| Period       | 12M+B  | MH+VT  | MH+B   |
|--------------|--------|--------|--------|
| GFC          |    n/a | -11.1% |  -3.8% |
| EuroCrisis   | -12.8% |  -7.4% |  -7.1% |
| COVID        |    n/a |  -6.4% |  -4.9% |
| Inflation    |    n/a |  -9.4% |  -3.6% |

### 4. Propfirm gate decision per variant
| Variant      | MaxDD > -10% | COVID > -5% | Resid SR > 0.40 | DSR < 0.05 (n=64) | Verdict        |
|--------------|--------------|-------------|-----------------|-------------------|----------------|
| MH+VT        | ✗            | ✗           | ✓               | ✗                 | FAIL           |
| MH+B         | ✗            | ✓           | ✓               | ✗                 | FAIL           |

### 5. Did multi-horizon fix EuroCrisis?
- 12M-only EuroCrisis MaxDD: −16.0% (baseline VT) / −12.8% (with Overlay B)
- Multi-horizon VT EuroCrisis MaxDD: -7.4%
- Multi-horizon + Overlay B EuroCrisis MaxDD: -7.1%

Per-asset signal flip dates during EuroCrisis (equity ETFs, Apr 2011 value → first negative month):

| ETF  | 1M apr2011 | 1M flips | 3M apr2011 | 3M flips | 12M apr2011 | 12M flips | Combined flips |
|------|-----------|---------|-----------|---------|------------|----------|----------------|
| SPY  |     0.002 | 2011-06-30 |     0.564 | 2011-08-31 |      0.668 |    never |     2011-08-31 |
| QQQ  |    -0.076 | 2011-04-30 |     0.489 | 2011-07-31 |      0.721 |    never |     2011-09-30 |
| EFA  |    -0.344 | 2011-04-30 |     0.263 | 2011-08-31 |      0.395 | 2011-10-31 |     2011-08-31 |
| EEM  |     0.747 | 2011-02-28 |     0.193 | 2011-07-31 |      0.623 | 2011-10-31 |     2011-08-31 |
| IWM  |     0.366 | 2011-02-28 |     0.584 | 2011-07-31 |      0.769 | 2011-10-31 |     2011-08-31 |

- 1M signal first flipped short on a major equity: **2011-02-28**
- 3M signal first flipped: **2011-07-31**
- Combined signal first flipped: **2011-08-31**
- Did multi-horizon fix EuroCrisis? **Yes**
  Multi-horizon VT: -7.4% vs baseline -16.0% — improvement of 8.6%

### 6. Recommendation
Multi-horizon improves EuroCrisis MaxDD from −16.0% to -7.4% (VT) / -7.1% (B). Full-sample MaxDD -14.5% — still above −10% propfirm gate. The 1M+3M+12M ensemble addresses signal latency but complete propfirm compatibility may require tighter stops (−3% per leg) or a longer OOS sample to accumulate DSR significance.

### 7. n_tests counter end of session: 64
- Entering session: 62
- MH+VT: n_tests = 63
- MH+B: n_tests = 64

### 8. Files written
- multi_horizon.py (this script)
- multi_horizon_results.json (machine-readable)
- multi_horizon_summary.md (this summary)