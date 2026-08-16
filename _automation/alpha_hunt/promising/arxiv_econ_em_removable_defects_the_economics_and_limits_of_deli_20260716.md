# Removable Defects: The Economics and Limits of Deliberate Deficiency

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.11983v2
**Captured**: 2026-07-16 01:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: a13aba685d3e7270148f75f284f1b311

## Summary
Formalizes when a "specialist" (a model/agent/system) should deliberately keep a blind spot rather than fix it, treating the deficiency as a design variable that pays off on average but is routed to a compensating channel ("detector") in the rare case it would be fatal. Derives conditions for when this "removable defect" strategy earns a positive premium versus when a confounded detector earns zero premium and even destroys long-run growth under repeated (multiplicative) exposure, drawing on selective prediction, reject-option classification, and Kelly-criterion ruin theory.

## Why it might be useful
Conceptually close to the project's own guardrail architecture — Strategy A/C's kill-switches and consistency caps are exactly a "detector routed to a compensation channel" (halt trading) rather than fixing the underlying blind spot (e.g., beta-dominance in long-only crypto per L11), and the paper's Kelly-ruin argument formalizes why a confounded/uninformative detector can make things worse than no guardrail at all — directly relevant to L54's finding that the MONO book's regime overlay failed because its "detector" (a vol-based regime flag) was informative about variance but not about the mean. Second link: the framework's costly-state-verification lens is a formal way to think about when it is worth paying for a "detector" (a propfirm evaluation gate) versus self-insuring (trading the personal account directly, per L53).

## Extracted content
No code. Formula stated qualitatively (not numerically) — "a defect is profitably removable iff the detector-relevant distinction survives the restriction and the advantage condition holds." No Sharpe/numeric trading claims (pure theory).

## Action proposed
REFERENCE.
