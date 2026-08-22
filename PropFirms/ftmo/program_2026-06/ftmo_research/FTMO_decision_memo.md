# FTMO research — decision memo

*Synthesis of the full FTMO research arc (2026-06). One read to decide what to do.*
*Sources: `OVERNIGHT_drift_hardening.md`, `ALPHA_hunt_ftmo.md`, `MR_deepdive_ftmo.md`,
`statarb_deepdive_ftmo.md`, `breakout_deepdive_ftmo.md` (+ `_multiinstr`), `momentum_deepdive_ftmo.md`,
`swing_carry_deepdive_ftmo.md`, `dedale_eval_ftmo.md`. Real FTMO swaps: `ftmo_specs.csv` →
`code/ftmo_swaps.py`.*

---

## The decision

> **No retail-accessible price-pattern strategy — intraday *or* swing/multi-day — beats the ~50 % barrier on liquid FTMO instruments. Verified at depth across ~1,100 systematic trials and every major family, now with the trader's real FTMO swaps.** The **incumbent and current best vehicle is ORB-30min + floor_taper** (no-bust × unlimited-time exploit, ~46–50 % durable). The **overnight harvester is dead at the real swap** (US100 long −3.31 bps/night → p_funded **31 %**). **Carry is dead** (receivable < 1.2 %/yr, unwind tail −15 to −20 % breaches the 10 % floor). **Dédale** (the friend's carry+trend algo) is a decayed regime trade (flat at real swaps, p(pass) 22–30 %). The one genuinely reusable output is the **swap-sign guardrail** (`ftmo_swaps.py`): never hold the negative-swap side overnight — cost discipline, not alpha. FTMO is a *funding* mechanism, not an alpha source.

---

## The one unifying result

Every short-horizon family on liquid FTMO instruments — **directional and market-neutral, intraday and
swing** — reduces to **one-sided directional drift, or a decayed regime trade, after honest costs.** The
discriminating tests fire every time:

- **L25 two-sided test** — a real directional edge is positive on *both* legs. Every directional family
  is positive only on the **long** leg = the equity/carry up-drift = **beta**.
- **L26 delay test** — a real edge survives 1-bar execution delay. The apparent intraday edges live in
  same-bar fill / overlapping windows and **collapse**.
- **OOS / post-regime test** — the few cells that pass two-sided + delay (swing-MR) then **decay out of
  sample** and **don't generalise** (2/18 instruments).
- **DSR on the total search space** — the best in-sample t (≈3.5 for one swing-MR cell) sits at the
  multiple-testing bar and **fails once OOS decay is included**.

Because there is **no durable per-trade alpha**, a symmetric +10 %/+5 % barrier with no time limit pays
**~50 % by no-bust math** regardless of packaging. The recurring "~50 %" is the mathematical signature of
harvesting beta on a symmetric barrier, not bad luck.

---

## What was tested, and the verdict

