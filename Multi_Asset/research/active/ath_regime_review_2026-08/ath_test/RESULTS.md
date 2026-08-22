# RESULTS — Does proximity to the all-time high condition the MEAN of the deployed FTMO
# overnight book?

**Verdict: REJECTED — and along the way, a config bug that was understating Phase-2
p(pass) by 2.7×.** Near the ATH the sleeve earns less *and* risks less, but the effect is a
lagged inverse-**volatility** proxy: controlling for trailing realised vol shrinks it 82-89%
and kills the t (−2.94 → −0.49), a plain vol-quartile sort captures a *larger* spread, and
on the decision metric the exposure variant sits at the **54th-58th percentile of its own
placebo band**. Nothing here justifies changing exposure. **Separately and more
importantly: the inherited config literal scored 183/183 Phase-2 winners as deaths —
corrected P2 p(pass) is 63.4%, not 23.1%.**

Design frozen in `PREREGISTRATION.md` before any number below was computed. Sample
2013-10-01 → 2026-06-05, 3,295 engine days. Writes confined to this folder; no git command
was run; `regime_overlay_ftmo_2026-07/`, the cleanroom engine, `ftmo_live/` and `Portfolio/`
were read-only.

---

## 0. STEP 0 — the config audit, which turned out to matter more than the question

The suspicion was correct, the mechanism is worse than "a missing key", and it bites
**hardest in Phase 2** — the phase the account is actually in.

**What is missing.** `MIN_OPEN_DAYS = 4` is a *module constant* in `cleanroom/engine.py`
and is always enforced. The escape hatch is the **`fix_deadlock` cfg key**
(`engine.py:363-368`). It is **absent from `CFG_V2`, from the study's `CFG_LIVE`, and from
`CFG_MONO`** — see `outputs/config_diff.csv`. Every other difference between those literals
is deliberate and documented (`orb_risk=0` for the MONO book, `mrate=MRATE_SWING`,
`brk_mode="daily"`, `brk_needs_pos=True` for EA v2.4).

**The mechanism is an absorbing deadlock, not a rounding error.** Once the account is above
target and flat, at bar 0 of segment 0 of *every subsequent day* `hit_tgt` fires
immediately, the engine flattens (a no-op), finds `open_days < 4`, and latches
`flat_today = True` **for the whole day**. It therefore never opens a position again,
`open_days` never increments, and the account rides the 91-day wall to `timeout`. Verified
directly:

```
start 2014-01-16  out=timeout  end=10,523.52  goal=10,500.00  used=66 days  above_target=True
start 2014-01-27  out=timeout  end=10,581.16  goal=10,500.00  used=66 days  above_target=True
```

**Measured impact** (454 cohort starts, 91-day wall, `outputs/config_impact.csv`):

| geometry | p(pass) | bust daily | bust floor | timeout | median days | share of deaths **at or above target** |
|---|---:|---:|---:|---:|---:|---:|
| **P2 (+5%) inherited** | **23.13%** | 5.73% | 26.65% | **40.31%** | 16 | **52.4%** |
| **P2 (+5%) corrected** | **63.44%** | 5.73% | 26.65% | **0.00%** | 7 | 0.0% |
| P1 (+10%) inherited | 25.99% | 11.45% | 37.44% | 19.38% | 21 | 22.9% |
| P1 (+10%) corrected | 42.95% | 11.45% | 37.44% | 2.42% | 12 | 0.0% |

`bust_daily` and `bust_floor` are **identical** across the pair: the entire difference is
the artefact. **All 183 Phase-2 timeouts were accounts sitting above +5%** — 100% of
"timeouts", 40.3% of all cohorts, 52.4% of all "deaths". Phase 2 is hit harder than Phase 1
exactly as predicted: the +5% target is reached sooner, so more accounts arrive above target
before the day counter fills, and with `orb_risk = 0` the counter only ticks on Mon/Tue.

**Where it does *not* bite.** `build_book.run_book` pins equity at INIT and never evaluates
a target, so `fix_deadlock` is provably inert there: return streams with and without it are
**bit-identical** (`max_abs_diff = 0.0`). **The 2026-07 study's return-stream reconstruction
and its REJECTED verdict are unaffected** — that verdict rests on paired comparisons under
one convention. Its *absolute* cohort levels (the "7% p(campaign)") are contaminated.

Corrected config is used for every p(pass) below, and both versions are reported.

## 1. The conditioner — clean, and verified rather than asserted

Two definitions, both strictly T−1 (`.reindex(...).ffill().shift(1)`), because US100 posts
risk at **22:05 CET = 16:05 ET**, before the US cash close prints:

