# PRE-REGISTRATION (frozen before any result) — Intraday mean-reversion, exhaustive axis grid

**Date frozen:** 2026-08-21. **Isolation:** shared main working dir, **zero git HEAD operations**
(branch stays `claude/book-idle-escalation`, never switched). Live book untouched. Writes are
confined to this folder. Interpreter: `/usr/bin/python3`.

**Mandate:** the family is *intraday mean-reversion on the FTMO universe*. The method is not "find
the best variant" — it is "sweep the axes and read the DISTRIBUTION of t-stats." A real mechanism
shows a whole neighbourhood of positive, robust variants; a dead mechanism shows a t-distribution
indistinguishable from the max-order-statistic of N draws from N(0,1). Multiple testing is the
measuring instrument, not a nuisance to correct away after the fact.

## 0. What already exists — READ FIRST, DO NOT RE-RUN

Before designing a single cell, the repo was searched for prior intraday-MR work. Three studies
already measured this family, at real rigor, on the CORRECT exchange-clock timezone (L56), with
proper two-sided (L25) and paired-baseline (L58) discipline:

| study | scope | cells | verdict |
|---|---|---:|---|
| `yt_strategy_replications/intraday_mr_ftmo/` (2026-06-20) | US100/US500/US30/GER40 + EURUSD/GBPUSD/USDJPY, 15-min, z-score(SMA) reversal, ATR-bracket exit, z0∈{1.5,2,2.5}×H∈{4,8,12}, momentum-flip, gap-fade | ~13 | **FALSIFIED** — gross both SR ∈[−0.49,−0.04], momentum-flip also negative, gap-fade dead. Only positive leg (US500 long) is an L25 beta trap. |
| `Multi_Asset/research/active/mr_timezone_repair_2026-08/` (2026-08-01) | US100/US500/US30/GER40, 5/15/30-min, logics {sma20_z, ema20_z, vwap_z, rsi14, range_fade}, delay+1 entry AND exit (no stops/brackets, by design), L58-paired baseline, plus a closing-auction B1 grid (153 cells + falsification battery) | 579 | **REJECTED** — 0/384 MR cells at t>2.5 (46 at t<−2.5); B1 closing-window: US indices sign-flipped (continuation, not reversion), GER40 has a real gross effect (3.52bps, t 3.68) but it lives entirely inside the 5-min Xetra auction and dies on a 5-min entry delay (0.56bps, t 1.00, sub-cost). |
| `Multi_Asset/research/active/mr_stress_conditional_2026-08/` (2026-08-02/03) | same 4 indices, same archived grid, conditioned on stress state (VIX/realized-vol/dispersion quintiles) | 180 | **REJECTED** — quantile profile is FLAT (share of positive gradients 0.506, mean Spearman ρ +0.006); the one candidate that survives permutation (GER40×rsi14) dies on multiplicity (DSR 0.101/0.017) and n=1/4 instruments. |
| `Multi_Asset/research/active/pairs_cointegration_2026-08/` (2026-08-03) | 171 pairs across 19 FTMO macro instruments, cointegration + OU half-life | 171 | **REJECTED mechanically** — 0/171 pairs has a session-compatible half-life (shortest 1,588 min vs an 8-hour gate); only AUDUSD/USDCAD has a real gross edge, killed by the CFD swap bill, not the mechanism. |
| `Multi_Asset/research/active/gross_surface_map_2026-08/` (2026-08-06) | 19 instruments incl. FX/metals/oil/copper, `S3_MA` = deviation from a 20-**day** MA at the same local hour, hourly buckets × 5 horizons | ~2,184 unconditional + 6,511 conditional | **Structure exists (4.42% of cells |t|>2.5 vs 1.65% placebo) but shortlist is EMPTY** — 3/6,511 clear `gross>3×cost`, all at |t|≤2.0. Median gross/cost of clean hot spots = 0.38, independently replicating L43 (0.36) outside FX. |

