# Dual vs. Single Momentum in Commodities: Adding an Absolute Trend Filter to Relative Strength Rankings

**Source**: quantpedia
**URL**: https://quantpedia.com/dual-vs-single-momentum-in-commodities-enhancing-risk-adjusted-returns-through-absolute-trend-filtering/
**Captured**: 2026-06-15 15:00 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 45171dd9b8bb1db2923e8a694898127c

## Summary
The paper tests whether layering a time-series (absolute) trend filter on top of a cross-sectional (relative) momentum ranking improves performance in commodity markets. Using four sector ETFs (agriculture DBA, base metals DBB, energy DBE, precious metals DBP) over 2007–2026, it finds that pure relative momentum is highly parameter-sensitive and inconsistently outperforms an equal-weighted benchmark. Adding an absolute trend screen — essentially going flat when the asset is below its own momentum threshold — structurally reduces tail drawdowns and delivers benchmark outperformance across all tested parameter combinations. The key claim is that dual momentum makes results more robust and less parameter-dependent than standalone cross-sectional ranking.

## Why it might be useful
This maps directly onto the active **Commodities XS — Basis + TSMOM** research (`Commodities/research/active/xs_basis_tsmom/`), which is building exactly the S_TSMOM + S_BASIS two-signal stack on 24 continuous contracts. The paper's empirical result — that combining XS ranking with a TS filter makes the system parameter-agnostic — is a testable hypothesis for the futures version: once Phase A (roll validation + data fetch) completes, a natural Phase B step would be to compute the dual-momentum portfolio and compare Sharpe stability across lookback parameters versus XS-only. **Critical caveat**: this paper uses ETFs (DBA/DBB/DBE/DBP), not continuous futures — L5 applies (ETF roll drag contaminates momentum signals on commodity ETFs). The archived "Commodity TSMOM ETF (Sharpe 0.39, AMTP p=0.808)" is likely suffering the same contamination. Do NOT replicate on ETFs; replication must use the 24-contract continuous futures universe already planned. The N=4 ETF universe also falls far below the N≥30 methodology floor. The economic intuition to carry forward: XS ranking alone forces holding "least-declining" assets in bear markets — the TS filter exits those, which should show up as a reduction in MaxDD when tested on the futures universe.

## Extracted content
No code, formulas, or specific numeric claims (Sharpe, MaxDD, %) in the excerpt. Full article needed for further extraction. The description mentions only qualitative findings ("universally outperforms," "structurally mitigates drawdowns," "parameter-agnostic framework") without reporting Sharpe ratios, MaxDD levels, or parameter grids used.

## Action proposed
TEST_LATER — The dual-momentum principle (XS rank + TS absolute filter) should be added as a Phase B hypothesis in `Commodities/research/active/xs_basis_tsmom/` once Phase A (data + roll validation) completes. Replicate only on the 24 continuous futures universe, not ETFs. Pre-register the specific parameter grid (lookback window candidates) before running to protect the DSR budget. No action until Phase A is complete.
