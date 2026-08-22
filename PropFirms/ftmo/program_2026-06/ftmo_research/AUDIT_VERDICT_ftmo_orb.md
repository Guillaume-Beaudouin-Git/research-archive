# Audit adversarial — Stratégie FTMO ORB (indices)
## Verdict : **NO-GO** sur le critère « p(pass) > 70% single-attempt, FTMO $10K, ≤ 2 mois »

**Conclusion en une ligne — Audit chaîné (Phase 1 +10% puis Phase 2 +5%, real-path, full 2022-2025) : p(funded) = 51% sans filtre régime, max 57% avec le meilleur filtre ex-ante (vr5 low tercile). La cible 70% single-attempt est structurellement inatteignable, et le rapport interne sous-estime cet écart en parlant uniquement de la Phase 1.**

---

## 0. Périmètre, base de code et reproductibilité du baseline

### 0.1 Code audité
- Dossier : `data/ftmo_research/code/` (et nouvel audit `data/ftmo_research/audit/`).
- Stratégie testée : **3-sleeve core** déclaré dans `CHALLENGE_REPORT_FINAL.md §4` :
  - US100 ORB @ 16:30 EET, OR=30min.
  - GER40 ORB @ 16:30 EET, OR=15min.
  - GER40 ORB @ 10:00 EET, OR=30min.
- **Écart code/rapport (lot 1) :** le sleeve GER40 @ 16:30 n'existe PAS dans
  `strategy_orb.py` (la fonction `orb_daily_R` n'utilise qu'une seule session
  par symbole, et la session GER40 codée est 10:00–18:00). Le `ENSEMBLE`
  effectivement déclaré (`{"US100":(1,3,6), "GER40":(1,3,6), "US30":(3,)}`)
  = 7 setups, pas 3, et inclut US30 qui est explicitement rejeté par la
  documentation du rapport.
  → J'ai donc ré-implémenté le 3-sleeve dans `audit/orb_core.py`.
- **Écart code/rapport (lot 2) :** le rapport (§3) affirme « contiguous real-path
  challenge simulation (not iid bootstrap) ». Le code `ftmo_sim_ensemble.py`
  fait **strictement de l'iid bootstrap** (ligne 36, `rng.integers(0, n_hist, n_paths)`).
  Le nom « DAY-BLOCK » dans le docstring est trompeur : il signifie « on tire un
  jour entier d'un coup » (pour préserver la corrélation intra-jour), pas
  « on enchaîne des jours contigus ». Le rapport décrit une autre méthodo que celle qui tourne.

### 0.2 Reproduction du baseline 58% / 36%
- **Baseline du code (ENSEMBLE 7 setups, iid bootstrap, risk=0.6%/trade) :**
  - 2021-22 : 70.7% pass, 25.4% bust ✓ (correspond au docstring `ftmo_sim_ensemble.py:14`)
  - 2023 chop : 40.3% pass, 58.6% bust ✓
  - 2024-25 OOS : 64.7% pass, 34.1% bust ✓
  - **Full 2022-2025 : 61.1% pass, 38.0% bust** ← le baseline reproductible est 61%, pas 58%.
- **Baseline 3-sleeve ré-implémenté (block-cap 1.5%, iid) sur 2022-2025 : 61.1% pass.**
  Le chiffre 58% du rapport est introuvable depuis le code disponible.

  Hypothèses pour l'écart 61% vs 58% : (a) le rapport a appliqué un stress
  slippage caché supplémentaire ; (b) le 3-sleeve diffère de mon ré-implémentation
  (window OR exact, vol-target différent) ; (c) le rapport a rapporté la moyenne
  de plusieurs simulations « weekly » avec contraintes ad hoc. Aucune de ces
  variantes n'est retrouvable dans le code livré.

> **Décision méthodologique :** plutôt que stopper sur cet écart (+3pts), j'audite
> la version reproductible (61%). Les conclusions sur la **structure** (Sharpe, tail,
> régime, slippage, chaînage) sont robustes à un offset de 3pts du baseline.

---

## 1. Chiffres rapport vs chiffres re-dérivés

Toutes les colonnes « Re-dérivé » = mon 3-sleeve audit, block-cap 1.5%, méthodo identique au rapport (iid pour pass-rate, daily Sharpe HAC lag-6 pour Sharpe).

