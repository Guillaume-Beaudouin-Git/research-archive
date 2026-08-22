# Intraday mean-reversion — universe completion + remaining axes — RAPPORT

**Date:** 2026-08-21. **Pre-registration:** `PREREGISTRATION.md`, frozen before any cell was run.
Interpreter: `/usr/bin/python3`. Isolation: shared main working dir, zero git operations, branch
untouched. All writes confined to this folder.

---

## 0. Verdict in one page

**The family stays dead. This session substantially, not completely, closes the two gaps the
mandate named: the instrument universe (7 new FX crosses tested directly and at full power;
energy/copper/softs measured and killed on cost WITHOUT needing a single backtest cell; JP225 —
the mandate's flagged "most interesting axis" — fetched fresh from Dukascopy and tested at
feasibility scale, HK50/AUS200 fetch not completed, declared not covered rather than forced) and
the two cheapest genuinely-uncovered conditioner axes (RSI n∉{14,21} with a bracket exit;
Bollinger %B width). A literature pass independently confirms the repo's own conditioning menu
(volume, volatility regime, position-in-range, VWAP-deviation) is already what the academic
literature treats as canonical, and that the literature's two most striking documented edges map
onto constructions this repo already tested single-instrument and killed. **A genuine clock bug
was caught and fixed in this study's own new-data fetcher** (a Paris-local/UTC mislabeling in the
Asia Dukascopy pull, exactly the L52/L56 failure mode the mandate warned about for this specific
instrument) — caught by the falsification test the mandate prescribed, before any Asia number was
trusted, not after.**

