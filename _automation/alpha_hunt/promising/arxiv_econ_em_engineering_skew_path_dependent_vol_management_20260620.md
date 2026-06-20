# The Engineering of Skew: A Path-Dependent Framework for Asymmetric Volatility Management

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.09123
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: f52e01657cbd1207738e4ddd745f5629

## Summary
This paper develops a path-dependent framework for asymmetric volatility management, motivated by the nonlinearity of drawdown recovery: after a drawdown of depth D, the required gain is R = 1/(1-D) - 1, which is nonlinear and increasingly penalizes deep drawdowns. The paper proposes risk-management rules that target the drawdown path directly (not just current volatility), including a "skew budget" that asymmetrically penalizes downside vol vs. upside vol. Applied to institutional allocator contexts (spending rules, rebalance decisions), the path-dependent rules outperform symmetric vol targeting on drawdown-adjusted return metrics.

## Why it might be useful
The MAX_DAILY_DD=2.8% and MAX_TOTAL_DD=5.5% guardrails for Strategy A (Propr) and the FTMO 10% MaxDD gate are symmetric thresholds that don't account for the nonlinearity of drawdown recovery. The path-dependent framework here could inform a more nuanced guardrail design: rather than a hard floor at 5.5%, a soft penalty function that accelerates delevering as drawdown deepens. The propfirm canonical config in `Portfolio/risk/propfirm_canonical.py` models the drawdown-barrier problem for propfirm challenge simulation — this paper's recovery nonlinearity analysis is directly relevant to the L24 lesson (propfirm pass rate is shape-driven, not scale-invariant). The formula R = 1/(1-D) - 1 is the core insight.

## Extracted content
Recovery formula: "after a drawdown of depth D, the required gain is R = 1/(1-D) - 1." Path-dependent risk management targets the drawdown path directly. "Skew budget" asymmetrically penalizes downside vol. Applied to institutional allocator contexts.

## Action proposed
REFERENCE

Apply the R = 1/(1-D) - 1 recovery formula when calibrating propfirm guardrails in `Portfolio/risk/propfirm_canonical.py`. The nonlinearity is already implicitly captured in the trailing_dd_simulator, but the path-dependent skew budget could improve the soft delevering schedule. Cross-reference with L24 (propfirm pass rate is shape-driven) for the challenge simulation interpretation.
