# Voie B — L_cap Sweep (vol-target family, moteur corrigé)

**Date:** 2026-05-29  **Branch:** `claude/voieb-sizing-reconciliation`

**Signal:** US-only BL1, N=2/4, gap≥15bp, 5bp RT. Familles vol-target uniquement.
T=4267 jours, block_size=65, 10,000 paths.

---

## Résultats bootstrap

| L_cap | P(pass) | P(pass)_lo | P(bust) | P(undec) | eq_p5 | j5 surv 2% | j5 surv 3% | j5 surv 4% | Gate |
|-------|---------|-----------|---------|----------|-------|----|----|----|----|
| `A_1.0` | 0.816 | **0.809** | 0.002 | 0.182 | 1.004 | 1.000 | 1.000 | 1.000 | ✅ |
| `A_1.3` | 0.861 | **0.854** | 0.009 | 0.130 | 1.005 | 1.000 | 1.000 | 0.570 | ✅ |
| `A_1.5` | 0.874 | **0.867** | 0.009 | 0.117 | 1.007 | 1.000 | 1.000 | 0.570 | ✅ |
| `A_1.7` | 0.880 | **0.874** | 0.010 | 0.110 | 1.008 | 1.000 | 0.843 | 0.570 | ✅ |
| `A_2.0` | 0.884 | **0.878** **← WINNER** | 0.010 | 0.106 | 1.008 | 1.000 | 0.840 | 0.570 | ✅ |

*(Gate = P(survie -3% choc j5) ≥ 50%)*

---

## Détail des chocs (j5 — le plus létal)

Condition de bust immédiat : `eq × lev × |shock| > 5%` de la balance initiale.
Cliff analytique : lev_cliff = 5% / |shock|

| Choc | Cliff lev (eq=1.0) | L=1.0 | L=1.3 | L=1.5 | L=1.7 | L=2.0 |
|------|-------------------|-------|-------|-------|-------|-------|
| 2% | **2.500** | ✅ | ✅ | ✅ | ✅ | ✅ |
| 3% | **1.667** | ✅ | ✅ | ✅ | ❌ (5.1%) | ❌ (6.0%) |
| 4% | **1.250** | ✅ | ❌ (5.2%) | ❌ (6.0%) | ❌ (6.8%) | ❌ (8.0%) |

---

## Verdict

**Gate :** maximiser P(pass)_lo sous contrainte P(survie choc -3% à j5) ≥ 50%

**L_cap retenu : `A_2.0`**
  - P(pass) = 0.884
  - P(pass)_lo CI95 = 0.878
  - P(survie -3% j5) = 0.840
  - P(survie -2% j5) = 1.000

L_caps disqualifiés (choc -3% j5 survie < 50%) :

---

## Méthodologie

1. Signal identique à sizing_study v1 (US BL1, N=2/4, 5bp RT).
2. Block bootstrap stationnaire (Politis-Romano), block_size=√T, N=10 000, seed=42.
3. Chocs testés : -2%, -3%, -4% — single-pass, check immédiat de la limite daily -5%.
4. Gate = P(survie -3% choc à j5) ≥ 50%.
   Justification : un gap macro de -3% intraday est un événement réaliste (~1×/an).
   La limite daily FTMO (-5%) est statique. À L=1.67, ce choc est exactement fatal.
   Marge de 0.167 lev = buffer de sécurité minimal acceptable.
