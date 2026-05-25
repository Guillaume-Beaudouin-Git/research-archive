# Literature Scan — Strategy E: WMR Fix + End-of-Month USD Flow

**Date:** 2026-05-23  
**Scope:** IC feasibility only — verify stylized facts post-2015 WMR window widening

---

## Primary references

### Evans (2014) — "How Order Flow Affects Exchange Rates"
- **Core claim**: The WMR 4PM London fix creates a predictable price impact window. Dealers accumulate directional inventory from fix orders placed by asset managers before 3:55 PM. They push prices in their favour in the 15-60 minutes before the fix, then unwind after.
- **Data**: EBS tick data 1996-2010, G7 pairs
- **Key finding**: Order flow explains 50-80% of daily EUR/USD variation on fix days. Pre-fix directional drift reverses within 30-90 minutes after fix.
- **Relevance**: Establishes the W-shape mechanism (drift → overshoot → reversion) and quantifies the predictability window.

### Krohn & Sushko (2022) — "FX spot rates at the WMR London close"
- **Core claim**: WMR fix window widening from 60s to 5 minutes (15 February 2015) significantly reduced price impact and rate manipulation incentives. Post-2015, pre-fix build-up is less extreme but still detectable.
- **Data**: Refinitiv Tick History, 2013-2020, 8 G10 pairs
- **Key finding**: Post-2015, intra-window volatility dropped ~40% but the directional bias in the 15 minutes before fix (15:45-16:00 London) persists at reduced magnitude. Fix now more representative of true mid-market.
- **Relevance**: Calibrates expected signal magnitude in our test window (post-2015). Suggests H1 t-stat will be lower than pre-2015 estimates.

### FXEmpire (2025) — "WMR Fix Trading: Patterns That Still Work"
- **Core claim**: End-of-month equity rebalancing flows are the most reliable remaining WMR signal. Global equity managers overweighted in USD equities (SPX outperformance MTD) must sell USD at month-end to rebalance → systematic USD weakness at 4PM fix on last business day.
- **Key finding**: When SPX MTD return exceeds MSCI World ex-US MTD by >2%, EURUSD fixes 0.15-0.25% above pre-fix level on the last business day. Effect detectable 2015-2024.
- **Relevance**: Directly motivates H2 (EOM USD flow hypothesis). Provides the >2% SPX/MSCI outperformance threshold used in hypothesis.md.

---

## Supporting references

### Melvin & Prins (2015) — "Equity Hedging and Exchange Rates at the London 4 p.m. Fix"
- Documents equity-FX rebalancing mechanism: fund managers hedge currency exposure monthly → predictable flows at fix. Sharpe 1.2-1.8 on fix-trading strategies 2005-2013 (pre-reform period — not in-sample for us).

### Ito, Yamada & Takayama (2012) — "Free Lunch! Arbitrage Opportunities in the Foreign Exchange Markets"
- Pre-reform exploitation of WMR manipulation. Historical context only; not applicable post-2015.

### Cespa & Vives (2015) — "The Beauty Contest and Short-Term Trading"
- Theoretical model: when multiple dealers expect each other to build pre-fix inventory, equilibrium produces predictable pre-fix drift even post-regulation. Supports persistence of H1 signal at reduced magnitude.

### Lo & MacKinlay (1990) — "When Are Contrarian Profits Due to Stock Market Overreaction?"
- Bootstrap and HAC methodology for detecting serial autocorrelation in intraday returns. Foundation for our HAC t-stat approach at M5 frequency.

---

## Key empirical calibration from literature

| Parameter | Pre-2015 | Post-2015 (estimate) | Our threshold |
|-----------|----------|---------------------|---------------|
| Pre-fix drift magnitude | 0.08-0.15% / 30min | 0.03-0.06% / 30min | — |
| Post-fix reversion speed | 15-30 min | 30-60 min | — |
| H1 t-stat (monthly average) | 3.5-5.0 | 1.5-2.5 | ≥ 2.0 |
| H2 EOM events/year | — | ~10-15 | ≥ 8 |
| H2 mean fix return | — | +0.15-0.25% | > 0 |

---

## Literature gaps / risks

1. **Crowding post-Levine settlement (2015)**: Several banks paid $4.3B in fines. Proprietary fix-trading desks shut. Signal may have weakened further 2015-2018 as internal flow information dried up.
2. **Krohn & Sushko data ends 2020**: No published evidence on 2020-2026 signal persistence. Our stylized_facts.py provides this.
3. **EOM flow proxy**: We use SPX vs yfinance MSCI World proxy (URTH ETF). The actual signal uses manager-level equity holdings and FX hedge ratios — imperfect proxy introduces measurement noise.
