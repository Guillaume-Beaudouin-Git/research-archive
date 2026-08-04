# Audit de la sleeve J1 (USDJPY 12-1 long-only) — 2026-08-04

**Statut : DIAGNOSTIC. Aucune modification de spec proposée en dur.**
Périmètre : lecture seule sur tout chemin live (`ftmo_live/`, `strategies/`, `Portfolio/`).
Moteur : `data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py` (librairie canonique
trackée) — importé, **jamais modifié** ; l'instrumentation de levier passe par un monkey-patch
en mémoire dans `code/q4b_realised_leverage.py`.
Interpréteur `/usr/bin/python3`. Échantillon **2013-10-01 → 2026-06-05, N = 3 295 jours**.

---

## 0. Verdict en une ligne

**J1 n'est pas une sleeve : c'est un long USDJPY vol-targeté allumé 65 % du temps
(R² = 65.6 %, α = +0.29 %/an, t_HAC = +0.22).** Le filtre 12-1 ne sépare rien
(E[r|mom>0] = +1.88 bps/j contre **+1.68 bps/j inconditionnel**), il ne bat le buy-and-hold
que **4 années sur 14**, et **remplacer le signal par un long inconditionnel donne
exactement la même p(campagne) : 72.10 % contre 72.10 %, Δ = +0.00 pt [-4.05, +4.05]**.
La diversification qu'elle apporte est réelle (+6.17 pt de p(campagne) contre J1 OFF)
**mais générique** : elle tombe au 88ᵉ percentile de ses propres placebos par décalage
circulaire — n'importe quelle série USDJPY persistante fait le même travail.
Et c'est la jambe qui a cassé un compte : **à levier déployé elle consomme à elle seule
la totalité du budget daily un jour sur cinq**, avec jusqu'à **7.3 points d'équité
invisibles** au breaker M5.

Formulation demandée : **c'est du beta long déguisé, sans edge propre — mais dont la
PRÉSENCE (pas le signal) paie encore ~6 pt de p(campagne).** Les deux moitiés de la phrase
sont vraies simultanément, et elles pointent vers des actions différentes.

---

## 1. Q1 — Régression d'orthogonalité (L38) — LA réponse

Benchmark = **buy-and-hold USDJPY vol-targeté à l'identique** : mêmes `rv` 60 j, même
`(0.10/rv).clip(5.0)`, même `shift(1)`, même clip ±1.5 — **seul le gate 12-1 est retiré**.
C'est aussi, par construction, la **baseline inconditionnelle appariée exigée par L58**
(le piège L58 croît avec la directionnalité, et cette sleeve est long-only : cas dangereux).

| | α (%/an) | t_HAC(6) | p | β | t_HAC(β) | **R²** |
|---|---|---|---|---|---|---|
| **GROSS** (coût 0) | **+0.294** | **+0.22** | 0.824 | **0.6558** | +21.20 | **65.6 %** |
| **NET** (1.86 bps all-in + swaps) | +0.232 | +0.18 | 0.860 | 0.6554 | +21.19 | **65.5 %** |

**R² = 65.6 % ≫ 30 % ⇒ ce n'est pas une sleeve, c'est du TIMING DE BETA.**
Le seuil L38 est franchi par un facteur 2.2.

Le détail qui ferme la question : **duty cycle = 64.8 %** et **β = 0.656**. β ≈ duty cycle
à 1 point près. C'est la signature arithmétique d'une sélection **non informative** : la
sleeve est le benchmark, allumé 65 % des jours, et le choix des jours n'ajoute rien.
Le résidu de 34 % de variance n'est pas de l'alpha, c'est du **bruit d'allumage**.

Corollaire mesuré : **SPREAD J1 − BH = SR −0.237, −1.37 %/an**. Le gate ne se contente pas
de ne rien ajouter, il **retranche** — voir §3.

> Ceci **confirme et durcit L37** (qui donnait « 70 % de beta » et le filtre carry cosmétique
> à 99.9 %). Mesure ici : 65.6 % de R², α nul à t 0.22, et le filtre **12-1** lui aussi
> cosmétique au sens fort — non pas parce qu'il coïncide avec un autre signal, mais parce que
> **sa version inconditionnelle produit le même résultat de campagne au centième de point**.

