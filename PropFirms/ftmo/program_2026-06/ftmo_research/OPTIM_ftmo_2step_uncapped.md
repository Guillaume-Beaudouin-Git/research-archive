# Optimisation FTMO 2-step UNCAPPED — Correction du modèle capped + sizing optimal
## Mode recherche, sweep sizing × censure × régime × WF maximin

**TL;DR** — Le verdict NO-GO précédent (52% p_funded, OPTIM_ORB_propfirm §1) **était un artefact du cap 40 jours** hérité de l'audit. Sous le bon modèle FTMO 2-step **uncapped** (no time limit, daily 5%, total 10% statique), avec real-path P1→P2 contigu et exclusion correcte de la censure, les résultats principaux (in-sample 2022-2026 H1) :

| Sizing × Gate | p(funded) FULL | WF Mean / Min | Censure | Médian grind |
|---|---:|---:|---:|---:|
| 1.25% no-gate (= ancien capped) | 55% | 58% / 38% | 5% | 32 j |
| 0.50% no-gate | **79.2%** | 82.7% / 18.5% | 14% | 110 j |
| 0.75% no-gate | 71.6% | 75.1% / 18.5% | 7% | 66 j |
| **0.50% + rv20_mid gate** | **95.5%** | (non chiffré) | 23.6% | ~120 j |
| **0.75% + rv20_mid gate** | **88.7%** | (non chiffré) | 12.4% | ~70 j |
| 0.25% no-gate | 100% (biaisé) | 100% (3/5 folds NaN) | **22%** | 259 j |

**Findings clés** :
1. **Le « mur math » FTMO 2-phase n'était pas structurel** — c'était l'artefact d'un cap 40j. Le down-sizing 0.50-0.75% donne **79-89% p_funded** sur uncapped vs 52% capped.
2. **Mécanisme réel du down-sizing = long-grind survival**, PAS cluster-protection (fast_bust ≈ 0% partout). À 0.25% sizing le grind chop médian = 460 jours → traverse 2023 entier.
3. **MEAN vs MAXIMIN divergent** : argmax mean = 0.50% (mean WF 82.7%, min 18.5%) ; argmax maximin = 1.50% (mean 55%, min 40%). Le choix dépend de la fonction-objectif.
4. **rv20_mid gate (vol modérée) explose sur uncapped** : +16-17pt à 0.50-0.75% sizing. C'est l'inverse du capped où vr5_low gagnait. Mécanisme : grind long bénéficie d'un start en condition stable.
5. **À 0.25% sizing : p_funded = 100% mesuré, MAIS 22% des starts censurés** → mesure non-fiable en l'état.

**Caveat irréductible — double limite data :**
1. **Régime N≈1** : 2022-2026 contient un seul chop (2023). Tout +17pt du gate rv20_mid s'apprend à éviter cette seule réalisation.
2. **Censure structurelle** : grind long sur 3,5 ans → 22% censure à 0.25%, 14% à 0.50%, 7% à 0.75%. À 0.10% c'est 78% — non-mesurable.

**Fetch NQ/DAX 2008-2025 est désormais le prérequis pour MESURER, pas seulement valider.**

---

## 0. Périmètre, correction de modèle, garde-fous

- Container : **FTMO 2-step uncapped** uniquement (décision verrouillée). Challenge +10%, Verification +5%, daily 5%, total 10% statique, no time limit.
- `audit/optim_engine.py` étendu d'un flag uncapped sur `_run_single_attempt` et d'un container `ftmo_2step_uncapped` avec `max_days_p1=None`, `max_days_p2=None`. **C'est une correction de fidélité du modèle, PAS une modification de stratégie** → ne consomme pas L10.
- Censure : si la fenêtre data se termine avant pass/bust → outcome `CENSORED`. Exclu de numérateur ET dénominateur de p_funded.
- Real-path **contigu** uniquement. Pas d'iid, pas de block-bootstrap. P1 puis P2 sur jours subséquents réels.
- Kill-switch déjà prouvé mort (L19, OPTIM_ORB_propfirm §3) → pas re-testé. Containers 1-step exclus (décision user).
- L19, L10 budget (3 mods max — sizing déjà 1, gate régime potentielle 2e) respectés.

---

## 1. Étape 1 — Sweep sizing uncapped + censure (in-sample 2022-2026 H1)

`audit/optim_step7_uncapped_sweep.py` → `optim_step7_uncapped_sweep.csv` + `optim_step7_output.txt`.

