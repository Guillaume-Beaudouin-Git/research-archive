# DATA AUDIT MANIFEST — market / macro / calendar
**Scope:** strictly READ-ONLY inventory + provenance + quality of all existing OHLCV, macro and
calendar data under `<HOME>/Desktop/Algo_claude`.
**Date:** 2026-06-07 · **Mode:** read-only (no data file created/edited/moved/deleted; downloads = none).
**Reproducible from:** `audit/scripts/{schema_sweep,mt5_fingerprint,macro_calendar,assemble_table}.py`
(intermediate JSON in `audit/_intermediate/`). Reader env: `…/Unholy returns/Python3.12.9/myenv` (pandas 3.0.2 / pyarrow 24).

---

## ★ SOURCE VERDICT (read this first)

> ### The primary intraday OHLCV is a **LIVE MT5 BROKER export from FTMO‑Demo** — **NOT** Dukascopy reformatted.
> **Confidence: VERY HIGH** (artifact‑level proof + schema + 3 independent empirical fingerprints converge).
>
> The estate is **MIXED but cleanly segregated by source** — there is more than one dataset and they do **not** overlap in storage:
>
> | Dataset | Location | Source | Resolution | Time basis | Spread col |
> |---|---|---|---|---|---|
> | **Primary panel (FX+indices+XAU+BTC)** | `data/panels/m5_indices/*_M1.csv`, `*_M5.csv` | **MT5 / FTMO‑Demo (live)** | M1 + M5 | **EET/EEST server (mislabeled UTC)** | **real, populated** |
> | Crypto panel | `data/panels/m5_indices/binance/*_M1.csv` | Binance Spot REST | M1 | true UTC | const 0 |
> | Dukascopy M5 cache | `Forex/data/cache/dukascopy_m5/*.parquet` | **Dukascopy bi5→M5** | M5 | true UTC | **none** |
> | Dukascopy M1 raw | `data/raw/dukascopy_{EURUSD,GBPUSD}_*.parquet` | **Dukascopy M1** | M1 | true UTC | **none** |
> | Derived EURUSD | `data/ftmo_research/EURUSD_m1/m5.parquet` | re‑export of the MT5 EURUSD CSV | M1/M5 | naive (server) | none (OHLC only) |
> | Daily store | `data/oxfordstrat_109/ohlc/*.parquet` | MT5‑resample + yfinance + 2000‑panel | D1 | UTC‑day cutoff | median/day |
> | Daily futures | `data/mtf_survey/raw/prices_*_F.parquet` | yfinance `=F` | D1 | naive | — |
> | Macro | `data/raw/fred_*.parquet` | FRED | D1 (business) | naive | — |
>
> **`CALIBRATE_SPREAD` downstream = `TRUE`.** Existing primary = MT5‑live carrying a *real* broker spread that
> varies by instrument (FX raw/ECN‑tight, indices round‑clustered). Any backfill from the Dukascopy caches (which
> carry **no spread** and are in **true UTC**) is *not* a homogeneous source: it requires (a) synthesizing/calibrating a
> spread to the FTMO raw feed, **and** (b) a +2h/+3h time shift to align with the panel's server clock.

### Top caveats (each detailed below)
1. **Timestamps are NOT UTC.** The `timestamp_utc` column on every MT5 panel file is **broker server time = EET/EEST (UTC+2 winter, UTC+3 summer)**. Empirically proven (US cash‑open volume spike sits at 16:30 *labeled* in **both** winter and summer) and corroborated by the repo's own prior `ftmo_3strats` audit. **Shift −2h/−3h before any UTC‑anchored logic.**
2. **2 broken files:** `data/ftmo_research/eurusd_m1_spread.parquet` is **corrupt** (no parquet footer); `data/ftmo_research/EURUSD_m15.parquet` is **4 bytes (empty)**.
3. **FX crosses are stale.** The 9 FX crosses end **~2025‑05/06**; EURUSD + 5 indices + XAUUSD + BTCUSD run to **2026‑05‑29**. Re‑export needed to extend crosses.
4. **BTCUSD (MT5) first bar (2018‑11‑20) is a synthetic aggregate** (tick_vol 10.8 M, intra‑bar range 4298→5044) — discard row 1.
5. **FX spread is ECN‑tight and touches 0** — that is the FTMO *raw* feed, **not** evidence of Dukascopy. The anti‑Dukascopy proof is structural (spread column exists at all + real_volume column + server time + the `.mq5` exporters), not the spread magnitude.

