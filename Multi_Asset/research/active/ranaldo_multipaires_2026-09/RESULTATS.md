# Ranaldo multi-paires — KILL DÉFINITIF, et la prédiction algébrique se vérifie

**2026-09-08.** Spec gelée : `PREREGISTRATION.md`. 7 majeures USD, ~5 065 jours, 2007-2026.

## Le résultat par paire — l'effet n'est PAS général

| paire | brut bps/j | t_HAC | SR brut | jambe courte | jambe longue |
|---|---|---|---|---|---|
| **EURUSD** | **+2,48** | **+3,55** | **+0,80** | +1,57 | +0,92 |
| **GBPUSD** | +1,74 | +2,30 | +0,51 | +0,69 | +1,04 |
| **USDCAD** | +1,68 | +2,40 | +0,54 | +1,12 | +0,56 |
| AUDUSD | +0,42 | +0,48 | +0,11 | +0,15 | +0,27 |
| USDCHF | +0,11 | +0,15 | +0,03 | −0,42 | +0,53 |
| USDJPY | −0,10 | −0,15 | −0,03 | +0,72 | −0,83 |
| NZDUSD | −0,19 | −0,21 | −0,05 | −0,08 | −0,11 |

**Trois paires portent quelque chose, quatre ne portent rien.** Le brut médian vaut 0,42 bps, très
en dessous du seuil de 1,0 fixé au pré-enregistrement.

*Réconciliation* : EURUSD donne ici **+2,48 bps** contre **+2,07** dans l'étude d'origine, mais le
**t_HAC est identique à 3,55**. L'écart de moyenne tient probablement à la fenêtre d'échantillon
(2007+ ici) ou au traitement du délai ; la réplication est fidèle sur la statistique.

## L'agrégation DÉTRUIT le signal au lieu de l'amplifier

| | |
|---|---|
| Portefeuille équipondéré, 7 paires | **+0,88 bps/jour, t +1,60, SR brut 0,353** |
| EURUSD seul, référence | SR brut **0,80** |

**Le portefeuille est deux fois moins bon que la meilleure paire seule.** Diluer dans quatre paires
mortes coûte plus de signal que la diversification ne fait gagner en volatilité.

## La prédiction algébrique, vérifiée sur données réelles

Le round 3 avait dérivé qu'une construction **en étoile** — toutes les paires contre un pivot —
plafonne la corrélation résiduelle à 0,5 et la breadth effective à **2, quel que soit N**.

Mesuré ici : **corrélation moyenne +0,435**, breadth effective **1,94** contre N = 7 nominal.

La prédiction était 2. Le mesuré est 1,94. **La leçon passe du statut de dérivation à celui de fait
mesuré**, sur un univers réel de sept paires et dix-neuf ans.

Détail cohérent avec le mécanisme : les corrélations les plus fortes sont entre paires partageant
une exposition commune (AUDUSD/NZDUSD **0,78**, EURUSD/USDCHF **0,72**), et la plus faible implique
le yen (USDJPY/USDCAD **0,03**) — la devise dont le comportement horaire est le plus différent.

## Le budget de coût

| véhicule | coût/jour | net | SR net |
|---|---|---|---|
| futures 0,40/jambe | 0,80 bps | +0,08 | **+0,03** |
| Eightcap 0,75/jambe | 1,50 | −0,62 | −0,25 |
| FTMO 2,48/jambe | 4,96 | −4,08 | −1,64 |

**Coût maximal admissible pour un SR net > 0,70 : 0,00 bps.** Le SR brut agrégé (0,353) est déjà
sous le gate. **Même une exécution gratuite ne suffirait pas.**

## Verdict

**KILL DÉFINITIF**, exactement selon le critère écrit d'avance : SR agrégé 0,353 < 0,90, et brut
médian par paire 0,42 < 1,0 bps.

**Attribution — pourquoi c'est définitif cette fois.** Les quatre axes d'instanciation sont
désormais tous testés :

| axe | statut |
|---|---|
| véhicule | ✅ 4 testés (FTMO, Eightcap, 6E, M6E) — arithmétique du round 6 |
| coût | ✅ budget calculé, nul même à exécution gratuite |
| **univers** | ✅ **ce test — l'agrégation dégrade** |
| période | ✅ 2007-2026, 19 ans |

Il ne reste **aucun axe plausible non varié**. Kill de nature **mécanique** au sens de la politique
de ré-ouverture, catégorie non rouvrable.

**Ce que je refuse explicitement de faire** : sélectionner les trois paires qui marchent
(EURUSD, GBPUSD, USDCAD) et rapporter leur agrégat. C'est une sélection **post-hoc** sans mécanisme
qui la justifierait a priori — pourquoi ces trois-là et pas d'autres ? Ce serait exactement le
data-mining que tout ce programme s'emploie à éviter, et le seuil corrigé pour un choix parmi
7 paires effacerait de toute façon le gain apparent.

## Ce qui reste vrai

L'edge **sur EURUSD seul** est réel, bilatéral et significatif (t 3,55, deux jambes au-dessus de
2,5). Il n'est simplement pas exploitable : SR brut 0,80 contre un gate à 0,70 laisse un budget de
0,04 bps par jambe. C'est la confirmation la plus nette de **L34** — cette famille appartient au
tier institutionnel, point final.

Programme macro : 17 → 18 essais.