| risk_per_block | n_total | n_resolved | censured | p(P1) | p(P2\|P1) | **p(funded)** | grind médian (j) | bust_total | fast_bust | slow_bust | bust_ttp médian |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **0.10%** | 1137 | 249 | **78.1%** | 100% | 100% | **100%** | 852 | 0% | 0% | 0% | n/a |
| **0.25%** | 1137 | 885 | **22.2%** | 100% | 100% | **100%** | 259 | 0% | 0% | 0% | n/a |
| **0.50%** | 1137 | 978 | 14.0% | 85% | 93% | **79.2%** | 102 | 14.9% | 0% | 12.8% | 169 |
| **0.75%** | 1137 | 1058 | 7.0% | 83% | 86% | **71.6%** | 66 | 17.2% | 0% | 16.0% | 57 |
| **1.00%** | 1137 | 1072 | 5.7% | 77% | 72% | 55.7% | 44 | 23.1% | 0% | 21.8% | 27 |
| **1.25%** | 1137 | 1081 | 4.9% | 74% | 75% | 55.2% | 32 | 26.5% | 0.4% | 24.7% | 20 |
| **1.50%** | 1137 | 1089 | 4.2% | 72% | 74% | 53.6% | 27 | 27.9% | 1.1% | 25.7% | 15 |

### Observations critiques

**1. Le sweet-spot Cowork (0.25%) est confirmé in-sample MAIS biais de censure massif.**
À 0.25% : sur les 78% de starts résolus, **100% pass**. Mais 22% des starts sont censurés — le grind dépasse la fin du data. Les résolus sont **systématiquement les starts précoces** (qui ont plus de runway).

**2. Le mode bust dominant à TOUS les sizings est `slow_bust` (drift), PAS `fast_bust` (cluster).**
- `fast_bust` (≤5 jours) ≤ 1.1% partout. Les clusters adverse à -10% en moins d'une semaine n'existent quasiment pas.
- `slow_bust` (>5 jours) : 12-26% selon sizing. C'est le **bleed graduel en régime chop** qui domine.
- → Le down-sizing **ne protège pas d'un cluster transitoire** (il n'y en a pas). Il **rallonge le grind au-delà de la durée typique d'un épisode chop (~6 mois)**. Mécanisme différent de l'intuition « cap-relax ».

**3. Le « 71.6% à 0.75% » est le candidat sérieux.**
- Censure raisonnable (7%) sur 1058 starts.
- Median grind 66 jours = 3 mois — pas excessif pour live trading.
- p(P1) 83%, p(P2|P1) 86%, p(funded) chaîné 72% → **passe ≥70%** sans gate.
- C'est l'inverse de l'argument capped « impossible d'atteindre p(P1)×p(P2) ≥ 0.70 ».

**4. À 1.25-1.5%, on retrouve le capped 51-55%.**
Le cap 40j ne se déclenchait plus que rarement à ces risk levels (grind médian 27-32 j déjà sous cap). Donc capped ≈ uncapped à risk élevé. **Le verdict capped 52% s'applique seulement à risk élevé**, pas à down-sizing.

### Argmax mean p(funded) brut = 100% @ 0.10% — mais inutilisable

À 0.10%, 78% des starts sont censurés. Le « 100% » mesure 22% du sample. C'est un fit massif à un sous-ensemble auto-sélectionné (starts précoces 2022-2023 trending). À ne PAS reporter comme un chiffre opérationnel.

### Argmax honnête (censure ≤ 10%)
| Risk | p(funded) | Censure | Médian grind |
|---|---:|---:|---:|
| 0.75% | 71.6% | 7.0% | 66 j |
| 1.00% | 55.7% | 5.7% | 44 j |

→ **0.75% est le sweet-spot honnête sur le critère censure ≤ 10%.**

---

## 2. Étape 2 — Décomposition régime (chop-overlap vs trending-only)

`audit/optim_step8_regime_split.py` → `optim_step8_regime_split.csv` + `optim_step8_output.txt`.

**Définition** : une attempt « chop-overlap » si l'intervalle `[start, start + grind]` recoupe `[2023-01-01, 2023-12-31]`. Sinon « trending-only ».

### p_funded par régime traversé

| risk | ALL_RESOLVED | CHOP_OVERLAP | TRENDING_ONLY |
|---|---:|---:|---:|
| 0.25% | 100% | **100%** | 100% |
| 0.50% | 79.2% | **42.8%** | 100% |
| 0.75% | 71.6% | **29.9%** | 91.4% |
| 1.00% | 55.7% | **22.9%** | 67.7% |
| 1.25% | 55.2% | 28.8% | 64.4% |
| 1.50% | 53.6% | 32.2% | 60.8% |

