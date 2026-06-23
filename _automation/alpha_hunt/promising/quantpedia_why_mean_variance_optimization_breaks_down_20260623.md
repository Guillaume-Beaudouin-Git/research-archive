# Why Mean-Variance Optimization Breaks Down in Practice

**Source**: quantpedia
**URL**: https://quantpedia.com/why-mean-variance-optimization-breaks-down/
**Captured**: 2026-06-23 14:00 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 9fbe2e41a03d235060d71d79f8ae3101

## Summary

Plug-in Mean-Variance Optimization (MVO), where sample-estimated returns and covariances are fed directly into the Markowitz solver, does not simply carry estimation error into portfolio weights—it actively magnifies it. The mechanism is geometric: the inverse-covariance operator concentrates extreme weights on directions that appear low-variance in finite samples, yet these directions are precisely those dominated by sampling noise rather than genuine signal. The result is a well-documented backtest-to-live gap where backtests look exceptional but live portfolios are over-leveraged and unstable. The VertoxQuant analysis frames this as a fundamental statistical pathology of the optimizer itself, not a data quality issue that better inputs would fix.

## Why it might be useful

This article validates the ERC (Equal Risk Contribution) 50/50 weighting already in production for the A+B book (`_audit/portfolio_recalc_2026-06-10.md`, SR 2.31). Had raw MVO been used instead, the short history of Strategy B (proxy SR 2.0 estimated from mainnet simulation, L14 inadmissible testnet data) would be especially susceptible to the error-amplification described here—a single noisy covariance estimate between two barely-correlated strategies (ρ_AB=0.039) would push the optimizer toward an extreme allocation. When Strategy D is evaluated for book inclusion (gate: SR(book+D) > 2.54, `Portfolio/state/portfolio_state.py`), the question of *how* to size the three-way allocation will arise; this paper is a direct pre-read for that decision—use shrinkage estimators (Ledoit-Wolf) or ERC rather than MVO. Methodologically, the error-amplification argument is the portfolio-construction analogue of the DSR/AMTP discipline already applied to signal evaluation: in-sample optimization overfits regardless of whether the optimization target is Sharpe (signal selection) or portfolio weights (MVO).

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

REFERENCE

Background read before any future portfolio rebalancing or Strategy D book-integration work. Confirms ERC is the right tool for the current 2-3 strategy book given estimation uncertainty; MVO would be particularly fragile with B's short live track record and the sparse covariance matrix at N=2-3 strategies.
