# Track B — Commodity complex MANIFEST (Dukascopy M1, TRUE UTC)

**Output:** `data/deep_history_utc/<SYM>_M1.csv` · **Schema:** `timestamp_utc,open,high,low,close,tick_volume,spread,real_volume` (= existing XAUUSD), OHLC = Dukascopy BID, **TRUE UTC** (native, no shift). Pipeline reused from Track A (`duka_m1_backfill.py`: OCLH decode, per-instrument decimalFactor, `v<=0 AND h<=l` flat-drop, fail-loud-on-dropped-day, nw=8).

## Decoder gate (new decimalFactor families)
- df=1000 (WTI) and **df=10000 (copper, natgas — NEW)** vs `dukascopy-node`, days with down-bars: **0 OHLC mismatches**, max|Δ|=0.0. OCLH byte order confirmed for commodities.

## ⚠ Spread basis (honest — NOT validated MT5)
`ftmo_specs_full.csv` has **no spread column** (only digits/swap/commission/session) → spec-anchor unavailable. So:
- **XAGUSD = gold-proxy**: raw ECN spread × gold's hour-of-UTC ECN→MT5 multiplier (fitted on the 2024 FTMO-XAU vs Duka-XAU overlap).
- **all others = ECN_RAW_UNCALIBRATED**: raw Dukascopy ask−bid (instrument points = 1/decimalFactor).
> These commodity spreads are **ECN-or-proxied, NOT validated MT5**. Acceptable for a daily, cost-robust strategy (Ross Hook); **NOT** for intraday spread-sensitive use without a real FTMO overlap.
- `real_volume` = all-zero (Dukascopy has none). `tick_volume` = Dukascopy M1 candle volume (zero-fraction reported per instrument; some bars carry v=0 with a real range, kept via the h>l rule).

## Instruments

| sym | code | df | range (UTC) | rows | spread_basis | sprd_med | vol0% | mono/dups/ohlc✗ | spotcheck | gaps |
|---|---|--:|---|--:|---|--:|--:|---|---|--:|
| XAGUSD | XAGUSD | 1000 | 2003-08-08→2026-06-05 | 7290493 | gold-proxy (×X | 13 | 0.2904 | True/0/0 | 2d mism=0 | 120433 |
| USOIL | LIGHTCMDUSD | 1000 | 2013-01-01→2026-06-05 | 4434667 | ECN_RAW_UNCALI | 50 | 0.9779 | True/0/0 | 2d mism=0 | 36371 |
| UKOIL | BRENTCMDUSD | 1000 | 2010-12-02→2026-06-05 | 4579620 | ECN_RAW_UNCALI | 50 | 0.9378 | True/0/0 | 2d mism=0 | 36335 |
| NGAS | GASCMDUSD | 10000 | 2012-09-02→2026-06-05 | 3725891 | ECN_RAW_UNCALI | 107 | 1.0 | True/0/0 | 2d mism=0 | 172803 |
| COPPER | COPPERCMDUSD | 10000 | 2012-03-02→2026-06-07 | 4325524 | ECN_RAW_UNCALI | 39 | 0.997 | True/0/0 | 2d mism=0 | 107202 |
| SUGAR | SUGARCMDUSD | 1000 | 2017-10-02→2026-06-05 | 1047541 | ECN_RAW_UNCALI | 764 | 0.9997 | True/0/0 | 2d mism=0 | 21669 |
| COCOA | COCOACMDUSD | 1000 | 2017-10-20→2026-06-05 | 1006658 | ECN_RAW_UNCALI | 5718 | 0.9999 | True/0/0 | 2d mism=0 | 14866 |
| COFFEE | COFFEECMDUSX | 1000 | 2017-12-04→2026-06-05 | 1108493 | ECN_RAW_UNCALI | 387 | 0.4339 | True/0/0 | 2d mism=0 | 9483 |
| SOYBEAN | SOYBEANCMDUSX | 1000 | 2017-12-01→2026-06-05 | 1779222 | ECN_RAW_UNCALI | 1704 | 0.7908 | True/0/0 | 2d mism=0 | 51710 |
| COTTON | COTTONCMDUSX | 1000 | 2017-10-20→2026-06-05 | 1758811 | ECN_RAW_UNCALI | 196 | 0.5394 | True/0/0 | 2d mism=0 | 75758 |
| OJUICE | OJUICECMDUSX | 1000 | 2017-10-20→2026-06-05 | 511864 | ECN_RAW_UNCALI | 1138 | 0.9377 | True/0/0 | 2d mism=0 | 43044 |
| DIESEL | DIESELCMDUSD | 1000 | 2017-12-26→2026-06-05 | 2434631 | ECN_RAW_UNCALI | 900 | 1.0 | True/0/0 | 2d mism=0 | 43539 |

**Gaps note:** the `gaps` column = intra-week >2min gaps. High for commodities because (a) product-specific
RTH sessions (NOT 24×5 — e.g. COCOA 11:50-20:30, SOYBEAN split session) and (b) the `v<=0 AND h<=l` flat-drop
on mostly-zero-volume candles keeps only range-bars. These are **session/flat-period gaps, NOT data holes**
(spotcheck confirms 0 decode mismatch; the downstream EET daily resample is unaffected — daily OHLC = max/min
over the day). All series are strictly increasing, 0-dup, 0-OHLC-violation (1 corrupt COTTON bar dropped, reported).

## What could NOT be fetched (reported, not invented)
- **WHEAT, CORN — ABSENT on Dukascopy** (no instrument code in `instrumentMetaData`). Not fetched, not invented.
- **Depth floors (Dukascopy candle):** silver 2003-08, Brent 2010-12, copper 2012-03, natgas 2012-09, WTI 2013-01, all ags 2017. PRIORITY = breadth: shallow ags kept, floors reported.
- **No FTMO M1 overlap** for any new commodity (existing FTMO commodity = gold only) → no instrument got a validated MT5 spread calibration; silver is gold-proxied, the rest are raw ECN (flagged above).
- **ftmo_specs has no spread field** → option (b) spec-anchored calibration impossible.
- M5 Dukascopy caches exist (`Forex/data/cache/dukascopy_m5/` XAGUSD/USOIL/UKOIL/NGAS) but are M5, not M1 — not used; this delivers fresh M1.
- **Download failures (OHLC-guard/fetch_err):** none

## Scope
Commodities ONLY. FX/metals-gold/indices/crypto untouched and NOT re-fetched. No splice (net-new). No Ross-Hook re-test (separate Cowork step). Daily resample (EET server-day) is downstream.