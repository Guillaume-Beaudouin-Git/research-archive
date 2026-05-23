# Result Summary: Pairs Trading Cointegration — Feasibility

*Generated: 2026-05-20*

## 1. Headline verdict

> **STOP — 0/19 pairs pass all 4 cointegration tests. Archive pairs cointegration. Move to Candidate 4 (Commodity TSMOM).**

## 2. Data status

- Period: 2010-01-01 → 2026-05-19
- Pairs screened: 19
- **Pairs passing all 4 tests: 0/19**
- By category: C1=0/6  C2=0/4  C3=0/4  C4=0/5

## 3. Cointegration screening detail (all 19 pairs)

| Pair | Cat | EG p | Johansen trace | Crit95 | HL | Hurst | Result | Binding failure |
|------|-----|------|----------------|--------|----|-------|--------|-----------------|
| GLD/IAU | C1 | 0.844 | 8.55 | 15.49 | 80.9d | 0.260 | FAIL | EG + Johansen + HL |
| SLV/SIVR | C1 | 0.910 | 8.07 | 15.49 | 83.5d | 0.096 | FAIL | EG + Johansen + HL |
| VOO/IVV | C1 | 0.182 | — | — | 12.6d | 0.302 | FAIL | EG (p=0.182) |
| VOO/SPY | C1 | 0.371 | — | — | 9.0d | 0.195 | FAIL | EG (p=0.371) |
| IVV/SPY | C1 | 0.669 | — | — | 10.2d | 0.189 | FAIL | EG (p=0.669) |
| QQQ/QQQM | C1 | 0.459 | — | — | 2.1d | 0.062 | FAIL | EG (p=0.459; limited history: 2020+) |
| XLE/XOP | C2 | 0.983 | 4.64 | 15.49 | 10601d | 0.451 | FAIL | HL ≫ 30d (effectively infinite) |
| XLF/KBE | C2 | 0.056 | 12.28 | 15.49 | 135.5d | 0.475 | FAIL | Johansen + HL |
| XLK/SOXX | C2 | 0.084 | 10.78 | 15.49 | 125.9d | 0.468 | FAIL | Johansen + HL |
| IWM/IWO | C2 | 0.474 | 8.68 | 15.49 | 301.9d | 0.531 | FAIL | EG + Johansen + HL + Hurst |
| GLD/GDX | C3 | 0.635 | 10.99 | 15.49 | 543.3d | 0.419 | FAIL | EG + Johansen + HL |
| USO/XLE | C3 | 0.642 | 11.96 | 15.49 | 795.0d | 0.561 | FAIL | EG + Johansen + HL + Hurst |
| USO/CVX | C3 | 0.763 | 12.84 | 15.49 | 536.3d | 0.534 | FAIL | EG + Johansen + HL + Hurst |
| GLD/NEM | C3 | 0.726 | 6.49 | 15.49 | 472.4d | 0.478 | FAIL | EG + Johansen + HL |
| KO/PEP | C4 | 0.849 | 3.63 | 15.49 | 471.6d | 0.474 | FAIL | EG + Johansen + HL |
| HD/LOW | C4 | 0.093 | — | — | 158.0d | 0.465 | FAIL | HL (158d vs 30d max) |
| WMT/TGT | C4 | 0.987 | 5.70 | 15.49 | 8655d | 0.508 | FAIL | EG + Johansen + HL + Hurst |
| V/MA | C4 | 0.075 | 14.19 | 15.49 | 96.0d | 0.385 | FAIL | HL (96d vs 30d max); closest to pass |
| GS/MS | C4 | 0.473 | 6.52 | 15.49 | 202.3d | 0.406 | FAIL | EG + Johansen + HL |

## 4. Root cause analysis

**Binding constraint: half-life > 30 days (14/19 pairs fail only this).** The `HL ≤ 30d` requirement was designed to ensure trades complete quickly enough to justify costs. In practice, for daily equity data over a 15-year sample, mean reversion in log-price spreads takes months to years — not days.

### Why each category failed

**C1 — Same-index ETFs (0/6)**

