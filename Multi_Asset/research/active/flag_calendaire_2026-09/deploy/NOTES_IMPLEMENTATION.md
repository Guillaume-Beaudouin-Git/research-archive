# Notes d'implémentation — filtre FOMC sur le funded ORB

**2026-09-07.** Livrable pour `PLAN_DEPLOIEMENT.md`. Aucun fichier de `ftmo_live/` n'a été
modifié — tout vit ici, dans `deploy/`. Ce document explique CE QUI a changé, POURQUOI, et
CE QUI RESTE INCERTAIN. Le code n'a **pas été compilé** (pas de MetaEditor sur ce Mac,
contrainte déjà documentée dans `ftmo_live/README.md` §Divergences sim↔live) : la compilation
reste l'étape 2 du plan de déploiement, à faire avant tout le reste.

---

## 1. Ce qui a changé, fichier par fichier

### `book_executor_FOMC.mq5` (copie modifiée de `ftmo_live/mt5/book_executor.mq5`)

Six changements, tous non destructifs :

1. **Global `g_fomc_today`** (près des autres flags `g_opened_today`/`g_flat_today`) —
   `bool`, recalculé une fois par jour, jamais persisté dans `ea_state.json`.
2. **Fonction `IsFomcToday()`** — nouvelle, placée juste avant `Do1600Arm()`. Lit
   `MQL5/Files/fomc_dates.txt`, compare la date Paris du jour (composants entiers
   année/mois/jour, PAS une comparaison de chaîne) à chaque ligne du fichier.
3. **Condition d'entrée** dans `Do1600Arm()`, branche funded ORB :
   `else if(FundedOrbOn() && width_ok && !g_flat_today && !g_fomc_today)`
   — un seul `&&` ajouté.
4. **Appel quotidien** de `IsFomcToday()` à deux endroits : dans `DayRollover()` (le
   chemin normal, une fois par jour au changement de date Paris) et dans `OnInit()`
   (pour qu'un redémarrage intra-journée en jour FOMC ne perde pas le flag — voir
   §4 "cas limites").
5. **Champ `"fomc_today"`** ajouté au JSON de `WriteState()` (`state.json`), à côté de
   `flat_today`, pour que `supervisor.py`/`reconcile.py` voient l'état sans lire le
   fichier de dates.
6. **Version bump** `1.01 → 1.02` (`#property version`) et une ligne de log au `Print`
   d'`OnInit` (`fomc_today OUI/non`) — diagnostic pur, zéro effet fonctionnel.

