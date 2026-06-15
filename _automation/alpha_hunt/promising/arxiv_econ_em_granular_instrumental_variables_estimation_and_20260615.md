# Granular Instruments via Factor-Loading Complement: Identifying Aggregate Shocks from Cross-Sectional Data

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.14057v1
**Captured**: 2026-06-15 01:30 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: d30d6d25bd91c08ac0e4afbb640dc080

## Summary
The paper constructs valid instruments for models with latent aggregate shocks by exploiting the fact that idiosyncratic components span the orthogonal complement of the factor-loading space. This characterization allows building granular instrumental variables (GIVs) even when factor loadings are unknown and without requiring a large cross-sectional dimension — resolving a key limitation of the Gabaix-Koijen (2021) approach. The authors provide inference procedures, specification tests, and apply the framework to estimate the aggregate equity market multiplier (how much does a $1 shift in aggregate demand move equity prices). Empirical results show substantial heterogeneity in demand elasticities across investor sectors, offering qualified support for the inelastic-markets hypothesis.

## Why it might be useful
Two links. First, the `Equities/research/active/sector_hothand_propfirm/` project currently has a t_HAC alpha of 10.38 — flagged as a red flag in `_audit/sector_hothand_audit_2026-05-30.md` and the MDD at -13.3% already breaches the FTMO 10% floor. The GIV framework offers a diagnostic tool: if sector momentum returns are partly driven by aggregate demand shifts (a latent factor), OLS alpha will be overstated. Running the GIV projection — regressing sector returns on the idiosyncratic residual after removing the dominant factor loading — would give a cleaner estimate of whether the t_HAC=10 survives factor contamination, or if the signal is essentially a levered bet on aggregate equity demand. This is a robustness check, not a new signal. Second, the inelastic-markets mechanism implies that large institutional flows into specific sectors create persistent price pressure. If the sector hothand effect is demand-elasticity-driven rather than information-driven, it would behave differently around high-volume vs. low-volume periods — a quick subsample test worth pre-registering before the full audit.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
