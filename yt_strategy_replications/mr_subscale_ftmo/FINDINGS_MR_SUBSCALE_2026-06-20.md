# FINDINGS — Sub-15-min mean-reversion: does the edge live at a finer scale?
**Date:** 2026-06-20 · **Pre-registration:** `PREREGISTRATION.md` (frozen before any return/AC result).
**Type:** STRICT preliminary, reimplemented engine → independently audited (author≠auditor). No git HEAD ops
(shared dir, 2026-06-19 incident); live book read-only; nothing deployed.

## 0. Verdict — (b) THE EDGE IS REAL, THE RETAIL CFD VEHICLE KILLS IT
A genuine, **two-sided** short-horizon reversal exists at **M2–M5** on equity-index and FX CFDs — gross (zero-cost)
Sharpe ~1.4–2.4, HAC t-stat **+4 to +11**, both legs positive, stable across sample halves, look-ahead-free, and
**not** a bid-ask-bounce artifact (it is ~0 at M1 and *grows* with aggregation; bounce would do the opposite).
**But it is annihilated net of the spread** at every fine scale: the reversion is ~0.05–0.10 bps/bar (≈0.1–0.2
bps/trade) while the measured RT spread is 0.2–1.2 bps, at 130k–1.5M trades/yr → net Sharpe −2 to −50.

This is verdict **(b)** of the three pre-registered outcomes: **the signal exists; the vehicle (retail-CFD cost) is
the problem.** The required cost tier to break even is **~0.1–0.2 bps RT — institutional/DMA**, not retail. So it
redirects to the §4 "lower-cost venue" lever, and it generalises **L34** (flow-anchored edges are institutional-tier
only) and **L33b** from FX-fix/intraday-flat to the whole sub-15-min reversal family. For an FTMO/retail vehicle it
is **off-table** — but, unlike the 15-min MR and the event family, the obstacle is **cost, not absence of signal.**

> Confidence tag: this is a NEGATIVE *for the retail vehicle* (definitive) and a POSITIVE *gross-edge diagnostic*.
> It is NOT a deployable candidate (net-negative on every accessible venue). It would only become a Claude Code
> revalidation candidate if a sub-0.2-bps execution venue were actually available — which the repo's own L34/L33b
> say it is not at retail.

## 1. Q0 — data & cost credibility (blocking gate, PASSED with caveats)
- **Finest scale = M1** (no tick data in the store) → true sub-minute microstructure is out of scope (stated limit).
- **Spread** well-populated/credible for indices (US100 ~0.5–2 bps over time); **FX spread has many zero entries
  post-2021** → floored. The MT5 quoted spread is a **lower bound** on real retail cost → all net figures here are
  **optimistic**; the true net is worse. A verdict that survives the lower bound is robust — and the verdict is "dead net."

## 2. Q1 — autocorrelation vs cost (measure-first): a net edge is IMPOSSIBLE at every scale
reversion amplitude = |AC(1)|×σ_bar (bps) vs RT spread (bps). **ratio = amplitude/spread:**

| | M1 | M2 | M5 | M15 |
|---|--:|--:|--:|--:|
| US100 | 0.03 | 0.02 | 0.10 | 0.03 |
| US500 | 0.01 | 0.02 | 0.10 | 0.07 |
| US30 | 0.02 | 0.06 | 0.05 | 0.35 |
| GER40 | 0.03 | 0.15 | 0.33 | 0.27 |
| EURUSD | 0.07 | 0.13 | 0.31 | 0.16 |
| GBPUSD | 0.08 | 0.14 | — | — |

**Every ratio ≪ 1 (max 0.35).** The predictable reversion is 3–30× smaller than the spread. AC(1) is ~0 at M1
(even +0.004 on US indices = mild momentum) and turns weakly negative only at M2–M5 (max |AC|≈0.026, GER40 M5) →
genuine but tiny reversal, **not** bounce-dominated.

## 3. Q2 — confirmatory backtest (gross two-sided + net), unconditional 1-bar reversal
Per bar, fade the prior bar, hold 1 bar (the pure AC harvester). Gross = zero-cost; net subtracts the measured spread
on each position change. (HAC lag-6 t; SR annualised.)

| sym | M5 gross bps/bar | gross t | SR_gross | leg up / dn | spread bps | net SR |
|---|--:|--:|--:|--:|--:|--:|
| US100 | +0.084 | +4.0 | +1.07 | +0.05 / +0.12 | 0.80 | −6.2 |
| US500 | +0.103 | +6.5 | +1.67 | +0.07 / +0.15 | 1.19 | −8.7 |
| US30 | +0.053 | +3.2 | +0.88 | +0.03 / +0.08 | 0.39 | −2.4 |
| GER40 | +0.094 | +6.2 | +1.69 | +0.07 / +0.13 | 0.63 | −4.6 |
| EURUSD | +0.058 | +10.2 | +2.30 | +0.07 / +0.04 | 0.23 | −2.2 |
| GBPUSD | +0.067 | +10.8 | +2.42 | +0.08 / +0.06 | 0.37 | −5.9 |