| Métrique | Rapport | Re-dérivé | Écart | Statut |
|---|---:|---:|---:|---|
| **2026 ONLY (cherry-pick)** | | | | |
| Trades | 308 | 308 | 0 | ✓ match exact |
| Win rate | 44% | 44.2% | +0.2pt | ✓ |
| Expectancy (R) | +0.106 | +0.109 | +0.003 | ✓ |
| Profit factor | 1.20 | 1.21 | +0.01 | ✓ |
| Skew | +2.2 | +2.13 | -0.07 | ✓ |
| Sharpe (daily ann) | 1.62 | **1.93** | **+0.31** | ⚠ audit + favorable |
| MaxDD | -8.2% | -8.1% | +0.1pt | ✓ |
| Total return | +28.9% | +34.7% | +5.8pt | ⚠ audit + favorable |
| **CROSS-RÉGIME 2022-2025** | | | | |
| Expectancy (R) | ~+0.05 | **+0.103** | **+0.05** | ⚠ rapport pessimiste 2× |
| Sharpe (daily ann) | non chiffré | **1.54** | n/a | passe le gate L8 (>1.0) |
| t HAC lag-6 | non chiffré | **3.37** | n/a | t-stat significatif |
| MaxDD | non chiffré | **-48.4%** | n/a | catastrophique en compoundé |
| Worst calendar month | non chiffré | **-17.7%** | n/a | **excède le floor FTMO 10%** |
| **PASS RATES (single attempt)** | | | | |
| Baseline 2022-2025 | 58% (claim "real-path") | 61.1% (iid) / 68.7% (real-path) | +3 à +10pts | ⚠ rapport ne reproduit pas |
| 2023 chop | 38-58% selon section | 38.8% (iid) / 54.3% (real-path) | dans le range | ✓ |
| 2026 (cherry) | 62-93% | 65.8% (iid) / 100% (real-path) | audit + favorable | ⚠ |
| **PROBABILITÉS MULTI-ATTEMPTS** | | | | |
| « 80% en 2 essais » | 1-(1-0.58)² = 82% indep. | block-bootstrap 86-90% (block=5-40j) | + favorable | ⚠ mais voir §3 |
| **p(funded) = p(P1) × p(P2 | P1)** | non chiffré | **44.6%** (iid) / **50.9%** (real-path) | n/a | ⚡ chiffre manquant majeur |

> **Conclusion §1 :** sur les nombres factuels, le rapport est globalement honnête
> sur 2026 (match parfait), prudent sur cross-régime (audit +50% sur expectancy)
> et son « 80% en 2 essais » reste flou car (a) ne couvre que Phase 1 et (b)
> assume l'indépendance des tirages — voir §3. Le seul écart méthodologique
> grave est sur la nature du bootstrap (iid vs real-path) et sur l'absence du
> chiffre p(funded) chaîné, qui est précisément le seul qui compte.

---

## 2. Étape 1 — Sharpe full-sample HAC vs 2026

| Période | Trades | Mean R | Sharpe ann (daily) | t HAC lag-6 | MaxDD | Worst month | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 852 | +0.149 | 2.41 | 3.10 | -19.7% | -4.7% | +265% |
| **2023 chop** | 764 | **+0.002** | **-0.11** | -0.12 | -39.9% | **-17.6%** | **-14.4%** |
| 2024-2025 | 1523 | +0.129 | 1.78 | 2.75 | -23.1% | -17.7% | +347% |
| **Full 2022-2025** | 3056 | +0.103 | **1.54** | **3.37** | **-48.4%** | **-17.7%** | +1181% |
| All 2021-2026 | 3447 | +0.104 | 1.56 | 3.75 | -48.4% | -17.7% | +1783% |
| **2026 ONLY** | 308 | +0.109 | **1.93** | 1.78 | -8.1% | -0.0% | +34.7% |

**Gate L8 PROPFIRM (Sharpe > 1.0) :**
- Full 2022-2025 : 1.54 → **PASS brut**.
- 2026 only : 1.93 → **PASS brut**.
- 2023 chop : -0.11 → **DEAD**.

