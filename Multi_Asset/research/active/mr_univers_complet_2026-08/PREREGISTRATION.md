# PRE-REGISTRATION (frozen before any result) — Intraday MR, universe completion + remaining axes

**Date frozen:** 2026-08-21. **Isolation:** shared main working dir, **zero git operations**,
branch untouched. Writes confined to this folder (`Multi_Asset/research/active/
mr_univers_complet_2026-08/`) — new data fetched from Dukascopy is cached under this folder's
own `_cache/`, never under `Forex/data/cache/` (that would be a write outside the allowed path).
Interpreter: `/usr/bin/python3`.

**Mandate:** close the intraday-MR family for good by covering the two remaining gaps —
**instrument universe** and **unswept axes** — plus a literature pass for constructions not yet
tried. Method is unchanged from the two prior sessions in this chain: **sweep, read the
distribution, do not chase a candidate.** A live mechanism shows a whole neighbourhood of
positive cells; a dead one shows a t-distribution indistinguishable from max|N(0,1)| order
statistics. Combined prior N = **1,454** cells (943 pre-2026-08-21 + 396 `mr_intraday_grille` +
115 `mr_grille_suite`) — this study's cells are additive on top of that count.

## 0. What is NOT re-run

Every already-tested (instrument × conditioner × entry × exit) combination named in
`mr_intraday_grille_2026-08/PREREGISTRATION.md` §0 and `mr_grille_suite_2026-08/PREREGISTRATION.md`
and their RAPPORT.md §6-9 "not covered" lists. In particular: SMA/EMA/VWAP/RSI14/percentile
z-score MR on US100/US500/US30/GER40/EURUSD/GBPUSD/USDJPY/XAUUSD/XAGUSD at 15/30/60-min with
delay+1 or ATR-bracket exits — 0 survivors, ~1,454 cells. Wider brackets, trailing stops,
sub-minute bars, basket spreads, and staggered entries are also already closed (`mr_grille_suite`
§0). The M1 tie-break bias is characterized (`audit_moteur_bracket_2026-08`): real, but
**−0.3 to −0.4 bps/trade** at the canonical cell (1×ATR, H=8) — small relative to the recalibrated
**1.4bps** L33b floor, and a resolver (`m1_resolve.py`, imported read-only) recovers ~77-79% of it
where M1 data exists.

## 1. Chantier 1 — instrument-universe inventory (established BEFORE any cell was run)

**FTMO categories** (`PropFirms/ftmo/rules.md` §"Instruments offered"): Forex, Indices,
Commodities, Stocks, Crypto — nothing else (no bonds/rates).

**Data feasibility audit, done first:**

