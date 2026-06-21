# Crypto-Equity-FX Network Integration and Cross-Asset Spillovers During Turbulent Regimes

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.30442
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 66165a12b1f734f1290008bf2b01cc1a

## Summary
Using a balanced panel of 381 assets (crypto, fiat currencies, S&P 500 equities) from October 2017 to February 2024, this paper studies cross-market integration dynamics through rolling correlation networks, consensus community detection, Turbulence Indices, and VAR-based connectedness measures. The central finding is that crypto increasingly migrates into the equity community over time, and cross-market spillovers intensify precisely during turbulent regimes when diversification is most needed. This creates a structural challenge: the diversification benefit of crypto versus equity is regime-dependent and weakest at exactly the moments when it would be most valuable.

## Why it might be useful
This finding directly challenges the portfolio diversification assumption underlying the A+B book (SR=2.31, ρ_AB=0.039 full-sample): if BTC/ETH/SOL in Strategy A increasingly co-move with S&P 500 equities during stress, the low correlation assumed in the book-level Sharpe calculation may be overstated in tail scenarios. The turbulent-regime migration finding is also a concrete concern for Strategy B's mainnet deployment decision around 2026-07-17—delta-neutral carry pays down during stress via funding rate compression, but if HMSTR or other HL perps experience liquidation cascades correlated with equity stress, the "neutral" position may not be neutral. The authors' rolling correlation network approach could be implemented on the `data/deep_history_utc/` panel to build a crypto-equity stress indicator as a kill-switch input for Strategy B.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Building a rolling crypto-equity correlation turbulence indicator to serve as an additional input to Strategy B's kill switch logic is feasible with existing `data/deep_history_utc/` data; implement before mainnet deployment.
