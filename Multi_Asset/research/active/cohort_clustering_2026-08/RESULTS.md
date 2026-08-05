# Do challenge outcomes cluster in time? — phase-2 cohort study

**Date** 2026-08-05 · **Branch** `claude/cohort-clustering` · **Scope** deployed MONO book,
phase 2 (target +5 %), daily −5 % on the equity path, STATIC −10 % floor,
`min_trading_days = 4` with the micro-ORB counter ARMED, `p2_mult = 1.2`, Pace denominator
frozen at 91. 463 cohorts, starts every 7 trading days, 2013-10-01 → 2026-03-13.

**Machine** — the `phase2_sizing_2026-08` harness is reused verbatim
(`code/p2_lib.py`, engine `data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py`
+ `v22/engine_v22.py`). Nothing about the simulator is re-implemented here; only the per-cohort
outputs, which were gitignored and lost, are regenerated. The `CFG_LIVE` fix (min-trading-days
backstop armed) is kept, so no winner is written off as a timeout.

---

## VERDICT — conclusion **3** of the three

**There is no clustering of challenge outcomes beyond what the cohort overlap already
produces. The starting date does not matter. The `Q1 10.7 % vs Q2 34.6 %` citation is an
artefact and must be retired.**

Three findings carry it, and one of them was not on the menu:

1. **The overlap premise is itself wrong on this book.** Adjacent cohorts do *not* share
   95 % of their trajectory — they share a **median of 6 %**, and **49 % of adjacent pairs
   share nothing at all**. A phase-2 attempt resolves in a median of **12 calendar days**,
   while cohorts start ~10 calendar days apart. What matters is the *decisive* window, not
   the nominal horizon.
2. **Against the overlap-matched placebo, the real series clusters LESS, not more** — at
   every sizing (vm 8/10/12/14) and every horizon (28→70 days), without a single exception.
   One-sided p = 0.78 → 1.00.
3. **Post-2021 the book's phase-2 pass rate sits INSIDE the placebo band.** The
   +14 pt edge over a zero-drift, sign-scrambled version of itself that the book had before
   2021 is **+1 to +2 pt after 2021**, and the real value lies between the placebo's 5th and
   95th percentiles at every vm and horizon. The ~60 % pass rate that survives is
   **geometry** (+5 % target against −5 %/−10 % barriers, vol-targeted), not edge.

Consequence for the account entering phase 2 in a few days: **start whenever. There is no
free p(pass) in the calendar, and waiting costs option value** (`feedback_dont_destroy_option_value`).
The consequence in (3) is a different, more serious matter and is flagged as such below.

---

## 1. The time series of outcomes by start date

`tables/cohort_timeline_vm10.csv` (also vm 8 / 12 / 14). vm 10, horizon 56 calendar days:

```
year | one character per cohort start (7 trading days apart)  | p(pass)
2013 | FFFFa..PPP                              |  30.0%  (n=10)
2014 | PPPPPPPPPFFaaFaPPPPPPPPFPFFFFPPPPPPFa   |  64.9%  (n=37)
2015 | PPFFaFFFPPP.FPaPPPPddFFPFPdPF.PPPPPPP   |  54.1%  (n=37)
2016 | dPFaPFFaPPPPPPPFPPdaPaPPPPPPFPFFPPPPP   |  64.9%  (n=37)
2017 | PPPPPP.PPPPP.FPPPFFPPPPPF.PPPPPPdPdPPP  |  76.3%  (n=38)
2018 | PPPPFPPFPPFPPPPPPPPPPPdPdFFPPFPFPFPPP   |  73.0%  (n=37)
2019 | PFPPFPPPPPPdPPdPPFFdFFPPPFFFPPdPPdPPP   |  62.2%  (n=37)
2020 | PPPPFddPFPFPFPPPPPdFdFPPFPFFPPPPPPPPP   |  64.9%  (n=37)
2021 | PPPaPPPPPPFaPPPPPPP.PPPPPPF.PPFPaPFPP   |  75.7%  (n=37)
2022 | PFPPFFPPPFPFPPFPaPPFFFFPFdFPPFPFPPPdF   |  51.4%  (n=37)
2023 | FPaPFFPPPPP.PFFPPPPPFFPPFFFPPPPPPPP.F   |  62.2%  (n=37)
2024 | FPFFFFPFPFPPPPPPPaFFPPPPPPdFFFaPFPPPP   |  56.8%  (n=37)
2025 | PdPFPFFPPPPFPPPPFPPPPPPaPPFFF.PPFPFd.   |  59.5%  (n=37)
2026 | PPPFFFFd                                |  37.5%  (n=8)
```

