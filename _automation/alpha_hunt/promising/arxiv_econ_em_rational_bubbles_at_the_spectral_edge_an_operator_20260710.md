# Rational Bubbles at the Spectral Edge: An Operator-Spectral Theory of Fragility, Identification and Finite-Sample Certification

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.03933v2
**Captured**: 2026-07-10 03:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: f86f90f4a02931545b5a56a48d16fafd

## Summary
Proposes measuring market "fragility" via the strength of the single dominant factor in the cross-sectional covariance structure of returns, defining a "fragility edge" — a discount-rate-calibrated threshold beyond which a rational bubble becomes possible — and showing across eighteen global equity indices (2004-2024) that this dominant-factor strength rises in every documented crisis, with the market's effective number of independent factors collapsing from roughly six to roughly four. The authors are explicit that the measure reliably flags when a crisis-level co-movement regime is being crossed, only roughly whether a bubble exists, and not at all which asset carries it — these are coincident, not predictive, readings.

## Why it might be useful
Directly relevant to the project's guardrail/regime work, with an important caveat baked into the paper itself: the authors state plainly these readings "coincide with crises, not forecasts," exactly the trap L54 identified — a variable that correctly signals elevated systemic risk in real time doesn't automatically make a good regime overlay unless it also predicts the mean in the same direction. Filed as a candidate coincident risk-monitor (a factor-concentration measure computed on the crypto book's own asset covariance, or on the broader risk-asset universe Strategy A/B trade in) for the guardrail stack, explicitly not as a predictive signal — consistent with keeping A's guardrails reactive (MAX_DAILY_DD/MAX_TOTAL_DD) rather than trying to anticipate drawdowns via a forecast that L54 already showed does not help.

## Extracted content
No code/formulas. Numeric claim (author's): the dominant factor's effective count "collaps[es] from about six to about four independent factors" during crises, across 18 global equity indices 2004-2024.

## Action proposed
REFERENCE.
