# Pré-enregistrement — `mr_stress_conditional`

**Écrit AVANT de toucher la donnée.** Horodatage : 2026-08-02, worktree `claude/mr-stress-conditional`,
base `origin/main` @ `2f728b3e`. Interpréteur `/usr/bin/python3` (pandas 2.2.3 / numpy 2.0.2 vérifiés).

## 1. Mécanisme testé

Nagel (2012), *Evaporating Liquidity* : le rendement du reversal court terme **n'est pas une
anomalie de prévisibilité**, c'est la **rémunération d'un service de fourniture de liquidité**.
Sa prédiction centrale est **conditionnelle** : le rendement attendu du reversal **croît avec le
stress** (VIX, vol réalisée, illiquidité), parce que c'est en état de stress que les fournisseurs
de liquidité se retirent et que le prix du service monte.

**Ce que ce repo a mesuré jusqu'ici :** la version **INCONDITIONNELLE** (384 cellules,
`mr_timezone_repair_2026-08`, two-sided gross moyen −1.78 bps, 0 cellule à t > 2.5), et il en a
conclu « famille fermée par mécanisme ». **C'est une erreur de raisonnement** : une moyenne
inconditionnelle négative est compatible avec un edge conditionnel fort si l'état porteur est rare.
Les 60 cellules « regime-conditional » de l'étude d'origine n'ont **aucun code dans le repo**.

**L'élément AJOUTÉ ici, et le seul :** le **conditionnement d'état**. Les formes de trade ne sont
pas re-balayées pour elles-mêmes ; elles sont reprises **telles quelles** de la grille déjà
archivée, précisément pour que la seule différence entre les deux études soit l'état.

## 2. Proxys d'état — déclarés AVANT mesure, non modifiables après

Tous calculables à **T-1**, constants à l'intérieur de la séance T (aucun conditionnement
intra-journalier ⇒ aucune fuite intra-séance possible).

| | proxy | définition | source |
|---|---|---|---|
| **P1** | **VIX** | clôture VIX de la séance T-1 | `data/panels/vix.csv` (série propre déjà dans le repo, 2007-01-03 → 2026-05-27, 4 881 lignes, 0 NaN sur `^VIX`) — **la variable de Nagel elle-même** |
| **P2** | **vol réalisée** | écart-type des rendements log clôture-à-clôture de l'instrument sur les 20 séances finissant en T-1 | série instrument |
| **P3** | **dispersion intra-journalière** | moyenne des \|rendements 5 min\| à l'intérieur de la séance T-1 | série instrument |

**Bucketisation strictement causale :** la valeur d'état de la séance T est convertie en
**percentile expanding** — son rang parmi toutes les valeurs antérieures **du même statistique
jusqu'à T-1 incluse**, avec **≥ 500 observations antérieures** requises (sinon la séance est
écartée). Les frontières de quintile ne contiennent donc **aucune** information future. Un
découpage en quintiles plein-échantillon est rapporté **en robustesse seulement**.

Quintiles notés **Q1 (calme) → Q5 (stress)**.

## 3. Forme de trade primaire — déclarée AVANT mesure

La forme la plus proche du service de liquidité de Nagel dans la grille déjà archivée :

- barres **5 min**, ancrées à l'ouverture de séance, **horloge d'échange avec son DST propre** (L56) ;
- déviation `sma20_z` = (px − SMA20) / sd20, calculée **intra-séance** ;
- seuil **θ = 2.5** ;
- **jambes DISJOINTES (L25)** : `z < −2.5` → **LONG** (on fournit de la liquidité aux vendeurs),
  `z > +2.5` → **SHORT**. Aucune jambe n'est jamais obtenue par négation de l'autre ;
- **delay+1 sur l'ENTRÉE ET LA SORTIE (L59)** : entrée à l'**OPEN** de la barre j+1, sortie à
  l'**OPEN** de la barre k+1, avec k = j + 6 (time-stop 30 min). **Aucun stop, aucun bracket,
  aucun remplissage à une barrière** ⇒ le mode de défaillance L59 est structurellement absent ;
- trades **non chevauchants**.

**Instruments primaires :** US500, US100, US30, GER40 (indices FTMO, `data/deep_history_utc/`,
vrai UTC vérifié). `data/panels/m5_indices/` n'est **jamais** lu (EET mal étiqueté).

