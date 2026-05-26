# MC Stress Test — Strategy C (Tradeify $25K, 2 MNQ)

N=20,000 | seed=42 | CRN | config: DD_eval=$1,000 DD_funded=$1,000 lock=$26,100

| Scenario              |  P(pass) |  P(bust) | P(timeout) | E[days] |
|-----------------------|----------|----------|------------|---------|
| A — Baseline          |    62.8% |    34.1% |       3.1% |    72.7 |
| B — Slippage 1.5×     |    59.9% |    36.9% |       3.2% |    73.1 |
| C — Vol 1.2×          |    58.9% |    40.6% |       0.5% |    55.7 |
| D — Combined          |    56.7% |    42.8% |       0.6% |    56.1 |

_Runtime: 36.1s_