`P` pass · `F` static floor −10 % · `d` daily −5 % · `a` abandon · `.` unresolved within 56 days.

The eye sees clusters — `FFFFa` in 2013, `FFFFPFPF` in 2024, the 2022 run of `FFFF`. That
impression is exactly what the rest of this document tests, and it does not survive.

**Death mix, vm 10 / H = 56**: pass 62.6 % · static floor −10 % 25.3 % · daily −5 % 5.2 % ·
abandon 4.1 % · unresolved 2.8 %. The floor, not the daily barrier, is what kills this book.

### 1b. How much do cohorts actually overlap? (`tables/overlap_vm*.csv`)

The brief assumed >95 % shared trajectory. Measured on the **decisive** window
(start → resolution, truncated at the horizon), Jaccard overlap of adjacent cohorts:

| vm | median Jaccard | mean | share of adjacent pairs with ZERO overlap | Jaccard if attempts ran the full 56 d |
|---|---|---|---|---|
| 8 | 0.071 | 0.203 | 46.8 % | 0.697 |
| 10 | 0.062 | 0.189 | 48.9 % | 0.697 |
| 12 | 0.000 | 0.187 | 50.4 % | 0.697 |

Median attempt duration is 11-12 calendar days (median **7 days** conditional on passing,
p90 ≈ 29). The barrier problem resolves fast; the nominal 8-9-week horizon is mostly
runway for the unlucky tail. **This is why the clustering is weak and why n_eff is high** —
and it is the single most load-bearing measurement in this study, because it invalidates the
premise that any clustering had to be there by construction.

### n_eff (`tables/clustering_vm*.csv`)

| basis | value (vm 10, H = 56) |
|---|---|
| nominal cohorts | 463 |
| **block bootstrap on the pass indicator** (dependence unit = `block_for_horizon(56)` = 6 cohorts) | **320** |
| variance-ratio implied (`n / VR₈`) | 383 |
| non-overlapping calendar tiling of the 56-day horizon | 82 |

The repo's "62 independent windows at 91 days" is the **tiling** figure, and it is the wrong
one for this object: it assumes an attempt occupies its whole nominal horizon. Realised
dependence gives **n_eff ≈ 305-380** across vm 8-12 and H 28-70. Power is therefore much
better than feared — see §3.

---

## 2. MAIN RESULT — clustering, real vs overlap-matched placebo

**The control.** The placebo re-runs the *entire* cohort machine on a tape whose directional
drift is destroyed and whose persistence is matched: a ±1 sign schedule on the overnight leg,
constant over blocks of 10 trading days (`p2_lib.block_signs`, the pre-existing control of the
phase-2 study). Everything else is untouched — same starts, same barriers, same measured costs,
same swaps, same volatility path, same vol clustering. So the placebo carries **exactly the
same overlap structure and no regime**. 150 replicates at vm 10, 70 at vm 8 / 12 / 14.

Statistics are base-rate normalised on purpose (run lengths are not, and are controlled
separately): lag-k autocorrelation of the pass indicator along the start axis, and the variance
ratio VR_q = Var(pass count in q consecutive cohorts) / [q·p(1−p)], which equals 1 under
independence whatever p is.

### vm 10 (`tables/clustering_vm10.csv`)

