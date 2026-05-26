# POSTMORTEM — CIP EOQ (End-of-Quarter Basis)

**Date archived:** 2026-05-26  
**Status:** KILLED — PMR (Passed Methodology Review, killed by cost ceiling per L11)  
**n_tests consumed:** 0 (killed at feasibility/sigma estimation stage, no IC test run)

---

## Root Cause

The EUR/USD 3M cross-currency basis trade (short basis T-15, close T+5 around quarter-end)  
fails the L11 cost gate by a factor of ×5:

- **Gross capture** post-2020: ~5–10 bps (vs ~40 bps in 2017–2019)
- **Cost 4-jambes** (Saxo retail, spot + forward outright × 2): −6 to −12 bps
- **Net μ per trade**: −3 to +4 bps → effectively zero
- **L11 requirement**: α > 3 × cost_drag = 3 × 8 = 24 bps. Actual α ≈ 5 bps. **Ratio = 0.63 (fails by ×5).**

The σ per trade (17–32 bps from academic literature, vs original assumption 15 bps) is a  
secondary concern — even if σ were correct at 15 bps, the net μ ≈ 1 bps gives SR_annual ≈ 0.13.

## Academic Signal Is Real — Retail Implementation Is Not

The CIP deviation at quarter-end is academically well-documented (Du-Tepper-Verdelhan 2018 JoF;  
Correa-Du-Liao 2022 NBER; Pliszka-Schlam Bundesbank 2025) and structurally driven by G-SIB  
balance sheet window-dressing. The mechanism is real and persistent.

However, it is **institutionally accessible only**: institutions with cross-currency swap  
desks (bid-ask ≤ 1 bps, 2-jambe execution) and Bloomberg EUBSC3 data access can extract  
the edge. Retail implementation requires 4-jambe spot+forward execution with 6–12 bps  
roundtrip — this consumes the entire post-2020 edge and then some.

## Compounding Structural Headwinds (2024–2026)

1. **EU CRR3 (Jan 2025) + Fed Basel III endgame re-proposal (Sept 2024)**: replaces  
   point-in-time G-SIB reporting with daily/monthly averages → directly compresses the  
   window-dressing driver. EUR/USD EOQ basis in Feb 2025 = −1.89 bps (Clarus FT).

2. **CME XEU futures launched Feb 2025**: in principle allows listed basis trading, but  
   ADV effectively zero one year after launch (Tier-2/Tier-3 settlement procedures  
   documented by CME = sessions with zero trades are routine).

3. **Fed/ECB swap lines**: any activation (March 2020, occasional 2023) instantly  
   compresses the basis, killing the hold-period reversion. Non-stationary left-tail risk.

## σ Estimation Findings (This Session)

- Rate-differential proxy (DGS3MO − IRSTCI01EZM156N) is NOT a valid CIP basis proxy.  
  It measures the interest rate differential (200–300 bps in 2017–2019) not the CIP  
  deviation (which stayed at −40 to −65 bps over the same period).
- True σ from academic literature: 17 bps (post-2024 XEURBI era) to 32 bps (post-COVID).
- Original σ=15 assumption: lower tail of plausible range, not central estimate.
- Worst-case intra-hold DD: −90 bps (Mar 2020 COVID), not modelled in original σ=15.

## Lessons

- **L11 arithmetic must use NET μ (after costs), not gross capture.**  
  The feasibility report correctly computed net but the sigma session initially used gross.
- **Retail cost structure for synthetic 4-jambe implementation is the binding constraint**,  
  not the σ or even the mean capture magnitude.
- **The CIP basis series is a useful REGIME INDICATOR** for other strategies  
  (e.g., USD funding stress as a filter for G1 carry or F2 range trades). Keep the  
  data infrastructure.

## Reusable Artifacts

| Artifact | Path | Use |
|----------|------|-----|
| fetch_basis.py | sigma_estimation/ | Fetch synthetic basis proxy (DGS3MO − EUR 3M) |
| validate_basis.py | sigma_estimation/ | QC pipeline, detrending, proxy gap analysis |
| analyze_trade_window.py | sigma_estimation/ | Trade window PnL, σ estimation framework |
| data/synthetic_basis_daily.parquet | sigma_estimation/data/ | 4099 daily obs 2010–2026 |
| data/trade_outcomes.csv | sigma_estimation/data/ | 63 QE windows, proxy PnL |

The code and data are fully reusable as:
1. USD funding stress indicator for regime conditioning in G1/F2
2. Foundation for σ re-estimation if CME XEU futures develop meaningful liquidity

## Trigger for Reconsideration

Two conditions must BOTH be met:
1. CME XEU EUR/USD basis futures ADV > 500 contracts/day with bid-ask < 1 tick (0.5 bps)
2. EUR/USD EOQ CIP spike ≥ 30 bps for ≥ 2 consecutive quarters (Bloomberg XEURBI index)

Neither condition is close to being met as of 2026-05-26.
