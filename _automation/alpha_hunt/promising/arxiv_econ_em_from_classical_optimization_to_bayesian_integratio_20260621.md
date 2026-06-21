# Survey: Mean-Variance vs Black-Litterman vs Monte Carlo on 10 US Stocks

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.29413
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: eb1e05f766ea9020e77591469c6a7acb

## Summary
A comparative study of six portfolio construction approaches on 10 US stocks (TSLA, WMT, BAC, GS, LLY, MRK, GOOG, META, AAPL, XOM) over September 2023 – December 2025. Methods compared: unconstrained mean-variance, constrained MV, Fama-French 5-factor regression, Monte Carlo MV, and Black-Litterman. Main findings: unconstrained MV produces concentrated portfolios; constrained MV changes the efficient frontier shape; FF5 reveals defensive/large-value/profitability exposure; BL produces more economically intuitive and stable allocations vs raw MV.

## Why it might be useful
The sample (N=10 stocks, 2 years, 2023-2025) is very small — making any conclusions statistically fragile. The BL "more stable" finding is already widely known and our portfolio methodology (ERC in `Portfolio/risk/propfirm_canonical.py`) avoids BL's view-specification problem by using equal risk contributions. For the A+B book (N=2 strategies), all of these frameworks reduce to simple two-asset optimization — the ERC approach in propfirm_canonical.py is already appropriate. Not novel relative to existing methodology.

## Extracted content
"Standard optimization may result in highly concentrated portfolios, while constrained optimization leads to changes in portfolio allocations by altering the efficient frontier, five factor regression models suggest that a basic investment style of defensive large value and profitability exposure, Monte Carlo approximation is a viable technique to arrive at mean-variance optimal portfolios provided the simulations are high enough especially under a box constraint, the Black Litterman portfolio approach produces more economically intuitive allocations and greater stability compared to standard mean-variance optimization."

No code in excerpt.

## Action proposed
REFERENCE

Survey paper on standard portfolio methods, too small a sample to be informative. Methodology already more sophisticated in our current framework.
