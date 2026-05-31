# Beyond the Hype: What Statistical Independence Really Means for Trading Strategies

**Source**: quantinsti
**URL**: https://blog.quantinsti.com/independent-events/
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[trading_topic, methodology], L2_OK
**Hash**: e349eb48ea1846ff2c44d64e756f2a5b

## Summary
The article clarifies the distinction between statistical independence, correlation, and cointegration in the context of trading signal design and portfolio construction. It works through practical examples showing how traders misapply independence assumptions — for instance, treating successive trades as iid when autocorrelated signals are used, or conflating zero correlation with independence. The discussion covers implications for position sizing, event-count inflation, and the dangers of overcounting effective sample size when trades cluster in time.

## Why it might be useful
This concept underpins two mandatory methodology requirements in CLAUDE.md. First, the HAC lag-6 correction (Newey-West, t > 2.5 threshold) is required precisely because trading signals are serially correlated: nominal N overstates N_eff, as quantified in L12b (ETH netflow: naive t=2.58 → HAC t=0.11, N_eff≈73 from 3398 events). Strategy C (NQ ORB, N=346 trades) already applies HAC throughout, but this article could surface additional diagnostics useful before paper trading begins. Second, the cointegration versus correlation distinction is directly relevant to the active Commodities XS basis research (`Commodities/research/active/xs_basis_tsmom/`), where spread stationarity — not mere low correlation — is the prerequisite for a tradeable basis signal (Erb-Harvey 2006). The iid-versus-clustered distinction also matters for the block bootstrap (Politis-Romano) required by CLAUDE.md methodology when trade clusters exist.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — Background on statistical independence and its trading implications. Reinforces the HAC/AMTP methodology already embedded in CLAUDE.md hard rules. No new test path opened.
