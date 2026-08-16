# Are 0DTE Straddles Overpriced? We Tested 193 SPY Sessions (2022-2026)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=QmWIYbWLAl&amp;source=feedburner
**Captured**: 2026-07-22 06:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: ac818105bb82f72c9b1186e3960bcbc2

## Summary
The post ("Flash Alpha" series) asks whether SPY 0DTE straddles are systematically
overpriced — i.e. whether implied vol embedded in same-day-expiry option premiums exceeds
realized intraday moves often enough to make short-straddle selling a persistent edge. It
frames this as one of the most contested questions in options trading since 0DTE expiries
came to dominate SPY volume, and backs the discussion with an empirical test across 193
SPY sessions from 2022 to 2026. The excerpt cuts off before stating the actual answer or
effect size.

## Why it might be useful
This is a volatility risk premium (VRP) question, which directly overlaps the repo's own
open "VRP short gamma" active-research thread (currently listed with empty bootstraps in
Research history) — a positive finding here would be a candidate mechanism or at least a
cross-check dataset/date-range for that hypothesis. It is also a natural target for the
_automation/feasibility gate-A IC test (does realized-vs-implied spread on 0DTE SPY show a
statistically robust edge net of bid-ask) and, if pursued, would need HAC lag-6 and a
walk-forward ≥5 folds rather than the single 193-session sample implied here, plus a
two-sided check per L25 given how thin premium-selling edges usually are once assignment
and pin risk are priced in.

## Extracted content
The author claims a sample of 193 SPY sessions (2022-2026) was tested; no Sharpe, edge size,
or formula is given in the excerpt. No code or formulas present.

## Action proposed
TEST_LATER — options (0DTE SPY) data is not part of this repo's local/VPS data sources
(equities options are absent from the Binance/HL/Databento/deep_history_utc inventory), so
sourcing and validating a dataset is a multi-day prerequisite before any IC test can run.
