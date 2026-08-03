# Pricing the mission wall — `mission_wall_days: 91`

**Date** 2026-08-03 · **Branch** `claude/wall-economics` · **Book** deployed MONO (gold w=0, J1 off,
ORB challenge-off ⇒ overnight indices sleeve only), live Swing margin, EA v2.4+ breaker semantics.

`spec_v22.yaml` carries two neighbouring lines: `time_limit: null` (FTMO imposes **no** deadline)
and `mission_wall_days: 91` (we impose one on ourselves). This report prices the second.

**Headline.** The wall has never been operational in live except through one channel — it is the
**denominator of the `Pace()` sizing multiplier**. The 91-day *timeout* exists only in the
simulator, where it is the **second-largest killer of attempts** (26.6 % of all P1 deaths). Moving
the horizon from 91 to 182 days is worth **+5.09 pt** of p(campaign) (CI95 [+1.62, +9.26], Pace
held fixed) and flips the enterprise from **−$0.32/day to +$0.39/day** at the measured funded value.
The Pace channel is **statistically indistinguishable from zero** everywhere we can measure it
(point estimates 0 to −2.6 pt, every CI straddling zero) — *and that is precisely why the live
2× saturation described in §6 is dangerous: it is un-priced, not proven safe.*

---

## 1. The map of `WALL_DAYS` — operational vs measurement horizon

| # | Consumer | Path | What it actually does | Class |
|---|---|---|---|---|
| 1 | `Pace()` | `ftmo_live/mt5/book_executor.mq5:210-217` | `frac_t = elapsed/WALL_DAYS`; `x = clip(1 + CH_PACE_K·(frac_t − max(prog,0)), 0.8, 2.0)`; multiplies `Scale()` | **OPERATIONAL — the only live use** |
| 2 | `#define WALL_DAYS 91` | `ftmo_live/mt5/spec_v22.mqh:19` | constant; **referenced only by `Pace()`** (verified by grep: single hit at l.213) | operational, via #1 |
| 3 | `spec.wall_days()` | `ftmo_live/lib/spec.py:141-143` | reads `account.mission_wall_days` from the frozen yaml | accessor |
| 4 | `governor.phase_cfg()` | `ftmo_live/lib/governor.py:65` | `cfg["max_cal"] = S.wall_days(sp)` for P1/P2 (`None` for FUNDED, l.57) | **OPERATIONAL — see §2** |
| 5 | `brain.py` | `ftmo_live/brain.py:180` | `governor.preview(...)` → `targets.json` consumed by the EA | operational, via #4 |
| 6 | `supervisor.build_morning` | `ftmo_live/supervisor.py:463,479` | prints `J{n}/{wall}` in the Telegram morning message | **cosmetic** |
| 7 | `engine.run_phase` | `cleanroom/engine.py:245-249` | `if (dates[i]−dates[i0]).days > max_cal: return out="timeout"` — **abandons the attempt** | **SIMULATION ONLY** |
| 8 | `engine.run_funnel` | `cleanroom/engine.py:446-473` | `wall` caps the whole campaign **and** is injected as `max_cal` into both phases | **SIMULATION ONLY** |
| 9 | `engine._target_for_segment` | `cleanroom/engine.py:386-389` | Pace denominator — exact mirror of #1 | both |
| 10 | study forks | `v22/engine_v22.py:82,232`, `j1_suspend_study/j1_engine.py:97,212`, `v23_j1_study/j1_engine.py`, `v222_swing_fit/run_swing_fit.py:80` | same two roles | simulation |
| 11 | `GAP_BDAYS`, `RETRY_BDAYS`, `CH_ABANDON_DAYS` | `spec_v22.mqh:20,21,42` | **not referenced anywhere in `book_executor.mq5`** — process documentation for the human | dead constants |

### 2. What `max_cal` triggers — established, not assumed

