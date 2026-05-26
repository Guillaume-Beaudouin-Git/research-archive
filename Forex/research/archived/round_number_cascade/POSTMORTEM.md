# POSTMORTEM — Round Number Stop-Loss Cascade (FX-RNC)

**Archived:** 2026-05-26  
**Research period:** 2026-05-23  
**Stage killed:** IC Feasibility (Phase 1.5) — no backtest run  
**n_tests consumed:** +10 (170 → 180)

---

## 1. Identification

**Hypothesis:** When price breaches a psychologically significant FX level (big-figure .XX00 or
half-figure .XX50 at 50-pip spacing), clustered stop-loss orders execute, generating a cascade
of momentum in the breach direction. Signal: +1 (breach upside), −1 (breach downside). Forward
return expected positive at 1–60 min.

**Literature basis:**
- Osler (2003, *Journal of Finance* 58:4) — order clustering at round numbers documented in
  Citibank proprietary data.
- Osler (2005, *JIMF* 24:2) — stop-loss cascades generate unusually rapid price moves at round
  levels.

**Signal definition (pre-registered):**
- Level: `.XX00` + `.XX50` in 4-decimal EUR/USD convention (50-pip spacing).
- Breach: close-through (close[t] crosses level, close[t-1] does not). No free parameter.
- Direction: momentum (cascade follows breach direction).
- Horizons: 1min, 5min, 15min, 30min, 60min — all pre-registered, all reported.
- Pairs: EUR/USD primary; GBP/USD only if EUR/USD IC > 0 on ≥1 horizon.

**Data:** Dukascopy M1 OHLCV (2020–2024) via Parquet cache in `Forex/data/cache/dukascopy_m5/`.

---

## 2. Verdict: KILL

**Gate failed:** IC Feasibility (both pairs FAIL)  
**Density gate:** PASS — 28,361 EUR/USD events and 41,196 GBP/USD events well above N≥200 floor.
The KILL is not from event sparsity.

**IC verdict:**
- EUR/USD: 9/10 horizons FAIL; only 1min WEAK (t=+1.167, below gate 1.65). Remaining horizons
  trend increasingly negative: 30min t=−2.188, 60min t=−2.357.
- GBP/USD: all 5 horizons FAIL. t_HAC ranges from +0.487 (noise) to −1.976 (negative).
- Hit rates: 48.3%–49.5% across all horizons and pairs — structurally below 50%, consistent
  with slight anti-edge rather than edge-absent noise.

---

## 3. Arithmetic

### EUR/USD IC table

| Horizon | IC_spearman | t_HAC_NW6 | mean_sret (pips) | hit% | Gate |
|---------|-------------|-----------|-----------------|------|------|
| 1min | +0.0019 | +1.167 | +0.0149 | 48.4% | WEAK |
| 5min | −0.0090 | −1.421 | −0.0276 | 49.2% | FAIL |
| 15min | −0.0100 | −1.542 | −0.0406 | 49.3% | FAIL |
| 30min | −0.0132 | −2.188 | −0.0708 | 49.2% | FAIL |
| 60min | −0.0103 | −2.357 | −0.0945 | 49.3% | FAIL |

### GBP/USD IC table

| Horizon | IC_spearman | t_HAC_NW6 | mean_sret (pips) | hit% | Gate |
|---------|-------------|-----------|-----------------|------|------|
| 1min | −0.0114 | +0.487 | +0.0063 | 48.3% | FAIL |
| 5min | −0.0120 | −1.261 | −0.0268 | 48.9% | FAIL |
| 15min | −0.0107 | −1.403 | −0.0406 | 49.2% | FAIL |
| 30min | −0.0103 | −1.976 | −0.0703 | 49.3% | FAIL |
| 60min | −0.0076 | −1.499 | −0.0648 | 49.5% | FAIL |

**Pattern:** IC consistently negative across both pairs at 5min+, with t_HAC approaching statistical
significance in the *anti-momentum* direction at 30–60min. Not edge-absent noise — more likely the
cascade mechanism is HFT-intermediated and exhausted within sub-minute, leaving retail-accessible
horizons with a mild mean-reverting residual.

