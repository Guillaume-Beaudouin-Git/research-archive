# Audit indépendant #2 — vérification des correctifs post-audit-1

**Auditeur** : second passage, lecture seule, aucune modification de fichier existant, aucun
sous-agent, aucune connexion VPS, aucun backtest, aucun moniteur armé.
**Périmètre** : `deploy/book_executor_FOMC.mq5`, `deploy/diff.patch`, `deploy/fomc_dates.txt`,
`deploy/NOTES_IMPLEMENTATION.md`, `deploy/AUDIT_INDEPENDANT.md` (1er audit), contre
`ftmo_live/mt5/book_executor.mq5` (original, intact) et `PLAN_DEPLOIEMENT.md`.
**Mandat** : attaquer les deux correctifs de code appliqués suite au 1er audit, pas confirmer.
Compte réel 10 000 $ statique, fenêtre de déploiement samedi 12 septembre.

---

## Méthode (pour que la profondeur soit jugeable)

1. `git log` sur `deploy/` : un seul commit (`0b9ece99`) a introduit tout le dossier ; les deux
   correctifs sont des modifications **non commitées** de l'arbre de travail. `git diff HEAD --
   book_executor_FOMC.mq5` donne donc le diff EXACT des deux correctifs, isolé du reste — je l'ai
   lu intégralement plutôt que de me fier au résumé de `NOTES_IMPLEMENTATION.md`.
2. **Le diff livré (`diff.patch`) a été RÉ-APPLIQUÉ programmatiquement** (`patch -p1 --dry-run`
   puis pour de vrai) sur une copie fraîche de `ftmo_live/mt5/book_executor.mq5`, comparé au
   fichier livré par `diff -u` (vide) **et par MD5** (`3bfca3f5a2644b540e7b3e918bdf5b1c` des deux
   côtés) — refait moi-même, pas recopié du 1er audit (mandat point 7).
3. Comparaison ligne à ligne du bloc `if(np!=3) continue; ... if(y<=1900||...) continue;` (avant
   correctif #2, retrouvé via `git diff HEAD`) contre `bool ok=(np==3); ... ok=(y>1900&&...);` —
   application de la loi de De Morgan terme à terme, pas une relecture visuelle.
4. `grep` exhaustif de `g_fomc_today` (10 occurrences) et `IsFomcToday(` (3 occurrences : def +
   2 appels) sur le fichier **livré** (pas sur les notes) — les deux appels vérifiés un à un pour
   confirmer qu'ils affectent bien le retour.
5. Relecture complète, ligne par ligne, de `DayRollover()`, `OnInit()`, `OnTimer()`, `WriteState()`
   — recherche spécifique d'un chemin où le nouvel appel `IsFomcToday()` s'intercale entre deux
   écritures d'état partiellement effectuées (question non posée par le 1er audit).
6. Comparaison de `DayRollover()` **original** (sans FOMC) contre la version livrée pour établir si
   le risque trouvé au point 5 est pré-existant ou introduit par ce patch.
7. Lecture de `ftmo_live/supervisor.py::_cooldown_ok`/`_alert`/`evaluate_alerts` (717 lignes) pour
   répondre factuellement à la question spam (mandat point 3) plutôt que par déduction.
8. `xxd` sur `fomc_dates.txt` livré : pas de BOM, LF pur, pas de ligne vide finale.
9. Recalcul Python indépendant (from scratch, pas recopié du 1er audit) : les 11 dates tombent
   toutes un mercredi et sont toutes postérieures à aujourd'hui (2026-09-07).
10. Relecture de `ftmo_live/lib/statefiles.py::read_json` : `json.loads` nu, pas de validation de
    schéma — confirmé indépendamment que le nouveau champ `fomc_today` ne peut rien casser.
11. `git diff HEAD -- PLAN_DEPLOIEMENT.md` : vide → les corrections de documentation (À CORRIGER
    #3/#4 du 1er audit) sont déjà committées, vérifié plutôt que supposé.

---

## BLOQUANT

**Aucun.**

---

## À CORRIGER

**Aucun point bloquant ou fonctionnel n'a été trouvé sur les deux correctifs eux-mêmes** — voir
cependant la REMARQUE ci-dessous, qui documente un résidu du même défaut de conception que
corrigeait le correctif #1, non couvert par sa correction, mais d'impact négligeable.

---

## REMARQUES

### 1. Le correctif #1 ne couvre que `g_fomc_today` — pas les autres champs remis à zéro par `DayRollover()` après son appel à `IsFomcToday()`
**Fichier** : `book_executor_FOMC.mq5:1295-1318` (`DayRollover()`), en particulier l'ordre des lignes
1299-1306.

`DayRollover()` remet à zéro plusieurs globales exposées dans `state.json` (`g_micro_state`,
`g_or_hi`, `g_or_lo`, `g_micro_be`, entre autres) **APRÈS** sa ligne `g_fomc_today=IsFomcToday();`
(ligne 1301), qui intervient juste après le reset de `g_opened_today/g_flat_today/g_breaker_today`
mais **avant** le reset de l'état micro-ORB/OR (lignes 1302-1305) et avant le calcul de
`g_zombie_days`. Si `IsFomcToday()` emprunte un chemin fail-open ce jour-là (fichier absent/vide/
tout illisible — situation rare, ~1×/an), son `SetError(...)` interne déclenche un
`WriteState(true)` **au milieu de `DayRollover()`**, avant que `g_micro_state`/`g_or_hi`/`g_or_lo`/
`g_micro_be` n'aient été remis à zéro. Ce `state.json` intermédiaire contiendrait donc
`anchor_balance`/`anchor_date`/`opened_today`/`flat_today`/`fomc_today` **corrects (jour du jour)**
mais `micro_state`/`micro_or_hi`/`micro_or_lo`/`micro_be` **encore ceux de la veille**.

C'est la **même famille de défaut** que corrigeait le correctif #1 (SetError synchrone qui écrit un
état partiellement mis à jour), mais sur un périmètre plus large que ce que corrige le correctif —
qui ne traite que la variable qu'il vient de calculer, pas l'ensemble de la fonction appelante dans
laquelle il s'insère.

**Confirmé comme NOUVEAU (introduit par ce patch), pas pré-existant** : dans le
`DayRollover()` **original** (sans FOMC, vérifié par lecture directe de `ftmo_live/mt5/book_executor.mq5:1209-1232`),
aucune fonction appelée avant la fin du bloc de reset ne peut déclencher `SetError`
(`LogSwapsBilled()` ne contient aucun appel à `SetError`, vérifié par grep sur son corps) — ce
chemin d'écriture intermédiaire partiellement stale n'existait donc pas avant l'insertion de
`IsFomcToday()`.

**Sévérité réelle jugée très faible, pour trois raisons** :
- Fenêtre d'exposition = quelques instructions MQL5 synchrones (pas de `sleep`/yield entre les deux
  écritures) : `DayRollover()` se termine elle-même par `SaveState(); WriteState(true);` (forcé,
  ligne ~1317-1318), qui réécrit un état **totalement cohérent** microsecondes plus tard, dans le
  même appel de fonction — pas 60 secondes plus tard.
- Ce constat **nuance d'ailleurs la sévérité affichée par le 1er audit pour son propre point #1**
  (« jusqu'à 60 secondes ») : ce chiffre venait du throttle du `WriteState(false)` de fin
  d'`OnTimer()`, mais ignorait que `DayRollover()` (et `OnInit()`, même schéma) fait déjà son
  **propre** `WriteState(true)` forcé en sortie — la fenêtre réelle, dans les deux cas, est de
  l'ordre de la microseconde intra-fonction, pas du cycle de throttle. Le correctif #1 reste une
  bonne pratique (il évite même cette fenêtre microscopique), mais le risque qu'il corrige était
  déjà, en pratique, quasi inobservable de l'extérieur.
- Un opérateur qui lirait ce `state.json` exactement dans cette fenêtre verrait un OR/micro-état
  d'hier sur un jour où, de toute façon, `micro_state` ne sera pertinent qu'à partir de 15:30 Paris
  — aucune décision opérationnelle ne se prend sur ce champ à cette heure (rollover = minuit).

**Correction suggérée (optionnelle, bon marché)** : déplacer `g_fomc_today=IsFomcToday();` à la
**fin** du bloc de reset de `DayRollover()` (juste avant le calcul de `g_zombie_days` ou juste avant
`SaveState()`), pour que le `WriteState(true)` interne éventuel — s'il se produit — retrouve un état
déjà entièrement remis à jour. Zéro risque, zéro recompilation supplémentaire par rapport à ce qui
est déjà prévu pour cette livraison.

### 2. `IsFomcToday()` n'est plus une fonction "pure" — son nom ne le dit pas
**Fichier** : `book_executor_FOMC.mq5:1061` (signature) et commentaire `:1063-1067`.

Le mandat demande explicitement de chercher « un appel futur qu'un développeur ajouterait
naïvement ». Réponse : aujourd'hui, aucun risque (2 appels, tous deux affectent le retour, l'un et
l'autre sont d'ailleurs redondants avec l'effet de bord désormais interne). Mais le correctif change
la nature de la fonction : `bool IsFomcToday()` a un nom de **prédicat pur** (« est-ce que
aujourd'hui est FOMC ? ») alors qu'elle **modifie désormais toujours** une globale qui gate un
ordre réel, y compris si un futur mainteneur l'appelait seulement pour un diagnostic ponctuel («
est-ce que le filtre serait actif aujourd'hui ? », ex. depuis un `Comment()` de debug ou un script
utilitaire) sans intention de changer le comportement de trading du jour. Le commentaire en tête de
fonction (« ⚠ EFFET DE BORD ASSUMÉ ») documente bien le risque pour les 2 appelants actuels, mais ne
protège pas un futur appelant qui ne lirait que la signature.

Pas un défaut de CE livrable (2 appels, tous deux corrects et vérifiés) — un risque de
maintenabilité à moyen terme. **Aucune action requise avant samedi.** Suggestion pour une itération
future : soit renommer (`IsFomcTodayAndArm()`), soit séparer un calcul pur
(`bool FomcMatch(MqlDateTime &p, string &err)`) d'un appelant qui affecte `g_fomc_today` et lève
l'alerte — repousse le couplage hors de la fonction de lecture.

### 3. Spam Telegram : couvert par un mécanisme préexistant, non touché par ce patch — vérifié, pas supposé
**Fichier** : `ftmo_live/supervisor.py:157-159` (`_alert`), `:368-381` (catégorie `reject`).

`evaluate_alerts()` clé le cooldown des erreurs EA sur
`"reject_" + hashlib.sha1(err.encode()).hexdigest()[:8]`, cooldown **60 minutes**, avec un
commentaire explicite dans le code notant que `hash()` nu avait déjà causé un bug de non-dédup
corrigé antérieurement (accumulation de 15/67 clés orphelines). Les 3 nouveaux messages
`SetError(...)` d'`IsFomcToday()` sont des chaînes **statiques ou quasi-statiques** (le message
« n_bad>0 » varie seulement si le fichier change, ce qui n'arrive qu'au rafraîchissement annuel) :
un redémarrage en boucle de l'EA (crash-loop, watchdog agressif) ne produirait donc **au plus une
alerte Telegram par heure**, quel que soit le nombre de redémarrages MT5 dans cette fenêtre — le
journal MT5 (`Print`), lui, verrait un message par redémarrage, mais c'est un comportement
générique déjà partagé par tous les `SetError()` existants du fichier (48 sites), pas quelque chose
introduit par ce patch. **Pas d'avalanche possible côté opérateur.**

### 4. Équivalence de la restructuration du parsing — démontrée, pas seulement relue
**Fichier** : `book_executor_FOMC.mq5:1082-1109`, comparé à la version pré-correctif-2 retrouvée via
`git diff HEAD`.

Avant : `if(np!=3) continue;` puis, après extraction, `if(y<=1900||m<1||m>12||d<1||d>31) continue;`.
Après : `bool ok=(np==3); if(ok) { extraction; ok=(y>1900 && m>=1 && m<=12 && d>=1 && d<=31); }
if(!ok) { n_bad++; ...; continue; }`.

Par la loi de De Morgan, `!(y<=1900 || m<1 || m>12 || d<1 || d>31)` ≡
`(y>1900 && m>=1 && m<=12 && d>=1 && d<=31)` — **terme à terme identique** à la nouvelle condition
`ok`. Aucune borne n'a changé de sens (le `y<=1900` de l'original devient bien `y>1900`, pas
`y>=1900` ni une autre dérive). Le calcul de `hit`/`n_parsed` (donc de `g_fomc_today`) est
**rigoureusement identique** avant/après sur toute entrée, valide ou invalide — seule
l'instrumentation (`n_bad`, `first_bad`, l'alerte `else if(n_bad>0)`) est additive. Le correctif #2
ferme exactement le trou décrit dans `AUDIT_INDEPENDANT.md` « À CORRIGER #2 » (ligne isolée
malformée jamais alertée) sans toucher au comportement de filtrage lui-même.

### 5. MQL5 strict — vérifié construction par construction
- `StringFormat(... \"%s\" ...)` : `\"` est une séquence d'échappement standard MQL5 (héritée du
  C++) — syntaxe valide, produit des guillemets littéraux autour de `first_bad` dans le message.
- `first_bad==""` : comparaison de `string` par `==`, opérateur natif MQL5, pattern déjà utilisé
  ailleurs dans ce même fichier (`if(l=="" || ...)`, ligne 1090) — pas de gotcha.
- `string parts[];` redéclaré à chaque itération : tableau dynamique local, libéré automatiquement
  en fin d'itération (pas de gestion mémoire manuelle en MQL5 pour ce cas) — idiome sûr, pas neuf
  (le fichier utilise déjà ce pattern ailleurs, ex. `JKey()`).
- `StringSplit(l, '.', parts)` sur une ligne sans point : renvoie `np=1` avec `parts[0]` = la ligne
  entière (comportement documenté MQL5) → `ok=(np==3)` faux, aucun accès hors-bornes, correctement
  routé vers `n_bad`.
- Accès `parts[0..2]` toujours **gardé** par `if(ok)` (donc `np==3` garanti) avant toute lecture —
  aucun risque d'index hors-bornes, y compris sur les lignes exotiques (`"..."` → `np=4` → `ok`
  faux avant tout accès).
