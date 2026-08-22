# PRE-REGISTRATION — Does proximity to the all-time high condition the MEAN of the
# deployed FTMO overnight book?

**Frozen 2026-08-09, before any conditioner number, bucket mean, or t-stat was computed.**
Session `ath_regime_review_2026-08`. Writes are confined to
`Multi_Asset/research/active/ath_regime_review_2026-08/ath_test/`. No git command is run.
`regime_overlay_ftmo_2026-07/`, the cleanroom engine, `ftmo_live/` and `Portfolio/` are
**read-only** here.

---

## 0. Why this is not a re-run of `regime_overlay_ftmo_2026-07`

That study is REJECTED and stays rejected. It tested two **stress** flags — VIX/VIX3M > 1
and US100 < MA200 — i.e. the *left* side of the state distribution, proposed as an
exposure-cutting overlay. Its decisive finding (now L54) was that the book's high-variance
regimes are also its high-**mean** regimes, so cutting there removes the earnings.

This study is a different object on three counts, and it is opened under the project's
re-opening policy in the **POWER** category (a conditioner never measured, not a
recalibration of a dead one):

1. **The conditioner is new and lives on the opposite side of the distribution.** Distance
   to the all-time high is a *high*-side state variable. Nothing in the prior study
   measured it. `US100 < MA200` is not its complement: MA200 is a slow trend filter that
   fires ~18% of days, whereas "within 1% of the ATH" is a distinct, much tighter state.
2. **It is a MEASUREMENT of conditional EV, not a proposed overlay.** The primary
   deliverable is the conditional mean/variance table for the two legs and the book. The
   exposure variant in §7 exists only to translate a measured effect into the project's
   decision metric, and is pre-committed to fail if it cannot beat a constant de-lever.
3. **It carries a directional prior from published work** (§2), so it is falsifiable in
   both directions rather than being a fishing expedition.

Re-opening discipline: this angle is written here **before** the data is touched. If the
result is null, that is the deliverable; no threshold, bucket edge, or window will be
changed after seeing a number.

Modification budget for the hypothesis: **3 allowed, 0 consumed.** Any bucket-edge or
window change after §8 is executed counts against it and is logged in RESULTS.md.

## 1. The question

The deployed book is **MONO**. What trades is a single unconditional sleeve: **US100
22:05→15:30 CET** and **GER40 17:35→09:00 CET**, **Mondays and Tuesdays only**, **LONG-only,
with no signal at all** (`cleanroom/engine.py:171-173` — `ON = 1.0` iff `dayofweek ∈ {0,1}`).
Both indices are currently at or near their all-time highs.

**Question:** is the return of those nights different **in the MEAN** — not merely in the
variance — when price is near its all-time high?

