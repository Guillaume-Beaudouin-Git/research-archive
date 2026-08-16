# GAMLSS/ZAGA: Conditional IR* Distribution For Trading Strategies (Krzysztof Ozimek)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=zjqcaiXNf4&amp;source=feedburner
**Captured**: 2026-07-28 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 7a05f2623c9fc018712395e8e070a659

## Summary
The author challenges the standard practice of summarizing a trading strategy's performance by a single point estimate (e.g. one Sharpe/IR number) and instead proposes modeling the full conditional distribution of that performance metric using GAMLSS (Generalized Additive Models for Location, Scale and Shape) with a ZAGA (zero-adjusted gamma) response distribution. The stated motivation is that a single observational point hides how the metric's distribution shifts with conditioning variables (regime, time, etc.), which a single Sharpe cannot represent. The excerpt is a teaser and stops before the paper's actual model specification, dataset, or results are shown.

## Why it might be useful
This is directly relevant to Strategy A's current uncertainty problem: the live-config Sharpe (0.566, excess-of-RF, BTC/ETH/SOL) has a bootstrap/HAC IC95 of [-0.50, 1.63] that contains zero, which is currently reported only as a single interval rather than a full conditional distribution — a GAMLSS/ZAGA-style model could in principle characterize how that distribution shifts across regimes rather than collapsing it to two numbers. It also connects to the methodology axis of DSR/block-bootstrap already mandated for n_mod>1 hypotheses (L20) and to lesson L21's Sharpe-by-category sanity ranges, which are themselves crude point summaries this approach could refine or replace for `_automation/feasibility` Level B.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — no off-the-shelf GAMLSS implementation exists in the repo's Python stack (statsmodels lacks it; would need a port or R interop), so applying it to Strategy A's excess-return series to refine the existing IC95 estimate is a 1-3 day methodology investment, not a same-day check.
