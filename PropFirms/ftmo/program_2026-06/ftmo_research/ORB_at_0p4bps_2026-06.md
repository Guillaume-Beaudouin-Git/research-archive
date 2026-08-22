# ORB V2+E7 — Re-test sous hypothèse de coût 0.4 bps RT (2026-06-03)

**Statut de l'hypothèse 0.4 bps** : mesure réelle de fills aller-retour sur US100.cash FTMO démo, **mais à ~18h Paris (session calme, spread serré) — PAS à 15h30 (l'open, où l'ORB entre réellement et où le spread est le plus large)**. **0.4 bps est une BORNE HAUTE optimiste**, à traiter comme telle. Le coût réel à l'open est en cours de mesure séparément. **Ne PAS relire ce résultat plus tard comme "le coût ORB confirmé".**

**Ledger canonique** : `data/ftmo_research/audit/nq_v2_trades.parquet` (4013 trades V2 baseline, NQ databento 2010-2026). Spec **FIGÉE V2+E7** : OR 30min, stop=côté opposé (1R), E7 trail-to-BE après +1R sinon close RTH, V2 filtre OR≥10bps, flat overnight. **Aucune modification du signal** (L10/L19 respect).

**Approche** : re-coût trade-by-trade par interpolation linéaire des colonnes `r_1bps` et `r_2bps` du ledger (canonical) ; ajout du **lift E7 = +0.015 R/trade** (doc4 ORB_reconciliation_2026-06.md l.224). Aucun re-fit, aucun mining.

---

## Étape 1 — mean_R @ 0.4 bps + monotonie

### Cost grid V2+E7 sur ledger canonical (4013 trades)

| cost_bps | V2 baseline mean_R | V2+E7 mean_R | doc4 référence (E7) |
|---:|---:|---:|---:|
| 0.0 (gross) | +0.0492 | +0.0642 | — |
| **0.4** | **+0.0402** | **+0.0552** | (this study) |
| 1.0 | +0.0267 | +0.0417 | — |
| 2.0 | +0.0042 | +0.0192 | +0.020 ✓ |
| 3.0 | -0.0182 | -0.0032 | -0.003 ✓ |
| 4.0 | -0.0407 | -0.0257 | — |

- **Monotonie confirmée** : à coût croissant, mean_R décroît ; 0.4 bps donne mean_R **> 1 bps > 2 bps > 3 bps**. Pas d'anomalie.
- **Reproduction doc4** : @ 2bps = +0.019 (doc4 +0.020) ; @ 3bps = -0.003 (doc4 -0.003) — match à la décimale.
- À 0.4 bps : **mean_R = +0.0552**, hit_rate = 45%, std = 1.20, skew = +1.66, kurt = +6.7, min = -1.094, max = +13.74.

### Year-by-year mean_R @ 0.4 bps (V2+E7) — fragilité régime

| Année | n_trades | mean_R | hit_rate | Année | n_trades | mean_R | hit_rate |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2010 | 144 | **−0.0036** ❌ | 47.2% | 2018 | 252 | +0.0301 | 39.3% |
| 2011 | 253 | +0.0541 | 46.6% | 2019 | 249 | +0.0444 | 45.8% |
| 2012 | 247 | +0.0879 | 43.3% | 2020 | 254 | +0.0059 | 44.9% |
| 2013 | 244 | **−0.0268** ❌ | 41.8% | 2021 | 253 | +0.0750 | 50.6% |
| 2014 | 244 | +0.0094 | 43.0% | 2022 | 253 | +0.1294 | 48.6% |
| **2015** | 254 | **−0.0867** ❌ | **38.6%** | 2023 | 251 | +0.1323 | 46.6% |
| 2016 | 251 | +0.0216 | 41.0% | 2024 | 255 | +0.1917 | 48.2% |
| 2017 | 253 | +0.0871 | 44.3% | 2025 | 252 | +0.0867 | 47.2% |
| | | | | 2026 partial | 104 | +0.0923 | 53.8% |

