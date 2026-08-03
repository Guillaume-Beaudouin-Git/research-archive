# La vraie thèse de Nagel : la mean-reversion conditionnée à l'état de stress

**Date :** 2026-08-02/03 · **Branche :** `claude/mr-stress-conditional` (worktree dédié, base `origin/main` @ `2f728b3e`)
**Interpréteur :** `/usr/bin/python3` explicite (pandas 2.2.3 / numpy 2.0.2 vérifiés au lancement)
**Données :** `data/deep_history_utc/{US500,US100,US30,GER40}_M1.csv` (vrai UTC vérifié) + `data/panels/vix.csv`,
lues en **LECTURE SEULE** depuis le répertoire principal. `data/panels/m5_indices/` (EET mal étiqueté) n'est
jamais lu. **Gate au GROSS, `cost_rt = 0`** ; coût seulement en aval, à **1.8 bps RT** indices
(`cost_denominator_2026-07/COST_AUDIT.md`) — **jamais** la colonne `spread`.
**Pré-enregistrement :** `PREREGISTRATION.md`, écrit **avant** tout accès à la donnée.
**Cellules : 180 distinctes** (§7). **N1 local = 180.**

---

## Verdict en une page

| # | Question | Verdict |
|---|---|---|
| **V1** | **Le profil par quantile de stress est-il MONOTONE croissant, comme Nagel le prédit ?** | **REJECTED — le profil est PLAT.** Sur 172 formes, la part de gradients positifs est **0.506** (une pièce lancée en l'air), le ρ de Spearman moyen **+0.006**, le Q5−Q1 moyen **+0.09 bps**. Profil poolé : Q1 −2.09 / Q2 −1.55 / Q3 −0.70 / Q4 −1.48 / **Q5 −2.12 bps**. |
| **V2** | Les 12 cellules primaires pré-enregistrées | **REJECTED — 0/12 atteignent t > 2.5.** Les 9 cellules US ont un gradient **NÉGATIF** (les 3 proxys, les 3 instruments) : la MR **empire** avec le stress. Les 3 cellules GER40 sont positives, la meilleure à t 2.30 < 2.5. |
| **V3** | GER40 × `rsi14` 15 min — l'exception | **NON TUÉ mais NE PASSE PAS.** Survit à la permutation d'état (p ≤ 0.001), à l'exclusion COVID, aux 3 proxys, au délai d'entrée. Meurt sur la **multiplicité** : **DSR 0.101** (44 essais) / **0.017** (184), Šidák **échoué**, et **1 instrument sur 4**. Signalé, pas promu. |
| **V4** | Couche barrière (si l'on faisait comme si) | **p(pass) plafonne à 0.184** (vm 5) contre ~53.7 % du livre déployé, et l'avantage sur le placebo d'alignement **disparaît dès vm ≥ 10** (p 0.18/0.47/0.35). **80-93 % des morts sont la barrière journalière.** |

**Ce que ça ferme, et que la mesure inconditionnelle ne pouvait pas fermer :** la thèse **conditionnelle**
de Nagel — le rendement du reversal croît avec le stress — **ne tient pas au niveau INDICE sur véhicule
CFD retail**. Ce n'est plus « la moyenne est négative donc c'est mort » (raisonnement invalide, c'était
l'erreur réparée ici), c'est **« le gradient d'état est nul, mesuré sur 180 cellules, au GROSS »**.
Immune au modèle de coût, aux swaps et à la colonne `spread`.

---

## 1. L'erreur qui est réparée ici

`mr_timezone_repair_2026-08` a mesuré 384 cellules de MR **inconditionnelle** (two-sided gross moyen
**−1.78 bps**, 0 cellule à t > 2.5) et en a conclu « famille fermée par mécanisme ». **Le raisonnement
était invalide** : une moyenne inconditionnelle négative est parfaitement compatible avec un edge
conditionnel fort si l'état porteur est rare. Nagel ne dit pas « la MR paie » ; il dit que le reversal
**rémunère un service de fourniture de liquidité** et que ce prix **monte avec le stress**. Les 60
cellules « regime-conditional » de l'étude d'origine n'ont **aucun code dans le repo** ⇒ la version
conditionnelle n'avait **jamais** été mesurée ici.

**Le seul élément ajouté est le conditionnement d'état.** Les formes de trade sont reprises **telles
quelles** de la grille archivée, pour que la seule différence entre les deux études soit l'état.
Aucune variante inconditionnelle n'est rejouée pour elle-même.

## 2. Proxys d'état — déclarés avant mesure, jamais modifiés après

| | proxy | définition (tout à **T-1**) |
|---|---|---|
| **P1** | **VIX** — *la variable de Nagel elle-même* | clôture VIX de la séance T-1, `data/panels/vix.csv` (2007-01-03 → 2026-05-27, 4 881 lignes, 0 NaN) |
| **P2** | vol réalisée | écart-type des rendements log clôture-à-clôture sur les 20 séances finissant en T-1 |
| **P3** | dispersion intra-journalière | moyenne des \|rendements 5 min\| dans la séance T-1 |

**Bucketisation strictement causale :** percentile **expanding** (rang parmi les valeurs antérieures
uniquement, burn-in **500** observations) ⇒ les frontières de quintile ne contiennent aucune information
future. L'état est **constant à l'intérieur de la séance** ⇒ aucune fuite intra-séance possible.
**Q1 = calme → Q5 = stress.**

## 3. Hygiène, faite avant tout usage

**L60 — barres à fourchette nulle (`high == low`), par série et par année.** Dans la fenêtre réellement
utilisée (séance cash), pire année par série : US500 **5.96 %** (2014), GER40 **1.41 %** (2013),
US30 **1.35 %** (2013), US100 **0.80 %** (2013). Post-2015 : **≤ 0.29 % partout**, le plus souvent
< 0.05 %. **Aucun syndrome XPT/XPD** (61-69 %). Les séries sont utilisables.

**L56 — ancrage à l'horloge d'échange.** Corrélation du profil horaire de |rendement| hiver~été :

| | US500 | US100 | US30 | GER40 |
|---|--:|--:|--:|--:|
| horloge d'**ÉCHANGE** | **0.988** | **0.991** | **0.985** | **0.971** |
| UTC fixe | 0.766 | 0.785 | 0.739 | 0.703 |

Toutes les fenêtres sont définies en `America/New_York` / `Europe/Berlin`, **avec leur DST propre**.

**Colonne `spread` — non utilisée comme coût.** Pour mémoire, part de barres à spread nul mesurée ici :
US30 **80 / 100 / 75 %** en 2019/2020/2021, GER40 15-40 % sur 2013-2017. Confirme l'audit.

---

## 4. LE RÉSULTAT PRINCIPAL — le profil par quantile de stress

### 4.1 Les 12 cellules primaires pré-enregistrées (forme canonique : 5 min, `sma20_z`, θ 2.5, exit ts)

Pente = bps par unité de percentile d'état, **t HAC(6)**. Une pente positive = prédiction de Nagel.

| instrument | P1 (VIX) | P2 (vol réalisée) | P3 (dispersion) | signe |
|---|---|---|---|---|
| **US500** | −4.24 (t −1.60) | −2.74 (t −1.34) | −4.10 (t −1.92) | **négatif ×3** |
| **US100** | −4.45 (t −1.42) | −2.04 (t −0.74) | −4.71 (t −1.64) | **négatif ×3** |
| **US30** | −3.52 (t −1.61) | −2.03 (t −0.97) | −3.84 (t −1.88) | **négatif ×3** |
| **GER40** | +1.30 (t 0.80) | +4.13 (t **2.30**) | +3.08 (t 1.60) | positif ×3 |

**0 cellule sur 12 n'atteint t > 2.5.** La condition 1 de la kill rule échoue d'emblée.
**9 cellules sur 12 ont le gradient du signe INVERSE** à la prédiction : sur les indices US, la
mean-reversion **se dégrade** quand le stress monte.

**Profil complet, US500 × P1 (VIX) — la forme typique du cas US :**

| quantile | n | two-sided m | t | jambe LONG (n, m) | jambe SHORT (n, m) | baseline inconditionnelle **appariée en état** |
|---|--:|--:|--:|---|---|--:|
| Q1 calme | 1073 | **+0.07** | 0.17 | 597, −0.37 | 476, +0.61 | +0.15 |
| Q2 | 675 | −0.78 | −1.21 | 371, −0.54 | 304, −1.07 | +0.27 |
| Q3 | 549 | +0.75 | 0.79 | 317, +0.01 | 232, +1.76 | −0.22 |
| Q4 | 458 | −1.93 | −1.44 | 246, −2.41 | 212, −1.36 | +0.64 |
| **Q5 stress** | 313 | **−3.99** | −1.26 | 170, −1.69 | 143, **−6.72** | **+0.83** |

Noter la colonne de droite : **la baseline inconditionnelle MONTE avec le stress** (+0.15 → +0.83).
C'est exactement le piège annoncé — une baseline plein-échantillon aurait fabriqué un faux PASS sur la
jambe short en état de stress. Avec la baseline **appariée en état** (L58), Q5 reste négatif des deux
côtés (excès −2.52 long / −5.89 short).

**Profil complet, GER40 × P2 — le seul cas où la prédiction tient :**

| quantile | n | two-sided m | t | LONG (n, m, excès L58) | SHORT (n, m, excès L58) |
|---|--:|--:|--:|---|---|
| Q1 calme | 922 | −0.60 | −1.20 | 491, −1.97, −1.71 | 431, +0.97, +0.71 |
| Q2 | 928 | −0.28 | −0.42 | 483, −0.07, −0.28 | 445, −0.51, −0.30 |
| Q3 | 831 | +1.31 | 2.00 | 458, +1.31, +1.31 | 373, +1.31, +1.32 |
| Q4 | 655 | +0.95 | 1.00 | 348, −0.56, −0.92 | 307, +2.66, +3.03 |
| **Q5 stress** | 673 | **+3.12** | 1.79 | 348, +3.99, **+4.09** | 325, +2.19, **+2.10** |

Monotone, deux jambes positives en Q5, deux excès L58 positifs. **Mais t = 1.79 en Q5 et t 2.30 sur la
pente** : sous le seuil pré-enregistré, avant même toute correction de multiplicité.

### 4.2 Le test du mécanisme — la distribution des gradients sur 172 formes

Un edge qui n'apparaît que dans une cellule isolée, sans gradient, est du bruit sélectionné. Le test
honnête est donc la **distribution complète** des gradients sur toute la grille archivée × P2 :

| statistique | valeur | prédiction de Nagel |
|---|--:|---|
| part de pentes **> 0** | **0.506** | ≫ 0.5 |
| pente moyenne | +0.109 bps | ≫ 0 |
| pente médiane | +0.048 bps | ≫ 0 |
| ρ de Spearman moyen (quintile ~ rendement) | **+0.006** | ≫ 0 |
| part de ρ > 0 | 0.453 | ≫ 0.5 |
| Q5 − Q1 moyen | **+0.091 bps** | ≫ 0 |
| part de Q5 − Q1 > 0 | 0.465 | ≫ 0.5 |
| cellules à t_pente > +2.5 / < −2.5 | **5 / 8** | asymétrie positive |

**C'est une pièce lancée en l'air.** Et les queues sont **symétriques** : 5 positives contre 8 négatives,
pour ~1.1 attendue par queue en iid — la sur-dispersion (13 au lieu de ~2) est réelle, mais elle est
**des deux côtés**, donc c'est du bruit sur-dispersé, pas un signal.

**Profil poolé par quantile (moyenne des moyennes two-sided par cellule, 172 formes) :**

| | Q1 | Q2 | Q3 | Q4 | **Q5** |
|---|--:|--:|--:|--:|--:|
| moyenne (bps) | −2.09 | −1.55 | −0.70 | −1.48 | **−2.12** |
| médiane (bps) | −1.32 | −0.84 | −0.09 | −0.71 | −1.40 |
| part de cellules > 0 | 0.05 | 0.13 | 0.42 | 0.27 | 0.29 |

**Q5 ≈ Q1.** Le profil n'est pas croissant ; il est **légèrement en U**, avec un maximum au CENTRE.
Par instrument : GER40 −2.18 → +0.51 (croissant), US100 −1.83 → −3.93, US30 −1.37 → −2.22,
US500 −2.93 → −2.92 (plats ou décroissants).

Le clivage est net et il est **par instrument, pas par quantile** :

| | formes | part de pentes > 0 | pente moyenne |
|---|--:|--:|--:|
| **GER40** | 44 | **0.818** | **+3.47** |
| **US (3 indices)** | 128 | 0.398 | −1.05 |

---

## 5. L'exception GER40 — la batterie de falsification

GER40 est le seul instrument porteur. Il aurait été malhonnête de l'écarter d'un revers de main : il a
été attaqué sur six axes.

**Ce qu'il SURVIT** (cellule la meilleure : GER40 × 15 min × `rsi14` × θ 25 × exit `mt`) :

| test | résultat |
|---|---|
| Q5, gross | **+16.16 bps, t 2.82, n 177** ; jambes **+17.92 / +14.46** (L25 honorée) ; excès L58 apparié en état **+17.34 / +15.08** |
| **Permutation par blocs des ÉTIQUETTES d'état** (L = 21 séances, 2 000 tirages) | pente observée +23.22 contre nulle **+0.17 ± 6.12** ⇒ **p = 0.0005**, percentile 100.0. Contrôle l'autocorrélation d'état — les 4 cellules GER40 testées sont à **p ≤ 0.001** |
| Accord des 3 proxys | VIX **+14.27 (t 2.23)**, vol réalisée +23.22 (t 3.46), dispersion +16.29 (t 2.28) — **les trois du même signe**, y compris la variable propre de Nagel |
| Exclusion COVID (15/02–30/06 2020) | pente **+17.01 (t 2.80, p 0.005)** ; Q5 ex-COVID +10.48 (t 2.00). **Ce n'est pas une crise unique** |
| **Délai d'entrée** (ce qui avait tué le candidat GER40 précédent) | Q5 : **+16.16 → +13.35 → +11.93** à delay+1/+2/+3 (15 et 30 min de retard). **Robuste** — contrairement au candidat d'auction de l'étude précédente (+3.52 → +0.56) |
| L38 β-orthogonalité (cellule primaire) | β **+0.011 (t 0.02)**, α +0.70 bps (t 1.91), **R² = 0.00 %** ⇒ ce n'est pas du beta déguisé |

**Ce sur quoi il MEURT :**

| test | résultat |
|---|---|
| **DSR** (`dsr.py` racine, σ_SR_trials **déclaré** = 0.496, mesuré sur les 44 formes de la recherche GER40) | SR 0.724 contre E[max SR] **1.106** ⇒ **DSR = 0.101 FAIL** (44 essais) ; contre E[max SR] 1.359 ⇒ **DSR = 0.017 FAIL** (184 essais) |
| **Šidák** sur 180 cellules (seuil **2.85 × 10⁻⁴**) | meilleure p de pente **5 × 10⁻⁴** ⇒ **échoue** |
| **Cohérence inter-instruments** (condition 5) | **1 instrument sur 4**. Un mécanisme de fourniture de liquidité n'a aucune raison d'exister à Francfort et de s'inverser à New York |
| Forme primaire pré-enregistrée (5 min `sma20_z`) | pente t **2.30 < 2.5**, et **meurt au délai** : Q5 +3.12 → +2.00 (t 1.22) → **−0.06** à delay+3 |
| Concentration (cellule primaire) | top 1 % des trades = **76.8 %** du P&L de Q5 ; moyenne hors top 5 % = **−3.07 bps** |

**La cellule survivante n'est pas la forme pré-enregistrée** : c'est `rsi14` 15 min, trouvée dans un
balayage de 172. C'est la définition d'un résultat sélectionné, et c'est précisément ce que le DSR
mesure. **DSR 0.017 est un échec net, pas une frontière.**

---

## 6. Couche barrière — « et même si c'était vrai »

Le gate au gross décide déjà (§4). Cette section borne ce que vaudrait la sleeve **si** on ignorait la
multiplicité. Sleeve Q5-only, GER40 15 min `rsi14`, **nette à 1.8 bps RT** : 2 728 séances,
**95.1 % de jours flat**, +196 bps/an, SR net 0.724, pire jour −211 bps.
Barrières FTMO : daily **−5 %** sur l'équité, floor **STATIQUE −10 %**, **aucune limite de temps**
(`Portfolio/admission/barrier.py`, importé sans modification).

| vm | p(pass) | durée médiane (j) | p_floor | **p_daily** | p_timeout |
|--:|--:|--:|--:|--:|--:|
| 1 | 0.003 | 393 | 0.000 | 0.000 | 0.998 |
| **5** | **0.184** | 201 | 0.006 | **0.585** | 0.226 |
| 10 | 0.115 | 182 | 0.010 | **0.770** | 0.093 |
| 20 | 0.061 | 164 | 0.000 | **0.901** | 0.041 |
| 40 | 0.041 | 173 | 0.000 | **0.926** | 0.034 |

**Le maximum est 0.184 à vm 5**, pour 201 jours de durée médiane — contre ~53.7 % pour le livre
déployé. Et **la mort est journalière à 59-93 %**, ce qui rejoint le fait mesuré côté livre (80.2 % des
morts à vm 14) : c'est bien le comportement **intra-journalier en état de stress** qui lie, pas le Sharpe.
Le balayage de taille ne sauve rien : au-delà de vm 5 la barrière journalière mange tout le gain.

### Contrôle apparié — placebos de barrière

**PL-0 (le contrôle demandé, instancié correctement).** Décaler circulairement la *série de rendements*
serait **dégénéré** : `simulate_campaign` la ré-échantillonne par blocs, une rotation laisse sa loi
inchangée. La rotation non dégénérée est celle de **la série d'ÉTAT contre les rendements** : elle
conserve chaque trade, chaque rendement, le clustering et l'autocorrélation d'état, et ne détruit
**qu'une chose** — quelles séances sont étiquetées « stress ». Sanity : 60 décalages, moyenne
**+0.008 bps/j** (observé +0.773), acf(1) −0.014 (observé −0.048), flat **94.9 %** (observé 95.1 %).

**PL-A (zéro-edge, géométrie identique, zéros PRÉSERVÉS).** ⚠ Une première version démoyennait toute la
série ; c'était **confondu** — cela transforme les 95 % de jours flat en jours non nuls et change le
compteur `traded` de `barrier.py`. Version corrigée : on ne démoyenne **que les jours non flat**.

| vm | p(pass) observé | **PL-0** médiane (p95) | p(PL-0 ≥ obs) | **PL-A** médiane |
|--:|--:|--:|--:|--:|
| 5 | **0.184** | 0.059 (0.107) | **0.000** | 0.053 |
| 10 | 0.115 | 0.084 (0.153) | 0.183 | 0.053 |
| 20 | 0.061 | 0.060 (0.102) | 0.467 | 0.031 |
| 40 | 0.041 | 0.035 (0.067) | 0.350 | 0.022 |

Lecture honnête : à **vm 5** l'alignement d'état achète réellement du p(pass) (0.184 contre 0.059,
p 0.000) et la sleeve bat aussi le placebo zéro-edge. **Mais dès vm ≥ 10 l'avantage disparaît**
(p 0.18 / 0.47 / 0.35) : à toute taille qui raccourcirait la campagne, la barrière journalière domine et
l'état ne distingue plus rien. Un p(pass) de 0.184 sur 201 jours n'est pas un véhicule de challenge.

---

## 7. Comptabilité — N1 local

| bloc | cellules |
|---|--:|
| **Primaire** — forme canonique × 4 instruments × 3 proxys | **12** |
| **Breadth** — grille archivée (5 logiques × 2 θ × 2 sorties × 3 TF) × 4 instruments × P2, après filtres n | **172** |
| moins le recouvrement (forme primaire × P2, déjà comptée dans le breadth) | **−4** |
| **TOTAL distinct** | **180** |

**N1 = 180.** Seuil Šidák 5 % = **2.85 × 10⁻⁴**. Les batteries des §5 et §6 (permutation, proxys,
sous-périodes, délai, concentration, DSR, barrière, placebos) sont des **diagnostics sur des cellules
déjà comptées**, pas de nouveaux essais.

Vocabulaire à trois valeurs :
- **REJECTED** — la thèse conditionnelle de Nagel au niveau indice sur CFD retail (V1, V2). Profil plat,
  au gross, sur 180 cellules.
- **NON TUÉ mais NE PASSE PAS** — GER40 × `rsi14` 15 min (V3). Ne consomme pas de budget de modification ;
  aucune promotion, aucune pré-inscription ouverte.
- **UNDERPOWERED** — le conditionnement plus extrême (top 5 % au lieu du quintile) : non testé, faute de
  puissance (n < 60 trades/jambe). Ne consomme pas le budget.

---

## 8. Ce que ce résultat NE prouve PAS

1. **Il ne réfute pas Nagel.** Nagel mesure une **coupe transverse d'actions individuelles US** — le
   reversal y est payé pour absorber des chocs d'inventaire **idiosyncratiques**. Au niveau **INDICE**,
   ces chocs se compensent largement par construction : il ne reste que le déséquilibre agrégé. Un
   gradient nul sur 4 indices est **cohérent** avec un mécanisme réel qui ne survit pas à l'agrégation.
   **Ce qui est fermé, c'est la transposition indice-CFD-retail, pas la thèse académique.**
2. **La version cross-sectionnelle n'est pas testée et ne peut pas l'être ici** : elle demande ≥ 30 noms
   individuels (règle N ≥ 30), qui n'existent pas sur le véhicule FTMO CFD.
3. **Seul l'horizon INTRA-JOURNALIER est testé** (tenues 10-90 min). Le reversal daily/hebdomadaire
   conditionné au stress reste non mesuré ici.
4. **Le résultat GER40 n'est pas montré faux** — il est montré **non établi** : il survit à tous les
   contrôles d'artefact (permutation, COVID, proxys, délai, β) et échoue uniquement sur la
   **multiplicité** (DSR 0.017-0.101) et sur l'**absence de cohérence inter-instruments**. C'est une
   distinction qui compte : si un angle nouveau et pré-enregistré revenait sur GER40, il faudrait
   l'attaquer sur **pourquoi Francfort et pas New York** — un mécanisme (structure d'auction, mix
   d'acteurs, heure de chevauchement US) — et non re-balayer des formes.
5. **Le gradient nul est mesuré sur des quintiles**, donc sur le top 20 % de stress. Un état
   **beaucoup plus rare** (top 1-5 %) pourrait porter un effet que ce découpage moyenne : c'est
   explicitement **UNDERPOWERED**, pas testé, et ce serait un angle de ré-ouverture légitime
   (catégorie « puissance ») — à condition d'être pré-enregistré et de ne pas rejouer les mêmes formes.
6. **Échantillons :** US500 2014-2026, US100 2015-2026, US30 et GER40 2015/2016-2026 (après burn-in de
   500 séances). Le VIX s'arrête au 2026-05-27, les indices au 2026-06-05.
7. **La couche barrière suppose la config FTMO $10k 2-step** (daily −5 %, floor statique −10 %, sans
   limite de temps). Elle ne transfère pas telle quelle à une autre géométrie.

---

## 9. Conséquence pour le registre

La famille `intraday_mr` × indices × CFD retail était fermée sur un **raisonnement invalide** (« la
moyenne inconditionnelle est négative »). Elle est maintenant fermée sur une **mesure du gradient
d'état** — ce qui est une fermeture beaucoup plus solide, et **au GROSS**, donc insensible au modèle de
coût. Selon la politique de ré-ouverture, ce kill est de nature **mécanique** (gradient nul mesuré) sur
la portée indice/intraday ⇒ **reste fermé**. Les deux portes qui restent ouvertes sont d'une autre
nature : la coupe **transverse** (jamais testée, véhicule absent) et le conditionnement **extrême**
(puissance), toutes deux hors du périmètre mesuré ici.

**Leçon candidate (nommée, non numérotée — le numéro se grave à la réconciliation) :**
`conditional-before-closing` — **une moyenne inconditionnelle négative ne ferme pas une famille dont la
thèse est conditionnelle.** Le test qui ferme est le **profil complet par quantile d'état** ; et c'est
la **monotonie** qui teste le mécanisme, pas le quantile extrême — un edge sans gradient est du bruit
sélectionné, ce que confirme ici la symétrie des queues (5 cellules à t > +2.5 contre 8 à t < −2.5,
pour ~1.1 attendue par queue). Corollaire opératoire : **la baseline L58 doit être appariée DANS
l'état**, car l'espérance inconditionnelle dérive avec l'état (mesuré : +0.15 → +0.83 bps de Q1 à Q5),
et une baseline plein-échantillon fabrique un faux PASS sur la jambe short en état de stress.