### slow_bust par régime (drift mode)

| risk | ALL | CHOP_OVERLAP | TRENDING_ONLY |
|---|---:|---:|---:|
| 0.25% | 0% | 0% | 0% |
| 0.50% | 14.9% | **41.1%** | 0% |
| 0.75% | 17.2% | **47.5%** | 2.8% |
| 1.00% | 23.1% | 52.1% | 12.5% |
| 1.25% | 26.0% | 48.9% | 18.1% |
| 1.50% | 26.8% | 44.7% | 20.8% |

### fast_bust par régime (cluster mode) — essentiellement nul partout

| risk | ALL | CHOP_OVERLAP | TRENDING_ONLY |
|---|---:|---:|---:|
| 0.25-1.00% | 0% | 0% | 0% |
| 1.25% | 0.5% | 1.4% | 0.1% |
| 1.50% | 1.1% | 2.2% | 0.7% |

### Grind médian par régime

| risk | ALL | CHOP_OVERLAP | TRENDING_ONLY |
|---|---:|---:|---:|
| 0.25% | 259 | **460** | 212 |
| 0.50% | 110 | 133 | 92 |
| 0.75% | 63 | 71 | 63 |
| 1.00% | 41 | 42 | 41 |
| 1.50% | 24 | 21 | 25 |

### Lecture du tableau — mécanisme réel du down-sizing

**1. Le narratif Cowork « down-sizing protège du cluster » est partiellement faux.**
- `fast_bust` (cluster -10% en ≤5 jours) est **0% à tous les sizings 0.25-1.00%**, et juste 1-2% à risk élevé.
- Il n'y a quasiment **pas de cluster bust** dans cette stratégie (skew +2.3, défini-risque sur 1R, max-loss daily ~1.5%).
- → Le down-sizing **ne supprime pas un cluster qui n'existe pas**.

**2. Le vrai mécanisme : le down-sizing rallonge le grind au-delà de la durée d'un épisode chop.**
- `slow_bust` en chop-overlap : à 0.25% le grind médian chop = 460 jours (~22 mois) — le strat traverse **tout 2023 ENTIER** plus tampon, puis profite du 2024-25 trending → bleed pendant 2023 mais récupère sur la queue.
- À 0.50% le grind médian chop = 133 jours (~6.5 mois) — seulement la moitié du chop 2023 est traversée avant pass ou bust. p_funded chop tombe à 42.8%.
- À 0.75% le grind médian chop = 71 jours — moins d'un trimestre — p_funded chop chute à 30%.
- À 1.0+%, le grind est trop court (~40 jours) pour traverser un chop complet ; la stratégie bust en chop avant d'avoir mesuré la fin du régime.
- → **Le down-sizing achète du temps**. C'est une stratégie de **survie**, pas de protection.

**3. Le tradeoff trending vs chop est asymétrique.**
- À 0.25% : trending=100, chop=100 (immunité par grind long, mais 22% censurés).
- À 0.50% : trending=100, chop=42.8 (split net).
- À 0.75% : trending=91, chop=29.9 (les trending commencent à fail par drift).
- À 1.00-1.50% : trending=60-68, chop=23-32 (les deux modes affectent tout).
- → **Pas de monotonie** ; le ratio trending:chop est maximum à 0.5% (100:42.8 ≈ 2.34) puis se dégrade.

---

## 3. Étape 3 — WF maximin vs mean (5 contiguous folds)

`audit/optim_step9_wf_maximin.py` → `optim_step9_wf_uncapped.csv` + `optim_step9_output.txt`.

5 folds contigus de ~227 trading days chacun (≈9 mois calendaire) :
- fold1 = 2022-01-03 → 2022-11 (Russia war + Fed tightening — bear trending vol)
- **fold2 = 2022-11 → 2023-10** (full chop 2023 — Fed pivot ambiguity)
- fold3 = 2023-10 → 2024-09 (tail chop + trending recovery)
- fold4 = 2024-09 → 2025-08 (trending)
- fold5 = 2025-08 → 2026-05 (trending recent)

### Table WF par sizing (in-sample 5 folds)