---

## §0 Discovery — data groups, sizes, resolution

| Group | Path | Files | Size | Resolution | Source (verdict) |
|---|---|---|---|---|---|
| **MT5 FTMO panel** | `data/panels/m5_indices/*.csv` (top level) | 17 FX/idx + 4 idx‑M5 + wide panels | ~2.7 GB | **M1**, some **M5** | MT5/FTMO‑Demo |
| Binance crypto | `…/m5_indices/binance/*_M1.csv` (+ top‑level `BTCUSD_M1.csv` is MT5) | 17 | ~3.1 GB | M1 | Binance Spot |
| Panel parquet | `…/m5_indices/{m1,m5,EURUSD_m1,…}_panel.parquet` | 6 | ~290 MB | M1/M5 | derived from MT5 CSV |
| Dukascopy M5 | `Forex/data/cache/dukascopy_m5/*.parquet` | 143 (17 syms) | 255 MB | **M5** | Dukascopy bi5 |
| Dukascopy M1 raw | `data/raw/dukascopy_*.parquet` | 12 | ~210 MB | **M1** | Dukascopy |
| Derived EURUSD | `data/ftmo_research/EURUSD_*.parquet` (+ corrupt spread, empty m15) | 4 | 95 MB dir | M1/M5 | re‑export of MT5 EURUSD |
| Daily OHLC store | `data/oxfordstrat_109/ohlc/*.parquet` | 30 (`_coverage.csv`=40 instr) | 4.4 MB | **D1** | mixed (tagged) |
| Daily futures | `data/mtf_survey/raw/prices_*_F.parquet` | 24 | 5.5 MB | D1 | yfinance `=F` |
| NQ intraday | `data/raw/NQ_1min_databento_2010‑2026.parquet` (+ Kaggle CSV) | 2 | 109 MB | M1 | Databento / Kaggle |
| Macro (FRED) | `data/raw/fred_*.parquet` | 13 (6 series) | ~0.7 MB | D1 | FRED |
| Equities/vol | `data/raw/yf_*.parquet` | 274 | ~50 MB | D1 | yfinance |
| Calendar | `data/panels/economic_calendar.csv`, `Forex/data/news_events_2020_2025.csv` | 2 (+1 dup) | small | event | curated |

Distinct OHLCV **resolutions co‑exist** (M1 MT5 panel **and** M5 Dukascopy **and** M1 Dukascopy **and** D1 stores) — kept separate throughout.

---

## §1 Provenance artifacts (most decisive)

**MT5 exporters** (`data/panels/m5_indices/*.mq5`, with a compiled `export_fx_m5.ex5`):
- `export_fx_m5.mq5` (writes the 8‑col schema incl. `real_volume`):
  > *"Univers FTMO calibré sur **FTMO‑Demo** (server name observable in MT5 → Outils → Options → Serveur). Noms vérifiés via inspection du cache **bases/FTMO‑Demo/history/** — 2026‑06‑01."*
  > *"SYMBOLES ABSENTS du broker FTMO‑Demo … FRA40, JP225, AUS200, EU50, HK50, USOIL, UKOIL, NGAS … → utiliser **Dukascopy (background)** pour ceux‑ci."*
  Reads bars via `CopyRates(sym, PERIOD_M1, …)` → this is a **live MT5 terminal pull**, not a file reformat.
- `export_new_m1.mq5` (GER40.cash, EURUSD, XAUUSD, BTCUSD) and `export_m1_news.mq5` (US500/100/30/2000.cash) — 7‑col variants. *All files on disk carry the 8‑col `real_volume` header*, i.e. `export_fx_m5.mq5` is the one that wrote the canonical CSVs.
- `ingest_m5.py` docstring: *"Ingère les CSV exportés par **export_m5.mq5** (ou l'export GUI MT5)."*

