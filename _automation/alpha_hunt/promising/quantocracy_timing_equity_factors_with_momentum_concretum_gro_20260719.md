# Timing Equity Factors with Momentum

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=69vi650Jd3&amp;source=feedburner
**Captured**: 2026-07-19 07:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: ad256f3af3c1a4f8bf142e7ec1a80fdd

## Summary
Concretum Group's post is a response/extension to a Man AHL paper ("A Trend Following Deep
Dive: Cash (Equities) Is King", Panjabi/Bordigoni/Buchanan 2026) about applying trend
following overlays specifically to cash equity indices rather than futures. The angle
described is using momentum as a timing signal for equity factor exposures (i.e. rotating
into/out of a factor based on the factor's own trailing trend), rather than as a
standalone directional strategy. The excerpt stops before giving the actual timing rule or
any performance figures.

## Why it might be useful
This is directly comparable to Strategy A's TSMOM design
(`tanh(cumret_28d/(vol_28d*sqrt(28))).clip(lower=0)`, long-only, currently only 0.566
excess Sharpe on the live 3-coin config, IC95 containing zero): the "timing a factor with
its own momentum" framing is exactly Strategy A's mechanism applied to equity factors
instead of crypto assets, so it is a natural beta-orthogonality check per L38 — regress the
described factor-momentum overlay on a vol-targeted buy-and-hold of the underlying factor
and see if R²>30% reveals the same beta-timing-not-alpha pattern already suspected for A.
It could also stress-test whether Strategy A's specific functional form (tanh of a
vol-scaled cumulative return, clipped long-only) is idiosyncratic or a known/replicated
shape in the equity-factor-timing literature, informing whether A's ceiling (L11 long-only
crypto beta-dominance) generalizes.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — equity factor return series (value/quality/momentum long-short factors) are
not part of the repo's crypto/futures/FX data inventory, and this would require sourcing a
factor dataset (e.g. AQR/Ken French) plus 1-3 days to replicate the timing rule and run the
L38 beta-orthogonality regression before it could inform Strategy A's design.
