# Hour-Aware Risk Management for Autonomous Crypto Trading: Empirical Fragility Study

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.08232
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: b270243f79da88fa40ad4b27978fb2d8

## Summary
A 15-day paper-trading deployment (190 trades, March 29 – April 12 2026) of an autonomous memecoin trading bot on Solana DEXes. The system achieved a 40.5% win rate, mean per-trade return of +0.62%, and cumulative +117.7% (net +0.039 SOL). However, the distribution was severely fat-tailed: skewness -1.21, excess kurtosis 6.61. A Mann-Whitney test for hour-of-day effects on the three worst UTC hours (2, 13, 23) was directional but not significant (p=0.22) at N=190. Critically, removing the top 3 trades flips the result to unprofitable — structural fragility documented explicitly. A parallel rejection-tracking system found that 26% of rejected tokens reached ≤50% of reference price within 24 hours, supporting that the filter stack adds value.

## Why it might be useful
Strategy B (delta-neutral carry on Hyperliquid) currently rebalances at 00:10, 08:10, 16:10 UTC. The hour-of-day significance test in this paper is directly applicable: run an equivalent Mann-Whitney test on Strategy B's 8h fill P&L by UTC hour slot to check whether one of the three windows systematically underperforms — this could justify rescheduling one rebalance window. The 26% "rejected tokens crashed" filter validation methodology is also transferable: our VIABLE_ASSETS list in Strategy B is updated with similar criteria, and this paper provides a simple counterfactual test structure to verify filter value. The fragility analysis (top-3-trades flip) is a direct parallel to L14 (N<250 inadmissible) and should be applied to Strategy B's testnet fills: currently N<250, so the per-rebalance P&L distribution may be similarly fragile. Data available: `logs/fills.csv` on VPS.

## Extracted content
"The 190-trade sample (March 29 to April 12, 2026) shows a 40.5 percent win rate, mean per-trade return of +0.62 percent, cumulative +117.7 percent (net SOL +0.039), skewness -1.21, excess kurtosis 6.61."

"A Mann-Whitney U test of three poorest-performing UTC hours (2, 13, 23) against the others yields U = 1,274, p = 0.22; directional but not significant at n = 190."

"Removing the top three trades (1.6 percent of sample) flips cumulative return unprofitable. Profitability rests on a small number of large winners and is structurally fragile."

Dataset DOI: 10.5281/zenodo.20043302 (CC-BY-4.0).

## Action proposed
TEST_LATER

Apply Mann-Whitney hour-of-day test to Strategy B VPS fill logs (pull `logs/fills.csv`, extract UTC hour, test 00:10 vs 08:10 vs 16:10 slots). This is a 1-hour analysis. But with current testnet N likely <100, the test will be underpowered — file this for mainnet launch (~July 2026). LATER also because the memecoins context (Solana DEX) is far from our HL perp delta-neutral setup; the methodology ports but the base effect sizes may differ entirely.
