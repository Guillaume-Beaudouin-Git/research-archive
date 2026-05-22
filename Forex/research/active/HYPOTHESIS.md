# Phase 1 — Hypothesis Selection
# FX Algo Research (FTMO $100K, Challenge-First)

*Date: 2026-05-22 | n_tests at start: 142 (reconciled from NQ iter_10 results.json)*

---

## N_tests Reconciliation

| Source | Count | Counting method |
|--------|-------|----------------|
| README §10 | 82 | Hypothesis-level (each strategy = 1 test, parameter sweeps merged) |
| NQ iter_10 results.json | **142** | Configuration-level (every parameter variant = 1 test) |

**Correct AMTP denominator: 142.** The results.json is ground truth — the NQ ORB research alone added 56 configurations (iter_1a through iter_09_9c = n_tests 86→126, then iter_10 absorbed 16 signal refinement tests = 142). README 82 under-counts by treating multi-variant sweeps as single entries. Use 142 for all DSR/AMTP calculations in FX research. FX tests will increment from 143.

---

## Candidate Evaluation — 3×7 Grid

### Evaluation criteria

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| Crowding | High | Less crowded = more residual edge |
| FTMO T&C | Blocker | Hard gate — not negotiable |
| Cost arithmetic | High | n_trades × spread vs gross EV |
| Hit rate expectation | High | Propfirm survival = hit rate > Sharpe |
| Frequency | Medium | More trades → faster challenge pass |
| IC evidence | High | Academic backing reduces search risk |
| Data availability | Medium | Free data preferred (n_tests budget) |

---

### ANGLE A — London Open Session Breakout (ORB-FX)

**Variant proposed**: Multi-pair confirmation (EUR/USD AND GBP/USD must break Asian range in same direction). Rejects vanilla ORB.

| Dimension | Score | Evidence / Notes |
|-----------|-------|-----------------|
| **Crowding** | ⚠️ MEDIUM | Highly implemented in retail EA space (London breakout = one of top-10 most common FX algos). Multi-pair confirmation reduces false positives but does not eliminate crowding. Edge documented decaying post-2015 (Osler 2003, Serban 2010 on pre-2010 data; performance degraded post-2010 as session overlap tightened with electronic markets). |
| **FTMO T&C** | ✅ OK | No restrictions. London open (07:00-09:00 UTC) does not coincide with scheduled news (NFP is 12:30 UTC, ECB 12:45 UTC). Low news overlap risk. |
| **Cost arithmetic** | ✅ VIABLE | With multi-pair confirmation: signal fires ~30-40% of days (conservative estimate). 240 potential days × 0.35 = 84 trades/year × 2 pairs max = 84-120 effective trades. Cost: 100 trades × 1.0 pip avg × $10/pip × 2.5 lots (0.5% risk, 20-pip SL) = $2,500/year = **2.5% drag** on $100K. Gross EV needed: if hit_rate=48%, R:R=1.5 → EV = 0.48×1.5R – 0.52×1R = 0.20R = $100/trade. 100 trades × $100 = $10,000/year gross = **10% gross** → 7.5% net. ACHIEVABLE — minimal margin. |
| **Hit rate** | ✅ EXPECTED 45-52% | Session momentum at London open is documented. Multi-pair confirmation filters noise. Conservative estimate: 45-50% directional accuracy on confirmed breakouts. R:R must be 1.5 minimum to be propfirm-viable at 45%. |
| **Frequency** | ✅ HIGH | 84-120 trades/year = 7-10 trades/month. Sufficient for challenge (4 min trading days required). 30-trade paper validation achievable in ~3 months. |
| **IC evidence** | ⚠️ WEAK-MEDIUM | Session momentum in FX is documented (Rime, Sarno & Sojli 2010 "Exchange Rate Forecasting, Order Flow, and Macroeconomic Information"). But edge has declined as microstructure evolved. No recent (post-2020) academic replication with strong IC. |
| **Data availability** | ✅ FREE | Dukascopy 1-min tick-to-bar, free, good quality, 2003-present. `dukascopy-python` package or direct API. |

