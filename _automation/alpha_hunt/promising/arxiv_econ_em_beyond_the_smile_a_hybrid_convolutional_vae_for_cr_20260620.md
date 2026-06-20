# Crypto Implied Volatility Surface Completion with Convolutional VAE (BTC/ETH)

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.16961
**Captured**: 2026-06-20 10:02 UTC
**Filters passed**: L1=[methodology, code_quant], L2_OK
**Hash**: 52188a1306049f717076e3336945c2f1

## Summary

Singh, Reddy & Chopra train a convolutional variational autoencoder (VAE) on 6,034 hourly BTC and ETH implied volatility surfaces from Binance Options (May–October 2023), parameterized on a 6×7 tenor-delta grid. The model achieves surface-completion RMSE of 0.94–1.56 vol points even at 50% masking rates. A hybrid predictor combining the VAE with a quadratic smile re-fit reduces error from 7.00 to 0.83 vol points at 50% masking. Crucially, joint BTC/ETH training improves performance by 9–27% relative to single-symbol training, indicating a largely shared implied-vol manifold between the two largest crypto assets. The model also flags the late-October ETH-anticipation rally as a high-reconstruction-error regime, suggesting it can serve as an anomaly detector for unusual vol surface conditions.

## Why it might be useful

Strategy B (delta-neutral carry) currently holds delta-neutral positions in perpetual futures. If the strategy expands toward options for hedging or VRP capture (which was explored and closed at VRP level in L13: gross 4.4%/yr vs. costs 8.9%/yr), the BTC/ETH vol surface manifold finding is relevant background. More concretely: the joint BTC/ETH vol manifold result implies that BTC implied vol is a strong proxy signal for ETH implied vol (and vice versa), which matters if we ever use implied vol regime filters on Strategy A or B. The paper also offers an anomaly-detection angle — the per-snapshot reconstruction error can flag unusual vol regimes, which is useful for guarding against adverse conditions during Strategy A rebalances (e.g., avoid rebalancing when implied vol surface is in an "anomalous" state). However, this requires Binance Options data access, which we don't currently have.

## Extracted content

From abstract:
- "the model attains a hidden-cell surface-completion RMSE in the 0.94-1.56 vol-point range across both markets and mask rates 10-50%"
- "The hybrid predictor attains 0.83 vol points at 50% masking against 7.00 for the smile re-fit alone, an eightfold reduction"
- "Joint training on BTC and ETH improves the in-distribution model on both markets by 9-27% relative to the better-performing single-symbol counterpart, indicating a substantially shared vol-surface manifold across the two largest cryptocurrencies"
- "The per-snapshot reconstruction error of the trained model flags the late-October ETF-anticipation rally" as anomalous.

Training data: 6,034 fully-filled hourly Binance Options surfaces (May-October 2023), 6×7 tenor-delta grid.

No code in excerpt (GitHub not linked in abstract). Full article needed.

## Action proposed

REFERENCE

Interesting background on crypto vol structure but not actionable without Binance Options access. VRP short gamma on crypto was closed at L13 (costs > gross). File as reference for if/when exploring options-based Strategy D variants. The BTC/ETH shared vol manifold finding is a useful prior for any future cross-asset implied-vol signal design.