---

## 2. Q2 — Le signal 12-1 a-t-il encore un edge ?

Bootstrap **par blocs** (Politis-Romano, bloc moyen 10 j, 1 500 tirages) — jamais iid.

| série | SR | t_HAC(6) | boot95 | ann. |
|---|---|---|---|---|
| J1 **GROSS** (coût 0) | +0.434 | +1.55 | [−0.13, +1.01] | +3.47 %/an |
| J1 **NET** (1.86 bps + swap) | +0.416 | +1.49 | [−0.15, +0.98] | +3.32 %/an |
| **BH vol-targeté (net)** | **+0.478** | **+1.74** | [−0.04, +1.02] | +4.72 %/an |

Le gate au **GROSS** est déjà sous le RESEARCH_PASS (0.7). **Le coût n'est pas le sujet** :
drag 0.13 %/an à 1.86 bps all-in, 0.25 %/an même à 2× le tarif, contre 3.45 %/an de gross.
Le CI95 bootstrap **contient zéro**. Le SR 0.49 du checkup de juillet est reproduit à
l'arrondi ; la marque « DÉCAYÉE » est confirmée, mais le diagnostic exact est plus dur que
« décayée » — voir les ères.

### Ères (L31 : régime carry JPY exceptionnel 2022-24 puis unwind)

| ère | N | SR J1 (net) | t_HAC | SR BH |
|---|---|---|---|---|
| pré-2021 (2013-10 → 2020-12) | 1 884 | +0.137 | +0.37 | +0.030 |
| post-2021 | 1 411 | +0.715 | +1.67 | **+1.058** |
| **fenêtre 2022-2024** | 780 | +1.025 | +1.73 | **+1.235** |
| **HORS 2022-2024** | 2 515 | **+0.153** | +0.49 | +0.219 |

Tout le SR de la sleeve vit **dans la fenêtre 2022-2024** — exactement le régime que L31
ordonne d'isoler. Hors cette fenêtre : **SR 0.153**. Et dans **chaque** ère où la sleeve
performe, le **buy-and-hold fait mieux qu'elle**.

### Walk-forward (5 folds expanding, OOS net)

| fold | période | N | SR J1 | SR BH |
|---|---|---|---|---|
| 1 | 2020-02 → 2021-05 | 330 | +0.358 | −0.177 |
| 2 | 2021-05 → 2022-08 | 329 | +1.872 | +1.983 |
| 3 | 2022-08 → 2023-11 | 330 | +0.836 | +1.097 |
| 4 | 2023-11 → 2025-02 | 329 | −0.184 | +0.147 |
| 5 | 2025-02 → 2026-06 | 330 | +0.384 | +0.686 |

**WF = 4/5 = 80 %** — au-dessus du gate PROPFIRM_PASS (60 %). **Et ça ne prouve rien ici** :
le BH fait mieux que J1 sur **4 des 5 folds**. Le walk-forward mesure la persistance du
**beta USDJPY**, pas celle du signal. C'est le cas d'école du « WF vert sur une sleeve
sans alpha ».

### DSR (`dsr.py` racine, **rf = 0**, `std_sr_trials` estimé sur la famille = 0.341)

| n_trials | benchmark E[max SR] | **DSR** | verdict |
|---|---|---|---|
| 4 (les 4 variantes de cet audit) | 0.359 | **0.582** | FAIL |
| 30 | 0.707 | **0.148** | FAIL |
| 321 (ledger global) | 0.994 | **0.019** | FAIL |
| 321, au **GROSS** | — | **0.022** | FAIL |

Skew journalier **−0.271**, excès de kurtosis **+6.94**. Plancher de bruit d'échantillonnage
SR = 0.277 pour N = 3 295. **DSR échoue à tous les comptes d'essais, y compris n_trials = 4**,
c'est-à-dire même en ne comptant que les quatre variantes tournées dans ce seul document.
Conformément à l'avertissement du brief, DSR et WF sont **orthogonaux** : ici WF 80 % et
DSR 0.019 coexistent, et c'est le DSR qui a raison — le WF est vert **par le beta**.

