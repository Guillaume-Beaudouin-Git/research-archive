# The Sharpe Ratio of Pure Noise

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=CK8nimr2sw&source=feedburner
**Captured**: 2026-06-17 06:00 UTC
**Filters passed**: L1=[trading_topic, metrics], L2_OK
**Hash**: 0f89180ffe5c02d1da66f09a45561759

## Summary
The authors ran 2,000,000 backtests on strategies built from pure random noise — zero true edge by construction — and mapped the resulting Sharpe ratio distribution. The exercise quantifies how often random backtests produce impressive-looking Sharpe ratios by luck alone, giving an empirical null distribution against which real strategies can be compared. This is an applied illustration of the multiple-testing problem: the best Sharpe out of N random trials grows predictably with N, independent of any true signal.

## Why it might be useful
This maps directly to the Algo_claude AMTP and DSR enforcement policy. At n_tests = 321 globally (ledger), the research book is exactly the regime where a random null distribution from 2M backtests is most instructive: how many of those 321 tests would look "significant" purely by overfitting? The finding is directly applicable to the sector_hothand audit (t_HAC = 10.38 flagged as red flag, `_audit/sector_hothand_audit_2026-05-30.md`) — comparing its Sharpe against an empirical null would quantify how implausible it is. Practically: use the article's null distribution to stress-test any strategy in the PROPFIRM_PASS gate (Sharpe > 1.0) by asking what fraction of pure-noise strategies at N_tests would clear the gate.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Background validates the methodological discipline already in place (AMTP, DSR, HAC). Useful as a citation to anchor the sector_hothand audit argument, but no new test warranted.
