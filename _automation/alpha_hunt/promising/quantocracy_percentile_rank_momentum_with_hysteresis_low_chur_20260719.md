# Percentile-Rank Momentum With Hysteresis: Low-Churn Signals

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=px7BLE2OZf&amp;source=feedburner
**Captured**: 2026-07-19 07:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: e09b8ac2a8353d1ca71e49d9290c6e45

## Summary
Aligrithm reviews Landolfi's percentile-rank momentum framework, which reframes classic
momentum not as a raw-return ranking but as a percentile-rank signal combined with
hysteresis bands — the idea being that a position only flips when the rank crosses a wide
enough threshold, rather than re-ranking and rebalancing every period. The stated goal is
reducing portfolio churn/turnover relative to standard rank-momentum rebalancing while
preserving the underlying momentum signal's information content. The excerpt is cut off
before giving the actual hysteresis band width or backtest results.

## Why it might be useful
This maps concretely onto Strategy B's core, currently fatal problem: the live 8-hour
rebalance rotation produces a net Sharpe of roughly -1.55 (0/4 positive WF folds) versus a
backtest built on slow rotation, and the repo's own stated live hypothesis is a slower,
≥10-day holding variant using data already on hand — a percentile-rank-plus-hysteresis
signal is exactly the mechanism that would let a slower, lower-churn rotation be built
without simply widening a fixed rebalance clock, by letting the position hold until the
funding-carry rank moves far enough to justify the switch. It is also relevant to Strategy
A's tanh-based signal, which rebalances daily on HL testnet — a hysteresis band could be
tested as a turnover-reduction modification (one of the ≤3 allowed per hypothesis) before
concluding A's design is exhausted.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — directly relevant to Strategy B's rotation-frequency hypothesis, but adapting
a percentile-rank/hysteresis signal to the funding-carry universe (TST/MEGA/WLD/STX/WIF/
BIO/TRUMP/HMSTR) and re-running the ≥5-fold walk-forward needed to clear the "3 folds is
INADMISSIBLE" gap is a 1-3 day effort, not same-day.
