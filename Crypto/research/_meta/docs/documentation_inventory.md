# Documentation Inventory — Crypto Research Marathon
*Generated: 2026-05-23 | For README "Crypto Research — Saturation Map" section*
*Target: README §6.xx, audience: senior quant peers (CFM, Qube, Squarepoint)*

---

## I. Research Missions (3 missions, 4 archived families, 156 tests)

### Mission 1 — Free-data OHLCV Alpha (V1)
**Slug**: `crypto_v1_ohlcv`  
**Sections**: 6.01–6.36  
**Hypothesis**: Public OHLCV from Binance/HL (N=29 perps) contains exploitable orthogonal alpha across momentum, reversal, volatility, calendar, and ML-engineered signals.  
**Scope**: ~36 distinct signals tested including: TSMOM (became Strategy A LIVE), MAX factor, ILLIQ, OI-MOM, liquidation flow, calendar anomalies (weekday/weekend/monthly), LSTM 4h classification, cross-sectional L/S variants.  
**Verdict**: STRUCTURAL EXHAUSTION. Strategy A (TSMOM) LIVE. All others Sharpe_HAC < 0.7. Two structural constraints identified: (1) β-dominance in long-only CS → Lesson 11; (2) ML signal real but cost floor too high (LSTM: IC real, 117 trades/yr × 0.17% = 19.95%/yr cost floor → any gross edge wiped).  
**Best gross Sharpe (pre-cost)**: ~1.45 (TSMOM, later Strategy A). Non-Strategy-A best: ≈ 0.55–0.65.  
**Effective cost model**: 0.17% RT taker throughout.  
**IC stats (representative)**: MAX factor IC t = 3.06, port corr(A) = 0.81 (β-dominated); ILLIQ IC t = 3.60, port corr(A) = 0.84.  
**n_tests consumed**: ~142 (6.01–6.36)

---

### Mission 2 — HL Maker-Native + On-Chain (V2)
**Slug**: `crypto_v2_hl_onchain`  
**Sections**: 6.37–6.44  
**Core question**: Can delta-neutral execution on HL + maker rebates produce orthogonal alpha (|ρ_A| < 0.3) that survives 0.17% RT cost model?

#### Family 2a — Delta-neutral HL maker (PMR / OAGF / CS-FS)
**Hypothesis**: HL-specific microstructure signals (basis mean-reversion, funding settlement gaps) accessible at near-zero cost via maker fills provide edge invisible to long-only portfolios.  
**Representative result — PMR basis**:
- Signal: perp/spot basis z-score ≥ 1.5σ → delta-neutral mean-reversion
- IC: -0.064 (3d horizon), t_HAC = **2.86** (PASS pre-flight gate)
- Backtest: Sharpe_HAC = **-0.551**, MaxDD = **-65.02%**, WF = **0/2 folds**
- Root cause: 912 events/yr (12.6% of coin-days) → turnover ≈ 178%/yr cost drag vs ~16-20%/yr gross — cost ceiling gate failure
- Orthogonality: corr_A = 0.18, corr_B = 0.06 ✓ (delta-neutral confirmed escape from β-dominance)

**OAGF (Open Auction Gap Fade)**:
- Signal: |gap_ret| > 0.30% at funding settlement (0:00/8:00/16:00 UTC) → reversion trade
- IC: -0.189 (correct direction), t_HAC = **-1.17** (FAIL, gate = -2.5)
- Root cause: 128 events/yr → requires ~10 years of data to reach significance. Pre-flight STOP, no backtest.

**Verdict**: ARCHIVE. Signal-level IC real for both. Unexploitable: PMR cost overflow, OAGF event-count floor.  
**n_tests consumed**: 142→151 (+9: CS-FS/FRA IC ×4, PMR backtest ×1, OAGF IC ×3 horizons, PMR WF ×1)

#### Family 2b — On-chain ETH (MVRV + Netflow)
**Hypothesis**: ETH exchange netflows (accumulation signal) + MVRV z-score (mean-reversion on cost-basis premium) predict 14-60d returns orthogonally to TSMOM.  
**Results** (weekly obs 2017–2026, HAC lag=4):

| Signal | IC (fwd-30d) | t_HAC | corr_A | Gate |
|--------|-------------|-------|--------|------|
| MVRV_z | +0.113 | 1.41 | **0.734** | FAIL — wrong direction + β-dominated |
| Netflow_z | +0.003 | 0.11 | **0.512** | FAIL — autocorrelation-deflated |

- MVRV root cause: in crypto, high MVRV = bull regime continuation (momentum), not mean-reversion as in equity P/B analogy. Signal fires on 90-95% of bull-run observations as trending indicator.
- Netflow root cause: naive t = 2.58 (N=3398 daily), HAC(4) → t = 0.11. Persistent flow regimes (accumulation lasts 6-18 months) make effective N ≈ 73 vs nominal 3398 → Lesson 12b.

