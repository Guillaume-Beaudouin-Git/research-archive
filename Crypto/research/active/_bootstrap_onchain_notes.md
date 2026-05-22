# On-Chain Alpha Research Bootstrap
*Date: 2026-05-23 | Phase: 0 | Status: GATE 0 — AWAITING "GO PHASE 1"*

---

## 0. Constraints Inherited (Lessons 11/12 + V1/V2 Postmortems)

- **Lesson 11 (β-dominance)**: Long-only CS crypto → corr(A) ≈ 0.80-0.85 regardless of signal IC. Only escape: delta-neutral execution OR very selective infrequent positioning.
- **Lesson 12 (event ceiling)**: Gate BOTH floor (< 50/yr → underpowered) AND ceiling (> 500/yr → cost overflow at taker). At maker execution, ceiling is de facto higher (~2000/yr for fills), but sparse signal power matters — OAGF failed t-stat at 128 events/yr.
- **PMR lesson**: IC can be real (t=2.86) and the strategy still fails if event rate × taker cost >> IC gross edge.
- **OAGF lesson**: IC direction correct (−0.19) but t_HAC=−1.17 because only 128 events/yr → 10 years needed to reach t=2.5. Sparse event-driven signals die on t-stat.
- **Strategy B Sharpe = 2.0** (not 9.64) for all portfolio gate computations.
- **n_tests = 151** | Budget: 151 → 156 max (+5). Hard stop.

---

## 1. Data Source Landscape (Verified 2026-05-23)

### CoinMetrics Community API
**URL**: `https://community-api.coinmetrics.io/v4/timeseries/asset-metrics`
**Auth**: None required | **Rate limit**: 10 req / 6s (1.67 RPS)

Verified free-tier metric availability per token:

| Token | AdrActCnt | TxCnt | CapMrktCurUSD | CapMVRVCur | FlowInExUSD | FlowOutExUSD | Notes |
|-------|-----------|-------|--------------|-----------|-------------|--------------|-------|
| ETH   | ✓ (2015) | ✓     | ✓            | ✓         | ✓           | ✓            | 31 metrics |
| LINK  | ✓ (2017) | ✓     | ✓            | –         | –           | –            | 22 metrics |
| UNI   | ✓ (2020) | ✓     | ✓            | –         | –           | –            | 22 metrics |
| AAVE  | ✓ (2020) | ✓     | ✓            | –         | –           | –            | 22 metrics |
| MKR   | ✓ (2017) | ✓     | ✓            | –         | –           | –            | 17 metrics |
| SOL   | –        | –     | –            | –         | –           | –            | Price only |
| JUP   | –        | –     | –            | –         | –           | –            | Price only |
| PYTH  | –        | –     | –            | –         | –           | –            | Price only |

**CRITICAL**: SOL, JUP, PYTH have NO on-chain metrics in CoinMetrics free tier — only price reference rates.
**NVTAdj/NVTAdj90**: PAID tier. Can compute pseudo-NVT = CapMrktCurUSD / TxCnt (transaction count proxy, not transfer value).

### Etherscan API
**URL**: `https://api.etherscan.io/api`
**Auth**: Free API key (no cost) | **Rate limit**: 5 calls/sec, 100k calls/day
**Coverage**: Full Ethereum mainnet history from genesis
**Available**: ERC20 token transfers, transaction history per address, contract events (logs), gas prices
**Use case**: Direct on-chain query for ETH ecosystem — more granular than CoinMetrics but requires more parsing

### Solana RPC (Helius free tier)
**URL**: `https://mainnet.helius-rpc.com/?api-key=<FREE_KEY>`
**Auth**: Free API key via helius.dev | **Rate limit**: 10 RPS (shared, ~1M credits/month)
**Available**: `getSignaturesForAddress`, `getTransaction`, token transfers via SPL token program
**Use case**: SOL, JUP, PYTH on-chain activity — viable but pipeline complexity HIGH (parse raw transaction data, identify SPL transfers, deduplicate)
**Estimate**: Building 2yr history for SOL + 2 SPL tokens = ~3-5 days of development + significant rate limit management. This is the "pipeline overhead > 30% of time" warning signal.

### Dune Analytics
**Rate limit**: 2.5k credits/month free — one heavy SQL query ≈ 500 credits → ~5 queries/month
**Verdict**: NOT viable for automated research pipeline. Manual exploration only.

### Glassnode Free Tier
**Rate limit**: Shared with web dashboard, daily resolution only
**Verdict**: Insufficient for research. NVT, MVRV, exchange flows all behind paid tier.

---

## 2. Universe Adjustment

