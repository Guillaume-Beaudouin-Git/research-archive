# Bootstrap V2 Notes — Maker-Native HL Strategy
*Date: 2026-05-23 | Phase: 0 | Status: GATE 0 — AWAITING "GO PHASE 1"*

---

## 1. Burned Angles (INTERDIT — No Cosmetic Variants)

| # | Signal | Failure Mode | Why No Variants |
|---|--------|-------------|-----------------|
| 6.34 | **Liquidation Signal (Crash Recovery)** | No historical liquidation data; gross IC unverified | Data structural: HL liquidation feed not accessible historically |
| 6.35 | **MAX Volatility** | IC t=3.06 real, but long-only portfolio corr(A)=0.81 (β-dominance, Lesson 11) | Delta-neutral variant → only 2 extremes, signal not suited |
| 6.36 | **ILLIQ Amihud** | IC t=3.60 real, portfolio corr(A)=0.84 (same root cause) | Same β-dominance trap — long-only CS fundamentally broken |
| 6.37 | **CS-FS Funding Cross-Section** | IC t=1.54 FAIL (below gate t > 2.5) | Signal not predictive; FRA variant also t=1.01 FAIL |
| 6.38 | **FRA-DN Funding Acceleration** | IC t=1.01 FAIL | Signal not predictive |
| 6.39 | **PMR Basis Mean-Reversion** | IC t=2.86 at 3d (PASS), but 912 events/year at 1.5σ → ~178%/yr cost drag (Lesson 12) | Threshold 1.5σ = 12.6% of coin-days (Gaussian 13.4%). Wider threshold → < 18 events/year → below gate |

**Root lesson**: 8 signals tested across free-data crypto; 6 killed by data absence or β-dominance; 2 by cost structure. Free-data crypto edge with taker execution is structurally exhausted.

---

## 2. HL Maker Fee Structure

### ALO Order Implementation
- HL SDK: `tif: "Alo"` in order type spec (post-only, guaranteed maker fill or cancel)
- No partial fill risk: ALO cancels rather than crossing the spread
- Current `hyperliquid_client.py` uses MARKET ORDERS ONLY — `exchange.market_open()` / `exchange.market_close()` — no ALO support
- **Phase 5 infra requirement**: new `limit_open()` / `limit_close()` methods using ALO

### Actual Fee Tiers (HL, verified 2026-05-23)
| Tier | 14-Day Volume | Taker | Maker |
|------|--------------|-------|-------|
| Base | $0–$5M | **0.045%** | 0.015% |
| MM Elite | >$5M + qualify | 0.025% | **−0.003% rebate** |

**Discrepancy with mission spec**: Mission states taker = +0.0245%. Actual base taker = 0.045%. The 0.0245% likely refers to a mid-volume tier or a typo. For conservative backtesting, use 0.045% for any taker leg.

### Net Round-Trip Cost Model (per the mission spec, with discrepancy noted)
```
fill_rate = fraction of orders that execute as maker (ALO)
maker_cost  = −0.003% (rebate; requires MM Elite qualification)
taker_cost  = +0.0245% (mission spec) / +0.045% (base actual)
adverse_sel = +0.001% (assumed per position)

Net RT (mission spec) = fill_rate × (−0.003%) + (1 − fill_rate) × (+0.0245%) + 0.001%
Net RT (conservative)  = fill_rate × (−0.003%) + (1 − fill_rate) × (+0.045%) + 0.001%
```

| fill_rate | Net RT (mission taker) | Net RT (conservative taker) |
|-----------|----------------------|----------------------------|
| 50% | +0.011% | +0.022% |
| 70% | +0.006% | +0.015% |
| 90% | +0.001% | +0.005% |

**At 70% fill / mission spec taker**: +0.006% RT ≈ **0.6 bps** — 28× cheaper than pure taker (17 bps).

**Critical caveat**: The −0.003% rebate requires >$5M 14-day volume — institutional MM status, not accessible at research capital levels. Conservative assumption: maker cost = 0% (no rebate, no charge) → use +0.0% maker, +0.045% taker, 70% fill → Net RT ≈ +0.013%.

**Phase 3 sensitivity test**: fill_rate ∈ {50%, 70%, 90%} × taker ∈ {0.0245%, 0.045%} = 6 scenarios.

---

## 3. Evaluation of 3 Suggested Angles

### Angle 1: Spread Capture (Quote on both sides, capture bid-ask)
**Status: BLOCKED — data structural**
- Requires historical L2 order book depth (bid/ask by level, tick-by-tick)
- HL public API provides only trades + OHLCV; no historical L2 snapshot data available via free API
- Backtesting market-making P&L without L2 data is not feasible without fabricating fill assumptions
- Cannot proceed without paid L2 data or live simulation
- **Verdict**: Archive pending data access. Not a research path for this phase.