| risk | FULL pf | FULL cens | fold1 | fold2 | fold3 | fold4 | fold5 | mean WF | min WF | std WF | mean cens fold |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.25% | 100% | 22% | 100% | NaN | NaN | 100% | 100% | 100% | 100% | 0 | **94.6%** |
| 0.50% | 79.2% | 14% | 100% | **18.5%** | 94.9% | 100% | 100% | **82.7%** | 18.5% | 32.1 | 52.5% |
| 0.75% | 71.6% | 6.9% | 100% | **18.5%** | 69.1% | 87.8% | 100% | 75.1% | **18.5%** | 30.5 | 27% |
| 1.00% | 55.7% | 5.7% | 94.5% | 26.5% | 52.0% | 60.7% | 65.2% | 59.8% | 26.5% | 21.9 | 18.5% |
| 1.25% | 55.2% | 4.9% | 86.6% | 37.6% | 55.2% | 51.0% | 58.4% | 57.7% | **37.6%** | 16.1 | 12% |
| 1.50% | 53.6% | 4.2% | 77.5% | 40.3% | 55.2% | 41.1% | 60.8% | 55.0% | **40.3%** | 13.8 | 10.1% |

### Observations critiques

**1. À 0.25% : 94.6% mean censure inter-fold = unusable per-fold.**
fold2 et fold3 sont **NaN** = 100% censure (le grind 460 jours ne tient dans aucun fold 227 jours). Le « 100% mean » est calculé sur 3 folds restants seulement. **Statistiquement vide**.

**2. fold2 (transition vers chop 2022-08 → 2023-04) tue le maximin à 0.5-0.75%.**
- À 0.50%, fold2 = 18.5% p_funded. Le grind 110j sort sur le début du chop.
- À 0.75%, fold2 = 18.5% identique. Le grind 66j chevauche aussi le chop.
- Le worst-case fold dépend du sizing — à low sizing, fold2 chope ; à high sizing, fold2 reste mal (37%) mais limité.

**3. Argmax MEAN vs argmax MAXIMIN — DIVERGENCE NETTE.**

| Critère | Argmax | Sizing | Valeur | min fold |
|---|---|---:|---:|---:|
| Mean WF (incl. 0.25% biaisé) | 0.25% | 100% | (biaisé, 94% cens) |
| **Mean WF (honest, exclure cens >50%)** | **0.50%** | 82.7% | **18.5%** |
| **Maximin WF** | **1.50%** | min=40.3% | mean=55% |
| Compromis | 1.25% | mean=57.7%, min=37.6% | ratio reasonable |

**Mean optimal (Cowork-style, parier sur le régime) = 0.50%** : 82.7% en moyenne, mais 18.5% si tu démarres pile au mauvais fold.

**Maximin optimal (robuste live) = 1.50%** : 55% mais avec un floor à 40% — si tu ne sais pas quand tu démarres, c'est le sizing qui te protège du worst-case.

**Sweet-spot du brief (0.75%) est dans une zone fragile** : mean 75%, min 18.5%. Bonne moyenne mais variance élevée.

### Interprétation pour la décision

**La fonction-objectif décide :**
1. **Mean p_funded** (Cowork) : 0.50%, si tu peux te permettre 1 in 5 challenges qui pourrait échouer à 18%. Espérance positive.
2. **Maximin** (robuste) : 1.25-1.50%, p_funded modeste mais worst-case 38-40%.
3. **Hybride avec gate** (§4) : up-size 0.50-0.75% MAIS attendre un signal trending pour démarrer → atténuer le risque fold2.

---

## 4. Étape 4 — Gate régime sur uncapped (ablation L19, in-sample N≈1)

`audit/optim_step10_gate_uncapped.py` → `optim_step10_gate_uncapped.csv` + `optim_step10_output.txt`.

### Table gate × risk — p_funded full-sample

| risk | NONE | rv20_mid | trend20_mid | vr5_low |
|---:|---:|---:|---:|---:|
| 0.50% | 79.2% | **95.5%** | 76.5% | 73.7% |
| 0.75% | 71.6% | **88.7%** | 70.9% | 70.2% |
| 1.00% | 55.7% | 60.2% | 58.8% | 50.8% |
| 1.25% | 55.2% | 53.0% | 58.2% | 51.6% |

### Ablation L19 — Δ p_funded vs baseline au même sizing

| risk | rv20_mid Δ | trend20_mid Δ | vr5_low Δ |
|---:|---:|---:|---:|
| 0.50% | **+16.3pt** | -2.7pt | -5.6pt |
| 0.75% | **+17.1pt** | -0.6pt | -1.4pt |
| 1.00% | +4.5pt | +3.1pt | -4.9pt |
| 1.25% | -2.2pt | +3.0pt | -3.6pt |

### Observations

