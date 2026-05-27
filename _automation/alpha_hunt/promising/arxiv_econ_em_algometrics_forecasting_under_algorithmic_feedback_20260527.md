# Algometrics: Forecasting Under Algorithmic Feedback

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.23978v1
**Captured**: 2026-05-27 12:08 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: edba64b8fb4551baa78fd43b8efda8a6

## Summary
When predictive models drive the decisions they forecast, the data-generating process is no longer passive — the model's output becomes an input to the market it is trying to predict. This paper formalizes this feedback loop and proves three results. First, deployment risk (error when the model drives trades) is fundamentally unidentifiable from passive historical data: infinitely many feedback environments can produce the same historical error distribution while implying different live performance. Second, historical model rankings can invert under crowding — a predictor with lower backtest error can have higher live error once competing algorithms adopt similar models. Third, randomized or instrumented actions (analogous to A/B testing in markets) can identify short-horizon linear feedback, with a finite-sample bound on deployment-risk estimation.

## Why it might be useful
This paper directly explains why many strategies in the CLAUDE.md archive failed in walk-forward or live testing despite showing decent in-sample results. The crowding-driven inversion (result 2) applies to the archived CS crypto strategies (L11, β-dominance), multi-asset TSMOM (Sharpe 0.21 corrected), and the NQ ORB class (Strategy C): as more propfirm traders adopt ORB-style entry at 09:46 ET, the strategy's deployment risk increases relative to its historical risk. The non-identifiability result (result 1) is the formal justification for CLAUDE.md's walk-forward requirement and AMTP correction — passive backtests systematically underestimate live risk. The instrumental-variables identification (result 3) is the most actionable: for Strategy C (NQ ORB, Tradovate), randomly varying entry timing (09:46 vs 09:47 vs 09:48 ET) across paper trades would allow direct estimation of how much of the signal is crowding-sensitive versus durable. This is a <1 day modification to the strategy_c paper-trade script once paper trading starts.

## Extracted content
Key formal results from abstract:
- "Deployment risk is not identifiable from passive historical data alone: even in a one-step linear feedback model, infinitely many algorithm-mediated environments induce the same historical law while implying different deployment risks."
- "Historical model rankings can invert under crowding, so a predictor with lower passive error can have higher deployment error once similar algorithms are adopted."
- "Randomized or instrumented actions identify short-horizon linear feedback, and [the paper derives] a finite-sample bound for deployment-risk estimation."

## Action proposed
TEST_LATER — Read the full paper before Strategy C paper-trade launch. The randomized-entry identification design (result 3) is directly implementable in the Tradovate paper-trade setup: randomly dither entry timing by ±2 minutes across 30+ paper trades to estimate the crowding-sensitive component of the ORB edge. This costs nothing in infrastructure and takes <0.5 days to add to strategy_c_live/signal_engine.py once paper trading starts. Also use the non-identifiability theorem (result 1) as formal justification in any future propfirm submission that shows walk-forward OOS results.
