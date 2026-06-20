# Continuous Cash-Overlay Filters for a Growth-Defensive Risk Sleeve with Walk-Forward Validation

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.09025
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[metrics, methodology], L2_OK
**Hash**: 281c9e9ef336fb3a61c566c78092746c

## Summary
The paper examines a dynamic cash-overlay decision applied to a fixed 50/50 growth/defensive ETF sleeve. Two continuous filters are developed: a slow-tail compensator that targets the asymmetric return distribution of risky assets (conditioning on tail events), and a V-shape crash brake that detects rapid drawdown patterns and shifts to cash. Both filters are evaluated using walk-forward validation with expanding windows, and a combined max-cash variant is tested. The excess return over the cash rate is measured correctly (relative to contemporaneous cash rate), making this an excess-return-aware backtest.

## Why it might be useful
Strategy A (TSMOM, weekly rebalance) currently uses a `tanh(cumret_28d / vol_28d)` signal clipped long-only. The V-shape crash brake concept from this paper — detecting rapid drawdown patterns and shifting to cash — is mechanically similar to the MAX_DAILY_DD guardrail (2.8% in `execution/__init__.py:46-47`). However, a continuous version that adjusts position size smoothly (rather than hard-stopping) could be more propfirm-friendly. For Strategy B (delta-neutral, 8h rebalance), the V-shape brake could serve as an intra-day kill switch complement to the existing STOP-file mechanism. The walk-forward methodology with expanding windows (matches the ≥5 folds mandate in hard rules) and excess-return measurement (mandatory in CLAUDE.md) make this a clean methodological template.

## Extracted content
The paper develops two filters: (1) slow-tail compensator and (2) V-shape crash brake. The excess return target is "future risky-sleeve return over cash." Walk-forward validation uses "the cash leg measured using the contemporaneous cash rate." The max-cash combination combines both filters. No specific Sharpe numbers in abstract.

## Action proposed
TEST_LATER

Read Section 3 (filter specifications) for the V-shape crash brake signal definition. If the brake signal can be computed from daily BTC/ETH/SOL returns (already available), test as a continuous guardrail modifier for Strategy A. Budget: 1 day. Pre-register: "V-shape brake → reduce position by x% when triggered, revert when clear." Note: does NOT reset the 3-modification budget for A (which is frozen) — this would be a structural enhancement only if A is unfrozen for FTMO.
