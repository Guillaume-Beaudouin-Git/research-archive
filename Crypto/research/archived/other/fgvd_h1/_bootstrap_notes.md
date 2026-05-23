# Bootstrap Notes — FGVD H1 Fear & Greed Velocity Divergence
*Date: 2026-05-23 | Mission: single-shot IC test, n_tests 157 → 158 max*
*GATE 0 — awaiting "GO PHASE 1"*

---

## 1. Mission Framing

**Signal hypothesis** (H1 from `Crypto/research/_meta/research/sentiment_alpha_deep_dive.md` §7):
When the Fear & Greed Index changes faster than price (sentiment accelerates beyond price), the excess sentiment is retail FOMO noise — price reverts to fundamentals rather than sentiment catching up. Conversely, when sentiment collapses faster than price (panic overshoot), long entry is contrarian.

**This is NOT**:
- A naive "long when F&G < 20 (fear)" strategy (documented failure: momentum proxy, confirmed in postmortem)
- A level-based overlay on Strategy A (L15: regime overlays on high-Sharpe strategies sub-threshold)
- A signal derived from MVRV or any on-chain price derivative (confirmed FAIL: corr_A = 0.73 per `archived/other/eth_mvrv_netflow/POSTMORTEM.md`)

**This IS**: The DIFFERENCE between normalized sentiment velocity and normalized price velocity. The subtraction explicitly removes the momentum component embedded in F&G construction.

**Pre-registered success criterion (locked before any data analysis)**:
- PHASE 2 IC gate: Spearman IC < −0.05, HAC t-stat (lag=6) < −2.0
- PHASE 3 RESEARCH_PASS: Sharpe HAC NET > 0.7, MaxDD > −25%, WF > 50%

---

## 2. Signal Specification (Pre-Registered, LOCKED)

**Formula** (from deep_dive §7 H1, verbatim):

```python
# Step 1 — 7-day raw changes
delta_fg_7d(t)    = F&G_t - F&G_{t-7}         # absolute change, 0-100 scale
delta_price_7d(t) = log(BTC_close_t / BTC_close_{t-7})  # log return

# Step 2 — Z-score normalization (90-day rolling, unbiased std, min_periods=30)
fg_velocity(t)    = (delta_fg_7d(t) - mean_90d(delta_fg_7d)) / std_90d(delta_fg_7d)
price_velocity(t) = (delta_price_7d(t) - mean_90d(delta_price_7d)) / std_90d(delta_price_7d)

# Step 3 — Divergence signal
fgvd_signal(t)    = fg_velocity(t) - price_velocity(t)

# Step 4 — Entry condition (contrarian, signal at T-1, trade at T)
entry_long(t)     = fgvd_signal(t-1) < -1.5   # panic-overshoot: FG fell >> price fell
exit_long(t+7)    = hold 7 calendar days after entry

# NOTE: signal < -1.5 means F&G has dropped far MORE than price → panic overshoot → long
# signal > +1.5 would be FOMO (FG rose >> price rose) → short → not traded in this mission
```

**Why signal < −1.5 = long (not short)**:
- `fg_velocity < 0` → F&G dropped (sentiment deteriorated)
- `price_velocity ≈ 0` or less negative than sentiment
- Divergence = large negative → panic overshoot → contrarian long
- At signal < −1.5: market is MORE fearful than price decline justifies → reversion expected

**Why no SHORT leg in this mission**:
- Short FOMO (signal > +1.5) requires margin/borrowing; additional risk layer
- Mission lite = single-shot; short-side orthogonality to B (carry) is untested
- IC test covers both directions (Spearman IC measures full signal); the backtest will test long-only for Phase 3

**THRESHOLD LOCKED AT −1.5**: No tuning. If threshold −1.5 fails but −1.0 would pass → this is spec search, archive.

---

## 3. Data Architecture

### 3.1 Fear & Greed Index — alternative.me

**Endpoint**: `GET https://api.alternative.me/fng/?limit=0`

Response format:
```json
{
  "name": "Fear and Greed Index",
  "data": [
    {"value": "45", "value_classification": "Fear", "timestamp": "1716768000", "time_until_update": "..."},
    ...
  ]
}
```

**Coverage**: Daily since **2018-02-01** (confirmed from Farzulla 2026 paper: N=2,896 days as of Jan 2026). May 2026 ≈ 3,000 daily observations.

