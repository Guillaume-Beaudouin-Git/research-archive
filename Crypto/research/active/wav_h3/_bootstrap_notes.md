# Bootstrap Notes — WAV H3 Wikipedia Attention Velocity
*Date: 2026-05-23 | Mission: single-shot IC test, n_tests 158 → 159 max*
*GATE 0 — awaiting "GO PHASE 1"*
*Context: FGVD H1 archived (L17 — existing-holder sentiment = momentum, not contrarian)*

---

## 1. Mission Framing

**Signal hypothesis** (H3 from `sentiment_alpha_deep_dive.md` §7):
Wikipedia pageview spikes for altcoins represent NEW-BUYER DISCOVERY attention — the mechanism from Da, Engelberg & Gao (2011): uninformed retail discovers an asset → buys → temporary price inflation → 2-week reversal. Wikipedia is a purer proxy than Google Trends because (1) absolute counts available (not normalized), (2) history since July 2015, (3) no manipulation possible (bot traffic tracked separately).

**Critical L17 context**: FGVD tested F&G velocity (existing-holder sentiment) → wrong direction (momentum proxy). Wikipedia tests NEW BUYER attention (non-holders looking up an asset for the first time). These are mechanistically different:

| Signal type | Mechanism | Expected IC direction |
|-------------|-----------|----------------------|
| F&G velocity (FGVD) | Existing holders' mood → momentum | WRONG direction (→ archive L17) |
| Wikipedia pageviews | New non-holders discover asset → reversal after 1–2 weeks | Negative IC expected (attention spike → reversal) |

**If H3 also fails** → branche sentiment crypto definitively closed for retail. Lesson L18 would read: "Both existing-holder sentiment (F&G, MVRV) and new-buyer attention discovery (Wikipedia) fail to predict crypto altcoin returns at 7-day daily frequency — the entire sentiment alpha category is saturated or non-existent for retail quant."

---

## 2. Critical Pre-Bootstrap Question: Is Wikipedia Attention Leading or Lagging?

Before designing the signal, we must assess whether Wikipedia attention for crypto altcoins is:

**(a) Leading** (new buyers discover → research → buy → price rises): Da et al. 2011 mechanism  
**(b) Lagging** (price rises → news coverage → curious users research on Wikipedia): momentum proxy

This is an empirical question. The bootstrap flags it as **Alert A** (see §5) and requires a price-lead correlation check in Phase 2:
- Compute `corr(wiki_z_t, price_ret_7d_prior)` for each token
- If this correlation is > +0.3 on average → Wikipedia attention is LAGGING (price drives curiosity) → same failure as MVRV/F&G level → stop early
- If this correlation is near zero → Wikipedia attention is orthogonal to recent price → proceed

The decomposition framework (Tests A/B/C) will empirically resolve this.

---

## 3. Data Architecture

### 3.1 Wikimedia REST API — Pageviews Per Article

**Endpoint** (confirmed live 2026-05-23):
```
GET https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{article}/daily/{start}/{end}
```
- `{article}`: URL-encoded article title (e.g., `Bitcoin`, `Solana_(blockchain_platform)`)
- `{start}`, `{end}`: `YYYYMMDD` format (e.g., `20200101`, `20261231`)
- Maximum date range per request: ~2 years (730 days). For 8-year backtest: 4–5 requests per token.

**Response schema** (confirmed via live test):
```json
{
  "items": [
    {
      "project": "en.wikipedia",
      "article": "Bitcoin",
      "granularity": "daily",
      "timestamp": "2024010100",
      "access": "all-access",
      "agent": "all-agents",
      "views": 10488
    }
  ]
}
```

**Rate limit**: 200 requests/second (as of 2026 rate limit rollout). No API key required. No auth header needed.

**Historical depth**: **Since July 2015** (timestamp 2015070100). Coverage for our 2018-2026 backtest is complete.

**Total API calls needed**: 50 tokens × ~5 date-range requests = ~250 calls. Trivial at 200 req/s.

**Bot traffic**: The `agent=all-agents` parameter includes bots. Using `agent=user` excludes automated crawlers. We will use `all-agents` (consistent with most academic studies) but document this choice. For altcoins with very low traffic (< 50 views/day), bot traffic may dominate → flag these tokens for exclusion.

**Cache**: Save per-token parquet files to `data/wiki/{token}.parquet`. Index = date, column = views.