**EUR/USD per-year breakdown (1min — only horizon with IC > 0):**

| Year | N | IC | t_HAC | hit% |
|------|---|----|-------|------|
| 2020 | 6,564 | +0.0062 | 0.895 | 48.6% |
| 2021 | 4,538 | +0.0011 | 0.968 | 48.3% |
| 2022 | 7,624 | −0.0057 | 0.173 | 48.8% |
| 2023 | 5,415 | −0.0027 | −0.274 | 48.4% |
| 2024 | 4,209 | +0.0167 | 1.598 | 47.6% |

No year reaches t_HAC > 1.65. The cross-year variance is noise-consistent.

---

## 4. Root cause analysis

### Why no edge at retail 1-min resolution?

The Osler (2003, 2005) mechanism operates at the order-book level: stop orders execute as soon as
price *touches* the level intrabar. At 1-min bars, the close-through definition captures only
events where price *stays* above the level at bar close — a subset of the full stop-loss cascade
events. By the time the 1-min close is observed:

1. **HFT arbitrage lag:** HFT participants detect the level breach within microseconds via
   order-flow imbalance and front-run the cascade. The cascade impulse is substantially absorbed
   before the first 1-min close.
2. **Mean reversion residual:** Post-cascade, price faces a liquidity vacuum (all stops
   executed) — typical intrabar pullback produces the slight anti-momentum at 5–60min.
3. **Time elapsed since Osler:** The 2003/2005 papers used Citibank prop data from the late
   1990s/early 2000s — pre-HFT era. The edge may have been genuine then and is now fully
   arbitraged.

### Why density was not the binding constraint?

28k+ EUR/USD events pass the N≥200 gate by two orders of magnitude. Unlike OAGF (128 events/yr
sparse due to threshold), this hypothesis has abundant events — the failure is pure IC direction
and magnitude.

---

## 5. Lessons

No new constitutional lesson warranted. This is a standard IC FAIL:
- **L4** (β-dominance) not relevant — not a long-only CS strategy.
- **L12** (event-count ceiling) not binding — density PASS.
- The correct classification: well-motivated literature-based hypothesis with likely
  HFT-intermediated mechanism, untestable at retail 1-min resolution.

The anti-momentum IC pattern at 30–60min is noteworthy but not actionable — testing the
fade-the-cascade direction would be a distinct hypothesis consuming additional n_tests, and
the effect is small (t=−2.2/−2.4 at 30/60min, not economically significant after 0.15% RT
cost).

---

## 6. Re-evaluation triggers

**Would warrant re-opening:**
1. Access to quote-level (tick/trade) data at sub-second resolution — close-through at 1-min
   is the wrong granularity for the Osler mechanism.
2. New microstructure theory showing retail-accessible persistence of cascade at ≥5min horizon,
   with empirical evidence post-2015 (post-HFT-normalization era).
3. Evidence that algorithm-mediated stop clusters have migrated to non-round levels (e.g.,
   algos concentrate stops at ATR-normalized pivots, not .XX00).

**Does NOT warrant re-opening:**
- Threshold tuning (.XX25/.XX75 inclusion) — not in Osler and consumes new n_tests.
- Adjusting the breach definition (high/low touch vs close-through) — introduces free parameter.
- Testing fade-the-cascade direction — contradicts the pre-registered momentum hypothesis and
  consumes new n_tests.

---

## 7. Decorrelation to existing strategies

Not applicable — no position generated. The strategy was killed at IC feasibility before any
backtest. Strategy C (NQ ORB) and future propfirm strategies are unaffected.

---

## Infrastructure preserved

- `ic_round_number.py` — breach detection + HAC IC engine, reusable for other FX level-based
  hypotheses.
- `PRESPEC.md` — pre-registration methodology frozen 2026-05-23.
- `results_ic.json` — raw IC results.
- Dukascopy M1 parquet cache in `Forex/data/cache/dukascopy_m5/` — reusable for future FX
  intraday research. See `strategy_e_fix_flow/data_setup.py` for fetcher.
