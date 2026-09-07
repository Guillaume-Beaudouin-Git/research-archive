# Fiche d'attribution — liquidité nette : correction de mon propre verdict

**2026-09-08.** `RESULTATS.md` conclut « kill MÉCANIQUE, non rouvrable sans un mécanisme
entièrement neuf ». **C'est une sur-affirmation de ma part** : je n'ai testé qu'une instanciation.
La candidate « attribution-du-kill » exige l'énumération avant l'archive ; je ne l'avais pas faite.
Δn_tests = 0 — cette fiche n'est que de l'écriture.

## Ce qui a été testé, exactement

| axe | valeur testée |
|---|---|
| Agrégat | `WALCL/1000 − TGA − RRP`, en niveau agrégé |
| Transformation | **variation hebdomadaire** de l'agrégat |
| Règle | **signe** de la variation |
| Actif | **US100** seul |
| Horizons | 1 et 4 semaines |
| Période | 2008-2026 |
| Fréquence de décision | hebdomadaire |

## Ce qui est réellement mort, et sur quelle portée

Trois résultats sont **de niveau mécanisme**, pas de niveau variante :

1. **La régression signée est plate** (pente +0,0002 bps par milliard, t +0,80). L'ampleur du
   mouvement de liquidité ne porte aucune information sur l'ampleur du rendement. Ça condamne toute
   version **proportionnelle** de la thèse, pas seulement la version en signe.
2. **La jambe courte est massivement négative** (−72,7 bps, t −4,66). Un vrai edge directionnel est
   positif des deux côtés (L25).
3. **Le placebo à taux de base apparié n'est pas franchi** (p = 0,0621).

Ces trois-là valent pour **US100 en hebdomadaire**. Ils ne s'étendent pas automatiquement ailleurs.

## Axes NON variés — l'énumération que j'aurais dû écrire

| axe | varié ? | pourrait-il retourner le verdict ? |
|---|---|---|
| **Actif** (obligations, or, crypto, dollar) | ❌ non | **Possiblement.** Le contrôle inconditionnel qui tue ici repose sur une dérive de **+86,4 bps/semaine**. Sur un actif à dérive faible ou nulle — l'or, le dollar, une jambe long/short — le taux de base ne fabrique plus rien et le test devient réellement informatif. **C'est l'axe le plus sérieux.** |
| **Composantes séparées** (TGA seul, RRP seul) | ❌ non | Possiblement. Le drainage des prises en pension 2023-2024 est le cas le plus cité de la thèse ; l'agréger avec le bilan peut noyer un effet de composante. |
| **Transformation** (accélération, écart à une tendance, niveau normalisé) | ❌ non | Peu probable — la régression signée plate porte déjà sur l'ampleur. |
| **Horizon** (au-delà de 4 semaines) | ❌ non | Peu probable, et coûteux en chevauchement. |
| **Long/short contre un panier** | ❌ non | **Possiblement** — c'est la forme qui neutralise la dérive, donc qui échappe au mécanisme de kill identifié. |
| Période | ✅ 3 sous-périodes | Non |
| Règle de signe vs continue | ✅ les deux | Non |

## Reclassement

| | avant | après |
|---|---|---|
| Nature | mécanique, non rouvrable | **PARTIEL** — deux axes plausibles non variés |
| Portée du kill | « la liquidité nette » | **« la liquidité nette agrégée, en signe hebdomadaire, sur un actif actions à forte dérive »** |

**Ce qui reste solidement établi et transférable** : le mécanisme de faux positif. Sur tout actif à
dérive, une règle de signe rapporte `(2p−1)×μ` sans aucune relation. Ça ne dépend pas de la
liquidité nette — c'est un contrôle à appliquer partout.

**Angle de ré-ouverture, s'il devait être pris** : tester l'agrégat, puis les composantes séparées,
sur un actif à **dérive faible** (or, dollar) ou en **long/short** — configuration où la baseline
mécanique s'annule. Coût : 2 à 4 essais. Priorité **basse** : le prior reste défavorable et rien
dans ce qui a été mesuré ne suggère un effet caché.

## Ce que cette fiche m'apprend sur ma propre pratique

J'ai écrit « non rouvrable » dans le même document où je démontrais que le kill venait d'une
propriété de **l'actif choisi** (sa dérive), pas du prédicteur. C'est précisément l'erreur
d'attribution que la règle vise. La règle ne sert pas si on ne l'applique qu'aux verdicts des autres.