- Fuite de handle : les 3 chemins de sortie d'`IsFomcToday()` ferment le handle avant `return`, sauf
  `INVALID_HANDLE` où aucun handle n'a été ouvert — confirmé par relecture complète de la fonction,
  aucun changement par rapport au 1er audit sur ce point.
- `#property version "1.02"` / commentaire de tête : cosmétique, sans consommateur strict côté
  Python (revérifié ci-dessous).

### 6. Conclusions du 1er audit — revalidées sur le fichier actuel, pas recopiées
- **`FundedOrbOn()`** : un seul appel hors définition dans le fichier livré (`:1144`, branche
  ENTRÉE de `Do1600Arm()`), confirmé par `grep` sur le fichier **actuel** (pas celui du 1er audit).
- **`g_fomc_today`** : 10 occurrences au total, dont exactement 2 appels à `IsFomcToday()`
  (`:1301` DayRollover, `:1773` OnInit), tous deux de la forme `g_fomc_today=IsFomcToday();` —
  aucun appel « orphelin » sans capture du retour.
- **Chemins de sortie** : `Do2200TimeStop()`, `InvariantCheckM5()` (breaker), le kill-file `FLAT`
  (`OnTimer()`) et `FlattenAll()` ne référencent ni `FundedOrbOn()` ni `g_fomc_today` (recherché
  directement dans le corps de chacune de ces fonctions sur le fichier livré, résultat vide) — les
  sorties restent gouvernées uniquement par le volume signé / magic number, comme conclu par le 1er
  audit, et ce constat **tient toujours** sur la version corrigée.
