# FTMO Challenge — Metrics & 2026 Weekly Simulation
### Strategy: index-core ORB ensemble (forward-validated), block-cap 1.5%

---

## 1. FTMO challenge rules & pass/fail metrics (recap)

| Metric | Value ($10k account) | Definition |
|---|---|---|
| **Profit target** (Phase 1) | **+10% = $1,000** → equity ≥ **$11,000** | must be reached to pass |
| **Max daily loss** | **5% = $500** | floor = (day-start balance) − $500, on *floating* equity; reset 00:00 CE(S)T |
| **Max overall loss** | **10% = $1,000** | static equity floor **$9,000**, on floating equity |
| **Min trading days** | **4** | days with ≥1 position opened (non-consecutive OK) |
| **Time limit** | none (we cap at **40 trading days** ≈ 2 months) | per the trader's brief |
| Phase 2 (Verification) | +5% target, same limits | binding case is Phase 1, modelled here |

**Three ways to fail:** (i) **daily breach** — floating equity drops below day-start − $500; (ii) **total breach** — floating equity below $9,000; (iii) **timeout** — target not reached in the window.

---

## 2. Strategy under test

Forward-validated **index-core ORB** (USDJPY removed — it failed forward validation as a yen-regime artifact):

| Sleeve | Open (EET) | OR window | Session block |
|---|---|---|---|
| US100 breakout | 16:30 (US cash open) | 30 min | PM |
| GER40 breakout | 16:30 (reacts to US open) | 15 min | PM |
| GER40 breakout | 10:00 (DAX open) | 30 min | AM |

Stop = opposite side of the opening range (1R); exit at session close (no overnight). **Risk = block-capped at 1.5% per session-open** (AM 1.5% on GER40; PM 1.5% split across US100+GER40us). Circuit-breaker: halt the day after −3%. Daily-loss enforced on floating equity.

---

## 3. 2026 weekly-challenge simulation (real path, deterministic)

One challenge started **every Monday, 5 Jan → 25 May 2026**, run on the actual 2026 market path (data ends 28 May; later starts are still running today, 1 Jun).

![2026 simulation](figures/s10_01_challenge_sim_2026.png)

| Start | Outcome | Days to resolve | Trading days | Trades | Peak eq | Trough eq | Final eq |
|---|---|---:|---:|---:|---:|---:|---:|
| 05 Jan | **PASS** | 35 | 35 | 105 | 11,458 | 9,334 | 11,458 |
| 12 Jan | **PASS** | 16 | 16 | 48 | 11,188 | 10,000 | 11,109 |
| 19 Jan | **PASS** | 25 | 25 | 75 | 11,336 | 9,242 | 11,336 |
| 26 Jan | **PASS** | 7 | 7 | 21 | 11,058 | 9,838 | 11,010 |
| 02 Feb | **PASS** | 15 | 15 | 45 | 11,358 | 10,000 | 11,358 |
| 09 Feb | **PASS** | 30 | 30 | 90 | 11,101 | 9,492 | 11,101 |
| 16 Feb | **PASS** | 25 | 25 | 75 | 11,060 | 9,877 | 11,060 |
| 23 Feb | **PASS** | 40 | 39 | 115 | 11,707 | 9,354 | 11,676 |
| 02 Mar | **PASS** | 35 | 34 | 100 | 11,787 | 9,417 | 11,755 |
| 09 Mar | **PASS** | 10 | 10 | 30 | 11,024 | 10,000 | 11,024 |
| 16 Mar | **PASS** | 10 | 10 | 30 | 11,047 | 9,683 | 11,024 |
| 23 Mar | **PASS** | 20 | 19 | 55 | 11,315 | 9,426 | 11,284 |
| 30 Mar | **TIMEOUT** | 41 | 40 | 116 | 11,032 | 9,120 | 10,793 |
| 06 Apr | RUNNING | 39 | 39 | 113 | 10,959 | **9,060** | 10,444 |
| 13 Apr | **PASS** | 5 | 5 | 15 | 11,718 | 9,841 | 11,687 |
| 20 Apr | RUNNING | 29 | 29 | 85 | 10,186 | 9,214 | 9,706 |
| 27 Apr | RUNNING | 24 | 24 | 70 | 10,760 | 9,733 | 10,253 |
| 04 May | RUNNING | 19 | 19 | 57 | 10,878 | 9,840 | 10,366 |
| 11 May | RUNNING | 14 | 14 | 42 | 10,253 | 9,274 | 9,770 |
| 18 May | RUNNING | 9 | 9 | 27 | 10,530 | 9,895 | 10,034 |
| 25 May | RUNNING | 4 | 4 | 12 | 10,473 | 9,970 | 10,111 |

