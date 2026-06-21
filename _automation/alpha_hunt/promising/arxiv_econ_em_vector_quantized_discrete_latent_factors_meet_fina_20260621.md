# PRISM-VQ: Vector-Quantized Factor Model for Cross-Sectional Stock Ranking

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.13407
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 127e1291b9cff22e22f2e8249f96cd4a

## Summary
PRISM-VQ integrates expert factor priors (existing financial factors) with discrete latent factors learned via vector quantization (VQ) from cross-sectional return structure, and a Mixture-of-Experts (MoE) module that generates time-varying factor loadings conditioned on the VQ regime codes. The VQ bottleneck acts as noise suppression while providing routing signals for temporal regime specialization. Tested on CSI 300 and S&P 500 with reported improvements over baselines in cross-sectional return prediction and portfolio performance. Code available at https://github.com/finxlab/PRISM-VQ.

## Why it might be useful
The VQ bottleneck mechanism is conceptually related to the regime filter problem in Strategy D: discrete regime codes are explicitly a routing signal that determines which model sub-component to apply. However, PRISM-VQ targets cross-sectional equity ranking (N≥300 stocks, monthly or daily), which is outside our universe (crypto TSMOM on 3 assets, NQ intraday single instrument). The code availability is the main practical value. Background for the Equities sector hothand propfirm research (`Equities/research/active/sector_hothand_propfirm/`) where a small equity universe (N<30 sectors) would fail the L6 gate (N≥30 required for CS strategies) — PRISM-VQ does not resolve this.

## Extracted content
"Vector quantization acts as an information bottleneck that suppresses noise while capturing robust market structure, with discrete codes serving both as latent factors and as routing signals for temporal expert specialization."

Code: https://github.com/finxlab/PRISM-VQ

## Action proposed
REFERENCE

Cross-sectional equity ranking on large universe (CSI 300, S&P 500). No direct path to our active strategies. Keep as methodology reference for the VQ-as-regime-signal concept.
