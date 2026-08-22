# Validation Baseline ORB sur NQ 2010-2026 — Exécution Propre

**TL;DR — Le verdict change radicalement sur 16 ans avec exécution propre + cost CFD live.**

| Scenario | p_funded max (0.50% sizing) | Verdict |
|---|---:|---|
| OPTIM_ftmo_2step_uncapped 2022-25 (3-sleeve, EXEC_0) | **79%** (baseline) → 95.5% (+rv20 gate) | sample-specific |
| **NQ 2010-2026 EXEC_0 CFD cost** | **37%** | **structurellement marginal** |
| **NQ 2010-2026 EXEC_NEXT_OPEN CFD cost** | **30%** | **NO-GO sur 16 ans** |
| NQ 2010-2026 EXEC_NEXT_OPEN Futures cost (FTMO interdit) | 52% | hypothétique |

**Le baseline +0.10R / SR 1.54 du précédent rapport était sample selection sur 2022-2025.** Sur 16 ans sous CFD live :
- Pré-2021 (~75% des données) : meanR -0.10 à -0.28, p_funded = **0%** dans tous les régimes.
- 2021-2026 : meanR +0.01 à +0.10, p_funded 53-100% selon régime.

**Le cost-to-R ratio explique tout.** OR range scale avec le prix de NQ (NQ 1800 en 2010 → 30000 en 2026, ×17). Cost 3 pts CFD :
- 2010 : cost / OR ≈ 0.25R (mortel)
- 2024-26 : cost / OR ≈ 0.025R (négligeable)

L'edge ORB sous CFD n'existe **structurellement que sur NQ cher**. C'est un phénomène de fenêtre, pas un edge persistent.

**Conséquence opérationnelle** : sur FTMO 2-step uncapped, NQ-only sleeve, **p_funded honnête sur 16 ans = 30%** — NO-GO franc. Le gate rv20 OOS donne +3-5pt seulement (vs +16pt in-sample revendiqué). Le ré-examen sur 16 ans confirme la primauté du gate honnêteté: **la stratégie ne tient pas sur la vraie variété de régimes**.

---

## 0. Périmètre

- **Data** : `data/raw/NQ_1min_databento_2010-2026.parquet` (5.1M bars UTC, is_rth/is_roll_day flagués).
- **Sleeve unique** : NQ ORB @ US cash open (09:30 ET = 13:30/14:30 UTC selon DST). 30-min OR (= 6 × 5-min bars).
- **Skip is_roll_day** (1.4% du data, contrats roulant tous les 3 mois).
- **Cost CFD** = 3 pts/RT (proxy US100 CFD = instrument FTMO live) ; **cost Futures** = 0.11 pts (= $2.15/$20, NQ futures direct, hors FTMO).
- **2 modèles exécution** :
  - **EXEC_0** : same-bar fill at level (legacy, optimiste)
  - **EXEC_NEXT_OPEN** : detect via close-confirmation, enter at next-bar open (clean, conservateur)

Le vrai chiffre live est entre les deux, plus proche de EXEC_NEXT_OPEN.

---

## 1. Étape 1 — Sweep sizing (16 ans, 4 sizings × 2 exec × 2 cost)

`audit/nq_step1_sizing_sweep.py` → `nq_step1_sizing_sweep.csv`.

### Table p_funded (FTMO 2-step uncapped, real-path chaîné)

| Exec | Cost | 0.50% | 0.75% | 1.00% | 1.25% |
|---|---|---:|---:|---:|---:|
| EXEC_0 | CFD 3pts | **37.2%** | 34.4% | 26.0% | 22.4% |
| **EXEC_NEXT_OPEN** | **CFD 3pts** | **30.3%** | **25.4%** | **24.0%** | **18.7%** |
| EXEC_0 | Futures 0.11pts | 65.2% | 57.5% | 48.9% | 51.2% |
| EXEC_NEXT_OPEN | Futures 0.11pts | 52.4% | 40.4% | 38.9% | 32.5% |

### Lectures clés

1. **Sous CFD live + clean exec : max p_funded = 30.3%** à 0.50% sizing. Loin du seuil 70%.
2. **Le ratio EXEC_NEXT_OPEN / EXEC_0 ≈ 0.8** : clean exec coûte ~7pt p_funded vs same-bar fill.
3. **Cost differential CFD vs Futures = ~22-28pt** à 0.50% sizing. **L'instrument détermine la viabilité.**
4. **Censure 9-12% à 0.50%** sur 16 ans (raisonnable, plus de runway disponible).

### Comparaison directe avec OPTIM_ftmo_2step_uncapped (2022-2025, 3-sleeve)