**Verdict**: ARCHIVE. Both signals fail Gate 1 before IC pre-flight completes.  
**n_tests consumed**: 151→153 (+2: MVRV IC ×1, Netflow IC ×1)

---

### Mission 3 — Deribit BTC Volatility Risk Premium (VRP)
**Slug**: `crypto_vrp_deribit`  
**Sections**: 6.45–6.47  
**Hypothesis**: BTC implied volatility (DVOL) structurally exceeds realized volatility (RV30). Unconditional short ATM straddle 30 DTE → 14 DTE roll, delta-hedged with HL perp, generates positive net P&L retail-accessible.

#### Phase 2 — IC Feasibility (signal timing test)
**Question**: Does DVOL² − RV30² signal predict forward option P&L (timing layer)?  
**Data**: 2021-05-01 → 2026-05-07 (1833 days, 1879 DVOL bars via backward pagination)  
**Descriptive**: VRP mean = 0.0906 (80.1% of days positive), raw Sharpe unconditional = **1.45**  
**IC overlapping**: 0.1261, t_HAC = **2.351** (BORDERLINE — fails >2.50 gate; sub-period stability 33% of years positive)  
**IC non-overlapping**: -0.0156, t_HAC = **-0.153** (effectively zero on independent cycles)  
**Gates**: 3/5 PASS. Verdict: BORDERLINE → user GO for Phase 3.  
**n_tests**: 153→154

#### Phase 3 — Walk-Forward Backtest (unconditional always-short)
**Strategy**: Always-short ATM straddle at every cycle. N=2 concurrent, 1% portfolio per straddle. Regime filter: no entry if BTC DD30 > 15%, unwind if > 20%. Hold 16 days (30 DTE → 14 DTE).  
**Cost model**: option fees 0.12% (4 × 0.03% taker), bid-ask spread 0.10-0.12% per cycle, delta-hedge blended 0.004% per cycle.  
**Walk-forward**: 13 folds, 18m train / 6m test / 3m step, 2022-11 → 2026-05.

**Full-sample results (N=184 cycles, 2021–2026)**:
- Gross annual P&L: **+4.44%**/yr of underlying notional
- Total cost annual: **-8.89%**/yr (option fees 49%, bid-ask 49%, hedge 2%)
- Net annual: **-4.46%**/yr | Sharpe_HAC = **-2.682** | t_HAC = -6.035
- Skewness = -1.767, excess kurtosis = 4.679 (confirmed fat left tail)
- WF positive folds: **0/13**

**Root cause — GATE 1 unit error**: Almeida (2024) "14%/yr VRP" is in variance units (DVOL² − RV² ≈ 0.14 annualized), not % of underlying notional. After correct B-S conversion: `gross% ≈ ½ × N'(0) × VRP_var × T_hold / DVOL` → +4.44%/yr. Costs = 8.89%/yr. Net = −4.46%/yr. The prior GATE 1 calculation compared variance-unit VRP directly to a % cost model — 3-order-of-magnitude unit mismatch.

**Stress tests**: LUNA cycle -0.44%, FTX cycle -2.56%. Synthetic COVID (BTC -50%/24h, IV×3): -37.83% of notional per concurrent position; at 2% sizing → -75.7% portfolio (vs -15% hard-stop → disqualifying even if net positive).  
**Conditional DVOL>80%**: net ≈ -0.008%/cycle (near-breakeven) — potential but would consume n_tests=157.  
**What rescues it**: institutional maker option fees (rebate rather than 0.03% taker). Retail-inaccessible.

**Verdict**: ARCHIVE. VRP premium exists (+4.44%/yr gross) but not retail-accessible net of realistic costs.  
**n_tests**: 154→156 (+1 Phase-3 WF + budget = n_tests_before=155, after=156)

---

## II. Structural Lessons (5, applicable cross-mission)

| # | Slug | One-liner |
|---|------|-----------|
| L11 | `beta_dominance` | Any long-only crypto CS portfolio has corr(A) ≈ 0.80+, independent of signal IC (tested: MAX t=3.06 → port corr=0.81). Only delta-neutral execution escapes. |
| L12 | `event_count_ceiling` | Event-driven strategies need both a floor (≥18/yr for statistical power) AND a ceiling (≤200/yr to avoid cost overflow). PMR: 912/yr → 178%/yr cost drag. |
| L12b | `autocorrelation_deflation` | Persistent regime signals (on-chain flows, macro) have effective N ≈ 1/autocorr_sum × nominal N. Netflow: nominal N=3398, HAC deflates to effective N≈73, t 2.58→0.11. |
| L13 | `vrp_unit_conversion` | When VRP is in variance units (σ²), convert to % of notional via `½ × N'(0) × VRP_var × T_hold / σ_DVOL` before comparing to cost models. Failure = 3-order-of-magnitude mismatch. |
| L14 | `strategy_b_recalibration` | Testnet Sharpe (9.64, N=66 days) is statistically inadmissible (SE=0.85) and structurally contaminated (no arb capital on testnet). Mainnet proxy = 2.0 (backtest 4.10 × 0.7 × 0.8 × 0.9). |