**Rate limit**: No API key. CORS enabled. Server-side cache 5 minutes. Fetching once per session is sufficient. Excessive automated requests throttled (fair use).

**Parse logic**:
- `timestamp` → Unix epoch seconds → `pd.Timestamp(ts, unit="s").date()`
- `value` → integer (0 = extreme fear, 100 = extreme greed)
- Sort ascending by date, set DatetimeIndex

**Cache**: Save to `data/fg_raw.parquet` after first fetch. Subsequent runs load from cache, append only new dates.

### 3.2 BTC Price — CoinGecko Free API

**Endpoint**: `GET https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=max`

**Coverage**: Daily OHLCV since CoinGecko inception (~2013). F&G starts 2018-02, so usable range = 2018-02-01 → today.

**Rate limit**: Free tier, 5–10 requests/min. `days=max` fetches entire history in one call.

**Parse**: `prices` array `[[unix_ms, price], ...]` → DataFrame. Convert ms to date. Use `Close` = `price` (CoinGecko daily = close/last price at midnight UTC).

**Alternative**: Binance OHLCV API `GET /api/v3/klines?symbol=BTCUSDT&interval=1d&limit=1000` (pagination required for 8 years). CoinGecko is simpler for daily close; Binance is the fallback.

**Cache**: Save to `data/btc_price_raw.parquet`.

### 3.3 Date Alignment

- F&G: UTC midnight timestamp
- CoinGecko: UTC midnight price
- → Natural alignment. Both indexed by `date` (naive date, no tz) after parsing.
- Forward fill F&G for any missing dates (rare). Drop dates with missing price.

### 3.4 TSMOM Signal (Strategy A) — For Orthogonality Check

**Source**: `strategies/tsmom_v2_propfirm/signal.py` → `compute_signal(prices_df, lookback=28)`

**Formula** (read-only reference):
```python
log_returns = np.log(prices_df / prices_df.shift(1))
cum_return = log_returns.rolling(28).sum().shift(1)
vol_L = log_returns.rolling(28).std().shift(1) * np.sqrt(28)
t_stat = cum_return / (vol_L + 1e-8)
signal = np.tanh(t_stat).clip(lower=0.0)
```

**Usage in FGVD**: Compute `tsmom_z(t) = tanh(t_stat_28d)` for BTC only. Then compute `corr(fgvd_signal, tsmom_z)` on the shared sample. Pre-registered gate: |ρ| < 0.5.

---

## 4. Signal Properties Assessment (Pre-Data, Theoretical)

### 4.1 F&G Construction and Momentum Contamination

The alternative.me F&G Index components include price momentum (30-day price change is an explicit input). This means `corr(ΔF&G_7d, Δprice_7d) > 0` by construction — when price rises 10%, F&G tends to rise too.

**Expected contamination magnitude**:
- `corr(delta_fg_7d, delta_price_7d)` ≈ +0.30 to +0.45 (based on MVRV analogy and Albrecht 2025 finding of corr(F&G, 4–32d returns))
- After z-scoring both: `fg_velocity` and `price_velocity` still corr ≈ same value
- **`fgvd_signal = fg_velocity − price_velocity` explicitly subtracts the correlated component**
- Expected residual corr(fgvd_signal, price_velocity) ≈ 0.0 (by construction, since signal = A − B → corr(A−B, B) ≈ corr(A,B) − 1 ≈ 0.40 − 1 = −0.60... )

Wait — this is key. By subtracting price_velocity, the FGVD signal inherits a **negative** correlation with price velocity:
- `corr(fgvd, price_velocity) = corr(fg_vel - price_vel, price_vel) = corr(fg_vel, price_vel) - 1 ≈ 0.40 - 1 = -0.60`

This means the signal is **structurally contrarian to price momentum** — by design. A negative IC (signal < −1.5 → positive forward return) would be consistent with this construction. But it also means the signal is NEGATIVELY correlated with TSMOM (which is long when price_velocity > 0).

**Implication for orthogonality gate**: `corr(fgvd_signal, tsmom_z)` may be NEGATIVE (not just < 0.5). A large negative correlation (e.g., −0.4 to −0.6) is acceptable for orthogonality (gate is |ρ| < 0.5). If |ρ| > 0.5, it means FGVD is essentially a short-TSMOM signal (no independent alpha).

