# Multi-Dimensional Behavioral Evaluation of Agentic Stock Prediction Systems

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.05739
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[metrics, methodology], L2_OK
**Hash**: 40cdcaaba6061ec1d9a9dd822ac85932

## Summary
This paper develops a behavioral evaluation methodology that goes beyond output-level accuracy testing for AI-based stock prediction agents. Behavioral traces at each autonomous decision point are grouped into five-day episodes and scored along six domain-specific dimensions: regime detection, risk calibration, momentum sensitivity, mean-reversion awareness, event-response, and contrarian capacity. A closed-loop RL feedback mechanism updates the LLM judge's scoring weights based on subsequent market outcomes, creating an adaptive evaluation system. The study is applied to agentic systems but the behavioral dimensions are also relevant to rule-based systems.

## Why it might be useful
The six behavioral dimensions mirror several gaps in the current research methodology. "Regime detection" maps to the L15/L31 concern about regime-dependent edges. "Risk calibration" maps to the daily vol targeting requirement. "Event-response" is relevant to Strategy B's 8h rebalance timing (funding spikes during events). The RL-updated judge concept is interesting for the `_automation/feasibility/` pipeline: instead of static L0/L1/L2 filters, a feedback loop that updates filter weights based on which staged items actually backtest successfully would improve the pipeline's hit rate. However, implementing this requires tracking backtest outcomes of staged items — currently not done.

## Extracted content
Six behavioral dimensions: "regime detection, risk calibration, momentum sensitivity, mean-reversion awareness, event-response, and contrarian capacity." The closed-loop RL mechanism updates scoring weights based on "subsequent market outcomes." Applied to LLM agentic systems but dimensions generalize.

## Action proposed
REFERENCE

Use the six behavioral dimensions as a pre-flight checklist template for new strategy hypotheses in `_automation/feasibility/`. Add to the Generic handler in `_automation/feasibility/` as optional behavioral audit dimensions. Cross-reference with the mandatory 5-script fixes in CLAUDE.md.
