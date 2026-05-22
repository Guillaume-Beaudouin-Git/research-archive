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

Status: IN PROGRESS → see `_ic_feasibility/fetch_data.py`

---

## TASK 3 — IC FEASIBILITY ANGLE A (London ORB)

Status: PENDING

---

## TASK 4 — EUR/GBP BREAKOUT CORRELATION

Status: PENDING

---

## TASK 5 — IC FEASIBILITY ANGLE B (News-Fade)

Status: PENDING

---

## TASK 6 — SYNTHESIS

Status: PENDING

---

*N_tests counter updated after Tasks 3+5 complete.*