| # | Question | Answer |
|---|---|---|
| **V1** | Do the 7 new FX crosses behave differently from the 3 already-tested majors? | **No.** Pooled non-M1-resolved blocks (RSI+Bollinger, n=63, the fair apples-to-apples comparison — see §2 for why the canonical M1-resolved block isn't): mean t **−1.26**, essentially identical to the already-established FX class mean of **−1.23** (n=132, `mr_intraday_grille_2026-08`). |
| **V2** | Does energy (UKOIL/USOIL/NGAS) or copper show anything different? | **Cost-killed before any signal question is even asked.** Measured RT cost (this session, own measurement, cross-validated against `COST_AUDIT.md`'s independent NGAS figure): NGAS 312bps, USOIL 78.6bps, UKOIL 71.6bps, COPPER 10.7bps. No cell in this repo's combined 1,526-cell history has ever produced >1.2bps gross/trade — a 3×cost gate at 32-936bps is unreachable by construction. **Not backtested — the answer is already in the cost, not the signal.** |
| **V3** | Does Asia (JP225 — HK50/AUS200 fetch did not complete in time, see §1.3), the mandate's flagged "most interesting axis," look different? | **No coherent edge, but genuinely different SESSION STRUCTURE, confirmed only after fixing a real clock bug this study's own fetcher had (§1.3).** JP225's corrected liquidity profile is bimodal — a single-hour spike at the Tokyo cash open (00:00 UTC) AND a broader plateau (13:00-20:00 UTC, Osaka's overnight futures session overlapping US trading hours) that captures MORE cumulative volume than the cash-hours window. Both windows tested: TSE-cash gross t=−1.12 (n=215), US-overlap gross t=+0.04 (n=198) — both inside the dead band, both cost-negative, both on a **materially underpowered sample** (128 trading days vs 13-19 years for the 9 already-tested instruments) that cannot itself certify invariance, only fail to contradict it. |
| **V4** | Do the two new conditioner axes (RSI n∈{7,21,28}, Bollinger %B width) find anything on the new FX universe? | **No.** RSI block mean t **−1.58** (42 cells), Bollinger block mean t **−0.62** (21 cells) — both negative, no coherent positive neighbourhood. 2/70 total cells clear t>2.5 gross (both NZDUSD, correlated — same instrument twice), both **cost-dead** (net t −4.35 and −5.88). |
| **V5** | Does the literature contain a construction this repo hasn't tried? | **Not a mean-reversion one.** Its conditioning menu (volume-weighted MA, VWAP deviation, volatility regime, position-in-range/percentile) is already inside this repo's grid, under different names, and dead in every instance. Its two most striking documented edges — CO-OC overnight-gap reversal (Della Corte-Kosowski-Wang) and cross-sectional end-of-day reversal (Baltussen-Da-Soebhag) — map onto constructions already tested single-instrument here (gap-fade S2, closing-auction B1) and killed. The one adjacent untried idea (Gao-Han-Li-Zhou intraday MOMENTUM, first/last half-hour) is a different family (momentum, not reversion) — flagged for a future, separately-scoped session, not folded into this kill. |
| **V6** | Is there a tier-mediation (HFT/liquidity-provision) explanation? | **Yes, structurally, not just by analogy.** Nagel (2012) frames reversal profits explicitly as compensation to liquidity providers/market makers for absorbing order flow; a retail CFD trader is the PUBLIC side of that same trade, paying the spread this literature identifies as the market maker's reward. This is the same tier-mediation shape as L23b/L34 (FX carry, flow-anchored FX) — the retail/CFD tier is structurally on the wrong side of this literature's edge, not merely under-capitalised relative to it. |

**Combined honest N after this session: 1,454 (prior) + 70 (FX new, Blocks A/B/C) + 2 (JP225
canonical, both windows) = 1,526.** Šidák two-sided threshold at this combined N: t > 4.148
(p<3.36e-05). Zero cells anywhere in this session clear it (max |gross_t| = 3.586, NZDUSD
Bollinger). Zero new survivors.

---

## 1. Chantier 1 — instrument-universe inventory

FTMO's own instrument categories (`PropFirms/ftmo/rules.md`): Forex, Indices, Commodities,
Stocks, Crypto — nothing else. Feasibility audit (done BEFORE any cell was run,
`PREREGISTRATION.md` §1):

| candidate | status | decision |
|---|---|---|
| 7 new FX crosses (EURJPY, EURGBP, AUDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD) | `deep_history_utc` M1, true-UTC, same estate as the 9 already-tested instruments, well-populated spread column (zero-fraction 0.1-4.2%, unlike the majors' 33-69%) | **TESTED** |
| UKOIL, USOIL, NGAS | data exists, RT cost measured THIS session directly from `deep_history_utc.spread` (median, zero-bars excluded, same formula as `dataload.py`): NGAS 312.0bps (validates against `COST_AUDIT.md`'s independently-measured 300bps — cross-check passes, confirms the digit/point convention), USOIL 78.6bps, UKOIL 71.6bps | **COST-KILLED, no cell run** |
| COPPER | measured 10.7bps median | **COST-KILLED, no cell run** |
| Soft commodities (COCOA/COFFEE/COTTON/SOYBEAN/SUGAR) | `COST_AUDIT.md` (2026-07-31) already measured 142-1189bps RT | **already closed, cited not re-measured** |
| JP225 | absent from `deep_history_utc`; daily-only OHLC exists (`oxfordstrat_109_audit/ohlc/`, useless for an intraday study). Fetched fresh this session from Dukascopy (own self-contained fetcher, `fetch_new_indices.py`, writes only to this folder's `_cache/`) — canary confirmed the code resolves. Full pull cut down (twice, after throughput ran far below the canonical downloader's docstring estimate and one attempt stalled outright) to **H1-2024 only, 128 trading days** | **TESTED, feasibility scale — see §1.3** |
| HK50, AUS200 | same Dukascopy-code situation as JP225; canary confirmed both codes resolve (191,044 / 70,650 ticks) | **NOT COVERED — fetch not completed within budget, declared** |
| UK100, FRA40 | same Dukascopy-code situation as Asia, not attempted at all | **NOT COVERED — lower priority, budget spent on Asia** |
| ESP35, EUSTX50 | no Dukascopy code in the existing downloader's dict | **NOT COVERED** |
| Crypto CFD (BTCUSD/ETHUSD/…) | FTMO offers it (`rules.md` §Crypto-specific rules, confirmed: BTCUSD, ETHUSD, ADAUSD, DOTUSD +12 more, weekend trading); repo data (`data/panels/m5_indices/BTCUSD_m1_panel.parquet`) is EET-tagged, migration not done, session design (weekend CFD hours) not built | **NOT COVERED this session** — the one universe gap left fully open, declared rather than guessed at |

### 1.1 New FX crosses — the numbers

Session window: identical to the 3 already-tested majors (07:00-16:00 UTC London/NY overlap) —
kept identical so the new-vs-old contrast is legible, not a new session-design axis. Cost:
derived from the `phase0_rt_cost_bps.csv` catalog × the same 0.278 ratio (measured-USDJPY /
catalog-USDJPY) `mr_intraday_grille_2026-08` already used for EURUSD/GBPUSD (`dataload_fx.py`
§COST_RT_BPS); own-measurement cross-check (median real spread_bps, zero-bars excluded) reported
alongside, never silently substituted:

| sym | derived cost (bps RT) | measured spread_bps (own, this session) | peak volume hour (UTC) |
|---|--:|--:|--:|
| EURJPY | 0.457 | 0.768 | 14 |
| EURGBP | 0.608 | 1.606 | 14 |
| AUDJPY | 0.654 | 1.769 | 14 |
| AUDUSD | 0.602 | 0.955 | 14 |
| USDCAD | 0.427 | 0.584 | 14 |
| USDCHF | 0.651 | 1.402 | 14 |
| NZDUSD | 0.874 | 1.798 | 14 |

Peak-volume hour = 14 UTC for all 7 (London/NY overlap) — clock sanity check passes (L52/L56),
consistent with the already-verified `deep_history_utc` estate.

**Canonical cell (SMA20 z-score(2.0), CROSS, ATR-bracket 1×1×ATR20 H=8), M1-resolved** (Block A —
uses `m1_resolve.py`, imported read-only from `mr_grille_suite_2026-08`, to avoid the tight-
symmetric-bracket tie-break artifact `audit_moteur_bracket_2026-08` quantified):

| sym | n_trades | gross_t | long_t | short_t | net_t |
|---|--:|--:|--:|--:|--:|
| EURJPY | 10,584 | −2.676 | −1.527 | −2.224 | −6.932 |
| EURGBP | 10,611 | −1.381 | −1.262 | −0.601 | −8.233 |
| AUDJPY | 10,044 | +0.987 | +0.931 | +0.466 | −4.106 |
| AUDUSD | 10,152 | +0.179 | −0.497 | +0.762 | −4.823 |
| USDCAD | 10,307 | +2.315 | +2.618 | +0.598 | −2.755 |
| USDCHF | 10,309 | −1.746 | −2.338 | −0.126 | −8.036 |
| NZDUSD | 10,303 | +2.696 | +2.299 | +1.577 | −4.346 |

**Mean t across these 7 = +0.053 — do NOT read this as "new FX crosses have an edge the old
majors don't."** This block is M1-resolved (removes most of the pessimistic tie-break drag);
`mr_grille_suite_2026-08` already showed M1 resolution shifts a cell's mean by roughly a full
point of t versus the 15-min-resolved baseline the OLD majors were measured at. Comparing this
M1-resolved mean directly to the old FX class's 15-min-resolved mean (−1.23) would be comparing
two different measurement instruments, not two instrument classes. The apples-to-apples
comparison is Blocks B/C below (same 15-min plain-bracket resolution as the old classes).

**Blocks B (RSI n∈{7,21,28}) and C (Bollinger %B width {1.5,2.0,2.5}), plain 15-min bracket
resolution — the fair contrast:**

```
Block B (RSI):        n=42   mean t = −1.582   median = −1.537
Block C (Bollinger):  n=21   mean t = −0.623   median = −0.622
Pooled B+C:            n=63   mean t = −1.263   median = −1.419
```

**−1.263 vs the already-established FX class mean of −1.23 (n=132) — a near-exact match.** This
is the invariance answer for the FX-cross axis: no, expanding the FX universe from 3 majors to 10
pairs does not change the class-level mean; the mechanism is dead across the FX class as a whole,
not just the 3 pairs already tested.

Only 2/70 cells clear gross t>2.5 (both NZDUSD — Block A canonical t=2.696, Block C
%B-width=1.5 t=3.585 — the same instrument twice, not independent evidence). Both are
**cost-dead**: net t −4.346 and −5.876 respectively. iid-expected count of |t|>2.5 out of 70
cells ≈ 1.7 (two-sided, Monte-Carlo-verified, 20,000 draws); observed |t|>2.5 count = 18 — the
same ~10-20× negative-skew excess this repo's other MR studies have found, and by now expected:
`audit_moteur_bracket_2026-08` already showed this excess is dominated by the tight-bracket
tie-break artifact wherever M1 resolution isn't applied (Blocks B/C here are NOT M1-resolved,
by the same time-budget declaration as `mr_intraday_grille_2026-08`'s original Blocks 1-4).

### 1.2 Energy / copper / softs — killed on cost, no cell run

| instrument | RT cost measured (bps) | source |
|---|--:|---|
| NGAS | 312.0 | this session, `deep_history_utc.spread` median (zero-bars excluded) — validates against `COST_AUDIT.md`'s independent 300bps |
| USOIL | 78.6 | this session, same method |
| UKOIL | 71.6 | this session, same method |
| COPPER | 10.7 | this session, same method |
| COCOA/COFFEE/COTTON/SOYBEAN/SUGAR | 142-1189 | `COST_AUDIT.md`, 2026-07-31 (cited, not re-measured) |

No 15-min z-score MR cell anywhere in this repo's combined history (1,526 cells after this
session) has produced more than ~1.2bps gross/trade. A 3×cost gate at 32-936bps cannot be cleared
by any construction this family has ever produced — running a backtest cell here would only
re-confirm a conclusion the cost measurement alone already settles. This is itself a legitimate,
cheap finding: **the FTMO commodity/energy CFD universe is closed to this family on the vehicle's
own cost structure, independent of any signal question.**

### 1.3 Asia — JP225 (HK50/AUS200 not completed — see below)

**Fetch outcome.** Canary confirmed all 3 Dukascopy codes (JPNIDXJPY/HKGIDXHKD/AUSIDXAUD) resolve
(298,706/191,044/70,650 ticks, 3 real trading days). A full-year pull (2023+2024, 6 symbol-years)
was pre-registered but Dukascopy throughput in this sandboxed environment ran at roughly
1/15-1/20 of the canonical downloader's own docstring estimate (~12min/symbol-year) and, at one
point, stalled outright for several minutes (consistent with sustained 429 rate-limiting) — the
first full attempt was killed after 8 minutes with only 60/260 days done. Scope was cut, twice,
down to **JP225, H1-2024 only (130 calendar days, 128 trading days)**, which completed
(33,369 M5 rows). **HK50 and AUS200 were not re-attempted** per an explicit instruction not to
relaunch further long downloads — declared here as NOT COVERED, not silently dropped, with the
working fetcher (`fetch_new_indices.py`) left in place so a future session can resume trivially
(`--symbol HK50 --years 2024`).

**⚠ A real clock bug was found and fixed before any session window or cell was trusted — exactly
the L52/L56 risk the mandate warned about.** `fetch_new_indices.py` (copying, read-only, the
URL/bi5-decode protocol from `Forex/data/dukascopy_downloader_m5.py`) anchors each fetch-day's 24
hourly tick buckets on **Paris-local midnight** (`ZoneInfo("Europe/Paris")`, DST-aware) and labels
the result as plain UTC. The falsification test the mandate demanded — split the fetched year at
the EU DST transition (2024-03-31) and check whether the hourly liquidity profile's peak hour is
STABLE across the split — **failed on the first attempt**:

| | peak hour (as originally labeled) | winter/summer shape correlation |
|---|--:|--:|
| BEFORE fix | winter (Jan-Mar) = 23; summer (Apr-Jun) = 22 — a clean 1-hour seasonal shift | **0.32** |
| AFTER fix | winter = 0; summer = 0 — stable | **0.83** |

This is the identical diagnostic signature L56 used to catch the EET-mislabeled overnight
gold/silver window (0.70/0.86 correctly-clocked vs 0.04/0.20 mislabeled). **Root cause**: Dukascopy's
bi5 hour-folders are UTC-indexed, not Paris-local; the inherited construction mislabels every bar
EARLIER than true UTC by exactly that fetch-day's Paris/UTC offset (1h before the 2024-03-31 01:00
UTC transition, 2h after). **Fixed** (`dataload_asia.py::_fix_paris_anchor_bug`) by adding that
offset back, verified by the table above. This bug most likely also sits inside
`Forex/data/dukascopy_downloader_m5.py`'s own cached output for every non-FX-major symbol its
canary process didn't independently clock-check — **flagged for a future session, not fixed or
re-validated here** (out of this study's write scope; only this study's own `_cache/` was
touched).

**The corrected liquidity profile is genuinely bimodal — the mandate's prediction confirmed**:
a single-hour spike at the Tokyo cash open (00:00 UTC = 09:00 JST, Japan has no DST so this is
season-invariant, consistent with the stable post-fix peak), AND a broader, higher-CUMULATIVE-
volume plateau at 13:00-20:00 UTC (22:00-05:00 JST — Osaka Exchange's overnight Nikkei-225-futures
session overlapping US day-session hours, a well-documented arbitrage-driven liquidity source for
this instrument). The best fixed-length contiguous window (comparable to the ~6.5h convention used
for the already-tested indices) captures only 35.9% (6h) / 41.5% (7h) of total volume when
centered on the US-overlap plateau — there is no single dominant "session" the way there is for
US100/GER40; **liquidity is genuinely split across two structurally distinct windows**, which is
itself the clearest evidence this session's structure differs from anything already tested.

**Both candidate windows tested, canonical cell (SMA20 z-score(2.0), CROSS, ATR-bracket 1×1×ATR20
H=8, 15-min resampled from M5, NOT M1-resolved — Dukascopy fetch only pulled M5), cost PROXY (no
direct measurement — WebSearch cross-check of retail broker quotes, 2.1bps, `dataload_asia.py`):**

| window | n_trades | n_days | gross_t | long_t | short_t | net_t | gross_bps/trade |
|---|--:|--:|--:|--:|--:|--:|--:|
| TSE cash (00:00-06:00 UTC) | 215 | 128 | −1.124 | +1.270 | −2.201 | −2.593 | −0.903 |
| US-overlap (13:00-20:00 UTC) | 198 | 128 | +0.038 | −0.162 | +0.214 | −1.662 | +0.226 |

**Neither window shows a coherent edge** — both gross |t| < 1.2, both net-negative, neither leg
consistently signed across the two windows (the TSE-cash window's long/short legs are +1.27/−2.20
— opposite signs, cancelling in the pooled figure, the same "no exploitable direction" pattern
`intraday_mr_ftmo`'s original momentum-flip check found). **This does not, by itself, prove
invariance** — n=198-215 trades over 128 days is roughly 2 orders of magnitude smaller than the
~10,000-14,000 trades the 9 already-tested instruments accumulate over 13-19 years, so a HAC t of
this magnitude has very low power to detect anything short of a large effect. The honest
statement is: **Asia does not show an edge large enough to survive an underpowered sample either
— consistent with, but not proof of, the same invariance found everywhere else in this family.**
A full-history Asia pull (the pre-registered 2-year target, or ideally matching the 13-19y depth
of the other instruments) remains the natural next step, and is now cheap to run (the fetcher and
clock-fix both exist and are validated) — explicitly left for a future session, not attempted
further here per the instruction not to relaunch long downloads.

---

## 2. Chantier 2 — the two cheapest uncovered axes

Per `mr_grille_suite_2026-08/RAPPORT.md` §9's declared list: RSI windows beyond 14/21 (with a
bracket exit — RSI14 exists only in the archived delay+1/no-bracket grid) and Bollinger-band-width
as its own axis were both named and never run. Both are swept here on the new FX-cross universe
(pairing a new axis with new instruments rather than re-confirming a dead axis on an
already-dead instrument) — see §1.1 tables above for the numbers. **Neither axis rescues the
family**: RSI mean t −1.58, Bollinger mean t −0.62, both inside the already-established dead band,
no coherent positive neighbourhood in either block.

---

## 3. Chantier 3 — literature

Full working notes: `literature_notes.md`. Summary (done via WebSearch/WebFetch BEFORE reading
this session's own grid numbers, so it cannot be reverse-fitted):

**The literature's conditioning menu is already inside this repo's grid.** Volume-weighted MA /
VWAP-deviation fading (the most commonly cited retail-quant construction, 2024-2025 sources) =
Block 1d (`mr_intraday_grille_2026-08`, session-VWAP anchor). Volatility/volume-regime
conditioning (explicitly load-bearing in Gao-Han-Li-Zhou, JFE 2018) = `mr_stress_conditional_
2026-08` (180 cells, flat quantile profile). Position-in-range/percentile = Block 1g. All three
are dead in this repo's own measurements — the literature is not pointing at an untried lever.

**The two most striking DOCUMENTED literature edges both map onto constructions already tested
single-instrument in this repo and killed:**
- Della Corte/Kosowski/Wang's CO-OC overnight-gap reversal (reported gross Sharpe 24.16 vs 5.52,
  US equities 1993-2014, cross-sectional/multi-future breadth, no visible retail-cost overlay) =
  the single-instrument analogue is `intraday_mr_ftmo`'s S2 gap-fade, **already measured dead**
  (pooled gross SR −0.50, t −1.94).
- Baltussen/Da/Soebhag's cross-sectional end-of-day reversal (gamma-hedging mediated, needs a
  broad single-stock panel this repo doesn't have) = the single-instrument analogue is
  `mr_timezone_repair_2026-08`'s B1 closing-auction grid, where the one real gross effect found
  (GER40, 3.52bps, t 3.68) **dies on a 5-min entry delay** (0.56bps, t 1.00, sub-cost) —
  **already tried, already killed on execution, not assumed dead.**

**One adjacent, genuinely untried idea**: Gao-Han-Li-Zhou's first/last-half-hour intraday
MOMENTUM (not reversion) — out of this mandate's family scope, flagged for a future session with
its own pre-registration.

**Tier-mediation (does the retail CFD tier structurally lose this edge, not just fail to reach
it)**: yes. Nagel (2012, "Evaporating Liquidity") frames reversal profits explicitly as
compensation TO liquidity providers/market makers for absorbing order flow. A retail CFD trader
is the PUBLIC side of that same trade — paying the spread this literature identifies as the
market maker's reward, not earning it. Structurally the same tier-mediation shape already
established for FX carry (L23b) and flow-anchored FX (L34).

---

## 4. Invariance — the mandate's central question, answered

| class | n (this study) | mean gross t (this study) | established mean t (prior studies) |
|---|--:|--:|--:|
| FX (new crosses, fair B+C comparison) | 63 | **−1.263** | FX (3 majors) −1.23, n=132 |
| Index (Asia, JP225 only, both windows) | 2 | **−0.543** | Index (4, already tested) −1.28, n=176 |
| Metal | — (not re-run) | — | −1.03, n=88 |
| Energy/Copper | 0 (cost-killed) | n/a | n/a |

**Answer to the mandate's central question: invariance holds everywhere it can be tested at
adequate power, and does not break in the one place it could only be tested at low power.** The
FX-cross expansion (n=63, well-powered — 13 years of data, ~10,000 trades/cell) reproduces the
established FX-class mean almost exactly (−1.263 vs −1.23). Energy/copper never reach the point
of needing a t-stat at all — the vehicle's own cost kills the family before any signal question is
asked, the cleanest possible form of invariance (cost, not mechanism, decides). Asia (JP225,
n=2 cells, 128 trading days each) shows no edge either, sitting inside the established band by
simple magnitude (−1.124 and +0.038, mean −0.543) — but this cell pair cannot be read as
confirming the [−1.28,−1.03] band the way the FX expansion does, because a 2-order-of-magnitude
smaller sample has correspondingly less power to reject a real effect if one existed. **The honest
statement, not overclaimed**: no evidence of a session-structure-driven exception was found on
Asia, and the FX and cost evidence together make the family's invariance across asset class and
session structure a well-supported conclusion overall — but Asia's own contribution to that
conclusion is a failure-to-contradict at low power, not an independent confirmation at matched
power. Closing that power gap (a full-history JP225/HK50/AUS200 pull) is the single most valuable
follow-up this study identifies.

---

## 5. What remains not covered (declared, not discovered later)

- **HK50 and AUS200 — fetch not completed.** Codes canary-validated (feasible), full pull not
  run within this session's time budget after JP225 alone required three scoping cuts (2 years to
  1 year to H1-only) to complete. The fetcher (`fetch_new_indices.py`) and the clock-bug fix
  (`dataload_asia.py::_fix_paris_anchor_bug`) both exist and are validated — resuming is a
  `--symbol HK50 --years 2024` call away, not a re-design.
