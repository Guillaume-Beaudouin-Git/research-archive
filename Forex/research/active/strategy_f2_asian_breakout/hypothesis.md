# Strategy F2 — Asian Range Breakout (London Open)
# PRE-REGISTERED HYPOTHESIS — DO NOT MODIFY AFTER CREATION

**Pre-registered:** 2026-05-25  
**Status:** FROZEN — any modification constitutes a new strategy hypothesis and consumes n_tests budget  
**n_tests baseline at pre-registration:** 321 global (CLAUDE.md), DSR computed with n_trials=282 (274 cross-asset + 8 F2 variants)

---

## Asian Range Definition (FIXED)

- **Window:** 22:00 UTC (J−1) → 07:00 UTC (J). High = max(close) in window. Low = min(close) in window.
- **Justification:** Covers Sydney + Tokyo sessions in full. Ends 1 hour before London open (08:00 UTC), giving a clean separation between Asian range formation and London breakout.
- **Data resolution:** M5 closes (Dukascopy). Range computed on M5 close prices only (not intrabar wicks).
- **CONFIRMED (2026-05-25 STOP-POINT 1 validation):** Window = 22:00 UTC (J−1) → 07:00 UTC (J). No change from pre-registration. This definition is frozen.

---

## Universe

{GBPUSD, EURGBP, GBPJPY, AUDJPY}

EURUSD explicitly excluded: edge decayed to near-zero 2020–2024 per Tzimopoulos (2025) sub-period analysis. This is a structural decision, not a retrospective filter.

---

## Backtest Period

2020-01-01 → 2025-12-31 (6 calendar years, approximately 1,500 trading days).

---

## Trading Rule

1. **Entry condition:** First M5 bar that closes strictly outside the Asian range, between 08:00 UTC and 11:00 UTC (inclusive of 08:00, exclusive of 11:00).
   - Long entry: close > asian_high + 1 pip
   - Short entry: close < asian_low − 1 pip
   - Entry price: close of the triggering bar (no limit order, no anticipation)
2. **Stop-Loss (SL):** 0.5 × asian_range from entry price
3. **Take-Profit (TP):** 0.9 × asian_range from entry price
   - Note: TP = 0.9× (not 1.0×) → R:R = 0.9/0.5 = 1.8. Deliberate choice: avoids the "round number" clustering at exactly 2:1 that causes slippage; consistent with Tzimopoulos sweet-spot empirics.
4. **Time-stop:** If neither SL nor TP hit by 11:00 UTC → close at 11:00 UTC market.
5. **Max trades per pair per day:** 1 (first valid trigger only).
6. **Direction:** Whichever direction breaks out first. No directional bias from prior day.

---

## Mandatory Filters (ALL 6 MUST PASS)

### Filter 1 — Range Sweet-Spot (Tzimopoulos 2025)
`asian_range ∈ [0.4 × ATR(20d), 1.0 × ATR(20d)]`  
ATR(20d) = daily ATR computed from D1 OHLC aggregated from M5 data, 20-day trailing.  
Skip the day for the pair if range is outside the interval.

### Filter 2 — No High-Impact News (Hardcoded Calendar)
No high-impact macro event whose ±30 min blackout window overlaps the 07:00–11:00 UTC entry window for either base or quote currency of the pair.

**Implementation:**  
Source: `news_events_2020_2025.csv` (same directory as this file). Columns: `date, time_utc, event_type, currencies_affected, source`.  
Skip condition per pair: for any row in the CSV where `pair's_currencies ∩ currencies_affected ≠ ∅`, compute `blackout = [time_utc − 00:30, time_utc + 00:30]`. If `blackout ∩ [07:00, 11:00] UTC ≠ ∅` → skip that pair for that day.  
Simplified equivalent: skip if `06:30 ≤ event_time_utc ≤ 11:30` and currencies match.

**Events included in CSV (2020–2025) and which actually trigger filtering:**

