# Scoring macro — synthèse des 5 dossiers et plan de travail

**2026-09-06.** Programme lancé sur la question « construire un système de scoring macro
institutional grade ». Cinq dossiers indépendants : littérature académique (01), pratique des desks
(02), données point-in-time (03), économétrie (04), porte de faisabilité (05). **Δn_tests = 0** —
aucune donnée téléchargée, aucun backtest lancé. Phase de conception uniquement.

**Verdict d'ensemble : le score macro cross-sectionnel tenu est REJETÉ avant backtest. La famille
événementielle intraday-flat est retenue et devient le projet.**

---

## 1. Le résultat central, et il tient en un tableau

La loi fondamentale `IR = TC × IC × √BR` appliquée avec une breadth honnêtement comptée :

| TC | IC | BR (paris indép./an) | Sharpe brut | |
|---|---|---|---|---|
| 0,30 | 0,04 | 6 | **0,029** | scénario central réaliste |
| 0,40 | 0,08 | 15 | **0,124** | le plus optimiste défendable |
| 0,40 | 0,08 | **240** | **0,496** | ⚠ breadth FAUSSE (20 instruments × 12 mois) |

Et en sens inverse, pour franchir RESEARCH_PASS (Sharpe 0,7) :

| BR | TC | IC requis | crédible ? |
|---|---|---|---|
| 6 | 0,35 | **0,82** | non — aucun signal macro documenté n'en approche |
| 15 | 0,40 | **0,45** | non — 5 à 20× les IC macro académiques |
| 240 (faux) | 0,40 | 0,11 | bord extrême, et seulement en trichant sur BR |

**L'IC macro documenté dans la littérature vaut 0,02 à 0,08.** L'écart au requis est d'un facteur 6
à 40. Ce n'est pas un projet à optimiser, c'est un projet dont l'arithmétique ne ferme pas.

La ligne à 240 est la leçon du programme : **compter la breadth naïvement fabrique un Sharpe de 0,50
qui a l'air presque investissable**, quand la même hypothèse honnêtement comptée donne 0,124. La
breadth est l'endroit où un projet se ment à lui-même avant d'avoir écrit une ligne de code.

## 2. D'où vient la breadth réelle de 2-15 paris/an

Deux effondrements successifs, multiplicatifs :

**Effondrement transversal.** Le cycle macro est synchronisé entre pays, et le facteur dollar est
présent dans presque toutes les paires FX. Vingt instruments ne donnent pas vingt paris, mais
environ **2 à 5**.

**Effondrement temporel.** Un score macro porte un noyau de décroissance. Pour un noyau exponentiel
de demi-vie τ, le nombre de paris effectifs sur T jours vaut `T·(1−ρ)/(1+ρ)` avec `ρ = 2^(−1/τ)` :

| Demi-vie | Autocorrélation | Paris effectifs / 1 000 jours |
|---|---|---|
| 1 jour | 0,50 | ~333 |
| 5 jours | 0,87 | ~67 |
| 20 jours | 0,966 | **~17** |
| 45 jours *(la demi-vie de l'indice de surprise Citi)* | 0,985 | **~8** |
| 60 jours | 0,989 | **~6** |

Croisement des dossiers 02 et 04 : **l'indice de surprise le plus utilisé de la profession porte,
par construction, une mémoire de 45 jours** — soit environ huit paris indépendants pour quatre ans
de données. Ce n'est pas un défaut de l'indice, qui décrit une conjoncture et ne prétend pas
déclencher des trades. Mais ça borne ce qu'on peut espérer en s'en inspirant.

**Combiné : 2 à 15 paris par an, valeur centrale 5-8.** Le scénario à 20 exigerait de supposer
*simultanément* une faible corrélation inter-pays et un noyau rapide — deux hypothèses optimistes
qui se contredisent.

## 3. Ce que font réellement les desks (dossier 02)

**Il n'existe quasiment aucune trace publique d'un z-score composite sur PIB/inflation/PMI servant
seul de signal directionnel chez un gérant systématique sérieux.** Quatre objets distincts portent
le nom de « score macro » :

1. un narratif causal codifié en règles conditionnelles — Bridgewater ; le cadre est public, les
   règles et les seuils ne le sont pas ;
2. un indice de conjoncture vendu comme produit de recherche, jamais comme position — Citi, Goldman ;
3. **une brique parmi cinq ou six** dans un modèle multi-facteurs, jamais isolée — CFM ; et 25 % du
   risque seulement chez Winton ;
4. du trend-following sur instruments macro, sans rien de fondamental malgré le nom — le « macro
   momentum » d'AQR, ce qui lève la contradiction apparente avec leur scepticisme publié sur le
   timing macro : ce ne sont pas les mêmes objets.

Sur la question *signal ou overlay* : le motif dominant est un **vote pondéré à poids fixes entre
clusters**, jamais un overlay multiplicatif sur un book construit ailleurs. Convergent avec notre
propre falsification d'overlay de régime (L54).

**Réplicable en solo** : une approximation de l'indice de surprise (méthode Scotti, Fed IFDP 1093 —
trouvée indépendamment par les dossiers 02 et 03), un cluster macro en profondeur à poids fixes, du
macro-momentum type trend. **Hors de portée** : la largeur multi-cluster, l'accès aux swaps OTC, les
consensus propriétaires en temps réel, le mélange systématique/discrétionnaire.

