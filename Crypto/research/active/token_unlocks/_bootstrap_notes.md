# Bootstrap Notes — Token Unlocks Event-Driven Short
*Date: 2026-05-23 | Mission: single-shot event-driven short pre-cliff unlock*
*Budget: n_tests 157 → 159 (+2 max). GATE 0 — awaiting user decision on data source.*

---

## 1. Mission Framing

This is a **single-shot event-driven short** strategy: enter short T-30 days before a cliff unlock event (>5% circulating supply), exit at T+7. NOT a portfolio overlay — a standalone directional strategy.

**Source hypothesis** (Keyrock 2024, 16,000+ events):
- 90% of cliff unlocks are followed by price decline
- Team unlocks: average -25% price drop
- Investor unlocks: more controlled (institutional hedging absorbs supply)
- Timing: price pressure begins ~30 days before the unlock date
- Exit 14 days post-unlock as stabilization target; we use T+7 (more conservative)

**Empirica distinction (per compass §7)**: The "Empirica edge inversion 2024" refers to the **Binance listing effect** (buy-on-listing → now sell-on-listing for 2024 cohort at -22.66% 3-month return). This is a SEPARATE signal from cliff unlocks. The pre-cliff-unlock short mechanism is structurally independent: it is driven by known forced-selling by team/VC holders, not by listing-day retail momentum. Keyrock's study covers 2020–2024, and the effect is documented as persistent across market regimes.

**Success criterion (pre-registered, locked before any data analysis)**:
- PHASE 2 IC gate: `E[ret_T-30..T+7 | cliff_unlock > 5%] < -0.30%/day`, HAC t < -2.0
- PHASE 3 RESEARCH_PASS: Sharpe HAC NET > 0.7, MaxDD > -25%, WF > 50%, N_events > 50

---

## 2. Data Architecture: Full Assessment

### 2a. Primary Sources (Specialized Token Unlock Data)

**Tokenomist.ai / TokenUnlocks.app** (same company, Tokenomist rebranded):

| Tier | Cost | Historical Coverage | API Access |
|------|------|---------------------|-----------|
| Free | $0/mo | 3 historical events only | None |
| Pro | $49/mo | All historical, -2Y to +4Y | Browser/CSV only |
| Standard API | $250/mo | **1Y** historical via API | REST endpoints |
| Elite API | $450/mo | **2Y** historical via API | REST endpoints |

**→ PAID DATA for any useful historical coverage.** The stop condition names this source explicitly.

**DeFiLlama Emissions API** (`pro-api.llama.fi/api/emissions`):
- Returns 402 (Payment Required) on free tier
- Pro subscription: $300/mo
- **→ PAID DATA.** Confirmed via live test 2026-05-23.

### 2b. Alternative Sources (Not Named in Stop Condition)

**CryptoRank.io**:
- Public API requires API key (`401` without key)
- Free public API key available at `cryptorank.io/public-api` (no credit card required per their docs)
- Token unlock endpoints documented in V1/V2 API
- **UNKNOWN**: whether free API key provides historical unlock event data back to 2022
- Current page SSR data confirmed 200 OK — contains 419 upcoming events in browser
- **Action required**: User to sign up for free CryptoRank API key and test historical unlock endpoint

**CoinGecko market_chart (free, no key, 365-day window)**:
- `market_chart?days=365` works without API key (confirmed 200 OK)
- Contains `prices` + `market_caps` + `total_volumes` at daily granularity
- **Derived circulating supply**: `circ_supply ≈ market_cap / price` (confirmed working for APT)
- Can detect cliff events algorithmically: supply jump > N% in one day = unlock event
- **Confirmed**: APT had an 8.4% supply jump in the last 365 days (detectable!)
- **Limitation**: Only 365 days free (May 2025 → May 2026). 4-year backtest requires paid.
- **Limitation**: Market cap lags actual on-chain unlocks by 1-3 days (CoinGecko update cycle)

**CoinGecko Pro Demo key (free signup)**:
- 30 calls/min, but `days > 365` requires Pro ($129/mo)
- Insufficient for 4-year backtest

### 2c. Manual Curated Dataset (Last Resort)

For the top 50 mid-cap tokens (by 2022-2026 average market cap, $100M–$5B range), cliff unlock schedules >5% supply are **publicly documented** in:
- Project whitepapers / tokenomics pages
- Team blog posts and foundation announcements
- CoinDesk / The Block / Blockworks coverage at the time of major unlocks
- Tokenomist public pages (browser-viewable, not API-accessible for historical)

**Estimated universe** (50 tokens × avg 2 cliff events/year × 4 years = ~400 events):
Top candidates: APT, SUI, ARB, OP, DYDX, WLD, SEI, STRK, PYTH, JTO, TIA, BLUR, DYDX, IMX, ILV, GALA, LOOKS, APE, MAGIC, GMX, GNS, PERP, ID, AGIX, RNDR, FIL, INJ, BAND, KAVA, EGLD

**Problems with manual approach**:
- Selection bias: only tokens we know about (survivors, headline events)
- Labor intensive: 3-5 hours to build even a partial dataset
- Data quality: risk of incorrect dates, amounts, or event types
- NOT REPRODUCIBLE: would need Tokenomist verification later

