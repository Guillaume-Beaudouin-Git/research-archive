# Discovery under Hypothesis Redundancy: A Geometric Theory of Discovery Rate

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.14386
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 3737be89e8c9a133

## Summary
Scientific discovery saturates when new hypotheses cease to provide independent information. The paper formalizes this via a geometric theory in a reproducing kernel Hilbert space: the effective number of independent discoveries grows as the square root of hypotheses tested when they are highly correlated, recovering Bonferroni penalization as a special case. The authors propose Geometric FWER (G-FWER), an adaptive testing procedure that controls familywise error rate while crediting hypotheses for their orthogonal contribution.

## Why it might be useful
This paper addresses multiple testing correction — directly relevant to the AMTP methodology used throughout Algo_claude (n_tests=321 global ledger, AMTP mandatory when n_tests>1). G-FWER's RKHS angle-based approach could be more powerful than flat AMTP when tested hypotheses are correlated (e.g., NQ intraday variants D1-D5 all share the same instrument and data). The methodology could inform how to credit partially-overlapping signal families in the global n_tests ledger. However, implementation requires the RKHS kernel structure across test families, which is not trivially available from current data, and AMTP remains the canonical tool per hard rules.

## Extracted content
- Key result: effective independent discoveries ∝ √(n_tests) under high correlation, recovering Bonferroni as special case
- Procedure: Geometric FWER (G-FWER) controls FWER while crediting orthogonal contribution via RKHS angles

No verbatim code or formulas in the excerpt.

## Action proposed
REFERENCE