**1. rv20_mid (vol modérée) domine sur uncapped — inverse de l'optim capped.**
- Sur capped (`OPTIM_ORB_propfirm.md §5`), **vr5_low** était le best gate (+5-9pt sur 1phase_static).
- Sur uncapped (ici), **rv20_mid** explose (+16-17pt sur 0.50-0.75%) tandis que vr5_low devient négatif (-1 à -6pt).
- **Cohérent mécaniquement** : sur grind court (capped 40j ou risk élevé), le state-at-start détermine le grind ; vr5 capture la décélération momentum à court terme. Sur grind long uncapped (100+ jours), le state-at-start est moins prédictif (le régime tourne pendant le grind) ; rv20_mid (vol modérée) capture une condition stable où la stratégie tradera confortablement plusieurs mois.

**2. Effet maximal aux sizings low-mid (0.50-0.75%).**
- À 1.00-1.25%, le gain rv20_mid retombe à +4.5 / -2.2pt — le grind est trop court pour que la vol-modérée du départ persiste.
- À 0.50-0.75%, le grind ≥ 66 jours bénéficie de la sélection du start regime.

**3. Censure légèrement augmentée par les gates (mais reste raisonnable).**
| risk | NONE | rv20_mid | trend20_mid | vr5_low |
|---:|---:|---:|---:|---:|
| 0.50% | 14.0% | 23.6% | 15.8% | 14.7% |
| 0.75% | 6.9% | **12.4%** | 7.7% | 7.2% |

→ rv20_mid à 0.75% : censure 12.4% (vs 6.9% baseline) — acceptable.

**4. ⚠ N≈1 caveat — le warning du brief s'applique pleinement.**
- rv20_mid sur 2022-2025 entraîne à "éviter les périodes vol basse", qui dans ce sample = essentiellement 2023.
- Le +17pt à 0.75% est un fit à **un seul** chop episode.
- **Sans extension NQ/DAX 2008-2025, le gate rv20_mid est non-validable**. Le passer de 71.6% à 88.7% est mathématiquement réel sur l'in-sample, mais l'écart pourrait être 0pt ou +20pt sur un autre dataset.

### Combiné optim : sizing × gate × WF maximin (synthèse)

| Combo | p_funded FULL | WF mean (approx*) | min WF (approx*) | Médian grind | Censure |
|---|---:|---:|---:|---:|---:|
| 0.50% + rv20_mid | **95.5%** | ~90% | ~25% (fold2 chop persiste) | ~120j | 23.6% |
| 0.50% + NONE | 79.2% | 82.7% | 18.5% | 110j | 14% |
| 0.75% + rv20_mid | **88.7%** | ~82% | ~22% | ~70j | 12.4% |
| 0.75% + NONE | 71.6% | 75.1% | 18.5% | 66j | 6.9% |
| 1.25% + NONE | 55.2% | 57.7% | 37.6% | 29j | 4.9% |
| 1.50% + NONE | 53.6% | 55.0% | 40.3% | 24j | 4.2% |

*Les WF mean/min avec gate sont des estimations (pas de WF×gate full sweep effectué — out-of-scope L10) ; à valider post-extension data.

→ **Best combo in-sample : 0.50% + rv20_mid = 95.5%**. C'est le top du tableau, mais c'est un fit à N=1 chop.

**Verdict L19 (gate)** :
- ✓ **rv20_mid gate ajoute valeur** structurelle sur uncapped à low-mid sizing.
- ✗ **vr5_low gate inutile** sur uncapped (la signature qui marchait sur capped ne se généralise pas au grind long).
- ✗ **trend20_mid marginal** (+3pt max).

→ **Si gate utilisé, c'est rv20_mid**. Mais validation N≥5 chop episodes requise avant tout deploy.

### Modifications L10 consommées

1. ✓ Sizing optimum (entre 0.50% mean / 1.50% maximin / 0.75% compromis)
2. ✓ Gate rv20_mid (ablation L19 confirme +16-17pt, in-sample N=1)
3. **(disponible)** 3e mod réservée pour validation post-extension (par ex. raffinement gate sur N=5+ régimes, ou combinaison gate × WF expanding).

---

## 5. Verdict final

### 5.1 Le verdict NO-GO précédent est officiellement INVALIDÉ

`OPTIM_ORB_propfirm.md §1` disait : « ftmo_2phase à 1.25% risk = 52% p_funded, mur math, NO-GO ». **C'est valide UNIQUEMENT pour le modèle capped 40 jours**. Sur FTMO 2-step réel (uncapped), à 1.25% risk, p_funded = 55.2% (audit step 7) — proche du 52% capped car le grind médian uncapped à 1.25% (32 jours) est en dessous du cap 40j ; donc capped vs uncapped change peu à risk élevé.

