# Detecting unusual trading patterns on cryptocurrency exchanges by means of complexity measures

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.13916v1
**Captured**: 2026-07-16 01:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 99329c4ae60fb06a38e97f56398eaf30

## Summary
Builds a diagnostic framework for spotting suspicious/manipulated trading activity on crypto exchanges using complexity measures (tail behavior, autocorrelation, multifractal structure, approximate entropy, detrended cross-correlation) computed on trade-level BTC/ETH/XRP data from Binance, Bitget, KuCoin, and Kraken (April-June 2025). Finds a sharp, isolated anomaly on Bitget for BTC/ETH after mid-May 2025 — transaction counts spike without a matching rise in volume or return volatility, consistent with (though not proof of) artificially inflated trade counts / wash trading.

## Why it might be useful
Directly relevant to Strategy A and B's live execution on Hyperliquid — both sleeves depend on the reported liquidity/volume of the venues they trade (Strategy B gates VIABLE_ASSETS on MIN_VOL_USD=1,000,000), and this paper's complexity-measure toolkit is a candidate sanity check for distinguishing genuine liquidity from wash-trading-inflated volume before trusting an asset's volume screen. Second link: ties to Strategy B's VIABLE_ASSETS universe of small/mid-cap perps (HMSTR, TST, MEGA, WLD, STX, WIF, BIO, TRUMP) — exactly the kind of thinner, more manipulation-prone market where this diagnostic would matter most, unlike BTC/ETH/SOL in Strategy A.

## Extracted content
No code/formulas in excerpt. Qualitative finding only (Bitget anomaly post mid-May 2025) — no quantitative complexity-measure thresholds given.

## Action proposed
TEST_LATER — worth a quick multifractal/entropy check on HL volume data for Strategy B's smaller-cap perps before the next VIABLE_ASSETS review, but not urgent (no evidence of a live data-quality problem currently) and requires trade-level, not just OHLCV, data not yet in the local cache.
