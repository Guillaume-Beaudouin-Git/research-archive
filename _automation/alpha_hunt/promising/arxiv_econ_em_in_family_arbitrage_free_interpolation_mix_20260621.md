# Arbitrage-Free Mixture Density Interpolation Across Option Expirations

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.12717
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 9bd6f46a608147e0d980b1c39b3b91b3

## Summary
When risk-neutral densities at discrete expiration pillars are fitted as N-component mixtures, interpolating between them to form a continuous-time surface is non-trivial because naive interpolation can introduce calendar-spread or butterfly arbitrage. This paper establishes algebraic conditions guaranteeing that the interpolated surface is both in-family (remains a mixture) and satisfies the peacock (convex order) property required for a non-negative Dupire local volatility. Explicit constructions are given for the log-normal and normal kernel families. The method yields smile interpolation that is arbitrage-free across both strikes and calendar time by construction.

## Why it might be useful
This paper is indirectly relevant to the VRP short gamma research track in `Crypto/research/active/vrp_short_gamma/` — constructing a proper vol surface for BTC options (Deribit) requires arbitrage-free interpolation across expiries, which is the exact problem addressed here. However, that research track was already gated out by L13 (gross ~4.4%/yr vs costs ~8.9%/yr), so the interpolation method would only be useful if a new options edge emerged. For the ZN Baltussen bond futures momentum research at `Futures/research/active/zn_baltussen/`, implied vol surfaces from swaptions or treasury options could serve as regime filters, and this interpolation framework would be needed to construct consistent term-structure vol signals.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Options infrastructure paper; no current active strategy uses options vol surfaces. File for potential ZN Baltussen regime filter application.
