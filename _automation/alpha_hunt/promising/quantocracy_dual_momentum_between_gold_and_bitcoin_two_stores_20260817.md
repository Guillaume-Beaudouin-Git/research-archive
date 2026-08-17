# Dual Momentum Between Gold and Bitcoin (Two Stores of Value) [Aligrithm]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=XMiAX7eUTv&source=feedburner
**Captured**: 2026-08-17 06:30 UTC
**Filters passed**: L1=[trading_topic, metrics], L2_OK
**Hash**: b9b9caad06f0afe09410fb870bd36c5d

## Summary
The article covers a binary dual-momentum switching strategy between GLD (gold ETF) and IBIT (spot bitcoin ETF), rebalanced every 8 weeks, holding whichever of the two "store of value" assets had stronger recent momentum. The author cites a Quantpedia note (Vojtko and Dujava, covering the period since end-2024) reporting a headline annualized return near 80% at a Sharpe of 1.64. The framing treats gold and bitcoin as two competing stores-of-value and the switch as a simple relative-momentum allocator between them rather than a market-neutral or hedged construction.

## Why it might be useful
This lands directly on two open threads. First, it's a candidate diversifying sleeve for the book, which is currently described in CLAUDE.md as structurally MONO (book de référence = A seul, SR 0.57) — the registre-L finding is that a low-correlation sleeve raises p(pass) and shortens median duration even at modest solo Sharpe (flat-filling sleeve example: solo SR 0.62, ρ≈0 → Δp(pass) +0.05, Δduration -12j), so a gold/bitcoin switch is worth pricing on that criterion (Δp(pass)/Δduration via `Portfolio/admission/marginal.py`), not on raw Sharpe. Second, and more urgently, the headline number itself needs a correctness check before it's trusted at all: an 8-week rebalance frequency should be annualized at √(52/8)≈√6.5 per year, not the naive √52 (L47: "un edge hebdo s'annualise en √52, √252 gonfle le Sharpe ×2.2" — the same inflation risk applies one level up whenever the *rebalance* period, not the *observation* period, is conflated with the annualization base). A binary two-asset switch is also outside the N≥30 cross-sectional rule (L6) by construction, so it should be judged as a directional timing strategy, not benchmarked against cross-sectional Sharpe norms. Both BTC data (Binance daily klines, already canonical) and gold futures (`GC=F` via yfinance, already listed as a data source) are available locally with no new infra.

## Extracted content
The author claims an annualized return of "79.91% a year at a Sharpe of 1.64" for the 8-week GLD/IBIT dual-momentum switch, attributed to a Quantpedia note by Vojtko and Dujava covering the period starting 31 December (year unspecified in the excerpt, presumably 2024).

## Action proposed
TEST_NOW — data for both legs is already local/available with zero new infrastructure, implementation is a same-day job (simple 8-week lookback momentum switch, two series), and it directly serves the portfolio's stated diversification gap. Priority is to first re-derive the Sharpe with correct annualization (L47) and realistic crypto/ETF round-trip costs before citing the 1.64 figure — a claim this far above the L21 "day-trade/CS academic" Sharpe bands (>2× → audit DSR/cherry-pick) warrants direct verification rather than a later slot.
