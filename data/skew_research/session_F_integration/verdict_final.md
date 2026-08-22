# FTMO book — FINAL VERDICT (swap MEASURED) — session_F_integration
*2026-06. The gate is no longer an assumption. BTCUSD demo FTMO: interest-%/yr mode, long −30 AND short −30 → **−30%/yr ≈ 8.3 bps/night, SYMMETRIC, Friday ×3** (→ 58.1 bps/week held, day-weighted not 7×8.3-phantom), commission 6.5 bps RT. Swap charged on **held notional per leg** (L33), both-directions. Circuit-breaker −3% KEEP. Does NOT overwrite the low/mid/high capstone (`exploration_2026-06.md`). Nothing frozen/merged.*

## VERDICT: NO-GO — the FTMO branch has NO validated engine at measured cost.
At the measured all-in overnight cost the multi-asset daily TSMOM engine collapses from **gross Sharpe 0.9 (ann 8.0%/yr) to net Sharpe 0.0 (ann 0.0%)** — the full ~8.0%/yr trend premium is eaten by ~8.0%/yr all-in carry (6.75% swap + ~1.25% commission). The assembled book passes only **13% (L2, CB−3%)** — pure container-math (bust-total 83%). **Crypto ablation makes it WORSE** (Sharpe −0.13), so there is no viable sub-configuration. ETH swap precision is irrelevant.

## The reframe — the bleeder was never crypto-specific (the key new finding)
Measured per-leg annual swap drag (held notional × rate × day-weight, L1):

| leg | rate (bps/night) | **ann swap drag** | why |
|---|---:|---:|---|
| US500 | 2.5 | **2.26%** | low-vol → LARGE notional under vol-targeting |
| GLD | 3.5 | **1.70%** | " |
| SLV | 3.5 | 0.94% | |
| USO | 4.0 | 0.91% | |
| **BTC** | **8.3** | **1.04%** | high-vol → SMALL notional → modest drag despite high rate |
| **ETH** | **8.3** | **0.66%** | " |
| **total** | | **6.75%/yr** | |

**Crypto contributes only 1.70% of the 6.75%/yr drag.** Vol-targeting gives the high-vol crypto legs *small* notional, so even at 8.3 bps/night their carry is minor — *less* than the low-vol, large-notional index/metal legs. **The killer is the AGGREGATE overnight carry across all six legs, not crypto.** Verified decomposition: **gross trend = Sharpe 0.9, ann 8.0%/yr** (2018–2026, full cycle) → consumed almost exactly by **6.75% swap + ~1.25% commission = 8.0%/yr all-in carry → net Sharpe 0.0, ann 0.0%.**

*(Sanity: weekly crypto swap = 7×8.3 = 58.1 bps ✓ matches the measured ~58. Day-weighting = 4×1 + 1×3 on trading days, the triple covers the weekend — not phantom calendar rows.)*

## PHASE 1 — book WITH crypto (measured swap, L2)
| | p(pass) +10% P1→P2 | bust-DAILY (5%) | bust-TOTAL (10%) | median |
|---|---:|---:|---:|---:|
| no circuit-breaker | 7% | 17% | 72% | 3.2 mo |
| **CB −3% (KEEP)** | **13%** | **0%** | 83% | 4.0 mo |

Leverage frontier (CB−3%): L1.5 **8%** / L2 **13%** / L3 **26%** / L4 **28%** — even pushed to L4 it can't clear the wall, and bust-total stays 70–83%. **ETH −45% sensitivity (12.3 bps): TSMOM Sharpe −0.04 → book p(pass) still 13% → ETH precision does NOT change the verdict.** The circuit-breaker again works exactly as designed (daily bust 17%→0%) but it can only fix the daily cap; it cannot rescue a net-zero engine bleeding to the total floor.

**STOP-POINT 1: p(pass) 13% ≤ 33% → NO-GO → Phase 2.**

## PHASE 2 — crypto ablation (isolate the bleeder)
**TSMOM NO-CRYPTO (US500+GLD+SLV+USO), measured swap: Sharpe −0.13, ann −1.1%, maxDD −47.4% — DEAD, and WORSE than the full engine.**

- **(a) residual net-SR = −0.13 ≤ 0 → dead.** Short-the-crash property survives (mean US500 sign on the 40 worst equity days = **−0.72** → it does short crashes), but a correct crash-short with no net edge is not an engine.
- **(b) two-sided per class (L25), (long-SR / short-SR):** index **0.69 / 0.08**, metals **1.07 / 0.03**, oil **0.05 / 0.53**. The index & metal legs are almost entirely **long-driven** (short legs ≈ 0) — i.e. disguised long-trend beta over the 2009–2025 bull; only oil is genuinely short-driven. So even the gross signal is half-beta on the non-crypto legs.
- **(c) matched-leverage (L19, CB−3%, L2):** book WITH crypto **13%** vs book NO-crypto **9%** → removing crypto *lowers* p(pass). No-crypto frontier: L1.5 4% / L2 9% / L3 11% / L4 18% — below the with-crypto curve everywhere.

**Removing crypto removes the best raw-trend leg (crypto trend Sharpe was 1.12 gross) while only shedding 1.7% of the carry → strictly worse.** There is no crypto-free sub-engine.

**STOP-POINT 2 → binary verdict: multi-asset daily TSMOM is WEAK INDEPENDENTLY.** Crypto was *not* the marginal bleeder that tipped a healthy engine to zero — the engine is zero with crypto and negative without it. **The FTMO branch has no validated engine at measured all-in cost.**

## What this resolves
The long-deferred "conditional GO if the crypto swap is benign" is now decided. The crypto swap *was* benign-ish (minor, 1.7%/yr) — **and the engine still fails**, because the real cost was always the aggregate multi-leg overnight carry, not crypto. At honest cost, daily multi-asset TSMOM on the FTMO universe has no net edge that survives the container. The daily-cap mode is fully solved (diversification + circuit-breaker → 0% daily busts); the engine's net drift is the binding constraint and it is ~0. **NO-GO.**

**Lesson candidates (named, not numbered):**
- **"the FTMO killer was the aggregate overnight carry, not the crypto swap"** — vol-targeting gives high-vol crypto small notional (1.7%/yr drag); the low-vol large-notional index/metal legs dominate the 6.75%/yr total. Measure the *book-level* carry, not the scary single-instrument rate.
- **"daily multi-asset TSMOM is net-zero at measured all-in cost"** — gross trend premium (~6–7%/yr) ≈ all-in carry (~6.75%/yr) → Sharpe 0.0; the book passes 13% (container-math, bust-total 83%).
- **"crypto ablation makes it worse, not better"** — crypto was the best raw-trend leg and a minor swap-payer; the crypto-free core is net-negative and half long-beta (L25: index/metal short-SR ≈ 0).
- **"the circuit-breaker fixes the daily cap but never the engine"** — daily bust 17%→0% across every leverage, yet p(pass) stays ≤28%; survival ≠ profitability.
- **"a net-zero engine's p(pass) is pure leverage-arbitraged container-math"** — frontier 8/13/26/28% across L1.5–4 with bust-total 70–86%; no leverage clears the wall.

*Reproduce: `verdict_final.py` (imports `tsmom_engine.load_basket`; daily; measured per-leg day-weighted swap; MACD/seasonal overnight haircut = conservative non-crypto assumption, flagged, second-order). Stayed in session_F_integration/; nothing frozen/merged.*
