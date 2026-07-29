# B1 Month-End Bond Rally — VEHICLE study (2026-07)

> **Question**: not "is the edge real" (it is — B1 is VALIDATED, t_HAC 4.65, and was
> **not re-tested here**), but "does a CME-futures propfirm give it a home?"
> **n_tests contribution: 0.** No signal search, no parameter scan, no new hypothesis.
> The only statistical object produced is a *decomposition* of an already-frozen
> window, plus a first-passage simulation of account mechanics. DSR of the repo is
> untouched.

**Verdict in one line: the effect is capturable on a futures propfirm (93% of it,
even under the strictest flat rule) — and you should still not buy one, because the
minimum lot needs only ~$1,800 of margin that the personal account already has.**

---

## 0. The premise that had to be checked first

The 2026-06-10 freeze ("all futures firms — daily-flat — are DISQUALIFIED for
multi-day holds") was written for Strategy C on NQ, five weeks before B1 was
validated. The pair {month-end Treasury × futures propfirm} was never evaluated.
Re-reading it against the instrument shows the reasoning imports an **equities**
mental model:

| | equity / ETF (TLT) | CME rate futures (ZN) |
|---|---|---|
| trading day | 09:30 → 16:00 ET | **18:00 ET (D‑1) → 17:00 ET (D)** |
| what "no overnight" forfeits | the whole night, 16:00 → 09:30 | only the firm's flat window, **16:10 / 16:59 → 18:00 ET** |

A futures "no-overnight" rule does **not** put you flat through the night. It puts
you flat across the daily settlement break. Asian and European hours are *inside*
the trading day and are held. Verified flat rules (2026):

- **MyFundedFutures** — overnight holding **permitted on all plans** (Core, Rapid, Pro, Flex, Builder), no daily loss limit. → forfeits **nothing**.
- **Apex Trader Funding 4.0** (since 2026‑03‑01) — flat by **16:59 ET**, resume 18:00 ET.
- **Topstep** — auto-flatten **15:10 CT = 16:10 ET**, resume 18:00 ET.
- **FTMO** — confirmed dead, and re-confirmed here: `PropFirms/ftmo/rules.md:135-143`, no bond/treasury/rate CFD in any of the 5 listed categories. Not pursued further.

---

## 1. Identifying the session — the load-bearing step

The whole verdict hinges on what a data "open" and "close" mean, so this was
measured, not assumed (`code/step2_identify_session.py`, tick-level matching of
daily bars against independent hourly bars):

| series | daily `Open` is… | daily `Close` is… |
|---|---|---|
| **ZN=F** | **18:00 ET Globex open of the prior calendar day** — median 0 ticks, **71.6% exact** | **15:00 ET settlement** — median 1 tick |
| **TLT** | 09:30 ET cash open — median 0.13 ticks, 66.7% exact | 16:00 ET cash close — median 0.64 ticks |

**This is the trap the study was built to avoid.** A naive read of the ZN daily
split ("open→close = 93% of the effect") looks like "intraday-dominant" but is in
fact "the 21-hour CME session captures 93%". Stated correctly it is still the
answer we need — it is exactly the *held* leg of a daily-flat account — but it is
not a statement about the US cash session.

Convention stability checked across 2000–2026 (`gap_sd / session_sd` ratio 0.19–0.66,
no jump that would betray a redefinition of `Open`), and cross-validated against the
independent hourly series on the 2024‑03→2026‑07 overlap (held +10.8 bps daily-data
vs +14.0 bps hourly-data, forfeit ≈ 0 in both, n≈29).

---

## 2. THE DECISIVE TEST — HELD vs FORFEITED

Window = frozen B1 spec (last 3 trading days, entry close dend4, exit close dend1).
Convention reproduced first: TLT close-to-close **+36.5 bps, t 4.73, hit 63%**
vs the frozen **+37.5 bps, t 4.65, 63%** → same window, data-vintage difference only.

Decomposition, per event, in log-bps. `HELD` = 18:00→15:00 ET session legs (×3),
`FORFEITED` = 15:00→18:00 ET flat gaps (×3). Significance by **circular block
bootstrap, block = 3 events, 40k draws** (never iid — events cluster in rate regimes).

### 2a. Long sample, CME rate futures (2000‑09 → 2026‑07, n = 311)

| instrument | leg | mean (bps) | t | hit | **p_block** | 95% CI (bps) |
|---|---|---:|---:|---:|---:|---|
| **ZN 10y** | TOTAL close→close | **17.49** | 5.15 | 63.0% | **0.0000** | [10.9, 24.0] |
| | **HELD** 18:00→15:00 | **16.25** | **4.79** | 62.7% | **0.0000** | [9.7, 22.7] |
| | FORFEITED 15:00→18:00 | 1.24 | 1.43 | 51.4% | 0.168 | [−0.5, 3.0] |
| **ZB 30y** | TOTAL | 27.36 | 4.84 | 63.7% | 0.0000 | [16.2, 38.1] |
| | **HELD** | **27.87** | **5.02** | 62.4% | **0.0000** | [16.7, 38.8] |
| | FORFEITED | −0.51 | −0.34 | 51.4% | 0.734 | [−3.6, 2.5] |
| **ZF 5y** | TOTAL | 14.02 | 6.35 | 65.3% | 0.0000 | [9.7, 18.3] |
| | **HELD** | **10.24** | **4.93** | 62.1% | **0.0000** | [6.1, 14.4] |
| | FORFEITED | 3.78 | 3.57 | 53.1% | 0.0004 | [1.8, 5.9] |

**HELD share: ZN 92.9% · ZB 101.9% · ZF 73.0%.** On ZN and ZB the forfeited leg is
statistically indistinguishable from zero. This is measured on a flat window
(15:00→18:00 ET) that is **strictly wider** than what Apex (16:59) or Topstep
(16:10) actually impose — so 93% is a **lower bound** on real capture.

### 2b. Robustness of the cut — tested, not posed once

Window length (ZN):

| last-k days | n | total | HELD | held_t | FORFEIT | **held share** |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 311 | 8.40 | 6.80 | 3.58 | 1.60 | 81% |
| 2 | 311 | 13.30 | 12.25 | 4.50 | 1.05 | 92% |
| **3 (spec)** | 311 | **17.49** | **16.25** | **4.79** | 1.24 | **93%** |
| 4 | 311 | 18.17 | 16.46 | 4.36 | 1.71 | 91% |
| 5 | 311 | 19.43 | 18.45 | 4.66 | 0.98 | 95% |

Sub-periods (ZN): 2000‑07 → 82% · 2008‑14 → 99% · 2015‑21 → 101% · 2022‑26 → 87%.
Never below 81% on any cut.

**Placebo** (ZN, per-day): on the 933 month-end days the session leg is
**+5.42 bps, t +4.71**; on the 5,554 other days it is **−0.13 bps, t −0.27**.
The drift is month-end-specific and lives inside the session — it is not a generic
session-vs-gap artefact.

### 2c. …but it is NOT US-cash-session dominant — the honest caveat

Two independent sources say the same thing: roughly **half** the drift accrues
outside US cash hours (i.e. in the European morning), which is fine for futures and
fatal for an RTH-only implementation.

TLT / IEF, where `Open` is unambiguously 09:30 ET (n = 288, 2002‑08 → 2026‑07):

| | TOTAL | RTH 09:30→16:00 | ON 16:00→09:30 | RTH share |
|---|---:|---:|---:|---:|
| **TLT** | 36.52 (t 4.73) | **20.48 (t 3.55)** | 16.04 (t 3.10) | **56%** |
| **IEF** | 22.50 (t 5.80) | **12.62 (t 4.51)** | 9.88 (t 3.79) | **56%** |

ZN hourly (2024‑03 → 2026‑07, n = 28-29, block-bootstrapped) — the same sweep of
flat-windows on the actual futures contract:

| policy | HELD (bps) | held_t | **p_block** | FORFEIT | held share |
|---|---:|---:|---:|---:|---:|
| continuous (MFFU) | 18.10 | 2.08 | **0.017** | 0.00 | 100% |
| **flat 17:00 → back 18:00 (Apex 4.0)** | **16.51** | 2.00 | **0.029** | 1.58 | **91%** |
| **flat 16:00 → back 18:00 (Topstep)** | **18.35** | 2.35 | **0.010** | 0.72 | **96%** |
| flat 15:00 → back 18:00 (conservative) | 13.95 | 2.06 | **0.019** | 1.68 | 89% |
| flat 16:00 → back 08:00 (RTH-ish) | 9.74 | 1.14 | 0.256 | 9.33 | 51% |
| **flat 16:00 → back 09:00 (US cash only)** | **9.62** | 1.23 | **0.202** | 9.45 | **50%** |
| flat 16:00 → back 10:00 | 5.23 | 0.83 | 0.370 | 13.84 | 27% |

Hour-by-hour accrual on event days confirms it: cumulative +2.8 bps by 08:00 ET
(European hours), then +6.5 bps by 14:00 ET. Base (non-event) days accrue nothing.

> **The precise answer to the framing question**: the effect is **session-dominant
> relative to the CME trading day (93%)**, and only **~50% intraday relative to the
> US cash session**. "Intraday vs overnight" is not well-posed until you say
> *whose* day. A futures propfirm's day is 23 hours long; an ETF's is 6.5.

---

## 3. Material constraints — where it actually dies

### 3a. Costs — *not* the killer

| leg | per ZN contract |
|---|---|
| commission + exchange/NFA fees, propfirm tier (Rithmic/Tradovate) | ~$3.10 RT |
| slippage, 0.5 tick each way (ZN top-of-book = 1 tick = $15.625, thousands deep) | ~$15.60 RT |
| **all-in** | **~$19 RT** |

Gross per event ≈ $209/contract → **cost drag 9.1%**, edge is 11× the round trip.
Daily-flat firms pay 3 round trips ($57) → drag 27%, net $137. Both survive
comfortably. No L33 death here.

### 3b. Lot granularity — **this is the binding constraint**

At the sample's average settle (119.25), 1 ZN = **~$119k notional**, $11.92 per bp
of price return.

| instrument | mean/event | sd/event | **worst event** | init margin |
|---|---:|---:|---:|---:|
| **ZN** 10y ($100k face) | **+$209** | $714 | **−$2,009** | ~$1,800 ⚠ |
| ZF 5y | +$152 | $423 | −$1,121 | ~$1,100 ⚠ |
| ZB 30y | +$315 | $1,146 | −$4,016 | ~$3,800 ⚠ |
| 10Y micro yield ($10/bp) | +$27 | $94 | −$263 | ~$320 ⚠ |

⚠ margins are indicative (CME/IBKR pages could not be scraped this session; they
move with volatility). **The conclusion is not sensitive to them** — the binding
constraint is the DD barrier, not margin.

**The kill shot**: on a $50k MFFU account the max loss buffer is **$2,000**. The
worst historical single event on **one** ZN contract is **−$2,009**. *The minimum
tradeable lot already spans the entire kill barrier.* You cannot size below it.
Micro 10Y yield futures fix granularity but pay only ~$21 net/event — you need
4–14 of them, which rebuilds the same risk.

### 3c. Frequency — 12 events/year against a profit target

Between events the account is flat: calendar burns without approaching the target,
which is exactly where a monthly subscription bites.

---

## 4. First-passage simulation (`code/step5_propfirm_sim.py`)

`Portfolio/admission/barrier.py` is **not** reusable — it hard-codes an FTMO 2-phase,
%-of-balance contract with a mandatory `daily_stop > 0`; futures firms are 1-phase,
dollar-denominated, no daily loss limit. Bespoke engine, same philosophy: real event
paths, block-bootstrapped (block = 3), equity marked at each of the 3 event EODs,
correct static vs EOD-trailing floor mechanics, 36-month horizon.

Best cell per firm:

| firm / product | DD model | size | **p(pass)** | median months | subs paid | plateau p(pass) at large size |
|---|---|---:|---:|---:|---:|---:|
| **MFFU Flex 50k** (overnight OK) | **static $2,000** | 1 ZN | **81%** | 11 | $639 | 50% |
| MFFU Flex 25k (overnight OK) | static $1,000 | 4 micro 10Y | 75% | 11 | $511 | 46% |
| MFFU Builder 50k (overnight OK) | EOD trail $2,000 | 1 ZN | 66% | 10 | $1,031 | 48% |
| Apex 4.0 100k (daily-flat) | EOD trail $3,000 | 2 ZN | 48% | 10 | $783 | **38%** |
| Topstep 150k (daily-flat) | EOD trail $4,500 | 2 ZN | 51% | 17 | $6,110 | **28%** |

Three readings:

1. **Static ≫ trailing**, as expected: MFFU Flex static 81% vs Builder trailing 66%
   at identical $2,000 buffer and identical size.
2. **The daily-flat firms lose ~12 pts of plateau** (38%/28% vs 50%) — but mostly
   from their **target/DD ratio of 2.0** (Apex $6,000/$3,000, Topstep $9,000/$4,500)
   vs MFFU's 1.5, plus 3× the cost. The flat rule itself costs ~7% of the edge.
3. **The L24 signature is textbook**: sizing up to hurry collapses every cell onto a
   scale-invariant plateau (~50% / 38% / 28%). Money management is not the lever.
   Getting 81% requires accepting **11 months** of waiting.

⚠ **MFFU Flex is a legacy plan, no longer sold to new customers** (per 2026 reviews).
The sellable equivalents are Builder (66%) and Pro/Core (EOD-trailing). The single
best cell is therefore **not purchasable today**, which weakens the case further.

---

## 5. The verdict — the propfirm buys nothing

Funded phase, 24 months, at the best size:

| vehicle | p(alive 24m) | mean profit | after split |
|---|---:|---:|---:|
| MFFU Flex 50k, 1 ZN (static) | 80% | $4,239 | $3,391 (80%) |
| MFFU Flex 50k, 2 ZN (static) | 60% | $7,040 | $5,632 (80%) |
| Apex 4.0 100k, 2 ZN (daily-flat) | 50% | $5,075 | $4,567 (90%) |

Counterfactual — the *same trade*, in the personal futures account that already exists:

| capital | size | margin | expected | sd | worst event | share of P&L |
|---|---|---:|---:|---:|---:|---:|
| **~$13.0k (€12k)** | **1 ZN** | ~$1,800 (14%) | **+$2,275/yr (+17.6%)** | $2,473 | −$2,009 (−15.5%) | **100%** |
| ~$13.0k | 2 ZN | ~$3,600 (28%) | +$4,550/yr (+35.1%) | $4,946 | −$4,018 (−31.0%) | 100% |
| ~$54k | 4 ZN | ~$7,200 (13%) | +$9,101/yr (+16.9%) | $9,892 | −$8,035 (−14.9%) | 100% |

Standalone sleeve quality, per ZN contract, annualised by **√12 not √252** (L47 —
this fires 12×/yr): net **$2,275/yr**, sd **$2,473**, **Sharpe 0.92 net of costs**,
hit 63%. That matches the `personal_book_research_2026-07` figure (trend +
bond-month-end, combined SR 1.02) — consistent, not a new claim.

**A propfirm sells leverage on capital you don't have. One ZN contract needs ~$1,800
of margin. The €12k personal account already carries it — comfortably.** So the
propfirm route asks for 11 months of waiting and ~$639 of subscriptions in order to
end up with **80% of the P&L of one contract**, under a $2,000 barrier that a single
historical event has already breached, on a plan that is no longer sold. It is
**strictly dominated** by simply placing the trade.

### Recommendation

1. **Deploy B1 on ZN in the personal IBKR futures account** at 1 contract (~14% of
   capital in margin, worst historical event −15.5%). ZN over TLT/IEF: 93% of the
   effect survives any session constraint, $19 RT vs ~5 bps ETF, no ETF wrapper, and
   no dependence on the US cash session.
2. **Do not buy a futures propfirm challenge for this sleeve.** Not because the edge
   can't be held — it can, 93% of it — but because the vehicle adds nothing that the
   personal account lacks, and subtracts 20% of the P&L plus a kill barrier.
3. **Unfreeze the blanket 2026‑06‑10 ruling.** "All futures firms are disqualified
   for multi-day holds" is factually wrong for CME instruments and should not be
   allowed to pre-kill future candidates. Replace it with the correct statement:
   *futures propfirms forfeit only the 16:10/16:59→18:00 ET flat window.*
4. If a futures propfirm is ever wanted for a *different* sleeve, the ranking from
   this study is **MFFU (static DD, overnight allowed, target/DD = 1.5) > Apex 4.0 >
   Topstep**, and the discriminator is target/DD ratio far more than the flat rule.

---

## 6. Lesson candidates (named, not numbered — engraving happens at reconciliation)

- `futures-trading-day-is-not-a-calendar-day` — a "no overnight positions" rule at a
  CME propfirm forfeits only the daily settlement flat window (16:10/16:59→18:00 ET),
  **not the night**. A multi-day effect measured on daily closes can be ~93%
  capturable under it. Never transfer an equity/CFD daily-flat intuition to futures
  without checking the contract's session hours.
- `whose-day-is-it` — "intraday vs overnight" is undefined until the session is named.
  The same B1 window is 93% intraday on the CME day and 50% intraday on the US cash
  day. Identify the session **empirically** from the data (tick-matching daily bars
  against intraday bars), never from the vendor's field names.
- `propfirm-adds-nothing-when-min-lot-margin-fits-personal-capital` — before pricing
  p(pass), compare the minimum tradeable lot's margin to the personal account. If it
  fits, the propfirm is strictly dominated (fees + split + barrier, zero benefit).
  Corollary of L24: it is a *vehicle* test, and it is cheaper than the MC.
- `sequencing-debt` — B1 was rejected twice on the vehicle, both times by rulings
  written before it existed (FTMO gate‑0, then the NQ-driven futures-firm freeze).
  A blanket venue exclusion should carry the *instrument class it was derived from*,
  or it silently pre-kills unrelated future candidates.

---

## Files

```
code/fetch_data.py                    yfinance pull (daily TLT/IEF/ZN/ZB/ZF/SPY, 60m ZN/TLT)
code/step1_replicate_and_split.py     B1 convention reproduction + RTH/ON split, dividend check
code/step2_identify_session.py        empirical identification of the daily O/C session marks
code/step3_hourly_shape.py            hour-by-hour accrual + flat-window sweep + block bootstrap
code/step4_longsample_and_economics.py  n=311 decomposition, robustness, placebo, costs
code/step5_propfirm_sim.py            bespoke first-passage MC (1-phase, $ DD, no daily stop)
code/step6_vehicle_verdict.py         funded-phase EV vs personal-account counterfactual
data/                                 fetched OHLC caches (regenerable — do not commit)
```

## Sources (vehicle rules, verified 2026-07)

- [MyFundedFutures overnight holding rules](https://proptradingvibes.com/blog/myfundedfutures-overnight-holding)
- [MyFundedFutures account types & pricing 2026](https://proptradingvibes.com/blog/myfundedfutures-account-types)
- [MyFundedFutures rules 2026 — Core, Rapid, Pro](https://tradecovex.com/guides/myfundedfutures-rules-2026)
- [Topstep live funded account rules](https://www.topstep.com/live-funded-account-rules)
- [Apex Trader Funding 4.0 — what changed](https://phidiaspropfirm.com/education/apex-trader-funding-4-0-explained)
- [Apex futures trading times](https://support.apextraderfunding.com/hc/en-us/articles/31519771524891-Futures-Trading-Times)
- [CME 10-Year T-Note contract specs (Ironbeam)](https://www.ironbeam.com/knowledge-base/10-year-u-s-treasury-note-futures-zn-contract-specifications/)
- [CME Micro Treasury Yield futures](https://www.cmegroup.com/markets/interest-rates/micro-treasury-futures.html)
- In-repo: `PropFirms/ftmo/rules.md:135-143` (bond CFDs absent — re-confirmed)
