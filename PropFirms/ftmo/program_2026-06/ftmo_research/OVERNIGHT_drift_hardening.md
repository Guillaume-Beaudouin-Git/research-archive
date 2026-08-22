# Hardening the overnight-drift harvester — financing, crash-tail, time, replication

**Mission:** price the *deployable* funded-probability of the MA200-gated overnight
equity-drift harvester on NQ — net of financing at **today's** rate, crash-tail-aware,
time-aware, replicated on a second index. The signal's *existence* is settled
(see `OVERNIGHT_drift_findings.md`); this report does **not** re-test it. It prices it
as the **beta** it is.

**Date:** 2026-06-02 · **Account:** FTMO 2-Step, $10k · **Reference (in-sample, swap-free, pre-tail):** p(funded) **88% @0.5× / 81% @0.75×**.

---

## TL;DR verdict

> **The honest deployable p(funded) is ~50% (a coin flip), not 82–88%, for a typical (non-Islamic) trader launching today.** Three independent haircuts each cost ~15–30 points, and they stack:
> 1. **Financing (decisive).** A Standard account *cannot hold overnight at all*; the strategy **requires** the Swing account, which **charges swap**. At today's SOFR (~3.6%) the swap is ~2 bps per overnight hold — the same size as the entire net edge — pulling p(funded) **88% → 55% @0.5×**, **81% → ~54% @0.75×**. Only a swap-free **Islamic** account (proof of religion required) preserves the high number.
> 2. **Inactivity rule (operational gate).** FTMO deactivates any account with **no trade for 30 days**. The gate sits flat **60–162 consecutive days in every bear** (2022: three stretches of 162/138/69 days). Un-managed → account dies in the first bear → p(funded) ≈ 0. Survivable only with a **monthly keep-alive token trade** — the strategy is not "set-and-forget."
> 3. **Concentration / weak √N.** The 88% is **NDX-specific**. The same harvester on **SPX (+2.2 bps, Sharpe 0.60)** and **DAX (+2.68 bps, Sharpe 0.82)** replicates *in sign* but at ~half strength → ~37% funded even swap-free, <10% at today's swap.
>
> Crash-tail is real but second-order to the above: at ≤0.5× no single historical overnight gap busts you, but the **lagging gate ate −21.3% cumulative through COVID** (busts every sizing if you're near $10k when it hits), and an un-sampled 1987-style −20% gap would bust even 0.5×.
>
> **Bottom line:** deployable today ≈ **45–55%** (NQ, 0.5×, non-Islamic, actively managed). It only clears **>70%** if **all** of: swap-free Islamic account **and** disciplined keep-alive management **and** acceptance of NDX concentration + the rare crash tail. The financing at today's rate is the dominant killer.

Method note: all p(funded) figures are **contiguous real-path** — a stationary block
bootstrap (Politis–Romano, mean block 21 trading days; robust to block length 10–63)
of the joint (gate-state, overnight-return) night series — **not** an IID bootstrap,
which destroys the regime clustering the gate exploits. Code: `code/overnight_harvester_sim.py`.

---

## 0. Signal reproduction (sanity gate, not a re-test)

Rebuilt cleanly from `raw/NQ_1min_databento_2010-2026.parquet` (5.1M 1-min bars,
per-contract → roll seams excluded for overnight returns, ratio back-adjusted for the
MA200 gate; no look-ahead — the gate decision at close[t] uses only close[t]).

| metric | value |
|---|---|
| gated overnight mean | **+5.00 bps/night** |
| ungated overnight mean | +4.89 bps/night |
| gated overnight Sharpe (ann.) | **1.24** |
| in-market share of sessions | 78.3% |
| 2020 (COVID) in-market | **93%** — gate *lagged*, stayed long |
| 2022 (bear) in-market | **6%** — gate *sat out* the bear |

At swap = 0, spread 1.5 bps, my bootstrap returns **88% @0.5× / 81% @0.75% / 71% @1.0×** —
matching the findings' 88/82/67. Reproduction confirmed; proceeding to the haircuts.

---

## 1. Financing / swap — the decisive, near-binary item

### 1a. Policy (web-verified against FTMO)
- **A Standard account cannot run this strategy.** FTMO Standard accounts must close positions within ~2 h of market close; **holding the overnight close→open is only permitted on the Swing account**, which is offered **exclusively on the 2-Step Challenge** (selectable at order time; Standard→Swing switching is not allowed). This is *fortunate* — the user's account type is exactly the one that works.
- **The Swing account still charges swap** on overnight index positions, including the standard **triple-swap on Wednesday** (covers the weekend value date). Swing removes the *holding restriction*, not the *financing cost*.
- **Only a swap-free Islamic account removes the swap** — available "on request, subject to approval," and FTMO **requires proof of religion**. For a typical trader this is not an honest option, so the base case carries the swap.
- **Fees:** one-time €155 for the $10k 2-Step, **refunded with the first reward withdrawal**; **no recurring fee**.

### 1b. Magnitude (at today's rate)
Long index CFD financing ≈ `(reference + broker markup − dividend yield)` on notional, per night:

| era | reference (SOFR) | + markup | − NDX div | ≈ annual | per cal-night | **per overnight hold¹** |
|---|---:|---:|---:|---:|---:|---:|
| ZIRP 2010–21 | ~0.1% | ~2.75% | ~0.85% | ~2.0% | 0.55 bps | **~0.75 bps** |
| **Today (Jun-26)** | **~3.6%** | ~2.75% | ~0.85% | **~5.5%** | 1.5 bps | **~2.0 bps** |
| 2023 peak | ~5.4% | ~2.75% | ~0.85% | ~7.3% | 2.0 bps | ~2.8 bps |

¹ ×~1.4 for the triple-Wednesday weekend charge spread over in-market holds. Markup (FXCM +3% USD; ActivTrades 2.5%) is the main uncertainty → today's swap ≈ **1.5–2.1 bps/hold**.
Today's Fed funds target is **3.50–3.75%** (held since early 2026), well below the 2023 peak but far above ZIRP.

### 1c. p(funded) recomputed by swap level (NQ 2-step, spread 1.5 bps)

| swap (bps/hold) | era / account | **0.5×** | **0.75×** | 1.0× |
|---|---|---:|---:|---:|
| **0.0** | swap-free **Islamic** (any rate) | **88%** | **81%** | 71% |
| 0.75 | ZIRP-era Swing (hypothetical) | ~80% | ~73% | ~66% |
| 1.5 | low-markup today | 66% | 63% | 57% |
| **2.0** | **today, central** | **55%** | **~54%** | 51% |
| 2.5 | 2023-peak / high-markup | ~46% | 46% | 44% |

Robustness (verified): block length 10/21/42/63 → swap0 stays 79–81%, swap2.0 stays 50–55% (k=0.75);
seed-stable to ±1% across 3 seeds; a **1-day entry-delay test leaves it 80% → 78% (no look-ahead artifact)**.
Spread is the one *favorable* assumption here: at the prior findings' implied **2.6 bps** spread, today's
k=0.75 number is only **34%** — so the ~54% central is, if anything, generous. Higher financing or spread
only deepens the verdict.

**Read-out:** at today's rate the swap eats most of the ~2 bps net edge, halving the funded
probability to a **coin flip (~50–55%)** and lengthening the median grind (3.4 → 4.7 yr at 0.5×,
because you pay swap on more nights and drift toward the floor more often: bust 9% → 26%).
The edge is **not** robust to current financing unless swap-free.

---

## 2. Crash-from-highs tail — cluster risk, not single-gap binary

### 2a. Worst single overnight gaps while above MA200
Clean NQ databento (2010–26) + daily index panel (2000–26, captures 2008/Brexit/COVID;
note yfinance *opens* are compressed for US500/US30 → those understate, US100/GER40 opens are real):

| index | worst gated overnight | date | bust at 0.5×? |
|---|---:|---|---|
| NQ (clean) | **−6.5%** | 2020-03-06 (COVID) | no (needs −10%) |
| NQ (clean) | −5.4% | 2024-08-02 (carry unwind) | no |
| US100 | −7.2% | 2020-03-06 | no |
| GER40 | **−9.9%** | 2016-06-23 (Brexit) | borderline |

Bust thresholds (daily-DD = −5%/k near start): **0.5× → −10%**, 0.75× → −6.67%, 1.0× → −5%.
In 16 yr of clean NQ, **0 nights ≤ −6.67% and 0 ≤ −10%** — **no single overnight gap ever busts 0.5×.** Single-gap risk at ≤0.5× is effectively nil in-sample.

### 2b. The real in-sample bust mode: the lagging gate eats the *cluster*
The 200-day MA sits ~15–20% below price at a top, so price must fall that far before the gate
flips — you eat the **first leg** of every fast crash. Measured directly:

| episode | gate behaviour | cumulative gated overnight | 0.5× outcome from $10k |
|---|---|---:|---|
| **COVID** (Feb 18–Mar 31 2020) | **lagged, 58% long** | **−21.3%** | **BUST** ($8,886 < $9,000) |
| 2022 bear (full year) | sat out, 6% long | −4.8% | survives ($9,760) |
| Aug-2024 unwind | lagged, 75% long | −3.4% | survives ($9,826) |

**This corrects the prior findings' "0% bust at 0.5×."** That was an *aggregate* artifact — few
paths sit near $10k exactly when COVID begins. Conditional on being mid-grind near the start
balance, a COVID-magnitude fast crash **busts every sizing, including 0.5×**. The honest bootstrap
already prices this: **bust ≈ 9% @0.5×** (not 0%), rising to 20–26% once today's swap lengthens the grind.
The gate protects against **slow** bears (2022, perfectly) but **not fast crashes from highs**.

### 2c. Un-sampled catastrophe and what mitigates it
A **1987-style −20% single gap from above the MA** (Black Monday: SPX −20.5%, market still above
its 200-day MA going in) would bust **even 0.5×** on both the daily and total limits. Not in the
2000–26 sample; frequency ~once/century ≈ ~1%/yr → **~3–4% over a 3.5-yr grind**. This is a rare
**binary total bust**, not a smooth haircut.
- **A fixed catastrophe stop-loss does *not* help** — a gap fills *through* the stop at the open.
- **Only smaller size or a self-imposed halt mitigates:** 0.5× survives everything except a COVID-magnitude *cluster* near the start balance; surviving a −20% *single gap* on the daily limit needs **≤0.25×** (much longer grind). A discretionary "halt and wait for the gate to re-confirm if equity < ~$9,500" rule converts most cluster-busts into survivable pauses (you stay above the $9,000 floor) — the most capital-efficient mitigation.

---

## 3. Time + FTMO multi-year rules

- **No time limit — confirmed.** FTMO removed the 30/60-day deadline from both 1-Step and 2-Step; only the 4-day minimum and the DD limits remain. A 2–3 yr (or 4.7 yr at 0.5× with swap) grind is **legal**.
- **…but the 30-day inactivity rule still applies, to challenge *and* funded accounts.** No trade for 30 days → account **deactivated**. This **collides head-on** with a trend gate that sits flat through bears:

| longest gate-OFF (flat) stretches, NQ 2010–26 | calendar days |
|---|---:|
| 2022 (Aug) | **162** |
| 2022 (Mar) | 138 |
| 2018 (Nov) | 98 |
| 2022 (Jan) | 69 |
| 2025 (Mar) | 67 |

**9 flat stretches exceed 30 days; 7 exceed 45.** Un-managed, the account dies in the first bear —
i.e., during exactly the "sit out the bear flat" behaviour that makes the strategy *survive*. 
**Mitigation:** a **monthly keep-alive token trade** (minimal size) during gate-off periods keeps
the account active; FTMO's "freeze" option is for short planned absences (holidays), not multi-month
bear-sitting. This is a real **operational burden** — the strategy is systematic but **not passive**,
and forgetting one keep-alive in year 3 forfeits the account.
- **Opportunity cost:** the challenge slot, the €155 (refundable only on a payout that may be years away), and ongoing attention are tied up for a **multi-year beta harvest**. On a funded account the same inactivity rule + multi-year horizon means the slot is largely idle. Activating a faster, two-sided strategy on the same funded capital would dominate on a risk-adjusted, time-adjusted basis if one exists.

---

## 4. √N replication — sign yes, magnitude no

Same MA200-gated overnight harvester, independent indices/sources:

| index | source | period | gated mean | Sharpe | p(funded) 0.75× swap0 | swap2.0 |
|---|---|---|---:|---:|---:|---:|
| **NDX / NQ** | databento intraday | 2010–26 | **+5.00 bps** | 1.24 | **80%** | 54% |
| NDX / US100 | yfinance daily | 2000–26 | +4.84 bps | 1.21 | 80% | 50% |
| NDX / US100 | MT5 intraday | 2021–26 | +5.15 bps | 1.06 | — | — |
| **SPX / US500** | MT5 intraday | 2021–26 | **+2.20 bps** | **0.60** | (weak) | — |
| **DAX / GER40** | yfinance daily | 2000–26 | **+2.68 bps** | **0.82** | **37%** | 6% |

- **NDX reproduces across three independent data sources** (+4.8 to +5.2 bps, Sharpe ~1.1–1.2) — the signal is real and the pipeline is clean.
- **SPX and DAX replicate in *sign* but at ~half the strength.** The overnight premium is genuinely there everywhere, but **only NDX is strong enough to clear the FTMO +10%/+5% barriers with high probability.** DAX funds only **37% even swap-free**, <10% at today's swap.
- **Implication:** the 82–88% is **NDX-specific** and partly reflects that NQ was the highest-overnight-drift liquid index of this era (mega-cap tech earnings/AI overnight gaps). This is an implicit selection — a **yellow flag** for out-of-sample robustness. A true beta edge *should* replicate at full strength; this one concentrates.

---

## 5. Verdict — deployable p(funded), honestly

Stacking the haircuts onto the in-sample reference (NQ, 0.5×):

| stage | p(funded) | note |
|---|---:|---|
| In-sample, swap-free, pre-tail | **88%** | the headline — but Islamic-only at this level |
| − financing at **today's** rate (Swing, non-Islamic) | **~55%** | the dominant haircut; swap ≈ net edge |
| − un-sampled 1987-style crash tail | **~51–52%** | rare binary bust, ~3–4% over the grind |
| − inactivity rule | **≈0% if un-managed / no haircut if managed** | hard operational gate, not a probability |
| OOS / NDX-concentration discount | qualitative | edge is NDX-specific, not uniform √N |

**Deployable today (NQ, 0.5×, non-Islamic Swing, tail-aware, actively keep-alive-managed): ≈ 45–55% — a coin flip, plus a multi-year grind and an un-hedgeable crash tail.** It does **not** stay above 70%.

**It clears >70% only under a conjunction:**
1. a **swap-free Islamic account** (proof of religion) — restores ~80%, minus tail ≈ ~75%; **and**
2. **disciplined monthly keep-alive** through every bear; **and**
3. acceptance that the edge is **NDX-concentrated** and carries a rare **−20%-gap total-bust** tail that no stop can hedge.

**As beta, priced as beta:** the in-sample 82–88% reflected 16 benign years (+1500% NDX), unlimited
time, and **zero financing**. At today's ~5.5%/yr CFD financing the harvest is roughly halved; the
strategy is essentially *"borrow at SOFR+3% to hold the overnight equity premium"* — and at current
rates that premium barely clears its own carry. **The single most decisive lever is the financing
rate**, not the signal: this becomes attractive again only if (a) rates fall back toward ZIRP, or
(b) the account is genuinely swap-free.

### Recommended disposition
- **Do not deploy at 1.0×** (bust 29–38%, swap-fragile). If deployed at all, **0.5×** with a self-imposed catastrophe halt (~$9,500) and **monthly keep-alive discipline**.
- **Pursue the swap-free question first** — it is binary and worth a direct ticket to FTMO support ("is a swap-free/Islamic 2-Step Swing account available to me?"). The entire economics hinge on it.
- **Treat the 82–88% as an Islamic-account, ZIRP-era ceiling, not the deployable number.** The deployable number for most traders today is **~50%**.

---

### Artifacts
- `code/overnight_harvester_sim.py` — signal build (roll-safe, no look-ahead), stationary block bootstrap, vectorised FTMO 2-step barrier sim, rolling-start cross-check.
- `outputs/nq_daily_rth.parquet`, `outputs/nq_overnight_signal.npz` — cached clean daily RTH series and per-night (gate, overnight-return) arrays.

### Sources (web)
- FTMO Swing account (2-Step only, holds overnight/weekend): https://ftmo.com/en/faq/ftmo-swing-account-type/
- Swap on Swing still charged / what is a swap: https://ftmo.com/en/blog/what-is-a-swap-and-for-whom-is-it-important/
- Swap-free Islamic (on request, proof of religion): https://tradersunion.com/brokers/prop/view/ftmo/halal-or-haram/
- 30-day inactivity rule + no time limit: https://ftmo.com/en/blog/trade-without-any-time-limit-and-take-as-long-as-you-want-to-pass/
- Fees one-time, refunded on first 2-Step reward, no recurring: https://ftmo.com/en/faq/are-the-fees-recurrent/
- US Fed funds 3.50–3.75% (2026): https://tradingeconomics.com/united-states/interest-rate
- Index CFD financing ≈ benchmark + 2.5–3% markup: https://www.activtrades.com/en/news/what-are-swap-rates-overnight-financing-for-cfd-positions
