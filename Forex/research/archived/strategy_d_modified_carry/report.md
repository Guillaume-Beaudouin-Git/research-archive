# Strategy D Modified Carry — Phase 1 Report
**Date:** 2026-05-23  
**Verdict: FAIL — archive**  
**n_tests consumed:** 173 (raw carry IC), 174 (REER-modified carry IC)  
**n_tests after:** 174

---

## 1. Results summary

| Test | IC_mean | t_HAC | N | Gate |
|---|---|---|---|---|
| Raw carry (n=173) | **+0.0221** | 0.81 | 255 | PASS stop gate (≥0.02), FAIL significance |
| Modified carry REER (n=174) | **−0.0097** | −0.26 | 131 | FAIL — REER destroys signal |

**Key diagnostic — raw carry IC on same 2013–2023 period:**  
IC = **−0.028**, t = **−0.86**  
The overall IC of +0.022 is driven entirely by the 2005–2007 pre-GFC period.

---

## 2. Structural break: FX G10 carry is a pre-GFC artifact

| Period | IC_mean | t_HAC | n | Interpretation |
|---|---|---|---|---|
| 2005–2007 | **+0.119** | 1.69 | 35 | Pre-GFC boom — carry worked |
| 2008–2010 | +0.007 | 0.07 | 36 | GFC crash — carry dead |
| 2011–2013 | −0.002 | −0.03 | 36 | Post-GFC compression — carry dead |
| 2014–2016 | +0.011 | 0.16 | 36 | Near-zero rates everywhere — carry dead |
| 2017–2019 | −0.015 | −0.34 | 36 | Continued compression — slightly negative |
| 2020–2022 | −0.037 | −0.47 | 36 | COVID + zero rates — negative |
| **2023–2025** | **+0.026** | 0.52 | 36 | Rate-hike cycle — slight recovery |

**Root cause:** Post-2008, global central bank rate compression eliminated G10 carry differentials.
BOJ Yield Curve Control (2016–2024) locked JPY near zero, creating systematic carry unwinds in risk-off
events. The 2005–2007 IC (+0.119) is not replicable; it represents a structural regime that ended with the GFC.

---

## 3. REER modification failure

The BIS broad trade-weighted REER (2020=100) reduced IC from +0.022 to −0.010.  
Two reasons:

1. **Wrong metric**: Trade-weighted REER measures a basket of partners. For bilateral USD carry
   positions, what matters is the bilateral USD rate — not the trade-weighted average. A currency
   can be overvalued in trade-weighted terms while fairly or undervalued vs USD specifically.

2. **Structural REER trends**: JPY REER z-score = −2.44 std (deeply undervalued) in 2023, which should
   signal "increase carry weight on JPY longs" (carry = short JPY). But JPY carry shorts are the
   most crash-prone positions precisely when JPY is "undervalued" — the REER factor is
   counterproductive in risk-off environments.

---

## 4. VIX regime breakdown

| VIX regime | IC (modified carry) | t_HAC | n | Signal |
|---|---|---|---|---|
| Low (< 33rd pct.) | +0.043 | 0.75 | 43 | Carry works in calm markets |
| Mid (33rd–66th pct.) | +0.023 | 0.42 | 43 | Mild carry edge |
| **High (> 66th pct.)** | **−0.092** | −0.98 | 45 | **Carry crashes — REER doesn't protect** |

The REER filter fails its primary objective (crash protection). High-VIX IC remains deeply negative.

---

## 5. AMTP assessment

- n_tests = 174 after this test
- Bonferroni t-threshold: 3.45 (requires Sharpe > 0.75 over 21Y)
- BH FDR t-threshold: ~3.0 (requires Sharpe > 0.65)
- Observed t_raw = 0.81 → **fails all thresholds**
- Even if we ignore AMTP, the raw t = 0.81 is not significant at the naive 1.65 level
- Conclusion: No significance at any correction level

---

## 6. Connection to archived strategies