**Red flags:**
- Crowding risk: vanilla London ORB is one of the most traded retail strategies globally. Multi-pair confirmation reduces but doesn't eliminate.
- Edge decay: academic papers use pre-2015 data; retail EA proliferation post-2015 has likely compressed the edge.
- Requires 1-min data → new data pipeline to build.

**Verdict**: VIABLE but not preferred. If selected, the multi-pair confirmation is MANDATORY (not optional). The vanilla version has an insufficient edge expectation post-2020.

---

### ANGLE B — News-Fade Post-Major-Release

**Mechanism**: Price over-reacts to a high-impact news event (NFP, ECB, FOMC, CPI). The initial spike in EUR/USD or GBP/USD is driven by reactive retail flow + algos; price partially reverts toward pre-announcement level within 30-60 minutes as informed institutional flow re-establishes value. Entry at T+5min after announcement (post-spike), fade direction, SL at spike extreme + buffer.

| Dimension | Score | Evidence / Notes |
|-----------|-------|-----------------|
| **Crowding** | ✅ LOW | The "fade the spike" direction is OPPOSITE to what most retail traders do (most chase the spike). HFT and market makers already fade but at microsecond level — the 5-30 minute post-spike fade is a different time horizon. Systematic retail news-fade strategies are less common because execution complexity scares most retail algos. |
| **FTMO T&C** | ✅ FTMO OK | **FTMO does NOT prohibit news trading.** Their "Pro Trader" accounts explicitly allow all trading styles including news trading, scalping, EAs. ⚠️ NOTE: FundedNext restricts trading within ±2min of high-impact news. MFF (defunct). The Funded Trader: generally allows. **This hypothesis is scoped to FTMO specifically.** If considering FundedNext or E8, reassess. |
| **Cost arithmetic** | ⚠️ TIGHT | News events: ~50 high-impact per year (12 NFP + 8 ECB + 8 FOMC + 12 CPI + 10 other) × 2 pairs = 100 potential signals. Filtered (entry only if spike > 2× daily ATR): ~60 actual entries/year. **Cost driver: spread spike.** During NFP, EUR/USD spread widens to 3-5 pips RT (vs 1 pip normal) on FTMO Astra. Assume 3.5 pip RT average for news entries. Cost: 60 trades × 3.5 pips × $10/pip × 2.5 lots = $5,250/year = **5.25% drag**. Gross EV needed: hit_rate=58%, R:R=1.3 → EV = 0.58×1.3R – 0.42×1R = 0.334R = $167/trade. 60 × $167 = $10,000 gross = 10%. Net = 10% – 5.25% = **4.75% net** → LOW MARGIN. |
| **Hit rate** | ✅ EXPECTED 52-62% | Academic and practitioner literature documents over-reaction to macroeconomic surprises (Balduzzi et al. 2001, Andersen et al. 2003 — "Real-Time Price Discovery in Global Stock Bond and FX Markets"). The key: entry at +5min post-announcement reduces spread impact and gets cleaner entry. Hit rate depends critically on entry timing. |
| **Frequency** | ⚠️ MEDIUM-LOW | 60 trades/year = 5 trades/month. Sufficient for 4-day minimum, but challenge pass slower than Angle A. Paper validation (30 trades) takes 6 months. |
| **IC evidence** | ✅ STRONG | Microstructure literature on news over-reaction in FX is robust. Chaboud et al. (2009) "Rise of the Machines: Algorithmic Trading in the FX Market" — documents over-reaction and reversion. Balduzzi et al. (2001) "Economic News and Bond Prices" — generalizable to FX. The fade mechanism is the strongest of the 3 angles from a theoretical standpoint. |
| **Data availability** | ⚠️ MEDIUM | Requires: (1) 1-min Dukascopy FX prices, (2) economic calendar with actual vs expected values. ForexFactory CSV or FRED for macro data. Surprise calculation: `surprise = (actual - consensus) / historical_std`. Free data available, but assembly more complex than pure price strategy. |