`governor.py:65` sets `cfg["max_cal"]`, and that cfg reaches exactly one engine function:
`phase_cfg()` → `preview()` → `_call()` → **`E._target_for_segment`** (`governor.py:86`). The
governor **never calls `run_phase` or `run_funnel`**. `_target_for_segment` reads `max_cal` at one
site only — `engine.py:386-389`, the `frac_t` numerator/denominator.

> **In the live Python chain, `max_cal` is a SIZING DENOMINATOR and nothing else.** It does not
> abandon, does not stop counting, does not bound anything. The abandonment semantics of `max_cal`
> exist **only** inside `run_phase`, which live code never invokes.

This is corroborated in-repo: `config_v22.py:51-53` — *« l'EA n'ABANDONNE pas tout seul (ab_days =
alerte Telegram, décision humaine) »*. The equity-based abandon (`ab_days=5` consecutive EOD below
floor+2 %) is a **supervisor alert** (`supervisor.py:333-335`), not an automatic action.

**Consequence.** The simulator applies a terminal clock the live account does not have, so every
p(pass) this project has quoted "at 91 days" is **biased downward** relative to the deployed rule.
In the funnel a `timeout` is also *harsher than a death*: bust and abandon retry after 2 business
days, **a timeout ends the campaign** (`engine.py:466-474`).

---

## 3. Method

* **Track 1 (primary).** Canonical cleanroom 2-step retry funnel on **real historical paths**, M5
  resolution, cohort starts every 7 trading days. Engine **imported, never modified**; the wall is
  decoupled from the Pace denominator by wrapping `_target_for_segment` and overriding only the cfg
  *it* sees, leaving `run_phase`'s timeout untouched (`code/wall_lib.py`).
  *Non-regression:* with the published cohort filter the harness reproduces the previous study
  **exactly** — p(campaign) 7.05 %, p(1-try) 25.99 %, median 53.5 d, N=454
  (`regime_overlay_ftmo_2026-07/RESULTS.md` §6). The sweep below uses a **fixed cohort set with 275
  trading days of runway** (N=433) so every wall is scored on the *same* starts.
* **Track 2.** Stationary block bootstrap (Politis-Romano, mean block 10 d, 20 000 paths) of the
  deployed book's daily returns, with `Portfolio/admission/barrier._run_phase` **imported unchanged**
  and driven by a thin campaign-wall loop (barrier.py only knows per-phase horizons).
* **Track 3.** Forward walk from the **live state** (§6). Reduced-form governor mirroring
  `ftmo_live/lib/invariants.py`; cross-checked **388/400 identical** against
  `barrier._run_phase` in the only regime both cover (par start, governor off) — the 12 differences
  are the taper, which my walker models and `_run_phase` does not.
* **Placebos.** Every gradient point is read against a null at the **same horizon**. Track 1: ±1
  sign schedule on the newly-posted overnight leg, persistent in **10-trading-day blocks**
  (zero expected edge, identical path geometry, identical trade frequency, matched persistence), 12
  draws, *same draw id ⇒ same signs at every wall*. Track 2: the return series **demeaned** (mean
  exactly zero), paired draws.
* Barriers throughout: daily **−5 %** on intraday **equity** off the day's opening balance; **static**
  floor −10 % of initial. No ratchet (1-step, excluded).
* Interpreter `/usr/bin/python3` (pandas 2.2.3). Caches read read-only from the main checkout.

---

## 4. The gradient (Track 1, deployed semantics: wall drives horizon **and** Pace)

N = 433 cohorts, 2013-10 → 2026-06. CI95 = block bootstrap over cohorts, block length = the number
of cohorts one wall spans (cohorts 7 td apart, so two cohorts closer than a wall share most of
their path).

