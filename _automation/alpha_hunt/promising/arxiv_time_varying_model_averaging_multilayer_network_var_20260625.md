# Time-Varying Model Averaging for Multi-Layer Network Vector Autoregressions

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.25292v1
**Captured**: 2026-06-25 01:30 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: c5bf0a2c7a45096e2dd600332cb2163c

## Summary
This paper proposes a framework for large-scale time series where agents interact through multiple network channels simultaneously. Rather than selecting a single network VAR model, it uses penalized model averaging with time-varying weights to combine multiple candidate models whose count can grow with sample size. The theory provides asymptotic optimality and convergence rates for both in-sample and out-of-sample prediction. A practical addition is conformal prediction for locally stationary time series, producing valid prediction bands without distributional assumptions. The empirical application is CPI inflation forecasting using multiple network information sets.

## Why it might be useful
The methodological connection to CLAUDE.md is the archived Network Momentum (GMOM) research: `Multi_Asset/research/archived/network_momentum/` was closed primarily because the equity universe was too small (N < 35 after filtering, graph density = 1.0), not because the network VAR framework itself failed. This paper's multi-layer approach — handling multiple adjacency matrices — is exactly what would be needed to revisit network momentum with multiple network types (e.g., sector adjacency + volatility correlation + return co-movement) simultaneously. However, the L6 constraint (N ≥ 30 instruments minimum) and the cost of expanding the universe remain binding. The conformal prediction band approach is also relevant for any strategy where you need honest uncertainty bounds on signal estimates rather than parametric confidence intervals.

## Extracted content
No code available in the excerpt. The paper develops estimators with asymptotic properties:

> "The asymptotic properties such as asymptotic optimality and convergence rates of the proposed time-varying weight estimation are derived in the contexts of both the in-sample fitting and out-of-sample prediction."

No specific Sharpe or financial performance claims (applied to CPI forecasting, not trading).

## Action proposed
REFERENCE — Network momentum is archived for universe size reasons. Read if reopening that arc with a broader equity universe (N > 35). Conformal prediction bands are a future methodology consideration for any strategy with non-parametric uncertainty requirements.
