# How to Spot Outliers: an Ensemble Anomaly Detection Framework for Risk Valuation Outputs

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.20079
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 8b3fb11780abbdff

## Summary
An ensemble anomaly detection framework combines isolation forests, local outlier factor, and autoencoder reconstruction error into a unified score for detecting errors in risk valuation outputs (P&L and Greeks time series). Applied to a multi-asset trading desk, the ensemble achieves 94% detection rate on injected anomalies with 2% false positive rate. The framework is particularly effective at distinguishing systematic drift (model recalibration errors) from isolated spikes (data-feed failures).

## Why it might be useful
This framework is directly applicable to data quality monitoring for Strategy A (daily crypto rebalancing on HL testnet/Propr) and Strategy B (8h delta-neutral carry), where VPS data-feed failures and position drift are known operational risks. The 94% detection rate at 2% FPR is strong for production use. Concretely: apply isolation forest on daily vol/signal/fill data from `logs/fills.csv` and strategy A's `signal.py` outputs to detect anomalies before they cause sizing errors. The isolation forest component is available in scikit-learn with no additional dependencies, making implementation < 1 day feasible. However, the current VPS monitoring (guardrails in `execution/__init__.py:46-47`) already covers the most critical path; this would add a second layer.

## Extracted content
- Claims: 94% detection rate, 2% false positive rate (injected anomalies on multi-asset trading desk P&L/Greeks)
- Components: isolation forest + local outlier factor + autoencoder reconstruction error → unified score
- Effective at: systematic drift (model recalibration) vs isolated spikes (data-feed failures)

No verbatim code or formulas in the excerpt.

## Action proposed
TEST_LATER
(Isolation forest on Strategy A/B daily fill/signal logs is a meaningful operational improvement; implement when Strategy B moves to mainnet where data integrity has higher stakes.)
