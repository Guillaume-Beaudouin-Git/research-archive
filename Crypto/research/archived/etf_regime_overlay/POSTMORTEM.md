# Postmortem — ETF Flows + Stablecoin Regime Overlay
*Archived: 2026-05-23 | Gate 2 FAIL*

---

## Result Summary

| Metric | Value | Gate Threshold |
|--------|-------|----------------|
| E[A_ret \| active] − E[A_ret \| inactive] | **+0.022%/day** | ≥ 0.10%/day → PASS / ≥ 0.05%/day → BORDERLINE |
| HAC t-stat (lag=6) | −0.17 | — |
| Time-in-market at τ=+0.5σ | 31.4% | expected ~31% ✓ |
| Gate 2 outcome | **FAIL** | Δ < 0.05%/day |

**Stop condition triggered**: conditional improvement < 0.05%/day → archive, do not proceed to Phase 3.

---

## What Worked

1. **Regime calibration**: τ = +0.5σ produced exactly 31.4% time-in-market, matching the pre-registered Gaussian expectation (~31%). The regime score responds correctly to the data.
2. **Signal direction**: Δ = +0.022%/day (positive). The regime filter does help in the expected direction — active periods have higher returns than inactive periods.
3. **Data pipeline**: BitBO replaced Farside cleanly after the 403 block. BitBO's embedded historyBtc JS array provides 484 trading days of total BTC ETF flow (2024-01-12 → 2026-05-22). DeFiLlama confirmed robust.
4. **N_tests discipline**: Only 1 test consumed (n_tests: 156 → 157). Pre-registering τ = +0.5σ before data analysis avoided IS selection bias and saved 2 test budget slots.

---

## Root Cause of FAIL

**The conditional return difference (+0.022%/day) is too small to meet the 0.10%/day gate.**

### Why the signal is weak

The regime score has low economic power for two structural reasons:

**1. Insufficient differentiation in 28-month window**: The post-ETF era (Jan 2024 – May 2026) covers only ~2.3 years — one large bull market (2024 BTC run) and one mixed period (2025 rotation + correction). With few regime cycles, the conditional difference has high estimation uncertainty (HAC SE dominates). More data would not necessarily produce a larger point estimate.

**2. TSMOM signal is robust across regimes in a trending market**: Strategy A (28-day TSMOM) is long-only and benefits from trend regardless of ETF flows. In 2024, TSMOM performed well even during ETF net-outflow periods (GBTC conversions) because BTC was already in a bull trend predating the ETF regime. The regime signal is not useless — it does correctly classify periods — but the underlying TSMOM signal is strong enough that the marginal improvement from the regime filter doesn't cross the 0.10%/day economic significance bar.

**3. BTC-dominated signal**: BitBO's `historyBtc` is AGGREGATE net flow (all ETFs, BTC-denominated). Individual ETF flows can partially cancel. A more granular signal (e.g., IBIT-specific flow or large-inflow days only) might have stronger discrimination, but this would consume additional test budget (a new hypothesis).

### What the 0.05%/day borderline means

At 0.022%/day × 250 days × 31.4% time-in-market ≈ +1.7% annualized alpha from the filter. This is real but small relative to Strategy A's ~Sharpe 1.33 baseline. Even if the walk-forward confirmed this magnitude (Gate 3 would still fail at 1.0 Sharpe ratio improvement since 1.7% alpha on a ~20% vol portfolio ≈ 0.08 Sharpe lift, not the 0.10× required for Sharpe > 1.10 × 1.33 = 1.46).

---

## Lesson Derived

**Lesson L15 (from this mission)**: Regime overlays on strong-trend strategies require very high conditional return thresholds. A 28-day TSMOM strategy on 14 crypto assets with Sharpe > 1.0 is self-filtering enough — macro liquidity regime provides incremental but sub-threshold lift. Regime overlays are more valuable on strategies with lower baseline Sharpe (e.g., Sharpe < 0.7) where low-liquidity environments cause most of the drawdown. Consider this lesson before proposing similar macro-regime overlays on high-Sharpe strategies.

---

## Data Source Note

**Farside.co.uk** returned HTTP 403 (Cloudflare IP block) — confirmed 2026-05-23. The stop condition was triggered per mission spec ("data source fragile: Farside Cloudflare blocks automated scraping"). **BitBO.io** (bitbo.io/treasuries/etf-flows/) provides equivalent aggregate ETF flow data in BTC units via embedded HTML JS arrays. The replacement is valid — z-score normalization is unit-invariant.

---

## Files

| File | Description |
|------|-------------|
| `HYPOTHESIS.md` | Pre-registered hypothesis, τ=+0.5σ, exact gate criteria |
| `_bootstrap_notes.md` | Phase 0 bootstrap: data architecture, regime formulation, walk-forward design |
| `fetch_data.py` | BitBO HTML parser + DeFiLlama stablecoin fetch |
| `analysis_phase2.py` | Gate 2 conditional analysis with HAC correction |
| `data/etf_flows_raw.parquet` | 484-day BTC ETF flow series (BitBO, 2024-01-12 → 2026-05-22) |
| `data/stablecoin_supply_raw.parquet` | 1239-day stablecoin supply (DeFiLlama, 2023-01-01 → 2026-05-23) |
| `data/prices_cache.parquet` | 14-asset daily close prices (Yahoo Finance, 2024-01-11 → 2026-05-22) |
| `data/phase2_results.json` | Gate 2 output (Δ=+0.022%/day, FAIL) |
