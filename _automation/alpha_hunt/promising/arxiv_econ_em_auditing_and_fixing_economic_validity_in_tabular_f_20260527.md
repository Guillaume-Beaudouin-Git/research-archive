# Auditing and Fixing Economic Validity in Tabular Foundation Models for Discrete Choice

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.26559v1
**Captured**: 2026-05-27 12:08 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 4cd0d4b120c609b6fa52eaf01cf33c33

## Summary
Large tabular foundation models can achieve high accuracy on discrete choice prediction (e.g., transportation mode selection) but frequently produce economically incoherent outputs — raising a price may increase predicted demand, implied willingness-to-pay becomes negative. The paper proposes wrapping foundation model outputs inside a constrained utility-maximization layer, recovering up to 13 percentage points of accuracy over a standard logit model while guaranteeing monotonic price-demand relationships. The two-stage adapter freezes the economically constrained parameters in stage one, then trains a correction term using the foundation model's predictions in stage two.

## Why it might be useful
The mechanism — constraining a flexible model to satisfy domain-specific monotonicity — has a loose parallel to CLAUDE.md's mandate for signal monotonicity in cross-sectional strategies (quintile monotonicity check in the mandatory script fixes). However, the application is consumer choice in transportation, not financial markets, and there is no direct path to any active strategy. The closest conceptual hook is the Commodities XS research: if a factor model for commodity roll returns produces non-monotonic price-return relationships, a similar constraint wrapper could enforce structural priors. That said, this is speculative and the paper offers no financial data results.

## Extracted content
The author claims recovery of "up to 13 percentage points of accuracy over a standard logit model" on two transportation datasets while maintaining "perfect economic consistency."

## Action proposed
REFERENCE