Explicitly *not* asked: whether an ATH overlay should be deployed (that is a consequence,
decided by §7's rule), and anything about ΔSharpe (not a decision metric here).

## 2. Directional prior, frozen before the data — and its limit

The 52-week-high literature (George & Hwang 2004; Chen, Stivers & Sun 2024; "Momentum on
historical high" 2024; "Anchor Reversion: the case of the 52-week high and asset prices")
predominantly finds that **proximity to the high predicts POSITIVE future returns** —
anchoring / under-reaction: traders anchor on the salient high and under-react to good
news near it. (A parallel session is doing the detailed review; it is not duplicated here.)

**Frozen prior: near-ATH is the BENIGN state — mean equal or HIGHER, not lower.**
Under that prior the correct decision is *no exposure cut*, and a measured near-ATH mean
that is *lower* would be the surprise. Writing the prior down is what makes the test
falsifiable in both directions.

**⚠ CAVEAT, stated up front because it bounds every inference below.** That literature is
**CROSS-SECTIONAL on INDIVIDUAL STOCKS**: it ranks a universe of names by
price / 52-week-high and goes long the top decile against the bottom. It does **not**
establish a **time-series TIMING** effect on an **INDEX**. This study is time-series, on an
index, on a single 17-hour overnight window, at 14× leverage against a −5% daily barrier —
a different object. The literature supplies a **direction and a mechanism, not a
transposable validation**. A confirmation here is weak evidence for the anchoring story; a
rejection here does not touch the cross-sectional result. The project's own N≥30 rule for
cross-sectional claims is why the cross-sectional version cannot be run on 2 instruments.

## 3. Step 0, run FIRST: audit the config literal before any p(pass) is quoted

Documented suspicion: the `CFG_MONO` / `CFG_LIVE` literals in
`regime_overlay_ftmo_2026-07/` omit the engine's **min-trading-days backstop**, and the
same omission elsewhere counted **winners as deaths** (88% of "timeouts" at or above
target).

Mechanism to check (`cleanroom/engine.py`): `MIN_OPEN_DAYS = 4` is a **module constant**,
always enforced, but the escape hatch is the **`fix_deadlock` cfg key** (engine.py:363-368)
— "a rational trader above target with <4 open days opens a token 0.01-lot trade to tick
the day counter". Without it, an account that reaches its target early is forced to keep
posting **full-size** risk until it has 4 open days, and can die above target.

**This bites far harder in Phase 2** (§6): the target is +5%, not +10%, so a P2 account
reaches target sooner and is more likely to hit it with fewer than 4 open days. And because
`orb_risk = 0` in the MONO book, the day counter only ticks on **Mon/Tue**, so reaching 4
open days takes **≥ 2 calendar weeks** at minimum.

Frozen actions, in order, before any conditioner statistic:
1. Diff `CFG_MONO` and `CFG_LIVE` against the engine's `CFG_V2` and against the module
   constants; report every key that differs, and classify each as *deliberate* (MONO book:
   `orb_risk=0`, `WT≡0`) or *omission*.
2. Report where the omission does and does **not** bite: `build_book.run_book` pins equity
   at INIT and never evaluates a target, so `fix_deadlock` is inert there; the funnel path
   (`run_funnel`/`run_phase`) is where it bites.
3. **Measure** the impact: re-run the P2 funnel with and without `fix_deadlock=True`, and
   report Δp(pass), Δduration, and the share of "deaths" that occurred **at or above
   target**. If that share is material, every downstream p(pass) uses the corrected config
   and the uncorrected numbers are labelled as such.
4. My copy only. The `regime_overlay_ftmo_2026-07` folder and the engine are not modified.

## 4. The conditioner — two definitions, both strictly T-1

Hard rule: signal at T-1, trade at T. The binding look-ahead hazard here is that **US100
posts risk at 22:05 CET = 16:05 ET**, before the US cash close prints settle, so any
same-day US end-of-session value is forbidden. GER40 posts at 17:35 CET, earlier still.

**Frozen rule: every conditioner is built from daily closes through day T−1 and then
`.reindex(engine_dates, method="ffill").shift(1)`.** Verified mechanically, not asserted,
by rebuilding the conditioner from truncated inputs at ≥40 cut dates and requiring every
past value to be unchanged (mirrors `regime_signals.assert_no_lookahead`).

Price series: daily closes for US100 and GER40 from the engine's audited
`data/ftmo_portfolio/cache/panel_px.parquet`, seeded back to 2007 with
`data/deep_history_utc/{US100,GER40}_M1.csv` resampled to daily close, so the running
maximum has ~6.75 years of burn-in before the book sample starts (2013-10-01). Cross-check
required: corr(panel_px daily, deep_history daily) ≥ 0.999 on the overlap, else stop and
report.

| id | definition (all at T−1) |
|---|---|
| **C1 — ATH drawdown (PRIMARY)** | `dd_t = 1 − C_t / max(C_s, s ≤ t)`, **expanding** running max ("all-time") |
| **C2 — 52-week-high ratio (George & Hwang)** | `ratio_t = C_t / max(C_s, t−251 ≤ s ≤ t)`, i.e. **rolling 252-day** — the literature's exact definition |

C2 doubles as the robustness variant for C1's window and as the literature-faithful form.
Both are reported for both legs.

**Definitional honesty, written before the fact:** "all-time" means **since 2007-01** (the
start of the canonical true-UTC series), not since inception of the index. US100 did not
exceed its 2000 dot-com print until ~2016, so in 2014-2016 C1 will call the market "near
its high" on a within-sample high. C2 is immune to this by construction, and the
sub-period table (§6) isolates it. This is disclosed, not corrected after the fact.

**Buckets, frozen** (C1, in drawdown from the running max):

| bucket | condition |
|---|---|
| **B0 "at the high"** | dd ≤ 1% |
| B1 | 1% < dd ≤ 3% |
| B2 | 3% < dd ≤ 7% |
| B3 "far" | dd > 7% |

Plus a **continuous decile** version of the conditioner (deciles of dd computed on the
in-sample ON-day distribution), reported for monotonicity. For C2 the identical edges are
applied to `1 − ratio`. **No other bucket edge will be tried.**

Headline contrast for every object: **B0 vs (B1∪B2∪B3)**, i.e. "at the high" vs
"everything else". Deciles are a shape diagnostic, not a second headline.

## 5. What is measured — two separate objects

**(a) Raw legs**, per leg, so the result is readable independently of any sizing choice:
- US100: return from the M5 bar at **22:05 CET on day T** to the bar at **15:30 CET on the
  next engine day**; GER40: **17:35 CET day T → 09:00 CET next engine day**. These are the
  engine's own segment boundaries (`SCHED_MIN`), read from the engine's own market via
  `load_market()`, so leg returns and book returns come from one ledger.
- Restricted to ON days (Mon/Tue), LONG side, matching the deployed sleeve.
- **Gross and NET.** Net = gross − full round-trip cost from the audited measured panel
  `outputs/phase0_rt_cost_bps.csv` − the **measured asymmetric FTMO swap** on the nights
  held (`panel_swapL` × triple-day multiplier), which is a first-order cost on this family
  (L36) and is never omitted.
- **The `spread` column of `data/deep_history_utc/` is used NOWHERE** — it is massively
  unpopulated and understates the real FTMO round-trip by ~2.4×.

**(b) The reconstructed MONO book** at deployed leverage, via
`regime_overlay_ftmo_2026-07/build_book.py` imported **read-only** (`run_book`, `CFG_MONO`
with the §3 audit applied in my copy). Constant-risk series, no barriers — barriers are
applied downstream in §7.

Book-level conditioner, frozen: **US100's** (the dominant risk leg, and the leg the prior
study used). `min(dd_US100, dd_GER40)` ("either index at its high") and GER40-alone are
reported as secondary colour, not as headlines.

**Per bucket, reported for every object:** n, mean (bps), **t_HAC Newey-West lag 6**,
median, skew, excess kurtosis, **p1 and p5** (the left tail is what kills against the
barrier), annualised realised vol, and — for the book — P(day < −5%), the daily-barrier
hazard.

### 5.1 The L54 test, stated as the headline of RESULTS.md

L54: a regime conditioner is useful **only if the regime that predicts the VARIANCE
predicts the MEAN in the same direction.** So the mean-vs-variance comparison is reported
explicitly and first:

> **If near-ATH predicts LOW variance and an EQUAL-or-HIGHER mean, the ATH is the BENIGN
> state, there is nothing to cut, and the dossier closes there** — consistent with the §2
> prior. That is a complete and publishable answer, and it is the outcome the prior
> expects.

The only configuration that would justify touching exposure is near-ATH predicting a
**lower mean** (with or without lower variance), surviving §6's controls.

## 6. Mandatory controls — non-negotiable

1. **MATCHED PLACEBO.** The null is "any T−1-measurable indicator with this duty cycle and
   this persistence". Realised as **999 circular rotations** of the B0 indicator, which
   preserve the duty cycle **exactly** and the run-length/autocorrelation structure
   **exactly**, destroying only alignment with returns. The real contrast is reported as a
   **percentile of its own placebo distribution**. A bare t-stat is not evidence here: this
   project has a documented cell at bootstrap p = 0.0000 that was at p = 0.13 under the
   matched placebo.
2. **UNCONDITIONAL BASELINE (L58).** The **mean of the placebo pool must equal the
   unconditional expectation of the trade form.** If |placebo pool mean − unconditional
   mean| exceeds 1 pooled SE, the placebo is biased rather than the signal, and no verdict
   is issued for that object until the interaction is explained. Reported as a table, at
   zero cost.
3. **BLOCK BOOTSTRAP.** Stationary block bootstrap (Politis-Romano) via
   `Portfolio.admission.marginal.stationary_bootstrap_indices`, mean block 10 days, 10,000
   reps, on the paired difference. **iid bootstrap is forbidden** — these returns cluster
   (2 ON days a week, and the conditioner is highly persistent).
4. **TEMPORAL STABILITY.** Reported per sub-period: 2013-10→2016-12 / 2017→2019 /
   2020→2021 / 2022→2026-06, plus the pre/post-2021 split, because it is documented that
   post-2021 this sleeve's edge falls **inside its placebo band**.
5. **Persistence disclosure.** dd is strongly autocorrelated, so effective N ≪ N. The HAC
   t is reported alongside the block-bootstrap CI, and where they disagree the **bootstrap
   is decisive**.

## 7. Decision translation — Phase 2 geometry, as confirmed by the risk-bearer

**Geometry is fixed by the live account, not assumed:** the account is in **PHASE 2** with
**€10,000 equity (fresh P2 account)**. Target **+5% → 10,500**. Static floor **90% of
initial → 9,000**. Daily loss budget **5% → 500**, anchored at **00:00 CET on equity**.

Consequences, frozen:
- **All p(pass) and duration figures in this study are PHASE-2 figures (+5%).** No
  P1→P2 funnel number is quoted as the headline. If the campaign runner simulates the full
  funnel, the **P2 branch is isolated** and it is stated explicitly which target was
  simulated, in every table.
- The **min-open-days backstop is treated explicitly** per §3, precisely because a P2
  account can reach +5% before it has 4 open days.
- Barriers via `Portfolio/admission/barrier.py` with `target_p2 = 0.05`, `daily_stop = 0.05`,
  `static_floor = 0.10` (**static** DD model — settled, not re-opened), `min_days_p2 = 4`,
  no time limit. Paths: stationary block bootstrap, mean block 10, **all variants on the
  same pre-drawn index matrix** so every Δ is paired.
- **Death decomposition mandatory**: p(fail daily) vs p(fail floor) vs p(reached target but
  short of min days), the third being the §3 bug's signature.

**Variants evaluated (both directions pre-declared, so neither is a post-hoc sign choice):**

| id | rule |
|---|---|
| V+ | e = 0.30 when B0 fires (cut *at* the high), else 1.00 |
| V− | e = 0.30 when B0 does *not* fire (cut *away from* the high), else 1.00 |
| **D** | **constant multiplier c, calibrated to the same realised daily volatility** as the variant it is paired against |

**THE CONTROL THAT KILLS, frozen:** any conditional variant must beat its **volatility-matched
constant de-lever D** on Δp(pass). This is the exact condition that rejected the previous
overlay. A variant that does not beat a constant number is a sizing parameter in disguise,
already available for free through `vm`, and is REJECTED.

## 8. Test count and verdict rule — frozen

**Primary tests: 6** = 3 objects (US100 leg, GER40 leg, MONO book) × 2 conditioner
definitions (C1 expanding ATH, C2 52-week-high ratio). Šidák at family α = 0.05 over 6
tests ⇒ per-test α = 0.0085 ⇒ **|t| ≥ 2.63**; the project's own IC-feasibility floor is
2.5, so the binding threshold is **|t_HAC| ≥ 2.63**.

Not counted as new discoveries, reported as fragility diagnostics only: deciles,
sub-periods, GER40/min-dd book conditioners, gross-vs-net, and the two exposure variants
(which are read against the placebo band, itself the multiplicity control for exposure
schedules of a given duty cycle).

**Verdict rule:**

- **PASS** requires ALL of: (a) |t_HAC| ≥ 2.63 on the B0-vs-rest **mean** contrast;
  (b) real contrast **above its matched-placebo p95**; (c) the placebo pool passes the
  unconditional-baseline check of §6.2; (d) the sign is **stable across sub-periods** and
  survives post-2021; (e) the implied exposure variant **beats its vol-matched constant
  de-lever** on Δp(pass) at P2 geometry.
- **UNDERPOWERED** — point estimate in the prior's direction but CI straddles 0, or the
  placebo band is too wide to separate. Reported as UNDERPOWERED, never as PASS.
- **REJECTED** — any of: mean contrast not significant; inside the placebo band; fails the
  de-lever control; sign flips across sub-periods.
- **BENIGN-STATE CLOSE** — near-ATH shows lower/equal variance with equal-or-higher mean.
  L54's condition is unmet in the direction that would justify a cut, the §2 prior is
  confirmed, and the dossier closes with **no exposure change proposed**.

## 9. What stops this study early

- Config audit (§3) shows the reconstruction is unusable → report the config finding as the
  deliverable, no conditioner verdict.
- panel_px vs deep_history cross-check corr < 0.999 → stop, report the data problem.
- Look-ahead assertion fails → stop.
- Placebo pool mean ≠ unconditional expectation (§6.2) → no verdict on that object.

**A cleanly established null is a full-value deliverable here. No PASS will be manufactured.**