### 3.2 BTC/Altcoin Price — Yahoo Finance

For altcoin prices: `yfinance.download(['{TOKEN}-USD', ...], start='2018-01-01', auto_adjust=True)`. BTC-USD already cached from FGVD mission at `Crypto/research/archived/other/fgvd_h1/data/btc_price_raw.parquet` (reuse).

**Issue with yfinance altcoin coverage**: Some tokens may have incomplete history or incorrect data on yfinance. If yfinance fails for a token:
- Primary: try `{TOKEN}-USDT` pair (some tokens only have USDT pairs)
- Fallback: skip token (exclude from universe)

Validate: drop tokens where yfinance returns < 365 days of history before the analysis window.

### 3.3 Universe: Token → Wikipedia Article Mapping

**Pre-registered mapping** (40 tokens identified with high-confidence Wikipedia articles):

| Ticker | Wikipedia Article | Notes |
|--------|------------------|-------|
| SOL | `Solana_(blockchain_platform)` | Confirmed exists |
| BNB | `BNB_(cryptocurrency)` | Check disambiguation |
| XRP | `XRP_(cryptocurrency)` | Formerly Ripple, article renamed |
| ADA | `Cardano_(blockchain_platform)` | Confirmed exists |
| AVAX | `Avalanche_(blockchain_platform)` | Likely exists |
| DOGE | `Dogecoin` | Confirmed exists |
| DOT | `Polkadot_(cryptocurrency)` | Confirmed exists |
| MATIC/POL | `Polygon_(blockchain)` | Confirmed exists |
| TRX | `TRON_(cryptocurrency)` | Confirmed exists |
| LINK | `Chainlink_(blockchain)` | Confirmed exists |
| LTC | `Litecoin` | Confirmed exists |
| ETC | `Ethereum_Classic` | Confirmed exists |
| BCH | `Bitcoin_Cash` | Confirmed exists |
| XLM | `Stellar_(payment_network)` | Confirmed exists |
| ATOM | `Cosmos_(blockchain)` | Confirmed exists |
| SUI | `Sui_(cryptocurrency)` | Check if exists |
| APT | `Aptos_(blockchain)` | Check if exists |
| NEAR | `NEAR_Protocol` | Confirmed exists |
| FIL | `Filecoin` | Confirmed exists |
| ICP | `Internet_Computer` | Confirmed exists |
| VET | `VeChain` | Confirmed exists |
| ALGO | `Algorand` | Confirmed exists |
| EOS | `EOS.IO` | Confirmed exists |
| ZEC | `Zcash` | Confirmed exists |
| XMR | `Monero` | Confirmed exists |
| DASH | `Dash_(cryptocurrency)` | Confirmed exists |
| AXS | `Axie_Infinity` | Confirmed exists |
| MANA | `Decentraland` | Confirmed exists |
| SAND | `The_Sandbox_(video_game)` | Check disambiguation |
| GRT | `The_Graph_(database)` | Check disambiguation |
| WLD | `Worldcoin` | Probably exists |
| BAT | `Basic_Attention_Token` | Confirmed exists |
| COMP | `Compound_(DeFi_protocol)` | Probably exists |
| EGLD | `MultiversX` | Check |
| INJ | `Injective_Protocol` | Probably stub |
| CRO | `Cronos_(blockchain)` | May not exist |
| ZIL | `Zilliqa` | Confirmed exists |
| WAVES | `Waves_(cryptocurrency)` | Confirmed exists |
| ONT | `Ontology_(blockchain)` | Check |
| ICX | `ICON_(cryptocurrency)` | Check |

**Auto-validation step in Phase 1**: For each token, fetch a 7-day sample from Wikimedia API. If response is 404 → article doesn't exist → exclude. If avg views < 50/day → too low traffic → exclude. Expected valid universe: 30–45 tokens.

**Stablecoins excluded by definition** (USDT, USDC, DAI, BUSD — no price signal).
**BTC, ETH excluded** per mission spec (too dominant, macro-driven, separate universe from altcoins).

### 3.4 Universe ADV Filter

Altcoin ADV > $5M on Binance or ByBit is a required filter per deep_dive H3 spec. For tokens in the pre-registered list:
- All top-50 market cap tokens comfortably exceed $5M ADV
- The filter mainly excludes micro-caps that might have Wikipedia stubs
- CoinGecko API free tier provides `total_volumes` in the `market_chart` endpoint — but this is daily, not hourly. Use 30-day average daily volume from yfinance volume column × price as proxy.