| Scenario | p_funded 0.50% |
|---|---:|
| Précédent rapport (3-sleeve US100 CFD 2022-25, EXEC_0) | **79%** |
| NQ 2010-2026 EXEC_0 CFD | **37%** |
| NQ 2010-2026 EXEC_NEXT_OPEN CFD | **30%** |
| Diff CFD: 79% → 30% | **−49pt** |

Le `−49pt` se décompose grossièrement :
- 3-sleeve → 1-sleeve : −15 à −20pt (perte de diversification)
- Sample 2022-25 → 2010-26 : −25 à −30pt (régime-mix)
- EXEC_0 → EXEC_NEXT_OPEN : −7pt

---

## 2. Étape 2 — Décomposition par régime (11 épisodes)

`audit/nq_step2_regime.py` → `nq_step2_regime.csv`.

### Sous EXEC_NEXT_OPEN + CFD 3pts (le scénario FTMO honnête)

| Régime | n_trades | mean_R | cost/R | p_phase1 | p_funded | MaxDD | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| 2010-12 recovery | 637 | **-0.260** | 0.245 | 0% | **0%** | -73% | mort |
| 2013-14 QE trend | 485 | **-0.275** | 0.211 | 0% | **0%** | -64% | mort |
| 2015-16 China chop | 373 | **-0.211** | 0.132 | 0.3% | **0%** | -49% | mort |
| 2016H2-17 trend | 371 | -0.158 | 0.167 | 5% | **0%** | -37% | mort |
| 2018 vol shock | 247 | -0.069 | 0.076 | 0% | **0%** | -16% | mort |
| 2019 dovish pivot | 243 | -0.096 | 0.089 | 0% | **0%** | -22% | mort |
| 2020 COVID | 253 | -0.088 | 0.039 | 0% | **0%** | -16% | mort |
| 2021 recovery | 245 | +0.009 | 0.037 | NaN | NaN (cens) | -7% | borderline |
| **2022 bear** | 249 | **+0.093** | 0.024 | **100%** | **100%** | -8% | live |
| **2023 chop** | 248 | +0.026 | 0.038 | NaN | NaN (cens) | -9% | borderline |
| **2024-26 bull** | 604 | **+0.067** | 0.026 | 87% | **53%** | -14% | live |

### Le mécanisme révélé : cost-to-R ratio

Le cost CFD (3 pts) est constant, mais OR range scale avec le prix de NQ. Sur 16 ans, NQ passe de ~1800 à ~30000 :
- 2010-2017 : cost / OR median = 0.13 à 0.25 → **un trade neutre devient un gros perdant après cost**.
- 2018-2020 : cost / OR = 0.04 à 0.08 → cost commence à être absorbable.
- 2021-2026 : cost / OR = 0.02 à 0.04 → cost négligeable.

→ **L'edge ORB de "+0.10R" mesuré sur 2022-2025 N'EST PAS un edge stratégie, c'est un edge instrument-prix** : ORB sur NQ à 25000 a un cost relatif 10× plus faible qu'ORB sur NQ à 2000. Sous-jacent identique, prix multiplié par 10 → "edge net de cost" multiplié par ~10.

### Sous Futures cost (sensibilité)

| Régime | mean_R Futures | p_funded Futures |
|---|---:|---:|
| 2010-12 recovery | -0.002 | 24% |
| 2013-14 QE | -0.04 | 0.4% |
| 2015-16 China | -0.06 | 0% |
| 2024-26 bull | +0.10 | 66% |

Même avec cost futures (0.11 pts), p_funded ne franchit 70% dans aucun régime. **L'edge ORB sur NQ est faible même sans cost.** Le cost CFD en plus le détruit.

---

## 3. Étape 3 — Gate rv20 OOS test (le test clé)

`audit/nq_step3_gate_oos.py` → `nq_step3_gate_oos.csv`.

### Ablation L19 : rv20_mid gate vs no-gate sur NQ 2010-2026

| Risk | BASE p_funded | MID gate Δ OOS | LOW gate Δ | HIGH gate Δ |
|---:|---:|---:|---:|---:|
| 0.50% | 30.3% | **+4.8pt** | -4.1pt | +1.0pt |
| 0.75% | 25.4% | **+2.7pt** | -1.6pt | +0.2pt |
| 1.00% | 24.0% | +0.4pt | +2.3pt | -1.6pt |
| 1.25% | 18.7% | +0.6pt | -0.7pt | +1.0pt |

### Control sur 2022-2025 subset (NQ only)

| Risk | BASE | rv20_mid | Δ |
|---:|---:|---:|---:|
| 0.50% | 100% | 100% | +0.0pt (saturé) |
| 0.75% | 83.1% | 86.0% | +2.8pt |
| 1.00% | 67.8% | 71.8% | +3.9pt |
| 1.25% | 57.5% | 57.9% | +0.4pt |

