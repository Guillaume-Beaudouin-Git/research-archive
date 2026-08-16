# Refiner Trade Part 3/3: A Second Signal and the Case for Trading Less (Beyond Passive)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=OdPY90Ozea&source=feedburner
**Captured**: 2026-07-26 06:00 UTC
**Filters passed**: L1=[trading_topic, metrics], L2_OK
**Hash**: 03f39da381be682cae41a8ff803b839a

## Summary
This is the third installment of a three-part series on a strategy the author calls "Refiner Trade." Part 1 (referenced here, and covered separately in this batch as "Refiner Trade: From Gross Sharpe to Net") established a gross Sharpe of roughly 1.5, and part 2 subtracted broker fees and financing/interest costs to derive net performance. This third part reportedly introduces a second signal and argues for trading less frequently, implying that some of the net-Sharpe erosion seen when moving from gross to net is recoverable by lowering trade frequency rather than by improving entries or exits.

## Why it might be useful
This directly parallels L47 (annualize in √(obs/year), not √252 — a lower-frequency edge needs the correct annualization, and trading less frequently changes both the measured Sharpe and the realized cost drag) and L55 (CS macro momentum: slowing to monthly rebalancing cut gross Sharpe from 0.846 to 0.423 while saving only 0.09 pts/yr of swap — i.e. "trade less" is not automatically a win). This item's "case for trading less" claim should be checked against L55's finding that the tradeoff is often unfavorable before treating it as a general prescription. It is also relevant to the active Commodities XS Basis+TSMOM research (`Commodities/research/active/xs_basis_tsmom/`, phase A incomplete), where rebalance frequency and cost drag are still open design choices this series' methodology could inform, if the full article's numbers hold up under HAC lag-6 and walk-forward.

## Extracted content
No code or formulas are present in the excerpt. The author quotes carrying over "a gross Sharpe of about one and a half" from part 1 of the series.

## Action proposed
TEST_LATER — the "second signal + trade less" combination is a plausible design lever but the excerpt gives no net Sharpe, cost assumptions, or instrument universe for part 3, so reading the full article is needed before deciding fit.