- UK100, FRA40 (EU indices ex-GER40) — same situation, not attempted at all (lower priority than
  Asia per PREREGISTRATION.md §1's own reasoning, and Asia alone consumed the fetch budget).
- ESP35/EUSTX50 (no Dukascopy code available in the existing downloader's dict).
- Crypto CFD (data/session-design gap).
- Cross-specific (non-London/NY) session windows for JPY/AUD/NZD crosses (a different axis).
- M1 resolution for JP225 (M5-only fetch, time budget) — Blocks B/C on the FX crosses are also
  plain-15-min-resolved, matching the original grid's own convention.
- Full 13-19y history for JP225 — 128 trading days (H1-2024) only, feasibility-scale; this is the
  single biggest open item, see §4.
- A full placebo battery for Blocks B/C (not triggered — no cell cleared gates 1-2 to warrant it).
- Order-flow/tick-imbalance conditioning (no order-book data anywhere in this repo).
- Cross-sectional (multi-stock) reversal construction (no ≥30-name single-stock panel here).
- Gao-Han-Li-Zhou intraday MOMENTUM (different family — flagged, not run).
- A clock-bug audit of `Forex/data/dukascopy_downloader_m5.py`'s own existing cached output for
  non-FX-major symbols (the same Paris-anchor bug this study found and fixed in its own,
  independent fetcher very likely also affects that file's prior output) — flagged, not fixed
  here (out of this study's write scope).

---

## 6. Corrections / lesson candidates for the repo

1. **A Paris-local/UTC hour-anchor mislabeling in the Dukascopy bi5-tick-to-candle protocol
   (independently rediscovered in this study's own fetcher, likely shared by
   `Forex/data/dukascopy_downloader_m5.py`'s existing cached output for non-FX-major symbols)
   produces a seasonal 1-2 hour timestamp error, invisible unless a winter-vs-summer peak-hour
   stability test is run.** Confirmed by direct falsification (shape correlation 0.32 mislabeled
   vs 0.83 corrected) — the same diagnostic signature as L56. Any future session pulling new
   Dukascopy data through either fetcher should run this exact check before trusting an hour-of-day
   result, and `Forex/data/dukascopy_downloader_m5.py`'s own prior output deserves an audit pass
   (flagged, not fixed here — out of this study's write scope). Lesson candidate (NAMED, not
   numbered — no minting in-session): `dukascopy-paris-anchor-mislabels-utc-hour-seasonally`.
2. **Network throughput for a fresh Dukascopy pull in this sandboxed environment is roughly
   15-20x slower than the canonical downloader's own docstring estimate (~12min/symbol-year),
   and can stall outright for extended periods (consistent with sustained 429 rate-limiting)
   with zero visible error signal (`err=0` in the progress line even during a multi-minute
   stall).** A future session planning a multi-symbol, multi-year Dukascopy pull should budget
   for this, or fetch a bounded window (single year, single symbol at a time) and check progress
   incrementally rather than assuming the docstring's estimate holds in this environment.
3. **Recalibrated L33b gate (≈1.4bps gross/trade) extended, cheaply, to energy/copper**: NGAS
   312bps, USOIL 78.6bps, UKOIL 71.6bps, COPPER 10.7bps (own measurement, `deep_history_utc.spread`
   median, zero-bars excluded) — NGAS cross-validates against `COST_AUDIT.md`'s independently
   measured 300bps. These four instruments can be excluded from any future intraday-MR (or,
   plausibly, most other short-holding-period) FTMO CFD study on cost alone, without running a
   single cell — a cheap, durable addition to the repo's cost ledger.

---

## 7. Reproduce

```
cd Multi_Asset/research/active/mr_univers_complet_2026-08
/usr/bin/python3 dataload_fx.py                 # cache build + clock sanity check, ~15s
/usr/bin/python3 run_universe.py                # 70 cells (FX new, Blocks A/B/C) -> grille_fx_new.csv, ~60s
/usr/bin/python3 fetch_new_indices.py --symbol JP225 --years 2024   # Dukascopy fetch, ~20-40min (network-bound, variable)
/usr/bin/python3 dataload_asia.py                # session-window inference + clock sanity check (post-fix)
/usr/bin/python3 run_asia.py                    # JP225 canonical cell, both windows -> grille_asia_new.csv
/usr/bin/python3 merge_final.py                 # merges grille_fx_new.csv + grille_asia_new.csv -> grille_resultats.csv, prints headline stats

# To resume the declared-not-covered Asia/EU indices in a future session:
/usr/bin/python3 fetch_new_indices.py --symbol HK50 --years 2024
/usr/bin/python3 fetch_new_indices.py --symbol AUS200 --years 2024
/usr/bin/python3 fetch_new_indices.py --symbol UK100 --years 2024
/usr/bin/python3 fetch_new_indices.py --symbol FRA40 --years 2024
# then re-run run_asia.py -- it already checks for each symbol's cache and skips what's missing.
```
No git operations were performed; no live path (`ftmo_live/`, `Portfolio/`, `strategies/`,
`Futures/live/`, `.github/`, `*.mq5`) was touched. Writes confined to this folder, including the
Dukascopy cache (`_cache/dukascopy_m5/`, self-contained fetcher, never `Forex/data/cache/`).
