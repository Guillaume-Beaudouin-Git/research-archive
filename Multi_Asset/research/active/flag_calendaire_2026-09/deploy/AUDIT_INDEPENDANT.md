# Audit indépendant — filtre FOMC sur le funded ORB

**Auditeur** : passe indépendante, lecture seule, aucune modification de fichier existant,
aucun sous-agent, aucune connexion VPS, aucun backtest.
**Périmètre** : `deploy/book_executor_FOMC.mq5`, `deploy/diff.patch`, `deploy/fomc_dates.txt`,
`deploy/NOTES_IMPLEMENTATION.md`, contre `ftmo_live/mt5/book_executor.mq5` (original, intact),
`PLAN_DEPLOIEMENT.md`, `ETAPE0_RESULTAT.md`, `ftmo_live/README.md`,
`ftmo_live/lib/statefiles.py`, `ftmo_live/supervisor.py`, `ftmo_live/reconcile.py`.
**Mandat** : attaquer, pas confirmer. Compte réel 10 000 $ statique.

---

## Méthode (pour que la profondeur soit jugeable)

1. `git diff --stat -- ftmo_live/` vérifié vide (aucun fichier live touché).
2. **Le diff a été RÉ-APPLIQUÉ programmatiquement** (`patch -p1`) sur une copie propre de
   `ftmo_live/mt5/book_executor.mq5`, puis comparé octet à octet au fichier livré
   `book_executor_FOMC.mq5` : **identique**. Ce n'est pas une relecture visuelle du diff, c'est
   une preuve que le diff est la représentation EXHAUSTIVE des changements — aucune modification
   silencieuse hors diff n'est possible.
3. `grep` exhaustif de `FundedOrbOn(` sur l'original ET la copie modifiée : un seul point d'appel
   dans les deux, à l'identique (`Do1600Arm()`, branche ENTRÉE). Confirmé indépendamment de
   l'affirmation de l'implémenteur.
4. `grep` exhaustif de `g_fomc_today`/`IsFomcToday` sur le fichier modifié : 6 occurrences, toutes
   listées et tracées une à une (déclaration, définition, appel DayRollover, appel OnInit, condition
   d'entrée, champ JSON, ligne de log) — aucune occurrence supplémentaire cachée.
5. Lecture complète de `Do2200TimeStop()`, `InvariantCheckM5()` (breaker), `OnTimer()` (kill-file
   `FLAT`), `FlattenAll()` : aucun ne référence `FundedOrbOn()` ni `g_fomc_today`. Confirmé par
   grep + lecture, pas par confiance dans les notes.
6. **Recalcul indépendant, en Python, des dates de bascule DST US et UE pour 2026 et 2027**
   (2ᵉ dimanche de mars / dernier dimanche de mars-octobre / 1ᵉʳ dimanche de novembre), et
   confrontation aux 11 dates FOMC du fichier — pas une relecture du tableau de
   `NOTES_IMPLEMENTATION.md`, un calcul de zéro (détail §3).
7. Vérification que les 11 dates du fichier tombent bien un mercredi (`date`/`python3`), cohérent
   avec le format d'annonce FOMC — détecterait une erreur de retranscription du calendrier Fed.
8. Lecture de `ftmo_live/lib/statefiles.py`, `supervisor.py`, `reconcile.py` : confirmation qu'il
   n'existe aucune validation de schéma strict (`read_json` = `json.loads` nu, `STATE_SCHEMA` est
   une constante jamais consultée) — un champ JSON supplémentaire ne peut rien casser côté Python.
9. Hexdump du fichier `fomc_dates.txt` livré : pas de BOM, terminaison LF pure, dernière ligne
   correctement terminée par `\n`, pas de ligne vide finale.
10. Relecture complète de `OnInit()`, `OnTimer()`, `DayRollover()` pour l'ordre d'initialisation et
    les scénarios de redémarrage (avant/après 16:00, jour FOMC ou non, VPS multi-jours down).

---

## BLOQUANT

**Aucun.**

---

## À CORRIGER

