---
name: lesson-11-beta-dominance
type: finding
date: 2026-05-23
source: Phase 1 pre-flight — PMR/CS-FS/FRA research mission
status: PERMANENT (independent of PMR outcome)
---

# Lesson 11 — Long-Only Crypto CS Strategies Are β-Dominated

## Finding

Any long-only cross-sectional portfolio of crypto perpetual futures has portfolio-level
correlation ≈ 0.80–0.85 with Strategy A (TSMOM), regardless of signal-level orthogonality.

Tested signals: MAX factor (Liu & Tsyvinski analog), Amihud ILLIQ, funding-momentum proxies.
Signal-level correlations were low (<0.20 in all cases). Portfolio-level correlations
exceeded 0.80 in all cases.

## Root Cause

All top liquid crypto perps (BTC, ETH, SOL, XRP, DOGE, etc.) share β_crypto ≈ 0.65+.
Long-only CS selection — regardless of which factor drives the ranking — tends to concentrate
in large-cap coins with the highest β_crypto. Equal-weight or rank-weighted portfolios of
the top 5–10 coins by any factor are structurally correlated with the BTC factor.

TSMOM (Strategy A) is itself a long-only portfolio of the same universe, so any competitor
strategy drawing from the same universe will share the BTC component.

Signal-level Spearman IC can be statistically significant (t > 3) while the resulting
portfolio is nearly perfectly correlated with TSMOM at the portfolio level. IC measures
cross-sectional rank correlation, not cross-sectional exposure to the common factor.
A strategy can have IC = 0.09 and portfolio corr(A) = 0.81 simultaneously.

## Corollary — Residualization Does Not Fix This

Regressing the cross-sectional signal on TSMOM_28d and using the residual signal
preserves or improves IC (tested: MAX residual IC t = 3.72 vs raw t = 3.06). But the
portfolio-level correlation with TSMOM remains high (0.80+) because the realized holdings
still share β_crypto. Residualizing the SIGNAL is not the same as residualizing the
PORTFOLIO'S MARKET EXPOSURE.

## Escape Routes

Only two structural escapes exist:

1. **Delta-neutral execution**: Long top-K + short bottom-K in perps, or long perp /
   short spot pairs. The long and short legs cancel the common β_crypto factor.
   Portfolio-level corr(A) drops to < 0.10 by construction.
   This is why Strategy B (delta-neutral carry) has corr(A,B) = 0.039.

2. **Very selective, infrequent positioning**: Sometimes hold 0–2 coins with high-
   confidence entries, large cash allocation. Strategy C (XGBoost CS) achieves
   corr(A,C) ≈ 0.37 this way — still above |ρ| < 0.3 target, accepted as an exception.

## Implication for Future Research

**Any new strategy with |ρ| < 0.3 constraint vs Strategy A must use delta-neutral
execution.** Testing long-only CS signals is valid for IC discovery but should not
proceed to portfolio simulation without delta-neutral execution design.

Pre-flight screen (PHASE 1): reject long-only CS angles before backtesting.
Confirmed by 5 failed CS angles in this research cycle.

## Empirical Data (2024-01-01 → 2026-05-22, Binance perps, N=29 coins)

| Signal | IC t-stat | Signal corr(A) | Portfolio corr(A) |
|--------|-----------|----------------|-------------------|
| MAX factor | 3.06 | -0.384 | **0.81** |
| ILLIQ factor | 3.60 | +0.131 | **0.84** |
| MAX residual | 3.72 | ~0.00 | **0.80+** |

All delta-neutral designs tested (CS-FS, PMR, FRA) show portfolio corr(A) < 0.08.
