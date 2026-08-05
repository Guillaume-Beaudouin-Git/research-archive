# Making the wall decidable — closing the two gaps

**Date** 2026-08-05 · **Branch** `claude/wall-decision` · **Book** deployed MONO (gold w=0,
J1 off, ORB challenge-off ⇒ overnight indices sleeve only), live Swing margin, EA v2.4+
breaker semantics · **Predecessor** `wall_economics_2026-08/RESULTS.md` (2026-08-03).

I was asked to fill two holes in the first pass — the aggregated Pace channel, and the
unaudited `V` — and not to redo its work. Filling the second one forced me to re-open the
first one's measurement stack, and that is where the report goes.

---

## 0. Headline

**Three findings, in order of how much they move the decision.**

1. **The harness both passes ran on carries a defect that sits exactly on the channel the
   first pass priced.** The inherited `CFG_LIVE` omits the min-trading-days backstop. As a
   result **88 % of the "timeouts" at wall 91 (100 % at wall 182) are accounts sitting AT
   OR ABOVE the +10 % target** — median terminal equity **$11,073** against a target of
   $11,000 — frozen by a day-counter deadlock the deployed spec does not have. They are not
   deaths. With the backstop armed (two independent engines agree), single-attempt pass goes
   **25.9 % → 43.3 %**, timeout **19.7 % → 2.3 %**, and floor deaths do not move at all
   (36.81 % in both). §1.
2. **V audited: the cited $2,529 is wrong three times over, and every error is in the same
   direction.** It is a **gross** extraction (the 80 % split is applied elsewhere in the same
   script), from the **OOS half only**, of the **FULL 4-sleeve book**. The deployed MONO
   book's trader share is **$782 pooled** (CI95 [713, 852]), regime range **$347–$1,195**.
   The first pass's point estimate is **above the entire measured range**. §3.
3. **The two errors pointed in opposite directions, and on the corrected numbers the wall
   no longer flips the sign of the enterprise.** Break-even V is **$354 at wall 91** and
   **$278 at wall 182** — not $2,912 / $1,995. Measured V of $782 clears both. The wall is a
   **ranking** question worth **+$0.67/day**, not a survival question. §4.

**And the two gaps themselves:**

* **Gap 1 (asymmetry).** The legs do separate, and **not the way the hypothesis predicted**.
  The costly leg is the **LOW (protective)** one — **−6.25 pt** of p(campaign) at wall 91
  (CI95 [−10.65, −2.08], **significant**, placebo −0.37) — because de-levering a lead slows
  the attempt and fewer retries fit inside the wall. The **HIGH (amplifying)** leg is
  **−1.85 pt [−5.56, +1.39], ns**. On floor risk both legs point the hypothesised way
  (HIGH +0.69 pt, LOW −1.16 pt) but **neither is resolvable**: MDE₈₀ is ±3.1 to ±4.1 pt and
  both effects are smaller than that. **The floor channel is UNDERPOWERED — I am not
  concluding on it.** §2.
* **Gap 2 (the interaction).** The A-without-B hazard the first pass flagged is **small and
  measured**: only **2.8 %** of attempts are still open at calendar day 91 (not 20 % — that
  figure was the deadlock), only **1.9 %** ever reach the 2.0 clip, and the measured cost of
  running horizon 182 with the denominator still at 91 is **0.00 pt** of p(campaign)
  (CI95 [−2.55, +2.78]) and **+0.46 pt** of floor deaths [−1.39, +2.31]. §5.

**Recommendation: take lever A, leave lever B alone.** §6.

---

## 1. The harness defect — and why it is on the critical path

`engine.run_phase` flattens **and latches `flat_today`** the moment equity touches the
target (`engine.py:322-325`), and FTMO requires **≥ 4 trading days**
(`PropFirms/ftmo/rules.md:27`, `MIN_OPEN_DAYS = 4`). An account that reaches +10 % before it
has opened 4 trading days is therefore frozen flat: it cannot open another trade, the
counter never advances, and the attempt is eventually recorded as a **`timeout`**.