- **Gross passes gate 1 (HAC-t≫2.5) and the two-sided test (L25)** — both legs positive on every instrument; this is
  a real reversal, not the long-only beta trap that killed the 15-min MR. At **M1** the edge is ~0 (no exploitable
  reversal at the very finest scale → the 15-min "no sign" was scale-averaging of a real M5 effect).
- **Net fails catastrophically at every scale** (SR −2 to −50). Thresholding (fade only |move|>p80) does not rescue it
  (US100 thresholded net SR −4 to −21). **DSR(net, N_trials=135) ≈ 0.**
- **§4 excursion (m):** a 1-bar (5-min) hold has adverse excursion ≈ 1 ATR → **m ≈ 1 < 1.5** ✓, and a thresholded
  version is intermittent (presence ≤0.4). So the edge would fit the §4 *shape* axes — the sole blocker is cost.

## 4. Q3 — the cost wall (where is breakeven?)
Gross reversion grows toward coarser bars (M1≈0 → M5≈0.06–0.10 bps) while the spread is ~scale-invariant
(0.2–1.2 bps); trade count falls with bar size. Net is "least bad" around **M5** but **never positive at any tested
scale** (M1/M2/M5/M15). Per-trade gross ≈ 0.1–0.2 bps ⇒ **breakeven RT cost ≈ 0.1–0.2 bps** = institutional/DMA tier.
Retail CFD (0.2–1.2 bps measured, more in reality) is 2–10× above breakeven. **There is no retail frequency that works.**

## 5. Independent audit (author≠auditor) — verdict CONFIRMED
From-scratch reimplementation: US500 M5 gross +0.0855 bps/bar (HAC-t +5.29, SR 1.38; legs short +0.057 t2.45 / long
+0.122 t5.05); EURUSD +0.0414 (t +7.26, SR 1.60; both legs +). Stable across halves. Predictive regression
r_t~r_{t-1}: slope −0.0158 (t −2.59) US500, −0.0112 (t −4.28) EURUSD → genuine forecastable reversal. **No look-ahead**
(timing verified; legit edge ~50–100× smaller than the same-bar cheat). **Not bounce** (edge grows M1→M5).
**Net killed by spread.** Colleague's verdict (b) CONFIRMED.

## 6. Redirect (per the pre-registered map)
Verdict (b) ⇒ **the edge exists, the vehicle is the blocker** ⇒ §4 "lower-cost venue" lever, with a hard number:
needs **≤~0.15 bps RT**. Practical reading: this is an **institutional-microstructure** edge (cf. L34); for a
retail/FTMO setup it is **not reachable**. The honest options it points to:
1. **Lower-cost execution** (DMA futures/equities at exchange/rebate tier, maker fills) — the only path that could turn
   the real gross edge net-positive; outside the retail-CFD scope and likely outside an FTMO vehicle.
2. **A different data axis** (order-flow / depth) — what actually drives this transitory reversal; the price-only
   shadow of it is too small to clear retail cost.
Price-only OHLC is now exhausted across scales for MR: 15-min = no signal; M2–M5 = real signal, cost-dead at retail.

**Lesson candidate (NAMED, to engrave at reconciliation):**
`sub-15min-reversal-is-real-two-sided-but-institutional-tier-only` — a genuine two-sided short-horizon reversal lives
at M2–M5 (gross SR 1.4–2.4, HAC-t +4..+11, both legs +, look-ahead-free, not bounce, grows M1→M5) but per-trade gross
~0.1–0.2 bps ⇒ breakeven RT ≈0.15 bps ⇒ retail CFD spread (0.2–1.2 bps) kills it at every scale (net SR −2..−50).
Distinct from the 15-min MR death (there: no signal even gross). Generalises L34/L33b to the intraday-reversal family.

## 7. Reproduce, ledger & handoff (no git ops performed)
```
cd yt_strategy_replications/mr_subscale_ftmo
/usr/bin/python3 q1_q3_diagnostic.py   # AC + reversion-amplitude/spread ratio (Q1/Q3 cost wall)
/usr/bin/python3 q2_confirm.py         # gross two-sided + net harvester (Q2 confirmation)
```
Data: `data/deep_history_utc/*_M1.csv` (true-UTC, spread column). `n_tests` added ≈ **6** (pre-registered grid),
deployable verdict FAIL net — increment the program ledger. **Isolation:** additive folder, zero git HEAD ops; commit
recipe identical to `intraday_mr_ftmo/FINDINGS.md §7`; run `tools/check_register_integrity.py` in the MAIN dir before any commit.
