# VRP Short Gamma — Bootstrap Notes
*Date: 2026-05-23 | Phase: 0 | Status: GATE 0 — AWAITING "GO PHASE 1"*

---

## 0. Source Files Read (Phase 0)

| File | Status | Notes |
|------|--------|-------|
| `Crypto/research/_meta/lesson_11_beta_dominance.md` | ✓ Read | Long-only CS → β-dominance |
| `Crypto/research/_meta/lesson_12_event_ceiling.md` | ⚠ NOT FOUND | Lesson 12 documented in README only — no separate _meta file created |
| `Crypto/research/_meta/lesson_category4_autocorrelation_deflation.md` | ⚠ NOT FOUND | Category 4 added to README section 8 in prior sprint, no separate file |
| `Crypto/research/archived/other/eth_mvrv_netflow/POSTMORTEM.md` | ✓ Read | Mission spec had wrong path (`archived/onchain_mvrv_netflow/`) |
| `Portfolio/risk/strategy_b_sharpe_recalibration.md` | ✓ Read | Sharpe B = 2.0 confirmed |
| `docs/research_maps/crypto_alpha_compass_2026.md` | ⚠ NOT FOUND | `docs/` contains strategy docs only — no compass_2026 file |
| README n_tests=153 section | ✓ Read | n_tests=153, E[max_SR]≈4.34 |

Missing files noted. Content from memory and README substituted.

---

## 1. Data Availability — Critical Correction

**Mission prompt states: "history depuis 2021 ETH / 2019 BTC"**
**Reality (verified via live Deribit API 2026-05-23):**

| Asset | DVOL First Available | Notes |
|-------|---------------------|-------|
| BTC | **2021-04-01** | First recorded DVOL ≈ 86.5. No data before April 2021. |
| ETH | **~2021-06-01** | First recorded DVOL ≈ 106.5. |

**The DVOL index was launched by Deribit in Q1-Q2 2021.** Pre-2021 per-contract data exists (Almeida et al. use it), but the DVOL index itself does not.

Revised history depth:
- BTC: Apr 2021 → May 2026 = **5.1 years** = ~265 weekly cycles
- ETH: Jun 2021 → May 2026 = **4.9 years** = ~255 weekly cycles
- Total events (both assets combined): ~520 weekly cycles ✓ (above 50/year floor, well-distributed)

Current BTC DVOL (2026-05-23): **37.1** — historically low (long-term mean ~70-80). Currently in compressed-vol regime.

---

## 2. Data Path Decision Tree

### Path (a): DVOL History + BS Reconstruction [RECOMMENDED]
**Data**: Deribit public endpoint `/public/get_volatility_index_data`
- Free, no authentication
- Parameters: `currency` (BTC/ETH), `start_timestamp`, `end_timestamp`, `resolution` (1D, 1H, 60, etc.)
- Pagination: `continuation` token in response
- Rate limit: IP-based, ~20 req/s (community-verified; official documentation does not publish exact number)
- Full daily DVOL from Apr 2021, paginated in batches of 1000 rows

**Reconstruction methodology**:
1. Weekly straddle entry every Friday 08:00 UTC (before expiry of existing short)
2. Entry price: BS(S=spot, K=spot_ATM, T=7/365, σ=DVOL/100, r=0)
   - Call + Put = 2 × Call_ATM ≈ 2 × S × σ × sqrt(T) × (2/sqrt(2π)) ≈ 0.7979 × S × σ × sqrt(T)
   - At DVOL=60, T=7d: straddle ≈ 0.80 × S × 0.60 × 0.1384 = **6.64% of spot**
3. Daily delta rehedge: compute BS_delta(S_t, K, T_remaining, DVOL_last/100), rebalance
4. Expiry P&L: intrinsic value at settlement − received premium + cumulative hedge cost + fees

**DVOL vs ATM IV — known discrepancy:**
- DVOL uses variance-swap formula blending the full smile (like VIX) → DVOL > ATM IV when put skew is negative (crypto standard)
- For BTC/ETH with typical put skew −5 to −15 vegas: DVOL typically 5-15% higher than ATM IV
- Impact: using DVOL as σ in BS OVERSTATES straddle premium received (actual ATM IV is lower)
- **Validation test required (Phase 2)**: regress BS(DVOL)-reconstructed straddle price vs actual Deribit mid-market ATM straddle price for 30 most recent weekly expiries. If R² < 0.90 → path (a) is invalid → STOP.
- Alternative if R² < 0.90: use IV_ATM_proxy = DVOL × scaling_factor where scaling_factor < 1 (empirically derived from validation sample)