**Dukascopy downloaders** (separate, explicitly segregated):
- `Forex/data/dukascopy_downloader_m5.py`: pulls `https://www.dukascopy.com/datafeed/{code}/…h_ticks.bi5`, ticks→M5, cols `open,high,low,close,tick_count` (no spread). Output `Forex/data/cache/dukascopy_m5/`.
- `_downloads_logs/run_dukascopy_p2.sh`: `SKIP=( EURUSD GBPUSD US500 US100 US30 US2000 GER40 XAUUSD )` — *"Skip what's already exported from MT5"*. Log confirms USOIL/UKOIL/NGAS/UK100/XAGUSD pulled OK; XPTUSD/XPDUSD/ex‑US indices failed (wrong codes).
- `data/raw/dukascopy_{EURUSD,GBPUSD}_*.parquet` produced by `Forex/research/archived/london_orb_v1/_ic_feasibility/fetch_data*.py` (older M1 pull, 2020‑2024).

**Binance:** `Forex/data/binance_klines_downloader.py` → *"spread = 0 (Binance Spot = no broker spread)"*, `tick_volume = number_of_trades`. Log: 17 symbols 2018‑2026.

**Git:** the large data files are git‑ignored/untracked (`git status` shows `??`), so file content has no commit history; provenance rests on the scripts above (all tracked) + the empirical fingerprint.

---

## §2 Schema & dtypes (per group)

| Group | Columns | ts dtype / tz | Homogeneous? |
|---|---|---|---|
| **MT5 panel CSV** | `timestamp_utc, open, high, low, close, tick_volume, spread, real_volume` | text `YYYY.MM.DD HH:MM:SS` (dotted MT5), **EET/EEST** | ✔ (all 22 files; 8 cols) |
| Binance CSV | `timestamp_utc, open, high, low, close, tick_volume, spread` | text `YYYY-MM-DD HH:MM:SS`, **UTC** | ✔ (7 cols, no real_volume) |
| Dukascopy M5 | `open, high, low, close, tick_count, time` | `timestamp[ns, UTC]` | ✔ |
| Dukascopy M1 raw | `open, high, low, close, volume, timestamp` | `timestamp[us, UTC]` | ✔ |
| ftmo_research EURUSD | `open, high, low, close` + `timestamp_utc` index | `timestamp[ns]` naive | OHLC‑only (no spread) |
| oxfordstrat D1 | `open, high, low, close[, spread]` idx `Date` | `timestamp[ns]` naive | spread only on M1‑resampled rows |
| mtf futures | `Adj Close, Close, High, Low, Open, Volume` idx `Date` | naive | ✔ (yfinance) |
| FRED | one value col per series + date | naive D1 | per‑series files |

Deviation from the canonical `…,tick_volume,spread,real_volume`: **only the MT5 panel matches it fully**; Binance drops `real_volume`; Dukascopy/derived/daily carry their own schemas (documented above).

---

## §3 Source fingerprinting (empirical — the decider)

Reference instrument **EURUSD** and the full FX/index set (`audit/instrument_table.csv`, `audit/_intermediate/mt5_fingerprint.json`).

**SPREAD** — *units:* MT5 integer **points** (`IntegerToString(rates.spread)`), 1 point = 10⁻⁵ price for 5‑digit FX (=0.1 pip).

| Instr | min | p5 | p50 | p95 | max | min(13‑16 UTC) | mult‑of‑5 frac | shape |
|---|---|---|---|---|---|---|---|---|
| EURUSD | 0 | 0 | **1** (0.1 pip) | 11 | 363 | **0** | 0.05 | raw/ECN, touches 0 |
| GBPUSD | 0 | 0 | 4 | 19 | 770 | 0 | 0.14 | raw |
| USDJPY | 0 | 0 | 3 | 15 | 395 | 0 | 0.14 | raw |
| AUDJPY | 0 | 4 | 10 | 50 | 549 | 0 | 0.15 | raw |
| US500 | 0 | 28 | 45 | 70 | 390 | 0 | 0.45 | round‑clustered |
| US100 | 0 | 60 | 140 | 220 | 2440 | 0 | **0.96** | strong round‑cluster (60/140/150/220) |
| GER40 | 0 | 55 | 139 | 790 | 3040 | 0 | 0.74 | round‑cluster |
| XAUUSD | 0 | 5 | 18 | 40 | 1744 | 0 | 0.19 | broker spread |
| BTCUSD(mt5) | 0 | 100 | 900 | 5275 | 81325 | 0 | 0.53 | wide, clustered 900/1200 |