## 4. Ce que la littérature permet de rayer (dossier 01)

- **Facteurs macro obligataires** (Cochrane-Piazzesi, Ludvigson-Ng) : **invalidés hors échantillon
  par Bauer & Hamilton (RFS 2018)** une fois corrigée la distorsion de petit échantillon. Ne plus
  citer sans ce caveat.
- **Fondamentaux en FX** au niveau standard : morts depuis Meese-Rogoff (1983), conclusion tenue
  quarante ans après, explication théorique par Engel-West (2005). Pas un axe.
- **Carry cross-asset** (KMPV, JFE 2018, Sharpe diversifié 1,1) : seul résultat solide — mais nous
  avons **déjà un verdict interne** (`Forex/research/active/g2d_carry_cross_asset/report_v1.md`) :
  conditionnel oui sur futures, non sur CFD/perp retail, et $50-100k de capital requis pour la
  granularité. Rien de neuf à €13k.
- **Le piège régime-variance/moyenne est un théorème**, pas notre accident de jeu de données :
  Ang & Timmermann (2012). Toute variante future devra démontrer que le régime prédit la moyenne
  *dans le même sens* que la variance, sinon c'est de la parité de risque déguisée.
- **Prime d'annonce** (Savor & Wilson, JFQA 2013, 51 ans) : le résultat le plus robuste et
  gratuitement réplicable, plafonné à 30-50 paris/an. → voir §7, c'est là que va le projet.

**Motif transversal du dossier 01** : l'erreur de breadth est **endémique à la littérature
elle-même**, y compris en peer-review au JFE, à la RFS et à l'AER. Le modèle amateur qui a lancé
cette enquête ne l'avait pas inventée, il en avait hérité.

## 5. Le véhicule tue le projet une deuxième fois (dossier 05)

Un score macro réagit à des publications mensuelles ou trimestrielles : sa fréquence naturelle de
rebalancement est **mensuelle**, donc **tenue**.

| Véhicule | Coût RT | Portage | Granularité | Fréquences viables |
|---|---|---|---|---|
| CFD FTMO | ~2,48 bps mesuré | asymétrique ; **~6,75 %/an agrégé** (L36) | 0,01 lot | **événementiel / intraday-flat seulement** |
| CFD Eightcap | ~0,75 bps EURUSD | **non mesuré chez nous** — à vérifier, jamais supposer | 0,01 lot | FX seul ⇒ réduit la breadth à un facteur USD |
| Futures IBKR | ~0,4 bps | pas de swap | **1 lot entier** | mensuel/trimestriel, coût quasi nul |

- Le **CFD meurt au portage** : L36 a déjà mesuré que ~6,75 %/an de swap annule une prime de trend
  de ~8 %/an. Un score macro tenu y meurt exactement au même endroit.
- Les **futures meurent à la granularité** : respecter N≥30 sur des contrats à lot entier est
  arithmétiquement impossible à €13k, sauf à se concentrer sur quelques minis — ce qui, par L57,
  dégrade le skew et ouvre une queue mono-séance.

**Aucun des trois véhicules ne supporte une tenue mensuelle sur N≥30 à capital personnel.** Ce
verdict est indépendant de la qualité du signal.

## 6. Décision

**On ne construit pas de score macro cross-sectionnel tenu.** Le raisonnement s'effondre en trois
endroits indépendants, chacun suffisant seul : l'arithmétique de breadth (§1-2), le véhicule (§5),
et le risque élevé de bêta déguisé pour tout score qui achète le risque quand la macro va bien.

Le point de rupture principal est la **breadth**. Tout le reste est secondaire tant que l'IC requis
reste à 5-10× l'IC macro documenté.

---

# 7. LE PROJET RETENU — famille événementielle intraday-flat

## 7.1 Pourquoi cette forme survit là où l'autre meurt

Un signal ancré à une **publication macro datée**, tenu sur une fenêtre courte :

