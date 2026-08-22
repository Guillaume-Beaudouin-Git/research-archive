# Intraday mean-reversion — exhaustive axis grid — RAPPORT

**Date:** 2026-08-21. **Pre-registration:** `PREREGISTRATION.md`, frozen before any cell was run.
**Grid:** `run_grid.py` → `grille_resultats.csv` (396 rows). **Placebo:** `placebo.py` →
`placebo_results.json`. Interpreter: `/usr/bin/python3`. Isolation: shared main working dir, zero
git HEAD operations, branch stays `claude/book-idle-escalation`.

---

## 0. Verdict in one page

**The family is dead, and — new this session — a large part of *why the grid looks so
lopsidedly negative* turns out to be a measurement artifact, not a market effect. Both facts are
reported, because they answer different questions.**

| # | Question | Answer |
|---|---|---|
| **V1** | Does any axis (new anchors, new entries, new exits, new instruments, new bar frequency) show a real gross edge? | **No.** 396 cells, mean gross t = **−1.21**, median **−1.18**. Only **1/396** clears t>2.5 (vs. **73/396** below −2.5). The positive tail is *at or below* what pure noise produces (iid-expected ≈2.5 cells); the negative tail is ~30× the iid expectation. |
| **V2** | Is the negative skew itself real (markets punish naive fades) or artifact? | **Mostly artifact, and it's now demonstrated, not assumed.** A **pure i.i.d. Gaussian random walk**, with no market structure whatsoever, run through the *identical* canonical cell (SMA20 z-score, CROSS entry, symmetric 1.0×ATR bracket, pessimistic stop-first tie-break, vol-targeted), produces t ∈ [−4.1, −1.4] across 5 draws — and a **450-draw matched-autocorrelation placebo** (real price dynamics, block-shuffled) produces **0/450 positive draws**, mean t ≈ **−4.2 to −5.2**. This isolates the engine's documented *pessimistic same-bar tie-break* (stop wins on ambiguous bars) interacting with a **tight (1×ATR) bracket on a **short** hold (avg 2.8-4 bars)** as a structural drag independent of any genuine mean-reversion. |
| **V3** | Does the ONE candidate that crosses t>2.5 (XAUUSD, MEAN_REVERT_TARGET exit) survive scrutiny? | **No — same conclusion as every prior candidate in this repo's MR programme: flagged, not promoted.** Gross bps/trade = 0.35 (vs a recalibrated 1.4bps floor), DSR = 0.468 (<0.5), net t = **−5.78** at the instrument's own measured cost, and Šidák at the honest combined n≈1,339 (this grid's 396 + the ~943 already spent by five prior studies) requires p<3.8×10⁻⁵ — the cell's own p≈0.0034 misses by two orders of magnitude. |
| **V4** | Do metals (the one genuinely untested instrument class) behave any differently? | **No.** Mean gross t: index −1.28, FX −1.23, metal −1.03 — metals sit inside the same dead range, no asset-class effect. |
| **V5** | Which axis comes closest to "not obviously dead"? | **Exit logic.** Loosening the exit off the tight symmetric bracket (mean-revert-to-target, or pure time-stop) moves the block mean from −1.2ish to **+0.06 / +0.33** — i.e., closer to (but still not clearing) zero, exactly as V2 predicts: remove the tight-bracket tie-break drag and the residual is centred on nothing. |

**Bottom line for the mandate's central question:** the family does not die because of the
z-score conditioner specifically — every new conditioner tried (VWMA, inverse-vol MA, session
anchors, percentile rank, price-level) dies at the same rate, and metals die at the same rate as
indices/FX that were already dead. What *does* move the needle by a full point of t is the exit
mechanic, and that turns out to be mostly a backtest-engine artifact, not alpha. **There is no
live mean-reversion content anywhere in this 396-cell extension, on top of the ~943 cells already
measured in this repo for the same mechanism family.**

---

## 1. What was measured

9 FTMO instruments (US100/US500/US30/GER40, EURUSD/GBPUSD/USDJPY, XAUUSD/XAGUSD), `data/deep_history_utc`
true-UTC M1 resampled to 15-min (primary) and 60-min (Block 4), session-filtered, vol-targeted,
delay+1, intraday-flat. 396 cells across 4 blocks (see `PREREGISTRATION.md` §3 for the exact
definitions — not restated here):

| block | axis | n cells |
|---|---|--:|
| 1a/1b | VWMA / inverse-vol-weighted MA anchor, ATR-distance, k∈{10,20,50}, z0∈{1.5,2,2.5} | 162 |
| 1c/1d/1e | Session-open / session-VWAP / prior-close anchor, ATR-distance | 81 |
| 1f | Price-level sweep (open/typical/median vs the canonical close) | 27 |
| 1g | Percentile-rank conditioner, k∈{20,50}, {5/95, 10/90} | 36 |
| 2 | Entry logic: CROSS / CONFIRM / REVERSAL_CANDLE | 27 |
| 3 | Exit logic: ATR-bracket-asym, mean-revert-target, fraction-50-target, time-only H4/H16 | 45 |
| 4 | Bar-frequency extension: 60-min, k∈{20,50} | 18 |
| **Total** | | **396** |

**Bug caught and fixed before any number was reported:** the first pass annualised the
daily-aggregated P&L series by `bars_per_year` (used correctly elsewhere for the intraday
vol-target rolling window) instead of `252` trading days/year (L47) — inflating every Sharpe by
√(bars/day) (≈√26 for indices). Caught by replicating the known `intraday_mr_ftmo` US100 primary
result (SR −0.40/t −1.52) before trusting a single new number; after the fix the replication is
exact (SR −0.397, t −1.517). **HAC t-stats, DSR, and WF fraction were never affected** (they don't
depend on this annualisation constant) — only the reported Sharpe column was wrong pre-fix.

**Bug caught in Block 4 (60-min):** the intraday-flat no-entry guard (`H_BACKSTOP=8` bars,
calibrated for a 26-36-bar/day 15-min session) blanked out *every* bar of a 6-9-bar/day 60-min
session → **all 18 cells returned 0 trades on the first run.** Fixed by deriving `H_60` from each
instrument's own bars/day (`max(2, bars_per_day // 3)`); re-run gave 1,100-3,600 trades/cell.
Both bugs are left visible in `run_grid.py`'s comments rather than silently smoothed over, per the
project's own culture of documenting what broke, not just what shipped.

**Data-quality note, new this session:** `tick_volume` (used to weight VWMA/session-VWAP/
inverse-vol-MA) is **zero on ~50-55% of resampled 15-min bars** even inside the declared liquid
session for US100 (confirmed: US100 `tick_volume==0` on 55.0% of bars). This is a new instance of
the L60 family (a data-quality caveat already established for `close==high==low` prints and for
the zero-inflated `spread` column) — extended here to the **volume field**. It does not corrupt
the rolling-window anchors (VWMA/inverse-vol-MA over k=10-50 bars almost always has *some*
nonzero-volume bar in the window), but it does starve the **expanding session-VWAP** anchor of
~46% of its bars early in each session (safe fallback: those bars are converted to a large
sentinel distance and never fire a false signal, but the effective sample for that one anchor
type is smaller than its raw bar count suggests).

---

## 2. The distribution — the primary deliverable

```
n = 396         mean(t) = -1.209      median(t) = -1.175      max|t| = 4.847
t > +2.5 :   1 cell    (iid-expected ≈ 2.5)
t < -2.5 :  73 cells    (iid-expected ≈ 2.5)
fraction of cells with gross_t > 0 : 20.7%   (would be ~50% under a fair coin)
mean gross bps/trade across all 396 cells: -0.34 bps
```

**Naive iid-N(0,1) comparison** (20,000 Monte-Carlo draws of max|396 iid standard normals|):
E[max|t|] = 3.17, P95 = 3.81. The observed max|t| (4.85, a *negative* extreme cell) exceeds even
the 95th percentile of pure iid noise (P(max ≥ observed) = 0.0006) — read naively this says "there
is more extreme dispersion here than iid noise would produce." **That reading is correct but
incomplete, and §3 below explains why the excess dispersion is not evidence of a market effect.**
It is also entirely one-sided: the positive tail (1 cell) sits *under* the iid expectation, not
over it — a real edge would show excess density on the side that matters, not only on the side
that doesn't.

Per-block means (worst to least-bad):

| block | mean t | n | t>2.5 | t<−2.5 |
|---|--:|--:|--:|--:|
| 1c session-open | −1.96 | 27 | 0 | 11 |
| 4 bar-frequency (60min) | −1.66 | 18 | 0 | 4 |
| 1g percentile | −1.66 | 36 | 0 | 13 |
| 1d session-VWAP | −1.62 | 27 | 0 | 4 |
| 1e prior-close | −1.31 | 27 | 0 | 4 |
| 1a VWMA | −1.24 | 81 | 0 | 15 |
| 1b inverse-vol MA | −1.18 | 81 | 0 | 15 |
| 1f price-level | −0.95 | 27 | 0 | 1 |
| 2 entry-logic | −0.88 | 27 | 0 | 3 |
| **3 exit-logic** | **−0.26** | 45 | 1 | 3 |

No block is positive on average; no block shows a coherent neighbourhood of positive cells. The
entry-logic block (CROSS/CONFIRM/REVERSAL_CANDLE) is the clearest illustration of "sign
inconsistent across instruments = noise, not mechanism": REVERSAL_CANDLE is the best-looking entry
on US100/US500/GER40 (t +1.12/+1.09/+0.39) but among the *worst* on EURUSD/GBPUSD/XAUUSD/XAGUSD
(t −0.96/−0.80/−1.05/−2.53) — a real entry-timing improvement would not flip sign by instrument.

By instrument class: index mean t **−1.28** (n=176), FX **−1.23** (n=132), metal **−1.03** (n=88).
Metals — the one instrument class never tested for this exact mechanism anywhere in the repo —
land inside the same dead range as everything else; the pre-registered honest prior ("metals
behave like everything else tested to date") is confirmed, not merely un-contradicted.

---

## 3. The mechanical-artifact finding (new, and the most useful output of this session)

This was not planned in the pre-registration as a *result* — it emerged from taking the placebo
step seriously (constraint #8) rather than treating it as a formality, and it changes how the
negative skew above should be read.

**Step 1 — matched-autocorrelation placebo, first pass (block-shuffle mean length 20 bars,
gap-naive):** block-shuffling the whole 15-min return series (Politis-Romano stationary bootstrap)
and re-running the canonical cell (SMA20 z-score / CROSS / ATR-bracket 1:1 / H=8) produced **0/225
positive draws**, mean t = −5.42 — *more* negative than the real data. This could have two
explanations: (a) the placebo construction is flawed, or (b) the mechanism itself is this biased
and real markets merely dilute it. Both turned out to be partially true.

**Step 2 — ruling out a block-length resonance:** re-running at mean block length 100 (≫ the
20-bar signal window, so a shuffle seam rarely falls inside a live rolling window) gave a nearly
identical result (mean t = −4.10, 0/225 positive) — **ruling out** "the shuffle block length
matches the signal window and creates fake seam-triggered extremes" as the driver.

**Step 3 — ruling out cross-session gap relocation:** a session-filtered 15-min series embeds the
overnight/weekend gap in the *first* logret of every session; a naive flat shuffle can relocate
that fat-tailed gap return to a random mid-session position, manufacturing a fake isolated jump
that triggers the z-score entry with no genuine reversion tendency behind it. Re-running with the
shuffle restricted to intra-session continuation returns only (session-open gaps pinned at their
true position and magnitude) gave essentially the **same** result (mean t = −5.23 / −4.16 at block
20/100) — **ruling out** the gap-relocation hypothesis too.

**Step 4 — decisive test: a pure i.i.d. Gaussian random walk**, zero autocorrelation, zero fat
tails beyond the resampled bar-range distribution, no gaps, no real-market structure of any kind,
run through the identical canonical cell: **t = −4.06, −3.35, −2.96, −2.45, −1.43** across 5 draws.
**A structural artifact confirmed at its source, not merely by process of elimination.**

**Mechanism, and why it is a documented engine choice, not a new bug:** `engine/backtest.py`
resolves same-bar stop/target ambiguity with `sl_first_on_tie=True` by default — its own docstring
calls this deliberate: *"we resolve it pessimistically (stop first) by default — the honest
choice."* With `sl=tp=1.0×ATR(20)` and an average hold of **2.8-4.2 bars**, a meaningful fraction of
trades have both barriers inside reach of a single subsequent bar's range — and every such
ambiguous bar counts as a loss under the pessimistic convention, even though a fair (unknowable)
resolution would split them close to 50/50. This is a **real, generalisable property of any short-
hold, tight-symmetric-bracket cell built on this shared engine** — it also silently sat inside the
original `yt_strategy_replications/intraday_mr_ftmo` study's numbers (same engine, same
convention), though that study never had a placebo strong enough to isolate it, because its grid
never varied the exit axis wide enough to see the drag move.

**What this does and does not change about the verdict:**
- It does **not** rescue the family: the *real* data's canonical-cell average (mean t across the 9
  instruments = **−1.25**) is still solidly negative, still shows no instrument with a robust
  positive t, and the exit-logic block (which most directly removes this drag) still averages a
  flat, not positive, **−0.26 to +0.33**.
- It **does** mean the negative skew in §2 should not be read as "the market punishes naive
  fades" — a large share of it is mechanical. The comparison that actually matters is real vs.
  placebo, not real vs. zero: **real data (mean canonical t −1.25) is markedly LESS negative than
  the matched placebo (mean −4.1 to −5.2, 0/450 draws ever positive).** Real intraday prices do
  provide *some* genuine cushioning against this drag (plausibly ordinary bid-ask-bounce / short-
  term liquidity-provision reversion) — enough to move the average by roughly 3-4 points of t —
  but nowhere near enough to flip the sign positive or clear any economic hurdle. This is a
  *stronger* form of the null result than "distribution looks like noise": the real grid is
  measurably better-behaved than noise under the identical mechanism, and it is *still* dead.
- **Practical correction for future sessions using this shared engine:** do not read a negative
  gross Sharpe/t on a **tight (≤1.5×ATR), short-hold (<5 bar)** symmetric bracket as evidence
  against a mechanism without first checking it against a same-mechanism placebo — the tie-break
  convention alone can produce t as extreme as −4 to −9 with zero market content. Wider/asymmetric
  exits, or exits that don't force simultaneous barrier proximity (mean-revert-to-target, time-
  stop-only), are far less exposed to this artifact, which is exactly what Block 3's flatter mean
  (−0.26 vs the grid's −1.21) already shows empirically.

---

## 4. The one cell above t > 2.5 — full scrutiny

`XAUUSD · 15min · SMA20+z-score(2.0) · CROSS entry · MEAN_REVERT_TARGET exit (tp = distance to
SMA20 at signal time, sl = 1.0×ATR20, H=8 backstop)`:

| metric | value |
|---|--:|
| n_trades | 11,023 |
| gross SR / t | +0.649 / **+2.928** |
| long leg SR / t | +0.447 / +1.967 |
| short leg SR / t | +0.470 / +2.096 |
| gross bps/trade | **+0.348** |
| DSR (n_trials=396, this grid only) | **0.468** |
| WF (5 folds) | 0.8 (4/5 positive) |
| net SR / t at measured XAUUSD cost (2.037bps RT) | **−1.284 / −5.778** |

**Why it is flagged, not promoted, following the same discipline every prior candidate in this
repo's MR programme has been held to:**
1. **Recalibrated L33b gate** (§ below, ≈1.4bps at this universe's real costs): 0.348bps gross is
   **25% of the floor**, not 3× over it.
2. **DSR 0.468 < 0.5** even before adding the ~943 cells already spent elsewhere in the repo on
   this exact mechanism family.
3. **Šidák at the honest combined count**: this grid's own 396 cells plus the ≈943 already
   measured (`PREREGISTRATION.md` §0) ≈ 1,339 trials → 5% family-wise requires p < 3.8×10⁻⁵. A
   t=2.93 two-tailed normal-approx p ≈ 0.0034 (with n=11,023, the normal approximation is safe) —
   **two orders of magnitude short.**
4. **Net t is the single most decisive number in the whole table: −5.78.** Even setting aside
   every multiplicity correction, this cell does not survive its own instrument's measured cost.

**Verdict: NOT PROMOTED.** Consistent with `mr_stress_conditional_2026-08`'s GER40×rsi14 exception
(survived permutation, died on multiplicity/DSR) and `mr_timezone_repair_2026-08`'s nominal
CLOSE_ENTRY survivor (died on the L25 one-sidedness test) — a third instance in this exact
programme of "one cell clears a bare significance bar, dies immediately on the multiplicity/cost
checks that were pre-registered before it was found."

---

## 5. Net-of-cost reality, in one line

Of 396 cells, **2** have a positive net Sharpe at the calibrated native cost (§ below); median net
t across the whole grid is **−6.50**; the worst is **−29.6**. No cost-model uncertainty changes
this — every net number here is already dwarfed by the gross story in §2-3.

**Cost provenance** (never the blanket `phase0_rt_cost_bps.csv` 2.2bps, never the raw `spread`
column — `PREREGISTRATION.md` §2): US100 1.045bps / GER40 1.017bps / XAUUSD 2.037bps / USDJPY
0.379bps **measured 2026-08-19**; US500 1.07bps / US30 0.86bps derived from `COST_AUDIT.md`
2026-07-31 figures scaled by the GER40 old→new ratio (0.588); EURUSD 0.313bps / GBPUSD 0.338bps
derived from catalog ratios scaled by the USDJPY old→new ratio (0.278); XAGUSD 7.05bps derived
from `gross_surface_map_2026-08`'s own measurement scaled by the XAUUSD old→new ratio (1.107).
**Recalibrated L33b gate** (the mandate asks for this explicitly): at these real costs the honest
floor is **gross/trade > ≈1.4bps**, not the ">3bps" figure that was calibrated against the
discredited 2.2bps blanket rate. The single most economically interesting gross cell in the entire
grid (§4) sits at 0.348bps — **25% of the corrected floor**, not the >300% the old, wrong floor
would have implied was needed. Recalibrating the gate makes the family's death *harder* to escape,
not easier: even the best cell found across 396 variants doesn't approach the corrected bar.

---

## 6. Prior-art accounting (so the next session doesn't re-spend this budget)

| study | cells | scope |
|---|--:|---|
| `yt_strategy_replications/intraday_mr_ftmo` (2026-06-20) | ~13 | indices+FX, z-score+ATR-bracket, momentum-flip, gap-fade |
| `mr_timezone_repair_2026-08` (2026-08-01) | 579 | indices, {sma/ema/vwap-z, rsi14, range_fade}, delay+1 no-bracket, closing-auction B1 |
| `mr_stress_conditional_2026-08` (2026-08-02/03) | 180 | same archived grid, VIX/vol/dispersion-conditioned |
| `pairs_cointegration_2026-08` (2026-08-03) | 171 | 171 pairs, half-life gate — spread/relative-value axis CLOSED mechanically |
| `gross_surface_map_2026-08` (2026-08-06) | ~8,695 | 19 instr incl. FX/metals, hourly S3_MA daily-deviation predictor (a related, coarser mechanism) |
| **this study (2026-08-21)** | **396** | metals + new anchors (VWMA/ivol-MA/session/percentile) + new exits (ATR-asym/mean-revert-target/fraction/time-only) + new entries (confirm/reversal-candle) + 60-min bar |

Combined defensible count for "intraday-session same-day mean-reversion, price/volume-conditioned,
on the FTMO CFD universe": **≈1,339** cells (this grid's 396 is additive to, not overlapping with,
the ≈943 already spent — see `PREREGISTRATION.md` §0 for the exact non-overlap argument per block).
**Zero surviving candidates across the combined count.** Three separate "flagged, not promoted"
near-misses exist (this study's XAUUSD MEAN_REVERT_TARGET; `mr_stress_conditional`'s GER40×rsi14;
`mr_timezone_repair`'s CLOSE_ENTRY nominal survivor) — each dies on a different, independent check
(cost/DSR/Šidák here; DSR+n=1/4-instrument there; L25 one-sidedness there), which is itself a
useful cross-validation that the pre-registered kill criteria are doing real work, not
rubber-stamping.

---

## 7. Variants NOT covered (declared so they can be added)

Everything listed in `PREREGISTRATION.md` §6, plus two items identified only while running this
grid:
- **Trailing-stop exits** — not vectorisable in the shared `engine.backtest` without a bar-by-bar
  rewrite (pre-declared as out of scope).
- **A version of the exit-logic axis with a WIDER-than-1×ATR symmetric bracket** (e.g. 1.5×ATR or
  2×ATR both sides) — §3's diagnosis implies this should reduce the tie-break drag further; this
  grid tested asymmetric (1:1.5) but never a wider *symmetric* bracket. Cheap to add, would help
  separate "artifact shrinks with wider brackets" from "artifact is entry-frequency-driven."
- Sub-5-minute bars, scaled/pyramided entries, Bollinger-band-width as its own axis, RSI windows
  beyond 14/21, range-based-std normalisation (`range_fade` already exists archived), full
  statistical-cointegration pairs beyond the 171 already tested, non-USD FX crosses, non-metal
  commodities, regional indices absent from `deep_history_utc`, volatility-regime conditioning of
  any of these 396 new cells — all pre-declared in `PREREGISTRATION.md` §6, unchanged.
- **A dedicated placebo re-run of the mechanical-artifact finding on a wider bracket** (see above)
  to quantify how much of the drag survives at 1.5×/2×ATR — flagged as the natural next step for
  whoever wants to isolate the residual real-microstructure cushioning effect found in §3 more
  precisely (it is currently bounded only qualitatively: real ≈ −1.25 vs placebo ≈ −4.1/−5.2).

---

## 8. Corrections / lesson candidates for the repo

1. **`engine/backtest.py`'s pessimistic same-bar tie-break is a real, quantified source of
   negative drag for tight (≤1.5×ATR), short-hold (<5 bar) symmetric brackets — confirmed on a
   pure i.i.d. random walk (t −1.4 to −4.1) and a 450-draw matched placebo (0/450 positive, mean
   t −4.1 to −5.2).** Any study using this shared engine with a tight symmetric bracket should
   place its gross-negative reading against a same-mechanism placebo before citing it as evidence
   against a hypothesis — the engine can manufacture t as extreme as −9 with zero market content.
   Lesson candidate (NAMED, not numbered — no minting in-session): `tight-symmetric-bracket-
   pessimistic-tiebreak-manufactures-negative-t-independent-of-market-content`.
2. **`tick_volume` is zero on ~50-55% of resampled 15-min bars** for at least US100 inside its own
   declared liquid session — a new instance of the L60 family, on the volume field rather than
   price/spread. Degrades (but does not corrupt — NaN-safe fallback confirmed) any volume-weighted
   conditioner (VWMA, session-VWAP, inverse-vol-MA indirectly). Worth a repo-wide L60-style audit
   of `tick_volume` zero-fraction the next time a volume-weighted signal is built on this feed.
3. **Recalibrated L33b for this universe's real 2026-08-19 costs: gross/trade > ≈1.4bps**, not the
   ">3bps" figure calibrated against the discredited 2.2bps blanket index cost. Documented here so
   it doesn't need re-deriving; the correction makes the family's death harder to escape, not
   easier.

---

## 9. Reproduce

```
cd Multi_Asset/research/active/mr_intraday_grille_2026-08
/usr/bin/python3 dataload.py       # builds 15min + 60min caches (_cache/, gitignored), ~1min
/usr/bin/python3 run_grid.py       # 396 cells -> grille_resultats.csv, t_distribution.json, ~90s
/usr/bin/python3 placebo.py        # iid max-order-stat + 450-draw matched placebo, ~2min
```
No git operations were performed; no live path (`ftmo_live/`, `Portfolio/`, `strategies/`,
`Futures/live/`, `.github/`, `*.mq5`) was touched. Writes are confined to this folder.