→ Spread is **present, integer‑points, instrument‑specific, with a fat upper tail**. FX is *raw/ECN‑tight and can hit 0*; indices show **round‑number clustering** (the classic MT5 broker quoting artifact). **No file has an all‑zero spread** except where hardcoded (Binance). Dukascopy carries **no spread column at all** → the mere presence of this populated `spread` is decisive against the "Dukascopy reformatted" hypothesis.
*Spread floor:* `min(liquid hrs)=0` for every MT5 FX → **no markup floor** (raw feed), reported `spread_floor_detected=FALSE`.

**tick_volume** (median, 13:00–16:00 UTC liquid window): FX **31–95**, indices 21–95, XAU 80 — i.e. MT5 *tick counts* (tens per minute). Binance ETHUSD/BTCUSD **469 / 921** = `n_trades`, ~10× higher and a different quantity. Distinct scales confirm distinct sources.

**real_volume:** all‑zero for every MT5 instrument **except XAUUSD** (max 467,462 — FTMO supplies aggregated volume for gold only). Binance has **no** real_volume column. (All‑zero real_volume is consistent with a CFD broker feed; the non‑zero XAU is a useful exception to note.)

**digits (close):** FX = **5** (real 5‑digit), JPY pairs also written at 5 (effective 3‑digit price). Indices/XAU/BTC are *formatted* to 5 by the EA but are not 5‑digit instruments (the M5 index files are written at 2). Binance ETH/BTC = 2, SOL = 4. *(The `spread_median_pips` column in the CSV is therefore only meaningful for the 10 FX rows.)*

**Session boundaries (UTC label):** weekly **open Mon 00:00–00:02**, **close Fri 23:54–23:58** (FX); daily server rollover gap clusters at **23:54 labeled** (≈21:54 UTC) — the broker's ~22:00‑UTC day boundary. Indices open **Mon 01:05**, close **Fri 23:49**. BTC(mt5): open **Sun 00:00**, close **Sat 00:00** (a ~24 h FTMO weekend halt; Binance has none).