- **C1** = drawdown from the **expanding** running max ("all-time"), seeded from 2000-01 —
  `panel_px` reaches back to 2000, so this covers the dot-com high and the pre-registered
  "since 2007" caveat is moot.
- **C2** = `1 − price / 252-day rolling max`, the **George & Hwang 52-week-high ratio**.

Checks demanded by the pre-registration, all passed:

| check | US100 | GER40 |
|---|---|---|
| corr(panel_px, engine M5 daily last) | 0.999959 | 0.999888 |
| corr(panel_px, deep_history_utc daily) | 0.999979 | 0.999843 |
| flat-bar / zero-diff share (L60) | 0.001 | 0.000 |

Look-ahead assertion (rebuild from truncated prices at 40 cut dates, both conditioners,
both legs): **PASS**. Duty cycle of B0 (`dd ≤ 1%`): C1 26.1%, C2 35.2% on US100.

**Costs.** The `spread` column of `data/deep_history_utc/` is used **nowhere**. Leg returns
carry the audited measured round-trip (2.2 bps) **and the measured asymmetric FTMO swap**
(US100 −1.76 bps/night, GER40 −1.23 bps/night on ON days). Swap is ~43% of the US100 leg's
all-in cost and is never omitted.

## 2. The answer: near the ATH the sleeve earns LESS and risks LESS

US100 overnight leg, **net** of RT and swap, ON days only (`outputs/bucket_tables.csv`):

| bucket (C1) | n | mean bps | t_HAC | median | skew | p5 | ann vol |
|---|---:|---:|---:|---:|---:|---:|---:|
| **B0 at the high (dd ≤ 1%)** | 344 | **−1.49** | −0.68 | +1.34 | −0.92 | −77.1 | **688%** |
| B1 (1-3%) | 212 | −4.98 | −1.22 | −1.12 | −0.80 | −112.0 | 929% |
| B2 (3-7%) | 268 | +0.86 | 0.23 | +0.37 | −0.12 | −99.4 | 1019% |
| **B3 far (>7%)** | 493 | **+13.88** | **3.52** | +3.92 | +0.91 | −132.6 | **1550%** |
| ALL | 1317 | +4.18 | 2.28 | +2.24 | +0.82 | −111.7 | 1177% |

Deployed MONO book, active days, C1 on US100:

| bucket | n | mean bps | t_HAC | ann vol | **P(day < −5%)** | worst day |
|---|---:|---:|---:|---:|---:|---:|
| **B0 at the high** | 523 | **+35.96** | 1.66 | **66.8%** | **7.27%** | −19.5% |
| B1 | 318 | +49.67 | 1.55 | 82.5% | 10.06% | −18.2% |
| B2 | 389 | +17.45 | 0.53 | 103.9% | 13.62% | −31.9% |
| **B3 far** | 727 | **+103.80** | 3.15 | **123.1%** | **14.17%** | −26.0% |

### 2.1 The L54 test, reported first as pre-registered

The conditioner **does** forecast variance, strongly and monotonically: 66.8% → 123.1%
annualised, and the daily-barrier hazard **doubles** from 7.3% to 14.2%. Near the ATH is
unambiguously the **benign** state in risk terms.

But it forecasts the **mean in the same direction**: +36 bps near the high vs +104 bps far
from it; on the raw US100 leg, **0 net vs +13.9 bps**. The overnight index premium is
compensation for variance, so the calm state is also the barren one. **This is L54's
mechanism reappearing on a brand-new conditioner** — and it is why the ATH cannot be traded
as a "danger" signal: there is no danger there to avoid.

### 2.2 The literature prior is falsified in direction for this object

Pre-registered prior (§2 of `PREREGISTRATION.md`): the 52-week-high literature says near the
high predicts **positive** future returns, so near-ATH should be **benign with an equal or
higher mean**. Measured: near-ATH mean is **lower**, on both conditioners and both legs,
and the sign is stable across all four sub-periods (4/4 negative).

This is a falsification of the prior **for this object only**, and the pre-registered caveat
binds: that literature is **cross-sectional on individual stocks** (rank a universe by
price / 52-week-high). This is a **time-series** test on an **index**, on one 17-hour
overnight window. The result does not touch the cross-sectional finding, and §3 shows it is
not really a test of anchoring at all.

## 3. THE FALSIFIER — the conditioner is a lagged inverse-volatility proxy

Near the ATH *is* a low-realised-vol state (`corr(B0, trailing vol) = −0.36 to −0.44`). L38
orthogonality test, `outputs/orthogonality.csv`:

| object | cond | B0 alone | t | **B0 controlling for trailing 20d vol** | **t** | vol coef | t | shrink |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| US100 leg net | C1 | −7.67 | −2.43 | **−0.88** | **−0.26** | +79.3 | 3.01 | **89%** |
| US100 leg net | **C2** | **−9.14** | **−2.94** | **−1.68** | **−0.49** | +77.3 | 2.81 | **82%** |
| GER40 leg net | C1 | −6.19 | −1.64 | −1.87 | −0.49 | +75.8 | 2.39 | 70% |
| Book, active | C2 | −76.55 | −2.02 | **+28.52** | **+0.64** | +1091 | 2.96 | **sign flips** |

**Horse race.** A plain trailing-vol quartile sort captures a *larger* spread than the ATH
buckets on the same series: **+16.81 bps** (Q4 high-vol +17.80, t 3.58, vs Q1 +0.99) against
**+15.37 bps** for the ATH buckets. The ATH conditioner is a noisier, lagged version of a
variable we already have for free — it adds nothing and subtracts precision.

**Supporting fragility.** Deciles are **not monotone** (D1 +31, D4 +78, D5 −2, D7 +182,
D9 +49 bps). No sub-period contrast is individually significant (|t| = 0.74-1.60) and the
magnitude decays (−68 → −94 → −97 → −29 bps). The placebo pool mean equals the unconditional
mean to within **0.003-0.058 pooled SE** on every object, so the **L58 baseline check
passes** — the placebo is unbiased, and the signal is what is weak.

## 4. Decision translation — PHASE 2 (+5%), as confirmed by the risk-bearer

Geometry simulated: **Phase 2, €10,000 fresh equity, target +5% → 10,500, static floor
9,000 (−10% of initial), daily budget €500 (−5%) anchored 00:00 CET**, min 4 open days.
**No Phase-1 or funnel figure is quoted.** 20,000 stationary-block-bootstrap paths
(mean block 10, never iid), all variants on the **same** pre-drawn index matrix so every Δ
is paired. Corrected backstop (`flat_after_target`) plus the inherited behaviour for
contrast (`outputs/decision_p2.csv`).

| variant (corrected P2) | ann vol | p(pass) | Δp | paired 95% CI | median days | p90 days |
|---|---:|---:|---:|---:|---:|---:|
| **baseline** | 77.5% | **55.95%** | — | — | **7** | **14** |
| V+ cut at the high (C1) | 73.7% | 57.67% | +1.72pt | [+1.33, +2.11] | 8 | 19 |
| V+ cut at the high (C2) | 73.2% | 58.47% | +2.52pt | [+2.10, +2.94] | 8 | 21 |
| *de-lever vol-matched to V+ C1* (c=0.942) | 73.7% | 57.14% | +1.18pt | [+0.98, +1.38] | 7 | 15 |
| *de-lever vol-matched to V+ C2* (c=0.933) | 73.2% | 57.14% | +1.19pt | [+0.98, +1.40] | 7 | 15 |
| V− cut away from the high (C1) | 37.3% | 63.84% | +7.89pt | [+7.24, +8.54] | 11 | 35 |
| *de-lever vol-matched to V− C1* (c=0.414) | 37.3% | **64.34%** | +8.39pt | [+7.73, +9.05] | 10 | 36 |

Read the pairs. **V− (cutting away from the high) FAILS its de-lever outright** (−0.50pt,
−2.40pt on C2) — as expected, since it cuts the high-mean state. **V+ nominally beats its
de-lever** by +0.53pt (C1) and +1.33pt (C2), which is the only apparent PASS in this study.

### 4.1 The placebo band on the decision metric kills it

The pre-registration requires that gap to be read against "any exposure schedule with this
duty cycle and this persistence" — 120 circular rotations, same paths
(`outputs/placebo_decision.json`):

| | baseline | **real V+** | placebo p50 | placebo p95 | placebo max | **percentile of real** |
|---|---:|---:|---:|---:|---:|---:|
| **C1** | 55.71% | **57.41% (+1.70pt)** | 57.18% | 59.16% | 59.84% | **0.575 → INSIDE BAND** |
| **C2** | 55.71% | **58.23% (+2.51pt)** | 58.07% | 59.69% | 60.99% | **0.542 → INSIDE BAND** |

**A randomly placed schedule with the same duty cycle is worth +1.55pt (C1) and +2.31pt
(C2) on its own.** The real ATH schedule lands at the 57.5th and 54.2nd percentile of its
own placebo — indistinguishable from noise. At 14× leverage against a −5% daily barrier,
reducing exposure on *any* 26-35% of days helps mechanically; **the information content of
the ATH is zero.** And the gain is paid for in time: median 7 → 8 days, **p90 14 → 19-21
days**, which for a challenge is the wrong currency.

