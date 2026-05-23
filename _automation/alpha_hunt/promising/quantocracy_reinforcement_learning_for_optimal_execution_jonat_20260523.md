# Reinforcement Learning for Optimal Execution [Jonathan Kinlay]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=THS8gtcmCV&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 75d74635d4e30d5022cfacdf261db5da

## Summary
Jonathan Kinlay covers RL-based optimal execution — the problem of minimizing market impact when entering or exiting large positions. The example used (80% annual turnover on a $5bn book) illustrates how execution quality compounds significantly at scale. The RL framing treats execution as a sequential decision problem with state (remaining inventory, time, market conditions) and action (order size/timing) to minimize implementation shortfall.

## Why it might be useful
At current strategy scales (5-10 /MNQ on $50K for Strategy C, BTC/ETH/SOL on retail sizes for Strategy A), optimal execution concerns are minimal — round-trip costs of 0.01% (futures) or 0.17% (crypto) at retail scale are dominated by signal quality rather than execution slippage. Strategy B (delta-neutral on Hyperliquid testnet) could theoretically benefit from execution timing around 8h rebalances, but testnet liquidity is artificial. This item becomes relevant if/when AUM reaches $1M+ range. Not actionable now.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

RL-based execution optimization. Not applicable at current small-account scale. Revisit when strategy AUM exceeds $500K.