### 1. `IsFomcToday()` écrit un `state.json` transitoirement incohérent sur le chemin fail-open
**Fichier** : `book_executor_FOMC.mq5:1066, 1072, 1096` (les trois appels `SetError(...)` internes
à `IsFomcToday()`) et `:1278`/`:1750` (`g_fomc_today=IsFomcToday();`).

`SetError()` (ligne 522) appelle `WriteState(true)` **de manière synchrone à l'intérieur même de
l'appel** à `IsFomcToday()` — c'est-à-dire **avant** que la valeur de retour ne soit assignée à
`g_fomc_today` par l'appelant. Sur le chemin fail-open (fichier absent/vide/illisible), la séquence
réelle est :

1. `IsFomcToday()` détecte l'anomalie, appelle `SetError(...)`.
2. `SetError` écrit `state.json` **avec la valeur ENCORE PRÉCÉDENTE de `g_fomc_today`** (celle de
   la veille, ou `false` par défaut) — pas la valeur `false` qui sera assignée juste après.
3. `IsFomcToday()` retourne `false`, l'assignation `g_fomc_today=false` a lieu.
4. Le `WriteState(false)` suivant, en fin d'`OnTimer()`, est **throttlé 60 s**
   (`if(!force && TimeCurrent()-g_last_state_write<60) return;`, ligne ~1561) car le
   `WriteState(true)` de l'étape 2 vient de réinitialiser `g_last_state_write`.

**Conséquence** : sur le chemin d'erreur — précisément celui que `supervisor.py` doit diagnostiquer
via `last_error` — le champ `fomc_today` de `state.json` peut afficher la **mauvaise valeur pendant
jusqu'à 60 secondes**. Aucun impact sur le trading réel (la variable globale en mémoire, seule lue
par `Do1600Arm()`, est correcte dès le retour de la fonction) — c'est un défaut d'observabilité,
pas de sécurité. Mais c'est trompeur exactement au moment où un opérateur regarderait `state.json`
pour comprendre l'alerte.

**Correction proposée** : séparer le calcul du résultat de l'émission de l'alerte, par ex. faire
retourner à `IsFomcToday()` un message d'erreur par référence plutôt que d'appeler `SetError`
elle-même, et laisser l'appelant faire `g_fomc_today=v; if(err!="") SetError(err);` — assignation
AVANT l'écriture forcée.

### 2. Une ligne de date isolée malformée n'est jamais alertée
**Fichier** : `book_executor_FOMC.mq5:1095-1097`.

L'alerte ne se déclenche que si **AUCUNE** ligne n'est parseable (`n_lines>0 && n_parsed==0`). Une
ligne de date individuellement mal formée au milieu d'un fichier par ailleurs correct (coquille
humaine — le fichier est maintenu à la main 1×/an — ex. `2026.09.61`, un jour hors bornes, ou une
transposition de chiffres qui reste dans les bornes `1-31`/`1-12` mais tombe sur la mauvaise date)
est **silencieusement ignorée sans aucune alerte**, puisque les autres lignes parsent normalement.
C'est un choix assumé par l'implémenteur (§5.3 des notes) mais **le pire scénario possible pour
cette fonctionnalité** : un jour FOMC réel qui n'est PAS filtré, sans que personne ne le sache avant
de constater après coup un `funded_orb_entry` dans `fills.csv` un jour FOMC. Le fichier livré
(11 dates) a été vérifié manuellement correct (tous les jours tombent un mercredi, formats valides)
— ce constat ne bloque donc pas CE déploiement, mais expose le prochain rafraîchissement annuel.

**Correction proposée** : logguer/alerter aussi si `n_parsed < n_lines` (au moins un `Print`), ou
mieux, comparer `n_parsed` à un nombre minimal attendu (ex. ≥ 6/an) et alerter en dessous.