| wall (cal. d) | p(campaign) | CI95 | p(1-try) | median d | p90 d | attempts | bust daily | bust floor | **timeout** | abandon |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 65 | 5.56 % | [2.08, 9.72] | 24.07 % | 51.0 | 63.0 | 1.87 | 10.4 % | 34.3 % | **26.2 %** | 5.1 % |
| **91** | **7.41 %** | [2.78, 12.73] | 25.93 % | 53.5 | 82.1 | 2.09 | 11.8 % | 36.8 % | **19.7 %** | 5.8 % |
| 130 | 10.65 % | [5.32, 16.67] | 26.16 % | 62.5 | 107.0 | 2.28 | 13.2 % | 37.3 % | 17.6 % | 5.8 % |
| 182 | 12.50 % | [6.25, 18.98] | 26.62 % | 79.5 | 151.7 | 2.46 | 12.7 % | 37.5 % | 17.4 % | 5.8 % |
| 270 | 12.04 % | [5.32, 19.68] | 26.62 % | 89.5 | 188.0 | 2.66 | 13.0 % | 37.3 % | 17.1 % | 6.0 % |
| 360 | 12.96 % | [5.56, 20.83] | 25.69 % | 91.0 | 195.5 | 2.63 | 12.3 % | 38.4 % | 17.1 % | 6.5 % |

Death channels are shares of **all cohorts** (the balance is p(1-try)). At the deployed wall, deaths
split **floor 49.7 % / timeout 26.6 % / daily 15.9 % / abandon 7.8 %**.

> **This book is floor-dominated, not daily-dominated.** The brief's "80.2 % of deaths are daily
> barrier" does not hold here, and the reason is mechanical: the M5 engine has a **breaker** that
> flattens intraday at `equity < limit + 30 % × daily budget` (`engine.py:303-330`), converting
> would-be daily busts into slow bleeds to the static floor. A daily-resolution model has no breaker
> and therefore mis-attributes the same deaths to the daily barrier — Track 2 below shows exactly
> that inversion (79-96 % daily). The live account confirms the M5 reading: `daily_floor 8973.89` is
> **below** `static_floor 9000.00`, so the static floor is what binds.

### 4b. Placebo at the same horizon — most of the gradient is geometry

| wall | real | placebo p50 | placebo max | edge | rank of real |
|---:|---:|---:|---:|---:|---:|
| 65 | 5.56 % | 2.08 % | 3.47 % | +3.47 pt | 1.00 |
| 91 | 7.41 % | 4.63 % | 6.71 % | +2.78 pt | 1.00 |
| 130 | 10.65 % | 6.37 % | 10.65 % | +4.28 pt | 0.92 |
| 182 | 12.50 % | 8.10 % | 12.73 % | +4.40 pt | 0.92 |
| 270 | 12.04 % | 8.68 % | 16.44 % | +3.36 pt | **0.67** |
| 360 | 12.96 % | 8.56 % | 17.59 % | +4.40 pt | **0.75** |

Gain over the 91 baseline, decomposed against the null:

| wall | real gain | placebo gain | **edge-attributable** |
|---:|---:|---:|---:|
| 130 | +3.24 pt | +1.74 pt | **+1.50 pt** |
| 182 | +5.09 pt | +3.47 pt | **+1.62 pt** |
| 270 | +4.63 pt | +4.05 pt | **+0.58 pt** |
| 360 | +5.56 pt | +3.94 pt | **+1.62 pt** |

**A zero-edge book gains 3.9 of the 5.6 points.** Track 2 makes the same point far more starkly on
20 000 bootstrap paths, where a **strictly demeaned** series reaches **92.9 %** p(pass) at a 360-day
wall:

| wall | real p(pass) | placebo (mean ≡ 0) | median d real | median d placebo | attempts real | attempts placebo |
|---:|---:|---:|---:|---:|---:|---:|
| 65 | 37.6 % | 32.4 % | 40.6 | 37.7 | 2.96 | 3.18 |
| 91 | 52.0 % | 44.5 % | 49.2 | 47.8 | 3.51 | 3.86 |
| 130 | 67.8 % | 58.9 % | 60.8 | 59.4 | 4.11 | 4.68 |
| 182 | 80.9 % | 72.3 % | 71.0 | 73.9 | 4.63 | 5.45 |
| 270 | 92.0 % | 85.6 % | 79.7 | 88.4 | 5.05 | 6.21 |
| 360 | 96.7 % | 92.9 % | 84.0 | 97.0 | 5.24 | 6.62 |

