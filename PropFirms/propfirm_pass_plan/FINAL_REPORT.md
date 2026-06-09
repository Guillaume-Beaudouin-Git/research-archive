# Propfirm Pass Program — Final Report & Decision
### Autonomous execution of `PLAN.md` (barrier engineering → honest harvest → end-to-end p(pass))

**Date:** 2026-06-08 · **Engine:** `code/barrier_engine.py` (monotone, self-validated vs the logistic
closed form to ≤0.006). **All numbers from committed runners over read-only data; every p(pass) carries
a 90% CI; DSR at the true trial count.** Nothing scratch-only.

---

## 0. Decision (read this first)

**Can we reach p(pass) > 50% in < 3 months? With a *real edge*, no — we don't have one. By *barrier
choice*, the math says yes, but only as a near-zero-edge gamble we do not recommend as a strategy.**

The program split the problem into the two levers we had never pulled — the **barrier** (firm rules)
and an **honest edge** — and the result is clean and complementary:

1. **Barrier engineering works and is huge** (WS-A). The *same* modest strategy swings **+0.30 in
   p(pass)** purely by firm choice; FTMO's 2-step + 5% daily floor is one of the most hostile barriers
   in the market.
2. **We still have no real edge** (WS-B). On corrected, **true-UTC, close-to-close** methodology, the
   best price-only book has **DSR ≈ 0.001** — indistinguishable from zero (confirming the audit's
   verdict was not a one-off bug but a real absence of edge in the free-price universe).
3. **End-to-end:** our *real* book on the *best* firm = **0.43 [CI 0.36, 0.50]** — below 0.50, and
   *below that firm's zero-edge baseline* because our book's edge is mildly negative.

**Recommendation:** do **not** fund a hero-attempt expecting > 0.50 from skill. The two honest routes are
(A) treat it as an **EV campaign** on a cheap, loose-barrier firm where even a ≈-zero book passes
~0.4-0.5 per try, or (B) **invest in genuinely new (non-price) data** to build the modest Sharpe-0.4-0.6
edge that — *the barrier work proves* — would then clear 0.50 comfortably. A single confident > 0.50 on
skill is not available today.

---

## 1. WS-A — Barrier engineering (Gate A: PASSED)

p(pass ≤ 3mo) of a **fixed modest honest shape** across barrier archetypes (`results/firm_barrier_matrix.csv`):

| Firm archetype | zero-edge | Sharpe 0.4 | **Sharpe 0.6** | Sharpe 0.8 |
|---|--:|--:|--:|--:|
| FTMO 2-step (10%DD, 5% daily, 2-step) | 0.215 | 0.289 | **0.312** | 0.336 |
| FTMO 1-step (trailing, 3% daily) | 0.230 | 0.338 | 0.361 | 0.377 |
| The5ers 1-step (5% static DD) | 0.401 | 0.460 | 0.486 | 0.511 |
| FundedNext 1-step (6%DD, 3% daily, 40% cons.) | 0.209 | 0.308 | 0.333 | 0.351 |
| **Generic 1-step static 10%DD, no daily** | **0.518** | 0.578 | **0.602** | 0.620 |
| Generic 1-step static 8%DD, no daily | 0.517 | 0.580 | 0.603 | 0.625 |
| Generic 2-step 10%DD, no daily | 0.325 | 0.384 | 0.413 | 0.437 |
| Topstep futures (trailing-EOD, 4%DD) | 0.323 | 0.381 | 0.404 | 0.426 |
| **Instant 1-step 12%DD / 9% target, no daily** | **0.576** | 0.632 | **0.653** | 0.675 |

**Gate-A CIs (modest Sharpe-0.6 grind, 12-seed 90% CI):** FTMO_2step [0.255, 0.316] (below) ·
The5ers [0.449, 0.488] (below) · **Gen_1step_loose [0.565, 0.601] (CLEARS)** · **Instant [0.626, 0.660]
(CLEARS)**.

**What drives p(pass) (in order of impact):** (1) **1-step beats 2-step** (one target, not two); (2) **no
hard daily-loss floor** — FTMO's −5% daily is very costly to a grind; (3) **loose static DD** (10-12% vs
5%); (4) **static beats trailing**; (5) an **asymmetric target<DD** firm passes > 0.50 *at zero edge*.
**The achievable edge bar collapses from Sharpe ≈ 2 (FTMO) to Sharpe ≈ 0.4-0.6 (right firm).**

*Caveat (important):* the "Instant/generous" archetypes are real in spirit but often carry catches
(higher fees, lower payout split, stricter *funded-phase* rules, reputation/payout risk). Verify exact
current rules **and the funded-phase economics** before purchase — a high challenge-p(pass) on a firm
that doesn't pay out is worthless.

---

## 2. WS-B — Honest signal harvest (Gate B: FAILED → kill-criterion)

