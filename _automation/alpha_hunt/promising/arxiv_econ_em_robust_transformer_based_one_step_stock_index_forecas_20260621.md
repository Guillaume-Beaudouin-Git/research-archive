# Robust Transformer-Based One-Step Stock Index Forecasting via Shifted Feature Windows

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.15701
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 4d32c7e9b4cccec5

## Summary
The paper proposes a one-step-ahead transformer framework for stock index forecasting using shifted feature windows to enforce temporal causality and prevent lookahead bias. Tested on SPX, NDX, FTSE, and DAX over 2010-2024, the approach achieves 55-58% directional accuracy with walk-forward Sharpe of 0.65-0.85 after 3 bps transaction costs. The critical finding is that without shifted windows, directional accuracy inflates to 72-79% — a data leakage artifact directly comparable to the same-bar discipline issue in L26.

## Why it might be useful
This paper is relevant to NQ/NDX forecasting methodology, with direct connections to Strategy D (NQ intraday research) and to methodology lesson L26 (delay-1/same-bar discipline). The walk-forward Sharpe of 0.65-0.85 at 3 bps cost is at the RESEARCH_PASS gate (Sharpe>0.7) but below PROPFIRM_PASS (Sharpe>1.0). The lookahead-bias warning (L26 validated externally) is operationally useful. NQ futures RT cost is ~$29 (L19, Databento re-baseline), substantially higher than the 3 bps assumed here — applying this cost would likely push the NQ-specific variant below gate. Useful as a methodology reference for D research and as a leakage-check template.

## Extracted content
- Claims: 55-58% directional accuracy OOS, walk-forward Sharpe 0.65-0.85 after 3 bps RT costs (SPX/NDX/FTSE/DAX, 2010-2024)
- Leakage quantification: without shifted windows, directional accuracy inflates to 72-79%
- Instruments: SPX, NDX, FTSE, DAX

No verbatim code or formulas in the excerpt.

## Action proposed
TEST_LATER
(Shifted-window lookahead check is applicable to D3/D5 signal construction; test only after D3+D5 combo research is concluded, as NQ futures cost ($29 RT) likely kills the edge at this Sharpe level.)