| Event type | Typical time UTC | In [06:30, 11:30]? | Pairs affected |
|------------|-----------------|---------------------|---------------|
| UK_CPI | 07:00 | **YES** ✓ | GBPUSD, EURGBP, GBPJPY |
| UK_EMPLOYMENT | 07:00 | **YES** ✓ | GBPUSD, EURGBP, GBPJPY |
| UK_GDP_MONTHLY | 07:00 | **YES** ✓ | GBPUSD, EURGBP, GBPJPY |
| UK_RETAIL_SALES | 07:00 | **YES** ✓ | GBPUSD, EURGBP, GBPJPY |
| GERMAN_IFO | 09:00 | **YES** ✓ | EURGBP |
| EUROZONE_PMI_FLASH | 09:00–10:00 | **YES** ✓ | EURGBP |
| BOE_RATE | 12:00 | no (12:00 > 11:30) | — |
| ECB_RATE | 13:15 | no | — |
| FOMC | 19:00 | no | — |
| NFP_US | 13:30 | no | — |
| CPI_US | 13:30 | no | — |
| RBA_RATE | 04:30 | no (04:30 < 06:30) | — |
| BOJ_RATE | ~03:00 | no | — |

Non-filtering events included in CSV for documentation completeness only. AUDJPY: no JPY events (BoJ at ~03:00 UTC), no AUD events (RBA at 04:30 UTC) fall in window → AUDJPY only filtered by USD events (none in window). Effective news filter applies primarily to GBP and EUR pairs.

**Calendar source:** `news_events_2020_2025.csv` hardcoded from official public calendars (BLS, Fed.gov, ONS, BoE, ECB, RBA, BoJ). Column `source = CONFIRMED` for verified dates; `source = APPROX` for dates derived from release patterns (±1–2 days accuracy). For production deployment, all APPROX entries must be verified against official source calendars.

### Filter 3 — D1 Trend Filter (EMA50)
EMA(50) computed on D1 closes (aggregated from M5), updated daily at 22:00 UTC (Asian session open).  
- Long entry only if: close(J−1) > EMA50(J−1)
- Short entry only if: close(J−1) < EMA50(J−1)  
If entry direction conflicts with D1 trend → skip for that pair that day.

### Filter 4 — Weekday Filter
Allowed trading days: **Tuesday, Wednesday, Thursday only**.  
Monday excluded: weekend gap risk. Friday excluded: position hold over weekend risk.  
No substitution for bank holidays — if Tue/Wed/Thu is a UK/US bank holiday, skip it.

### Filter 5 — BoJ Intervention Risk Gate
If USDJPY close(J−1) > 158.00 → skip GBPJPY and AUDJPY for that day.  
Rationale: USDJPY above 158 indicates elevated BoJ intervention risk; JPY crosses exhibit correlated shock behavior that invalidates range structure.  
USDJPY data loaded from M5 cache (derived close D1).

### Filter 6 — Weekend Gap Skip
If gap(open J) > 0.5 × ATR(D1) relative to close(J−1) → skip ALL pairs for that day.  
Note: Filter 4 already excludes Monday in normal weeks. Filter 6 applies to edge cases where Monday is the first tradeable day after a long weekend (e.g., bank holiday Tuesday → Monday must trade). Under this strategy, we do NOT shift Tuesday to Monday — we simply skip. Filter 6 is coded defensively for completeness.

---

## H1 — Viability Gate (PRIMARY)

On portfolio {GBPUSD, EURGBP, GBPJPY, AUDJPY}, 2020-2025, after all 6 filters, equal-weighted daily P&L:

| Metric | Gate | Verdict logic |
|--------|------|---------------|
| Sharpe net (HAC lag-6) | ≥ 0.70 | t-stat on daily portfolio returns, Newey-West HAC |
| MaxDD | ≤ −15% | Peak-to-trough on cumulative net equity curve |
| Profit Factor | ≥ 1.25 | Sum(winning trades) / Sum(losing trades) |
| N_trades | ≥ 400 over 6 years | L12 floor gate |

