# Multi-regime Markov-Switching Models with Time-Varying Transition Probabilities

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.14976
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: cba4b4a2674af73025c7b8b0a8948a5f

## Summary
This paper extends Generalized Autoregressive Score (GAS) Markov-switching models to handle K regimes (not just 2) with regime-specific means, variances, and time-varying transition probabilities driven by lagged variables. The key empirical findings are that regime means/variances are well-recovered but the GAS score coefficient is non-identifiable (ridge in the likelihood surface), and that exogenously-driven TVTP (lagged yield level) dominates constant-probability and lagged-change specifications on U.S. Treasury yields 1961-2024. One-step point forecasts are robust to TVTP misspecification, but filtered regime probabilities are sensitive — so regime characterization requires correct specification. An open-source R package (`multiregimeTVTP`) is provided.

## Why it might be useful
Strategy D (D3 mid-fade + D5 BB squeeze) is currently failing individually, with the regime filter as the main open hypothesis for a viable combination. The TVTP framework is directly relevant: a 3-regime model (trending/choppy/volatile) with exogenous variables (VIX, ATR, volume) as transition drivers maps precisely onto the proposed D3+D5 regime filter. The identifiability warning on the GAS score coefficient is important to pre-register before fitting — it means TVTP with lagged VIX level (exogenous, GAS-free) is the safer specification. Also relevant to ZN Baltussen (`Futures/research/active/zn_baltussen/`) where regime detection for bond momentum is an open question. The R package `multiregimeTVTP` is not our Python stack, but the Monte Carlo simulation results and specification tests can guide a Python statsmodels/PyMC implementation. See also `Futures/research/active/strategy_d/hypotheses_preregistered.md` for the regime filter pre-registration entry.

## Extracted content
"one-step point forecasts are remarkably robust to TVTP misspecification, but filtered regime probabilities are not, so correct specification matters most for characterizing regime dynamics rather than short-horizon forecasting"

"An exogenous specification driven by the lagged yield level dominates the constant and lagged-change models in fit, while the GAS specification fails to converge, with $\hat{A}$ collapsing to zero, reflecting the same identifiability issue observed in simulation."

Open-source R package: `multiregimeTVTP` (on CRAN based on context).

## Action proposed
TEST_LATER

Adapt the exogenous TVTP specification in Python for NQ 1-min data: 3 regimes, lagged ATR-5min or VIX as transition driver. Apply to the D3/D5 regime filter study in `Futures/research/active/strategy_d/`. Cost: 1-2 days (Python port of GAS-free TVTP via statsmodels HMM or PyMC). Pre-register contrast: regime-labeled D3 vs D5 out-of-sample before fitting. LATER because the individual D3/D5 signals need to be re-evaluated first under the current hypothesis set.
