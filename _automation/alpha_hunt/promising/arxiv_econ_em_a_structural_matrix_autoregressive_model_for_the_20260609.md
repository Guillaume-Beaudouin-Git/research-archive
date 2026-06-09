# Joint Volume-Volatility-Returns Dynamics in DJIA: Volatility Dominates, Cross-Asset Spillovers Dominate Long Horizons

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.08141v1
**Captured**: 2026-06-09 06:04 UTC
**Filters passed**: L1=[methodology, macro_trading], L2_OK
**Hash**: 78b07276f5a13b60ff2859f62e83331c

## Summary
A structural VAR framework (SMAR) jointly models daily returns, realized volatility, and trading volume for all 30 DJIA constituents over 2021-2025. Identification uses restrictions from the Mixture of Distributions Hypothesis and efficient market theory. The main empirical findings: volatility is the dominant driver of trading volume (not returns), which implies that information arrival manifests primarily as price uncertainty rather than directional flow. At short horizons, own-asset shocks dominate volume, but at longer horizons, cross-asset volatility spillovers account for over half of volume variance. An event study around FOMC announcement days shows a sharp spike in the "informative" component of volume followed by rapid mean reversion, consistent with fast incorporation of monetary policy surprises.

## Why it might be useful
Two concrete links. First, Strategy C (NQ ORB, `Futures/live/strategy_c_live/`): the FOMC mean-reversion finding is practically useful — on FOMC announcement days (typically 14:00 ET), volatility and the "informative" volume component spike and then revert quickly. Strategy C's time stop is 12:30 ET, so FOMC days are already partly excluded, but the FOMC calendar should be verified against the signal_engine's existing filters. If there's no explicit FOMC filter and the backtest includes FOMC days without separating them, the WF=78% result could be partially driven by unusually favorable post-FOMC drift. Worth a quick subsample split in `Futures/research/active/nq_intraday/analysis/`. Second, Strategy A (TSMOM vol targeting): the result that volatility is the primary information channel — not returns — is a theoretical backing for why vol-targeted momentum (tanh(cumret/vol)) outperforms equal-weight momentum. No new implementation needed; this is methodological reinforcement.

## Extracted content
No code or specific numeric Sharpe/return claims in the excerpt. The paper reports: "cross-asset spillovers account for more than 50% of trading volume variation at longer horizons" and observes "significant increases in the informative component of trading activity on announcement days followed by rapid mean reversion" for FOMC events.

## Action proposed
REFERENCE