**Verdict on manual approach**: Acceptable for a "mission lite" single-shot test IF the user explicitly accepts the survivorship bias caveat. The bias direction is CONSERVATIVE (we'd miss unlocks that had no price impact, thus overestimating the edge).

---

## 3. GATE 0 — DATA DECISION TREE

```
├── Option A: CryptoRank free API key
│   └── User signs up at cryptorank.io/public-api
│   └── Test: GET /v1/currencies/{id}/vesting?api_key=FREE_KEY
│   └── IF historical events 2022-2026 accessible → PROCEED TO PHASE 1
│   └── IF only upcoming events → STOP or go to Option B
│
├── Option B: Manual curated dataset (50 tokens)
│   └── Explicit survivorship bias caveat pre-registered
│   └── IF user accepts bias → PROCEED TO PHASE 1 with caveat noted in HYPOTHESIS.md
│   └── Expected time: 4-6 hours to build
│
└── Option C: Stop condition triggered
    └── "paid data required: Tokenomist $49-450/mo, DeFiLlama $300/mo, CryptoRank (unclear)"
    └── Archive with lesson: "token unlock event data requires paid subscription for backtest"
```

**Recommendation**: Try Option A first (30 min max to test). If CryptoRank free key gives 2022+ historical data → proceed with clean, comprehensive dataset. Otherwise, Option B is viable for a mission-lite single-shot test given the strategy's economic robustness (Keyrock 16k+ events vs our curated 100-400).

---

## 4. Universe Definition

### Filtering Logic
```
eligible_token(t) = (
    mcap_rank ≤ 100                          # top 100 by market cap (excludes BTC/ETH at top)
    AND NOT in {BTC, ETH}                    # no team/VC unlocks for native PoW assets
    AND unlock_size > 0.05 * circ_supply      # cliff > 5% of circulating supply
    AND category IN {"team", "investor",
                     "foundation", "treasury"} # NOT ecosystem/community airdrops
    AND adv_30d_usd > 5_000_000              # ADV > $5M on Binance or ByBit
    AND NOT linear_vesting                   # cliff event only (not daily drip)
)
```

### Keyrock Size Classification
| Category | % of Circulating Supply | Expected Impact |
|----------|------------------------|-----------------|
| Nano | <0.1% | Negligible |
| Micro | 0.1%–0.5% | Minimal |
| Small | 0.5%–1% | Moderate |
| Medium | 1%–5% | Moderate |
| **Large** | **5%–10%** | **Significant (-25% avg)** |
| **Huge** | **>10%** | **Very significant (2.4× effect)** |

Pre-registered filter: **Large + Huge** (>5% circulating supply).

### Exclusions
- **Ecosystem / Community** unlocks: Keyrock documents +1.18% average (POSITIVE) — these are incentive/airdrop unlocks with no forced sellers. Exclude to avoid diluting the signal.
- **BTC / ETH**: No team vesting (PoW genesis, no VC allocation).
- **Micro-caps** (ADV < $5M): Illiquid, unreliable fill on 0.1% taker. Slippage model breaks down.
- **Already-vested tokens** (>90% circulating/total supply): No more unlocks.

### Expected Universe Size
Based on compass assessment and Keyrock paper:
- Top 100 mid-cap tokens: ~60-70 have VC/team vesting schedules
- Of these, ~30-40 have had at least one cliff unlock >5% since 2022
- Average 2-3 cliff events per year per token
- Expected total events 2022-2026: **100-200 events** ✓ (above N_floor=50, below N_ceiling=500)

---

## 5. Pre-Registered Hypothesis (LOCKED, before any data analysis)

**Entry**: T-30 calendar days before cliff unlock date
- "T" = the official unlock date (on-chain or whitepaper-announced)
- "T-30" = 30 calendar days prior → short entry at close
- Source: Keyrock finds price pressure starts ~30 days pre-unlock

**Exit**: T+7 calendar days after cliff unlock date
- "T+7" = 7 calendar days post-unlock → close position at close
- Source: Keyrock finds stabilization within 14 days; we use 7 as more conservative re-entry
- Total holding period: ~37 calendar days

**Universe filter** (as above): >5% supply, ADV>$5M, team/investor category, top-100 mcap rank

**Sizing**: 1% portfolio per event, max 10 concurrent positions

**Regime filter**: NONE (per L15 lesson — regime overlays on event-driven mechanical signals are not justified)

**Direction**: SHORT ONLY (no long on positive-regime unlocks; focus on the core short edge)

**Cost model**:
- Taker fee: 0.045% per side (HL Tier 0) → 0.09% RT
- Slippage: 0.10% per side on entry + 0.10% exit → 0.20% RT additional
- Total RT cost: **0.29%** per trade
- At 37-day hold, annualized: ~2.86% drag for 100 events × 1% sizing × 2 sides

**Pre-registered threshold** (before data): Success = mean return over [-30, +7] window < -0.30%/day on a per-position basis (net of costs), HAC t-stat < -2.0 at lag=6.

---

## 6. Regime Detection: Why NO Filter (L15)

Per HYPOTHESIS.md §2 rationale: The cliff unlock mechanism is **mechanical and pre-scheduled**. Forced sellers (team members, VCs with lock-up expiry) MUST sell regardless of macro regime. In a positive-regime environment (high liquidity, ETF inflows), the effect may be smaller but still present because:
1. The total supply impact is absolute (same BTC worth of tokens entering market)
2. Institutional investors (VC) are contractually obligated to unlock (they can hedge, but they must unlock)
3. Keyrock documents the effect across bull and bear regimes

The ETF regime overlay (Mission: ETF flows + stablecoin supply) failed because Strategy A's TSMOM signal already self-filters. Event-driven strategies based on KNOWN forced supply events have a different mechanism — no regime overlay needed.

---

## 7. Walk-Forward Design

**Data window**: 2022-01-01 → 2026-05-23 (4.4 years)

**WF structure** (event-driven, larger windows due to sparse events):

| Fold | Train | Test |
|------|-------|------|
| 1 | 2022-01-01 → 2023-06-30 | 2023-07-01 → 2023-12-31 |
| 2 | 2022-01-01 → 2023-12-31 | 2024-01-01 → 2024-06-30 |
| 3 | 2022-01-01 → 2024-06-30 | 2024-07-01 → 2024-12-31 |
| 4 | 2022-01-01 → 2024-12-31 | 2025-01-01 → 2025-06-30 |
| 5 | 2022-01-01 → 2025-06-30 | 2025-07-01 → 2026-05-23 |

**No fitting in train period**: The entry/exit window (T-30, T+7), universe filter (>5%), and sizing (1%) are ALL pre-registered and fixed. Train periods are for warm-up and regime classification ONLY.

**Minimum events per fold**: Need ≥10 events per test period. With 100-200 total events over 4.4 years, each 6-month window should have ~11-23 events. Borderline for folds 1-3, acceptable for 4-5 (2024 peak unlock season).

---

## 8. Cost Model

**Position sizing**: 1% of portfolio per event, max 10 concurrent shorts

**Cost per trade** (conservative):
```
fee_per_side = 0.045%        # HL Tier-0 taker
slip_entry   = 0.10%         # slippage on T-30 short entry
slip_exit    = 0.10%         # slippage on T+7 cover
total_rt     = 0.29%         # fee + slippage (RT)
```

**At 100 events/year × 1% sizing × 0.29% RT**:
- Annual cost drag = 100 × 0.01 × 0.0029 = **0.29%** annualized
- This is very low cost drag (vs the strategy's expected gross return of -15% to -25% on team unlocks)

**Concurrent position risk**: With max 10 concurrent events × 1% sizing = 10% max short exposure. The remaining 90% earns a cash rate (negligible in crypto, modeled as 0).

**Gross expected return** (from Keyrock):
- Team unlocks >5%: avg -25% over ~37 days = -0.68%/day gross
- Investor unlocks >5%: less clear, but still negative pressure
- Blended expectation (mix of team + investor): -15% to -25% per event gross
- With 0.29% RT cost per event: net expected -14.7% to -24.7% per event over 37 days

---

## 9. Stop Conditions

| Condition | Action |
|-----------|--------|
| CryptoRank free API AND manual approach both unavailable | STOP — archive "paid data required: Tokenomist $49-450/mo; DeFiLlama $300/mo" |
| Universe filter produces < 30 events/year after filtering | STOP — L12 floor violation |
| Universe filter produces > 500 events/year after filtering | STOP — L12 ceiling; cost drag domination |
| Phase 2 IC: mean daily return > -0.30%/day (not negative enough) | STOP — edge not measurable |
| Phase 2 HAC t-stat > -2.0 | STOP — statistically insignificant |
| Phase 3 Sharpe HAC NET < 0.7 | Archive — RESEARCH_FAIL |
| Phase 3 MaxDD > -25% | Archive — tail risk exceeds gate |
| Phase 4 Sharpe 2024-2026 sub-period < 0 | Flag — Empirica-style inversion may apply |
| 2 tests consumed (after Phase 2 + Phase 3) | Automatic stop |

---

## 10. GATE 0 — HARD STOP

Bootstrap complete. Data source decision required before Phase 1 can proceed.

**User action required**: Choose ONE of:

1. **Option A** (preferred): Sign up for free CryptoRank API key at `cryptorank.io/public-api`. Test if `GET https://api.cryptorank.io/v1/currencies/{symbol}/vesting?api_key=YOUR_KEY` returns historical unlock events back to 2022. If yes → reply "GO PHASE 1 — CryptoRank API". I will build the full data pipeline.

2. **Option B** (fallback): Authorize manual curated dataset (50 top tokens, known vesting schedules from public documentation). Survivorship bias acknowledged and documented. Reply "GO PHASE 1 — manual curated, survivorship bias accepted". I will build the dataset from scratch (~4-6h effort).

3. **Option C** (stop): "STOP — paid data, archive." I will archive with lesson L16 (token unlock event data not freely accessible for historical backtesting at scale).

**Without explicit GO + data source choice, no Phase 1 will proceed.**