The mission-specified 8-token universe cannot be uniformly covered with free on-chain data:

| Tier | Tokens | On-Chain Coverage | Source |
|------|--------|-----------------|--------|
| **A (full)** | ETH | 31 metrics, full history 2015 | CoinMetrics free |
| **B (partial)** | LINK, UNI, AAVE, MKR | AdrActCnt + TxCnt + market cap, 2017-2020+ | CoinMetrics free |
| **C (blocked)** | SOL, JUP, PYTH | Price only — on-chain requires Solana RPC pipeline | Helius (buildable, expensive in dev time) |

**Recommended approach**: Use Tier A+B (5 ETH-ecosystem tokens) for IC testing. Note SOL/JUP/PYTH exclusion explicitly. If Phase 1 passes IC with N=5, consider whether Solana RPC pipeline extension is warranted before Phase 3 — this is a GO/NO-GO decision at Phase 2 based on pipeline overhead assessment.

---

## 3. Five On-Chain Signal Categories

### Category 1: Active Address Count Momentum
**Signal**: `addr_zscore = (AdrActCnt - MA_90d) / std_90d` → positive z → user adoption surge
**Hypothesis**: Metcalfe's Law proxy — network value ∝ active users². Address surges reflect genuine adoption and tend to precede price discovery by 7-14 days.
**Source**: CoinMetrics Community (free)
**Available for**: ETH, LINK, UNI, AAVE, MKR (N=5)
**Genuinely on-chain**: YES — unique daily addresses transacting on-chain. NOT derivable from OHLCV (price does not determine who transacted).
**IC horizon**: 7-21d
**Corr(A) risk**: MODERATE (0.25-0.45). Address surges correlate with bull markets. But the lead-lag relationship (addresses lead price) is structurally distinct from price momentum. Needs empirical verification.
**Corr(B) risk**: NEAR ZERO (B is carry, direction-independent)
**Event count**: Not event-driven — continuous daily signal → no event ceiling concern, but IC measured weekly (5 tokens × 52 weeks ≈ 260 obs/year for cross-sectional IC)

