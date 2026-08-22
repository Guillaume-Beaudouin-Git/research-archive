# SYNTHESIS — 3 decorrelated-sleeve candidates (stat-arb / range / MR indices)

**Date:** 2026-07-08 · **Mandate:** independent "fresh per brief" exploration of three candidate sleeves
for the FTMO book, with pre-registration → net-of-cost backtest → two-sided + OOS + deflated-Sharpe →
verdict, reconciled against in-repo precedent only at the end. Live book untouched; additive folder; no
git-HEAD ops. Engine, data, cost model, pre-registrations, results and an independent verification are in
this directory tree.

> **⚠ Correction 2026-07-08 (financing sign bug):** figures citing the stat-arb backtest Sharpe (e.g.
> "US500/US30 net SR 0.97") were inflated by a swap-sign bug found later in the iteration-2 verification;
> corrected best is **0.27**. **All iteration-1 verdicts (3× FALSIFIED) are UNCHANGED** — they rest on the
> cointegration screen / two-sided test, which are financing-independent. Full detail:
> `../iteration_2/CORRECTION_2026-07-08.md`.

---

## 0. Bottom line (one paragraph)
**All three pistes are FALSIFIED as FTMO sleeves — cleanly, with named mechanisms, and independently
verified.** None produces a two-sided, OOS-stable, cost-surviving, §4-compatible edge. The three failures
are *different* and instructive: **A (stat-arb)** dies at the cointegration-stability layer (0/12 pairs
OOS-cointegrated; the seductive ~1.0 Sharpe is 80-day-hold relative-drift on non-cointegrated spreads —
the beta trap in a market-neutral costume); **B (range)** dies because the range *detection* is a
look-ahead artefact (causal gross Sharpe −0.06 vs oracle +2.66) and what survives is cost-dead (0/56 pass
the L33b gate); **C (daily MR)** dies on the two-sided test exactly as its falsified 15-min ancestor did
(short leg net-negative on all four indices; the horizon change did not help). The unifying finding
repeats across all three: **on liquid retail-FTMO instruments, every short-horizon family reduces to
one-sided directional drift after honest costs — the two-sided/OOS test is the decisive falsifier.**

## 1. Promise ranking (as requested) — with the honest caveat that none is FTMO-deployable

| rank | piste | verdict (FTMO) | residual promise & where |
|:--:|---|:--:|---|
| **1** | **A — stat-arb / pairs** | FALSIFIED | Highest residual value, but **not on FTMO**. Genuinely satisfies the §4 tail-decorrelation axis, and the **gold/silver** relative-value thread is a *real* medium-Sharpe edge (repo 3A: net Sharpe 0.77, cost/delay-robust) that only the **−10 % floor** kills → worth a look for a **non-barrier / personal account**, never FTMO. |
| **2** | **B — range** | FALSIFIED | One real thread: **XAU intraday range-reversion** has a genuine *causal* gross signal (gross Sharpe +1.30, not look-ahead) but is **cost-dead net** (gross/cost 1.0 < 3). A *vehicle* failure — resurrectable only at a **sub-spread (market-maker) venue**, not retail FTMO. |
| **3** | **C — daily MR on indices** | FALSIFIED | **No residual.** Pure beta trap; the short leg cannot escape index up-drift, and daily holds add overnight swap for nothing. Least promising of the three. |

Note this *inverts the brief's premise* in one important way: Piste A was flagged as "the only one
without a negative precedent." It is in fact **the most thoroughly closed family in the repo** (see §3),
and §4 ranks relative-value **last**. Its "promise" here is real but lives **outside** the FTMO container.

## 2. Per-piste verdicts (mechanism first)

**A — stat-arb (`piste_A_statarb/RESULTS.md`).** Falsification triggers **F1 + F2 + F4**.
0/12 pairs OOS-cointegrated (best EURUSD/GBPUSD p=0.06; US500/US30 p=0.82). Half-lives **112–566 days**
→ forced **63–82-day holds** → presence ≈ 1.0 (§4 reject). The high-Sharpe cells (US500/US30 net SR 0.97,
US30/GER40 0.90) are **relative drift**: the profitable leg is always the one aligned with the realised
2013–2026 trend (long-spread win 83–87 % vs short-spread 50–58 %); daily HAC t 3.7 is autocorrelation-
inflated (true N_eff = 35 trades). FTMO also forbids the 2-leg construction (hedging rule) and a −10 %
floor cannot survive an OOS drift reversal. **No engine re-test warranted** (fails upstream of any engine).

**B — range (`piste_B_range/RESULTS.md`).** Triggers **F1 + F2 + F3 + F4**.
Causal gross Sharpe median **−0.06** vs oracle (look-ahead) **+2.66** — *the detection, not the fade, was
the edge.* 0/56 cells clear gross/cost ≥ 3 (L33b); best net Sharpe 0.57 < 0.7; short leg negative on 6/7
instruments. Only XAU shows a real causal gross tendency, cost-dead net.