---

## 3. Q3 — La jambe short (L25), jambes DISJOINTES, coût ZÉRO

Jambes construites séparément sur des ensembles de dates **disjoints** (`mom>0` vs `mom<0`),
pas par `-side_long`. **Recouvrement vérifié = 0 jour.**

| jambe | N jours actifs | SR | t_HAC | ann. |
|---|---|---|---|---|
| LONG (gross, coût 0, swap 0) | 2 135 | +0.434 | +1.55 | +3.47 %/an |
| **SHORT (gross, coût 0, swap 0)** | 1 144 | **−0.237** | **−0.88** | **−1.37 %/an** |

Moyennes conditionnelles du rendement USDJPY :

```
E[r | mom > 0]  = +1.88 bps/j   (N = 2 136)
E[r | mom < 0]  = +1.32 bps/j   (N = 1 145)
E[r] uncond.    = +1.68 bps/j   <-- baseline L58
```

Trois lectures, toutes fatales :

1. **La jambe short est négative à coût ZÉRO** ⇒ L25 échoue ⇒ **beta long déguisé**, verdict
   sans appel.
2. Les jours « mom < 0 » ont un rendement moyen **positif** (+1.32 bps/j). Le signal ne
   désigne pas des jours baissiers, il désigne des jours **un peu moins haussiers**.
3. Le pouvoir séparateur total du 12-1 vaut **+1.88 − 1.68 = +0.20 bps/j** au-dessus de
   l'inconditionnel. À comparer au coût all-in de **1.86 bps RT** : le lift conditionnel du
   signal représente **11 % d'un aller-retour**. Il n'existe aucun régime de coût où ce gate
   est monétisable.

**Année par année (gross, échelle recherche, % cumulé)** — le gate ne bat le buy-and-hold
que **4 années sur 14** (8 défaites, 2 égalités), et ses deux seules grosses victoires
(2017, 2020) sont compensées par ses deux grosses défaites (2018, 2021) :

| | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| J1 | 8.50 | 17.46 | −0.81 | −0.87 | 1.00 | −10.78 | −1.72 | 1.07 | 6.63 | 18.87 | 2.91 | 5.17 | −3.45 | 1.35 |
| BH | 8.50 | 17.42 | −0.90 | −0.30 | −2.74 | −5.06 | 2.39 | −9.04 | 16.68 | 18.87 | 5.95 | 9.12 | 0.56 | 1.80 |
| **Δ** | 0.00 | +0.04 | +0.09 | −0.58 | **+3.74** | **−5.72** | −4.11 | **+10.11** | **−10.05** | 0.00 | −3.04 | −3.95 | −4.01 | −0.44 |

**Swap — de quel côté la sleeve paie-t-elle ?** L'alerte du jour (`spec_bounds_breach = 1`,
USDJPY short **−22.18** vs ancre **−20.30**, dérive +9.3 %) porte sur le **côté SHORT**.
La sleeve est **long-only** : elle ne le touche jamais.
- swap effectivement payé, jambe long, sur les 2 146 nuits tenues : **−0.015 %/an** (nul).
- ce que la même exposition aurait coûté du côté short : **−3.63 %/an**.
⇒ **La dérive de swap du jour est sans effet sur J1.** Elle est en revanche la preuve
chiffrée qu'une version two-sided serait morte deux fois : jambe short négative en gross
**et** −3.63 %/an de portage.

---

## 4. Q4 — La queue est-elle modélisable ? (le point le plus utile)

### 4.0 Qualité de la donnée (L60) — série propre

`data/deep_history_utc/USDJPY_M1.csv`, 4 753 398 barres M1 depuis 2013-09 :
**high == low sur 0.82 %** des barres (max annuel 1.86 % en 2014, 1.15 % en 2026).
Pas de zéro-inflation, pas de print de règlement. **La série est utilisable.**
(Contraste avec XPT/XPD de L60 : 61-69 %.)

### 4.1 Le simulateur est structurellement aveugle à l'intra-M5