**Combined prior N ≈ 943 cells**, all on indices except the pairs study (macro-wide) and the
surface map (19 instruments, but a **daily**-MA deviation at hourly resolution — a related but
distinct mechanism from same-session intraday z-score MR). Bottom line the new grid must respect:
**do not re-run SMA/EMA/VWAP-zscore or RSI14 z-score MR on US100/US500/US30/GER40 15/30-min with
plain delay+1 exits — it is already measured, 0 survivors.** The new grid below is designed to be
**additive**: instruments never tested for this specific mechanism (metals), conditioner types
never tried (volume-weighted / inverse-vol-weighted / session-anchored means, percentile rank),
an exit-logic axis nobody has swept (ATR-bracket / mean-revert-target / fraction-of-path — the
prior MR studies deliberately used delay+1 with **no** stops or brackets), an entry-logic axis
(confirm-on-return, reversal-candle) nobody has swept, and a bar-frequency extension to 60-min
(multi-session window). The spread/relative-value axis the mandate names is **already closed
mechanically** by `pairs_cointegration_2026-08` (half-life gate) — it is not re-run here; it is
cited as answered.

## 1. Universe and data

9 FTMO-tradable CFD instruments, `data/deep_history_utc/*_M1.csv` (true UTC, audited,
`MANIFEST.md`), read-only:
- **Indices:** US100, US500, US30, GER40 (already heavily tested — included here only for the
  genuinely new axes: new conditioners, new entry/exit logic, 60-min bar).
- **FX:** EURUSD, GBPUSD, USDJPY (z-score+ATR-bracket already tested in `intraday_mr_ftmo`; new
  conditioners/entries/exits/frequencies are new here).
- **Metals:** XAUUSD, XAGUSD — **never tested for this mechanism in any prior study.** Genuinely
  new instrument class for intraday same-session MR.

**Session windows (local liquid hours, UTC on the true-UTC series, no DST games needed at 15-min/
60-min resolution since sessions are wide):**
- Indices: 13:30–20:00 UTC (US cash overlap, unchanged from `intraday_mr_ftmo`).
- FX: 07:00–16:00 UTC (London/NY overlap, unchanged).
- Metals (XAU/XAG): 12:00–20:00 UTC (COMEX pit-hours/NY overlap — the peak-liquidity window per
  the overnight-gold research already in the repo; this study only touches the **intraday**, not
  the overnight, part of the gold/silver clock).

**Bar frequencies:** 15-min (primary, matches existing caches/conventions) + 60-min (new — the
"multi-session window" extension of the window axis; a 20-60 bar lookback at 60-min spans well
beyond one session).

**Clock check (cheap, done before any performance number):** `dataload.py` reports median/​p90
intrabar range and volume-per-bar-per-hour profile for each instrument/frequency at cache-build
time; a flat or clearly-mistimed liquidity profile (e.g., peak volume outside the declared session
window) fails the sanity check and blocks the run. `deep_history_utc` is independently audited as
true UTC (`MANIFEST.md`, seam-gate PASS on US100/US500/GER40) and this exact series is what two
prior sessions (`mr_timezone_repair_2026-08`, `gross_surface_map_2026-08`) already tick-verified
against EET-mislabeled panels — this study inherits that verification rather than repeating it,
and only checks the volume-profile sanity gate as a cheap corroboration.

This is a time-series (per-instrument) sweep, not a cross-sectional ranker — the CLAUDE.md N≥30
instrument rule targets XS strategies and does not apply here (same disclaimer as the prior MR
studies).

## 2. Costs — measured, never the repo's blanket constants

Per constraint #2 of the mandate: **do not use `phase0_rt_cost_bps.csv`'s 2.2bps blanket index
cost** (it is 2.1× too expensive per the 2026-08-19 remeasurement) and **do not use the raw
`deep_history_utc.spread` column alone** (zero-inflated on FX, `L60`/`COST_AUDIT.md`).

