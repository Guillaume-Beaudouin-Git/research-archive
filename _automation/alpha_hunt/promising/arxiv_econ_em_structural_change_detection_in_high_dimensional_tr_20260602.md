# Structural Change Detection in High-Dimensional Factor Models via Canonical Correlation

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.01553v1
**Captured**: 2026-06-02 06:06 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: f00696e68f1a3087872bd5b1d47b6d5c

## Summary
This paper proposes an eigenvalue-ratio criterion for detecting structural breaks in high-dimensional factor models by exploiting the canonical correlation (CCA) structure of the return panel. In a dynamic factor model, common factors produce non-zero canonical correlations between two time windows; a break in factor loadings (regime change) produces a detectable shift in the residual canonical correlation spectrum in the estimated noise subspace. The authors develop an alternating iterative algorithm that jointly estimates the break date and regime-specific factor counts, deriving asymptotic properties under mixing and moment conditions. Empirical applications include intraday U.S. stock returns and a temperature series, demonstrating finite-sample performance via Monte Carlo.

## Why it might be useful
Two active research items could directly benefit from this methodology. First, the sector_hothand_propfirm strategy (`Equities/research/active/sector_hothand_propfirm/`, currently in audit at `_audit/sector_hothand_audit_2026-05-30.md`) has a flagged t_HAC=10.38 alpha stat — a plausible explanation is a regime break in cross-sectional equity returns (e.g., 2020 COVID shock or 2022 rate cycle shift) that inflates the in-sample IC when the WF windows straddle the break. Running this CCA-based break test on the sector equity return panel would either confirm or rule out structural change as the source of the anomalous t-stat, which is the audit's open question. Second, Strategy D (`Futures/research/active/strategy_d/`) is seeking a regime filter to combine individually failing D3 (mid-fade, SR=-1.08) and D5 (afternoon squeeze, SR=-1.32) signals. The eigenvalue-ratio approach applied to rolling 63-day windows of NQ 1-min returns (local dataset `Dataset_NQ_1min_2022_2025.csv`) would yield a model-free break-date series to test whether D3/D5 performance is regime-conditional. Concrete implementation: extract rolling canonical correlations on a 2-window split of the NQ intraday return panel, compute the eigenvalue-ratio statistic, flag break dates, and measure D3/D5 performance in each regime. Estimated effort: 1-2 days after reading Section 3 of the full paper.

## Extracted content
Key claim from abstract: "Monte Carlo experiments and empirical applications to intraday stock returns and U.S. temperature series demonstrate the finite-sample [performance of the proposed estimators]." (sentence truncated in excerpt)

No code or formulas reproduced in the excerpt. The eigenvalue-ratio criterion and alternating iterative algorithm are in the full paper at http://arxiv.org/abs/2606.01553v1.

## Action proposed
TEST_LATER — Implement eigenvalue-ratio break detection on rolling 63-day NQ 1-min windows as a regime signal for Strategy D (D3+D5 combination). Also run on sector equity return panel to resolve the sector_hothand t-stat=10 audit question. Prerequisite: read Section 3 of the paper (algorithm spec). Estimated effort: 1-2 days.
