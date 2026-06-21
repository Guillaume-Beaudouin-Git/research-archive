# AgenticAITA: Multi-Agent LLM Deliberation for Autonomous Trading Without Offline Training

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.12532
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 469598d65c814d64bda90edb21ed7df7

## Summary
AgenticAITA replaces the traditional statistical signal-then-execute trading paradigm with a fully autonomous deliberative loop in which specialized LLM agents reason, negotiate, and take actions without offline training or human intervention. The framework reports a Sharpe ratio of 1.3 and maximum drawdown of 8% on an S&P 500 backtest spanning 2022-2024, claiming strong generalization across market regimes through a specialized regime-detection agent. The absence of offline training is presented as a robustness advantage, though the backtest methodology is not described in the abstract.

## Why it might be useful
The reported Sharpe of 1.3 and MaxDD of 8% on S&P 500 2022-2024 falls within the PROPFIRM_PASS gate (Sharpe>1.0, MaxDD<-10%) and would technically meet RESEARCH_PASS thresholds—however, this result must be viewed with deep skepticism. First, the memory contamination issue identified in the memory-controlled benchmark paper (id=2605.28359 in this batch) almost certainly applies: 2022-2024 is within the training window of frontier LLMs. Second, no walk-forward validation (≥5 folds mandatory per CLAUDE.md), HAC correction, or AMTP adjustment is mentioned. Third, LLM inference costs per trade would make this uneconomical at Strategy A/B scale. The result is useful as a benchmark illustration of what methodology failures look like at face value.

## Extracted content
Specific numeric claims: Sharpe ratio 1.3, maximum drawdown 8%, S&P 500 backtest 2022-2024.

## Action proposed
REFERENCE

Claimed results likely contaminated by LLM memorization (see id=2605.28359); no walk-forward or HAC correction mentioned. Do not replicate without applying the memory-controlled benchmark and mandatory methodology fixes from CLAUDE.md.
