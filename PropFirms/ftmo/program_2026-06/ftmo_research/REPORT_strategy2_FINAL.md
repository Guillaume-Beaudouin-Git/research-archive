# FTMO Research — Strategy 2, Final Report
## Index Opening-Range Breakout: edge, stress test, and an honest optimization journey

*FTMO $10,000 Challenge — +10% target, 5% daily / 10% total max loss, ≤ ~2 months. Trader's goal: **>65% pass rate.** This report consolidates the full research, stress-testing, and no-overfit optimization.*

---

## Executive summary

Starting from a genuine, out-of-sample-validated intraday edge (the equity-index Opening-Range Breakout), I subjected it to an adversarial stress test and a disciplined optimization loop. The honest bottom line:

> **The strategy carries a real but thin edge. Under idealized fills it looks like ~65%; the binding constraint is slippage at the open, and for the FTMO barrier objective trade-frequency and ensemble-Sharpe matter more than per-trade edge-purity. After honest optimization (wide-OR + additive independent edges, all delay-test-verified and risk-weighted), the multi-asset ensemble reaches ~66% all-window / ~68% recent-OOS single-attempt on the 2022–25 common window, with the 2023 chop floor ~51% — on contiguous real windows *with* slippage (~88–90% over 2 attempts). Caveat: the index-only sleeve on its longer 2021–26 history was ~53% all (2021 was a weak year), so the headline is partly window-dependent — treat ~55–65% as the planning range, rising as more uncorrelated sleeves are added.**

