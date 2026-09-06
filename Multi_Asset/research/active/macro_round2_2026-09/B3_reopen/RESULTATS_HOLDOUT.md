# B3 — résultats sur holdout 1990-2003 : KILL MÉCANIQUE DÉFINITIF

**2026-09-07.** Spec gelée : `PREREGISTRATION_HOLDOUT.md` (commit `b0848b31`), écrite avant tout
contact avec les résultats. Moteur `code/engine_holdout.py`. Mesure : drift signé du rendement 10 ans
en bps, `signe(choc) × Δ DGS10`, positif = continuation.

---

## Le tableau

| échantillon | H | n | drift (bps) | t_HAC | MDE80 | **effet/MDE** | contrôle non-tradés |
|---|---|---|---|---|---|---|---|
| **HOLDOUT 1990-2003** *(test primaire)* | 5 | 50 | **−3,54** | −1,55 | 5,80 | **−0,61** | −0,63 (t −1,05) |
| | 10 | 50 | **−3,08** | −0,76 | 8,63 | −0,36 | −0,82 (t −0,99) |
| | 20 | 50 | **−3,22** | −0,77 | 12,07 | −0,27 | −1,77 (t −1,45) |
| vu 2004-2024 *(contaminé)* | 5 | 63 | +3,57 | +2,18 | 4,61 | +0,77 | **+2,10 (t +3,01)** |
| | 10 | 63 | +4,57 | +2,02 | 6,52 | +0,70 | **+2,11 (t +2,14)** |
| | 20 | 63 | +7,17 | +2,67 | 9,79 | +0,73 | **+2,44 (t +2,51)** |
| poolé 1990-2024 | 5 | 113 | +0,08 | +0,05 | 3,68 | +0,02 | +1,10 (t +1,99) |
| | 10 | 113 | +0,65 | +0,29 | 5,27 | +0,12 | +1,13 (t +1,53) |
| | 20 | 113 | +2,22 | +0,85 | 7,66 | +0,29 | +0,79 (t +0,84) |

## Trois critères pré-enregistrés, trois échecs

**1. Le critère de MORT est atteint sur le holdout.** |t_HAC| < 2,0 aux trois horizons (1,55 / 0,76 /
0,77) **et** effet sous son MDE80 aux trois horizons. C'est exactement la condition écrite d'avance.

**2. Le test de cohérence de signe échoue.** Le pré-enregistrement disait : *« un signe qui s'inverse
entre les deux moitiés est un échec, quel que soit le t »*. Il s'inverse : **−3,54 bps sur
1990-2003 contre +3,57 bps sur 2004-2024** à H=5, et de même aux deux autres horizons.

**3. Le contrôle L58 invalide le résultat 2004-2024 que j'avais trouvé.** Sur cette fenêtre, les
événements **NON tradés** — ceux dont le choc est sous le seuil — portent un drift de **+2,10 bps
avec t = +3,01**, soit un t **plus élevé** que celui des événements tradés. Le pré-enregistrement
disait : *« si les non-tradés portent eux-mêmes un drift, le seuil sélectionne une période et non une
dose — et le résultat est invalidé »*. L'effet n'est **pas dose-dépendant** : il est présent dans
toute la période, indépendamment de la taille du choc. Ce n'est donc pas une réaction au choc, c'est
une propriété de la fenêtre 2004-2024.

Et le poolé sur 34 ans est **nul** : +0,08 / +0,65 / +2,22 bps, t de 0,05 à 0,85.

## Verdict

**KILL MÉCANIQUE ET DÉFINITIF.** L'axe B3 est fermé, sans ré-ouverture possible.

La chaîne est complète et chaque maillon a été fermé par un test écrit d'avance :
- axe **mélange** → réfuté par la composition des chocs (la composante information n'a pas de masse) ;
- axe **mesure de surprise** → le gain apparent sur 2004-2024 est invalidé par son propre contrôle de
  dose, et ne survit pas au holdout ;
- axe **véhicule** → l'instrument n'était pas le facteur limitant : sur 34 ans de rendements, le
  drift est nul et son signe s'inverse entre les moitiés.

Il ne reste aucun axe d'instanciation plausible. Par la politique de ré-ouverture, c'est un kill de
nature **mécanique**, catégorie non rouvrable.

## Ce que ça dit de l'étude d'origine

**Le NO-GO du 2026-06-10 était juste**, et il l'était plus solidement qu'il ne le pensait. Son
proxy journalier atténuait effectivement le signal — c'est vrai, je l'ai mesuré. Mais corriger
l'atténuation ne révèle rien : ce qui apparaissait sur 2004-2024 est un effet de période et non de
dose, et il disparaît sur l'échantillon long.

## Ce que ça dit de ma propre séquence

J'ai produit un résultat intermédiaire encourageant (+21 à +46 bps de brut, t jusqu'à 2,32) et je
l'avais correctement signalé comme **sous-puissant** (ratio effet/MDE 0,63-0,65). Ce signalement
était le bon réflexe : **le ratio effet/MDE a vu ce que le t-stat ne voyait pas.** Un t de 2,32
lu seul aurait pu justifier un déploiement.

Mais ce sont le **holdout** et le **contrôle de dose** qui ont tranché, et ni l'un ni l'autre n'était
disponible dans l'étude d'origine. Ils ne coûtaient rien : le holdout existait depuis 1990, le
contrôle est une ligne de code.

## Coût total

**5 essais** sur le programme macro (3 + 2). Global figé. Une famille fermée définitivement, avec sa
raison mécanique nommée — au lieu d'un NO-GO ambigu qui aurait pu être rouvert indéfiniment.

## Leçon candidate

**Candidate « contrôle de dose »** — Dans toute étude à seuil, mesurer l'effet sur les observations
**SOUS le seuil** et exiger qu'il soit proche de zéro. Si les non-sélectionnés portent le même effet,
le seuil sélectionne une **période**, pas une **dose**, et le résultat ne teste pas le mécanisme
revendiqué. Mesuré ici : sur 2004-2024, les événements non tradés rendent **+2,10 bps à t = +3,01**,
soit un t **supérieur** à celui des tradés (+3,57 bps, t +2,18) — le « signal » n'avait aucune
relation à la taille du choc. Coût du contrôle : une ligne. Il a invalidé un résultat que le t-stat
et le walk-forward auraient laissé passer. Parent de L58 (placebo apparié), mais distinct : L58
valide la BASELINE du placebo, celle-ci valide la MONOTONIE en la variable de sélection.
