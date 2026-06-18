# Tracking Brazil's Real Neutral Rate: A Multi-Block Ensemble Framework

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.19000v1
**Captured**: 2026-06-18 02:00 UTC
**Filters passed**: L1=[macro_trading], L2_OK
**Hash**: 3e78aa4c043f2ef8377f36a217e92408

## Summary
This paper builds a reproducible framework for estimating Brazil's short-to-medium-run real neutral interest rate (r-star proxy) using five complementary model blocks: simple moving averages on the ex-ante real Selic rate, HP-type trend filters, market-implied curve proxies, a yield-curve state-space model, and a semi-structural IS-Phillips Kalman model. The ensemble assigns zero weight to the IS-Phillips block in the current sample because it degenerates to a local-level trend. The May 2026 estimate comes out at 9.48% p.a., with a P25–P75 block range of 8.71%–9.97%; the ex-ante real rate sits at 10.04%, implying a 0.56 pp policy gap that the framework classifies as neutral relative to its own elevated proxy. The authors are careful to distinguish this from a long-run structural equilibrium estimate — it is a restrictive-cycle shadow rate tracker.

## Why it might be useful
This is primarily a Brazil-specific macro measurement exercise with no direct path to the active strategies (A/B: crypto carry/TSMOM; Strategy D: NQ intraday). The ensemble methodology — combining five heterogeneous model blocks and explicitly down-weighting a block that degenerates in-sample — is a clean implementation pattern worth noting for the Commodities XS Basis+TSMOM research (`Commodities/research/active/xs_basis_tsmom/`), where regime detection across commodity cycles relies on macro regime signals. The key transferable idea is the explicit block-weight rule: if a model's output is indistinguishable from a simpler sub-model, set its ensemble weight to zero rather than blend noise. No immediate test available given Brazil's real-rate data is outside the active research universe.

## Extracted content
Numeric claims from abstract:
- "The latest estimate, for May 2026, places the final operational neutral-rate proxy at 9.48% p.a."
- "P25-P75 block range of 8.71%–9.97%"
- "The ex-ante real rate is 10.04%, implying a policy gap of 0.56 p.p."
- "The IS-Phillips Kalman model falls back to a local-level trend in the current sample, its output is not labeled as structural r-star and receives zero weight in the final ensemble."

No code or formulas in excerpt.

## Action proposed
REFERENCE
