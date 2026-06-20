# What Deep Hedging Actually Learns: Delta Corrections, Regime Fragility, and Symbolic Distillation

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.21696
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[metrics, methodology], L2_OK
**Hash**: 256029cca7bc4ded2134909d00cb52ea

## Summary
This paper audits what a TD3 (Twin Delayed Deep Deterministic) RL agent actually learns when trained on S&P 500 index options under a local downside-shortfall reward. Rather than comparing performance, it asks what the learned hedge does and when it fails. The key finding: the TD3 agent learns a systematic delta haircut relative to Black-Scholes, explained by the spot-implied correlation in the data. In walk-forward tests from 2015–2023, the hedge works well in normal regimes but fails catastrophically when the regime shifts (e.g., 2020 COVID crash, 2022 rate shock). Symbolic distillation reveals the agent's implicit strategy as a simple formula, making the hedge interpretable.

## Why it might be useful
The "regime fragility" finding is directly relevant to L31 in CLAUDE.md: "edges real in their regime decay out of it; OOS / post-regime split is MANDATORY." The symbolic distillation approach — extracting a simple formula from a complex RL agent — is a useful framework for auditing any ML-based strategy variant. For Strategy D (D3+D5 NQ intraday), if an ML-augmented signal is ever proposed, symbolic distillation could help audit whether the model is learning genuine edge or fitting to a specific regime (2021–2023 NQ data was strongly trending). The walk-forward design (2015–2023, multiple market regimes) is more rigorous than most papers in the dataset.

## Extracted content
"TD3 agents are compared with a daily-updated Black-Scholes delta hedge on the same option episodes." The agent "usually learns a systematic delta haircut relative to Black-Scholes." Walk-forward tests from 2015 to 2023. Symbolic distillation extracts the agent's implicit strategy as a formula. "Correction is explained by spot-implied correlation."

## Action proposed
REFERENCE

Use symbolic distillation approach as audit methodology for any future ML signal in Strategy D or successor strategies. The regime fragility finding reinforces L31 and the walk-forward requirement. Not directly tradeable (requires options infrastructure), but the methodology generalizes to any RL-trained strategy.
