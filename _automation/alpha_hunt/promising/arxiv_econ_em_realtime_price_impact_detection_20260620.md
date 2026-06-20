# Real-Time Price Impact Detection for Algorithmic Order Execution

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.13419
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 1e1154770fa9284f1ce61deeee209eb7

## Summary
This paper proposes an online Kalman-filter framework to detect in real time whether an algorithm's trading activity is causing market impact during order execution. The core insight is that conventional slippage monitoring fails because it cannot distinguish between impact (own-caused price movement) and adverse selection (informed flow moving against you), while ex-post aggregate models are too slow for intra-order adaptive control. The paper formulates an online state estimator that disentangles both components from tick-by-tick price and volume data, enabling an execution algorithm to slow down or switch venues when impact is detected. Empirical validation uses institutional equity orders; the method generalizes across asset classes.

## Why it might be useful
Strategy B (delta-neutral carry on Hyperliquid) targets mainnet launch around 2026-07-17. The current execution spec in `strategies/delta_neutral/` places rebalance orders every 8 hours. Once on mainnet at larger notional, the question of whether the 8-hour rebalances cause detectable market impact on HL's perpetual markets becomes real — HL's L2 depth on smaller pairs (HMSTR, TST) is limited. The detection framework from this paper could be adapted as a post-trade monitoring check on each 8-hour rebalance. Additionally, the 10:02 run already staged "Trading in the Sunshine or in the Shade" (market impact on HL), which is complementary. Together these two papers form a complete pre-mainnet execution audit.

## Extracted content
"Realtime monitoring fails because reliable slippage estimates require large samples, and online slippage is confounded by adverse selection." The proposed solution is an online state estimator that separates impact from adverse selection. Validation uses institutional equity orders.

## Action proposed
TEST_LATER

Read before Strategy B mainnet launch (~2026-07-17). Assess whether the online detection framework is tractable for HL REST/WS API at 8h rebalance frequency. Pair with "Trading in the Sunshine or in the Shade" (arxiv 2606.15715, already in `promising/`) for complete execution risk picture. Implementation cost: 2–3 days for adaptation to HL API.
