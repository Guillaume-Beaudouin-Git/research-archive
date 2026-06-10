# Independent Adversarial Audit — FTMO 10k 2-Step "Decorrelated 3-Sleeve Portfolio"

**Target:** `PropFirms/ftmo_decorrelated_portfolio/REPORT.md` (3-sleeve portfolio, p(pass)≈0.55 ≤3mo OOS).
**Date:** 2026-06-08 · **Method:** clean-room REGENERATION (no import/call of the author's engine
`engine/ftmo_first_passage.py`, no trust of cached series). READ-ONLY on all source data; all outputs
under `research/ftmo_portfolio_audit/`. Code: `code/*.py`. Machine-readable: `results/*.json|csv`.

---

## 0. Bottom line

**The headline does not survive independent regeneration. VERDICT: NOT-CONFIRMED.**

1. **No reproducible artifact exists.** There is **no committed runner** that builds the 3-sleeve
   RSI2+BTC+US30 portfolio or its p(pass) table. §9's "cached and regenerable end-to-end" is unbacked
   (the engine exists; the portfolio assembly does not). Regeneration was therefore mandatory.
2. **None of the three sleeves reproduces its claimed Sharpe at the stated §4 spec** — two of three
   flip sign. The claimed numbers correspond to *different* configs than documented, selected on the
   favorable 2022-26/OOS window.
3. **Even granting the report's *claimed* combined Sharpe (1.39) and optimal leverage**, my
   first-passage MC gives **p(pass≤3mo) ≈ 0.18–0.29** (correct method) / ≤0.41 (the author's own
   optimistic method). The claimed **0.549 is not reproducible**.
4. **With honest confidence intervals**, the 90% CI for p(pass≤3mo) sits **entirely below 0.50** in
   every scenario. "0.55 clears the bar" reverses to "central estimate ~0.2–0.3, upper-90% < 0.50."
5. The report attaches **no CIs**, its results row **violates monotonicity**, and it rests on an
   **inflated Sharpe × an optimistic per-phase MC × favorable leverage** stacked together.

---

## 1. What the report actually is (provenance)

- Report lives in `PropFirms/ftmo_decorrelated_portfolio/REPORT.md` (only the .md; no code/series).
- It reuses the engine in `PropFirms/ftmo_alpha_program/` and primitives from a 109-strategy library
  (`data/oxfordstrat_109/`, Sleeve A ≈ `strat_s072_rsi2.py`) — but the committed `ftmo_alpha_program`
  book (`book.py`, `phase2_validation.json`) is a **different, FAILED** intraday-MR book (daily Sharpe
  **−0.026**) that **excludes indices** ("kurtosis 25-45, fail the gate"). The decorrelated portfolio's
  Sleeve C (US30 intraday MR) directly contradicts that exclusion.
- **Finding:** the report is a fresh synthesis with no persisted code/series; its reproducibility claim
  is hollow. (This is the "author=auditor, same blind spots / re-run validates nothing" trap the brief
  warned about — there is not even a runner to re-run.)

---

## 2. Per-gate verdicts (each with the number behind it)