**Mais à retenir :**
- En **compoundé** (block-cap 1.5%, pas reset FTMO), la stratégie traverse une DD
  de -48% sur 2022-2025 et un mois pire de -17.7%. Un compte FTMO de $10K aurait été
  bust ~plusieurs fois en chop 2023 (single-month -17.7% > floor 10%).
- Le Sharpe 1.54 est **brut** : il faut le déflater par DSR (§3 T4).

---

## 3. Étape 2 — Robustesse (T3 / T4 / T5 / T6)

### 3.1 T3 — Loterie de queue (drop top-N trades)

| Drop N | Full 2022-25 meanR | Sharpe | Pass% iid | 2026 meanR | Sharpe 2026 | Pass% 2026 |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | +0.103 | 1.54 | 61.1% | +0.109 | 1.93 | 65.8% |
| 1 | +0.098 | 1.50 | 60.6% | +0.083 | 1.61 | 61.0% |
| 3 | +0.089 | 1.35 | 59.1% | **+0.034** | **0.70** | **47.3%** |
| 5 | +0.083 | 1.29 | 58.4% | **-0.006** | **-0.24** | **34.0%** |
| 10 | +0.071 | 1.15 | 56.6% | -0.076 | -1.66 | 18.6% |

**Verdict T3 :**
- **Full sample : edge survit drop-top-5** (Sharpe 1.29, pass 58%). Pas un edge tail-only sur la fenêtre complète.
- **2026 cherry : pure loterie**. Retirer 3 trades → Sharpe 0.70, retirer 5 → mean R **négatif**. Le headline « 1.62 Sharpe / 93% pass » du rapport repose sur **5 trades** sur 308. **Statistiquement, le 2026 est un single-realisation outlier, à ignorer**.

### 3.2 T4 — Deflated Sharpe (Bailey-LdP)

Le rapport déclare ~18 familles testées (FX, indices, gold, crypto, mean-rev, trend, etc.).

| Période | n_trials | SR0 (seuil expected-max) | SR déflaté | DSR P(real) | Verdict (gate 1.0) |
|---|---:|---:|---:|---:|---|
| **Full 2022-2025** | 1 | 0 | 1.540 | 1.00 | pass |
| 2022-2025 | 5 | 0.54 | 1.00 | 0.99 | pass (limite) |
| **2022-2025** | **18** | **0.84** | **0.70** | **0.94** | **FAIL** |
| 2022-2025 | 50 | 1.03 | 0.51 | 0.87 | FAIL |
| **2026 ONLY** | 1 | 0 | 1.93 | 1.00 | pass |
| 2026 only | 5 | 1.74 | 0.20 | 0.55 | FAIL |
| **2026 only** | **18** | **2.70** | **-0.77** | **0.30** | **FAIL** |

**Verdict T4 (cf. L20 du CLAUDE.md) :**
- À n_trials=18 (la familly count revendiquée par le rapport), le Sharpe full-sample
  déflaté tombe à **0.70**, qui **ÉCHOUE le gate PROPFIRM_PASS (1.0)**.
- Le Sharpe 2026 (1.93 brut, T=104 jours seulement) est ANNIHILÉ par DSR :
  à n_trials=5 (très conservateur), SR déflaté = 0.20. Le 2026 « 1.62 » du rapport
  n'a aucune signification statistique au sens DSR.

### 3.3 T5 — Slippage breakeven sweep

Slip_R = fraction de l'opening-range (1R) appliqué symétriquement (entry adverse + stop fills past level).

| slip_R | meanR | Sharpe | Pass% iid | Bust(tot)% |
|---:|---:|---:|---:|---:|
| 0.000 | +0.103 | 1.54 | 61.1% | 31.9% |
| 0.025 | +0.079 | 1.16 | 56.6% | 36.9% |
| 0.050 | +0.049 | 0.70 | 50.8% | 43.1% |
| **0.063** (estimé) | — | — | **pass=bust crossover** | — |
| 0.075 | +0.022 | 0.26 | 45.5% | 49.0% |
| **0.092** (estimé) | **≈0** | — | — | — |
| 0.100 | -0.004 | -0.14 | 40.6% | 54.3% |
| 0.150 | -0.050 | -0.84 | 33.4% | 62.9% |
| 0.200 | -0.093 | -1.48 | 27.4% | 70.0% |