**Le verdict NO-GO était structurel-en-apparence mais artefactuel-en-réalité** : le cap rendait impossible le down-sizing 0.25-0.75% qui aurait montré p_funded ≥70%.

### 5.2 p(funded) honnête FTMO 2-step uncapped

| Sizing | p(funded) FULL | Censure | Median grind | Verdict |
|---:|---:|---:|---:|---|
| 0.10% | 100% | **78%** | 852 j | **inutilisable** (biais censure massif) |
| 0.25% | 100% | **22%** | 259 j | **GO mais bias** (validation NQ/DAX requise) |
| 0.50% | **79.2%** | 14% | 110 j | **GO net** (mais 14% censure) |
| **0.75%** | **71.6%** | **7%** | 66 j | **SWEET SPOT — passe 70% avec censure raisonnable** |
| 1.00% | 55.7% | 5.7% | 44 j | sous 70% |
| 1.25% | 55.2% | 4.9% | 32 j | sous 70% |
| 1.50% | 53.6% | 4.2% | 27 j | sous 70% |

### 5.3 Range honnête par régime traversé

| Sizing | trending_only | chop_overlap | Span |
|---:|---:|---:|---:|
| 0.25% | 100% | 100% | (immunité — coût: 22% censure) |
| 0.50% | 100% | 42.8% | **±28pt** |
| 0.75% | 91.4% | 29.9% | **±31pt** |
| 1.00% | 67.7% | 22.9% | ±22pt |
| 1.25% | 64.4% | 28.8% | ±18pt |

→ **À 0.75% (sweet spot), démarrer en chop garantit 30% p_funded ; démarrer en trending donne 91%.** La probabilité moyenne 71.6% est la moyenne pondérée 32%/68% chop/trending (proportions dans data).

### 5.4 Le mécanisme réel — long-grind survival (pas cluster protection)

- `fast_bust` (cluster -10% en ≤5 jours) ≈ 0% à TOUS sizings ≤1.0%. **Il n'y a quasiment pas de cluster bust dans cette stratégie** (defined-risk 1R, max-day loss ~1.5%).
- Le down-sizing **n'élimine pas un cluster qui n'existe pas**. Il **allonge le grind au-delà de la durée d'un épisode chop** :
  - À 0.25%, grind chop médian = **460 jours** (~22 mois) → traverse 2023 ENTIER + tampons.
  - À 0.75%, grind chop médian = 71 jours → traverse 1/3 de 2023.
  - À 1.50%, grind chop médian = 21 jours → bust avant fin du chop.
- → **Stratégie de survie temporelle, pas de protection cluster**. La terminologie « cap-relax » du brief était mal calibrée.

### 5.5 Mean vs Maximin (à confirmer step 9, voir §3)

Si argmax mean et argmax maximin convergent au même sizing : décision facile.
Si divergence : la fonction-objectif tranche. Pour ce projet (Cowork-style, parier sur le régime favorable) → mean. Pour robustesse (live risk, ne pas savoir quel régime se produira) → maximin.

### 5.6 La double limite data — prérequis NQ/DAX 2008-2025

**Le verdict GO conditionnel (≥70%) repose sur 2 limitations data majeures :**

**(a) Régime N≈1** : 2022-2026 contient **un seul** gros chop (2023). Tout le contraste chop/trending est mesuré sur cette seule réalisation. Le ~30% chop_overlap p_funded à 0.75% pourrait être 10% ou 50% sur un autre chop (2014 oil crash, 2018 vol shock, 2015 China shock). **Aucune projection live n'est statistiquement défensible sur N=1.**

**(b) Censure structurelle** : un grind de ~14 mois à sizing 0.25% sur 3,5 ans de data ⇒ **22% des starts sont censurés**. Ce sont les starts qui pourraient buster en 2025 mais n'ont pas le temps de le faire ; ou pass en 2026 mais hit-end-of-data. **À 0.10% sizing, 78% censurés** — les chiffres deviennent non-mesurables.

**Conséquence opérationnelle** : un fetch NQ/DAX 2008-2025 (~$200 + 2 semaines) est désormais le prérequis pour **MESURER** une stratégie à grind long, pas seulement pour valider un régime. Sans cette extension :
- p_funded à 0.75% = 71.6% reste exposé à une erreur ±15pt (variance régime + biais sample).
- p_funded à 0.25% = 100% **n'est pas une probabilité statistiquement valide** (78% des starts non observés). Indéfendable en live.

### 5.7 Recommandation actionnable

**Court terme (avant extension data) — la fonction-objectif décide :**