`cache/sim_m5_repaired.parquet` ne contient **qu'un CLOSE M5 par instrument** — pas d'OHLC.
Le breaker du moteur (`run_phase`) teste l'équité **sur cette grille de closes M5**. Il ne
peut donc, par construction, voir aucune excursion vivant **à l'intérieur** d'une barre M5.
C'est le pendant **L59** pour cette sleeve : le delay+1 certifie l'ENTRÉE (22:05), la SORTIE
est un **stop rempli au close M5 exact** alors que la liquidation réelle est continue.

Mesure directe, grille jour-compte **Europe/Prague** (offset vérifié par appariement
tick-à-tick : les timestamps du panel sim sont CET/CEST, pas UTC — L52 appliqué), excursion
adverse depuis l'ouverture du jour, côté long, N = 3 294 jours :

| quantile | M1 low (réel) | M5 close (vue du sim) | sous-estimation |
|---|---|---|---|
| p50 | −0.280 % | −0.252 % | −9.9 % |
| p90 | −0.882 % | −0.852 % | −3.4 % |
| p99 | −2.001 % | −1.905 % | −4.8 % |
| p99.9 | −4.284 % | −4.050 % | −5.5 % |
| **p100** | **−7.162 %** | **−6.240 %** | **−12.9 %** |

Profondeur invisible : **moyenne 3.05 bps, p99 19.75 bps, max 97.65 bps** (2023-10-03,
suspicion d'intervention BoJ — 98 bps de mouvement entièrement logés **entre deux closes M5**).

### 4.2 Levier RÉELLEMENT porté (405 cohortes du funnel audité, marges Swing)

`w × vm` est une borne haute — le cap marge 60 % rabote toutes les jambes. Levier
**mesuré** au rebalance 22:05 (notionnel J1 / équité) :

| config | p10 | p50 | p90 | p99 | ≥ 12x | ≥ 16.8x |
|---|---|---|---|---|---|---|
| pré-v2.8 (cap marge seul) | 4.38x | **8.98x** | 17.98x | 18.04x | 28.2 % | **16.4 %** |
| v2.8 `leg_lev_cap` 12x | 3.86x | **7.40x** | 12.01x | 12.05x | 20.0 % | **0.0 %** |

**Le cap 12x fait son travail** : l'état 16.8x — celui du breach du 2026-07-02 — était atteint
**16.4 % des nuits** avant v2.8 et l'est **0.0 %** après. Le mouvement USDJPY qui consomme
tout le budget daily passe, au décile le plus levé, de **0.278 % à 0.416 %**.

### 4.3 Ce que ça donne face à la barrière : J1 consomme le budget d'un jour sur cinq

Levier réalisé × excursion vraie du jour de détention. **Fraction du budget daily (−5 %)
consommée par J1 SEUL** :

| | p50 | p75 | p90 | p95 | p99 | p100 |
|---|---|---|---|---|---|---|
| pré-v2.8, réel (M1) | 45.3 % | 94.6 % | 167 % | 218 % | 391 % | **1 139 %** |
| **v2.8 12x, réel (M1)** | **38.4 %** | 80.6 % | 139 % | 173 % | 293 % | **958 %** |
| v2.8 12x, vu par le sim | 34.3 % | 75.4 % | 131 % | 165 % | 287 % | 811 % |

| événement | pré-v2.8 | v2.8 12x | le sim le voit |
|---|---|---|---|
| J1 seul mange **tout** le budget daily | **24.1 %** des jours | **18.7 %** | sous-estimé de 9 % |
| J1 seul franchit la **ligne du breaker** (30 % restant) | 35.5 % | **30.3 %** | sous-estimé de 9-11 % |

**Un jour de détention sur cinq, la seule excursion intraday de USDJPY suffit à épuiser
l'intégralité du budget daily de −5 %.** Ce qui sépare ces jours d'un bust n'est pas la
taille de l'edge : c'est le fait que le **breaker M5 discret** parvienne à sortir à temps.

### 4.4 Combien le sim sous-estime : la réponse chiffrée

Profondeur d'équité **invisible à un breaker qui ne voit que les closes M5**, en points
d'équité (budget daily = 5.00 pts, floor statique = 10.00 pts) :

| config | moyenne | p90 | p99 | **max** | p(invisible > 30 % du budget) |
|---|---|---|---|---|---|
| pré-v2.8 | 0.289 pt | 0.557 | 2.513 | **8.727 pt** | 2.23 % |
| **v2.8 12x** | **0.237 pt** | 0.475 | **2.176** | **7.345 pt** | 1.47 % |

**Le post-mortem a raison, et voici la taille de l'erreur.** Il existe dans l'échantillon des
journées où **plus d'un budget daily entier (jusqu'à 7.3 points sur un floor de 10)** s'est
produit *entre deux closes M5* — donc totalement invisible au breaker du simulateur, qui
sort proprement à la ligne là où le compte réel est liquidé en continu. C'est **exactement
le mécanisme du 2026-07-02**. Et ~1.5 % des jours-compte franchissent le seuil « la partie
invisible dépasse à elle seule 30 % du budget ».

