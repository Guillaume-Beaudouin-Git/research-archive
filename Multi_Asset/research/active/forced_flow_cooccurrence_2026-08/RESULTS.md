# RÉSULTATS — Co-occurrence de flux forcés à dose calendaire

**Verdict global : REJECTED.** La courbe de dose est plate une fois retirés les deux confondants
que le protocole a lui-même exposés. Le seul effet survivant n'est pas de la co-occurrence : c'est
**la fin de trimestre, un flux unique que ma propre construction de dose comptait deux fois** — et
il vaut **6 bps/an** au coût central, **0.7 bps/an** au coût de queue.

Pré-enregistrement : `PREREGISTRATION.md`, committé `70420ee9` avant toute lecture de prix.
Données : `data/deep_history_utc/`, 19 instruments, **59 687 jours-instrument**, 2007-02-26 →
2026-06-05. Interpréteur `/usr/bin/python3` (pandas 2.2.3).

---

## 1. Ce que le test a établi de neuf, indépendamment du verdict

**Le contrôle L54 s'inverse complètement.** C'était le point du dossier : une dose de PRIX
(`|R_day|`) prédisait la variance 50 à 250× plus que la moyenne. Une dose **calendaire**, connue
des semaines à l'avance, donne :

| dose | R²_moyenne | R²_variance | **ratio var/moyenne** |
|---|--:|--:|--:|
| dose complète, bps | 7.71 × 10⁻⁵ | 1.17 × 10⁻⁴ | **1.52** |
| dose complète, unités σ | 8.59 × 10⁻⁵ | 1.41 × 10⁻⁴ | **1.64** |
| dose sans le jour-de-semaine, bps | 3.22 × 10⁻⁴ | 1.24 × 10⁻⁴ | **0.38** |
| dose sans le jour-de-semaine, σ | 2.92 × 10⁻⁴ | 3.31 × 10⁻⁵ | **0.11** |
| dose « flux distincts », σ | 1.67 × 10⁻⁴ | 4.50 × 10⁻⁵ | **0.27** |

Rapport **0.11 – 1.64** contre **50 – 250** pour la dose de prix. **L'exogénéité au prix fait
exactement ce qu'on attendait d'elle : le canal de variance disparaît.** C'est un acquis de
méthode réutilisable, pas un résultat de trading — et c'est la seule chose ici qui justifiait le
déplacement.

Mais les deux R² valent **~2 × 10⁻⁴**. Le canal de variance a bien été éliminé, et **il ne reste
rien dans le canal de moyenne non plus.** La dose n'explique ni l'un ni l'autre : elle est inerte.

---

## 2. Le calendrier des flux construit

Purement calendaire, calculable au 1ᵉʳ janvier, aucun prix en entrée. Occurrences après filtres :

| flux | définition (jour SERVEUR) | portée | occurrences |
|---|---|---|--:|
| F1 TRIPLE_SWAP | `weekday == triple_dow` — mercredi FX/métaux/énergie, vendredi indices (`spec_v22.yaml`) | tous | 12 072 |
| F2 MONTH_END | dernier jour coté du mois | tous | 2 770 |
| F3 QUARTER_END | dernier jour coté de mars/juin/sept/déc | tous | 900 |
| F4 OPEX | 3ᵉ vendredi | tous | 2 610 |
| F5 FUT_ROLL | jeudi avant le 3ᵉ vendredi de mars/juin/sept/déc (roll CME) | indices | 119 |
| F6 INDEX_REBAL | 3ᵉ vendredi de mars/juin/sept/déc | indices | 128 |
| F7 FOMC | `fomc_events.csv` (182 événements) | tous | 1 919 |