### 3. `PLAN_DEPLOIEMENT.md` §5 promet un retour arrière "immédiat" qui ne l'est pas un jour FOMC en cours
**Fichier** : `PLAN_DEPLOIEMENT.md` §5 ("Immédiat, sans recompilation : supprimer `fomc_dates.txt`
du VPS ⇒ `IsFomcToday()` renvoie `false` ⇒ comportement actuel restauré **au tick suivant**").

C'est FAUX pour le cas qui compte le plus : si le filtre s'est déjà armé au rollover de minuit
(`g_fomc_today` mis en cache pour toute la journée), supprimer le fichier entre 00:00 et 16:00 le
jour FOMC lui-même **ne débloque PAS l'entrée de 16:00 de ce jour** — seulement celle du lendemain,
puisque `IsFomcToday()` n'est relue qu'à `DayRollover()`/`OnInit()`, jamais à chaque tick (conforme
à la règle #4 du brief, mais en contradiction avec le libellé du plan). **L'implémenteur l'a
lui-même identifié** (NOTES §6, doute #2) mais **le document du plan n'a pas été corrigé en
conséquence** — un opérateur qui s'y fierait en pleine crise le jour J croirait à tort disposer
d'un levier de dernier recours qui n'existe pas.

**Mitigant réel existant, non documenté dans le plan** : le kill-file `FLAT`
(`OnTimer():1773`, vérifié à chaque tick, `FileIsExist("FLAT")`) **est**, lui, un vrai levier
instantané intra-jour — mais il flatten et désarme **tout** l'EA, pas seulement l'ORB funded. C'est
un marteau, pas un scalpel, mais il fonctionne le jour même.

**Correction proposée** : reformuler §5 du plan (« *retour arrière : empêche le PROCHAIN jour FOMC
non encore armé ; pour interrompre une entrée déjà armée le jour même, seul le kill-file `FLAT`
agit, et il désarme tout l'EA* ») avant samedi — c'est un changement de documentation, zéro
recompilation, zéro risque.

### 4. `fomc_dates.txt` doit être déposé DEUX fois pour que les tests du plan (étapes 3-4) soient probants
**Fichier** : `PLAN_DEPLOIEMENT.md` §4, étapes 3 et 4.

`FileOpen("fomc_dates.txt", ...)` sans `FILE_COMMON` résout un chemin **relatif au dossier
`MQL5/Files` de l'agent/du Testeur de stratégie**, distinct du `MQL5/Files` de l'instance live sur
le VPS. Si l'opérateur ne dépose `fomc_dates.txt` QUE dans le dossier live (comme le décrit l'étape
6 du plan) et lance ensuite l'étape 3/4 dans le Testeur MT5 SANS l'y copier aussi, `IsFomcToday()`
tombera systématiquement sur `INVALID_HANDLE` (fail-open) dans le Testeur — **l'étape 3 "passera"
pour la mauvaise raison** (aucun filtrage nulle part, pas parce que le filtre respecte les jours
non-FOMC) et **l'étape 4 (test positif) échouera silencieusement** — pas parce que le code est
cassé, mais parce que le fichier de test n'est pas visible du Testeur. Un faux verdict dans un sens
comme dans l'autre est possible ici.

**Correction proposée** : ajouter une sous-étape explicite au plan — déposer `fomc_dates.txt`
également dans `<data_folder>/Tester/Agent-XXX/MQL5/Files/` (ou utiliser `FILE_COMMON` si un
partage commun existe) avant les étapes 3 et 4.

---

## REMARQUES

- **BOM UTF-8** : non géré explicitement, mais inoffensif ici *par construction incidente* — même
  si un BOM corrompait le premier caractère de la première ligne de commentaire, cette ligne
  contient de toute façon plusieurs points (`fomc_dates.txt`, `YYYY.MM.DD`) donc `np!=3` la
  filtrerait quand même. Robuste pour ce fichier précis, pas par design délibéré — à garder en tête
  si le format du fichier évolue (ex. un jour où une ligne de commentaire aurait exactement 2 points).
- **CRLF** : le fichier livré est en LF pur (vérifié par hexdump). Le pattern de lecture
  (`while(!FileIsEnding(h)) { FileReadString(h); ... }`) est **déjà utilisé deux fois en production**
  dans le fichier original (`targets.json` ligne 921, `ea_state.json` ligne 1616) — ce n'est pas du
  code neuf non éprouvé, c'est un pattern déjà validé sous Wine sur le VPS.
- **Fuite de handle** : aucune trouvée — les 3 chemins de sortie de `IsFomcToday()` ferment le
  handle avant `return`, sauf le cas `INVALID_HANDLE` où aucun handle n'a été ouvert (correct).
- **Dates FOMC hors calendrier** (réunion d'urgence, changement de date par la Fed en cours d'année)
  : le fichier est une liste statique, rafraîchie 1×/an — un changement de calendrier Fed en cours
  d'année ne serait PAS reflété avant le prochain rafraîchissement manuel. C'est un risque
  opérationnel connu et déjà nommé dans le plan (« fichier à rafraîchir 1×/an »), pas un défaut de
  ce livrable.
- **Log `Print`** : « jamais par tick/OnTimer » (commentaire ligne ~1057) est une formulation
  légèrement trompeuse — `IsFomcToday()` EST bien invoquée depuis `OnTimer()` (via `DayRollover()`
  quand la date change), pas depuis un `OnTick()` inexistant dans ce fichier (aucune fonction
  `OnTick` n'est définie — toute la logique tourne sur `EventSetTimer(1)`). L'intention documentée
  (pas recalculée à chaque cycle) est correcte ; le mot « jamais » est trop absolu. Cosmétique.
- **`#property version` / schéma `state.json`** : aucun consommateur Python ne lit ni la version EA
  ni `STATE_SCHEMA` (constante définie mais jamais comparée) — le bump `1.01→1.02` et l'ajout du
  champ `fomc_today` ne peuvent rien casser côté `supervisor.py`/`reconcile.py`, vérifié par lecture
  complète de `statefiles.py`.

---

## Réponse point par point au mandat

**1. Sortie jamais bloquée.** Confirmé indépendamment : un seul appel à `FundedOrbOn()` dans tout
le fichier (ligne 1121, branche ENTRÉE), identique dans l'original et la copie hors ce `&&` ajouté.
`Do2200TimeStop()` (ligne 1203), `InvariantCheckM5()`/breaker (ligne 1252), le kill-file `FLAT`
(ligne 1773) et `FlattenAll()` (ligne 733) filtrent tous par **magic number** / volume signé, jamais
par `FundedOrbOn()` ni `g_fomc_today`. Un redémarrage un jour FOMC (avant ou après 16:00) ne change
rien à ce constat : `g_fomc_today` ne module QUE la pose des ordres stop d'entrée.

**2. Cas limites de fichier.** Fichier absent → `INVALID_HANDLE`, fail-open + alerte. Vide →
détecté par `FileSize==0` avant la boucle (évite un fail-open silencieux). BOM/CRLF → non
dangereux ici (voir REMARQUES), pattern de lecture déjà éprouvé en production sur ce même fichier
EA. Ligne mal formée isolée → silencieusement ignorée, **gap réel signalé en À CORRIGER #2**. Ligne
dupliquée → sans effet (comparaison `hit=true` idempotente). Handle → toujours fermé sur tous les
chemins vérifiés.

**3. Fuseau horaire.** Démonstration refaite de zéro, indépendamment : DST US 2026/2027 (2ᵉ
dimanche mars, 1ᵉʳ dimanche nov.) et DST UE 2026/2027 (dernier dimanche mars/oct.) recalculés en
Python, pas recopiés des notes. Sur les 11 dates du fichier, **2 tombent dans une fenêtre de
désynchronisation** (2026-10-28 : UE hiver/US été, écart 5h ; 2027-03-17 : US été/UE hiver, écart
5h) — les 9 autres sont en régime normal (6h). Pour les 2 dates à risque, la décision d'entrée
(16:00 Paris) tombe en ET entre 10:00 et 11:00 selon l'écart réel — **toujours à ≥9h de tout minuit
ET**, donc la date calendaire ne dérive jamais. Le raisonnement de l'implémenteur est correct et
suffisant pour la question posée (la DATE, pas l'heure exacte de capture de l'OR — ce dernier point,
hors périmètre, est honnêtement signalé comme non résolu dans les notes, cf. L56). Le serveur FTMO
en EET est une hypothèse préexistante (`ftmo_live/README.md:67-68`), hors périmètre de ce diff ; un
changement de fuseau serveur casserait `ParisDate()` globalement (donc aussi `g_anchor_date`), pas
seulement `g_fomc_today` — risque déjà existant, non aggravé par ce patch.

**4. Non-régression.** Vérifiée programmatiquement (patch réappliqué = fichier livré, byte-exact).
Le seul changement de comportement possible un jour non-FOMC serait si `g_fomc_today` valait `true`
à tort — impossible sauf coïncidence de date dans le fichier, or les 11 dates sont vérifiées
correctes. Aucune variable globale, ordre d'`OnInit`, ou logique de rollover préexistante n'est
modifiée hors l'ajout strictement additif documenté.

**5. Persistance/redémarrage.** `g_fomc_today` n'est PAS persisté dans `ea_state.json` — recalculé
à `OnInit()` (ligne 1750) et à `DayRollover()` (ligne 1278), qui se déclenche lui-même au premier
tick post-redémarrage si `ParisDate()!=g_anchor_date`. Les deux mécanismes se recouvrent (le second
est redondant mais inoffensif si le premier a déjà tourné) : tous les scénarios de redémarrage
testés (avant 16:00, après 16:00, VPS down plusieurs jours, VPS redémarré à 23:00 un jour FOMC)
donnent une valeur correcte au moment où elle compte.

**6. Consommateurs `state.json`.** `statefiles.py`/`supervisor.py`/`reconcile.py` lus en entier pour
ce qui touche au parsing JSON : aucune validation de schéma stricte, `json.loads` nu, champ inconnu
toléré sans effet. Pas de risque de casse.

**7. Tension déclarée (lecture 1×/jour vs retour arrière).** Avis : **la conception 1×/jour est la
bonne décision** — elle respecte la règle #4 du brief et évite d'introduire une lecture de fichier
à chaque tick sur un chemin critique. La vraie faille n'est pas le code, c'est que
**`PLAN_DEPLOIEMENT.md` promet quelque chose que l'implémentation ne fait pas** (À CORRIGER #3) —
un problème de document, pas de conception, et qui se corrige sans toucher au `.mq5`.

**8. Au-delà de la liste de l'implémenteur.** Trouvé : la staleness transitoire de `state.json` sur
le chemin fail-open (À CORRIGER #1, un défaut de séquencement `SetError`/assignation que l'auteur
n'avait pas identifié), le gap d'alerte sur ligne isolée malformée (À CORRIGER #2, nommé par
l'auteur comme un choix mais pas creusé comme un risque), et l'isolation Testeur/live du dossier
`MQL5/Files` (À CORRIGER #4, absent des notes et du plan). Types/conversions MQL5
(`StringSplit`, `StringGetCharacter`, `StringToInteger`) vérifiés conformes aux signatures
documentées, pas de gotcha octal/hex sur les dates à zéro initial.

---

## Recommandation

**Déployer samedi 12 septembre, avec les 4 points « À CORRIGER » traités avant le déploiement** —
aucun ne touche à la logique de blocage d'entrée elle-même (donc aucun ne remet en cause le
raisonnement central de sécurité du filtre), mais tous sont bon marché à corriger et réduisent un
risque réel :
- #1 et #2 sont des modifications de code mineures dans `IsFomcToday()`/son appelant (quelques
  lignes), à faire AVANT compilation (étape 2 du plan) puisque le code n'est pas encore compilé.
- #3 et #4 sont des corrections de documentation pure (`PLAN_DEPLOIEMENT.md`), zéro risque, zéro
  recompilation.

Si le temps manque d'ici samedi pour #1/#2, ils peuvent être traités en itération suivante SANS
annuler le déploiement : ce sont des défauts d'observabilité/alerte sur un chemin fail-open déjà
sûr par construction (l'échec ouvert restaure le comportement actuel, jamais pire), pas des défauts
qui font trader l'EA de façon incorrecte. #3 et #4, en revanche, devraient être corrigés avant
samedi — ce sont des lignes de markdown, sans coût, qui évitent une mauvaise décision opérationnelle
en cas d'incident réel le jour J.
