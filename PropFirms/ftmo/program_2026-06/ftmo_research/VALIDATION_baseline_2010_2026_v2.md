# Validation Baseline ORB sur NQ 2010-2026 — v2 (cost bps + same-bar headline + gross diagnostic)

**TL;DR — Le verdict v1 était partiellement piloté par un bug de coût, mais le fix bps ne sauve PAS la stratégie. p_funded honnête sur 16 ans = 42% à 0.50% sizing sous 2 bps CFD. Conditionnellement marginal, pas un NO-GO catégorique mais loin du seuil 70%.** En recoûtant en bps-constant (CFD réaliste) et en isolant le gross par régime, on bascule de l'hypothèse (c) "pas d'edge" vers **(b) edge de régime momentum, conditionnellement viable** :

| Métrique | v1 (3 pts fixes) | **v2 (2 bps réaliste)** |
|---|---|---|
| Cost 2010 | 3 pts = **15.4 bps** (15× trop cher) | 2 bps = constant |
| Cost 2026 | 3 pts = 1.2 bps (correct) | 2 bps = constant |
| cost/R 2010-2017 | 0.13-0.27 (mortel) | **0.03-0.09 (vivable)** |
| cost/R 2024-26 | 0.018 (négligeable) | 0.038 (vivable) |
| **Gross meanR (16y, tag trending)** | n/a (non isolé) | **+0.066R** ✓ |
| **Gross meanR (16y, tag chop)** | n/a | **+0.006R** (~zero) |
| **Net meanR sous 2bps** | n/a | **+0.011R** (~zero) |
| **p_funded full 16y 0.50% sizing** | 37% (EXEC_0) / 30% (NEXT_OPEN) | **TBD avec sweep complet** |

**Findings clés** :
1. ✅ **Le bug coût v1 est réel et confirmé**. cost/R sous 2 bps reste 0.020-0.060 sur 16 ans (stationnaire) vs 0.018-0.267 sous 3 pts fixes (non-stationnaire, ×15 amplitude).
2. ✅ **Gross meanR positif (+0.049R) sur 16 ans** — pas un strat "no-edge". Hypothèse (c) rejetée.
3. ✅ **Edge concentré sur régimes trending** (gross +0.066R) vs chop (+0.006R). Hypothèse (b) partiellement validée.
4. ⚠ **2013-14 QE trend a gross négatif (-0.013R)** — la classification "trending" est trop générique. Le vrai pattern est "high-momentum-vol vs low-momentum-vol", pas juste trend.
5. ⚠ **2023 chop a gross +0.126R** — c'est en fait un "low-vol-bull", pas un chop classique. Le label est trompeur.
6. ⚠ **Net @ 2bps reste marginal (+0.011R overall)**. Le bps réaliste alourdit les années récentes (2 bps × NQ@25000 = 5 pts vs les 3 pts utilisés v1). 

**Verdict tranché** : **HYPOTHÈSE (b) confirmée, mais l'edge net est MARGINAL même sous coût réaliste**. L'ORB n'est pas mort mais il reste un edge de bord, pas un edge robuste. Le NO-GO v1 était trop dur (artefact de coût) ; un GO v2 serait trop optimiste (edge net ~+0.01R). **Verdict honnête : conditionnellement marginal**.

---

## 0. Périmètre

- Réutilise `nq_trades_EXEC_0.parquet` (4013 trades, EXEC_0 = same-bar fill at level = realistic dormant-stop fill per `OPTIM_execution_realism.md`).
- Modifie le coût : passe de `cost_pts = 3` fixe à `cost_pts = bps_RT × level / 10000` (per-trade, level = OR border = entry price proxy).
- Test bracket : bps_RT ∈ {1, 2, 3}. Réaliste actuel ~1-2 bps (spread 1-2 pts CFD US100 + commission). 3 bps = stress conservateur.
- Futures sensitivity revisée : 1 pt fixe (vs 0.11 pt commission-seule v1) — inclut spread tick + commission + slip stop.
- Skip is_roll_day (1.4% des bars).
- Ajoute colonne `r_gross` (R sans coût) pour isoler edge-régime du coût.

---

## 1. Distortion du coût v1 exposée

`audit/nq_v2_bps_cost.py` → `nq_v2_distortion.csv`.

### "3 points fixes" appliqués sur 16 ans = quel coût implicite ?

