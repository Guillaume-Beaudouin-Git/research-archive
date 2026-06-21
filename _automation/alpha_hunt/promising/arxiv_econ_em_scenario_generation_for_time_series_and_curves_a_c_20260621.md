# Semiparametric Bootstrap for Yield Curve Scenario Generation

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.11859
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[macro_trading], L2_OK
**Hash**: 45b2230d5af54a92e0a350d17740acfa

## Summary
A comparison of nonparametric (stationary bootstrap, preserving empirical distribution) vs semiparametric (parametric AR/mean-reverting structure + bootstrapped residuals) simulation for yield curve scenarios. The key finding is that stationary bootstrap produces valid joint distributions but implausible individual trajectories, while semiparametric methods combining term-structure models with residual resampling generate economically coherent paths. Applied to interest rate curves where direct resampling of rate changes can produce negative-rate explosions or yield inversions that violate economic realism constraints. The issue is most acute for interest rates because the mean-reverting constraint is structurally necessary, not optional.

## Why it might be useful
ZN Baltussen research (`Futures/research/active/zn_baltussen/`) studies bond futures momentum and may require yield curve scenario generation for stress testing. The semiparametric approach (AR + residual bootstrap) is directly applicable to the ZN signal's vol-targeting module — using a mean-reverting model for yield changes rather than iid bootstrap prevents the walk-forward overfitting that occurs when residual distribution is implausible. However, our block bootstrap methodology (Politis-Romano, current standard per CLAUDE.md) already addresses some of this by preserving autocorrelation structure. The interest rate specific concern (negative-rate explosion) is less critical for ZN futures which have a natural floor. Comparison: semiparametric bootstrap ≈ our block bootstrap + parametric mean-reversion constraint; marginal gain is modest.

## Extracted content
"Scenarios may be valid in distribution while single trajectories fail to represent plausible states of the world."

"Combining these methods with fully parametric term-structure models yields more coherent and realistic simulations of yield-curve dynamics."

No code or specific numeric claims in excerpt.

## Action proposed
REFERENCE

Useful methodology context for ZN Baltussen stress testing. Does not replace our existing Politis-Romano block bootstrap, but adds rationale for mean-reversion-constrained residual resampling as an enhancement.