| H (cal. d) | p(pass) real | p(pass) placebo | AC₁ real | AC₁ placebo | p(AC₁) | VR₈ real | VR₈ placebo | p(VR₈) |
|---|---|---|---|---|---|---|---|---|
| 28 | 56.6 % | 49.4 % | 0.154 | 0.201 | 0.867 | 1.145 | 1.487 | 0.960 |
| 42 | 61.3 % | 52.5 % | 0.168 | 0.232 | 0.953 | 1.213 | 1.649 | 0.980 |
| 49 | 62.4 % | 53.3 % | 0.178 | 0.238 | 0.953 | 1.198 | 1.695 | 0.987 |
| **56** | **62.6 %** | **53.8 %** | **0.176** | **0.240** | **0.940** | **1.210** | **1.727** | **0.993** |
| **63** | **63.3 %** | **54.2 %** | **0.170** | **0.241** | **0.973** | **1.108** | **1.756** | **1.000** |
| 70 | 63.5 % | 54.3 % | 0.168 | 0.242 | 0.973 | 1.138 | 1.772 | 1.000 |

p is one-sided: the share of placebo replicates that cluster **at least as much as the real
series**. It is never below 0.87. **The real series is at the low end of the no-regime
distribution.**

### Same conclusion at every sizing (H = 56)

| vm (spec) | vm effective (×1.2) | AC₁ real / placebo | VR₈ real / placebo | p(VR₈) |
|---|---|---|---|---|
| 8 | 9.6 | 0.248 / 0.286 | 1.290 / 1.852 | 0.971 |
| 10 | 12.0 | 0.176 / 0.240 | 1.210 / 1.727 | 0.993 |
| 12 | 14.4 | 0.166 / 0.234 | 1.144 / 1.643 | 1.000 |
| 14 (deployed spec) | 16.8 | 0.201 / 0.247 | 1.342 / 1.635 | 0.814 |

**24 cells (4 vm × 6 horizons) and not one in which the real series clusters more than the
mean placebo.** No multiplicity correction is needed to accept a null this uniform.

### Base-rate control

The placebo has no drift, so its p(pass) sits ~9 pt below the real one, and run lengths depend
mechanically on p. Two controls, both in `tables/clustering_vm*.csv`:

* **matched subset** — placebo replicates with |p_plac − p_real| < 0.05 (n = 5-32 depending on
  the cell). Matched p-values: VR₈ 0.82-1.00, AC₁ 0.64-1.00, mean run 0.31-1.00. Same verdict.
* **regression adjustment** — each placebo statistic regressed on its own p_bar and evaluated
  at the real p_bar. z of real vs adjusted placebo: VR₈ **−1.34 to −2.44**, AC₁ **−1.04 to
  −2.35**. All negative: real clusters *less*, and at vm 12 significantly so.

### Run-length distribution (`tables/runlength_hist_vm*.csv`)

The deliverable asked for the distribution of same-outcome block sizes. vm 10, H = 56, 5-class
outcome label:

| run length | 1 | 2 | 3 | 4 | 5-6 | 7-9 | ≥10 | mean | max |
|---|---|---|---|---|---|---|---|---|---|
| real | 0.591 | 0.191 | 0.056 | 0.042 | 0.065 | 0.037 | 0.019 | 2.15 | 12 |
| placebo | 0.575 | 0.187 | 0.100 | 0.050 | 0.054 | 0.023 | 0.011 | 2.06 | 14.0 |

The real tail (runs ≥ 7) is marginally fatter than the placebo *mean* — but the placebo's own
max run averages **14.0** against the real **12**, and the whole difference disappears under
the base-rate controls above. The eye-catching `FFFF` blocks of 2022 and 2024 are inside what a
tape with **zero** directional edge produces on this cohort grid.

---

## 3. VERDICT on the contradiction: `Q1 10.7 % vs Q2 34.6 %` vs `timing NULL`

### How each was obtained

| | `ftmo_attribution_timing_2026-06` | `ftmo_checkup_2026-07` |
|---|---|---|
| design | **27 pre-registered buckets** (DOW 5, FOMC-wk 2, CPI-wk 2, ORB-regime 3, gold-state 3, month 12) | post-hoc scan, 4 quarters + 12 months |
| inference | block-bootstrap CIs, N_eff printed per bucket (19-237), **deflation bar √(2 ln 27) = 2.57** | none — the report's own caveat says *"block-bootstrap CIs still TODO"* |
| result | **max |z| = 1.70 < 2.57 → nothing survives**; months z ≤ 0.86 | raw extremes of an uncorrected 16-cell scan, reported as actionable |
| artefacts | `attribution_timing/tables/p3_buckets.csv` present and reproducible | **no generating script survives in the repo** |

