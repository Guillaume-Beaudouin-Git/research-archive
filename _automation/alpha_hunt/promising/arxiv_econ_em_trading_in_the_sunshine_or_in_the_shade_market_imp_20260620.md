# Market Impact and Adverse Selection on Hyperliquid: Sunshine vs. Hidden Order Execution

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.15715
**Captured**: 2026-06-20 10:02 UTC
**Filters passed**: L1=[methodology, macro_trading], L2_OK
**Hash**: 41cfef6a227343236c79fdbd69ce2690

## Summary

Barone & Lillo study 4.3 million hidden metaorders and 465,000 publicly-disclosed TWAP orders on Hyperliquid, the on-chain perpetual futures DEX. Protocol-native TWAP orders broadcast their terms from inception, making Hyperliquid a natural experiment in "sunshine trading" where preannouncement is observable. The key empirical finding is that visible TWAP executions experience lower adverse-selection costs and leave a smaller permanent price impact than comparable hidden orders. When a hidden order trades alongside an already-visible same-direction TWAP, adverse-selection costs shift toward the non-announcing trader. Visible TWAPs also elicit genuine liquidity provision: displayed depth on the absorbing side increases while the TWAP is active, the effect scaling with order size.

## Why it might be useful

Strategy B (delta-neutral carry, HL testnet live since 2026-05-17, every 8h rebalance) executes directly on Hyperliquid — the exact venue studied in this paper. Our current rebalance logic places market or limit orders without broadcasting intent. The paper gives us a quantified mechanism: announced TWAP execution reduces permanent impact because liquidity providers see the order and tilt the book. For the current NOTIONAL_USD=50 testnet positions this is irrelevant, but at mainnet scale (~2026-07-17 target) position sizes will matter more. Concretely: (a) review `strategies/delta_neutral/execution.py` to determine whether we are placing taker vs. maker orders on rebalance; (b) at mainnet launch, if rebalance notional exceeds ~$5k/leg, prefer limit-order execution over market orders to avoid the adverse-selection penalty identified here; (c) the hidden-vs-announced asymmetry also informs how we should interpret our 8h fill prices in `logs/fills.csv` — fills during periods when large TWAP flows are active on the same side will be systematically worse.

## Extracted content

From the abstract:
- "Visible TWAPs face lower execution costs than comparable hidden metaorders and leave a smaller permanent price impact."
- "Hidden metaorders executed alongside already-visible same-direction TWAP flow incur higher permanent costs: adverse-selection costs shift toward non-announcers."
- "Visible TWAP programs elicit liquidity provision: while active, displayed depth rises and the book tilts toward the absorbing side, the more so the larger the announced order."
- Dataset: 4.3 million hidden metaorders + 465,000 visible TWAP executions on Hyperliquid, reconstructed from address-level on-chain data.

No code in excerpt. Full article needed for quantitative cost estimates by order size.

## Action proposed

TEST_LATER

Execution insight is immediately relevant to Strategy B at mainnet scale, but the paper needs to be read in full for quantitative impact estimates. Implementation step: read Section 4 of the paper for the cost differential magnitude by order size; then update the Strategy B execution spec in `strategies/delta_neutral/` before mainnet launch. Data needed: on-chain Hyperliquid fills (not currently in repo). Cost-to-implement < 0.5 day once the paper is read; currently blocked on paper access, hence LATER not NOW.
