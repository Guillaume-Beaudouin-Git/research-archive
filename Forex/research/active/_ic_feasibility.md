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

**EURUSD 2020 validated:** 365,459 bars (8.7MB parquet)  
Status: **IN PROGRESS** (fetching EURUSD 2021-2024 + GBPUSD 2020-2024, ~2.5h remaining)

**PREVIEW RESULT (EURUSD 2020 only, n=1 year — directional only):**

| Signal | Horizon | N | IC_spearman | t_HAC_lag4 | Direction |
|---|---|---|---|---|---|
| close-based | 1h | 92 | +0.073 | +0.50 | ✓ |
| close-based | 2h | 92 | +0.080 | +0.19 | ✓ |
| close-based | 4h | 92 | -0.054 | -0.84 | ✗ (reversal) |
| HL-based | 1h | 170 | +0.056 | +0.65 | ✓ |
| HL-based | 2h | 170 | +0.020 | +0.08 | ✓ (weak) |
| HL-based | 4h | 170 | -0.022 | -0.35 | ✗ (reversal) |

**Interpretation:** Positive IC at 1h-2h → breakout momentum exists. Negative at 4h → fades by noon. With 5 years (N≈460-850), t_HAC should reach 1.5-2.0 at 1h.

---

## TASK 3 — IC FEASIBILITY ANGLE A (London ORB)

**Signal:** Asian range (00:00–07:00 UTC) breakout at London open (07:00–08:00 UTC)
**Variants:** (1) close-based — 07:59 close vs Asian range; (2) HL-based — high/low of 07:00–07:59 vs Asian range
**Horizons:** 1h, 2h, 4h, session-end (17:00 UTC)
**Gate:** N > 400 breakout days, |t_HAC_NW6| > 1.65 at any horizon
**N_tests added:** +8 (2 signal variants × 4 horizons) per pair → +16 total for 2 pairs

Status: PENDING (waiting for data)

---

## TASK 4 — EUR/GBP BREAKOUT CORRELATION

**Metric:** P(same breakout direction on same day) for EUR/USD and GBP/USD
**Interpretation threshold:** > 75% same = dual-pair confirmation is mostly cosmetic
**N_tests added:** 0 (diagnostic, not an independent signal)

Status: PENDING (waiting for data)

---

## TASK 5 — IC FEASIBILITY ANGLE B (News-Fade)

**Signal:** -sign(spike) at T+5min after NFP/CPI/FOMC/ECB (hardcoded calendar 2020–2024)
**Events:** NFP (60), CPI (60), FOMC (~40), ECB (~40) = ~200 event-dates
**Horizons:** 15min, 30min, 1h, 2h after entry
**Gate:** N > 150 observations, |t_HAC_NW6| > 1.65
**N_tests added:** +4 horizons × 2 pairs = +8 for Angle B; pooled: +4

Status: PENDING (waiting for data)

---

## N_TESTS ACCOUNTING

| Source | Count |
|---|---|
| Baseline (NQ iter_10) | 142 |
| Angle A Tasks 3+4 (2 variants × 4 horizons × 2 pairs) | +16 |
| Angle B Task 5 (4 horizons × 2 pairs) | +8 |
| **FX Phase 1.5 total** | **166** |

*FX Phase 2 tests will start at N=167.*

---

## TASK 6 — SYNTHESIS

Status: PENDING (waiting for Tasks 3–5)

**Decision criteria:**
- GO A: Angle A t_HAC > 1.65 on any horizon for any pair
- GO B: Angle B t_HAC > 1.65 on any horizon for any pair  
- GO BOTH: both pass
- STOP: both fail → archive FX ORB/news-fade, pivot to alternative

---