This is a methodological flag to check in Phase 2.

### 4.2 Expected Signal Frequency at Threshold −1.5

Z-score from a roughly normal distribution: P(Z < −1.5) ≈ 6.7%.

Over 8 years × 365 days = 2,920 days × 6.7% ≈ **196 signal days** total.
At an average holding period of 7 days, positions can overlap → effective events ≈ 196 / 7 ≈ 28 independent trades.

**L12 gate check**: 196 signal days / 8 years ≈ 24.5 events/year → above the L12 floor of 20 events/year. ✓ Borderline.

If signal frequency < 20/year after filtering for overlaps → L12 floor violation → STOP.

### 4.3 Expected F&G Autocorrelation

F&G level has AR(1) ≈ 0.90 (daily, highly persistent). The 7-day DIFFERENCE has substantially lower autocorrelation: `AR(1)(ΔF&G_7d) ≈ 0.50-0.70` (persistence drops with differencing). After 90-day z-scoring: `AR(1)(fg_velocity) ≈ 0.30-0.50`.

Effective N for HAC: With AR(1) ≈ 0.40 and N ≈ 2900 obs:
- `N_eff ≈ N × (1 - 0.40) / (1 + 0.40) ≈ 2900 × 0.43 ≈ 1247`
- This is substantially above the 100+ required for t_HAC > 2.0 at IC = 0.05.
- Conclusion: differencing the F&G resolves the autocorrelation problem that killed the Netflow signal (MVRV postmortem: `N_eff ≈ 73` for highly persistent flow signals).

---

## 5. Three Methodological Alerts (Pre-Registered)

### Alert A — Guégan & Renault 2021: "No Economic Profits"

**Verbatim from paper** (Finance Research Letters 38, 2021): "the magnitude of the effect is rather small making it **impossible for a trader to make economic profits** by trading on the information published on social media."

**Context**: This finding is for StockTwits sentiment at 15-minute frequencies (intraday). The signal has ~0.001–0.003% gross per trade at 15-min → sub-cost economically.

**Relevance to FGVD**: The FGVD signal is NOT the same signal (daily divergence vs. intraday level), but the warning applies: even if IC is statistically significant, the economic magnitude may be too small to survive 0.29% RT costs.

**Mitigation**: The 7-day hold period reduces trade frequency → fewer RT cost events per year. Expected ≈ 24 trades/year × 0.29% = 7% annual cost drag on the active portion. With 1% portfolio sizing per trade × 24 trades = 24% of capital touched per year → total cost ≈ 0.24% of total portfolio per year. Very low. But gross edge must exceed this.

### Alert B — Da et al. 2011: Equity Mechanism, Not Crypto

**The foundation of H1**: Da, Engelberg & Gao (2011) document that Google SVI spikes → retail buying → 2-week reversal in S&P 500 stocks.

**Crypto differences**:
1. Crypto retail composition: larger proportion of crypto-native participants vs. equity (where SVI spike = new buyers discovering stocks). Crypto markets may have already incorporated sentiment faster.
2. Crypto "faster metabolism" (Dobrynskaya 2021): momentum decays faster in crypto. A 2-week reversal in equities may translate to a 5-7 day reversal in crypto — aligns with our 7-day exit.
3. Market regime 2022–2026: post-FTX (Nov 2022), post-ETF (Jan 2024) — institutional participation increased. The retail-FOMO mechanism may be weaker in this sub-period.

**Mitigation**: Run Phase 3 stress test for 2022–2026 sub-period specifically (Alert C below).

### Alert C — Post-2022 ETF Regime Change

**Risk**: The 2024–2026 crypto market is qualitatively different from 2018–2021. Bitcoin ETF approval (Jan 2024) brought institutional capital. Institutional actors:
1. Have more resources to trade against retail F&G extremes (faster arbitrage of sentiment divergence → smaller window for retail signal to be tradeable)
2. Ignore F&G Index directly (they use their own models)

**Pre-registered stress test** (not an iteration — documented here before data analysis): In Phase 3 WF analysis, record separately:
- Period 1: 2018-02 → 2021-12 (pre-institutional, retail-dominated)
- Period 2: 2022-01 → 2023-12 (post-FTX, recovery)
- Period 3: 2024-01 → 2026-05 (post-ETF institutional)