---

## 4. Signal Specification (Pre-Registered, LOCKED)

**Formula** (from deep_dive §7 H3, verbatim, H3a only per mission lite):

```python
# Raw 7-day and 60-day pageview windows
pageviews_7d(t, i)       = sum(views[t-6 : t])   # 7-day total for token i
pageviews_60d_avg(t, i)  = mean(views[t-59 : t])  # 60-day rolling average daily views

# Attention signal per token (log-ratio of 7d total vs expected from 60d avg)
attention_raw(t, i) = log(pageviews_7d(t, i)) - log(7 * pageviews_60d_avg(t, i))

# Cross-sectional z-score (at each date t, across universe)
attention_z(t, i)   = (attention_raw(t, i) - mean_i(attention_raw(t))) / std_i(attention_raw(t))

# H3a: contrarian signal (high attention → reversal)
# signal = attention_z directly
# entry condition: attention_z(t-1, i) > +1.5 → short token i (attention spike → reversal)
# exit: T+7 calendar days
```

**Note on formula**: `log(7 * pageviews_60d_avg)` converts the 60-day average to a 7-day expected total, making both sides of the log-ratio in the same units (7-day totals). This ensures `attention_raw ≈ 0` when actual 7-day matches the expected baseline.

**LOCKED**: 7-day window, 60-day average, cross-sectional z-score, threshold +1.5 for top-quintile short entry. No alternatives.

**Holding period**: 7 calendar days (same as FGVD, Da et al. 2011 mechanism).

---

## 5. Three Methodological Alerts (Pre-Registered)

### Alert A — Wikipedia Attention May Be Lagging (Not Leading)

**Risk**: The dominant direction of causality in crypto may be: price rises → news coverage → Wikipedia edits/views increase. This would make Wikipedia attention a LAGGING indicator of price (same as MVRV, F&G level) — a momentum proxy, not a reversal signal.

**Evidence for concern**: Da et al. 2011 documents SVI spike PRECEDES price in equities. The reversal mechanism works because SVI represents NEW uninformed buyers BEFORE they buy. In crypto, by the time a token shows up on Wikipedia, it has often ALREADY spiked in price (the news/price action drives the Wikipedia traffic, not vice versa).

**Mitigation**: The decomposition test (Test A vs Test B vs Test C) will empirically distinguish. If `corr(wiki_z, price_ret_7d_prior) > 0.3` → Wikipedia is lagging → D1 decomposition rule fires → STOP.

**If Lagging is confirmed**: This produces Lesson L18: "Wikipedia attention for crypto altcoins is a lagging indicator of price, not a new-buyer discovery signal — the causality direction is reversed from Da et al. 2011 equity mechanism."

### Alert B — Low Traffic Variance on Altcoin Pages

**Quantitative concern**: Bitcoin Wikipedia page gets ~10,000–25,000 views/day. Mid-cap altcoins (SOL, ADA tier) might get 200–2,000 views/day. Small altcoins (COMP, ZIL tier) might get 20–200 views/day.

At 50–200 views/day with ±1σ daily noise of ~±30% (Poisson approximation: σ ≈ √mean → for 100 views: σ ≈ 10 → 10% noise), the 7-day sum has ~3.6% noise. A genuine "attention spike" of 2× normal = log(2) = 0.69 signal, against ~0.04 noise → SNR ≈ 17. But if most days show no spike, the IC across all dates will be diluted by the 95%+ of "normal attention" days.

**Expected signal frequency**: If genuine attention spikes (≥1.5σ above 60d baseline) occur ~10% of the time per token per year = 36 events/year/token × 40 tokens = 1,440 cross-sectional signal observations/year → above the L12 floor. But most cross-sectional "signals" will be noise, with a few genuine discoveries.

### Alert C — corr(wiki_z, GT_z) Potential Redundancy

**Risk**: Wikipedia pageviews and Google Trends may capture the same information (same retail discovery behavior, just measured at different points in the discovery funnel). If `corr(wiki_z, google_trends_z) > 0.7` → these are the same signal.

**Mitigation**: We do NOT have Google Trends data in this mission (would require pytrends fetching across 40 tokens = rate-limit challenge). We'll flag this as a known theoretical concern but won't test it in Phase 2 (would require additional data).

