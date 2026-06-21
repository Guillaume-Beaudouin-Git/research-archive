# Taylor Expansion of the Rough Heston Fractional Riccati Solution in the Hurst Parameter H

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.16619
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 60224ddc5e0935111b88d5db24972abd

## Summary
In the rough Heston model, the fractional Riccati equation depends on the Hurst parameter H in a complex way that makes calibration gradients with respect to H difficult to compute. This paper derives a Taylor expansion of the Riccati solution around any expansion point in (-1/2, 1/2], with coefficients recursively characterized as solutions to linear Volterra equations with fractional-logarithmic kernels. Local uniform convergence and analyticity of the Riccati solution in H are proved. The expansion enables efficient computation of implied volatility sensitivities to H and calibration gradients, making rough vol model calibration more tractable.

## Why it might be useful
The rough Heston model captures the volatility roughness (H < 1/2) documented in empirical vol surfaces, which is relevant to the VRP short gamma research at `Crypto/research/active/vrp_short_gamma/` since BTC options exhibit rough vol behavior. However, that research track is blocked by L13 (costs kill the edge). The calibration gradient result is useful if the ZN Baltussen bond futures research ever incorporates rates vol surface data—bond vol is known to exhibit roughness, and the Hurst parameter expansion would enable fast recalibration. This is a pure mathematical finance paper; no direct application at current project stage.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Rough stochastic vol theory; no active strategy uses rough Heston calibration. File for potential ZN rates vol regime filter consideration.
