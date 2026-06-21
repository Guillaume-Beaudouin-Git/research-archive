# Scaling Limits of Bivariate Nearly-Unstable Hawkes Processes and Applications to Microstructure

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.03703
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 8727983b73eb4d0f5f62de99b5ba45a2

## Summary
A functional limit theorem is proved for two coupled nearly-unstable Hawkes processes with different heavy-tail kernel exponents, producing distinct degrees of roughness in the limiting intensity processes. As criticality is approached, the renormalized intensities converge to a coupled stochastic Volterra system. The heterogeneous result applies to microstructure models where bid and ask intensities have different clustering speeds.

## Why it might be useful
Strategy B executes on Hyperliquid using limit orders, and fill quality depends on the asymmetry between buy and sell order clustering. The bivariate Hawkes with different kernel exponents models exactly this regime: at funding extremes (L50 confirmed), buy-side clustering should dominate. A concrete test: fit a bivariate Hawkes model to HMSTR L2 data from the HL WebSocket to estimate the asymmetry parameter at funding extremes vs normal regimes. This requires HL order book streaming data and hawkeslib/tick library. 2-3 days, best done post-mainnet deploy.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Fit bivariate Hawkes to HMSTR order flow to quantify buy/sell clustering asymmetry at funding extremes vs normal regimes; post-mainnet deploy.
