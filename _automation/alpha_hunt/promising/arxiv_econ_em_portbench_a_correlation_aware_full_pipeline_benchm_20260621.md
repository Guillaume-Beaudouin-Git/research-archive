# PortBench: LLM-Driven Portfolio Management Benchmark with Correlation Awareness

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.27887
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: f7884fa6845d47b244f04847e822f3df

## Summary
A benchmark for evaluating LLMs as portfolio managers across six asset classes over 10 years, with two layers: a static QA dataset (6,269 correlation-based questions across seven task templates) and a dynamic five-stage PM pipeline mirroring the full decision cycle. Two new metrics: a dual-layer correlation score (measures whether proposed portfolios exploit inter-class hedging and avoid intra-class concentration) and CEPS (quantifies how reasoning errors compound across pipeline stages). Key finding: 90% of model-profile combinations fail to outperform equal-weight allocation, and models that satisfy procedural constraints still suffer catastrophic drawdowns under stress. Code available at GitHub.

## Why it might be useful
The CEPS metric (compounding error propagation across pipeline stages) is a useful concept for evaluating our alpha hunt automation pipeline: if each stage (signal detection → feasibility → walk-forward → implementation) introduces independent errors, the compound error rate may be higher than each individual gate failure rate. However, the benchmark itself is for LLM-as-portfolio-manager evaluation, not systematic algorithmic trading — the LLM is making discretionary allocation decisions, which is antithetical to our fully systematic approach. The "90% fail to beat equal-weight" result is consistent with the CRSP benchmark paper (`4900a0ca`): LLMs are not reliable portfolio allocators. Irrelevant to our current strategy pipeline.

## Extracted content
"90% of model-profile combinations fail to outperform a basic equal-weight allocation, and models that satisfy every procedural constraint still suffer catastrophic drawdowns under stress."

Code: https://github.com/AgenticFinLab/PortBench (partial URL in excerpt).

## Action proposed
REFERENCE

LLM portfolio benchmark. Confirms LLM-driven portfolio management is unreliable; our systematic approach is the right alternative. CEPS metric is an interesting meta-evaluation concept for our automation pipeline but no immediate action needed.
