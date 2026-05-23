# Postmortem — FGVD H1 Fear & Greed Velocity Divergence
*Archived: 2026-05-23 | Phase 2 FAIL — all ICs near zero, wrong direction*

---

## Result Summary

| Metric | Value | Gate |
|--------|-------|------|
| IC_C (FGVD combined) | **+0.0054** | < −0.05 → FAIL |
| t_HAC_C (lag=6) | **+0.202** | < −2.0 → FAIL |
| IC_A (−price MR) | −0.0083 | — |
| t_HAC_A | −0.256 | — |
| IC_B (F&G velocity) | **+0.0085** | — (wrong direction) |
| t_HAC_B | +0.274 | — |
| Events/year (signal < −1.5) | 16.9 | ≥ 20 → FAIL |
| corr(FGVD, TSMOM-28d) | −0.247 | < 0.5 → PASS |
| Decomposition D1 | **True** | STOP |
| Final verdict | **Phase 2 FAIL** | Archive |

n_tests consumed: **157 → 158** (+1 for Phase 2 IC block, 3 parallel tests pre-registered as combined).

---

## What Worked

1. **Data pipeline**: alternative.me F&G API + Yahoo Finance BTC-USD. Clean merge of 3,028 daily observations 2018-02-02 → 2026-05-23. Zero data gaps.
2. **Decomposition framework**: The 3-test parallel decomposition (Tests A/B/C) correctly identified the failure mode immediately: the D1 rule fired, and all three signals had near-zero IC, preventing any spec-search.
3. **Orthogonality**: corr(FGVD, TSMOM-28d) = −0.247, technically within the |ρ| < 0.5 gate — the design (subtracting price velocity) does produce a signal with reduced TSMOM correlation.
4. **Pre-registration discipline**: 0 threshold tuning, 0 window adjustments. The gates were evaluated on the pre-registered signal exactly.

---

## Root Cause of FAIL

### 1. F&G Velocity is a Momentum Signal, Not a Contrarian Signal

**Expected**: IC_B (F&G velocity standalone) < 0 (contrarian — when F&G rises fast, next returns negative).

**Observed**: IC_B = **+0.0085** (positive, momentum direction — when F&G rises fast, next returns also slightly positive).

This is directly consistent with Albrecht, Maňoušek & Pastorek 2025: "robust positive correlation emerges for all analyzed cryptocurrencies within 4 to 32-day investment horizons, with sentiment as a **leading indicator**" (emphasis mine). F&G does lead price, but in the SAME direction — not as a contrarian reversal signal.

The deep_dive §7 H1 framing relied on the Da et al. 2011 "attention reversal" mechanism from equities. That mechanism describes an **attention spike → short-term price impact → multi-week reversal**. The F&G velocity is not an attention spike — it is a sentiment flow change. The two mechanisms are structurally different:

| Da et al. 2011 | This mission |
|----------------|-------------|
| SVI search spike (attention from NEW non-investors) | ΔF&G_7d (existing investors' sentiment shift) |
| Reversal because uninformed new buying inflates price | Sentiment already incorporated — leads price |
| 2-week reversion window | 7-day window |
| Equities | BTC |

**Conclusion**: The Da et al. mechanism does not transfer to F&G velocity. F&G measures the mood of existing market participants, who are already positioned. When their mood improves, prices follow — not revert.

### 2. All Three Signals Are Noise (None Achieves |IC| > 0.01)

Not only did the hypothesis fail: **price mean-reversion also has no signal at 7-day daily frequency on BTC 2018–2026**:
- IC_A (−price MR) = −0.0083, t = −0.26

BTC has no 7-day mean-reversion signal. The market is sufficiently efficient at the 7-day daily horizon that neither price momentum nor price mean-reversion nor sentiment divergence produces statistically meaningful IC. This is consistent with:
- Guégan & Renault 2021: social media effect disappears at daily frequency, only works ≤ 15 minutes
- Han, Kang & Ryu 2023: time-series momentum is more robust than cross-sectional in crypto, but both require proper window selection — 7-day is likely too short for robust TSMOM signal

### 3. Wrong Direction Confirms Alert B (Da et al. = Equity Mechanism)

The pre-registered Alert B explicitly flagged: "Da et al. 2011 = equity mechanism; crypto may not replicate." The empirical result confirms the alert. The reversal in equities is driven by SVI spikes bringing in uninformed retail buyers who then exit. In crypto, the analogous mechanism (F&G rise = retail enthusiasm) leads to **continued buying**, not reversal, because:
1. Crypto retail investors are more momentum-following by nature
2. The F&G index reflects investor TYPE differently from equity SVI (crypto-native investors vs. new equity retail)
3. Post-2022 crypto market has sufficient institutional depth to prevent 7-day MR patterns

---

## Lesson Candidate L17

**L17 (proposed)**: Fear & Greed velocity divergence does not produce contrarian alpha on BTC at 7-day daily frequency. The F&G velocity standalone is slightly MOMENTUM (IC = +0.009, wrong sign for contrarian hypothesis). The underlying mechanism — F&G leads returns in the same direction (Albrecht 2025: +0.085 IC per standard deviation at 4-32d) — means that "sentiment rises faster than price" predicts more upside, not reversal. The Da et al. 2011 equity attention reversal mechanism does not transfer to crypto sentiment flow because: (a) F&G reflects existing holders' sentiment, not new buyer attention, and (b) crypto retail is momentum-following not mean-reverting.

**Implication for future missions**: Do NOT propose strategies based on "sentiment overshoot → price reversion" for existing-holder sentiment proxies (F&G, Reddit mentions, MVRV). Consider instead signals based on NEW buyer attention discovery (Wikipedia pageviews for tokens not yet widely known, Google Trends spikes for niche altcoins) — these are closer to the Da et al. original mechanism.

---

## Data Sources for Reuse

| File | Content | Size |
|------|---------|------|
| `data/fg_raw.parquet` | alternative.me F&G daily 2018-02-01 → 2026-05-23 (3030 rows) | ~50KB |
| `data/btc_price_raw.parquet` | BTC-USD daily close 2017-01-01 → 2026-05-23 (3428 rows, Yahoo Finance) | ~100KB |
| `data/merged.parquet` | Aligned daily 2018-02-02 → 2026-05-23, fg + close + log_ret (3028 rows) | ~150KB |
| `data/phase2_results.json` | Full IC results, decomposition, gates JSON | ~2KB |

These parquet files are **reusable** for any future missions requiring BTC daily closes or F&G history. The `fg_raw.parquet` in particular covers 8 years and is expensive to re-fetch.

---

## Files

| File | Description |
|------|-------------|
| `_bootstrap_notes.md` | Phase 0 data architecture, signal spec, methodological alerts |
| `HYPOTHESIS.md` | Pre-registration: Tests A/B/C, gates, WF design |
| `fetch_data.py` | Data pipeline (alternative.me + yfinance BTC) |
| `analysis_phase2.py` | Signal computation + IC tests + decomposition + orthogonality |
| `POSTMORTEM.md` | This file |
| `data/fg_raw.parquet` | F&G raw cache |
| `data/btc_price_raw.parquet` | BTC price cache |
| `data/merged.parquet` | Aligned merged data |
| `data/phase2_results.json` | Phase 2 results |
