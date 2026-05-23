# Postmortem — WAV H3 Wikipedia Attention Velocity
*Archived: 2026-05-23 | GATE 2 (D4) FAIL — IC_B positive, Wikipedia = momentum proxy*

---

## Result Summary

| Metric | Value | Gate | Verdict |
|--------|-------|------|---------|
| Universe (N tokens) | **21** | ≥ 20 → PASS | GATE 0 PASS |
| Lagging corr (wiki_z vs price_prior) | **+0.102** | ≤ 0.30 → PASS | GATE 1 PASS |
| IC_B (WAV standalone) | **+0.00158** | < 0 (D4) → **FAIL** | GATE 2 STOP |
| t_HAC_B | +0.156 | — | — |
| IC_A (−price MR) | +0.01283 | — | momentum direction |
| t_HAC_A | +1.407 | — | — |
| IC_C (combined) | +0.02143 | — | positive (momentum-amplified) |
| t_HAC_C | +2.172 | — | — |
| Events/year (attention_z > +1.5) | 343 | — | high frequency |
| corr(attention_z, TSMOM-28d) | −0.022 | < 0.5 → PASS | orthogonal |
| D4 fires | **True** | STOP | archive L18 |
| Final verdict | **GATE 2 FAIL (D4)** | Archive | |

n_tests consumed: **158 → 159** (+1 for combined A/B/C Phase 2 block, pre-registered).

Panel: 21 tokens, 3063 dates, 2018-01-01 → 2026-05-21.

---

## What Worked