Fenêtre de trade **W = les 60 dernières minutes de cotation du jour serveur**, une seule forme,
fixe à tous les niveaux de dose, entrée à l'ouverture de la 1ʳᵉ barre, sortie à la clôture de la
dernière, **sortie temporelle pure** et **zéro swap payé** (la position est fermée avant le
rollover — c'est un choix de conception, il neutralise L36).

### Le contrôle d'horloge L56 a été fait d'abord, et il a tranché

Corrélation du profil horaire hiver-vs-été, dans les deux horloges, 19 instruments :

| horloge | corrélation moyenne | instruments gagnés |
|---|--:|--:|
| **serveur (Europe/Bucharest, DST)** | **0.428** | **13 / 19** |
| UTC | 0.184 | 6 / 19 |

Et la vérification directe : la fin de W tombe à l'heure serveur **23** dans les DEUX saisons,
alors qu'en UTC elle se scinde en **21 h l'hiver / 20 h l'été**. La fenêtre est bien ancrée à
l'horloge de l'échange. (`clock_test.csv`)

### Le contrôle L60 a écarté 26 années-instrument, dont l'instrument le mieux classé

Fraction de barres `high == low` dans W, par série et par an. **26 années-instrument > 20 %**,
écartées avant toute mesure : COPPER (11 années, jusqu'à **57.7 %**), XAGUSD (8), GER40 (2),
UKOIL (2), NZDUSD (2), US500 (1). Ce n'est pas cosmétique : **COPPER arrive premier au ratio
gross/coût du flux de tête (4.78×)** et c'est la série la plus sale du lot — son « effet » est un
artefact de prints de règlement. Sans ce contrôle, le rapport aurait titré sur COPPER.

---

## 3. Le résultat principal : la forme de la courbe

### 3.1 Brute — monotone, et entièrement trompeuse

| dose | N | dates | moyenne (bps) | t-HAC | IC95 bloc |
|--:|--:|--:|--:|--:|---|
| 0 | 42 523 | 4 059 | −0.636 | −7.86 | [−0.79, −0.48] |
| 1 | 14 163 | 1 709 | −0.663 | −4.61 | [−0.93, −0.38] |
| 2 | 2 648 | 345 | −1.098 | −2.46 | [−1.94, −0.27] |
| ≥3 | 353 | 78 | −3.768 | −2.78 | [−6.20, −0.93] |

**Spearman ρ = −1.0, monotonie parfaite.** C'est le résultat qu'on aurait publié en s'arrêtant là.
Deux contrôles le démontent.

### 3.2 Confondant n°1 — le jour de la semaine

F1_TRIPLE **est** un jour de semaine. Deux conséquences, dont la seconde n'était pas anticipée :

**(a) L'effet de base par jour de semaine est plus gros que tout le gradient de dose** (bps) :

| classe | lun | mar | mer | jeu | ven |
|---|--:|--:|--:|--:|--:|
| FX | −0.65 | −0.78 | −0.88 | −0.72 | **−1.91** |
| indices | **+3.31** | −0.32 | −1.03 | +1.11 | +1.59 |
| métaux | **−3.18** | −1.49 | −1.14 | −2.15 | +1.10 |
| énergie | −3.61 | +2.96 | +0.90 | +1.09 | +3.76 |

Après **dé-moyennage par (instrument × jour de semaine)** :

| dose | moyenne (bps) | t-HAC |
|--:|--:|--:|
| 0 | **+0.042** | 0.53 |
| 1 | **+0.091** | 0.64 |
| 2 | −0.607 | −1.38 |
| ≥3 | −4.178 | −2.97 |

**Tout le passage dose 0 → dose 1 était du jour de semaine.** Les deux premiers bins tombent à
zéro. Il ne reste qu'une falaise sur le dernier bin — une falaise, pas un gradient.

**(b) Le placebo apparié est IMPOSSIBLE, par construction.** Aucun jour à dose 0 ne peut partager
son jour de semaine avec un jour à dose ≥ 1, puisque le mercredi (FX) et le vendredi (indices)
portent F1 **par définition**. Taux d'appariement mesuré : **0.000**, pour les trois clés testées.
C'est une extension nette de L58 : *quand une covariable d'appariement est déterministiquement
colinéaire avec l'un des flux, le placebo apparié n'existe pas — et un appariement partiel
fabrique un pool sévèrement sélectionné.* Ce qu'on a vu : la variante à 26 % d'appariement rendait
un pool de moyenne **−0.171** contre une espérance inconditionnelle de **−0.118**, soit **1.7 SE
d'écart ⇒ placebo DÉCLARÉ BIAISÉ** par le contrôle à coût nul du pré-enregistrement. Le contrôle a
fonctionné : il a refusé un placebo qui aurait rendu le signal plus impressionnant qu'il n'est.

### 3.3 Confondant n°2 — j'ai compté un flux deux fois

Le pré-enregistrement fait compter F3_QUARTER_END **en plus** de F2_MONTH_END. Or F3 n'est jamais
vrai sans F2. Donc **toute fin de trimestre marque 2 automatiquement, sans qu'aucun second acteur
ne soit impliqué.** Composition du bin « dose ≥ 2 » hors jour-de-semaine (N = 1 127) :

| combinaison | N | part |
|---|--:|--:|
| MONTH_END + QUARTER_END (**le même flux, deux fois**) | 900 | **79.9 %** |
| OPEX + INDEX_REBAL | 128 | 11.4 % |
| MONTH_END + FOMC | 95 | 8.4 % |
| FUT_ROLL + FOMC | 4 | 0.4 % |

**Quatre cinquièmes du bin de co-occurrence sont un artefact de comptage.**

### 3.4 La courbe honnête — dose de flux GÉNUINEMENT distincts

`dose_y = F2 + F4 + F5 + F6 + F7` (F3 retiré, plus de double compte) :

| dose_y | N | dates | moyenne (bps) | t-HAC | **t groupé par DATE** |
|--:|--:|--:|--:|--:|--:|
| 0 | 52 368 | 4 432 | −0.607 | −8.42 | — |
| 1 | 7 092 | 628 | −1.074 | −4.81 | −1.30 |
| 2 | 227 | **50** | −5.647 | −2.39 | **−1.29** |
| ≥3 | **0** | **0** | — | — | — |

Deux faits terminent le dossier :

1. **Le bin « 3 flux distincts ou plus » est VIDE.** Zéro occurrence, 19 ans, 19 instruments. La
   prémisse même — « plusieurs flux tombent le même jour » — ne se réalise essentiellement pas au
   delà de deux. Le calendrier ne s'empile pas.
2. **À dose_y = 2, l'effet n'est pas significatif** dès que l'erreur-type est groupée par date :
   **t = −1.29, p = 0.20**. Le t-HAC de −2.39 traite 227 observations comme indépendantes ; ce sont
   **50 dates** × des instruments corrélés à ~0.9. **K1 échoue.**

Et son placebo est **BIASÉ** (écart au inconditionnel 1.23 SE avec la clé large, 2.54 SE avec la
clé fine) ⇒ invalide. Et son walk-forward **change de signe dans le fold le plus récent et le plus
fourni** : −6.30 / +0.73 / −19.28 / −11.25 / **+6.20** (fold 4, N = 84 soit 37 % de l'échantillon).

**La courbe de co-occurrence est plate.**

---

## 4. Le flux de tête — le swap triple, testé pour la première fois ici

Le mécanisme prédisait : le côté qui paie doit s'aplatir avant le rollover, donc pression **vers le
bas** là où le LONG paie, **vers le haut** là où le SHORT paie. Jambes disjointes par construction
(ensembles d'instruments différents, pas un `-side_long` — L25).

| ensemble | instruments | N jours triples | Δ vs jours normaux (σ) | Δ (bps) |
|---|---|--:|--:|--:|
| **le LONG paie** | XAUUSD, XAGUSD, COPPER, US500, US100, US30, GER40, UKOIL, USOIL | 3 044 | **−0.0023** | +0.48 |
| **le SHORT paie** | USDJPY, EURJPY, AUDJPY | 2 847 | **−0.034** | **−0.34** |

**Rien.** −0.0023 σ sur la jambe principale. Et sur la jambe « short paie », le signe observé est
**l'inverse** de la prédiction du mécanisme (on prédisait une pression acheteuse, on mesure une
dérive baissière — qui est simplement la dérive de base du FX dans cette fenêtre).

Gate de coût par instrument, 19 séries (`triple_cost_gate.csv`) — un seul dépasse 1.5× :

| instrument | Δ triple (bps) | coût RT | gross/coût | t | verdict |
|---|--:|--:|--:|--:|---|
| COPPER | +8.80 | 1.84 | 4.78 | 0.92 | **écarté L60** (jusqu'à 57.7 % de barres nulles) |
| GER40 | +3.40 | 1.80 | 1.89 | 2.06 | **signe INVERSE au mécanisme** ; ne survit pas Šidák(19) ⇒ |z| ≥ 3.0 |
| tous les autres | ≤ 1.68 | — | ≤ 0.93 | < 2 | sous le coût |

**Le seul instrument avec |t| > 2 sur le flux de tête bouge dans le sens opposé au mécanisme
postulé.** Ce n'est pas un edge, c'est une falsification. **La famille swap-triple est fermée sur
un kill MÉCANIQUE** (gross ≈ 0 à coût nul, signe contredit) — donc **NON rouvrable** au sens de la
politique de ré-ouverture.

---

## 5. Le seul survivant, et pourquoi il ne survit pas non plus

La fin de trimestre **seule** (F3 sans aucun autre flux) — c'est-à-dire le porteur des 79.9 % :

| | valeur |
|---|--:|
| moyenne de W en fin de trimestre | **−3.06 bps** (base −0.61) |
| contraste, **groupé par date** | −2.46 bps, **t = −2.84**, p = 0.005 |
| N | 900 obs / **80 dates** |
| placebo apparié `sym+dow` | **VALIDE** — écart au inconditionnel **0.011 SE**, appariement **100 %** |
| effet vs placebo p05 | −3.06 contre −1.57 ⇒ **dépasse** (K5 ✔) |
| walk-forward 5 folds | −2.91 / −3.18 / −3.37 / **+0.35** / −3.32 ⇒ **4/5, magnitudes stables, fold récent fort** (K8 ✔) |
| L38 orthogonalité vs buy&hold vol-targeté | β 0.50 (t 0.54), **R² = 0.4 %**, α **+2.89 bps (t 3.31)** ⇒ **orthogonal** ✔ |

C'est un effet **réel, stable, non-beta, et validé par un placebo qui, lui, n'est pas biaisé.**
Il meurt sur l'arithmétique, pas sur la statistique :

| | par événement | par an | Sharpe (annualisé en √(obs/an), L47) |
|---|--:|--:|--:|
| brut | **+2.93 bps** (t 3.38, réussite 66.3 %) | +12.2 bps | 0.77 |
| net coût central (1.46 bps) | **+1.46 bps** (t 1.69, **IC95 [−0.32, +3.14] contient zéro**) | **+6.1 bps** | 0.38 |
| net coût de queue (2.73 bps) | **+0.18 bps** (t 0.21) | **+0.75 bps** | 0.05 |

- **Fréquence : 4.15 événements/an.** Sur l'horizon FTMO de référence (182 jours) cela fait **~2
  événements**. Aucune barrière ne se franchit avec deux trades.
- **K4 échoue au coût de queue** : 3.06 / 2.73 = **1.12×**, sous le gate de 1.5×. Et W est adjacente
  au rollover, exactement là où le spread s'élargit — le coût de queue est le bon coût ici, pas le
  central.
- **DSR = 0.328** (`dsr.py` racine, `rf=0` car la position dure 60 minutes ; SR 0.379 contre un
  benchmark d'attendu-max de 0.472 sur 9 essais) ⇒ **échoue**.
- **Au levier réellement déployé du livre (vm 14) : 0.85 %/an.** Contre une barrière statique de
  −10 %.

⚠ Note d'exécution : l'appel DSR initial retranchait un taux sans risque de **période entière**
d'une position tenue **60 minutes** et rendait un Sharpe de −12.1. Corrigé à `rf=0` (l'accrual RF
sur 60 min vaut ~0.02 bps). À retenir pour tout usage de `dsr.py` sur des formes de trade
intra-journalières à basse fréquence d'événement.

**Et surtout : ce n'est pas de la co-occurrence.** C'est un flux unique, déjà connu (rebalancement
de fin de trimestre), que mon propre codage de dose comptait deux fois. Il ne répond pas à la
question posée.

Contre-épreuve qui achève l'histoire additive : **la fin de mois NON-trimestrielle, seule, va dans
le sens OPPOSÉ** — +0.70 bps (t 1.88) contre −3.06 bps pour la fin de trimestre. Deux flux de la
même famille, de signes contraires. **Il n'y a pas de « pression de flux » additive à doser.**

---

## 6. Verdicts par cellule

Budget déclaré **9 cellules**, compteur **N1 local**. **5 cellules exploratoires** ajoutées en
cours de route (dé-moyennage jour-de-semaine, dose sans F1, dose « flux distincts », fin de
trimestre seule, fin de mois seule) — **déclarées ici, comptées, non dissimulées**. **Total 14.**
Šidák à α = 0.05 sur 14 ⇒ seuil **|z| ≥ 2.91**. Modifications de l'hypothèse : **0 / 3**.

| # | cellule | résultat | K échouée | verdict |
|---|---|---|---|---|
| A | courbe poolée | ρ = −1.0 brute ; bins 0-1 → 0 après jour-de-semaine ; contraste t −1.71 (d≥2) / −1.75 (d≥3) | K1 | **REJECTED** |
| B1 | FX | contraste d≥3 t −1.75, 18 dates | K1 | **REJECTED** |
| B2 | indices | contraste d≥3 t −1.68, 60 dates ; WF s'inverse (+4.50 fold 4) | K1, K8 | **REJECTED** |
| B3 | métaux | d≥3 : 17 obs / **11 dates** | K6 | **UNDERPOWERED** |
| B4 | énergie | d≥3 : 5 obs / **3 dates** (t +3.14 sur 3 dates = bruit) | K6 | **UNDERPOWERED** |
| C1 | « le long paie » (9 instr.) | aucun bin \|t\| ≥ 2 ; d≥3 t −1.08 | K1 | **REJECTED** |
| C2 | « le short paie » (3 instr.) | d≥3 : **N = 49 < 60** ; signe contraire au mécanisme | K6 | **UNDERPOWERED** |
| D1 | swap triple, long paie | Δ −0.0023 σ / +0.48 bps | K1, K4 | **REJECTED** |
| D2 | swap triple, short paie | Δ −0.034 σ / −0.34 bps, signe inverse | K1, K4 | **REJECTED** |
| E* | dose dé-moyennée jour-de-semaine | bins 0 et 1 ≈ 0 ; contraste t −1.75 | K1 | **REJECTED** |
| F* | dose sans F1 | t −2.85 mais **79.9 % = un flux compté deux fois** | Šidák (2.85 < 2.91) | **REJECTED** |
| G* | dose « flux distincts » | t −1.29, placebo BIASÉ, WF s'inverse, bin ≥3 **VIDE** | K1, K5, K8 | **REJECTED** |
| H* | fin de trimestre seule | réel et propre au brut, mais 4.15 év./an, K4 en queue 1.12×, DSR 0.328 | K4, DSR | **REJECTED (coût + fréquence)** |
| I* | fin de mois seule | **signe opposé** à la fin de trimestre (+0.70 bps) | — | falsifie l'additivité |

`*` = exploratoire.

---

## 7. Ce que ça NE prouve PAS

- **Ça ne prouve pas qu'il n'existe aucun flux forcé exploitable.** Ça teste **une fenêtre** (les
  60 dernières minutes du jour serveur) sur **un véhicule** (CFD FTMO). Un flux dont l'exécution se
  concentre à l'ouverture, au fixing de 16:00 Londres, ou à la clôture cash US (≠ clôture CFD)
  n'est pas mesuré ici.
- **Ça ne prouve pas que la fin de trimestre est sans valeur.** Elle est réelle (t 3.38 au brut,
  4/5 folds, orthogonale au beta, α 2.89 bps t 3.31). Elle est tuée par **le coût et la fréquence**,
  pas par le mécanisme ⇒ au sens de la politique de ré-ouverture, kill de type **COÛT**, donc
  **ROUVRABLE sur un véhicule moins cher** — le compte IBKR personnel (futures ~0.4 bps RT contre
  1.5-2.7 bps en CFD) ferait passer le ratio gross/coût de 1.12× à ~7×. **Ça reste 4 événements par
  an** : à re-évaluer comme *appoint* d'un livre existant, jamais comme sleeve autonome.
- **Ça ne ferme pas la famille « acteur contraint ».** Ça ferme **le swap triple** (kill mécanique :
  gross ≈ 0 à coût nul et signe contredit) et **la co-occurrence calendaire dans cette fenêtre**
  (kill de puissance et de structure : le bin ≥ 3 est vide en 19 ans).
- **Ça ne dit rien sur la taille de l'effet dans les queues.** Tout est mesuré en moyenne
  conditionnelle ; un flux qui ne mord que lors des 5 % de jours les plus tendus serait invisible
  ici — mais conditionner là-dessus rappellerait la dose de PRIX et son confondant de variance.
- **La dose FX/métaux est diluée par approximation** : F4 utilise le 3ᵉ vendredi pour tous, alors
  que les options FX se règlent au cut 10:00 New York et les options métaux COMEX ~4 jours ouvrés
  avant le mois de livraison ; F5 n'est propre que pour les indices. Ces approximations **ajoutent
  du bruit au comptage** — elles ne peuvent pas fabriquer d'effet, mais elles peuvent en masquer un.

---

## 8. Enseignements à graver (candidats nommés, sans numéro — le numéro se grave à la réconciliation)

**`FLOW-DOUBLE-COUNT`** — *Une dose composite doit être auditée pour l'implication logique entre
ses composantes avant d'être interprétée.* F3_QUARTER_END ⊂ F2_MONTH_END : toute fin de trimestre
marquait 2 sans qu'un second acteur existe, et **79.9 % du bin de « co-occurrence » était un flux
unique compté deux fois**. Contrôle à coût nul : tabuler la composition du bin haut avant de lire
sa moyenne. Corollaire mesuré : sur des flux **génuinement** distincts, le bin « ≥ 3 » est **VIDE**
sur 19 ans × 19 instruments — la prémisse « plusieurs flux tombent le même jour » ne se réalise
presque jamais.

**`PLACEBO-COLLINEAR`** — *extension de L58.* Quand une covariable d'appariement est
**déterministiquement colinéaire** avec un des traitements, le placebo apparié **n'existe pas**
(taux d'appariement 0.000 ici, F1 étant un jour de semaine), et un appariement **partiel** produit
un pool sévèrement sélectionné — mesuré : 26 % d'appariement, pool à −0.171 contre −0.118
d'espérance inconditionnelle, **1.7 SE**, rejeté par le contrôle à coût nul. **Vérifier la
colinéarité clé-d'appariement × traitement AVANT de tirer le placebo.** Le remède qui a marché :
retirer le flux colinéaire de la dose (l'appariement remonte à **1.000**, biais à **0.011 SE**).

**`DOW-FIRST`** — *Avant toute revendication de saisonnalité intra-journalière, dé-moyenner par
(instrument × jour de semaine).* L'effet de base par jour de semaine atteint ici **±3.8 bps**,
plusieurs fois le gradient de dose ; après dé-moyennage les deux premiers bins passent de −0.64 /
−0.66 à **+0.04 / +0.09**. Une monotonie parfaite (ρ = −1.0) a survécu à HAC, au bootstrap par
blocs et à un IC95 excluant zéro — et n'était que du jour de semaine.

**`DSR-RF-HORIZON`** — `dsr.py` retranche `rf / periods_per_year`. Sur une forme de trade
**intra-journalière** à **basse fréquence d'événement** (4.15/an), cela retranche un RF de trimestre
entier d'une position de 60 minutes : Sharpe rendu **−12.1** au lieu de **+0.38**. Passer `rf=0.0`
quand le capital n'est pas immobilisé sur la période d'annualisation.

---

## 9. Reproduction

Code d'analyse en cache de session (hors dépôt, aucun blob de données committé) :
`extract.py` (fenêtre W par jour serveur) · `flows.py` (calendrier) · `clock_test.py` (L56) ·
`analyse.py` (courbe primaire, deux R², placebo) · `deepdive.py` (contrastes groupés par date,
walk-forward, L38) · `dow_control.py` (le contrôle décisif) · `final_check.py` (dose honnête) ·
`economics.py` (arithmétique + DSR).

Aucun chemin live touché (`ftmo_live/`, `strategies/`, `Futures/live/`, `Portfolio/`, `.github/`,
`*.mq5`). `Portfolio/admission/` n'a **pas** été appelé : aucun candidat n'a atteint le stade
p(pass) — un effet à 4.15 événements/an et 0.85 %/an au levier déployé ne se soumet pas à une
barrière, il s'écarte avant.