**Directly measured, 2026-08-19 (given):** US100 = 1.045 bps, GER40 = 1.017 bps, XAUUSD = 2.037
bps, USDJPY = 0.379 bps RT.

**Derived for the remaining 5 instruments (transparently, not measured at the same rigor —
flagged in every output table):**
- US500, US30: no fresh 2026-08-19 point exists. `COST_AUDIT.md` (2026-07-31) gives US500=1.82,
  US30=1.47, GER40=1.73 on the same methodology that gave GER40=1.017 today (ratio 0.588). Apply
  the same 0.588 ratio (average of the only two indices with both an old and a new point — here
  only GER40 has both, so the ratio is single-anchored; reported as such): US500 ≈ 1.82×0.588 =
  **1.07 bps**, US30 ≈ 1.47×0.588 = **0.86 bps**.
- XAGUSD: `gross_surface_map_2026-08` measured XAGUSD ≈ 6.37 bps RT on 2026-08-06 with its own
  spread×tick+slippage method; the one metal with both an old (`COST_AUDIT.md` XAUUSD=1.84) and a
  new (today's 2.037) point gives ratio 1.107. Apply it: XAGUSD ≈ 6.37×1.107 = **7.05 bps**.
- EURUSD, GBPUSD: no direct measurement anywhere (FX spread column is zero-inflated, catalog-only).
  `phase0_rt_cost_bps.csv` catalog gives EURUSD=1.127, GBPUSD=1.217, USDJPY=1.364 (catalog ratios
  preserved); the one FX pair with a real 2026-08-19 point is USDJPY=0.379, ratio 0.379/1.364 =
  0.278 vs catalog. Apply uniformly: EURUSD ≈ 1.127×0.278 = **0.313 bps**, GBPUSD ≈ 1.217×0.278 =
  **0.338 bps**.

These derived numbers are **estimates by extrapolation**, reported as such, and used only to
populate the net-SR column; **the verdict rests on the gross column** (constraint #5) — no
derived-cost uncertainty can flip a verdict decided at cost zero.

**Recalibrated L33b gate:** the mandate asks to recompute the ">3bps gross" rule at the real cost.
At ≈0.3–2.0 bps RT across this universe, the honest floor is **gross/trade > 1.4bps** (≈3× the
higher end of the index/metal costs, ≈4-5× the FX costs) — reported per-instrument as
`gross_bps_per_trade / (3 × cost_rt)`, not a single constant.

## 3. Conditioner axes — the grid

Held fixed across the whole grid: **delay+1 execution** (signal at bar close *t*, act at open
*t+1* — hard rule, enforced by `engine.backtest`), **daily vol-targeting** (63-bar-equivalent
rolling realized vol, shifted 1 bar, cap 3×, reused from `signals.vol_target_scale`),
**intraday-flat** (no entries within `H` bars of session end — swap-free by construction, the only
escape from L36), **HAC lag-6** significance, **two-sided reporting mandatory** (long-leg and
short-leg HAC-t always reported separately, L25).

### Block 1 — New conditioner types × window × threshold (306 cells)
For each of the 9 instruments:
- **1a. VWMA-anchor, ATR-distance:** `(close − VWMA_k) / ATR_k`, k∈{10,20,50}, threshold z0∈
  {1.5,2.0,2.5} → 9 cells/instrument.
- **1b. Inverse-vol-weighted-MA anchor, ATR-distance:** weight_i = 1/ATR_bar_i within the trailing
  window (a bar with high realized range counts less), k∈{10,20,50} × z0∈{1.5,2.0,2.5} → 9/instr.
- **1c. Session-open anchor, ATR-distance:** distance of current close from the session's first
  bar open, z0∈{1.0,1.5,2.0} → 3/instr.
- **1d. Session-VWAP anchor (expanding intraday VWAP), ATR-distance** (distinct normalisation from
  the archived `vwap_z`, which used a rolling-std zscore — here the distance is ATR-normalised):
  z0∈{1.0,1.5,2.0} → 3/instr.
- **1e. Prior-session-close anchor, ATR-distance** (an intrabar, continuously-monitored version of
  the archived open-only gap-fade): z0∈{1.0,1.5,2.0} → 3/instr.
- **1f. Price-level sweep:** anchor=SMA20, deviation=z-score (the one canonical form already
  tested on CLOSE) but the compared level ∈ {OPEN, TYPICAL=(H+L+C)/3, MEDIAN=(H+L)/2}, z0=2.0
  fixed (isolating the price-level axis, not re-sweeping the threshold) → 3/instr.
- **1g. Percentile-rank conditioner:** rolling percentile of close in window k∈{20,50}, thresholds
  {≤5/≥95, ≤10/≥90} → 4/instr.
- Total: (9+9+3+3+3+3+4) × 9 instruments = **306 cells**.

### Block 2 — Entry-logic axis (27 cells, new)
Fixed conditioner SMA20+z-score, z0=2.0, exit=ATR-bracket symmetric 1:1×ATR, H=8 (backstop).
Entry ∈ {**CROSS** (fire the bar the threshold is breached — the archived convention), **CONFIRM**
(fire one bar later, when the z-score has started coming back through the threshold — i.e. wait
for the reversal to already be underway), **REVERSAL_CANDLE** (fire only if the extreme bar itself
closed back toward the mean from its own open, a cheap reversal-candle proxy)} × 9 instruments.

### Block 3 — Exit-logic axis (45 cells, new — the axis every prior MR study deliberately skipped)
Fixed conditioner SMA20+z-score, z0=2.0, entry=CROSS. Exit ∈ {ATR-bracket asymmetric (sl=1.0×ATR,
tp=1.5×ATR, H=8 backstop), **mean-revert-target** (tp = distance from entry price to the anchor
value at signal time, sl=1.0×ATR, H=8), **fraction-of-path** (tp = 0.5×distance-to-anchor, sl=
1.0×ATR, H=8), time-stop-only H=4 (wide sl/tp so the time-stop binds), time-stop-only H=16} × 9.
(The symmetric-ATR-bracket/H=8 cell is already produced in Block 2's CROSS row — not duplicated.)

### Block 4 — Bar-frequency extension (18 cells, new)
Fixed conditioner SMA-z-score, z0=2.0, CROSS/ATR-bracket-symmetric-H=8, at **60-min** bars, k∈
{20,50} (20×60min=20h and 50×60min=50h, both genuinely multi-session lookbacks) × 9 instruments.

**Grand total: 306+27+45+18 = 396 new cells**, none of which duplicate a cell already measured by
the five prior studies in §0.

## 4. Gates (pre-registered, not renegotiated after the fact)

1. **Gross first, cost zero (constraint #5).** Any cell with gross-both HAC-t ≤ 0 or gross both
   SR ≤ 0 is reported and not carried further — no cost model can rescue a negative gross.
2. **Two-sided (L25).** Both legs' HAC-t reported for every cell; a one-sided "MR" (one leg
   negative or non-significant) is flagged `ONE_SIDED — beta trap candidate`, never promoted.
3. **Multiplicity is read as a DISTRIBUTION, not filtered post-hoc for a winner.** Primary
   deliverable: histogram of the 396 gross-both t-stats, compared to (a) the closed-form expected
   maximum of 396 iid draws from N(0,1) [`E[max] ≈ Φ⁻¹(1 − 1/396) ≈ 3.32`, refined by Monte-Carlo
   simulation of the exact order statistic], and (b) an empirical placebo: for each cell, the same
   conditioner/entry/exit machinery is re-run on a block-permuted (autocorrelation-preserving,
   mean geometric block length 20 bars, Politis-Romano) version of the SAME instrument's price
   series, producing a matched-null t for every one of the 396 cells. The **shape** of the real
   distribution vs both nulls is the verdict; a single best cell is never reported as a finding on
   its own.
4. **Net (constraint #2 costs).** Reported for every cell that clears gate 1, at the calibrated
   native cost (§2). No blanket net-Sharpe/DSR threshold is applied to a single cell as a "pass" —
   consistent with gate 3, the family-level verdict is read off the distribution, and Šidák/DSR
   correction for n_trials=396 (plus the ≈943 already spent by the five prior studies, reported
   for context, not re-charged against this grid's own local budget) is applied only if any cell
   individually clears gates 1–2 by a wide margin.
5. **Walk-forward** (5 expanding folds, `engine.stats.fold_metrics`) reported for every cell as a
   column; not a per-cell gate given the expected outcome, but available for any cell that would
   otherwise look promising.

## 5. Pre-registered expectation (honest prior, stated before running anything)

Given 943 cells already measured on this exact mechanism family (indices, all with 0 gross
survivors at t>2.5, one flagged-but-rejected exception on DSR/one-sidedness) and the surface-map's
independent finding that intraday conditional asymmetry across 19 instruments including FX/metals
tops out at gross/cost=0.38 with an empty >1 shortlist — **the expected outcome of this grid is
also a null: a t-distribution indistinguishable from (or narrower than) the matched placebo, no
cell clearing gross/trade > recalibrated 1.4bps gate, and the metals instruments (the one genuinely
untested asset class) behaving like everything else tested to date.** A clean confirmation of this
prior, extended to metals and to the exit/entry/conditioner axes nobody had swept, is the
pre-registered, useful, and fully anticipated result. Any cell that appears to beat this prior by a
wide margin gets the full multiplicity treatment (gate 3) before any claim is made.

## 6. What this grid does NOT cover (declared before running, so it can be added later)

- Sub-5-minute bars (tick/1-min execution) — the prior studies note this changes the cost gate
  qualitatively (finer execution / lower-cost venue), out of scope for a retail-CFD study.
- Trailing-stop exits (not vectorizable in the shared `engine.backtest` without a bar-by-bar
  rewrite; left for a dedicated follow-up).
- Pure session-close-only exit with zero stop (the intraday-flat constraint already forces a
  same-session exit; an explicit no-stop-until-close variant is not separately isolated here).
- Scaled/pyramided entries (adding to a position on repeated threshold touches).
- Bollinger-band-width as its own axis distinct from the ATR/z-score distance metrics already
  swept (treated as redundant with z-score threshold sweep, not run separately).
- RSI on windows other than 14/21 (only two RSI windows are in the archived grid Block 0 already;
  not re-swept here).
- Range-based std-normalisation distance (`range_fade` logic already exists in the archived grid,
  §0 — not duplicated; if it needs a genuinely different definition, note it as a gap here).
- Full statistical cointegration / OU half-life pairs beyond the 171 already tested in
  `pairs_cointegration_2026-08` — that axis is cited as closed, not re-opened.
- Non-USD-quoted FX crosses (EURJPY, EURGBP, etc.) and non-metal commodities (oil, copper, softs)
  — `gross_surface_map_2026-08` already covers a superset of these for the daily-MA mechanism; this
  study's intraday-session mechanism on them is untested and left for a follow-up.
- Emerging/Asian/other regional indices (UK100, JP225, ASX) — not present in `deep_history_utc`.
- Volatility-regime conditioning of any of the 396 new cells (the mechanism was already shown flat
  under stress-quantile conditioning for the archived indices grid; re-testing it on the new
  conditioners/instruments here would double the grid for a dimension already shown null).

Frozen. Execution and all output files follow in `dataload.py`, `engine_lib.py`, `run_grid.py`,
`grille_resultats.csv`, `RAPPORT.md`.