**Implication**: Even if WAV works, it may be extractable more cheaply via Google Trends (better documented, more signal variance for popular tokens). This is a future research note, not a stop condition.

---

## 6. Decomposition Test Design (L17-Inspired)

Three parallel IC tests on same window 2018-01 → 2026-05, cross-sectional (all tokens simultaneously):

| Test | Signal | Expected IC (H3a) |
|------|--------|------------------|
| A | `−price_velocity_7d_z(t)` (cross-sectional price MR) | IC < 0 (price MR, baseline) |
| B | `attention_z(t)` (WAV) | IC < 0 (contrarian) |
| C | `attention_z(t) - price_velocity_7d_z(t)` (combined) | IC < 0 (enhanced) |

**Decision rules** (pre-registered, same structure as FGVD but adapted for positive attention_z signal):

**D1 (Price MR dominates WAV)**: If `|IC_A| ≥ 0.5 × |IC_B|` → Wikipedia attention does not add independent contrarian information beyond price mean-reversion. STOP.

**D2 (WAV has independent value)**: If `|IC_B| ≥ 0.3 × |IC_A|` AND `|IC_B| > |IC_A|` → Wikipedia provides independent contrarian signal beyond price MR. PROCEED.

**D3 (Wikipedia void)**: If `|IC_B| < 0.01` → Wikipedia attention has no predictive power at all. STOP.

**D4 (Wrong direction, momentum proxy)**: If `IC_B > 0` (positive IC = attention spike predicts continuation) → Wikipedia is a momentum proxy, not contrarian. STOP, archive with L18.

**Additional check**: `corr(attention_z, price_ret_7d_prior)` — if > +0.3 on average across tokens → Wikipedia is lagging price → same failure as MVRV → STOP D4.

---

## 7. Walk-Forward Design (Phase 3 only — if Phase 2 passes)

**CS context**: With 40 tokens × daily observations, the CS IC has substantially higher effective N than the FGVD time-series test. Expected annual signal events: ~1,440 (40 tokens × 36 events/yr). Much higher statistical power.

**WF folds** (18-month train / 6-month test):

| Fold | Train | Test | Expected events |
|------|-------|------|-----------------|
| 1 | 2018-01 → 2019-06 | 2019-07 → 2019-12 | ≈720 |
| 2 | 2018-01 → 2020-06 | 2020-07 → 2020-12 | ≈720 |
| 3 | 2018-01 → 2021-06 | 2021-07 → 2021-12 | ≈720 |
| 4 | 2018-01 → 2022-06 | 2022-07 → 2022-12 | ≈720 |
| 5 | 2018-01 → 2023-06 | 2023-07 → 2023-12 | ≈720 |
| 6 | 2018-01 → 2024-06 | 2024-07 → 2024-12 | ≈720 |
| 7 | 2018-01 → 2025-06 | 2025-07 → 2026-05 | ≈840 |

Events per fold is high (720+) → WF is well-powered. RESEARCH_PASS gate: Sharpe HAC NET > 0.7, MaxDD > −25%, WF pass rate > 50% (4+/7 folds).

---

## 8. N_tests Accounting

| Event | Δ Tests | Cumulative |
|-------|---------|-----------|
| Start of WAV mission (Phase 0) | 0 | 158 |
| Phase 2 IC block (Tests A+B+C combined) | +1 | 159 |
| **BUDGET EXHAUSTED** | — | 159 |

No iterations. No threshold tuning. If H3a IC gate fails → archive definitively. No H3b sub-test (skipped per mission lite spec).

---

## 9. GATE 0 — HARD STOP

Bootstrap complete. Signal formula, universe design, and decomposition rules are locked.

**No data fetched yet. No IC tested.**

Upon "GO PHASE 1":
1. Write `HYPOTHESIS_WAV.md` (pre-registration)
2. Write `fetch_data.py` (Wikimedia per-token + yfinance altcoin prices)  
3. Write `analysis_phase2.py` (signal + Tests A/B/C + decomposition + orthogonality)
4. Execute universe validation (verify all 40 tokens have valid Wikipedia articles + avg > 50 views/day)
5. Run IC analysis, report results
6. Archive with L17/L18 or proceed to Phase 3

Reply **"GO PHASE 1"** to proceed.
