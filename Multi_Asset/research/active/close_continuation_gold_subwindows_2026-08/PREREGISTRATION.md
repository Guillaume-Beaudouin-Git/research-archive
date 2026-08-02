# PRÉ-INSCRIPTION — deux tests indépendants

**Écrite le 2026-08-02, AVANT toute lecture de donnée dans ce worktree.**
Branche `claude/close-continuation-gold-subwindows`, base `origin/main`.
Interpréteur : `/usr/bin/python3` explicitement.

Ce fichier fige les hypothèses, les specs et les **règles de mort chiffrées** des deux tests.
Il est commité **avant** l'exécution du moindre script de mesure. Tout écart ultérieur est
signalé comme tel dans `RESULTS.md`.

Les deux tests sont **indépendants** : compteurs d'essais séparés, verdicts séparés, aucune
réutilisation de résultat de l'un pour défendre l'autre.

---

# TEST A — la CONTINUATION de la pression de clôture sur indices US

## A.0 Pourquoi une pré-inscription, alors que le signe est déjà connu

`mr_timezone_repair_2026-08` cherchait un **fade** de la pression de clôture (mécanisme
Baltussen-Da-Soebhag) et a trouvé que le fade **perd** significativement : US100 −3.29 bps
(t −2.77), US500 −1.49 (t −2.88), US30 −2.18 (t −2.36), sur les **deux jambes** et **après**
retrait de l'inconditionnel. Autrement dit : la pression de clôture **continue**.

L'agent a refusé de revendiquer ce signe, correctement : il a été **trouvé, pas pré-enregistré**.

⇒ Ce document est la pré-inscription manquante. Elle ne peut évidemment pas rendre l'échantillon
de découverte innocent. Elle sert à deux choses, et à rien d'autre :
1. **Fixer d'avance ce qui compterait comme une confirmation**, pour que la confirmation ne
   puisse pas être fabriquée après coup en choisissant la cellule.
2. **Déplacer la charge de la preuve hors de l'échantillon de découverte** — vers un test de
   **mécanisme** (gradient), un **hors-échantillon temporel**, un **placebo d'ancre**, et un
   **test d'exécutabilité**. Une re-confirmation sur l'échantillon qui a révélé le signe
   ne vaut rien et n'est pas comptée comme preuve.

## A.1 Hypothèse, formulée comme un mécanisme (pas comme un signe)

> **H_A.** Le rendement des dernières minutes de la séance cash d'un indice US **CONTINUE**
> dans la fenêtre post-clôture, et l'ampleur de cette continuation est **CROISSANTE dans
> l'intensité** de la pression de clôture.

Le second membre est la partie falsifiable qui distingue une vraie continuation d'un artefact.
Si le rendement post-clôture conditionnel ne dépend **pas** de l'intensité du signal, alors ce
n'est pas de la continuation de pression : c'est un **drift déguisé** capté par le
conditionnement, exactement le piège L58/L49.

**A priori explicite, écrit avant mesure :** l'effet, s'il existe, est **petit** (quelques bps),
il est **microstructurel** (post-clôture cash, liquidité mince), et sa demi-vie se compte
**en minutes** — comme celle de son symétrique GER40. Je m'attends donc à ce que le test
d'exécutabilité (A.5-K3) soit **le plus liant**. Probabilité subjective de PASS avant mesure :
**faible, < 20 %**.

## A.2 Spec figée (identique à `close_window.py`, aucun paramètre ré-optimisé)

