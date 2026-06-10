# Passing a Propfirm Challenge in < 3 Months at p(pass) > 50%
### An institutional-grade plan — what a systematic quant would actually do

**Date:** 2026-06-08 · **Context:** after a full research cycle + independent audit that retracted a
3-sleeve FTMO book (real p(pass≤3mo) ≈ 0.35-0.43, edge indistinguishable from zero — see
`../ftmo_decorrelated_portfolio/RECONCILIATION.md`).

---

## 0. The reframe (the single most important idea)

A propfirm challenge is **not an alpha problem. It is a first-passage problem against a barrier.**
`P(pass) = P(reach +target before −maxDD, respecting the daily floor, within the clock)`. It is governed
by **three** things a quant controls, only one of which is "alpha":

1. **The barrier** — the firm's *rules* (DD type, daily limit, steps, clock). **We never optimized this.**
2. **The distribution shape** — daily Sharpe **and** kurtosis of the book (breadth + decorrelation).
3. **The bet** — sizing/leverage and execution quality.

Our entire failed cycle attacked only #2, on free price data, and proved that universe is arbitraged
(no robust edge survives true-UTC + standard MTM + honest costs + OOS + DSR). **A Two Sigma quant would
not keep mining #2. They would attack #1 first (cheapest, highest ROI), industrialize #2 with real
rigor and breadth, and treat #3 as optimal betting.** And they would reframe the goal as **EV of a
campaign**, not a single hero-attempt.

> Hard truth a senior quant would say out loud: with *retail execution* (propfirm spreads, no
> co-location) and *free data*, a robust > 0.50 single-attempt edge is genuinely scarce. The value is in
> the **process** and in **barrier engineering** — and in being honest about when the game isn't worth it.

---

## 1. What we have proven (so we don't relitigate it)

- Need **daily Sharpe ≈ 0.12 (annual ≈ 2) + low kurtosis** to clear 0.50 in 3 months on FTMO's symmetric
  +10/−10 + −5% daily barrier. That is a *very* high bar.
- Free-data, price-only, FTMO-executable edges: **exhausted** (≈12 families, all rejected honestly).
- Zero-edge baseline on FTMO's barrier ≈ **0.35-0.43** — and the clock/horizon does *not* rescue a
  zero-edge book (DSR is binding, not time).
- **Decorrelation machinery is real** (|ρ|<0.06, kurtosis averages down). It just needs *real* sleeves.

---

## 2. Workstream A — BARRIER ENGINEERING (do this first; ~1-2 weeks; highest ROI)

The same modest edge can swing **0.35 → 0.55+** purely from which firm/product you choose. FTMO's
symmetric 2-step **+ −5% daily floor** is one of the *most hostile* barriers for a grindy mean-reversion
book (it punishes the occasional bad day). A quant treats the rule set as a free optimization variable.

**A1 — Build a firm-rules database** (one CSV, ~15-25 products). Columns that change p(pass):
`DD_type {static, trailing-EOD, trailing-intraday}`, `maxDD%`, `daily_limit% {or none}`, `target%`,
`steps {1, 2, instant}`, `min_days`, `time_limit`, `consistency_rule`, `payout_split`, `fee`, `refund`,
`crypto/futures_allowed`, `leverage_cap`.

**A2 — Run our (validated, monotone) first-passage MC across the matrix** for a *realistic* strategy
shape — even a **modest, honest** one (e.g. daily Sharpe 0.4-0.6, kurt 3-6, the best we can truly build).
Output a **firm × shape → p(pass) (with CIs)** table. Pre-register the shape; no peeking.

**A3 — Decision:** pick the **best-fit barrier**, not the most famous firm. Likely winners for a
low-Sharpe grind: **static-DD, no-daily-limit, 1-step, generous target/DD ratio** firms. This alone may
do more than any new signal.

*Deliverable:* `firm_barrier_matrix.csv` + `barrier_mc_report.md`. *Cost:* near-zero (we have the engine).

