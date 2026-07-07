# Quantpedia API as an On-Demand Factor Database

**Source**: quantpedia
**URL**: https://quantpedia.com/quantpedia-api-as-an-on-demand-factor-database/
**Captured**: 2026-07-07 10:30 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 2113eb1495f02a72eee0404f6433dc61

## Summary
Quantpedia frames a common allocator problem: you receive an opaque equity curve — a fund track record or manager-reported return series — with only a vague description of what drives it, when in reality it may blend momentum, tactical allocation, defensive overlays, and cross-asset rotation. Rather than using the built-in Quantpedia Pro multi-factor report, the case study builds a custom pipeline through the Quantpedia API and an AI-assisted methodology: the curated Quantpedia strategy library becomes a bank of candidate "factors," and the workflow searches for the combination that best explains the unknown curve's behavior. The test was run blind — the true composition was withheld during the analysis — so it checks whether an API-driven decomposition can actually recover a strategy mix rather than just curve-fit after the fact. This is a methodology demonstration (returns-based style analysis, generalized to a large factor library), not a specific tradable signal; no Sharpe, MaxDD, or fit-quality numbers appear in the excerpt.

## Why it might be useful
This is the same idea CLAUDE.md already codifies as L38 (beta-orthogonal test: regress a "structural premium" sleeve on a vol-targeted buy-and-hold of its primary asset and report β, α_HAC, R²) — just generalized from one benchmark to a whole library of candidate explanatory strategies (Sharpe-style returns-based style analysis). It maps onto two concrete internal gaps without needing a Quantpedia subscription, since Algo_claude already holds its own candidate basis: (1) Strategy A's live equity curve (HL testnet daily fills + frozen Propr history since 2026-05-11) has no formal results.json validation artifact — CLAUDE.md flags the cited Sharpe 1.33 / MaxDD -6.9% as sourced only from a docstring. Regressing A's realized daily returns against a small local basis (spot BTC/ETH/SOL buy-and-hold, a rebuilt 28d tanh-momentum proxy) would independently check whether the live curve still matches the claimed long-only TSMOM signal or has drifted, filling the gap the missing artifact leaves open. (2) Strategy B is ~10 days from its ~2026-07-17 mainnet review (L14: testnet Sharpe 9.64 is inadmissible, proxy SR=2.0 used instead) — the same regression-against-known-factors logic applied to B's realized 8h returns against spot legs of its active pair(s) would give a live, out-of-sample β estimate and could catch beta leakage (L11 long-only β-dominance) that the testnet-inadmissibility caveat alone can't detect.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — the method itself (regress a strategy's realized returns on a small local factor basis, HAC SE) is cheap, but it needs a cleaned, unified daily return series for A (mixed Propr + HL testnet, frozen since 2026-05-11) and B (8h rebalance, rotating active pair) assembled first; best timed just ahead of the B mainnet review (~2026-07-17) rather than run now.
