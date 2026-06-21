# ReCAP: Regime-Adaptive Continual Learning for Portfolio Management

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.00143
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: dd4136b0f0ad0bd24b10c801b4cdcbb0

## Summary
ReCAP (Regime-aware Continual Adaptive Portfolio) integrates continual learning into portfolio management to address non-stationarity. It detects variable-length market regimes in an unsupervised way, learns regime-specific policy vectors, and builds a policy library. During live trading, a regime-gate module blends policy vectors based on current regime similarity. Only the gate and the current regime's policy vector are updated online, preventing catastrophic forgetting of regime-specific knowledge from the past. Evaluated on five real-world datasets, showing superior Sharpe over rolling-window retraining and naive fine-tuning baselines.

## Why it might be useful
The regime detection component of ReCAP (variable-length unsupervised segmentation) is the conceptually useful part for Strategy D. The current D3+D5 portfolio hypothesis (`Futures/research/active/strategy_d/hypotheses_preregistered.md`) proposes a regime filter but has not yet chosen a regime detection method. ReCAP's approach — unsupervised segmentation of NQ intraday price into variable-length regimes, then per-regime policy scoring — maps onto the D3 (mid-fade 09:45-11:00) vs D5 (BB squeeze 14:00-15:30) selection problem: which signal to weight on which days. The continual learning framing is over-engineered for our single-instrument intraday context, but the regime segmentation pipeline alone is extractable. Connection to `cba4b4a2` (TVTP Markov switching): ReCAP's segmentation is more flexible (variable-length, no fixed K) at the cost of being less interpretable.

## Extracted content
"ReCAP employs an adaptive regime detection module to segment historical market data into variable-length regimes, enabling regime-specific learning of policy vectors and the construction of a policy library."

"Only the regime-gate and the current regime's policy vector are continually updated to preserve useful knowledge effectively."

No numeric claims for our asset classes. Five unspecified real-world datasets. No code in excerpt.

## Action proposed
TEST_LATER

Extract the regime segmentation algorithm from ReCAP (likely based on change-point detection or clustering on rolling features) and apply to NQ 1-min data from `data/raw/NQ_1min_databento_2010-2026.parquet`. Test hypothesis: D3 win-rate correlates with detected regime label. Cost: 2-3 days (full paper + implementation). LATER because this requires the full ReCAP paper for the segmentation spec, and D3/D5 regime filter should first be tested with simpler TVTP Markov switching (see `cba4b4a2` entry) before adding continual learning overhead.