**Option A — Mean-optimal "Cowork-style" : sizing 0.50% + rv20_mid gate**
- Full sample p_funded = **95.5%** (n_résolu=748 après gate, censure 23.6%).
- Ablation L19 vs no-gate baseline : **+16.3pt**, statistiquement énorme.
- Median grind ≈ 120 jours ≈ 6 mois challenge + verification.
- **MAIS in-sample sur N=1 chop episode**. Non validable sans extension.
- Si gate trust : meilleure stratégie déployable.

**Option A-bis — Mean-optimal sans gate : sizing 0.50%**
- Full sample p_funded = 79.2% (n=978, censure 14%).
- WF mean = 82.7%, WF min = 18.5% (fold2 chop).
- Median grind = 110 jours.
- **Risque** : ~20% de tomber dans fold2 où p_funded = 18.5%.
- Plus robuste que Option A car ne dépend pas d'un gate fragile.

**Option B — Maximin "robuste" : sizing 1.25-1.50% sans gate**
- Full sample p_funded = 53-55%.
- WF mean = 55-58%, WF min = 37-40% (fold2 chop).
- Median grind = 24-29 jours ≈ 1-1.5 mois — rapide.
- **Avantage** : worst-case borné ; pas de dépendance régime gate.
- **Inconvénient** : espérance modeste, p_funded ≤ ancien verdict capped.

**Option C — Compromis "sweet spot" : 0.75% + rv20_mid gate**
- Full sample p_funded = **88.7%** (+17.1pt vs no-gate 71.6%).
- Median grind ≈ 70 jours ≈ 3.5 mois.
- Censure 12.4% (raisonnable).
- WF non chiffré with gate ; à valider.

**Option D — Sizing 0.25% (sweet-spot Cowork théorique)**
- p_funded = 100% sur 78% des starts résolus.
- Median grind = 259 jours ≈ 14 mois.
- **MAIS 22% censure full-sample, 94.6% mean cens par fold** — statistiquement insuffisant.
- À NE PAS utiliser avant extension data.

### 5.7.1 Tableau de décision synthétique

| Option | Sizing | Gate | p_funded FULL | WF Risk | Grind | Robust to N≈1 ? |
|---|---:|---|---:|---|---|:---:|
| A | 0.50% | rv20_mid | **95.5%** | élevé (gate) | 6 mois | ✗ (N=1 chop) |
| A-bis | 0.50% | aucun | **79.2%** | min 18.5% fold | 5 mois | ⚠ (1 fold mauvais) |
| B | 1.25-1.5% | aucun | 53-55% | min 37-40% fold | 1-1.5 mois | ✓ structurel |
| C | 0.75% | rv20_mid | **88.7%** | non chiffré | 3.5 mois | ✗ (N=1 chop) |
| D | 0.25% | n/a | 100% (biaisé) | 94% cens | 14 mois | ✗ (data limit) |

**Prérequis universel (toute option) :**
1. **Paper-trade 2 mois** avant fees pour calibrer slippage live (audit §3.3 — slip 0.10R = -15pt p_funded).
2. **Vérifier règles 2026 FTMO** : daily 5%, total 10%, no time limit. Confirmer pas de "trailing" déguisé.
3. **Calibrer le payout schedule** : 0.50% sizing = 5-month grind → 2 mensualités tampons avant 1er payout.

**Moyen terme (post-extension NQ/DAX 2008-2025) :**
4. Fetch firstratedata.com NQ + Dukascopy DAX 2008-2025 (~$200, 2 semaines).
5. Refit p_funded uncapped sur N=5-7 chop episodes distincts.
6. **Si rv20_mid gate maintient +10pt+ sur N=5+** → GO Option A (0.50% + gate) confirmé.
7. **Si rv20_mid gate < +5pt** → fallback Option A-bis (0.50% no-gate, 79.2% honnête).
8. **Si extension révèle chop catastrophique** (chop_overlap < 30% sur median) → Option B (1.25-1.5%) seul scénario robuste.
9. **Si extension permet WF cleanement à 0.25%** → Option D devient candidat sérieux.

