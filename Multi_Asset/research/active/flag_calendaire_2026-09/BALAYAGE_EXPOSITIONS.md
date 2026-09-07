# Balayage systématique — d'autres défauts d'exposition dans le book déployé ?

**2026-09-08.** Motivation : le seul axe survivant de tout le programme macro est celui qui
**retire une exposition non voulue** (le flag FOMC). Hypothèse de travail : il en existe peut-être
d'autres du même type. Δn_tests = 51 (balayage, compteur programme séparé).

⚠ **C'est un BALAYAGE, pas une hypothèse pré-enregistrée.** Tout résultat serait un candidat à
confirmer indépendamment, jamais un verdict.

## Protocole

17 cellules calendaires × 3 sleeves = **51 tests**. Seuil Šidák à 5 % : **|t| ≥ 3,29**.

Cellules : les 5 jours de semaine ; trois tranches de jour du mois ; le 3ᵉ vendredi (échéances
d'options) ; la fin de trimestre ; six types de publications américaines (CPI, emploi, PIB, PMI
services, confiance du consommateur, prix à la production) ; et le FOMC en **témoin connu**.

## Résultat

**Deux cellules sur 51 dépassent |t| = 2,0. Aucune ne franchit le seuil de Šidák.**

| sleeve | cellule | n | écart | t_HAC | Šidák |
|---|---|---|---|---|---|
| ORB US100 | **FOMC** *(témoin)* | 67 | −10,37 bps | −3,00 | sous seuil |
| ORB US100 | vendredi | 415 | +4,92 | +2,84 | sous seuil |

30 cellules sur 32 testées sont sous |t| = 2,0. La cellule vendredi est **positive**, donc ce n'est
pas un défaut. **Aucun autre défaut d'exposition n'est détectable à cette granularité.**

## Le résultat méthodologique, qui vaut plus que le résultat empirique

**L'effet FOMC — pourtant réel, validé par placebo apparié à p = 0,0011 — NE PASSERAIT PAS ce
balayage.** Son t de −3,00 est sous le seuil de Šidák de 3,29 imposé par 51 tests.

Même donnée, même effet, même ampleur. Deux chemins de découverte, deux verdicts opposés :

- **par balayage** : 51 tests ⇒ seuil 3,29 ⇒ **rejeté** ;
- **par hypothèse** : l'axe « le macro prédit le risque » du round 2 désignait CPI, emploi et FOMC
  avant de regarder les données ⇒ 4 tests ⇒ seuil **2,49** ⇒ **retenu**, puis confirmé par un
  placebo apparié et un contrôle de confondant.

⇒ **Le pré-enregistrement n'est pas une formalité administrative : il change le seuil de preuve d'un
facteur qui décide.** Un mécanisme économique posé à l'avance achète de la puissance statistique. Un
balayage la dépense.

Corollaire opératoire : quand un effet est trouvé par balayage, il faut le **re-tester sur des
données indépendantes** — le seuil corrigé est presque toujours hors d'atteinte autrement.

## Conclusion

La veine « audit d'expositions non voulues » est **épuisée à cette granularité**. Le book déployé
n'a pas d'autre défaut calendaire détectable que celui déjà traité.

Ce qui resterait à explorer si on y revenait un jour : une granularité **intra-journalière**
(certaines heures plutôt que certains jours), et les événements **non américains** — le book porte
du GER40, et le calendrier BCE n'a pas été balayé. Aucun des deux n'est prioritaire.
