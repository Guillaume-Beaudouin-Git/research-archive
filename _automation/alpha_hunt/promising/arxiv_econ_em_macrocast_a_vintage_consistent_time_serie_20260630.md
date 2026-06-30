# MACROCAST: A Vintage-Consistent Time Series Foundation Model for Real-Time Macroeconomic Forecasting

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.28670v1
**Captured**: 2026-06-30 02:00 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: ff1ed5186fde9f24f37133fcc25d8277

## Summary
MACROCAST is a lightweight time-series foundation model for real-time macro forecasting that eliminates two data leakage paths: temporal contamination (model trained on future realizations) and revision bias (training on fully revised data that wouldn't have been available at forecast time). It is pretrained on synthetic time series in ~1 GPU-day, then fine-tuned on synthetic draws from Bayesian VARs, DFMs, and ARIMAs estimated on ALFRED vintage-specific data — no observed future or revised value enters at any stage. In genuine real-time OOS evaluation on FRED-MD, MACROCAST outperforms AR(1) on ~80% of series-horizon pairs and matches or surpasses Chronos-2 on most benchmarks. Each fine-tuning run takes nine minutes.

## Why it might be useful
The paper's primary contribution is methodological hygiene: properly separating training from forecasting vintages to eliminate look-ahead bias. This directly parallels the delay-1 discipline (L26) and excess-returns methodology (L8) already in place for all Algo_claude backtests. It validates that the right framing for any macro signal used as a regime filter is the REAL-TIME data vintage — not the revised series available later. Concretely: the ZN Baltussen research (`Futures/research/active/zn_baltussen/`) may want to use macro indicators (e.g., inflation surprise, ISM) as momentum regime filters; any such filter must use ALFRED vintage data, not revised FRED series. MACROCAST's synthetic-pretraining + vintage-fine-tuning workflow is a reproducible recipe for building such a filter without look-ahead. The nine-minute fine-tune time makes it practically feasible to re-estimate quarterly as new vintages arrive.

## Extracted content
The authors claim: "MACROCAST improves on the AR(1) benchmark for roughly 80% of series-horizon pairs, matches or surpasses Chronos-2 — the strongest currently available TSFM — and outperforms the Bayesian VAR and dynamic factor model benchmarks, all in a data-leakage-free manner."

No code or formulas in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