**Cellules primaires : 4 instruments × 3 proxys = 12.** Chacune produit un profil à 5 quintiles.

## 4. Test du MÉCANISME — la monotonie, pas le quantile extrême

Un edge qui n'apparaît que dans un quintile isolé, **sans gradient**, est du bruit sélectionné.
Le test principal est donc le **gradient**, mesuré de deux façons :

- **pente continue** : OLS du rendement de trade (bps, two-sided, jambes disjointes) sur le
  **percentile d'état** de sa séance (∈ [0,1]), **t HAC(6)** sur la pente ;
- **Q5 − Q1** : différence de moyennes, **bootstrap par blocs** (Politis-Romano, blocs de 5
  trades, 2 000 tirages) — **jamais iid** ;
- **ρ de Spearman** entre l'indice de quintile (1..5) et la moyenne two-sided du quintile.

Le **profil complet des 5 quintiles est le résultat principal, PASS ou non.**

## 5. Contrôles obligatoires, tous pré-déclarés

- **L25** — jambes disjointes, chaque jambe rapportée séparément par quintile.
- **L58, dans sa version qui mord ici** — la baseline inconditionnelle est calculée
  **À L'INTÉRIEUR DU MÊME ÉTAT** : espérance inconditionnelle de la même forme de trade (long, même
  durée de tenue) sur **les barres des séances du même quintile**. Une baseline plein-échantillon
  fabriquerait un faux PASS, puisque les états de stress ont une moyenne inconditionnelle
  différente. C'est le piège explicitement identifié pour ce dossier.
- **L60** — part de barres à fourchette nulle (`high == low`), par série et par année, **avant**
  tout usage.
- **L56** — corrélation du profil horaire hiver~été en horloge d'échange contre UTC.
- **L38** — β-orthogonalité : régression des rendements quotidiens de la sleeve sur un
  buy-and-hold vol-targeté du sous-jacent ; **R² > 30 % ⇒ pas une sleeve neuve**. Appliqué
  **seulement si** quelque chose passe le gross.
- **Gate au GROSS d'abord, `cost_rt = 0`.** Coût seulement en aval : indices **1.8 bps RT**
  (`cost_denominator_2026-07/COST_AUDIT.md`). La colonne `spread` n'est **jamais** utilisée comme
  coût (US30 79.7/100/74.9 % de barres nulles en 2019/2020/2021).
- **DSR** via `dsr.py` racine (`framework.py:131` et `ftmo_lab.py:232` sont cassés : σ_SR_trials absent).

## 6. Kill rule — écrite AVANT de voir les résultats

**PASS** exige **TOUT** ce qui suit, au gross (`cost_rt = 0`) :
1. pente continue **positive** avec **t HAC(6) > 2.5** ;
2. **Q5** two-sided > 0 avec **les deux jambes > 0** (L25) ;
3. **Q5** : les deux jambes battent leur baseline **appariée en état** (L58) ;
4. significativité survivant **Šidák** sur 12 cellules primaires ⇒ **p < 1 − 0.95^(1/12) = 4.27 × 10⁻³** ;
5. gradient **cohérent en signe** sur une majorité d'instruments (le mécanisme est universel ou il
   n'est pas).

**REJECTED** si le profil de quantiles est **plat ou décroissant** (pente non positive, ou Q5 ≤ 0,
ou Q5 sous sa baseline appariée) — et ceci **est un résultat**, pas un échec : ce serait la
fermeture de la thèse de Nagel au tier retail, ce que la mesure inconditionnelle ne pouvait pas faire.

**UNDERPOWERED** (ne consomme pas le budget) : gradient du bon signe mais IC contenant zéro, ou
n < 30 trades par jambe et par quintile.

**Suite conditionnelle :** le balayage de taille + p(pass)/durée sous barrières FTMO
(`Portfolio/admission/barrier.py`, importé sans modification) n'est exécuté **QUE SI** le gross
conditionnel passe. Un balayage de taille n'est pas une modification de stratégie.

## 7. Comptabilité

Famille **neuve** (`mr_stress_conditional` × `deep_history_utc` × univers FTMO) ⇒ compteur **N1
local**, ouvert à 0. Primaire = **12 cellules**. Le balayage de robustesse (toutes les formes de la
grille archivée × P2) est rapporté comme **distribution de gradients** — c'est un test de mécanisme
agrégé, et le nombre exact de couples forme×instrument est rapporté.
