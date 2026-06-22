# To Cluster Or Not To Cluster: Portfolio Optimization with Hierarchical Grouping

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=CljVC51ULu&source=feedburner
**Captured**: 2026-06-22 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: a38616ed7c41e54986141a85f0d51f2c

## Summary

This is the sixth entry in a multi-part series on portfolio optimization from the Investment Idiocy blog. Prior posts in the series established that naive mean-variance optimization on historical data leads to poor out-of-sample performance, likely due to estimation error in the covariance matrix. This post addresses a specific structural question: does grouping assets into clusters before applying an allocation rule improve robustness, or does the clustering step itself introduce new parameter sensitivity? The argument explores whether hierarchical clustering (e.g., grouping assets by correlation structure before sizing) genuinely reduces concentration risk versus simply redistributing it. The excerpt is too truncated to extract the conclusion or empirical results — the full article is needed for the quantitative findings.

## Why it might be useful

The most direct connection is the A+B book extension problem: the current ERC 50/50 allocation was computed with ρ_AB=0.039, and the CLAUDE.md notes the ERC solver degenerates when B's backtest series contains 92% zeros (`_audit/portfolio_recalc_2026-06-10.md`). When a Strategy D candidate clears RESEARCH_PASS, the question of how to allocate across A, B, D becomes concrete — a clustering approach could determine whether D genuinely adds an independent risk factor before computing its contribution to the SR > 2.54 gate. This article, as part of a systematic series, likely provides code or at least pseudocode for the clustering step. Secondary connection: if Commodities XS (`Commodities/research/active/xs_basis_tsmom/`) reaches Phase B, its 24-contract universe with overlapping TSMOM+BASIS signals loading on energy/metals clusters is exactly the problem this methodology targets. Read the full article to extract the clustering algorithm and any empirical results on realistic out-of-sample universes.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. The description is a blog lead truncated at the introductory framing. Full article needed for further extraction.

## Action proposed

REFERENCE

Useful background for Strategy D portfolio construction once a D candidate clears RESEARCH_PASS, and for Commodities XS allocation design. No immediate test path with the current two-strategy book. Read the full series (6+ posts) before implementing any clustering-based allocation to understand the empirical conclusion — the series may conclude clustering does not help (the title's question format suggests the answer could go either way).
