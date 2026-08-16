# Vector Search As Nearest Neighbor Matching: RAG-based Policy Learning in Causal Inference

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.18225v1
**Captured**: 2026-07-21 03:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: d96f8455c83e23d9f726db617dc93a82

## Summary
Formalizes retrieval-augmented-generation (RAG) based decision-making as a form of nearest-neighbor matching in causal inference: a two-step method retrieves action-specific similar past cases via vector search, a generator estimates the expected outcome or contrast for each candidate action, and a plug-in rule picks the best one; a one-step variant is evaluated directly as a policy since its internal computation is unobservable. Decomposes the resulting regret into a candidate-generation component and a within-candidate choice component, bounding the latter using existing nearest-neighbor/transformer prediction-error guarantees.

## Why it might be useful
Directly relevant to this repo's own `_automation/alpha_hunt/` and `_automation/feasibility/` infrastructure, which is effectively a RAG-adjacent pipeline (an LLM screening/staging items, deduped via `_seen.json`, then triaged into TEST_NOW/TEST_LATER/REFERENCE) — the paper's regret decomposition (candidate-generation regret versus within-candidate choice regret) maps cleanly onto that pipeline's two failure modes: missing a genuinely useful paper at the L0/L1/L2 filtering stage (candidate-generation regret) versus mis-triaging a correctly-surfaced paper (choice regret, the exact task this document performs). Second link: the nearest-neighbor-matching framing formally justifies a dedup/similarity check on `_seen.json` beyond exact-hash matching (catching near-duplicate papers across arXiv versions, like the Kyle-model and "Optimizing Regret" duplicates found in this very batch) — currently `_seen.json` only dedupes by exact content hash.

## Extracted content
No code. No finance-specific numeric claims (pure methodology/regret-bound paper).

## Action proposed
TEST_LATER — the near-duplicate-detection idea (nearest-neighbor matching on title/abstract embeddings rather than exact hash) is a concrete, cheap improvement to `process_raw_filter.py`'s dedup step, motivated by this run finding 3 exact-duplicate-paper pairs (different arXiv versions) that consumed staging slots; worth a follow-up PR to `_automation/alpha_hunt/`, not urgent.
