# Markets Underreact to Sequenced Public Information: Evidence from Prediction Markets

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.07811v1
**Captured**: 2026-06-09 06:04 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 41a36b797afd2d98b8c321130beeb769

## Summary
Using high-frequency prediction market data where a precise out-of-sample benchmark probability is observable, this paper quantifies the degree to which prices fail to fully incorporate public signals on arrival. Each one-unit move in the benchmark probability generates only a 0.64-unit contemporaneous price move, with the remaining 0.36 predictably drifting in over the following several minutes. The underreaction is amplified when liquidity is low and when signals are salient — paradoxically, the most obvious signals trigger the greatest shortfall. The result holds net of subsequent information arrivals, ruling out a rational Bayesian explanation. The authors frame it as gradual price discovery governed by the interaction between attention and trading frictions.

## Why it might be useful
The 0.64-for-one contemporaneous response with predictable subsequent drift is mechanistic background for why the Strategy C NQ ORB works: the 09:30-09:45 opening range forms as public information (macro releases, futures overnight gap) is only partially priced. Entry at 09:46 then rides the residual drift. The paper's finding that underreaction is *larger* when liquidity is low ties directly to Strategy C's gap filter (gap < 1.2%): large gaps often co-occur with thin pre-market, exactly the regime where underreaction would be highest — this is a candidate explanation for why the gap filter improves WF pass rate (78%, 7/9 folds). More concretely: run a cross-tabulation in `Futures/live/strategy_c_live/signal_engine` of (gap_magnitude, pre-mkt_volume_proxy) vs trade outcome — if the gap filter is proxying for liquidity-driven underreaction, the threshold could be sharpened. Also relevant to D2 deferred (VWAP touch fade with inverted IC): the directional inversion in D2 may reflect that the fade strategy was entered *after* the underreaction drift had already resolved, not before.

## Extracted content
The authors report: "a one-minute change in the benchmark probability is associated with only about a 0.64-for-one contemporaneous change in market prices." The missing 0.36 predicts "future price drift over the following several minutes, including drift net of subsequent changes in the benchmark probability." No Python code in the excerpt.

## Action proposed
REFERENCE
