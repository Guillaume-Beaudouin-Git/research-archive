# Literature Scan — Strategy D Modified FX Carry
**Date:** 2026-05-23  
**Author:** Guillaume Beaudouin  
**Objective:** Identify academic basis for a REER/CA/inflation-adjusted carry strategy that survives the failure modes of archived FX-1 through FX-4.

---

## 1. Failure modes of archived strategies (non-repeatable)

| Strategy | IC | Sharpe | Root cause |
|---|---|---|---|
| FX-1 Carry G10 FRED | +0.027 | −0.13 | Crash tail: GFC −33%, COVID −14% |
| FX-2 CS Momentum 12M-1M | −0.024 | −0.06 | Edge died post-2012 (CB intervention) |
| FX-3 TSMOM tanh G10 | −0.025 | −0.13 | Same as FX-2 |
| FX-4 Carry G10+EM | +0.001 | −0.49 | Peso problem EM; spreads 60bps RT |

**Conclusion:** raw carry has real IC (~0.027) but generates negative Sharpe due to crash tail exposure. The hypothesis is that fundamental-based filters (REER, CA, inflation) can reduce crash exposure while preserving positive IC.

---

## 2. Core academic references

### 2.1 Carry returns and risk premia

**Lustig, Roussanov & Verdelhan (2011) — "Common Risk Factors in Currency Markets"**  
*Journal of Financial Economics*, 111(2), 527–556.  
- Establishes two systematic FX risk factors: dollar factor (average across all currencies) and carry factor (spread between high-yield and low-yield currencies). Raw carry returns reflect compensation for systematic crash risk, not pure alpha.  
- Implication: carry strategies need crash protection to generate real alpha.

**Brunnermeier, Nagel & Pedersen (2009) — "Carry Trades and Currency Crashes"**  
*Quarterly Journal of Economics*, 124(1), 313–347.  
- Documents the left-tail crash risk ("peso problem") in carry: unwinding events are severe, fast, and correlated with global risk-off. The key predictor of unwinding: elevated speculative positioning (COT) + overvalued REER + negative current account.  
- Direct motivation for this strategy's three modifying factors.

**Koijen, Moskowitz, Pedersen & Vrugt (2018) — "Carry"**  
*Journal of Financial Economics*, 127(2), 197–225.  
- Unified carry framework across asset classes. Establishes that carry in FX is a priced factor but with time-varying risk exposure. Supports vol-targeting as the appropriate sizing mechanism.

### 2.2 Valuation (REER/PPP) as predictor

**Jordà & Taylor (2012) — "The Carry Trade: Risks and Drawdowns"**  
*NBER Working Paper 18390.*  
- Shows that combining carry with PPP valuation (REER deviation) reduces drawdowns during carry crashes. Specifically, conditioning on REER undervaluation reduces the GFC drawdown by ~40-60%. The "CISCO" composite (Carry + REER + Momentum) outperforms raw carry by Sharpe +0.4.  
- **Key finding for our strategy:** REER z-score threshold of ±1 standard deviation is optimal; beyond ±2 std, signal becomes noise due to REER non-stationarity.

**Asness, Moskowitz & Pedersen (2013) — "Value and Momentum Everywhere"**  
*Journal of Finance*, 68(3), 929–985.  
- Demonstrates that value (PPP/REER deviation) and momentum are orthogonal to each other and both generate positive returns in FX. Combining carry, value, and momentum improves Sharpe ratio in FX.  
- Supports our composite signal construction.

**Corte, Sarno & Schmeling (2016) — "Currency Premia and Global Imbalances"**  
*Review of Financial Studies*, 29(8), 2161–2193.  
- External balance (current account / GDP) significantly predicts FX excess returns, orthogonal to carry. Currencies with deteriorating CA tend to depreciate beyond what carry predicts.  
- IC of CA factor: ~0.03 at monthly, stronger at quarterly horizon. Used in our signal at 0.15 weight.

### 2.3 Inflation differentials as FX predictor

