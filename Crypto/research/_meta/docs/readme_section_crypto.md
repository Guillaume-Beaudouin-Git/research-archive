## Crypto Research — Saturation Map (2026-05)

*Standalone section for manual merge into README.md. Insert after §6.47 (VRP Deribit entry).*

---

### 6.50 Saturation Summary — 156 Tests, 3 Missions, 4 Archived Families

Between January 2026 and May 2026, this research program ran **156 hypothesis tests** across three sequential missions on crypto perpetual futures and options, mapping the extractable alpha available to a systematic retail trader using exclusively public APIs. Methodology throughout: excess returns over cash rate, HAC Newey-West SE (lag-6), walk-forward validation (≥5 folds, 18m train / 6m test / 3m step), multiple-testing correction (AMTP/DSR per López de Prado 2018), and explicit stress tests on tail events.

The structural conclusion is that **free-data retail alpha on 29-coin Binance/HL perpetuals is exhausted**: every remaining candidate edge requires either institutional execution access (options market-maker rebates, maker fills at sustained scale) or paid proprietary data sources. One live strategy was extracted (Strategy A — TSMOM v3, OOS Sharpe 1.33) and one is in testnet validation (Strategy B — delta-neutral 8h carry, proxy Sharpe 2.0). Limitations: data gap in Deribit DVOL pre-2021 constrains VRP analysis to the post-DeFi-summer period; Phase 2 IC sub-period stability (33% of years positive) suggests potential regime shift post-ETF approval; all costs assume taker execution (no rebate access).

---

### 6.51 Missions Table

| Mission | Family | Universe | Best Gross Sharpe | Net Sharpe HAC | MaxDD | Verdict | n_tests |
|---------|--------|----------|-------------------|----------------|-------|---------|---------|
| **V1 OHLCV** (6.01–6.36) | Long-only CS: MAX factor, ILLIQ, OI-MOM, LSTM 4h, calendar (×36 signals) | Binance/HL 29 perps daily OHLCV | 1.45 (TSMOM → Strategy A); ≤0.65 all others | <0.70 (no non-A signal passed gate) | — | STRUCTURAL EXHAUSTION; Strategy A extracted | ~142 |
| **V2 HL maker** (6.37–6.42) | Delta-neutral CS: PMR basis MR, OAGF gap fade, CS-FS, FRA | HL/Binance 29 perps + Deribit settlement prices | ~0.50 pre-cost (PMR vol-target est.); OAGF IC=−0.195 (preflight STOP) | PMR: −0.551; OAGF: no backtest | PMR: −65.02% | ARCHIVE | 142→151 |
| **V2 On-chain** (6.43–6.44) | ETH on-chain: MVRV z-score, exchange Netflow z-score | CoinMetrics ETH daily 2016–2026 | — (Gate 1 fail before backtest) | — | — | GATE 1 FAIL (wrong direction + HAC deflation) | 151→153 |
| **VRP Deribit** (6.45–6.47) | BTC ATM straddle short, daily delta-hedged via HL perp, unconditional 16d hold | Deribit BTC options + HL perp 2021–2026 | 1.45 raw unconditional (pre-cost) | −2.682 (0/13 WF folds positive) | −0.247% portfolio at 1% sizing; synthetic stress: −37.8% notional/position | ARCHIVE | 153→156 |

**VRP stress note**: the −0.247% MaxDD reflects smooth bleeding at 1% sizing/straddle × 2 concurrent. At realistic sizing for a standalone strategy (2% portfolio), synthetic COVID scenario (BTC −50%/24h, IV×3) → −75.7% portfolio, far exceeding the −15% hard-stop threshold.

---

### 6.52 Structural Lessons — Documented as Theorems

#### L11 — β-Dominance in Long-Only Crypto CS (2026-05-23)

**Statement**: For any long-only rank-weighted cross-sectional portfolio over N≥5 liquid crypto perps, portfolio-level corr(TSMOM) ≥ 0.80, independent of signal-level IC orthogonality.

**Mechanism**: All liquid crypto perps share β_crypto ≈ 0.65+. Rank-weighted long-only selection concentrates in high-β large-cap coins regardless of the ranking criterion. Spearman IC measures cross-sectional rank order within a period; portfolio-level correlation measures time-series co-movement across periods. The two statistics operate on orthogonal dimensions — a signal can produce IC=0.09 and portfolio corr(A)=0.81 simultaneously. Residualizing the signal on TSMOM preserves IC (tested: from t=3.06 to t=3.72) but does not residualize the portfolio's market exposure, because realized long-only holdings still share β_crypto.

