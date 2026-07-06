# Silicon vs. Satoshi: Tactical Asset Rotation Between NASDAQ-100 and Bitcoin

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=e0LzSHh76G&amp;source=feedburner
**Captured**: 2026-07-05 06:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: f6f3a0560154268b66160dc090b66f07

## Summary

Originally a Quantpedia piece, this describes a tactical rotation strategy that switches exposure between QQQ (as a NASDAQ-100 proxy) and Bitcoin based on Donchian channel breakouts, with a cash fallback during periods where neither asset is trending ("consolidation"). The excerpt cuts off before stating the test period or performance figures, so no specific Sharpe/return/drawdown numbers are available here — only the mechanism (dual-asset trend rotation with a cash state) and the claim that it was backtested across multiple periods.

## Why it might be useful

This is a direct structural match to **Strategy A** (crypto TSMOM, long-only BTC/ETH/SOL, currently FROZEN since the 2026-05-11 Propr breach). Strategy A's structural ceiling is explicitly a beta-exposure problem (**L11**: long-only CS crypto is β-dominated regardless of IC; only escape is delta-neutral execution) combined with a 3% daily DD limit it couldn't survive. The cash-fallback state in this rotation design is worth testing specifically as a **drawdown-mitigation overlay** on Strategy A's existing tanh(cumret/vol) signal — i.e. does routing to cash when BTC is in Donchian "consolidation" reduce the daily/total DD enough to matter for a propfirm-style guardrail (MAX_DAILY_DD=2.8%, MAX_TOTAL_DD=5.5%), rather than expecting it to escape L11 (it won't — the strategy is still long-only in one of two assets at any time, so the beta-dominance conclusion still applies whenever it's in a trending phase). Both legs of the required backtest are cheap: BTC daily klines are already the standard input for Strategy A (Binance), and NASDAQ-100/QQQ daily data is already pulled via yfinance elsewhere in the repo (Equities/Commodities research) — no new data infrastructure needed, and a Donchian breakout + cash-state rotation is a same-day implementation. Frame the test as "does this reduce Strategy A's realized DD," not as a new independent alpha source.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

TEST_NOW

Edge mechanism is simple (Donchian breakout rotation + cash fallback), data for both legs is already available via existing pipelines, implementation is well under a day, and it maps directly onto Strategy A's current unresolved drawdown problem rather than requiring a new strategy slot.