**Timezone resolution (empirical):** US500 minute with max total `tick_volume`:
- winter Jan‑2024 → **16:30** label · summer Jul‑2024 → **16:30** label (cash open 09:30 ET).
- True UTC would put it at 14:30 (winter) / 13:30 (summer). A constant **16:30 across DST ⇒ EET/EEST server time** (ET↔EET offset is fixed at +7 h). ⇒ **`timestamp_utc` is mislabeled; data are GMT+2/+3.** (Matches the repo's `06_mt5_tz_resolve.py` design and the `ftmo_3strats` finding "MT5 timestamps GMT+3 mislabeled utc".)

### Per‑instrument best guess → **OVERALL VERDICT**
- All 17 `data/panels/m5_indices/*_M1/_M5.csv` + duplicates → **MT5 / FTMO‑Demo (live), server‑time** · *very high*.
- `…/binance/*` → **Binance Spot, UTC** · *certain* (downloader + spread≡0).
- `Forex/data/cache/dukascopy_m5/*` + `data/raw/dukascopy_*` → **Dukascopy, UTC** · *certain*.
- **The "existing OHLCV" the question targets = MT5‑live, not Dukascopy‑reformatted. Confidence VERY HIGH.**

---

## §4 Coverage map (per instrument)

Full numbers in `audit/instrument_table.csv`. Completeness = rows ÷ (business‑days × bars‑per‑24h‑×‑5); for non‑24h indices this is a lower bound (it counts only the hours they trade).

**Deep history (start 2018):** EURUSD, USDJPY, USDCAD, AUDUSD, US500, US100, US2000(2018‑01‑23), GER40, XAUUSD, BTCUSD(2018‑11‑20). **US30** starts 2019‑02‑08.

**SHORT pairs (first ts > 2021‑01‑01) — CONFIRMED:**
- **2021‑12:** GBPUSD & NZDUSD & USDCHF **2021‑12‑14**, EURGBP **2021‑12‑15**.
- **2022‑04:** AUDJPY & EURJPY **2022‑04‑06**.

**STALE crosses (coverage gap):** the 9 FX crosses end **~2025‑05‑30 / 06‑26**, whereas EURUSD + 5 indices + XAUUSD + BTCUSD end **2026‑05‑29**. The cross panel is ~11 months behind and needs re‑export.

**Completeness:** FX **≈99%** (true 24×5). Indices vary by session coverage: US500 51.5%, US100 52.3%, GER40 47.6% (RTH‑ish) vs US30 91.6%, US2000 91.6% (near‑extended‑hours). XAU 93.3%. BTC(mt5) 119.8% & Binance ≈140% (>100% because the 24×5 denominator understates 6–7‑day crypto).

**Dukascopy ∩ MT5 OVERLAP (for later spread calibration):** the Dukascopy M5 cache holds **USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD, EURGBP, EURJPY, AUDJPY (2018‑2026)** — the *same* FX crosses the MT5 panel has (with spread). Clean overlap window ≈ **2022‑04 → 2025‑06** (both present) → use it to fit a Dukascopy→FTMO spread model and a +2/+3 h time map.

---

## §5 Data quality (counts)

- **Duplicate timestamps:** **0** across all 22 fingerprinted instruments.
- **Non‑monotonic:** 0 (files are sorted ascending).
- **OHLC validity:** **0** violations everywhere — `high<max(o,c,l)=0`, `low>min(o,c,h)=0`, `high<low=0`, non‑positive prices `=0`. Clean.
- **NaNs (o/h/l/c):** 0 in the MT5/Binance price columns.
- **spread<0:** 0. **spread==0:** by design varies — FX 0.4%–33% of bars (EURUSD 33%, raw feed); indices 1–35%; Binance 100% (hardcoded).
- **Gaps:**
  - *Weekend* (expected): the Fri≈23:5x → Mon≈00:0x (FX) / Mon 01:05 (indices) breaks.
  - *Intra‑week:* FX **131–372** (mostly the daily ~22:00 UTC rollover + holidays). Indices **2,083–6,491** — dominated by *normal overnight session closes* (cash indices aren't 24 h), not anomalies. Largest intra‑week gaps are holiday closures (e.g. Dec 25, Jan 1) and the deep‑history start.
  - *Server‑midnight rollover gap present:* yes — modal intra‑week small‑gap time = **23:54 labeled** (FX) / **23:49** (indices) ≈ the 22:00‑UTC broker day boundary.
- **close→open jumps:** max |1‑bar log‑gap| — FX 0.6–1.7%, indices 4–16% (GER40 0.156 = weekend/holiday gap), **BTC(mt5) 0.308 = the bogus first bar**. (`gap_abs_z>10` counts are large only because the per‑minute gap variance is ~0, making the z‑test hypersensitive; not a defect.)
- **Broken / empty files:**
  - `data/ftmo_research/eurusd_m1_spread.parquet` — **CORRUPT** ("Parquet magic bytes not found in footer"). This was the only EURUSD‑with‑spread parquet; spread must come from `panels/m5_indices/EURUSD_M1.csv`.
  - `data/ftmo_research/EURUSD_m15.parquet` — **4 bytes (empty placeholder)**.
  - `data/raw/NQ_1min_2022‑12‑26_2025‑12‑11.parquet` — exactly **1,048,575 rows** (= 2²⁰−1), a spreadsheet row‑cap truncation artifact; prefer the Databento file (`NQ_1min_databento_2010‑2026.parquet`, 5.12 M rows).
  - `data/ftmo_research/audit/` holds 30 *research* trade‑set parquet (not raw market data).
- **Duplication (not a defect, note it):** `data/ftmo_universe/intraday_m1/{fx,indices,metals,crypto}/*.csv` are **symlinks (0 B)** to the panel CSVs; `data/ftmo_research/EURUSD_m1.parquet` ≡ `…/m5_indices/EURUSD_m1_panel.parquet` (same 2,368,782 rows, OHLC‑only, 2020+ clip).

---

## §6 Macro (FRED) — `data/raw/fred_*.parquet` (13 cached files, 6 series, business‑day D1)

| Series | Meaning | First | Last | Rows |
|---|---|---|---|---|
| **DTB3** | 3‑mo T‑bill (RF for excess returns) | 2000‑01‑03 | **2026‑05‑26** | 6887 |
| **T10Y2Y** | 10y‑2y term spread | 2003‑01‑01 | 2026‑05‑22 | 6103 |
| **DGS3MO** | 3‑mo Treasury | 2003‑01‑01 | 2026‑05‑21 | 6102 |
| **DTWEXBGS** | USD broad index | 2006‑01‑02 | 2026‑05‑15 | 5315 |
| **VIXCLS** | VIX | 2007‑01‑01 | 2026‑05‑21 | 5059 |
| **BAMLH0A0** | ICE BofA US HY OAS (credit) | 2007‑01‑01 | 2026‑05‑22 | 5071 |

NaN coverage is low (business‑day series with holiday NaNs only). The 13 files are redundant hashed cache copies of these 6 series (widest‑range per series shown). All current to ~2026‑05. **No CBOE PCR / NAAIM here** — those live in `data/raw/http_*.parquet` (3 files).

---

## §7 Calendar

Two distinct artifacts (+1 duplicate):

**A. `data/panels/economic_calendar.csv`** — curated, **high‑impact‑only, USD‑only**.
- Cols `date, time_utc, event, currency, impact, datetime_utc`; **231 rows**; **2020‑01‑03 → 2026‑05‑12**; **~36 events/yr**.
- `impact`: **HIGH ×231** (100%). `currency`: **USD ×231**. `event`: **NFP 77, CPI 77, FOMC 52, GDP 25** → confirms NFP/CPI/FOMC focus; sparse.
- **Exact duplicate** at `data/ftmo_universe/news/economic_calendar.csv` (231 rows, identical).

**B. `Forex/data/news_events_2020_2025.csv`** — Strategy‑F2 multi‑currency calendar (`#`‑commented header).
- Cols `date, time_utc, event_type, currencies_affected, source`; **760 events**; **2020‑01‑03 → 2025‑12‑19** (does **not** reach 2026); **~128/yr**.
- By currency: GBP 338, USD 193, EUR 120, AUD 61, JPY 48. By event: NFP_US/CPI_US/UK_CPI/UK_EMPLOYMENT/UK_GDP/UK_RETAIL/GERMAN_IFO (72 each), RBA/BOE/FOMC/ECB/BOJ rate decisions. No `impact` column (implicitly high‑impact).

---

## Appendix — pointers & how to reproduce
- Per‑instrument table: **`audit/instrument_table.csv`** (55 rows: 22 fingerprinted + 33 inventory).
- Raw metrics: `audit/_intermediate/{mt5_fingerprint,schema_sweep,macro_calendar}.json`, `fingerprint_stdout.log`.
- Re‑run (read‑only): `"<venv>/bin/python" audit/scripts/<script>.py`.
- Decisive source files to read: `data/panels/m5_indices/export_fx_m5.mq5` (broker = FTMO‑Demo), `_downloads_logs/run_dukascopy_p2.sh` (MT5↔Dukascopy split), `Forex/data/dukascopy_downloader_m5.py`, `Forex/data/binance_klines_downloader.py`, `data/oxfordstrat_109/code/build_ohlc_store.py` (daily lineage).
- **Next‑step (not done here — backfill prep):** before any backfill, (1) re‑export the 9 stale FX crosses to 2026; (2) shift MT5 panel time −2h/−3h (DST‑aware) or re‑pull with a UTC EA; (3) if extending FX with Dukascopy M5, fit spread on the 2022‑2025 overlap; (4) rebuild/repair `eurusd_m1_spread.parquet` and `EURUSD_m15.parquet`.
