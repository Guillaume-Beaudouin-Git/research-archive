# Indices Swing — Sprint 2 Postmortem

**Date**: 2026-05-23  
**Outcome**: FAIL → ARCHIVE  
**n_tests**: 92 (Sprint 1 IC scan) + 8 (Sprint 2 backtests) = **100 total**

---

## What Was Tested

**Sprint 1 (IC scan)**: 6 signals × 4 horizons × 3 assets (SPY, QQQ, EWQ).
- 12 GO signals identified: S1 VRP (SPY h=1,3; QQQ h=1,3,5,10), S2 VIX term (SPY h=1,3,5,10; QQQ h=1; EWQ h=1)
- All 12 passed 4-gate IC filter: |IC|>0.02, |t_HAC|>2.0, stability>0.70, post-2020 consistent.

**Sprint 2 (full backtest)**: Vol-targeted daily positions on 5 unique (signal, ticker) pairs + 2 combined + 1 ERC portfolio.
- vol_target = 10%, cost = 0.10% RT (ETF), walk-forward 5 folds.

---

## Results

| Strategy | Gross SR | ETF net (0.10%RT) | Fut net (0.01%RT) | Turnover/yr | Verdict |
|----------|----------|-------------------|-------------------|-------------|---------|
| S1 VRP SPY | 0.309 | 0.143 | 0.292 | 47× | FAIL |
| S1 VRP QQQ | 0.467 | 0.341 | 0.454 | 33× | FAIL |
| S2 VIX SPY | 0.184 | −0.129 | 0.153 | 72× | FAIL |
| S2 VIX QQQ | 0.174 | −0.085 | 0.148 | 56× | FAIL |
| S2 VIX EWQ | 0.259 | 0.017 | 0.235 | 53× | FAIL |
| Combo SPY | — | 0.171 | — | — | FAIL |
| Combo QQQ | — | 0.319 | — | — | FAIL |
| ERC Portfolio | — | 0.088 | — | — | FAIL |

Gates: RESEARCH_PASS requires Sharpe>0.7, MaxDD>−25%, WF>50%.
**All 8 strategies fail RESEARCH_PASS.** Even with 10× cheaper futures execution, the best achievable is Sharpe 0.454 (S1 QQQ).

---

## Root Cause Analysis

### 1. IC Magnitude Too Small

The IC (Spearman rank) of 0.033–0.075 is statistically significant (t>2.0) but economically tiny.
Theoretical pre-cost Sharpe (Grinold–Kahn): `IC × sqrt(252)` = 0.052–1.19.
Observed gross Sharpe: 0.18–0.47 — **only 35–40% of the Grinold prediction**.

The gap arises because:
- Spearman IC ≠ linear Pearson IC (rank correlation does not directly map to P&L)
- Vol-targeting adds position noise from rolling vol estimation
- Signal autocorrelation reduces effective breadth well below 252

### 2. High Turnover (33–72×/year) Destroys Edge

Daily vol-targeted rebalancing generates position turnover of 33–72× per year.
- At 0.10% RT (ETF): annual cost drag = 33–72 × 0.05% one-way × 252 ≈ 2–5%/year
- Signal edge (gross annual return ≈ SR × vol = 0.18–0.47 × 10%) = 1.8–4.7%/year
- Net: cost ≈ signal → near-zero or negative P&L

S2 VIX term is particularly extreme: 72× turnover because VIX9D/VIX is very noisy day-to-day. The signal generates large position changes daily, overwhelming the weekly-to-monthly IC signal.

### 3. S2 Direction Anomaly

S2 (VIX term structure) shows IC=−0.042 (backwardation → bullish) but the signal is noisy at daily frequency. The IC captures a weekly-to-monthly regime effect that doesn't survive daily rebalancing friction.

---

## What Passed / Survived

- **S1 QQQ WF=80%**: 4/5 OOS folds positive — the VRP signal has genuine, persistent directional edge on QQQ. It is just too small to run as a standalone strategy.
- **S2 stability=0.94–0.97**: The VIX term structure IC is extremely stable over rolling 2y windows. It is a real risk regime indicator, but daily rebalancing destroys the edge through costs.

---

## Lessons Learned

**L14 (NEW)**: IC significance ≠ backtest viability. For daily-rebalanced strategies, a cost-adjusted IC gate is required BEFORE running a full backtest:

> `IC_min_required > (RESEARCH_SHARPE × vol_target + annual_cost) / vol_target / sqrt(252)`
> With RESEARCH_SHARPE=0.7, vol=10%, annual_cost=2% (33× turnover × 0.10% RT):
> IC_min > (0.7 × 0.10 + 0.02) / 0.10 / sqrt(252) = (0.07 + 0.02) / 0.10 / 15.87 ≈ **0.057**

S1 QQQ at h=5,10 had IC=0.073–0.075, just above this threshold, but the Grinold multiplier correction (actual gross SR ≈ 0.40 × IC × sqrt(252)) means it still fails.

**For future screening**: Daily-rebalanced equity swing signals need IC > 0.10 to survive costs at 0.10% RT ETF, or IC > 0.06 for futures execution (0.01% RT).

---

## Why This Direction Is Closed

1. Signal ICs are 0.033–0.075, well below the viable threshold for daily execution
2. Even with futures costs (10× cheaper), max achievable Sharpe = 0.454 for best signal
3. RESEARCH_PASS requires Sharpe > 0.70 → gap of 0.25 Sharpe (56% improvement needed)
4. No modification achievable within max-3-modification rule can close this gap — the IC magnitude is a fundamental property of the signal, not a tunable parameter
5. Modification count: Sprint 1 (IC scan) + Sprint 2 (backtest) = 2 of 3 allowed; remaining 1 modification insufficient to reach 0.70 from 0.45

---

## What Would Change the Verdict

This research direction would only be re-opened if:
1. A new high-IC variant of VRP is discovered (IC > 0.10 at h=1) — e.g., model-free implied variance vs realized
2. A slower signal (monthly VRP changes, quarterly term structure) shows IC > 0.10 at monthly frequency
3. These signals serve as INPUTS to a larger multi-signal ensemble where each contributes alpha in a regression framework (not standalone strategies)

**Archive status**: CLOSED. Do not re-propose without IC > 0.10 or a fundamentally different execution framework.
