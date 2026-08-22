# MR intraday — uncovered axes — RAPPORT

**Date:** 2026-08-21. **Pre-registration:** `PREREGISTRATION.md`, frozen before any cell was run.
**Grid:** `run_axis_{A,B,C,D,E}_*.py` → `axis_*_results.csv` → merged by `merge_and_stats.py` into
`grille_resultats.csv` (115 rows) and `t_distribution.json`. Interpreter: `/usr/bin/python3`.
Isolation: shared main working dir, zero git operations, branch stays `claude/book-idle-escalation`.

---

## 0. Verdict in one page

**The family is still dead. And this session's most useful output is a second, independent
demonstration of the same meta-lesson the prior 396-cell grid discovered from the other side: a
striking t-stat from this shared backtest machinery must be checked against a matched placebo
before it is believed — in EITHER direction.** The prior grid caught a construction that
manufactures FALSE NEGATIVES (tight symmetric brackets, tie-break bias, t as low as −9 on pure
noise). This grid catches a construction that manufactures FALSE POSITIVES (weighted-average
pyramided entries, t as high as +15 on pure noise) and a second, unrelated trap (sub-minute bars,
where huge sample size turns microscopic bid-ask-bounce into "significant" t-stats that are 10-70x
smaller than the instrument's own trading cost).

| # | Question | Answer |
|---|---|---|
| **V1** | Did wider symmetric brackets (2x/3x ATR), properly M1-resolved, find an edge? | **No.** Axis A mean gross t = **−0.20** (27 cells), still negative at every width (1x/2x/3x means −0.21/−0.30/−0.09). But M1 resolution DID shrink the previously-measured tie-break drag substantially: the exact same US100 cell (SMA20 z-score, CROSS, 1x ATR bracket, H=8) moves from **t=−1.52** at 15-min resolution (prior grid) to **t=−0.82** once the exit is walked minute-by-minute — the pre-registered prediction ("closer to zero, not positive") is confirmed cell-for-cell. |
| **V2** | Did a real ATR-trailing stop, M1-resolved, find an edge? | **No.** Axis B mean gross t = **−0.92** (18 cells); the tighter 1x-ATR trail is markedly worse (mean t −1.74) than the 2x trail (mean t −0.10) — a real, mundane cost of trailing too tight, not a market effect. |
| **V3** | Do sub-5-minute bars (1-min, 3-min) reveal something the 15/60-min grid couldn't see? | **They reveal a trap, not an edge.** Axis C mean gross t = **+5.48** with 25/36 cells clearing t>2.5 (up to t=19.8) — but gross bps/trade is **0.02 to 1.2 bps**, ~10-70x smaller than the same instrument's measured round-trip cost, and net t collapses to **−4 to −79** on every single cell. This is large-N bid-ask-bounce, not alpha: statistically "significant" only because n_trades reaches 100,000-220,000 at 1-min resolution, which manufactures huge t-stats from an effect the size of the spread itself. |
| **V4** | Does a basket-relative (one-vs-three) index spread — a construction never tested before in this repo — show reversion? | **No, and it replicates the pairwise-spread finding on a different construction.** Axis D mean gross t = **+0.30** (16 cells, near-flat). The one cell cluster that stands out (US500 vs the other 3, both k=20 and k=50, t≈2.9-3.1) is **one-sided** (long leg t 3.25-3.59, short leg t 0.86-1.17) — a drift/beta-trap, not reversion, exactly the L27 pattern `pairs_cointegration_2026-08` already found in the pairwise construction. |
| **V5** | Do staggered (pyramided) entries — 1σ/2σ/3σ ladders — reveal a real averaging-into-extremes edge? | **No — it is a proven construction artifact, not alpha.** All 18/18 Axis E cells clear t>2.5 (mean t=**+8.6**, up to t=**14.7** on real data). A matched block-shuffle placebo (same conditioner, same ladder, pure autocorrelation-preserving noise, tested on US100/XAUUSD/EURUSD, 7 independent draws) reproduces **t=5.8 to 14.7 on i.i.d. noise with zero market content** — as large or larger than the real numbers. The single full-size entry (baseline, cited from the prior grid) shows NO such effect (t≈−1 to +1 on the identical placebo). The bias lives entirely in the weighted-average-of-tranches accounting, not in any instrument. **Full detail in §4 — this is the most important finding of the session.** |

**Bottom line:** every one of the five uncovered axes is, on its own economic merits, dead — exactly
the pre-registered expectation. What makes this session valuable is that TWO of the five axes
(sub-minute bars, staggered entries) would have produced a false "PASS" under the grid's own
pre-registered gates (gross t>2.5, gross bps/trade>1.4, two-sided, same-signed legs) if the
placebo/cost checks had not been run — **15 cells clear every naive gate simultaneously, and every
single one of them is Axis E** (§4 shows this precisely). This is a clean, reproducible
demonstration that the placebo step is not a formality.

---

## 1. What was measured

115 cells across 5 axes (see `PREREGISTRATION.md` §3 for exact definitions):

| axis | n cells | mechanism |
|---|--:|---|
| A — wider symmetric brackets, M1-resolved | 27 | 9 instruments x {1x,2x,3x} ATR20, exit walked on real 1-min path |
| B — trailing stop, M1-resolved | 18 | 9 instruments x {1x,2x} ATR20 trailing distance, no fixed TP |
| C — sub-5-minute bars | 36 | 9 instruments x {1-min,3-min} x {ATR bracket, TIME_ONLY} |
| D — basket-relative index spread | 16 | 4 indices x {k=20,50} x {TIME_ONLY, BRACKET-provisional} |
| E — staggered (pyramided) entries | 18 | 9 instruments x {2-step, 3-step} ladder, 1σ/2σ/3σ |

Same house rules as the prior grid throughout: delay+1, daily vol-targeting, intraday-flat, HAC
lag-6, two-sided reporting mandatory, gross-first-at-zero-cost, measured/derived native costs
(`PREREGISTRATION.md` §1, unchanged from `mr_intraday_grille_2026-08`).

**M1 resolver built from scratch (`m1_resolve.py`)** — `audit_moteur_bracket_2026-08/` (the
dedicated resolver project named in the mandate) does not exist in this repo (checked by path and
repo-wide filename search at freeze time). The resolver walks the session-filtered 1-minute series
(`dataload.build(sym, bar="1min")`, cached, reused read-only from the prior grid's pipeline)
starting at the exact entry minute, for up to 120 minutes (the grid's own H=8-bar-equivalent
backstop), fully vectorised via strided sliding-window batching for diagnostics and a lightweight
scalar path for the sequential one-position-at-a-time loop. Validated against the prior grid: the
same US100 SMA20/z0=2.0/CROSS/1x-ATR-bracket/H8 cell gives **n=5,829 trades at M1 resolution vs
n=5,841 at 15-min resolution** (near-identical population, as expected — only the EXIT changed).

---

## 2. The distribution — read per-axis, not pooled (pooling would mislead here)

```
n = 115        mean(t) =  2.913      median(t) =  1.060      max|t| = 19.772
t > +2.5 :  45 cells    (iid-expected for n=115  ~2.5)
t < -2.5 :   5 cells    (iid-expected for n=115  ~2.5)
iid Monte-Carlo (20,000 draws, n=115): E[max|t|] = 2.79,  P95 = 3.51
```

Read naively, this looks like an extreme excess of "significant" cells (45 vs an iid-expected
~2.5) — but unlike the prior 396-cell grid (where the whole family shared one mechanism and the
distribution was a single honest read), **this grid deliberately mixes five structurally
unrelated axes, two of which have their own known, non-market-content trap.** Pooling the
histogram would hide exactly the finding that matters. Per-block means:

| block | n | mean t | median t | t>2.5 | t<−2.5 |
|---|--:|--:|--:|--:|--:|
| A — bracket, M1-resolved | 27 | −0.20 | +0.03 | 0 | 2 |
| B — trailing stop, M1-resolved | 18 | −0.92 | −0.31 | 0 | 2 |
| C — sub-5-min bars | 36 | **+5.48** | +3.68 | **25** | 1 |
| D — basket spread | 16 | +0.30 | −0.14 | 2 | 0 |
| E — staggered entries | 18 | **+8.61** | +8.09 | **18** | 0 |

Every one of the 45 "significant" cells decomposes exactly as: **25 from Axis C (cost-dead, §3),
18 from Axis E (proven artifact, §4), 2 from Axis D (one-sided beta trap, L25)** — zero cells with
an unexplained, clean two-sided, cost-surviving positive. The 5 cells below −2.5 are the residual,
much-shrunk (vs the prior 15-min-resolution grid) tie-break drag in Axis A (2) and Axis B (2), plus
one Axis C 3-min bracket cell.

---

## 3. Axis C — sub-5-minute bars: statistically "significant," economically dead

`grille_resultats.csv` rows for `block==C_subminute`. The pattern is stark and consistent across
every instrument and both frequencies:

| sym (1-min, ATR bracket) | n_trades | gross_t | gross_bps/trade | cost_bps | net_t |
|---|--:|--:|--:|--:|--:|
| GBPUSD | 221,694 | 19.77 | 0.129 | 0.338 | −38.46 |
| EURUSD | 215,582 | 17.23 | 0.112 | 0.313 | −33.77 |
| USDJPY | 221,282 | 17.65 | 0.110 | 0.379 | −47.95 |
| XAUUSD | 189,631 | 15.21 | 0.193 | 2.037 | −79.29 |
| GER40 | 96,679 | 5.37 | 0.085 | 1.017 | −53.45 |

**Gross bps/trade never exceeds 1.2bps anywhere in the axis (best case XAGUSD, 3-min bracket) —
below the recalibrated L33b floor of ≈1.4bps before any multiple-testing correction, and net t is
catastrophically negative (−4 to −79) on all 36 cells.** The mechanism is not subtle: at 1-min
resolution, n_trades reaches 100,000-220,000 — two full orders of magnitude above the 15-min
grid's typical 5,000-14,000 — and HAC t-stats scale with `sqrt(n)`, so an effect the size of
ordinary bid-ask bounce (the price mechanically alternating around the true mid by roughly the
spread) becomes "significant" purely from sample size while remaining a small fraction of the cost
that would be paid to capture it. **This is the textbook large-N trap the grid's own gross/cost
gate exists to catch** — and it catches it cleanly: every cell fails gross > 1.4bps before net is
even considered. TIME_ONLY exits (no bracket at all) show the identical pattern at lower magnitude
(t up to 7.7, gross bps 0.03-0.25), confirming the effect is not specific to the bracket's own
tie-break mechanics — it is a property of trading at this frequency at all on these instruments.

---

## 4. Axis E — staggered entries: a proven, and important, construction artifact

This is the most useful single result of the session. **All 18/18 Axis E cells clear t>2.5**
(mean t=+8.6, up to +14.7 on real XAGUSD 3-step data), with DSR≈1.000 on nearly every cell and 15
of the 18 clearing the full pre-registered gate stack (t>2.5, gross bps>1.4, both legs
significant and same-signed — see the table in §0/V5). Read at face value, this looks like the
strongest, cleanest, cheapest-to-clear signal in the entire ~1,454-cell research programme to
date. **It is not.**

**Falsification, done before trusting the number (exactly the discipline the prior grid's §3
established):** a block-shuffled (Politis-Romano, mean block 20 bars) placebo was built by
reconstructing a random-walk price series from the SAME instrument's own shuffled 15-min log
returns (autocorrelation removed, marginal distribution and volatility clustering roughly
preserved), then running the identical SCALE_2STEP/SCALE_3STEP machinery through it:

| instrument | trial | single-rung (baseline) placebo t | SCALE_3STEP placebo t |
|---|--:|--:|--:|
| US100 | 1 | (not tested this trial) | +6.57 |
| US100 | 2 | | +5.81 |
| US100 | 3 | | +7.87 |
| US100 | 4 | −1.08 | (2-step) +5.88 |
| XAUUSD | 1 | −0.37 | +12.40 |
| XAUUSD | 2 | −0.25 | +11.85 |
| EURUSD | 1 | +0.08 | +13.53 |
| EURUSD | 2 | +1.00 | +14.68 |

**On PURE NOISE, with zero market content, the staggered-entry construction reproduces t as large
or larger than anything found on real data (up to +14.7), while the single-shot baseline stays in
the −1 to +1 noise band on the identical placebo path.** The artifact lives entirely in the
weighted-average-of-tranches return accounting, not in any instrument or in market microstructure.

**Best available mechanism (empirically diagnosed, not yet a closed-form proof):** breaking real
US100 episodes down by how many rungs filled shows the signature clearly —

| rungs filled | count | mean return |
|---|--:|--:|
| 1 (never extended past 1σ) | 3,355 | **+11.5 bps** |
| 2 (extended to 2σ) | 2,583 | −4.9 bps |
| 3 (extended to 3σ) | 117 | −30.0 bps |

The SAME rolling statistic (the z-score of close vs SMA20) is used both to TRIGGER an episode and
to decide, continuously through the holding window, whether to ADD to it. "Only 1 rung filled"
is not a blind, ex-ante population — it is the sub-population of paths that, having crossed 1σ,
did **not** continue extending during the window, which is mechanically correlated with the price
having already turned back toward the mean by the time the window's fixed exit is reached. This
selection effect (using one endogenous, self-referential statistic to both gate entry and gate
position-sizing) manufactures a positive mean on the dominant (1-rung, ~55% of episodes) bucket
regardless of whether the instrument's price process has any genuine reversion tendency — exactly
reproduced by the placebo on pure noise. The deeper-rung buckets (2,583 and 117 episodes) are
NEGATIVE on average (consistent with "the position kept extending against the entry, and the
time-stop caught it before any reversion"), but are outnumbered and outweighed by the
dominant, artifact-positive 1-rung bucket in the pooled weighted mean.

**Practical correction for future sessions using this shared machinery:** any strategy that
conditions ADDITIONAL position sizing on the SAME rolling statistic used to trigger the original
entry, and reports a size-weighted average return across the resulting tranches, inherits this
bias — it must be checked against a matched block-shuffle placebo (same ladder, same weights,
same instrument's own return distribution) before any claim is made, exactly as a tight symmetric
bracket must be checked against a placebo per the prior grid's finding. **Two independent
sessions, two independent constructions, the same meta-lesson from opposite directions: never
trust a striking t-stat from this backtest family without a matched-construction placebo.**
Lesson candidate (NAMED, not numbered — no minting in-session):
`self-referential-sizing-ladder-manufactures-positive-t-independent-of-market-content`.

---

## 5. Axis A/B in detail — quantifying how much of the prior drag was artifact

| | 15-min-resolved (prior grid) | M1-resolved (this grid) |
|---|--:|--:|
| US100, 1x bracket, gross t | −1.52 (n=5,841) | **−0.82** (n=5,829) |
| US500, 1x bracket, gross t | −0.87 (n=5,769) | −0.33 (n=5,761) |
| USDJPY, 1x bracket, gross t | −2.81 (n=10,816) | −1.55 (n=10,815) |
| XAGUSD, 1x bracket, gross t | −2.64 (n=13,742) | +0.12 (n=13,523) |

Every one of the four spot-checked instruments moves **closer to zero** at M1 resolution, exactly
the pre-registered prediction — but none flips solidly positive, and the axis-wide mean (−0.20
across all widths) stays negative. Widening the bracket further (2x, 3x) does not monotonically
help at M1 resolution (means −0.21 / −0.30 / −0.09 for 1x/2x/3x) — average hold time roughly
triples (35 → 86 → 108 minutes) without a corresponding improvement in t. **Conclusion: M1
resolution recovers roughly half of the previously-measured drag (confirming it was tie-break
artifact), but the remaining, smaller negative is real and not an artifact of bracket width.**
Axis B (trailing stop) shows the same qualitative pattern: a tight (1x ATR) trail is notably worse
(mean t −1.74) than a looser (2x ATR) one (mean t −0.10) — an ordinary, expected cost of trailing
too tight, not a hidden edge.

---

## 6. Axis D in detail — basket-relative spread replicates the pairwise finding

Mean gross t = +0.30 (near-flat), long-leg mean t = +0.47 vs short-leg mean t = +0.01 — a mild but
real asymmetry, concentrated entirely in US500 (both k=20 and k=50: gross t 2.9-3.1, long t
3.25-3.59, **short t only 0.86-1.17**). This is the same L27 signature `pairs_cointegration_2026-08`
already found in the pairwise construction (US100/GER40 asymmetric legs, "when the spread is high
it keeps rising, when low it keeps falling" — drift, not reversion): US500 persistently
outperforms the other three indices in the sample, and fading that persistent outperformance loses
money on the short side while randomly "working" on the long side — a beta trap, flagged
`ONE_SIDED` per L25, never promoted. GER40 and US30 are flat both ways; US100 is mildly negative.
**The basket (one-vs-three, multilateral) construction, tested here for the first time in this
repo, reproduces the same qualitative conclusion as the already-closed pairwise construction: index
relative-value spreads in this universe carry drift, not exploitable reversion.**

---

## 7. Net-of-cost reality and the "would-be survivors" table

Of the 115 cells, the ones that clear the FULL naive gate stack (gross t>2.5, gross bps/trade>1.4,
both legs individually significant and same-signed — i.e. everything the pre-registration asks
for before any promotion is even considered) number **15**. **All 15 are Axis E.** Zero cells from
Axis A, B, C, or D clear this stack. Given §4's placebo demonstration, all 15 are traced to a
proven construction artifact and **NOT PROMOTED**. This is the cleanest possible illustration of
why gate 3 (distribution + placebo, never a bare significance bar) is pre-registered as
non-negotiable: applied mechanically, the OTHER four gates (gross, cost, two-sided, same-signed)
would have certified 15 false positives.

---

## 8. Prior-art accounting (cumulative honest N)

| study | cells |
|---|--:|
| Five 2026-06/07/08 studies (see `mr_intraday_grille_2026-08/PREREGISTRATION.md` §0) | 943 |
| `mr_intraday_grille_2026-08` (396-cell grid, 2026-08-21 earlier this session-chain) | 396 |
| **this study (2026-08-21)** — Axis A (27) + B (18) + C (36) + D (16) + E (18) | **115** |
| **Combined** | **≈1,454** |

**Zero surviving candidates across the combined ≈1,454 cells.** The family (intraday-session
same-day mean-reversion, price/volume/spread-conditioned, on the FTMO CFD universe) has now been
swept across every axis named in this repo's own declared-gap lists (`mr_intraday_grille_2026-08`
§6/§7) plus two axes opened fresh by this mandate (basket-relative spread, staggered entries).

---

## 9. Variants NOT covered (declared so they can be added)

- Everything already declared out of scope in `mr_intraday_grille_2026-08/PREREGISTRATION.md` §6
  and not picked up here: Bollinger-band-width as its own axis, RSI windows beyond 14/21,
  range-based-std normalisation, full cointegration pairs beyond the 171 already tested, non-USD
  FX crosses, non-metal commodities, regional indices absent from `deep_history_utc`,
  volatility-regime conditioning of any cell in this grid.
- **A true M1-resolved reading of Axis D's bracket variant** — the synthetic basket-spread series
  has no native intrabar high/low; it stayed PROVISIONAL by design (`PREREGISTRATION.md` §6).
- **A closed-form (not just empirically-diagnosed) derivation of the Axis E artifact's exact
  magnitude as a function of ladder shape** (number of rungs, spacing, weight scheme) — this
  session demonstrated the effect exists and roughly why, on 3 instruments and 7 placebo draws;
  a dedicated follow-up could map how the bias scales with ladder depth/spacing to give a
  correction factor rather than just a kill.
- **Trailing stops with a ratchet-step or volatility-adaptive rule** (only plain ATR-multiple
  trailing was tested) and **asymmetric-weight staggered ladders** (only equal-split 2/3-step was
  tested) — both declared out of scope in `PREREGISTRATION.md` §6.
- **Basket-relative spread for FX or metals** — only the 4 indices named in the mandate were
  tested; a 10-instrument FX basket or a metals pair-as-basket is a separate, unscoped axis.
- **A full 450-draw placebo battery for Axis A/B/E** — this session ran 7 (E) + a handful of
  spot-checks (A/B, via the real-vs-prior-grid comparison in §5) for budget reasons; a dedicated
  battery at the scale of the prior grid's §3 (450 draws) is the natural next step if any of these
  numbers need a tighter confidence bound than "clearly the same order of magnitude as the real
  result."
- **Sub-second or tick-level execution** — 1-min was the finest resolution available from
  `deep_history_utc`; anything finer would need a different data source.
- Cross-instrument portfolio construction / combining any surviving cells into a book — moot here
  (zero survivors), and out of scope for a cell-level sweep regardless.

---

## 10. Corrections / lesson candidates for the repo

1. **Wider/M1-resolved brackets confirm (do not merely repeat) the prior session's tie-break
   finding**: M1 resolution recovers roughly half the previously-measured negative drag on
   spot-checked cells (US100 −1.52→−0.82, USDJPY −2.81→−1.55, XAGUSD −2.64→+0.12), but the
   residual, smaller negative bias persists and is not eliminated by wider brackets — it is a
   genuine (if small) real-market cost of the strategy shape, not purely artifact.
2. **Sub-5-minute bars on this universe are a large-N trap, not a frequency edge**: gross t
   reaches 19.8 with gross bps/trade of 0.02-1.2 — 10 to 70x below the instrument's own measured
   cost. Any future session tempted to "just try 1-minute bars" on this family should check
   gross bps/trade against cost BEFORE reading the t-stat; the t-stat alone is actively
   misleading at n>100,000.
3. **Self-referential position-sizing ladders (staggered entries gated on the same rolling
   statistic used for the original signal) manufacture a large POSITIVE t on pure noise — the
   mirror image of the tie-break bracket's negative artifact.** Confirmed via matched block-shuffle
   placebo on 3 instruments, 7 independent draws (placebo t = +5.8 to +14.7, matching or exceeding
   the real data's +6.4 to +14.7); the single-shot baseline shows no such effect on the identical
   placebo (t ≈ −1 to +1). DSR is not a safeguard here (DSR≈1.000 on nearly every affected cell).
   Lesson candidate (NAMED): `self-referential-sizing-ladder-manufactures-positive-t-independent-
   of-market-content`.
4. **Meta-lesson, stated once for both directions**: this repo's shared backtest engine can
   manufacture a striking t-stat in EITHER direction from construction alone — tight symmetric
   brackets (negative, prior session) and self-gated sizing ladders (positive, this session) are
   two separate, now-documented instances of the same underlying risk. **Any cell whose exit or
   entry construction has this shape must clear a matched-construction placebo before its t-stat
   is read at face value**, regardless of which sign looks compelling.

---

## 11. Reproduce

```
cd Multi_Asset/research/active/mr_grille_suite_2026-08
/usr/bin/python3 run_axis_A_bracket.py       # 27 cells, M1-resolved wider brackets, ~75s
/usr/bin/python3 run_axis_B_trailing.py      # 18 cells, M1-resolved trailing stop, ~5s (cache warm)
/usr/bin/python3 run_axis_C_subminute.py     # 36 cells, 1-min/3-min bars, ~2min
/usr/bin/python3 run_axis_D_basket.py        # 16 cells, basket-relative index spread, ~3s
/usr/bin/python3 run_axis_E_staggered.py     # 18 cells, staggered entries, ~5s
/usr/bin/python3 merge_and_stats.py          # merges to grille_resultats.csv + t_distribution.json
```
No git operations were performed; no live path (`ftmo_live/`, `Portfolio/`, `strategies/`,
`Futures/live/`, `.github/`, `*.mq5`) was touched. Writes are confined to this folder. The Axis E
placebo checks (§4) were run ad hoc from the Python REPL during investigation (not a standalone
script) — the block-shuffle helper is reproduced inline in §4's methodology description; a
dedicated `placebo_axis_E.py` is a natural addition if this needs re-running (see §9).