### Category 2: Exchange Netflow (Accumulation Signal)
**Signal**: `netflow_pct = (FlowOutExUSD - FlowInExUSD) / CapMrktCurUSD` for ETH
**Hypothesis**: Exchange outflows = tokens moving to cold storage, removing sell liquidity. Large outflows precede price appreciation over 7-14 days.
**Source**: CoinMetrics Community (free, ETH only)
**Available for**: ETH only (Tier B tokens don't have exchange flow data in free tier)
**Genuinely on-chain**: YES — requires tracking labeled exchange wallet addresses on-chain.
**IC horizon**: 7-14d
**Corr(A) risk**: MODERATE (0.20-0.40). Outflows occur during accumulation which may co-occur with early-stage momentum. But can also occur in bear market consolidation → potentially lower corr(A) than address momentum.
**Corr(B) risk**: NEAR ZERO
**Universe limitation**: ETH only → time-series IC (N=1 asset, T=~700 weekly obs)

### Category 3: MVRV (Market Value / Realized Value)
**Signal**: `mvrv_zscore = (CapMVRVCur - MA_365d) / std_365d` for ETH
**Hypothesis**: MVRV high → current holders have large unrealized gains → profit-taking pressure → negative forward return. Counter-cyclical to TSMOM.
**Source**: CoinMetrics Community (free, ETH only)
**Available for**: ETH only in free tier
**Genuinely on-chain**: YES — Realized Value requires tracking each coin's acquisition price on-chain (UTXO cost basis for BTC, account-based tracking for ETH). Genuinely non-OHLCV.
**IC horizon**: 14-30d (slow-moving, structural signal)
**Corr(A) risk**: LIKELY NEGATIVE (MVRV mean reversion is counter-trend). If A is long when price is rising (high MVRV), and MVRV predicts negative return, then corr(A,MVRV_strategy) < 0 → beneficial for orthogonality. Verify empirically.
**Corr(B) risk**: NEAR ZERO
**Universe limitation**: ETH only → time-series IC. Can apply as market-timing on 8-token basket.

### Category 4: Stablecoin Supply Change (Capital Inflow Proxy)
**Signal**: Net USDC/USDT minting on Ethereum mainnet (Etherscan event logs)
**Hypothesis**: New stablecoin issuance = new capital entering crypto ecosystem → bullish for ETH ecosystem tokens over 7-21d.
**Source**: Etherscan API (USDC contract: `0xA0b86991...`, USDT: `0xdAC17F95...`, Transfer from address 0x0 = mint)
**Genuinely on-chain**: YES — stablecoin minting is purely on-chain, completely independent of crypto OHLCV.
**Pipeline complexity**: Moderate. Need to: query Etherscan logs for mint events, aggregate daily, normalize.
**Corr(A) risk**: POTENTIALLY HIGH (0.35-0.55). Stablecoin minting correlates with bull markets — more capital enters when sentiment is positive. May be partially a lagging indicator of the same regime that drives A.
**Corr(B) risk**: LOW
**Concern**: Likely OHLCV-correlated enough to fail orthogonality gate. Requires empirical test.

### Category 5: Protocol-Level Activity (DeFi Metrics)
**Signal**: Token-specific transaction activity, smart contract interaction count
**Examples**: AAVE borrow/supply volume changes (Etherscan event logs), UNI DEX volume (Etherscan logs)
**Hypothesis**: Surge in protocol usage → fee revenue up → token value up over 14-30d (fundamental, not momentum)
**Source**: Etherscan event logs (complex parsing of contract ABIs)
**Genuinely on-chain**: YES — smart contract interaction data is purely on-chain.
**Pipeline complexity**: HIGH. Each token needs: ABI decoding, specific event signature hashing, pagination through potentially millions of events.
**Corr(A) risk**: MODERATE (DEX/lending volume surges during momentum regimes)
**Warning**: Pipeline overhead likely > 30% of sprint time for even 2-3 tokens. Violates the overhead gate in mission attitude.

---

## 4. Two Preselected Angles

### Angle 1 (RECOMMENDED): Cross-Sectional Active Address Momentum
**Why this angle over others**:
- Widest cross-sectional coverage: 5 tokens (N=5 cross-section, 260+ obs/year)
- Lowest pipeline complexity: single CoinMetrics API call, no Etherscan parsing
- Clear Metcalfe's Law economic mechanism — academically studied (Liu & Tsyvinski 2021 find on-chain user growth predicts crypto returns with t > 3 over 1-month horizon)
- History depth: ETH 2015, LINK/MKR 2017, UNI/AAVE 2020 → cross-sectional IC available from 2020 (first year all 5 tokens coexist)
- Not a Lesson 11 β-dominance trap: signal is NOT based on price or OHLCV, and can fire with low or negative price momentum (new users in accumulation)
- Lesson 12 event-count: N/A (continuous signal, not event-driven)

**Signal (fixed ex-ante)**:
```python
addr_zscore[t] = (AdrActCnt[t] - AdrActCnt.rolling(90d).mean()[t]) / AdrActCnt.rolling(90d).std()[t]
```
Long ranking: coins with highest addr_zscore get positive weight; delta-neutral execution (long top 2, short bottom 2 of 5 tokens) to address β-dominance.

**IC test**: Cross-sectional SpearmanR(addr_zscore, fwd_14d_ret) weekly, N=5 tokens, T=~150 weekly periods (2020-2026)

**Expected corr(A)**: 0.25-0.40. Address momentum correlates with price momentum in trending regimes, but diverges during accumulation and distribution phases.

**Key risk**: If corr(A) > 0.50 empirically → FAIL (orthogonality gate). This is the binding gate.

---

### Angle 2 (ALTERNATIVE): ETH MVRV + Exchange Netflow Composite
**Why this angle**:
- MVRV is the most theoretically orthogonal to A (counter-cyclical, mean-reverting)
- Exchange netflow is purely on-chain accumulation signal
- Both available for ETH with full history (2015)
- Neither requires Etherscan parsing (CoinMetrics pre-computes both)

**Signal (fixed ex-ante)**: Composite score for ETH market-timing:
```python
mvrv_z[t]     = (CapMVRVCur[t] - MA_365d[t]) / std_365d[t]          # high = expensive
netflow_z[t]  = (FlowOutExUSD[t] - FlowInExUSD[t]) / SplyExUSD[t]   # positive = accumulation
composite[t]  = netflow_z[t] - 0.5 * mvrv_z[t]                       # bullish minus overvaluation
```
Applied as a binary long/flat market-timing signal on ETH (and by extension the correlated DeFi basket).

**IC test**: Time-series SpearmanR(composite[t], fwd_14d_ETH_ret[t+1])
- N=1 (ETH), T=~700 weekly periods (2015-2026) → enough statistical power if IC t > 2.5

**Expected corr(A)**: 0.10-0.25 (MVRV is counter-trend; netflow is regime-uncertain). Likely lower than Angle 1.
**Expected corr(B)**: Near zero.
**Universe limitation**: ETH-only signal. Applied to DeFi basket via ETH correlation, not token-specific.

**Key risk**: Single-asset IC is more susceptible to ETH-specific regime changes. No cross-sectional diversification.

---

## 5. Data Pipeline Architecture

### Core Design
```
CoinMetrics Community API (1.67 RPS)
    → rate_limited_fetcher.py  (token bucket, retry-with-backoff)
    → cache/onchain/{asset}/{metric}.parquet  (column-by-metric, date index)
    → incremental_update()  (only fetch from last_cached_date → today)
    → onchain_universe.py  (assemble cross-sectional DataFrame)
```

### Rate Limit Strategy
CoinMetrics: 1.67 RPS = 10 requests per 6 seconds.
For 5 tokens × 5 metrics × 2 years = ~14,600 daily rows: 1 API call with `assets=eth,link,uni,aave,mkr&metrics=AdrActCnt,TxCnt,CapMrktCurUSD&start_time=2020-01-01` → returns all tokens in one call → **≤ 5 API calls total for initial bootstrap**. Rate limiting is trivial.

Incremental updates (daily): 1 API call per day → negligible.

### Etherscan (if needed for Angle 2 extension)
Etherscan: 5 calls/sec, 100k/day. For USDC mint events: 1 call/block range (~2000 blocks/call at Etherscan event log pagination). ~500 calls for 2 years of history. Feasible but requires parsing.

### Solana RPC (if needed for SOL/JUP/PYTH extension)
Helius 10 RPS. For active address count on SOL: must iterate `getSignaturesForAddress` for a sample of active addresses + aggregate. This is a multi-day pipeline project. **Recommendation: defer until Phase 1 passes with 5-token ETH universe.**

### Cache Strategy
```
data/onchain/
├── cache/
│   └── coinmetrics/
│       └── eth_link_uni_aave_mkr_daily.parquet  ← merged, one file
└── raw/  ← gitignored
```
Parquet because: columnar (fast per-metric slicing), compressed, pandas-native. No pickle (non-reproducible across Python versions).

### Failure Modes
- **API 403 on specific metric**: metric not in free tier → log + remove from request, don't fail pipeline
- **429 rate limit**: exponential backoff 2s → 4s → 8s, max 3 retries
- **Missing dates in CoinMetrics**: forward-fill max 3 days (holiday gaps), flag longer gaps
- **Token not in free tier** (SOL): raise DataNotAvailableError, not silent skip

---

## 6. Pipeline Overhead Assessment

| Task | Estimated dev time |
|------|--------------------|
| CoinMetrics fetcher + cache (5 tokens, 5 metrics) | 1-2h |
| IC pre-flight script | 1-2h |
| Backtest engine (vectorized, 5 tokens) | 2-3h |
| **Total (Angles 1 or 2)** | **4-7h** |
| Solana RPC extension (SOL/JUP/PYTH) | **+2-3 days** — DO NOT proceed unless IC passes first |

Pipeline overhead is within bounds (<30% of sprint). Solana extension is the threshold violation risk.

---

## 7. N_tests Budget Accounting

| Event | Tests | Cumulative |
|-------|-------|-----------|
| Session start | — | 151 |
| Phase 2 IC test (1 horizon = 1 test) | +1 | 152 |
| Phase 3 backtest iter_01 | +1 | 153 |
| Phase 3 iter_02 (if Phase 3 fails with clear diagnosis) | +1 | 154 |
| Phase 3 iter_03 (final) | +1 | 155 |
| Phase 4 DSR/bootstrap (validation, not new test) | +0 | 155 |
| **Remaining at RESEARCH_PASS** | +1 (portfolio sensitivity) | **156 = hard limit** |

**At budget limit**: Any additional angle = ARCHIVE + STOP. No negotiation.

---

## GATE 0

**STOP. Awaiting "GO PHASE 1".**

Pending user decision:
1. **Which angle to advance**: Angle 1 (Active Address Momentum, 5-token cross-sectional) or Angle 2 (ETH MVRV + Exchange Netflow, time-series)
   - My recommendation: **Angle 1** — cross-sectional N=5 gives more statistical power per year; active address data academically validated (Liu & Tsyvinski 2021)
2. **Universe decision**: Proceed with 5 ETH-ecosystem tokens (SOL/JUP/PYTH deferred until IC passes) or force inclusion of SOL via Helius pipeline (adds 2-3d dev time)
3. **Delta-neutral execution**: Angle 1 long/short design (top 2 vs bottom 2 of 5 tokens, delta-neutral) vs long-only with β-dominance risk. Recommend delta-neutral to respect Lesson 11.
