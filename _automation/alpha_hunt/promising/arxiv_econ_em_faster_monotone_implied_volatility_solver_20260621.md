# ThiopheneIV: Fast Monotone Black-Scholes Implied Volatility Solver

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.22427
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 145a957fb5fd9832916bf3182792e1bb

## Summary
ThiopheneIV is an implied volatility solver for Black-Scholes that guarantees monotone convergence from below without overshoot, using a Choi-Huh-Su lower-bound seed plus three Euler-Chebyshev iterations. The solver handles production edge cases (parity normalization, Bachelier-limit near zero, saturated prices, fallback seeds) and includes an optional Jäckel-Newton polish. The core theoretical contribution is a formal proof that the Euler-Chebyshev map increases monotonically without crossing the solution, giving clean error bounds and predictable convergence.

## Why it might be useful
We have no active options strategies, and the archived VRP arc (L13: BTC VRP gross 4.4%/yr vs costs 8.9%/yr) is closed. This solver is relevant only if an options VRP or vol surface strategy is reconsidered, which requires paid Deribit data. Background reference for SPX VRP archives (`Options/` — currently not active). No connection to Strategies A/B/C/D.

## Extracted content
"The solver starts from the non-iterative Choi-Huh-Su L3 lower-bound seed and applies three Euler-Chebyshev corrections. In exact arithmetic, the seed is below the admissible root and the Euler-Chebyshev map increases monotonically without overshooting; the proof is included."

No code available in excerpt. Implementation described in prose.

## Action proposed
REFERENCE

Options pricing utility with no path to current active strategies. File for future reference if options trading is reconsidered.