**Verdict T5 :**
- **Pass = bust à slip_R ≈ 0.063** (6.3% de l'OR adverse, symétrique entry+stop).
- **Expectancy = 0 à slip_R ≈ 0.092** (9.2% de l'OR).
- À slippage réaliste 5–10% : pass 40–51%, bust 43–54%.
- Marge de sécurité **étroite mais positive** : l'edge survit ~1.5–2× le slippage modélisé,
  mais ne survit pas 3×. Cohérent avec le rapport.

### 3.4 T6 — Delay test sur les 3 sleeves RETENUS

Le delay test 1-bar a tué EURGBP et PDH/PDL **dans le rapport**. Sur les sleeves CONSERVÉS :

| Période | Delay (5min bars) | meanR | Sharpe | Pass% iid |
|---|---:|---:|---:|---:|
| Full 2022-25 | 0 | +0.103 | 1.54 | 61.1% |
| Full 2022-25 | 1 (5 min après breakout) | +0.081 | 1.22 | 56.8% |
| Full 2022-25 | 2 (10 min après) | +0.070 | 1.09 | 55.7% |
| 2023 chop | 0 | +0.002 | -0.11 | 38.8% |
| 2023 chop | 1 | -0.015 | -0.38 | 35.1% |
| 2023 chop | 2 | -0.018 | -0.50 | 33.2% |
| 2024-25 OOS | 0 | +0.129 | 1.78 | 65.1% |
| 2024-25 OOS | 1 | +0.108 | 1.50 | 61.5% |
| 2024-25 OOS | 2 | +0.096 | 1.40 | 60.7% |

**Verdict T6 :**
- ✓ **Edge survit 1-bar et 2-bar delay** sur les 3 sleeves retenus.
  Pas un artefact same-bar fill — le delay test a été appliqué correctement aux survivants.
- ⚠ **Décroissance ~30% par bar** : timing d'exécution important. Une exécution
  qui slip de 2 × 5min réduit le Sharpe full-sample 1.54 → 1.09 (-29%).
- ⚠ **2023 chop = mort à tout delay.** Pas de spécification fragile-au-delay : c'est
  l'absence d'edge en 2023, pas un artefact.

---

## 4. Étape 3 — Block-bootstrap + chaînage Phase 1 + Phase 2

### 4.1 Block-bootstrap vs iid
Diagnostics autocorrélation sur le PnL daily portfolio 2022-2025 :
- VR_q5 = 0.91, VR_q10 = 0.83, VR_q20 = 0.70 → mean-reversion des rendements daily (anti-momentum).
- RV_AC_lag1 = 0.94, lag20 = -0.14, lag60 = -0.08 → vol persistante sur ~20 jours.
- **Régime persistence ≈ 20 jours** d'après la décroissance de l'autocorr de vol.

| Méthode | Pass% | Fail_total% | 2 attempts (indep) |
|---|---:|---:|---:|
| iid (modèle du rapport) | 61.1% | 31.9% | 84.8% |
| block_len=5 | 62.7% | 29.3% | 86.1% |
| block_len=10 | 63.7% | 28.5% | 86.8% |
| block_len=20 (≈régime) | 65.4% | 27.4% | 88.0% |
| block_len=40 | 68.8% | 28.7% | 90.3% |

**Verdict §4.1 :**
- **Surprise contre-intuitive :** block-bootstrap donne pass-rate **PLUS élevé** que iid.
  Pourquoi : RV est persistante (lag1=0.94), donc une bonne période génère une suite de bons jours.
  iid mélange bons et mauvais → plus de chances de buster dans la transition.
- ✗ Argument du rapport « real-path préserve les mauvais clusters → pessimiste » : **faux**.
  Real-path est en moyenne **plus favorable** que iid sur ce data.
- ✓ Mais 2 attempts à 88% (block=20) suppose **tirages indépendants** : pour deux tentatives
  consécutives sur des fenêtres adjacentes, la dépendance est plus forte → 88% est encore optimiste.

### 4.2 Conditionnel régime au départ (real-path)
Tag des starts par tercile de feature (avec info ≤ J−1) :

| Feature | Tercile favorable | Pass% | n | Spread vs pire tercile |
|---|---|---:|---:|---:|
| rv20 (vol réalisée 20j) | mid (vol modérée) | **72.1%** | 262 | +19.2pt vs high |
| vr5 (Lo-MacKinlay q=5) | low | **75.1%** | 358 | +14.6pt vs high |
| vr10 | mid | 68.1% | 213 | +1.1pt — non discriminant |
| trend20 | mid | **74.3%** | 261 | +12.5pt vs low |

→ La meilleure feature (vr5 low) donne **75.1% en single Phase 1**. C'est au-dessus de 70% ✓.
→ Mais voir §6 : la P2 érode cela à 57% funded.

### 4.3 Chaînage Phase 1 + Phase 2 (chiffre clé)

| Méthode | p(P1 +10%) | p(P2 +5% \| P1) | **p(funded)** |
|---|---:|---:|---:|
| iid bootstrap, full 2022-25 | 62.3% | 72.5% | **45.2%** |
| **real-path enchaîné** (each start runs P1, then P2 sur jours suivants) | **68.8%** | **74.1%** | **50.9%** |

**Verdict §4.3 :**
- Le **rapport ne chiffre pas p(funded) end-to-end**. Son « 80% en 2 essais » couvre seulement la Phase 1.
- La Phase 2, plus courte (+5%, 40j), est en pratique plus facile sachant un P1 réussi (~72-74%).
- **p(funded) honnête = 51%**. **Loin** des 80% laissés entendre par le rapport.
- 1.7 essais en moyenne pour P1 ≠ 1.7 essais pour funded — il faut payer 2 fees par tentative
  P1+P2 (FTMO challenge fee Phase 1 + Verification fee Phase 2 incluse, mais reset complet
  en cas de bust en P2).

### 4.4 2026 weekly real-path (audit reproduit le 93%)
Audit : 15 PASS sur 21 starts (100% des 15 résolus à fin mai 2026). Match qualitatif avec
le rapport's 13 PASS / 14 résolus / 1 TIMEOUT / 7 still running. L'écart vient probablement
de paramètres slippage légèrement différents — l'audit est **plus favorable** que le rapport sur 2026.

**N-effectif :** 21 starts hebdo sur ~104 jours, chacun 40 jours → ~2.6 blocs indépendants.
**Le 93% n'a aucune valeur statistique** (variance d'un Bernoulli sur N=3).

---

## 5. Étape 4 — Gate intermédiaire

| Critère | Mesure audit | Status |
|---|---|---|
| Sharpe full-sample > 1.0 (brut) | 1.54 | ✓ pass |
| Sharpe full-sample > 1.0 (DSR n_trials=18) | 0.70 | ✗ **FAIL** |
| Edge survit drop-top-3 | meanR +0.089R, Sharpe 1.35 | ✓ pass |
| MaxDD < -25% (research) ou < -10% (propfirm) | -48% / -17.7% pire mois | ✗ **FAIL** |
| WF > 60% sur 5 folds | non testé séparément | n/a |
| p(funded) > 70% single attempt | **51% real-path / 45% iid** | ✗ **FAIL** (très loin) |
| Edge survit 1-bar delay | Sharpe 1.54 → 1.22 (-21%) | ✓ marginal |
| Edge survit slippage réaliste (0.10R) | pass 41%, bust 54% | ⚠ marginal |

**Gate intermédiaire :** ÉCHEC sur 3 critères majeurs (DSR, MaxDD, p(funded)). Le seul chemin de
sauvetage théorique = filtre régime ex-ante → §6.

---

## 6. Étape 5 — Thèse de timing de régime (le seul chemin de sauvetage)

### 6.1 Cadre L15 — pertinent ici
L15 dit : overlays régime utiles sur SR<0.7 avec clustering conditionnel de DD.
- **SR cross-régime 2022-25 (post-DSR) ≈ 0.70**. ✓ Cas limite L15.
- **Clustering de DD** : 2023 = un seul gros épisode chop (95% des jours) qui contribue
  presque tout le drawdown -48% full-sample. ✓ Très concentré.

→ Le filtre régime EST légitime ici.

### 6.2 Persistance des épisodes (5-B)
- 18 épisodes « chop » (rv20 bottom-tercile expanding) dans 2022-2025.
- Durée médiane 13 jours, moyenne 32 jours, max 183 jours (= quasi-tout 2023).
- **5 épisodes ≥ 40 jours** (la fenêtre challenge). Ce sont les seuls qui dépassent l'horizon.
- 2023 = 95% chop ≈ un seul épisode dominant.

⚠ **N≈3-5 épisodes longs distincts.** Tout modèle d'évitement-de-chop validé sur ce dataset
est entraîné sur ~3-5 réalisations. Le warning N≈1 du brief est confirmé.

### 6.3 Gate ex-ante observable (5-A)
Pass-rate single Phase 1 par tercile :
- **vr5 low (mean-reverting bullish breakout?)** : 75.1% (n=358) ✓ > 70%
- **trend20 mid (modéré)** : 74.3% (n=261) ✓ > 70%
- **rv20 mid (vol modérée)** : 72.1% (n=262) ✓ > 70%
- vr5 high (très trending) : 60.5% (n=352) ✗
- rv20 high : 52.9% (n=119) ✗

→ Plusieurs features dégagent un tercile favorable >70% en Phase 1.

⚠ Note : vr5 LOW (donc mean-reverting au sens Lo-MacKinlay) donne le MEILLEUR pass-rate,
ce qui est contre-intuitif pour un breakout. Hypothèse : vr5<1 capture une période où la
vol_5d est moins haute que la vol_1d annualisée → vol stable, pas folle, mais pas chop.
Le mapping vr5 ↔ régime ORB-favorable n'est PAS direct/économique et donc fragile.

### 6.4 HMM Student-t walk-forward filtré (5-C) + ablation L19

| Modèle | n_states | Pass % état favorable au départ | Pass % état défavorable |
|---|---|---:|---:|
| 2-state HMM filtré | 2 | 70.5% (n=448) | 67.2% (n=534) |
| **3-state HMM filtré** | 3 | **77.4%** (n=381) | 55.1% (n=296) |

**Ablation L19 (même n=358 starts sélectionnés) :**
| Gate | Pass% | Bust% | Overlap |
|---|---:|---:|---:|
| Threshold (vr5 low tercile) | 75.1% | 21.5% | — |
| **HMM 3-state filtré** | **77.9%** | 20.1% | 38% |

**Verdict §6.4 :**
- HMM 3-state gagne **+2.8pt** sur le threshold (77.9 vs 75.1). Marginal.
- **Overlap de seulement 38%** : les deux gates pickent des starts différents → l'un des deux
  (probablement les deux) overfit à des features peu robustes.
- **Matrice de transition HMM** : P(stay good) = 0.46 (n=2) ou 0.46 (n=3) → expected dwell
  **2 jours**, P(stay good ≥14 jours) ≈ 0. **L'HMM ne capture PAS la persistance** — il flippe
  d'état tous les 2 jours, c'est de la classification de bruit, pas du modélisation de régime.
- Donc **per L19** : HMM n'apporte pas de valeur structurelle au-delà du threshold simple.
  Si on retient un filtre, on retient le threshold (vr5 low ou trend20 mid).

### 6.5 Gate régime + Chaînage P1+P2 — LE TEST DE VÉRITÉ

| Gate | n sélectionnés | p(P1) | p(P2\|P1) | **p(funded)** |
|---|---:|---:|---:|---:|
| **Aucun (baseline)** | 953 | 68.8% | 74.1% | **51.0%** |
| vr5 low tercile | 317 | 76.3% | 74.8% | **57.1%** |
| rv20 mid tercile | 244 | 74.2% | 61.3% | 45.5% |
| trend20 mid tercile | 246 | 75.6% | 73.7% | **55.7%** |
| vr5_low OR trend20_mid | 461 | 74.4% | 73.2% | 54.4% |

**Verdict §6.5 — DÉCISIF :**
- **Aucun filtre régime ne fait passer p(funded) au-dessus de 60%.**
- Le meilleur (vr5 low) → 57.1% funded. Encore **-13pt sous la cible 70%**.
- Mathématiquement : pour clear 70% funded, il faut p(P1) × p(P2) ≥ 0.70.
  En supposant p(P2|P1)=0.75 (best observé), p(P1) doit être ≥ 0.93. Le meilleur tercile
  donne 0.76. **Inatteignable depuis ce sleeve.**

---

## 7. Étape 6 — Extension données NQ futures 2008-2025 (faisabilité)

Le N≈1 sur les épisodes chop (2023) est l'objection majeure à toute conclusion régime.

**Sources évaluées :**
| Source | Coût | Effort | Qualité |
|---|---|---|---|
| firstratedata.com (NQ 1-min 2008+) | one-shot ~$200 | 1-2 jours (fetch + roll dates) | bon (continuous, ajusté) |
| IQFeed (DTN) | $120/mo + $300 backfill | 2 jours setup, recurring | très bon |
| Polygon.io | $200/mo | manual rolls, automatable | bon |
| Algoseek | $2-5K/an | clé en main | excellent |

**Ce que ça apporte :**
- 2008 GFC (mega-trend), 2009 rally, 2011 crise EUR, 2014 oil crash, 2015-16 chine,
  2018 vol shock (XIV + Q4), 2020 COVID.
- → ~5-7 épisodes additionnels chop/trend distincts.
- → portait régime de N=3-5 à N=8-12. Sortie du N≈1.

**Recommandation :** **avant toute thèse régime, fetch firstratedata.com NQ 2008-2025
(~$200, 2 jours).** Sans cela, le HMM/threshold est entraîné sur 2023 = 1 épisode, et la
sauvegarde par régime n'a aucune validité statistique.

Note : les sleeves GER40 ne bénéficient pas de NQ. Il faudrait aussi DAX 2008-2025
(Dukascopy, ~$0 mais bi5 décompression, 1 semaine d'effort).

---

## 8. Verdict final & ce qui changerait la conclusion

### 8.1 NO-GO sur le critère ≥70% single attempt

Argumentaire en cascade, du moins restrictif au plus :

1. **Sharpe brut full-sample 1.54 → DSR n_trials=18 = 0.70 → ÉCHOUE PROPFIRM 1.0.**
   Donc avant même de regarder pass-rate, la stratégie ne passe pas le gate canonique
   de la maison (L8 + L20).
2. **Pass-rate single Phase 1 honnête (audit, real-path, full 2022-25) = 68.8%.**
   Sous 70% mais proche.
3. **p(funded) chaîné P1+P2 honnête = 51% (real-path) / 45% (iid).**
   **-19 à -25pt sous la cible 70%.**
4. **Avec le meilleur filtre régime ex-ante : p(funded) = 57%.**
   Encore **-13pt sous la cible.** Le filtre achète +6pt funded ; impossible de combler 19pt.
5. **Le filtre régime est lui-même fragile** : entraîné sur ~3-5 épisodes longs, dont
   2023 (un seul gros chop) compte pour la moitié.
6. **HMM ne bat pas le threshold** (L19) : overlap 38%, expected dwell 2 jours = bruit.

→ **Verdict consolidé : NO-GO.**

### 8.2 Cas où le verdict pourrait basculer GO
1. **Fetch NQ 2008-2025 + DAX 2008-2025** (~$200 + 1-2 semaines), refit avec N=8-12 régimes
   distincts. Si le pass-rate du tercile favorable se maintient ≥75% sur les 5 fold WF,
   et si p(P2|P1) ≥85% est confirmé OOS, alors p(funded gated) → 64% — encore court mais à 6pt.
   Toujours pas 70%.
2. **Ajout d'un sleeve décorrélé positif-EV (corr ≤ 0.2)** sur un autre asset class qui
   diversifie le moteur ORB. Le rapport (REPORT_strategy2_FINAL §6) mentionne USDJPY (mais
   échoué forward), gold (negative-EV), BTC (negative-EV), AUS200/UK100/JP225 (pas de data
   intraday). C'est l'angle « √N » du rapport — pas trivial.
3. **Passage à un challenge à 1 phase seulement** (e.g. FundedNext Stellar 1-step ou
   FTMO Single-phase Standard, ~$10K, target +10% sans Verification). p(funded) = p(P1)
   directement = 68.8% sans gate, 75-77% avec gate → **proche de 70%**. À vérifier dans les
   règles 2026 : ces produits évoluent vite.
4. **Tout autre prop firm avec un drawdown trailing intraday non-cumulatif** (Apex EOD trailing):
   change la barrière du bas, ne change pas la barrière du haut +10%. Effet limité car
   le bust ici vient du floor 10% (cf. mon audit : 0% fail-daily, 32% fail-total).

### 8.3 Recommandation
1. **Ne pas acheter de challenge FTMO 2-phases en l'état.** Probabilité honnête 45-57%
   per attempt = espérance négative à $155-$250/challenge (FTMO $10K fee).
2. **Investiguer une variante 1-phase** : recalcul rapide avec target +10% seul.
   Si p(P1) gated ≥75% est confirmé sur N=8-12 régimes (post extension NQ/DAX), GO partiel.
3. **Fetch NQ 2008-2025** comme prérequis à toute thèse régime sérieuse. ~$200, 2 jours.
4. **Stress-tester p(P2|P1) explicitement** : le rapport ne le chiffre pas. Mon audit donne
   72-75%, mais c'est sur le R-pool full-sample (qui inclut 2026 cherry). Une P2 démarrée
   *juste après une P1 réussie* peut avoir une autocorrélation positive (régime favorable
   continue) ou négative (mean reversion). À tester avec real-path enchaîné par year-bucket.

---

## 9. Reproductibilité de l'audit

Scripts (dossier `data/ftmo_research/audit/`) :
- `orb_core.py` — Ré-implémentation 3-sleeve core (US100@1630 30m + GER40@1630 15m + GER40@1000 30m), avec slippage et delay paramétrables.
- `ftmo_engine.py` — Simulateur FTMO 2 modes (iid bootstrap + real-path) avec floating-equity AM/PM, block-cap 1.5%, et phase chaining.
- `step1_full_vs_2026.py` — Sharpe HAC + métriques full-sample vs 2026 (résultats : `step1_metrics.csv`).
- `step2_robustness.py` — T3 drop-top-N, T4 DSR Bailey-LdP, T5 slippage sweep, T6 delay test (output : `step2_output.txt`).
- `step3_blockboot.py` — Variance ratios, block bootstrap, conditional-on-regime pass rates, chaining (output : `step3_output.txt`).
- `step3b_weekly_2026.py` — Reproduction 2026 weekly + real-path P1+P2 chained (output : `step3b_output.txt`).
- `step5_regime.py` — Gate ex-ante par tercile, persistance régime, output `step5_output.txt`, CSV `step5A_regime_gate.csv`.
- `step5C_hmm.py` — HMM walk-forward filtré, ablation L19, transition matrix (output : `step5C_output.txt`).
- `step5D_gated_funded.py` — Combiné gate régime × chaînage P1+P2 (output : `step5D_output.txt`).

Tous seeded, déterministe. `cd audit && /usr/bin/python3 stepX.py` pour reproduire chaque étape.

---

## 10. Annexes — drapeaux d'honnêteté du rapport interne

✓ **Honnête à mon sens :**
- Section 9 "honest viability verdict" déclare bien la fragilité régime et l'écart 36-58% bust.
- Section 2 "verification log" expose les vrais bugs trouvés et fixés.
- Section 8 "forward validation" admet l'archive de USDJPY (regime artifact).
- Caveat répété sur 2026 = sample favorable non extrapolable.

✗ **Suspect ou imprécis :**
- Le « 80% en 2 essais » suppose tirages indépendants et ne couvre que la Phase 1 — silence sur la Phase 2 chaînée.
- Le « contiguous real-path » de §3 n'est pas dans le code livré (iid bootstrap pur).
- Le « 3-sleeve core » de §4 inclut GER40@16:30 qui n'est pas implémenté dans le code livré.
- L'expectancy cross-régime « ~+0.05R » est ~2× plus pessimiste que mon audit (+0.103R), inversement les Sharpe 2026 sont 15% sous l'audit. Ces écarts vont dans des directions opposées : impossible que les deux soient corrects sans une explication. Hypothèse : le rapport a appliqué un slippage agressif qui réduit 2026, mais a aussi sous-estimé l'expectancy 2022-25 (perhaps en incluant des sleeves rejetés ?).
- Le DSR (L20 du CLAUDE.md) n'est pas calculé alors qu'on est à n_trials~18 — c'est la condition de validation principale absente.

---

*Audit réalisé 2026-06-01 — Claude Code (Opus 4.7 1M ctx). Pas de re-fit massif. Tous chiffres reproductibles depuis `data/ftmo_research/audit/` avec `/usr/bin/python3`.*