Real Δ(91→182) = +28.9 pt; placebo Δ = +27.9 pt. **~97 % of the horizon gain is geometry.**

> **Read this correctly.** The placebo does *not* say the book has no edge, and it does *not* say
> lengthening is worthless. It says **p(pass) is not evidence of edge**, because a longer horizon
> buys more lottery tickets against a floor that resets on every fresh account. The edge is what
> makes a *funded* account worth anything, and that is measured separately (§7, V = $2,529). This is
> why the decision must be taken on **EV per unit time**, which charges for the tickets and the days.

---

## 5. The decomposition — horizon vs Pace

Three pace modes at every wall. `coupled` = today's code (`max_cal = W` everywhere). `frozen` =
timeout at `W` but the Pace denominator pinned at 91 ⇒ **pure horizon channel**. `off` = Pace
multiplier ≡ 1.

| wall | Pace off | Pace frozen@91 | coupled (deployed) | **horizon** | **Pace** | total | Pace *feature* (frozen−off) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 65 | 4.63 % | 5.32 % | 5.56 % | −2.08 pt | +0.23 pt | −1.85 pt | +0.69 pt |
| 91 | 7.41 % | 7.41 % | 7.41 % | 0 | 0 | 0 | **0.00 pt** |
| 130 | 10.88 % | 10.42 % | 10.65 % | +3.01 pt | +0.23 pt | +3.24 pt | −0.46 pt |
| 182 | 14.35 % | 12.50 % | 12.50 % | +5.09 pt | 0.00 pt | +5.09 pt | −1.85 pt |
| 270 | 15.51 % | 14.58 % | 12.04 % | +7.18 pt | −2.55 pt | +4.63 pt | −0.93 pt |
| 360 | 16.20 % | 14.81 % | 12.96 % | +7.41 pt | −1.85 pt | +5.56 pt | −1.39 pt |

Paired block-bootstrap CIs (same cohorts, same blocks):

| contrast | Δ | CI95 | verdict |
|---|---:|---|---|
| **Horizon** 91→182, Pace frozen | **+5.09 pt** | [+1.62, +9.26] | **SIGNIFICANT** |
| **Horizon** 91→360, Pace frozen | **+7.41 pt** | [+2.08, +14.81] | **SIGNIFICANT** |
| **Horizon** 91→360, Pace fully off | **+8.80 pt** | [+2.31, +17.13] | **SIGNIFICANT** |
| Total 91→182, deployed coupling | +5.09 pt | [−0.23, +10.19] | ns |
| Total 91→360, deployed coupling | +5.56 pt | [+1.16, +10.65] | SIGNIFICANT |
| **Pace channel** @270 (coupled−frozen) | −2.55 pt | [−9.72, +3.94] | **ns** |
| **Pace channel** @360 (coupled−frozen) | −1.85 pt | [−8.33, +3.70] | **ns** |
| Pace *feature* @91 (frozen−off) | +0.00 pt | [−3.24, +3.24] | ns |
| Pace *feature* @182 (frozen−off) | −1.85 pt | [−8.33, +4.40] | ns |
| Pace *feature* @360 (frozen−off) | −1.39 pt | [−8.34, +5.32] | ns |

**The two channels separate cleanly, and the answer is not the one the code's shape suggests.**
All of the measurable gain is the **horizon**. The **Pace channel is zero within noise** at every
wall; its point estimate turns negative only when the denominator is allowed to follow a long wall
(−1.9 to −2.6 pt at 270/360), i.e. **if you lengthen the wall you should not let Pace follow, or you
hand back a third of the gain.**

Pace denominator swept at a **fixed** horizon of 91 (isolates the feature):

