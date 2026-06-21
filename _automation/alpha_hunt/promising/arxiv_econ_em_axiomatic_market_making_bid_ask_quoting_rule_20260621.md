# Axiomatic Derivation of the Bid-Ask Market Maker Quoting Rule

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.09454
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 9cb6944d7433a9a21638ede92535eea5

## Summary
Eight natural axioms on a market maker's quoting behavior—mapping inventory, belief, variance, trade intensity, and informed-trader fraction to bid-ask pairs—uniquely determine a three-parameter family of quoting rules. The mid-quote is linear in inventory, and the spread decomposes additively into inventory and adverse-selection components. Each parameter is identified by a single axiom, and the resulting model nests Avellaneda-Stoikov and Cartea-Jaimungal as special cases with different parameter restrictions. The axiomatic approach provides a grounding for existing models and a framework for evaluating whether observed spreads are consistent with rational market-making.

## Why it might be useful
Understanding bid-ask spread structure and adverse-selection decomposition is directly relevant to Strategy B's delta-neutral carry execution on Hyperliquid. The HL testnet execution fills visible in `logs/fills.csv` could be analyzed using the adverse-selection component to distinguish whether HMSTR fill quality degrades due to inventory constraints (spread-widening from maker inventory) or due to informed trading (adverse selection component). This would inform the NOTIONAL_USD=50 sizing decision for mainnet—if adverse selection is the dominant spread component for HMSTR, increasing notional could worsen fills non-linearly. The Cartea-Jaimungal nesting is directly applicable since that model is standard in algo execution research.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Analyzing `logs/fills.csv` to decompose spread into inventory vs. adverse-selection components using the Avellaneda-Stoikov special case is a concrete 1-day test. Defer until Strategy B mainnet deployment approach (post-July 17) when understanding fill quality becomes critical.