### Verdict §3

- **Le rv20_mid gate OOS donne +3-5pt sur 0.50-0.75% sizing**.
- C'est cohérent avec ce qu'il donne in-sample 2022-25 (~3pt) — donc le gate **ne s'effondre PAS** OOS sur 16 ans.
- **MAIS** : son effet absolu (+3-5pt) est très loin du +16pt revendiqué dans OPTIM_ftmo_2step_uncapped, parce que le +16pt était mesuré sur 3-sleeve pooled, pas NQ-only.
- **Le gate ne sauve pas la stratégie** : 30% + 4.8 = **35% au mieux**, toujours loin de 70%.

→ **Cohérent avec le prior Cowork** (features daily prédisent μ_ORB à 52% ≈ pile ou face) — le gate a un effet marginal, pas transformatif.

---

## 4. Étape 4 — WF maximin par régime

`audit/nq_step4_wf_maximin.py` → `nq_step4_wf_*.csv` + `nq_step4_output.txt`.

11 régimes = 11 folds naturels = vraie diversification (vs précédent 5 folds contigus sur 4 ans).

### Sous EXEC_NEXT_OPEN + CFD cost (FTMO live)

| Risk | FULL p_funded | WF Mean | **WF Min** | Régime au min |
|---:|---:|---:|---:|---|
| 0.50% | 30.3% | 12.5% | **0.0%** | 7+ régimes à 0 |
| 0.75% | 25.4% | 17.1% | **0.0%** | 7+ régimes à 0 |
| 1.00% | 24.0% | 19.2% | **0.0%** | 4+ régimes à 0 |
| 1.25% | 18.7% | 19.5% | **0.0%** | 4+ régimes à 0 |
| 1.50% | 15.5% | 18.4% | **0.0%** | 3+ régimes à 0 |

### Per-régime p_funded à 1.00% sizing (le plus généreux par WF mean)

| Régime | p_funded | Verdict |
|---|---:|---|
| 2010-12 recovery | **0%** | mort |
| 2013-14 QE | **0%** | mort |
| 2015-16 China | **0%** | mort |
| 2016H2-17 | 3.4% | quasi-mort |
| 2018 vol shock | 0% | mort |
| 2019 dovish | 0% | mort |
| 2020 COVID | 0% | mort |
| 2021 recovery | NaN | trop court ou censuré |
| 2022 bear | 84% | live |
| 2023 chop | 47.8% | live |
| 2024-26 bull | 56.8% | live |

### Sous Futures cost (sensibilité)

À cost 0.11pts, WF mean monte à 25-40%, mais WF min reste 0-3%. Même les "vrais" coûts NQ futures ne sauvent pas la stratégie sur 16 ans.

### Verdict §4

- **Le WF min sur 16 ans est 0% à tous les sizings testés sous cost CFD**. Cela veut dire qu'il existe **au moins 7 régimes sur 11** où la stratégie échoue complètement (p_funded = 0%).
- **Argmax mean WF = 1.25% (19.5% pass moyen)**. Toujours bien sous 70%.
- **Argmax maximin = trivial** : tous les sizings donnent min=0%, donc tous sont également mauvais en worst-case.
- **Mean vs maximin divergent : OUI** — mais ils convergent tous deux vers "la stratégie ne marche pas". Le mean choisit 1.25% (sizing rapide pour limiter exposure), le maximin reste à 0%.

**Pas de sizing robuste possible sur 16 ans.**

---

## 5. Verdict final

### 5.1 Le baseline honnête sur 16 ans est marginal

Sous l'execution propre (next-bar-open) et cost CFD (= FTMO live) :
- **p_funded max sur 16 ans = 30%** (à 0.50% sizing).
- **Sur 7 régimes / 11 (= toute la période pré-2021), p_funded = 0%**.
- **Sur 4 régimes (2022-2026), p_funded = 53-100%**.

### 5.2 L'edge n'est PAS structurel — c'est instrument-prix dépendant

Le cost CFD (3 pts) en pourcentage du OR range varie de 0.025R (NQ@30000) à 0.25R (NQ@1800). Le baseline mean R est entièrement déterminé par ce ratio :
- 2010-2017 : mean R -0.16 à -0.28 → strategy dies under cost
- 2024-26 : mean R +0.07 à +0.10 → strategy viable

**Le "edge ORB" est un edge cost-relatif. Quand NQ devient cher, l'edge apparait.** Ce n'est pas une signature structurelle de l'auction microstructure ; c'est un coincidence prix-cost.

### 5.3 Le verdict du précédent rapport (95.5% p_funded à 0.50% + rv20 gate) était sample-specific

