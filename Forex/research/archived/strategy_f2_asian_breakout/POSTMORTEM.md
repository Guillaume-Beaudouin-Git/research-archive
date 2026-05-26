# Strategy F2 — Asian Range Breakout (London Open)
# POSTMORTEM — ARCHIVED 2026-05-26

**Pre-registered:** 2026-05-25  
**Archived:** 2026-05-26  
**Verdict:** ARCHIVED — Option A. L11 cost gate pre-registered FAIL. No backtest run.  
**n_tests consumed:** 1 (L11 preflight evaluation; 0 backtests)  
**DSR n_trials running total:** 275 (274 cross-asset + 1 F2; 7 of the 8 pre-planned F2 variants NOT consumed)  
**Global n_tests running total:** 322 (CLAUDE.md updated)

---

## L11 Cost Gate — IJR (Binding, Pre-Registered)

**Formula:** `gross_alpha = 0.40 × IC × √N × σ_target;  gate_ratio = gross_alpha / (cost_frac × N)`  
**Source:** Israel-Jiang-Ross (2017) + Grinold-Kahn fundamental law  
**Gate threshold:** gate_ratio ≥ 3.0 (pre-registered, non-negotiable)

### Cost model (pre-registered, non-uniform)

| Pair | Cost RT (pips) | pip_pct | Cost RT (% notional) |
|------|---------------|---------|----------------------|
| GBPUSD | 2.5 | 0.0001/1.27 | 0.019685% |
| EURGBP | 2.6 | 0.0001/0.86 | 0.030233% |
| GBPJPY | 4.0 | 0.01/192   | 0.020833% |
| AUDJPY | 3.8 | 0.01/97    | 0.039175% |
| **Mean** | — | — | **0.027482%** |

mean_cost_frac = 2.7482 × 10⁻⁴

### N estimation (analytical, pre-download)

Per-pair annual signal days:  
252 × F4(0.60) × F1(0.57) × F3(0.75) × F2+F5(0.90) ≈ **58 days/pair/year**

| N interpretation | Value | Rationale |
|-----------------|-------|-----------|
| N_trades | 232 | 4 pairs × 58, all treated as independent |
| N_calendar | 94 | Calendar days with ≥1 pair signal (GBP-correlated: 2 independent groups, P(≥1 fires)≈0.622) |

N_calendar is the most favorable interpretation for IJR (lowest N → highest ratio).

### IJR gate results

| Scenario | gross_alpha | cost_drag | gate_ratio | IC required to pass | Verdict |
|----------|-------------|-----------|------------|---------------------|---------|
| N = 232 (total trades) | 3.046%/yr | 6.376%/yr | **0.478** | 0.314 | **FAIL** |
| N = 94 (calendar days, best case) | 1.939%/yr | 2.583%/yr | **0.751** | 0.200 | **FAIL** |

**Both scenarios FAIL at IC = 0.05.**

---

## L11 Alt — Binary TP/SL Gate (Informational, Ad-Hoc, No Academic Citation)

**Formula:** `E[gross/trade] = win_rate × tp_equity − (1−win_rate) × sl_equity;  gate_ratio = gross/trade ÷ mean_cost_frac`  
**Note:** N-independent (gross and cost both linear in N → they cancel). Not a registered gate substitute.

| Parameter | Value |
|-----------|-------|
| IC | 0.05 |
| win_rate = 0.5 + IC/2 | 0.525 |
| tp_equity = 0.15% × 0.9/0.5 | 0.27% of equity |
| sl_equity | 0.15% of equity |
| gross/trade | **0.0705% of equity** |
| mean cost/trade | 0.02748% of equity |
| gate_ratio | **2.565** |
| Verdict | **FAIL** (< 3.0) |

Alt gate passes at IC ≥ 0.107 (win_rate ≥ 55.3%). This is plausible for London breakout in favorable conditions but requires numerical documentation from Tzimopoulos (2025) per-regime win rates — not available from the literature summary alone. Bumping IC post-failure without data is post-hoc adjustment; refused.

---

## Why IJR Is Structurally Inappropriate for Binary TP/SL Breakout

### The structural problem

Simplifying: `gate_ratio_IJR = (0.40 × IC × σ) / (cost × √N)` — this is **monotonically decreasing in N**.

At IC=0.05, σ=0.10, mean_cost_frac=2.748×10⁻⁴:

