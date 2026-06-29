# Estimating the Capacity of a Trading Strategy Under Non-Linear Transaction Costs

**Source**: quantocracy (via Concretum Group)
**URL**: https://quantocracy.com/redirect.php?key=3NhyVSWE3f&source=feedburner
**Captured**: 2026-06-29 07:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 6b16af786e0460bd9675b81a0df64d0a

## Summary
This article extends a previous analysis of transaction cost modeling to address the non-linear relationship between trade size and market impact. Conventional backtest frameworks assume linear costs (bps × notional), but real market impact is convex: doubling position size more than doubles cost due to order book depth constraints. The article apparently provides a framework for estimating at what AUM level a strategy's edge is fully consumed by slippage, making it a capacity estimation tool for real deployment decisions.

## Why it might be useful
Concrete connection to L19 (NQ propfirm market impact): the calibrated slippage model used in `Futures/research/active/nq_intraday/sizing_analysis.py` assumed $29 RT for the Databento re-baseline but the non-linear (OFI + momentum_velocity) model was explicitly deferred to Topic 3 in CLAUDE.md. If this article provides a tractable non-linear model, it could fill that gap for any future NQ propfirm re-evaluation. Also relevant to Strategy B (delta-neutral carry on HL testnet): as B scales toward mainnet, understanding the order-book depth constraint on HMSTR notional is critical — the current NOTIONAL_USD=50 is clearly sub-capacity, but the ceiling is unknown. The capacity framework would let you compute the max feasible notional before edge erosion.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — Worth reading in full before the Strategy B mainnet scaling decision (~2026-07-17 target). No immediate test needed.
