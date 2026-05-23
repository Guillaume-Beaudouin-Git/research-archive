# Hypothesis — ETF Flows + Stablecoin Regime Overlay on Strategy A
*Pre-registered: 2026-05-23 | Threshold locked before any data analysis*
*n_tests: 156 → 157 (+1 for Phase 2 IC measurement at pre-registered τ)*

---

## 1. Hypothesis Statement

Post-ETF approval (January 2024), the combination of net BTC ETF flows and stablecoin supply growth rate constitutes a measurable macro liquidity regime for crypto markets. Periods of positive regime (both flows and stablecoin supply above their rolling 30-day baseline) are associated with higher conditional Strategy A returns than periods of negative regime. Filtering Strategy A long-only positions to only activate during positive liquidity regime improves risk-adjusted performance.

**Falsifiable success criterion**: `Sharpe(A_filtered) / Sharpe(A_unfiltered) > 1.10` on OOS walk-forward, computed at τ = +0.5σ.

---

## 2. Theoretical Mechanism

Strategy A (TSMOM) holds long positions in trending crypto assets. Its signal (tanh of 28-day return z-stat) is strongest in sustained uptrend regimes. In low-liquidity macro environments — net ETF outflows signal institutional de-risking; stagnant stablecoin supply signals no new capital entering crypto — momentum signals are more likely to trigger on exhausting rather than initiating trends. The regime filter acts as a macro-liquidity gate: it does not predict BTC direction, it identifies whether the environment supports trend continuation.

**Mechanism is non-circular**: The regime score uses ETF flows and stablecoin supply (macro liquidity proxies, not price-derived) rather than any price signal. It is therefore structurally uncorrelated with the TSMOM signal, which uses only OHLCV.

**Key prior**: BIS WP 1087 (Schmeling et al. 2023) documents that crypto carry strategies have significantly different risk-return profiles in high vs low funding regimes. The analogous hypothesis here is that macro crypto liquidity regimes (proxied by ETF flows + stable supply) condition TSMOM performance.

---

## 3. Pre-Registered Threshold: τ = +0.5σ

**Threshold**: regime is considered "active" when `regime_score(t-1) > +0.5`

**Pre-registration rationale** (per Bailey & López de Prado, Multiple Testing in Finance):

1. **Sweet spot for binary regime filter**: Under a Gaussian assumption, τ = +0.5σ corresponds to approximately 31% time-in-market. This lies between: τ = 0 (50% time-in-market, insufficient discrimination between favorable and unfavorable regimes) and τ = +1.0σ (16% time-in-market, too selective — sacrifices too much exposure to genuine trending regimes at the cost of variance reduction).

2. **Filter intent is asymmetric**: The objective is to suppress "clearly unfavorable" environments, not "neutral" ones. Positive but weak liquidity (regime_score ∈ [0, +0.5]) should not trigger the filter; only clearly negative regimes (regime_score < +0.5) warrant suppressing Strategy A. A threshold above zero, but not aggressively high, achieves this.

3. **IS Selection Bias prevention**: Testing τ ∈ {0, +0.5, +1.0} and selecting the best-performing threshold in-sample requires DSR adjustment for 3 simultaneous tests. Pre-registering a single τ before any data analysis removes this adjustment requirement, consuming only 1 test instead of 3, and avoids the Winner's Curse. This approach follows the pre-registered replication methodology of Harvey (2017, *CFA Research*).

**This threshold will not be changed** after any data analysis. Post-hoc threshold changes would convert this into an IS selection exercise.

---

## 4. Exact Regime Score Formulation

All operations use data strictly available at T-1 (computed from closes through day T-1, applied at T open).

```
# Input series (daily, calendar-aligned to Strategy A trading dates)
net_flow(t)     = sum of all BTC ETF daily net flows in US$M (Farside)
supply(t)       = total stablecoin circulating supply in USD (DeFiLlama /stablecoincharts/all)

# Signal smoothing
flow_7d(t)      = Σ_{k=0}^{6} net_flow(t-k)                     # 7-day rolling sum
Δstable_7d(t)   = (supply(t) - supply(t-7)) / supply(t-7)        # 7-day growth rate

# Z-score normalization (rolling 30-day, min_periods=20)
flow_z(t)       = (flow_7d(t) - μ_{30d}(flow_7d)) / σ_{30d}(flow_7d)
stable_z(t)     = (Δstable_7d(t) - μ_{30d}(Δstable_7d)) / σ_{30d}(Δstable_7d)

# Composite regime score
regime_score(t) = 0.5 × flow_z(t) + 0.5 × stable_z(t)

# Overlay indicator (T-1 regime score applied at T)
regime_active(t) = [regime_score(t-1) > +0.5]  # Boolean → {0, 1}

# Filtered signal
signal_A_filtered(t) = signal_A(t) × regime_active(t)
```

**Design choices fixed ex ante**:
- Equal weighting 0.5/0.5: no optimization; both components are theoretically equal-priority proxies for the same underlying variable (crypto market liquidity)
- 7-day smoothing: standard weekly aggregation, avoids single-day noise from settlement flows
- 30-day z-score window: captures medium-term regime shifts (2–4 week momentum) without 3-12 month persistence that would trigger L12b autocorrelation deflation
- GBTC included: use `net_flow_all` as primary signal; `net_flow_ex_gbtc` as robustness check in Phase 2 only (not a new threshold test)

