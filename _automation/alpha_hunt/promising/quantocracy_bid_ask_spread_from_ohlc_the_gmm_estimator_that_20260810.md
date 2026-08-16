# Bid-Ask Spread From OHLC: The GMM Estimator That Beats Roll/CS

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=kpX0m4aFrq&source=feedburner
**Captured**: 2026-08-10 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 2c6d8e6d3b29c470eed88f153bd4e292

## Summary
Aligrithm opens by calling out the common backtesting practice of subtracting "a spread" for transaction costs without ever justifying where that number came from — whether typed as a guess or pulled from a single quoted spread snapshot. The piece then introduces a GMM (generalized method of moments) estimator for recovering the effective bid-ask spread purely from OHLC price data, positioning it as an improvement over the classic Roll (1984) and Corwin-Schultz (CS) high-low spread estimators. The excerpt cuts off before presenting the estimator's formula or its comparative accuracy figures.

## Why it might be useful
This lands directly on an open, explicitly flagged problem in the project's own cost infrastructure: the CLAUDE.md data-sources section states the `deep_history_utc` `spread` column is unusable alone (66-69% null on EURUSD in 2021-2023, underestimates real FTMO round-trip cost by roughly 2.4x where populated) and that two incompatible cost tables currently coexist (`top10_test/framework.py` vs `phase0_rt_cost_bps.csv`), over-penalizing gold by 1.9x and never actually measuring indices (hardcoded 1.2 bps vs a 0.47-0.82 bps cache range). A validated OHLC-only spread estimator that beats Roll/CS is a plausible tool to reconcile or replace both of those ad hoc tables with a single principled measure, and any output would still need to clear the same bar the project already applies to cost estimates before use in gating decisions (e.g. the L43 FX intraday gross/cost_p95 ≥ 1.5 threshold, and the general rule that a backtest calibrated at 2 bps doesn't transfer to a 6-10 bps CFD per L33).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — the excerpt gives no formula or code for the GMM estimator itself, so it can't be implemented yet; the full article is needed to extract the actual estimator before it could replace the flagged Roll/CS-based cost tables (medium effort: implementing and validating a new spread estimator against the existing `phase0_rt_cost_bps.csv`/`COST_AUDIT.md` discrepancy is a multi-day task, not a same-day fix).