### Angle 2: Funding-Timed Delta-Neutral (Conditional entry on extreme funding)
**Status: CONDITIONAL — needs IC pre-flight**
- Core idea: enter delta-neutral (long spot + short perp) only when funding > threshold (e.g., 0.2%/8h); hold for 1 funding period then exit
- Genuine structural difference from Strategy B: B holds continuously; this strategy holds only for extreme funding events
- **Corr(B) risk**: if funding extremes occur frequently (high-carry regimes), position overlap with B is substantial → likely |ρ_B| > 0.5
- **Viable scenario**: Funding > 0.2%/8h fires < 15% of 8h periods AND exit happens within 1-2 periods (avoids prolonged B overlap)
- Event frequency at 0.2%/8h threshold: need to measure against Lesson 12 ceiling gate (< 500/year per position slot)
- **Decision**: Requires Phase 1 IC feasibility with event count. Potentially promising but corr(B) measurement is the binding gate.

### Angle 3: Liquidation Absorption (Fade large liquidations)
**Status: BLOCKED — same data constraint as 6.34 + analogous failure**
- Requires real-time or historical liquidation event stream (size, time, coin)
- HL does publish liquidation notifications, but historical archive not available via free API
- This is structurally identical to signal 6.34 (Crash Recovery) which was archived for the same reason
- Even if data were available: liquidation events are infrequent enough that the floor gate (< 18/year per coin) is likely to bind
- **Verdict**: Archive. Same block as 6.34.

---

## 4. New Maker-Native Angles for Phase 1

### Angle A: Funding Momentum + ALO Reversion Entry
**Hypothesis**: After a funding spike (>0.15%/8h), the NEXT 8h period has elevated probability of funding normalization. Enter counter-directional perp position via ALO limit (inside spread) immediately post-spike, hold 1 period, exit.

**Why maker-native**: Entry during post-spike vol compression; spread likely to widen momentarily after large funding event → ALO has realistic fill probability. NOT a market-impact signal.

**Why potentially orthogonal to B**: B enters unconditionally on carry schedule; this only enters on momentum reversal of funding. Entry frequency low (event-driven, not continuous). If funding spikes are infrequent: corr(B) < 0.5.

**Why different from CS-FS (burned)**: CS-FS was cross-sectional ranking across coins. This is time-series: fade a spike in a SINGLE coin's funding sequence. Different mechanism, different IC test.

**IC test**: fwd_return_1period ~ f(funding_lag1 - funding_mean_30d). Horizon 8h. Measure at coin level, not cross-section.

**Pre-flight gate**: event count with 0.15%/8h threshold; require 50–500 events/year across universe.

---

### Angle B: Order Book Imbalance Proxy via OHLCV (Open Auction Fade)
**Hypothesis**: Large gap between open and prior close (gap_ret = open/close_lag1 - 1) reflects order book imbalance at session open. Positions entered at close-of-last-bar against the gap direction (ALO limit at prior close), held for 1 bar.

**Why maker-native**: Entry limit order placed BEFORE the opening auction resolves. ALO placed at prior close price → fills if price reverts; cancels if gap extends.

**Why potentially viable**: Open-gap reversion is a well-documented microstructure effect in equity markets. In crypto perps (24/7, no hard "open"), the analog is: the first 1h bar of each UTC day has systematically different gap properties due to funding settlement (8h cycle).

**IC test**: fwd_1h_ret ~ f(gap_ret_0h_UTC). Measure daily 0:00 UTC bar specifically. Coin-level IC, not cross-sectional.

**Distinction from burned angles**: Not based on funding level (CS-FS, PMR), not cross-sectional (β-dominance), not liquidation-dependent. Pure OHLCV, maker-targeted entry.

---

### Angle C: Cross-Asset Momentum Lag (BTC→Altcoin Propagation)
**Hypothesis**: BTC hourly return predicts altcoin hourly return with 1h lag (propagation delay as information disseminates from BTC to smaller coins). Enter ALO limit on altcoin in BTC's direction, hold 1h.

**Why maker-native**: 1h forward horizon means frequent entries. ALO entry placed mid-spread after BTC move resolves. Fill rate plausibly high because alts will drift toward BTC direction (ALO price is "fair" given BTC signal).

**Why potentially orthogonal to A and B**: A (TSMOM) is 28-day horizon, weekly rebalance — completely different frequency. B is carry-driven, not directional. This is intraday 1h momentum propagation.

