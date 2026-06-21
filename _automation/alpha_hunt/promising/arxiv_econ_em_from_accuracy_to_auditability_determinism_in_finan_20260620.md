# From Accuracy to Auditability: Determinism in Financial AI Systems

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.23955
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 829cb0a7bddb855f678c00c390da47a3

## Summary
A survey covers reproducibility failures across tabular ML, graph neural networks, and generative AI in regulated finance. GPU non-determinism, floating-point ordering, and stochastic sampling each independently break reproducibility. Architectural patterns for auditable ML are proposed: fixed seeds, deterministic CUDA ops, and version-locked inference pipelines.

## Why it might be useful
The sector_hothand_propfirm t_HAC=10.38 red flag could partly result from non-deterministic training (different seeds yielding different Sharpe estimates). The determinism checklist is directly applicable to the mandatory audit (_audit/sector_hothand_audit_2026-05-30.md): fixing seeds and deterministic ops would isolate whether t-stat inflation is numerical artefact or real. L20 DSR also requires exact N_modifications, impossible with non-deterministic training runs. Concrete action: add seed-fixing to all sector_hothand backtest runs before the next audit pass.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Apply determinism checklist (fixed seeds, deterministic ops) to sector_hothand_propfirm backtests as part of the mandatory t_HAC=10.38 audit.