---

## 3. Workstream B — BREADTH (the actual Two Sigma model; ~4-6 weeks)

Two Sigma does not run 3 signals. It runs **thousands of weak, decorrelated, individually-validated**
signals and lets √N + risk-parity do the work. Our thesis was right; our **N was 3 and the sleeves were
fake.** To make the decorrelation machinery pay we need **10-30 sleeves that are each real.**

**B1 — Industrialize the research pipeline (non-negotiable, from our scars):**
- **One committed runner** builds every sleeve + the portfolio end-to-end. No scratch-only numbers.
- **Empirical timezone check** on every source (the −3h test) before use.
- **Standard close-to-close MTM only**; reject any convention that doesn't survive a vanilla mark.
- **Purged/embargoed K-fold + combinatorial CV (CPCV)**; **DSR at the true trial count** before any
  Sharpe is cited; **outer block-resample CIs** on every p(pass).
- A **pre-registered signal graveyard** (hypothesis → gate result), so multiple-testing is *counted*.

**B2 — Widen the universe** (still propfirm-executable): full FX majors+crosses, all index CFDs, metals,
**the firm chosen in WS-A's** asset set (some allow futures/crypto with better rules), more bar
frequencies and sessions — each entering the book **only** through the B1 gate.

**B3 — Go beyond raw OHLC** (free price is arbitraged — this is the crux). Cheap, retail-executable,
documented-edge data we can actually use as *signals* (not necessarily as the traded instrument):
- **Crypto funding/basis & perp-spot** (we have `data/funding_carry/`) — strong documented carry; use it
  to *time/condition* an executable crypto-CFD sleeve even if the pure delta-neutral trade isn't
  FTMO-legal.
