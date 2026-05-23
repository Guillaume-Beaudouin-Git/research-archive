# POSTMORTEM — London ORB v1 (FX Phase 1.5)

**Archived:** 2026-05-23  
**Research period:** 2026-05-22 → 2026-05-23  
**N_tests consumed:** 28 (16 Angle A + 8 Angle B + 2 dual-pair correlation + 2 data quality variants)  
**N_tests cumulative after archive:** 142 + 28 = 170  

---

## Hypothesis Tested

**Angle A — London Open Range Breakout (ORB-FX)**

Signal: Asian session range (00:00–07:00 UTC) computed from 1-min OHLCV. At London open (07:00 UTC), if price at end of 07:00–07:59 UTC bar BREAKS above the Asian high (or below the Asian low), take a momentum position in the direction of the break. Exit at 1h / 2h / 4h / end-of-session (17:00 UTC).

Tested two signal variants:
- `close_based`: 07:59 UTC close vs Asian range extremes
- `hl_based`: 07:00–07:59 UTC bar high/low vs Asian range extremes

Economic rationale invoked: institutional order flow from EU market open creates directional momentum above/below the Asian equilibrium range.

**Angle B — News-Fade Post-Major-Release**

Signal: ATR-filtered spike detection around NFP/ECB/FOMC/BOE announcements. If spike > 2× ATR(14), fade the direction at T+5min.

Pairs: EUR/USD, GBP/USD  
Data: Dukascopy 1-min OHLCV 2020–2024  

---

## Data Quality

Phase 1.5 v2 fetch (after CONCURRENCY=5 + 0.5s delay + force_close=True fix):

| Pair    | Year | LO fill |
|---------|------|---------|
| EURUSD  | 2020 | 99.9%   |
| EURUSD  | 2021 | 100.0%  |
| EURUSD  | 2022 | 99.9%   |
| EURUSD  | 2023 | 100.0%  |
| EURUSD  | 2024 | 99.8%   |
| GBPUSD  | 2020 | 100.0%  |
| GBPUSD  | 2021 | 99.9%   |
| GBPUSD  | 2022 | 100.0%  |
| GBPUSD  | 2023 | 99.9%   |
| GBPUSD  | 2024 | 100.0%  |

LO fill gate (07:00–08:59 UTC ≥ 95%): ALL PASSED. Data quality not a confounder.

---

## IC Results — Angle A (Phase 1.5 v2)

### EURUSD — close_based (N=489 breakout days)

| Horizon | IC_spearman | t_HAC_NW6 | mean_signed_ret | Gate     |
|---------|-------------|-----------|-----------------|----------|
| 1h      | +0.0564     | +0.39     | +0.0066%        | FAIL     |
| 2h      | +0.0134     | -0.50     | +0.0083%        | FAIL     |
| 4h      | **-0.1022** | **-2.45** | +0.0111%        | WEAK ⚠️  |
| session | -0.0893     | -1.41     | +0.0387%        | WEAK     |

**4h finding**: IC negative and t_HAC = -2.45 (p=0.014) — statistically significant but WRONG DIRECTION. Momentum hypothesis predicts IC > 0. The actual signal is reversal at 4h. This is NOT exploitable as momentum and was NOT switched to reversal (new hypothesis = new N_test).

### EURUSD — hl_based (N=864 breakout days)

| Horizon | IC_spearman | t_HAC_NW6 | Gate     |
|---------|-------------|-----------|----------|
| 1h      | +0.0374     | +0.12     | FAIL     |
| 2h      | -0.0031     | -0.57     | FAIL     |
| 4h      | **-0.0741** | **-2.37** | WEAK ⚠️  |
| session | -0.0671     | -1.34     | WEAK     |

### GBPUSD — close_based (N=517 breakout days)

| Horizon | IC_spearman | t_HAC_NW6 | Gate |
|---------|-------------|-----------|------|
| 1h      | +0.0518     | +0.76     | FAIL |
| 2h      | +0.0526     | +0.46     | FAIL |
| 4h      | +0.0336     | -0.19     | FAIL |
| session | +0.0119     | -0.44     | FAIL |

### GBPUSD — hl_based (N=905 breakout days)

| Horizon | IC_spearman | t_HAC_NW6 | Gate |
|---------|-------------|-----------|------|
| 1h      | +0.0550     | +1.01     | WEAK |
| 2h      | +0.0495     | +0.70     | FAIL |
| 4h      | +0.0528     | -0.02     | FAIL |
| session | +0.0163     | -0.26     | FAIL |

**Best momentum signal found**: GBPUSD hl_based 1h IC=+0.055, t=+1.01 — below gate (t > 1.65 required).

### Per-year breakdown — 1h horizon, close_based

