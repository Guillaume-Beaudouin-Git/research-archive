# Generalized Impulse Responses of Portfolio Default Probabilities: A Modular Framework with an Application to Geopolitical Risk

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2608.04469v1
**Captured**: 2026-08-06 03:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: b4fafbc35efa33ccf3b747fc91c57a5d

## Summary
Derives closed-form generalized impulse responses for portfolio default-probability statistics (mean, quantiles/PD-at-Risk, expected shortfall) by combining a Bayesian VAR, a Gaussian satellite model, and the Merton-Vasicek credit model underlying Basel bank-capital regulation, applied to US geopolitical-risk shocks. Shows the responses are strongly nonlinear — a naive plug-in evaluation understates projected default probabilities by 6-8% and misses tail quantiles, with 99%-quantile responses exceeding mean responses by 50% and peak responses varying 4.6x across the credit cycle.

## Why it might be useful
No direct tie — Algo_claude has no credit/bond sleeve and no default-probability exposure in any active or live strategy; the paper's actual machinery (Merton-Vasicek, Basel IRB) is specific to credit portfolios and not directly reusable. The one transferable point, filed honestly as weak: the general finding that a linear/plug-in impulse response systematically understates tail response versus the true nonlinear one is a generic caution applicable to the project's own tail-risk work (Strategy C's MaxDD sizing, the barrier/p(pass) simulator).

## Extracted content
No code. Numeric claims (author's): plug-in evaluations "understate projected default probability levels by 6-8%"; "99%-quantile responses exceed mean responses by 50%"; "peak responses vary 4.6-fold across the credit cycle."

## Action proposed
REFERENCE.
