# Retrieval over Reasoning: A Cost-Controlled Benchmark of LLMs for Energy-Retrofit Recommendation

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.05440v1
**Captured**: 2026-07-08 01:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: c2547deef7b2f96828d0c43c29cb3368

## Summary
The authors study how to recommend energy-conservation measures for NYC buildings from audit records, comparing tree ensembles, neural nets, and LLMs. Two of the four findings generalize beyond the building-energy domain: reframing a multi-label recommendation task as genuine multi-label classification (rather than forcing single-label choice) sharply improves accuracy versus a prior baseline, and across eight LLMs, retrieval-augmented generation improves per-label F1 by 0.11-0.20 while adding explicit reasoning steps produces no measurable accuracy gain at up to 8.4x the cost — retrieval fixes low precision, reasoning doesn't.

## Why it might be useful
This is a domain mismatch — building energy retrofits have no bearing on Algo_claude's trading research, and the L1 "topic_relevance" match is almost certainly a keyword false-positive (likely "cost-controlled benchmark" or "recommendation" triggering the filter) rather than a genuine hit. The one transferable finding is about LLM automation infrastructure, not trading: `_automation/alpha_hunt` and `_automation/feasibility` are Claude-Code-driven pipelines, and if any future handler in `_automation/feasibility/` (SkipMonth, ExitRule, RegimeFilter, Generic) were extended to use an LLM for classification-style judgment calls (e.g., classifying hypothesis type or triaging papers), this paper's result — retrieval grounding beats chain-of-thought reasoning for precision on structured recommendation tasks, at far lower cost — would argue for adding a retrieval step over adding more reasoning tokens. That is speculative and not tied to any current automation gap.

## Extracted content
The paper reports specific numeric claims: gradient-boosted-tree EUI prediction reaches R^2 = 0.757 (stacking ensemble, beating all six neural architectures tested); reframing ECM recommendation as 19-way multi-label classification lifts accuracy from a previously reported 25.9% to micro-F1 = 0.571; RAG improves micro-F1 by +0.11 to +0.20 on every one of eight LLMs tested, while explicit reasoning changes accuracy by only -0.018 to +0.010 at up to 8.4x the cost; a 70B open-weight model with a 15-line nearest-neighbor retrieval step reaches 0.511 micro-F1 at $0.00032/building, ~10.1x cheaper than a comparable frontier model.

## Action proposed
REFERENCE
