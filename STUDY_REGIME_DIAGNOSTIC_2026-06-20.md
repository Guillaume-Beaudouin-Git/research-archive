# STUDY — Do the FTMO book's losses concentrate in identifiable macro regimes?

**A diagnostic that decides whether a macro-overlay study is worth running. It is not a strategy.**

Date: 2026-06-20 · Branch `claude/regime-diagnostic` · Worktree `Algo_claude_regime_diag`
Pre-registration frozen & committed BEFORE any result: `regime_diag/PRE_REGISTRATION.md` (commit `ccfd9ad`).
Engine: clean-room `engine.py` imported read-only from main dir (same audited engine as the
asia / soybean / funded-sizing / overnight-basket / vm-sweep studies). **Live book / EA / FLAT
untouched. No deployment. 0 strategy trials minted** (a diagnostic/decision, like session_H).

---

## VERDICT (both books): **DISPERSED — a macro overlay has no robust target. Do not spend trials on it.**

| | Challenge (busts) | Funded (drawdowns) |
|---|---|---|
| **Primary axes surviving Holm @0.05 (T-1 causal)** | **0 / 3** | **0 / 3** |
| Vol (VIX) | lift 1.05, p 0.58 — none | down-legs lift 1.37, p 0.25 — none |
| Dollar (USD-up 3m mom) | lift 1.20, p 0.020 → **Holm 0.118** (fails) | lift 1.42, p 0.25 — none |
| Announce (FOMC ±1) | lift 1.01, p 0.62 — none | lift 1.01, p 0.85 — none |
| Day-of-week (Q3) | tail × DoW p 0.59 — none | same series — none |

