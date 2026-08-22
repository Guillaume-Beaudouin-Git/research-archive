# Results — Commodity XS Short-Term Reversal (characterisation)

**Date:** 2026-07-09 · **Pre-registration:** `../PREREG_reversal_2026-07-09.md` (frozen before run).
**Data:** 24 continuous futures, 2005-2026, 259 monthly obs. Grid: k∈{1,2,3}, long losers /
short winners, dollar-neutral risk-parity. **This run characterises; it does not confirm
(signal found in-sample — see the pre-reg contamination statement).**

## Verdict: **HALF — one-sided LOSERS-REBOUND** (not a clean XS alpha; DSR-fail after AMTP)

| k | net SR | 3×-cost SR | long-losers SR | short-winners SR | sr_pre | sr_post | IC | IC t |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 1 | 0.114 | 0.087 | 0.579 | −0.447 | −0.156 | 0.328 | 0.040 | 2.56 |
| 2 | 0.143 | 0.125 | 0.678 | −0.498 | 0.073 | 0.202 | 0.028 | 1.63 |
| **3** | **0.456** | 0.439 | **0.824** | **−0.335** | 0.127 | 0.719 | 0.052 | 2.79 |

**Gate read (best cell k=3):**
- **G1 two-sided → FAIL.** The entire premium is the **long-losers leg (SR +0.82)**; the
  short-winners leg **loses (SR −0.34)**. Beaten-down commodities rebound; shorting winners
  doesn't pay. By L25 (a real directional edge is positive on BOTH legs) this is **not a
  market-neutral XS alpha** — it is an **oversold-bounce / long-side effect**.
- G2 cost → PASS (net +0.46, still +0.44 at 3× cost; turnover ~23×/yr). Cost is not the issue.
- G3 IC → reversal IC +0.052, HAC t 2.79 (>2.5) — but this is the same in-sample fact
  restated (the mirror of the momentum run's negative IC), not independent evidence.
- G4 OOS → post-2015 SR 0.72 > pre-2015 0.13 (suggestive only — sample already seen).
- **G5 DSR (n_trials=19) → 0.588, FAIL.** After honest AMTP over the full commodity XS
  thread (16 momentum + 3 reversal), the deflated Sharpe does not survive.

## Honest reading
The reversal is **real but one-sided**: it is a **losers-rebound**, dominated by going long
the most beaten-down commodities. That is almost certainly **commodity mean-reversion / beta
timing** (oversold bounce), *not* a decorrelated cross-sectional alpha — and it fails DSR
after multiple-testing anyway. It confirms the pre-registered prior (stated before the run:
"likely one-sided").

## Where this actually points (constructive, not acted on)
The economically-grounded driver of a commodity "reversal" is the **term structure**:
beaten-down commodities are typically shifting contango→backwardation (roll-yield turns
favourable). So the losers-rebound is most likely a **price proxy for the basis/roll-yield
mechanism (Erb-Harvey)** — which is precisely the **untested S_BASIS leg** of this mission.
→ The right next step is **not** to chase the long-losers leg (that would be leg-picking /
more snooping), but to **finish S_BASIS**: fetch front/second contracts (`fetch_front_second.py`),
build the proper basis signal, and test it two-sided with its own fresh pre-registration.
Any use of the long-losers leg would first need a beta-orthogonality check (L38: regress on a
vol-targeted long-commodity-basket; R²>30% ⇒ it's beta timing, present it as such).

## n_tests
Proposed (not graved): **+3** → cumulative commodity XS thread = **19**. Reconcile manually.

---
*Run 2026-07-09 on the frozen pre-reg. HALF-verdict (one-sided losers-rebound), DSR-fail after
AMTP, in-sample. Not deployable; redirects to the S_BASIS mechanism.*