| denominator | 65 | 91 | 130 | 182 | 270 | 360 | OFF |
|---|---:|---:|---:|---:|---:|---:|---:|
| p(campaign) | 8.56 % | 7.41 % | 8.33 % | 6.94 % | 6.02 % | 6.48 % | 7.41 % |
| p(1-try) | 26.39 % | 25.93 % | 25.69 % | 25.46 % | 25.46 % | 24.77 % | **22.45 %** |
| median days | 57.0 | 53.5 | 54.0 | 53.5 | 51.5 | 59.0 | **62.0** |
| timeout | 20.6 % | 19.7 % | 20.1 % | 20.8 % | 20.8 % | 20.6 % | **23.4 %** |

On p(campaign) the whole denominator range spans 6.0-8.6 %, comfortably inside a ±5 pt CI — **not
resolvable**. On p(1-try) there *is* a coherent monotone signal: more pacing → higher single-attempt
pass (26.4 % at denominator 65 down to 22.5 % with Pace off) and a **faster** challenge (median 53.5
vs 62.0 days). Mechanically, larger size resolves an attempt sooner in *either* direction; because
the book's daily skew is **+1.13**, that trade is mildly favourable on a mean-based metric.

> **Stated plainly, against the prior that motivated this study: I could not measure a p(pass) cost
> for pro-cyclical pacing.** On the M5 cohort sweep it is 0.00 pt at the deployed wall
> (CI [−3.24, +3.24]); at the live operating point (§6) it is mildly *positive*. The case for
> changing it does not rest on these numbers — it rests on §6.

---

## 6. The live operating point — where Pace actually bites

`state.json`, 2026-08-03, day 13 of an attempt opened 2026-07-21:

```
equity 9473.89 | static_floor 9000.00 | daily_floor 8973.89 | target_equity 11002.20
vm 14 | taper 1.0 | glide 1.0 | governor.pace 1.1429 | scale 16.0
```

Reconstruction confirmed against the frozen spec: `frac_t = 13/91 = 0.1429`,
`prog = (0.947389−1)/0.10 = −0.526 → max(prog,0) = 0`, so `pace = 1 + CH_PACE_K × 0.1429 = 1.1429`.
**`CH_PACE_K = 1.0` verified in both `spec_v22.yaml:43` (`pace_k: 1.0`) and
`spec_v22.mqh:39` (`#define CH_PACE_K 1`); `PACE_MAX = 2.0` (`invariants.py:22`).**
Room to the binding barrier is **$473.89 = 4.74 %** of initial, and the binding barrier is the
**static** floor (daily_floor sits $26 below it).

Forward walk from this exact state, 40 000 paired block-bootstrap paths, taper/glide/pace all live:

| variant | p(pass) | p(**static floor**) | p(daily) | p(death) | floor share of deaths | median d | pace now |
|---|---:|---:|---:|---:|---:|---:|---:|
| **pace ON, wall 91 (DEPLOYED)** | 31.96 % | 15.12 % | 52.89 % | 68.01 % | 22.2 % | 13 | **1.1429** |
| pace OFF (decoupled) | 30.03 % | 16.74 % | 52.98 % | 69.73 % | 24.0 % | 14 | 1.0000 |
| pace ON, denominator 182 | 31.09 % | 15.46 % | 53.32 % | 68.78 % | 22.5 % | 14 | 1.0714 |
| pace ON, denominator 360 | 30.70 % | 16.13 % | 52.90 % | 69.03 % | 23.4 % | 14 | 1.0361 |
| pace ON wall 91 / horizon 400 | 31.97 % | 15.12 % | 52.90 % | 68.03 % | 22.2 % | 13 | 1.1429 |
| pace OFF / horizon 400 | 30.14 % | 16.78 % | 53.08 % | 69.86 % | 24.0 % | 14 | 1.0000 |

**Pace channel at the live point (ON − OFF):** Δp(pass) **+1.93 pt**, Δp(static floor) **−1.62 pt**,
Δp(daily) −0.09 pt.