Conclusion de modélisation : **la queue n'est pas modélisable dans le stack actuel.** Non
parce que le générateur est mauvais, mais parce que **la donnée d'entrée n'a pas la
résolution** — un breaker est un stop, et L59 dit de repricer la SORTIE séparément. Le
correctif est une donnée (OHLC M1 ou M5-OHLC dans `sim_m5`), pas un paramètre.

### 4.5 Moments (L39 : daily ET monthly, au levier DÉPLOYÉ — L54)

| échelle | vol | skew daily | exkurt daily | skew monthly | MaxDD |
|---|---|---|---|---|---|
| recherche (w brut, vol-target 10 %) | 7.97 %/an | **−0.271** | **+6.94** | +0.287 | −22.3 % |

Skew **daily négatif** / **monthly positif** : dissociation L39 pleine et entière. Le daily
lie la barrière FTMO, le monthly flatte le book perso — **c'est le daily qui décide ici**.
Épaisseur de queue : p(z < −3) = 1.028 % contre 0.135 % gaussien (**×7.6**) ;
p(z < −4) = 0.363 % contre 0.003 % (**×114**). Pires séances à échelle recherche :
−3.50 %, −3.40 %, −3.19 %, −2.97 %, −2.84 %.
*(La MaxDD n'est PAS invariante d'échelle — L54 : au levier déployé, l'objet pertinent est
la table §4.3, pas un MaxDD annualisé.)*

---

## 5. Q5 — Rendement ou diversification ?

### 5.1 Corrélations (échelle recherche, net)

| sleeve | SR | vol | ann. | jours flat |
|---|---|---|---|---|
| overnight (US100+GER40, lun/mar) | +0.470 | 6.26 %/an | +2.94 %/an | 60.1 % |
| gold trend | +0.124 | 8.04 %/an | +0.99 %/an | 40.5 % |
| **J1** | +0.416 | 7.97 %/an | +3.31 %/an | 33.3 % |

**ρ(J1, overnight) = +0.037** (+0.070 sur les jours où les deux sont actifs) ;
ρ(J1, gold) = +0.058. **Décorrélation réelle.** Et J1 est actif **17.8 %** des jours où
tout le reste du book est flat — le profil de « remplisseur de temps mort » qui fait gagner
du p(pass) indépendamment du SR (mécanisme documenté dans `barrier.py`).

### 5.2 Effet marginal, barrières réelles (daily −5 %, floor **STATIQUE** −10 %, horizon 182 j)

`Portfolio/admission/barrier.py`, poids **ERC**, bootstrap par blocs (bloc moyen 10 j),
chemins **appariés** (même graine), 4 000 chemins, book re-levé ×6 pour placer la p(pass)
de l'incumbent dans la bande live.

| | p(pass) | médiane |
|---|---|---|
| book seul (overnight + gold, ERC) | 26.85 % | 43 j |
| **+ J1** | 28.82 % | 43 j |
| **Δ** | **+1.97 pt** | **+0.0 j** |

Répartition des morts dans CETTE simulation : **daily 54.6 % / floor 18.1 %** ; ajouter J1
déplace le floor à 16.8 % et laisse le daily à **54.3 %**. **J1 ne réduit pas la mort par
barrière daily** — c'est-à-dire précisément la barrière que sa propre queue attaque (§4.3).

