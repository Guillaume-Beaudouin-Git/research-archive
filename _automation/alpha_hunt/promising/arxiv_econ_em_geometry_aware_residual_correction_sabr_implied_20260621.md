# Geometry-Aware Neural Residual Correction of the SABR Implied Volatility Formula

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.06604
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 1614cb281032bb3c7c587aacd005296e

## Summary
The standard Hagan SABR formula for implied volatility has known approximation errors in extreme parameter regimes. This paper augments a neural network's input representation with geometric features derived from the SABR SDE structure, rather than either fully replacing the formula with a black box or relying on it alone. The hybrid approach—analytical backbone plus ML residual correction with geometry-aware inputs—substantially reduces approximation error compared to the Hagan formula alone, especially in extreme regimes. The method preserves interpretability through the analytical structure while gaining accuracy from the learned residual.

## Why it might be useful
The hybrid analytical-backbone-plus-ML-residual architecture is a design pattern applicable to any signal with a known theoretical form but known approximation errors in specific regimes. Strategy A's TSMOM signal uses a tanh transformation of a cumret/vol ratio—a theoretically motivated form—but the vol estimator itself may have regime-dependent biases (documented in L15: regime overlays only useful when MaxDD>20%). Adapting the SABR hybrid approach to the vol estimator (keep the 28-bar rolling window as backbone, add a lightweight ML correction for regime-specific biases learned from the FinStressTS diagnostic profiles) would be an application of this principle. This is speculative and distant from current priorities; the paper is primarily relevant to options vol surface calibration in the VRP research track.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Options vol surface paper; SABR not used in current strategies. Design pattern of analytical backbone + ML residual is philosophically useful but no direct test path.
