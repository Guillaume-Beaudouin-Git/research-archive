# PRE-REGISTRATION (frozen before any result) — MR intraday, uncovered axes

**Date frozen:** 2026-08-21. **Isolation:** shared main working dir, zero git HEAD operations
(branch stays `claude/book-idle-escalation`, never switched, never committed). Writes confined to
this folder. Interpreter: `/usr/bin/python3`.

**Mandate:** continue the exhaustive intraday-MR sweep on the FTMO universe, covering ONLY the
axes the existing 396-cell grid (`mr_intraday_grille_2026-08/`) declared uncovered in its own §6/§7:
trailing stops, wider symmetric brackets (2x/3x ATR), sub-5-minute bars, plus two axes named in
this mandate that no prior study opened for this exact mechanism: inter-index spread/ratio/basket,
and staggered (pyramided) entries. Method unchanged from the prior grid: **read the distribution
of t-stats, do not chase a winner.** Compare to the max-order-statistic of N draws from N(0,1).

## 0. What already exists — READ FIRST, DO NOT RE-RUN

Read in full before designing a cell: `mr_intraday_grille_2026-08/PREREGISTRATION.md` (§0, prior
studies) and `mr_intraday_grille_2026-08/RAPPORT.md` (§0-§7, results + declared gaps).

**Combined prior N ≈ 1,339 cells** (943 from five 2026-06/07/08 studies + 396 from the grid this
session extends). Verdict of the 396-cell grid: **dead**, mean gross t = −1.21, only 1/396 clears
t>2.5 (vs ≈2.5 expected under iid noise), and the negative skew is now understood to be **mostly a
backtest-engine artifact**: `engine/backtest.py`'s `sl_first_on_tie=True` convention manufactures
t as extreme as −4 to −9 on a **tight (≤1.5×ATR), short-hold (<5 bar) symmetric bracket**, proven
on a pure i.i.d. random walk (t −1.4 to −4.1, 5 draws) and a 450-draw matched-autocorrelation
placebo (0/450 positive, mean t −4.1 to −5.2). This is the single most important design constraint
for this session: **any cell reusing that tight-bracket shape inherits an uninterpretable number
unless resolved at finer (M1) resolution or explicitly benchmarked against a matched placebo of
the same geometry, never against zero.**

**Also checked before designing the spread axis**: `pairs_cointegration_2026-08/` already measured
all C(4,2)=6 pairwise index spreads (US500/US100, US500/US30, US500/GER40, US100/US30,
US100/GER40, US30/GER40) at three constructions (Gatev-distance 1:1 normalised-price ratio, static
OLS beta, dynamic beta), all failing the session half-life gate (min 1,893 min vs an 8-hour/480-min
gate — see `RESULTS.md` lines 96-111), and found the two-sided legs of the index pairs are
**asymmetric in the direction of drift, not reversion** (US100/GER40: high-side leg t −7.68,
low-side leg t +5.82 — L27 confirmed: a cointegrated spread inherits the relative-outperformance
drift of its legs). **Pairwise index ratio/cointegration spread is therefore CLOSED — not re-run
here.** What that study never built is a **basket-relative** (multilateral, one-vs-three) spread —
a genuinely different construction (no pairwise hedge ratio, no OU fit) — which is the only spread
variant this grid adds.

Also checked: `mr_intraday_grille_2026-08/RAPPORT.md` §7 explicitly flags "a wider *symmetric*
bracket" and trailing stops as not yet run, and its own §6 (carried from PREREGISTRATION §6) lists
scaled/pyramided entries and sub-5-minute bars as declared-out-of-scope-for-that-grid. This session
picks up exactly those four items, plus the basket-spread axis named directly in this mandate.

## 1. Universe, data, house rules (unchanged from the prior grid)

