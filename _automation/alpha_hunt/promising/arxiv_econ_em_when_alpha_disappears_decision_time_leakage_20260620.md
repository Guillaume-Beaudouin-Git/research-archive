# When Alpha Disappears: A Benchmark for Decision-Time Leakage in Financial Backtests

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.23959
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 50ec4a67c9888d7833dce46d2b64c72a

## Summary
This paper introduces a systematic benchmark for quantifying how much of backtest alpha disappears when decision-time data leakage is removed. The approach toggles one evaluation convention at a time around a clean t+1-open reference (the canonical correct convention), holding the data panel, WF split, model family, horizon, portfolio rule, and cost convention fixed. Applied to two daily OHLCV equity panels and six model families, the benchmark shows that many common backtest protocols embed 20–80% of their reported alpha via leakage from using same-bar close prices, forward-filling data, or overlapping windows. The "one-switch" methodology is directly applicable to any backtest protocol.

## Why it might be useful
L26 in CLAUDE.md explicitly codifies this concern: "overlapping-window and same-bar-fill screens inflate intraday edges; validate with non-overlapping trades + a 1-bar execution-delay test." This paper operationalizes L26 as a systematic benchmark. For Strategy D (D3+D5 NQ intraday), the pre-registration in `Futures/research/active/strategy_d/hypotheses_preregistered.md` should reference this paper's one-switch methodology as the validation standard. The paper also aligns with the "5 mandatory script fixes" in CLAUDE.md — specifically fix #1 (signal at T-1, trade at T). Any new research archive referencing Sharpe improvements should be audited against this benchmark.

## Extracted content
"Rather than treating leakage as a binary property, the benchmark estimates protocol-induced inflation by toggling one evaluation convention at a time around a clean t+1-open reference." The paper finds "20–80% of reported alpha" can be leakage from common protocol errors. Uses "two daily-OHLCV equity panels, six model families." No specific Sharpe numbers given.

## Action proposed
REFERENCE

Cite in D3/D5 pre-registration as the standard for leakage validation. Cross-reference with L26 and hard rule #1 (signal at T-1, trade at T). Use the one-switch checklist when reviewing any new backtest before RESEARCH_PASS classification.
