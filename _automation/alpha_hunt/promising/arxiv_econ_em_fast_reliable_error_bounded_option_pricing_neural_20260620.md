# Fast, Reliable, and Error-Bounded Option Pricing with Pretrained Neural Networks

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.15502
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 443aa0262b924d739b35003201a3ca96

## Summary
This paper presents a recipe for neural surrogate models of option pricing that are fast, have bounded and verifiable error, and work with any simulation-based density model. A Mixture Density Network (MDN) maps model parameters and option maturity to the terminal return density as a Gaussian mixture, enabling closed-form option prices, implied volatilities, and Greeks without Monte Carlo. Applied to GJR-GARCH, the method achieves sub-millisecond pricing with provable error bounds derived from the MDN output distribution. The paper positions this as a replacement for slow Monte Carlo in risk management and pricing workflows.

## Why it might be useful
Options pricing infrastructure is not currently a focus of Algo_claude (FTMO does not support CME options per L22c). However, the BTC VRP Deribit research (`Crypto/research/archived/vrp_short_gamma/_bootstrap_vrp_notes.md`) was archived due to cost infeasibility (gross 4.4%/yr vs costs 8.9%/yr). If BTC options are ever revisited (e.g., on a lower-cost venue), this neural surrogate approach could speed up the vol surface calibration step. More immediately, the MDN + error bound methodology is a clean template for any regression problem in Algo_claude where uncertainty quantification is needed — for example, estimating the confidence interval on Strategy A's 28-bar vol signal.

## Extracted content
Mixture Density Network (MDN) maps parameters + maturity → terminal return density as Gaussian mixture. Prices, IVs, and Greeks follow in closed form. Applied to GJR-GARCH. "Sub-millisecond pricing with provable error bounds derived from the MDN output distribution."

## Action proposed
REFERENCE

Not actionable for current non-options strategies. File as pricing methodology reference if BTC options are ever revisited (`Crypto/research/archived/vrp_short_gamma/`). The MDN + error bound approach is generally useful for uncertainty quantification in any signal estimation context.
