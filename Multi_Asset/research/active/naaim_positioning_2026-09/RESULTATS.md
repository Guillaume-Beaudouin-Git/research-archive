# NAAIM — le résidu orthogonalisé ne porte rien. Kill, et portée précisée.

**2026-09-08.** Spec gelée : `PREREGISTRATION.md`. 904 semaines, 2008-12 → 2026-04.
Source : `data/raw/http_naaim_exposure_xlsx_ffd686b1.parquet` (1 039 obs depuis 2006, provenance
tracée dans `data/metadata/`).

## Le résultat

Signal = `−signe(résidu)`, où le résidu est le z-score NAAIM orthogonalisé au momentum 4/12/26
semaines. Comparaison **contre la baseline de taux de base**, jamais contre zéro.

| horizon | brut | baseline `(2p−1)μ` | **excédent** | t_HAC |
|---|---|---|---|---|
| 1 semaine | −2,9 bps | −0,3 | **−2,6** | −0,34 |
| 4 semaines | +4,2 | −1,3 | **+5,5** | +0,26 |

**Critère de KILL atteint** : l'excédent est indistinguable de zéro aux deux horizons.

Détail utile : après orthogonalisation, le taux de base tombe à **49,4 %** (contre 41,3 % sur le
signal brut). L'asymétrie du signal brut venait donc bien du momentum — l'orthogonalisation la
supprime, ce qui valide au passage la construction.

## Les deux jambes (L25) — deuxième kill, indépendant

| jambe | n | contribution | t |
|---|---|---|---|
| achat (positionnement bas) | 447 | **+25,8 bps** | +2,17 |
| vente (positionnement haut) | 457 | **−30,9 bps** | **−3,69** |

La jambe vendeuse est massivement négative. Le signal ne survit que du côté acheteur — signature de
bêta, pas d'edge directionnel.

## Stabilité et puissance

Excédent par sous-période : −2,8 / −18,4 / −0,3 bps, aucun t au-dessus de 0,51 en valeur absolue.
Aucun signe de vie nulle part.

Et l'autocorrélation du résidu vaut **0,742** ⇒ `N_eff ≈ 134` contre 904 nominal. L'échantillon
effectif est **6,7 fois plus petit** qu'il n'en a l'air.

## Ce que le pré-test L37 a révélé — une faiblesse de la leçon

Le gate L37 dit : *si `sign(filtre) ≠ signal natif` moins de 5 % du temps, le filtre est cosmétique*.
Ici le désaccord vaut **69,8 %** — gate franchi haut la main.

**Mais c'était trompeur.** La corrélation des signaux **continus** vaut **+0,526** (z-score contre
momentum 12 s) et **+0,577** en niveau : l'exposition NAAIM **suit** le momentum, les gérants étant
plus exposés après une hausse. Le fort désaccord n'était qu'une **conséquence mécanique** d'avoir
retourné le signe — pas une preuve d'indépendance.

⇒ **Amendement proposé à L37** : le test du taux de désaccord est **insuffisant seul**. Il doit être
accompagné de la **corrélation des signaux continus** avec le signal natif. Un désaccord élevé
obtenu en inversant le signe d'un proxy de momentum n'est pas de l'information propre — c'est de
l'anti-momentum déguisé. *(Candidate « L37-bis ».)*

## Attribution du kill — l'énumération, écrite avant d'archiver

**Ce qui meurt** : le **résidu du NAAIM orthogonalisé au momentum, en signe, sur US100, aux horizons
1 et 4 semaines**. Pas « les enquêtes de positionnement ».

| axe | varié ? | pourrait-il retourner le verdict ? |
|---|---|---|
| **Extrêmes seulement** (queues du z-score) | ❌ non | **OUI — l'axe le plus sérieux.** La littérature de sentiment revendique généralement un effet **aux extrêmes**, pas sur toute l'étendue. Tester la plage complète dilue mécaniquement. |
| **Enquête** (AAII = particuliers, BofA FMS = institutionnels) | ❌ non | **Possiblement** — population différente. NAAIM mesure des gérants actifs ; le sentiment des particuliers est un objet distinct, pas une variante. Bloqué sur l'accès aux données (AAII en 403, NAAIM complet sur abonnement). |
| Transformation (niveau, variation, percentile) | ❌ non | Peu probable — le résidu est déjà nul en moyenne. |
| Actif | ❌ non | Peu probable ici : l'orthogonalisation a équilibré le taux de base, donc le piège de dérive ne s'applique plus. |
| Horizon au-delà de 4 semaines | ❌ non | Peu probable, et coûteux en chevauchement à `N_eff` = 134. |
| Momentum aligné plutôt que contrarien | ❌ non | Sans objet — ce serait tester du momentum. |

**Classification : kill PARTIEL**, catégorie **puissance/géométrie**, rouvrable **une fois** sur
l'axe des extrêmes. Coût estimé : 2 essais. Priorité **moyenne** — c'est le seul axe où la
littérature prédit spécifiquement un effet, et il n'a jamais été regardé ici.

Programme macro : 15 → 17 essais.