- **3 / 17 années négatives** (2010, 2013, **2015**) — à 0.4 bps, le régime tue 18% des années. Moins sévère qu'à 3 bps (où on aurait 6+ années négatives), mais **2015 reste à -0.087 R/trade : un candidat ouvert dans ce régime ferait face à une P1-pass effondrée**.
- Performance dominée par **2022-2024** (+0.13 / +0.19 R/trade) — bull régime tardif.

### Tag régime
| Tag | n_trades | mean_R | hit_rate |
|---|---:|---:|---:|
| trending | 2877 | +0.0712 | 46.2% |
| vol_shock | 506 | +0.0180 | 42.1% |
| chop | 630 | +0.0121 | 41.9% |

Trending domine l'edge ; chop et vol_shock proches de zéro même à 0.4 bps.

---

## Étape 2 — MC FTMO 2-step block-bootstrap @ 0.4 bps

**Règles SETTLED** : Phase 1 +10% / Phase 2 +5% ; daily 5% (anchored midnight balance) ; floor STATIQUE $9k sur $10k (max total −10%) ; **no time limit** (max 5 ans/phase pratique) ; account $10k initial ; sizing = % du capital initial (fixed dollar risk). Block bootstrap 21-trade blocks (≈1 mois), 12000 paths/phase.

### Real ORB V2+E7 @ 0.4 bps

| Sizing | P1 pass | P1 bust | **p(funded)** | overall bust | médiane jours P1 si pass | médiane jours total si funded |
|---:|---:|---:|---:|---:|---:|---:|
| 1.0% | 72.3% | 27.7% | **57.8%** | 42.2% | 63 | 89 (~4 mois) |
| 1.5% | 64.4% | 35.6% | **48.2%** | 51.8% | 31 | 44 (~2 mois) |
| 2.5% | 58.2% | 41.8% | **40.1%** | 59.9% | 13 | 19 (~1 mois) |

À sizing 1%, **médian temps total ≈ 4 mois**. À 2.5%, ~1 mois mais bust 60%.

---

## Étape 3 — Décomposition placebo (mean / vol / skew matched)

### Placebos générés (même container FTMO, mêmes règles)

| Placebo | μ | σ | skew | Description |
|---|---:|---:|---:|---|
| A — Gauss zero-μ | 0.0 | 1.20 | 0 | Pas d'edge ; pure math container (unlimited time + DLL 5% + floor 10%) |
| B — Gauss μ+σ matched | +0.0552 | 1.20 | 0 | Edge gaussien sans skew/clustering |
| C — Skew-normal fit | +0.253* | 0.99 | +1.01 | Fit MLE déformé (mean 4.6× réel) — **non fiable**, ignoré |

(*) le `skewnorm.fit` MLE déforme la mean — α=111 inflate considérablement le first moment. Le placebo C est exclu de l'interprétation.

### p(funded) par placebo (sizing 1%)

| Bloc | p(funded) | vs zero-μ container math |
|---|---:|---:|
| **Real ORB V2+E7 @ 0.4 bps** | **57.8%** | **+33.4 pts** |
| Placebo B (μ+σ matched Gauss) | 52.1% | +27.7 pts |
| Placebo A (zero-μ Gauss) | 24.4% | — (baseline container) |

Décomposition :
- **Container math pure (Placebo A) = 24.4%** — c'est le "free lunch" du conteneur FTMO 2-step unlimited-time + floor statique. Avec aucun signal, ~1 candidat sur 4 passe purement par dérive variance ascendante.
- **Edge de mean drift (PlcB − PlcA = +27.7 pts)** — c'est le gain de mean_R positif (+0.055) si on assume Gaussian.
- **Edge de skew/kurt/clustering (Real − PlcB = +5.7 pts)** — la skew positive (+1.66) et le clustering régime ajoutent un PETIT gain au-dessus du Gaussien matched. C'est marginal vs le mean drift.