The deployed spec closes exactly this hole with the **micro-ORB day counter**
(`config_v22.CFG_CHALLENGE: micro_orb=True, fix_deadlock=True`; CLAUDE.md records the
micro-ORB counter's failure rate as **0.00 %**). The cleanroom's `fix_deadlock` is its
stand-in — a $1 token trade to tick the counter, described in the engine's own comment as
escaping "the flatten-deadlock **artifact**".

`wall_economics_2026-08/code/wall_lib.py:38-43` sets **neither flag**. So does
`regime_overlay_ftmo_2026-07/cohort_funnel.py:26-30` — the same `CFG_LIVE` literal, and the
study the first pass reproduced "exactly" as its non-regression check. The two agreed
because they share the defect.

| arm (432 cohorts, wall 91) | p(pass) | timeout | p(floor) | p(daily) | **timeouts at/above target** | median timeout equity |
|---|---:|---:|---:|---:|---:|---:|
| cleanroom `CFG_LIVE` (first pass) | 25.93 % | 19.68 % | 36.81 % | 11.81 % | **88.2 %** | **$11,073** |
| cleanroom **+ `fix_deadlock`** | **43.29 %** | **2.31 %** | 36.81 % | 11.81 % | 0.0 % | $9,930 |
| v2.2 engine, micro-ORB OFF | 25.93 % | 19.68 % | 36.81 % | 11.81 % | 88.2 % | $11,073 |
| **v2.2 engine, micro-ORB ON (the spec)** | **44.91 %** | **2.31 %** | 36.57 % | 10.42 % | 0.0 % | $9,935 |

At wall 182 the contamination is total: **100 %** of timeouts sit at or above target,
median equity **$11,097**.

Two independent engines, written by different passes of this project, agree to within
**1.6 pt**, and the cleanroom stand-in tracks the real micro-ORB implementation. The floor
and daily channels are **untouched** by the fix — it only releases deadlocked winners.
`code/validate_deadlock.py`, `tables/deadlock_defect.csv`.

> **Consequence for the first pass.** Its §2 claim — *"the 91-day timeout is the
> second-largest killer of attempts (26.6 % of all P1 deaths)"* — is true of the model and
> false of the world. Those attempts had **already earned the target**. Every number in its
> §4, §5, §7 gradient inherits this, and the gradient it measured is largely the wall
> deciding how long a deadlocked winner sits before being written off. **Everything below is
> re-measured on the corrected harness.** The wall's real timeout channel at 91 is 2.31 %,
> and at 182 it is **zero**.

*(Cohort count: 432 here vs 433 quoted by the first pass, same code and same runway filter —
an off-by-one in its prose, immaterial.)*

---

## 2. GAP 1 — the asymmetric decomposition

`Pace = clip(1 + K·(frac_t − max(prog,0)), 0.8, 2.0)`, `K = 1.0` (verified `spec_v22.yaml:43`
and `spec_v22.mqh:39`), `frac_t = elapsed_cal_days / WALL_DAYS`.

Four arms on the **same 432 cohorts**, implemented by recomputing the engine's own two pace
lines and calling `_target_for_segment` with `cfg["pace"]=0` and `vm → vm·p*` — exact
arithmetic, every downstream cap and the quantizer untouched. **Non-regression: `frozen`
with the denominator equal to the wall reproduces `coupled` bit-for-bit** (432/432 identical
flags).

| arm | rule | wall 91 p(camp) | p(1-try) | p(floor\|1try) | p(daily\|1try) |
|---|---|---:|---:|---:|---:|
| `off` | x ≡ 1 | 60.19 % | 42.82 % | 35.88 % | 11.34 % |
| `hi_only` | x := max(x,1) — **amplification only** | 58.33 % | 44.91 % | 36.57 % | 11.11 % |
| `lo_only` | x := min(x,1) — **protection only** | 53.94 % | 41.90 % | 34.72 % | 12.27 % |
| `coupled` | x — **deployed** | 54.40 % | 43.29 % | 36.81 % | 11.81 % |

Each leg gets **two** estimates — its main effect against no pacing, and its interaction
when added on top of the other leg. Reporting one number is what erased the question.

### 2a. Wall 91 — block bootstrap over cohorts, 7-cohort blocks, n_eff **62** independent windows

| metric | leg | estimand | Δ (pt) | CI95 | placebo | edge | **MDE₈₀** | verdict |
|---|---|---|---:|---|---:|---:|---:|---|
| **p(campaign)** | HIGH | main (hi−off) | −1.85 | [−5.56, +1.39] | +1.97 | −3.82 | ±4.96 | ns |
| | HIGH | interaction | +0.46 | [−3.24, +4.63] | +1.72 | −1.25 | ±5.62 | ns |
| | **LOW** | **main (lo−off)** | **−6.25** | **[−10.65, −2.08]** | −0.37 | **−5.88** | ±6.12 | **SIGNIFICANT** |
| | LOW | interaction | −3.94 | [−8.80, +1.16] | −0.62 | −3.32 | ±7.11 | ns |
| | BOTH | aggregate | −5.79 | [−11.34, −0.23] | +1.35 | −7.14 | ±7.94 | SIGNIFICANT |
| **p(1-try)** | HIGH | main | +2.08 | [+0.00, +4.63] | +0.56 | +1.52 | ±3.31 | borderline |
| | LOW | main | −0.93 | [−3.01, +1.39] | −0.27 | −0.66 | ±3.14 | ns |
| | BOTH | aggregate | +0.46 | [−2.31, +3.70] | +0.50 | −0.04 | ±4.30 | ns |
| **p(floor\|1-try)** | HIGH | main | +0.69 | [−2.55, +3.24] | +2.01 | −1.31 | ±4.13 | **ns — underpowered** |
| | HIGH | interaction | +2.08 | [−0.69, +4.86] | +2.95 | −0.87 | ±3.97 | **ns — underpowered** |
| | LOW | main | −1.16 | [−3.70, +0.69] | −0.96 | −0.19 | ±3.14 | **ns — underpowered** |
| | BOTH | aggregate | +0.93 | [−2.78, +4.17] | +1.99 | −1.06 | ±4.96 | ns |

At wall 182 (n_eff 43) the LOW leg is significant on both estimands — main **−7.41 pt**
[−14.81, −1.39], interaction **−6.94 pt** [−13.66, −3.24] — and the HIGH leg is +1.39 pt
[−0.93, +3.47], ns. Full table `tables/pace_legs2.csv`.

### 2b. What the asymmetry actually is

**The hypothesis was that the high leg is the risk and the low leg is the benefit. On
p(campaign) the sign is the other way round, and the mechanism is the clock, not the floor.**

* The **LOW leg** de-levers a lead by up to 20 %. That makes the attempt *slower*
  (median days to funded 45.0 vs 48.0 with pace off is noisy, but attempts rise 2.32 → 2.37),
  and **a slower attempt fits fewer retries inside the wall**. It costs **−6.25 pt** of
  p(campaign) and buys **−1.16 pt** of floor deaths that I cannot resolve from zero.
* The **HIGH leg** buys **+2.08 pt** of single-attempt pass — bigger size resolves an attempt
  sooner in either direction, and the book's daily skew is **+1.13** so that trade is mildly
  favourable — and costs **+0.69 pt** of floor deaths, also unresolvable.
* **Averaging them gave the first pass 0.00 pt.** The decomposition shows that is a real
  cancellation between a **−6.25 pt** speed cost and a **+2.08 pt** speed benefit, not an
  inert feature.

### 2c. Power, stated plainly

| channel | n_eff windows | MDE₈₀ | what I can and cannot say |
|---|---:|---:|---|
| p(campaign), LOW leg, wall 91 | 62 | ±6.1 pt | effect (−6.25) **just clears** its own MDE — resolved, but only just |
| p(campaign), HIGH leg, wall 91 | 62 | ±5.0 pt | **cannot resolve** anything smaller than 5 pt |
| p(1-try), either leg | 62 | ±3.1–3.3 pt | HIGH leg's +2.08 is **below** MDE₈₀ — borderline, do not lean on it |
| **p(floor), either leg, either wall** | 43–62 | **±3.0–4.6 pt** | **UNDERPOWERED. Both point estimates (+0.69, −1.16) are inside the noise floor. I am not concluding on the floor channel in either direction.** |

The first pass reported ~13 independent windows; the correct dependence unit is the campaign
span in cohorts (cohorts are 7 trading days apart, a campaign at wall 91 spans ~7 of them),
giving **62** at wall 91 and **43** at wall 182. Even at 62, a 1-point floor effect is four
times below what this design can see.

### 2d. The live operating point — where the low leg is right now

2026-08-05, attempt opened 2026-07-21, day 15, **equity $10,589.83**:
`prog = 0.5898`, `frac_t = 15/91 = 0.1648`, `x_raw = 0.575` → **clipped to 0.80**,
`scale = 14 × 1.0 × 1.0 × 0.80 = 11.2` (was 16.0 on Monday). Reconstruction matches the brief
exactly. **The account is on the LOW leg, at the clip.**

Forward walk from this state, 40 000 paired block-bootstrap paths, taper/glide/pace live,
governor mirrored from `ftmo_live/lib/invariants.py`, cross-checked **388/400** against
`Portfolio/admission/barrier._run_phase`:

| variant | p(pass) | p(static floor) | p(daily) | median d | pace now |
|---|---:|---:|---:|---:|---:|
| **DEPLOYED — pace ON, denom 91** | **61.98 %** | 0.43 % | 37.56 % | 7 | **0.80** |
| pace OFF | 60.21 % | 0.37 % | 39.30 % | 5 | 1.00 |
| HIGH leg only | 60.36 % | 0.43 % | 39.19 % | 5 | 1.00 |
| LOW leg only | 61.74 % | 0.36 % | 37.73 % | 7 | 0.80 |

| leg | Δp(pass) | Δp(static floor) | Δp(daily) |
|---|---:|---:|---:|
| **LOW leg** (deployed − hi_only) | **+1.61 pt** | −0.00 pt | **−1.63 pt** |
| HIGH leg (deployed − lo_only) | +0.24 pt | +0.07 pt | −0.17 pt |

**From here the Pace channel *is* the low leg**, and it is worth +1.6 pt by converting
daily-barrier deaths into passes. The high leg is inert from this state — at `prog 0.59` it
cannot arm unless the account gives the lead back. Note also that from +5.9 % the binding
barrier is the **daily** one (37.6 %), not the static floor (0.4 %): the first pass's live
walk started from $9,473.89 where the reverse was true. **The binding barrier is a function
of the state, and it has flipped since 2026-08-03.** `tables/live_point2.csv`.

---

## 3. GAP 2 — the audit of V

### 3a. Provenance: where $2,529 comes from

`RECOST_v2.2.1.md:15-16` reports "Funded sous coûts mesurés : OOS **$2,529**". Tracing it to
source (`run_recost_v221.py:78-89` → `engine_v22.run_funded`), `extr = wd + residual` is the
**gross** amount extracted from the account over a **504-trading-day (≈2 y)** horizon with a
payout every 14 trading days. Re-running the same engine, same windows:

| book | window | gross E[extr] | **× 0.80 = trader share** |
|---|---|---:|---:|
| **FULL 4-sleeve (gold + J1 on)** | IS 2013-17 | $684 | $547 |
| | **OOS 2020-24** | **$2,632** | **$2,105** |
| | POOLED | $1,683 | $1,347 |
| **DEPLOYED MONO (gold w=0, J1 off)** | IS 2013-17 | $434 | $347 |
| | OOS 2020-24 | $1,494 | **$1,195** |
| | **POOLED** | **$978** | **$782** |

$684 / $2,632 are the v2.2 baseline anchors verbatim (`run_recost_v221.py:270`); RECOST's
$683 / $2,529 are the same figures after the measured commission drag (−$103 OOS). **The
chain reproduces.** `code/audit_v_provenance.py`, `tables/v_provenance.csv`.

**Three errors, all in the same direction:**

1. **Gross, not trader share.** RECOST applies the split *separately* — `VAL = FEE + 0.8 ×
   extr_pooled` (`run_recost_v221.py:193`) — so $2,529 has not been split. ÷1.25.
2. **OOS half only.** The IS half of the same book is $684. Pooled is $1,683. ÷1.56.
3. **The wrong book.** $2,529 is the FULL 4-sleeve book. The deployed book is MONO. ÷1.72.

The first pass's own econ formula then adds the fee on top (`p·(V+fee)`), which is correct
*if* V is the trader share — it was not. **Net: the value driving the entire first-pass
conclusion was overstated by ≈3.2× against the deployed book.**

This also resolves the $1,467 discrepancy the brief asked about: the memory's "$1,467 net80"
is the **full-book pooled** figure at 0.80, and my re-run gives **$1,347** for the same
quantity — the same number to within the config/step differences between the two studies.
It was never in conflict with $2,529; it is a *different quantity* (pooled·0.8 vs OOS gross).

### 3b. Dispersion — an interval, not a point

Deployed MONO book, live-faithful config (v2.4 breaker + Swing margin), h504, wd14, n=191:

| quantity | value |
|---|---|
| **V (trader share), pooled** | **$782** |
| bootstrap CI95 (sampling) | **[$713, $852]** |
| p10 / median / p90 across cohorts | $70 / $739 / $1,449 |
| **regime range (IS ↔ OOS)** | **$347 ↔ $1,195** |
| funded bust rate (MONO, vm 1.0) | **1.05 %** |
| payouts per funded account | 10.5 |
| horizon sensitivity (h126 / h252 / **h504** / h756) | $244 / $414 / **$782** / $1,169 |
| vm sensitivity (0.70 / 0.85 / **1.00**) | $730 / $754 / **$782** |

**The sampling interval is ±$70. The regime interval is 3.4×.** The repo already knew this
("valeur funded ∝ régime gold, spread 4.5×"); the sampling CI is not the uncertainty that
matters. Two assumptions are load-bearing and should be read as such:

* **V is very nearly linear in the assumed funded lifetime.** The 504-day cap is an arbitrary
  truncation, not a measured lifetime, and the MONO book’s funded bust rate is only 1.05 % —
  so V is essentially "*n* years of funded income" and doubles if you assume 4 years. (This
  is far below the memory's 30–63 % funded bust rates, which are the **full** book at vm 1.0;
  MONO at vm 1.0 barely risks anything, and barely earns anything.)
* **No account scaling** is modelled (FTMO +25 %/4 mo); the memory records that scaling helps
  the upside only.

`code/audit_v.py`, `tables/v_audit.csv`.

---

## 4. The corrected economics, and the mur-optimal-vs-V curve

Renewal-reward, unchanged from the first pass: `rate(W) = [p(W)(V+fee) − attempts(W)·fee] /
E[cycle days]`, `fee = $107` refunded on the first payout.

### 4a. The corrected gradient

| wall | p(campaign) | CI95 vs 91 | p(1-try) | attempts | median d | timeout | **placebo p50** | **edge** |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 65 | 42.59 % | [−17.13, −7.18] | 41.90 % | 2.06 | 35.5 | 8.33 % | 35.88 % | +6.71 |
| **91** | **54.40 %** | — | 43.29 % | 2.34 | 44.0 | **2.31 %** | 47.34 % | +7.06 |
| 130 | 68.29 % | [+8.56, +17.82] | 43.52 % | 2.61 | 54.0 | 0.23 % | 60.88 % | +7.41 |
| **182** | **78.94 %** | [+15.97, +30.32] | 43.98 % | 2.84 | 63.0 | **0.00 %** | 71.99 % | +6.94 |
| 270 | 87.50 % | [+21.76, +41.67] | 43.75 % | 3.16 | 70.0 | 0.00 % | 84.38 % | +3.12 |
| 360 | 97.92 % | [+31.48, +53.47] | 42.82 % | 3.23 | 83.0 | 0.00 % | 93.87 % | +4.05 |

**p(1-try) is flat at ~43–44 % from wall 91 upward.** The entire gradient is retries. And
against the matched-persistence sign placebo at the **same horizon**, the *marginal* gain is
**pure geometry**: real 91→182 = **+24.54 pt**, placebo 91→182 = **+24.65 pt**,
**edge-attributable −0.12 pt**. The book's edge shows up as a **level** (+7 pt over the null
at every wall ≤ 182), never as a slope.