So on this metric the pro-cyclical multiplier is **mildly protective of the floor**, not corrosive:
bigger size resolves the attempt faster, and the slow bleeds that would have ground into the static
floor are converted into either a pass or a daily stop. I report this because it is what the
measurement says, and it contradicts the hypothesis I was asked to test.

### The hazard the metric cannot see

Two things sit outside every model above.

1. **Saturation.** `pace = clip(1 + (frac_t − max(prog,0)), 0.8, 2.0)`. An attempt that is *behind*
   and passes day 91 has `frac_t ≥ 1` ⇒ **pace pinned at 2.0, permanently**. The account then runs at
   an effective `vm 28` for the rest of its life. Today's trajectory: **1.14 at day 13 → ~1.50 at day
   45 → 2.00 at day 91 and flat thereafter.** This is a real, dated consequence of a deadline FTMO
   does not impose, and it is not a corner case — it is what happens to *every* attempt that survives
   the wall while behind.
2. **The tail.** Both Track 1 (M5 grid) and Track 3 (daily) are mean-based and neither resolves
   intra-M5 liquidation. The repo's own record is explicit that this is where the model is weakest:
   `breach_<ACCOUNT_ID>_2026-07-02` (continuous liquidation beat the discrete M5 breaker; root cause
   **sizing**), `p2_flash_tail_2026-07` (flash costs −3.9 pt single / −1.7 pt campaign, and USDJPY
   accounts for 50 % of flash busts). A +14.3 %-and-rising size multiplier applied $474 from a hard
   floor is a **tail** decision; p(pass) is structurally blind to it.

**Therefore: my p(pass) measurements do not condemn pacing, and they do not exonerate it either.
They are silent on the one dimension where a 2× multiplier near a static floor matters.**

---

## 7. The economic model

Renewal-reward. A *cycle* is one campaign under a wall of `W` calendar days: with probability `p(W)`
it ends funded at `T_f`, otherwise it is abandoned at day `W` and a fresh challenge is bought.

```
rate(W) = [ p(W)·(V + fee) − attempts(W)·fee ] / E[cycle days]
E[cycle days] = p(W)·E[T_f | funded] + (1 − p(W))·W
```

**Assumptions, made explicit:**

* `fee = $107` (FTMO $10k Swing ≈ €99). **Refunded on the first payout** —
  `spec_v22.yaml funded.withdrawals.fee_refund: "1er payout"` — hence `V + fee` in the numerator.
* `V` = value of a delivered funded account, trader share. **Baseline $2,529** = funded OOS over 2
  years under measured costs (`RECOST_v2.2.1.md`, the current canonical figure; the older $2,632 is
  the pre-commission v2.2 number). Scenario range $1,262 (ORB-off branch) → $4,728 (the $197/mo ×
  24 mo memory anchor).
* `p(W)`, `attempts(W)`, `E[T_f]` from Track 1 (real historical paths).

| wall | p(campaign) | attempts | E[cycle days] | EV/cycle | **$/day** | $/month | E[days to funded] | E[fees to funded] |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 65 | 5.56 % | 1.87 | 64.0 | −$53.9 | **−$0.84** | −$25.6 | 1153 | $3,607 |
| **91** | 7.41 % | 2.09 | 88.3 | −$28.4 | **−$0.32** | −$9.80 | 1191 | $3,019 |
| 130 | 10.65 % | 2.28 | 123.3 | +$36.5 | **+$0.30** | +$9.00 | **1158** | $2,294 |
| **182** | 12.50 % | 2.46 | 170.6 | +$66.7 | **+$0.39** | **+$11.90** | 1365 | **$2,102** |
| 270 | 12.04 % | 2.66 | 249.7 | +$32.5 | +$0.13 | +$3.96 | 2074 | $2,366 |
| 360 | 12.96 % | 2.63 | 326.8 | +$60.6 | +$0.19 | +$5.64 | 2521 | $2,169 |

### Sensitivity — where the optimal wall moves, and where the *sign* moves

$/day by (wall, V):