**Verified by**: MAX factor — IC t=3.06, signal corr_A=−0.38, portfolio corr_A=**0.81**. ILLIQ (Amihud) — IC t=3.60, signal corr_A=+0.13, portfolio corr_A=**0.84**. MAX residualized on TSMOM_28d — IC t=3.72, signal corr_A≈0, portfolio corr_A=**0.80+**. All delta-neutral CS designs tested (CS-FS, PMR, FRA): portfolio corr_A < 0.08.

**Implication for future research**: Testing long-only CS signals for IC is valid for hypothesis generation. Portfolio simulation without delta-neutral execution is invalid — any resulting corr(A) ≥ 0.50 fails the orthogonality gate structurally, not marginally. Requirement: long-K / short-K perpetual pairs, or perpetual/spot pairs for β cancellation.

---

#### L12 — Event-Count Ceiling in Threshold-Driven Strategies (2026-05-23)

**Statement**: For threshold-entry strategies, a statistically significant IC is necessary but not sufficient for viability. The following must both hold: `E[events/yr] ≥ N_floor` (statistical power) AND `E[events/yr] ≤ gross_edge / (RT_cost × mean_hold_turnover)` (cost overflow ceiling).

**Mechanism**: Prior methodology gated only the floor (sufficient events for IC stability). The ceiling gate was absent. PMR basis at |z| ≥ 1.5σ: 12.6% of coin-days trigger → 912 events/yr across N=29 coins → 4.1 closes/day × 0.17% RT = 0.70%/day = **178%/yr cost drag** vs estimated gross ≈ 16–20%/yr. The IC gate passed (signal is real); the ceiling gate would have rejected before any backtest.

**Verified by**: PMR backtest — IC t=2.86 (floor: PASS, threshold ≥18/yr passed); events/yr=912 (ceiling: FAIL); Sharpe_HAC=−0.551, MaxDD=−65.02%, WF%=0/2.

**Implication for future research**: Pre-flight must compute: `ceiling = max_acceptable_annual_cost / RT_cost`. At 0.17% taker and 5%/yr target net edge, ceiling ≈ 29 events/yr per position. Event-count gates must be stated as intervals [N_floor, N_ceiling], not one-sided. OAGF failed the floor (128/yr below power threshold for t_HAC=2.5 at IC=0.19); PMR failed the ceiling (912/yr above cost-overflow threshold).

---

#### L12b — Autocorrelation Deflation of HAC Statistics (2026-05-23)

**Statement**: For signals derived from persistent regime series (autocorrelation half-life > 30 days), naive t-statistics overstate significance by factor ≈ √(N_nominal / N_effective). HAC correction with lag ≥ max(6, 4√T) is not a robustness check — it is the primary test.

**Mechanism**: Newey-West SE grows with the long-run variance ratio Ω/σ². For a series with positive autocorrelation summing to S = Σ_{k=1}^{L} (1 − k/L)·ρ_k, the correction factor is ≈ 1 + 2S. For exchange netflow with 6–18 month accumulation regimes, the effective sample size N_eff ≈ N_nominal / (1 + 2S) ≈ 73 from N_nominal = 3,398.

**Verified by**: ETH exchange netflow IC (fwd-30d) — naive t=2.58 (N=3,398 daily, would reject H0); HAC(4) t=0.11 (N_eff ≈ 73, indistinguishable from noise).

**Implication for future research**: Any on-chain, macro, or sentiment signal with |ρ_1| > 0.3 (daily lag-1 autocorrelation) requires HAC with lag ≥ max(6, 4√T). For weekly signals with persistent regimes, effective N can fall below 50 from samples exceeding 400 observations. If HAC t < 2.5 at any lag choice in [4, 12], treat as FAIL regardless of naive significance.

---

#### L13 — VRP Unit Conversion: Variance Space → Notional P&L (2026-05-23)

**Statement**: Academic VRP estimates expressed in annualized variance units (DVOL² − RV² space) must be converted to percentage of underlying notional via the B-S approximation before comparing to transaction cost models expressed as % of notional.

