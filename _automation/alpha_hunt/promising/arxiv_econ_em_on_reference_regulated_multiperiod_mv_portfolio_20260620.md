# Reference-Regulated Multiperiod Mean-Variance Portfolio Optimization in High Dimensions

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.13697
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[metrics, methodology], L2_OK
**Hash**: 95eb8a2103eb2d877c5abaa9bd398cc4

## Summary
The RRMV (Reference-Regulated Mean-Variance) framework penalizes deviations from a reference policy (e.g., equal-weight or market portfolio) to control estimation error in multiperiod portfolio optimization. By anchoring the dynamic strategy to a robust reference, the framework avoids the instability of unconstrained multiperiod MV that compounds estimation errors across periods. The key result: in high dimensions (N >> T), the RRMV converges to the closed-form solution of the reference policy while in low dimensions (N << T) it approximates the true MV optimum. The framework includes a closed-form adaptive regularization parameter calibrated on the cross-sectional return distribution.

## Why it might be useful
The A+B book uses ERC weighting with a 2-strategy universe (N=2, T → ∞ as strategies accumulate live history). RRMV is more relevant when Strategy D is added (N=3 or more) and the estimation error on cross-strategy correlations becomes non-trivial. The reference-to-ERC anchoring concept is directly applicable to the portfolio_state.py logic: when Strategy B's live data is sparse (just launched mainnet), anchor B's weight to the ERC reference to avoid instability. The framework also has closed-form adaptive regularization — no hyperparameter tuning needed. Implementation in Python using the formula from Appendix A of the paper is ~1 day.

## Extracted content
RRMV: "penalizes deviations from a reference policy." Closed-form adaptive regularization. "Penalizing deviations from a reference policy successfully combines the advantages of dynamic strategies and reference portfolios." Closed-form solution in high and low dimension limits. No specific Sharpe numbers given in abstract.

## Action proposed
REFERENCE

Apply RRMV regularization concept to `Portfolio/state/portfolio_state.py` when B mainnet data is available and Strategy D is added (book becomes N=3). Use ERC as the reference policy with adaptive regularization. Implementation: read Appendix A for closed-form formula. ~1 day implementation cost. Cross-reference with `_audit/portfolio_recalc_2026-06-10.md`.
