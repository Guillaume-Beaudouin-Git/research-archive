# Incremental SVD for Large-Scale Dynamic Matrices: Accuracy, Subspace Stability, and Applications

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.24514
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: d31d33635cc93cc6d6f75a0890fc4d0c

## Summary
Brand-style incremental SVD is studied systematically, supporting row/column appends, rank-1 entry updates, and subspace stability monitoring in a unified engine. Two contributions are: a subspace stability metric detecting when incremental updates degrade quality, and criteria for deciding when full recomputation is warranted. Motivated by return panels and covariance matrices that change incrementally.

## Why it might be useful
The Commodities XS research (24 contracts, monthly CS IC scans) needs efficient rolling covariance updates; Brand incremental SVD handles this without full recomputation. The sector_hothand_propfirm rolling return panels also benefit: one new month appended to a 12×24 return matrix is handled incrementally rather than from scratch. The subspace stability diagnostic is useful for detecting when the A+B correlation matrix (ρ_AB=0.039) drifts, triggering a reallocation review. Implementation: 1 day using scipy's existing SVD routines as base.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Implement Brand incremental SVD for rolling covariance in Commodities XS (24 contracts) and sector_hothand; 1 day, scipy available.