**C — daily MR (`piste_C_mr_daily/RESULTS.md`).** Triggers **F1 + F3**.
Short-leg (fade overbought) net-negative across **all 48 index cells** (0/48 significant; US500-RSI2 short
t −2.22); the long leg is buy-the-dip index beta. Best net Sharpe anywhere **0.53 < 0.7**. Daily swap
asymmetry actually *favours* the short leg (shorting US100 earns +0.09/night), which cleanly isolates the
killer as **drift**, not financing — an isolation the swap-free 15-min study could not make.

## 3. Reconciliation with in-repo precedent (consulted only now, per the fresh-pass rule)

This independent pass **reproduces every prior verdict**, on fresh data and a fresh engine (author≠auditor):

| this study (fresh, daily/hourly, 2026-07) | in-repo precedent | agreement |
|---|---|:--:|
| A: 0/12 OOS-coint, half-life wall, relative-drift, 2-leg cost/financing | `statarb_deepdive_ftmo.md` (18 pairs/48 trials, 4 killers) + `STATARB_VERDICT.md` (6 ideas) | **✓ reproduced** — and *weaker* at daily freq (0/12 OOS vs their 2/18 at 1H; half-lives 112–566 d vs 22–180 d) |
| C: short-leg beta trap on indices; weak FX-reversal knife-edge | `MR_deepdive_ftmo.md` (350 trials, intraday) + `intraday_mr_ftmo/FINDINGS.md` | **✓ reproduced** — extended to the **daily horizon** with the swap-isolation addition |
| B: breakout = execution rent; range-fade cost-dead; XAU no net edge | `breakout_deepdive_ftmo.md` (delay-1 collapse) + `xauusd_rangefade_honest` (NO-GO) | **✓ reproduced** — adds the explicit **causal-vs-oracle** decomposition |

The value of the fresh pass is therefore threefold: (i) it **independently confirms** three prior negatives
that the book relies on, (ii) it **corrects the brief's premise** that Piste A was un-tested, and (iii) it
contributes three clean methodological artefacts (the causal-vs-oracle selection test; the daily-MR
swap-isolation; the N_eff/relative-drift autopsy of a "Sharpe-1.0" pairs mirage).

## 4. §4 profile scorecard (why the *shape* fits but the *edge* doesn't)
| §4 axis | A stat-arb | B range | C daily-MR | required |
|---|:--:|:--:|:--:|---|
| tail-decorrelation vs book | ✓ | ✓ | ✗ (index beta) | ρ_tail ≤ 0.3 |
| presence ≤ 0.4 (intermittent) | ✗ (80-day holds) | ✓ | ✓ | ≤ 0.4 |
| short-hold / intraday-m ≤ 1.5 | ✗ | ✓ | ✓ | ≤ 1.5 |
| deleverageable | ⚠ | ✓ | ✓ | ✓ |
| **per-active-day edge SR ≥ 1.5** | ✗ | ✗ | ✗ | **the axis that cannot be engineered** |

Every piste fails the one axis §4 said cannot be manufactured — a **real two-sided edge**. §4 remains
*necessary, not sufficient*: it tells you what shape to build; it does not put an edge in the market.

## 5. What would have to be true to re-open any thread (nothing to run on the audited engine now)
- **A (gold/silver) on a NON-barrier account:** re-test the repo's 3A (Sharpe 0.77) with the daily
  engine here + real 2-leg cost/financing, **removing the −10 % floor constraint** — a personal-book
  question, not FTMO. This is the single most worthwhile follow-up.
- **B (XAU range-reversion):** only meaningful with **measured sub-spread execution** (maker rebate /
  MM-tier fills). Requires an execution-cost study, not more signal mining.
- **C:** none. Do not re-propose without a structurally non-up-drifting universe and a *significant*
  two-sided short leg — neither exists here.

## 6. Lesson candidate (NAMED, for reconciliation into the L-registry)
**`decorrelated-sleeve-triage-2026-07`** — *On the liquid retail-FTMO universe, the three "obvious"
market-neutral / reversion families (cointegration pairs, causal range-fade, daily index MR) each reduce
to one-sided drift after honest cost, and each is caught by a distinct cheap falsifier: (A) OOS-
cointegration + N_eff-honest leg asymmetry; (B) causal-vs-oracle regime detection; (C) the two-sided
short-leg event study. A "market-neutral" Sharpe ~1.0 with multi-week holds on a non-OOS-cointegrated
spread is the relative-drift beta trap — always split the legs and check OOS cointegration before
believing it.* (Generalises L27/L25/L43; consistent with `statarb_deepdive_ftmo`, `MR_deepdive_ftmo`,
`xauusd_rangefade`.)

---
*Reproduce:* pre-regs `piste_*/PREREGISTRATION.md` (frozen 13:52 UTC pre-results); engines `piste_*/run_*.py`;
independent check `synthesis/verify.py` → `VERIFICATION.md`; cost model `lib/ftmo_costs.py` (measured FTMO
anchors). Nothing deployed; no live file touched.
