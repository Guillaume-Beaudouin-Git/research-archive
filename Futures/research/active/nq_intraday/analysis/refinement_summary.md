## Strategy C Refinement — iter_10 Summary

*Generated: 2026-05-21  |  n_tests: 141 → 142*


### 1. Methodology

Starting point: **iter_05_A400+B012** — VWAP + A$400 dollar stop + B1.2% gap filter
Baseline Sharpe: 1.2132  |  MaxDD: -25.1%  |  N trades: 567

**Part A** — Descriptive analytics: 567 trades enriched with 13 contextual variables.
Key findings: Q3 range (38-63pts) avg +$184/trade, Q1 (≤20pts) avg -$15/trade. Strong range-P&L relationship.

**Part B** — 6 pre-specified hypotheses, Bonferroni p*=0.0083:
- H1 DOW effect: p=0.143 FAIL
- H2 VIX level: p=0.020 FAIL
- H3 Opening range: p≈0.000 **PASS** (Kruskal-Wallis 4-group)
- H4 Trend alignment: p=0.172 FAIL
- H5 Long/Short: p=0.481 FAIL
- H6 30-min ORB: p=0.920 FAIL

**Part C** — M1 range filter tested at rng_min ∈ {20..50pts}:
- rng_min=30pt adopted: ΔSharpe=+0.31, retention=61%, WF%=78% (all 3 rules passed)

**Part D** — iter_10 = baseline + M1(rng_min=30pt)


### 2. iter_10 Performance

| Metric | iter_10 | Baseline | Delta |
|--------|---------|----------|-------|
| N trades | 346 | 567 | -221 |
| Win rate | 27.8% | 26.1% | |
| Sharpe HAC | 1.5212 | 1.2132 | +0.3080 |
| MaxDD | -13.4% | -25.1% | +11.6pp |
| Profit Factor | 1.4319 | 1.2798 | +0.1521 |
| Total P&L | $45,510 | $37,897 | |
| P(EV≤0) | 0.0048 | 0.0188 | |
| WF% (12M/6M) | 100% | 100% | |

**Verdict: RESEARCH_PASS**


### 3. Extended Walk-Forward (6M/3M)

- Windows: 9  |  Positive: 78%
- Median OOS Sharpe: 1.720
- Total OOS P&L: $41,961


### 4. FTMO Trailing-DD Analysis (Monte Carlo)

Parameters: $100K initial  |  +10% target ($10K)  |  10% trailing DD  |  30 days  |  10,000 paths

| Outcome | Probability |
|---------|------------|
| Hit +$10K target | 2.5% |
| Trailing DD breach | 0.0% |
| Neither (still running) | 97.5% |

E[final P&L]: $1,758  [5th pct: $-3,481  |  95th pct: $8,033]

**FTMO verdict: FTMO_RISKY** ← driven by low P(target=2.5%), NOT by DD risk.
P(trailing DD breach) = 0.0% — the strategy does not blow up FTMO accounts.
Root cause: at 1 contract, daily mean=$59, std=$652 → reaching $10K in 30 days
requires ~$333/day average (5.6× mean). Needs 4–5 contracts OR longer window.
Risk classification: capital-safe but challenge-pass probability low at 1 contract.


### 5. Decision

iter_10 = **iter_05_A400+B012 + rng_min=30pt** is adopted as the refined Strategy C.

Gate matrix: See Part D1 output.
Next step: Paper trade at 1 contract, log to paper_trade_log.csv.


### 6. n_tests counter

- Start: 141
- End:   142 (+1 iter_10 full run)
- Total from beginning of Strategy C refinement: 134 → 142