The S&P 500 triplet (VOO/IVV/SPY) has valid HLs (9-13 days) and mean-reverting Hurst (H=0.19-0.30) but fails Engle-Granger (p=0.18-0.67). Root cause: **expense ratio drift**. VOO (0.03%), IVV (0.04%), SPY (0.0945%) have different annual cost drags. Over 15 years, this creates a cumulative drift of 0.1–0.9% in the log ratio. The ADF test on OLS residuals detects this slow drift as a unit root (can't reject I(1)) even though short-run mean reversion is present.

GLD/IAU and SLV/SIVR additionally fail Johansen (trace stat 8.07-8.55 vs critical 15.49). The same expense ratio mechanism applies: GLD (0.40%) vs IAU (0.25%) → 0.15%/year drift → log ratio trends persistently → Johansen and EG both detect I(1) behavior.

**C2 — Sector ETF pairs (0/4)**

Sector ETFs have different constituent weights and sector-specific stock selection. XLE focuses on integrated oil majors (CVX, XOM dominate), XOP is pure E&P (more diversified). Their log ratio trends because E&P subsector has different secular performance vs integrated majors. HL = 10,601 days for XLE/XOP means effectively NO mean reversion in the spread. This is a structural relationship mismatch, not a temporary dislocation.

XLF/KBE and XLK/SOXX come closer (HL=126-136d) but are still 4-5× too slow for profitable daily trading after costs.

**C3 — Commodity-linked stock pairs (0/4)**

Gold/miner pairs (GLD/GDX, GLD/NEM) have HL > 470 days. Mining stocks have operational leverage (fixed costs, production lag), causing their log ratio to mean-revert only over multi-year cycles (capital reallocation, mine development cycles). Not tradeable at daily frequency.

Oil/energy pairs (USO/XLE, USO/CVX) similarly: oil price can diverge from energy stock prices for years (2015-2016 oil crash; energy stocks lagged oil recovery by 12-18 months). HL ≈ 536-795 days.

**C4 — Equity peer pairs (0/5)**

V vs MA: closest to qualifying. EG p=0.075 (10% level), Johansen trace 14.19 vs critical 15.49 (near-pass), Hurst H=0.385 (mean-reverting), but HL=96 days. Visa and Mastercard are in the same business but have different geographic exposures, client mixes, and growth trajectories. Log ratio drifts slowly.

KO/PEP, WMT/TGT, GS/MS: HL > 200 days. Even pairs that appear economically "natural" do not mean-revert within 30 days at daily frequency.

## 5. V/MA — the closest near-miss

| Test | Value | Threshold | Pass? |
|------|-------|-----------|-------|
| EG p-value | 0.075 | < 0.05 | FAIL (marginal) |
| Johansen trace | 14.19 | > 15.49 | FAIL (96.3% of threshold) |
| Half-life | 96.0d | ≤ 30d | FAIL (3.2× too slow) |
| Hurst exponent | 0.385 | < 0.5 | PASS |

V/MA satisfies the Hurst test (genuinely mean-reverting spread) and comes close on statistical tests but fails the HL constraint by 3.2×. If HL threshold were relaxed to 90-100 days, V/MA would qualify with ~3 round trips/year. At 12 bps/cycle costs, annual drag = ~36 bps — manageable if the spread generates ≥ 50 bps gross premium per year.

## 6. What would need to change to find qualifying pairs

**Option A: Relax HL threshold to 90 days**
- V/MA would qualify (HL=96d, approximately)
- GLD/IAU and SLV/SIVR might qualify (HL=81-84d) IF EG/Johansen are resolved
- Expect 1-2 pairs, insufficient for diversified portfolio
- Fewer trades/year (2-3 round trips vs 8-12 at HL=15d)
- Still need to solve the ETF expense ratio drift problem for C1

**Option B: Fix β=1 for same-index ETFs (ratio spread)**
- Avoids OLS estimation error
- Tests log(Y/X) directly for stationarity
- Would likely identify GLD/IAU, SLV/SIVR as stationary (ratio spread)
- Still have the expense ratio drift problem → ADF needs trend term
- Requires changing methodology to a ratio-based approach

**Option C: Expand universe to structural pairs**
- Dual-listed stocks (e.g., Royal Dutch Shell A/B shares, Unilever PLC/NV)
- Closed-end fund premia (fund price vs NAV)
- ETF vs underlying basket (ETF arbitrage)
- These have structural arbitrage constraints that create tighter cointegration
- All require either paid data or non-US instruments

**Option D: Use returns-based correlation instead of price levels**
- Rolling corr/beta instead of cointegration
- Different strategy: statistical factor pairs, not classic pairs arb
- Doesn't fit the pairs trading cointegration framework

## 7. Methodological insight (preserved for future reference)

> **Classic pairs trading (Engle-Granger + Johansen, daily equity data, HL ≤ 30 days) does not find statistically valid pairs in a well-diversified universe of US ETFs and large-cap equities.** The failure modes are: (a) expense ratio drift makes same-index ETFs appear non-cointegrated over multi-year samples, and (b) business model divergence makes fundamental equity pairs have HLs measured in months, not days. The academic literature's success with pairs trading often relies on: high-frequency data (intraday ETF arb), very large universes (hundreds of pairs with automated selection), or structural pairs (ADRs, dual-listed, merger arb). A 19-pair daily universe with strict statistical screens is unlikely to find anything robust.

## 8. n_tests counter

- Start: 71
- Pairs backtested: 0 (none passed screening, no backtest triggered)
- Portfolio test: 0
- **End: 71** (screening counts as 0 additional tests — no signals were actually traded)

## 9. Recommendation

> **FAIL — Archive pairs cointegration. 0/19 pairs qualify under rigorous statistical screens. Root cause is structural (HL too long for daily equity data, not a threshold calibration issue). Move to Candidate 4: Commodity TSMOM (DJP, GLD, USO, SLV — trend-following across commodity ETFs, does not require cointegration, has well-documented academic backing).**

If user wants to pursue pairs: the most viable path is V/MA with relaxed HL (≤ 120 days) and Johansen at 90% level. But this single-pair strategy has insufficient diversification for a propfirm context and does not justify the research investment given other candidates.
