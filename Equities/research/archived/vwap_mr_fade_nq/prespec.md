# VWAP MR Fade NQ — Pre-registered Specifications

**Status** : PRE-REGISTRATION (avant tout code)
**Date** : 2026-05-26
**Ref** : Adams-Dim-Eraker-Fontaine-Ornthanalai-Vilkov 2025 SSRN 5641974

---

## Adaptation vs prespec template (ES → NQ)

| Paramètre | Template initial | Retenu ici | Raison |
|---|---|---|---|
| Univers | ES futures 1-min | NQ futures 1-min | Pas de ES 1-min dispo (pas de Kaggle credentials, pas de Databento key) |
| Période | 2018–2025 (8 ans) | 2023-01–2025-12 (3 ans) | NQ parquet commence fin déc 2022 |
| VWAP | Reconstruit depuis volume | `vwap_rth` pré-calculé parquet | Disponible nativement, anchoré 09:30 ET |
| Instrument live | MES | MNQ | Idem Strategy C, mêmes commissions Tradovate |
| Coût RT | $1.55 ($1.30 + $0.25 MES tick) | $1.80 ($1.30 + $0.50 MNQ tick) | MNQ tick = 0.25pts = $0.50 |
| N_trades minimum | ≥ 300 (8 ans) | ≥ 200 (3 ans) | Ajusté proportionnellement |

**Justification mécanique** : Adams et al. documentent le GEX dealer-hedging sur l'ensemble du marché S&P.
Le même flux de hedging 0DTE s'applique aux futures NQ via les options QQQ/NDX (deuxième marché 0DTE en volume).
La corrélation ES/NQ est > 0.95 en intraday. Le mécanisme est testable sur NQ.

---

## Univers

NQ E-mini (Nasdaq-100 futures) 1-min bars RTH (09:30–16:00 ET).
**Source** : `data/raw/NQ_1min_2022-12-26_2025-12-11.parquet`
Colonnes disponibles : `open, high, low, close, volume, vwap_rth, vwap_eth`

## Période backtest

2023-01-01 → 2025-12-11 (RTH uniquement)
Sessions disponibles : ~750 jours de trading

## Walk-forward — 5 folds expanding window (CLAUDE.md L2)

| Fold | Train | Test |
|---|---|---|
| 1 | Jan 2023 – Déc 2023 (12m) | Jan 2024 – Jun 2024 (6m) |
| 2 | Jan 2023 – Jun 2024 (18m) | Jul 2024 – Déc 2024 (6m) |
| 3 | Jan 2023 – Déc 2024 (24m) | Jan 2025 – Jun 2025 (6m) |
| 4 | Jan 2023 – Jun 2025 (30m) | Jul 2025 – Sep 2025 (3m) |
| 5 | Jan 2023 – Sep 2025 (33m) | Oct 2025 – Déc 2025 (3m) |

Minimum 5 folds satisfait (CLAUDE.md hard rule).

---

## Signal (pré-enregistré, ne pas modifier post-failure)

1. **VWAP anchoré** : colonne `vwap_rth` (09:30 bar = 0, ignoré ; anchoré depuis 09:31)
2. **Écart** : `dev = close - vwap_rth`
3. **Rolling std** : `sigma_30 = dev.rolling(30).std()` (30 minutes glissantes)
4. **Z-score** : `Z = dev / sigma_30`
5. **Entry trigger** : `|Z| > 2.0` (seuil pré-enregistré)
6. **Direction** : FADE — short si `Z > 2.0`, long si `Z < −2.0`

**Note LPT** : Signal calculé sur bar T−1, exécution au T (CLAUDE.md L1).

## Filtres temporels (deux variantes pré-enregistrées)

- **VARIANT_A** : 10:30–15:00 ET (skip 60 min ouverture + 60 min clôture)
- **VARIANT_B** : 10:00–15:30 ET (fenêtre plus large)

Deux variantes testées en parallèle → 2 n_tests consommés.

