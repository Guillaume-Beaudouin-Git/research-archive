# Sequential Structure in Intraday MNQ Futures: LSTM vs Gradient Boosting Comparison

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.17724
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 9725261b62ac081cf45144065e7607e0

## Summary
This paper directly compares LSTM and gradient boosting (XGBoost) on 5-minute OHLCV bars of MNQ futures across 944 trading days from 2021–2025, motivated by the Kronos foundation model research on candlestick data. Four model configurations are tested: GBT with technical features, GBT with raw bars, LSTM with raw bars, and LSTM with technical features. The core finding is that neither architecture extracts statistically significant predictive structure from this single-instrument dataset at this scale — both models fail to beat a hold benchmark after accounting for transaction costs. The authors conclude that the MNQ 5-min dataset is too small for sequential deep learning, and that any measured edge is likely spurious in-sample.

## Why it might be useful
This paper directly speaks to Strategy D (NQ intraday research). D3 and D5 use rule-based signals (opening range mid-fade, afternoon BB squeeze); neither uses ML. This paper's negative result is actually supportive of the rule-based approach: if LSTM/GBT fail to find structure in MNQ 5-min data, ML-augmented D3/D5 would likely fail too. More importantly, the paper's walk-forward framework (944 days, 2021–2025) is almost identical to the dataset used in `data/raw/NQ_1min_databento_2010-2026.parquet`. The conclusion "single-instrument 944-day dataset is too small for sequential deep learning" aligns with the L20 DSR lesson — small N + many models = everything inflates. Use as a negative reference before any D3/D5 ML augmentation is proposed.

## Extracted content
"Four model configurations are evaluated" on "944 trading days from 2021-2025." Paper finds insufficient predictive structure to beat a hold benchmark after transaction costs. The Kronos foundation model is cited as motivation. No specific Sharpe or IC statistics given in abstract.

## Action proposed
REFERENCE

Use as a pre-flight document if ML augmentation of D3/D5 is ever proposed. Confirms the rule-based approach is appropriate for this dataset size. Cross-reference with L20 (DSR for n_mod > 5) before any ML-based signal addition to Strategy D.
