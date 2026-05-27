# Phase 1.2 — Corrected FTMO MC Results

**Run date:** 2026-05-28  
**Correction:** timeout removed — absorbing barriers only (±10% P1, ±5/10% P2)  
**Bootstrap:** stationary block, block_size=78 (~√T=6138)  
**Paths:** 10,000

## Analytical cross-check (Brownian motion with drift)

μ/day = 0.001001 (0.1001%)  σ/day = 0.007768 (0.7768%)

| Phase | Barriers | P(pass) analytical |
|-------|----------|--------------------|
| Phase 1 | +10% / -10% | 0.9650 |
| Phase 2 | +5% / -10% | 0.9705 |
| **Both (independent)** | — | **0.9365** |

## Monte Carlo results

| Metric | Value |
|--------|-------|
| P(pass Phase 1) | 0.9791 |
| P(pass Phase 2 \| Phase 1) | 0.9825 |
| **P(pass both)** | **0.9620** |
| **CI 95% (Wilson)** | **[0.9583, 0.9657]** |
| Median days Phase 1 | 77 |
| Median days Phase 2 | 36 |
| Median days total | 129 |
| Safety cap hits | 0 |

## Fail modes

| Mode | % |
|------|---|
| Daily loss — Phase 1 | 0.000% |
| Max loss — Phase 1 | 2.090% |
| Daily loss — Phase 2 | 0.000% |
| Max loss — Phase 2 | 1.747% |

## Static metrics (Phase 1, unchanged)

| Metric | Value |
|--------|-------|
| Sharpe net | 2.0455 |
| Sharpe DSR-deflated | 2.0116 |
| t_HAC (lag-6) | 10.3766 |
| WF folds | 5/5 |

## Min trading days note

FTMO Challenge Phase 1 & 2 (standard 2024-2026): **no minimum trading days**.
The '10-day minimum' applies to the funded account verification, not the challenge.
→ `min_days_p1=0`, `min_days_p2=0` (correct for challenge phases).

## Gate & verdict

| Gate | Threshold | Value | Status |
|------|-----------|-------|--------|
| p_pass_both CI95[0] | ≥ 0.50 | 0.9583 | ✅ PASS |

**VERDICT: RESEARCH_PASS → continue Phase 2 (ablation ratchet)**