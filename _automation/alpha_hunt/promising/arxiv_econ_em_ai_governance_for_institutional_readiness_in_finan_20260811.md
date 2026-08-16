# AI Governance for Institutional Readiness in Finance

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2608.02311v2
**Captured**: 2026-08-11 04:00 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: d09f33d8bd829a9956eb93130348309f

## Summary
Revised version of the same governance-framework paper as 5c91323c1ed4975430a1568fc2eabf4a (filed elsewhere in this batch, captured 2026-08-04), adding two further real-world case studies to ground the four-layer (Policy/Engineering/Composition/Systemic) framework: a $45 billion discretionary fund's forced-deleveraging blowup, and a tribunal ruling holding an airline liable for its customer-service chatbot's statements. Keeps the same computable diagnostics (regret-covariance drift monitor; crowding-driven joint-drawdown simulation rising from 39.2% to 79.3%) but now explicitly separates "synthetic, calibrated illustrations" from "real, documented cases" as two distinct evidence types.

## Why it might be useful
Same core relevance as the earlier version filed in this batch — the regret-covariance drift monitor remains a candidate lightweight check for `_automation/feasibility/`'s own agentic pipeline. The added case study is the more useful addition: a $45B fund's forced-deleveraging blowup is directly on-theme with this project's guardrail discipline (MAX_DAILY_DD/MAX_TOTAL_DD enforcement in Strategy A's execution/__init__.py, the propfirm barrier simulator) — worth checking whether the underlying case offers a concrete forced-deleveraging mechanism to stress-test against in the trailing_dd_simulator.

## Extracted content
Numeric claims (author's, same as v1): "88% of surveyed finance professionals report no operational governance framework"; "24 of 75 large U.S. money managers... report a formal governance policy"; crowding "joint drawdown risk rising from 39.2% to 79.3%." New in v2: a "$45 billion discretionary fund's forced-deleveraging blowup" case and an airline-chatbot liability tribunal ruling (unnamed/unquantified in the excerpt).

## Action proposed
TEST_LATER — same drift-monitor rationale as the v1 paper; read arxiv_econ_em_ai_governance_for_institutional_readiness_in_finan_20260804.md (the earlier, shorter version) first.
