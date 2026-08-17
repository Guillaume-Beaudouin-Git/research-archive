# Macroprudential Policy and Downside Risk: Regime-Dependent Effects of Capital Regulation

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2608.14307v1
**Captured**: 2026-08-17 02:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: c2db1c92a76db4a80b42fa440fae0a23

## Summary
The paper uses a threshold Bayesian VAR to show that the growth effect of bank capital regulation in Hungary depends heavily on the prevailing stress regime, with a systemic-stress index acting as the threshold variable — echoing the "Growth-at-Risk" literature but built for a data-scarce economy. The headline asymmetry: releasing regulatory capital during a stress regime meaningfully lifts peak GDP growth, with the effect lingering for roughly 20 months, while forcing capital accumulation during the calm regime barely dents growth. The authors report this holds up across different Cholesky orderings, sample windows, and definitions of the credit variable.

## Why it might be useful
No tradable instrument here (it's a central-bank policy paper on Hungarian macroprudential regulation), but the *mechanism it documents* is a clean real-world instance of the exact condition L54 identifies as necessary for a regime overlay to add value: the state variable (systemic-stress index) predicts the mean effect and not just the variance, and it does so *asymmetrically* — cheap in the calm regime, valuable in the stress regime — which is precisely the asymmetry L54 found missing in the regime overlay tested on the MONO book (flags predicted variance correctly but the mean effect ran the "wrong" way, penalizing the days that paid). It's also a useful methodological reference for the toolkit's regime-dependence discipline (the "FX carry regime-dependence" bullet, which currently only checks per-decade splits): a threshold-VAR with a continuous stress index and robustness to ordering/sample/definition is a more rigorous template than a fixed calendar split. No path to a specific strategy test — this is background for the next regime-overlay attempt, not a signal to build.

## Extracted content
No code or explicit formula given in the excerpt. Numeric claim preserved: the paper reports peak GDP growth is raised by releasing capital in the stress regime, with the effect persisting "for roughly twenty months," and that the cost of building capital buffers in the normal regime is "economically negligible" — no specific magnitude (e.g. bps or pp) is given in the excerpt itself.

## Action proposed
REFERENCE

Methodological validation of a regime-dependent effect using a threshold-VAR framework more rigorous than the ad hoc percentile flags used in L54's regime-overlay experiment; no direct instrument or dataset to test against an Algo_claude strategy.
