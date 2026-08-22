# FTMO book integration — session_F_integration (GO/NO-GO)
*2026-06, MEASURED (cost = FLAGGED swap-sensitivity, crypto swap UNMEASURED → re-run on real). Book = TSMOM (engine) + MACD (shape) + commodity-seasonal (return diversifier), equal-risk, common window 2016–2026 (n=2617). pre-FOMC built but kept out of the core MC (dated/short-window/parallel-pending; adds little). No de-levered baseline (L19). Nothing frozen/merged.*

## VERDICT: CONDITIONAL NO-GO at realistic cost — the book is GATED by the unmeasured crypto swap, not by the assembly.
The assembled book passes **51% (low swap) / 25% (mid) / 6% (high swap)** at L2. **The crypto swap (unmeasured) is the single gating factor.** At realistic (mid–high) swap the book is **below the ~33% wall**, because the engine (TSMOM) is net-zero-to-negative after swap — and **no assembly can manufacture a passing drift from a dead engine.** GO **only if** the swap measurement (session_D / Claude Code) lands in the low-swap regime (→ 51%).

## #1 — Integration MC + bust-mode decomposition (THE deliverable), L=2×

| Swap (FLAGGED assumption) | p(pass) +10% P1→P2 | bust-DAILY (5% cap) | bust-TOTAL (10% floor) | median |
|---|---:|---:|---:|---:|
| LOW (optimistic) | **51%** | 15% | 31% | 10.1 mo |
| MID | **25%** | 18% | 54% | 7.3 mo |
| HIGH (conservative) | **6%** | 14% | 77% | 3.6 mo |

**The deferred question, answered:** at realistic/high swap **the TOTAL floor is the dominant bust mode (54–77%), NOT the daily cap (~14–18%).** When swap eats the engine's drift, the book bleeds cumulatively to the −10% floor. The daily 5% cap is the *manageable* mode; the killer is the engine's net-of-swap drift.

**Assembly works on the daily cap:** diversification cuts the daily-cap bust **31% (TSMOM-alone) → 18% (book)** — MACD + seasonal (decorrelated, corr 0.08/0.10) genuinely reduce the single-day crash exposure. But it cannot fix the total-floor bleed of a net-negative engine.

## #5 — Leverage frontier (MID swap) — the DP ceiling
| Leverage | p(pass) | bust-daily | bust-total | median |
|---|---:|---:|---:|---:|
| 1.0× | 4% | 39% | 13% | 52.9 mo (too slow — ~0 drift never reaches +10%) |
| 1.5× | 10% | 10% | 76% | 10.8 mo |
| **2.0×** | **25%** | 18% | 54% | 7.3 mo |
| 3.0× | 26% | 16% | 56% | 5.6 mo |
| 4.0× | 25% | 27% | 47% | 2.5 mo |

**Sizing arbitrates speed-vs-bust, NOT probability** — p(pass) is flat ~25–26% across L2–4 (the container-optimal plateau / DP ceiling). Confirms: you cannot size your way past a ~0-drift engine; the leverage choice only trades median-time for bust-rate.

## #2 — Daily circuit-breaker (flat at −3% intraday) → KEEP (net-positive)
| | p(pass) | bust-daily |
|---|---:|---:|
| no CB | 25% | 18% |
| **CB −3%** | **30%** | **0%** |
**Δp(pass) +5pp; eliminates the daily-cap bust (18%→0%).** The survival gained beats the EV sacrificed → a genuine net-positive container lever. (Still ~30% at mid swap — it fixes the daily cap, not the total-floor engine problem.)

## #4 — Gross-scaling on inter-sleeve corr-spike → KILL
Cutting gross when the 3 sleeves co-move (dispersion bottom-quintile = crash signature): p(pass) 25% (unchanged), **bust-daily 20% vs 18% unscaled → NO reduction → KILL.** The crash-day detector doesn't work — consistent with session_C (no live regime/crash predictor). There is no usable real-time crash signal; the circuit-breaker (reactive, #2) is the only daily-cap defense that works.

## #3 — Phase-conscious sizing (L19, matched-leverage)
P2 (+5%) is structurally easier than P1 (+10%) → lower leverage clears P2 at the same bust budget (read off the frontier: the +5% target is reached at ~half the leverage-time of +10%). Optimal: **size P1 nearer the L2–3 plateau (need the +10%), de-emphasise leverage in P2** (the +5% is cheap). Not a new edge — a container-allocation refinement.

## Synthesis — what the whole program converges to
1. **The book is structurally sound on the DAILY cap** (diversification 31→18% + circuit-breaker →0%). That mode is solved.
2. **The book's viability is GATED by the ENGINE's net-of-swap drift** (the total-floor mode). TSMOM net is unmeasured (crypto swap) → p(pass) ranges 6–51%. At realistic swap the engine is ~0-drift → total-floor bust dominates → below the wall.
3. **GO/NO-GO = the crypto-swap measurement.** Benign swap → GO (~51%, with circuit-breaker ~55%). Punitive swap → NO-GO (the engine is dead, no assembly rescues it).

**The single decisive remaining measurement is unchanged from before: TSMOM's crypto overnight swap on demo.** Everything else (assembly, daily-cap defense, leverage) is settled. The book lives or dies on the engine's carry — measure it before any deployment.

**Lesson candidates (named, not numbered):**
- **"the assembled book's p(pass) is gated by the engine's net-of-swap drift, not by the assembly"** — diversification fixes the daily cap (31→18%) but cannot pass a barrier with a ~0-drift engine.
- **"at realistic swap the TOTAL floor is the dominant bust mode, not the daily cap"** — the deferred question answered: negative carry → cumulative bleed to −10%; the daily cap is the *manageable* mode.
- **"the daily circuit-breaker is a net-positive container lever"** — flat at −3% eliminates daily busts (18→0%) and lifts p(pass) +5pp.
- **"the inter-sleeve corr-spike crash detector fails"** — no real-time crash signal (consistent with session_C's dead regime detector); only the reactive circuit-breaker works on the daily cap.
- **"sizing arbitrates speed-not-probability (DP ceiling)"** — frontier flat ~25–26% across L2–4 at mid swap.

*Reproduce: `integration_mc.py`. Daily, GATE-0-clean, swap FLAGGED. Stayed in session_F_integration/; nothing frozen/merged.*
