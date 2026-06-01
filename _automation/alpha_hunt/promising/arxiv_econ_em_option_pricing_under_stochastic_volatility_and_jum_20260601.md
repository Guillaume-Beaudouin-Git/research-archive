# Option Pricing under Stochastic Volatility and Jumps: PIDE Framework with S&P500 Calibration

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.30562v1
**Captured**: 2026-06-01 06:06 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: f947078aee6e6f1a0d75b6761746cafa

## Summary
The paper builds a PIDE (partial integro-differential equation) solver for option pricing under a model combining stochastic volatility and return jumps, derived from an affine Lévy-type process. Numerically, it uses finite-difference grids with FFT-based treatment of the jump integral operator. Calibration via GMM on S&P500 index options at three maturity buckets produces a clear hierarchy: Heston stochastic volatility alone cuts implied-volatility RMSE by 39% relative to Black-Scholes, while adding either Merton or CGMY jump components yields only marginal further improvement concentrated in the short-maturity and deep-OTM region. The calibrated CGMY activity parameter points to a compound-Poisson (rare discrete jumps) rather than infinite-activity structure, consistent with high-frequency S&P500 evidence.

## Why it might be useful
Two concrete connections to Algo_claude. First, both SPX VRP Angle C (IC t=-0.144, wrong direction, archived) and BTC VRP Deribit (L13: gross 4.4%/yr vs 8.9%/yr cost, 0/13 WF folds positive, archived) were closed on cost and signal grounds — not model mismatch. This paper's result that jump risk premium is marginal at medium maturities and near-ATM reinforces the diagnosis: short-gamma VRP strategies on index options were not failing because the pricing model was wrong, but because the edge after costs is structurally absent at retail cost tiers. Second, if Strategy D eventually pivots to a futures-options hybrid (NQ vol carry for Tradeify), or if the Voie B FTMO analysis (`Futures/research/active/voie_b_ftmo/`) touches index option delta-hedging, this paper establishes that a Heston-calibrated IV surface is the practical minimum for realistic P&L attribution — flat-vol Black-Scholes delta-hedging would materially distort attribution at short maturities. Concretely: nothing to code now, but file as reference when any vol-surface work is reopened.

## Extracted content
The authors report: "relative to Black-Scholes, the Heston specification reduces implied-volatility RMSE by 39%." Jump augmentation via Merton or CGMY delivers "marginal improvements concentrated at short maturities and in the deep out-of-the-money region." Calibrated CGMY activity index "supports a compound-Poisson structure, consistent with high-frequency evidence on S&P500 index returns."

## Action proposed
REFERENCE

Both archived VRP tracks (SPX and BTC) were killed by cost economics (L13) and signal direction, not model issues. This paper does not change those conclusions. Retain as reference if options-based strategies are revisited: the key quantitative takeaway is that stochastic vol (Heston) dominates the vol surface, and jump augmentation only matters OTM and short-dated.