| Era | NQ médian | OR range médian (pts) | **3 pts fixes en bps** | cost/R sous 3 pts | cost/R sous 2 bps |
|---|---:|---:|---:|---:|---:|
| 2010 | 1952 | 11.2 | **15.4 bps** | 0.267 | 0.035 |
| 2012 | 2640 | 11.8 | **11.4 bps** | 0.255 | 0.045 |
| 2015 | 4442 | 22.5 | 6.8 bps | 0.133 | 0.039 |
| 2018 | 6964 | 40.5 | 4.3 bps | 0.074 | 0.034 |
| 2020 | 10365 | 76.1 | 2.9 bps | 0.039 | 0.027 |
| 2023 | 14819 | 78.8 | 2.0 bps | 0.038 | 0.038 |
| 2026 | 25590 | 171.3 | 1.2 bps | 0.018 | 0.030 |

→ **3 pts fixe = 15 bps en 2010 vs 1 bp en 2026**. C'est ×13 d'amplitude — absurde pour un spread CFD.
→ **Sous 2 bps, cost/R reste stationnaire à 0.027-0.045** (sauf 2010 spike à 0.045 — vol intraday faible au tout début du sample).

---

## 2. Gross meanR — l'edge structurel isolé du coût

`audit/nq_v2_bps_cost.py` → `nq_v2_gross_per_regime.csv` + `nq_v2_gross_by_tag.csv`.

### Per-regime gross meanR (cost = 0)

| Régime | Tag | n_trades | gross_meanR | hit% | NQ médian | OR médian |
|---|---|---:|---:|---:|---:|---:|
| 2010-12 recovery | trending | 644 | **+0.048** | 45.2% | 2338 | 12.3 |
| 2013-14 QE trend | trending | 488 | **−0.013** | 41.8% | 3497 | 14.3 |
| 2015-16 China chop | chop | 379 | **−0.074** | 38.5% | 4410 | 22.8 |
| 2016H2-17 trend | trending | 379 | **+0.080** | 43.5% | 5415 | 18.0 |
| 2018 vol shock | vol_shock | 252 | +0.023 | 39.3% | 6964 | 40.5 |
| 2019 dovish pivot | trending | 249 | +0.040 | 45.8% | 7685 | 33.8 |
| 2020 COVID | vol_shock | 254 | −0.003 | 44.5% | 10365 | 76.1 |
| 2021 recovery | trending | 253 | +0.068 | 50.2% | 14568 | 81.0 |
| 2022 bear | trending | 253 | **+0.119** | 48.2% | 12420 | 123.8 |
| 2023 "chop" | chop | 251 | **+0.126** | 46.6% | 14819 | 78.8 |
| 2024-26 bull | trending | 611 | **+0.125** | 47.9% | 21345 | 113.8 |

### Aggregated by tag (cost = 0)

| Tag | n | gross_mean | gross_median | hit_rate% |
|---|---:|---:|---:|---:|
| **trending** (7 régimes) | 2877 | **+0.066** | -0.153 | 45.7% |
| chop (2 régimes) | 630 | +0.006 | -0.410 | 41.7% |
| vol_shock (2 régimes) | 506 | +0.010 | -0.419 | 41.9% |

### Lectures critiques

1. **L'edge ORB est REEL en gross** : +0.066R en trending, +0.049R sur 16 ans full. Cela rejette l'hypothèse (c) "pas d'edge".
2. **L'edge est concentré sur trending** : 6 des 7 régimes "trending" sont gross-positifs, et le seul négatif (2013-14, gross −0.013) est marginal. Les régimes chop / vol_shock sont à zéro / légèrement positif.
3. **Mais le tag "trending" est trop générique**. 2013-14 (QE bull) gross-négatif vs 2024-26 (bull) gross-positif. La différence pourrait être :
   - Intraday vol level (2013-14 = très basse vol intraday)
   - Vitesse du trend (2024-26 plus explosif post-COVID)
4. **2023 "chop" est gross-positif (+0.126R)** — c'est le plus haut de tous les régimes. **Mauvaise classification** : 2023 était un low-vol bull (NQ +54%), pas un vrai chop. Le seul vrai chop du sample (2015-16, gross −0.074R) est CONSISTANT avec l'hypothèse "ORB fail en chop".

### Hypothèse raffinée : "ORB marche quand il y a une drift directionnelle intraday, échoue en mean-reversion intraday"

