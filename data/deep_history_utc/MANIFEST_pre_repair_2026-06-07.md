# Deep-history M1 backfill — MANIFEST (TRUE UTC)

**Output dir:** `data/deep_history_utc/`  ·  **Scripts/cache:** `data/deep_history_m1/`
**Timestamps:** column `timestamp_utc` now holds **TRUE UTC** (existing MT5 files were broker EET/EEST mislabeled UTC; localized `Europe/Bucharest`→UTC). Dukascopy backfill is native UTC. Schema/dtypes/units identical to the existing MT5 panel.

## Gates (passed before bulk)
- **GATE 1 — decoder vs `dukascopy-node`:** EURUSD(1e5)/USDJPY(1e3)/XAUUSD(1e3)/US500(1e3), days with down-bars, **0 OHLC mismatches** (max|Δ|=0.0). Confirms the O,C,L,H byte order + per-family decimalFactor.
- **GATE 2 — full pipeline EURUSD (2010+2024):** 0 OHLC violations, monotonic true-UTC, 0 dups, **overlap close-corr 0.999999** (re-confirms tz direction).

## Method
- **Source:** Dukascopy per-day M1 **candle** bi5 (`{BID,ASK}_candles_min_1.bi5`), record `>iiiiif` = (sec, O, **C, L, H**, vol) — byte order O,C,L,H (the prior OHLC bug, now fixed).
- **Splice:** existing MT5 range stays authoritative; Dukascopy fills strictly before/after it.
- **Spread calibration (2024 overlap, true-UTC hour-of-day):** fit BOTH additive (MT5≈Duka+offset_h) and multiplicative (MT5≈Duka×ratio_h); pick per instrument by lower MAE on a held-out (last-30%) slice; refit on full overlap; apply to all Dukascopy rows. Existing spreads never modified. Indices optionally rounded to the existing spread tick.
- **tick_volume caveat:** FX/metals backfill tick_volume = Dukascopy M1 bid volume (≈millions scale), NOT an MT5 tick count — different scale than existing rows. **Index backfill tick_volume = 0** (Dukascopy index candles carry no volume; see "Index v=0 fix" below). Dtype-matched int throughout.
- **real_volume:** backfill = `0` (Dukascopy has none); existing values kept verbatim (note: existing column is cosmetically mixed `0`/`0.0`/empty across MT5 exporters).

## Execution findings & integrity hardening
Two silent-corruption classes were found and fixed before the final build (both verified against `dukascopy-node`):
1. **503 retry-exhaustion dropped days (FIXED).** Dukascopy enforces a hard **~5 successful req/s per-IP** limit; early high-concurrency runs (10/40 threads) triggered 503 storms whose `_fetch` retries silently exhausted → multi-day holes (confirmed: GBPUSD 2013/2014). Fixes: optimal **nw=8** (ceiling throughput, 0×503); `_fetch` now **raises** after retries (never returns None silently); `download_year` **refuses to cache any year with ≥1 failure** (re-downloads on next run). All suspect early-cached years were purged and re-fetched clean.
2. **Index candle volume=0 dropped real bars (FIXED).** Dukascopy **index** candles report volume=0 even on real trading bars (FX/metals report true volume), so the original `v<=0` drop-filter deleted whole index sessions (US500 lost Feb–May 2013 entirely). Filter changed to drop only `v<=0 AND high<=low` (no volume *and* no range) — a no-op for FX/metals, recovers index bars (US500 2013 0→23,549 bars; US500/US100 88-day 2013 hole eliminated).
- **Rate-limit reality:** the full 15-instrument 2007→present backfill (~110k requests) is bounded to ~5 req/s; it ran resumably (per-year parquet cache) with `caffeinate` preventing macOS sleep.

## Per-instrument summary