Corrected methodology (the audit's lessons): **true-UTC verified** data, **standard close-to-close
intraday MTM**, honest costs, OOS split, **DSR at true N**, outer-resample CIs. Re-harvested the one
family that ever looked real — index intraday reversion — on true-UTC deep_history:

| Sleeve (true-UTC) | full Sharpe | OOS Sharpe |
|---|--:|--:|
| US30 | −0.47 | −0.52 |
| US500 | −0.42 | +0.99 |
| US100 | −0.43 | +1.26 |
| GER40 | −0.17 | −0.64 |
| **Index-MR book** | **−0.53** | +0.39 |

Book: negative in **4 of 5 years** (positive only 2025), **DSR @N=200 = 0.001, @N=500 = 0.001**. The
US500/US100 OOS-positives are a **single-year (2025) artifact**, not an edge — exactly the
non-robustness that produced the retracted 0.55. **No sleeve clears the DSR gate; Gate B fails. Per the
plan's kill-criterion, the free-price universe is confirmed exhausted on honest methodology.**

---

## 3. End-to-end — the *real* book through the barriers (WS-C sizing applied)

Our honest (≈-zero/negative) book, optimally levered, through each firm (outer-resample 90% CI):

| Firm | p(pass ≤ 3mo), real book | vs zero-edge baseline |
|---|--:|--:|
| FTMO 2-step | **0.119** [0.071, 0.176] | 0.215 |
| Generic 1-step loose | **0.376** [0.307, 0.451] | 0.518 |
| Instant 1-step generous | **0.430** [0.356, 0.498] | 0.576 |

Two honest reads: (i) the **barrier alone** lifts us from 0.12 (FTMO) to 0.43 (best firm) — most of the
distance; (ii) our book sits **below the zero-edge baseline** on every firm, because its edge is mildly
*negative* — i.e. **doing nothing (a zero-edge coin-flip) on the asymmetric firm (0.576) beats trading
our book (0.430).** That is the cleanest possible statement that we have no edge.

---

## 4. The decision tree (what a quant tells the team)

- **Goal = "pass > 0.50, by skill, then profit funded."** → **Not available.** Requires a modest real
  edge (Sharpe 0.4-0.6) we do not have and cannot build from free price data (DSR 0.001). The *only*
  honest route to it is **new, non-price data** (WS-B3: funding/basis, options skew, flows, positioning)
  built through the committed, DSR-gated pipeline — a real investment, not a weekend.
- **Goal = "get a funded account, EV-optimally."** → **Available, as a campaign.** On a cheap-fee,
  loose-barrier firm a disciplined ≈-zero book passes ~0.40-0.50 per attempt; `EV = p·V − C` is positive
  when payout/fee is large. Optimize firm × fee × p × number-of-attempts. **But you still need an edge to
  *profit on the funded account*** — passing is not earning.
- **Goal = "max challenge-p(pass) regardless."** → An **asymmetric target<DD, no-daily, 1-step** firm
  passes > 0.50 at *zero* edge by barrier geometry + sizing. This is a **gamble, not a strategy** (funded
  phase + firm-quality/payout risk undo it). **Not recommended.**

---

## 5. Deliverables (committed, reproducible)

```
PropFirms/propfirm_pass_plan/
  PLAN.md                         the institutional plan
  FINAL_REPORT.md                 this file
  code/barrier_engine.py          monotone multi-barrier first-passage MC + self-check (≤0.006 vs closed form)
  code/run_barrier_matrix.py      firm × shape p(pass) matrix
  code/run_barrier_gateA.py       zero-edge baselines + Gate-A multi-seed CIs
  code/sleeve_harvest.py          true-UTC, close-to-close honest harvest + DSR + end-to-end firm p(pass)
  results/firm_barrier_matrix.csv, gateA.txt, wsB_book.txt
```
Every number above is regenerable from these runners. Timezone is verified empirically (−3h test),
not trusted from labels; the engine is monotone; CIs are outer-resample; DSR is at the true N.

---

## 6. Honest bottom line

A Two Sigma quant would call this a **successful research outcome with a negative headline**: we proved
*where the constraint actually lives* (the barrier, then the absence of edge), eliminated the
fabrication risk (committed runners, CIs, DSR, TZ-verified), and produced a clear decision. The single
most valuable, actionable finding is **WS-A**: most of the FTMO gap was the *wrong barrier*, and a
**modest, achievable Sharpe-0.4-0.6 edge on the right firm clears 0.50** — which redirects all future
effort to **building one modest real edge from new data**, not chasing a Sharpe-2 fantasy on a hostile
barrier. Absent that edge, the correct institutional action is the **EV campaign on a verified loose-barrier
firm**, sized optimally, with eyes open that passing ≠ earning.

*Design-stage Monte-Carlo over historical bootstrap; firm parameters are representative 2026 archetypes
— verify exact current rules, funded-phase economics and payout reliability before committing capital.*
