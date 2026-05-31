# The Attention Factor: The Cross-Asset Link Between Crypto and Public Equity Markets

**Source**: quantpedia
**URL**: https://quantpedia.com/the-attention-factor-the-link-that-connects-crypto-and-public-equity-markets/
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: dc5b7e5b04f4c9f1532cb7ae72d7dccc

## Summary
Harin de Silva's paper "The Attention Factor: The Speculative Risk You May Already Own" identifies a transmission channel between crypto and public equities driven by a speculative cohort of retail investors who shift between BTC, zero-day-to-expiration (0DTE) options, commission-free brokerage accounts, and social-sentiment-driven equities. The author constructs an "Attention factor" — a capital-backed measure of collective speculative conviction — and shows it explains residual cross-asset price connectedness after controlling for standard macro factors. The post argues that conventional equity risk models that ignore this channel systematically underestimate portfolio exposure.

## Why it might be useful
The Attention factor directly affects Strategy A (crypto TSMOM, BTC/ETH/SOL): if speculative retail flows drive co-movement between crypto and equity momentum names, then Strategy A's β_crypto exposure may be partially explained by the Attention factor rather than pure crypto fundamentals. This is important for the portfolio construction in CLAUDE.md (A+B+C ERC, theoretical Sharpe 2.24) — if A and C (NQ opening momentum) both load on the Attention factor, the correlation between them is higher than naive cross-asset analysis suggests. Also relevant to L11 (β-dominance): the Attention factor could be the mechanism by which long-only crypto CS strategies have corr_A ≥ 0.80 regardless of signal. No direct test path — this is a portfolio risk framework tool — but understanding the Attention factor should inform the correlation assumption in Portfolio/state/portfolio_state.py.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full academic paper needed for the Attention factor construction methodology.

## Action proposed
REFERENCE — Portfolio risk management context. Read the underlying de Silva paper to assess whether the Attention factor materially changes the A+B+C correlation matrix used in ERC sizing. No new strategy signal.