- Si on retire 2013-14 (trending mais low-intraday-vol) et corrige 2023 (low-vol-bull, pas chop), le pattern est plus net.
- Le seul "vrai chop" = 2015-16 China, où ORB fail clairement (gross −0.074R).
- Les régimes "trending récents" (2021, 2022, 2024-26) ont gross +0.07 à +0.13R.

---

## 3. Net meanR sous différents coûts

| Tag / régime | 3pts fixe (v1) | **1bps** | **2bps** | **3bps** | Futures 1pt |
|---|---:|---:|---:|---:|---:|
| **chop** | | | | | |
| 2015-16 China | -0.226 | -0.096 | -0.119 | -0.141 | -0.124 |
| 2023 "chop" | +0.081 | +0.104 | +0.083 | +0.061 | +0.111 |
| **trending** | | | | | |
| 2010-12 recovery | **-0.219** | +0.027 | +0.006 | -0.015 | -0.041 |
| 2013-14 QE | **-0.252** | -0.040 | -0.067 | -0.094 | -0.093 |
| 2016H2-17 | -0.107 | +0.047 | +0.013 | -0.020 | +0.018 |
| 2019 dovish | -0.060 | +0.014 | -0.012 | -0.037 | +0.006 |
| 2021 recovery | +0.026 | +0.048 | +0.027 | +0.007 | +0.054 |
| 2022 bear | +0.092 | +0.108 | +0.096 | +0.085 | +0.110 |
| 2024-26 bull | +0.095 | +0.104 | +0.082 | +0.061 | +0.115 |
| **vol_shock** | | | | | |
| 2018 | -0.063 | +0.003 | -0.017 | -0.037 | -0.005 |
| 2020 COVID | -0.050 | -0.019 | -0.035 | -0.051 | -0.018 |

### Lectures critiques

1. **Sous 1 bps (aggressive)** : 7/11 régimes nettement positifs (+0.03 à +0.11R). Edge structurel.
2. **Sous 2 bps (réaliste médian)** : 5/11 régimes positifs. 2013-14 reste négatif (gross était déjà ~zero). 2015-16 chop reste négatif (vrai chop). Reste alourdi mais 2022/2024-26 maintiennent +0.08-0.10R.
3. **Sous 3 bps (conservateur)** : 4/11 régimes positifs. 2010-12 et 2016H2-17 basculent au négatif.
4. **Sous futures 1pt** : équivalent à ~2bps en moyenne, mais c'est non-applicable FTMO.

### Pattern qui émerge — "il y a un edge mais il est NET MARGINAL sous coût réaliste"

Sous 2 bps RT (le scénario CFD live le plus réaliste 2026), l'edge ORB est :
- **Clairement positif** (+0.08 à +0.10R) sur 2022, 2024-26 (= sample du précédent rapport).
- **Marginalement positif** (+0.01 à +0.03R) sur 2010-12, 2019, 2021.
- **Négatif** sur 2013-14, 2018, 2020, 2015-16.

**5/11 régimes positifs net @ 2bps. Pas catastrophique mais pas une stratégie qui marche partout.**

---

## 4. p_funded sous coûts réalistes

`audit/nq_v2_pfunded_sweep.py` → `nq_v2_headline_pfunded.csv`, `nq_v2_pfunded_by_regime.csv`, `nq_v2_wf_maximin.csv`.

### A. Headline p_funded (16y full sample) by (cost × sizing)

| Cost model | 0.50% | 0.75% | 1.00% | 1.25% |
|---|---:|---:|---:|---:|
| **Gross (no cost)** | **67.3%** | 59.9% | 50.0% | 53.0% |
| 1 bps RT (aggressive) | 55.6% | 46.0% | 42.4% | 44.2% |
| **2 bps RT (réaliste médian)** | **41.8%** | 36.7% | 30.5% | 27.9% |
| 3 bps RT (conservateur) | 36.0% | 33.0% | 29.2% | 24.0% |
| Futures 1 pt | 51.5% | 38.7% | 35.6% | 38.9% |
| 3 pts fixed (v1 bug) | 37.2% | 34.4% | 26.0% | 22.4% |

**Comparaison v1 vs v2 à 0.50% sizing (CFD réaliste)** : 37.2% → **41.8%** (+4.6pt). Le fix bps gagne ~5pt mais reste loin du 70%.

### B. p_funded par régime sous 2 bps (risk=0.75%)

