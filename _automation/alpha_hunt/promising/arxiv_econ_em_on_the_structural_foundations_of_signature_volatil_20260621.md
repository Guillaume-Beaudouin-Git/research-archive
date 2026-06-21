# Signature Volatility Models: Existence, Arbitrage-Free Conditions, and Hedging

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.17142
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: a372d80aac602fd92311d26f4286b31f

## Summary
Four structural results for signature SDE models of the form dS_t = S_t⟨ℓ, Ŵ_t⟩dB_t where the volatility is a linear functional of the path signature. (1) Global existence and uniqueness under summability conditions. (2) NFLVR (no free lunch with vanishing risk) holds if the stochastic exponential is a true martingale. (3) Market completeness characterized by the density of truncated signature span in L²(Q). (4) Hedging error decomposition into projection error beyond the completeness depth. The paper establishes the mathematical foundations for using path signatures as volatility drivers.

## Why it might be useful
Signature methods are a promising alternative to recurrent neural networks for path-dependent financial modeling, with the advantage of being mathematically tractable. For our vol-targeting in Strategy A (28-day window, sqrt(365)), replacing the rolling-window vol estimator with a signature-based vol estimator could improve responsiveness to regime changes. However, this requires: (1) translating the theoretical SDE into a practical discretization; (2) fitting the linear functional ℓ from data; and (3) ensuring the estimator is computationally feasible for daily rebalancing. All of this is complex implementation work for marginal vol-estimation improvement when the current estimator already gives Sharpe 1.33 OOS. The paper provides theoretical foundations, not a turnkey implementation.

## Extracted content
"dS_t = S_t ⟨ℓ, Ŵ_t⟩ dB_t on the weighted tensor algebra T_w"

"H3 makes the reference-measure stochastic exponential a true martingale, hence yields NFLVR."

Highly mathematical; no code in excerpt.

## Action proposed
REFERENCE

Advanced stochastic vol theory. Signature-based vol estimator is an interesting research direction but too complex for near-term implementation. Current vol-targeting approach already validated OOS.