- **Options-implied skew / term-structure** as a *regime/conditioning* signal for index sleeves.
- **ETF flows, short-interest, COT positioning, cross-venue lead-lag** — signal inputs, retail-priced.
- Realistic expectation: most fail the B1 gate (that's the job). Target survivors: **5-10 real sleeves.**

**B4 — Honest gate per sleeve:** positive net of true costs, on true-UTC, **out-of-sample**, **DSR-clean**,
pairwise ρ < 0.3 to the existing book. A sleeve that needs a special execution convention to be positive
is **rejected** (Sleeve-A lesson).

*Deliverable:* `signal_factory/` (committed) + a sleeve registry with per-sleeve DSR + the correlation
matrix. *This is where the real time goes.*

---

## 4. Workstream C — SIZING & EXECUTION (first-passage optimal; ~2 weeks, overlaps B)

**C1 — Optimal betting under the barrier.** Not a naïve fixed leverage: **fractional-Kelly capped by the
DD constraint**, phase-specific (Phase 2's +5% target wants different sizing than Phase 1). Solve the
sizing that *maximizes the first-passage probability* on the chosen firm's barrier, with CIs.

**C2 — Real execution stack.** Our intraday sleeves were timing-sensitive (a +1-bar delay killed them).
Build and **measure** the actual execution: the firm's MT5/cTrader API, real fills, **measured slippage**
vs backtest, the daily-reset boundary in the broker's *server* timezone (not a label).

**C3 — Paper-trade → re-baseline.** Run the book in paper for ≥ 4 weeks; replace backtest fills with
realized fills; recompute p(pass) with CIs. **Only the paper-confirmed number counts.**

---

## 5. The EV reframe (the decision a quant actually makes)

A challenge is a **repeated +EV bet**, not a one-shot. With fee `C`, funded-account expected value `V`,
and per-attempt `p`:  `EV_per_attempt = p·V − C`. Even at **p = 0.35-0.45**, if `V/C` is large (typical:
fee €100-600 vs funded payouts), the *campaign* is +EV: run `N` attempts, expected funded ≈ `N·p`. 

→ **Two decision branches, state them to the team explicitly:**
- **Goal = "get funded efficiently"** → optimize `EV(firm, p, N, sizing)`; > 0.50 per attempt is *not
  required*. Pick the firm with the best **EV-adjusted** `p` (WS-A) and run a disciplined campaign.
- **Goal = "> 0.50 in a single attempt"** → requires *either* a genuinely better-fit barrier (WS-A
  delivers most of this) *or* a real multi-sleeve edge (WS-B). If neither clears 0.50 with its CI on the
  best-fit firm, the honest answer is **"this configuration does not support it"** — and you choose the
  campaign/EV route or stop.

---

## 6. 10-week roadmap, with gates and kill-criteria

| Wk | Workstream | Deliverable | Gate / kill-criterion |
|---|---|---|---|
| 1-2 | **A — Barrier** | firm-rules DB + firm×shape p(pass) matrix (CIs) | **Gate A:** ∃ a firm where a *modest* honest shape (SR 0.4-0.6) → p(pass) CI **clears 0.50**? If yes, that firm is the target. If no firm clears even at SR 0.6 → the edge bar is the binding constraint → WS-B mandatory. |
| 3-6 | **B — Breadth** | committed signal factory + 5-10 DSR-clean sleeves + corr matrix | **Gate B:** ≥ 5 sleeves pass the B1 rigor gate, pairwise ρ<0.3, each DSR>0.5 at true N. **Kill:** if < 3 survive, the universe is exhausted → EV/stop branch. |
| 7-8 | **B+C — Portfolio** | ERC book + first-passage sizing on the chosen firm → p(pass) with CIs | **Gate C:** book p(pass≤3mo) **CI clears 0.50** on the target firm (monotone engine). |
| 9-10 | **C — Live** | paper-trade ≥4wk, measured slippage, re-baselined p(pass) | **Gate D (fund-or-not):** paper-confirmed p(pass) CI still clears 0.50 **and** realized slippage ≤ modeled. Only then deploy fee capital. |

**Overriding kill-criterion:** if at Gate C the best honest book on the best-fit firm is < 0.50 with its
CI, **do not fund a hero-attempt** — switch to the EV-campaign framing or stop. (A reproducible 0.45 on
the right firm, run as a campaign, beats a fantasy 0.55.)

---

## 7. What I would explicitly NOT do (our scars, as guardrails)

- ❌ More clever formulas on free OHLC price (arbitraged — proven).
- ❌ Scratch-only numbers; every figure must come from a committed runner.
- ❌ Naked p(pass) points; **always** outer-resample CIs + a monotone engine.
- ❌ Trusting data labels; **verify timezone empirically**, use the broker server day.
- ❌ Execution conventions (open-to-open, entry-booking, cap-and-continue) that don't survive a standard
  MTM and a +1-bar delay.
- ❌ Citing a Sharpe before DSR at the **true** trial count.

---

## 8. Honest bottom line

A Two Sigma quant in our exact situation would **(1) stop hunting price alpha**, **(2) spend week one on
barrier engineering** — most of the gap to 0.50 is probably hiding in the *wrong firm choice*, not a
missing signal — **(3) industrialize a real, DSR-gated, true-UTC signal factory** to get breadth (the
actual TS model), **(4) size as optimal first-passage betting and measure real execution**, and **(5)
frame the result as campaign-EV** with an explicit fund-or-stop gate.

The most likely *honest* outcome, stated up front: **barrier engineering (WS-A) gets us the furthest for
the least cost** and may itself reach > 0.50 for a modest real edge on a better-fit firm; a single-attempt
> 0.50 on FTMO's hostile barrier with retail execution remains the hardest version of the problem and
may not be reachable — in which case the correct, institutional answer is the EV-campaign on the best-fit
firm, not a fabricated headline.

*Recommended first action: execute Workstream A now (we have the engine, the data, and the rigor
protocol). It is cheap, fast, and decisive.*
