# DECISION — Deribit BTC VRP Strategy
*Phase 3 complete: 2026-05-23 | n_tests: 153 → 156 (+3)*

---

## VERDICT: ARCHIVE

**Reason**: Retail option costs (8.89%/yr of underlying notional) exceed the gross VRP premium
(4.44%/yr) by a factor of 2×. Net P&L = −4.46%/yr. Sharpe HAC = −2.68. Zero folds
positive across all 13 WF windows (2022-2026).

**Conclusion**: *VRP premium exists structurally (DVOL > RV 80% of time, gross positive) but
is not retail-accessible net of realistic Deribit option fees and bid-ask spreads.*

---

## Phase Progression Summary

| Phase | Gate | Result | n_tests |
|-------|------|--------|---------|
| Phase 0 | Bootstrap / literature review | Complete | 153 (+0) |
| Phase 1 | GATE 1: Net edge > 5%/yr (back-of-envelope) | **PASS** (7.4%/yr estimated) | 153 (+0) |
| Phase 2 | GATE 2: IC > 0.10, t_HAC > 2.5 | **BORDERLINE** (IC=+0.126, t=2.35) | 154 (+1) |
| Phase 3 | Walk-forward net-of-costs Sharpe > 0.5 | **FAIL → ARCHIVE** (Sharpe=−2.68) | 156 (+2) |

---

## Phase 3 Key Numbers

### Per-cycle P&L (% of underlying notional, 184 cycles, 2021–2026)

| Component | Per cycle | Annualized |
|-----------|-----------|------------|
| Gross P&L (B-S approx) | +0.122% | +4.44%/yr |
| Option fees (0.03% × 4 legs) | −0.120% | −4.36%/yr |
| Bid-ask spread (0.5% entry + 0.6% exit) | −0.121% | −4.38%/yr |
| Delta hedge (maker 70%, blended rate) | −0.004% | −0.15%/yr |
| **Net P&L** | **−0.123%** | **−4.46%/yr** |

Cost/Gross ratio: **200%** — costs are exactly twice the gross premium.

### Portfolio metrics (cycle-level Sharpe, 2% underlying sizing)

| Metric | Value |
|--------|-------|
| Sharpe HAC (primary gate) | **−2.68** |
| t_HAC | −6.04 (mean significantly ≠ 0, but negative) |
| Ann vol (% notional) | 1.58% |
| Skewness | −1.77 (fat left tail) |
| Excess kurtosis | 4.68 |
| Worst cycle | −1.46% of notional |
| WF folds positive Sharpe | 0/13 |

### Walk-forward stability

All 13 OOS folds (Nov 2022 → May 2026) show negative Sharpe, ranging from −2.77 to −6.38.
The result is remarkably stable — **consistently losing across all sub-periods**.

---

## Cost Breakdown Insights

**Option fees = 49%, Bid-ask spread = 49%, Hedge = 2%**

The strategy is symmetrically killed by exchange fees AND market impact, not dominated by one.
There is no single cost to fix.

**DVOL-level dependency** (from cost breakdown analysis):

| DVOL at entry | Net P&L/cycle | Interpretation |
|---------------|---------------|----------------|
| < 40% | −0.172% | Badly underwater: low DVOL → tiny gross, same fixed fees |
| 40–60% | −0.146% | Still negative, 55% of all cycles |
| 60–80% | −0.088% | Less negative but still losing |
| > 80% | **−0.008%** | Near break-even at high vol regimes |

**Implication**: Only cycles entered when DVOL > 80% are near-breakeven. This suggests that a
DVOL-level entry filter (only trade when IV is elevated) could potentially pass the cost gate —
but this is a new, un-tested hypothesis that would consume another n_test budget. Decided NOT
to pursue in this mission.

---

## Stress Test Results

### Historical events (within 2021–2026 data window)

| Event | Active cycles | Net P&L (% notional) | Note |
|-------|--------------|----------------------|------|
| LUNA (May 5–15, 2022) | 1 | −0.443% | Early unwind triggered at DD>20% |
| FTX (Nov 6–14, 2022) | 2 | −2.563% total | Both early unwind; worst = −1.46% per cycle |

The regime filter (DD30 > 20% → unwind) **worked as designed** — both events triggered early
exits. However, "working as designed" still means large per-cycle losses. The regime filter
reduces but does not eliminate tail losses.

### Synthetic COVID (BTC −50%/24h, IV ×3)

| DVOL at entry | Premium received | Mark post-shock | Loss (% notional) |
|---------------|-----------------|-----------------|-------------------|
| 50% | 11.43% | 50.59% | **−39.17%** |
| 60% | 13.71% | 51.54% | **−37.83%** |
| 80% | 18.26% | 54.77% | **−36.51%** |

With continuous delta-hedging (20–40% offset), realistic loss ≈ 22–30% of notional.
At 2% portfolio sizing: **portfolio loss ≈ 44–60%**. Far exceeds the −15% hard-stop threshold.

**Gate: FAIL**. Phase 4 stress mitigation redesign would be required.

---

## Root Cause of GATE 1 Error

Phase 1 GATE 1 estimated net VRP = 7.4%/yr by taking Almeida's "14%/yr VRP" as gross and
subtracting costs. This was a unit mismatch:

- Almeida's "14%/yr" = variance premium (DVOL² − RV²) in annualized variance units
- Costs were expressed as % of underlying notional (a different unit)

Converting correctly via the B-S formula:
```
Gross P&L per cycle ≈ ½ × N'(0) × VRP × T_hold / DVOL
                    ≈ 0.5 × 0.3989 × 0.09 × (16/365) / 0.61
                    ≈ 0.12% per cycle  ← far below costs (0.24%)
```

The error should have been caught at GATE 1. **Lesson**: always convert VRP (variance units)
to strategy P&L (% of notional) via the B-S formula before comparing to cost models.

---

## What Would Make This Work?

For the net VRP to turn positive net of costs, one of:

1. **Maker option liquidity** (not available to retail at Deribit — institutions only): if option
   fees dropped from 0.03% to −0.01% per leg, option fee cost becomes rebate → saves 4.36%/yr.
   This alone would flip the strategy to profitable.

2. **DVOL > 80% entry filter**: near-breakeven at high vol. A conditional entry rule
   (new hypothesis, new n_test) that only trades when DVOL > 80%. Would reduce cycle frequency
   to ~5/yr but may pass the cost gate.

3. **Variance swap replication** (Design B from Phase 0): avoids bid-ask but 3× more expensive
   in transaction costs — actually worse. Not viable.

4. **Institutional venue / prop firm desk**: cost structure fundamentally different from retail.
   Research value = "this is why institutions own this premium, not retail."

---

## Methodology Lesson

**Lesson 13 (added)**: When VRP is expressed in variance units (σ²), convert to P&L % of
notional via the B-S delta-hedge formula BEFORE comparing to a cost model. Variance premium
(e.g., 14%/yr in σ² units) does not equal strategy P&L (which is 4–5%/yr in notional units
due to T_hold and σ normalization factors).

---

## Next Steps

1. Archive `Crypto/research/active/vrp_deribit/` → `Crypto/research/archived/options/vrp_deribit/`
2. Update README n_tests: 155 → 156, E[max_SR] update accordingly
3. Document Lesson 13 in `Crypto/research/_meta/lessons/`
4. Optionally pursue: DVOL-level conditional entry as a NEW hypothesis (n_tests → 157)

**HARD STOP. No Phase 4 launched. Research complete.**

*Signed: Claude Sonnet 4.6, 2026-05-23*
