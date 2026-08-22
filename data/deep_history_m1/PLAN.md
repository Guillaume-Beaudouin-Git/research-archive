# Deep-history M1 backfill — plan & decisions (frozen 2026-06-07)

## ⚠ TZ DIRECTION OVERRIDE (2026-06-07, supersedes the EET notes below)
Output is **TRUE UTC**, not EET. The existing MT5 files (broker EET/EEST mislabeled
`timestamp_utc`) are localized `Europe/Bucharest`→UTC (ambiguous=infer w/ DST fallback,
nonexistent=shift_forward; DST-seam bars flagged, never crash). Dukascopy backfill is
already UTC and left as-is. Splice + spread hour-of-day bucketing are all in TRUE UTC.
The output column is still named `timestamp_utc` but now holds TRUE UTC. Rationale:
aligns OHLCV with the true-UTC economic calendar + FRED macro; honest labels.
Final outputs → `data/deep_history_utc/` (scripts+cache stay in `data/deep_history_m1/`).
Gates passed: GATE 1 (decoder vs dukascopy-node, 0 mismatch on 4 df families);
GATE 2 (EURUSD 2010+2024 full pipeline, overlap corr 0.999999).

## Source / engine
- Source: Dukascopy per-day **M1 candle** bi5 endpoint
  `https://datafeed.dukascopy.com/datafeed/{CODE}/{YYYY}/{MM-1:02d}/{DD:02d}/{BID|ASK}_candles_min_1.bi5`
- Record = 24 bytes `>iiiiif` = (time_seconds_from_UTC_midnight, O,H,L,C as int/decimalFactor, volume f32).
- Download bid+ask per day (one pass). Drop flat minutes (bid volume == 0) to match MT5 "bar iff ticked".
- ~520 files/symbol-year (bid+ask) vs ~6240 for ticks → ~12× faster.

## Verified facts
- Existing schema (AUTHORITATIVE, never mutate): `timestamp_utc,open,high,low,close,tick_volume,spread,real_volume`,
  timestamp `YYYY.MM.DD HH:MM:SS`, OHLC = **bid** printed `%.5f`, spread = **int in MT5 points**, real_volume = 0.
- Existing files are **broker time EET/EEST (UTC+2 winter / +3 summer, EU DST)** mislabeled `timestamp_utc`.
  Verified: Jun 2018 offset +180 / Jan,Mar11,Oct29 +120, all corr ≥ 0.99998 → tz = `Europe/Bucharest`.
- decimalFactor & MT5 point per instrument:
  5-dp FX (EURUSD/GBPUSD/EURGBP/NZDUSD/USDCHF/AUDUSD/USDCAD): df 1e5, point 1e-5, round 5dp.
  JPY (USDJPY/EURJPY/AUDJPY): df 1e3, point 1e-3, round 3dp.
  XAUUSD: df 1e3, point 1e-2 (MT5 Digits=2), round 2dp.
  Indices (US500/US100/US30/GER40): df 1e3, point 1e-2, round 2dp.

## Targets & depth
P1 crosses (backfill before existing start + forward gap to today):
  GBPUSD(exist 2021-12-14→2025-06-03), EURGBP(2021-12-15→2025-06-03), NZDUSD(2021-12-14→2025-06-03),
  USDCHF(2021-12-14→2025-05-30), AUDJPY(2022-04-06→2025-06-26), EURJPY(2022-04-06→2025-06-03).
  Dukascopy depth all ≥2003 → target_start 2007-01-01.
P2 FX/metals (backfill 2007→2018 + forward gap):
  EURUSD(2018-01-02→2026-05-29), AUDUSD(2018-01-02→2025-06-03), USDCAD(2018-01-02→2025-06-03),
  USDJPY(2018-01-02→2025-05-30), XAUUSD(2018-01-02→2026-05-29).
P2 indices (backfill to earliest available):
  US500 (USA500IDXUSD, depth 2012-01-16), US100 (USATECHIDXUSD, 2013-01-01),
  US30 (USA30IDXUSD, 2013-01-01), GER40 (DEUIDXEUR, 2013-01-01).
  US2000: Dukascopy USSC2000IDXUSD starts **2018-08-08** > existing 2018-01-23 → **BACKFILL IMPOSSIBLE**, report gap.
  BTCUSD: skip (per task).
- Calibration/validation year: download Dukascopy **2024** (full year, inside everyone's existing range)
  for hour-of-day spread calibration + overlap correlation check.

## Spread calibration (updated 2026-06-07)
- On 2024 overlap, per instrument, bucketed by hour-of-day (**UTC**): fit BOTH additive
  (MT5 ≈ Duka + offset_h) and multiplicative (MT5 ≈ Duka × ratio_h); select per instrument
  by lower MAE on a held-out (last-30%-by-time) slice; refit chosen on full overlap; apply
  to ALL Duka rows (pre-existing backfill + post-existing top-up). FX tends to pick additive
  (offset≈0, raw≈raw). Indices optionally rounded to the existing spread tick.
- Never modify existing (post-splice) spreads.

## Output (NEW dir, never overwrite)
- `data/deep_history_utc/<SYM>_M1.csv` = existing rows (values verbatim, ts→true UTC) +
  calibrated Duka backfill (before & after). Schema/dtypes/units identical to existing.
- `data/deep_history_m1/_cache_duka/<SYM>_<YEAR>.parquet` = raw Duka (true UTC) cache for resume
  (`_failed/` holds OHLC-guard-failed years, never spliced).
- `data/deep_history_m1/reports/`: assembly_report.{json,csv}, download_status*.json.
- `data/deep_history_utc/`: MANIFEST.{md,csv}.
- `data/deep_history_utc/calendar/`: P3 economic calendar (TradingView API; FF was Cloudflare-blocked)
  + gap report. NOT merged into existing calendars.

## tick_volume caveat
Pre-splice tick_volume = round(Dukascopy M1 bid volume, millions) — NOT an MT5 tick count.
Different scale than post-splice rows. Documented in MANIFEST (honest, dtype-matched int).