| élément | valeur |
|---|---|
| Instruments | **US500, US100, US30** (échantillon de découverte) + **GER40** (indépendant, a priori de signe OPPOSÉ) |
| Données | `data/deep_history_utc/{US500,US100,US30,GER40}_M1.csv`, vrai UTC, **lecture seule** depuis le répertoire principal |
| Horloge | **horloge d'échange avec son DST** (L56) : `America/New_York` (US), `Europe/Berlin` (GER40) |
| Échantillon | **2018-2026** pour les US (avant 2018 le CFD ne cote pas après la clôture cash — contrainte de donnée, pas résultat), 2014-2026 pour GER40 |
| Signal | rendement des **K dernières minutes** de la séance cash, K ∈ {15, 30, 60}, **z-scoré** sur 250 séances glissantes **strictement passées** |
| Jambes (L25) | **DISJOINTES** : `z > +θ` → **LONG** (continuation haussière), `z < −θ` → **SHORT**. θ ∈ {0.5, 1.0, 1.5}. Aucune jambe obtenue par négation de l'autre |
| Entrée (L59) | **OPEN de la barre `close+1`** — une barre pleine après la barre de signal |
| Sortie (L59) | **OPEN de la barre `close+11`** (tenue 10 min). Aucun stop, aucun bracket, aucun remplissage à une barrière ⇒ le mode de défaillance L59 est structurellement absent |
| Tenue | **10 min**, imposée par la donnée (couverture des barres post-clôture : +10 min 0.96, +15 min 0.56) |
| Gate | **GROSS, `cost_rt = 0`**. Coût appliqué en aval seulement : **1.8 bps RT** indices (`cost_denominator_2026-07/COST_AUDIT.md`), **jamais** la colonne `spread` |
| Baseline (L58) | espérance **INCONDITIONNELLE de la même forme de trade sur la même fenêtre** ; bootstrap de la différence ré-échantillonnant le panneau **conjointement** |
| Inférence | t **HAC(6)** ; bootstrap **par blocs circulaires** (Politis-Romano, L = 5 séances, 2 000 tirages). **Jamais iid** |

**Aucune modification de spec n'est autorisée en cours de test.** Budget : **0 modification**.

## A.3 Ce qui NE compte PAS comme preuve

- Une re-confirmation des cellules θ/K exactes de `mr_timezone_repair` sur 2018-2026 entier.
  Elle sera rapportée pour traçabilité et **explicitement exclue** du faisceau de preuve.
- Un maximum sur grille. Toute valeur « meilleure cellule » est rapportée comme **frontière**,
  jamais comme estimation ponctuelle d'une politique pré-enregistrée.

## A.4 Les quatre sources de puissance, décidées d'avance

1. **Gradient (mécanisme).** Régression du rendement post-clôture sur `z` **sur toutes les
   séances, sans seuil** ; et moyennes par **quintile de z**. C'est le test central : il
   n'utilise aucun seuil, donc il n'a aucun degré de liberté à exploiter.
2. **Hors-échantillon temporel.** Coupure **2018-2021 / 2022-2026**, fixée maintenant.
3. **Placebo d'ancre.** La même forme de trade ancrée toutes les 30 minutes de la séance
   (~13-14 ancres intra-séance par instrument, θ = 1.0). Si la continuation existe à toutes
   les ancres, ce n'est pas un effet de **clôture** : c'est du momentum intraday générique.
4. **Exécutabilité.** Entrée retardée de 1, 2, 3, 5 minutes, sortie maintenue à `close+11`
   puis à durée constante. C'est le test qui a tué GER40 ; il coûte zéro essai supplémentaire.

## A.5 Règles de mort — CHIFFRÉES, écrites avant la donnée

| # | Test | Condition de MORT |
|---|---|---|
| **K1** | **Gradient** — pente OLS de `r_post` sur `z`, HAC(6), pooled US, sans seuil | pente **≤ 0** **OU** `t_pente < 2.0`. En outre : si la cellule à seuil est significative alors que la pente est plate (t < 2.0), le verdict est **DRIFT DÉGUISÉ → REJECTED** en tant que mécanisme |
| **K2** | **Monotonicité** — moyenne de `r_post` par quintile de z | l'écart Q5 − Q1 n'est pas du signe de la continuation (**> 0**), **OU** moins de **3 transitions sur 4** dans le bon sens |
| **K3** | **Exécutabilité** — two-sided à entrée retardée de **5 min** | `m_two_sided < 1.5 × 1.8 = 2.7 bps` **OU** `t < 1.5` |
| **K4** | **Placebo d'ancre** — rang de l'ancre de clôture parmi toutes les ancres 30 min | l'ancre de clôture n'est **pas dans le top 20 %** des ancres (sur `m_both`), **OU** la moyenne des ancres non-clôture est elle-même **> 0 avec t > 2.0** (⇒ momentum générique, pas effet de clôture) |
| **K5** | **L58** — excès de chaque jambe sur l'inconditionnel de la même forme | l'une des deux jambes a un excès du **mauvais signe**, **OU** les deux ont `p > 0.10` |
| **K6** | **Hors-échantillon** — sous-période 2022-2026 | signe **inversé** par rapport à 2018-2021, **OU** `t_both < 1.5` sur 2022-2026 |
| **K7** | **Hygiène (L60)** — barres à fourchette nulle dans la fenêtre d'entrée/sortie | **> 5 %** sur une année quelconque de l'échantillon retenu ⇒ la série est disqualifiée pour cet instrument |

