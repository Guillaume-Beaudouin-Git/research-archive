# Commodity-carry gate — independent IC corroboration (complement to CARRY_FEASIBILITY.md)

**Date:** 2026-06-08 · **Status:** this file CORROBORATES the canonical verdict in `CARRY_FEASIBILITY.md`
(FAIL) from a **different method**, and does not replace it. (`CARRY_FEASIBILITY.md` was produced in parallel
and reaches FAIL at Q1 + cites the prior documented NO-GO `data/ftmo_research/commod_carry_makeorbreak.md`.
I agree with it; this note adds the empirical IC test it deliberately did not run.) Code: `carry_ic.py`,
`carry_ic_results.json`, `usoil_daily.parquet`.

## What this adds
`CARRY_FEASIBILITY.md` correctly **STOPs at Q1** (no term structure on disk → can't measure a carry slope →
FAIL rather than fabricate one) and notes the angle is already killed with *real deferred-contract* data
(Sharpe −1.15, t=−5.18, fails 2020 tail L31, one-sided-uncollectable L32). To be maximally rigorous I went
one step further and **built the single best proxy that IS constructible without a term structure** — the
**realized roll yield** = trailing-63d [rolling-ETF return − front-month-price return] (a rolling ETF like
UNG/USO/CPER under/out-performs the front price by exactly the roll cost) — and ran the causal IC. **It also
FAILS**, which independently confirms the close from the proxy side.

## Result (causal, lag-1; HAC maxlags≥horizon for overlapping returns; 2015+ where ETFs exist)
| signal→fwd-return | strongest | finding |
|---|---|---|
| per-instrument (5 commodities × {1d,21d}) | **oil 21d HAC t = −2.06** | below 2.5, **WRONG sign** (high realized carry → *lower* fwd return), 2020-driven |
| pooled ALL5 (h=21) | HAC t = **+0.50** | null |
| pooled rolling-3 (oil+natgas+copper) | HAC t = **+0.11** | null |
| **2020 tail (L31)** | pooled Pearson **−0.13 / −0.22** | **sign INVERTS** in the stress (vs +0.06 ex-2020) |

- **No variant clears |HAC t|>2.5** (deflated for 12 variants the bar is ~3.0); pooled IC ≈ 0.
- The **2020 tail flips the sign** — the same regime-dependence the prior real-basis work found, reproduced here on the proxy. Independent method, same conclusion.
- **Cost is moot** (no robust gross IC to erode), though commodity CFD spreads are material under +50% stress (WTI ~7→11 bps, copper ~9→14, natgas ~36→54).

## Method limitations (why this is a *corroboration*, not the primary evidence)
The realized-roll-yield proxy is **backward-looking** (assumes carry persistence; not the live F1/F2 slope),
**ETF-fee/tracking confounded**, and **2015+ only**; metals' physical ETFs (GLD/SLV) carry ~no roll →
financing-contango only (wrong regime). It is strictly weaker than the prior work's real CLZ26 deferred
contract — which is why `CARRY_FEASIBILITY.md`'s documentary FAIL (with better data) is the primary evidence
and this IC test is the secondary, same-direction confirmation.

## Net
**Two independent paths → FAIL:** (1) no term structure on disk + a documented real-basis NO-GO
(`CARRY_FEASIBILITY.md`); (2) the best constructible proxy yields a null, wrong-signed, 2020-inverting IC
(this note). **Do not advance L37 to a backtest or MT5-spread calibration.** Re-opening requires a genuine
historical futures **term-structure** dataset (paid deferred curves) — not the free CFD/spot on disk, so it is
*not* the zero-marginal-cost test the premise assumed. Long-only flagged (L32: short-contango uncollectable).

*Causal; HAC t-stats; proxy limits stated; +50% spread-stress noted; 2020 tail (L31) decisive; READ-ONLY on
source; wrote only under `research/commodity_carry_feasibility/`; did NOT overwrite the parallel-session
canonical verdict; nothing fabricated.*
