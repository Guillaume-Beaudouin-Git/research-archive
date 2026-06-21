# Predicting Stock Price Direction on Earnings Announcement Days using Machine Learning

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.25894
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 363994d151b313d0

## Summary
The paper builds an ML framework to predict stock price direction on earnings announcement days using historical price patterns, earnings call transcript sentiment (NLP), financial ratios, and analyst forecast revisions. An ensemble of gradient boosting and LSTM networks achieves 67% directional accuracy on OOS test (2020-2024), Sharpe ratio of 1.8, and maximum drawdown of 12%. The feature set targets the information asymmetry window around earnings releases.

## Why it might be useful
This paper is directly relevant to L42 (pre-FOMC drift — post-event momentum continuation documented on 8 equity index instruments) and to Strategy D research (NQ intraday, propfirm-targeted). The 67% directional accuracy and Sharpe 1.8 OOS would exceed PROPFIRM_PASS gates if replicable on NQ futures. The key implementation questions are: (1) does the edge survive at NQ futures cost level ($29 RT per L19 re-baseline); (2) is the LSTM feature set constructable from free data (yfinance + FRED); (3) does HAC-deflation of the 2020-2024 sample (4yr, ~200 earnings events/yr if broad equity) survive AMTP. Pre-register an NQ-focused variant using the ORB signal date as the earnings-day proxy and test against D3/D5 before committing a new hypothesis slot.

## Extracted content
- Claims: 67% directional accuracy OOS (2020-2024), Sharpe 1.8, MaxDD 12%
- Feature set: historical price patterns, earnings call transcript sentiment, financial ratios, analyst forecast revisions
- Models: gradient boosting + LSTM ensemble

No verbatim code or formulas in the excerpt.

## Action proposed
TEST_LATER
(Requires earnings transcript data and NQ-specific adaptation; pre-registration against D3/D5 needed before consuming a hypothesis slot — implement only after current D3+D5 combo is resolved.)
