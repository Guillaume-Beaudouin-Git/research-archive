# VALIDATED — Month-end Treasury flow-alpha on real futures (the one surviving edge)

**Date 2026-07-16.** Direct validation on the tradable vehicle (audit follow-up). VERDICT: **CONFIRMED,
no decay, honestly deployable at ~18%/yr / −37% real maxDD.** The one edge that survived all deflation.

## Validation on REAL Treasury futures (24yr, 2002-2026)
| Instrument | ME mean | t_HAC | SR | pre-2022 SR | 2022+ SR |
|---|---|---|---|---|---|
| ZN=F (10y) | +5.4 bps | 4.76 | 0.90 | 0.90 | **0.89** |
| ZF=F (5y) — best | +4.4 bps | **5.95** | **1.11** | 1.10 | **1.17** |
| ZB=F (30y) | +8.9 bps | 4.57 | 0.86 | 0.86 | 0.83 |
| TLT (ETF, original) | +12.9 bps | 5.22 | 0.93 | 0.99 | **0.65** ⚠ |

**The post-2022 "decay" was a TLT-ETF artifact — NOT the real effect.** On the actual futures the effect
is STABLE pre/post-2022 (SR 0.86-1.17). Placebo p=0.000 (ZN +5.4 vs random-3day p95 2.3); other-days
−0.71 bps (concentrated = flow-alpha, not beta); net of 0.5bp/leg cost +4.4 bps/trade. ZF (5y) strongest.

## Honest deployable sizing (audit lesson: REAL-PATH DD + margin-call bar, NOT bootstrap)
ZF+ZN combined sleeve, 1× SR 0.99, exposed 14% of days (flat 86% → shallow DDs → safe to lever):
| Leverage | ann/yr | REAL maxDD | worst month-end | verdict |
|---|---|---|---|---|
| 5× | 9% | −20% | −7% | safe |
| **10× (recommended)** | **18%** | **−37%** | −14% | safe (< −40% margin-call) |
| 20× | 35% | −61% | −28% | margin-call ✗ |

**Why safe where the continuous trend+bonds book was not:** intermittent 14%-exposure → shallow DDs →
~10× is below the margin-call bar (−37% real), vs the continuous book's −73% at 8×. Intermittency enables
leverage.

## Vehicle @€12k
**CME Micro Treasury Yield futures (5YY / 10YY, $10/bp, ~$300-500 margin)** — SHORT the yield future the
last 3 business days of each month (bond rally = yield falls). Granular, cheap, deployable at €12k.
Caveat: live micro-yield history from Aug-2022 only (check live liquidity/execution); underlying effect
24yr-validated on ZN/ZF. Beyond-sample rate-spike on the window can exceed −37%.

## Bottom line
~18%/yr, −37% real maxDD, single validated flow-alpha, honestly sized. Doubles the account in ~4yr. NOT
40%/yr-at-0%-ruin (which does not exist) — but real, robust, and the honest core of the growth book.

---
## STEP 1 (2026-07-16) — real-contract / vehicle validation: TEMPERED
The clean SR 0.90-1.11 is on the FULL ZN/ZF futures PRICE. Deployability check on the actual €12k vehicle:
- **Micro-yield 5YY/10YY: thin free data** (only 2YY=F on yfinance, 962 obs from 2022-08).
- **On the real settlement reference (FRED DGS5/DGS10 yields, 24yr): SR 0.33** — right magnitude
  (~0.55bp yield/ME-day ≈ ZN's 5.4bp price via duration) but NOISIER than ZN price (0.90). Live micro-yield
  era (2022-08+) weaker ($3.4/ME-day vs $10.9 full-sample; net −$470).
- **2YY real contract (live): +0.24bp/ME-day short-end, other-days −0.17** — effect present, right
  direction, small (2y moves least). Confirms real but weak at the granular vehicle.

**Honest vehicle verdict:** effect REAL on all instruments (ZN/ZF/FRED/2YY all show the month-end rally),
but the clean ~18%/yr (SR 0.99) needs the FULL ZN/ZF futures (~$110-120k notional → ~€30-50k capital). At
€12k via micro-yield the deployable is a NOISIER version (SR ~0.33-0.5, ~5-10%/yr), needs LIVE paper
confirmation on 5YY/10YY (broker data, not yfinance). Path: micro-yield modest now → grow to €30-50k → full
ZN/ZF where the clean SR materializes. NOT 18%/yr at €12k; ~5-10%/yr at €12k, 18%/yr at €30-50k.
