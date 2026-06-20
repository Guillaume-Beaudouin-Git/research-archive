# Beyond Agent Architecture: Execution Assumptions and Reproducibility in LLM-Based Trading Systems

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.08285
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 2233e81d4ef34f04730aac8d87288ab7

## Summary
This paper audits 30 LLM-based trading research studies for execution realism using a coded evidence matrix. The audit covers: data provenance, temporal split discipline (whether test data truly follows training data), execution timing (same-bar vs. next-open fill), turnover treatment (whether costs are accurately modeled), and transaction cost modeling. The key finding: most papers fail at least one of these dimensions, and those that pass all five criteria show materially lower reported Sharpe ratios than those with protocol gaps. The paper proposes a minimum reproducibility checklist for LLM trading research.

## Why it might be useful
This paper's reproducibility checklist for LLM trading research applies equally to any algorithmic strategy backtesting, including the rule-based strategies in Algo_claude. The five audit dimensions (data provenance, temporal split discipline, execution timing, turnover treatment, cost modeling) map exactly to the "5 mandatory script fixes" in CLAUDE.md and the "signal at T-1, trade at T" hard rule. The paper's finding that protocol-compliant papers show lower Sharpe directly validates the CLAUDE.md methodology: the research gate (Sharpe>0.7) and propfirm gate (Sharpe>1.0) should be applied AFTER ensuring all 5 mandatory fixes are applied. Use as a cross-check when reviewing backtest results in `_automation/feasibility/`.

## Extracted content
"A coded evidence matrix covering 30 trade-relevant primary studies." Five audit dimensions: data provenance, temporal split discipline, execution timing, turnover treatment, transaction-cost modeling. "Studies that pass all five criteria show materially lower reported Sharpe ratios." Proposes a minimum reproducibility checklist.

## Action proposed
REFERENCE

Add the five audit dimensions as a checklist in `_automation/feasibility/` Generic handler. Cross-reference with L26 (decision-time leakage) and paper 50ec4a67 (When Alpha Disappears). Applicable to any new strategy submission in the alpha_hunt pipeline.
