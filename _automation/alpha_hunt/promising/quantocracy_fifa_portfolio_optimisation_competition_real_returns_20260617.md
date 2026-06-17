# FIFA Portfolio Optimisation Competition With Real Returns

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=sOV3obXAcM&source=feedburner
**Captured**: 2026-06-17 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: b45e40b4c4ac01329d34e20c5293ef3a

## Summary
This is the fourth post in a summer 2026 series on portfolio optimization, following a competition format (FIFA = Fitting and Forecasting Actual data). The series compares optimization methods on actual return data — likely varying between mean-variance, equal-risk-contribution (ERC), minimum-variance, and similar schemes. The "forecasting" component suggests the competition evaluates OOS portfolio performance rather than IS fit quality.

## Why it might be useful
The A+B book uses ERC (equal-risk-contribution) for the SR 2.31 calculation (`_audit/portfolio_recalc_2026-06-10.md`). A new strategy D must push the book above SR 2.54. The open question is whether the ERC risk-unit weighting is truly optimal vs. alternatives — the current ERC was chosen analytically under zero correlation assumptions (ρ_AB = 0.039). If this series provides a rigorous OOS comparison of ERC vs. other schemes on real data, it could either validate the current approach or reveal a more efficient weighting that lowers the bar for Strategy D. Specifically: with SR_A=1.33 and SR_B=2.0 and near-zero correlation, does mean-variance weighting materially outperform ERC? The book MaxDD is also not yet measured (pending 60d live B mainnet), so the optimization comparison on that dimension would be valuable once live data is available.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Read the full 4-post series when Strategy B mainnet goes live (~Jul 2026) and the book has ≥60 days of real returns to optimize. At that point, running the A+B allocation through the competition's methodology would yield a concrete comparison vs. the current ERC. Not actionable today since B mainnet data is not yet available.