> This is the first pass's §4b lesson, sharpened. It does **not** say lengthening is
> worthless — it says p(pass) is not the metric. EV per unit time charges for both the extra
> fees and the extra days, which is why the decision is taken there.

### 4b. Break-even V, and the sign of the enterprise

| wall | 65 | **91** | 130 | **182** | 270 | 360 |
|---|---:|---:|---:|---:|---:|---:|
| **break-even V** | $412 | **$354** | $302 | **$278** | $280 | $246 |

**Measured V = $782, weak-regime floor $347.** Every wall clears break-even at the pooled
estimate. Only in the **IS/weak-regime** scenario ($347) does the deployed wall sit on the
line (−$0.06/day at 91, +$0.58/day at 182).

$/day by (V, wall):

| V scenario | 65 | 91 | 130 | 182 | 270 | 360 | argmax |
|---|---:|---:|---:|---:|---:|---:|---|
| MONO / IS (weak) — $347 | −0.52 | **−0.06** | +0.38 | +0.58 | +0.53 | +0.86 | 360 |
| **MONO / POOLED — $782** | +2.97 | **+3.47** | +4.01 | **+4.20** | +3.91 | +4.55 | 360 |
| MONO / OOS (strong) — $1,195 | +6.28 | +6.82 | +7.47 | +7.63 | +7.13 | +8.05 | 360 |
| FULL book pooled — $1,347 | +7.50 | +8.05 | +8.74 | +8.90 | +8.32 | +9.34 | 360 |
| first pass's V — $2,529 | +16.98 | +17.64 | +18.62 | +18.74 | +17.53 | +19.37 | 360 |

