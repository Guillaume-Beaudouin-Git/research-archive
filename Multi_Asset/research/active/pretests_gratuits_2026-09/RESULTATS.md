# Deux pré-tests gratuits — la prémisse du nowcast survit sur l'inflation seule, et le choix de contrat IBKR s'inverse

**2026-09-08.** Δn_tests = 0 pour le test 2 (calcul de construction) ; test 1 = 3 essais
(DM, CG, stabilité OOS). Programme macro : 18 → 21.

---

# TEST 1 — le consensus est-il battable ?

Données : `economic_calendar_2018_2026_full.csv`, 86 indicateurs américains avec réalisé,
prévision **et** précédent, ≥ 40 observations chacun.

## A. Le consensus a une vraie compétence

Diebold-Mariano contre un modèle naïf « prévision = valeur précédente », HAC lag-6 :

| | |
|---|---|
| consensus significativement meilleur | **51 / 86** |
| naïf meilleur | **0 / 86** |
| indistinguable | 35 / 86 |

**Le naïf ne bat le consensus sur aucun indicateur.** Construire un nowcast qui batte le consensus
*en niveau* est donc un objectif difficile — ce qui condamne l'approche « modèle à facteurs
dynamiques » décrite au round 1 comme point d'entrée.

## B. Mais son ERREUR est prédictible — c'est une cible bien plus facile

Coibion-Gorodnichenko : régression de l'erreur sur l'erreur précédente. Un coefficient positif
signifie que le consensus **sous-réagit** systématiquement.

**15 indicateurs sur 86 montrent une sous-réaction significative**, dont les plus suivis du marché.
Seuil Šidák pour 86 tests : |t| ≥ 3,43.

⇒ **Reformulation décisive de l'axe** : il n'est **pas nécessaire de construire un nowcast**. Il
suffit d'exploiter l'autocorrélation de l'erreur, qui est **publique et gratuite**. Cela supprime
toute l'infrastructure de nowcasting du plan initial.

## C. Trois contrôles, et ils font le tri

**Contrôle d'artefact** — la prévision est-elle simplement paresseuse ?
`Unemployment Rate` : **54,5 % des prévisions égalent exactement la valeur précédente** ⇒ **écarté**.
Les autres passent (0-18 % de reprise).

**Contrôle d'informativité** — la prévision domine partout le précédent (coefficients ~1, t de 12 à
118). Le consensus porte bien de l'information.

**Contrôle hors échantillon** — estimation sur la première moitié, test sur la seconde. **C'est lui
qui décide** :

| indicateur | coef IS | coef OOS | t OOS | verdict |
|---|---|---|---|---|
| **Inflation Rate (CPI)** | +0,364 | **+0,322** | **+2,91** | ✅ **stable** |
| **Inflation Rate MoM** | +0,284 | **+0,223** | **+2,56** | ✅ **stable** |
| Case Shiller YoY | +0,670 | +0,556 | +4,71 | ✅ stable (mais peu tradable) |
| Initial Jobless Claims | +0,672 | +0,085 | +1,47 | ⚠ coefficient divisé par 8 |
| **Non Farm Payrolls** | +0,271 | **−0,094** | −1,33 | ❌ **signe inversé** |
| Unemployment Rate | +0,297 | −0,121 | −1,23 | ❌ signe inversé (+ artefact) |
| Manufacturing Payrolls | +0,409 | **−0,243** | −2,45 | ❌ signe inversé, et significatif |

**Quatre candidats sur sept tombent, dont la tête d'affiche.** Le NFP — la publication la plus
suivie — inverse son signe hors échantillon. C'est exactement le test que B3 avait échoué, appliqué
en amont cette fois.

## Verdict test 1

**La prémisse survit, mais sur l'inflation seulement.** CPI et sa variante mensuelle sont les deux
seuls candidats à la fois stables hors échantillon, non artefactuels et économiquement suivis.

**Breadth : 12 paris par an.** Petite, mais honnête et non gonflée.

⚠ **Ce qui n'est PAS démontré** : que prédire le signe de la surprise se traduise en P&L. La chaîne
a encore une étape non franchie, et deux résultats du dossier invitent à la prudence — l'EIA a
montré une dose monotone dans le **mauvais** sens, et Kroner (2025) documente que la fonction de
réaction du prix est pilotée par l'attention et **instable dans le temps**.

---

# TEST 2 — quel contrat IBKR ? Le coefficient de transfert inverse la réponse

Coefficient de transfert = corrélation entre la position **idéale** (vol-ciblée, continue) et la
position **réellement tenable** en lots entiers. Capital 13 000 €, vol 20 jours sur proxy 10 ans.

| cible de vol | contrat | position idéale médiane | **TC** | % du temps à 0 lot |
|---|---|---|---|---|
| **10 %/an** | ZN (10 ans) | 0,20 lot | — | **100 %** |
| | ZF (5 ans) | 0,38 | +0,766 | 80 % |
| | **micro 10Y yield** | **15,25** | **+0,999** | **0 %** |
| **15 %/an** | ZN | 0,30 | +0,573 | 93,9 % |
| | **micro** | **22,82** | **+0,999** | **0 %** |
| **20 %/an** | ZN | 0,40 | +0,783 | 75,8 % |
| | **micro** | **29,61** | **+0,999** | **0 %** |

**À 13 000 €, ZN arrondit à zéro entre 76 et 100 % du temps.** Il est inutilisable pour toute
stratégie vol-ciblée. Le micro-contrat donne un TC de **0,999** et atteint la cible exactement.

## Ce que ça corrige, et ce que ça ne corrige pas

Le plan du book perso recommandait **ZN** et écartait le micro-contrat au motif que son DV01 de
10 $/point de base était « trop petit à 13 k€ ». **Ce jugement portait sur la taille d'effet de la
sleeve month-end, pas sur le coefficient de transfert** — et les deux ne se recouvrent pas.

**La règle de décision qui en sort, et elle est nette :**

| type de stratégie | contrat | pourquoi |
|---|---|---|
| **lot fixe, intermittente** (month-end : 12 événements/an, exposée 14 % du temps) | **ZN** | pas de vol-targeting à transférer, et le coût fixe est dilué sur 115 k$ de notionnel |
| **vol-ciblée, exposition continue** | **micro** | seul TC utilisable ; ZN arrondit à zéro |

⚠ **Le micro a le TC parfait mais le mauvais coût** — L57 mesure 2,3-2,8 bps rien qu'en commission
fixe sur 6-7 k$ de notionnel, contre 0,66 bps sur les 40 k$ du MGC. **Aucun contrat ne domine
l'autre** : le choix dépend entièrement de si la stratégie a besoin de vol-targeting.

⚠ **Spécifications approximatives** (notionnel, multiplicateurs de DV01). L'ordre de grandeur — ZN
arrondit à zéro à 13 k€ — est robuste, mais les valeurs exactes sont à vérifier sur les specs IBKR
réelles à l'ouverture du compte.
