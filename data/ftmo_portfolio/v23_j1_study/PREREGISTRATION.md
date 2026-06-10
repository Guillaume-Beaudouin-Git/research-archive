# v2.3 PRE-REGISTERED STUDY — J1 sizing/turnover (executes ON the v2.2 commit)

*Frozen 2026-06-10 ~20:45 CET, BEFORE any variant run. Mission text is the contract; this file
operationalizes it. Written while the v2.2 contractual run was in flight (acceptance_A PASS
pooled 86.58 seen; no variant outcome seen). Execution gated on the v2.2 commit hash.*

## GATE (from mission, verbatim discipline)
- Do nothing until the v2.2 commit hash exists; baseline = that commit.
- All deltas measured against frozen v2.2, never v2.0/v2.1 (the ORB-off × J1 interaction must
  live inside the baseline).
- Baseline commit hash: **605f4a4** (`605f4a426da3eac4f5a2644bca774a07f1e5f754`, 2026-06-10
  20:55:53 +0200) — file SHA256s pinned in `baseline_pin.json`; any post-pin change to v22/
  invalidates the study. Canonical baseline table: `v22/tables/v22_challenge_91.csv`
  (IS 90.6 / OOS 83.4 / pooled 87.0). EV convention: VAL=$1,422 (re-derived, contractual),
  FEE=$96.

## MOTIVATION (from the v2.1 attribution study — NOT re-derived here)
J1 = 51% of gross notional (16.3× equity when active) for 25% of risk; in-container drift
−$8.6/day (re-trading cost bleed; the signal itself is fine, standalone SR +0.42); not-funded
cohorts lose −$1,932/cohort on J1; removal ~free unrescaled (−2.2 ns, EV +$8) but re-levering
replaces it badly (−5.2). Source: `attribution_timing/ATTRIBUTION_TIMING.md` P1/P2.

## VARIANTS (≤3 per L10; adopt at most ONE)
Spec mapping: the book's J1 budget is 0.5 (PORTFOLIOS.md "budgets spec : or 0.5 / jpy 0.5");
the engine carries it inside `WT[:,1]` as built by `E.build_signals()`. Therefore:

- **A. J1 budget 0.5 → 0.25** ≡ multiply engine J1 weight column by 0.25/0.5 = **0.5**:
  `WT_A[:,1] = 0.5 × WT[:,1]`. Signal, timing, all other legs untouched.
- **B. No-trade band on J1's daily 22:05 vol-target rebalance ONLY** (hysteresis ±X% around
  target notional ≡ lots for USDJPY, $1,000/0.01-lot price-independent): at segment 4, if
  `pos_J1 ≠ 0, tgt_J1 ≠ 0, same sign, |tgt_J1 − pos_J1| ≤ X·|tgt_J1|` → hold `pos_J1`
  (no J1 trade). Entries (0→w), exits (w→0) always execute. Band applies BEFORE margin cap
  and quantization (cap and lot-rounding are risk/mechanical layers and stay untouched).
  Signal untouched. **X set ex-ante** (procedure below) to cut J1 turnover ~50%.
- **C. J1 OFF**: `WT_C[:,1] = 0`.

Each in two forms per L19:
- **(i) iso-leverage**: book rescaled to baseline realized vol via the FROZEN v2.1 factor
  procedure — `FACT = std(book_pnl) / std(book_pnl − removed_component)` computed on the
  **v2.2 baseline** attributed day records (this study's baseline run), then `vm = 14 × FACT`
  (P2 inherits ×1.2 as always):
  - FACT_A: removed_component = 0.5 × jpy_pnl
  - FACT_C: removed_component = 1.0 × jpy_pnl
  - FACT_B: the band removes ~no variance (positions stay within ±X% of target; the effect is
    cost drag, ~zero variance). FACT_B is measured as std(book_base)/std(book_B_raw) from the
    two arms' day records. If |FACT_B − 1| ≤ 0.01, B-iso is DECLARED ≡ B-raw (engine is
    deterministic; a duplicate run is not evidence) and reported as such; else B-iso runs with
    vm = 14 × FACT_B. This resolution is fixed here, before any B run.
- **(ii) raw**: vm = 14 unchanged.

= 6 runs + baseline (B-iso possibly collapsing to B-raw by the rule above).

## X CALIBRATION (ex-ante, mechanical, outcome-blind)
From the BASELINE run's recorded (pos_J1_before, tgt_J1_raw) pairs at segment 4 (pre-band,
pre-cap, pre-quantize), replay the hysteresis offline per attempt for
X ∈ {2.5, 5, 7.5, 10, 12.5, 15, 20, 25, 30}% and compute simulated J1 turnover
Σ|Δ$| ratio vs X=0, pooled IS+OOS. **X\* = grid value with ratio closest to 0.50.**
X\* frozen in `band_X.json` before any variant B run. (Offline replay ignores eq-path feedback;
the honest realized turnover reduction of the actual B run is reported in results.)

