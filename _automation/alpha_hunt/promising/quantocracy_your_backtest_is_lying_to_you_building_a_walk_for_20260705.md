# Your Backtest Is Lying to You: Building a Walk-Forward Validation Harness in Python

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=SomsaTK8Nc&amp;source=feedburner
**Captured**: 2026-07-05 06:30 UTC
**Filters passed**: L1=[trading_topic, code_quant, methodology], L2_OK
**Hash**: aa7ea4beab19b621ca694846e670110b

## Summary

The author describes building a stock scanner whose naive backtest reported roughly +40% over two years, then discovering that fixing unspecified bugs (the excerpt cuts off before naming them, but the framing strongly implies lookahead bias or improper train/test separation) collapsed the apparent edge. The piece then walks through constructing a proper walk-forward validation harness in Python meant to catch this class of error before a strategy is trusted. No code or specific numeric before/after results are present in the captured excerpt itself, only the narrative setup.

## Why it might be useful

Directly on-topic for two of this project's hard rules: "Walk-forward ≥5 folds — never single split" and the mandatory expanding-window ≥5-fold methodology in the toolkit. Worth reading the full article to see whether the author's harness implementation offers a reusable pattern (e.g., embargo/purge logic between folds, or a cleaner API) that could be diffed against the existing walk-forward code used across strategies A/B/C and the `Futures/research/active/strategy_d/infra/` pipeline. More concretely, this is a good independent gut-check to run against **sector_hothand_propfirm** (`Equities/research/active/sector_hothand_propfirm/`), which is currently flagged in CLAUDE.md as needing a mandatory audit before promotion because of a suspiciously high t_HAC alpha=10.38 — reimplementing that strategy's walk-forward split with a fresh, independently-written harness (rather than re-running the existing one) is exactly the kind of "backtest is lying to you" bug this article is about, and would be a useful cross-check ahead of the required audit.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

TEST_LATER

The excerpt doesn't include the harness code itself, so the full article needs to be read before any comparison to existing walk-forward implementations can happen; pair that read with the already-scheduled sector_hothand_propfirm audit rather than treating it as a separate task.
