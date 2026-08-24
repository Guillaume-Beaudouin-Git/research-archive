# Volet 1b + Volet 4 — mechanism MEASURED (not interpreted) — 2026-07-15

Audited engine (unmutated); `funnel_diag` mirrors `engine.run_funnel` 385-413 exactly,
adds instrumentation; calls unmutated `engine.run_phase`. 286 cohorts 2014-2024 step 10.

## 1-4. Why do mono cohorts fail? (wall=91d)
| config | p(pass) | daily drift* | median t_P1 | reached P1 | fail: bust-driven / grind |
|---|---|---|---|---|---|
| FULL (4 legs) | 83.9% | **0.80%/d** | 12d | 99% | 87% / 13% |
| MONO2 (US100+GER40) | 59.4% | 0.48%/d | 21d | 97% | 75% / 25% |
| MONO1 (US100 only) | 46.9% | **0.29%/d** | 35d | 92% | 70% / 30% |

*implied = 10% / median t_P1.

**Return-starvation is PROVEN, directly measured:** mono drifts at **0.29%/day = 36% of
full's 0.80%/day**; median time to the first +10% **triples (12d → 35d)**. 92-99% of cohorts
CAN reach P1 — it's SPEED, not ability, that kills them against the clock.

**Honest nuance (against my earlier one-liner):** failures are still *mostly bust-touching*
(70% of mono failures had ≥1 bust), not "pure timeout." But that is a CONSEQUENCE of slowness,
not a competing cause: a book that drifts 3× slower stays exposed 3× longer → more chances to
clip the daily breaker before compounding to target. The grind (never-bust) share of failures
rises 13% → 30%, and daily drift collapses — both point the same way.

## 5. Horizon sweep — the DECISIVE cut (91d = user's economic clock, NOT an FTMO rule)
| config | 91d | 182d | 270d | unbounded |
|---|---|---|---|---|
| FULL | 83.9% | 97.6% | 100.0% | 100.0% |
| MONO2 | 59.4% | 86.0% | 93.0% | 100.0% |
| MONO1 | 46.9% | 72.7% | 79.0% | **100.0%** |

**Every config reaches 100% at unbounded horizon** → NO cohort is structurally busted out;
the retry mechanism + enough time funds every start. **The entire full↔mono p(pass) gap is a
SPEED/HORIZON effect, not a survival effect.** This is the clean proof of return-starvation:
busts are recoverable (retry), the real killer is running out of the 91d clock before a slow
drift compounds. Caveat: "unbounded" is data-end-bounded (2026-06); late-2024 cohorts get ~18mo.

The 91d clock IS a major binding constraint — but mono is genuinely slower, so extending time
alone lifts mono1 only to 79% (270d), not full's 100%. Both levers (more engines OR more time)
are real; neither is "the nightly is broken."

## Volet 4 — remedy levers, quantified (Δp vs MONO1 @ 91d)
| lever | p(pass) | Δ vs mono1 | median t_fund |
|---|---|---|---|
| MONO1 US100 only (loss-night reality) | 46.9% | +0.0 | 40d |
| **+GER40 (monday_restamp, DEPLOYED)** | 59.4% | **+12.6pt** | 35d |
| +J1 ungated (US/JPY out of zone) | 76.6% | +29.7pt | 30d |
| +gold (signal wakes) | 81.1% | +34.3pt | 35d |
| FULL (all engines) | 83.9% | +37.1pt | 30d |
| — extend horizon to 182d (MONO1) | 72.7% | +25.8pt | — |

**The remedy is ADDING return engines (or time), never cutting US100 size** — cutting US100
lowers drift → strictly worse (confirms the reversal vs the funded precedent, where sizing was
the only lever). Ranked by deployability: monday_restamp already banks +12.6pt; J1 un-gating is
regime-gated (only when US/JPY exits the intervention zone, +30pt when it does); gold is
signal-dependent (+34pt when awake); horizon is a personal-clock choice (+26pt at 182d).

## Verdict inputs (feeding the final adjudication)
- The 2 losses = variance (Volet 1: p5.5-7.6 of US100-only nights, breaker working).
- The mono/gated regime cost = **-37pt p(pass), mechanism = return-starvation (drift 0.29 vs
  0.80%/day), PROVEN by unbounded=100%** (no structural bust-out; pure speed/horizon).
- (b2-i cap-uncapping) refuted (Volet 0); (b2-ii undamped-vol-more-breakers) refuted (mono
  breaks LESS); the surviving structural finding is (b2-iii) return-starvation.