| V \ wall | 65 | 91 | 130 | 182 | 270 | 360 | argmax |
|---:|---:|---:|---:|---:|---:|---:|---|
| $1,000 | −2.17 | −1.61 | −1.03 | −0.73 | −0.61 | −0.42 | 360 *(all negative)* |
| $1,262 | −1.94 | −1.39 | −0.80 | −0.54 | −0.48 | −0.32 | 360 *(all negative)* |
| $1,381 | −1.84 | −1.29 | −0.70 | −0.45 | −0.42 | −0.27 | 360 *(all negative)* |
| $1,800 | −1.48 | −0.93 | −0.33 | −0.14 | −0.22 | −0.10 | 360 *(all negative)* |
| $2,000 | −1.30 | −0.77 | −0.16 | **+0.00** | −0.13 | −0.02 | 182 |
| $2,200 | −1.13 | −0.60 | +0.01 | **+0.15** | −0.03 | +0.06 | 182 |
| **$2,529** | −0.84 | **−0.32** | +0.30 | **+0.39** | +0.13 | +0.19 | **182** |
| $2,632 | −0.75 | −0.24 | +0.39 | **+0.47** | +0.18 | +0.23 | 182 |
| $2,897 | −0.52 | −0.01 | +0.61 | **+0.66** | +0.31 | +0.33 | 182 |
| $3,500 | +0.00 | +0.49 | **+1.14** | +1.10 | +0.60 | +0.57 | 130 |
| $4,728 | +1.07 | +1.52 | **+2.20** | +2.00 | +1.19 | +1.06 | 130 |

* **The optimal wall is stable at 130-182 across every scenario in which the enterprise is
  EV-positive at all.** It is never 91, and never 65.
* **The sign is far less stable than the optimum, exactly as anticipated.** Break-even funded value
  at the best wall is **V = $1,995**; at the **deployed** wall of 91 it is **V = $2,912**. The
  measured value is **$2,529** — *between the two*. So under the repo's own canonical number, the
  wall choice **flips the sign of the whole enterprise**: EV-negative at 91, EV-positive at 182.
* This is the single most decision-relevant sentence in the report, and it is also the most fragile:
  it rests on a funded-value estimate that spans $1,262-$4,728 in this repo's own ledger.

Track 2 (bootstrap, no abandon rule, no terminal timeout) makes `$/day` **monotonically increasing**
to 360 in every scenario — its optimum is "no wall at all". The interior optimum in Track 1 comes
from the engine's equity-based abandon rule and the terminality of a timeout. **The two models
disagree about where the optimum is; they agree without exception that 91 is too short.**

---

## 8. Recommendation

Two candidate actions, and they are not alternatives — **the second is a prerequisite for the first.**

### (1) Lengthen the horizon 91 → 182. **Recommended. Confidence: moderate-high.**

This is **not a code change**. The wall is not operational as a deadline: the EA has no timeout, and
`governor.max_cal` is only a sizing denominator (§2). "Lengthening the wall" means changing **the
human's abandon-and-rebuy policy** and the reporting horizon — nothing in `ftmo_live/` executes it.
Worth **+5.09 pt** of p(campaign) (CI95 [+1.62, +9.26]) and moves $/day from −$0.32 to +$0.39 at
V=$2,529. Zero execution risk, reversible, no spec-freeze chain involved.

*Confidence qualified by:* ~70 % of the gain is reproducible with a zero-edge book (§4b), so the
gain is real but it is mostly "more attempts", not "better attempts". The EV/time metric already
charges for that, which is why I trust the ranking more than the level.

### (2) Decouple `Pace` from `WALL_DAYS`. **Recommended, but *conditional* and on a different basis. Confidence: low on the p(pass) evidence, high on the structural argument.**

**Be clear about what I did *not* find:** at the deployed wall the pacing feature is worth
**0.00 pt** (CI [−3.24, +3.24]) and at the live operating point it is **+1.93 pt and −1.62 pt of
floor deaths**. *There is no measured p(pass) case for touching it.*

The case is structural and it only becomes binding **if (1) is adopted**:

