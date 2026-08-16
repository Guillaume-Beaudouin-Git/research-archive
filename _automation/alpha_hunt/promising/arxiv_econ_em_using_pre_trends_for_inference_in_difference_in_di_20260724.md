# Using Pre-Trends for Inference in Difference-in-Differences

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.21312v1
**Captured**: 2026-07-24 01:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: db5379828d1eb373f5a2efdcfb46ca9b

## Summary
Proposes a difference-in-differences inference method that uses the observed pre-treatment outcome trends themselves as the reference distribution for testing the post-treatment DID estimate, related to conformal inference but with a DID-specific predictor. Unlike standard DID inference, this approach does not require the parallel-trends assumption to hold.

## Why it might be useful
Directly relevant to the project's own event-study/calendar-effect research — L42 (pre-FOMC drift), L49 (unlock-drift versus calendar placebo), and L58 (treasury-auction blackout placebo bias) are all effectively DID-style before/after event designs currently relying on either a parallel-trends-style assumption or an explicitly-constructed placebo/matched control. This paper's core idea — calibrate the post-event test against the actual distribution of pre-event trend noise rather than assuming trends would have stayed parallel — is a direct, assumption-light upgrade candidate for any future event-study, sidestepping exactly the kind of placebo-construction pitfall L58 documents (a badly-chosen placebo reference distribution manufacturing a false PASS).

## Extracted content
No code/formulas in excerpt. No numeric claims (methodology paper).

## Action proposed
TEST_LATER — worth adopting as the default inference procedure next time an event-study/calendar hypothesis is tested (replacing the current placebo-matching approach), since it directly addresses the L58 failure mode; not urgent since no new calendar-effect candidate is currently in active research.