If Phase 3 shows clear degradation in Period 3 vs Period 1 (Sharpe drops by >50%) → flag as "structural break — signal may be decaying" even if overall Sharpe > 0.7. This does NOT prevent a RESEARCH_PASS, but it does affect deployment decision.

---

## 6. Walk-Forward Design (Phase 3 only)

| Fold | Train | Test | Expected N events |
|------|-------|------|-------------------|
| 1 | 2018-02 → 2020-06 | 2020-07 → 2020-12 | ≈3 (6m × 24/yr) |
| 2 | 2018-02 → 2021-06 | 2021-07 → 2021-12 | ≈3 |
| 3 | 2018-02 → 2022-06 | 2022-07 → 2022-12 | ≈3 |
| 4 | 2018-02 → 2023-06 | 2023-07 → 2023-12 | ≈3 |
| 5 | 2018-02 → 2024-06 | 2024-07 → 2024-12 | ≈3 |
| 6 | 2018-02 → 2025-06 | 2025-07 → 2026-05 | ≈4 |

**Caveat**: Only ~3 events per 6-month fold. Walk-forward is structurally underpowered for event-driven strategies with 24 events/year. Minimum meaningful WF assessment requires ≥10 events per fold → would need **2+ years per fold** → only 2-3 folds total with 8 years of data.

**Revised WF structure for Phase 3** (only if Phase 2 passes):
- Use ANNUAL test folds (12-month windows) instead of 6-month
- 5 folds: 2019 / 2020 / 2021 / 2022–2023 / 2024–2026
- This gives ≈8 events per fold (24/yr × half the year visible) — still borderline
- WF "pass rate" > 50% gate = 3/5+ folds profitable

**Note**: This is a methodology decision documented here BEFORE Phase 3 code is written, to avoid WF design choice being influenced by results.

---

## 7. Cost Model

| Item | Value |
|------|-------|
| Taker fee (Hyperliquid Tier-0) | 0.045% per side |
| Slippage (BTC spot, market order) | 0.05% per side (BTC is liquid; lower than 0.10% altcoin default) |
| RT cost | 0.19% per trade |
| Position sizing | 1% of portfolio per signal |
| Holding period | 7 calendar days |
| Events/year (expected) | ~24 |
| Annual cost drag | 24 × 0.01 × 0.0019 = **0.046%** of total portfolio |

At 24 events × 1% sizing, only 24% of portfolio capital is "used" per year on this signal (non-concurrent positions, BTC only). Annual cost drag is very low.

**Gross edge required**: With 0.19% RT cost per trade and 7-day hold, the gross return per trade must exceed 0.19% on the deployed 1% position = 0.19% / 0.01 = 19 bps on the 1% position → i.e., the 7-day BTC return on signal days must be > +0.19% on average.

---

## 8. N_tests Accounting

| Event | Δ Tests | Cumulative |
|-------|---------|-----------|
| Start of FGVD mission (Phase 0) | 0 | 157 |
| Phase 2 IC test (FGVD signal, 1 horizon 7d forward, pre-registered) | +1 | 158 |
| **BUDGET EXHAUSTED after Phase 2** | — | 158 |

No iterations, no alternative windows, no threshold tuning. 1 test = Phase 2 IC. Phase 3 backtest does not consume a test (pre-registered, fixed parameters, no fitting).

---

## 9. GATE 0 — HARD STOP

Bootstrap complete. All design decisions are locked.

**No data has been analyzed. The pre-registration above is complete and frozen.**

**Ready to execute Phase 1 (HYPOTHESIS.md) and Phase 2 (data + IC test) immediately upon GO signal.**

User action required: Reply **"GO PHASE 1"** to proceed.

Upon GO:
1. Write `Crypto/research/active/fgvd_h1/HYPOTHESIS.md` (pre-registration, no new design choices)
2. Write `Crypto/research/active/fgvd_h1/fetch_data.py` (alternative.me + CoinGecko)
3. Write `Crypto/research/active/fgvd_h1/analysis_phase2.py` (signal + IC + orthogonality check)
4. Execute and report results
5. If all 4 sub-gates pass → proceed to Phase 3 backtest. If any fail → archive.

**Without explicit GO, no data will be fetched and no analysis will run.**
