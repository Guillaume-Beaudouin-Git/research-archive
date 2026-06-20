# A Validated Volatility-Volume-Gap Classifier for Day-Type Identification in MNQ Intraday Data

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.11423
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 056537d9ce950f2d3d31ffdcdb8d933c

## Summary
The paper builds a composite pre-market classifier for MNQ (Micro E-Mini Nasdaq 100) using three observables measured before the regular session: the magnitude of the overnight gap, the first-30-minute return magnitude, and abnormal opening-bar volume relative to a rolling baseline. Applied to 947 trading days of 5-minute MNQ data from 2021–2025, classifier-positive days exhibit statistically distinct intraday structure: a directional morning drift followed by a systematic late-session reversal, while classifier-negative days show early chop then continuation. The study validates the classifier out-of-sample using nested walk-forward splits, confirming that the three pre-market signals together outperform any single-signal version.

## Why it might be useful
This is a direct input to Strategy D (D3+D5 portfolio). D3 is an opening-range mid-fade (09:45–11:00) and D5 is an afternoon BB squeeze breakout (14:00–15:30); both failed individually but are under study for regime-conditional combination. The VVG classifier is exactly the day-type filter needed: on VVG-positive days (directional morning drift), D3 fade signals may be suppressed in favor of D5 continuation, and vice versa. The three pre-market features (gap, opening 30-min return, abnormal volume) can all be computed from `data/raw/NQ_1min_databento_2010-2026.parquet` before session open. Cost of implementing: compute VVG signal at 09:30, use it as a regime gate in the D3/D5 combo backtest already in `Futures/research/active/strategy_d/`. This is exactly the "regime filter" step in the `hypotheses_preregistered.md`. Time to implement: less than 1 day.

## Extracted content
The authors report that classifier-positive days are identified by: gap ≥ threshold_g (calibrated on rolling 20-day baseline), opening-30min |return| ≥ threshold_r, and volume in opening bar ≥ k × rolling_vol_baseline. No specific Sharpe or win-rate statistics are given in the abstract, but the paper claims classifier-positive days "exhibit statistically distinct intraday behavior" with nested walk-forward validation. Full numeric claims require reading Sections 3–4.

## Action proposed
TEST_NOW

Implement VVG classifier as regime gate for D3+D5 combo. Pre-register: "VVG=1 → suppress D3 fade, enable D5 continuation; VVG=0 → enable D3, suppress D5." Data: `data/raw/NQ_1min_databento_2010-2026.parquet`. Target file: `Futures/research/active/strategy_d/`. This uses 1 of the remaining 3 hypothesis budget slots for Strategy D. Read Sections 3–4 to extract exact threshold calibration method before implementing.