**IC test**: fwd_ret_alt_1h ~ f(ret_BTC_lag1h). N = coins × hours. Require IC t > 2.5. Orthogonality measured on daily aggregated returns.

**Known risk**: If BTC propagation is strong and frequent, portfolio will have high beta → corr(A) risk from β-dominance. Mitigant: enter only when |ret_BTC_lag1h| > threshold (event-driven, reduces frequency and concentrates in high-signal bars).

**Pre-flight gate**: event count, IC t-stat, and MANDATORY corr(A) check on daily returns before Phase 2.

---

## 5. Critical Portfolio Gate Analysis

### The Problem
ERC portfolio weights (from B-dominated Sharpe landscape):
- Strategy B: 68% (vol=2.6%, Sharpe=9.64 from 3m OOS)
- Strategy C: 22% (vol=6.2%, Sharpe=1.52)
- Strategy A: 10% (vol=8.5%, Sharpe=1.13)

Adding any strategy D at ERC weight (~10-25%) with realistic Sharpe 0.7–1.1 **decreases** A+B+C+D Sharpe by 35–53% relative to A+B+C. The "10% portfolio gain" threshold in the mission is not achievable with any realistic D unless B's Sharpe is properly discounted.

### Root Cause: B Sharpe Is Likely Inflated
Strategy B OOS data: **3 months only** (2026-02 → 2026-05). This period coincides with elevated crypto funding rates (bull market carry era). The reported Sharpe of 9.64 annualized from 3m data is:
- Based on only ~66 daily observations
- Measured during a high-carry regime (funding consistently 0.1–0.3%/8h)
- Subject to regime change (bear market → funding collapses to near-0 or negative)

Realistic Sharpe estimate for B in a normalized carry environment: **1.5–3.0** (based on longer-horizon carry strategies in crypto literature and 2022 bear-market data where funding went negative for extended periods).

### Recommended Portfolio Gate Recalibration
**Option 1 (Preferred)**: Cap B Sharpe at 3.0 for portfolio simulation purposes. Recompute ERC weights. At Sharpe(B)=3.0, vol=2.6%: B weight drops from 68% to ~40%, A+C weights rise. Adding D with Sharpe 0.7 then achieves ~5-8% portfolio Sharpe improvement — marginal but meaningful.

**Option 2**: Use absolute portfolio Sharpe improvement as gate: A+B+C+D Sharpe > A+B+C Sharpe + 0.05 (additive, not multiplicative). This removes the sensitivity to B's inflated denominator.

**Option 3 (Mission-compatible)**: Keep the 1.10× multiplicative gate but acknowledge that it will likely fail for any D ≤ Sharpe 5.0 at current B weighting. Accept the mission ARCHIVE outcome and treat D as "optionality on B regime change."

**Recommendation**: Raise this recalibration question with user at GATE 0 before proceeding. The portfolio gate as written is structurally broken by B's ERC weight dominance and 3m OOS data inflation.

---

## 6. N_tests Accounting

| Session | Tests | Cumulative |
|---------|-------|-----------|
| Prior sessions | — | 142 |
| V1 pre-flight (CS-FS, PMR×3, FRA) | +5 | 147 |
| PMR backtest v1 | +1 | **148** |
| V2 Phase 0 (no tests yet) | +0 | **148** |

E[max_SR] at N=148: **≈ 4.33** (AMTP). All future strategy Sharpes must be deflated by this threshold.

---

## 7. Next Phase Decision Matrix

| Angle | Viable? | Primary Risk | Phase 1 IC Type |
|-------|---------|-------------|-----------------|
| A: Funding Momentum Reversion | YES — conditional | corr(B) > 0.5 | time-series 8h IC |
| B: Open Auction Gap Fade | YES — conditional | fill rate assumption | 1h bar IC, event-driven |
| C: BTC→Alt Lag Propagation | YES — conditional | β-dominance (corr A) | 1h cross-coin IC |
| Suggested 1: Spread Capture | NO — data block | no L2 historical data | N/A |
| Suggested 2: Funding-Timed DN | CONDITIONAL | same as Angle A | same |
| Suggested 3: Liquidation Abs | NO — data block | same as 6.34 | N/A |

**Recommendation for Phase 1**: Start with **Angle A** (Funding Momentum Reversion) — most differentiated from burned signals, clearest IC test design, and Lesson 12 event-count ceiling is directly testable at the threshold gate.

---

## GATE 0

**STOP. Awaiting "GO PHASE 1".**

Pending user decision on:
1. Which of the 3 new angles to advance (A / B / C, or different angle entirely)
2. Portfolio gate recalibration — Option 1 / 2 / 3 above, or keep as-is
3. Confirm taker cost assumption: mission spec (0.0245%) or conservative (0.045%)