**Note on excess returns**: Raw intraday FX returns (hold <4h) — DTB3 daily RF is negligible (<0.05 bps per trade at 2022-2024 rates). Mentioned in results.json; not subtracted per-trade.

**Note on vol-targeting**: Sizing per trade = 0.15% equity at risk, scaled by rolling 20-day σ per pair (vol-targeting at trade level, not portfolio level). Portfolio-level vol target = 10% annualized equity exposure. Sharpe computed on daily portfolio returns (sum of pair returns for trades closing that day).

---

## H2 — Temporal Stability Gate

Decompose into 3 sub-periods:
- 2020–2021 (COVID + post-COVID recovery)
- 2022–2023 (rate hike cycle, USD strength)
- 2024–2025 (normalization, BoJ pivot)

Gate: Sharpe per sub-period ≥ 0.50.  
**Failure condition**: Monotonically declining Sharpe across the 3 periods → HFT decay confirmed → ARCHIVE with POSTMORTEM "HFT decay" verdict.

---

## H3 — Cross-Pair Decorrelation Gate

Compute Pearson correlation of daily conditional returns (on days where both pairs have an active signal) across all 6 pair-combinations:
{GBPUSD–EURGBP, GBPUSD–GBPJPY, GBPUSD–AUDJPY, EURGBP–GBPJPY, EURGBP–AUDJPY, GBPJPY–AUDJPY}

Gate: No pair-combination exceeds ρ = 0.50.  
**Failure condition**: Systematic ρ > 0.50 → edge dominated by a single GBP/JPY factor, basket diversification is illusory → re-test on single best pair, report to user.

---

## Gate Decision Tree

```
H1 FAIL                          → ARCHIVE direct, POSTMORTEM (no WF)
H1 PASS + H2 FAIL (monotone decay)→ ARCHIVE, POSTMORTEM "HFT decay"
H1 PASS + H2 PASS + H3 FAIL     → re-test on single best pair, report to user
H1 PASS + H2 PASS + H3 PASS     → proceed to walk-forward + DSR
```

---

## Cost Model (Per Pair, Non-Uniform)

Spread ECN moyen 08:00–11:00 UTC + 1 pip slippage stress + commission $7/lot RT (ICMarkets Raw), expressed in pips RT:

| Pair | Spread (avg) | Slippage stress | Commission | **Total RT** |
|------|-------------|-----------------|------------|-------------|
| GBPUSD | 0.8 pip | 1.0 pip | 0.7 pip | **2.5 pip** |
| EURGBP | 0.9 pip | 1.0 pip | 0.7 pip | **2.6 pip** |
| GBPJPY | 1.8 pip | 1.5 pip | 0.7 pip | **4.0 pip** |
| AUDJPY | 1.6 pip | 1.5 pip | 0.7 pip | **3.8 pip** |

Justification: JPY crosses (GBPJPY, AUDJPY) incur spread expansion at Tokyo-London overlap (08:00–08:30 UTC) and reduced AUDJPY liquidity post-Tokyo close. Uniformizing to 1.5 pip for all pairs would understate cost drag on crosses — prohibited per project methodology (L9).

---

## L11 Cost Gate Pre-Flight — EXPLICIT GATE (Israel-Jiang-Ross 2017)

**This gate runs in `data_setup.py` before any backtest. FAIL = execution stops immediately.**