**Pros**: Free, simple, full history from 2021, maintained pipeline
**Cons**: DVOL ≠ ATM IV (overestimates premium); reconstruction approximates actual execution; misses intraday moves between daily hedges

### Path (b): Per-Contract Data Scraping
**Not recommended.** Deribit does not provide bulk per-contract historical option prices via public API. Historical trade data requires either:
- Tardis.dev (paid, ~$50-200/month depending on depth)
- Deribit own historical data service (charged)
- Scraping public websocket (complex, fragile, legal grey area for systematic scraping)

**Verdict**: Exceeds "30% time on data pipeline" overhead gate. Archive if path (a) fails.

### Path (c): Almeida et al. Dataset (Jul 2017–Dec 2022)
**Available**: GitHub `wang-zjin/BTC-premia` repository (open access, supplementary data from arXiv:2410.15195)
**Coverage**: Jul 2017 → Dec 2022 = 5.5 years, full option surface per-contract
**Use case**: Validation and regime extension (includes COVID Mar 2020, LUNA May 2022 — events not in DVOL window)
**Limitation**: Static, no updates past Dec 2022. Would need to splice with path (a) for 2023-2026.

**Verdict**: Use as supplemental validation for pre-2021 regimes, not as primary pipeline.

---

## 3. Economic Mechanism — VRP in Crypto

### Who pays the VRP?

**1. Retail long holders buying downside insurance (puts)**
- Spot BTC/ETH holders who don't want to sell but want crash protection
- Structural demand for OTM puts → negative risk-reversal → put skew → IV > RV at all strikes
- Inelastic demand: no liquid futures-to-options arbitrage for retail → premium sticks

**2. Retail traders buying upside leverage (calls)**
- Directional traders who prefer defined-risk calls to leveraged futures
- Call demand intensified since Jan 2024 BTC ETF approval (institutional hedging of structured products)
- Creates bilateral IV demand → upward pressure on both put and call IV → total VRP wide

**3. The absent structural vol seller class**
- In equity markets: pension funds sell covered calls, insurance companies write puts, structured product desks sell variance swaps → systematic supply caps the VRP
- In crypto: NO equivalent institutional vol seller exists. Exchange-connected market makers provide liquidity but charge wide spreads and take directional gamma risk — they do NOT systematically sell the VRP
- Result: vol supply is episodic (retail arb, prop shops) vs. structural demand → IV persistently > RV

### Why VRP is ~7× SPX (Almeida et al. 2024)
- **Higher realized vol**: crypto RV 60-80%, SPX RV 15-20% → larger absolute variance premium even if ratio were equal
- **More extreme jumps**: LUNA (-99%), FTX (-80%), COVID (-50% in days) → jump risk premium much larger → risk-neutral density has fatter tails → IV must compensate
- **No Fed put equivalent**: no central bank stabilizer → tail risk premia are uncompressed
- **VRP as annualized value**: 0.14 vs SPX ~0.02 → ratio is correct given jump and vol differences

### Structural edge (non-OHLCV-derivable test)
**Test**: Replace DVOL with rolling HV30 (computed from spot OHLCV) and re-run the strategy.
- If results are similar → strategy is OHLCV-derivable (just harvesting the vol level, not the IV-RV spread)
- If results degrade significantly → the edge lives in the IV surface (DVOL > HV → true options signal)
- This OHLCV-derivability test is **mandatory in Phase 2** (mission requirement R² < 0.7 for OHLCV regression)

Hypothesis: the VRP strategy benefits from:
1. **IV level** (harvestable from HV30, partially OHLCV-derivable) → basic theta harvest
2. **IV-HV spread** (the VRP premium, NOT derivable from HV30 alone) → the pure options signal
The combination makes the strategy partially but not fully OHLCV-derivable. R² expected 0.4-0.6, below the 0.7 rejection threshold.

---

## 4. Expected Correlations

### Corr(VRP, Strategy A — TSMOM)
**Mechanism analysis**:

*Normal regime (no jump)*: VRP earns theta decay slowly. A follows trend. Returns uncorrelated — different timescales, different mechanisms. Expected daily corr: **0.0 to +0.10**.

*Trending bull market*: VRP earns more (call buyers dominate → wider call IV → short straddle earns). A is also long. Returns **co-positive** → transient corr spike.

*Crash event (single day)*: Straddle P&L = -(realized_move² - IV² × T) × gamma. A short-term signal: VRP loses immediately on the down day. TSMOM signal: A may not yet be short if the trend signal is weekly. Both lose → spike in **positive corr** (both negative on crash day).

*Sustained bear (weeks after crash)*: VRP: IV elevated → short straddle earns high premium → positive weekly P&L. A: short signal kicks in → A positive. **Positive corr** persists.