```
constant C = 0.40 × 0.05 × 0.10 / 2.748e-4 = 7.278
gate_ratio = C / √N = 7.278 / √N

Gate passes (ratio ≥ 3.0) only at N ≤ (7.278/3.0)² = 5.88 trades/year
```

No realistic FX intraday strategy trades fewer than 6 times per year. The IJR gate is **structurally impossible to pass** for any intraday strategy with reasonable IC.

### Why this happens: formula mismatch

The Grinold-Kahn / IJR fundamental law is derived for **cross-sectional equity strategies** where:

1. The portfolio holds N instruments simultaneously (N≥30)
2. Each instrument contributes a small, uncorrelated alpha proportional to IC × σ
3. Gross alpha scales as IC × √N × σ (diversification across instruments)
4. Cost per instrument is fixed, so total cost scales as cost × N

For such strategies, `gross / cost ∝ IC × √N / (cost × N) ∝ 1/√N` — the gate gets harder as breadth increases because each additional instrument adds less alpha per unit cost once the IC is fixed.

For a **binary TP/SL breakout with 4 correlated pairs**:

1. There is no cross-sectional averaging — each trade is a directional binary bet
2. Gross alpha per trade is determined by `win_rate × TP_payoff − loss_rate × SL_payoff`, not by IC × σ / √N
3. Gross and cost both scale linearly with N → ratio is **N-independent**
4. The correct feasibility gate is: `E[gross/trade] > threshold × cost/trade`

IJR conflates "breadth" (annual independent bets) with "number of instruments held simultaneously". For a breakout strategy executing sequentially (one at a time), these are the same number — but the diversification mechanism of the fundamental law does not apply.

### The correct model for future breakout strategies

Use the **direct trade P&L gate**:

```
E[gross/trade] = win_rate × (TP_mult/SL_mult × eq_risk) − (1−win_rate) × eq_risk
gate: E[gross/trade] ≥ 3 × cost/trade
```

where win_rate and IC must be justified by **numerical literature** (win rates by regime/filter condition from a peer-reviewed backtest), pre-registered **before** any data is examined.

This model is N-independent, economically interpretable, and does not break down for small universes. At 55% win rate (IC≈0.10), gate passes for F2's cost structure. At 50% (IC=0), gate fails — which is the correct result (breakeven strategy should not pass).

---

## What Was Preserved

| File | Location | Purpose |
|------|----------|---------|
| `hypothesis.md` | `Forex/research/archived/strategy_f2_asian_breakout/` | Pre-registration record |
| `literature_scan.md` | same | Literature references (Breedon-Ranaldo, Tzimopoulos, BIS 2025) |
| `data_setup.py` | same | Dukascopy M5 infra (bi5 decoder, Pool(4) download, vectorized Asian range) |
| `results.json` | same | L11 preflight data (machine-readable) |
| `news_events_2020_2025.csv` | `Forex/data/` | Reusable for any future FX intraday strategy needing news blackout filter |

**Not preserved:** `feasibility.py` (stub with no implementation).

**Cache:** No data downloaded. Cache unchanged (`EURUSD_2016_M5.parquet` from strategy_e only).

---

## Recommendation for Future Breakout Strategies

1. **Pre-register the correct gate upfront:** use `E[gross/trade] > 3 × cost/trade`, not IJR.
2. **Document IC / win_rate numerically before pre-registration:** cite a peer-reviewed backtest giving win rates by market condition (e.g., Tzimopoulos 2025 by ATR regime, not just "sweet-spot improves outcomes"). Do not pre-register IC=0.05 as a placeholder.
3. **If IJR is used for any strategy with ≤10 instruments:** verify that gate_ratio is increasing in N for the formula you are using. If the formula produces a decreasing-in-N ratio, it is misapplied.
4. **Asian range breakout data infrastructure is ready:** `data_setup.py` provides the full Dukascopy M5 download + vectorized Asian range + 6-filter pipeline. If a future study documents win rates ≥ 55% with firm literature backing, re-open with L11b direct P&L gate and a new pre-registration.
5. **Universe and filters are valid:** EURUSD exclusion (Tzimopoulos 2025 edge decay), ATR sweet-spot filter, news blackout calendar — all structurally sound. The failure is in the feasibility gate calibration, not in the strategy concept.
