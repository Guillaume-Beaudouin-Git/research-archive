# Open Auction Gap Fade (OAGF) — Hypothesis V2
*Date: 2026-05-23 | Phase: 1 — Hypothesis + IC Pre-flight*
*n_tests_start: 148 | Status: IN PROGRESS*

---

## 1. Strategy Name and ID

**Strategy OAGF** (Open Auction Gap Fade)
Research slot: 6.40 (first test will increment n_tests to 149)

---

## 2. Hypothesis

**At each 8h funding settlement (0:00, 8:00, 16:00 UTC), the first 1h of price action in HL perps contains a predictable mean-reversion component driven by post-settlement order flow unwinding.**

### Mechanism

At 8h funding settlement, longs pay / shorts receive funding proportional to the funding rate. Participants who are adversely positioned (paying significant funding) face a cost event. Some fraction of them:
- Close positions immediately post-settlement → directional price pressure
- Reopen at better prices 30–60 min later → reversal toward pre-settlement price

The net effect: a gap forms at the settlement bar open (price moves directionally in response to funding imbalance). Over the next 1h, as post-settlement flow completes and the pressure exhausts, price reverts toward the pre-settlement level.

**Signal**: gap_ret = (open_t − close_{t-1}) / close_{t-1}, measured on the bar that opens immediately after each 8h settlement timestamp.

**Entry**: ALO limit order placed AT close_{t-1} (opposite to gap direction). If price reverts to close_{t-1}, order fills. If gap extends further, ALO cancels → zero cost, zero PnL. This is an embedded option: the strategy only executes when the reversion occurs.

**Hold**: 1h exactly (one 1h bar). Exit at bar close via limit or taker.

---

## 3. Signal Definition (Fixed Ex-Ante)

```
settlement_hours = {0, 8, 16}  # UTC

# For each coin c, each settlement bar t:
gap_ret[c, t] = (open[c, t] - close[c, t-1]) / close[c, t-1]

# Position direction (fade the gap):
signal[c, t] = -sign(gap_ret[c, t])   # +1 if gap down, -1 if gap up

# Entry condition (threshold FIXED ex-ante):
trade[c, t] = (|gap_ret[c, t]| > GAP_THRESHOLD) ? signal[c, t] : 0

GAP_THRESHOLD = 0.003  # 0.30% — chosen to filter noise, ex-ante
```

**No tuning of GAP_THRESHOLD permitted.** If IC fails at 0.30%, archive. Do not try 0.20% or 0.40%.

---

## 4. IC Pre-flight Test

### Metric
Spearman IC: rank correlation of gap_ret[c, t] with fwd_1h_ret[c, t], computed across all (coin, settlement_bar) pairs.

```
IC = SpearmanR(gap_ret, fwd_1h_ret)
```

Expected sign: **negative** (gap up → next 1h returns negative; gap down → next 1h returns positive).

HAC t-statistic (lag = 6 for 1h settlement data: roughly captures 8h autocorrelation):
```
t_HAC = IC_mean / SE_HAC
```

### Data
- Universe: top 30 HL perps by open interest (same as V1 preflight)
- Period: Jan 2024 → May 2026 (≈28 months)
- Frequency: 1h OHLCV for HL perps (public endpoint)
- Settlement bars: filter to bars where hour ∈ {0, 8, 16} UTC
- N potential: 30 coins × 28 months × ~30 days × 3 settlements/day ≈ 75,600 (coin, bar) pairs

### Gates (pre-flight)

| Gate | Threshold | Rationale |
|------|-----------|-----------|
| IC t-stat | ≥ 2.5 | Minimum statistical significance |
| |IC| value | ≥ 0.04 | Minimum economic magnitude |
| Event count at 0.30% threshold | 50–5000/year (total) | Floor: signal too sparse. Ceiling: n/a for maker (unfilled = zero cost) |
| corr(OAGF_daily, B_daily) | < 0.50 | Relaxed orthogonality constraint V2 |
| corr(OAGF_daily, A_daily) | < 0.50 | Same |

**On the event-count ceiling**: Lesson 12 ceiling gate (> 500/year → cost overflow) applies to TAKER execution only. For ALO maker execution, unfilled events have zero cost. The binding metric is FILLED events (= IC events where gap reverts to entry). Ceiling gate is therefore: filled events < 2000/year (practical position management limit), not based on potential events.

### Pass/Fail Decision
- **PASS** (→ Phase 2): IC t ≥ 2.5, |IC| ≥ 0.04, both corr thresholds met
- **FAIL** (→ Archive + postmortem): any gate not met
- **No iteration**: if IC is 2.3, this is a FAIL, not a reason to try a different threshold

---

## 5. Orthogonality Analysis

### Expected corr(OAGF, B)
- B (delta-neutral carry) earns funding through time — returns are driven by funding rate level
- OAGF earns from 1h price reversion — returns are driven by gap magnitude and reversion speed
- Structural overlap: near-zero. Different mechanisms, different holding periods (8h funding period vs 1h gap trade)
- Expected |ρ| < 0.20 based on mechanism. Verify empirically in pre-flight.

### Expected corr(OAGF, A)
- A (TSMOM) is 28-day momentum, weekly rebalance — completely different frequency and mechanism
- OAGF is intraday 1h counter-trend — anti-correlated in mechanism
- Expected |ρ| < 0.15. Verify empirically.

