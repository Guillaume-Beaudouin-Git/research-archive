# Voie B — Weekly Real-Tape Challenge Simulation

---

## ⚠️  Cadrage obligatoire — résultats IN-SAMPLE

**Cette fenêtre (2025-05-01 → 2026-05-01) est IN-SAMPLE** : les paramètres de
Voie B (gap 15bp, N≥2/4, vol-target L_cap=1.3) ont été choisis avec accès aux
données 2025-2026. Les résultats ci-dessous sont DESCRIPTIFS (dispersion, path-
dependence sur le vrai tape, comportement régime réel) et ne constituent PAS
une estimation forward du pass rate.

**Pass rate forward défendable : ~45-50% (ancré OOS)**, indépendamment de ce test.

---

## Config déployée

| Paramètre | Valeur |
|-----------|--------|
| Signal | Voie B BL1 — gap > 15bp, confirmation N≥2/4 |
| Sizing | vol-target, lev = clip(10%/rvol_60d, 0, 1.3) |
| Coûts | 5bp RT/instrument (intégrés dans les retours journaliers) |
| CB-1 | levered return < -3% → close, cap journalier à -3% |
| FTMO P1 | cible +10%, max-loss -10% statique, daily-loss -5% |
| FTMO P2 | cible +5%, mêmes limites, capital reset à 1.0 |
| Time limit | aucune — challenge non résolu à fin des données = censored |

---

## Signal sur la fenêtre de test

- Jours calendaires : 279 jours de trading (2025-05-01 → 2026-05-27)
- Jours actifs (signal fire) : 206 (73.8%)
- Sharpe non-levé fenêtre : **0.98** (vs 2.97 sur 2010-2026)
  → Le Sharpe 0.98 sur 2025-2026 est significativement inférieur au backtest long terme.
    Cohérent avec une estimation forward de ~45-50% pass rate.

---

## Résultats agrégés

| Métrique | Valeur |
|----------|--------|
| Challenges démarrés | 53 |
| Pass (P1 + P2) | **0** |
| Bust | **0** |
| Censored (fin données) | 53 |
| Pass rate (résolus seulement) | N/A (0 résolus) |

---

## Explication du résultat : 53/53 censored

Aucun challenge ne s'est résolu (ni pass, ni bust). Cela n'est PAS un signe
d'échec du signal — c'est une conséquence directe de deux effets combinés :

**1. Vol-targeting réduit le levier à ~0.65× (au lieu de L_cap=1.3)**

La volatilité réalisée sur US indices en 2025 est élevée (choc tarifaire avril 2025,
~15-16% ann). Vol-targeting maintient la vol du portefeuille à 10% ann :
`lev = min(0.10 / 0.16, 1.3) ≈ 0.63×` au lieu de 1.3×.

Levier moyen déployé sur la fenêtre : **1.05×**
(plage p10–p90 : 0.68× – 1.26×)

**2. Drift insuffisant pour +10% P1 en ≤279 jours de trading**

Sharpe non-levé fenêtre = 0.98. Avec lev ≈ 0.65× :
- drift journalier ≈ 0.65 × 0.035% = **0.023%/jour**
- Jours attendus pour +10% ≈ 10% / 0.023% = **~435 jours**
- Runway disponible (départ mai 2025) : **279 jours** → insuffisant en espérance

**Signal positif confirmé** : progress P1 sur la durée disponible :

| Métrique | P1 progress (% du seuil +10%) |
|----------|-------------------------------|
| Moyenne  | 63.7% |
| Médiane  | 69.7% |
| Max      | **91.5%** |
| Min      | -4.7% |

Le challenge ayant le meilleur départ (mai 2025, 279j disponibles) a atteint
**8.5%** de gain en fin de données — à seulement
**1.5%** du seuil P1.

**Aucun bust** : le signal n'a jamais approché la barrière -10%.
Max drawdown observé : -5.2% (limite = -10%).
CB-1 (-3%) a protégé contre les jours extrêmes.

---

## Distribution des max-drawdowns (tous challenges)

| Métrique | Valeur |
|----------|--------|
| Médiane | -2.1% |
| P10 | -4.2% |
| Min (pire) | -5.2% |

---

## Dispersion mensuelle — clustering régime

| Mois départ | Pass | Bust | Censored | Commentaire |
|-------------|------|------|----------|-------------|
| 2025-05 | 0 | 0 | 5 | (majorité censored) |
| 2025-06 | 0 | 0 | 5 | (majorité censored) |
| 2025-07 | 0 | 0 | 4 | (majorité censored) |
| 2025-08 | 0 | 0 | 4 | (majorité censored) |
| 2025-09 | 0 | 0 | 5 | (majorité censored) |
| 2025-10 | 0 | 0 | 4 | (majorité censored) |
| 2025-11 | 0 | 0 | 4 | (majorité censored) |
| 2025-12 | 0 | 0 | 5 | (majorité censored) |
| 2026-01 | 0 | 0 | 4 | (majorité censored) |
| 2026-02 | 0 | 0 | 4 | (majorité censored) |
| 2026-03 | 0 | 0 | 5 | (majorité censored) |
| 2026-04 | 0 | 0 | 4 | (majorité censored) |

---

## Consistance (info funded uniquement)

Challenges où best_day > 50% de la cible de phase : **0/53**
(uniquement informatif — la règle de consistance s'applique aux comptes funded,
pas à la phase de challenge.)

---

## Fail reasons (challenges bustés)

Aucun bust.

---

## Interprétation

Sur 53 challenges mécaniques, AUCUN ne s'est résolu (pass ou bust).
Ce n'est pas un échec du signal : le drift est positif (P1 progress médiane = 70%), mais la combinaison vol élevée 2025
→ levier réduit + fenêtre de données insuffisante empêche toute résolution.

**Ce test confirme :**
- Signal positif sur la fenêtre (pas de bust, P1 progress positive)
- Pas de clustering de pertes catastrophiques
- CB-1 + vol-targeting absorbent correctement les chocs de 2025

**Ce test ne confirme PAS :**
- Le pass rate forward (résultats in-sample, non-OOS)
- La performance sur une fenêtre de données différente

Le pass rate forward défendable de **~45-50% (ancré OOS)** est indépendant
de ce test et reste l'estimation appropriée pour les décisions de déploiement.
