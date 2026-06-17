# The Factor Zoo Has Hundreds of Animals, But Only a Handful of Species

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=ZkGIC3c3Xt&source=feedburner
**Captured**: 2026-06-17 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 4963d7204cf0a33fa37e8b59c45b9ba5

## Summary
A review of recent research arguing that the hundreds of documented equity factors are largely redundant — they cluster into a small number of distinct "species" with different economic mechanisms. Most factors described in the literature are variations on a handful of underlying themes (e.g., value, momentum, quality, low-volatility). The practical implication is that a diversified factor portfolio can be built from a minimal set of orthogonal tilts rather than from hundreds of individually-published signals.

## Why it might be useful
This is directly relevant to the sector_hothand research (`Equities/research/active/sector_hothand_propfirm/`), which is currently sitting with t_HAC alpha = 10.38 — a flag that screams factor collinearity or data-mining. If the sector hothand momentum signal is just another expression of a known momentum "species," then the claimed alpha is really beta to the momentum factor, and the t-stat would deflate significantly after regressing on a standard momentum factor portfolio. Run: identify which "species" the sector rotation signal belongs to, then partial-out that factor before computing the HAC t-stat. This is also relevant for the book-level diversification argument: the A+B portfolio already claims SR 2.31; adding Strategy D requires SR(book+D) > 2.54, which implicitly requires D to be a new "species" not already captured by A or B.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Useful as methodological grounding for the sector_hothand audit. The "species" framing is the right way to think about whether D adds genuine diversification to the A+B book. No new backtest warranted from this item alone.
