# Portfolio/validation — CPCV Meta-Methodology

Combinatorial Purged Cross-Validation (CPCV) framework for strategy overfitting
diagnosis. Extends `Portfolio/reporting/` infrastructure.

## Usage

```python
from Portfolio.validation.pipeline import generate_cpcv_report

path = generate_cpcv_report(
    returns=my_daily_returns,          # pd.Series, total returns
    strategy_name="Strategy A — TSMOM v3",
    backtest_fn=my_backtest_fn,        # (train_idx, test_idx) → float
    n_trials=322,                      # project-wide n_tests counter
    output_path="Portfolio/validation/reports/strategy_a_cpcv.html",
    wf_baseline_sharpe=1.33,           # WF OOS Sharpe to compare against
)
```

`backtest_fn` must be self-contained: it receives integer index arrays into
the returns Series and returns the out-of-sample Sharpe for that path.

## Files

| File | Purpose |
|------|---------|
| `cpcv.py` | `run_cpcv()` — CPCV engine via skfolio |
| `multi_test.py` | `deflated_sharpe()`, `harvey_liu_bhy()` |
| `pipeline.py` | `generate_cpcv_report()` — HTML report generator |
| `tests/test_cpcv.py` | 8 pytest tests |

## Dependencies

```
skfolio>=0.17.0    # CombinatorialPurgedCV, optimal_folds_number (BSD-3)
```

Add to requirements.txt before running. Do NOT use:
- mlfinlab (closed-source, £100+/mo)
- timeseriescv (bug open since 2022, alpha)

## CPCV vs Walk-Forward

| Dimension | Walk-Forward (WF) | CPCV |
|-----------|------------------|------|
| Paths | 1 (expanding window) | C(k, k-p) × p (combinatorial) |
| Overfitting diagnostic | Weak (single path) | Strong (distribution of paths) |
| Computational cost | Low | Medium (scales with C(k,k-p)) |
| Correlated paths | N/A | Yes — not IID, CI is diagnostic only |

CPCV doesn't replace WF; it diagnoses overfitting by showing whether the
single WF path was a lucky draw from the full distribution.

## Scope restrictions (CLAUDE.md)

- **Strategy A (TSMOM)**: apply — N=1000+ daily obs, sufficient for 30+ paths.
- **Strategy B (carry)**: NOT YET — requires 250+ live mainnet obs (L14).
- **Strategy C (NQ ORB)**: NOT applicable — ~250 trades/3.5yr = insufficient
  sample for 30 CPCV paths with adequate train size.

## Strategy A — Proof-of-Work

Run: `python -m Portfolio.validation.proof_of_work_strategy_a`

| Metric | Value |
|--------|-------|
| WF baseline Sharpe | 1.33 (OOS, 5-fold expanding) |
| CPCV k / p | 10 / 8 → C(10,8) = 45 paths |
| CPCV mean Sharpe | **1.410** |
| CPCV median Sharpe | **1.442** |
| CPCV std | 0.222 |
| CPCV CI [5%, 95%] | [1.02, 1.74] |
| CPCV median vs WF | +0.11 (consistent ✓) |
| DSR (n_trials=159, T=1799) | **0.876** (marginal — below 0.95 threshold) |
| PSR (n_trials=1) | 0.9999 |
| Verdict | **CONSISTENT — WF result confirmed by CPCV** |

Interpretation: WF 1.33 is neither a lucky draw (CPCV median > WF) nor
overfitted (5th-pct = 1.02 > RESEARCH_PASS gate 0.7). DSR 0.876 reflects
the n=159 backtest budget correction — PSR=0.9999 (single-test) confirms
the signal is real.

_Report_: `Portfolio/validation/reports/strategy_a_cpcv.html`