Rien d'autre n'a bougé. `FundedOrbOn()` elle-même (ligne ~171 de l'original) est
**intacte**, caractère pour caractère.

### `fomc_dates.txt`

Liste des 11 dates FOMC à venir depuis aujourd'hui (2026.09.16 → 2027.12.08), format
`YYYY.MM.DD`, une par ligne, commentaires `#` et lignes vides autorisés. Source :
`data/personal_book/post_fomc_drift/data_cache/fomc_events_forward.csv`. Les 5 dates
2026 déjà passées (2026-01-28 à 2026-07-29) sont volontairement omises — un fichier de
dates À VENIR n'a pas besoin de dates mortes, et ça réduit la surface de parsing.

---

## 2. Pourquoi cette conception (rappel du piège évité)

Le funded ORB (`Do1600Arm()`, branche `else if(FundedOrbOn()...)`) **ne lit pas**
`targets.json` — seule la branche micro-ORB appelle `TargetsValidate()`. C'est vérifié
dans le code lu (pas de `TargetsValidate()`/`g_targets_status` dans la branche funded ORB
de `Do1600Arm`), et le plan cite une observation empirique live (lundi 31 août, fill à
16:06 avec cibles du vendredi forcément `BAD_ONDAY`) qui confirme ce constat de code.

Un fichier dédié, découplé du cycle quotidien du brain (`fomc_dates.txt`, rafraîchi 1x/an),
évite les deux défauts symétriques d'un blocage passant par `targets.json` :
couper l'ORB tous les lundis (cibles du week-end périmées), ou lire un champ qui vaut 0
sur fichier périmé et laisser l'ORB tirer quand même un jour FOMC.

---

## 3. Démonstration — le fuseau horaire

**La question posée : la date SERVEUR/PARIS au moment de la décision d'entrée ORB
correspond-elle toujours à la date FOMC américaine (Eastern Time) ?**

### 3.1 Ce que fixe `InpServerTZOffsetMin`

`ParisNow() = TimeCurrent() - InpServerTZOffsetMin*60` (secondes). `InpServerTZOffsetMin=60`
suppose que le serveur FTMO (EET) est en permanence CET+1, car EET et CET sont toutes deux
des zones UE qui basculent DST le **même dimanche**. Cette hypothèse est déjà documentée
comme à re-vérifier à chaque DST dans `ftmo_live/README.md` (« InpServerTZOffsetMin=60 —
VÉRIFIER... re-vérifier aux DST »). Elle est **antérieure à ce changement** et hors de mon
périmètre — mais elle joue un rôle défensif dans la démonstration qui suit (§3.3).

### 3.2 Ce que je dois démontrer : le décalage Paris↔ET n'est PAS constant

Paris (CET/CEST) et New York (EST/EDT) ne changent pas d'heure d'été le même week-end :
- Le DST US démarre le **2ᵉ dimanche de mars** ; le DST UE démarre le **dernier dimanche
  de mars** — écart de 1 à 3 semaines.
- Le DST UE se termine le **dernier dimanche d'octobre** ; le DST US se termine le
  **1ᵉʳ dimanche de novembre** — écart d'environ 1 semaine.

Décalage Paris − ET = (UTC offset Paris) + (UTC offset ET, en valeur absolue) :

| période | Paris | ET | décalage |
|---|---|---|---|
| hiver (les deux en heure standard) | UTC+1 | UTC−5 | **6 h** |
| été (les deux en heure d'été) | UTC+2 | UTC−4 | **6 h** |
| fenêtre de mars (US déjà DST, UE pas encore) | UTC+1 | UTC−4 | **5 h** |
| fenêtre d'oct/nov (UE revenue en standard, US encore DST) | UTC+1 | UTC−4 | **5 h** |

⇒ **Le décalage Paris-ET vaut 5 h ou 6 h, jamais autre chose**, sur environ 2-4 semaines
par an (les fenêtres de transition) il vaut 5 h au lieu de 6 h.

### 3.3 La démonstration proprement dite : ça ne fait jamais dériver la DATE

`Do1600Arm()` s'exécute quand `hm>=1600 && hm<2000` (heure Paris). Convertie en ET, avec un
décalage dans `{5h, 6h}` :

- borne basse (Paris 16:00) → ET ∈ **[10:00, 11:00]**
- borne haute (Paris 20:00, exclue) → ET ∈ **[14:00, 15:00]**

Sur toute la fenêtre d'entrée, l'heure ET équivalente reste dans **[10:00, 15:00)** —
en plein après-midi américain, à des heures qui ne s'approchent JAMAIS de minuit ET dans
un sens ou dans l'autre. La date calendaire Paris et la date calendaire ET **coïncident
donc systématiquement** pendant toute la fenêtre où `Do1600Arm()` peut tirer, quel que
soit le régime DST en cours (6h normal ou 5h en fenêtre de transition).

Même raisonnement sur les bornes voisines, pour couvrir toute la vie active du funded ORB :
- construction de l'OR (`DoBuildOR`, Paris 15:30-16:00) → ET ≈ **9:30-11:00** (cohérent
  avec l'ouverture RTH 9:30 ET) ;
- sortie time-stop (`Do2200TimeStop`, Paris ≥22:00) → ET ≈ **16:00-17:00** (cohérent
  avec la clôture RTH ~16:00 ET citée dans `ETAPE0_RESULTAT.md`).

**Aucune de ces bornes n'approche minuit ET** (l'écart le plus proche de minuit est
Paris 22:00 → ET 16:00/17:00, soit 7-8 h de marge). Le filtre `IsFomcToday()` compare la
date Paris (via `ParisStruct()`, cohérent avec `ParisDate()`/`g_anchor_date` utilisés
partout ailleurs dans l'EA) — **jamais** `TimeToString(TimeCurrent(), TIME_DATE)` brut
(c'était la suggestion initiale du plan) car `TimeCurrent()` est l'heure SERVEUR (EET),
qui elle *peut* franchir minuit ~60 min avant Paris. Ce n'est pas un problème pour la
fenêtre 16:00-20:00 Paris (encore une fois loin de tout minuit, serveur ou Paris), mais
utiliser `ParisStruct()` élimine la question et reste cohérent avec le reste du fichier
— c'est un écart volontaire par rapport au pseudo-code du plan, documenté ici.

**Marge de robustesse supplémentaire** : même si l'hypothèse §3.1 (`InpServerTZOffsetMin`
constant à 60 min) était fausse d'une heure sur une session donnée (dérive serveur non
détectée), l'heure Paris résultante décalerait d'au plus 1 h — toujours à des heures
d'après-midi/soirée, toujours à 5-9 h de tout minuit. **La date FOMC ne peut pas driver
sur une erreur d'1 h de fuseau serveur.** Le risque réel serait sur l'HEURE d'ouverture
de l'OR (walk déjà documenté comme limite pré-existante, cf. §5), pas sur la DATE.

### 3.4 Ce que ça ne couvre PAS (hors périmètre, déjà connu)

L56 (registre de leçons) prévient que l'horloge d'échange avec son DST — pas UTC —
détermine QUELLE HEURE capture quel phénomène. Ici ce n'est pas un problème de date
(démontré ci-dessus) mais ça reste un problème potentiel de PRÉCISION HORAIRE : pendant
les 2-4 semaines de transition DST asynchrone, l'OR (15:30-16:00 Paris, censé capturer
9:30-10:00 ET) capture en réalité 10:30-11:00 ET (si décalage réel 5h) — une heure après
l'ouverture RTH, pas l'ouverture elle-même. C'est un défaut PRÉEXISTANT de calage horaire
du funded ORB, indépendant du filtre FOMC, et **hors périmètre de cette mission** (je n'ai
pas touché aux horaires `1530`/`1600`/`2200`). Je le signale parce que le brief demande
explicitement de traiter les bords DST — je le traite pour la question posée (la DATE),
et je documente que la question voisine (l'HEURE) reste ouverte et n'est pas résolue ici.

---

## 4. Inventaire complet des appels à `FundedOrbOn()`

Un seul appel dans tout le fichier, en dehors de sa définition :

| ligne (original) | fonction | rôle | modifié ? |
|---|---|---|---|
| 171 | définition | `(InpPhase==3) && (FU_ORB_RISK > 0.0)` | **NON** — intact caractère pour caractère |
| 1058 | `Do1600Arm()`, branche ENTRÉE (`else if(FundedOrbOn() && width_ok && !g_flat_today)`) | pose les deux ordres stop (`PlaceStopOrder` +1/−1) qui arment l'entrée funded ORB | **OUI** — `&& !g_fomc_today` ajouté |

Tous les autres points de code qui touchent la position funded ORB (`MAGIC_FORB`) filtrent
par **magic number**, pas par `FundedOrbOn()` :
- `Do2200TimeStop()` (sortie time-stop, ligne ~1140-1156) — boucle sur
  `magics[1]=InpMagicBase+MAGIC_FORB`, ferme la position si volume signé ≠ 0. Ne teste
  jamais `FundedOrbOn()`. **Inchangé, continuera de fermer une position FORB ouverte un
  jour FOMC** (cas qui ne devrait plus se produire après ce déploiement, mais qui reste
  géré correctement pour toute position résiduelle antérieure ou en cas de bug).
- `MicroManage()` (trail-to-BE) — teste `MicroEnabled()`, pas `FundedOrbOn()`, mais le
  magic effectif est `MicroEnabled() ? MAGIC_MICRO : MAGIC_FORB` : en phase FUNDED
  (`MicroEnabled()` faux car `InpPhase!=3` échoue), le trail s'applique bien au magic FORB
  s'il y a un volume signé non nul. Inchangé.
- `PositionMagicOk()`-like check ligne ~346 (`m>=InpMagicBase && m<=InpMagicBase+MAGIC_FORB`),
  filtre par plage de magic dans `OurPositionsExist()` ou équivalent — inchangé, indépendant
  de `FundedOrbOn()`.
- `LogSwapsBilled()`, `Do2258EOD()`, `WriteState()`/`PositionsJson()` — lisent les positions
  ouvertes par magic/symbole, aucun ne consulte `FundedOrbOn()`.

**Conclusion : `FundedOrbOn()` n'est appelée qu'à un seul endroit dans tout le fichier, et
c'est la branche d'ENTRÉE. Le risque identifié dans le brief (bloquer aussi les sorties)
n'existait donc que si j'avais gaté `FundedOrbOn()` elle-même — ce que je n'ai pas fait.**
Toutes les sorties (time-stop, trail, flatten global `FlattenAll` du breaker/kill-file)
restent gouvernées par la présence d'un volume signé sur le magic FORB, jamais par ce flag.

---

## 5. Cas limites envisagés

1. **Fichier absent** (jamais déposé, ou supprimé pour un retour arrière) — `FileOpen`
   renvoie `INVALID_HANDLE` → `false` + `SetError(...)` → `state.json.last_error` peuplé
   → `WriteState(true)` immédiat (SetError l'appelle) → visible par `supervisor.py` au
   prochain cycle (60 s) sans attendre le rapport du soir. C'est le mécanisme de retour
   arrière "immédiat, sans recompilation" du plan §5 — vérifié dans le code, pas supposé.
2. **Fichier vide (0 octet)** — `FileSize(h)==0` détecté explicitement (sans ça, une
   boucle `while(!FileIsEnding(h))` sur fichier vide se termine silencieusement sans
   alerte, ce qui aurait été un fail-open SILENCIEUX, contraire à la règle #2 du brief).
3. **Fichier présent mais aucune ligne parseable** (mauvais format, ex. dates avec des
   tirets au lieu de points, ou binaire corrompu) — distingué de "aucune date ne matche
   aujourd'hui" (cas normal, 361-362 jours/an) via les compteurs `n_lines`/`n_parsed` :
   alerte seulement si des lignes non-vides existent mais qu'AUCUNE n'a été parsée avec
   succès. Une ligne malformée isolée au milieu d'un fichier par ailleurs correct est
   silencieusement ignorée (comportement dégradé mais pas d'alerte-spam) — **c'est un
   choix, pas une évidence, voir §6 doutes**.
4. **Redémarrage EA un jour FOMC, après 16:00 Paris** — `g_fomc_today` est recalculé dans
   `OnInit()`, donc correctement réarmé même si `DayRollover()` n'a pas eu l'occasion de
   tourner ce jour précis (redémarrage même jour). Si le redémarrage survient APRÈS que
   `Do1600Arm()` ait déjà tiré (position déjà ouverte avant le redémarrage), le filtre
   n'a plus d'effet ce jour-là de toute façon — `g_done_1600` est persisté dans
   `ea_state.json` et ne re-déclenche pas `Do1600Arm()`. Comportement correct : le filtre
   ne peut agir qu'AVANT l'entrée, jamais après.
5. **Redémarrage un jour FOMC, avant 16:00 Paris** — `g_fomc_today` recalculé à `OnInit()`
   = `true`, le filtre s'applique normalement à 16:00. OK.
6. **Bascule de compte / démo→challenge un jour FOMC** — même raisonnement que #4/#5 : le
   flag est dérivé du fichier à chaque `OnInit()`, jamais porté par un état de compte.
7. **Ligne dupliquée ou date invalide dans le fichier** (ex. `2026.13.45`) — bornée par
   `m<1||m>12||d<1||d>31` avant d'incrémenter `n_parsed` ; une ligne hors bornes est
   traitée comme "non parseable" pour cette ligne (ni un match, ni comptée dans
   `n_parsed`), donc si TOUTES les lignes sont ainsi invalides, l'alerte `n_lines>0 &&
   n_parsed==0` se déclenche bien.
8. **Retour arrière** — supprimer le fichier suffit (`IsFomcToday()` devient fail-open dès
   le prochain `DayRollover()`, ou immédiatement si le fichier est supprimé avant 16:00
   du jour même, puisque `Do1600Arm()` lit `g_fomc_today` déjà calculé au rollover — donc
   un retrait du fichier APRÈS 00:00 mais AVANT que `DayRollover()` ne tourne le lendemain
   ne change rien au jour courant. **Le retour arrière "immédiat" du plan §5 n'est immédiat
   qu'à partir du rollover suivant, PAS à la seconde où le fichier est supprimé** — nuance
   à corriger dans le plan si l'intention était un effet instantané intra-jour (voir doute
   #2 ci-dessous).

---

## 6. Ce dont je ne suis PAS sûr

1. **Compilation non vérifiée.** Je n'ai pas de MetaEditor sur ce Mac (contrainte déjà
   documentée dans `ftmo_live/README.md`). J'ai utilisé des constructions MQL5 standard
   (`StringSplit`, `StringGetCharacter`, littéraux caractère `'.'`/`'#'`, `FileSize`,
   `StringToInteger`) dont je suis raisonnablement confiant mais que je n'ai **pas pu
   tester**. L'étape 2 du plan ("compiler le .ex5, noter le hash") est non négociable
   avant toute autre étape — je le souligne bien que ce soit déjà écrit dans le plan.
2. **Retour arrière "instantané" vs "au prochain rollover".** Le plan §5 dit "immédiat,
   sans recompilation" pour la suppression du fichier. Mon implémentation lit le fichier
   une fois par jour (à `DayRollover()`), pas à chaque tick, conformément à la règle #4 du
   brief ("une fois par jour, pas à chaque tick"). Ces deux exigences sont en tension :
   si l'incident se produit un jour FOMC APRÈS le rollover (typiquement, si on découvre
   à 15:00 Paris que le filtre bloque à tort — improbable vu la démonstration §3, mais pas
   impossible si une hypothèse s'avère fausse), supprimer le fichier ne débloquera PAS
   l'entrée de 16:00 du jour même, seulement celle du lendemain. Je n'ai pas ajouté de
   relecture à chaud (ex. sur détection FLAT ou sur un signal externe) car ça violerait la
   règle #4 et complexifierait le retour arrière réel (recompilation) qui reste, lui,
   instantané au sens propre. **Je signale la tension, je ne l'ai pas tranchée dans le
   code** — à valider explicitement par l'opérateur : le retour arrière "sans
   recompilation" du plan est correct pour "empêcher le PROCHAIN jour FOMC", pas pour
   "débloquer LE jour FOMC en cours si le filtre s'est déjà armé au rollover".
3. **`MicroEnabled()` vs `FundedOrbOn()` sont mutuellement exclusifs par construction**
   (`Do1600Arm()` est un `if/else if`) — j'ai vérifié que `MicroEnabled()` dépend de
   `InpPhase!=3` et `FundedOrbOn()` de `InpPhase==3`, donc les deux branches ne peuvent
   jamais être vraies simultanément pour le même run. Je le note comme vérifié plutôt que
   supposé, mais je n'ai pas de test unitaire pour le prouver formellement (le dossier
   `ftmo_live/tests/` — 145 tests — n'a pas été étendu par ce livrable, hors périmètre
   explicite de la mission : "aucun backtest").
4. **Format exact attendu par un futur mainteneur.** J'ai choisi de tolérer les
   commentaires `#` et les lignes vides dans `fomc_dates.txt` alors que le pseudo-code du
   plan §3.2(a) ne le prévoyait pas. C'est un ajout de robustesse (le fichier de dates est
   maintenu à la main 1x/an, un commentaire de source est utile) mais ça s'écarte du
   contrat exact décrit dans le plan — à valider que ce n'est pas une sur-ingénierie non
   désirée.
5. **Je n'ai pas vérifié le comportement de `FileOpen`/`FileReadString` sous Wine** (le
   MT5 du VPS tourne sous wine en screen, cf. `ftmo_live/README.md` §Install VPS). Le
   pattern `FileOpen(...,FILE_SHARE_READ)` est identique à celui déjà utilisé ailleurs
   dans le fichier (`swaps_billed.csv`, `ea_state.json`) donc je m'appuie sur un précédent
   qui fonctionne déjà en production — mais je ne l'ai pas re-testé moi-même.
6. **Le test de non-régression de l'étape 3 du plan** (rejouer 2026-08-17→2026-09-11 avec
   et sans le fichier, fills identiques attendus) n'a pas été exécuté par moi — explicitement
   hors périmètre ("aucun backtest"). Je note juste que la période n'a aucune date FOMC,
   donc `g_fomc_today` devrait rester `false` toute la période même AVEC le fichier déposé,
   ce qui est cohérent avec le critère d'arrêt du plan §6.

---

## 7. Ce qui n'a pas changé (vérifié, pas supposé)

`spec_v22.yaml`, les pins, `SPEC_SHA256` (référencé mais jamais réécrit), `FU_ORB_RISK`
(lu, jamais modifié), la logique de sizing (`CapQuantizeTrade`, `LegLevCap`, etc.), les
sleeves overnight (`Do1735()`, `Do2205Rebalance()`), le micro-ORB (`MicroEnabled()`,
`Do1600Arm()` branche micro, `MicroManage()`), tous les invariants de risque
(`InvariantCheckM5()`, `BreakerLine()`, `StaticFloor()`, `DailyFloor()`), `brain.py`
(fichier non touché, non lu même). Vérifié par `git diff --stat -- ftmo_live/` (vide) et
par relecture ligne à ligne du diff produit (141 lignes, dont l'écrasante majorité sont
des lignes de commentaire de documentation ou des lignes de contexte du diff).