| sym | final range (UTC) | rows | bf_before | bf_after | overlap corr | spread | amb/ne | mono | dups | ohlc✗ | sprd<0 | gaps |
|---|---|---|--:|--:|--:|---|---|---|--:|--:|--:|--:|
| GBPUSD | 2007-01-01→2026-06-05 | 7260253 | 5592955 | 374417 | 0.999998 | additive | 0/0 | True | 0 | 0 | 0 | 1070 |
| EURGBP | 2007-01-01→2026-06-05 | 7252687 | 5586129 | 374387 | 0.999987 | additive | 0/0 | True | 0 | 0 | 0 | 1206 |
| NZDUSD | 2007-01-01→2026-06-05 | 7250320 | 5583584 | 374374 | 0.999998 | additive | 0/0 | True | 0 | 0 | 0 | 1951 |
| USDCHF | 2007-01-01→2026-06-05 | 7242013 | 5576053 | 376961 | 0.999996 | additive | 0/0 | True | 0 | 0 | 0 | 3087 |
| AUDJPY | 2007-01-01→2026-06-05 | 7264227 | 5712070 | 350481 | 0.999996 | additive | 0/0 | True | 0 | 0 | 0 | 763 |
| EURJPY | 2007-01-01→2026-06-05 | 7263644 | 5710911 | 375470 | 1.0 | additive | 0/0 | True | 0 | 0 | 0 | 917 |
| EURUSD | 2007-01-01→2026-06-05 | 7259299 | 4118327 | 8481 | 0.999994 | multiplicative | 0/0 | True | 0 | 0 | 0 | 759 |
| AUDUSD | 2007-01-01→2026-06-05 | 7125523 | 3989084 | 374662 | 1.0 | additive | 0/0 | True | 0 | 0 | 0 | 11473 |
| USDCAD | 2007-01-01→2026-06-05 | 7255578 | 4118782 | 375215 | 0.999999 | multiplicative | 0/0 | True | 0 | 0 | 0 | 934 |
| USDJPY | 2007-01-01→2026-06-05 | 7256114 | 4118665 | 377539 | 1.0 | additive | 0/0 | True | 0 | 0 | 0 | 856 |
| XAUUSD | 2007-01-01→2026-06-05 | 6886976 | 3931970 | 8223 | 0.999995 | multiplicative | 0/0 | True | 0 | 0 | 0 | 16829 |
| US500 | 2012-01-16→2026-06-05 | 2883793 | 1247292 | 7913 | 0.999986 | additive | 0/0 | True | 0 | 0 | 0 | 24340 |
| US100 | 2013-01-01→2026-06-05 | 2856407 | 1197609 | 7903 | 0.999988 | multiplicative /tick10 | 0/0 | True | 0 | 0 | 0 | 10548 |
| US30 | 2013-09-30→2026-06-05 | 3954770 | 1397427 | 7900 | 0.999991 | additive | 0/0 | True | 0 | 0 | 0 | 7523 |
| GER40 | 2013-09-30→2026-06-05 | 2834721 | 1043568 | 7846 | 0.999973 | additive | 0/0 | True | 0 | 0 | 0 | 13929 |

> US30 (+36,613) and GER40 (+279,707) rows include **internal-gap fill** from Dukascopy (see below).

### Per-instrument notes
- **GER40:** DAX constituent change DAX30→DAX40 (Sep 2021); price series continuous. Dukascopy code DEUIDXEUR. Candle backfill effectively starts **2013-09-30** (earlier DEUIDXEUR candle files 404; tick depth is earlier but not used).
- **XAUUSD:** Existing real_volume is populated (FTMO supplies gold volume); Dukascopy backfill has NO real_volume → 0.
- **US500:** backfill to **2012-01-16** (true Dukascopy floor). Feb–May 2013 recovered by the index v=0 fix.
- **US100:** backfill to **2013-01-01**. 2013 recovered by the v=0 fix; one residual 5-day sparse stretch mid-May 2013.
- **US30 / GER40:** candle backfill starts **2013-09-30** (earlier candle files 404 at source). US30 existing MT5 starts 2019-02-08; GER40 2018-01-01.
- **AUDUSD:** high intra-week gap count (11,473) is **legitimate 2007–2010 thin-liquidity** (9,640 of them in 2007 alone, all 3–10 min no-tick minutes) — not holes (verified vs `dukascopy-node`).

### Index splice seams & existing-data internal gaps
- **Index 2017/2018 seams:** EURUSD/USDCAD/XAUUSD/US500/US100/GER40 `seam_before` falls on the **New-Year 2017/2018 holiday** (backfill ends Fri 2017-12-29, existing resumes 2018-01-01/02 → ~72 h `gap_minutes≈4321`). The `step_points` there is the genuine 3-day holiday move (+ possibly a small Dukascopy↔FTMO index price-level difference). Overlap corr ≥0.99997 confirms the feeds track; absolute index levels may differ by a few points across this single seam.
- **Pre-existing FTMO existing-data outages — FILLED from Dukascopy (`assemble.py --fill-internal`, on user request).** The fill inserts Dukascopy bars only inside existing gaps > 48 h *where Dukascopy has data* (weekends/holidays stay empty — Dukascopy is closed too); existing bars always win on any timestamp collision. Filled bars verified vs `dukascopy-node` (0 OHLC mismatches).
  - **GER40 2018** (≈199-day near-total hole) + **GER40 2019** (Feb/Aug/Sep outages) → **+279,707 bars**; GER40 max intra gap 4776 h → **122 h** (only DAX Christmas closures remain). Required downloading GER40 2018/2019 (inside the existing range, not in the original backfill set).
  - **US30 2019-08/09** (17 d + 15 d outages) → **+36,613 bars**; US30 max intra gap 410 h → **106 h** (holidays + early-2013 backfill sparsity only).
  - **US500 / US100:** scanned — no existing-data outages (all >72 h gaps are Easter/Christmas/New-Year holidays); nothing to fill.
  - Filled index bars carry `tick_volume=0` and a calibrated spread (same model), consistent with the rest of the index backfill. The few remaining multi-day index gaps are genuine market holidays (Dukascopy closed too).

