# No-Arbitrage Constrained Deep Learning for Implied Volatility Surface Reconstruction

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.24031
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 30a68f5fc01e93304a555f23c59d779a

## Summary
This paper compares multiple neural architectures—MLPs, CNNs, U-Nets, variational autoencoders, and Transformer-based models—for reconstructing implied volatility surfaces from sparse and noisy option quotes, under no-arbitrage constraints enforced via penalty terms in the loss function (butterfly and calendar-spread constraints). Transformer and U-Net architectures achieve the strongest reconstruction accuracy, especially under sparse data conditions. The penalty-based no-arbitrage approach is contrasted with classical SVI parameterizations.

## Why it might be useful
This paper is relevant to the VRP short gamma research at `Crypto/research/active/vrp_short_gamma/`, which would require a calibrated BTC Deribit vol surface, but that track is blocked by L13 (costs kill the edge). If VRP were reconsidered, this Transformer/U-Net approach would provide the surface calibration infrastructure. More immediately, the sparse-data reconstruction finding (Transformer architecture outperforms under sparse quotes) is relevant to the ZN Baltussen bond futures research at `Futures/research/active/zn_baltussen/`, where treasury options are thinly traded and a regime filter based on rates vol surface would suffer from data sparsity. The no-arbitrage constraint methodology is also directly applicable to Strategy D if options-based regime filters are considered.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Options vol surface reconstruction; no active strategy uses options. File for VRP potential revival and ZN Baltussen regime filter consideration.
