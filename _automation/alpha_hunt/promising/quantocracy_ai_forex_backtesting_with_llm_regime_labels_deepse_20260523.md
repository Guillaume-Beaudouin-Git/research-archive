# AI Forex Backtesting with LLM Regime Labels: DeepSeek vs K-Means in Python [Quant Insti]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=iERW2gVsce&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic, code_quant], L2_OK
**Hash**: ad2266f1e503dd3cef990a9e33a0d5ce

## Summary
A Python backtest pipeline where market regimes are classified by a DeepSeek LLM (given compact numeric feature summaries) and compared against K-Means clustering as a deterministic baseline. The pipeline applies LLM regime labels to a forex strategy and evaluates whether the LLM labeling improves out-of-sample results versus K-Means. The article includes Python code and is from Quant Insti, which typically provides executable implementations.

## Why it might be useful
FX testing is archived ("edge insufficient post-2018"), so the forex application is not replicable. However, the regime labeling methodology transfers: Strategy C (NQ opening momentum) currently uses hard-coded VWAP and gap filters as implicit regime conditions. Adapting this LLM-labeling pipeline to NQ 1-min session summaries could create an alternative regime filter to validate or replace the existing VWAP condition — which is the KNOWN GAP item (VWAP 1-min vs 5-min discrepancy). The Python code in the full article could be run on Dataset_NQ_1min_2022_2025.csv without new data acquisition.

## Extracted content
No code in excerpt. Full article contains Python implementation — retrieve for code extraction.

## Action proposed
TEST_LATER

Extract Python code from full article. Adapt K-Means baseline (not LLM, to keep it deterministic) to NQ 09:30-09:45 regime classification. Could resolve the VWAP filter gap before paper trading. 1-2 day effort.
