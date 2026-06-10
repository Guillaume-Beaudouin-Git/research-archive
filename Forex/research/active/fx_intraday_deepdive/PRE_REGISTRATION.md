# PRE-REGISTRATION — Intraday-FX microstructure deep-dive

**Frozen:** 2026-06-09, BEFORE any IC computation or backtest on the chosen hypothesis.
**Author:** Claude Code (autonomous /goal run).
**Discipline:** ONE hypothesis fully deep-dived before the next. Phase-0 pre-reg (this file) → Phase-1 IC
gate (cheap close) → Phase-2 full deep-dive only if IC passes. Two-sided + delay-robustness mandatory.
DSR at TRUE cumulative N or void. Real costs incl. calibrated spread (+50% stress) + commission +
≥1-tick slippage; swap only if held overnight (target profile is intraday-flat → swap-free).

**Cumulative trial count entering this run: N = 108** (program ledger, per `research/PROGRAM_DECISION_MEMO.md`
and memory `ftmo_candidate_funnel_2026-06`). Every IC configuration, backtest variant, delay variant,
param-grid point, and ablation below increments N. Tracked in `N_ledger.md`.

---

## 0. What is already BURNED (cited; will NOT be re-tested)

From an exhaustive repo reconnaissance (read-only). These are dead and **must not** be re-proposed:

| # | Burned family | Path | Verdict / key numbers | Lesson |
|---|---|---|---|---|
| B1 | Generic intraday FX **mean-reversion** (z-score/RSI, 5–15min, all hours) | `PropFirms/ftmo_alpha_program/strategy/intraday_fx_mr.py` + `results/phase1_feasibility.json` | EURUSD ann-Sharpe **0.708**, GBPUSD **0.011**, XAU −0.95; cost-ratio 2.49 < gate 3.0 → **FAIL** | L11, L23b |
| B2 | Generic intraday FX **momentum** (directional, 5–15min) | (no dedicated survivor; cost-killed per program) | gross < 3× cost at retail CFD spread | L11b |
| B3 | **London ORB v1** (opening-range *breakout* / momentum) | `Forex/research/archived/london_orb_v1/POSTMORTEM.md` | best t_HAC **1.01** (GBPUSD) < 1.65; hit 48–54%; dual-pair confirm = 0 value. **NB: EURUSD 4h horizon shows REVERSAL IC −0.102, t −2.45** (a prior look — see §6) | L2, L6, L10 |
| B4 | **F2 Asian-range breakout → London open** (momentum) | `Forex/research/archived/strategy_f2_asian_breakout/POSTMORTEM.md` | IJR gate 0.751 ≪ 3.0, pre-flight kill, no backtest | L11b |
| B5 | **WMR London 16:00 fix** + EOM USD flow (Strategy E) | `Forex/research/archived/strategy_e_fix_flow/POSTMORTEM.md` | killed at literature; gross 1–4 bp < 6–7 bp retail; window widened 1→5min (BIS 2015) | L23, L23b |
| B6 | **Fix-reversal** (Krohn 2024 / Ranaldo segmentation), London/ECB/Tokyo fixes | `Forex/research/active/fix_reversal/FIX_REVERSAL_FTMO.md` | London net **−1.78 bps** (gross 0.45, cost 2.23); pooled gross **0.22 bps**, net −3.11; Tokyo cost 5.59 bps; Ranaldo short-leg one-sided (L25 fail) | L34 |
| B7 | G10 carry, CS/TS daily FX momentum, Round-Number Cascade | CLAUDE.md research history | all dead post-GFC / all IC horizons FAIL | L23, FX-1..4 |

**Decisive takeaway from B3–B6:** at the **London 16:00 fix window** the binding RT cost on FTMO MT5 is
**~2.23 bps p95** and flow-anchored gross edges there are ~0.2–1.4 bps → net-negative (L34). Any new FX
intraday edge must clear an **L34 pre-flight: `gross_per_trade / cost_p95 ≥ 1.5`** or it is cost-killed by
construction. **However**, B3–B6 all trade at or after the *fix* / *breakout direction*; none tests the
**reversal of the overnight (Asian) displacement at the London OPEN**, and the one incidental look (B3's
4h EURUSD reversal t = −2.45) points *toward* a reversal, not away. That gap is the opening for H1.