- **`statefiles.py`** : `read_json` = `json.loads` nu, `STATE_SCHEMA` définie mais jamais comparée —
  reconfirmé par lecture directe, le nouveau champ `fomc_today` (et le bump de version) ne peuvent
  rien casser côté Python.
- **`PLAN_DEPLOIEMENT.md`** : `git diff HEAD` **vide** sur ce fichier — les corrections de
  documentation demandées par le 1er audit (§3 dépôt Testeur, §5 reformulation du retour arrière)
  sont **déjà committées** dans `0b9ece99`, vérifié et non supposé.

### 7. `fomc_dates.txt` — re-vérifié indépendamment
`xxd` : pas de BOM, fin de ligne LF pure, dernière ligne (`2027.12.08`) correctement terminée sans
ligne vide finale. Recalcul Python from-scratch (pas recopié du 1er audit) : les 11 dates tombent
toutes un mercredi et sont toutes strictement postérieures à aujourd'hui (2026-09-07) — cohérent
avec la note des notes d'implémentation sur l'omission volontaire des dates 2026 déjà passées.

### 8. Non-régression un jour non-FOMC — confirmée par preuve, pas par lecture
`patch -p1` de `diff.patch` sur une copie fraîche de `ftmo_live/mt5/book_executor.mq5`, suivi de
`diff -u` et de sommes MD5 : **fichier reconstruit strictement identique** (byte pour byte,
MD5 `3bfca3f5a2644b540e7b3e918bdf5b1c` des deux côtés) au fichier livré. Le diff est donc bien la
représentation EXHAUSTIVE des changements (mandat point 7, refait moi-même). Revue des hunks : hors
la ligne `else if(FundedOrbOn() && width_ok && !g_flat_today && !g_fomc_today)` (`:1144`), tous les
ajouts sont dans des blocs qui n'exécutent RIEN sur un jour non-FOMC sans anomalie de fichier
(`g_fomc_today` reste `false` toute l'année sauf sur les 11 dates listées) — le `&&` ajouté est un
no-op tant que `g_fomc_today==false`. Non-régression tenue.

---

## Réponse point par point au mandat

**1. Effet de bord `IsFomcToday()` sûr ?** Oui pour les 2 appelants actuels (tous deux affectent le
retour, effet interne idempotent avec l'affectation externe). **Trouvé au-delà de la question
posée** : le point d'insertion du 1er appel, à l'intérieur de `DayRollover()`, laisse un résidu
étroit et auto-corrigé du même défaut que corrigeait le correctif #1 (REMARQUE #1) ; et la fonction
n'est plus « pure » au sens de son nom, ce qui est un risque pour un appel futur non anticipé mais
n'affecte aucun appelant existant (REMARQUE #2). Mode Testeur : `IsFomcToday()` se comporte
correctement (fail-open) si le fichier n'y est pas déposé — c'est déjà couvert par « À CORRIGER #4 »
du 1er audit, dont la correction de plan est committée.

**2. Équivalence du parsing restructuré ?** Démontrée formellement (De Morgan), pas seulement
relue — voir REMARQUE #4. Aucune divergence, y compris sur les bornes (`y<=1900`↔`y>1900`,
inégalités toutes correctement inversées).

**3. `SetError` peut-il spammer ?** Non — cooldown SHA1 60 min pré-existant dans `supervisor.py`,
non touché par ce patch, vérifié par lecture directe du code (pas déduit) — voir REMARQUE #3.

**4. MQL5 strict.** Tous les points cités dans le brief (guillemets échappés, comparaison de
chaîne, tableau redéclaré en boucle, `StringSplit` sans séparateur, fuite de handle) vérifiés
construction par construction — voir REMARQUE #5. Aucun défaut trouvé.

**5. Non-régression un jour sans FOMC.** Tenue — voir REMARQUE #8, preuve par reconstruction
byte-exacte + revue des hunks.

**6. Le 1er audit reste-t-il valide ?** Oui sur tous ses points cités (`FundedOrbOn()` un seul
appel, sorties non gatées, `statefiles.py` tolérant, doc plan corrigée) — chacun **re-vérifié
indépendamment sur le fichier actuel**, pas recopié — voir REMARQUE #6.

**7. Exhaustivité du diff.** Ré-appliqué moi-même (`patch -p1`), comparaison `diff -u` + MD5 :
identique. Confirmé indépendamment, pas fait confiance à l'affirmation précédente.

---

## Recommandation

**Déployer samedi 12 septembre — aucune action requise avant compilation.**

Les deux correctifs de code font exactement ce qu'ils annoncent : le correctif #1 supprime la
staleness de `fomc_today` dans `state.json` sur le chemin fail-open (et, accessoirement, cette
staleness était déjà quasi inobservable dans les faits — voir REMARQUE #1) ; le correctif #2 ferme
le trou d'alerte sur une ligne de date isolée malformée, démontré logiquement équivalent au parsing
d'origine sur toute entrée valide. Aucun des deux n'introduit de régression, de fuite de ressource,
ni de risque de spam Telegram.

La seule chose trouvée qui n'était identifiée nulle part avant ce passage (REMARQUE #1 — résidu de
staleness sur `micro_state`/`micro_or_hi`/`micro_or_lo`/`micro_be` dans la fenêtre synchrone
`DayRollover()`) est d'impact opérationnel négligeable (fenêtre de l'ordre de la microseconde,
auto-corrigée dans le même appel de fonction, sur des champs qui ne pilotent aucune décision à
minuit) : elle **ne justifie pas** de retarder le déploiement. Le correctif suggéré (déplacer
`g_fomc_today=IsFomcToday();` en fin de bloc de reset dans `DayRollover()`) peut être appliqué avant
compilation samedi s'il reste du temps — coût de quelques minutes, zéro risque — ou reporté sans
conséquence.

Compiler le `.ex5` (étape 2 du plan, toujours non franchie — ni par l'implémenteur, ni par ce
passage d'audit, aucun MetaEditor disponible) reste la seule étape non négociable avant tout le
reste, comme déjà noté par les deux documents précédents.
