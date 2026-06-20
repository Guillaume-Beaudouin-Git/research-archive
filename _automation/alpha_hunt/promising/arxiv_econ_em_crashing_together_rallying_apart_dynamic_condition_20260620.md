# Asymmetric Tail Dependence in Crypto: Crashing Together, Rallying Apart

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.16840
**Captured**: 2026-06-20 10:02 UTC
**Filters passed**: L1=[methodology, metrics], L2_OK
**Hash**: 031117c197aab946086227d50ca399c0

## Summary

Mallela & Leonelli analyze joint tail dependence for the 13 largest cryptocurrencies over 89 overlapping windows spanning late 2021 to 2025, using dynamic Hüsler-Reiss graphical models of extremes. The lower-tail graph (joint crash structure) is near-complete and stable over time — all cryptos crash together. The upper-tail graph (joint rally structure) thins over time into emerging sectoral clusters. Standard covariance-based risk models underestimate market-wide crash probabilities by roughly 8× because they use symmetric correlation matrices that fail to capture asymptotic tail dependence. Ordinary diversification across crypto assets effectively fails during drawdowns — the cross-asset "diversification" benefit collapses exactly when it is most needed.

## Why it might be useful

Strategy A (TSMOM v3: BTC/ETH/SOL, long-only) and Strategy B (delta-neutral carry: HMSTR on HL testnet) both operate in the crypto space. The finding that all cryptos crash together (complete lower-tail graph) has two direct implications: (a) Strategy A's 3-asset diversification across BTC/ETH/SOL offers near-zero downside protection — all three drop simultaneously in crash scenarios, consistent with L11 (β-dominated long-only crypto = corr_A ≥ 0.80). The hard guardrails (MAX_TOTAL_DD=5.5% on Propr, MAX_DAILY_DD=2.8%) are the right defense since diversification doesn't help. (b) The book-level correlation ρ_AB=0.039 (full-sample) used in the SR 2.31 computation is a full-sample average; this paper suggests ρ_AB in crash scenarios may be much higher — HMSTR and BTC/ETH/SOL would likely all suffer simultaneously in a market-wide crypto crash, collapsing the book's tail diversification. This is directly relevant to the "MaxDD book: à mesurer sur ≥60j live B mainnet" note in CLAUDE.md.

## Extracted content

From abstract:
- "standard covariance-based metrics fail to capture asymptotic tail dependence, they systematically understate systemic risk and overstate diversification benefits precisely when markets crash."
- "results reveal a near-complete and stable lower-tail graph, an upper tail that thins over time to re-form sectoral structures"
- "intra-crypto diversification fails on the downside, standard risk models underestimate market-wide crash probabilities by roughly eight-fold"

No code in excerpt. Full article needed for Hüsler-Reiss model specification and the empirical graphs.

## Action proposed

REFERENCE

Validates known structural features of crypto markets (consistent with L11). No immediate test needed — our guardrails already account for this by design. Flag for use when computing proper tail-risk metrics for the A+B book once Strategy B has sufficient mainnet history (target: ~2026-07-17). At that point, use this paper's methodology to estimate ρ_AB in the joint lower tail rather than relying on the full-sample linear correlation.
