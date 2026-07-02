# Silicon vs. Satoshi: Tactical Asset Rotation Between NASDAQ-100 and Bitcoin

**Source**: quantpedia
**URL**: https://quantpedia.com/silicon-vs-satoshi-tactical-asset-rotation-between-nasdaq-100-and-bitcoin/
**Captured**: 2026-07-02 14:00 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: addd1b7d0f2374ca47e05a5d6fdec251

## Summary

The article argues that QQQ and Bitcoin compete for the same pool of retail speculative capital, so attention rotates between the two narratives (AI trade vs. crypto breakout) in a way that leaves a detectable price footprint. The proposed implementation uses Donchian channel breakouts on both assets, holding whichever one is trending and stepping into cash when neither is breaking out, rather than staying permanently exposed to either instrument's full drawdown. The authors frame this as harvesting momentum from retail attention flow while avoiding the deepest drawdowns of a buy-and-hold in either asset. No backtest statistics (Sharpe, drawdown, win rate) are given in the excerpt.

## Why it might be useful

This is directly comparable to Strategy A's mechanism, not a new asset class: like TSMOM v3's `tanh(cumret_28d/vol_28d).clip(lower=0)`, this is a long-only trend signal that goes flat (here: to cash) rather than short during non-trending regimes — worth a side-by-side read given Strategy A is frozen since the 2026-05-11 Propr breach and a fresh look at signal alternatives is due. But the framing that switching between QQQ and BTC "avoids remaining permanently exposed to either asset's drawdown profile" should be checked hard against **L11** (long-only CS crypto = β-dominated, port corr_A ≥ 0.80 regardless of IC): rotating into QQQ during BTC's weak stretches doesn't escape long-only beta, it just swaps which beta is held, and QQQ and BTC have been co-moving (both "risk-on tech-adjacent") through most of 2023-2026 — the diversification claim needs an explicit correlation check before it's taken at face value. It also collides with the **A+B book** concern from `_audit/portfolio_recalc_2026-06-10.md`: A is already crypto-beta-heavy, and adding a QQQ/BTC rotation sleeve would raise correlation to broader equity risk-on regimes rather than diversifying the book. If tested at all, it should be as a **quintile-monotonicity / dir-accuracy pre-flight** (per the 5 mandatory script fixes) on the QQQ-BTC pair specifically to check whether the "attention rotation" claim survives HAC-lag-6 significance, before any capital allocation is considered — data for both legs (yfinance QQQ, Binance BTC daily) is already in the repo's existing data pipeline.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

TEST_LATER

No immediate fit to A/B/C as a modification (it's a new two-asset rotation hypothesis, not a tweak to an existing signal), and the core long-only switching mechanism likely collides with L11's β-dominance finding — worth a cheap IC/correlation pre-flight before committing real backtest time, not immediate work.
