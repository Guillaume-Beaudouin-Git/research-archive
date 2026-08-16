# Bitcoin's Overnight Returns Forecast the VIX

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=yvPq04dQSp&source=feedburner
**Captured**: 2026-08-01 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 26f5778970ba50c0017a0edccc83e871

## Summary
Aligrithm's piece splits Bitcoin's continuous 24-hour trading day into two segments around the US equity market's open/close clock: the "overnight" segment running while US exchanges are shut, and the daytime segment running while they're open. The claimed finding, per the excerpt's framing, is that only the overnight segment of BTC's return carries forecasting power for next-day VIX — the daytime segment does not. This positions BTC's after-hours trading as an information channel about incipient equity-vol moves that trades ahead of the US cash session.

## Why it might be useful
This connects to two concrete project elements. First, Strategy A: its live config (BTC/ETH/SOL, long-only tanh cumret/vol signal) has a recalculated excess Sharpe of only 0.566 with a 95% CI of [-0.50, 1.63] that contains zero — a cross-asset predictor like overnight-BTC-return-to-VIX is a candidate exogenous signal not currently in A's feature set, though it would forecast equity vol rather than crypto returns directly, so it is not a drop-in fix. Second, and more directly, the session-splitting methodology itself is exactly the kind of decomposition L56 warns about: L56 shows that "overnight vs day" splits are only valid when anchored to the correct exchange clock (with DST) rather than UTC, and that naive session boundaries can silently absorb non-tradable gap/halt periods. Before trusting this claim, it would need the L56 falsification check (correlate the effect's winter-vs-summer profile in both UTC and the relevant local clock) applied to the BTC/VIX split.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — would require sourcing VIX data, re-deriving the BTC overnight/day split with correct exchange-clock handling per L56, and an HAC lag-6 regression before any claim is usable; medium cost with no direct fit onto Strategy A's current signal.
