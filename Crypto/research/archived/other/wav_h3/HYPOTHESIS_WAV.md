# Pre-Registration — WAV H3 Wikipedia Attention Velocity
*Locked: 2026-05-23 | n_tests budget: 158 → 159 (+1)*
*This file is PRE-REGISTRATION — no data has been examined at time of writing.*

---

## 1. Hypothesis

**H3a (contrarian)**: Cross-sectional Wikipedia pageview spikes for crypto altcoins predict
7-day forward returns with **negative** IC. Mechanism: new-buyer discovery (Da, Engelberg & Gao
2011) — uninformed retail discovers an asset via Wikipedia → buys → temporary price inflation →
2-week reversal.

**Mechanistic distinction from FGVD (L17)**: FGVD tested existing-holder sentiment (F&G velocity)
which is a momentum proxy (IC_B = +0.0085). Wikipedia tests NEW-BUYER attention — non-holders
researching for the first time. The causality direction is expected to be: discovery → buying
pressure → reversal (not: rising price → rising sentiment).

---

## 2. Signal Specification (LOCKED — no modifications permitted)

```
# Step 1: 7-day rolling pageview total per token
pageviews_7d(t, i) = sum(wiki_views[t-6 : t])       # 7 calendar days, inclusive

# Step 2: 60-day rolling average daily pageviews
pageviews_60d_avg(t, i) = mean(wiki_views[t-59 : t]) # 60 calendar days

# Step 3: Log-ratio attention signal
attention_raw(t, i) = log(pageviews_7d(t, i)) - log(7 * pageviews_60d_avg(t, i))
# = 0 when 7-day actual equals 7-day expected from 60d baseline

# Step 4: Cross-sectional z-score (date t, across all valid tokens)
attention_z(t, i) = (attention_raw(t, i) - mean_i[attention_raw(t)]) / std_i[attention_raw(t)]
```

**Entry condition**: `attention_z(t-1, i) > +1.5` → short token i (attention spike → reversal)
**Exit**: T+7 calendar days (holding period fixed, no early exit)
**Min CS size**: discard dates where < 15 tokens have valid attention_z

---

## 3. Universe (Pre-Registered, 38 Candidates)

**Pre-excluded before runtime validation**:
- SAND: gaming traffic dominates `The_Sandbox_(video_game)`
- GRT: `The_Graph_(database)` polluted by CS searches
- BTC, ETH: macro-driven, outside altcoin cross-section
- Stablecoins (USDT, USDC, DAI, BUSD): no price signal

**Runtime exclusion criteria** (applied in fetch_data.py):
1. Wikipedia article 404 or redirect broken → exclude
2. Available Wikipedia history < **730 days** (2 years) → exclude
3. Average pageviews < 50/day over available history → exclude
4. Price data (yfinance or Binance) < 365 days → exclude

**38 pre-registered candidates** (see `_bootstrap_notes.md` §3.3 for full mapping)

**Expected final universe**: 25–35 tokens

---

## 4. Decomposition Tests (Pre-Registered)

All three tests evaluated on same panel: 2018-01-01 → 2026-05-23, cross-sectional daily.

| Test | Signal | Expected IC under H3a |
|------|--------|----------------------|
| A | `−price_velocity_7d_z(t, i)` (CS z-score of −7d price return) | IC < 0 (price MR baseline) |
| B | `attention_z(t, i)` (WAV signal) | IC < **−0.05** (contrarian, target) |
| C | `attention_z(t, i) − price_velocity_7d_z(t, i)` (combined) | IC < 0 (enhanced) |

Forward return: `fwd_ret_7d(t, i) = log(price[t+7] / price[t])`, computed from T+1 (signal at T-1,
trade at T, forward 7d from T).

IC metric: **Spearman rank correlation** (cross-sectional, per date), mean across dates.

Statistical test: **HAC Newey-West t-statistic (lag=6)** on the time series of per-date ICs.

---

## 5. Evaluation Gates (Ordered — evaluate in sequence, stop at first failure)

### GATE 0 — Data Quality
- Final universe N ≥ 20 tokens with ≥ 730 days Wikipedia history → PROCEED
- If N < 20 → STOP (universe too small for CS IC)

### GATE 1 — Lagging Check (BEFORE IC tests)
- `corr(attention_z_t, price_ret_7d_prior_t)` panel correlation
- If > **+0.3** → Wikipedia lags price → causal direction reversed → STOP
  - Lesson L18: "Wikipedia altcoin pageviews lag price moves in crypto (Kristoufek 2013 replication)"

### GATE 2 — Direction (D4)
- If `IC_B > 0` → attention spike predicts continuation → momentum proxy → STOP + L18

### GATE 3 — Price MR Dominance (D1)
- If `|IC_A| ≥ 0.5 × |IC_B|` → price MR subsumes WAV signal → STOP

### GATE 4 — WAV IC Magnitude (D2)
- **PASS condition**: `|IC_B| > |IC_A|` AND `IC_B < −0.05` AND `t_HAC_B < −2.0`
- If all three sub-conditions met → WAV has independent contrarian value → PROCEED to Phase 3
- Otherwise → STOP

### GATE 5 — Wikipedia Void (D3)
- If `|IC_B| < 0.01` → no signal → STOP (catches near-zero ICs below D4/D1 thresholds)

### GATE 6 — Orthogonality
- `|corr(attention_z, TSMOM_signal_28d)| < 0.5` → PASS (informational, not stop condition)
- If > 0.5 → flag as potentially redundant with TSMOM; include in postmortem

---

## 6. N_tests Accounting

| Event | Δ | Cumulative |
|-------|---|-----------|
| Phase 2 IC block (Tests A+B+C pre-registered combined) | +1 | **159** |

Tests A, B, C counted as **1 combined test** because all three are pre-registered simultaneously
with pre-specified decision rules. No threshold tuning, no window search, no additional iterations.

**BUDGET EXHAUSTED at 159. If FAIL → archive with L17/L18. No H3b.**

---

## 7. Data Sources

| Data | Source | Fallback |
|------|--------|---------|
| Wikipedia pageviews | Wikimedia REST API (no key, free) | None (required) |
| Altcoin prices | yfinance `{TOKEN}-USD` | Binance `/api/v3/klines?symbol={TOKEN}USDT` |
| BTC price (TSMOM) | FGVD cached parquet | yfinance |

Analysis window: **2018-01-01 → 2026-05-23** (limited by Wikipedia coverage of altcoins).
Walk-forward (Phase 3 only): 7 folds, 18-month train / 6-month test, expanding window.

---

## 8. Stop Conditions Summary

| Condition | Gate | Lesson candidate |
|-----------|------|-----------------|
| N < 20 after universe filters | GATE 0 | None (data constraint) |
| `corr(wiki_z, price_prior) > 0.3` | GATE 1 | L18 (lagging proxy) |
| `IC_B > 0` | GATE 2 (D4) | L18 (momentum proxy) |
| `\|IC_A\| ≥ 0.5 × \|IC_B\|` | GATE 3 (D1) | L18 (MR dominates) |
| IC_B ≥ −0.05 or t_HAC_B ≥ −2.0 | GATE 4 (D2) | L18 (insufficient signal) |
| `\|IC_B\| < 0.01` | GATE 5 (D3) | L18 (Wikipedia void) |

**If any stop fires → archive WAV H3. Sentiment branch closed (L18).**