**The curve of the optimal wall against V is flat.** For every V above ≈$246 the argmax is
the longest horizon tested; below ≈$246 the enterprise is EV-negative at **every** wall.
There is no interior optimum. The first pass found one at 130–182 purely because the deadlock
inflated the timeout channel, which is the only mechanism that can make a longer wall
*costly*; with the backstop armed, timeout is 0.00 % from wall 130 onward and nothing
penalises waiting except time itself.

> This closes the first pass's open disagreement. Its Track 1 said "182", its Track 2 said
> "no wall at all", and it could not reconcile them. **Corrected, Track 1 agrees with Track 2:
> no wall.** The differences among 182 / 270 / 360 ($4.20 / $3.91 / $4.55 per day) are
> non-monotone and inside noise — **"≥182" is the defensible statement, not "182".**

**The first pass's single most decision-relevant sentence — *"the wall choice flips the sign
of the whole enterprise"* — does not survive.** It rested on a break-even band of
[$1,995, $2,912] straddling a V of $2,529. The corrected band is **[$246, $412]**, and the
corrected V is **$782**, well clear of all of it. The wall is worth **$0.67/day**, not the
survival of the project.

---

## 5. The interaction — A without B, priced

The first pass's warning: keep `WALL_DAYS = 91` while the human stops abandoning at 91, and
every attempt surviving the wall while behind runs at **pace pinned to 2.0 = effective
vm 28, permanently**. Measured:

