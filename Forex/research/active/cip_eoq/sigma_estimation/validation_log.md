# Validation Log — CIP Basis Series
*Generated: 2026-05-26*

## Data Sources Available

| Source | Status | Period | Notes |
|--------|--------|--------|-------|
| CME XEURBI settlement | ❌ NOT FETCHED | 2024-07-27 → today | Behind paywall/no public API |
| Synthetic (rate-diff, ECBDFR-based) | ✅ | 2010-2026 | N=4093 daily obs |
| Synthetic (rate-diff, EURIBOR 3M) | ✅ | 2010-2026 | N=4001, monthly interpolated |
| Academic dataset (Du et al. 2018) | ❌ NOT FETCHED | 2010-2016 | Manual download required |

## Critical Issue: Rate-Differential Proxy vs True CIP Basis

The synthetic basis (rate-diff proxy) measures:
```
  proxy = -(USD_3M_rate - EUR_3M_rate) × 100  [bps]
```

The TRUE CIP basis measures:
```
  cip_basis = r_USD_LIBOR_3M - r_EUR_LIBOR_3M - (F/S - 1) × 4
```

**The rate-diff proxy ≠ CIP basis.** The two diverge massively post-2017:

| Year | Rate-Diff Proxy (bps) | True CIP Basis (bps, lit.) | Gap |
|------|----------------------|---------------------------|-----|
| 2011_eurocrisie | -20 | -30 | +10 |
| 2014_low_rates | -5 | -20 | +15 |
| 2016_post_basel3 | -65 | -55 | -10 |
| 2017_fed_hiking | -150 | -55 | -95 |
| 2018_peak_hiking | -230 | -65 | -165 |
| 2019_prequarter | -250 | -55 | -195 |
| 2020_covid | -80 | -80 | +0 |
| 2023_post_hiking | -140 | -35 | -105 |
| 2024_2026 | -120 | -30 | -90 |

**Cause**: The 2015-2019 Fed hiking cycle pushed USD 3M rates from 0.1% to 2.5% while
EUR 3M rates stayed at -0.4% → 190 bps nominal rate differential. But the true CIP
basis stayed at -40 to -70 bps because the FX forward market CORRECTLY priced this
differential (F/S adjusted accordingly). The proxy confounds rate differential with
CIP deviation.

## Detrended Proxy Analysis

After removing 30-day rolling mean (to isolate QE-specific component):

- N_quarters = 63
- PnL mean = 0.16 bps (proxy measure, lower bound)
- PnL std  = 6.05 bps (proxy σ, lower bound)
- ρ₁ (lag-1 autocorrelation) = -0.361
- N_effective = 134 (Newey-West deflated)

⚠️ The detrended proxy σ is a LOWER BOUND — it only captures rate-diff short-term
variation, NOT the true CIP QE spike (which requires forward rate data).

## Data Requirement for Accurate Sigma Estimation

To measure true σ per trade, we need ONE of:

1. **CME XEURBI settlement prices** (Jul 2024 onwards, available via Bloomberg/Refinitiv)
2. **EUR/USD 3M FX forward outright rates** (daily, Refinitiv, Bloomberg — not free)
3. **Du-Tepper-Verdelhan (2018) replication dataset** (2010-2016, manual download)

In absence of these, σ must be estimated from **academic literature** (see findings).

## Plots Generated

- `figures/basis_3sources_overlay.png`: raw proxy + detrended, QE dates overlaid
- `figures/rate_diff_detrended.png`: 2015-2026 zoom, QE spike check