**Mechanism**: Short straddle B-S P&L approximation: `Gross% ≈ ½ × N'(0) × VRP_var × T_hold / σ_DVOL`. At DVOL=0.61 (BTC 2021–2026 mean), T_hold=16/365, VRP_var=0.0906 annualized: Gross% per cycle ≈ 0.162% → +4.44%/yr. Almeida et al. (2024) report "BTC VRP ≈ 14%/yr" in variance units — this is not the P&L percentage. Prior GATE 1 analysis used this figure directly against a cost model in % of notional, producing an apparent 14%/yr gross vs 8.9%/yr cost narrative. After unit conversion: actual gross = +4.44%/yr vs costs = 8.89%/yr → net = −4.46%/yr.

**Verified by**: VRP Phase 3 walk-forward — gross annual=+4.44%/yr, cost annual=−8.89%/yr (option fees 49% + bid-ask 49% + hedge 2%), net=−4.46%/yr, Sharpe_HAC=−2.682, 0/13 WF folds positive.

**Implication for future research**: When benchmarking against any academic VRP magnitude, verify: (a) variance units vs volatility units vs % notional; (b) whether delta-hedge costs are included; (c) whether the premium is quoted net of B-S model error. At retail taker fees (0.03% + 0.6% bid-ask per straddle leg), the gross VRP premium is retail-inaccessible. Break-even requires institutional option maker rebates (≈ −0.01% instead of +0.03% per contract notional).

---

#### L14 — Testnet / Short-Sample Sharpe Inadmissibility (2026-05-23)

**Statement**: Sharpe estimates from testnet or paper-trading periods with N < 250 observations are statistically inadmissible as portfolio optimization inputs, independent of the point estimate.

**Mechanism**: `SE(SR) ≈ √((1 + SR²/2) / N)`. At SR=9.64 (Strategy B testnet), N=66 daily observations: SE=0.848, 95% CI=[7.98, 11.30]. The CI width of 3.3 Sharpe units exceeds the plausible long-run range for any liquid continuous-trading strategy. Additional structural contamination: testnet lacks institutional arbitrage capital → funding rates diverge from mainnet reality; 3-month sample cannot distinguish structural alpha from regime-specific carry (Feb–May 2026 = high-funding bull phase).

**Verified by**: Strategy B testnet SR=9.64 (N=66) → recalibrated mainnet proxy SR=2.0 (backtest SR=4.10 × [1−0.30 mainnet friction] × [1−0.20 regime normalization] × [1−0.10 live vs backtest] ≈ 2.06). At SR=2.0 vs 9.64, ERC allocation to B drops from ~68% to ~40%, restoring meaningful weight to A and C.

**Implication**: Use SR(B)=2.0 for all portfolio simulation until N≥250 mainnet daily returns accumulate (review trigger: realized mainnet Sharpe outside [1.0, 4.0] over ≥12 months). Portfolio gate for any new strategy D: Sharpe(A+B+C+D) > 1.10 × Sharpe(A+B+C), computed at SR(B)=2.0.

---

### 6.53 Two-Dimensional Saturation Map

Each column is a structurally distinct failure mode. ✗ = confirmed primary cause; (✗) = contributing but secondary; — = not a binding constraint for this family.

| Family | β-Dominance | Autocorr HAC-deflation | Cost Drag | OHLCV-Contaminated | Tail Risk | Stat. Power |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|
| CS long-only OHLCV daily (V1) | **✗** | — | **✗** (LSTM: 20%/yr floor) | **✗** | — | — |
| CS delta-neutral funding (V2 PMR/CS-FS) | — | — | **✗** (PMR: 178%/yr drag) | — | **✗** (MaxDD −65%) | (✗) |
| Event-driven threshold panel (PMR high-freq) | — | — | **✗** | — | **✗** | **✗** (ceiling) |
| Event-driven gap fade (OAGF) | — | — | — | — | — | **✗** (floor: 128/yr) |
| On-chain valuation (MVRV z-score) | **✗** (corr_A=0.73) | (✗) | — | **✗** (momentum signal) | — | (✗) |
| On-chain flow (exchange Netflow) | (✗) (corr_A=0.51) | **✗** (t: 2.58→0.11) | — | — | — | **✗** |
| On-chain adoption (active addresses — untested) | — | **✗** (expected: slow-moving) | — | — | — | **✗** (expected) |
| Options VRP timing (Phase 2 IC) | — | (✗) (sub-period stability 33%) | **✗** | — | **✗** | **✗** (non-overlapping IC≈0) |

