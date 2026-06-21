# Coordination as a Configurable Architectural Layer in Multi-Agent LLM Systems

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.03310
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 0efb21919a6f3a25b611bc497abe2383

## Summary
Multi-agent LLM systems fail in production at rates of 41-87%, mostly due to coordination defects rather than base-model capability. This paper proposes treating coordination as a separable configurable architectural layer—a constraint satisfaction problem over shared state, message routing, and action timing—and maps six coordination patterns (broadcast, token-ring, publish-subscribe, consensus, hierarchical, market-based) to their failure modes under partial observability and asynchrony. The framework provides a principled mapping from coordination configuration to predictable failure-mode signatures, enabling systematic diagnosis rather than ad-hoc fixes.

## Why it might be useful
The `_automation/` pipeline structure (alpha_hunt scraper → feasibility gate → staging) is a multi-component system with coordination between VPS-side processing (`process_raw_filter.py`) and repo-side consumption (`promising/` directory). The 41-87% production failure rate and the coordination-over-capability finding maps directly to the documented issues in the VPS cron setup: the `*/30 * * * *` alpha_hunt fetch cron failure modes (Reddit 429 chronic, distillation on VPS, push limited to `_seen/`+`_staging/`) are coordination failures rather than filter-quality failures. The hierarchical coordination pattern described in the paper may offer a better architecture for the fetch-filter-stage-review pipeline than the current flat cron-based approach. This is a system architecture reference rather than a trading signal paper.

## Extracted content
Specific numeric claim: multi-agent LLM systems fail in production at rates 41-87%, mostly due to coordination defects.

## Action proposed
REFERENCE

System architecture paper for multi-agent LLM coordination; applies to `_automation/` pipeline design but not to trading signal generation. Useful when redesigning the alpha hunt fetch pipeline.
