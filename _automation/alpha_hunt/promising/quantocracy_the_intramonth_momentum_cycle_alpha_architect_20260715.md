# The Intramonth Momentum Cycle

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=algGtwbujf&amp;source=feedburner
**Captured**: 2026-07-15 07:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: dd656ed67ab980239240ce8c6d349743

## Summary
Alpha Architect's post revisits cross-sectional momentum — one of the most persistent
equity anomalies over three decades — but argues that its strength is not uniform across
the calendar month; it proposes an "intramonth cycle" where momentum returns concentrate in
particular days-of-month rather than being spread evenly. Standard explanations (investor
psychology, delayed information diffusion) are cited as insufficient to explain this
timing pattern. The excerpt ends before describing which days of the month show the effect
or its magnitude.

## Why it might be useful
This is conceptually adjacent to two things already in the repo: Strategy A's TSMOM signal
(a momentum strategy whose live Sharpe of 0.566 is thin enough that any day-of-month timing
refinement would be worth screening), and lesson L58's finding that ZN futures carry a real
day-of-month seasonality (days 16-20, t=-3.38) discovered via a placebo-vs-unconditional
check — the same "which days of the month actually carry the return" question this post is
asking for equity momentum. If the article specifies which calendar days concentrate the
momentum effect, that would be a candidate cheap addition to test on Strategy A's crypto
momentum signal (does BTC/ETH/SOL TSMOM performance cluster by day-of-month in the same
way), following the L58 protocol of checking the pooled mean against the unconditional
expectation before trusting any calendar-conditioned subset.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — the specific day-of-month pattern isn't stated in the excerpt, and testing it
against Strategy A's crypto universe (rather than the equities it was found on) requires
pulling the full article's exact day-of-month definition plus a fresh IC/HAC test on
existing BTC/ETH/SOL data, a same-day-but-not-immediate task given other priorities.
