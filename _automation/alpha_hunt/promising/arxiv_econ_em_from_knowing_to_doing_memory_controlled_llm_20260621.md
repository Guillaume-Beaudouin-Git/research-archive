# Memory-Controlled Benchmark for Isolating Genuine LLM Trading Reasoning from Memorization

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.28359
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: df195fabe7dd0952f9500a62d16a76d0

## Summary
LLM-based trading agent evaluations are contaminated by two failure modes: knowledge cutoff overlap (memorized prices, tickers, market narratives substituting for actual reasoning) and raw-return inflation from market drift. This paper introduces a benchmark that randomizes ticker names and dates to prevent memorization from masquerading as skill, and proposes excess-return metrics adjusted for market drift to separate genuine stock-selection alpha from passive exposure. The paper does not report strategy-level Sharpe ratios but argues that most existing LLM trading evaluations are methodologically invalid due to these two issues.

## Why it might be useful
This paper's excess-return methodology critique directly validates the mandatory excess-return requirement in CLAUDE.md (HAC lag-6, subtract daily RF from FRED DTB3). For the automation pipeline at `_automation/alpha_hunt/`, if LLM-assisted feasibility analysis or alpha candidate triage ever incorporated LLM market predictions rather than pure signal testing, the memorization contamination identified here would be a hard failure mode. More concretely, the AgenticAITA paper (id=2605.12532) in this same batch reports Sharpe=1.3 on S&P 500 2022-2024 without this control—the memory-controlled benchmark provides the exact methodological critique to apply when evaluating whether that result is genuine.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Methodology critique paper; no direct test path, but provides essential framework for evaluating any LLM-based trading claim including others in this batch.
