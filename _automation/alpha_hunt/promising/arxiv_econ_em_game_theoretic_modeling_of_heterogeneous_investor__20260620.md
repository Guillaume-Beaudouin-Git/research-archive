# Game-Theoretic Modeling of Heterogeneous Investor Interactions for Stock Price Forecasting

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.23953
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 2beba49963936083e8873838eca66a53

## Summary
A graph-neural-network framework treats each stock as a player in a strategic game, with dynamic inter-stock relationships inferred at each time step rather than using static correlation matrices. The model learns latent heterogeneous investor strategy types from price and volume data, which the authors claim improves multi-step return forecasting on Chinese and US equity indices.

## Why it might be useful
The sector_hothand_propfirm strategy uses sector ETF momentum, not inter-stock game dynamics. This dynamic relationship model could provide a richer feature for sector rotation if applied at the ETF level rather than individual stocks. The Network Momentum GMOM was archived (failed N<35), but this game-theoretic framing is distinct and could work on S&P500 (N≥30). However, GNN infrastructure adds N_mod cost (L20 DSR applies at N_mod≥5) and the sector_hothand audit must be resolved first (t_HAC=10.38 red flag). TEST_LATER after audit.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Reserve for sector_hothand_propfirm after completing the t_HAC=10.38 audit; GNN implementation requires 3+ days.
