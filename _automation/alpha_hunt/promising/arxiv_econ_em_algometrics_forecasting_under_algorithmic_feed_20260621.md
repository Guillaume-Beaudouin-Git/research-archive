# Algometrics: When Predictive Models Change the Data They Forecast

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.23978
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: d398ac195d1b03c067e135345596a380

## Summary
In algorithmic markets, predictive models alter the data-generating process they target once their outputs are converted into trades. This paper distinguishes historical risk (IC under passive evaluation) from deployment risk (IC when the algorithm affects prices or liquidity), and provides sufficient conditions for IC stability under deployment. Key finding: momentum-reinforcing strategies may gain IC from market impact, while mean-reverting strategies may lose IC. Models with higher passive IC can underperform in deployment if their trades are mean-reverting; the equilibrium IC depends on the interaction between signal direction and market impact.

## Why it might be useful
The momentum-reinforcing IC gain under deployment is directly relevant to Strategy A (TSMOM v3 on BTC/ETH/SOL): at NOTIONAL_USD equivalent for a $50K propfirm account with VOL_TARGET_LIVE=0.18, Strategy A's BTC trades are likely small enough that market impact is negligible, but if Propr allocated larger accounts, the TSMOM signal could in principle become self-reinforcing in the very assets it holds (BTC/ETH/SOL being small enough for large prop accounts to move). For Strategy B's 8h delta-neutral rebalancing on HL testnet, the mean-reversion component (rebalancing back to delta-zero) falls into the "mean-reverting strategies lose IC under deployment" category, which should motivate careful measurement of execution quality in `logs/fills.csv` for the rebalancing legs specifically.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Important conceptual framework for thinking about deployment effects; no direct test needed at current A/B notional scales, but essential reading before scaling notional significantly.