```python
# Fixed inputs (pre-registered, do not modify):
EXPECTED_IC   = 0.05    # conservative breakout intraday IC
SIGMA_TARGET  = 0.10    # 10% annualized vol target (basket)
GATE_RATIO_MIN = 3.0    # gross_alpha must be ≥ 3× cost_drag

# N estimated analytically pre-download, then refined from data post-download.
# Two interpretations (both reported in results.json):
#   N_trades   = total annual trades across basket (4 pairs × per-pair signal days)
#   N_calendar = annual calendar days where ≥1 pair has a valid signal (portfolio breadth)
# Structural property: gate_ratio = (0.40 × IC × σ) / (cost × √N) → DECREASING in N.
# N_calendar is the most favorable (lowest N → highest ratio).

# Per-pair cost in % of notional (pip_pct = pip_value / mid_price):
cost_pips = {"GBPUSD": 2.5, "EURGBP": 2.6, "GBPJPY": 4.0, "AUDJPY": 3.8}
cost_pct = {p: cost_pips[p] * pip_pct[p] for p in cost_pips}
mean_cost_pct = mean(cost_pct.values())

# Gate computation (run at both N_calendar and N_trades):
gross_alpha_est   = 0.40 * EXPECTED_IC * (N ** 0.5) * SIGMA_TARGET
annual_cost_drag  = mean_cost_pct * N
gate_ratio        = gross_alpha_est / annual_cost_drag
```

**VERDICT:**
- `gate_ratio ≥ 3.0` → **PASS** → log to `results.json`, proceed to `feasibility.py`
- `gate_ratio < 3.0` → **FAIL → STOP. Do NOT run feasibility.py. Archive F2 as structurally non-feasible (cost overflow). Report figures to user.**

**Mandatory logging in `results.json` at STOP-POINT 2 (regardless of PASS/FAIL):**
```json
{
  "preflight_l11_ijr": {
    "formula": "gross_alpha = 0.40 × IC × sqrt(N) × sigma_target",
    "source": "Israel-Jiang-Ross (2017)",
    "status": "PRE-REGISTERED BINDING GATE",
    "IC": 0.05,
    "sigma_target": 0.10,
    "N_annual_trades": null,
    "N_calendar_days": null,
    "cost_pct_by_pair": {"GBPUSD": null, "EURGBP": null, "GBPJPY": null, "AUDJPY": null},
    "mean_cost_pct": null,
    "gate_ratio_at_N_trades": null,
    "gate_ratio_at_N_calendar": null,
    "IC_required_to_pass_at_N_calendar": null,
    "gate_min": 3.0,
    "overall_verdict": "PENDING",
    "action": "PENDING"
  },
  "preflight_l11_breakout_alt": {
    "status": "INFORMATIONAL — ad-hoc, no academic citation, NOT a gate substitute",
    "formula": "gross/trade = win_rate × tp_equity − (1−win_rate) × sl_equity; gate_ratio = gross/trade / mean_cost_frac",
    "IC": 0.05,
    "win_rate": null,
    "gate_ratio": null,
    "IC_required_for_pass": null,
    "verdict": "PENDING"
  }
}
```

---

## DSR Configuration (Bailey–López de Prado 2014)

- **n_trials:** 282 (274 cross-asset already tested + 8 variants of F2 conservative hypothesis count)
- **T:** 1,500 trading days (6 years)
- **Compute:** Probabilistic Sharpe Ratio (PSR) and Deflated Sharpe Ratio (DSR) with empirical skew and kurtosis of portfolio returns
- **Benchmark SR\*:** computed from n_trials=282, T=1500, skew and kurtosis from actual distribution
- Gate: DSR > 0 (i.e., reported Sharpe exceeds the expected maximum from pure noise at n_trials=282)

---

## Methodology Compliance Checklist

- [ ] Excess returns: intraday <4h → DTB3 negligible, documented in results.json
- [ ] HAC SE: statsmodels OLS fit(cov_type='HAC', cov_kwds={'maxlags': 6})
- [ ] Vol-targeting: 20-day rolling σ per pair, 0.15% equity at risk per trade
- [ ] Walk-forward: expanding window ≥5 folds if H1+H2+H3 all pass
- [ ] AMTP/DSR: n_trials=282, compute before final reporting
- [ ] Filter audit log: results.json must record N_skipped per filter, per pair, per year
- [ ] No look-ahead: Asian range computed from bars [22:00 J−1, 07:00 J], entry at first bar closing outside after 08:00 J
- [ ] Signal at T (entry bar close), not T−1: confirmed by construction (first-close-outside = entry)