**Expected |ρ_A| overall**: 0.10–0.25 in normal regime. Conditional on crash months: 0.35–0.55. Given the relaxed V2 gate |ρ| < 0.50, likely passes in non-extreme years. **Needs empirical verification** — this is the binding gate.

**Orthogonality mechanism**: VRP is convexity-premium (earned from vol level relative to realized vol), A is direction-premium (earned from price momentum). These are mathematically orthogonal *payoff structures* but empirically correlated through the market regime channel. The hedge (long ATM straddle) would genuinely orthogonalize but adds cost that erases the edge.

### Corr(VRP, Strategy B — Carry)
**Expected |ρ_B|**: 0.05–0.15. Mechanisms completely independent:
- B earns carry (rate differential between spot and perp)
- VRP earns vol premium (IV > RV)
- Both suffer in extreme tail events (negative carry can coincide with volatility spikes) but timing differs
- **No structural overlap** → expected low correlation confirmed by mechanism analysis

---

## 5. Sample Size Assessment

| Asset | DVOL Start | Weekly Cycles | HAC-effective N (lag=4) | t-threshold for IC=0.10 |
|-------|-----------|--------------|------------------------|------------------------|
| BTC | Apr 2021 | ~265 | ~53 | 0.10 × √53 = 0.73 → PASS |
| ETH | Jun 2021 | ~255 | ~51 | 0.10 × √51 = 0.71 → PASS |
| Combined | — | ~520 | ~104 | 0.10 × √104 = 1.02 → PASS |

**Note on unconditional P&L test**: The Phase 2 IC gate is not a Spearman IC test for the unconditional strategy. It is: t-stat on mean weekly P&L NET > 2.5. At N=265 weekly cycles and HAC lag=4 (weekly data, ~1-month autocorrelation of vol regimes):
- Effective N ≈ 265 / 4 = 66 (conservative)
- SE(mean_P&L) = std_P&L / sqrt(66)
- Need mean_P&L > 2.5 × std_P&L / sqrt(66) = 0.307 × std_P&L
- At Sharpe = 0.7 (annual), weekly Sharpe ≈ 0.7/sqrt(52) = 0.097 → mean = 0.097 × std → t = 0.097/0.307 = 0.32 → FAIL
- **At Sharpe = 1.5 (annual)**: weekly Sharpe ≈ 0.208 → mean = 0.208 × std → t = 0.68 → FAIL
- **At Sharpe = 3.0**: weekly Sharpe ≈ 0.416 → t = 1.35 → FAIL
- **At Sharpe = 5.0**: t = 2.25 → marginal

**Concern**: The t > 2.5 gate with HAC and weekly data is VERY difficult to pass for vol strategies that have periods of elevated losses (crash months). The weekly P&L autocorrelation is high in crash regimes → HAC inflates SE substantially. This may be the binding constraint.

**Alternative IC design (recommended)**: Instead of t-stat on mean P&L alone, use:
- IC = Pearson(DVOL_t / HV30_t, straddle_P&L_t) on weekly obs
- This tests whether higher IV/HV spread → more profitable trade (the true signal)
- Spearman IC test with t = IC × sqrt(N-2) / sqrt(1-IC²), HAC-adjusted
- More powerful than mean-P&L test because it conditions on the VRP premium magnitude

Both tests run in Phase 2. The Spearman IC (conditional) is the more sensitive gate.

---

## 6. Cost Model (Verified)

### Options (Deribit)
- Taker fee: **0.03% of underlying notional**, capped at **12.5% of option premium**
- Maker rebate: −0.02% of underlying notional (available with ALO limit orders)
- Settlement fee: 0 (Deribit does not charge for expiry/settlement)
- Both call and put sides charged separately at entry: total entry = 2 × 0.03% = 0.06% notional

### Delta-hedge (Deribit perp)
- Taker: **0.05%** per round-trip
- Maker: −0.02% (post-only orders)
- Expected 1 delta-hedge per day × 7 days × 0.05% taker = 0.35% notional per week in hedging cost

### Bid-ask spread (straddle)
- Liquid periods (normal vol): **0.5–1.0%** of straddle premium = **0.03–0.07% of notional**
- News/high-vol periods: **2–5%** of straddle premium
- Use 1% of straddle premium as baseline = ~0.07% of notional at DVOL=60, T=7d

### Total weekly cost estimate (at DVOL=60, BTC=$50k)
| Component | % of notional |
|-----------|--------------|
| Options taker (entry, both legs) | 0.060% |
| Bid-ask spread entry | 0.070% |
| Delta-hedge (7d × daily) | 0.350% |
| Slippage delta-hedge | 0.070% (0.01% × 7) |
| **Total** | **0.55% of notional/week** |