**Interpretation**: Cost drag and statistical power are the two most prevalent failure modes (each appearing 5× as primary failures). β-dominance is structural in all long-only CS designs regardless of signal quality. Tail risk is binding for all strategies with short-gamma or leveraged mean-reversion exposure. No tested family failed for fewer than two independent reasons.

---

### 6.54 Untested Compass Categories

Source: `Crypto/research/_meta/compass/crypto_alpha_landscape_2026.md`. Eight categories remain unexplored by this research program.

| Category | Representative Angle | Required Data Source | Feasibility | Binding Constraint |
|----------|---------------------|---------------------|-------------|-------------------|
| 1. Microstructure & OFI | OFI 10-level, Binance Futures WebSocket | WSS tick stream (Binance public, free) | Low (retail) | Sub-second execution requires co-location; retail accessible only as execution timing overlay, not position signal |
| 4. Cross-asset / cross-exchange | BTC price discovery Coinbase→Binance lead-lag (Shu et al. 2023); CS cross-crypto LASSO (Jia et al. 2023) | Multi-venue WebSocket, sub-second timestamps | Medium | Lead-lag window < 5s for HF variant; multi-day CS variant feasible but L11 applies |
| 5. Sentiment / narrative | Fear & Greed z-score divergence vs price; Google Trends crypto | alternative.me API (free); pytrends | Medium | Daily granularity; L12b autocorrelation risk (sentiment regimes persistent); prior V1 fear/greed signal failed at cost/signal ratio |
| 6. Macro / cross-market | ETF flow signal (Farside.co.uk) + stablecoin supply (DeFiLlama) as regime filter | FRED API + DeFiLlama stablecoins endpoint (both free) | Medium | Non-stationary BTC–NDX loading post-ETF inclusion; BTC–QQQ corr peaked at 0.87 (2024); regime signal requires HAC from day 1 |
| 7. Calendar / event-driven | Token unlock cliff short (Keyrock 2024: 16,000+ events); short post-listing micro-cap (Empirica 2024 inversion documented) | TokenUnlocks.app (free); Binance Announcements RSS | Medium | L12 floor applies per coin; 2024 data shows naïve listing-long inverted (−22.7% at 3m); short variant requires per-event statistical screening |
| 8. DEX-specific edges | HLP Hyperliquid vault flow contrarian; Uniswap V3 LP active rebalancing (Loesche et al.: 50% of V3 LPs underperform HODL) | HL API public; Uniswap subgraphs via The Graph (free with rate limit) | Medium | Pure MEV fully saturated by professional searchers; LP management feasible; requires web3.py + gas cost model; IL complicates P&L accounting |
| 9. Alternative data | Wikipedia pageviews z-score (Kristoufek 2013 prior); GitHub commit velocity as dev proxy | Wikimedia REST API + GitHub REST API (both free, no key required) | High | Very low institutional competition; slow-moving series → L12b autocorrelation risk; daily granularity caps signal frequency |
| 10. ML / feature engineering transfer | Cross-sectional SHAP-universal model: OFI+spread+VWAP (Bieganowski-Ślepaczuk 2025 show same SHAP structure across BTC/ETH/SOL/alts) | Binance tick stream (public WebSocket) | Low–Medium | L11 applies unless delta-neutral execution; tick data infra cost; requires TimeSeries CV to avoid regime-shift overfitting |

---

### 6.55 References

1. Almeida, C., Grith, M., Miftachov, M., Wang, C. (2024). "Risk Premia in the Bitcoin Market." arXiv:2410.15195. *(VRP magnitude benchmark; L13 unit error source)*

2. Schmeling, M., Schrimpf, A., Todorov, K. (2023). "Crypto Carry." BIS Working Paper No. 1087. *(Funding carry baseline ~7–8%/yr; Mission 2 prior)*

3. López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. *(AMTP / Deflated Sharpe Ratio methodology used throughout)*

4. Harvey, C. R., Liu, Y., Zhu, H. (2016). "…and the Cross-Section of Expected Returns." *Review of Financial Studies* 29(1):5–68. *(HAC necessity rationale; t>3 bar for published factors)*

5. Bieganowski, B., Ślepaczuk, R. (2025). "Universal features of price formation in financial markets." arXiv:2602.00776. *(OFI/VWAP SHAP universality across crypto assets; ML transfer prior)*

6. Drogen, S., Hoffstein, C., Otte, J. (2023). "Cross-Sectional Momentum in Crypto Assets." SSRN:4322637. *(30d→7d CS momentum prior; V1 methodology comparison)*