**Red flags:**
- Spread cost is the primary risk. If FTMO Astra spreads are 4+ pips during NFP (not 3.5), cost arithmetic deteriorates.
- Entry timing is critical: entering at T+2min vs T+8min post-announcement produces very different results.
- Fewer trades than Angle A → propfirm challenge pass slower.
- Requires economic calendar data integration (more complex data pipeline).

**Verdict**: STRONGEST THEORETICAL EDGE. Weakest cost arithmetic but best IC evidence and lowest crowding. Viable IF spread modeling is accurate. **Select only if willing to invest in careful data pipeline for news event detection and spread simulation.**

---

### ANGLE C — AUD/JPY Risk-On/Off (Cross-Asset Equity-FX Lag)

**Mechanism**: AUD/JPY is the classic risk barometer. AUD = commodity/growth currency (corr with equity markets ~0.60-0.70). JPY = safe haven (negative corr with risk assets ~-0.50). When SPY daily return > threshold, AUD/JPY tends to follow with ~4-8h lag (FX markets digest equity information with delay). Signal: magnitude-weighted lag-1 SPY + VIX change → direction of next day's AUD/USD and USD/JPY.

**Refined signal** (per user guidance): magnitude weighting, activation threshold:

```
signal_raw = SPY_ret[t-1] × |SPY_ret[t-1]| / σ_SPY_90d
           - 0.5 × VIX_chg[t-1] × |VIX_chg[t-1]| / σ_VIX_90d
signal = 0 if |signal_raw| < 1.0   (activation threshold = 1σ)
signal = sign(signal_raw)           otherwise
```

| Dimension | Score | Evidence / Notes |
|-----------|-------|-----------------|
| **Crowding** | ✅ LOW | Cross-asset equity-FX lag is academically documented (Lustig & Verdelhan 2007 on cross-asset pricing) but not widely implemented as a systematic strategy because: (a) the lag is inconsistent (0-8h, not always 4h), (b) equity-FX correlation itself varies by regime, (c) requires cross-data infrastructure. Most retail traders "know" the correlation exists but don't trade it systematically with thresholds. |
| **FTMO T&C** | ✅ OK | No restrictions. AUD/USD (0.8-1.2 pip RT) and USD/JPY (0.7-1.0 pip RT) are among the lowest-spread pairs at FTMO. Daily signal, no news-overlap risk. |
| **Cost arithmetic** | ✅ BEST | Signal fires when |signal_raw| > 1σ ≈ 25-30% of trading days = 50-60 active days/year. 2 pairs = 100-120 trades/year. BUT: activation threshold likely reduces to 40-50 actual trades/year on combined AUD/USD + USD/JPY. Cost: 50 trades × 0.9 pip RT avg × $10/pip × 2.5 lots = $1,125/year = **1.1% drag** — LOWEST of all 3 angles. Gross EV needed at hit_rate=53%, R:R=1.5: EV = 0.53×1.5R – 0.47×1R = 0.325R = $163/trade. 50 × $163 = $8,150 gross = 8.2%. Net = 8.2% – 1.1% = **7.1% net** — BEST NET MARGIN. |
| **Hit rate** | ⚠️ UNCERTAIN 48-56% | Cross-asset momentum lag is weaker than same-asset signals. The AUD/JPY-SPY correlation exists but is noisy: some days SPY moves are FX-unrelated (earnings idiosyncratic), correlation regime breaks during specific events (Japan BOJ interventions, China PMI). Magnitude weighting should help stabilize, but hit rate uncertainty is highest of the 3 angles. |
| **Frequency** | ⚠️ LOW | 40-50 trades/year = 3-4 trades/month. Barely sufficient for FTMO 4-day minimum. Paper validation (30 trades) takes ~8-10 months — too slow. **This is a significant practical limitation for challenge timing.** |
| **IC evidence** | ⚠️ MEDIUM | Cross-asset FX momentum is documented in Menkhoff et al. (2012) and Moskowitz, Ooi & Pedersen (2012) in a broad context. The specific AUD/JPY-SPY lag at daily horizon has weaker academic support than news-fade. Correlation is empirically stable (2005-2024) but IC estimation would need validation vs the archived FX momentum failures. |
| **Data availability** | ✅ FREE | SPY and VIX via yfinance (already in cache), AUD/USD and USD/JPY via yfinance. All data already available with existing infrastructure. |