### Aggregate (21 weekly challenges)

| Outcome | Count | % of all |
|---|---:|---:|
| **PASS** | 13 | **62%** |
| BUST — daily (−5%) | 0 | 0% |
| BUST — total (−10%) | 0 | 0% |
| TIMEOUT (40 days) | 1 | 5% |
| Still RUNNING (today) | 7 | 33% |
| **Pass rate among the 14 *resolved*** | 13/14 | **93%** |
| **Median time-to-pass** | **19 trading days** (range 5–39) | |

**Why zero busts?** The block-cap 1.5% sizing kept the realised daily loss under −5% on every day (worst single day −3.27%), and 2026 had no sustained chop-bleed to −10%. **But two challenges came within a whisker of the total floor** — the 6 Apr start dipped to **$9,060 (−9.4%)** and 30 Mar to $9,120. The −10% bust was *one bad day away*. The strategy ran close to the limit.

---

## 4. Full quant metrics

### Trade-level (2026, pooled across sleeves, net of cost + slippage)
| Metric | Value |
|---|---|
| Trades | 308 |
| Win rate | 44% |
| Avg win / avg loss | +1.47R / −0.96R |
| **Expectancy** | **+0.106R / trade** |
| Profit factor | 1.20 |
| Best / worst trade | +9.2R / −1.2R |
| Skew | +2.2 (positive — the edge is the right tail) |

### Continuous track record (2026, compounding, block-cap 1.5%)
| Metric | Value |
|---|---|
| Total return (≈5 months) | **+28.9%** |
| Annualised Sharpe (daily) | **1.62** |
| Max drawdown | **−8.2%** |
| Worst day / best day | −3.27% / +10.47% |
| % winning days | 48% |
| Trading days | 105 |

### Challenge-level
| Metric | Value |
|---|---|
| Pass rate (resolved) | 93% (2026) — *favourable regime; see caveats* |
| Bust rate | 0% (2026); historically via daily-breach at high sizing & total-breach in chop |
| Median time-to-pass | 19 trading days |
| Fastest pass | 5 trading days (13 Apr) |
| Closest call | −9.4% (6 Apr, near total-floor bust) |

---

## 5. Honest interpretation (read this before celebrating the 93%)

**2026 was a favourable regime, and these challenges are not independent.**

1. **Good draw.** 2026 ran at Sharpe 1.62 with every sleeve positive (US100, GER40, GER40@US all worked). The strategy thrives in trending/expansion regimes; 2026 was one. The **honest forward expectation across regimes is ~55%** (2021–25 average), with **chop years like 2023 ≈ 40%** and closer brushes with busts.
2. **Overlapping windows.** 21 weekly challenges on a single ~100-day path are heavily **correlated** — they largely share the same good period. The "93% of resolved" is one realisation, not a per-attempt probability. Treat it as "*a challenge started in early-2026 would very likely have passed*," not "*this strategy passes 93% of the time.*"
3. **Tail risk was live even in a good year.** Two starts dipped to −9.4% / −8.8% — a single adverse day from a −10% bust. The strategy operates **close to the floor**; in a worse regime the 0% bust rate would not hold.
4. **Realistic planning number: ~55% per attempt (~80% over two attempts)**, median ~19 trading days to pass, with disclosed sensitivities to slippage (−15 pts at 2×), exact open-timing (−10 pts, DST), and chop regimes.

**Bottom line:** 2026 confirms the edge is real and currently working (28.9% return, Sharpe 1.62, 0 busts, fast passes) — but the 62%/93% headline is a favourable, correlated sample. Plan to ~55%/attempt and run it block-capped with a live floating-equity kill-switch.