**Grille de verdict :**
- **PASS** : aucune règle de mort déclenchée **ET** net après coût (1.8 bps RT) positif avec
  `t > 2.0` **ET** p(pass)/durée rapportés contre les barrières FTMO.
- **REJECTED** : K1 ou K2 ou K4 déclenchée (le **mécanisme** est faux), ou K3 déclenchée (l'effet
  existe mais n'est pas prenable — kill de type **exécution**, rouvrable seulement sur véhicule).
- **UNDERPOWERED** : toutes les statistiques du bon signe mais IC contenant zéro / t entre 1.5 et
  2.0 sur les tests hors-découverte. **UNDERPOWERED ≠ PASS.**

## A.6 Comptage

Compteur **N1 local A**, indépendant de B. Les diagnostics purement descriptifs (L60, couverture
des barres, profils horaires L56, part de gap) sont **N0** et ne sont pas comptés : ils ne
mesurent aucune performance.

---

# TEST B — décomposition en sous-fenêtres de l'heure de réouverture de l'or

## B.0 Point de départ, et pourquoi ce test précis

Le candidat or overnight **E002** est **UNDERPOWERED, famille ouverte**
(`overnight_sleeve_reopen_2026-08`) : p(pass) 0.593, IC90 **[0.321 ; 0.817]**, DSR post-2021
**0.284**, coût = **49 %** du signal post-2021.

Deux faits établis ailleurs cadrent ce test :
- **L56** : l'effet « overnight or » n'est pas de la demande asiatique — il tient **dans la
  première heure après la réouverture Globex 18:00 ET**, ancrée à l'horloge d'échange.
- **L56 corollaire** : une barre **H1** agrège le **gap de halt non tradable** — mesuré à
  **17.5 %** sur l'or (35.5 % WTI, 59.3 % argent). Personne n'est allé plus fin que H1.

Et il existe un précédent immédiat : sur GER40, la même décomposition a tué un candidat qui
semblait solide (gross +3.52 bps, t 3.68, 12/13 ans positifs, 1ᵉʳ sur 29 au placebo) — parce que
**60 % de l'effet vivait dans les 5 minutes de l'auction** et qu'entrer 5 min plus tard ne
laissait que 0.56 bps, t 1.00.

## B.1 Hypothèses, écrites avant mesure

> **H_B1 (localisation).** Le rendement de la fenêtre de réouverture de l'or n'est pas uniforme :
> il est concentré sur les premières minutes après 18:00 ET.
>
> **H_B2 (exécutabilité) — celle qui décide.** La part du rendement de fenêtre qui survit à un
> retard d'entrée de **5 à 10 minutes** est suffisante pour couvrir le coût mesuré.
>
> **H_B3 (gap).** Au-delà des 17.5 % déjà mesurés en H1, une part supplémentaire du rendement
> attribué à la fenêtre est du **gap non tradable** ou du **prix figé** (L60).

**A priori explicite :** l'entrée à la réouverture après une pause d'une heure est **le pire
moment de la journée pour le spread** (`COST_AUDIT §7`, réserve non résolue). Un retard
d'entrée réduit ce spread ; donc **si l'effet survit au retard, le candidat se renforce
doublement** (numérateur préservé + dénominateur réduit). Symétriquement, s'il s'effondre comme
GER40, il passe de **UNDERPOWERED à REJECTED**. Probabilité subjective avant mesure de
« survit à 5 min » : **~50 %** — c'est un vrai test, pas une formalité.

## B.2 Spec figée

| élément | valeur |
|---|---|
| Instrument | **XAUUSD** (véhicule CFD FTMO du candidat E002). Contrôles : XAGUSD, USOIL |
| Données | `data/deep_history_utc/XAUUSD_M1.csv`, **M1 BRUT** |
| ⚠ Winsorisation | **INTERDITE.** `overnight_futures_2026-07/code/step3_performance.py:47` winsorise à 0.5/99.5 **dans le constructeur** (pire séance −6.77 % → −1.65 %). Toute série est **reconstruite depuis le M1 brut**. La version winsorisée est calculée **uniquement** pour chiffrer l'écart |
| Horloge | **`America/New_York` avec DST** (L56). Réouverture Globex = **18:00 ET** |
| Fenêtre héritée | 8 h après réouverture (18:00 → 02:00 ET) — **non modifiée** |
| Sous-fenêtres | profil **minute par minute** de la réouverture à +60 min, puis cumul jusqu'à la fin de fenêtre |
| Décomposition | `gap` = log(1ᵉʳ print ≥ 18:00 / dernier print avant le halt) ; `capturable(d→T)` = log(prix à T / 1ᵉʳ print ≥ 18:00 + d min) |
| Retards testés | d ∈ **{0, 1, 2, 3, 5, 10, 15, 20, 30}** minutes, **fixés maintenant** |
| Sorties | (i) fin de fenêtre **8 h** (durée variable, comparable au sleeve déployé) ; (ii) **durée constante** (T = entrée + 8 h) — les deux rapportées, L59 |
| Échantillons | **full** (2007→) et **post-2021** (échantillon décisionnel de E002) |
| Gate | **GROSS d'abord** (`cost_rt = 0`). Coûts en aval : XAUUSD **1.84 bps** au centre / **3.88 bps** en queue provisionnée ; swap or **ASYMÉTRIQUE** −2.065 long / −0.335 short (2020+), **pas** −2.9 symétrique |
| Inférence | t **HAC(6)**, bootstrap **par blocs** (Politis-Romano). Jamais iid |

## B.3 Règles de mort — CHIFFRÉES, écrites avant la donnée

| # | Test | Condition de MORT / de renforcement |
|---|---|---|
| **KB1** | **Exécutabilité à 5 min** (le test qui a tué GER40) | **MORT** si le rendement moyen de fenêtre à entrée retardée de 5 min **post-2021** tombe sous **1.5 × 1.84 = 2.76 bps** **OU** si `t_HAC < 1.5` |
| **KB2** | **Exécutabilité à 10 min** | **MORT** si sous **2.76 bps** post-2021. Si KB1 **et** KB2 passent, le candidat est **RENFORCÉ** (numérateur intact + spread réduit) |
| **KB3** | **Part de gap** | Si le `gap` non tradable représente **> 40 %** du rendement de fenêtre gap-inclus, la mesure H1 héritée est déclarée **non transférable** et tout chiffre H1 du dossier est retiré |
| **KB4** | **L60 — prix figés** | **MORT** si > **10 %** des barres M1 de la fenêtre d'entrée ont `high == low == close` sur une année quelconque post-2021, **ou** si la part de barres à fourchette nulle dans les 5 premières minutes dépasse **25 %** |
| **KB5** | **Concentration** | Si retirer les **5 % de meilleures séances** fait passer le rendement moyen sous le coût de 1.84 bps, la sleeve est déclarée **portée par la queue** (rapporté, non éliminatoire seul — mais éliminatoire combiné à KB1) |
| **KB6** | **L56 — ancrage d'horloge** | Contrôle : corrélation du profil **minute** hiver~été en ET vs en UTC. Si l'ancrage ET n'est pas nettement supérieur, la localisation minute n'est **pas interprétable** et la décomposition est déclarée inconclusive |

**Grille de verdict :**
- **RENFORCÉ (reste UNDERPOWERED, famille ouverte)** : KB1 et KB2 passent, KB3/KB4 non déclenchées.
  ⇒ recommandation : mesurer le spread réel à l'heure décalée, puis re-décider.
- **REJECTED** : KB1 déclenchée (effet non prenable à l'exécution) — kill de type **exécution**,
  rouvrable seulement sur véhicule/donnée nouvelle.
- **INCONCLUSIF** : KB6 déclenchée.

## B.4 Comptage

Compteur **N1 local B**, séparé de A. La décomposition en sous-fenêtres est une **mesure de
localisation d'un effet déjà mesuré**, pas une nouvelle hypothèse de rendement : les retards
d'entrée sont comptés comme **une famille d'essais** (9 retards × 2 échantillons), pas comme
9 stratégies indépendantes. Les diagnostics L60 / L56 / gap sont **N0**.

---

## Discipline commune

- Aucun chemin live touché : `ftmo_live/`, `strategies/`, `Futures/live/`, `Portfolio/`,
  `.github/`, `*.mq5`. `Portfolio/admission/` peut être **importé**, jamais modifié.
- **Aucun blob de données dans git.** Les caches sont écrits dans le scratchpad.
- Vocabulaire de verdict : **PASS / REJECTED / UNDERPOWERED**. Jamais « prometteur ».
- Les deux tests ne se contaminent pas : un résultat de A ne peut pas servir d'argument dans B,
  et réciproquement.
