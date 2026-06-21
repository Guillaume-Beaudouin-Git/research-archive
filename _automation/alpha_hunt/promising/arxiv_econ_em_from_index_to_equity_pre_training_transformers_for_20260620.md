# From Index to Equity: Pre-Training Transformers for Stock Return Prediction

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.23962
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 5be83263797e331da3d8428ec1a84f23

## Summary
A transformer is pre-trained on the TSX index to predict intra-day return direction, then fine-tuned on individual TSX stocks. Index pre-training provides a market-level representation that transfers to individual equity prediction, improving directional accuracy relative to models trained from scratch. The model is also adapted for return-value regression tasks.

## Why it might be useful
The sector_hothand_propfirm research (Equities/research/active/) uses sector ETF momentum; pre-training on SPY/QQQ and fine-tuning on sector ETFs is the direct analogy of this paper's approach. The current equity indices sprint IC of 0.033-0.075 is below the 0.08 daily ETF gate — pre-training might lift IC above threshold. Requires transformer infrastructure and yfinance sector data (both available). DSR correction is mandatory under L20 if this adds a modification. TEST_LATER after the mandatory t_HAC=10.38 audit clears.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Apply index→sector ETF pre-training to sector_hothand after t_HAC=10.38 audit; yfinance available, transformer adds DSR modification count.
