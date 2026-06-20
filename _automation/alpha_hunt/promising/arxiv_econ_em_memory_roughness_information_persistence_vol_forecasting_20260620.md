# Memory, Roughness, and Information Persistence: A Structural Approach to Volatility Forecasting

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.24285
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 15f9f6e134070972e86db64c4c2ff104

## Summary
This paper analyzes the joint role of long-memory dynamics, rough-volatility behavior, and persistence-based forecasting on a panel of 115 S&P 500 constituents from November 2001 through April 2026. It combines semiparametric long-memory estimation (fractional integration), rough-volatility diagnostics (Hurst exponent estimation), and structured HAR-type regressions that incorporate persistence-based features. The key finding: for most stocks, volatility exhibits rough behavior (Hurst < 0.5) at high frequency but long memory (d > 0) at daily frequency — these two properties coexist and both contain forecasting information beyond standard HAR.

## Why it might be useful
Strategy A's vol targeting uses a 28-bar rolling standard deviation. This paper shows that for equity-adjacent assets, daily vol exhibits long memory (d > 0 fractional integration) — meaning historical vol observations beyond 28 bars contain forecasting information that is discarded. BTC/ETH/SOL's daily volatility is likely also long-memory (crypto vol has been documented as persistent). The practical question: does replacing the 28-bar rolling vol in `signal.py:13` with an EWMA or HAR specification improve signal quality? Given Strategy A is frozen, this is deferred. But for Strategy D's vol targeting design, the rough-vol + long-memory framework here is the right theoretical basis. The 115-stock panel from 2001–2026 provides robust cross-sectional evidence.

## Extracted content
"Using a panel of 115 S&P500 constituents from November 2001 through April 2026." Semiparametric long-memory estimation + rough-volatility diagnostics. "Volatility exhibits rough behavior (Hurst < 0.5) at high frequency but long memory (d > 0) at daily frequency." HAR-type regressions with persistence features.

## Action proposed
REFERENCE

Reference for Strategy D vol targeting design. When designing the vol estimator for D3/D5, use HARQ specification (as in paper e0de6106) rather than simple rolling std. Cross-reference with Strategy A's `signal.py:13` to check whether a HAR vol estimator would materially differ from 28-bar rolling vol on BTC daily data.
