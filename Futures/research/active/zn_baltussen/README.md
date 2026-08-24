# ZN Baltussen Intraday Momentum

**Status**: FEASIBILITY — branch `feature/zn-baltussen-feasibility`  
**Reference**: Baltussen, Da, Lammers, Martens (2021) *JFE* 142(1), 377-403  
**n_tests at entry**: 322

## Strategy

Last-30-min momentum in ZN (10-Year T-Note futures): the rest-of-day return
(09:30–15:00 ET) predicts the last 30 minutes (15:00–15:30 ET).

Extended hypothesis: effect amplified on macro announcement days (FOMC, CPI, NFP, PCE).

## Files

| File | Purpose |
|------|---------|
| `prespec.md` | Pre-registered hypotheses H1/H2/H3, gates, cost model |
| `data_setup.py` | Data loading (1-min/1h) + macro calendar + STOP-POINT 1 |
| `feasibility.py` | Backtest engine H1/H2/H3 + walk-forward + STOP-POINT 2/3 |
| `analysis/tail_risk_test.py` | Stress tests: repo crisis, dash-for-cash, tariff shock |
| `analysis/results.json` | All results (written by feasibility.py + tail_risk_test.py) |

## Data requirements

| Mode | Source | Coverage | Notes |
|------|--------|----------|-------|
| Canary (1h) | yfinance ZN=F | ~Jun 2024 – present | Approximation, 730-day limit |
| Full backtest | FirstRateData ZN 1-min | 2018–2025 | ~$99 one-time |

To enable full backtest: download ZN 1-min from [firstratedata.com/i/futures](https://firstratedata.com/i/futures), save to `data/raw/ZN_1min.csv`.

## Usage

```bash
# STOP-POINT 1: data diagnostics
python -m Futures.research.active.zn_baltussen.data_setup

# STOP-POINT 2: canary backtest (1h, available data only)
python -m Futures.research.active.zn_baltussen.feasibility --canary

# STOP-POINT 3: full backtest (requires 1-min data)
python -m Futures.research.active.zn_baltussen.feasibility

# Tail-risk stress tests
python -m Futures.research.active.zn_baltussen.analysis.tail_risk_test

# Tests
pytest Futures/research/active/zn_baltussen/tests/ -v
```

## Gates (from prespec.md)

| Gate | Criterion |
|------|-----------|
| H1 PASS | Sharpe ≥ 1.0, win-rate ≥ 53%, N ≥ 1,800 |
| H2 PASS | Sharpe ≥ 1.3, win-rate ≥ 55%, N ≥ 350 |
| H3 PASS | Sharpe decay < 40% (2022-25 vs 2018-21) |
| WF PASS | ≥ 60% positive folds |

All four PASS → tail-risk test → RESEARCH_PASS candidate.

## Modification budget

0 / 3 modifications consumed.
