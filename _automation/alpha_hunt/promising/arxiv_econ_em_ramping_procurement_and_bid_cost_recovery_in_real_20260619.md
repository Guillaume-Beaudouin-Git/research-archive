# Electricity Market Ramping Products: Pricing Design and Bid-Cost Recovery Under Uncertainty

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.19599v1
**Captured**: 2026-06-19 02:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: b05117e424a4ab47b026821b229bb87a

## Summary

The paper studies real-time electricity market design for flexible ramping products when net demand is uncertain. Grid operators (CAISO, ERCOT) co-optimize dispatch and ramp procurement through rolling stochastic optimization with binding and advisory intervals. The authors compare single-interval versus multi-interval co-optimization and three pricing rules — locational marginal pricing (LMP), maximum dispatch cost pricing (MDCP), and maximum temporal LMP (MTLMP). They show that MDCP eliminates discriminatory bid-cost recovery (BCR) and yields truthful bidding incentives for price-taking generators, while MTLMP achieves this in most cases. Single-interval co-optimization outperforms under high forecast uncertainty and moderate ramp requirements; multi-interval is superior when forecasts are accurate and ramp needs are challenging. Empirical results on CAISO and ERCOT data confirm MDCP and MTLMP increase producer profits with negligible BCR, at the cost of higher consumer payments relative to LMP.

## Why it might be useful

The active Commodities pipeline (`xs_basis_tsmom`, 24 continuous CFTC-reportable futures) does not include electricity futures (CAISO/ERCOT are physical market operators, not NYMEX/CME). The ramping premium analyzed here has no direct structural equivalent in the futures basis signals targeted by `xs_basis_tsmom`. Natural gas (NG=F) is plausibly in the 24-contract universe and does interface with power market dynamics, but this paper analyzes clearing mechanism design rather than a tradable basis or TSMOM signal on NG. There is no archived research in the history that this paper extends or contradicts. The paper's stochastic optimization framing (rolling window, binding vs advisory intervals) has superficial similarity to walk-forward strategy design, but that parallel is not actionable. No path into A, B, or C.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

REFERENCE — electricity market microstructure (CAISO/ERCOT ramping products) is out of scope for the current commodities pipeline; no tradable signal for A/B/C.
