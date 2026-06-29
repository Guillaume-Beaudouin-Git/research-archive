# FX Trend-Following: A Walk-Forward Validation Study Across Three Signal Families

**Source**: quantocracy (via Quant Insti)
**URL**: https://quantocracy.com/redirect.php?key=z3sFSBnGXH&source=feedburner
**Captured**: 2026-06-29 07:00 UTC
**Filters passed**: L1=[trading_topic, methodology], L2_OK
**Hash**: 97618b940bc5a36d482c8f739ebe461d

## Summary
This study tests whether trend-following — a strategy family with multi-decade documented success in futures markets — transfers to spot FX. Three signal architectures are evaluated: time-series momentum (TSMOM), dual moving average crossover, and Donchian channel breakouts. The study uses walk-forward validation to assess OOS robustness, which is the correct methodology per CLAUDE.md (≥5 folds). The TL;DR in the excerpt stops short of revealing the conclusion, but the research question directly addresses the futures-vs-FX transferability gap.

## Why it might be useful
This study maps directly onto the archived FX research in CLAUDE.md: CS momentum and TSMOM G10 are both closed ("dead post-Menkhoff, central bank anchoring"). This Quant Insti study likely reconfirms that finding with updated data, or finds a narrow surviving variant. The walk-forward methodology serves as a template comparison for how CLAUDE.md's 5-fold gate was applied to the same signal family. The main reason to read it in full: (1) check whether any post-2020 subsample shows sign of revival (the archived FX results used older data), and (2) extract the Sharpe/WF statistics to add to the FX trend-following evidence base. If the study finds WF > 60% on any variant, that reopens a targeted test on `data/deep_history_utc/` (true UTC, 2007–2026). Currently, evidence from the archive weighs heavily against it.

## Extracted content
No specific Sharpe, MaxDD, or win-rate figures in the excerpt. Full article needed for the WF pass rates across three signal families.

## Action proposed
REFERENCE — FX TSMOM family is closed in the CLAUDE.md archive. Read the full article to extract WF statistics and confirm or update the closure verdict. No immediate backtest without evidence of post-2020 revival in the full article.