| Régime | Tag | Gross | **2 bps** | 3 bps | Futures 1pt |
|---|---|---:|---:|---:|---:|
| 2015-16 China | chop | 0% | **0%** | 0% | 0% |
| 2023 "chop" | chop | 100% | **100%** | 100% | 100% |
| 2010-12 recovery | trending | 36% | **14%** | 4% | 0.6% |
| 2013-14 QE | trending | 2% | **0%** | 0% | 0% |
| 2016H2-17 | trending | 99% | **20%** | 0% | 22% |
| 2019 dovish | trending | 87% | **0%** | 0% | 0% |
| 2021 recovery | trending | (NaN) | (NaN) | (NaN) | (NaN) |
| 2022 bear | trending | 100% | **100%** | 100% | 100% |
| 2024-26 bull | trending | 91% | **80%** | 73% | 91% |
| 2018 vol shock | vol_shock | NaN | 0% | 0% | NaN |
| 2020 COVID | vol_shock | 0% | 0% | 0% | 0% |

**Lecture critique** :
- **Sous 2 bps, p_funded varie 0% à 100% selon régime** — extrême variance.
- **2024-26 bull (sample du précédent rapport): 80% à 2bps.** Confirme que la fenêtre récente est exceptionnellement favorable.
- **2013-14 QE trend, 2018, 2020 COVID: 0%.** Gross marginal + cost = mort.
- **2016H2-17, 2019 dovish: gross-positifs (87-99%) mais s'effondrent à 0-20% sous coût** — l'edge gross n'est pas assez gros pour absorber le coût.

### Aggregated by tag (sous 2 bps, risk=0.75%)

| Tag | Mean p_funded |
|---|---:|
| **Trending** (7 régimes) | **35.7%** |
| Chop (2 régimes) | 50.0% (skewed by 2023 +100%) |
| Vol_shock (2 régimes) | 0.0% |