---

## 1. Candidate hypotheses (Phase-0 menu, ranked)

Each: (a) microstructural mechanism, (b) why it could survive on retail M1, (c) why it is NOT in the
burned set, (d) intraday-flat vs overnight, (e) the binding risk.

### H1 — **London-open reversal of the Asian-session displacement** ★ CHOSEN FIRST
- **(a) Mechanism.** During the Asian session, EUR/GBP/CHF/CAD trade in their *thinnest, least-informed*
  window (no domestic price discovery; Tokyo flow is cross-driven and range-bound). Small, often noise-
  driven displacements accumulate. When **London** — the dominant liquidity venue for these pairs — opens,
  genuine two-way price discovery resumes and **disproportionately corrects (reverts)** the overnight
  displacement. Prediction: corr(Asian-session return, London-morning return) **< 0**.
- **(b) Retail-M1 survival.** The signal is one decision/day/pair (low turnover → cost-survivable, unlike
  B1's all-hours churn). Entry is the **London open (07:00–09:00 UTC)**, among the *tightest-spread,
  highest-liquidity* windows of the day — the cost-favorable opposite of the news/fix trap. Intraday-flat.
- **(c) Not burned.** B3/B4 trade the *breakout* (momentum continuation) at the open and the Asian-range
  *breakout* — H1 is the **opposite sign** (fade, not follow) and conditions on the *overnight return*, not
  a range break. B1 is continuous all-hours z-fade; H1 is a single session-handoff event. B6 trades the
  16:00 fix, a different window. The reconnaissance found **no FX session-handoff reversal test** in repo.
- **(d) Intraday-flat → swap-free** (enter ~07:00 UTC, exit ≤15:00 UTC, well before the ~21:00 UTC rollover).
- **(e) Binding risk.** Cost (L34): is the London-open RT spread tight enough that the reversal clears
  `gross/cost ≥ 1.5`? And mechanism specificity: does the edge **concentrate in European pairs** (mechanism)
  or smear across all pairs incl. Asia-native (→ it's just burned B1)?

### H2 — Post-scheduled-news intraday drift (first 1–4 h after high-impact USD/EUR releases)
- **(a)** Staggered institutional repricing / underreaction to macro surprises (Andersen-Bollerslev-Diebold-
  Vega 2003). Daily event studies in-repo show post-event **continuation**, not reversal (FTMO top-10).
- **(b)** Calendar 2018–2026 on disk (74,543 events); the release time is known exactly; predictor = sign/size
  of the initial jump. (c) Repo only tested daily event windows + B3's spike-*fade* (failed N-floor at 130<150);
  intraday first-hour *drift* untested. (d) Intraday-flat. **(e) Binding risk: COST TRAP** — spreads blow out
  3–10× at release (the purest L23b retail-microstructure trap); + calendar only 2018–26 (no 2007–15 depth).

### H3 — Day-of-week × time-of-day liquidity seasonality (pure calendar-time intraday)
- **(a)** Predictable institutional flow windows (EOM/EOW squaring, fixing-adjacent). (b) Pure calendar
  position, zero estimation. (c) Repo tested daily weekday effects, not intraday hour-of-week on FX.
  (d) Intraday-flat. **(e) Weak mechanism; likely thin / data-mined if unconstrained.**

### H4 — (considered, NOT chosen) NY-open / late-session / fix windows
- Burned or cost-killed: the London/NY/Tokyo **fixes** are B5/B6 (L34); NY behaviour is a sub-window of the
  burned B1. Listed only to record it was considered and rejected on the burn list.

### Ranking — `mechanism × retail-feasibility × swap-avoidance × cost-favorability`

| H | mechanism | feasibility | swap-free | cost-favorable | history | **rank** |
|---|---|---|---|---|---|---|
| **H1** | high (session handoff, clean) | high (1 trade/day) | yes | **yes (London open = tight)** | full 2007–26 | **#1** |
| H2 | high | medium | yes | **no (release blowout)** | 2018–26 only | #2 |
| H3 | low | high | yes | yes | full | #3 |

**→ Deep-dive H1 first.** H2/H3 deferred to their own pre-registrations after H1 reaches a clean verdict.

---

## 2. H1 — FROZEN SPECIFICATION

### 2.1 Universe (mechanism-driven split — this split IS the falsification)
- **PRIMARY pool (Asian session thin/uninformed → predict reversal):**
  `EURUSD, GBPUSD, EURGBP, USDCHF, USDCAD` (5 pairs).
- **CONTRAST pool (Asia-native, Asian session is their *active* session → predict weak/absent or
  *continuation*):** `USDJPY, EURJPY, AUDJPY, AUDUSD, NZDUSD` (5 pairs).
- **XAUUSD:** cached as an out-of-class contrast only (global 24h metal — mechanism N/A); not in either pool.

### 2.2 Sessions (UTC, primary spec; DST handled as a Phase-2 robustness leg)
- **Asian/overnight predictor window:** `23:00 (prev day) → 06:59 UTC`.
- **London-open entry:** the `07:00 UTC` 15-min bar (delay+1 after the 06:45 signal bar).
- **London-morning holding/return window:** `07:00 → 12:00 UTC` (primary exit 12:00, before NY open 13:00).
- All times are bar-start UTC on the cached 15-min bars. FX day = Mon–Fri sessions only.
- *DST note:* London open is 07:00 UTC (summer/BST) vs 08:00 UTC (winter/GMT). The primary spec fixes UTC
  07:00 and accepts the 1-h winter wobble; **Phase 2 adds a DST-correct leg** (Europe/London-local 08:00 open).

### 2.3 Signal (causal — known at decision time, T-1 information only)
- `asian_ret_d = log(close_06:45) − log(close_22:45 prev)` (overnight displacement; known by 07:00).
- `x_d = − asian_ret_d / σ_asian` where `σ_asian` = trailing 60-day std of `asian_ret` (lagged, causal).
  Continuous reversion predictor (two-sided by construction: fades up-moves AND down-moves).
- Backtest position: `pos_d = clip(x_d, −1, +1)`, entered at the 07:00 bar **open** (delay+1), held to 12:00,
  flat thereafter (intraday-flat, no overnight carry, no swap).

### 2.4 Forward return for the IC gate
- `R_London_d = log(close_12:00) − log(open_07:00)` (the holding-window return).
- IC target tests `corr(x_d, R_London_d)` — must be **> 0** (i.e. `corr(asian_ret, R_London) < 0`: reversal).

### 2.5 Costs (always real; never gross-only for a verdict)
- RT cost via `funnel_lib.rt_cost_fraction(sym, spread_pts, close)` = markup(3×)·spread·point/price +
  FX commission/slippage (0.9 bps). Spread = the **cached calibrated median spread at the entry (07:00) and
  exit (12:00) bars**. **+50 % spread-stress leg** mandatory. **+1-tick (≥) intraday slippage** added.
- Swap = 0 (intraday-flat). If any variant holds past ~21:00 UTC, the measured CFD swap is applied.

### 2.6 Vol-targeting & aggregation
- Per-pair daily net return → equal-risk (inverse trailing-vol, lagged) sleeve across the PRIMARY pool
  (`funnel_lib.combine_inv_vol`). p(pass) scales the sleeve to σ_d = 1 % (`funnel_lib.p_funded`).

---

## 3. GATES & FALSIFICATION (frozen)

### Phase-1 IC gate (cheap close — run BEFORE any full backtest)
- Causal IC of `x_d` vs `R_London_d`, **per-pair AND pooled** over the PRIMARY pool: Spearman ρ, Pearson r,
  and **HAC/Newey-West (lag 6) t-stat** on the pooled OLS slope (clustered/pooled across pairs).
- **PASS requires ALL:**
  1. pooled PRIMARY **HAC |t| > 2.5**, and
  2. **sign = reversal** (corr(asian_ret, R_London) < 0), and
  3. N ≥ 50 events/yr (trivially met: ~250/yr/pair × 5 ≈ 1250/yr pooled), and
  4. survives **multiple-testing deflation** for the Phase-0 variants tried at cumulative N.
- **NULL → STOP H1, write the negative report, return to Phase-0 for H2.**

### Falsification criteria (any TRUE ⇒ H1 is not the claimed edge)
- **F1** pooled PRIMARY HAC |t| < 2.5 → no edge → STOP.
- **F2** CONTRAST (Asia-native) pool reversal is **≥** PRIMARY pool (|t|_contrast ≥ |t|_primary, same sign)
  → it is generic all-pairs MR (burned B1), not the session-handoff mechanism → STOP / reclassify as burned.
- **F3** edge is **one-sided** (only the fade-of-up leg OR only the fade-of-down leg carries it; the other
  ≈0 or wrong sign) → **L25 fail** → beta-disguised / look-ahead → do not promote.
- **F4** edge exists at **delay-0** but collapses **>30 %** at **delay+1** → **L26 fill artifact** → STOP.
- **F5 (L34 cost pre-flight)** gross-per-trade edge **< 1.5×** the p95 RT cost at the 07:00/12:00 windows →
  cost-killed → report as real-but-sub-threshold, not tradable.
- **F6** edge lives **only** in one sub-period (e.g. only 2021–26, ≈0 on 2007–20 — the TSMOM-K200 trap) →
  regime artifact → at most "real-but-sub-threshold", never "clears bar".

### Phase-2 deep-dive (only if Phase-1 PASS) — each item's variants count toward N
- **Two-sided (L25):** split P&L by entry direction; both legs must contribute.
- **Delay (L26):** delay ∈ {0, +1, +2, +3} bars; non-overlapping trades; report the Δ.
- **Microstructure decomposition:** by pair, day-of-week, exit-hour bucket, and vol regime (where does it live?).
- **Sub-periods:** 2007–09 / 2010–15 / 2016–20 / 2021–26 (persist vs regime artifact).
- **Cost:** calibrated spread, +50 % stress, +slippage; gross-vs-net attribution (cost failure vs edge failure).
- **Parameter surface (coarse, controlled):** Asian-window start ∈ {22:00, 23:00, 00:00 UTC} × hold-exit ∈
  {10:00, 11:00, 12:00, 13:00, 15:00 UTC}. Report the Sharpe **surface** (plateau = real, spike = artifact).
  **Each grid point = +1 to N.**
- **Ablations:** strip vol-scaling (→ sign-only); strip the European filter (→ all-10 pool); strip two-sided
  (→ long-fade-only). Edge should degrade gracefully, not collapse onto one knob.

---

## 4. VERDICT RULES (frozen)

- **DSR** (Bailey-López de Prado, probabilistic ∈[0,1], `dsr.py` verbatim) computed on the full-history net
  daily sleeve **AND** the OOS hold-out (≥2025-01-01), deflated at **TRUE cumulative N** (108 + every variant
  counted in `N_ledger.md`). State N explicitly with every DSR.
- **Noise floor:** OOS Sharpe must exceed `SE0 × E[max of N iid N(0,1)]`, with SE0 estimated on the FX
  intraday daily sleeve (reusing `gate0_noise_floor.py` logic). State the threshold at the realized N.
- **Walk-forward:** expanding window **≥5 folds**; must hold on WF **and** full history, not just OOS.
- **Two-tier gates:** RESEARCH_PASS = Sharpe>0.7, MaxDD<−25 %, WF>50 %. PROPFIRM_PASS = Sharpe>1.0,
  MaxDD<−10 %, WF>60 %, **DSR(P) > 0.5** at cumulative N.
- **p(pass) ± CI** on **FTMO 2-step** (10 %/5 % targets, 10 % static max-DD, 5 % daily floor, NO time limit,
  `combined_pass_prob_empirical`) **AND FundedNext** geometry; swap-free intraday-flat is the favorable case.
- **Verdict label (one of):** *clears the bar* / *real-but-sub-threshold (like Ross Hook)* / *artifact* / *dead*.
- Only after a clean, written verdict on H1 do we proceed to H2 (new pre-registration appended here).

---

## 5. Output contract
`research/fx_intraday_deepdive/`: this `PRE_REGISTRATION.md` (frozen) · `REPORT_H1.md` (IC gate, microstructure
decomposition, sub-period table, parameter surface, ablations, DSR@N, p(pass)±CI, verdict) · `N_ledger.md`
(running cumulative trial count) · `cache/` (15-min bars + true-UTC verification, build artifacts).
READ-ONLY on `data/` and all prior deliverables. Never fabricate — missing/uncheckable is reported as such.

---

# ADDENDUM — H2 pre-registration (frozen 2026-06-09, AFTER H1's clean negative, BEFORE any H2 result)

**H1 verdict (closed, N=127):** real mechanism (European London-open reversal, F2 contrast textbook,
delay-robust) but DEAD net — cost-killed ~5–10× (L34), one-sided (L25), gross only at the N=127 noise floor.
Per the discipline, proceed to the next-ranked Phase-0 hypothesis.

## H2 — Post-scheduled-news intraday drift (first-hour continuation on USD majors)
- **Mechanism.** Underreaction to scheduled macro surprises (Andersen-Bollerslev-Diebold-Vega 2003): the
  initial impulse in the first minutes after a high-impact USD release **continues** (drifts) over the next
  ~45 min as staggered institutional repricing completes. The repo's *daily* event work found post-event
  **momentum continues** (FTMO top-10) and pre-FOMC drift is real (L42) — H2 tests the **intraday M1
  first-hour** version on FX majors, which is **untested** (B3 Angle B spike-*fade* failed N-floor 130<150;
  daily studies are separate). Intraday-flat → swap-free.
- **Cost reality (measured, not assumed).** Calendar timestamps verified true-UTC & minute-accurate (NFP
  12:30/13:30 UTC, FOMC 18:00/19:00 UTC). The release sits in the **tight London/NY window**: EURUSD 15-min
  median spread ≈ 1.0 pt at the release bar. Entering at **r+15min** (after the seconds-long spike) pays
  ~1.0-pt spread (≈1.2 bps RT) — NOT a blowout. *Known limitation:* the 15-min median misses the intra-bar
  spike; cost = cached spread_med at entry/exit + **+50 % stress + 1-tick news slippage** as a floor.

### FROZEN SPEC
- **Universe:** EURUSD, GBPUSD, USDJPY (most-liquid USD majors; tightest news-time spreads).
- **Events:** USD **HIGH**-impact releases (calendar 2018–2026), deduped to unique release minutes, floored
  to the 15-min grid (≈the NFP/CPI/FOMC/Retail/ISM/GDP moments). ~USD-HIGH ≈ 1530 events.
- **Impulse (predictor, causal):** `impulse_d = log(px(r+15)) − log(px(r))` (first-15-min reaction; r = release
  bar start). Signal `x_d = impulse_d / σ₆₀(impulse, lagged)`. Known at r+15.
- **Forward/holding window (IC target):** `cont_d = log(px(r+60)) − log(px(r+15))` (next 45 min).
- **Entry/exit (backtest):** enter at the r+30 bar open (delay+1 after the r+15 signal bar), exit at r+60.
  Position `= sign(x)` (continuation: long after up-impulse, short after down-impulse). Two-sided. Intraday-flat.
- **Costs:** `rt_cost_fraction` at the entry & exit bar spreads, **+50 % stress + 1-tick news slippage**.

### GATES & FALSIFICATION (frozen)
- **Phase-1 IC gate:** pooled (3 pairs) causal IC of `impulse` vs `cont`, Spearman + Pearson + HAC-NW(6) t.
  **PASS requires:** pooled **HAC |t| > 2.5**, sign = **continuation** (corr(impulse, cont) > 0), N ≥ 50/yr,
  deflated at cumulative N (= 127 + H2 variants).
- **F1** pooled HAC |t| < 2.5 → STOP. **F2-dir** if corr < 0 (it's *fade*/overreaction, not the registered
  continuation) → report as a distinct finding, do not claim H2. **F3 (L25)** one-sided (only up- or only
  down-impulses continue) → beta-disguised → do not promote. **F4 (L26)** edge only at delay-0 → fill
  artifact → STOP. **F5 (L34)** drift gross/trade < 1.5× news-time RT cost → cost-killed → sub-threshold.
- **Phase-2 (only if PASS):** two-sided split, delay 0/+1/+2/+3, decomposition by event type (NFP/CPI/FOMC/…),
  by pair, by surprise size; sub-periods; impulse-window × hold-window parameter surface (each cell +1 to N);
  ablations. Verdict identical rules to H1 (DSR@N, noise floor, WF≥5, p(pass)±CI FTMO-Swing & FundedNext).

---

# ADDENDUM 2 — H3 pre-registration (frozen 2026-06-09, AFTER H1+H2 negatives, BEFORE any H3 result)

**H2 verdict (closed, N=140):** DEAD — no intraday post-news continuation at ≥15-min horizons (pooled
HAC-t 0.19), cost-dead below. Two negatives now share one cause: **retail CFD RT cost (~2–5 bps) ≫ the
sub-bps / zero gross intraday-FX microstructure signal.** H3 asks the decisive closing question.

## H3 — Day-of-week × session directional seasonal (intraday-flat, swap-free)
- **Question (decisive):** is there ANY intraday-flat, swap-free **day-of-week × session** directional
  seasonal in FX majors that survives **real cost + DSR deflation at cumulative N**? If the best of a fully
  -counted controlled scan sits at the noise floor, the retail FX intraday-flat space is **burned across all
  three orthogonal angles** (reversal / news / seasonality).
- **Mechanism (weak, acknowledged):** predictable institutional flow timing — weekend position-squaring
  (Friday), Monday weekend-information repricing, mid-week settlement/rollover. Low conviction; the scan is
  framed as a **falsification of the cost-beating-seasonal hypothesis**, not a fishing expedition — every
  cell is counted toward N and the best must beat the deflated floor.
- **Swap-avoidance:** all sessions are intraday-flat (enter at session open, exit by ≤ 20:00 UTC) → swap = 0.

### FROZEN SPEC
- **Universe:** the 10 FX majors. **Sessions (UTC, intraday-flat):** London `07:00→16:00`, NY `13:00→20:00`.
- **Scan cells:** pair (10) × weekday (Mon–Fri) × session (2) = **100 cells**. For each cell: full-history
  mean session-return + Newey-West(6) t (gross), and a **causal WF seasonal** (sign = expanding-window IS
  mean of that (pair,weekday,session); applied OOS-forward; one round-trip/traded-day).
- **Costs:** `rt_cost_fraction` at session open/close spreads, +50 % stress.
- **Aggregate strategy:** the WF day-of-week sleeve = per pair, trade each session in the sign of its
  (weekday-specific) expanding-mean; equal-risk combine across pairs.

### GATES & FALSIFICATION (frozen)
- **Phase-1 gate (the whole H3, since it is itself a breadth scan):** (a) does the best of the 100 gross
  cells exceed the **DSR/noise floor at N = 140 + 100 = 240**? (b) does the **pooled WF day-of-week sleeve**
  net Sharpe beat the floor at that N, with **DSR(P) > 0.5** and **WF ≥ 5 folds**? (c) **L34** gross/cost ≥ 1.5?
- **F-mining:** if no cell beats the deflated floor and the WF sleeve is net ≤ 0 → **no cost-beating seasonal
  → H3 dead, space burned.** **F-cost (L34):** if a cell is gross-significant but gross/cost < 1.5 → cost-dead.
- **Phase-2 (only if a cell/sleeve PASSES):** mechanism check (is the surviving weekday economically
  sensible?), sub-periods, two-sided, ablations, DSR@N, p(pass)±CI. Otherwise close H3 and write SYNTHESIS.

## 6. Prior-look disclosure (honesty)
B3's POSTMORTEM incidentally reports a EURUSD **4h London reversal IC = −0.102, t = −2.45** on 2020–2024
Dukascopy. This run did not design H1 from that number, but it is a **prior look at a reversal at the London
open** and is disclosed here: it weakly *supports* H1's sign, and it means the "reversal at London" idea is
**not free of prior testing**. It is therefore counted in the deflation (a prior trial in the same direction),
and a "clears the bar" verdict requires H1 to hold on the **full 2007–2026 history and ≥5 WF folds**, not on
the 2020–24 window where that prior look occurred.
