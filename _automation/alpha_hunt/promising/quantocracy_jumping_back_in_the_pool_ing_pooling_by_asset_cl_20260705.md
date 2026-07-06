# Pooling by Asset Class and Portfolio Weight Distance

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=HypILkqGTw&amp;source=feedburner
**Captured**: 2026-07-05 06:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 7099691354c7487705688144d36a5dcc

## Summary

This is post #10 in the "Investment Idiocy" author's ongoing 2026 series on portfolio optimisation, and the excerpt is a recap rather than new content — it references prior posts without restating their conclusions in the captured text. The general thread of the series (based on the title) is grouping instruments first by asset class, then by a distance metric on portfolio weights, before applying a risk-allocation method — i.e. clustering correlated exposures into groups before allocating risk across groups rather than across raw instruments. No numeric results are present in the excerpt.

## Why it might be useful

Same author/series as the previously-accepted item `quantpedia_why_most_portfolios_are_under_diversified_20260619.md`, which was tied to the **A+B book construction** decision (SR 2.31, ERC 50/50 by risk-units, per `_audit/portfolio_recalc_2026-06-10.md`) and to sizing a future **Strategy D** allocation once it clears the SR(book+D) > 2.54 gate. This post continues the same clustering-before-allocating logic and reinforces the same actionable point: the current two-asset ERC has no cluster structure to test yet (only A and B are live), but the **Commodities XS basis+TSMOM** research (`Commodities/research/active/xs_basis_tsmom/`, 24 continuous contracts) is exactly the kind of universe where "pool by asset class first" matters, since S_TSMOM and S_BASIS both risk loading on the same energy/metals cluster if allocated instrument-by-instrument. No new action beyond what the earlier item already flagged — this is confirmation the author's framework is still being developed, not new methodology.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

REFERENCE

Background/continuation of an already-tracked portfolio-construction series with no new numeric or methodological content in this specific post; revisit the series once Commodities XS or Strategy D reach a stage with ≥3 return series to actually cluster.