---

## Règles de sortie

| Règle | Condition | Note |
|---|---|---|
| TP | `Z` revient à ≤ 0.5 (moitié du fade) | Approximation ~3-5 pts NQ typ. |
| SL | `|Z|` dépasse `Z_entry + 1.0` adverse | Approximation ~3-5 pts NQ typ. |
| Time stop | 30 min post-entry | Forcer fermeture |

Une seule position à la fois. Pas de pyramiding.
Signal T−1, trade T — le signal du bar T détermine l'entrée au open du bar T+1.

---

## Modèle de coût (MNQ Tradovate)

- Commission RT : $1.30/contrat (Tradovate, idem Strategy C)
- Slippage : 1 tick RT = $0.50/MNQ (25pts × $0.02 — ordres limit près du VWAP)
- **Total RT : $1.80/MNQ** (~0.009% pour NQ à ~20 000pts)

Coût par trade converti en points : $1.80 / $2.00 per pt (MNQ $0.50/0.25pt) = 0.9 pts RT.

---

## Hypothèses pré-enregistrées

### H1 — Edge brut (avant coûts)
Sur 2023–2025, VARIANT_A produit :
- Sharpe brut ≥ 1.0
- Win rate ≥ 60%
- N_trades ≥ 200

### H2 — Edge après coûts MNQ
Net Sharpe (après $1.80 RT) ≥ 0.7

### H3 — Filtre régime (bonus, ne compte pas comme modification)
Proxy GEX : `abs_move_first30 = abs((close_10h00 − open_09h30) / open_09h30)`

| Régime | Condition | Hypothèse |
|---|---|---|
| MR-favorable | abs_move_first30 < 0.30% | Sharpe MR > 1.5 → eligible follow-up |
| Trend-favorable | abs_move_first30 > 0.50% | VWAP non-mean-reverting |

Note : pas de données GEX réelles disponibles (Volland/Spotgamma payant).
Ce proxy est une approximation — résultat H3 à confirmer avec données GEX avant tout live.

---

## Gates PASS/FAIL

| Résultat | Action |
|---|---|
| H1 PASS + H2 PASS | CPCV validation → `Portfolio/validation/cpcv.py` |
| H1 PASS + H2 FAIL | Archiver — edge dominé par les coûts |
| H1 FAIL | Archiver — pas d'edge |
| H3 : SR conditionnel MR > 1.5 | Marquer pour follow-up GEX réel |

---

## DSR / multiple testing

```
n_trials = 180   # cumulé constitution Equities/Futures space
```
Formula Bailey-LdP 2014 via `Portfolio/reporting/metrics.py::compute_psr_dsr(n_trials=180)`.
Threshold : DSR > 0.95 → PASS.

---

## Hypothèses architecturales (non-testées, à vérifier data_setup)

1. `vwap_rth` est anchored depuis 09:30 ET, réinitialisé chaque session (vérifié empiriquement : bar 09:30 = 0, bars suivants = running anchored VWAP ✓)
2. Gaps RTH dans le parquet NQ négligeables (à vérifier : sessions manquantes, minutes vides)
3. Volume NQ suffisamment distribué intraday pour que sigma_30 soit stable après 10:30
4. VARIANT_A (10:30–15:00) exclut naturellement les minutes avec sigma_30 instable (premières 60 bars)

---

## Budget de modifications et n_tests

- Modifications consommées : **0/3** (CLAUDE.md L10)
- n_tests consommés cette série : **2** (VARIANT_A + VARIANT_B)
- n_tests global post-série : **322 → 324**

---

## Anti-patterns à respecter

- NE PAS modifier le Z-score threshold (2.0) après un FAIL H1 → compterait comme modification #1
- NE PAS ajuster la fenêtre rolling_std (30 bars) post-failure
- NE PAS lancer full backtest avant canary 2024 validé
- NE PAS committer results.json avant STOP-POINT 3 validé par l'utilisateur
