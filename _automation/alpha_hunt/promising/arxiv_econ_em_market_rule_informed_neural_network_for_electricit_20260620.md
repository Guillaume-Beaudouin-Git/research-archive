# Market-Rule-Informed Neural Network for Electricity Imbalance Price Forecasting

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.09061
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: f124a37c7ff2c193d1feefa9cac10bac

## Summary
Electricity imbalance prices are forecasted using a neural network whose latent space embeds the known market-rule-based price formation mechanics. Heterogeneous input signals with different publication lags are handled via attention. The framework is evaluated on battery assets and automated bidding pipelines in real-time energy markets.

## Why it might be useful
The market-rule-informed architecture embeds domain constraints into the latent space rather than post-processing predictions. For Strategy B, this translates to embedding funding rate mechanics (8h reset, ±0.05% clamp, oracle vs index price) into the signal model's architecture. This would be a 3+ day modification to an already-working strategy (Sharpe 4.10 backtest); the current CARRY_FLOOR_8H rule is validated and simpler. Background reference.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
