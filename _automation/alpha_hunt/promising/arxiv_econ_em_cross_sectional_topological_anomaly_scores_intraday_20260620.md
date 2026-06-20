# Cross-Sectional Topological Anomaly Scores and Intraday Return Predictability in S&P 500

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.08586
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: d46ee456b822993a17deb1793d94ba05

## Summary
This paper constructs a stock-level topological anomaly score for S&P 500 stocks using BallMapper (a topological data analysis tool), a decoder-conditional VAE, and Function-on-Function regression, applied to intraday data for 10 liquid S&P 500 constituents from April 2025–March 2026. The score captures when a stock's co-movement topology deviates from its latent peer structure. Intraday return curves are then regressed on historical topological anomaly scores to test for predictability. The study finds that topological anomaly scores contain marginal predictive content for same-day intraday return curves, beyond standard momentum and volatility features.

## Why it might be useful
This is a novel regime/anomaly signal for equity intraday trading, potentially applicable to Strategy D (NQ intraday). The BallMapper + VAE approach identifies when NQ's correlation structure with its peers (ES, RTY) is anomalous — which could flag days with unusual microstructure ahead of the D3/D5 signals. However, the study covers only 10 stocks over 11 months (April 2025–March 2026), which is well below the N≥30 minimum (hard rule) and the n_eff needed for HAC significance. The methodology is complex (BallMapper requires a TDA library) and the practical edge is modest. Given the already-thin NQ intraday research budget (Strategy D has 3 modification slots, 0 consumed), this approach is too complex vs. the VVG Classifier (paper 056537d9) which is simpler and more directly validated.

## Extracted content
"Ten liquid S&P 500 constituents (April 2025–March 2026)" — N=1 year. BallMapper for topological data analysis. Decoder-conditional VAE. Function-on-Function regression for intraday return curves. "Topological anomaly scores contain marginal predictive content."

## Action proposed
REFERENCE

File as a signal idea for future strategy D or equity CS research. The method is novel but the sample is too small (N=1 year, 10 stocks) to clear the HAC significance gate. Revisit if a larger dataset (full S&P 500, 5+ years) becomes available. The sector_hothand_propfirm research might benefit from this framework for identifying cross-sectional regime anomalies.