### Splice-seam price steps (points across the backfill↔existing join)
- **GBPUSD:** before={'step_points': 25.0, 'gap_minutes': 1.0}  after={'step_points': 2.0, 'gap_minutes': 1.0}
- **EURGBP:** before={'step_points': 24.0, 'gap_minutes': 1.0}  after={'step_points': 3.0, 'gap_minutes': 1.0}
- **NZDUSD:** before={'step_points': 72.0, 'gap_minutes': 1.0}  after={'step_points': 1.0, 'gap_minutes': 1.0}
- **USDCHF:** before={'step_points': 35.0, 'gap_minutes': 1.0}  after={'step_points': 35.0, 'gap_minutes': 1.0}
- **AUDJPY:** before={'step_points': 51.0, 'gap_minutes': 1.0}  after={'step_points': 1.0, 'gap_minutes': 1.0}
- **EURJPY:** before={'step_points': 25.0, 'gap_minutes': 1.0}  after={'step_points': 9.0, 'gap_minutes': 1.0}
- **EURUSD:** before={'step_points': 102.0, 'gap_minutes': 4321.0}  after={'step_points': 1.0, 'gap_minutes': 1.0}
- **AUDUSD:** before={'step_points': 55.0, 'gap_minutes': 1.0}  after={'step_points': 3.0, 'gap_minutes': 1.0}
- **USDCAD:** before={'step_points': 343.0, 'gap_minutes': 4322.0}  after={'step_points': 8.0, 'gap_minutes': 1.0}
- **USDJPY:** before={'step_points': 24.0, 'gap_minutes': 1.0}  after={'step_points': 14.0, 'gap_minutes': 1.0}
- **XAUUSD:** before={'step_points': 1520.0, 'gap_minutes': 4322.0}  after={'step_points': 15.0, 'gap_minutes': 1.0}
- **US500:** before={'step_points': 1743.0, 'gap_minutes': 4381.0}  after={'step_points': 0.0, 'gap_minutes': 1.0}
- **US100:** before={'step_points': 11725.0, 'gap_minutes': 4381.0}  after={'step_points': 80.0, 'gap_minutes': 1.0}
- **US30:** before={'step_points': 2790.0, 'gap_minutes': 1.0}  after={'step_points': 50.0, 'gap_minutes': 1.0}
- **GER40:** before={'step_points': 10234.0, 'gap_minutes': 3001.0}  after={'step_points': 150.0, 'gap_minutes': 1.0}

## What could NOT be fetched (reported, not invented)
- **US2000** — backfill IMPOSSIBLE: Dukascopy `USSC2000IDXUSD` depth starts 2018-08-08, LATER than the existing MT5 start (2018-01-23). No pre-existing history to add; not attempted.
- **BTCUSD** — skipped per task scope (crypto handled elsewhere; MT5 first bar is a synthetic aggregate).
- **Index depth floors** — US500 backfill only to 2012-01-16; US100/US30/GER40 only to 2013-01-01 (Dukascopy `startHourForTicks`). No CFD index data exists before those dates at the source.
- **Pre-2007** — FX/metals deep target capped at 2007-01-01 by design (depth ≥2003 exists but out of scope).
- **Legacy broken files (pre-existing, untouched):** `data/ftmo_research/eurusd_m1_spread.parquet` is corrupt (no parquet footer) and `data/ftmo_research/EURUSD_m15.parquet` is a 4-byte empty placeholder — both are derived re-exports, NOT inputs to this splice; left as-is.
- **Download year failures:** none (every fetched symbol-year passed the OHLC guard).

## P3 economic calendar
- `calendar/economic_calendar_2018_2026.csv` — **74543 events**, 2018-01-01→2026-06-07, 9 currencies, impact LOW/MED/HIGH.
- **Source:** TradingView economic-calendar API (no key; gray-area ToS — FLAGGED). Forex Factory historical was Cloudflare-blocked (403); faireconomy serves only the current week. NOT merged into existing calendars. See `calendar/calendar_gap_report.md`.

## Validation
- **Per instrument (all 15 PASS):** strictly-increasing true-UTC, 0 dups, 0 OHLC violations, 0 negative spreads, overlap close-corr **≥0.99997** (several =1.0), gap report — see `manifest.csv` / `reports/assembly_report.json`.
- **Spot-checks vs `dukascopy-node`** (random backfill days, 2 rounds, all instruments): **0 OHLC mismatches everywhere, max|Δ|=0.0** → decoder + splice + tz verified on real data.
  - FX/metals: `mine`≈`tv` (1440/day; small shortfalls = legitimate no-tick minutes).
  - Indices: `mine`<`tv` by design — candle+range filter keeps session/active bars (consistent with the existing MT5 index session-hours coverage); tick-aggregation (`tv`) additionally counts flat-ticked overnight minutes. Not a hole.
- **Gap classification:** all multi-day gaps confirmed legitimate — weekends, holidays (New Year/Christmas/Easter), AUDUSD 2007–2010 thin liquidity, index session closes, or the flagged pre-existing FTMO existing-data holes (GER40 2018, US30 2019-08). No download-induced holes remain (the 503-drop class was found, fixed, and the affected years re-fetched).