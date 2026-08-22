# PRE-REGISTRATION (FROZEN before any return/AC result) — Sub-15-min mean-reversion
**Date frozen:** 2026-06-20 · **Author:** research session · **Auditor:** separate subagent (post-hoc).
**Type:** STRICT preliminary. Reimplemented engine → a robust NEGATIVE is definitive; a POSITIVE is a CANDIDATE to
revalidate in Claude Code against the audited engine. No git HEAD ops (shared dir, 2026-06-19 incident); live book
read-only; nothing deployed.

**Why this step (named by the prior wall):** the 15-min MR death had a specific cause — (a) cost (5–11k trades/yr,
need >3 bps gross/trade, observed ~0.2) and (b) no exploitable autocorrelation *at 15-min*. 15-min averaging
destroys microstructure; short-horizon negative autocorrelation is documented finer. This is a **time-scale change**
named by the death mechanism, NOT re-mining 15-min OHLC. The decisive test is **signal-vs-cost at fine frequency**,
not "is there autocorrelation" (there is) but "does it survive the spread."

## Q0 result (cost input recon, pre-commit-legitimate — no returns touched)
- **Finest scale available: M1** (no tick data in the store) → sub-minute is out of scope; stated as a limit.
- **Cost model (per instrument, measured from the `spread` column, treated as a LOWER BOUND):** RT = 1 quoted
  spread. Indices spread well-populated (US100 ~0.5–2 bps over time); **FX spread has many zero entries post-2021**
  → FX uses measured-where-valid with a **0.5 bp floor**. Stress levels (fixed, pre-registered): indices {1 bp, 2 bp};
  FX {1 bp, 2 bp}. **A net edge that requires the spread at its measured floor is declared non-robust.**

## Anti-mining (binding)
Grid ≤6 configs, fixed below. Frequencies fixed = {M1, M2, M5} (M15 already done = reference). If I widen the grid,
add frequencies, or sweep thresholds to find a winner → STOP and report. Each addition is a new registry trial.

## Universe (fixed)
US100, US500, US30, GER40 (indices) + EURUSD, GBPUSD (FX). Per-instrument time-series; pooled equal-risk; per-leg
reported. Liquid session only (indices 13:30–20:00 UTC; FX 07:00–16:00 UTC) — but bars NOT session-restricted for
M1 AC measurement of Q1 (full 24h, then session for the strategy). Sample 2013→2026 (indices), 2007→2026 (FX).

## Q1 — descriptive (measure-first), FROZEN metrics
Per instrument at M1, M2, M5: AC(1), AC(2), AC(3) of bar returns; σ_bar (bps); **reversion amplitude
= |AC(1)| × σ_bar (bps)** = the predictable bps from 1-lag reversion. **Decisive ratio = reversion_amplitude / (RT
spread)**. If ratio < 1 at a frequency, a net 1-lag MR edge is impossible there before any strategy is built.
**Bid-ask-bounce caveat (pre-registered):** negative AC at M1 is partly microstructure bounce that *equals* the
spread; the gross backtest entered at real OPEN / exited at real CLOSE (Q2) is the honest test — phantom-bounce
profit cannot appear at tradable prices.

## Q2 — strategy grid (FIXED = 6 configs)
Signal = fade the prior k-bar move (short-term reversal), two-sided by construction. Causal; signal at bar close →
enter next bar open (engine-enforced). Configs:
1. M1, unconditional 1-bar reversal, hold H=1 bar (the pure AC harvester; high-frequency, cost-stress diagnostic).
2. M1, thresholded: enter when |prior-1-bar move| > rolling p80, hold H=3, hard stop = 3×ATR(20).
3. M2, thresholded (same rule, p80, H=3, stop 3×ATR).
4. M5, thresholded (same rule, p80, H=3, stop 3×ATR).
5. M5, unconditional 1-bar reversal, hold H=1.
6. M5, z-reversal (z=close vs SMA20, |z|>2, hold H=3, stop 3×ATR) — finer analogue of the 15-min primary.
Vol-target sizing as in the 15-min study (causal). No other configs.

## Gates (pre-registered)
1. **Gross two-sided:** pooled HAC lag-6 t-stat **> 2.5** (cost=0).
2. **Two-sided (L25, decisive):** long-leg AND short-leg gross-positive; check vs unconditional drift. One-sided ⇒
   beta/bounce artifact ⇒ reject.
3. **Net:** pooled net Sharpe **> 1.0** AND DSR **> 0.5** at the measured cost; AND still > 0 at the 2 bp stress.
   Per-trade gross must exceed **3× cost** (binary/short-hold gate, L11b).
4. **Walk-forward:** ≥5 folds, WF > 50%.
5. **§4 excursion:** intraday-m (avg adverse excursion / σ) ≤ 1.5 (expected easily met by short holds — verify).
6. **DSR cumulative penalty:** n_trials = **135** (program ~110 + 15-min MR ~13 + this study ~6+) per L20.

## Three pre-registered verdicts (all redirect — none is "give up")
- **(a)** net-positive two-sided MR sub-15-min on CFD → **MAJOR CANDIDATE** to revalidate in Claude Code vs the
  audited engine (first family to pass — must be demonstrated rigorously).
- **(b)** gross edge real but eaten by retail cost at ALL fine scales → the edge exists, the **vehicle** is the
  problem → redirect to the §4 "lower-cost venue" lever (NOT abandonment).
- **(c)** no exploitable autocorrelation even gross sub-15-min (or it is pure bid-ask bounce = the spread) →
  price-only is exhausted at every scale → redirect to a **different data axis** (order-flow).

## Deliverable
`FINDINGS_MR_SUBSCALE_2026-06-20.md` stating WHICH of (a)/(b)/(c) and the redirect, with the Q1 ratio table, the Q2
two-sided gross/net, the Q3 cost-wall, cumulative DSR, and the independent-audit verdict.