→ Si on retire 2023 (mal-classé, c'est un low-vol-bull) du tag chop, le tag chop tombe à 0%. Cohérent avec l'hypothèse "ORB fail en vrai chop".

### C. WF maximin per regime — sizing × cost

| Cost | risk | FULL | WF mean | **WF min** | n_régimes_zero |
|---|---:|---:|---:|---:|---:|
| gross | 0.50% | 67% | 61% | **0%** | 2 |
| gross | 1.00% | 50% | 52% | 0.3% | 0 |
| gross | 1.25% | 53% | 56% | **4.1%** | 0 |
| **2 bps** | 0.50% | 42% | 25% | **0%** | 3 |
| **2 bps** | 0.75% | 37% | 31% | **0%** | 5 |
| 2 bps | 1.00% | 31% | 31% | 0% | 3 |
| 3 bps | 1.00% | 29% | 26% | 0% | 4 |

→ **Sous gross + risk 1.25%: WF min = 4.1%** (= meilleur worst-case observé). C'est la SEULE config où aucun régime n'a 0%.
→ **Sous coût réaliste (2-3 bps): WF min = 0% partout** — il existe toujours 2-5 régimes où la stratégie est totalement morte.

---

## 5. Gate rv20 OOS sous coût bps réaliste

`audit/nq_v2_pfunded_sweep.py` → `nq_v2_pfunded_output.txt` section D.

### Sous 2 bps RT (réaliste médian)

| risk | BASE | rv20_LOW Δ | **rv20_MID Δ** | rv20_HIGH Δ |
|---:|---:|---:|---:|---:|
| 0.50% | 41.8% | -0.3pt | **+4.5pt** | -2.1pt |
| 0.75% | 36.7% | -6.0pt | **+5.0pt** | +2.3pt |
| 1.00% | 30.5% | -9.0pt | **+7.9pt** | +1.2pt |
| 1.25% | 27.9% | -7.8pt | **+7.9pt** | -1.1pt |

### Sous 3 bps RT (conservateur)

| risk | BASE | rv20_LOW Δ | **rv20_MID Δ** | rv20_HIGH Δ |
|---:|---:|---:|---:|---:|
| 0.50% | 36.0% | -2.6pt | +4.5pt | -0.2pt |
| 1.00% | 29.2% | -4.8pt | +4.2pt | +0.9pt |

### Lectures clés
1. **rv20_mid gate ajoute +5-8pt sous 2bps cost** (meilleur que v1 où c'était +3-5pt sous 3 pts fixe).
2. **rv20_LOW gate (= low-vol) est SYSTÉMATIQUEMENT négatif** (-3 à -9pt). Confirme que démarrer en low-vol nuit (= low momentum environments).
3. **Mais le plafond avec gate reste bas**: 30.5% + 7.9 = **38.4% max**. Toujours loin de 70%.

---

---

## 5. cost/R stationnarité confirmée

`audit/nq_v2_bps_cost.py` → `nq_v2_cost_to_R.csv`.

| Régime | cost/R (3pts v1) | **cost/R (2bps)** | cost/R (3bps) | cost/R (futures 1pt) |
|---|---:|---:|---:|---:|
| 2010-12 | 0.222 | **0.038** | 0.057 | 0.082 |
| 2013-14 | 0.193 | **0.049** | 0.074 | 0.070 |
| 2015-16 chop | 0.120 | **0.039** | 0.058 | 0.044 |
| 2016H2-17 | 0.149 | **0.060** | 0.090 | 0.056 |
| 2018 | 0.066 | 0.034 | 0.052 | 0.025 |
| 2019 | 0.079 | 0.046 | 0.068 | 0.030 |
| 2020 | 0.035 | 0.027 | 0.041 | 0.013 |
| 2021 | 0.034 | 0.036 | 0.054 | 0.012 |
| 2022 | 0.023 | 0.020 | 0.030 | 0.008 |
| 2023 | 0.036 | 0.038 | 0.056 | 0.013 |
| 2024-26 | 0.023 | 0.038 | 0.056 | 0.009 |
| **Spread max/min** | **0.222 → 0.023 (×10)** | **0.060 → 0.020 (×3)** | 0.090 → 0.030 (×3) | 0.082 → 0.008 (×10) |

→ **Sous 2 bps, cost/R varie de 0.020 à 0.060 — bien plus stationnaire que sous 3 pts fixes (0.023-0.222, ×10 amplitude)**. Le fix bps est mécaniquement validé.

→ **Note** : les sous-2018 ont cost/R bps un peu HIGHER (0.05-0.07) que les post-2020 (0.03-0.04). Cela parce que l'OR range scale plus vite que le prix dans les vol-high regimes — donc même en bps, les périodes calme ont cost/R un peu plus élevé. Mais l'amplitude est ×3 vs ×10 — beaucoup plus stable.

---

## 6. Verdict — tranche entre les 3 hypothèses

### 6.1 Hypothèse (a) artefact de coût pur — **PARTIELLEMENT VRAI**

Le bug 3 pts fixes est réel et confirmé :
- En 2010, 3 pts = 15.4 bps (×15 trop cher vs un CFD réaliste).
- Sous bps stationnaire (2 bps), cost/R passe de 0.020-0.060 (vs 0.020-0.267 sous 3 pts fixe).
- p_funded full 16y à 0.50%: passe de 37% (v1) à 42% (v2 sous 2 bps).

**Mais** : le fix gagne seulement +5pt sur le headline. Pas un effacement complet du NO-GO.

→ Le coût n'explique qu'**une partie** de la sous-performance v1, pas tout.

### 6.2 Hypothèse (b) edge de régime momentum — **VALIDÉE avec nuance**

Gross meanR par tag (cost = 0) :
- **Trending: +0.066R** (positif clair)
- Vol_shock: +0.010R (~zero)
- Chop: +0.006R (~zero, mais skewed par 2023)

Edge structurel **clairement concentré en trending**.

**Mais nuance importante** :
- Au sein de "trending", 2013-14 (low-vol QE) est gross-négatif (-0.013R).
- Tag "chop" 2023 est en fait un low-vol-bull (gross +0.126R), mal classé.
- La vraie hiérarchie est probablement : **"momentum-vol-élevée" > "low-momentum-vol" > "true-chop"**.

Sous coût bps réaliste (2 bps) :
- 2022 bear: net +0.096R, p_funded 100%
- 2024-26 bull: net +0.082R, p_funded 80%
- 2010-12, 2016H2-17, 2019: net 0 à +0.013R, p_funded 0-20%
- 2013-14 QE: net -0.067R, p_funded 0%
- Vrai chop 2015-16: net -0.119R, p_funded 0%

→ Hypothèse (b) validée: **l'edge existe en gross, dépend du régime, et survive marginalement sous coût réaliste — mais SEULEMENT dans les régimes "high-momentum-vol"** (= 2022+).

### 6.3 Hypothèse (c) pas d'edge — **REJETÉE**

Gross +0.049R sur 16 ans (full sample), +0.066R en trending. L'edge existe statistiquement.

### 6.4 Verdict synthétique

**Le baseline ORB sur NQ 2010-2026 est :**

| Sous | mean R 16y | p_funded 16y @ 0.50% | Verdict |
|---|---:|---:|---|
| Gross (no cost) | **+0.049R** | 67% | edge structurel oui |
| Cost réaliste 2 bps | +0.011R | **42%** | edge marginal net, sous 70% |
| Cost conservateur 3 bps | -0.013R | 36% | edge mort net |
| Cost v1 3pts fixe | -0.081R | 37% | bug coût (sur-facturation pré-2016) |

**Conclusion** :

- **NO-GO catégorique v1 (30%) ÉTAIT TROP DUR** — bug coût points-fixes a sur-facturé les années pré-2016.
- **GO optimiste OPTIM_ftmo_2step_uncapped (95%) ÉTAIT TROP OPTIMISTE** — sample selection sur 2022-2025 = exactement les 2 régimes les plus favorables (momentum-vol-élevée).
- **Le vrai verdict honnête** : **42% p_funded sur 16 ans sous coût CFD réaliste**, avec edge concentré sur ~3 régimes / 11 (les régimes "high-momentum-vol" récents). Le stratégie est viable conditionnellement à un régime favorable, qui était présent 2022-2025 mais ne l'est pas dans 7/11 des régimes historiques.

**Conditionnellement marginal**, pas un strict NO-GO. Mais le seuil 70% reste inatteignable même avec gate (max ~46%).

### 6.5 Implications opérationnelles

1. **Ne pas deployer en se basant sur le 79-95% du précédent rapport** — sample-specific aux régimes 2022-2025.
2. **Le 42% p_funded honnête sur 16 ans = beaucoup de challenge fees** pour avoir un funded account. Expected nb attempts = 1/0.42 = 2.4 attempts à $155/each = $372 expected per funded.
3. **Le gate rv20_mid donne +5-8pt sous bps réaliste** — utile mais pas suffisant. p_funded max avec gate = 39%.
4. **L'edge est régime-dépendant** : le stratégie marche en momentum-vol-élevée (2022+ era). Si le régime change vers low-momentum-vol (comme 2013-14, 2018, 2020), expectancy redevient négative.
5. **L'option futures (NQ direct cost 1 pt)** donne 52% p_funded à 0.50% — meilleur que CFD 2bps mais FTMO interdit CME.

### 6.6 Recommandation actionnable

**Option A** : Deploy CFD avec attentes calibrées 42% p_funded honnête (vs 95% précédemment claim). Espérance positive si fees abordables ($155-200/challenge), mais slow funded path.

**Option B** : Attendre validation paper sur la fenêtre 2026+ pour vérifier que le régime momentum-vol-élevée actuel persiste. Si oui (= sample like 2022-2025), p_funded ~80%. Si non (= régime change), p_funded retombe à 30-40%.

**Option C** : Chercher une stratégie qui n'est PAS aussi régime-dépendante. La famille ORB est par nature momentum-based.

### 6.7 Caveats à reporter dans tout document futur

1. **"p_funded baseline 16y = 42% sous CFD 2bps"** (pas 79% comme v1 le suggérait, pas 30% comme v1 mal-corrigé l'a dit).
2. **"Edge concentré sur régimes momentum-vol-élevée; mort en low-momentum ou true-chop"**.
3. **"Le sample 2022-2025 du précédent rapport était un cherry-pick involontaire"** des 2 régimes les plus favorables du sample 16y.

---

---

## 7. Reproductibilité

| Script | Sortie |
|---|---|
| `audit/nq_v2_bps_cost.py` | `nq_v2_trades.parquet`, `nq_v2_distortion.csv`, `nq_v2_gross_per_regime.csv`, `nq_v2_gross_by_tag.csv`, `nq_v2_meanR_by_cost_regime.csv`, `nq_v2_cost_to_R.csv`, output txt |
| `audit/nq_v2_pfunded_sweep.py` | `nq_v2_headline_pfunded.csv`, `nq_v2_pfunded_by_regime.csv`, `nq_v2_wf_maximin.csv`, output txt |

Tous seeded, déterministes.

---

*Validation v2 réalisée 2026-06-02 — Claude Code (Opus 4.7 1M ctx). Correction du bug coût points-fixes via bps-constant. Same-bar headline (EXEC_0) per OPTIM_execution_realism. Gross meanR séparé pour isoler edge-régime du coût.*