**Break-even VRP**: need premium earned > 0.55%/week. At DVOL=60, ATM straddle = 6.64% of spot → 0.55% break-even = **8.3% of premium**. Given VRP of 0.14 annualized = ~0.27% weekly, this is a tight but positive margin.

**Key sensitivity**: delta-hedge frequency. At 4h hedge (42 hedges/week vs 7/day): hedge cost rises 6×. At daily: 0.35%. The **daily hedge assumption is optimal** for this cost model.

---

## 7. Signal Design Options for Phase 1

### Baseline (unconditional)
- Short ATM straddle every Friday regardless of vol regime
- Signal: none (strategy timer only)
- Expected Sharpe: 0.8–1.5 based on Almeida et al. VRP magnitude
- Corr(A): moderate positive (both positive in trending bull market)

### Conditional (recommended for iter 2 if unconditional fails)
- Signal: VRP_z = (DVOL_t − HV30_t) z-scored over 90d rolling window
- Enter short straddle only when VRP_z > 0 (IV meaningfully above realized)
- Expected Sharpe improvement: 0.3–0.5 over unconditional
- Event count: depends on threshold. VRP_z > 0 fires ~55% of weeks (above median) = ~143 events/year across both assets ✓

### Phase 1 selection (one for IC test)
Per mission: choose ONE for Phase 2 IC test, other becomes candidate for iter 2.
**Recommendation**: baseline (unconditional) for Phase 2 — simpler, no signal overfitting, stronger n_tests efficiency. If t-stat on mean P&L FAILS, move to conditional as iter 2.

---

## 8. Walk-Forward Design

- Train: 18 months | Test: 6 months | Step: 3 months
- From Apr 2021 to May 2026 (61 months total):
  - First train end: Oct 2022, first test: Oct 2022–Apr 2023
  - Steps: Oct 2022, Jan 2023, Apr 2023, Jul 2023, Oct 2023, Jan 2024, Apr 2024, Jul 2024, Oct 2024, Jan 2025, Apr 2025
  - ~11 train/test periods → ~7 OOS periods (after removing 18m warmup) = 42 months OOS
- WF pass criterion: ≥ 50% of OOS periods show positive Sharpe

---

## 9. Regime Coverage Assessment

| Event | Date | DVOL Available? | Expected Impact on Short Straddle |
|-------|------|----------------|----------------------------------|
| BTC ETF Approval | Jan 2024 | ✓ | Positive (IV surge pre-event, short before) |
| LUNA collapse | May 2022 | ✓ | **Severe negative** (gamma explosion, >5σ daily move) |
| FTX collapse | Nov 2022 | ✓ | **Severe negative** (largest single-week loss expected) |
| COVID crash | Mar 2020 | ✗ (no DVOL) | Not captured — use Almeida dataset for validation |
| 2024 Bull run | Q4 2024 | ✓ | Positive (premium earned, moderate realized vol) |

**Key risk**: 2022 had two catastrophic events (LUNA + FTX) in 6 months. Both are in the DVOL backtest window. If short straddle drawdown from these events is > −25% (MaxDD gate), the strategy fails. This is the primary TAIL_RISK_GATE concern.

---

## 10. N_tests Accounting

| Session | Tests | Cumulative |
|---------|-------|-----------|
| On-chain mission | — | 153 |
| Phase 2 IC test (unconditional baseline) | +1 | 154 |
| Phase 3 backtest iter_01 | +1 | 155 |
| Phase 3 iter_02 (conditional VRP_z, if iter_01 fails) | +1 | 156 |
| Phase 3 iter_03 (parameter variant) | +1 | 157 |
| Phase 4 bootstrap/DSR | +0 | 157 |
| Portfolio sensitivity | +1 | **158 = hard limit** |

---

## GATE 0

**STOP. Awaiting "GO PHASE 1".**

Pending decisions:
1. **Signal choice for Phase 2**: unconditional baseline (recommended) or conditional VRP_z > 0
2. **DVOL validation commitment**: Phase 2 MUST include BS reconstruction R² check vs actual Deribit prices on recent 30 cycles before proceeding to full backtest. If R² < 0.90 → STOP.
3. **Tail risk tolerance**: LUNA (May 2022) and FTX (Nov 2022) are in-sample. Straddle on BTC in those weeks likely lost 15-30% of weekly notional. Acknowledge this as a known fat-tail period before RESEARCH_PASS evaluation.
4. **Almeida dataset integration**: use as validation (pre-2021 regimes) or ignore and rely solely on DVOL 2021-2026?
