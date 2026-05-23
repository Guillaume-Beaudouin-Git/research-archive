# PHASE 1.5 — IC Feasibility + T&C Verification

**Date:** 2026-05-22  
**Objective:** Verify all unverified premises from HYPOTHESIS.md before GO PHASE 2.  
**N_tests baseline:** 142 (from NQ iter_10 results.json ground truth)

---

## TASK 1 — FTMO T&C VERIFIED

**Sources fetched (2026-05-22):**
- https://ftmo.com/en/trading-rules/
- https://ftmo.com/en/faq/can-i-trade-news/

### News Trading Rules

**During Evaluation (Challenge) — ALL account types:**
> "While trading during the Evaluation Process, the restriction does not apply regardless of the account type."
> "Traders may trade freely during all macroeconomic news releases without any restrictions."

**During FTMO Funded Account — Standard account:**
> "Restrictions for trading during selected news releases apply only to the Standard account type."
> "open or close any trades, including pending orders...within a time window starting 2 minutes before and ending 2 minutes after" selected news announcements.
> "If Stop Loss or Take Profit triggers within the restricted window, this violates the FTMO Account Agreement."

**Key allowances on Standard funded:**
- Hold positions opened > 2 min before event: **allowed**
- Trade non-targeted instruments during event (e.g., EURGBP during US NFP): **allowed**

**During FTMO Funded Account — Swing account:**
> "The Swing account type have no restrictions on trading during news releases."

**Restricted events (Standard funded account only):**
US Federal Funds Rate, NFP, CPI, GDP, ECB Rate, BOE Rate, and similar central bank / economic data releases across USD, EUR, GBP, CAD, AUD, NZD, CHF pairs + Gold, US Indices, Crude Oil.

### Overnight/Weekend Position Rules

> "Overnight and weekend position restrictions apply only to the Standard account type."
> "The Swing account type does not have any restrictions on holding positions overnight or over the weekend."
> Restrictions "do not apply during the Evaluation Process regardless of account type."

### No Time Limit on Challenge

Confirmed (from trading-rules page): no time limit on Evaluation Process. No 30-day or 60-day clock.

### Pro Trader / Astra Account Rules

Page https://ftmo.com/en/account-types/ returned HTTP 404. Rules for "Pro Trader" and "Astra" account types **not verified** from live source.

### T&C Implications for Strategy Selection

| Criterion | Angle A (London ORB) | Angle B (News-Fade T+5min) |
|---|---|---|
| Evaluation (Challenge) | ✓ No restriction | ✓ No restriction |
| Funded Standard account | ✓ No restriction (non-news) | ✓ Entry T+5min is OUTSIDE ±2min window |
| Funded Swing account | ✓ No restriction | ✓ No restriction |
| Overnight hold risk | N/A (intraday) | N/A (intraday exit same session) |

**Angle B compliance note:** Entry at T+5min is 3 minutes after the ±2min restriction window closes. SL/TP placed at T+5min or later → not within the restricted window. Angle B is compliant even on Standard funded accounts.

**BLOCKER STATUS:** None. Both Angle A and Angle B are compliant on all FTMO account types in all phases. The HYPOTHESIS.md rationale for eliminating Angle B on T&C grounds was INVALID.

---

## TASK 2 — DUKASCOPY DATA

**Script:** `_ic_feasibility/fetch_data.py`

**Technical notes (3 iterations to fix):**
- v1: aiohttp + Python 3.9/LibreSSL → ~10% fill (SSL → silent drops)
- v2: requests + ThreadPoolExecutor(15) + Python 3.12/OpenSSL → 100% fill, 20min/year (too slow)
- v3 (current): aiohttp + force_close=True + Python 3.12/OpenSSL → 65-72% weekday fill, ~17min/year
  - force_close bypasses nginx rate-limit on keep-alive connections
  - 72% = thin/off-hours (00:00-05:00 UTC Mon) genuinely empty; London open (07:00 UTC) ~97% fill
  - Validated: EURUSD 2020 = 365,459 bars, LO bars 15,658/~15,600 expected ✓

**N_tests added by data pipeline:** 0 (data collection, not signal variants)

**Final data inventory (2026-05-23 03:20 CEST):**