No pre-registered macro axis robustly concentrates either book's losses at T-1. The **only**
structurally-stable signal is a *modest* one — the worst single-day losses tilt to a strengthening
dollar (gold's dollar-beta), lift ≈1.5, which (a) fails the primary multiple-testing gate, (b) is
already known to be a **dilutive, challenge-speed-killing overlay** (parallel `overnight-ftmo-improve`
session, 2026-06), and (c) removes only ~55 % of worst-day loss-mass for 33 % of sat-out exposure
(removal/exposure ≈1.6, far below the ≈3–4 that would justify an overlay). **The losses are
dispersed across regimes, time, and cause. A macro overlay has nothing to aim at.**

---

## 1. Method (full detail in the frozen pre-reg)

**Why not the headline MC.** The forward block-bootstrap MC that produces `p_funded` resamples
return *indices* (`ftmo_sim._boot`, Politis-Romano) → it is **date-less by construction** and can
never attach a macro regime to a bust. So the diagnostic uses the two **date-preserving** paths:

1. **Challenge busts** — `run_funnel(CFG_V2, vm=14)` over a dense full-sample sweep (step=2 bd,
   1 648 cohorts, **p_funded 0.851** ✓); the engine `diag` hook records every bust with its **real
   date** + cause (`bust_daily` −5 % daily / `bust_floor` −10 % static). → 1 647 bust events,
   **374 distinct bust days** (951 daily / 696 floor; 12 % at the day's first bar = overnight gap).
2. **Book daily series** — instrumented vm=1 run, **daily re-anchored to constant exposure**
   (removes account-state artifacts; tail regime-profile is sizing-invariant), real-dated:
   ann-vol 14.0 %, 54 distinct >5 % drawdown episodes, worst day −5.33 %. Funded mechanics
   cross-check: `funded_cohort` sweep (699 cohorts, **bust 1.6 %** ✓).

**Regime panel — 4 pre-registered axes, all lagged 1 trading day (T-1, overlay-relevant).** VIX
(`vix.csv`), DXY 3m momentum (`DTWEXBGS`), HY OAS (`bamlh0a0hym2`), FOMC ±1 (`fomc_events.csv`).
**Causal split:** T-1 governs the verdict; contemporaneous (T) is reported only as the "trap" check.

**Test.** χ² of independence (loss-day × regime-bucket) with an **autocorrelation-robust
circular-shift permutation null** (B=5000) as the governing p-value; **Holm** over the primary
family, **BH-FDR** over the secondary. Concentration magnitude = bucket lift, event-share vs
day-share, VIX top-quintile share.

### Deviation from pre-registration (data-driven, disclosed)
Pre-reg §2 assumed full-sample HY OAS. **It is wrong**: the store holds `bamlh0a0hym2` only for
**2023-05 → 2026-05** (786 days). The full-history series is **TO-SOURCE** (FRED BAMLH0A0HYM2).
A3 credit is therefore **demoted to a reduced-coverage secondary axis on its 2023+ window**, and
the **primary Holm family reduced to 3 axes × 2 books = 6** (VIX, USD, FOMC — all full-sample).
The frozen pre-reg is left untouched as the record of intent; this correction is pre-results.

---

## 2. Results

### 2.1 Primary family — 6 tests, Holm, T-1 causal (the verdict layer)

| Event | Axis | n_ev | base | lift (worst bucket) | ev-share / day-share | p_perm | **p_Holm** |
|---|---|---|---|---|---|---|---|
| Challenge busts | VIX | 374 | .114 | 1.05 (hi) | .35 / .33 | .585 | 1.00 |
| Challenge busts | USD | 374 | .114 | **1.20 (usd-up)** | .40 / .33 | **.020** | 0.118 |
| Challenge busts | FOMC | 374 | .114 | 1.01 (—) | .91 / .91 | .621 | 1.00 |
| Funded down-legs (roll-10 tail5) | VIX | 165 | .050 | 1.37 (hi) | .45 / .33 | .245 | 1.00 |
| Funded down-legs | USD | 165 | .050 | 1.42 (usd-up) | .47 / .33 | .250 | 1.00 |
| Funded down-legs | FOMC | 165 | .050 | 1.01 (—) | .92 / .91 | .848 | 1.00 |

**0/6 survive Holm.** The single raw-significant cell (USD on challenge busts) dies under correction.

### 2.2 Trap check — contemporaneous (T) vs causal (T-1)
The only place a contemporaneous signal beats its causal version: **VIX on funded down-legs**,
T-1 lift 1.37/p 0.245 → **T lift 1.49/p 0.093**. I.e. drawdown clusters partly *coincide* with high
VIX but yesterday's VIX predicts them less — a mild instance of the pre-registered trap (looks
concentrated, isn't exploitable). Neither survives anyway. USD is slow (T-1 ≈ T), as expected.

### 2.3 Secondary (BH over 24) + the one stable signal
- **USD-up → worst single-day loss is the only BH-survivor**: worst-5 % days lift **1.60, p 0.0013,
  BH q 0.032**; worst-1 % lift 1.91 (q 0.068). **Sub-period-stable** (pre-2020 lift 1.66/p 0.005;
  post-2020 1.53/p 0.074) → a genuine structural tilt (gold's dollar-beta + USDJPY exposure), **not
  a 2022 artifact**. But modest, and it fails the primary gate.
- **VIX**: only the worst-1 % extreme days lean high-vol (lift 1.64, p 0.069; top-quintile share
  **0.45 = 2.27×** the 20 % baseline) — n=33, not BH-robust, partly contemporaneous.
- **FOMC**: worst-1 % days lift 2.27 (p 0.027) but BH q 0.19 (n=33, underpowered); everything
  broader ≈ 1.0.
- **Dissociation worth noting** — drawdown *level* days (`dd_p90`) concentrate in **LOW** vol
  (top-VIX-quintile share **0.05**, q1 share 0.68): the book's deep-drawdown *plateaus* build in
  calm grinds, while the sharp *down-legs* mildly lean high-vol. **A vol overlay would sit out the
  wrong regime for the funded book.**
- **A3 credit (2023+ only)**: all cells NS (n 6–56). Inconclusive — full-history HY OAS to-source.

### 2.4 Q3 — day-of-week & per-sleeve announcements
- **Day-of-week:** χ²(tail5 × DoW) **p 0.59** — no risky weekday (Wed triple-swap, Tue overnight-gap
  *not* worse). Means Mon +5 / Tue +12 / Wed +3 / Thu −0.6 / Fri +2 bps; CVaR-5 % uniform (−1.8 to −2.2 %).
- **Per-sleeve announcement tails (the J1/BoJ, gold+overnight/FOMC question):** every sleeve has an
  **equal-or-better** tail on its own announcement day (gold CVaR-5 % −1.27 % on FOMC vs −1.72 % off;
  overnight −0.79 vs −0.89; J1 −1.59 vs −1.33 on BoJ). Announcements do **not** drive sleeve tails.

### 2.5 Mechanism anchors (why "dispersed")
- **Co-loss:** worst book days are moderately broad (mean 1.42 of 3 sleeves negative vs 0.56;
  gold −73 bps & J1 −70 bps co-down) but only **weakly risk-off** (P(hi-VIX | ≥2 sleeves down) 0.46
  vs 0.42 narrow vs 0.33 base). Not global-risk-off crashes.
- **Worst 12 days** span 2014→2026 with *different* drivers — 2022-11-10 USDJPY crash (CPI miss),
  2015-08-24 China-deval vol crash, 2016 election, assorted gold sell-offs; 8/12 high-VIX but only
  2/12 FOMC, 3 different weekdays. Temporally and causally **scattered**.
- **Funded book busts on just 2 calendar days in 12.5 y**: 2015-08-24 (VIX 28, vol crash) and
  2016-11-09 (VIX 19, election reversal) — **two different regimes**. The catastrophic tail itself
  is not single-regime.

---

## 3. Does the overlay study pass the bar? — per-book

**Challenge — NO.** Busts spread across regimes (VIX lift 1.05, FOMC 1.01). The USD tilt (lift 1.20)
fails Holm and only re-states gold's dollar-beta. Removal/exposure ≈ 0.40/0.33 ≈ 1.2 — essentially
proportional. An overlay has no target.

**Funded — NO.** Down-legs unconcentrated (lift 1.37–1.42, p ≈ 0.25); deep-drawdown plateaus sit in
**low** vol, so a vol overlay would gate the wrong regime; the two historical busts are two
different regimes. No target.

**Rough best-case upside (the number a future study would chase):** the best *causal* candidate
(USD-up) avoids ≈55 % of worst-day loss-mass (53 % of worst-day count) for 33 % sat-out exposure
(ratio ≈1.6, audit-corrected from 1.4) — and fails Holm.
For an overlay to pay you want most of the loss removed for little exposure (lift ≥ 3); nothing here
is close. The acute-vol tail that *does* lean high-VIX (worst-1 %) is already handled by the engine's
own intraday breaker + daily-loss flatten — not an unaddressed overlay target.

---

## 4. Honesty guards & limits
- **T-1 governs** (not the prettier contemporaneous T); **circular-shift p governs** (not naive χ²);
  **Holm** over the pre-registered 6; everything else BH-secondary and labelled.
- **The per-bucket `lift` is a data-driven worst-bucket point estimate** (upward-biased: under H0
  its mean ≈1.08). It is reported for magnitude only; the **governing inference is the joint χ²
  permutation p**, which is not inflated by the bucket selection. A naive logistic/χ² that ignores
  the down-leg autocorrelation (lag-1 ≈0.69, ~49 independent episodes for 165 days) **over-states**
  significance — the autocorrelation-robust null is why the verdict is DISPERSED, not significant.
- The DISPERSED verdict is **conservative-robust to look-ahead in bucketing** (full-sample quantile
  breaks would, if anything, *help* find concentration — none found) and to the challenge
  cohort-overlap (a null cannot be inflated by it).
- **Credit axis untested full-sample** — HY OAS 2023+ only; full history TO-SOURCE before any credit
  claim. NFP/CPI/BoJ are 2020+ (secondary). GER40 2018–21 hole is engine-masked. CET/EET-vs-UTC
  absorbed by the ±1-day announcement window.
- Two book series (governor effect is ≈1 at vm=1 under daily re-anchor) → the tail is undistorted.

## 5. Independent audit (author≠auditor)
**CONFIRM-WITH-CAVEATS.** An independent auditor reproduced every substrate number (p_funded 0.851,
funded bust 1.57 %, 374 bust days, ann-vol 13.95 %, the 2 funded-bust calendar days), verified the
T-1 causality (`shift(1)`, no look-ahead) and the HY-OAS 2023+ coverage, and **re-tested the headline
cells with two independent methods** (logistic regression + stationary block bootstrap L=21). A naive
logistic *appeared* to refute (2/6 survive) but the auditor traced this to the down-leg
autocorrelation (pseudo-replication); their block bootstrap **reproduced the study's circular-shift
p** (roll10×USD 0.203 vs 0.250; de-clustered episode GOF 0.368) → **0/6 Holm confirmed**, method
validated. No verdict-flipping bug. Caveats applied above: overlay ratio 1.4→**1.6** (loss-mass
basis; still ≪ the ≈3 bar), and the explicit selected-lift note (§4).

## 6. Reproduce
`regime_diag/`: `_smoke.py` (cache engine `M`) → `build_book.py` (events) → `lib_regime.py` (panel) →
`run_diagnostic.py` (primary/secondary/trap, `results/diagnostic_results.json`) → `run_mechanism.py`
(Q3/co-loss/robustness/anchors). Engine + caches read-only by absolute path from main dir; `_cache/`
regenerable (gitignored).
