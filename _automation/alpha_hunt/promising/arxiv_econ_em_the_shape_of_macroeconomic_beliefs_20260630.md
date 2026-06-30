# The Shape of Macroeconomic Beliefs

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.30040v1
**Captured**: 2026-06-30 04:30 UTC
**Filters passed**: L1=[macro_trading], L2_OK
**Hash**: 163150e227e6bacc0556b47e7af1b8bf

## Summary
This paper converts Kalshi prediction-market contracts on CPI and core CPI releases into full implied probability distributions over inflation outcomes at horizons from 30 days down to one hour pre-release. The market-implied mean is informative for headline CPI above and beyond the Reuters consensus, but the main signal is distributional — specifically, the upper-tail probability assigned to high-inflation states. The authors find that a 0.1 percentage point positive lagged CPI surprise raises the probability of monthly inflation exceeding 0.3% by approximately 4.7 percentage points, even after controlling for current consensus. Crucially, Kalshi upper-tail probabilities predict actual high-inflation realizations in cases where the point consensus appears normal, meaning distributional information from prediction markets is genuinely additive to point forecasts.

## Why it might be useful
The active ZN Baltussen research (`Futures/research/active/zn_baltussen/`) targets bond futures momentum without a macro conditioning layer. This paper provides a concrete, observable, real-time signal for inflation regime classification that could serve as a macro filter for ZN positioning: if Kalshi upper-tail CPI probability is elevated above a threshold before a release, trend-following on bonds faces a directional headwind (risk-off repricing). The L42 lesson already establishes that pre-FOMC drift on equity indices is real; the mechanism here (prediction market distributional beliefs vs. point consensus divergence) is orthogonal to the FOMC-timing channel and applies to CPI release windows. Practically: test whether ZN momentum returns are lower on the subset of holding periods that overlap with high Kalshi upper-tail CPI weeks — this is a pre-registerable conditional backtest requiring only the Kalshi public API and the existing NQ_1min Databento data.

## Extracted content
The author claims: "a 0.1 percentage point positive lagged surprise raises the probability of monthly inflation above 0.3 percent by about 4.7 percentage points, even after controlling for the current consensus forecast."

No code or formulas in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Kalshi API access required (free tier available). Implementation: pull Kalshi CPI upper-tail probabilities at daily frequency, merge with ZN futures daily returns from Databento parquet, run conditional Sharpe split — ~1 day of work. Defer until ZN Baltussen baseline is established in `Futures/research/active/zn_baltussen/`.
