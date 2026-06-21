# Explicit Signal-Adaptive Sequential Optimal Execution Quotes

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.24242
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 22f7f6ff598ad77bc1f5c3ef9b2235f6

## Summary
A closed-form solution is derived for optimal limit-order placement when the trader has a directional signal. The model jointly controls quote prices over a sequence of limit orders, incorporating signal-dependent drift, price impact, inventory risk, and fill uncertainty via point processes. Four execution criteria are treated explicitly: terminal wealth, wealth with inventory penalty, CARA utility, and mean-variance. The optimal mid-quote drifts toward the signal direction by an amount proportional to signal strength.

## Why it might be useful
This is directly applicable to Strategy B's Hyperliquid execution. Currently HMSTR positions are placed at the midpoint with NOTIONAL_USD=50 and fixed 8h rebalance; the paper provides a framework for adapting the quote to the funding z-score (Strategy B's signal). When funding is at an extreme, the optimal quote should drift toward the carry side by a signal-proportional amount — reducing slippage on entry. The Avellaneda-Stoikov nested model (cited in the June 21 1202 run's bid-ask paper) provides continuity. Concrete modification target: strategies/delta_neutral/rebalance.py entry logic post-mainnet deploy (~July 17).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Implement signal-adaptive quote adjustment in Strategy B's entry logic; defer until mainnet deploy (~July 17).