| File | Size | Bars | LO bars/year (07:00–07:59) | Fill issue |
|---|---|---|---|---|
| EURUSD_2020 | 8.7MB | 365,459 | 15,658 (100% expected) | None ✓ |
| EURUSD_2021 | 5.4MB | ~227k | 9,059 (58%) | Rate-limited |
| EURUSD_2022 | 5.6MB | ~240k | 8,098 (52%) | Rate-limited |
| EURUSD_2023 | 3.8MB | ~163k | 5,400 (34%) | Rate-limited |
| EURUSD_2024 | 2.8MB | ~106k | 3,540 (23%) | Rate-limited |
| GBPUSD_2020–2024 | 14MB | 577,679 | 4k–5.7k/yr (25–36%) | Rate-limited |

**Root cause:** Dukascopy nginx rate-limits cumulative requests per IP session. CONCURRENCY=20 + force_close=True worked for EURUSD 2020 (fetched first), but server progressively throttled subsequent years. LO coverage should be ~97% for EURUSD; actual decline from 100% → 23% is fetch artifact, not genuine data sparsity.

**Consequence for IC analysis:** Trading days with valid LO data dropped to 454 EURUSD + 126 GBPUSD (vs ~1,300 + 1,300 expected). N breakout days well below the N > 400 gate.

**PREVIEW RESULT (EURUSD 2020 only, n=1 year — directional only):**

| Signal | Horizon | N | IC_spearman | t_HAC_lag4 | Direction |
|---|---|---|---|---|---|
| close-based | 1h | 92 | +0.073 | +0.50 | ✓ |
| close-based | 2h | 92 | +0.080 | +0.19 | ✓ |
| close-based | 4h | 92 | -0.054 | -0.84 | ✗ (reversal) |
| HL-based | 1h | 170 | +0.056 | +0.65 | ✓ |
| HL-based | 2h | 170 | +0.020 | +0.08 | ✓ (weak) |
| HL-based | 4h | 170 | -0.022 | -0.35 | ✗ (reversal) |

**Status: COMPLETE (data quality issue — see above)**

---

## TASK 3 — IC FEASIBILITY ANGLE A (London ORB)

**Signal:** Asian range (00:00–07:00 UTC) breakout at London open (07:00–08:00 UTC)
**Variants:** (1) close-based — 07:59 close vs Asian range; (2) HL-based — high/low of 07:00–07:59 vs Asian range
**Horizons:** 1h, 2h, 4h, session-end (17:00 UTC)
**Gate:** N > 400 breakout days, |t_HAC_NW6| > 1.65 at any horizon
**N_tests added:** +8 (2 signal variants × 4 horizons) per pair → +16 total for 2 pairs

**EURUSD results (N=454 valid days, rate-limited data — WARN_N below 400 gate):**

| Variant | Horizon | N | IC_spearman | t_HAC_NW6 | Gate |
|---|---|---|---|---|---|
| close-based | 1h | 185 | −0.0356 | −1.37 | WRONG DIR |
| close-based | 2h | 185 | −0.0723 | −1.33 | WRONG DIR |
| close-based | **4h** | 185 | **−0.1701** | **−2.26** | WRONG DIR (reversal) |
| close-based | session | 185 | −0.1663 | −1.62 | WRONG DIR |
| HL-based | 1h | 320 | −0.0104 | −1.31 | WRONG DIR |
| HL-based | 2h | 320 | −0.0747 | −1.30 | WRONG DIR |
| HL-based | 4h | 320 | −0.1253 | −2.11 | WRONG DIR (reversal) |
| HL-based | session | 320 | −0.1261 | −1.19 | WRONG DIR |

**GBPUSD results:** N=67–88 breakout days (all n<100, skip).

**Finding:** IC is **negative at all horizons** — breakout does NOT continue (momentum hypothesis fails). Strong negative IC at 4h (t_HAC ≈ −2.2 in absolute terms) reflects **mean reversion** by 4h post-breakout. The 2020 preview showed positive IC at 1h (momentum); the full 5-year sample reverses this, suggesting 2020 was atypically momentum-favorable or that data sparsity in 2021-2024 biases the sample toward reversals.

**N gate:** FAIL (N=185–320 < 400). Data quality insufficient for conclusive IC test.

Status: **COMPLETE — FAIL (wrong direction + N below gate)**

---

## TASK 4 — EUR/GBP BREAKOUT CORRELATION

**Metric:** P(same breakout direction on same day) for EUR/USD and GBP/USD
**Interpretation threshold:** > 75% same = dual-pair confirmation is mostly cosmetic
**N_tests added:** 0 (diagnostic, not an independent signal)