## PROTOCOL
- Engine: instrumented clone (`j1_engine.py`) of `v22/engine_v22.py` (micro-ORB v2.2 semantics),
  observation-only except the J1-band hook (cfg `j1_band`, default 0 = off).
  **Acceptance**: with hooks off, (out, end, attempts, t, micro) must be IDENTICAL to
  `engine_v22.run_funnel` for every cohort, and match the committed
  `v22/tables/challenge_cohorts_v22.csv` row-for-row. Cash-conservation identity asserted
  per attempt (1e-6), as in v2.2.
- Cohorts: `config_v22.WINDOWS` (IS 2013-10-01→2019-12-31, OOS 2020-01-02→2026-02-25),
  step 7, wall 91d, retries — exactly the v2.2 contractual grid. All arms use identical starts
  (paired).
- CFG: `config_v22.CFG_CHALLENGE` verbatim; variants touch ONLY {WT J1 column, j1_band, vm(iso)}.
- Challenge-only study: the funded stage and its spec are untouched; EV uses the v2.2
  contractual funded value (VAL) as a constant across arms.

## METRICS per run (vs baseline, paired per cohort)
- Δp pooled / IS / OOS (pp), CI; Δattempts; Δmedian time-to-funded (funded cohorts).
- ΔEV = Δ(p × VAL − attempts × FEE), VAL = v2.2 contractual funded value (from the v2.2
  commit; if absent, fallback v2.1 $1,204 — flagged), FEE = $96.
- Δbust: per-cohort count of bust outcomes (bust_floor + bust_daily) across attempts; also
  attempt-level bust share (descriptive).
- Monday-gap exposure (J1 is weekend-held; weekend-held legs = gold + J1 by construction):
  (a) per-cohort count of busts whose breach day follows a ≥3-calendar-day gap
  ("Monday busts", engine's own weekend criterion);
  (b) J1 weekend-gap P&L on those breach days: pos_J1_heldover × (day_open/prev_close − 1),
  per-cohort sum (the $ exposure the decision rule guards);
  (c) descriptive: weekday split of busts, per-leg breach-day P&L.
- Margin: pre-cap need/equity at rebalances (17:35 & 22:05 snapshots, v2.1 convention):
  p50 / p99 / bind-rate (need > 0.60×eq).
- Realized risk shares: per-leg variance share via covariance decomposition
  share_k = cov(pnl_k, pnl_book) / var(pnl_book) on day records (+ notional shares, ×eq).
- Turnover: J1 executed $-turnover/day, J1 cost drag $/day (attributed), book drift $/day.
- CIs: paired block bootstrap on per-cohort deltas, blocks of 10 consecutive cohorts,
  3,000 draws, seed 23 (v2.1 convention). Report BOTH 90% ([5,95]) and 95% ([2.5,97.5])
  percentile CIs — the decision rule reads the 90% CI. N_eff ≈ n_cohorts/13 reported
  (91d wall / 7d step overlap).

## DECISION RULE (pre-registered, verbatim from mission)
Adopt the single best variant ONLY if Δp pooled or ΔEV is CI-significant (>0 at 90%) without
degrading bust rate or Monday-gap exposure beyond CI noise. Otherwise J1 stays and the study
closes on a documented null.
- Operationalization: "CI-significant (>0 at 90%)" = the paired 90% block-bootstrap CI of
  Δp pooled (or ΔEV) lies entirely above 0. "Without degrading … beyond CI noise" = neither
  the Δbust-count CI nor the Monday-gap-exposure CI (metrics a and b) is entirely on the
  adverse side at 90%. "Single best" = among qualifying variants, highest ΔEV; tie-break Δp.
- NO spec change in this session: a winning variant becomes THE one frozen change of a future
  v2.3 contractual re-run (same protocol as v2.2).

## TRIAL ACCOUNTING
6 pre-registered arms (3 variants × 2 forms), 1 decision, baseline not a trial. Logged to the
v2-program ledger as +6 (pre-registered family, fixed decision rule, no post-hoc additions).

## DELIVERABLES
`J1_STUDY.md` (verdict in first 10 lines), `tables/*.csv`, `plots/tornado.png`,
`band_X.json`, `factors.json`, `baseline_pin.json`, day records parquet per arm.
READ-ONLY outside this folder.
