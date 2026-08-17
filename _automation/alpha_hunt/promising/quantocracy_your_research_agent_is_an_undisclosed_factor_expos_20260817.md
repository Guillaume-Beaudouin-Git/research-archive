# Your Research Agent Is an Undisclosed Factor Exposure — And So Is Everyone Else's [Jonathan Kinlay]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=72hlrRiWkl&source=feedburner
**Captured**: 2026-08-17 06:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 3b96b8464e4dbd5334e6da0452e06d57

## Summary
This is a follow-up to an earlier case study by the same author on running alpha research through a team of LLM agents (four roles, instrumented handoffs). The framing here is that using an LLM agent pipeline for research introduces a systematic, correlated bias across every strategy the pipeline touches — effectively an undisclosed "factor" shared by all output, analogous to how every quant shop using the same open-source library or the same academic dataset ends up correlated in ways their individual backtests don't show. The argument is about research-process risk (crowding, correlated blind spots, shared model priors) rather than about a specific trading signal.

## Why it might be useful
This is meta-relevant to this very pipeline: `_automation/alpha_hunt/` and `_automation/feasibility/` are themselves an LLM-agent research pipeline, and the concern the article raises — that an LLM's own priors act as a hidden shared factor across everything it green-lights — is a direct argument for why the n_tests ledger (321 global, `_meta/n_tests_ledger.md`) and AMTP/DSR discipline (L20: DSR mandatory from N_mod≥2) matter even more when ideation itself is LLM-driven, not just when testing multiple variants of one idea. It also connects to L58 (a placebo can fabricate a PASS if its baseline isn't checked against the unconditional expectation) — the same "process correlated with itself" failure mode, just at the ideation stage instead of the validation stage. No trading signal to test; this is a process-risk argument to keep in mind when this pipeline (or the feasibility gate handlers) proposes new hypotheses.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — a methodology/process-risk argument about LLM-driven research pipelines, not a trading signal; useful background for how much weight to give ideas sourced through this same automated pipeline, no direct test to run.
