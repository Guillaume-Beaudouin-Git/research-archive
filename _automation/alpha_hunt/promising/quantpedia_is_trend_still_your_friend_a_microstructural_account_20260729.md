# Is Trend Still Your Friend? A Microstructural Account of the Demise of Short-Term Trend-Following

**Source**: quantpedia
**URL**: https://quantpedia.com/is-trend-still-your-friend-a-microstructural-account-of-the-demise-of-short-term-trend-following/
**Captured**: 2026-07-29 17:00 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 0fd77b9bcee25c64a7f07d20b3e19aef

## Summary
The paper studies roughly 100 liquid futures contracts from 1995-2025 and finds that trend-following's well-documented post-2008 performance decline is not uniform across markets: it is driven specifically by volatility-normalized tick size rather than asset class, liquidity, electronification, or crowding. Contracts with small volatility-normalized tick sizes saw trend profits collapse almost entirely after 2008 across all signal horizons, while large-tick contracts retained largely intact trend performance. The authors interpret this as evidence that modern trend portfolios split into two microstructure-driven regimes — a mechanism-based explanation rather than the usual "trend is dead/crowded" narrative.

## Why it might be useful
This gives a concrete, testable filter variable — volatility-normalized tick size — that could be applied to the project's own trend-following work: it's directly relevant to L55 (CS macro momentum, 17 instruments, where FX carries 53% of notional but contributes -7.8% of gross P&L — small-tick FX/CFD instruments may be exactly the "small-tick" regime this paper says trend profits collapsed in) and to the ZN Baltussen research (`Futures/research/active/zn_baltussen/`), since ZN is a large-tick, liquid contract that per this paper's logic should be in the "trend still works" bucket. It also bears on the reopening-policy table: any archived trend/momentum family killed for "mechanical" reasons (gross≈0) could be revisited if the underlying instrument turns out to be small-tick — the paper reframes some kills as vehicle/instrument-selection issues rather than pure signal death, which per the table is only a valid reopening path if the original kill was NOT purely mechanical. Testing this would mean computing tick-size/volatility ratios across the CS macro momentum universe and cross-tabulating against post-2008 trend Sharpe by instrument.

## Extracted content
The paper reports the study covers "approximately 100 liquid futures contracts from 1995 to 2025." No formulas or code are given in the excerpt; the core numeric claim is qualitative ("collapsed almost entirely" vs "largely intact") rather than quantified with a specific Sharpe or t-stat in this excerpt.

## Action proposed
TEST_LATER — requires sourcing/computing tick-size and volatility-normalized tick-size data across the CS macro momentum / ZN Baltussen instrument universe, which is a multi-day data-assembly task before any cross-tabulation against existing trend results.