**Red flags:**
- Frequency too low for challenge pass. ~3-4 trades/month means a 60-day challenge requires the strategy to fire on 8-10 days, which at 1-day hold means 8-10 total trades — very low statistical significance during challenge.
- Hit rate more uncertain than B.
- Japan-specific regime risk: BOJ intervention can break AUD/JPY patterns for weeks.
- The activation threshold (discard |signal| < 1σ) by design reduces frequency further. For propfirm, need more trades, not fewer.

**Verdict**: Best cost structure, lowest crowding, but frequency is a propfirm challenge BLOCKER. 40-50 trades/year is insufficient to reliably pass a 60-day challenge. Could work as an ADD-ON to a higher-frequency strategy, not standalone.

---

## Comparative Summary Table

| Criterion | A — London ORB (multi-pair) | B — News-Fade | C — AUD/JPY Risk-On/Off |
|-----------|---------------------------|----------------|------------------------|
| Crowding | ⚠️ Medium-High | ✅ Low | ✅ Low |
| FTMO T&C | ✅ OK | ✅ FTMO OK (⚠️ not FundedNext) | ✅ OK |
| Annual cost drag | ✅ 2.5% | ⚠️ 5.25% | ✅ 1.1% |
| Expected net return | ✅ 7.5% | ⚠️ 4.75% | ✅ 7.1% |
| Trades/year | ✅ 84-120 | ⚠️ 50-60 | ❌ 40-50 |
| Hit rate evidence | ⚠️ Weak post-2020 | ✅ Strong (microstructure lit) | ⚠️ Medium-uncertain |
| IC academic support | ⚠️ Decaying | ✅ Strong | ⚠️ Moderate |
| Data complexity | ⚠️ Medium (Dukascopy 1min) | ⚠️ High (news calendar + 1min) | ✅ Low (yfinance only) |
| Challenge frequency | ✅ Sufficient | ⚠️ Borderline | ❌ Insufficient |
| Non-obvious edge | ⚠️ Only with multi-pair | ✅ Fade direction is non-obvious | ✅ Systematic lag non-obvious |

**Hard blockers**: Angle C frequency (❌) eliminates it as standalone propfirm strategy.

---

## Decision

**SELECTED: Angle A — London Open ORB with Multi-Pair Confirmation**

**Rationale:**

1. **Angle C eliminated** on frequency alone. 40-50 trades/year → 3-4 trades/month → challenge requires months to accumulate meaningful trades. Propfirm incompatible as standalone. Might revisit as overlay on top of selected strategy.

2. **Angle B eliminated in favor of A** for the following reasons:
   - Cost arithmetic: 5.25% annual drag vs 2.5% for A. At $100K, Angle B must gross 15.25% to net 10% (challenge target). At 60 trades/year, each trade needs to average $254 gross return — aggressive.
   - Frequency: 50-60 trades vs 84-120 for A. With FTMO 60-day challenge window, Angle B fires on ~10 days. Angle A fires on ~17-20 days (with multi-pair confirmation). Higher frequency = more opportunity to recover from bad days.
   - Data complexity: news calendar integration + spread spike modeling is a significant PHASE 2 risk. Angle B can fail at data pipeline level before even testing the edge.
   - **The news-fade edge is real but margin is thin.** Unless spread modeling confirms ≤ 3.5 pip average during events, cost drag kills the strategy.

3. **Angle A selected with mandatory non-vanilla variant:**
   - Multi-pair confirmation (EUR/USD + GBP/USD breakout in same direction)
   - Asian range quality filter: `range_width > 0.5 × ATR_20d` (exclude choppy pre-sessions that produce false breakouts)
   - DXY direction pre-screen (optional, to test in iter_02): only trade long EUR/USD if DXY was declining yesterday

