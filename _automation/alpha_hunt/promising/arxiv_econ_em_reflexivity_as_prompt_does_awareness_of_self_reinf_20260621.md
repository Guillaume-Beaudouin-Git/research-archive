# LLM Financial Forecasting Under Reflexivity Awareness: GPT-5 vs Claude Sonnet 4.6 vs Gemini 3

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.00061
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: 3b76bed82b2b6cd10bbd42fb79370236

## Summary
A controlled study testing three frontier LLMs (GPT-5, Claude Sonnet 4.6, Gemini 3 Pro) as directional market forecasters under four levels of reflexivity awareness (from naive to Soros-theory-informed). Evaluated on anonymized/normalized price series from the dot-com bubble (1996-2001) and GFC (2004-2009). The primary metric is directional accuracy; secondary is Sharpe ratio of an implied long/cash strategy. The key finding is that reflexivity awareness improves directional accuracy differentially across models and context windows — the same theoretical framing produces qualitatively different forecasting behaviors in different LLMs.

## Why it might be useful
This is a research paper about LLMs as forecasters, not a tradeable edge. The direct mention of "Claude Sonnet 4.6" is notable (same model powering this alpha hunt routine). The Sharpe ratio of implied strategies from LLM forecasts is not directly applicable to our systematic strategies — LLM-driven discretionary signals are incompatible with our purely algorithmic approach. However, the anonymization methodology (normalizing and anonymizing prices to prevent memorization) is methodologically useful context if we were to evaluate LLM-based signals in our automation pipeline. No connection to A/B/C/D strategies. The dot-com and GFC evaluation periods predate most of our data (Strategy A backtest is post-2015 for crypto).

## Extracted content
"We evaluate three frontier models - GPT5, Claude Sonnet 4.6, and Gemini 3 Pro - under four accumulating zero-shot conditions across two historically distinct episodes: the dot-com bubble (1996-2001) and the global financial crisis (2004-2009). The primary metric is directional forecasting accuracy; we also report the Sharpe ratio of an implied long/cash strategy to capture the risk-adjusted economic value of the forecasts."

"All inputs are anonymized and normalized to guard against memorization."

## Action proposed
REFERENCE

LLM-as-forecaster research with no direct trading application for systematic strategies. Interesting methodological note on memorization guard, but not actionable for current strategy pipeline.