## 5. Verdict against the pre-registered rule

| condition | US100 leg C1 | **US100 leg C2** | GER40 C1/C2 | book C1 | book C2 |
|---|:--:|:--:|:--:|:--:|:--:|
| (a) \|t_HAC\| ≥ 2.63 (Šidák, 6 tests) | ❌ 2.43 | ✅ 2.94 | ❌ | ❌ 1.10 | ❌ 1.99 |
| (b) outside matched-placebo band | ✅ p0.03 | ✅ p0.004 | ❌ | ❌ p0.27 | ✅ p0.04 |
| (c) L58 unconditional-baseline check | ✅ | ✅ | ✅ | ✅ | ✅ |
| (d) sign stable across sub-periods | ✅ | ✅ | ✅ | ✅ (never sig.) | ✅ |
| (e) beats vol-matched de-lever on Δp(pass) | — | ✅ nominal → ❌ **inside placebo band** | — | — | ✅ nominal → ❌ **inside band** |
| **orthogonality to trailing vol** | ❌ 89% shrink | ❌ **82% shrink, t→−0.49** | ❌ | ❌ | ❌ **sign flips** |

**1 of 6 primary tests clears the significance bar, and it does not survive the volatility
control.** Verdict: **REJECTED**.

Nature of the kill, for the re-opening policy: **MECHANICAL — by confound**. The conditioner
carries no information beyond trailing realised volatility, which is already available for
free and measures the same thing better. Per the project's re-opening table, a mechanical
kill **STAYS CLOSED**: recalibrating a statistic does not create information that is not
there. Do not re-propose distance-to-ATH, 52-week-high ratio, or any monotone transform of
either, as a state variable on this book.

**Modification budget: 3 allowed, 0 consumed.** No bucket edge, window, or threshold was
changed after the data was touched.

## 6. What this establishes

1. **The Phase-2 p(pass) of the deployed book is 63.4%, not 23.1%** (cohort funnel), and
   55.95% on bootstrap paths. Any decision taken against the inherited number was taken
   against a figure understated **2.7×** by a simulation artefact that scored winners as
   deaths. This is the session's most consequential output and it is independent of the ATH
   question.
2. **Near the ATH is the benign-but-barren state**: half the daily-barrier hazard (7.3% vs
   14.2%), and roughly a third of the return (+36 vs +104 bps). There is nothing to cut.
3. **A new conditioner reproduced L54 exactly** — the regime that predicts variance predicts
   the mean in the same direction, so every exposure cut removes the days that pay. L54 now
   has an independent confirmation on the *high* side of the distribution, not just the
   stress side.
4. **Candidate lesson (named, not numbered).** *A state variable that is monotone in
   trailing volatility must be regressed against trailing volatility before it is called a
   state variable.* Distance-to-ATH looked like a −2.9σ effect and was 82-89% trailing vol;
   the free control that catches it is one extra regressor. Companion to L38, applied to
   conditioners rather than to sleeves.
5. **Candidate lesson (named, not numbered).** *At high leverage against a symmetric daily
   barrier, ANY duty-cycled exposure cut buys p(pass) — so a conditional overlay must be
   read against a rotation placebo on the DECISION metric, not on the t-stat.* Measured
   here: a random 26-35% duty-cycle schedule is worth +1.6 to +2.3pt of p(pass) by itself,
   which is larger than the entire apparent ATH effect.

## 7. Reproduce

```
/usr/bin/python3 config_audit.py       # STEP 0: config diff + measured impact  -> outputs/
/usr/bin/python3 conditioner.py        # conditioners + leg returns + look-ahead assertion
/usr/bin/python3 measure.py            # bucket/decile tables, contrasts, placebo, sub-periods
/usr/bin/python3 controls.py           # orthogonality to trailing vol + horse race
/usr/bin/python3 decision.py           # PHASE-2 (+5%) campaign, variants vs de-lever
/usr/bin/python3 placebo_decision.py   # rotation placebo band on the decision metric
```
Outputs: `config_diff.csv`, `config_impact.csv`, `bucket_tables.csv`, `contrast_table.csv`,
`deciles.csv`, `subperiods.csv`, `book_tail.csv`, `orthogonality.csv`, `decision_p2.csv`,
`decision_verdict.json`, `placebo_decision.json`, `measure.json`, `controls.json`.
`cache/` is regenerable.
