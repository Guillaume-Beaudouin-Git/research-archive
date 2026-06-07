# Non-Linear Transaction Costs: How Market Impact Curves Reshape Strategy Feasibility

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=kVQ5RW6nT6&source=feedburner
**Captured**: 2026-06-07 06:04 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 9ab72930e42f83cb899dd70f4b98966c

## Summary
Concretum Group explores how transaction costs deviate from a flat round-trip percentage once position size relative to daily volume grows. Rather than a constant cost per trade, execution costs follow a convex curve — small orders trade near the spread, but as size increases, market impact compounds non-linearly and realized slippage exceeds the naive per-trade estimate. The piece is framed around their client-facing strategy research practice, suggesting the non-linear model is production-ready and has been stress-tested across asset classes with different liquidity profiles.

## Why it might be useful
Two direct connections to active strategies: (1) **Strategy C (NQ, Tradeify)** — CLAUDE.md L19 explicitly defers "full non-linear model (OFI + momentum_velocity)" to Topic 3, noting that current sizing_analysis.py uses a 1.5–3× linear stress factor. If this article provides a tractable non-linear impact formula, it could replace the placeholder and sharpen the conservative bound for MNQ sizing. The current 4-MNQ sizing sits near the consistency cap ($628 avg winner > $600 cap) — a calibrated non-linear model could justify a 3-MNQ position that avoids the cap while improving p(pass) in the trailing_dd_simulator.py runs. (2) **L12 cost ceiling gate** — all future crypto delta-neutral feasibility gates (including the archived PMR basis at 178%/yr cost drag) were computed assuming linear 0.17% RT. If cost is convex in size, the ceiling at 29 events/yr per position (L12) shifts depending on trade notional. For Strategy B's $50 notional, non-linear effects are negligible; but any mainnet scale-up plan should recompute. Concrete next step: fetch the full article and extract the impact model; if it has a parameter for daily volume participation rate, plug in MNQ values (avg daily volume ~300K contracts, 4 MNQ = 0.0013% participation → likely linear regime, but confirms the assumption).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Fetch the full article and extract the market impact formula. If it's parameterized by participation rate, run a quick sanity check against current Strategy C sizing (4 MNQ, ~$430 notional, avg NQ volume). One half-day task. Blocked only by needing to read the full post.
