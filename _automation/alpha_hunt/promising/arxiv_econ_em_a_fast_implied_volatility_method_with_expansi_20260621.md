# Fast Closed-Form Implied Volatility Solver via Regime-Split Black-Scholes Expansions

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.10245
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: e4b8a6d1c26535bad987f19103fda41f

## Summary
This paper presents a Black-Scholes implied volatility solver that uses fully closed-form analytical expressions as initial seeds for Newton iteration, derived from asymptotic structure of the BS price in different moneyness regimes. At-the-money, a fourth-order seed from series reversion of an exact Gaussian identity achieves O(s^8) error. In moderate out-of-the-money regions, successive CDF approximations yield explicit seeds of increasing accuracy. The combined method achieves machine-precision IV computation in fewer Newton iterations than prior approaches, enabling fast vol surface calibration.

## Why it might be useful
Fast IV computation is a prerequisite for any real-time options-based regime filter, which is relevant to the VRP research track in `Crypto/research/active/vrp_short_gamma/` if that track is ever reopened (it is currently blocked by L13 cost kill), and to any FTMO-targeted strategy using options-quoted instruments. More immediately, the regime-split approach (different analytical seeds for different moneyness regions) mirrors the regime-conditional testing structure being explored in Strategy D (`Futures/research/active/strategy_d/hypotheses_preregistered.md`): treating ATM and OTM regimes as structurally different is a general principle that could inform how D3 and D5 define their signal domains. This is primarily a computational methods paper rather than an alpha source.

## Extracted content
Technical claim: ATM seed achieves error O(s^8) from fourth-order series reversion. Method achieves machine-precision IV in fewer Newton iterations than prior approaches.

## Action proposed
REFERENCE

Computational IV solver; no options trading in current pipeline. File for potential future options infrastructure.