- Mesuré sur 2022-2025 = exactement le sample favorable + 3-sleeve diversifié.
- Sur 16 ans NQ-only : **30% baseline + 4.8pt gate = 35%**. Pas 95.5%.

### 5.4 Recommandation actionnable

**Pour FTMO 2-step uncapped sur ORB indices CFD :**

1. **NE PAS deployer** sous l'hypothèse 79-95% p_funded. Le vrai chiffre live est ~30%.
2. **L'edge est sample-conditional** : ne marche que si NQ reste cher (cost-to-R faible). Pas robuste à un crash type 2008.
3. **Option robuste possible** : reformer la stratégie pour utiliser des thresholds en pourcentage du prix (= cost-to-R stable), pas en points absolus. Mais le test de robustesse à 16 ans casse même cette idée — le mean R est négatif sur 2010-2017 même en normalisant.
4. **Alternative** : NQ futures directs (cost 0.11 pts) donneraient 52% p_funded — mais FTMO interdit les futures CME.

**Le verdict honnête : ORB ne passe pas FTMO 2-step uncapped sur 16 ans sous CFD live cost.** L'optimisme des rapports précédents reposait sur sample selection à un moment où NQ était au sommet.

### 5.5 Leçons méthodologiques

1. **N≈1 régime warning persistant** : le 2023 chop était relativement gentil (mean R +0.03). Les vrais chops 2010-2017 sous cost CFD donnent mean R **−0.21 à −0.28** — c'est ça le tail event de régime, pas 2023.
2. **Sample selection sur période bénigne** : tous les rapports antérieurs (audit, optim, optim 2-step uncapped) étaient sur 2022-2025 = exactement le sample où NQ était assez cher pour que cost-to-R devienne négligeable.
3. **Le cost-to-R ratio comme métrique de pré-flight** : devrait être calculé sur toutes les stratégies intraday breakout sur instruments à prix variable. Un cost-to-R > 0.05 disqualifie probablement la stratégie sur cet instrument à ce niveau de prix.
4. **Le "+16pt rv20 gate" annoncé OPTIM_ftmo_2step_uncapped était fragile** : sur NQ-only, c'est +3-5pt. Le 3-sleeve aggregation a probablement amplifié l'effet via réduction de variance, mais l'effet structurel est plus faible.

---

## 6. Reproductibilité

Tous scripts dans `data/ftmo_research/audit/` :

| Étape | Script | Sortie |
|---|---|---|
| 0 — NQ loader | `nq_orb_backtest.py` | `nq_trades_EXEC_0.parquet`, `nq_trades_EXEC_NEXT_OPEN.parquet`, `nq_orb_sanity_output.txt` |
| 0 — Simulator | `nq_sim.py` | Module utilitaire |
| 1 — Sizing sweep | `nq_step1_sizing_sweep.py` | `nq_step1_sizing_sweep.csv` + `nq_step1_output.txt` |
| 2 — Régime decomp | `nq_step2_regime.py` | `nq_step2_regime.csv` + `nq_step2_output.txt` |
| 3 — Gate OOS | `nq_step3_gate_oos.py` | `nq_step3_gate_oos.csv` + `nq_step3_output.txt` |
| 4 — WF maximin | `nq_step4_wf_maximin.py` | `nq_step4_wf_*.csv` + `nq_step4_output.txt` |

Data : `data/raw/NQ_1min_databento_2010-2026.parquet`.

Tous seeded, déterministes. `cd audit && /usr/bin/python3 nq_stepX.py`.

---

## 7. In-sample vs OOS marquage explicite

| Chiffre | Source | Statut |
|---|---|---|
| Baseline meanR +0.10R 2022-25 (audit step1) | US100 CFD 3-sleeve | **in-sample favorable** |
| Baseline p_funded 79% à 0.50% uncapped 2022-25 | OPTIM_ftmo_2step_uncapped | **in-sample favorable** |
| Gate rv20_mid +16pt 2022-25 | OPTIM_ftmo_2step_uncapped step10 | **in-sample, 3-sleeve, favorable** |
| **NQ baseline meanR -0.11 2010-2026** | step1 ici | **OOS extension** |
| **NQ p_funded 30% sur 16y** | step1 ici | **OOS extension** |
| NQ gate +4.8pt OOS | step3 ici | **OOS confirmé mais marginal** |
| Cost-to-R ratio déterministe | step2 ici | **explication mécanique** |
| **Live performance** | — | **0 jour** |

---

*Validation 2010-2026 réalisée 2026-06-01 — Claude Code (Opus 4.7 1M ctx). Single sleeve NQ proxy US100. EXEC_NEXT_OPEN + CFD cost = scénario FTMO live honnête. Verdict : 30% p_funded sur 16 ans, NO-GO franc.*
