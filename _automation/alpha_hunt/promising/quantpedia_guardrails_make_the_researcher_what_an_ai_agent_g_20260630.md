# Guardrails Make the Researcher: What an AI Agent Got Right (and Wrong) Replicating Nine Equity Anomalies

**Source**: quantpedia
**URL**: https://quantpedia.com/guardrails-make-the-researcher-what-an-ai-agent-got-right-and-wrong-replicating-nine-equity-anomalies/
**Captured**: 2026-06-30 13:00 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 4f4b6471ecc06a31eac8c2f9a651d66f

## Summary

An autonomous AI agent was given the task of replicating nine published US equity anomalies using clean, survivorship-bias-free data. The central finding is that out-of-sample decay is not the exception but the norm: on a faithful, rigorous reconstruction, none of the nine anomalies survived. The sole apparent survivor was ultimately traced to a construction error — one that the agent's procedural guardrails caught before it could be reported as a positive result. The takeaway is that what determines trustworthy AI-assisted research is not the model's capability but the discipline of the pipeline around it: data hygiene, test-design rules, and honest failure criteria.

## Why it might be useful

This piece directly validates the aggressive gate architecture in `_automation/feasibility/` — our 3-level pipeline (IC → WF+bootstrap+DSR → sanity checks) is doing exactly what the article argues for: structured guardrails prevent the agent from promoting construction artifacts. The "none survive on faithful build" finding is external confirmation of our AMTP stance when n_tests > 1 and our DSR requirement when n_mod ≥ 2 (L20). More concretely, the audit flag on **sector_hothand_propfirm** (t_HAC=10.38 flagged as red flag in `_audit/sector_hothand_audit_2026-05-30.md`) maps exactly to the article's "apparent survivor was a construction error" scenario — the specific guardrail to run there is a survivorship-bias check and a no-lookahead verification on the sector rotation signal before any propfirm consideration. The article also reinforces L46 (honesty checklist: canonical ledger + frozen spec + measured real cost + full-sample regime), since every sign-flip in our FTMO arc was traced to one of those four being violated.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

REFERENCE — methodology validation without a direct test path. The most actionable use is as a checklist anchor for the pending `sector_hothand_propfirm` audit: apply the article's guardrail framework (survivorship, lookahead, multiple-testing) systematically before the strategy can be promoted beyond the RESEARCH_PASS gate.
