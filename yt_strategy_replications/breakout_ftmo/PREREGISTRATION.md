# PRE-REGISTRATION (FROZEN before any price result) — Short-term breakout, FTMO-targeted
**Date frozen:** 2026-06-20 · **Author:** research session · **Auditor:** separate subagent (post-hoc).
**Type:** STRICT preliminary, reimplemented engine → robust NEGATIVE definitive; POSITIVE = candidate to revalidate
in Claude Code. **FREE DATA ONLY** (OHLC + unsigned tick_volume + quoted spread; no Databento, no order-flow — decided).
No git HEAD ops (shared dir, 2026-06-19 incident); live book read-only; nothing deployed.

## Position in the program
§4 rank-1 (intraday MR) falsified: 15-min no signal; M2–M5 real two-sided reversal but cost-dead at retail
(institutional-tier only). §4 rank-2 (event) falsified: priced in the release bar + risk un-boundable on naked CFD.
**This = rank-3 = short-term breakout (continuation).** Rank-4 (carry) rejected a priori (always-on + negative tail).

## Why this is not just re-confirming dead price-only
Breakout has two properties OPPOSITE to MR that can change the verdict:
1. It trades **continuation**, not reversion → the scale/condition where continuation nets out can differ from MR.
2. **Potential POSITIVE tail** (big trends pay for false breaks) vs MR's negative tail → valuable for §4 (daily-barrier
   axis, no blow-up). Even at a modest Sharpe, a positive tail changes §4 fit.
3. **Far lower trade frequency** than the MR harvester (only on range breaks) → much less cost drag (the killer of MR).
Established facts to respect: at 15-min the "momentum flip" (trade WITH the move) was ALSO negative (neither reversion
nor continuation paid at 15-min; only beta) — so 15-min is known-dead; the live question is OTHER scales (M5/M30/H1)
and CONDITIONS (vol/range), with the skew/§4 angle.

## Universe (fixed)
US100, US500, US30, GER40 (indices) + EURUSD, GBPUSD (FX) + XAUUSD. Liquid session (indices/XAU 13:30–20:00 UTC;
FX 07:00–16:00 UTC). Per-instrument; pooled equal-risk; per-leg. Sample 2013→2026 (indices/XAU), 2007→2026 (FX).

## Signal — Donchian channel breakout (two-sided by construction)
At bar close t: if close_t > max(high, N) of the prior N bars → **long** (upside continuation); if close_t < min(low, N)
→ **short**. Enter next bar open (engine-enforced, no look-ahead). **Defined-risk, positive-skew exit:** hard stop
sl = 1×ATR(N); target tp = 3×ATR(N) (3:1 R-multiple → positive skew by design — the §4-differentiating tail); time-stop
at session end (intraday-flat ⇒ swap-free). Pessimistic stop-first tie-break.

## Q2 grid (FIXED = 6 configs)
1. Donchian N=20 breakout, **M15**.  2. **M30**.  3. **H1**.  4. **M5**.
5. Donchian N=20 + **vol filter** (enter only if ATR(N) > its rolling median) at the scale Q1 designates best.
6. Donchian **N=10** (shorter channel) at the best scale.
Vol-target sizing as in prior studies (causal). No other configs. (Anti-mining: if I add scales/thresholds to find a
winner → STOP; each addition is a new registry trial.)

## Q1 — descriptive (measure-first), FROZEN metrics
Per instrument at M5/M15/M30/H1: AC(1) of returns (positive = continuation); and the **conditional post-breakout
forward return**: after a Donchian-20 break, the next H=8-bar return in the break direction — mean (bps), HAC lag-6 t,
two legs (up-break / down-break). **Decisive ratio = |forward return| / RT spread.** If continuation is insignificant
or its amplitude < spread at every scale, a net breakout edge is impossible before building.

## Gates (pre-registered)
1. **Gross two-sided:** pooled HAC lag-6 t-stat **> 2.5** (cost=0).
2. **Two-sided (L25, decisive):** up-break AND down-break legs both gross-positive; check vs unconditional drift
   (long-only breakout on up-drifting indices = the beta trap that killed long-only MR).
3. **Net:** pooled net Sharpe **> 1.0** AND DSR **> 0.5** at the quoted (lower-bound) spread; still > 0 at stress
   (indices/XAU 2 bps, FX 1 bp). Per-trade gross must exceed 3× cost.
4. **Walk-forward:** ≥5 folds, WF > 50%.
5. **TAIL (the differentiator, reported):** skew of per-trade returns — expected POSITIVE (vs MR's negative). A
   positive tail improves §4 fit even at modest Sharpe.
6. **§4 excursion:** intraday-m (avg adverse excursion / σ) ≤ 1.5 (hard stop should bound it — verify; events gapped
   stops, intraday breakouts should not).
7. **DSR cumulative penalty:** n_trials = **145** (program ~110 + MR 13 + event 9 + subscale 6 + this 6) per L20.

## Three pre-registered verdicts (all redirect)
- **(a)** net-positive two-sided breakout at some scale, positive tail, §4-qualified → **CANDIDATE** to revalidate in
  Claude Code (first price-only family to pass — demonstrate rigorously).
- **(b)** gross edge real but cost-dead at retail (like sub-scale MR) → vehicle conclusion, price-only momentum
  confirmed institutional-tier; redirect (NOT Databento — decided).
- **(c)** no exploitable continuation even multi-scale → price-only OHLC **fully exhausted** (reversion AND
  continuation, all scales) → closes free price-only; program pivots to what remains free (unsigned tick_volume as a
  weak flow proxy? crypto as a different vehicle? multi-account architecture).

## Deliverable
`FINDINGS_BREAKOUT_2026-06-20.md` stating WHICH of (a)/(b)/(c) and the redirect, with the Q1 ratio table, Q2 gross/net
two-sided + **skew**, the §4 scorecard, cumulative DSR, and the independent-audit verdict.