### Why OAGF Passes β-Dominance Test (Lesson 11)
- OAGF is not long-only: it fades gaps in both directions (buys gap-downs, shorts gap-ups)
- Long and short legs are roughly symmetric (depends on funding regime: if longs always pay, gaps are mostly downward → slightly more buys than shorts, but not strongly unidirectional)
- Portfolio β_crypto will be near zero by construction of the fade mechanism
- No need for explicit delta-neutral hedging: the strategy is naturally balanced

---

## 6. Cost Model (Maker-Native)

### Per-trade costs (taker cost corrected: 0.045% base HL tier 0)
```
fill_rate    = 0.70   # fraction of ALO orders that fill (baseline)
maker_rebate = 0.000  # conservative: no rebate (requires MM Elite >$5M vol)
taker_cost   = 0.045% # tier 0 HL, for unfilled → re-enter as taker (not standard)
adverse_sel  = 0.001% # adverse selection on fills

# ALO structure: filled trades pay maker_rebate, unfilled = zero cost
# Exit (1h later): limit order at target; if not filled → taker exit

exit_maker_rate = 0.70  # same fill_rate assumption for exit

Net RT cost per FILLED trade:
= entry_maker_cost + exit_cost + adverse_sel
= 0.000% + (0.70×0.000% + 0.30×0.045%) + 0.001%
= 0.000% + 0.0135% + 0.001%
= 0.014% per RT
```

### Phase 3 sensitivity matrix
| fill_rate | Net RT (conservative, no rebate) |
|-----------|----------------------------------|
| 50% | 0.024% |
| 70% | 0.014% |
| 90% | 0.005% |

**Break-even IC**: at 0.014% net RT cost and 10% vol target, need:
```
IC × vol_per_bar ≥ net_RT / √(positions_per_day)
```
Rough estimate: IC ≥ 0.03–0.05 for 1h bars at typical 2–3% daily vol (≈0.5% per 1h bar).
Gate IC ≥ 0.04 is calibrated to cover costs at baseline fill_rate 70%.

---

## 7. Walk-Forward Design

Per V2 methodology (standard):
- Train: 18 months | Test: 6 months | Step: 3 months
- WF periods from 28m total data: ~3–4 periods (Jan 2024–May 2026)
- WF pass criterion: ≥ 50% of OOS periods show positive Sharpe

No parameter re-optimization across WF folds — signal threshold (0.30%) is fixed ex-ante throughout.

---

## 8. Potential Failure Modes (Pre-mortemed)

| Mode | Diagnosis | Verdict |
|------|-----------|---------|
| IC < 0.04 or t < 2.5 | Gap reversion doesn't exist or is too noisy at 1h | ARCHIVE |
| corr(B) > 0.5 | High-funding regimes: both B and OAGF trade in same direction | ARCHIVE (not path-B: different mechanism, different fix) |
| Fill rate < 30% in simulation | ALO rarely fills: gap extends rather than reverts | ARCHIVE (backtest vs live execution assumption mismatch) |
| IC real but Sharpe negative net cost | IC ≈ 0.04 at edge: margin too thin for cost structure | ARCHIVE — no threshold relaxation |
| WF% = 0% despite positive IS | Regime-specific: gap reversion only in high-funding environments | ARCHIVE — strategy is not robust |

---

## 9. Data Requirements for Phase 2

- HL 1h OHLCV for 30 perps, Jan 2024 → May 2026 (via HL public REST API — same endpoint as V1 preflight)
- HL 8h funding rates (same as V1 preflight — already cached in `_preflight/cache/`)
- Settlement timestamps: reconstruct from funding rate data (each funding rate record = one settlement)
- No paid data required — pure OHLCV + public funding feed

---

## 10. Live Execution Design (Phase 5, if RESEARCH_PASS)

```python
# New method required in hyperliquid_client.py:
def limit_open(self, symbol, side, usd_size, limit_price, tif="Alo"):
    """Post-only ALO order. Returns order_id or None if rejected."""
    ...

def limit_close(self, symbol, side, limit_price, tif="Alo"):
    """Post-only ALO exit. Falls back to market if ALO fails at T+55min."""
    ...
```

Execution timing:
1. T-5min before settlement: compute gap_ret estimate from recent price vs last bar close
2. T+0 (settlement): bar opens, gap_ret observable → place ALO at close_{t-1}
3. T+55min: if ALO not filled → cancel (gap extended, trade missed = correct behavior)
4. T+60min: if ALO filled → exit via ALO at limit; if not filled in 5min → market exit

---

## 11. Phase 1 Deliverables

1. `preflight_oagf_ic.py` — IC test script using HL 1h OHLCV data
2. IC results: t-stat, IC value, event count at 0.30% threshold
3. Orthogonality: corr(OAGF_daily, A), corr(OAGF_daily, B)
4. PASS → update HYPOTHESIS_V2.md with IC results, proceed to Phase 2
5. FAIL → postmortem, archive in `Crypto/research/archived/other/oagf/`

---

## N_tests Accounting

| Event | Tests | Cumulative |
|-------|-------|-----------|
| Prior (V1 complete) | — | 148 |
| Phase 1 IC pre-flight (OAGF) | +3 (3h IC at 1h, 2h, 4h horizons) | **151** |
| Phase 2 backtest (if Phase 1 PASS) | +1 | 152 |

E[max_SR] at N=151: ≈ 4.34 (marginal change from 148).