- **La breadth est petite par construction et honnête** : le nombre de paris est le nombre de
  publications par an (~12 pour le CPI), pas un univers gonflé. Aucune illusion de N≥30, aucune
  tentation d'inflation.
- **Pas de portage** : fenêtre courte ⇒ L36 ne s'applique pas ⇒ le CFD redevient viable, et c'est
  précisément le régime intraday-flat qui l'épargne.
- **Moins susceptible d'être du bêta déguisé** qu'un score qui pondère en continu des actifs risqués
  selon le cycle.

## 7.2 Les deux candidats déjà vivants dans le dépôt

**(a) XAUUSD la veille du CPI** — `t = 3,86`, ratio brut/coût **20,7**, DSR 0,637, N = 65 trades.
Le ratio de 20,7 est à comparer au seuil L43 de 1,5 et au plafond historique de 0,36 jamais dépassé
en FX intraday. C'est le meilleur candidat du dépôt, et il est déjà en recherche active.

**(b) Drift pré-FOMC** — classé NO-GO, mais le motif du kill est **la puissance, pas le mécanisme** :
l'effet est mesuré réel sur huit indices actions, et le rejet portait sur l'absence de support
bilatéral (les colonnes censées tester la jambe inverse étaient des miroirs exacts qui ne testaient
rien). Notre politique de ré-ouverture le nomme explicitement comme rouvrable, avec la cause :
**le fichier d'entrée n'apportait que 49 événements sur les 102 disponibles**. Angle nouveau et
légitime : doubler l'échantillon et construire un vrai test bilatéral.

## 7.3 Plan de travail

### Phase 0 — pré-enregistrement (1 jour, aucune donnée)

Écrire AVANT de toucher aux données, et geler par commit :
- la liste close des événements à tester et l'ordre de test ;
- pour chacun : instrument, fenêtre d'entrée et de sortie, sens attendu et **son fondement
  économique** ;
- la demi-vie du noyau, choisie sur un fondement économique et non par balayage de grille — c'est
  le paramètre le plus dangereux de la construction ;
- le nombre de lags HAC, **dimensionné sur la demi-vie retenue et non le lag-6 par défaut** (voir
  §7.5) ;
- les six critères d'arrêt du dossier 05, repris tels quels.

### Phase 1 — socle de données point-in-time (~1 semaine)

Construire une base d'événements horodatée à l'heure de publication réelle. Trois sources, dans cet
ordre :

1. **ALFRED** via `fredapi` (clé gratuite) — millésimes série par série, champ `realtime_start`.
2. **Archives de millésimes FRED-MD / FRED-QD** — panel académique standard, déjà en millésimes
   (confirmé par consultation directe ; la croyance courante qu'ils n'existent qu'en version
   courante est fausse). Épargne une reconstruction série par série.
3. **Calendriers officiels BLS et BEA** — pour l'horodatage exact de publication, recoupé avec
   `realtime_start`.

Ampleur du problème à garder en tête : le PIB américain est révisé de **+0,45 point en moyenne**, et
un trimestre a varié de **4,9 % à 9,6 %** selon le millésime. L'emploi a connu une révision de
référence de ~0,6 % du niveau en 2025. **L'inflation fait exception** — révisions sous le point, sauf
fin 2022. On commence donc par les séries les moins révisées.

Lacunes connues, à ne pas découvrir en route : la base temps réel de l'OCDE est **figée en 1998** ;
la zone euro est nettement moins bien servie que les États-Unis ; **aucune source OIS gratuite**
n'a été identifiée ; les calendriers d'Investing.com et FXStreet n'ont **aucune API officielle**
(scraping fragile, à éviter).

### Phase 2 — mesure, un événement à la fois

Pour chaque événement de la liste gelée, dans l'ordre gelé :

1. **Test de la forme inconditionnelle d'abord** — l'espérance de la forme de trade hors événement.
   C'est la baseline contre laquelle le placebo devra lui-même être validé (L58).
2. **Étude d'événement** en rendements en excès, avec HAC dimensionné.
3. **Placebo apparié** — même structure d'autocorrélation, même calendrier. Si la baseline du
   placebo dévie de plus de ~20 % de l'espérance inconditionnelle, **le placebo est biaisé** : le
   reconcevoir, ne jamais conclure sur un placebo compromis.
4. **Test bilatéral réel** — pas un miroir `-side_long`, qui ne teste rien (c'est l'erreur qui a
   invalidé le support bilatéral de L42).
5. **Coût mesuré, jamais supposé**, sur le véhicule visé, avec le pré-flight `brut/coût_p95 ≥ 1,5`.

### Phase 3 — véhicule et décision

