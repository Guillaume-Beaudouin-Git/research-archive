# Flag calendaire — étape 0 franchie, et le résultat change la nature de l'axe

**2026-09-08.** Protocole : `macro_round2_2026-09/A_risque/RAPPORT.md` §6, étape 0 (filtre gratuit
L54, à passer avant toute simulation de barrière). Book : série quotidienne du **book funded
réellement déployé** (`funded_1y_mono_2026-08/attribution/daily_raw.csv`), 2 188 jours,
2018-01 → 2026-06. Calendrier : `deep_history_utc/calendar/` + les 68 dates FOMC vérifiées.

## Le filtre L54

Le gate disait : si les jours flaggés ont une moyenne **positive** et significative, arrêt — couper
retrancherait les jours qui paient, exactement la faille de L54.

| flag | n | moyenne flag | moyenne hors | écart | t_HAC | ratio de vol |
|---|---|---|---|---|---|---|
| CPI | 100 | +3,74 bps | +2,77 | +0,97 | +0,29 | 0,83 |
| NFP | 102 | +3,93 | +2,76 | +1,17 | +0,44 | 0,67 |
| **FOMC** | **67** | **−7,80** | **+3,15** | **−10,95** | **−3,12** | 0,73 |
| union | 266 | +1,00 | +3,06 | −2,06 | −1,00 | 0,75 |

**CPI et NFP : rien.** Écarts sous 1,2 bps, t sous 0,5. Ces deux flags ne servent à rien sur ce book.

**FOMC : l'écart est NÉGATIF et significatif.** Le gate est franchi dans le bon sens — couper ne
retranche pas des jours profitables, il retranche des jours qui **perdent**.

⚠ Et une surprise qui invalide la prémisse de l'axe : **le flag ne prédit PAS une vol plus haute.**
Le ratio de volatilité vaut 0,67-0,83 partout, donc les jours d'événement sont **moins** volatils
pour ce book. Tout l'argument de convexité sous barrière qui avait motivé l'axe est sans objet ici.
Ce qui reste tient debout pour une raison entièrement différente : la moyenne.

## D'où vient l'effet : ce n'est pas de la macro, c'est un défaut d'exposition

| sleeve | n jours FOMC | moyenne FOMC | moyenne hors | écart | t_HAC |
|---|---|---|---|---|---|
| **ORB US100** | **67** | **−8,47 bps** | **+1,91** | **−10,37** | **−3,00** |
| overnight US100 | 1 | — | — | — | — |
| overnight GER40 | 0 | — | — | — | — |

**L'effet est intégralement porté par l'ORB, et l'explication est mécanique.** Le FOMC tombe le
mercredi à 14:00 ET. La sleeve overnight ne tient que les nuits de **lundi et mardi** : elle est
plate le mercredi par construction, d'où 1 et 0 observations. L'ORB, lui, entre vers 10:00 ET et
sort à la clôture RTH ~16:00 ET — **il tient donc une position US100 en travers de l'annonce**, sur
laquelle il n'a aucun edge.

Ce n'est pas un overlay macro. C'est **une sleeve qui traverse une annonce programmée sans raison
de le faire.**

## Robustesse

**Multiple testing** : 4 flags testés, seuil Šidák à 5 % ⇒ |t| ≥ 2,49. Observé **3,12**. Franchi.

**Stabilité de signe** — le test que B3 avait échoué :

| période | n | écart | t_HAC |
|---|---|---|---|
| 2018-2020 | 24 | −12,51 bps | −2,59 |
| 2021-2023 | 24 | −9,74 | −1,39 |
| 2024-2026 | 19 | −10,48 | −1,71 |

**Le signe ne s'inverse jamais** et l'amplitude est stable entre −9,7 et −12,5 bps. Les deux
dernières sous-périodes ne sont pas individuellement significatives, mais aucune ne contredit.

**Valeur** : la perte cumulée évitée vaut **+5,23 pt sur 8,4 ans, soit +0,62 pt/an**, sur un book
qui rend +7,30 pt/an. Environ **8,5 % de rendement en plus, en ne faisant rien 8 jours par an.**

## ⚠ La réserve que je dois poser, par cohérence avec moi-même

**Ratio effet/MDE80 = 0,81.** L'effet est sous son propre plancher de détection à 80 % de puissance.
Par L65, c'est **UNDERPOWERED** — et je viens de tuer l'axe B3 en partie sur ce critère (ratios
0,63-0,65). Je ne peux pas appliquer la règle dans un sens et pas dans l'autre.

Trois différences que je considère matérielles, et qu'il faut évaluer comme un argument, pas
comme une échappatoire :

1. **B3 changeait de signe sur son holdout.** Ici le signe est stable sur les trois sous-périodes.
2. **B3 échouait au contrôle de dose** (les événements non tradés portaient un t supérieur). Ici il
   n'y a pas de dose — le flag est binaire — et il existe une explication mécanique vérifiable :
   la sleeve tient à travers l'annonce.
3. **B3 cherchait un alpha. Ici on RETIRE une exposition non voulue.** Cesser de tenir une position
   en travers d'une annonce programmée sur laquelle on n'a pas d'edge n'exige pas le même niveau de
   preuve qu'ajouter une source de rendement. Le contrefactuel n'est pas « gagner plus », c'est
   « ne pas subir un risque qu'on ne s'est jamais donné pour objectif de porter ».

**Cette troisième différence est un argument, pas une preuve.** Elle doit être écrite comme telle
et pesée par l'opérateur.

## Ce qui reste à faire, et ce que ça change

Les étapes 1 à 3 du protocole (contrôle à duty cycle apparié contre un dé-levier piloté par la vol
réalisée, puis Δp(pass) par simulation de barrière) restent à exécuter. **Mais leur nature change** :
le contrôle « vol réalisée » n'a plus de sens comme comparateur, puisque le flag ne prédit pas la
vol. Le bon comparateur devient : **retirer 8 jours au hasard, appariés au duty cycle**, pour
vérifier que le gain ne vient pas du simple fait de moins s'exposer.

⚠ **Contrainte de déploiement** : sauter l'ORB les jours FOMC touche le code live et exige la chaîne
complète (config → yaml → sha → mqh → recompilation → dépôt), en fenêtre samedi. Ce n'est pas un
changement d'une ligne. À arbitrer contre la décision ORB déjà prévue en octobre — dont ce résultat
devient un intrant : **au coût mesuré de 2,11 bps s'ajoute un défaut daté de 0,62 pt/an.**
