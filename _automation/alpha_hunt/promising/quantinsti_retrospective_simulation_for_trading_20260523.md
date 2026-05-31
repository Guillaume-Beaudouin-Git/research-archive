# Retrospective Simulation for Trading: Non-Parametric Brownian Bridge Path Generation

**Source**: quantinsti
**URL**: https://blog.quantinsti.com/retrospective-simulation-trading/
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 7c16224e0c5ae706bdded8ee04a5a467

## Summary
The article describes "retrospective simulation" — generating alternative historical price paths using a non-parametric Brownian bridge conditioned on observed start and end points. Unlike forward Monte Carlo, the Brownian bridge preserves the realized endpoints of the historical path while varying the trajectory in between. This allows testing whether a strategy's historical profits depended on the specific intraday price path (fragile) or would have survived a range of plausible alternative paths with the same terminal values (robust).

## Why it might be useful
Directly applicable to improving `Portfolio/risk/trailing_dd_simulator.py`, which is used for Tradeify propfirm evaluation (Strategy C, PROPFIRM_PASS gate). L22 identifies that the Gaussian generator in trailing_dd_simulator.py "materially overestimates bust probability for SL-capped strategies" — the Brownian bridge non-parametric approach would preserve the actual trade P&L distribution shape (including the SL-cap) rather than assuming Gaussian paths. Concretely: replace the Gaussian path generator in trailing_dd_simulator.py's eval phase with Brownian bridge paths conditioned on Strategy C's actual trade size distribution. This would give more accurate P(pass) estimates for the Tradeify challenge. CLAUDE.md also mandates block bootstrap (Politis-Romano) for trade clusters, but the Brownian bridge is a complementary alternative for within-trade path simulation.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for Python implementation of the Brownian bridge generator.

## Action proposed
TEST_LATER — Read full article for Python implementation of the Brownian bridge path generator. Integrate into trailing_dd_simulator.py as an alternative to the Gaussian generator to address the L22 known issue. 1-day effort. Hard-fail path (touches `Portfolio/` directory) — must go through human review per CI rules.