> ⚠ Caveat honnête : le book de référence est décrit ailleurs comme **FLOOR-DOMINATED
> (49.7 %)**, ma simulation sort **daily-dominated**. La différence vient du levier (×6)
> et du proxy de sleeve overnight reconstruit ici, pas d'une contradiction de mesure.
> **C'est une raison de plus de citer §5.4 (funnel audité, comptabilité complète) plutôt
> que §5.2 comme chiffre de décision.**

### 5.3 PLACEBO À AUTOCORRÉLATION APPARIÉE (obligatoire — et c'est lui qui tranche)

Décalages **circulaires** de J1 : marginale identique, autocorrélation identique, moyenne
identique, **alignement temporel détruit**. 60 décalages tirés au sort.

```
placebo Δp     : moyenne +3.82 pt   p5 +1.46   p50 +4.08   p95 +6.09
J1 RÉEL        : +1.97 pt   ->  13e PERCENTILE de sa propre distribution placebo
```

**Le J1 réel diversifie MOINS bien que 87 % de ses propres versions décalées au hasard.**
Le +1.97 pt n'est pas de la diversification apportée par le signal : c'est l'effet mécanique
« ajouter une seconde source de vol quasi-décorrélée », que **n'importe quelle** série
persistante fournit — et le timing effectif de J1 le dégrade légèrement.
Contrôle complémentaire (J1 strictement dé-moyenné, persistance conservée) : Δp = **−1.50 pt**.

### 5.4 Ré-mesure du « J1 OFF = Δp −7.6 » SUR LE FUNNEL AUDITÉ LUI-MÊME

405 cohortes appariées (départs hebdo 2014-10 → 2025-08, mur 91 j, marges Swing, cap 12x) :

| | p(campagne) | médiane | tentatives |
|---|---|---|---|
| **J1 ON (déployé)** | **72.10 %** | 37 j | 3.13 |
| J1 OFF | 65.93 % | 39 j | 2.90 |
| **contribution J1** | **+6.17 pt** | CI95 **[+1.29, +11.05]** | 64 cohortes retournées gagnantes / 39 perdues |

**Le chiffre historique est CONFIRMÉ** : retirer J1 coûte ~6 pt, significativement > 0.
Mais le même protocole appliqué aux **placebos par décalage circulaire du poids J1** (N=25) :

```
placebo : moyenne +3.19 pt   p5 −0.69   p50 +2.96   p95 +9.14
J1 RÉEL : +6.17 pt   ->  88e percentile   (< p95)
```

**Non signal-spécifique.** Le book gagne ~6 pt parce qu'il porte une seconde jambe FX
persistante et quasi-décorrélée, pas parce que cette jambe est pilotée par un momentum 12-1.

### 5.5 Le test qui clôt le dossier : le gate contre l'inconditionnel, dans le funnel

Même 405 cohortes, on remplace le **seul** gate `1{mom>0}` par un **long inconditionnel**
(vol-targeting, cap, quantization, coûts, swaps : tout le reste identique) :

| variante | p(campagne) | médiane |
|---|---|---|
| 12-1 gate (déployé) | **72.10 %** | 37 j |
| **long inconditionnel** | **72.10 %** | **36 j** |
| **Δ (gate − inconditionnel)** | **+0.00 pt** [−4.05, +4.05] | **+1 j (au désavantage du gate)** |

**Zéro. Au centième de point.** Le signal 12-1 ne change **rien** au résultat de campagne ;
sa seule trace mesurable est **un jour de médiane en plus**.

### 5.6 Diagnostic annexe : sensibilité au cap de jambe (pour information, NON une reco)

| cap | p(campagne) | médiane | Δ vs 12x | CI95 |
|---|---|---|---|---|
| aucun (cap marge 60 % seul) | 75.06 % | 36 j | +2.96 pt | [−0.78, +6.71] |
| 18.05x | 74.57 % | 36 j | +2.47 pt | [−1.28, +6.21] |
| **12x (déployé v2.8)** | **72.10 %** | 37 j | — | — |
| 8x | 73.09 % | 36 j | +0.99 pt | [−3.18, +5.15] |
| 6x | 68.40 % | 36 j | −3.70 pt | [−8.10, +0.70] |
| 4x | 66.91 % | 38 j | −5.19 pt | [−9.52, −0.85] |

