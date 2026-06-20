# Yield Curve Dynamics Using Variational Autoencoders Under No-Arbitrage Constraints

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.12764
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology, macro_trading], L2_OK
**Hash**: dca6ece581258a354fb8c7e46049cfdc

## Summary
This paper introduces a physics-informed VAE for yield curve modeling that resolves the conflict between the statistical flexibility of deep learning and the theoretical constraints of fixed-income models. Standard generative models suffer from "manifold collapse" and arbitrage violations when extrapolating across macro regimes. The proposed two-stage architecture first learns a no-arbitrage-constrained latent space (using HJM drift conditions as a regularizer), then uses the VAE decoder to generate regime-consistent yield curve scenarios. Tested across multiple macro regimes (pre-GFC, GFC, zero-rates, rate-hike cycle), the constrained VAE avoids the arbitrage violations that afflict unconstrained models.

## Why it might be useful
The ZN Baltussen bond futures momentum research (`Futures/research/active/zn_baltussen/`) uses bond momentum signals. Yield curve dynamics — specifically the curvature and slope of the yield curve — are key drivers of ZN (10Y Treasury futures) momentum. A VAE-based yield curve model that respects no-arbitrage constraints could serve as the regime detector for the ZN strategy: when the VAE latent state indicates a transitional regime (e.g., from zero-rates to rate-hike), ZN momentum signals may invert. The no-arbitrage regularization also aligns with the term-spread and yield-curve signals in the macro_trading L1 patterns.

## Extracted content
Two-stage architecture: (1) no-arbitrage-constrained latent space (HJM drift conditions as regularizer), (2) VAE decoder for scenario generation. "Standard generative models suffer from manifold collapse and severe arbitrage violations when forecasting term structures across diverse macroeconomic regimes." Tested across pre-GFC, GFC, zero-rates, rate-hike regimes.

## Action proposed
REFERENCE

File for ZN Baltussen research (`Futures/research/active/zn_baltussen/`). The no-arbitrage VAE could serve as a regime indicator for ZN momentum — when the latent state shifts, adjust signal lookback. Implementation requires term structure data (FRED yield data available free) + VAE training. Priority: after ZN baseline tests are complete.
