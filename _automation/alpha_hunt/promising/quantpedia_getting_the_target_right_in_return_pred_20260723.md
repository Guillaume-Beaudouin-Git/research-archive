# Getting the Target Right in Return Prediction

**Source**: quantpedia
**URL**: https://quantpedia.com/getting-the-target-right-in-return-prediction/
**Captured**: 2026-07-23 17:00 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 002018a63dfdf632019c5a366a7704b7

## Summary
Cakici and Zaremba argue that in ML-based equity return prediction, the label
definition matters more than model complexity or feature engineering. Training
a model to predict cross-sectional rank rather than the raw level of future
returns produces materially stronger portfolios in large-cap universes, with
the authors reporting roughly a doubling of both returns and Sharpe ratios
relative to level-based targets. The implication is that most of the gains
researchers chase through fancier architectures may actually be available for
free just by reformulating the prediction problem as ranking instead of
regression.

## Why it might be useful
This connects to the methodology axis around IC computation used in
`_automation/feasibility` gate A: a rank-based target effectively changes IC
from a Pearson to a Spearman-style measure, and the claimed doubling of
Sharpe from relabeling alone is a useful prior when calibrating expected gains
from methodology changes versus genuinely new signals. It also brushes
against Strategy A's structural constraint — the live TSMOM config trades
only BTC/ETH/SOL (N=3), which is far below the N>=30 hard rule for
cross-sectional treatments, so a rank-based cross-sectional transform of the
signal cannot be legally applied there without first expanding the traded
universe. No equities CS strategy is currently active in the repo, so there
is no immediate host for this idea.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt beyond the
qualitative claim that rank-target models "roughly double" returns and Sharpe
ratios versus level-target models in large-cap universes (author-reported,
no exact figures given). Full article needed for further extraction.

## Action proposed
REFERENCE