**`attribution_timing` holds. `checkup` does not.** It is the multiplicity artefact its own
caveat page predicted.

Three further tells, all independent of my own runs:

* **It contradicts itself.** In the same document the 1-try lens calls October the *best*
  month (40 %) while the retry funnel calls Q4/October the *soft spot* (73.2 %, "Oct 67 %
  weakest"). A real calendar effect does not reverse sign between two lenses on the same
  cohorts.
* **It is not reproducible from the canonical artefacts of the same book family.** Rebuilding
  the 1-try funded flag from `attribution_timing/tables/attempt_log.csv` (462 cohorts, June v2
  4-sleeve book) gives quarters **25.0 / 25.7 / 28.1 / 29.3 %** — a 4.3 pt spread, not the
  claimed 24 pt, and Q1 is not the worst. Under a circular-shift null every quarter has
  p_shift ≥ 0.47, omnibus p = 0.86 (`tables/audit_checkup_seasonality.csv`). The closest
  artefact that *does* show the claimed *ordering* is the phase-2 leg alone (Q1 54.1 % vs Q2
  66.5 %, April 75 %) — a 1.23× effect, not 3×. **The 10.7 % level itself cannot be sourced
  to anything in the repo.**
* **The advice runs against the point estimates on this book** (below).

### My own test — circular-shift null (`tables/seasonality_vm*.csv`)

The outcome series is rotated against fixed calendar labels. This preserves the cohort
autocorrelation **exactly** (hence the overlap) and destroys only the calendar alignment. It is
the null the checkup never ran.

vm 10, H = 56, full sample:

| quarter | n | p(pass) | deviation | p_shift | p Šidák(4) | MDE80 |
|---|---|---|---|---|---|---|
| Q1 | 117 | 62.4 % | −0.2 pt | 1.000 | 1.000 | 21.1 pt |
| Q2 | 110 | 69.1 % | +6.5 pt | 0.374 | 0.846 | 21.4 pt |
| Q3 | 113 | 54.9 % | −7.8 pt | 0.251 | 0.685 | 20.9 pt |
| Q4 | 123 | 64.2 % | +1.6 pt | 0.875 | 1.000 | 20.5 pt |

**Omnibus (max |deviation| across the 4 quarters): p = 0.676. Range statistic: p = 0.613.**
At vm 8 omnibus p = 0.829, at vm 12 p = 0.387. Months (12 cells, Šidák): smallest adjusted p
is 0.19 (September, vm 12); nothing survives.

**Power.** n_eff ≈ 320 ⇒ ~80 effective observations per quarter. MDE80 per quarter
(Šidák-corrected over 4 cells, 80 % power) ≈ **21 pt**. The checkup's claimed Q1-vs-Q2 gap is
**24 pt** — comfortably above my MDE. **This is not an underpowered null: an effect of the
claimed size would have shown up, and it does not.** At the month level (MDE ≈ 30-35 pt with
n ≈ 37) the study *is* underpowered, which is precisely why month-level claims should never
have been made.

### And the sign is wrong

Point estimates on the deployed MONO book, vm 10, H = 56:

* **Q1 is dead on the average** (62.4 % vs 62.6 % overall) — not the worst quarter. Q3 is (54.9 %).
* **January is the second-best month** (75.0 %), not a month to avoid.
* **April is below average** (58.3 %); **October is the third-worst** (53.5 %).

So the operational instruction *"avoid Jan-Feb, launch in April or October"* is not merely
unsupported — on this book its point estimates point the other way. **Retire it.**

---

## 4. The recent era — post-2021 (`tables/era_vm*.csv`)

This is where the interesting result is, and it is not about timing.

vm 10, H = 56:

| era | n cohorts | p(pass) real | placebo mean | placebo 5-95 % | edge | AC₁ | VR₈ | n_eff |
|---|---|---|---|---|---|---|---|---|
| full 2013-2026 | 463 | 62.6 % | 53.8 % | [49.8, 58.4] | **+8.8 pt** | 0.176 | 1.21 | 320 |
| pre-2021 | 270 | 64.4 % | 50.2 % | [44.4, 55.6] | **+14.2 pt** | 0.213 | 1.34 | 182 |
| **post-2021** | **193** | **60.1 %** | **58.8 %** | **[52.0, 65.6]** | **+1.3 pt** | 0.120 | 1.48 | 167 |

Same at vm 8 (edge +14.2 pt → **−1.0 pt**) and vm 12 (+13.4 pt → **+1.9 pt**), and at H = 49
and 63. **Post-2021 the real pass rate is inside the placebo's 5-95 % band in every single
cell.** A sign-scrambled, zero-drift version of the same book, with the same volatility and the
same costs, reaches the same phase-2 pass rate.

Read it precisely:

* It does **not** say the book is broken. 60 % is still 60 %, and it is what the barrier
  geometry pays: a +5 % target with vol targeting against −5 % daily / −10 % static barriers is
  a favourable bet even on a driftless tape. This is the same mechanism as
  `orb_realconstraints_2026-06` ("placebo 97.7 % proves no-bust is mathematical, not an edge").
* It **does** say that **the overnight premium is no longer measurably contributing to phase-2
  p(pass) after 2021**, consistent with the erosion already on record (t 1.66 post-2021, 0.94
  excluding 2020). Whatever value phase 2 has now, it is being priced by the geometry, not by
  the sleeve.
* Clustering post-2021 is, if anything, *weaker* than full sample (AC₁ 0.120 vs 0.176), so
  there is nothing to time here either.

Post-2021 seasonality is also null (omnibus p = 0.601; Q2 highest at 71.7 %, p_shift 0.259,
Šidák 0.699; MDE80 ≈ 27-30 pt with n ≈ 46-53 per quarter — this sub-sample *is* underpowered
and should not be used to make any calendar claim in either direction).

---

## 5. Implication for p(campaign) — the conclusion-2 branch, chiffrée

The mission asked: if outcomes cluster, a re-buy after a failure lands inside the same bad
stretch, attempts are positively correlated, and `1 − (1 − p)^K` overstates the campaign.
**Measured, this does not happen** (`tables/campaign_vm10.csv`, `campaign_K_curve_vm10.csv`).

Sequential simulation on the real tape: attempt 1 from each of the 463 cohort starts; on
failure, re-buy at **resolution + 2 business days** (the simulator's own rule); up to K = 6
phase-2 attempts.

| | value |
|---|---|
| p(pass), single attempt, unconditional | **63.71 %** |
| **p(pass \| the previous attempt failed)** (n = 250 conditional attempts) | **67.20 %** |
| attempts to funded, measured | 1.540 |
| attempts to funded, under independence | 1.566 |

| K | p(funded ≤ K) measured | under independence | independence − measured |
|---|---|---|---|
| 1 | 63.71 % | 63.71 % | 0.00 pt |
| 2 | 87.26 % | 86.83 % | **−0.42 pt** |
| 3 | 96.11 % | 95.22 % | **−0.89 pt** |
| 4 | 99.14 % | 98.27 % | −0.87 pt |
| 5 | 99.78 % | 99.37 % | −0.41 pt |
| 6 | 100.00 % | 99.77 % | −0.23 pt |

**The dependence is mildly NEGATIVE, not positive.** Conditional on having just failed, the
next phase-2 attempt passes **3.5 pt more often** than unconditionally — a failure typically
means the account died on the floor after a bad stretch that is then over. The independence
formula therefore *understates* the campaign by up to 0.9 pt rather than overstating it. The
same computation on 25 placebo replicates gives −0.11 pt: the small negative gap is mechanical
(re-buys are not calendar-aligned with the cohort grid), not a regime.

**So the "~4.3 challenges per funded" model is not biased by serial dependence.** Two scope
limits, stated plainly: this measures **phase 2 only**, where p is high (64 %) and K = 6
saturates, and it uses the deployed MONO book. The full 2-step campaign has a much lower
per-attempt p, where the same *sign* of dependence would matter more in magnitude — but the
sign measured here is the benign one, and the conditional/unconditional gap (+3.5 pt) is the
transferable statistic.

---

## 6. Mechanism — L38 and L54 (`tables/mechanism_*_vm10_H56.csv`)

Run anyway, because a null clustering result is only trustworthy if the obvious confounder is
also measured. The sleeve is long-only overnight on indices, so the default suspicion is that
"good periods" are simply bull markets.

| regression (HAC, maxlags = 6 cohorts) | β | t | **R²** |
|---|---|---|---|
| **L38** pass ~ vol-targeted US100+GER40 B&H over the SAME window | +0.82 | 1.24 | **0.4 %** |
| L38b pass ~ realised index vol over the same window | −0.60 | −1.78 | 0.8 % |
| **L54 MEAN** — index return over window ~ rv60 at T−1 | +0.043 | 0.89 | **0.5 %** |
| **L54 VARIANCE** — realised vol over window ~ rv60 at T−1 | +0.331 | **3.30** | **9.2 %** |
| L54 variance — squared index return ~ rv60 at T−1 | −0.007 | −2.11 | 2.6 % |

* **L38: R² = 0.4 %, far below the 30 % bar. The outcome is NOT index beta.** Phase 2 is a
  barrier-hitting problem resolved in ~12 days; 8-week index drift barely touches it. This is a
  real orthogonality result, not a get-out.
* **L54 in textbook form: the pre-start state predicts the VARIANCE (R² 9.2 %, t 3.30) and not
  the MEAN (R² 0.5 %, t 0.89).** A state that only moves the variance cannot make a timing rule
  — the same conclusion the checkup itself reached for vol regime ("p(pass) flat, 23 % ± 1,
  high-vol only takes LONGER") and the one L24 predicts.

**Ex-ante predictability** — the only honest test, using states knowable strictly *before* the
start date: 4 predictors × 3 terciles = 12 pre-declared buckets, block-bootstrap SEs,
deflation bar √(2 ln 12) = **2.23**.

| predictor at T−1 | low | mid | high | max \|z\| | survives? |
|---|---|---|---|---|---|
| rv60 | 67.8 % | 64.7 % | 57.9 % | 1.16 | no |
| 60d index momentum | 56.5 % | 67.1 % | 64.3 % | **1.78** | no |
| 252d index momentum | 57.8 % | 64.3 % | 65.8 % | 1.15 | no |
| drawdown from 252d high | 63.6 % | 64.1 % | 61.0 % | 0.35 | no |

**Max |z| = 1.78 < 2.23. Nothing survives** — the same answer, on a different book and a
different phase, that `attribution_timing` got with 27 buckets (max |z| 1.70 < 2.57). MDE80 per
bucket ≈ 10-14 pt. No new angle was opened on `regime_markov_sleeves_2026-07`, which had already
falsified "regime = alpha" at the orthogonality filter; this is a consistency check, not a
re-test.

---

## 7. Sensitivity

* **vm** 8 / 10 / 12 / 14 (spec) = 9.6 / 12 / 14.4 / 16.8 effective in phase 2. Every
  conclusion identical. p(pass) at H = 56 is flat in vm (62.9 / 62.6 / 62.6 / 61.8 %) — sizing
  does not move phase-2 odds in this range, consistent with `phase2_sizing_2026-08`.
* **horizon** 28 → 70 calendar days. Identical. p(pass) gains only +0.9 pt going from 56 to 70
  days at vm 10, because 97 % of cohorts have already resolved by day 56.
* **placebo persistence** fixed at 10 trading days (the pre-existing matched value). The real
  AC₁ is 0.17 and the placebo's 0.24, so if anything the placebo is *more* persistent than the
  real tape — the test is conservative in the direction that matters.
* **cross-check engine**: the cleanroom + `fix_deadlock` arm (no micro-ORB) is carried by the
  inherited harness and does not change the sign of anything here.

## 8. Files

| file | content |
|---|---|
| `code/cc_lib.py` | thin wrapper over `phase2_sizing_2026-08/code/p2_lib.py`; clustering statistics |
| `code/run_cohorts.py` | regenerates real + placebo per-cohort resolutions |
| `code/analyze.py` | overlap, clustering vs placebo, run-length histogram, shift-null seasonality, era split |
| `code/campaign.py` | sequential re-buy simulation, measured vs independent |
| `code/mechanism.py` | L38 / L54 regressions + ex-ante tercile buckets |
| `code/audit_seasonality_claim.py` | re-derivation of the checkup claim from `attempt_log.csv` |
| `tables/cohort_timeline_vm*.csv` | **deliverable 1** — outcome per start date |
| `tables/overlap_vm*.csv` | decisive-window overlap of adjacent cohorts |
| `tables/clustering_vm*.csv` | **deliverable 2** — real vs placebo, all statistics, base-rate controls |
| `tables/runlength_hist_vm*.csv` | block-size distribution, real vs placebo |
| `tables/seasonality_vm*.csv` | **deliverable 3** — circular-shift null, Šidák, MDE |
| `tables/audit_checkup_seasonality.csv` | audit of the Q1/Q2 citation |
| `tables/era_vm*.csv` | **deliverable 4** — pre/post-2021 |
| `tables/campaign_vm10.csv`, `campaign_K_curve_vm10.csv` | **deliverable 5** — p(campaign) |
| `tables/mechanism_reg_vm10_H56.csv`, `mechanism_buckets_vm10_H56.csv` | L38 / L54 / ex-ante |

Per-cohort raw resolutions and placebo replicate arrays live in `outputs/` and are
**gitignored** — no data blob is committed. `code/run_cohorts.py` regenerates them
(~13 min for the full set on an unloaded machine).

---

## What this does NOT prove

1. **It does not prove the sleeve has no edge.** It proves the *outcome of a phase-2 challenge*
   does not group in time beyond overlap, and that post-2021 the pass rate is inside the
   no-drift band. Those are statements about a barrier-hitting problem with a 12-day median
   resolution, not about the sleeve's Sharpe.
2. **It does not prove that no calendar effect exists — only that none ≥ ~21 pt per quarter
   exists.** Below that, this sample cannot see. At the month level the study is genuinely
   underpowered (MDE ≈ 30-35 pt); the month table is descriptive only, in both directions.
   In particular "January is the best month, 75 %" is **not** a finding and must not become the
   next `Q1 10.7 %`.
3. **It does not clear phase 1.** Everything here is phase 2 (+5 % target) on the deployed MONO
   book. Phase 1 (+10 %) has a longer decisive window, therefore genuinely more overlap between
   cohorts, and the overlap measurement of §1b would have to be redone before transporting any
   of this.
4. **The placebo destroys drift, not everything.** It preserves the realised volatility path,
   the cost panel, the swap panel and the calendar. A regime that acts through *volatility
   alone* would be present in both arms and invisible to this test. §6 covers that channel
   separately (rv60 predicts variance, not mean) but by a different instrument.
5. **One market history.** 463 cohorts, n_eff ≈ 320, a single 2013-2026 tape. The placebo
   controls the *overlap*, not the fact that there is only one realised path of history.
6. **The p(campaign) result is phase-2-only and saturating.** K = 6 at p = 64 % reaches 100 %;
   the informative statistic is the conditional gap (+3.5 pt, benign sign), not the campaign
   levels, and it has not been re-measured on the full 2-step funnel.
7. **The checkup audit is a reconstruction.** The generating script for `Q1 10.7 % / Q2 34.6 %`
   does not exist in the repo; I re-derived the closest object from `attempt_log.csv`. I can
   show the claim is not reproducible and would not survive a proper null — I cannot show
   exactly which step produced the 10.7 %.
8. **No Sharpe is claimed here, so no DSR is reported.** The multiplicity instruments used are
   Šidák over the calendar cells and the √(2 ln k) deflation bar over the pre-declared buckets,
   matching `attribution_timing`. Importing a DSR would have been decoration.