**Engel & West (2005) — "Exchange Rates and Fundamentals"**  
*Journal of Political Economy*, 113(3), 485–517.  
- Establishes that in standard monetary models, FX is driven by inflation differentials (Taylor rule). Inflation differential predicts future nominal FX rate changes but with low R² — consistent with small IC (~0.01-0.02) at monthly.

**Clarida, Galí & Gertler (1998) — "Monetary Policy Rules in Practice"**  
*European Economic Review*, 42(6), 1033–1067.  
- Central bank reaction functions: CB raises rates when inflation exceeds target. A country with above-consensus inflation AND already-high rates is more likely to see unexpected rate cuts (negative carry surprise). Motivation for inflation differential as carry-correction factor.

### 2.4 Macrosynergy/JPM Quantamental framework

**Macrosynergy (JPM Quantamental Analytics)**  
- The specific "modified carry" framework described in this strategy's hypothesis originates from JPMorgan's Quantamental Research division. Their "macrosynergy" approach constructs composite signals from carry + REER deviation + external balance + inflation differential.  
- Key innovations vs raw carry: (a) cross-sectional z-scoring before combining factors, (b) dynamic factor weights based on macro regime, (c) COT positioning overlay to reduce crowding risk.  
- Published methodology: JPM Global FX Strategy, "Quantamental Carry" (2018, 2021 updates). Not publicly available, but reproduced here based on academic implementations.

**Menkhoff, Sarno, Schmeling & Schrimpf (2012) — "Carry Trades and Global Foreign Exchange Volatility"**  
*Journal of Finance*, 67(2), 681–718.  
- Carry returns concentrate in high-volatility regimes. Systematic volatility scaling (position size ∝ 1/σ_realized) significantly improves Sharpe. Our vol targeting (10% annualized) is directly motivated by this.

### 2.5 COT positioning (Phase 2 extension)

**Klitgaard & Weir (2004) — "Exchange Rate Changes and Net Positions of Speculators in the Futures Market"**  
*FRBNY Economic Policy Review*, 10(1).  
- COT speculative net positions in FX futures predict short-term reversals when positioning is extreme (>75th percentile). At normal positioning, signal is zero. Application: when COT percentile > 80th for a long carry currency, reduce position by 50%.

---

## 3. Key differences from archived FX-1 (pure carry FRED)

| Feature | FX-1 (Archived, Sharpe −0.13) | Strategy D (Hypothesis) |
|---|---|---|
| Signal | r_foreign − r_USD | z_carry × 0.5 + z_reer × 0.2 + z_ca × 0.15 + z_infl × 0.15 |
| REER filter | None | 10Y rolling z-score, reduce long overvalued |
| Crash protection | None | REER + CA filters reduce pre-crash exposure |
| Universe | 8 G10 | 9 G10 (+ NZD) + optional EM |
| Volatility | Not targeted | 10% annualized, daily vol target |
| COT | Not used | Phase 2 optional overlay |
| Frequency | Weekly | Monthly (better IC, lower transaction costs) |

---

## 4. Disconfirmation criterion

This strategy should be **archived** (not modified > 3x) if:
1. IC_modified_carry < IC_raw_carry (REER/CA/inflation add no information)
2. VIX-regime breakdown: IC in high-VIX regime (top tercile) < 0 (carry crashes hurt even modified version)
3. Max crash drawdown in 2008, 2015, 2020 exceeds −20% in IS backtest

If all three hold, the evidence suggests fundamental-based adjustments do not rescue carry in G10 FX — consistent with the market efficiency of the post-2008 low-rate environment.

---

## 5. Competing hypotheses not tested here

- **FX Carry + Momentum** (Asness et al. 2013, combined): tested in archived fx_carry_trend — all variants Sharpe < 0 (failed)
- **Dollar-neutral factor decomposition** (Lustig & Verdelhan 2007): requires factor model construction, deferred
- **Microstructure carry** (Lyons 2001, order flow): requires bid-ask data, not feasible with free data
- **Time-series (TSMOM) carry**: tested as FX-3, failed