Sur **[8x, 18x] tous les CI95 traversent zéro** : le coût en p(campagne) du serrage est
indistinguable de zéro sur cette plage, et **8x n'est pas mesurablement plus cher que 12x**
tout en portant le mouvement-à-breach de 0.417 % à 0.625 % (+50 %). En dessous de 6x le
coût devient réel. **Ce tableau ne justifie pas un re-fit du seuil** — la spec v2.8 pose
déjà explicitement que « le seuil se justifie par le tampon de queue, JAMAIS par p(pass) »,
et re-fitter sur cette frontière serait de l'overfit (Leçon 10, L20). Il est ici pour dire
une seule chose : **il reste du tampon de queue gratuit disponible.**

---

## 6. Synthèse — les deux moitiés de la vérité

**Ce que J1 n'est pas.** Une sleeve avec un edge. R² 65.6 % contre son propre buy-and-hold,
α +0.29 %/an à t 0.22, DSR 0.019 (0.582 même à n_trials = 4), jambe short négative à coût
zéro, lift conditionnel de +0.20 bps/j soit 11 % d'un aller-retour, SR 0.153 hors de la
fenêtre 2022-2024, battue par le buy-and-hold **8 années sur 14** (2 égalités, 4 victoires),
et **strictement
équivalente à un long inconditionnel dans le funnel (Δ = +0.00 pt)**.

**Ce que J1 est.** Une **seconde source de volatilité FX persistante et quasi-décorrélée**
(ρ = +0.037 avec l'overnight, active 17.8 % des jours où le book est flat), qui vaut
**+6.17 pt de p(campagne)** — chiffre robuste et significatif — mais dont **aucune part
n'est attribuable au signal** (88ᵉ percentile de son propre placebo ; 13ᵉ percentile sur la
mesure barrier.py).

**Ce qu'elle coûte.** À levier déployé elle consomme **tout le budget daily un jour sur
cinq** (18.7 % post-cap, 24.1 % pré-cap), avec skew daily −0.27, kurtosis +6.9, queue à
−3σ **7.6× la gaussienne**, et une profondeur d'équité **invisible au breaker M5 allant
jusqu'à 7.3 points** sur un floor de 10. Le cap 12x de v2.8 a supprimé l'état 16.8x du
breach (16.4 % → 0.0 % des nuits) et c'était la bonne décision ; il n'a **pas** rendu la
queue modélisable.

