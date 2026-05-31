# Multi-Regime Markov-Switching Models with Time-Varying Transition Probabilities: U.S. Treasury Yields

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.14976v1
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 4e5f586d9d58b80febabfeb7d1be662a

## Summary
The paper extends the two-regime, common-variance GAS-TVTP framework (Bazzi et al. 2017) to the general K-regime case with regime-specific means and variances. An open-source R package (`multiregimeTVTP`) is released for simulation and estimation. A key empirical finding in Monte Carlo work is that one-step point forecasts are robust to TVTP misspecification, but filtered regime probabilities are sensitive to the specified form — so the choice of transition probability driver matters most for regime characterization, not short-horizon forecasting. Applied to US Treasury yields at four maturities (1961-2024), the lagged yield level as exogenous driver dominates constant and lagged-change specifications; the GAS score-driven specification fails to converge (identifiability issue).

## Why it might be useful
The K-regime TVTP Markov-switching framework is a technically rigorous variant of the HMM approach being evaluated for Strategy D (D3+D5 portfolio, active research, 0/3 modifications consumed). Unlike the fixed-transition-probability HMMs in the quantinsti and arxiv items also in this run, TVTP models allow the probability of transitioning between regimes to itself depend on economic drivers — for NQ intraday strategies, a plausible driver would be the 5-day realized vol relative to 28-day realized vol. The identifiability failure of the GAS specification documented here is a direct implementation warning: don't use the GAS driver for the NQ TVTP regime filter without testing identifiability first. The open-source R package is an accessible entry point if Strategy D regime research eventually adopts a TVTP model. Complementary to the HMM items in this run.

## Extracted content
Key finding from abstract: "One-step point forecasts are remarkably robust to TVTP misspecification, but filtered regime probabilities are not." GAS specification failed to converge in empirical application due to "a ridge in the joint likelihood surface (σ², A)." The R package `multiregimeTVTP` is publicly available.

## Action proposed
REFERENCE — Technically relevant companion to the HMM regime filter work for Strategy D, but requires R (not Python) and is more complex than needed at the current research stage. Read after the simpler HMM variant has been prototyped and tested on NQ data.