**No fitting in this design**: the regime score is a deterministic transformation of raw data. There are no parameters to optimize, no lookback to tune, no weights to fit. The threshold τ is the only degree of freedom and it is pre-registered.

---

## 5. Overlay Architecture

```
# Crypto/research/active/etf_regime_overlay/engine.py

# Import Strategy A signal logic — NO modification to live code
from strategies.tsmom_v2_propfirm.signal import compute_signal, apply_weekly_rebalance
from strategies.tsmom_v2_propfirm.config import LOOKBACK_DAYS, REBALANCE_WEEKDAY

TAU = 0.5  # pre-registered threshold — do not change

def apply_regime_overlay(
    prices_df: pd.DataFrame,
    regime_score: pd.Series,
    tau: float = TAU,
    vol_target: float = 0.18,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (signal_filtered, signal_unfiltered). Same vol-target for both."""
    signal_A = compute_signal(prices_df, lookback=LOOKBACK_DAYS)
    weekly_A = apply_weekly_rebalance(signal_A, rebalance_weekday=REBALANCE_WEEKDAY)
    # Regime score at T-1; reindex to signal dates; fill gaps forward (weekend/holiday)
    regime_t1 = regime_score.reindex(weekly_A.index, method="ffill").shift(1)
    regime_active = (regime_t1 > tau).fillna(False).astype(float)
    signal_filtered = weekly_A.multiply(regime_active, axis=0)
    return signal_filtered, weekly_A
```

The overlay is multiplicative: `signal_A_filtered = signal_A × regime_active`. When regime is inactive, all 14 assets are set to zero exposure (no positions). When active, Strategy A runs unmodified.

---

## 6. Walk-Forward Structure

**Data window**: 2024-01-11 (first ETF trading day) → 2026-05-23 (~28 months)

| Fold | Train window | Test window | Notes |
|------|-------------|-------------|-------|
| 1 | 2024-01-11 → 2024-12-31 | 2025-01-01 → 2025-06-30 | 12m train |
| 2 | 2024-01-11 → 2025-03-31 | 2025-04-01 → 2025-09-30 | 15m train |
| 3 | 2024-01-11 → 2025-06-30 | 2025-07-01 → 2025-12-31 | 18m train |
| 4 | 2024-01-11 → 2025-09-30 | 2026-01-01 → 2026-05-23 | 21m train (partial test) |

**No fitting in train period** — the overlay has no parameters to optimize. The 12m minimum train period provides signal warm-up (30d z-score requires 37 calendar days; 28d TSMOM lookback adds another 28 days → 65 days minimum warm-up, well within 12m).

Primary comparison in each fold: `Sharpe(A_filtered) / Sharpe(A_unfiltered)`.

---

## 7. Gate Definitions

**Gate 1 (this document)**: Design is defensible — pre-registered threshold, fixed formulation, clear mechanism, no retroactive optimization. PASS.

**Gate 2 (Phase 2 — conditional analysis)**:
- `E[A_return | regime_active] - E[A_return | regime_inactive] > 0.10%/day`
- HAC-corrected (lag-6); regime_active defined at τ = +0.5σ
- If FAIL (< 0.05%/day): archive, do not proceed to Phase 3
- If BORDERLINE (0.05–0.10%/day): flag for user decision before Phase 3

**Gate 3 (Phase 3 — walk-forward)**:
- `Sharpe(A_filtered) / Sharpe(A_unfiltered) > 1.10` on OOS WF
- `MaxDD(A_filtered) ≤ MaxDD(A_unfiltered) + 5%` (filter must not worsen tail)
- Time-in-market reported explicitly — a ratio > 1.10 achieved purely by variance reduction (same returns, fewer days in market) is flagged

**Gate 4 (Phase 4 — robustness)**:
- DSR > 0 with n_tests = 157
- Threshold sensitivity: Sharpe ratio > 1.05 at τ ∈ {+0.25, +0.75} (i.e., ±0.25σ from pre-registered τ)
- Sensitivity check is a robustness test, not a new hypothesis; no additional n_tests consumed

---

## 8. N_tests Accounting

| Event | Tests | n_tests after |
|-------|-------|--------------|
| Prior research | — | 156 |
| Phase 2 IC measurement (this hypothesis, τ = +0.5σ) | +1 | 157 |
| Phase 3 WF (same hypothesis, same τ) | 0 | 157 |
| Phase 4 robustness (sensitivity ±0.25σ, DSR) | 0 | 157 |
| **Total budget** | **+1** | **157** |

Saves 2 tests vs testing all 3 thresholds — reserved for Token Unlocks mission if this passes.

---

## 9. Stop Conditions (carried from bootstrap)

| Condition | Action |
|-----------|--------|
| Farside returns 403 with correct headers | STOP — archive "data source fragile" |
| Gate 2 conditional improvement < 0.05%/day | STOP — archive |
| Gate 2 conditional improvement 0.05–0.10%/day | FLAG — user decision before Phase 3 |
| Phase 3 Sharpe ratio < 1.05 | ARCHIVE |
| Phase 3 MaxDD(filtered) > MaxDD(unfiltered) + 5% | ARCHIVE (even if Sharpe ratio > 1.10) |