---

## III. Academic Citations

| Paper | Authors | Year | Used for |
|-------|---------|------|---------|
| "Risk Premia in the Bitcoin Market" arXiv:2410.15195 | Almeida, Grith, Miftachov, Wang | 2024 | VRP magnitude benchmark; GATE 1 unit error source |
| "Crypto Carry" BIS WP 1087 | Schmeling, Schrimpf, Todorov | 2023 | Carry premium 7-8%/yr baseline; Mission 2 motivation |
| "Advances in Financial Machine Learning" | López de Prado | 2018 | AMTP methodology; WF design; HAC Sharpe framework |
| "...and the Cross-Section of Expected Returns" *JF* 72(1) | Harvey, Liu & Zhu | 2016 | HAC necessity rationale; t>3 bar for new factors |
| "Universal features of price formation in financial markets" arXiv:2602.00776 | Bieganowski, Ślepaczuk | 2025 | OFI/VWAP SHAP universality; ML cross-asset transfer |
| "Cross-Sectional Momentum in Crypto" SSRN 4322637 | Drogen, Hoffstein, Otte | 2023 | 30d→7d CS momentum prior; V1 methodology comparison |

---

## IV. Untested Compass Categories (8 of 10)

Categories from `Crypto/research/_meta/compass/crypto_alpha_landscape_2026.md` not addressed in the 3 missions:

| # | Category | Representative angle | Saturation | Binding constraint for next test |
|---|----------|---------------------|------------|----------------------------------|
| 1 | Microstructure & order flow | OFI 10-level Binance Futures WebSocket | Very high (sub-second) | Co-location required for HFT; useful as execution timing only |
| 4 | Cross-asset & cross-exchange | BTC price discovery Coinbase→Binance lead-lag; CS cross-crypto LASSO | Moderate | Multi-venue WebSocket infra; latency-sensitive (1s–5min) |
| 5 | Sentiment, social, narrative | Fear & Greed z-score divergence vs price | Low–moderate | Daily frequency, free data (alternative.me, pytrends) |
| 6 | Macro & cross-market | ETF flow (Farside.co.uk) + stablecoin supply as regime proxy | Low | DXY/CPI correlation shifts post-ETF; non-stationary loadings |
| 7 | Calendar & event-driven | Token unlock cliff short (Tokenomist.ai); post-listing short | Low–moderate | Event sparsity for rigorously tested coins; Keyrock 2024 data |
| 8 | DEX-specific edges | HLP Hyperliquid vault flow contrarian; Uniswap V3 LP imbalance | Moderate (MEV saturated, LP mgmt not) | On-chain data infra (web3.py / subgraphs); gas cost model |
| 9 | Alternative data | Stablecoin mint supply pulse (DeFiLlama); GitHub dev activity | Low | Autocorrelation risk (L12b) applies; need HAC from day 1 |
| 10 | ML / feature engineering | Cross-sectional SHAP transfer (OFI+spread+VWAP) per B-S 2025 | Moderate | Must pair with delta-neutral execution to avoid L11; requires tick data |

**Note**: Categories 3 (options/carry) and 2 (on-chain) were the focus of Missions 2 and 3. Category 3 partially lives as Strategy B (delta-neutral carry, LIVE). Category 7 was partially explored in V1 (calendar effects, failed at HAC gate).

---

## V. Test Count Summary

| Mission | n_tests range | Families | Key gate failures |
|---------|--------------|----------|-------------------|
| V1 OHLCV | 1–142 | Long-only CS signals | β-dominance (L11); cost floor ML |
| V2 HL maker | 142–151 | PMR basis, OAGF | Cost ceiling (L12); event-count floor (L12) |
| V2 on-chain | 151–153 | MVRV, Netflow | Wrong direction (MVRV); autocorr deflation (L12b) |
| VRP Deribit | 153–156 | BTC straddle short | Unit error GATE 1 (L13); costs 200% of gross |
| **Total** | **156** | **4 families archived** | **3 structural constraints codified (L11–L13)** |

---

*GATE 0 — Inventory complete. HARD STOP. Awaiting user validation before README Phase 1 writing.*