| family | depth | key result | verdict |
|---|---|---|---|
| **Overnight harvester** (MA200-gated, NQ) | hardened: financing, crash-tail, time, √N, **real swap** | beta; in-sample 82–88 % swap-free, but **real US100 swap −3.31/night → p_funded 31 %** | **dead at real swap** |
| **Breadth alpha-hunt** (5 families) | 1 backtest each | all 0-EV or one-sided long beta; the "good" MR fade was an overlap+look-ahead artifact | rejected |
| **MR intraday** (deep) | ~350 trials | 0 two-sided unconditional; regime cells t ≤ 1.44, knife-edge, OOS-unstable | **closed** |
| **Stat-arb / pairs** (deep) | 18 pairs, 48 trials | half-life 22–180 d; FX breaks OOS; index pairs financing-killed; spread not two-sided | **closed** |
| **Breakout** (deep) | NQ fill-artefact + 190 multi-instr | same-bar fill artefact (collapses on delay); two-sided cells t ≤ 1.02 | **closed** |
| **Momentum** (deep) | 176 trials | most one-sided of all; best two-sided t = 0.41 | **closed** |
| **Swing momentum** (deep) | daily, indices+FX | weak, one-sided, delay-collapses — beta at a longer frequency | **closed** |
| **Swing mean-reversion** (deep) | ~346 swing trials | **closest candidate**: EURGBP in-sample t=3.53 (two-sided, delay-robust) — but **decays OOS** (US500 train 2.92→test 0.42; EURGBP train 3.75→test 0.89) and **doesn't generalise** (2/18) | **closed (higher-quality no)** |
| **Multi-day FX carry** (deep, real swaps) | rate-diffs + specs | receivable < 1.2 %/yr (markup-eaten); unwind DD −15 to −20 % > 10 % floor | **dead** |
| **Dédale** (friend's carry+trend) | our framework, real swaps | trend trade + tiny carry kicker (~0.3 %/yr); flat at real swaps, **p(pass) 22–30 %**; decayed post-2024 | **does not beat incumbent** |

Total systematic depth: **≈ 1,100 trials** across intraday and swing/multi-day — all under non-overlap +
per-trade cost + 1-bar-delay + two-sided + DSR-on-total-space, now with **real FTMO swaps**.

---

## The two things that came closest (and why they still fail)

**1. Swing mean-reversion (the closest).** Fading multi-day moves on range-bound FX crosses hit
**EURGBP in-sample t=3.53** — two-sided, delay-robust, the first cell ever to clear a DSR bar. It is a
*higher-quality* "no" than everything intraday, but the battery kills it: the short-term-reversal edge
has **decayed** (US500 dead post-2013; EURGBP weak post-2023) and is **instrument-specific** (2/18). Real
swaps were *not* the killer (EURGBP held +28.6 bps). If anything is pursued further it is a **small-sized
breadth basket** of the few two-sided swing-MR instruments (EURGBP, UK100, USDJPY, AUDJPY/EURJPY),
explicitly accepting it is thin, decaying and may already be arbitraged.

**2. The overnight harvester (the only positive beta).** In-sample 82–88 % swap-free, but the **real
US100 long swap (−3.31 bps/night)** pushes the net edge to ~+0.2 bps/night and **p_funded to 31 %**. The
overnight equity premium is *long* but the positive-swap side of an index is *short* — you cannot collect
the premium without paying the swap. Plus the 30-day inactivity rule (keep-alive needed) and NDX
concentration. **Dead unless a swap-free account is available** (then ~75–80 %, minus the crash tail).

---

## The one keeper: the swap-sign guardrail (`ftmo_swaps.py`)

Distilled from Dédale's smartest line (`if swap<=0 don't trade that side`) and confirmed with the real
specs. It is **cost discipline, not alpha**:
- `swap_allowed(symbol, side)` — never hold the negative-swap side overnight.
- It **explains and confirms** the overnight-indices death (US100 long −3.31 → 31 %).
- It **trims** FX multi-day financing (EURGBP swing-MR short-only +35 vs +28.6 bps) — but makes the
  strategy one-sided and cannot fix OOS decay.
Adopt it as a hard filter on anything held across the broker rollover. Wired into `swing_deepdive.py`
(`trades_guarded`) and `overnight_harvester_sim.py`.

---

## Recommendation

1. **Stop mining price-pattern families on liquid FTMO majors — intraday *and* swing are now both
   exhausted at depth.** The anti-false-positive protocol (non-overlap + delay + two-sided + OOS + DSR +
   `ftmo_swaps`) is built and reusable — use it as a *gate*, not a miner. Further "wins" here will be
   L26/L31 artifacts.
2. **Use the incumbent.** ORB-30min + floor_taper (~46–50 %) is the best vehicle. The overnight harvester
   is dead at the real swap (31 %); Dédale is flat post-decay; carry breaches the floor. Don't deploy
   those expecting to beat ~50 %.
3. **Make the swap-sign guardrail standard** on any overnight hold (`ftmo_swaps.swap_allowed`).
4. **If you still want price-pattern EV:** the only residual lead is the swing-MR breadth basket on
   range-bound FX crosses — small size, eyes open that it's decaying. Otherwise, EV lives **off this
   menu**: a genuinely +EV FX/index book run on the *funded* account, or breadth (√N) across many
   independently-+EV sleeves, or sub-bp execution. (Crypto books are **not** FTMO-actionable.)
5. **Reframe the goal.** FTMO is funding, not alpha. Pass the barrier with the cheapest rule-clearing
   vehicle, accept ~50 %, and put real EV-search where it can actually live.

---

## Reusable methodology lessons (proposed registry adds)
- **L26** — overlapping-window / same-bar-fill screens inflate intraday edges; validate with
  non-overlapping trades + a 1-bar-delay test (decisive). Confirmed on MR (overlap) and breakout (fill).
- **L27** — market-neutral *by construction* ≠ two-sided *in spread*: a cointegrated spread inherits a
  relative drift, so even stat-arb fails the two-sided test. The beta trap survives hedging.
- **L28** — a market-neutral CFD pair pays **2× broker markup** in financing (benchmark cancels across
  legs) ≈ 1.5 bps/night in *every* rate era → fatal to weeks-to-revert spreads.
- **L29** — half-life-matched holding is necessary but not sufficient: fixing the exit did not manufacture
  EV; it only removed a confound so the true "no" could be seen.
- **L30 — swap-sign rule (Dédale, codified `ftmo_swaps.py`).** Real FTMO swaps are **asymmetric** (you
  pay more than fair on the costly side, receive less than fair on the carry side = broker markup). Never
  hold the negative-swap side overnight. Decisive case: US100 long −3.31 bps/night ⇒ overnight harvester
  31 %. The overnight equity premium (long) and an index's positive swap (short) **cannot be collected
  together**.
- **L31 — carry / short-term-reversal alpha-decay.** Carry-trend (Dédale, JPY 2022–24) and intraday/swing
  short-term-reversal (US indices pre-2013, EURGBP 2022–23) were real *in their regimes* and have decayed.
  Today's receivable carry is markup-eaten (< 1.2 %/yr) and carries an unwind tail (−15 to −20 %) that
  breaches the 10 % floor. **OOS / post-regime testing is mandatory** before citing any carry or reversal edge.

*Memo updated 2026-06-02. Artifacts: `code/{overnight_harvester_sim, mr_intraday_screen, mr_deepdive,
statarb_deepdive, directional_deepdive, swing_deepdive, ftmo_swaps}.py`; grids `*_grid.csv`; real swaps
`ftmo_specs.csv`.*
