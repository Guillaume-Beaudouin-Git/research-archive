# Prop-Firm Scan — EV ranking for a MOMENTUM/TREND-family systematic trader

**Date:** 2026-06-08 (live web research; prop-firm rules change constantly — re-verify before any purchase).
**Lens:** the trader's edges are **TSMOM** (weekly rebalance, holds over weekends) and **Ross Hook**
(multi-day breakout-continuation). These are **lumpy, position-holding momentum** edges — low win-rate,
P&L concentrated in a few big trend-run days, fat left tails (a trend-reversal day). They **lose under a
tight symmetric barrier** and need a geometry where the **profit target is reachable in a trend run before
the drawdown floor bites**, with **room to ride** and **no clock**.
**Method:** rules verified against each firm's **official** site/help-center (cited). Items not confirmable
on an official page are marked **[UNVERIFIED]**; I did not fill them from memory. Reputational/payout items
are flagged as **allegations** with sources unless adjudicated. This is research, **not endorsement**.

---

## 0. The barrier-geometry framework (what favors vs penalizes lumpy momentum)

| Lever | FAVORS momentum | PENALIZES momentum (TRAP) |
|---|---|---|
| **Max-drawdown type** | **STATIC** from initial balance (full cushion stays) | **TRAILING**, esp. **intraday on the *unrealized* peak** — a winning run that spikes then retraces ratchets the floor up and whipsaws you out. *The #1 momentum killer.* |
| **Max-DD width** | **Wide** (10% ≫ 6% ≫ 4%) — survives chop until a trend pays | Narrow (4-6%) |
| **Daily loss limit** | **Loose / none**, computed off **balance** (prev-day/initial) | **Tight (2-3%)** on **intraday equity high-water** — clips lumpy days and trips on a winner that retraces |
| **Time limit** | **None** — a variance-dominated edge needs time for a trend to appear | Any cap (Apex 30-day eval; FXIFY Lightning 3-7 day) |
| **Consistency rule** | **None / high** | **Best-day cap (30-50%)** — directly taxes the few big trend-run days momentum lives on |
| **Target vs floor** | **Asymmetric-favorable**: target distance **<** floor distance | Symmetric/worse: target ≥ floor (most 1-steps: 10% target vs 6% DD = target *farther* = harder) |
| **Holding window** | **Weekend + overnight allowed** (required for TSMOM/Ross Hook multi-day holds) | **Daily-flat** (all futures firms) or **no-weekend** (Master auto-close Friday) → **disqualifies the strategy** |

**Consequence proven in this project's own prior work (audit + survivors book, [CLAUDE.md L24]):** even on the
*best* static-DD / no-time-limit / no-consistency geometry, a lumpy momentum book's p(pass) is structurally
**modest (~0.2–0.4)** because the barrier is near-symmetric. So the ranking below is **relative geometry
favorability**, not a promise of a high pass rate. No firm turns lumpy momentum into a high-EV layup; the
goal is the *least-hostile* geometry from a *firm that actually pays*.

---

## 1. CRITICAL DISQUALIFICATION — the multi-day-hold requirement (read first)

TSMOM and Ross Hook **hold positions for days/weeks, across weekends**. This **hard-disqualifies**:

- **Every futures firm** (Topstep, Apex, Take Profit Trader, MyFundedFutures, FundedNext Futures): all
  require **daily flat** (auto-flatten by session close ~3:10–4:10 PM ET) → **you cannot hold a multi-day
  trend position.** *(MyFundedFutures allows the overnight Globex session but still flattens daily at 4:10 PM
  ET — no true multi-day hold.)* Source: Topstep products/hours, MFF permitted-times pages (cited below).