1. **Existence-check-first API strategy**: Fixed a critical data pipeline bug where historical
   404s (article didn't exist yet) were misidentified as article non-existence. The two-step
   approach (recent-data existence check → historical fill with 404-as-empty) correctly
   separated 17 truly non-existent articles from articles with short history.

2. **Lagging gate passed (GATE 1)**: `corr(attention_z, price_ret_7d_prior) = +0.10`. Wikipedia
   attention is NOT a pure lagging indicator of price. The correlation is significantly below
   the 0.30 threshold. This rules out the most naive failure mode: "people Google after price
   spikes." Wikipedia attention is partially orthogonal to recent price.

3. **Decomposition framework (D4 pre-registration)**: By pre-registering D4 ("if IC_B > 0 →
   momentum proxy → STOP"), the failure mode was identified immediately without any temptation
   to adjust the threshold or test alternative windows. IC_B = +0.00158, t = +0.16 is not just
   wrong-direction — it's essentially zero, with the tiny positive residual being noise.

4. **Orthogonality**: `corr(attention_z_mean, TSMOM_28d) = −0.022`. Wikipedia attention is
   structurally uncorrelated with BTC TSMOM. This confirms the signal is not a TSMOM duplicate.
   It simply has no predictive power at all.

5. **Pre-registered universe filters held**: 21 tokens survived all filters (from 38 candidates).
   Many altcoins (ZIL, WAVES, ONT, ICX, etc.) have no English Wikipedia article at all — this
   itself is a finding: Wikipedia coverage for long-tail crypto is thin.

---

## Root Cause of Failure

### 1. Wikipedia Attention Has Zero IC for Crypto Altcoins

**IC_B = +0.00158** is statistically indistinguishable from zero (t = 0.16, effectively a
random walk). Even ignoring direction, there is no predictive signal. The 95% confidence interval
for IC_B around this estimate, even with 2,995 cross-sectional observations, spans roughly
±0.03 — making the true IC compatible with zero at any reasonable significance level.

**D4 fires because**: the tiny positive residual is in the wrong direction. The mechanism
predicts IC_B < 0 (attention spike → reversal). The empirical IC_B ≈ 0 with a slight positive
tilt means: if anything, attention spikes are followed by continuation (momentum), not reversal.
This is directionally consistent with FGVD's L17 finding.

### 2. Price Momentum Signal Is Positive (CS Level, 7-Day)

**IC_A = +0.013** (Test A is *negative* of price velocity, so the underlying price velocity has
IC ≈ −0.013 vs forward returns, i.e., positive momentum at the CS level). The combined signal
(Test C = attention_z − price_vel_z) shows IC_C = +0.021, t = +2.17 — positive and marginally
significant. This is momentum amplification: attention + price both carry marginal positive-IC
momentum signal, which combines to an above-noise positive IC in Test C.

**Implication**: The "combined" signal being marginally significant (t_HAC_C = +2.17) is a
momentum signal, not a reversal signal. The combined test was pre-registered as a contrarian
test (expected IC < 0). Instead, it captures cross-sectional momentum.

### 3. Da et al. 2011 Mechanism Does Not Transfer to Wikipedia

The Da et al. (2011) reversal works because:
  - SVI captures NEW uninformed buyers entering a position
  - They enter at inflated prices → exit within 2 weeks → price reversal

Wikipedia for crypto altcoins does NOT replicate this because:
  - **Crypto buyers don't use Wikipedia for investment decisions** at meaningful scale.
    They use Twitter/X, Reddit, Discord, YouTube, Telegram — not Wikipedia.
  - Wikipedia traffic for crypto is largely informational curiosity (price already spiked → 
    curious non-participants research → no buying pressure → no reversal).
  - The 0.10 lagging correlation confirms partial orthogonality to price, but partial 
    orthogonality ≠ predictive signal in the contrarian direction.

The Da et al. mechanism in 2011 used Google SVI for individual stocks, where retail investors
actively searched tickers BEFORE buying. Wikipedia is read AFTER discovery, often for
fact-checking, not BEFORE investment.

### 4. Universe Thin Coverage — Many Altcoins Have No Wikipedia

17 tokens in the pre-registered universe of 38 failed to even have a valid Wikipedia article:
- BNB, ATOM, SUI, APT, ICP, VET, COMP, EGLD, INJ, CRO, ZIL, WAVES, ONT, ICX (article
  doesn't exist or wrong slug), plus XRP/NEAR with < 730 days and BAT with < 50 avg views.

This structural observation matters: **if Wikipedia coverage is sparse for crypto altcoins,
the "new buyer discovery" mechanism via Wikipedia is unlikely to generate economically
meaningful buying pressure even if some correlation exists.**

---

## Lesson L18 (Confirmed)

**L18**: Wikipedia attention velocity for crypto altcoins produces zero IC (IC_B = +0.00158,
t = +0.16) at 7-day daily cross-sectional frequency. The direction is wrong (positive = momentum)
confirming GATE 2 (D4) failure.

**Mechanistic explanation**:
- Da et al. (2011) requires NEW UNINFORMED BUYERS to use the searched medium for investment
  decisions. This applies to Google SVI for equities in 2011, not Wikipedia for crypto in 2018-2026.
- Crypto buyers use social media (Twitter/X, Reddit, Telegram), not Wikipedia for investment
  discovery.
- Wikipedia traffic for crypto altcoins is informational curiosity by non-participants, not
  pre-investment research by new buyers.
- The lagging correlation (0.10) suggests partial price-driven curiosity traffic, but not enough
  to generate a meaningful contrarian signal.

**Implication for future missions (definitive)**:
- **Do NOT propose contrarian strategies on existing-holder sentiment proxies** (F&G, MVRV,
  SOPR — L17 confirmed).
- **Do NOT propose contrarian strategies on Wikipedia pageview attention for crypto altcoins**
  (L18 confirmed).
- **The sentiment alpha branch for retail crypto altcoins is closed.** Both tested hypotheses
  (H1: FGVD, H3: WAV) failed with IC ≈ 0 in the wrong direction.
- Future sentiment-type work would require: institutional order flow divergence, on-chain
  large-wallet behavior, or developer GitHub activity — not retail discovery proxies.

---

## Data and Files

| File | Description | Reuse? |
|------|-------------|--------|
| `data/wiki/{TOKEN}.parquet` | Wikipedia daily pageviews (21 tokens, full history) | Yes — 8-year daily pageviews, expensive to re-fetch |
| `data/prices/{TOKEN}.parquet` | Altcoin daily close prices (21 tokens) | Yes — clean daily OHLCV 2018-2026 |
| `data/universe.json` | Full exclusion report (38 candidates → 21 valid) | Reference |
| `data/phase2_results.json` | Full IC results, gate evaluation JSON | Reference |
| `fetch_data.py` | Wikimedia API + yfinance/Binance fetcher with caching | Reuse pipeline |
| `analysis_phase2.py` | CS Spearman IC + HAC + lagging gate + decomposition | Template |
| `HYPOTHESIS_WAV.md` | Pre-registration (all gates pre-specified) | Methodology template |

**Wikipedia parquet files are expensive to re-fetch** (38 tokens × 5 Wikimedia API calls each,
with rate limiting). Retain in archive.

---

## Comparison: FGVD H1 vs WAV H3

| | FGVD H1 (L17) | WAV H3 (L18) |
|--|---------------|--------------|
| Signal type | Existing-holder sentiment | New-buyer attention |
| Source | Fear & Greed Index velocity | Wikipedia pageviews |
| IC_B | +0.0085 (wrong direction) | +0.00158 (wrong direction) |
| t_HAC_B | +0.27 | +0.16 |
| Lagging corr | N/A (TS test, not CS) | +0.10 (not lagging) |
| Root cause | F&G = momentum proxy | Wikipedia ≠ investment discovery medium |
| Lesson | L17 | L18 |
| Branch | Existing-holder sentiment CLOSED | New-buyer discovery CLOSED |

**Combined: The entire retail sentiment alpha branch for crypto altcoins is closed at daily frequency.**
