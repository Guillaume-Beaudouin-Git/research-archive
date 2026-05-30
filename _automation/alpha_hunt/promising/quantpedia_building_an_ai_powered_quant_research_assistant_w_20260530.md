# Building an AI-Powered Quant Research Assistant Using the Quantpedia API

**Source**: quantpedia
**URL**: https://quantpedia.com/building-an-ai-powered-quant-research-assistant-with-quantpedia-api/
**Captured**: 2026-05-30 18:06 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: af1e9a20024583d301d775e82f657e2b

## Summary
Quantpedia describes a workflow pairing its structured strategy database (via official API) with a conversational LLM (ChatGPT, Claude, Cursor) to create a lightweight quant research assistant. The API provides structured access to strategy classifications, equity curves, trading code, and performance metrics. Rather than manually browsing the database, a researcher queries in natural language and the LLM retrieves and summarizes the relevant structured records. This is a workflow-tooling article, not an alpha-generating strategy.

## Why it might be useful
The `_automation/alpha_hunt/` pipeline currently captures Quantpedia items via RSS/HTML scraping, which returns only title snippets with no performance metrics. If the Quantpedia API exposes Sharpe/MaxDD/WF data for each strategy at a free or low-cost tier, it would allow `process_raw_filter.py` to gate on numeric performance instead of keyword matching — e.g., reject if reported Sharpe < 0.7 or MaxDD > -25% (matching RESEARCH_PASS thresholds from CLAUDE.md). Concrete next step: read the full article to determine whether the API has a free tier and what fields are available. If structured metrics are accessible, update `_automation/alpha_hunt/fetch_quantpedia.py` to pull them and add a numeric L0 gate in `process_raw_filter.py`. This would reduce false positives from items like the "Quantpedia Days promotional offer" (ec45aefec16) that currently pass L1 on the `academic_curated` keyword.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — Tooling improvement, not an alpha signal. Worth reading the full article to check API pricing and available fields before deciding whether to integrate into the alpha_hunt pipeline.
