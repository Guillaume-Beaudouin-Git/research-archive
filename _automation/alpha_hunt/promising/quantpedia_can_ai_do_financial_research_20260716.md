# Can AI Do Financial Research?

**Source**: quantpedia
**URL**: https://quantpedia.com/can-ai-do-financial-research/
**Captured**: 2026-07-16 20:00 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: e6d97d709b51159c9e0ce8770defc040

## Summary
Researchers from Google, Boston College, and Columbia built an LLM-driven "research agent" that operates inside a constrained laboratory: a symbolic vocabulary of 66 accounting primitives plus a standardized backtesting harness. Rather than predicting returns directly from raw data, the agent runs an automated propose-test-reflect loop — forming a hypothesis, testing it through the fixed backtesting pipeline, and revising based on the result — to see whether it converges on signals that are both statistically robust and economically interpretable. The paper's contribution is less a specific trading signal and more a template for mechanizing empirical-finance hypothesis discovery under a controlled, auditable primitive set.

## Why it might be useful
The architecture described — a fixed primitive vocabulary, a standardized backtest, and an automated propose-test-reflect loop — is structurally the same pattern already implemented in this repo's `_automation/feasibility/` pipeline (3-level gate: A=IC, B=WF+bootstrap+DSR, C=sanity) and `_automation/synthesis/` (cross-paper theme tracking). Worth a read specifically for how they bound the hypothesis space (66 primitives) to keep the effective number of tests countable — directly relevant to this repo's AMTP/DSR discipline (L20: DSR mandatory once n_mod>=2), since an LLM freely generating hypotheses without a bounded primitive set would blow out n_tests and deflate every subsequent candidate's DSR. If the feasibility pipeline is ever extended to auto-generate hypotheses rather than just gate human-proposed ones, this paper's primitive-bounding + reflect-loop design is a concrete template to borrow, not just a "portfolio optimization" curiosity.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — informs the design of `_automation/feasibility/` and `_automation/synthesis/` as prior art on bounded-hypothesis-space automated research, but there is no strategy-level test to run from this excerpt.