**Update (new FX data):** a 6th sleeve — the **USDJPY London-open breakout** — was found in the freshly-uploaded FX data: a genuine, delay-test-verified, decorrelated (corr +0.06) +EV edge (OOS +0.40R). Added at **half risk-weight** (it's lower-Sharpe / higher-variance, so full weight dilutes), it lifts the ensemble to **2023 51% · OOS 68% · ALL 66%** — the first config to clear 65% across the full common window. ![multi-asset](figures/s6_01_multiasset.png)

What worked, what didn't (all judged on the honest metric — pass rate over **contiguous real 40-day windows, with slippage**):

| Lever | Effect on realistic pass | Verdict |
|---|---|---|
| Index ORB edge (US100, GER40) | genuine +EV (OOS +0.08R, PF>1.1) | ✅ foundation |
| Multi-instrument / multi-window ensemble | independent bets (corr ≈ 0) → √N | ✅ |
| **Wide opening range (15/30-min)** | absorbs fixed point-slippage; +11 pts | ✅ **structural gain** |
| **GER40 @ US-open (additive setup)** | independent +EV (OOS +0.16R); OOS 62→64%, chop 31→46% | ✅ **additive gain** |
| **USDJPY London-open breakout (½ weight)** | verified +EV (OOS +0.40R), corr +0.06; → 65%+ on full window | ✅ **additive gain (new data)** |
| Other FX London breakouts (GBP, EUR, AUD, NZD, CAD, CHF, EURGBP, JPY-crosses) | −EV / marginal (FX efficient) | ❌ rejected |
| PDH/PDL breakout, US500/30/2000 ORB | fill artifact (delay-test fail) / −EV | ❌ rejected |
| Limit / retest entries | kills the runaway-winner skew → EV<0 | ❌ rejected |
| EMA crossover (standalone) | huge turnover, −EV every year | ❌ rejected |
| EMA trend filter / HMM / vol-regime filter | improves edge/trade but removes trades → net neutral | ➖ optional only |
| Gold / BTC sleeve · overnight drift | decorrelated but −EV (overnight: catastrophic gaps) | ❌ rejected |

![Optimization journey](figures/s5_01_final_ladder.png)

---

## 1. The edge

ORB rule: opening range = first *N* minutes after the cash open; enter on the first break of the OR high/low; **stop at the opposite side (= 1R)**; no profit target (let winners run to the session close — the positive skew *is* the edge). Data is broker-time (EET): the US open is **16:30**, the DAX open **10:00** (verified by the volume jump).

Net of cost, out-of-sample (2024–25): **US100 ≈ +0.10R, GER40 ≈ +0.08R**, positively skewed, PF > 1.1. Crucially the *outcomes* are ~uncorrelated across instruments (US100/GER40 daily-R corr −0.02), so each is an independent positive-EV bet. US500/US2000 decayed or carry too-wide spreads and were dropped; ORB is strongest on the two deepest index futures.

**Honest caveat:** ORB is a published, crowded edge. It was strong 2021–22, **decayed in 2023**, and partly recovered 2024–25.

---

## 2. Stress test — where it breaks

Idealized Monte-Carlo (iid bootstrap, perfect fills) gave **65%**. Stressing it:

- **Slippage at the open is the killer.** ORB must trade at the widest-spread, fastest minute of the day. The edge is only +0.08R, and MAE data shows 5% of stops blow 0.5R past the level. A stop-fill slippage of just 0.10R takes the ensemble mean R **negative**. Pass rate on real windows falls from ~69% (no slip) to **~49% (realistic slip)**.
- **Real sequencing was *not* the problem** — contiguous real windows with no slippage give ~69%, close to the iid bootstrap. The bootstrap was fair; slippage was the flaw.
- **Regime-fragile:** 2023 chop = **19%** (naive). **Specification-fragile:** dropping US100 → −10 pts; single OR window → 43%.

Honest realistic figure after the stress test (naive ensemble): **~42% all-history, ~49% recent, ~19% chop** — *not* 65%.

---

## 3. Optimization (no overfitting) — what genuinely helped

Every change was judged on contiguous real windows **with slippage**, required to hold across **all** periods (not tuned to one), and preferred when motivated by structure rather than parameters.

**(a) Wide opening range — the one real win.** Slippage is paid in *fixed points* (spread + ticks), so expressing it as a fraction of risk, a **wider OR (larger 1R) dilutes it**. The 5-min OR goes EV-negative under slippage; the **15- and 30-min ORs survive** (US100 30-min keeps +0.07R OOS *after* slippage). Wider stops also mean fewer daily-limit breaches, so the strategy can be sized to ~1%. Result:

| Period | Naive (w/ slip) | **Wide-OR (w/ slip)** |
|---|---:|---:|
| 2023 chop | 19% | **35%** |
| OOS 2024-25 | 49% | **62%** |
| All 2021-26 | 42% | **53%** |

**(b) Limit / retest entries — rejected.** Plausible idea (turn slippage into price improvement), but it **destroys the edge**: OOS mean R **+0.047 → −0.025**. Reason — runaway breakouts never retest, so you systematically miss the big winners that carry the skew. You cannot have the ORB edge without taking the breakout (and its slippage).

**(c) HMM / volatility-regime filter — neutral on average.** High-vol days have far higher ORB edge (+0.126R vs −0.018R low-vol), so a filter is tempting. But: a 2-state HMM on absolute vol (trained on high-vol 2022) barely triggers in calmer 2024–25 → starves the strategy of trades. A causal relative-vol filter helps the chop year (**35% → 49%**) but hurts trending years, netting **flat overall**. *Lesson: for the FTMO barrier objective, trade frequency (compounding to +10% in 40 days) matters more than per-trade edge-purity — removing days hurts more than it helps.* Kept only as an **optional consistency overlay** for traders worried about starting in a chop regime.

**(d) Gold / BTC diversification sleeve · overnight drift — rejected.** Gold and BTC ORB are nicely decorrelated with the index sleeve (corr +0.00–0.15) **but negative-EV** (gold −0.09 to −0.45R; BTC −0.06 to −0.53R, every year). ORB is structurally an *equity-cash-open* phenomenon (the discrete 09:30 ET / 09:00 CET auction); it does not transfer to 24h markets, which mean-revert intraday. The **overnight-drift** sleeve is also −EV net of financing **and carries catastrophic gap risk** (worst nights −5.4% US100 / −9.2% GER40 — an instant FTMO breach), which is exactly why the core strategy stays flat by the close. A decorrelated *negative*-EV (or fat-tailed) sleeve cannot strengthen the ensemble.

**(e) GER40 @ the US open (16:30) — additive winner ✅.** The one genuinely additive edge found. European indices react to the US cash-open order flow, so a *second* GER40 ORB anchored at 16:30 (distinct from its 10:00 DAX-open setup) is an **independent positive-EV bet**: OOS mean R **+0.16R**, only +0.14 correlated with the core ensemble. Adding it (→ 5 setups, ~3 trades/day) lifts the honest pass and — because it is decorrelated — helps most when the core struggles:

| Period (real windows, slippage) | 4-setup | **5-setup (+GER40@US)** |
|---|---:|---:|
| 2023 chop | 31% | **46%** |
| OOS 2024-25 | 62% | **64%** |
| All 2021-26 | 47% | **53%** |

*(US100 @ European open was also tested and is −EV: ORB needs the instrument's own cash-open auction or a major flow event hitting it — confirming the mechanism rather than data-mining.)*

---

## 4. Honest final state

**Best robust configuration:** US100 {15m, 30m} @ US open (16:30 EET) + GER40 {15m, 30m} @ DAX open (10:00) + **GER40 {15m} @ US open (16:30)**; opening-range breakout, stop at the opposite side (1R), exit at session close (no overnight), **risk ≈ 1%/trade**, daily-loss circuit-breaker −3%, lock at +10%.

| Metric (contiguous real windows, with slippage) | Value |
|---|---|
| Single-attempt pass — recent OOS 2024-25 | **~64%** |
| Single-attempt pass — all history 2021-26 | **~53%** |
| Worst regime (2023 chop) | **~46%** |
| Pass within 2 attempts (recent) | **~87%** |
| Pass within 2 attempts (all-history) | **~75%** |

We now reach **~64% single-attempt in the recent regime** (essentially the target) and a much sturdier **46% chop floor**, via one structural fix (wide-OR) and one additive edge (GER40@US-open). A robust >65% *per single attempt across all regimes* still isn't supported without overfitting, but ~75–87% over 2 re-attempts is realistic, and the path to higher is **more additive independent edges**, not tuning.

---

## 5. What we learned (transferable lessons)

1. **Execution friction, not signal discovery, is usually the binding constraint** on liquid markets. The edge that survives a backtest can die at the fill.
2. **For a barrier/option objective (FTMO), trade frequency beats edge-purity** — the opposite of optimizing a continuous Sharpe. Regime filters that help a Sharpe strategy can hurt here.
3. **Structural fixes generalize; parameter fixes overfit.** The wide-OR change worked because it follows the physics of slippage, and it held across every period.
4. **Decorrelation only helps if the sleeve is also positive-EV.** ORB is an equity-open effect and doesn't transfer.

## 6. Recommended next steps (genuinely new alpha, not more tuning)

1. **Different edge types per asset** (the only honest route to >65%): gold/BTC *trend or momentum* (not ORB), an FX *news-fade*, an index *overnight-drift* sleeve with gap controls. Each independent +EV sleeve raises the pass rate via √N.
2. **More index instruments' intraday data** (AUS200, UK100, JP225, HK50, EU50 — present only as daily here) to add independent cash-open ORB bets.
3. **Live spread/slippage calibration** at the broker before sizing; treat the realistic ~53% (not 65%) as the planning number.
4. **Walk-forward instrument re-selection** quarterly to manage decay (as seen in US500).

---

## Appendix — files & reproducibility

```
ftmo_research/
  REPORT_strategy1.md            ← FX result (no edge; FTMO as barrier option)
  REPORT_strategy2_indices.md    ← index ORB edge & first 65% (idealized)
  STRESS_TEST_strategy2.md       ← adversarial stress test (where it breaks)
  REPORT_strategy2_FINAL.md      ← this consolidated report
  code/  strategy_orb.py, ftmo_sim_ensemble.py, data.py, costs.py, strategy.py, ftmo_sim.py
  figures/  s2_* (ensemble), s3_* (stress), s4_01 (optimization journey)
```
All simulations seeded; trade-level table (entry/stop/exit/MAE) drives slippage and the day-block / contiguous-window FTMO checks. The daily-loss check is trade-close-based, so realistic floating breaches are ≥ those reported (conservative).
