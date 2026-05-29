# Voie B — FTMO Single-Ticket Sizing Study

**Date:** 2026-05-29  **Branch:** `claude/voieb-sizing-singleticket`

**Signal:** US-only BL1, N=2/4, gap≥15bp, cost=5bp RT — identical across all families.
T=4267 days (2010–2026), block_size=65 (≈√T), 10,000 bootstrap paths, shared random seed 42.
vol_q15 (Family C gate vol threshold) = 4.74% ann.

---

## Problem statement

Single FTMO Challenge ticket (€10K, ~€99 fee). ONE draw from a bimodal distribution.
**Do NOT optimise E[pass].** Optimise the LOWER BOUND of P(pass) — worst-case survival.**
Hypothesis: aggressive sizing (B/C) has better mean but worse lower bound and worse
shock survival, because it amplifies daily P&L and can breach the -5% daily limit.

---

## FTMO 2-phase rules (encoded)

| Phase | Target | Max loss | Daily loss | Capital at start |
|-------|--------|----------|-----------|-----------------|
| 1     | +10%   | -10% (static, from phase start) | -5% of initial (fixed) | 1.0 |
| 2     | +5%    | -10% (static, from phase start) | -5% of initial (fixed) | 1.0 (reset) |

No time limit. Paths reaching 250 days without bust or pass → **undecided** (not fail).

Daily loss check: `E_prev × lev × r < -0.05` (P&L as fraction of phase-start balance).
At equity E_prev > 1.0, this becomes more restrictive: e.g., at E=1.10, bust if lev×r < -4.55%.

---

## Main results — block bootstrap

| Family | P(pass) | **P(pass)_lo CI95** | P(pass)_hi | P(bust) | P(undec) | P1 rate | eq_p5 |
|--------|---------|--------------------|-----------|---------|---------|---------|----|
| `A_1.0` | 0.816 | **0.809** | 0.824 | 0.002 | 0.182 | 0.943 | 1.004 |
| `A_1.5` | 0.874 | **0.867** | 0.880 | 0.009 | 0.117 | 0.959 | 1.007 |
| `A_2.0` | 0.884 | **0.878** | 0.890 | 0.010 | 0.106 | 0.961 | 1.008 |
| `B` | 0.929 | **0.924** **← WINNER** | 0.934 | 0.000 | 0.071 | 0.966 | 0.980 |
| `C_2.5` | 0.001 | **0.000** | 0.001 | 0.000 | 1.000 | 0.022 | 0.968 |
| `C_4.0` | 0.007 | **0.005** | 0.009 | 0.001 | 0.992 | 0.093 | 0.955 |

*(P(pass)_lo = decision criterion — maximise this column)*

---

## Days to resolution (bust + pass paths only)

| Family | Median days | P90 days | % undecided |
|--------|-------------|----------|-------------|
| `A_1.0` | 142 | 220 | 18.2% |
| `A_1.5` | 127 | 210 | 11.7% |
| `A_2.0` | 124 | 208 | 10.6% |
| `B` | 64 | 166 | 7.1% |
| `C_2.5` | 227 | 239 | 100.0% |
| `C_4.0` | 202 | 242 | 99.2% |

---

## Shock tests — P(survive shock | alive at day d)

Methodology: single-pass simulation; at each shock day d, record whether a -2%
shock would immediately breach the FTMO daily loss limit (immediate-bust check).
P(survive) = P(NOT immediate bust | path alive at day d) — **conditional on alive**.
A family that dies 100% of the time when the shock hits is **disqualifying**.

Daily limit breach condition for -2% shock: `E_prev × lev × 0.02 > 0.05`
  → lev > 2.5 / E_prev
  → At E_prev = 1.0: bust if lev > 2.5  |  At E_prev = 1.05: bust if lev > 2.38
Family B at lev=3.75 (cap): any E_prev > 0.67 → bust. Family C L=4.0: any E_prev > 0.625 → bust.

| Family | j5 P(surv\|alive) | j20 P(surv\|alive) | j40 P(surv\|alive) |
|--------|-----------------|------------------|-------------------|
| `A_1.0` | 1.000 | 1.000 | 1.000 |
| `A_1.5` | 1.000 | 1.000 | 1.000 |
| `A_2.0` | 1.000 | 1.000 | 1.000 |
| `B` | 0.461 | 0.484 | 0.551 |
| `C_2.5` | 0.939 | 0.944 | 0.932 |
| `C_4.0` | 0.888 | 0.927 | 0.910 |

---

## Equal-exposure comparison (L19 — same time-in-market)

Mean daily deployed leverage (all days, including inactive signal days).
Scale factor = `min_exp / family_exp` — multiply family leverage by this to match
the lowest-exposure family's total risk budget.

| Family | Mean lev | Scale to min | Note |
|--------|----------|--------------|------|
| `A_1.0` | 0.907 | 0.293 | reduce by 71% |
| `A_1.5` | 1.123 | 0.236 | reduce by 76% |
| `A_2.0` | 1.189 | 0.224 | reduce by 78% |
| `B` | 3.372 | 0.079 | reduce by 92% |
| `C_2.5` | 0.266 | 1.000 | reference |
| `C_4.0` | 0.344 | 0.773 | reduce by 23% |

---

## Verdict

**Winning family: `B`** — highest P(pass)_CI95_lower_bound = 0.924

**Family B REJECTED for single-ticket:** shock j5 survival=0.461 < best A=1.000.
Ratchet amplifies leverage as equity grows → -2% shock at day ≥20 lethal at lev≈3.75.
**C_2.5 REJECTED for single-ticket:** P(pass)_lo=0.000 < best A=0.878; shock j5 survival=0.939 < best A=1.000 (gate open ≈15% → always busts at L=2.5×).
**C_4.0 REJECTED for single-ticket:** P(pass)_lo=0.005 < best A=0.878; shock j5 survival=0.888 < best A=1.000 (gate open ≈15% → always busts at L=4.0×).

**Optimal L_cap for Family A: `A_2.0`**  (p_pass_lo=0.878, shock_j5=1.000)

---

## Methodology

1. Signal generated once from `data/panels/ftmo_{open,close}.csv` (US-only BL1, N=2/4).
   Cost = 5bp RT (task spec). Families share IDENTICAL signal — diff = sizing only.
2. Block bootstrap (Politis-Romano stationary): block_size=65,    N=10,000, seed=42.
   Bootstrap index array (N×T) generated once and shared across all families.
3. FTMO simulation: per-day equity tracking with hard phase transitions and bust checks.
   Daily loss check uses FIXED 5% of initial phase balance (not trailing).
4. Shock test: single-pass immediate-bust check. At each shock day d, records whether
   E_prev × lev × (-0.02) < -0.05 (daily limit breach). Conditional on path alive at d.
   Equivalent to full-simulation approach for -2% shocks (daily limit is binding).
5. L19 equal-exposure: mean lev computed on 500-path subsample × 250 days.
