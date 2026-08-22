# PRE-REGISTRATION — Piste B: Range trading (low-directionality regimes) on FTMO

**Frozen:** 2026-07-08 13:52 UTC · **Status:** design frozen BEFORE any result. Additive, no git-HEAD ops, live book untouched.
**Reconciliation policy:** independent fresh pass; in-repo precedent (`_audit/xauusd_rangefade_honest_2026-05.md`,
`breakout_deepdive_ftmo.md`) consulted only in the final synthesis.

---

## 0. Prior (declared)
Range-fade is a mean-reversion form → it inherits the cost-dead + beta-trap risks. The **specific trap
this design targets** is the one the user flagged: an in-sample range edge is usually a **selection
artefact** — you only call a window a "range" *because* it reverted. The decisive test is therefore
**causal (real-time) vs oracle (look-ahead) range detection**: a real edge survives when the regime is
flagged using trailing data only; a selection artefact collapses.

## 1. Hypothesis
**H_B:** on FTMO instruments, fading the extremes of a **causally-detected** low-directionality (range)
regime, with a hard stop on breakout, yields a **two-sided** net-positive edge after real FTMO cost.
**H0:** the range edge is a look-ahead selection artefact and/or is cost-dead (small intraday amplitude
vs spread+slippage), and/or is one-sided (beta).

## 2. Universe & data (frozen)
- Instruments: **US100, US500, US30, GER40, EURUSD, GBPUSD, XAUUSD** (indices primary; FX + gold for breadth).
- Bars: **hourly** UTC (`data/deep_history_utc` → resample). Intraday-flat design (flatten before the
  daily rollover) ⇒ **no swap** (matches §4 short-hold, isolates the spread as the binding cost, L33b).
- Sample: full available history (indices 2013→2026, FX/gold 2007→2026).

## 3. Causal range-regime detection (no look-ahead)
Computed on **trailing bars only**, regime known at T−1:
- **ADX(14) < 25** (trend filter OFF) → range regime candidate, AND
- **Bollinger band-width percentile < 40th** over a trailing 250-bar window (vol compression).
Both indicators use only data up to T−1. A trade may open at T only if the regime flag is true at T−1.

**Oracle contrast (falsification control):** re-run with a *centered* (look-ahead) range flag — regime =
true if the NEXT k bars stayed inside the channel. If causal≈0 while oracle≫0, the edge is selection.

## 4. Signal & execution (frozen)
- Channel: Bollinger(20, 2σ) on hourly closes (causal). Middle = SMA20.
- **Fade entry:** close ≥ upper band → **short** (fade high); close ≤ lower band → **long** (fade low) —
  only when the §3 range flag is on.
- **Exit:** reversion to middle band (SMA20) OR time-stop = 8 bars OR **hard stop**: close beyond the
  band by ≥ 1.0×ATR(14) (= range broken, cut and realise). Intraday-flat: force-close before rollover.
- **Timing:** signal at close T−1, execute at close T (1-bar delay). Non-overlapping per instrument.
- **Grid (search space for DSR):** ADX∈{20,25} × band-σ∈{2.0,2.5} × exit∈{mid, time-stop} = 8 configs
  × 7 instruments = **56 trials**.
- **Cost (NET):** round trip = 2 × `rt_cost_bps` (active fill). No swap (intraday-flat). Stress slip ×1.5.

## 5. Two-sided requirement (decisive)
Fade-high (short) and fade-low (long) legs reported separately. Qualify only if **both net ≥ 0, short-leg
HAC t > −1**. One-sided (only the long/beta leg pays) → REJECT.

## 6. Success / fail thresholds (frozen)
| Gate | RESEARCH_PASS | PROPFIRM_PASS |
|---|---|---|
| Net Sharpe | > 0.7 | > 1.0 |
| HAC t (lag-6) | > 2.5 | > 2.5 |
| **Gross per-trade / cost per-trade** (L33b intraday-flat gate) | ≥ 3× | ≥ 3× |
| Walk-forward folds positive | > 50% | > 60% |
| Two-sided | required | required |
| Causal-vs-oracle | causal edge ≥ 60% of oracle | — |
| DSR (N=56) | > 0.5 | > 0.95 |

## 7. Pre-declared falsification triggers (any ⇒ FALSIFIED, named mechanism)
- **F1:** gross (zero-cost) two-sided edge ≤ 0 → "no edge before cost" (not a cost problem).
- **F2:** causal edge ≪ oracle edge → "range detection is a look-ahead selection artefact".
- **F3:** gross/trade < 3× cost/trade → "intraday amplitude cost-dead vs spread (L33b)".
- **F4:** one-sided only → "beta, not two-sided reversion".
- **F5:** best DSR < 0.5 → "multiple-testing artefact".

## 8. Candidate criterion & re-test plan — as in Piste A §8 (report §4 profile; specify audited-engine re-run).
**Modifications budget:** 3.
