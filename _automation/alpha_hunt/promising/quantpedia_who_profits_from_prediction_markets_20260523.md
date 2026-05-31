# Who Profits from Prediction Markets?

**Source**: quantpedia
**URL**: https://quantpedia.com/who-profits-from-prediction-markets/
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 2bfcb664ba12c691b1cbb06e4d0aef82

## Summary
Using 222 million prediction market trades with directly observable terminal payoffs, the paper "Who Profits from Prediction? Execution, Not Information" decomposes trader returns into a directional component and an execution component. The surprising finding: retail traders who correctly pick winners more than 50% of the time still lose money, while automated traders with sub-50% directional accuracy earn nine-figure profits. The execution component — not information quality — determines which trader types earn positive returns.

## Why it might be useful
The execution-over-information finding is broadly relevant to all Algo_claude strategies, especially Strategy B (delta-neutral carry on Hyperliquid): the carry itself is essentially a directional forecast that funding rates will stay positive, but whether the 8h rebalance times produce positive P&L depends on execution timing relative to other traders. The mechanism documented here — that automated traders extract value through execution timing rather than information advantage — is the same mechanism behind Strategy B's Hyperliquid rebalance window design (00:10, 08:10, 16:10 UTC, 10 minutes after funding settlement). Prediction markets themselves are not an active research area; this is a structural insight applicable to execution quality evaluation more broadly.

## Extracted content
The paper uses "222 million prediction market trades with directly observable terminal payoffs." The key decomposition: "the execution component, not the directional component, determines which trader types earn positive returns." No specific Sharpe or win-rate statistics in the excerpt.

## Action proposed
REFERENCE — Prediction markets are outside current strategy scope. The execution-quality insight reinforces Strategy B's rebalance timing design but does not open a new test path.
