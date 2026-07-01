# Guardrails Make the Researcher: What an AI Agent Got Right (And Wrong) [Quantpedia]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=1IqcFi1zY8&amp;source=feedburner
**Captured**: 2026-07-01 06:00 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: dc1b6f079884371c8722210b50ddd617

## Summary

Quantpedia describes an experiment where an autonomous research agent was tasked with replicating nine published US-equity anomalies on clean, survivorship-free data, and the write-up focuses less on which anomalies replicated out-of-sample and more on what guardrails the agent needed (and which it lacked) to avoid the usual failure modes of automated quant research — look-ahead bias, survivorship contamination, and overfitting to in-sample specifics. The framing is explicitly about process design for AI-driven research, not about a specific tradeable signal.

## Why it might be useful

This is a direct structural analogue to Algo_claude's own automation: `_automation/feasibility/` runs a 3-level gate (A: IC; B: WF+bootstrap+DSR; C: sanity checks) with handlers dispatched by hypothesis type, and per `_meta/current_focus.md` the ExitRuleHandler and RegimeFilterHandler stubs are still `REQUIRES_HUMAN` — i.e., our own pipeline has known gaps in exactly the kind of automated-research guardrail this article evaluates. Worth reading the full piece specifically to extract which guardrail categories the agent got wrong (the article's stated angle), then diffing that list against the 3-level gate + 4 handlers to see if any failure mode isn't currently covered — e.g., whether "survivorship-free data" is enforced anywhere in the feasibility pipeline's data-loading step, which isn't obviously checked today. Also a natural cross-reference for the AMTP/DSR discipline (CLAUDE.md n_tests=321 ledger) since nine-anomaly replication is itself a multiple-testing exercise the article may or may not have corrected for.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt beyond "replicated nine published US-equity anomalies on clean, survivorship-free data." Full article needed for further extraction (which anomalies, replication rate, and the specific guardrail failures are not in the captured snippet).

## Action proposed

TEST_LATER

No direct fit to an active trading strategy — this validates the research *process* itself rather than a signal. Worth a full read specifically to audit `_automation/feasibility`'s handler stubs (ExitRuleHandler/RegimeFilterHandler still REQUIRES_HUMAN) against whatever guardrail gaps the article identifies, before the next handler gets built out.
