# AI Overfitting in Trading Systems: In-Sample vs Live Performance Gap

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=c8SScnXvbS&source=feedburner
**Captured**: 2026-06-02 06:06 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: af114c59419865f3ca80f0ed42e345a2

## Summary
A practitioner article from Wisdom Trading on the systematic divergence between in-sample and live performance when AI or machine-learning methods are incorporated into strategy development. The core thesis is that live trading is the only credible test — in-sample metrics, however impressive, routinely mislead. The article documents the team's hybrid workflow combining AI tools with their existing systematic infrastructure (Trading Blox), covering where AI adds value and where it introduces overfitting risk. The excerpt is truncated before the workflow specifics are revealed.

## Why it might be useful
This directly reinforces two hard rules in CLAUDE.md: the 3-modification cap per hypothesis, and the mandatory DSR (Bailey-LdP) when n_mod ≥ 2. The sector_hothand_propfirm research (`Equities/research/active/sector_hothand_propfirm/`, currently under audit `_audit/sector_hothand_audit_2026-05-30.md`) is the most immediate candidate for the problem described here: a t_HAC=10.38 alpha stat over 5 WF folds with iterative methodology is a canonical in-sample overfitting signature. Before reading the full Wisdom Trading article for workflow details, the concrete action is to apply DSR to sector_hothand using `approx_multi_test_penalty` on the full iteration count, and check whether the corrected Sharpe still clears 2.01 DSR. If the full article provides a practitioner checklist for detecting AI-induced overfit, it could feed directly into the audit criteria currently pending.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
