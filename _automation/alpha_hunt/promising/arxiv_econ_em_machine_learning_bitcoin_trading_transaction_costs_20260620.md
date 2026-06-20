# Machine Learning Models for Bitcoin Trading After Transaction Costs: Walk-Forward Evidence

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.00060
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[metrics, methodology], L2_OK
**Hash**: a68127ac2dc8421c6ae26ab665a2f0d0

## Summary
This paper evaluates three ML architectures — XGBoost, LSTM, and iTransformer — for predicting hourly BTC-USDT returns on approximately 70,000 observations from 2018–2026. The protocol uses 27 walk-forward folds. All three models achieve positive gross performance in some configurations, but naive sign-following strategies collapse once a 10-basis-point transaction cost is applied. The paper finds that cost-robust viability requires either very selective signal firing (only strongest quantile of predictions) or dynamic hedging variants that reduce turnover. The iTransformer architecture shows better calibration in late-sample folds than XGBoost or LSTM.

## Why it might be useful
Strategy A (TSMOM on BTC/ETH/SOL) is currently frozen but structurally relevant: this paper stress-tests hourly crypto signal-to-trade pipelines under realistic costs (10bps ≈ Binance taker rate) with a 27-fold WF protocol. The 10bps assumption is slightly lower than the 0.17% RT in CLAUDE.md (17bps), so a replication at 17bps would be a tighter test. The 27-fold WF approach is more rigorous than the minimum 5-fold standard in the hard rules; comparing fold-count sensitivity is methodologically useful. More directly: if a future Strategy D variant targets crypto (currently under consideration as a decorrelated asset class), this paper's architecture comparison and cost-filtering methodology would apply directly. Data (Binance hourly klines) is available via `data/raw/` or live API.

## Extracted content
The authors claim: "naive sign-based strategies fail once transaction costs of ten basis points are imposed." XGBoost, LSTM, and iTransformer are compared across 27 walk-forward folds. The paper uses the iTransformer architecture (Transformer with inverted attention dimension). No specific Sharpe numbers are given in the abstract; the emphasis is on the transition from gross to net performance.

## Action proposed
TEST_LATER

Strategy A is frozen. Revisit when designing a future crypto momentum variant (potential Strategy D crypto arm). Priority: after B reaches mainnet (~2026-07-17) and portfolio recalc is complete. Requires downloading Binance hourly data (available free) and implementing iTransformer pipeline (~2 days implementation).
