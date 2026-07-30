# DEPLOYMENT PLAN — Combined personal book (€12k IBKR, 6-12mo, DD budget 40-50%)

**Date:** 2026-07-15. Consolidates the session's 3 gate-passing sleeves into a deployable book.
All numbers from `RESULTS_H3/H4/H9.md`; combined stats over the common window 2016-2026 (N=125 months).

## 1. The combined book — diversification is the win

| Sleeve | Weight (inv-vol) | Sharpe | ann | MaxDD | Mechanism / vehicle |
|---|---|---|---|---|---|
| H3 month-end Treasury | **60%** | 1.02 | 4.3% | −4.8% | rebalancing flow · TLT / micro-yield |
| H4 commodity seasonality | 14% | 1.21 | 22.2% | −32% | physical calendar · commodity micros |
| H9 crack-spread grid | 26% | 0.54 | 5.3% | −16.8% | refining-margin MR · RB/HO/CL futures |
| **COMBINED (1×)** | — | **1.51** | 7.0% | **−4.9%** | corr matrix near-zero (see below) |

**Correlation matrix (near-orthogonal — the whole point):**
```
              H3     H4     H9
H3          1.00  -0.04   0.17
H4         -0.04   1.00   0.05
H9          0.17   0.05   1.00
```
Three ~SR 0.5-1.2 sleeves at ρ≈0 combine to **Sharpe 1.51** — higher than any component. This is the
session's core deliverable: **no single engine scales; the diversified combination does.**

## 2. Sizing — prudent fractional Kelly (NOT naive Kelly)

**⚠️ Naive Kelly on the combined book says 9-32× leverage. This is a trap — do NOT.** It assumes the
in-sample −4.9% DD holds forever, Sharpe 1.51 holds forever, and Gaussian tails — all false.

Honest adjustments:
- **Crisis-correlation:** if the sleeves' drawdowns align (corr→1 in a stress), the weighted DD is
  **≈ −11.7%**, not −4.9%. Size to this.
- **Estimation + provisional haircut:** forward Sharpe ≈ **0.9** (est-error + H4/H9 L5 roll provisional),
  not 1.51.

| Leverage | ann | vol | crisis-DD | in-sample-DD |
|---|---|---|---|---|
| 2× | ~14% | 9% | −23% | −10% |
| **3× (recommended ceiling)** | **~21%** | 14% | **−35%** | −15% |
| 4× | ~28% | 19% | −47% (breaches) | −20% |

**→ Deploy at 2-3× leverage: ~15-21%/yr, crisis-DD 25-35% (inside your 40-50% budget), doubles capital in
~4-5 years.** Hard cap 3×. This IS the aggressive-but-survivable point — via diversification + moderate
leverage, not a hot strategy or a martingale.

## 3. €12k deployment reality — staged (granularity binds)

| Sleeve | €12k now? | Vehicle |
|---|---|---|
| **H3 (60%)** | ✅ **deploy now** | **TLT fractional shares** (IBKR) or CME Micro Treasury Yield futures — fully granular |
| H4 (14%) | ⚠️ partial | a few commodity micros (MCL, MGC…) — can't hold all 20 at €12k; run the top-amplitude subset |
| H9 (26%) | ❌ blocked | crack = full-size RB+HO+CL (~$100k+ notional) — **add at ~€50k**; no micros exist |

**Realistic starting book at €12k:** ~H3 (TLT) + a slice of H4, at 2-3× leverage → ~12-15%/yr on a
granular, low-friction base. Add H9 (and full H4) as capital grows toward €50k — at which point the full
Sharpe-1.51 book comes online.

## 4. Mandatory risk controls

- **H9 trend kill-switch** (from H8): flatten the crack grid if the spread trends against the inventory —
  this is what caps the 2020-oil-crash tail. Non-negotiable before deploying H9.
- **Correlation monitor:** the book's leverage headroom rests on ρ≈0. Re-measure monthly; de-lever if
  correlations rise (crisis regime).
- **Provisional flags:** confirm H4 + H9 on roll-adjusted / true-excess data before trusting their
  magnitude at leverage (L5).

## 5. Honest bottom line

Expected ~15-21%/yr at 2-3× with a controlled ~25-35% crisis-DD — **real, survivable, and matched to your
horizon and budget.** Not the 66%/yr fantasy; that never existed (every headline deflated). This is what
a rigorous process delivers: three modest, real, decorrelated edges + disciplined leverage = a book that
compounds without a ruin tail.

**Open next steps:** (1) roll-adjusted confirm of H4/H9; (2) build the H9 kill-switch; (3) live-paper the
H3 TLT sleeve first (granular, deployable today); (4) re-consolidate at €50k when H9 unlocks.

---
**⚠️ CORRECTION 2026-07-15 (roll audit, see ROLL_AUDIT.md):** H4 was found to be a roll artefact and is DROPPED. Corrected combined book = **H3 + H9 only, Sharpe 1.02** (not 1.51). Prudent leverage 2-3x -> ~10-14%/yr, crisis-DD 20-30%. H3 (TLT) remains the clean deploy-today anchor; H9 confirmed roll-clean.