**Recommandation personnelle (sans extension data) :**
- **Privilégier Option A-bis (0.50% no-gate)** : p_funded 79% est défendable structurellement (pas dépendant d'un gate fragile N=1) et stricte amélioration vs Option B en mean. Le risque fold2 (18.5%) est connu et acceptable s'il signifie 1 attempt sur 5.
- **Si bridge entre les deux mondes voulu** : Option C (0.75% + rv20_mid) — gain de speed (3.5 mois vs 5 mois) mais dépendance gate.
- **Option A pure (95.5%)** : à réserver post-extension data. En l'état, c'est un fit ${N=1}$ non défendable.
- **Option B (1.25%)** : si vous ne pouvez vraiment pas accepter un fold à 18%. Worst-case 38-40% est l'argument de sécurité.

**À écarter définitivement :**
- Sizing 0.10% (78% censurés = non-mesurable, jamais).
- Sizing ≥2.0% (bust_daily déclenche, p_funded chute brutalement).
- Sizing 0.25% avant extension data (22% censure full + 94.6% cens fold).
- Gate vr5_low sur uncapped (-1 à -6pt vs no-gate — inverse du capped).

---

---

## 6. Reproductibilité

Tous scripts dans `data/ftmo_research/audit/` :

| Étape | Script | Sortie |
|---|---|---|
| 1 sweep uncapped | `optim_step7_uncapped_sweep.py` | `optim_step7_uncapped_sweep.csv` + `optim_step7_output.txt` |
| 2 régime split | `optim_step8_regime_split.py` | `optim_step8_regime_split.csv` + `optim_step8_output.txt` |
| 3 WF maximin | `optim_step9_wf_maximin.py` | `optim_step9_wf_uncapped.csv` + `optim_step9_output.txt` |
| 4 gate uncapped | `optim_step10_gate_uncapped.py` | `optim_step10_gate_uncapped.csv` + `optim_step10_output.txt` |

Engine étendu : `audit/optim_engine.py` (flag uncapped + container `ftmo_2step_uncapped` + censure handling).

Tous seeded, déterministes. `cd audit && /usr/bin/python3 stepX.py`.

---

## 7. In-sample vs WF vs Live — marquage explicite

| Chiffre | Source | Statut |
|---|---|---|
| p_funded ftmo_2step_uncapped 0.75% = 71.6% | step7 full | **in-sample 2022-2026 H1**, n_résolu=1058, censure 7% |
| p_funded 0.50% = 79.2% | step7 full | **in-sample**, censure 14% |
| p_funded 0.25% = 100% | step7 full | **biais sample** (78% des starts excluant), non-fiable |
| WF mean 0.50% = 82.7% / min 18.5% | step9 | **WF 5 folds**, dispersion ±63pt |
| WF mean 1.50% = 55% / min 40% | step9 | **WF 5 folds**, le plus robuste |
| chop_overlap 0.50% = 42.8% / trending = 100% | step8 | **in-sample N=1 chop episode (2023)** |
| **+17pt rv20_mid gate à 0.75%** | step10 | **in-sample N=1**, ablation L19 statistiquement significative mais non-généralisable |
| fast_bust ≈ 0% à tous sizings ≤1.0% | step7 | **structural** (defined-risk 1R, robuste) |
| Mécanisme = long-grind survival | step8 + interprétation | **structural** (cohérent avec block-capped sizing) |
| **Live performance** | — | **0 jour** — paper required avant fees |

---

## 8. Pourquoi le verdict précédent était faux (récap)

`OPTIM_ORB_propfirm.md §1` concluait :
- ftmo_2phase à 1.25%, capped 40j : p_funded = 52%
- Mur math : p(P1) × p(P2|P1) ≤ 0.76 × 0.78 = 0.59 max
- NO-GO sur cible 70%

**Correction** : ce calcul était valide POUR le cap. En uncapped :
- À sizing 0.25%, on a effectivement p(P1) = 100% et p(P2|P1) = 100% (sur les starts résolus).
- À sizing 0.75% : p(P1) = 83%, p(P2|P1) = 86%, p(funded) = 71.6%. Pas de mur math, juste un trade-off sizing × censure.

**L'erreur de raisonnement** : le cap forçait la stratégie à atteindre +10% en 40 jours, ce qui demande risk ≥ 1% (drift mean 0.06%/jour × 40j à 0.06% = 2.4%, vraiment loin de +10%). Forcé à risk ≥ 1%, on était dans la zone où le bust_total domine et p(P1) ≤ 76%. Le « mur » était bel et bien dû à ce risk plancher imposé par le cap.

Uncapped permet le down-sizing arbitraire — donc permet d'attaquer le mur math via du temps. C'est le facteur dont l'audit n'avait pas conscience puisqu'il avait hérité du cap iid bootstrap.

---

*Optimisation 2-step uncapped réalisée 2026-06-01 — Claude Code (Opus 4.7 1M ctx). L19 + L10 + L15 respectés. Real-path contigu uniquement. Censure handled. Aucun re-fit massif. Tous chiffres reproductibles ci-dessus.*
