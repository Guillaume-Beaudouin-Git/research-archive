# PIVOT: Differentiable Jäckel IV Solver Enabling End-to-End Neural Options Learning

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.17065
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 80d06bdd73df3cae5153cb99a4b4fd99

## Summary
Training neural networks whose objective is specified in implied volatility space while outputting prices (or vice versa) requires differentiating through the Black-Scholes inversion, but Jäckel's machine-precision solver is non-differentiable. PIVOT wraps the Jäckel solver in a differentiable layer using implicit differentiation, enabling gradient-based learning through the IV↔price interface. This allows end-to-end training with objectives formulated in IV space (where no-arbitrage constraints are natural) while producing price outputs (where market quoting occurs). Code is available at https://github.com/author/PIVOT.

## Why it might be useful
PIVOT enables a specific training objective that was previously blocked by non-differentiability: this is primarily relevant to machine-learning-based options pricing work. For the VRP short gamma track at `Crypto/research/active/vrp_short_gamma/` (currently blocked by L13 cost kill), if a vol-surface-based ML model were to be trained for BTC Deribit options, PIVOT would provide the differentiable bridge between the vol surface calibration (IV space) and option price prediction (price space). This is also relevant to the SABR residual correction paper (id=2605.06604 in this batch), which uses the same implicit differentiation principle. At current project priorities, there is no active use case requiring differentiable IV inversion.

## Extracted content
Code at https://github.com/author/PIVOT. Technical claim: wraps Jäckel solver in differentiable layer via implicit differentiation.

## Action proposed
REFERENCE

Options ML infrastructure paper; no active strategy uses options pricing models. File for potential VRP revival or FTMO CFD vol surface work.