| Gate | Verdict | One-line |
|---|---|---|
| **0 — MC reliability / headline** | **NOT-CONFIRMED** | 0.549 unreproducible; honest 90% CI for ≤3mo entirely **< 0.50**; report CI understated ~10-20×; monotonicity not reproducible |
| **1 — Timezone** | **BUG-FOUND (mixed)** | `deep_history_utc`=TRUE UTC (so Sleeve C *is* correctly US-aligned — the worst-case worry refuted); BTC panel=**EET** so Sleeve B "00-21 UTC" is mislabeled; UTC daily index parquets carry 467 weekend sliver-days; §9 "deep-history M5 UTC…BTC" is false |
| **A — Sleeve regeneration** | **NOT-CONFIRMED** | All 3 sleeves mis-specified; stated specs give A −0.5, B −0.54, C +0.09 vs claimed 0.97 / 0.51 / 1.00 |
| **B — Tail/cond. correlation** | **CONFIRMED** | Decorrelation real: |ρ|<0.07, co-breach 0.026≈indep 0.028, worst-day ρ(A,C)=−0.19; kurtosis-averaging intact — but not what fails |
| **C — Leverage** | **WEAKER (fragile)** | p(pass≤3mo) swings 0.015→0.31 over L∈[1.5,4]; at stated L=2.5-3 only 0.15-0.35; optimal L still < 0.45 |
| **D — BTC cost stress** | **CONFIRMED concern** | B is a weak hedge (zeroing it: Sharpe 0.95→0.90); net-negative → 0.36, pure-MR book |
| **E — Exec lag → p(pass)** | **CONFIRMED** | +1 bar kills Sleeve B (0.35→−0.06); combined 0.95→0.73; p(pass) 0.147→0.117 |
| **F — DSR honesty** | **NOT-CONFIRMED** | At regenerated Sharpe 0.95: DSR 0.47 (N=100) / 0.28 (N=500). 0.86 needs the unreproducible 1.39 |
| **G — Regime concentration** | **WEAKER** | Single-regime p(pass) 0.11-0.27; 2022-type year 0.11-0.19 (report's "0.40" optimistic) |

---

## 3. GATE 0 — MC reliability & the headline (the load-bearing result)

**Engine validation (independent of the author).** My single-phase MC matches the logistic closed
form `1/(1+e^{-2·S_d·n})` within +0.005…+0.014 across S_ann∈{0,0.8,1.5,2.5} (`gate0_run.selfcheck`).
The small positive bias is discrete-monitoring overshoot — it makes my p(pass) *slightly optimistic*,
which only strengthens the conclusions below.

**p(pass) — independent vs report (L=2.5; CIs are MC multi-seed):**

| window | horizon | **REPORT** | indep author-method | indep **corrected** (monotone) | corrected 90% CI |
|---|---|--:|--:|--:|--:|
| OOS | ≤3mo | **0.549** | 0.309 | **0.175** | [0.172, 0.178] |
| OOS | ≤6mo | ~0.55 | 0.578 | 0.467 | [0.464, 0.471] |
| OOS | ≤9mo | 0.531 | 0.673 | 0.620 | [0.617, 0.625] |
| full | ≤3mo | 0.485 | 0.345 | 0.202 | [0.198, 0.206] |
| full | ≤6mo | 0.580 | 0.597 | 0.505 | [0.501, 0.510] |
| full | ≤9mo | 0.531 | 0.665 | 0.632 | [0.628, 0.637] |

*(All rows use a series rescaled to the report's own **claimed** combined Sharpe 1.39, so this is the
most charitable test of the headline. `results/ppass_sidebyside.csv`, `figures/ppass_audit.png`.)*

**(a) CIs on every number — and the report's are ~10-20× too tight.** The author's engine returns a
delta-method binomial CI (`combined_pass_prob_empirical`, ±~0.003-0.006). But the bootstrap population
is a *short, serially-dependent* series, so the honest uncertainty comes from re-sampling the data
itself. **Outer block-resample 90% CIs for p(pass≤3mo):**
- reportSharpe OOS L2.5: **[0.084, 0.374]** (sd 0.099)
- reportSharpe full L3.0: **[0.214, 0.377]** (sd 0.053)
- steel-man full L2.5: **[0.092, 0.195]** (sd 0.121)

The honest SD (0.045-0.121) is **10-20× the delta-method SE** the report implies. Every one of these
90% intervals lies **entirely below 0.50**.

**(b) Monotonicity violation resolved.** The report's full row 0.485 → **0.580 → 0.531** is impossible
for a true cumulative first-passage CDF. My **corrected** engine (sequential two-phase, *total*-time
budget) is monotone by construction everywhere (e.g. reportSharpe full: 0.202 → 0.505 → 0.632 → 0.671
→ 0.686 terminal). The violation is **not** reproducible by faithfully replaying the author's
per-phase-product method, and it exceeds the inner MC SD (~0.003) by ~14× — so it is **not MC noise**;
it is consistent only with **inter-cell inconsistency** (different runs/configs/series per horizon) or
an undocumented engine path. Under the honest outer CI (±0.05-0.12) the three cells are statistically
**indistinguishable** regardless.

Note the *pattern*: the report's **6mo** (0.580) ≈ my author-method (0.597), but its **3mo is inflated**
(0.485/0.549 vs 0.31/0.35) and its **9mo deflated** (0.531 vs 0.62-0.67). The published row is not a
coherent CDF.

**(c) Headline verdict.** Even with (i) the claimed Sharpe 1.39, (ii) the author's optimistic
per-phase-product method, and (iii) leverage up to 3.0, the maximum p(pass≤3mo) I obtain is **0.41**
(reportSharpe full L3.0); the **correct** method gives **0.18-0.29**. **0.549 does not survive — it is
not distinguishable from "above 0.50"; it is distinguishable as BELOW 0.50.** Forward expectation for
the *as-described* portfolio is materially worse still (Gate A).

**(d) Bonus inconsistency.** §1 claims p(pass) is "invariant to horizon." It is not: my CDF rises
**0.18 → 0.69** from 3mo → terminal. Time is the binding constraint for this low-Sharpe grind, which is
also why §10's "relax to 5-6 months → 0.60" contradicts §1.

---

## 4. GATE 1 — Timezone (verified empirically, label not trusted)

Decisive price-alignment tests (`gate1_tz_check.py`, `results/gate1_tz.json`):
- **EURUSD panel vs deep:** corr **exactly 1.0 at −3h** shift (0.98 at 0h) → MT5 panel stamp = true UTC+3
  (EEST). **`panels/m5_indices` is EET/EEST mislabeled as `timestamp_utc`.**
- **BTC panel vs binance (true UTC):** corr **0.99998 at −3h** → BTC panel is EET/EEST too.
- **`deep_history_utc` is TRUE UTC:** US30 maintenance dip sits at **21:00 UTC** (the 17:00-ET CFD break);
  consistent with the MANIFEST's gate-2 overlap-corr 0.999999.

**Implications:**
- ✅ **Sleeve C / US30 is genuinely UTC** → "US cash 13-20 UTC" is correctly aligned. The audit's
  worst-case worry (C trading the wrong window) **does not materialize**.
- ⚠ **Sleeve B / BTC** has only an EET source; "liquid window 00-21 UTC" is actually 00-21 **EET**
  (~3h shift; modest for 24/7 BTC, but the daily-reset/intraday-flat boundary is EET not UTC).
- ⚠ §9's "deep-history M5 UTC … for FX/indices/gold/**BTC**" is **false**: the MANIFEST states BTC was
  *skipped*; BTC is the EET MT5 panel, not deep-history, not UTC.
- 🐞 The **UTC daily index parquets carry 467 weekend "sliver" days** for US30 (Sunday-evening CFD opens
  split off by UTC-calendar grouping; EET build has 0). Using the *_UTC daily series naively
  contaminates indices; the EET build (= FTMO's actual broker server day) is correct.

---

## 5. GATE A — Independent sleeve regeneration (causal, real-cost)

Signal at T-1 / execute at T; CFD cost = real MT5 spread × markup (+ FX commission + per-night swap on
Sleeve A; + 6.5 bps RT crypto commission on B). `sleeve_a.py`, `sleeve_a_variants.py`, `sleeve_bc.py`,
`sleeve_bc_sweep.py`.

| Sleeve | report claim | **stated-spec regen** | best charitable config | comment |
|---|---|---|---|---|
| **A** RSI2 daily MR | ann **0.97**, kurt 14, +every yr | **−0.47** (two-sided, 11 instr, EET) ; −0.59 on 2018-26 | **+1.09** only as **long-only classic Connors** (SMA200+RSI2<10+SMA5-exit) on **indices-only** | mis-described; the working version is **long equity-index beta** (S072's own words); "+every year" holds **only on 2022-26** (0.33, neg years on 2018-26) |
| **B** BTC 120m momentum | net OOS **0.51** | **−0.54 full / −0.73 OOS** (stated 120m,z2) | **0.35 full / 0.54 OOS** (60m,z2.5,stop3%) | claimed config gives negative; +0.5 needs different config, is OOS-specific, not +every yr |
| **C** US30 60m MR | IS **0.76** / OOS **1.00**, +every yr | **+0.09 full / 0.02 OOS** (stated 13-20 UTC) | **0.53 / 0.66** (best US-session) | +1.0 OOS only with an **8-21 (London+NY)** window — not "US cash"; never +every year; report §6#7 "13-20 already optimal" is false |

Economic sanity confirms the *engine* is correct, not the report: my RSI2 MR is **positive on US indices
(+0.4…+0.5)** and **negative on FX/gold** — exactly matching the report's own §3 ("Intraday FX MR: all
OOS-negative"). The report nonetheless lists 6 FX pairs + gold inside Sleeve A and claims +0.97
positive-every-year, which is internally inconsistent.

**Steel-man combined** (best reconstructions, equal-weight, each vol-targeted ~1%/day): ann Sharpe
**0.95** (not 1.39), kurt 5.7, sigma_d 0.51%/day; per-year +0.76/+0.63/+0.76/+1.00/+2.54.
(`build_steelman.py`, `results/sleeves_steel_combined.csv`.)

---

## 6. GATES B–G

**B — Tail/conditional correlation (CONFIRMED).** Steel-man: unconditional |ρ|<0.07; **co-breach
P(≥2 sleeves below own 10th pct) = 0.026 ≈ independence 0.028 (×0.9)**; in the **worst-decile portfolio
days correlations go negative** (ρ(A,C)=−0.19, ρ(A,B)=−0.39, ρ(B,C)=−0.47). Only a mild shared
equity-beta surfaces (down-day ρ(A,C)=+0.16, vol-shock +0.13). Combined kurtosis (5.7) is far below the
sleeves' (A* 27, B 7.8, C 5.5) → kurtosis-averaging is real. The decorrelation thesis **holds** — it is
simply not the binding constraint (the low combined Sharpe + the 3-month clock are).

**C — Leverage sensitivity (WEAKER/fragile).** p(pass≤3mo) corrected: L1.5→0.015, L2.5→0.15-0.21,
L3→0.23-0.30, L4→0.31-0.38, L5 plateaus/declines. At the **stated L=2.5-3 it is 0.15-0.35**; the
p(pass)-optimal L is ~4 (not the claimed 2.5-3 for this horizon), and even there the **correct method
stays below 0.45**. The result is a narrow-band, leverage-dependent artifact. (`figures/ppass_audit.png`.)

**D — BTC cost stress (CONFIRMED concern).** B contributes little: zeroing it moves combined Sharpe
only 0.95→0.90; net-negative B → 0.36 and a **pure mean-reversion book** (the regime hedge gone — the
exact Gate-B concentration risk §8.3 flags). (p(pass) numbers here are muddied by fixed-leverage vs
re-vol-targeting; the Sharpe deltas are clean.)

**E — Execution lag → p(pass) (CONFIRMED).** A **+1-bar delay destroys Sleeve B (0.35→−0.06)**,
drops combined Sharpe 0.95→0.73 and p(pass≤3mo) 0.147→0.117. The report propagated lag only to Sharpe
(A2); propagated to p(pass) the degradation is confirmed. Sleeve A (daily open execution) is robust.

**F — DSR honesty (NOT-CONFIRMED).** Bailey-López-de-Prado DSR at my regenerated combined Sharpe (0.95):
**0.47 (N=100), 0.28 (N=500)** — fails deflation. The report's 0.86 is reproduced **only** at the
unreproducible 1.39 Sharpe, and even then falls to **0.71 at the honest N=500**. The true trial count is
≫100 (the program's own search: ≈12 families × 11 FX pairs × multiple bar-frequencies × session windows
× a leverage search).

**G — Regime concentration (WEAKER).** Single-regime-conditioned p(pass≤3mo): 2022→0.11/0.19,
2023→0.13/0.21, 2024→0.15/0.27, 2025→0.16/0.26, 2026→0.27/0.47 (corrected/author). A **2022-type year
gives ~0.11-0.19**, so the report's documented "2022 repeats ≈ 0.40" downside is itself optimistic.

---

## 7. Honest limitations (what could NOT be independently checked, and why)

1. **No author runner / cached combined series exists** → I reconstructed Sleeve A/B/C from §4 prose +
   the referenced primitives. The literal-spec and steel-man versions **bracket** the intent; divergences
   may partly reflect spec ambiguity — but the magnitude (two **sign flips**) far exceeds plausible
   ambiguity, and the steel-man already grants the best-reconstruction sleeves.
2. **Swap cost (Sleeve A)** modeled as a flat per-night drag (no broker swap table); shown across
   0/0.5/1.0 bp/night — it shifts ann Sharpe by ≤0.2 and never changes the sign.
3. **FX commission** assumed 2.5 USD/lot/side; small vs spread.
4. **Gate D p(pass)** is confounded by fixed-leverage vs re-vol-targeting (a dead sleeve lowers vol →
   slower passes); the **Sharpe** deltas are clean and carry the conclusion.
5. **Rolling-63d ρ(A,C)** returned NaN (A* has flat stretches → undefined windowed corr); reported the
   masked-subset conditional correlations instead.
6. **All p(pass) are design-stage MC on bootstrap history, not realised performance** (same caveat the
   report carries). My discretization adds ~+0.01 optimistic bias — i.e. it favors the report.
7. **Live-cost reconciliation** (portal spreads/swaps/crypto commission) remains pending, as in the
   report; not independently checkable here.
8. **BTC true-UTC intraday:** the only spread-bearing source is the EET MT5 panel; I cross-checked
   against true-UTC binance (spread-free) — both give negative/weak Sleeve B.

---

## 8. Recommendation to the team

Treat the portfolio as **not validated**. The three claimed edges do not reproduce at their documented
specs; the headline p(pass) is inflated by stacking an unreproducible Sharpe, an optimistic per-phase MC,
and favorable leverage, and it carries no honest CI (the true 90% band for ≤3mo is **below 0.50**).
Before any further work: (1) commit the actual sleeve+portfolio runner and re-derive each sleeve at its
*documented* spec with CIs; (2) adopt the sequential total-time-budget first-passage engine (monotone)
and report outer-resample CIs; (3) re-state Sleeve A honestly as long equity-index beta and re-test
decorrelation against that; (4) drop the "positive every year" / "13-20 UTC optimal" / "horizon-invariant"
claims that the data contradict.

*Independent regeneration; all numbers from `code/*.py` over read-only source data. Where I could not
verify, I reported it rather than inventing it.*
