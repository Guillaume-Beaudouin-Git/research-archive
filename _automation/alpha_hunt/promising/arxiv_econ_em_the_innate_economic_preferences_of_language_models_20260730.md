# The Innate Economic Preferences of Language Models

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.26288v1
**Captured**: 2026-07-30 01:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: c908f10cf81a967b8f4debafb6582b93

## Summary
Shows that an LLM's next-token generation rule is mathematically isomorphic to the random-utility model used in discrete-choice economics, so the model's internal logit scores can be used to structurally identify its "economic preferences." Estimating risk attitudes across twelve LLMs on a portfolio-choice task finds universal but heterogeneous risk aversion; models reject strictly dominated options but violate invariance and independence-of-irrelevant-alternatives across prompt framings, and fine-tuning can explicitly engineer a target risk attitude.

## Why it might be useful
Directly relevant to this repo's own `_automation/` infrastructure, which is itself an LLM making resource-allocation-adjacent decisions (which papers to stage, which strategies to greenlight for testing) — the finding that LLMs have measurable but framing-unstable preferences ("violate invariance... across prompt variations") is a concrete reason to distrust any implicit risk-attitude the alpha_hunt/feasibility pipeline might be injecting into TEST_NOW/TEST_LATER/REFERENCE triage decisions (like the ones this very document is making) based on prompt wording rather than underlying evidence — a candidate check is re-running the same staged item through the classification prompt with reworded but semantically identical framing and confirming the action label does not flip. Second link: the fine-tuning-can-engineer-risk-attitude result is a caution for any future idea to use an LLM directly as a position-sizing or regime-classification component in a live strategy (none currently do) — the "preference" would be an artifact of training, not a market signal.

## Extracted content
No code/formulas. No finance numeric claims beyond qualitative "universal but heterogeneous risk aversion" across twelve models.

## Action proposed
REFERENCE.