**Verdict.** La sleeve est **mal nommée** : ce n'est pas du « carry-aligned trend », ni même
du « TSMOM long-only USDJPY » — c'est un **long USDJPY vol-targeté avec un interrupteur
non informatif**. Le nommer ainsi est la première correction, et elle est gratuite.
Le garder ou non n'est **pas** une question d'alpha (il n'y en a pas) : c'est un arbitrage
**+6 pt de p(campagne) contre une queue non modélisée qui a déjà tué un compte**. Ce
diagnostic ne tranche pas cet arbitrage — il en donne les deux termes chiffrés.

---

## 7. Ce que ça NE prouve PAS

1. **Ça ne prouve pas que retirer J1 est bon.** L'ablation est nette : −6.17 pt
   [−11.05, −1.29]. Le book déployé est **MONO** ; retirer la seule jambe décorrélée
   restante aggrave un problème déjà identifié (`desk_audit_2026-07-24`).
2. **Ça ne prouve pas qu'un long inconditionnel est le bon remplaçant.** L'équivalence
   mesurée est **Δ = +0.00 pt sur les mêmes 405 cohortes historiques** ; un long
   inconditionnel USDJPY est un pari directionnel permanent sur le dollar, dont le
   drawdown potentiel n'est pas borné par un signal qui coupe. Le gate est inutile
   *en espérance* ; il n'est pas prouvé inutile *en tail-risk conditionnel*, et je ne l'ai
   pas testé sous cet angle.
3. **Ça ne prouve pas que le placebo circulaire soit le bon nul dans l'absolu.** Il conserve
   marginale et autocorrélation mais casse toute co-dépendance de régime avec le book. Un
   placebo qui préserverait aussi l'appariement régime-par-régime serait plus dur.
4. **Ça ne prouve pas la taille exacte de l'erreur de queue du simulateur.** Je mesure
   l'écart entre un breaker M5-close et le vrai chemin M1 — la liquidation réelle est
   **continue**, plus fine que M1. Mes chiffres §4.4 sont donc une **borne inférieure**
   de la sous-estimation. Ils ne remplacent pas une ré-exécution du funnel sur donnée
   OHLC (qui exigerait de reconstruire `sim_m5` avec high/low, hors périmètre lecture seule).
5. **Ça ne prouve rien sur la période post-2026-06-05.** Le cache panel s'arrête là ;
   le breach du 2026-07-02 est **hors échantillon** — je caractérise son *mécanisme*
   sur l'historique, je ne rejoue pas l'événement.
6. **Le tableau §5.6 n'est pas une frontière optimisable.** 6 points de cap testés sur les
   mêmes cohortes ⇒ tout choix de seuil lu dans ce tableau serait un fit sur du bruit
   (tous les CI95 de [8x, 18x] traversent zéro).
7. **Les Δp de §5.2 dépendent de l'échelle** choisie (×6) pour placer l'incumbent dans la
   bande live. Le **signe** et la **position vs placebo** sont robustes ; le niveau absolu
   ne l'est pas. Le chiffre à citer est celui du funnel audité (§5.4), pas celui-ci.

---

## 8. Si une modification devait être envisagée (elle ne l'est pas ici)

Rien dans ces chiffres n'oblige à toucher la spec **aujourd'hui** — `ea_w_usdjpy = 0` :
la sleeve est déjà à poids nul, il n'y a pas d'urgence.

Les deux seuls candidats que les chiffres portent, par ordre de gratuité :

- **Renommer la sleeve** dans `spec_v22.yaml` (`signal:` → *long USDJPY vol-targeté,
  gate 12-1 non informatif, R² 65.6 % vs BH, α t 0.22*). Coût zéro, effet non nul :
  la mauvaise étiquette est ce qui a fait porter à cette jambe un budget de risque
  d'« alpha diversifiant ».
- **Le tampon de queue** : §5.6 montre qu'il en reste du gratuit entre 12x et 8x. À
  n'instruire que sur l'argument tampon, **jamais** sur p(pass).

Dans les deux cas : **chaîne de gel complète** (yaml → mqh → ex5 → pins, re-gel *vendredi
soir après le brain 19:50* pour éviter le piège du restamp-lundi), **fenêtre de déploiement
SAMEDI** (le VPS pull `main` toutes les 30 min : merger EST un déploiement), et
**jamais de squash-merge sur un lot de spec**.

---

## 9. Reproduction

```
code/j1_lib.py                  reconstruction fidèle du bloc J1 de engine.build_signals()
code/q1_orthogonality.py        Q1 (L38/L58) + Q2 (SR/t_HAC/DSR/WF/ères) + Q3 (short disjoint)
code/q4_tail.py                 L60 + excursions M1 vs M5-close + moments + frontière de breach
code/q4b_realised_leverage.py   levier J1 réalisé (monkey-patch, 405 cohortes)
code/q4c_budget_consumption.py  budget daily consommé par J1 seul, réel vs vu par le sim
code/q5_admission.py            rho + barrier.py ERC + placebo circulaire (60 décalages)
code/q5b_funnel_ablation.py     J1 ON/OFF sur le funnel audité + placebo (25 décalages)
code/q5c_variants.py            gate vs inconditionnel + sensibilité au cap de jambe
```

Toutes les entrées sont lues **en absolu** depuis `<HOME>/Desktop/Algo_claude/`
(caches gitignorés, lecture seule). Les artefacts intermédiaires sont écrits dans le
scratchpad de session — **aucun blob data n'est commité**.
