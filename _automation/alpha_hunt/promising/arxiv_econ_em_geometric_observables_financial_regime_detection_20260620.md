# Geometric Observables for Financial Regime Detection: Berry Phase and Spectral Entropy

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.17117
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: bb381ffbaa5d81cdc1ef735bf8aa35f8

## Summary
This paper extracts four geometric observables from a spectral embedding of equity-index returns — Berry Phase Rate, Spectral Entropy, Reduced State Purity, and Hamiltonian Sensitivity — and evaluates them as regime-shift detectors against 46 classical and ML baselines on 17 historical crises from 2000–2024. Under nested walk-forward hyperparameter selection on 9 labelled windows, the Berry Phase Rate achieves an out-of-sample median Cohen's d = 0.72 (top quartile among all 47 methods). The geometric framework draws on quantum mechanics concepts applied to financial correlation matrices.

## Why it might be useful
The Berry Phase Rate — a measure of rotation speed in the spectral embedding of the correlation matrix — is a novel regime indicator that could serve as a pre-trade filter for Strategy D (D3/D5 combo). The walk-forward validation on 17 historical crises (2000–2024) is rigorous, and the Cohen's d = 0.72 is non-trivial. However, implementation requires computing the spectral embedding of correlation matrices in real time — computationally feasible but more complex than the VVG Classifier (paper 056537d9). The 17-crisis OOS evaluation is a stronger test than the VVG paper's MNQ-specific validation. For the portfolio level, Berry Phase Rate could serve as a market-wide regime indicator for adjusting A+B positioning.

## Extracted content
Four observables: Berry Phase Rate, Spectral Entropy, Reduced State Purity, Hamiltonian Sensitivity. Evaluated against "46 classical and ML baselines on 17 historical crises spanning 2000–2024." "Berry Phase Rate achieves unbiased out-of-sample median Cohen's d = 0.72 (95% percentile)" among 47 methods. Walk-forward nested hyperparameter selection on 9 labelled windows.

## Action proposed
TEST_LATER

Implement Berry Phase Rate on daily index returns available in `data/deep_history_utc/` (US500, US100, GER40, 2007–2026). Test as a market-wide regime filter for D3/D5 on NQ data. Implementation cost: ~2 days (spectral embedding + rolling computation). Pre-register: "Berry Phase Rate in top quartile → reduce D3/D5 position size by 50%." This would be a regime overlay consistent with L15 criteria.