* Keeping `WALL_DAYS = 91` while the human stops abandoning at 91 means every attempt that survives
  the wall while behind runs at **pace pinned to 2.0 — effective vm 28 — indefinitely** (§6). That
  is an un-modelled tail exposure created by a deadline that does not exist, and the repo's own
  incident record says the model underestimates exactly this tail.
* If the denominator is instead allowed to *follow* a longer wall, the measured Pace channel is
  −1.9 to −2.6 pt (ns, but consistently signed) — you hand back roughly a third of (1)'s gain.

So: **if the horizon policy changes, `WALL_DAYS` must be decoupled from it** — either by pinning the
Pace denominator at its calibrated 91 independently of the mission horizon, or by capping
`PACE_MAX` well below 2.0. Choosing between those two is a sizing decision I have not priced.

**If only one action is taken, take (1)** — it is larger, significant, and requires no code. Do not
take (1) without (2).

Anything touching `spec_v22.mqh` / the yaml goes through the freeze chain and the **Saturday**
window, and is a human decision. **No live path was modified by this work.**

---

## 9. What this does *not* prove

1. **It does not prove pro-cyclical pacing is safe.** Every metric here is mean-based at M5 or daily
   resolution. The 2× saturation is priced at *zero* by these models precisely because they cannot
   see intra-M5 liquidation. Reading §6's +1.93 pt as a green light would be the exact error the
   `breach_<ACCOUNT_ID>_2026-07-02` post-mortem warns against.
2. **It does not prove the horizon gain is edge.** §4b shows a zero-edge book captures ~70 % (Track 1)
   to ~97 % (Track 2) of it. p(pass) rising with horizon is mostly the geometry of buying more
   tickets against a floor that resets.
3. **The wall optimum is model-dependent.** Track 1 says 182; Track 2 says "no wall". Only the
   *rejection of 91* is common to both.
4. **The CIs are wide and the sample is one history.** N=433 cohorts overlap heavily; the effective
   independent sample is ~13 non-overlapping 91-day windows over 12.7 years. Every p(campaign) here
   carries a ±5 pt CI. The Pace channel is *unresolved*, not *shown to be zero*.
5. **The economics rest on a single estimate of V.** $2,529 is one ledger entry; the repo's own range
   is $1,262-$4,728, and the sign of the enterprise flips inside it.
6. **The book is the deployed MONO book.** If gold or J1 re-arm, every number changes — the whole
   gradient was computed on a single-sleeve book that is flat ~40 % of days.
7. **Track 3's live-state result is conditional on one state.** It answers "from *here*", not "on
   average", and it inherits the daily-resolution limitation (its own death mix is daily-dominated
   where the M5 engine says floor-dominated — see the breaker note in §4).
8. **No multiple-testing deflation was applied.** This is a *pricing* exercise on a pre-existing
   parameter, not a search for a new edge; no strategy was selected on these numbers. If any of this
   is later used to select a configuration, it must be deflated.

---

### Artefacts

`code/` — `wall_lib.py` (engine wrapper, wall/Pace decoupling), `run_grid.py` (Track 1),
`track2_placebo.py` (Track 2), `live_point.py` (Track 3), `econ.py`, `analyze.py`.

`tables/` (tracked) — `gradient.csv`, `decomposition.csv`, `pace_denominator_at_wall91.csv`,
`track2_bootstrap.csv`, `live_point.csv`, `econ_baseline.csv`, `econ_sensitivity.csv`,
`econ_wall_by_V.csv`.

`outputs/` (regenerable, gitignored by the repo-root rule) — `grid_raw.csv`, `funded_flags.npy`,
`book_mono_daily.csv`, run logs. Rebuild with
`/usr/bin/python3 run_grid.py && /usr/bin/python3 track2_placebo.py && /usr/bin/python3 live_point.py && /usr/bin/python3 analyze.py`
(≈25 min on 8 cores; the M5 caches are read read-only from the main checkout by absolute path).

No data blobs are committed, per the data-governance rule.
