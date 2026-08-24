# PRE-REGISTRATION — Breakout in CONTAINER: does it improve funded survival despite low Sharpe?

**Frozen 2026-06-20 BEFORE any result** (git history attests). Branch `claude/breakout-container-combine`,
worktree `Algo_claude_breakout_combine`. **Diagnostic/feasibility of an existing candidate** (Cowork
breakout) — revalidate on the AUDITED engine + container ablation. No deployment; EA is frozen so even a
positive is a future-version topic. Live book / EA / FLAT untouched, read-only.

## The question
Every always-on, negative-tail OVERNIGHT sleeve DILUTED the book's funded survival (gold/soybean/basket
−26..−37 pt; gold-dosing dilemma: even 0.10× → −12.6 pt). The breakout is the FIRST candidate with the
profile the container logic rewards: **positive skew (+1.3..+2.7), bounded excursion, intermittent,
potentially tail-decorrelated** — but low standalone Sharpe (~0.43 lower-bound, ≈0 at realistic cost,
DSR 0.23). Does a low-Sharpe-but-positive-skew, tail-decorrelated sleeve IMPROVE funded survival where
the overnight family failed? (Lesson `container-intermittency-beats-standalone-Sharpe`.)

## Substrate (audited engine reused, NOT reimplemented)
- Funded engine: `engine_v22` (`data/ftmo_portfolio/v22`) + cleanroom `engine.py`, imported read-only by
  absolute path from main dir. **Canonical `FUNDED_WINDOWS`** (config_v22): IS 2013-10-01→2017-12-31 +
  OOS 2020-01-02→2024-06-30, `FUNDED_STEP=12`, `FUNDED_HORIZON=504`, `FUNDED_WD_EVERY=14`, FEE $96,
  `CFG_FUNDED` (vm=1, on_w=0.35, orb_risk=0.0025). ~191 cohorts.
- Book = gold (XAUUSD carry-adj TSMOM) + J1 (USDJPY 12-1) + overnight (GER40/US100 Mon/Tue) + ORB.
  **Baseline to reproduce as a gate:** survive252 **0.9791**, fundedV **$1442**, min-bal grazing ~$9058.
- Breakout sleeve = Donchian **D20**, **SL 1×ATR(20)**, **TP 3×ATR(20)**, entry next-bar-open,
  **force-flat true session-EOD** (no overnight bleed — lesson `intraday-flat-must-force-EOD`), two-sided.
  Instruments **EURUSD + GER40 + XAUUSD** (GBPUSD EXCLUDED: fails L25 long-leg). Sessions idx 13:30–20:00
  UTC / FX 07:00–16:00 UTC. Computed on **AUDITED data** (`data/deep_history_utc/*_M1.csv` → 1h OHLC),
  NOT Cowork's `_cache`. Pooled = equal-weight mean of the 3 instruments' daily series.
- Costs: **lower-bound** = median(spread/close) per instrument; **realistic** = 2 bps idx / 1 bps FX (stress).

## Q0 — revalidate the edge on the audited engine (prerequisite GATE)
Reproduce the Cowork standalone breakout on audited M1. **PASS iff ALL:**
(i) pooled book net SR ∈ [0.30, 0.60] at lower-bound cost (Cowork 0.43);
(ii) positive skew per instrument (+1.0..+3.0);
(iii) two-sided: EURUSD short-leg bps > 0 AND long-leg ≥ 0; GER40 both legs ≥ 0;
(iv) not-beta: EURUSD buy&hold SR ≤ 0 while breakout SR > 0;
(v) force-flat EOD verified (eod-exit fraction ~50–70%, no multi-day holds).
**If FAIL (sign-flip / negative skew / two-sided fails) → STOP and report**: the Cowork positive does not
survive the audited engine. Show all numbers (per instrument + pooled, both cost levels) + DSR (N=145).

## Q1 — tail-decorrelation breakout vs book (container prerequisite)
- Book daily series: the funded book's realized constant-exposure daily return (audited engine, vm=1), real-dated.
- **ρ_tail (pre-registered):** Spearman corr of daily returns restricted to the UNION of each series'
  bottom-decile days. Also report (a) P(breakout in its bottom-10% | book in its bottom-10%) vs 0.10
  (tail co-occurrence lift), (b) breakout mean return on the book's worst-5% days (the container ideal =
  breakout PAYS when the book bleeds).
- **Gate:** ρ_tail ≤ 0.3 for the container logic to have a chance (§4 sensitivity: ρ_tail 0.0→0.94 surv,
  0.3→0.80, 0.6→0.54, 0.9→0.26). If ρ_tail > 0.3 → the breakout cannot help (tail-correlated).

## Q2 — funded ablation (THE test)
Reuse `asia_inject.run_funded` VERBATIM, swapping the ASIA block for the breakout block (M["brk_net"],
M["brk_low"]). Sweep canonical FUNDED_WINDOWS. Metrics (gold-dosing defs): survive252 = mean(life≥252);
fundedV = mean(0.8·(wd+residual) over non-bust) + FEE; min_eq median.
- **Validation gate:** brk_off MUST reproduce baseline 0.9791 / $1442 (±0.5 pt / ±$30) — confirms correct harness use.
- **Doses (4, frozen):** breakout VT to 10% annual standalone, doses **{0.10, 0.25, 0.50, 1.0}×** (grid
  directly comparable to gold-dosing).
- Breakout (net, low) per day: net = Σ(trade returns exiting that day) − cost; low = min intraday pooled
  cumulative MTM (marked on 1h bars, half-spread applied) ≤ 0; both VT-scaled then ×dose.
- **Injection placement:** PRIMARY = canonical asia harness (day-start block, barrier `bal+brk_low<lim_eff`).
  ROBUSTNESS = conservative combined-low (book intraday-min + brk_low). Report BOTH (the breakout is
  intraday-concurrent with the book, unlike ASIA which closes at the book open — so the conservative
  variant bounds the timing approximation).
- Per dose: triplet (fundedV, survive252, min_eq) + Δsurv, Δextract vs baseline.

## Q3 — does cost bite even in container?
Run Q2 at BOTH lower-bound AND realistic cost. A benefit must survive realistic cost; one that exists only
at the optimistic lower-bound is not robust.

## Verdict rubric (frozen)
- **(a) IMPROVES** — ∃ dose with **Δsurv ≥ −2.5 pt (held) AND Δextract > 0 at REALISTIC cost** → FIRST
  viable container candidate; positive decorrelated tail beats dilution. MAJOR result → mandatory
  independent fresh-context audit before believing it. Present AVANT/APRÈS for decision (EA frozen → future version).
- **(b) DILUTES** — all doses Δsurv < −2.5 pt (like the overnight family) → positive tail insufficient when
  Sharpe too low / cost bites → closes the container logic for price-only.
- **(c) NEUTRAL** — tail-decorrelated but Δextract ≤ 0 after cost while not improving survival → neither helps nor hurts.
Cite triplets (extraction, survival, min-balance), ρ_tail, DSR, at lower-bound AND realistic cost.

## Hard constraints & guardrails
- **Survival is the binding constraint**: a dose that lifts extraction but degrades survival (Δsurv < −2.5 pt)
  is NOT an improvement (criterion = extraction AT survival held).
- Audited engine REUSED not reimplemented; canonical FUNDED_WINDOWS (not a convenience window — basket lesson).
- Integrity check in MAIN dir. author≠auditor mandatory if (a). Doses = the ≤4 pre-registered modifications.
- Feasibility ablation of an existing candidate → mints NAMED lessons only, no L-number; global registry chain verified intact.
