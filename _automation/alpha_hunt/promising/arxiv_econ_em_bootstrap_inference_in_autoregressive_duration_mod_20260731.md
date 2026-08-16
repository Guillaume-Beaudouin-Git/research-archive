# Bootstrap inference in autoregressive duration models

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.28294v1
**Captured**: 2026-07-31 01:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 41ce19a13ac5bbedd8f2347e7065b763

## Summary
Develops bootstrap-based confidence intervals for autoregressive conditional duration (ACD) models when the number of observed durations over a fixed calendar window is itself random. Shows the fixed-count bootstrap is consistent when the duration tail index kappa >= 1, and even under heavier tails (0 < kappa < 1), where the estimator has a non-standard mixed-normal limit, the bootstrap still recovers the Gaussian component so percentile intervals and bootstrap t-statistics stay valid. Monte Carlo results confirm accurate finite-sample coverage across both regimes and robustness to non-exponential duration innovations. The empirical illustration applies the method to cryptocurrency ETF transaction durations, finding strong persistence in trade timing and a material difference between conditioning on calendar time versus event count.

## Why it might be useful
Ties directly to the methodology toolkit's block-bootstrap requirement (Politis-Romano, iid forbidden when trade clusters exist): this is a bootstrap-validity result for duration/point-process data with fat tails, structurally the same family of problem the project already treats carefully via HAC lag-6 and block bootstrap. Concretely relevant to Strategy A/B's event-driven diagnostics — L12/L12b (event caps and HAC deflation under fat tails / long half-life) and L59 (delay+1 exit re-pricing) both hinge on correctly characterizing the tail/duration distribution before trusting a bootstrap CI. Second link: Strategy B's funding-carry rotation is itself a duration-like process (time between rebalance/funding events), currently blocked on WF < 5 folds; before any future bootstrap claim on B's 8h rotation, estimating the duration tail index kappa on inter-event gaps (per this paper's kappa >= 1 threshold) would sanity-check whether a standard block bootstrap is even valid there.

## Extracted content
No code in excerpt. Claims: duration tail-index threshold (kappa >= 1 for classical consistency); no numeric Sharpe/performance claims — this is a pure statistics/inference paper, not a trading strategy.

## Action proposed
TEST_LATER — implementing a kappa (tail-index) diagnostic for HL funding-event durations is roughly a half-day task but has no immediate P&L payoff; it hardens the methodology for Strategy B's currently-blocked WF/bootstrap claim rather than unblocking it directly, so it is not urgent until B's WF>=5-folds hurdle is otherwise addressed.