| Pair   | Year | N   | IC      | t_HAC | hit_rate |
|--------|------|-----|---------|-------|----------|
| EURUSD | 2020 | 92  | +0.073  | +0.50 | 48.9%    |
| EURUSD | 2021 | 109 | +0.113  | +1.04 | 48.6%    |
| EURUSD | 2022 | 93  | -0.024  | -0.87 | 48.4%    |
| EURUSD | 2023 | 96  | +0.056  | -0.11 | 47.9%    |
| EURUSD | 2024 | 99  | +0.081  | +0.36 | 53.5%    |
| GBPUSD | 2020 | 109 | +0.001  | -0.34 | 50.5%    |
| GBPUSD | 2021 | 101 | -0.018  | -0.14 | 53.5%    |
| GBPUSD | 2022 | 93  | +0.152  | +1.70 | 49.5%    |
| GBPUSD | 2023 | 107 | +0.077  | +0.05 | 50.5%    |
| GBPUSD | 2024 | 107 | +0.059  | +0.79 | 50.5%    |

Note: EURUSD 2021 shows highest per-year IC (+0.113) and is the single year closest to passing, but even here t=1.04 < 1.65.

### Dual-pair correlation

| Signal    | Days both break | P(same direction) |
|-----------|----------------|-------------------|
| close     | 266            | **95.5%**         |
| hl        | 666            | **84.8%**         |

Finding: EUR/USD and GBP/USD break in the same direction 95.5% of the time (close-based). Dual-pair confirmation adds zero filtering value — it fires on virtually every ORB day.

---

## IC Results — Angle B (Phase 1.5 v2)

| Pair   | N events | Gate    | Notes                         |
|--------|----------|---------|-------------------------------|
| EURUSD | 130      | FAIL_N  | < 150 gate; ATR filter too restrictive |
| GBPUSD | 118      | FAIL_N  | < 150 gate; ATR filter too restrictive |

Root cause: ATR(14) filter with `min_periods=5` reduced N to 130/118 (not a data quality issue). The news-fade mechanism requires more events than 5 years of EUR/USD + GBP/USD 1-min data provides at 2× ATR threshold.

---

## Why Dead — Root Cause Analysis

**Angle A (London ORB)**:
1. **IC magnitude too small**: Best momentum signal is t_HAC = +1.01 (GBPUSD hl_based 1h). Gate requires +1.65. Signal exists at noise level but cannot survive costs: 1 pip RT × 52-week trading = cost drag overwhelms a ~0.005% raw edge.
2. **Reversal at 4h is the real signal**: EURUSD exhibits statistically significant (t=-2.45, p=0.014) mean REVERSION at the 4h horizon — post-breakout prices revert. This is the OPPOSITE of the momentum hypothesis and is consistent with an over-reaction / false-breakout mechanism. Not exploited (would require new hypothesis + new N_test, and mechanism unclear).
3. **Hit rates near 50%**: Per-year hit rates (48–54%) are consistent with random walk — no directional bias after costs.
4. **Crowding**: London ORB is one of the most replicated retail strategies. Any residual pre-2015 edge has been arbitraged.

**Angle B (News-Fade)**:
1. **Insufficient events**: N=130/118 is too low for statistical power at HAC t-stat gate. The ATR-based spike filter is appropriate but structurally reduces eligible events below the minimum required for robust IC estimation.
2. **Low frequency**: Major EUR/USD/GBP/USD news events at 2× ATR threshold = ~25-30/year, insufficient for 5-year IC test.

**Structural conclusion**: The London ORB / news-fade hypothesis family as formulated produces no statistically detectable momentum IC on EUR/USD + GBP/USD 2020–2024 with clean institutional-quality Dukascopy data.

---

## Potential Overlay (Not Exploited)

The EURUSD 4h reversal (IC=-0.102, t=-2.45) is the one statistically significant finding. If an economic mechanism can be identified for WHY breakouts reverse at 4h (e.g., stop-cascade over-extension then institutional value buying), this could motivate a separate hypothesis. However:
- It was NOT switched to reversal in this study (would require new hypothesis + N_test)
- Mechanism unknown — empirical finding without academic backing
- Should be tested as a new hypothesis in a future cycle if the reversal mechanism can be documented

---

## Files in Archive

- `POSTMORTEM.md` — this file
- `_ic_feasibility.md` — full Phase 1.5 tracking document (moved from active/)
- `_ic_feasibility/` — IC code, fetch scripts, results JSONs (moved from active/)

---

## Lessons Applied

- L2: IC measured on 1h forward, backtest would have been 1h forward — alignment confirmed.
- L6: HAC Newey-West maxlags=6 used throughout.
- L10: Archived with full documentation. N_tests++ recorded. Root cause structural.
