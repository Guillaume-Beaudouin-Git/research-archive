# iter_11_fast — Pre-specification (pre-registered 2026-05-26)

## Modifications vs iter_10_refined

| Parameter      | iter_10 (canonical)         | iter_11_fast (pivot)         |
|----------------|-----------------------------|------------------------------|
| TP_R           | 1.5                         | **1.0**                      |
| time_stop_et   | 12:30 ET                    | **11:30 ET**                 |
| sizing (MC)    | 2 MNQ (propfirm context)    | **5 MNQ**                    |
| VWAP filter    | on                          | unchanged                    |
| gap_thresh     | 1.2%                        | unchanged                    |
| rng_min        | 30 pts                      | unchanged                    |
| dollar_stop    | $400                        | unchanged                    |

**Rationale**: deep research #32 identified that iter_10 is a "marathon" strategy
(P(pass in 30d) = 8% at 2 MNQ). The pivot targets sprint P(pass in 30d) via three
orthogonal levers: (1) TP reduction closes trades faster → higher win-day frequency;
(2) 11:30 time stop avoids afternoon chop (documented in regime analysis); (3) 5 MNQ
scales dollar PnL 2.5× to make $1,500 target reachable in fewer days.

**Constraint**: max 3 modifications per strategy hypothesis (CLAUDE.md rule 10).
This counts as modification #1 on the iter_10 hypothesis. Budget: 2 remaining.

---

## Hypotheses (pre-registered, DO NOT adjust post-failure)

### H1 — Sharpe preserved
Walk-forward median Sharpe (6M/3M rolling) ≥ **1.22** (= 0.80 × 1.52 iter_10 baseline).

Rationale: TP=1.0R captures same directional signal but smaller per-win dollar amount.
If the underlying momentum edge is real, win rate compensates; Sharpe should degrade
by ≤ 20% since vol of daily P&L decreases proportionally with avg_winner.

### H2 — Frequency accelerated
avg_bars_held < **120 bars** (= 2h at 1-min bars, from 09:46 entry to 11:30 max).

This is structurally guaranteed by time_stop=11:30 (at most 104 bars from 09:46 to 11:30),
but the H2 gate tests that time stops dominate and trades do not typically exit via SL
late in the window (which would indicate the strategy is forced to SL after 11:30 exits
compress TP wins).

### H3 — Sprint propfirm viability
P(pass in 30d) > **25%** on Tradeify Select Flex $25K at **5 MNQ**:
- DD_eval = $1,000, target = $1,500
- N_simu = 20,000, seed = 42
- Config: PropfirmConfig() canonical (trailing_dd_simulator.py)

Baseline comparison (sizing_vs_time_2026-05-26.md):
- iter_10 @ 2 MNQ: P(pass in 30d) = 8.0%
- iter_10 @ 5 MNQ: P(pass in 30d) = 38.4%

iter_11_fast @ 5 MNQ must beat the 25% gate AND ideally ≥ 38.4% (iter_10 @ 5MNQ).

---

## Gate matrix

| Gate | Required | Source |
|------|----------|--------|
| H1 PASS | WF Sharpe ≥ 1.22 | walkforward.py |
| H2 PASS | avg_bars_held < 120 bars | iter_11_refined.py |
| H3 PASS | P(pass 30d) > 25% | mc_pivot_test.py |

### Decision rules
- H1 PASS + H2 PASS + H3 PASS → **GO** (candidate for next paper trade at 5 MNQ)
- H1 FAIL → edge destroyed by TP reduction; archive iter_11_fast; NO-GO
- H1 PASS + H3 FAIL → sizing/TP combo not sufficient for sprint; NO-GO
  - Sub-case: P(pass 30d) > 15% → note as "promising, needs further sizing analysis"
  - Sub-case: P(pass 30d) ≤ 15% → full NO-GO, iter_10 remains marathon-only

---

## n_tests budget
- n_tests global before this: 322 (CLAUDE.md)
- iter_11_fast full backtest: +1 → **323**
- walkforward.py runs WF as part of same hypothesis: counted in the +1
- mc_pivot_test.py runs MC on same trade distribution: not an additional test
- n_tests after: **323**

## Files
```
variants/iter_11_fast/
├── prespec.md               ← this file
├── iter_11_refined.py       ← backtest + full metrics
├── walkforward.py           ← extended WF (6M/3M rolling, ≥9 windows)
├── mc_pivot_test.py         ← MC P(pass) at 5 MNQ, N=20,000
├── results.json             ← written by iter_11_refined.py
└── verdict_2026-05-26.md    ← written by mc_pivot_test.py
```