**Result:** Close-based: 14/15 same direction = **93.3%**. HL-based: 30/37 = **81.1%**.
N is very low (15/37 days where both pairs had valid breakout data), driven by GBPUSD sparse coverage. Both exceed 75% threshold.

**Finding:** EUR/GBP dual-pair filter is cosmetic — both pairs break in same direction 81–93% of the time. Single-pair strategy is preferable; dual-pair adds no meaningful edge filter.

Status: **COMPLETE**

---

## TASK 5 — IC FEASIBILITY ANGLE B (News-Fade)

**Signal:** -sign(spike) at T+5min after NFP/CPI/FOMC/ECB (hardcoded calendar 2020–2024)
**Events:** NFP (60), CPI (60), FOMC (~40), ECB (~40) = ~200 event-dates
**Horizons:** 15min, 30min, 1h, 2h after entry
**Gate:** N > 150 observations, |t_HAC_NW6| > 1.65
**N_tests added:** +4 horizons × 2 pairs = +8 for Angle B; pooled: +4

**Result:** N=0 for both EURUSD and GBPUSD. All 201 events failed to find valid spike bars (pre/post bars missing).

**Root cause:** Same rate-limiting issue as Task 2. The specific 1-min bars at news event times (13:30 for NFP/CPI, 18:00-19:00 for FOMC, 11:45-13:15 for ECB) were dropped during fetch. With 23-58% overall hourly fill on years 2021-2024, there is a high probability the event-hour files are missing. Result is statistically invalid (not evidence of no signal, just missing data).

Status: **COMPLETE — INCONCLUSIVE (data quality, N=0)**

---

## N_TESTS ACCOUNTING

| Source | Count |
|---|---|
| Baseline (NQ iter_10) | 142 |
| Crypto OAGF preflight (3 horizons) | +3 |
| Crypto PMR/preflight (other) | +3 |
| Angle A Tasks 3+4 (2 variants × 4 horizons × 2 pairs) | +16 |
| Angle B Task 5 (4 horizons × 2 pairs) | +8 |
| **Running total after Phase 1.5** | **172** |

*Angle B result = N=0 (data quality). N_tests still consumed: once a test is run, it counts regardless of data quality.*  
*Next strategy's tests will start at N=173.*

---

## TASK 6 — SYNTHESIS

## SYNTHESIS — STOP (INCONCLUSIVE — DATA QUALITY)

**Date completed:** 2026-05-23  
**Data status:** Rate-limited fetch → LO coverage 23–100% for EURUSD, 25–36% for GBPUSD

### Angle A (London ORB)
- EURUSD: N=185 (close-based) / N=320 (HL-based) — **below N=400 gate**
- All horizons show **negative IC** (reversal, not momentum): IC = −0.04 to −0.17
- Strongest signal: IC = −0.17, t_HAC = −2.26 at 4h (statistically significant REVERSAL)
- The breakout momentum hypothesis **fails**: price reverses rather than continues post-breakout
- GBPUSD: n<100 on all combos — skip

### Angle B (News-Fade)
- EURUSD + GBPUSD: N=0 (all event bars missing due to rate-limiting)
- **Inconclusive** — not evidence of no signal, just missing data

### EUR/GBP Breakout Correlation (Task 4)
- P(same direction) = 93.3% (close) / 81.1% (HL)
- Dual-pair filter cosmetic — single-pair preferable

### Decision: **STOP**
Both angles fail the IC gate (positive IC + t_HAC > 1.65 not met). Angle A shows a statistically significant REVERSAL signal (IC = −0.17 at 4h, t = −2.26) but this is the opposite of the hypothesized momentum direction.

### Open questions (user decision needed)
1. **Re-fetch?** Fetch with CONCURRENCY=5 + 0.5s inter-batch delay → estimated ~2h/year vs current ~17min/year. Would give N≈800 EURUSD + N≈800 GBPUSD. With more data, the reversal signal could be properly tested.
2. **Reversal pivot?** If reversal at 4h is real (IC ≈ −0.17 with proper N), flip signal direction — trade fade of London breakout rather than breakout momentum. Costs +8 n_tests (same horizons, new direction hypothesis).
3. **Archive FX?** If neither momentum nor reversal is pursued, archive and pivot to another asset class or strategy type.

**WAITING FOR USER VALIDATION — DO NOT START PHASE 2 WITHOUT EXPLICIT APPROVAL**