| exposure (first attempt, per cohort, corrected harness) | wall 91 | A-without-B (h 182, denom 91) |
|---|---:|---:|
| duty cycle on the HIGH leg | 59.4 % | 59.4 % |
| duty cycle on the LOW leg | 25.9 % | 25.8 % |
| attempts that ever arm the HIGH leg | 89.1 % | 89.1 % |
| mean pace / mean of per-attempt max pace | 1.043 / 1.229 | 1.045 / 1.229 |
| p95 of per-attempt max pace | 1.788 | 1.808 |
| **attempts that ever reach the 2.0 clip** | **1.39 %** | **1.85 %** |
| **P(attempt still open at calendar day 91)** | **2.78 %** | **2.78 %** |

| config (432 cohorts) | p(campaign) | p(1-try) | p(floor\|1try) | p(daily\|1try) |
|---|---:|---:|---:|---:|
| **A+B** — horizon 182, denominator 182 | 78.94 % | 43.98 % | 37.50 % | 12.73 % |
| **A only** — horizon 182, denominator **91** | 78.94 % | 43.98 % | 37.96 % | 12.04 % |
| pace OFF, horizon 182 | 84.49 % | 43.75 % | 36.81 % | 11.81 % |

**(A+B) − (A only): p(campaign) +0.00 pt [−2.55, +2.78]; p(floor) −0.46 pt [−2.31, +1.39].**

