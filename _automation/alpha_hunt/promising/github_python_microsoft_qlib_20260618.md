# Microsoft Qlib — AI-Oriented Quantitative Investment Research Platform

**Source**: github_python
**URL**: https://github.com/microsoft/qlib
**Captured**: 2026-06-18 12:00 UTC
**Filters passed**: L1=[code_quant, quant_tool], L2_OK
**Hash**: 6928c71690e44abbbe557a89a594b965

## Summary
Qlib is Microsoft's open-source quantitative investment platform designed around ML-driven research workflows. It covers the full pipeline from data ingestion and feature engineering to model training (supervised, market-dynamics, and reinforcement learning paradigms) and backtesting. A notable recent addition is integration with Microsoft's RD-Agent, which automates the research-development cycle of hypothesis generation and experiment execution. The framework is language-Python and targets lowering the iteration cost of testing diverse ML models on financial time series.

## Why it might be useful
For active Strategy D research (`Futures/research/active/strategy_d/`), Qlib's LightGBM/LSTM pipelines could provide a validated baseline for testing a ML-based regime filter on the D3 or D5 signals — concretely, running a walk-forward classification on the NQ 1-min Databento parquet (`data/raw/NQ_1min_databento_2010-2026.parquet`) to predict morning fade vs continuation. This is a 0-to-backtest path that leverages existing infra rather than building from scratch. The RD-Agent automation loop is also architecturally close to the `_automation/feasibility/` 3-level gate pipeline, and the Qlib codebase may contain reusable patterns for the Generic feasibility handler. Methodologically, Qlib enforces WF evaluation and standardized factor normalization; cross-checking its HAC/evaluation defaults against the mandatory fixes (excess returns, HAC lag-6, daily vol targeting) would be the first thing to verify before trusting any Qlib-generated Sharpe.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full repo needed for further extraction.

## Action proposed
REFERENCE — Qlib is a general-purpose ML-quant toolkit, not an independently tradable edge. No immediate fit to an open strategy test slot (Strategy D budget: 3 mods, 0 consumed — but the pre-registration step comes first). Bookmark for when Strategy D reaches the regime-filter modification phase, or if the `_automation/feasibility/` Generic handler is being redesigned.
