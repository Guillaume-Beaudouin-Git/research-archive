# POSTMORTEM — Strategy D: Modified FX Carry G10

**Archived:** 2026-05-23  
**Verdict:** IC FAIL → ARCHIVE (no full backtest run)  
**n_tests consumed:** 173 (raw carry IC), 174 (REER-modified carry IC)

---

## Result summary

| Signal | IC mean | t_HAC (lag-6) | Gate |
|--------|---------|---------------|------|
| Raw carry | +0.022 | 0.81 | IC ≥ 0.02 (PASS stop gate) — t insufficient |
| REER-modified carry | −0.010 | −0.26 | FAIL — REER destroys signal |

Soft gate requires t_HAC > 1.65. Hard gate requires IC > 0.04 + t_HAC > 2.5. Neither reached.

---

## Root cause: structural break, not noise

Raw carry IC per 3-year period:

| Period | IC | t_HAC | Notes |
|--------|----|-------|-------|
| 2005-2007 | +0.119 | 1.69 | Pre-GFC carry boom |
| 2008-2010 | −0.022 | — | GFC unwind |
| 2011-2013 | −0.038 | — | Post-GFC zero-rate regime |
| 2013-2015 | −0.019 | — | REER sample start |
| 2015-2018 | +0.011 | — | Near zero |
| 2018-2021 | −0.004 | — | Near zero |
| 2021-2023 | −0.008 | — | Near zero |
| 2023-2026 | +0.012 | — | Noise |

**The full-period IC of +0.022 is entirely an artifact of 2005-2007.** The carry trade — documented by Lustig et al. (2011), Brunnermeier et al. (2009) — has had zero or negative predictive power at monthly frequency since approximately 2011 in G10 markets.

The structural break coincides with:
1. Post-GFC central bank coordination (ECB/BOJ/SNB zero/negative rates → compressed differentials)
2. Risk-off regimes (2010 EU crisis, 2015 EM selloff, 2020 COVID) systematically unwinding carry positions
3. FX carry now widely arbitraged by institutional players who hedge the volatility crash risk

---

## Why REER modification failed

The REER modifier was expected to filter overvalued high-yield positions (à la Macrosynergy/JPM Quantamental).

Three failure modes:

1. **Wrong REER concept**: BIS trade-weighted REER measures competitiveness vs all trading partners. Bilateral USD carry positions are driven by USD strength, not trade balance. JPY REER z-score = −2.44 ("undervalued" = buy JPY carry) but JPY long is the most crash-prone in risk-off events.

2. **Non-stationarity**: JPY REER has trended weaker since 2010 due to BOJ monetary policy divergence. Rolling z-score of a trending series generates persistent false "undervalued" signals that are not mean-reverting.

3. **Starting from broken signal**: The REER window (2013-2023) coincides with the dead zone of carry. Raw carry IC in that period = −0.028. No modifier can rescue a signal with IC ≈ 0.

---

## Why Macrosynergy publishes Sharpe 0.70+

Their framework uses:
- **EM exotic pairs** (BRL, ZAR, TRY) with much larger carry differentials and structural risk premia
- **Proprietary point-in-time data vintages** for CA/GDP, CPI — not available via FRED (no real-time vintage)
- **Composite of 20-30 currencies** vs G10-only (N=9 insufficient for CS diversification)
- **Post-publication period (2005-2010)** may be in-sample for their methodology development

Reproducing their result with G10 + BIS REER + FRED rates is structurally infeasible.

---

## Infrastructure preserved (reusable for Strategy E+)

| Module | Location | Reuse value |
|--------|----------|-------------|
| `fred_loader.py` | `Forex/data/` | G10 rates, CPI — reusable for any FX strategy |
| `bis_reer_loader.py` | `Forex/data/` | BIS REER with pub lag — reusable for valuation filters |
| `cot_loader.py` | `Forex/data/` | COT net spec positions — stub for Phase 2 |
| `dukascopy_loader.py` | `Forex/data/` | yfinance monthly + M5 download skeleton |
| `metrics.py` | `Forex/backtest/` | HAC IC t-stat, sharpe_hac, perf_summary |
| `amtp.py` | `Forex/backtest/` | Bonferroni/BH thresholds |
| `costs.py` | `Forex/backtest/` | Spread + swap cost model |
| `vol_targeting.py` | `Forex/backtest/` | Vol-targeting weights |
| `walk_forward.py` | `Forex/backtest/` | Expanding-window WF splits |

---

## Lessons learned

- **Lesson 11**: Always check per-decade IC breakdown before calling FX carry feasible. 2005-2007 pre-GFC boom contaminates any carry backtest starting 2005.
- **Lesson 12**: BIS trade-weighted REER is unsuitable as modifier for bilateral USD carry positions. Use bilateral valuation proxies (PPP deviation, FEER) instead.