| candidate | data status | decision |
|---|---|---|
| 7 new FX crosses (EURJPY, EURGBP, AUDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD) | `data/deep_history_utc/*_M1.csv`, true-UTC, 2007-2026, same estate as the 9 already-tested instruments | **TEST** (Block A) |
| UKOIL, USOIL, NGAS (energy) | `data/deep_history_utc` M1 exists, but **measured RT cost is catastrophic**: NGAS 312bps (matches `COST_AUDIT.md`'s independently-measured 300bps — cross-validates the digit/point convention), UKOIL 71.6bps, USOIL 78.6bps (median, spread-column-derived, own measurement this session) | **COST-KILLED, not backtested** — no 15-min MR gross edge in this repo's entire 1,454-cell history exceeds ~1bps/trade; 3×cost gates at 215-936bps are not reachable by construction. Reported, not re-tested with a backtest cell (would waste budget on a foregone conclusion). |
| COPPER | data exists, measured cost 10.7bps median (own measurement) | **COST-KILLED** — 3×cost=32bps unreachable, same argument, not backtested. |
| Soft commodities (COCOA/COFFEE/COTTON/SOYBEAN/SUGAR) | data exists but `COST_AUDIT.md` (2026-07-31) already measured 142-1189bps RT | **Already closed, cited not re-measured.** |
| JP225, HK50, AUS200 (Asian indices) | **absent from `deep_history_utc`** (MANIFEST.md estate list). Daily-only OHLC exists in `Multi_Asset/research/archived/oxfordstrat_109_audit/ohlc/*.parquet` (2000-2026) — **useless for an intraday study** and itself carries an unverified L60-style flat-bar risk (not checked, moot since daily bars can't answer an intraday question anyway). `Forex/data/dukascopy_downloader_m5.py` documents Dukascopy CFD codes (JPNIDXJPY/HKGIDXHKD/AUSIDXAUD) as "best-guess, verify with --canary." | **NEW DATA FETCHED THIS SESSION** — canary confirms all 3 codes resolve (JP225 298,706 ticks / HK50 191,044 / AUS200 70,650 ticks over 3 real trading days, 2025-03-03/04/05). Full pull: 2023+2024 (2 years), M5 resolution, own fetcher (`fetch_new_indices.py`, self-contained, writes only to this folder's `_cache/`) reusing the SAME url/bi5-decode protocol as the canonical downloader (not modifying or importing it, to avoid its side-effecting `mkdir` outside this folder). **Sample is 2 years, not the 13-19 years the other 9 instruments have — reported as a materially smaller-N feasibility read, not a full-history verdict.** |
| UK100, FRA40, EU50 (EU indices ex-GER40) | same situation as Asia; Dukascopy codes exist (`GBRIDXGBP`, `FRAIDXEUR`, `EUSIDXEUR`) | **Fetched if time budget allows after Asia** (lower priority than Asia per the mandate's own "most interesting axis" framing — EU session structure is a smaller structural contrast to GER40, already heavily tested, than Asia is). ESP35/EUSTX50 have no Dukascopy code in the existing downloader's dict — **not covered**, declared. |
| Crypto CFD (BTCUSD/ETHUSD etc.) | `data/panels/m5_indices/BTCUSD_m1_panel.parquet`/`XAUUSD_m1_panel.parquet` exist but are EET-tagged panels (L52-flagged, migration not done) with unknown session/quality; FTMO's crypto CFD hours are non-standard (weekend trading) and would need its own session-window design | **NOT COVERED this session** — flagged as the one universe gap left open, budget did not allow a clean design + quality audit in addition to Asia/EU indices + FX crosses + 2 axes + literature. |

**Session windows for new instruments:**
- FX crosses: same convention as the 3 already-tested majors, **07:00-16:00 UTC** (London/NY
  overlap) — this is the cell that makes the new-vs-old contrast legible; a cross-specific
  session (e.g. Tokyo hours for AUDJPY/NZDUSD) is a DIFFERENT axis, not run here (declared in §5).
- New indices (JP225/HK50/AUS200/UK100/FRA40): **derived empirically from the fetched data's own
  hourly tick-count profile** (L52/L56 discipline — never assume a clock), not from an assumed
  cash-market timetable. Reported per-instrument in `RAPPORT.md` §1 before any cell is run.

## 2. Chantier 1 — the cell (unchanged canonical form, for a legible contrast)

**Identical** to the cell already run 9 times: SMA20 anchor, z-score deviation, z0=2.0, **CROSS**
entry, **ATR-bracket symmetric 1.0×1.0×ATR20, H=8** exit, 15-min bars (native for FX/energy from
`deep_history_utc`; resampled from M5 for the newly-fetched indices), delay+1, daily
vol-targeting (63-bar-equiv, shift-1, cap 3×), intraday-flat, HAC lag-6, two-sided (L25)
mandatory. Gross first, at zero cost. This is Block A of the grid below.

**M1 resolution** (pitfall #2 mitigation): applied wherever M1 data natively exists (the 7 new FX
crosses, from `deep_history_utc`) via `m1_resolve.resolve_bracket_batch` (imported read-only from
`mr_grille_suite_2026-08/m1_resolve.py` — pure functions, no side-effecting imports, verified by
reading the file before import). **Not applied** to the newly-fetched Asia/EU indices (only M5
resolution was fetched, for time-budget reasons) — declared as a residual tie-break exposure for
those instruments specifically (bounded by `audit_moteur_bracket_2026-08`'s abaque: at 1×ATR/H8
the real-data bias is −0.3 to −0.4bps, small relative to the ≈1.4bps gate).

## 3. Chantier 2 — the two cheapest genuinely-uncovered axes

Per `mr_grille_suite_2026-08/RAPPORT.md` §9's declared-not-covered list: **"Bollinger-band-width
as its own axis"** and **"RSI windows beyond 14/21"** were both named and never run (RSI14 exists
only in the archived delay+1/no-bracket grid, never combined with an ATR-bracket exit). Both are
run here on the **new instrument set only** (7 FX crosses + energy/copper already excluded on
cost + new indices where fetched) — this deliberately pairs a new axis with new instruments
rather than re-spending budget re-confirming a dead axis on an already-dead instrument.

- **Block B — RSI(n) conditioner, ATR-bracket exit:** n∈{7,21,28} (14 already tested elsewhere,
  skipped), threshold pairs {(20,80),(30,70)}, CROSS entry (RSI crossing back through the
  threshold from the extreme, direction as usual), exit=ATR_BRACKET_SYM(1:1,H8). 3×2 = 6
  cells/instrument.
- **Block C — Bollinger %B width axis:** %B = (close − lower_band)/(upper_band − lower_band),
  bands = SMA20 ± {1.5,2.0,2.5}×rolling-std20 (the width IS the axis: how far outside the band
  before firing), entry when %B < 0 (below lower) / > 1 (above upper) — i.e. threshold is the
  band width itself, not a separate z0. 3 widths/instrument. Exit=ATR_BRACKET_SYM(1:1,H8).

## 4. Chantier 3 — literature (WebSearch/WebFetch, sources dated, before any cell is read)

Done BEFORE reading Chantier 1/2 results, so the literature pass cannot be reverse-fitted to
whatever the grid finds. Key questions per the mandate: what canonical constructions has this
repo's 1,454-cell programme NOT tried; is the literature's own conditioning menu (volume,
volatility, time-of-day, order flow, range position) already inside our grid; does any
documented literature edge survive a retail cost tier; is the effect HFT/order-flow-mediated
(a tier kill, L23b/L34-style). Findings reported in `RAPPORT.md` §4, marked `[LIT: source, date]`.

## 5. Kill rules (frozen, apply mechanically)

Same three-gate stack as the two prior sessions in this chain:
1. **Gross gate:** HAC lag-6 |t| > 2.5 AND gross bps/trade > recalibrated L33b floor (≈1.4bps for
   the cheap-cost universe; the energy/copper/soft-commodity instruments are excluded from this
   gate entirely per §1 — their own measured cost already exceeds any plausible gross by 1-2
   orders of magnitude, so no cell is run for them).
2. **Two-sided (L25):** both legs individually HAC-significant AND same-signed as the pooled cell.
   A one-sided survivor is a beta trap, not promoted, regardless of the pooled t.
3. **Placebo/construction check (L58-style):** any axis whose construction resembles a known
   artifact family (path-dependent sizing, tight-bracket tie-break, large-N sub-minute) gets a
   matched placebo before its t-stat is read at face value. Blocks A/B/C here are all
   fixed-size-entry, ATR≥1×-bracket, 15-min-or-coarser — none matches the two known artifact
   shapes (staggered sizing, sub-5-min bars) — so a full placebo battery is not pre-registered as
   mandatory, but any cell that clears gates 1-2 gets one before being called a survivor.
4. **Multiplicity:** Šidák at the honest combined n (1,454 + this study's own cell count),
   reported per any survivor, never omitted.
5. **Invariance test (the mandate's central question):** report mean/median gross t **per asset
   class** (index-Asia, index-EU-new, FX-cross-new, [energy/copper: cost-killed, no t] ) against
   the already-established bands (index −1.28, FX −1.23, metal −1.03, n=396) and state plainly
   whether any class falls outside that band, with the smaller-N caveat for the fetched indices
   made explicit in the same sentence as any such claim.

## 6. What will NOT be covered even after this study (declared now, not discovered at write-up)

- Crypto CFD (data/session-design gap, see §1).
- ESP35/EUSTX50 (no Dukascopy code available in the existing downloader's dict).
- Cross-specific (non-London/NY) session windows for JPY/AUD/NZD crosses.
- M1 resolution for the newly-fetched Asia/EU indices (M5-only fetch, time budget).
- A full placebo battery for Blocks B/C unless a cell clears gates 1-2 first.
- Any full-history (13-19y) sample for JP225/HK50/AUS200/UK100/FRA40 — 2 years only.
- Order-flow/tick-imbalance conditioning (no order-book data in this repo for any instrument).
- Any cross-sectional (multi-stock) reversal construction (Baltussen-Da-Soebhag-style) — FTMO's
  "Stocks" category is not a ≥30-name cross-section in this repo's data estate.