**Lecture** : le signal ORB ajoute **+33 pts au-dessus du container math** à sizing 1% ; **l'essentiel du gain vient du mean drift positif, pas de la structure non-gaussienne**.

---

## Étape 4 — Cost sensitivity (FONDAMENTALE pour le verdict)

Le chiffre 0.4 bps est borne haute. Voici comment p(funded) évolue à mesure que le coût remonte vers le réaliste à l'open (15h30) :

| Coût bps | mean_R | p(funded) 1% | p(funded) 1.5% | p(funded) 2.5% | vs placebo 24% |
|---:|---:|---:|---:|---:|---:|
| **0.4 (optimiste, hors-open)** | +0.0552 | **57.8%** | 48.5% | 41.1% | **+33 pts signal** |
| 1.0 | +0.0417 | 51.3% | 44.4% | 38.4% | +27 pts |
| 2.0 (historique median) | +0.0192 | 41.1% | 37.6% | 33.9% | +17 pts |
| **3.0 (conservatif)** | **−0.0032** | **31.5%** | 30.9% | 29.6% | **+7 pts (signal s'efface)** |
| 4.0 | −0.0257 | 23.4% | 24.8% | 25.9% | ≈ placebo (signal mort) |
| 6.0 (CFD retail open) | −0.0706 | 11.6% | 15.9% | 19.1% | EN-DESSOUS placebo |

**Placebo zero-μ référence (sizing 1.0%) = 29.3%** ; à 2.5% = 20.5%.

### Lecture critique

> À **0.4 bps**, l'edge est franchement positif : +33 pts au-dessus du placebo container. Le coût ne tue PAS l'edge à ce niveau.
>
> Mais dès qu'on atteint **3 bps** (estimation conservative pour open NQ futures avec slippage 09:30 ; cf. L19 NQ market impact), **mean_R bascule sous zéro et p(funded) se replie au niveau du placebo container math (≈ 30%)**. Le signal devient indistinguable du bruit no-bust.
>
> Donc le résultat 58% à 0.4 bps **n'est PAS un résultat ORB tenable** : il dépend critiquement de la mesure du coût RÉEL à l'open. À l'open, 0.4 bps est très probablement faux.

### Stress 2015 (worst year)

| Sizing | P1 pass | P1 bust |
|---:|---:|---:|
| 1.0% | **9.5%** | 90.5% |
| 1.5% | 18.1% | 81.9% |
| 2.5% | 32.2% | 67.8% |

→ Si le candidat ouvre son challenge dans un régime "chop/sideways" comme 2015, **P1 pass s'effondre à <10%**. Le 58% global moyenne sur 16 ans, mais la dispersion régime est massive.

---

## Verdict en 2 niveaux SÉPARÉS

### (a) Le COÛT à 0.4 bps ne tue PAS l'edge

Au coût hypothétique de 0.4 bps (mesure 18h Paris session calme) :
- mean_R V2+E7 = **+0.0552 R/trade** (positif, monotone vs grille).
- p(funded) FTMO 2-step unlimited-time = **58% à sizing 1%**, **+33 pts au-dessus du placebo container math (24%)**.
- Le signal ORB est **réel et bien identifié** à ce niveau de coût.

### (b) Le RÉGIME et le COÛT RÉEL plafonnent quand même p(funded) ~30%

1. **0.4 bps est une borne haute optimiste** : mesure à 18h (calme), pas à 15h30 (open, spread le plus large).
2. **Coût attendu à l'open** : NQ futures direct 3 bps RT (cf. L19, $4.68 RT comm + 2 bps slippage 09:30) ; CFD US100 retail 6-10 bps. **À 3 bps : p(funded) = 31.5% ≈ placebo container math 29.3%** → **le signal s'efface dans le bruit du conteneur**.
3. **Régime fragility** : 3/17 années négatives, **2015 → P1 pass 9.5%** à sizing 1%. La moyenne 16 ans MASQUE la dispersion régime.
4. **Container math pure** = 24% (placebo zero-μ) — c'est le "ceiling" sans edge. Avec coût réaliste, on revient à ce ceiling.
5. **~80% du gain à 0.4 bps vient du mean drift positif** (Real − PlcA décomposé : +33 pts dont +28 pts via PlcB μ-matched, seuls +6 pts via skew/clustering). À coût réaliste, le mean drift devient nul ou négatif → l'edge s'évapore mécaniquement.

→ **Le 58% à 0.4 bps n'est PAS un résultat exploitable**. Il dépend totalement d'une mesure de coût optimiste. **Le ceiling régime ~33%** (référence ORB_reconciliation_2026-06.md : "p(funded) FTMO 2-step full sample = 33%") **est respecté dès que le coût atteint le coût mesuré réaliste à l'open**.

---

## Rappel explicite

> **0.4 bps = mesure de fills aller-retour sur US100.cash démo, fenêtre ~18h Paris (session US calme, spread serré).** L'ORB entre à **15h30 Paris (open RTH NY 09:30 ET)** où le spread est le plus large et l'OFI le plus volatil. **Le coût à l'open n'est PAS encore mesuré** ; la mesure est en cours séparément. **Ce résultat de 58% ne doit PAS être cité comme "le p(funded) ORB" sans avoir confirmé le coût à l'open. À ce stade : VERDICT INCERTAIN, dépend de la mesure 15h30.**

### Vérification à effectuer (DOIT être faite avant déploiement)

1. Mesurer le spread bid/ask sur US100.cash **à 15h30, 15h33, 15h35 EET** (rolling 5 sessions ≥20 trades chacune, capture MT5 spread_points).
2. Mesurer le slippage **market order** à l'open vs mid-price théorique.
3. Convertir en bps RT : `bps_RT = (spread_points + slip_points) / price × 1e4 × 2`.
4. Si bps_RT > 2.5 → p(funded) chute sous ceiling régime → re-classer NO-GO.
5. Si bps_RT ≤ 1 → mean_R reste positif → ré-examiner sérieusement.

---

## Artéfacts

- `data/ftmo_research/audit/orb_at_0p4bps_step1.py` — re-coût trade-by-trade + year stratification
- `data/ftmo_research/audit/orb_at_0p4bps_step2_mc.py` — MC FTMO 2-step + placebos A/B/C
- `data/ftmo_research/audit/orb_at_0p4bps_step3_cost_sensitivity.py` — sweep coût + stress 2015
- `data/ftmo_research/audit/orb_v2e7_cost_grid_0p4.csv` — grille coût
- `data/ftmo_research/audit/orb_v2e7_0p4bps_per_trade.parquet` — série per-trade @ 0.4 bps
- `data/ftmo_research/audit/orb_at_0p4bps_mc.csv` — sortie MC réelle + placebos
- `data/ftmo_research/audit/orb_at_0p4bps_cost_sweep.csv` — sweep coût
- Logs : `data/ftmo_research/audit/orb_at_0p4bps_step{1,2,3}_log.txt`

### Cohérence avec memory existante

- Cohérent avec [`orb_realconstraints_2026-06`] : "placebo Gaussian zero-mean+floor=97.7% prouve K5 100% n'est PAS un ORB edge mais math no-bust × unlimited-time" → ici, le placebo Gaussian zero-μ static-floor donne **24%** (vs 97.7% en floor_taper). Le floor STATIQUE plombe vraiment la math container, sans floor_taper. ORB ajoute +33 pts au-dessus, mais s'évapore au coût réaliste.
- Cohérent avec ORB_reconciliation_2026-06.md : ceiling p(funded) 32-34% full sample à coût propfirm réaliste — confirmé ici à 3 bps (31.5%).
- Cohérent avec L19, L20, L21, L24 : coût NQ futures direct 3 bps RT à l'open ; DSR 0.70 < gate ; lumpy momentum mal-fit symmetric barrier ; sprint <2mo impossible (mais ici unlimited time bypassé).