**The hazard is real in mechanism and small in magnitude, and the reason is now measurable:
the 20 % figure was the deadlock.** With the backstop armed, **2.8 %** of attempts are still
open at day 91 — matching the corrected timeout rate of 2.31 % — so the population exposed to
saturation is a fortieth of what the first pass's model implied. Fewer than **2 %** of
attempts ever touch 2.0 at all.

Two caveats I will not paper over. First, this is a **p(pass)** measurement at M5 resolution;
it is structurally blind to intra-M5 liquidation, which is exactly where a 2× multiplier near
a hard floor would show up (`breach_<ACCOUNT_ID>_2026-07-02`: continuous liquidation beat the
discrete M5 breaker, root cause **sizing**; `p2_flash_tail_2026-07`). Second, the floor
channel's MDE₈₀ is ±3 pt (§2c), so a +2 pt saturation cost would be invisible here. **Small
and unresolved is not the same as zero.**

---

## 6. THE DECISION — two-lever matrix

* **Lever A** — abandon-and-rebuy **policy**: stop retiring an attempt at day 91. `WALL_DAYS`
  is not an operational deadline (first-pass §1-2, which I did not re-derive and which
  survives the correction unchanged: `governor.max_cal` reaches only the Pace denominator,
  `run_phase`'s timeout is simulation-only). **No code.**
* **Lever B** — `WALL_DAYS` in the frozen spec, i.e. the Pace **denominator**. **Live code** ⇒
  freeze chain, Saturday window, binary re-pin, VPS auto-pull ordering.

All four cells on the same 432 cohorts, V = $782:

| option | p(campaign) | Δ | CI95 | Δ p(1-try) | Δ p(floor\|1try) | CI95 | attempts | median d to funded | Δ | E[cycle] d | **$/day** | **Δ$/day** | implementation cost | reversible |
|---|---:|---:|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---|
| **rien** (h 91, denom 91) | 54.40 % | — | — | — | — | — | 2.34 | 44.0 | — | 67.1 | $3.47 | — | — | — |
| **A only** (h 182, denom 91) | **78.94 %** | **+24.54** | [+15.74, +30.56] | +0.69 | +1.16 | [+0.00, +2.78] | 2.88 | 63.0 | **+19** | 95.0 | **$4.14** | **+$0.67** | **none — a human decision** | **fully, any day** |
| **B only** (h 91, denom 182) | 55.09 % | +0.69 | [−1.85, +3.47] | −0.46 | −0.46 | [−2.31, +1.39] | 2.34 | 45.5 | +1.5 | 67.0 | $3.57 | +$0.10 | freeze chain + Saturday + re-pin | needs another window |
| **A+B** (h 182, denom 182) | 78.94 % | +24.54 | [+15.97, +30.32] | +0.69 | +0.69 | [−1.39, +2.78] | 2.84 | 63.0 | +19 | 94.8 | **$4.20** | +$0.73 | freeze chain + Saturday + re-pin | partially |

**A carries 92 % of the joint gain at zero cost. B adds $0.05/day on top of A** — a
seventy-fifth of a dollar per day, against a live-code change that costs a Saturday window
and a binary re-pin, in a chain where "merger EST un déploiement" and a mis-ordered deploy
has already cost a trading day.

Lever B in isolation, denominator swept at a fixed horizon of 91:

| denominator | 65 | **91** | 130 | 182 | 270 | 360 |
|---|---:|---:|---:|---:|---:|---:|
| p(campaign) | 58.10 % | **54.40 %** | 55.32 % | 55.09 % | 53.94 % | 53.01 % |
| Δ vs 91 | +3.70 [+0.23, +7.18] | — | +0.93 [−0.69, +2.78] | +0.69 [−1.85, +3.47] | −0.46 [−3.01, +2.55] | −1.39 [−4.17, +1.62] |

The whole denominator range spans 53–58 %, and the only nominally-significant point is
**65 — a *shorter* denominator, i.e. MORE pacing**, which is the opposite of the change under
discussion. One nominal hit in a six-point sweep with no correction is a multiple-comparison
artefact and I am not proposing it. The monotone trend is however consistent and it says:
**if B is ever touched, lengthening it is the wrong direction.**

### Recommendation

**Take lever A. Do not take lever B. Confidence: moderate-high on A, high on "not B".**

* **A: stop abandoning at day 91.** +24.54 pt of p(campaign) [+15.74, +30.56], +$0.67/day at
  the audited V, robust in sign across the whole audited V range including the weak regime.
  It is a change to a human habit and a reporting horizon; nothing in `ftmo_live/` executes
  it; it is reversible on any day. Its cost is **+19 days** to a funded account and **+1.16 pt
  of floor deaths** (CI touching zero) — the days are already priced in the $/day figure, the
  floor cost is inside the noise floor and I flag it rather than dismiss it.
  *Qualified by:* the p(pass) gain is **100 % geometry** against the placebo (§4a). The reason
  I still recommend it is that the EV/time metric charges for exactly that geometry — more
  tickets cost fees and days — and A survives the charge.
* **B: leave `WALL_DAYS = 91` in the spec.** Its measured value is +0.69 pt, ns, and +$0.05/day
  once A is taken. The interaction the first pass feared is **+0.00 pt of p(campaign)** and
  **+0.46 pt of floor deaths, both ns**, because only 2.8 % of attempts reach day 91 and 1.9 %
  ever saturate. The reason the first pass thought otherwise is the deadlock artefact. Nothing
  here justifies a live-code change; and if B is ever revisited, the evidence points to a
  *shorter* denominator, not a longer one.
* **The one thing I would monitor rather than model:** an attempt that runs long *and* behind
  still pins pace at 2.0 = effective vm 28, and none of my metrics can see intra-M5
  liquidation. The cheap mitigation is a **supervisor alert** at `pace ≥ 1.8` — observation,
  not a spec change, and therefore outside the freeze chain.

**The account is currently at +5.9 %, i.e. 59 % of the way to phase 1, and on the LOW leg.**
Nothing in this report argues for touching anything while that attempt is live. Lever A is a
decision about what to do **when it resolves**, not now.

---

## 7. What this does *not* prove

1. **It does not prove the deployed spec is free of the deadlock.** I showed the *cleanroom
   harness* had it and that the *spec* closes it via micro-ORB, and I cross-validated the two.
   I did not audit the live EA's day counter against a live ledger. CLAUDE.md's "micro-ORB =
   compteur fiable, échec 0.00 %" is the evidence I leaned on, and it is second-hand here.
2. **It does not prove pro-cyclical pacing is safe.** Every number is mean-based at M5 or
   daily resolution. The 2.0 saturation is priced near zero by these models *because they
   cannot see intra-M5 liquidation*, which the repo's own breach post-mortem identifies as the
   binding failure mode with **sizing** as the root cause.
3. **The floor channel is UNDERPOWERED and I did not conclude on it.** MDE₈₀ is ±3.0–4.6 pt;
   both leg effects (+0.69, −1.16) are well inside it. "Not significant" here means "this
   design cannot see it", not "it is zero".
4. **The horizon gain is not edge.** A zero-edge book with matched persistence reproduces
   **100 %** of the 91→182 gain (+24.65 vs +24.54). The book's edge is a level, not a slope.
   Any future use of these p(pass) levels as evidence of edge would be an error.
5. **The economics rest on one estimate of V, and V rests on a 504-day assumption.** V is very
   nearly linear in the assumed funded lifetime and the MONO funded bust rate is 1.05 %, so a
   4-year assumption doubles it and a 1-year assumption halves it. The regime range (3.4×)
   dwarfs the sampling CI (±9 %).
6. **The book is the deployed MONO book.** If gold or J1 re-arm, both p(W) *and* V change, and
   they change in the same direction — the FULL-book V is $1,347 pooled. The ranking survives;
   the levels do not.
7. **Scope of the defect is not established beyond two studies.** The identical `CFG_LIVE`
   literal appears in `regime_overlay_ftmo_2026-07/cohort_funnel.py:26-30` and in
   `wall_economics_2026-08/code/wall_lib.py:38-43`. Any pinned p(campaign) derived from either
   is contaminated the same way. **I did not re-audit those studies** — flagging, not fixing.
   Studies built on `config_v22.CFG_CHALLENGE*` (which carries both flags) are unaffected.
8. **No multiple-testing deflation was applied.** This is a pricing exercise on a pre-existing
   parameter, not a search. The recommended action (A) is not a selected maximum — it is
   sign-stable across the entire V range and across every wall ≥ 130 — so the ranking does not
   depend on picking a noisy argmax. If any specific wall value is later *selected* on these
   numbers, it must be deflated.
9. **Everything is read-only with respect to live.** No file under `ftmo_live/`,
   `strategies/`, `Futures/live/`, `Portfolio/`, `.github/` or any `*.mq5` was modified. The
   cleanroom engine, `Portfolio/admission/barrier.py` and
   `Portfolio/risk/trailing_dd_simulator.py` were imported, never edited.

---

### Artefacts

`code/` — `pace_lib.py` (engine wrapper: exact leg decomposition + per-cohort duty-cycle
instrumentation), `validate_deadlock.py` (the defect + the two-engine cross-validation),
`audit_v.py` / `audit_v_provenance.py` (V), `run_grid2.py` (corrected gradient + legs +
placebo), `run_bonly.py` (lever B in isolation), `analyze2.py`, `econ2.py`, `matrix.py`,
`live_point2.py`. `run_pace.py` / `analyze_pace.py` are the same measurements on the
*uncorrected* harness, kept so the two can be diffed. `wall_lib.py` / `track2_placebo.py` are
copies of the first pass's, unmodified.

`tables/` (tracked, text only) — `deadlock_defect.csv`, `v_audit.csv`, `v_provenance.csv`,
`gradient2.csv`, `horizon_channel2.csv`, `pace_legs2.csv`, `pace_levels2.csv`,
`pace_exposure2.csv`, `pace_profile2.csv`, `breakeven_V.csv`, `econ_sensitivity2.csv`,
`wall_optimal_by_V.csv`, `two_lever_matrix.csv`, `matrix_by_V.csv`, `lever_B_sweep.csv`,
`live_point2.csv`, plus the uncorrected-harness counterparts (`pace_legs.csv`,
`pace_exposure.csv`, `pace_profile.csv`).

`outputs/` (regenerable, gitignored) — `grid2_raw.csv`, `bonly_raw.csv`, `*_flags.npy`,
`funded_panel.csv`, `book_mono_daily.csv`, run logs. Rebuild:
`/usr/bin/python3 validate_deadlock.py && /usr/bin/python3 audit_v.py && /usr/bin/python3
audit_v_provenance.py && /usr/bin/python3 run_grid2.py && /usr/bin/python3 run_bonly.py &&
/usr/bin/python3 analyze2.py && /usr/bin/python3 matrix.py && /usr/bin/python3 live_point2.py`
(≈40 min on 8 cores; M5 caches read read-only from the main checkout by absolute path).

Interpreter `/usr/bin/python3` (pandas 2.2.3, numpy 2.0.2) throughout. No data blobs committed.