Matrice de véhicule **avant** toute extrapolation de performance (L53). Pour un signal
intraday-flat : FTMO redevient éligible puisque le portage ne s'applique pas ; Eightcap est à
mesurer et non à supposer ; IBKR reste le moins cher si l'instrument existe en futures.

### Phase 4 — ce qu'on ne fait qu'après

L'overlay de sizing sur un book déjà validé reste envisageable mais **non prioritaire et à faible
probabilité**, sous la condition stricte de L54. À tester après épuisement de la piste
événementielle, jamais comme point de départ.

## 7.4 Code à mettre en place

Modules à écrire, dans l'ordre, sous `Multi_Asset/research/active/macro_events_2026-09/code/` :

| Module | Rôle |
|---|---|
| `vintage_loader.py` | Accès ALFRED/FRED-MD en millésimes. **Contrat non négociable : toute requête prend une date d'observation et ne peut retourner que ce qui était publié à cette date.** Aucune API ne doit permettre d'obtenir la série révisée par accident. |
| `event_calendar.py` | Calendrier d'événements horodatés à l'heure de publication, construit sur BLS/BEA et recoupé avec `realtime_start`. Fuseau de l'échange avec DST (L56), jamais UTC calendaire. |
| `surprise.py` | Construction du choc : réalisé − consensus, normalisé. Implémenter la méthode Scotti comme référence documentée. |
| `decay.py` | Noyaux de décroissance **et calcul de `N_eff`**. Doit refuser de rendre un t-stat sans rendre le `N_eff` correspondant. |
| `event_study.py` | Étude d'événement, HAC dimensionné sur la demi-vie, rendements en excès. |
| `placebo.py` | Placebo apparié **avec validation de sa propre baseline** contre l'espérance inconditionnelle. |
| `cost_probe.py` | Coût mesuré par instrument et par véhicule, avec le pré-flight `brut/coût_p95`. |

Réutilisable en l'état : `Portfolio/validation/` (multi-test, CPCV), `Portfolio/risk/`, et
`fomc_events.csv` (2004-2026, déjà présent).

## 7.5 Dérogation méthodologique à acter

Le **HAC lag-6 est une hard rule du dépôt**, calibrée sur des signaux à décroissance rapide. Le
dossier 04 établit qu'elle devient **mal spécifiée — et non simplement conservatrice** — dès que la
demi-vie du noyau dépasse quelques jours : corriger l'autocorrélation jusqu'à 6 jours de décalage
sur un processus dont la mémoire s'étend sur 45 n'est pas un test prudent, c'est un test faux.

Sur ce programme, les lags seront dimensionnés sur la demi-vie retenue. **À documenter comme une
dérogation motivée**, pas à appliquer silencieusement.

Test de falsification associé : comparer noyau rapide et noyau lent en walk-forward, **chacun avec
son propre dimensionnement HAC**. Si le lent ne gagne qu'à lag-6 fixe, c'est un artefact de
spécification et on garde le rapide.

## 7.6 Leçons candidates issues de ce programme

Non numérotées — à graver à la réconciliation, jamais en session.

- **Candidate A** : la breadth est le point où un projet se ment le plus tôt. Compter naïvement
  fabrique ici un Sharpe de 0,496 contre 0,124 honnêtement compté, soit un facteur 4, **avant tout
  backtest**. Corollaire : exiger le calcul de `BR` dans le pré-enregistrement, au même titre que le
  sens du signal.
- **Candidate B** : le HAC à lag fixe est mal spécifié, pas conservateur, dès que la demi-vie du
  signal dépasse le nombre de lags. Rapporter `N_eff` à côté de tout t-stat.
- **Candidate C** : l'erreur de breadth est endémique à la littérature peer-reviewed elle-même — un
  résultat publié au JFE/RFS/AER n'est pas une garantie sur ce point précis, et doit être recompté
  avant d'être cité comme fondation.

---

## Sources

Rapports complets : `01_academique/` (654 l.), `02_desks/` (204 l.), `03_donnees/`,
`04_econometrie/` (580 l.), `05_execution/` (392 l.).

⚠ Le dossier 05 signale n'avoir pas pu relire `CLAUDE.md` ni `_meta/lessons_registry.md` en session
(blocage de permission OS sur l'arborescence, persistant sur 7 tentatives). Son rapport s'appuie sur
le texte injecté en contexte et sur les citations verbatim fournies dans sa mission. **Les
références aux leçons L36/L38/L43/L49/L53/L54/L55/L57/L58/L64/L67 dans ce dossier sont à
re-vérifier contre le registre** une fois l'accès rétabli, avant toute citation externe.