Same 9 instruments, same `data/deep_history_utc/*_M1.csv` (true UTC), same session windows
(indices 13:30-20:00 UTC, FX 07:00-16:00 UTC, metals 12:00-20:00 UTC), same measured costs (§2 of
the prior PREREGISTRATION, reused verbatim — US100 1.045bps, GER40 1.017bps, US500 1.07bps (derived),
US30 0.86bps (derived), EURUSD 0.313bps (derived), GBPUSD 0.338bps (derived), USDJPY 0.379bps,
XAUUSD 2.037bps, XAGUSD 7.05bps (derived)), same recalibrated L33b floor (**gross/trade > ≈1.4bps**,
never the discredited 2.2bps-blanket-derived ">3bps"). Held fixed throughout: delay+1 execution,
daily vol-targeting (63-bar-equivalent rolling realized vol, shifted 1 bar, cap 3x), intraday-flat
(no entry within the block's own H-bar backstop of session end), HAC lag-6, two-sided reporting
mandatory (L25), gross-first-at-zero-cost (constraint #5).

Code reuse: `dataload.py` and `engine_lib.py` from `mr_intraday_grille_2026-08/` are imported
read-only (not modified, not duplicated) for the shared conditioner/entry/vol-target/metrics
primitives; `yt_strategy_replications/engine` (tracked shared library) supplies indicators, the
15-min/60-min-resolution bracket backtester, and HAC/DSR/fold stats. All NEW code (M1 path
resolution, trailing-stop walker, basket-spread construction, staggered-entry episode tracker)
lives only in this folder.

## 2. The critical design constraint — M1 resolution for bracket/trailing axes

Per the mandate's explicit instruction: `audit_moteur_bracket_2026-08/` (the dedicated M1-resolver
project referenced in the mandate) **does not exist yet** in this repo (checked at freeze time,
2026-08-21, both by direct path and by repo-wide filename search — confirmed absent). This session
therefore builds its own minimal M1 resolver (`m1_resolve.py`), used ONLY for Axis A (wider
symmetric brackets) and Axis B (trailing stops) — the two axes whose exit depends on intrabar
tie-break. Design, frozen before any cell is run:

- The entry decision, direction, and sl/tp (or trail) DISTANCE are still computed on 15-min bars
  (identical conditioner machinery to the rest of the grid) — only the **exit resolution** walks
  forward through the session-filtered 1-minute series (`dataload.build(sym, bar="1min")`, cached,
  read-only reuse of the prior grid's session-filter/cost pipeline) starting at the exact entry
  minute, checking sl/tp (or the trailing level) bar-by-bar in real chronological order for up to
  `W = H_bars15 × 15` minutes (`H_bars15 = 8`, i.e. W = 120 minutes — the SAME economic backstop
  used everywhere else in this grid, just expressed in native M1 units for the walk). If neither
  barrier is touched inside W minutes, the trade exits at the close of the W-th minute (reason
  "time"), exactly mirroring the 15-min engine's own `max_hold` convention.
- Same-MINUTE ties (both barriers touched inside the identical 1-min bar — expected to be rare)
  are still resolved stop-first, for consistency with the shared engine's own convention; the
  point of M1 resolution is to shrink the FREQUENCY of ties, not to change the tie-break rule
  itself.
- A cell that entered with fewer than `W` minutes of 1-min data remaining before its own data
  file's end is dropped (negligible, end-of-sample edge only).
- **Supplementary diagnostic (not a full 450-draw placebo — budget-scoped):** one representative
  instrument (US100) is re-run through the M1 resolver on (a) a pure i.i.d. Gaussian random walk
  at 1-min resolution and (b) a block-shuffled (Politis-Romano, mean block 20 min) real 1-min
  return series, for the 1x-ATR symmetric-bracket cell — to check how much of the previously
  measured artifact (t −4 to −9 at 15-min resolution) survives once the exit is resolved at true
  M1 granularity. This is diagnostic context for reading Axis A/B, not a family-wide placebo.

## 3. Axis definitions — the grid (frozen)

### Axis A — Wider symmetric brackets, M1-resolved (27 cells)
Conditioner: SMA20 z-score of close, z0=2.0, entry=CROSS (the grid's own canonical cell, unchanged,
to isolate the bracket-WIDTH axis cleanly). ATR20 computed on 15-min bars. Symmetric bracket
sl_mult=tp_mult ∈ **{1.0, 2.0, 3.0} × ATR20**. The 1.0x cell is included deliberately: it is the
M1-resolved counterpart of a cell already measured (15-min-resolved) in the prior grid, and the
gap between the two numbers is itself a finding (how much of the prior −1.21 mean was tie-break
artifact vs how much survives at true resolution). H backstop = 8 bars-equivalent = 120 min.
9 instruments × 3 multiples = **27 cells**.

### Axis B — Trailing stop, M1-resolved (18 cells)
Same conditioner/entry as Axis A. Trailing distance trail_mult ∈ **{1.0, 2.0} × ATR20**, NO fixed
take-profit (classic trailing design — let winners run). Initial stop = entry_px ∓ trail_dist;
trails favourably only (never loosens) using the running high (long) / low (short) of the M1 path.
H backstop = 120 min (same economic cap as everywhere else — if not stopped out, exit at the close
of the 120th minute, reason "time"). 9 instruments × 2 trail multiples = **18 cells**.

### Axis C — Sub-5-minute bars (36 cells)
Frequencies: **1-min and 3-min** (both sub-5-minute, per the mandate's own wording). Conditioner:
SMA20 z-score of native-bar close, z0=2.0, entry=CROSS — the one canonical form already run at
15-min AND 60-min, extended here to complete the bar-frequency axis across four frequencies.
Exit ∈ {ATR_BRACKET_SYM 1.0x (native-bar resolution — this IS M1 for the 1-min case, and is
explicitly labelled artifact-exposed-but-untested for the 3-min case since 3-min bars are coarser
than the M1 resolver built for Axis A/B), TIME_ONLY (clean, tie-break-insensitive, the primary
read for this axis)}. H backstop = 8 BARS (native units: 8 minutes at 1-min, 24 minutes at 3-min)
— an 8-bar backstop, not an 8×15-minute one, to stay the fair native-bar equivalent of the H=8
convention used at every other frequency in this grid. 9 instruments × 2 freq × 2 exits =
**36 cells**.

### Axis D — Basket-relative index spread (16 cells)
Scope: the 4 indices named in the mandate (US100, US500, US30, GER40) — NOT the already-closed
pairwise ratio/cointegration axis (§0). Construction: 15-min log-returns per index, session-
filtered; `basket_return_i(t)` = equal-weight average of the OTHER 3 indices' returns at t;
`spread_level_i` = cumulative sum of `(own_return - basket_return)` — a synthetic one-vs-three
relative-performance index, never built before in this repo for this mechanism. Conditioner:
z-score of `spread_level_i` vs its own rolling SMA(k), k ∈ {20, 50}, z0=2.0, entry=CROSS (canonical,
unchanged). Exit ∈ {TIME_ONLY H=8 (primary, clean), BRACKET using 1.0× the rolling std of the
spread's own bar-to-bar increments as a vol proxy (flagged **PROVISIONAL** — a synthetic combined
series has no real intrabar high/low to M1-resolve; reported only as a labelled secondary check,
never promoted on its own)}. Two-sided reporting = "long index_i / short basket" vs "short
index_i / long basket". 4 instruments × 2 k × 2 exits = **16 cells**.

**Pre-registered expectation for Axis D, stated before running:** given `pairs_cointegration_2026-08`
already found index-pair spreads exhibit drift (momentum), not reversion, in their two-sided legs,
the honest prior for this differently-constructed (multilateral, not pairwise) spread is the same:
**expect drift-asymmetric legs, not a reversion edge.** Run anyway because the construction is
genuinely new (never tested), not because the prior expects a different answer.

### Axis E — Staggered (pyramided) entries (18 cells)
Conditioner: SMA20 z-score (identical to the grid's canonical cell). Baseline for comparison — the
single full-size CROSS entry at z0=2.0 with TIME_ONLY H=8 exit — is **already measured** in
`mr_intraday_grille_2026-08`'s Block 3 (`TIME_ONLY_H4`/`H16`, and Block 2/entry-logic for the
z0=2.0 CROSS form itself); it is **cited, not re-run**, to avoid duplicating a cell. New variants:
- **SCALE_2STEP**: half-size entry when |z| first crosses 1.0σ (reversion direction), remaining
  half added if/when |z| extends to 2.0σ while the episode is still open in the same direction;
  if the second rung never fires, the episode carries only the half-size fill.
- **SCALE_3STEP**: thirds at |z| crossing 1.0σ, 2.0σ, 3.0σ respectively, added only while the
  deviation keeps extending in the same direction; unfilled rungs simply add no size.
Exit: TIME_ONLY, H=8 bars measured from the FIRST fill (same time-stop convention as the rest of
the grid — deliberately tie-break-insensitive, since this axis isolates entry SIZING, not exit
mechanics). Return accounting: size-weighted average of each filled tranche's own directional
return (not an average-entry-price approximation). 9 instruments × 2 variants = **18 cells**.

**Grand total: 27+18+36+16+18 = 115 new cells.** New combined N ≈ 1,339 + 115 = **1,454**.

## 4. Gates (frozen, not renegotiated after seeing a number)

1. Gross first, cost zero. Any cell with gross-both HAC-t ≤ 0 is reported dead, not cost-tested.
2. Two-sided (L25): long-leg and short-leg HAC-t always reported separately; one-sided flagged
   `ONE_SIDED — beta trap candidate`, never promoted.
3. Distribution is the primary deliverable: the 115 new gross-both t-stats are read as a histogram
   against (a) the closed-form/Monte-Carlo expected max of 115 iid N(0,1) draws, and (b) the
   Axis-A/B M1-resolution diagnostic in §2. A single best cell is never reported as a finding by
   itself.
4. Net (measured/derived cost, §1). No blanket net-Sharpe/DSR threshold "passes" a single cell —
   Šidák/DSR correction at the honest cumulative n=1,454 is applied only if any cell clears gates
   1-2 by a wide margin (mirrors the discipline in `mr_intraday_grille_2026-08` §4.4).
5. Walk-forward (5 expanding folds) reported as a column for every cell; not a per-cell gate given
   the pre-registered null expectation (§5).
6. **Recalibrated L33b floor** (≈1.4bps gross/trade) applies to any candidate before any promotion
   claim, exactly as in the prior grid.

## 5. Pre-registered expectation (honest prior, before running anything)

Given the 396-cell grid's own finding — every conditioner axis already tried dies at the same rate,
metals die at the same rate as indices/FX, and the ONE candidate that cleared a bare significance
bar died on cost/DSR/Šidák — the expected outcome here is **also a null**, with two specific
sub-predictions stated in advance:
- **Axis A/B (M1-resolved)**: the mean t should move CLOSER TO ZERO than the 15-min-resolved
  1x-bracket cells reported in the prior grid (removing tie-break drag), but should NOT flip
  positive — consistent with §3's finding that even the artifact-free exit-logic block (mean t
  −0.26 to +0.33) was flat, not positive.
- **Axis D**: expect the same drift-not-reversion asymmetry already found in pairwise index
  spreads (`pairs_cointegration_2026-08`), extended to the multilateral basket construction.
A clean confirmation of this prior — extended now to wider brackets, real trailing stops,
sub-5-minute execution, a genuinely new spread construction, and pyramided entries — is the
pre-registered, useful, anticipated result. Any cell beating this prior by a wide margin gets the
full multiplicity treatment (gate 4) before any claim is made.

## 6. What this grid does NOT cover (declared before running)

- Everything already declared out of scope in `mr_intraday_grille_2026-08/PREREGISTRATION.md` §6
  that this session doesn't pick up: Bollinger-band-width as its own axis, RSI windows beyond
  14/21, range-based-std normalisation, full cointegration pairs beyond the 171 already tested,
  non-USD FX crosses, non-metal commodities, regional indices absent from `deep_history_utc`,
  volatility-regime conditioning of any new cell here.
- A true M1-resolved reading of Axis D's bracket variant (the synthetic basket-spread series has
  no native intrabar high/low — building one would require constructing a synthetic M1 basket
  path, a nontrivial separate project; the bracket variant here stays PROVISIONAL by design).
- Trailing stops on anything other than a fixed ATR-multiple trailing distance (e.g. a
  volatility-adaptive or ratchet-step trailing rule) — only the plain ATR-trailing form is tested.
- Staggered entries with an asymmetric ladder (e.g. front-loaded 50/30/20 sizing) — only equal-
  split 2-step/3-step ladders are tested.
- Basket-relative spread for FX or metals (only the 4 indices named in the mandate are tested;
  a 10-instrument FX basket or a 2-instrument metals "basket" would be a different, separately
  worth-scoping axis).
- A full 450-draw placebo battery for Axis A/B at M1 resolution (§2's diagnostic is scoped to one
  instrument, one cell shape, for budget reasons) — a dedicated M1 placebo battery is the natural
  next step if Axis A/B numbers look ambiguous.
- Cross-instrument portfolio construction / combining any surviving cells into a book — out of
  scope for a cell-level sweep.

Frozen. Execution and outputs follow in `m1_resolve.py`, `dataload_ext.py`, `run_axis_A_bracket.py`,
`run_axis_B_trailing.py`, `run_axis_C_subminute.py`, `run_axis_D_basket.py`,
`run_axis_E_staggered.py`, `run_all.py`, `grille_resultats.csv`, `RAPPORT.md`.