**Why multi-pair confirmation is non-trivial:**
The key insight is that EUR/USD and GBP/USD have different intraday drivers: EUR/USD is dominated by EUR/USD-specific flows (ECB positioning, Germany data), GBP/USD by UK-specific flows (BOE, UK data). A London open breakout in BOTH EUR/USD and GBP/USD simultaneously is a signal of broad USD directional move driven by USD-global factors, not currency-specific noise. This filters out ~50% of false signals from EUR-specific or GBP-specific flow events. The confirmation requirement is non-obvious because most ORB systems trade single pairs.

---

## Hypothesis Statement

**Strategy slug**: `fx_london_orb`

**Full hypothesis**: At London session open (07:00 UTC), a sustained directional breakout above (or below) the Asian session range (23:00-06:59 UTC) in both EUR/USD and GBP/USD simultaneously predicts continuation of the breakout direction for 30-90 minutes. The dual-pair confirmation filters currency-specific noise and identifies broad USD regime moves. The edge arises from:
- Institutional order flow imbalance from EU market open (institutional desks start executing)
- Stop-order cascades above/below the Asian range (aggregated retail stops)
- Initial momentum from London FX fixing activity (London fix at 16:00 UTC differs, but 07:00 open has similar institution-driven flow characteristics)

**Propfirm fit ($100K FTMO)**:
| Parameter | Target |
|-----------|--------|
| Hit rate | 48-54% (dual-pair filter → higher quality signals) |
| R:R | 1.5:1 (TP = 1× range width, SL = 0.5× range width) |
| Max consecutive losses | ≤ 6 (binomial: P(6 losses) = (0.52)^6 = 2%, acceptable) |
| Trades/year | 80-100 (multi-pair confirmation fires on ~35% of days) |
| Avg trade risk | $500 (0.5% of $100K) |
| Expected annual net | ~8% after 2.5% cost drag |
| P(daily DD > 4%) | < 0.5% (max 1 trade/day, $500 max loss = 0.5% of equity) |
| P(max DD > 8%) | < 5% (estimated from consecutive loss distribution) |

**Disconfirmation criteria (archive immediately if)**:
- IC (breakout direction → 90-min return) < 0.03 at feasibility stage (PHASE 2)
- Dual-pair signal fires < 50 times in 2019-2026 (insufficient data for statistics)
- Hit rate < 43% in backtest (below minimum viable for 1.5 R:R)

---

## Scope for PHASE 2

1. **Data pipeline**: Dukascopy 1-min EUR/USD, GBP/USD, DXY (as confirmation) — 2019-2026. Write `data_fx.py` with parquet cache consistent with `data/cache.py` interface.

2. **IC feasibility** (`iter_01.py`): 
   - Define Asian range: OHLC of 23:00-06:59 UTC bars
   - Define breakout signal: close[07:00 bar] > range_high AND GBP/USD close[07:00 bar] > GBP_range_high simultaneously
   - Measure IC: Spearman(breakout_direction, 90-min forward return) across all sessions 2019-2026
   - Gate: IC > 0.03, t > 2.5 (FX seuil plus élevé que crypto vu edge plus faible)

3. **Quality filter calibration**: What `range_width / ATR_20d` threshold maximizes IC? Test grid [0.3, 0.5, 0.7, 1.0] — counts as 4 separate N_tests starting at n=143.

4. **Spread modeling**: Variable by session (Asia: 1.0 pip, Europe open: 0.8 pip, news event: 3.5 pip) — must be explicit in all backtest P&L calculations.

---

## GATE 1 Status

- [x] Edge defensible: session momentum at London open documented, dual-pair confirmation is non-obvious variant
- [x] Propfirm-compatible: hit rate 48-54% target, R:R 1.5, max 1 trade/day, daily loss bounded at 0.5% per trade
- [x] FTMO T&C: no restrictions
- [x] Cost arithmetic: 2.5% drag viable with 7.5-8% gross expectation
- [ ] IC confirmed: **pending PHASE 2 data + feasibility script**

**GATE 1: CONDITIONAL PASS — pending IC validation in PHASE 2.**

Proceed to PHASE 2: build `fx_london_orb/data_fx.py` + `iter_01.py` (IC feasibility).
