# Cross-Sectional Aggregation Attenuates Regime-Switching Signals: A Disaggregated Approach

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.08398v1
**Captured**: 2026-06-09 06:04 UTC
**Filters passed**: L1=[metrics, methodology], L2_OK
**Hash**: 71f2c6ce4060f2cb5d56799ad5995a57

## Summary
Hamilton-style regime-switching models applied to aggregated time series systematically miss regime transitions that are visible in the disaggregated components. Averaging across cross-sectional units smooths out the high-variance transitions that define a regime switch, making the aggregate appear to be in a "blended" state rather than clearly in one regime or another. The authors build regime-switching models that accommodate both autoregressive dynamics and grouped cross-sectional heterogeneity, then apply them to 94 U.S. macro series (GDP components, industrial production, employment, hours). The resulting business cycle classifications are sharper than those obtained from aggregate series alone, with Monte Carlo validation showing the approach is computationally feasible at a few hundred series.

## Why it might be useful
This is directly relevant to Strategy D's active research phase. D3 (Opening Range Mid-Fade) and D5 (Afternoon BB Squeeze) are both regime-conditional strategies, and the pre-registration in `Futures/research/active/strategy_d/hypotheses_preregistered.md` specifies a regime filter as a portfolio-level overlay. The paper's core finding — that aggregate regime detection (using e.g. a single NQ return series or a VIX level threshold) systematically attenuates the signal — suggests the current approach of using NQ composite as the regime input could be the reason D3/D5 looked like FAIL individually (Sharpe -1.08/-1.32): a blurry regime filter misclassifies expansion/contraction boundaries, which are the key differentiator. Concrete test: in `Futures/research/active/nq_intraday/analysis/`, replace the aggregate NQ-based regime classifier with a disaggregated one using the 94-series macro dataset (FRED is free) — check whether sharper regime labels improve the D3+D5 portfolio Sharpe in walk-forward. The AMTP correction (n_tests=156+158=314) would still apply, but this is a *pre-registered* modification (budget: 3 mods, 0 consumed for D).

## Extracted content
No code or formulas in the excerpt. The authors report "sharper business cycle classifications than those typically found in the literature" from the disaggregated model. Monte Carlo simulation verifies computational feasibility for "a few hundred time series."

## Action proposed
TEST_LATER — Data (FRED 94 macro series) is freely available and the integration point is clear (Strategy D regime filter), but the implementation requires fetching and aligning macro series + refitting the regime model, estimated at 1-2 days. Run after current D3+D5 portfolio combination baseline is established.
