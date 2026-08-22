# Microstructure & behavioral sleeves — session_cowork (5 candidates)
*2026-06, fresh VM. **MEASURED** (numbers below are real, from `phase1b_engine.py`; gap-fade run separately from the daily trio to avoid the NQ-load OOM). Phase 1 only this pass (raw edge + skew at the HOLDING horizon). Nothing frozen/merged. Scope: session_cowork only.*

## TL;DR
Phase 1 found one positive-skew discovery (**post-limit-move reversion**, t +2.30 / skew +0.91); **Phase 2 then KILLED it on the decisive two-sided test (L25)** — the edge is asymmetric (bearish-shock bounce t 2.12 vs bullish-shock fade t 1.38 n.s.) = **dip-buying = disguised long beta**, the exact MR-reversal trap. The other 4 failed Phase 1: **gap-fade = open-auction artifact** (collapses on +30-min delay, t 0.42 → −0.05), **VVIX = no predictive edge** (corr −0.01), **sector-pairs** = already-killed stat-arb branch (cite), **intraday-volume** = execution overlay, not an edge. **Net: 0 deployable skew+ sleeve from these 5;** the session's only survivor stays **Long-vol (VXX)** from the prior batch.

---

## PHASE 1 — measured raw edge + skew (gate: t>2 raw & skew≥0; generous)

| # | Candidate | n | mean (bps) | **t raw** | **SKEW** | hit | Phase-1 verdict |
|---|---|---:|---:|---:|---:|---:|---|
| 2 | **Post-limit-move REVERSION** (fade >2.5σ day, hold 1d) | 110 | **+40.3** | **+2.30** | **+0.91** | 0.60 | ✅ **EDGE + skew+ → PHASE 2** (small-N caveat) |
| 1 | Gap-fade (fade big gap, open→close) | 808 | +2.05 | +0.42 | +0.42 | 0.48 | ❌ no edge even same-bar; **+30min→close: t −0.05 → COLLAPSES on delay+1 = open-auction artifact → KILL** |
| 5 | VVIX → fwd-equity signal | 4879 | +0.85 | +0.67 | +0.36 | — | ❌ **no edge** (corr(VVIXz, fwd-5d) = −0.01) — weak as predicted; not even a usable decorrelated signal |
| 4 | Sector-pairs (intra-sector MR) | — | — | — | — | — | ⛔ **CITE not re-prove**: killed stat-arb branch (`../../ftmo_research/STATARB_VERDICT.md`) + 2-leg financing (L28) + FTMO hedging-rule (opposing-correlated prohibited). [raw metric was degenerate — skew +29 / hit 7% = rolling-σ artifact, disregarded] |
| 3 | Intraday volume U-shape | — | — | — | — | — | — **not a standalone edge** (execution-timing overlay); intraday → ORB cost-kill (archived). No test. |

**Mirror check (post-limit):** continuation (ride the >2.5σ move) is the exact mirror loser — mean −40 bps, t −2.30, skew −0.91. So the extreme is followed by a **reversion**, not continuation: short-horizon overreaction-correction (De Bondt–Thaler short-horizon reversal), strongest in the tail.

**The key distinction this batch surfaces:** *everyday* mean-reversion fails (gap-fade here is a delay-fragile artifact; intraday OU 2B was cost-killed) — **but reversion CONDITIONED ON THE EXTREME has a positive-skew edge**, because at >2.5σ the overreaction bounce is convex (sharp, large) rather than the negative-skew "pick-up-pennies" of everyday MR. Different animal, right profile.

**On the two "measure-for-discovery" candidates the brief flagged:** post-limit **delivered** (positive-skew edge); VVIX **did not** (no predictive power — decorrelated ≠ predictive).

---

## PHASE 2 — post-limit reversion → ❌ KILL on Test 1 (two-sided, the decisive test)

Order run: two-sided FIRST (it can kill outright). It did → tests 2–5 not run (per protocol).

**Test 1 — TWO-SIDED (L25), US500, >2.5σ events:**

| Conditioning | trade | n | mean (bps) | t | skew | hit |
|---|---|---:|---:|---:|---:|---:|
| **Bearish shock** (r < −2.5σ) | long the bounce | 111 | **+33.6** | **+2.12** | +1.44 | 0.50 |
| **Bullish shock** (r > +2.5σ) | short the spike | 68 | +17.7 | **+1.38** (n.s.) | +1.50 | 0.47 |

**ASYMMETRIC.** The edge is carried by the **bearish-shock bounce** (t 2.12, mean ~2× the bull side); the bullish side is **not significant** (t 1.38). This is **dip-buying = conditional long beta in disguise**, not a genuine two-sided overreaction-reversal — the exact trap from the package-2 MR reversal (long 1.11 / short 0.28). **→ KILL.** Tests 2 (power), 3 (cost), 4 (delay), 5 (OOS) not run (the decisive test already failed).

**Merge-relevant (why it's not even a useful sleeve):** dip-buying buys the day **after** the crash → it profits on the **recovery** = long-beta exposure, the **opposite timing** of Long-vol (VXX), which pays **during** the crash. So it is neither a crash hedge nor decorrelated — it is long beta, the thing the portfolio objective (L7) is trying to *avoid*. Redundant with equity beta, not a complementary skew+ sleeve.

### Net of both batches (10 candidates total this session)
The **only** genuine skew+ AND decorrelated survivor remains **Long-vol (VXX)** (skew +1.86, corr −0.75 to equity; negative-carry insurance — `exploration_2026-06.md`). Post-limit reversion was the lone Phase-1 discovery here but **dies at Phase 2 as disguised long beta.** Everything else: wrong-profile, artifact, or archive-killed.

*Lesson candidate (named): **"extreme-reversion is asymmetric = dip-buying"** — the crash-bounce is long-beta-conditional (pays on recovery), not a two-sided overreaction edge; the two-sided split (L25) catches it, same as the MR-reversal asymmetry.*

---

## Status
- **All 5 measured this pass** (fresh VM, gap-fade isolated from the daily trio per the OOM fix — only the needed columns loaded).
- **Phase 1 verdict:** 1 survivor (post-limit reversion, skew +0.91 / t +2.30), 4 out (gap-fade artifact, VVIX no-edge, sector-pairs cited-killed, intraday-volume not-an-edge).
- **Lesson candidates (named, not numbered):**
  - **"extreme-conditioned reversion ≠ everyday MR"** — the tail-overreaction bounce is positive-skew and real; everyday fades are negative-skew or artifacts.
  - **"gap-fade is an open-auction artifact"** — the +30-min delay test zeroes it (the decisive MR-reversal trap fired).
  - **"decorrelated ≠ predictive"** — VVIX is decorrelated from equity but carries no forward signal.
- **Nothing frozen/merged. Next pass: Phase 2 on post-limit-reversion only.**