- **CFD accounts that close Friday:** FundingPips **1-Step / 2-Step / Zero** funded (Master closes before
  Friday close — only **3-Step** Master allows weekend) ([FundingPips News/Weekend](https://help.fundingpips.com/hc/en-us/articles/34504137479441-News-Trading-Weekend-Holding)); **E8 Signature** (weekend only on E8 One); **TFT** non-Royal challenges (crypto-only weekend); **FTMO funded *Standard*** (must close before weekend — but **FTMO Swing** allows it).

**Therefore, for the strategies as-given, the eligible universe is CFD firms that ALLOW weekend holding on
the funded account:** FTMO (2-Step eval → **Swing** funded), **FundedNext CFD (all models)**, **Alpha
Capital** (Swing/One), **Blueberry Funded**, **FundingPips 3-Step**, **E8 One**, **TFT Royal/Royal Pro**.

> **If the trader instead runs an INTRADAY momentum variant** (e.g. intraday NQ trend/breakout, flat by
> close), the **futures firms re-qualify** — and several have geometry that's *good* for intraday momentum
> (no daily loss + no time limit). See §4 (conditional futures note).

---

## 2. Comparison table — momentum-decisive parameters (× official source)

CFD/FX firms first (eligible for multi-day holds where weekend-OK), then futures (intraday-only).
DD type is the decisive column. "Wknd" = weekend holding on the *funded* account.

| Firm — challenge | Target(s) | Max DD — TYPE | Daily loss (basis) | Time limit | Consistency | Wknd hold | Payout rep | **EV tier (momentum)** | Source |
|---|---|---|---|---|---|---|---|---|---|
| **FundedNext — Evaluation (2-step)** | 10% / 5% | **10% STATIC** | 5% (initial; granularity [UNV]) | None | **None** | **Yes** | Good (24h) | **HIGH** | [help](https://help.fundednext.com/en/articles/8917879-can-i-hold-my-trades-overnight-and-over-weekend-on-fundednext-cfd), [terms](https://fundednext.com/cfd-challenge-terms) |
| **FundedNext — Stellar 2-Step** | **8% / 5%** | **10% STATIC** | 5% (initial) | None | **None** | **Yes** | Good | **HIGH** (target<floor) | same |
| **FundedNext — Stellar Lite** | 8% / 4% | **8% STATIC** | 4% | None | **None** | **Yes** | Good | **HIGH** | same |
| **FundedNext — Stellar 1-Step** | 10% | **6% STATIC** | 3% | None | **None** | **Yes** | Good | MED (target>floor) | same |
| **FundedNext — Stellar Instant** | none | 6% **TRAILING→lock@initial** | **None** | None | [UNV] | Yes | Good | MED | [help](https://help.fundednext.com/en/articles/11641163) |
| **FTMO — 2-Step** | 10% / 5% | **10% STATIC** | 5% (initial, **equity intraday**) | **None** | **None** | **Yes (Swing)** | **Top-tier** | **HIGH** | [trading-objectives](https://ftmo.com/en/trading-objectives/) (upd 2026-05-13) |
| **FTMO — 1-Step** | 10% | **10% TRAILING (EOD bal)** | 3% | None | **50% best-day** | Yes (Swing) | Top-tier | LOW (trail+consistency) | same |
| **Alpha Capital — Swing (2-step)** | [UNV] | **10% STATIC** | 5% (balance) | None | **40%** | **Yes** | No crisis; [UNV] depth | MED | [products](https://alphacapitalgroup.uk/product), [daily-risk](https://help.alphacapitalgroup.uk/en/articles/6934210) (upd 2026-03-09) |
| **Alpha Capital — Pro (2-step)** | [UNV] | **6/8/10% STATIC** | 3-5% (bal / >bal,eq) | None | 40% | Yes | — | MED | same |
| **Alpha Capital — One (1-step)** | 10% | 6% **TRAILING→lock@initial (EOD)** | 4% (greater of bal/eq) | None | 40% | Yes | — | MED | [Alpha One](https://help.alphacapitalgroup.uk/en/articles/10097421) |
| **Blueberry — 2-Step** | 10% / 5% | **10% STATIC** | 5% (higher of SOD bal/eq) | None | **None** | **Yes** | **Concern (3.1★)** | MED (geom HIGH, rep drags) | [2-step DD](https://help.blueberryfunded.com/en/articles/12076157), [weekend](https://help.blueberryfunded.com/en/articles/9550589) |
| **Blueberry — 1-Step** | 10% | **6% STATIC** | 4% (higher of SOD bal/eq) | None | **None** | Yes | Concern | MED | [1-step DD](https://help.blueberryfunded.com/en/articles/12075830) |
| **FundingPips — 3-Step** | [UNV]/phase | TRAILING→lock [UNV%] | ~4% (higher of open bal/eq) | None | [UNV] | **Yes (only FP model)** | **Best newer (4.5★, $200M+)** | MED | [3-step](https://help.fundingpips.com/en/articles/9279479-3-step-model), [news/wknd](https://help.fundingpips.com/hc/en-us/articles/34504137479441-News-Trading-Weekend-Holding) |
| **FundingPips — 2-Step Std** | 8% / 5% | 10% **TRAILING→lock** [UNV] | 5% (open bal/eq) | None | **35%** | No (Master Fri-close) | Best newer | LOW (disq. wknd) | [2-step](https://help.fundingpips.com/hc/en-us/articles/34501809112081-2-Step-Model) |
| **E8 — One (1-step)** | 6% | **4% DYNAMIC TRAILING (intraday/eq)** | 3% (SOD bal, eq) | None | **40%** | **Yes** | Clean ($38–68M paid) | LOW (intraday-trail) | [E8 One](https://help.e8markets.com/en/articles/11775980), [DD](https://help.e8markets.com/en/articles/11864596) |
| **E8 — Signature (1-step)** | 6% | EOD dynamic trail (closed bal) | 2% pause (tight) | None | **35%** | **No** | Clean | LOW (no wknd) | [Signature](https://help.e8markets.com/en/articles/11755943) |
| **FXIFY — Two-Phase Std** | 5% / 5% | 10% **TRAILING→lock@initial** | 4% (prev-day EOD bal) | None | [UNV] | [UNV] | No crisis | MED/LOW | [trailing-DD FAQ](https://fxify.com/faqs/all-faqs/how-do-you-calculate-the-max-trailing-drawdown/) |
| **FXIFY — Lightning (1-step)** | 5% | 4% TRAILING | 3% | **3–7 days** | **30%** | [UNV] | — | LOW (time+consist+trail) | [Lightning](https://fxify.com/programs/lightning-challenge/) |
| **The Funded Trader — Royal/Royal Pro** | 8% / 5% | **10% STATIC** | 4-5% (balance) | None | [UNV] | **Yes (Royal only)** | **⚠ PAYOUT CRISIS (2026)** | LOW (reputation) | [Royal Pro](https://help.thefundedtraderprogram.com/en/articles/10309003); [Trustpilot Apr-2026] |
| **The Funded Trader — other** | ~8%/5% | 8-10% STATIC | 5% (balance) | None | varies | No (crypto-only wknd) | ⚠ crisis | LOW | [help center](https://help.thefundedtraderprogram.com/en/) |
| **Goat Funded — Instant PRO** | none | 4% **TRAILING (no lock, +−2% floating kill)** | **None** | None | **20%** | Yes | ⚠ Trustpilot-flagged (3.4★) | LOW | [Instant PRO](https://help.goatfundedtrader.com/en/articles/13574328) |
| **MyFundedFX (CFD)** | — | — | — | — | — | — | **DEFUNCT — closed 2026-02-06** | **N/A** | [Finance Magnates](https://www.financemagnates.com/forex/seacrest-ends-prop-trading-after-integrating-myfundedfx-shifts-focus-to-cfds/) |
| **FUTURES — Topstep Combine** | $3k/$6k/$9k (6%) | **$2k/$4k/$4.5k TRAILING (EOD)**, lock@start | Optional ($1-3k) | **None** | **50%** | **No (daily flat)** | No scandal surfaced | DISQ. multi-day / MED-intraday | [combine](https://help.topstep.com/en/articles/8284197), [MLL](https://help.topstep.com/en/articles/8284204) |
| **FUTURES — Apex eval** | $1.5–20k | **Intraday / EOD / Static** options, lock@target(eval) | **None** | **30 days** | **50%** (was 30%, Mar-2026) | **No** | **⚠ payout allegations (AG complaints)** | DISQ. / LOW | [intraday DD](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/) |
| **FUTURES — Take Profit Trader** | $1.5–4.5k | Test **EOD-trail**; PRO **INTRADAY-trail** lock@start | **None (removed 2025)** | **None** | **50%** | **No** | Generally OK | DISQ. / MED-intraday | [EOD DD](https://takeprofittraderhelp.zendesk.com/hc/en-us/articles/15170265979165) |
| **FUTURES — MyFundedFutures Flex** | $2.5–8k | **4% STATIC (EOD cap)** — "sidesteps trailing" | None | None | 50% | No (Globex only) | Generally OK | DISQ. / **MED-intraday (best futures geom)** | [MAX EOD](https://help.myfundedfutures.com/en/articles/8348565-max-eod-trailing), [Flex] |

*(Fee figures omitted from the table — they sit behind JS-rendered/checkout pages and were [UNVERIFIED] for
most firms; see §5. FTMO & FundedNext refund the challenge fee on first payout; profit splits 80%→90-95%.)*

---

## 3. Shortlist — the 3–5 most EV-favorable (firm × type) for MULTI-DAY momentum

Ranked by (geometry favorability) × (payout reliability) × (allows weekend hold). EV proxy reasoning:
EV ≈ p(pass) × [account × split × realistic payout-months] − fee × attempts; **payout reliability gates the
payout term** (a firm that won't pay → EV ≈ −fee regardless of p(pass)), and p(pass) is ranked by geometry.

1. **FundedNext — Stellar 2-Step (CFD)** — **HIGH.**
   *Why:* the best intersection — **STATIC 10% max DD** (full cushion, no ratchet), **phase-1 target 8% <
   10% floor = asymmetric-FAVORABLE** (rare; most firms are target≥floor), **phase-2 only 5%**, **NO
   consistency rule** (won't tax the lumpy big trend days), **no time limit** (let a trend appear),
   **weekend + overnight + news allowed** (runs TSMOM/Ross Hook as-is). Reputable, fee refunded on pass,
   ~24h payouts, 80→95% split. *Caveat:* daily 5% off-initial is still a real floor for a fat-tailed day,
   and CFD **swap applies** to multi-day holds (a real cost — this project measured CFD financing at ~3–11%/yr
   for held longs). Daily-loss balance-vs-equity granularity **[UNVERIFIED]** (balance-based would be kinder).
2. **FTMO — 2-Step → Swing funded** — **HIGH.**
   *Why:* **STATIC 10% DD, NO consistency, NO time limit** (verified 2026-05-13), **min 4 days**, **top-tier
   payout reliability**, fee refunded on pass, **Swing account allows weekend/overnight** for the funded
   stage. The reputable gold standard. *Caveat:* phase-1 is **symmetric (10% target = 10% DD)** — slightly
   harder geometry than FundedNext's 8% target; the prior audit's whole point is this symmetric barrier caps
   lumpy-momentum p(pass) (~0.2–0.34 at 12mo). Daily 5% is on **equity intraday** (tighter than balance-based).
   **Avoid FTMO 1-Step** (trailing DD + 50% best-day rule — hostile to momentum).
3. **Blueberry — 2-Step (or 1-Step)** — **MED** (geometry HIGH, reputation drags it down).
   *Why geometry is great:* **STATIC 10%/6% DD, NO consistency rule, weekend allowed, no time limit** — on
   paper as good as FundedNext. *Why MED:* **payout-reliability concern** (Trustpilot ~3.1★; multiple dated
   allegations of denials via "prohibited strategies/toxic-trading" clauses, breaches just before scheduled
   payouts — *allegations, not adjudicated*; ASIC-broker-backed parent is a mitigant). Reputation gates the
   payout term in the EV proxy → use only with small first-target and verify payout before scaling.
4. **FundingPips — 3-Step** — **MED.**
   *Why:* **best payout track record of the newer firms** (~4.5★ across ~52k reviews; **$200M+ paid, 127k+
   payouts, Payout-Junction-verified**) **and the only FundingPips model that allows weekend + news holding on
   the funded Master account** (verified). Low entry fee, scales toward 100% split. *Caveat:* **trailing-then-
   lock DD** (less favorable than static) + **3 phases** (three barriers to clear) + recurring **"risk per
   trade idea"** discretionary-enforcement complaints. Good for multi-day momentum *if* you accept trailing DD.
5. **Alpha Capital — Swing (2-step)** — **MED.**
   *Why:* **STATIC 10% DD**, **weekend-oriented** (holding allowed), no time limit, no surfaced payout crisis,
   UK firm (recently updated rules 2026-03-09). *Caveat:* **40% best-day consistency rule** taxes lumpy
   momentum; exact targets/fees **[UNVERIFIED]**; payout-reliability depth not probed.

**Honorable mention (geometry, but no-weekend → only for an intraday variant):** for an **intraday** momentum
reformulation, **MyFundedFutures Flex** (**STATIC 4% EOD**, no daily loss, no time limit, Pro one-day-pass =
no consistency) is the **best futures geometry**; **Take Profit Trader Test** (EOD-trail, no daily loss, no
time limit) is also reasonable until the PRO stage flips to intraday-trailing.

---

## 4. Which rules DISQUALIFY an intraday-flat or overnight strategy

- **Multi-day / weekend-holding momentum (TSMOM, Ross Hook) is DISQUALIFIED by:** every futures firm
  (daily flat); FundingPips 1-Step/2-Step/Zero funded (Master closes Friday); E8 Signature; TFT non-Royal;
  FTMO funded *Standard* (use **Swing** instead); FundedNext Futures (no overnight). → Need an explicit
  **Swing / weekend-hold-allowed CFD** account (FTMO Swing, FundedNext CFD, Alpha, Blueberry, FundingPips
  3-Step, E8 One).
- **Intraday-flat momentum is DISQUALIFIED / crippled by:** **intraday trailing DD on the unrealized peak**
  (Apex intraday accounts, TPT **PRO**, MFF **Rapid**, E8 One) — an intraday runner that spikes then gives
  back locks a higher floor and stops you out at the worst time; **time limits** (Apex 30-day, FXIFY
  Lightning 3-7d); **tight consistency caps** (30-50%) that void the one big trend day. Best intraday-momentum
  geometry = **no daily loss + no time limit + EOD-or-static DD + no/high consistency** → MFF Flex, TPT Test,
  Topstep Combine (EOD-trail, but 50% consistency).
- **Swap/financing** applies on **all CFD firms** for overnight/weekend holds (relevant: this project measured
  CFD financing dragging held-long momentum by ~3–11%/yr). Only **FundingPips / FXIFY** offer a paid
  **swap-free add-on, and only for FX + metals** (crypto/indices/energies always carry swap). **Futures pay no
  swap** but forbid the overnight hold entirely — a genuine trade-off for a carry-sensitive momentum book.

---

## 5. Honest limitations & flags

- **[UNVERIFIED] rules** (official page JS-rendered / Cloudflare-403 / behind checkout — *not* filled from
  memory): exact **fee tables** for nearly all firms ($50k/$100k); FundedNext/Blueberry/FundingPips/FXIFY
  **daily-loss balance-vs-equity & intraday-vs-EOD granularity**; per-phase targets & DD% for several
  TFT/Alpha/FXIFY/Goat variants; FundingPips 3-Step DD% and consistency; FundedNext Instant min-days. Apex and
  Take Profit Trader **block automated fetch** — their values here are from search snippets of official help
  text (URLs cited) and should be re-checked in a browser before purchase.
- **Payout-reliability flags (allegations unless noted; verify current before funding):**
  **The Funded Trader** — documented 2023-24 payout crisis and *active* 2026 complaints (KYC-rejection at
  withdrawal, platform-migration outages); **treat as a live concern.** **Apex** — payout-dispute history
  (mass-ban reports, AG complaints), partially addressed by a March-2026 "automated enforcement" update.
  **Goat** — Trustpilot-flagged for guideline breaches; copy-trade-denial complaints + a brutal −2% floating
  P&L kill. **Blueberry** — denial-clause allegations (broker-backed mitigant). **MyFundedFX — DEFUNCT
  (closed 2026-02-06).** **Cleaner track records:** FTMO (established), FundedNext (24h payouts), **FundingPips**
  ($200M+ verified), **E8** ($38–68M paid).
- **Promo / rule flux:** futures firms (esp. Apex) run near-permanent discounts and **change consistency/payout
  rules frequently** (Apex 30%→50% consistency, March 2026; Topstep payout terms cut April 2026; FTMO 1-Step
  is a newer trailing product). FundingPips dynamic-leverage change effective 2026-03-16. Anything dated here
  can move — re-verify the firm's official page at purchase time.
- **What this scan does NOT claim:** it does **not** rank "best firm" generically, and it does **not** assert
  a numeric p(pass) — the prior in-house first-passage work shows lumpy momentum is structurally capped even on
  the friendliest geometry. The deliverable is **relative geometry favorability × payout reliability**, with
  the honest conclusion that the *as-given* multi-day momentum edges fit a **narrow** set of weekend-hold CFD
  firms, of which **FundedNext CFD and FTMO 2-Step/Swing** are the geometry-and-reputation sweet spot.

**Sources (primary, official unless flagged):** FTMO [trading-objectives](https://ftmo.com/en/trading-objectives/);
FundedNext [CFD overnight/weekend](https://help.fundednext.com/en/articles/8917879-can-i-hold-my-trades-overnight-and-over-weekend-on-fundednext-cfd),
[CFD terms](https://fundednext.com/cfd-challenge-terms); FundingPips [News/Weekend](https://help.fundingpips.com/hc/en-us/articles/34504137479441-News-Trading-Weekend-Holding),
[3-Step](https://help.fundingpips.com/en/articles/9279479-3-step-model); Topstep [MLL](https://help.topstep.com/en/articles/8284204);
Apex [intraday DD](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/);
Take Profit Trader [EOD DD](https://takeprofittraderhelp.zendesk.com/hc/en-us/articles/15170265979165);
MyFundedFutures [MAX EOD trailing](https://help.myfundedfutures.com/en/articles/8348565-max-eod-trailing);
E8 [One](https://help.e8markets.com/en/articles/11775980); Alpha [One](https://help.alphacapitalgroup.uk/en/articles/10097421);
Blueberry [2-step DD](https://help.blueberryfunded.com/en/articles/12076157); FXIFY [trailing-DD FAQ](https://fxify.com/faqs/all-faqs/how-do-you-calculate-the-max-trailing-drawdown/);
TFT [Royal Pro](https://help.thefundedtraderprogram.com/en/articles/10309003); Goat [Instant PRO](https://help.goatfundedtrader.com/en/articles/13574328);
MyFundedFX closure [Finance Magnates](https://www.financemagnates.com/forex/seacrest-ends-prop-trading-after-integrating-myfundedfx-shifts-focus-to-cfds/).