| Test | IC | Sharpe | Failure mode | Consistent? |
|---|---|---|---|---|
| FX-1 Carry G10 FRED (n≈83) | +0.027 | −0.13 | Crash tail, pre-GFC contamination | ✓ Same |
| FX-4 Carry G10+EM (n≈86) | +0.001 | −0.49 | Peso problem | ✓ Same |
| **Strategy D Phase 1** | +0.022 | n/a | Pre-GFC contamination + dead post-2011 | ✓ Consistent |

The FX-1 test at weekly frequency showed IC = 0.027, t = 2.02. At monthly frequency with 9 currencies,
this is IC = 0.022, t = 0.81. Both are consistent: the carry signal is marginal, and any apparent
significance in FX-1 was due to higher frequency (more observations) amplifying a structurally weak signal.

---

## 7. VERDICT: ARCHIVE STRATEGY D

**Strategy D is archived.** Root cause: FX G10 carry is a pre-GFC edge that has not recovered
post-2011. The REER modification (Macrosynergy approach) provides no improvement because:
1. The underlying carry signal has IC ≈ 0 in the post-2011 period
2. BIS trade-weighted REER is misaligned with bilateral USD carry positions
3. The VIX crash regime shows REER does not protect against carry unwinds

Proceed to archiving with proper documentation.

---

## 8. Three pivot proposals (if pursuing FX personal book)

### Pivot 1 — FX Short-Term Trend + Risk Premium (n=175, 176)
**Hypothesis:** Cross-sectional 1M FX momentum (short-term continuation) applied to G10, not
the archived 12M momentum. Motivation: at 1-month horizon, FX often exhibits short-term trend
continuation (institutional order flow momentum), distinct from the longer-term reversal.
- n_tests: +1 for 1M IC test, +1 for combined 1M+3M; total n=175, 176
- Data: same yfinance monthly data, no new infrastructure
- *Different from archived FX-2 (12M), not yet tested*

### Pivot 2 — COT-Gated Carry (n=175)
**Hypothesis:** Use CFTC COT speculative positioning as a regime filter on raw carry. When
COT net spec positioning in a currency is above 80th percentile (crowded long), exclude
from carry portfolio. When below 80th percentile, apply normal carry sizing.
- IC evidence: Klitgaard & Weir (2004) — crowding predicts near-term reversals
- Directly addresses the crash mechanism (crowded positions → forced unwinds)
- *Modification #1 of Strategy D (within 3-modification budget)*
- Implementation: `cot_loader.py` already built; needs COT data fetch + carry filter
- Requires 2015+ data for COT percentile (3Y rolling window)
- n_tests: +1 (n=175)

### Pivot 3 — Abandon FX, redirect to equity/options VRP
**Hypothesis:** Equity VRP (SPX short 1M puts + 3M put spread) — documented edge with
Sharpe 0.8–1.2 in academic literature (Bondarenko 2014, Santa-Clara & Saretto 2009).
- FX carry is structurally dead in the current macro regime (2011–2026)
- Equity VRP has a different (and more robust) theoretical basis than FX carry
- Equity VRP risk: left-tail (2008 −100%, 2020 −60%); requires crash protection
- Architecture: completely new strategy, not a modification of Strategy D
- Not viable for propfirm (SPX options not a propfirm instrument); only for personal book
- n_tests: new series starting at n=175

---

## 9. Lessons for methodology

**Lesson 14** (new): FX carry IC is regime-dependent and dominated by the pre-GFC 2005-2007
period. Any FX carry backtest starting 2005 will show marginal IC driven by that era.
When a carry test shows overall IC ≈ 0.02–0.03, check the per-decade breakdown before
declaring a PASS — it may be masking a structural break.

**Lesson 15** (new): BIS broad trade-weighted REER is not a good predictor for bilateral
USD carry positions. REER "undervalued" signals (e.g., JPY in 2015-2023) can coincide
with extreme crash risk in the carry direction.
