# The Mathematics of Heuristic Portfolio Optimization: Why Equal-Weight and Risk Parity Work

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.12612
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[metrics, methodology], L2_OK
**Hash**: b0bc9a48d822dfee53743c72b57bfcad

## Summary
This paper formalizes heuristic portfolio rules — equal weight, inverse volatility, risk parity, HRP, and RA-HRP — as information-restricted projections of the Markowitz/tangency solution. The central result is an "implied-return principle": a weight vector is maximum-Sharpe if and only if the implied expected return vector is proportional to the covariance-weighted weights. Using this, closed-form optimality conditions are derived for each heuristic, exposing exactly which Schur-complement terms each rule ignores. The paper shows that risk parity is optimal when expected returns are proportional to volatility, and equal-weight is optimal when both returns and variances are equal across assets.

## Why it might be useful
The A+B book uses ERC (equal risk contribution) 50/50 weighting, which is the risk-parity special case. This paper's Schur-complement analysis shows the exact conditions under which ERC is optimal. Concretely: ERC is optimal for A+B when SR_A × vol_A ≈ SR_B × vol_B (returns proportional to vol). With SR_A=1.33, SR_B=2.0, and vol targeting at 18% each, this condition may not hold exactly — the paper's framework gives a closed-form expression for the ERC vs MVO performance gap. The `Portfolio/state/portfolio_state.py` currently uses ERC; this paper's implied-return test could verify whether MVO would improve on ERC for the A+B book. Also relevant to propfirm canonical config in `Portfolio/risk/propfirm_canonical.py`.

## Extracted content
The implied-return principle: "**w** is maximum-Sharpe iff **μ_e** ∝ **Σ w**" (implied returns proportional to covariance-weighted weights). Closed-form optimality sets for equal-weight, inverse-vol, risk parity, HRP, RA-HRP. The Schur-complement substitution framework identifies which covariance terms each heuristic ignores.

## Action proposed
REFERENCE

Use to audit whether ERC is appropriate for the A+B book given the current parameter estimates (SR_A=1.33, SR_B=2.0, ρ_AB=0.039). Apply implied-return test: if implied returns under ERC are far from the estimated expected returns, MVO may improve book Sharpe. File: `Portfolio/state/portfolio_state.py`. No new data needed.
