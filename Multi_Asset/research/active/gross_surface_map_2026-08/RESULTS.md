# La carte du gross — où existe la moindre asymétrie post-2021 ?

**2026-08-06. N0 — SCREENING, NON DÉFLATEUR. Aucun PASS n'est revendiqué ici, et aucune cellule
de ce fichier n'est un candidat.** Balayage à **coût strictement nul** sur les rendements ; le coût
n'entre que comme **seuil de lecture** dans les colonnes de sortie.

Méthode inversée : on ne part pas d'un mécanisme de la littérature pour le tester. On balaye la
surface, on regarde si elle a **plus de queue que le hasard**, et on n'explique qu'ensuite.

---

## 0. Résultat en trois lignes

1. **La carte a une vraie queue** : 4.42 % des cellules dépassent |t|>2.5 contre **1.65 %** sous un
   placebo apparié (2.7×), et 0.88 % dépassent |t|>4 contre 0.11 % (7.7×). Il y a de la structure.
2. **Cette structure est économiquement sous le plancher partout.** Sur 6 511 cellules
   conditionnelles, **3** franchissent `gross > 3 × coût` — et ces 3 ont |t| ≤ 2.0, soit du bruit pur
   dans un balayage de cette taille. **La shortlist est VIDE.**
3. Le rapport médian `gross / coût_à_l'heure_tradée` des points chauds propres est **0.38** — à
   comparer au **0.36** de L43, obtenu par une méthode entièrement différente. La carte **réplique
   L43 indépendamment**, et l'étend au-delà du FX.

---

## 1. Deux défauts silencieux attrapés en route (à documenter, pas seulement à corriger)

### 1.1 Les NaN de week-end empoisonnent toute fenêtre glissante

`px.rolling(20).mean()` sur une série horaire réindexée sur une grille régulière renvoyait
**100 % de NaN**. Cause : la grille porte les week-ends en NaN (28.8 % des barres pour du FX), et
`rolling` propage un seul NaN à toute la fenêtre — donc **aucune** fenêtre de 20 n'était propre.

**Comment il a été attrapé** — et c'est ça qui est réutilisable : un **compte de cellules par
prédicteur**. Trois prédicteurs rendaient 120 cellules chacun, le quatrième **0**. Aucun crash,
aucun avertissement, aucune valeur absurde : le prédicteur avait simplement **disparu** du
balayage. Un test de significativité n'aurait rien vu ; un `assert` sur le rendement non plus.
**Compter les cellules attendues par branche et comparer au réalisé** coûte une ligne et attrape
toute la classe « la branche ne s'est jamais exécutée ».

Correctif : faire tourner le glissant sur les **points observés** (`dropna()`), puis réindexer.

### 1.2 La colonne `spread` de MT5 est en POINTS, pas en unités de prix

`spread / prix × 1e4` donnait **5 370 bps** de fourchette pour XAGUSD. Il manque le pas de
cotation (10^-digits). Attrapé par l'absurdité du chiffre — mais la même erreur d'un facteur 10
sur un instrument à prix élevé serait passée inaperçue.

Correctif : pas de cotation inféré des données, **validé contre `COST_AUDIT.md`** — XAUUSD 0.607
mesuré ici vs 0.699, US500 0.870 vs 0.824, GER40 0.737 vs 0.730. ⚠ **L'inférence échoue d'un
facteur 10 sur US100 et US30** (7.32 et 4.27 bps contre 0.804 et 0.465 mesurés) ; c'est
précisément pourquoi les indices gardent la table fixe de `COST_AUDIT.md` et ne sont jamais
dérivés ici.

---

## 2. Test de falsification d'horloge (L56) — fait AVANT tout le reste

Profil horaire de |rendement| en hiver DST vs été DST, corrélé sur 24 points, dans les deux
horloges. Si la structure est ancrée à l'échange, les profils concordent en **local** et divergent
en **UTC**.

| classe | corr hiver/été **UTC** | corr hiver/été **LOCAL** | verdict |
|---|--:|--:|---|
| FX (10 paires, America/New_York) | 0.64 – 0.86 | **0.83 – 0.99** | LOCAL 10/10 |
| indices US (America/New_York) | 0.75 – 0.78 | **0.983 – 0.984** | LOCAL 3/3 |
| GER40 (Europe/Berlin) | 0.685 | **0.931** | LOCAL |
| XAUUSD / XAGUSD | 0.64 / 0.68 | **0.89 / 0.85** | LOCAL 2/2 |
| UKOIL (Europe/London) / USOIL | 0.79 / 0.80 | **0.95 / 0.96** | LOCAL 2/2 |
| **COPPER** | **0.803** | 0.802 | **ÉGALITÉ — voir ci-dessous** |

**LOCAL gagne sur 18/19.** Toute la carte est donc construite en heure d'échange avec son DST,
jamais en UTC (`clock_falsification.csv`).

**COPPER est l'exception et elle est cohérente** : c'est aussi l'instrument à la plus forte part
de barres M1 à fourchette nulle (**9.1 %**, contre 0.5 % pour XAUUSD — contrôle L60,
`_build_diag.csv`). Une série dont un dixième des barres est un print de règlement n'a pas de
profil horaire net à ancrer. **COPPER est le maillon faible de la carte**, indépendamment de son
coût.

---

## 3. Le plancher de coût affiché sur la carte

| classe | coût RT (bps) | **gate d'intérêt `3×`** | source |
|---|--:|--:|---|
| indices US500/US100/US30/GER40 | 1.80 | **5.40** | `COST_AUDIT.md` §5, bas de la fourchette honnête [1.8 ; 2.9] |
| XAUUSD | 1.84 | **5.52** | `COST_AUDIT.md` §3, mesuré |
| FX majors | 1.50 | **4.50** | catalogue — colonne `spread` zéro-inflée, **non mesurable** |
| XAGUSD | 6.37 | 19.11 | mesuré ici (fourchette × pas + 1.0 slippage) — **NON mesuré ailleurs** |
| UKOIL / USOIL | 7.24 / 7.53 | 21.7 / 22.6 | idem |
| COPPER | 11.38 | 34.14 | idem |

La zéro-inflation de `COST_AUDIT.md` §2 est **confirmée sur mon propre échantillon post-2021** :
EURUSD **48.6 %** de barres à spread nul, USDJPY 30.4 %, USDCHF 15.1 %. C'est pourquoi le FX garde
la valeur catalogue 1.50 et n'est pas mesuré depuis cette colonne.

---

## 4. LA CARTE

**19 instruments × 24 heures locales × 5 horizons (1/2/4/8/24 h) × 4 prédicteurs**, post-2021
(2021-01-01 → 2026-06-05, 5.4 ans), N ≥ 200 par cellule.
**8 695 cellules post-2021** (6 511 conditionnelles + 2 184 inconditionnelles), **9 065 cellules
pré-2021** de contrôle, **65 110 tirages placebo**. Prédicteurs déclarés d'avance, et seulement
ceux-là : `S0_LONG` (aucun — la baseline), `S1_MOM` (signe de la fenêtre précédente de même
longueur), `S2_RANGE` (position dans le range 24 h, ±1 aux déciles 0.2/0.8, sinon pas de trade),
`S3_MA` (écart à la moyenne 20 jours à la même heure locale).

> `S1_MOM` est rapporté **signé**. Le reversal en est le **miroir exact** (t change de signe) : le
> compter séparément doublerait le nombre de cellules sans tester quoi que ce soit — c'est
> exactement le défaut des colonnes `_SS` du batch top10. La distribution de t est donc lue
> **bilatéralement**.

### 4.1 Le tableau de lecture : meilleur gross conditionnel **÷ gate de coût**

Cellules propres au quote uniquement. **`≥ 1.00` = franchit le gate. Tout le reste est MORT quel
que soit son t.**

| classe | instrument | H=1h | H=2h | H=4h | H=8h | H=24h |
|---|---|--:|--:|--:|--:|--:|
| FX | AUDJPY | 0.31 | 0.36 | 0.70 | 0.74 | 0.99 |
| FX | AUDUSD | 0.25 | 0.29 | 0.20 | 0.35 | −0.17 |
| FX | EURGBP | 0.06 | 0.14 | 0.14 | 0.08 | 0.37 |
| FX | EURJPY | 0.25 | 0.33 | 0.48 | 0.50 | 0.77 |
| FX | EURUSD | 0.25 | 0.26 | 0.47 | 0.26 | 0.49 |
| FX | GBPUSD | 0.25 | 0.39 | 0.57 | 0.36 | 0.48 |
| FX | NZDUSD | 0.30 | 0.33 | 0.34 | 0.52 | 0.39 |
| FX | USDCAD | 0.19 | 0.25 | 0.21 | 0.20 | 0.09 |
| FX | USDCHF | 0.28 | 0.28 | 0.57 | 0.45 | 0.94 |
| FX | USDJPY | 0.31 | 0.38 | 0.65 | 0.74 | **1.24** |
| indice | GER40 | 0.38 | 0.58 | 0.90 | 0.84 | **1.24** |
| indice | US100 | 0.46 | 0.55 | 0.71 | 0.72 | 0.90 |
| indice | US30 | 0.26 | 0.38 | 0.72 | 0.42 | 0.34 |
| indice | US500 | 0.29 | 0.30 | 0.52 | 0.66 | 0.16 |
| métal | XAUUSD | 0.31 | 0.49 | 0.55 | 0.97 | 0.97 |
| métal | XAGUSD | 0.16 | 0.21 | 0.29 | 0.42 | 0.27 |
| métal | COPPER | 0.11 | 0.11 | 0.23 | 0.25 | 0.21 |
| énergie | UKOIL | 0.27 | 0.18 | 0.26 | 0.45 | 0.28 |
| énergie | USOIL | 0.18 | 0.26 | 0.34 | 0.77 | 0.57 |

**3 valeurs sur 95 atteignent 1.00**, et **les trois sont à H=24 h** — donc **TENUES**, donc
payant le swap asymétrique (US100 long −2.126 / GER40 long −1.564 / XAUUSD long −1.518 bps par
nuit) **en plus** du gate déjà franchi de justesse. Aucune cellule **intraday-flat** n'atteint
1.00, sur aucun instrument, à aucun horizon, à aucune heure.

### 4.2 Les 3 seules cellules qui franchissent le gate de coût

| instr. | h loc. | H | préd. | N | freq/an | gross bps | **t_HAC6** | gate | coût à l'heure | tenue ? | pré-2021 gross | pré-2021 t |
|---|--:|--:|---|--:|--:|--:|--:|--:|--:|---|--:|--:|
| USDJPY | 01 | 24h | S2_RANGE | 449 | 83 | 5.57 | **2.00** | 4.50 | 1.25 | **oui** | 6.79 | 3.55 |
| GER40 | 21 | 24h | S2_RANGE | 663 | 123 | 6.71 | **1.78** | 5.40 | 2.40 | **oui** | 4.36 | 0.85 |
| GER40 | 19 | 24h | S2_RANGE | 664 | 123 | 5.44 | **1.49** | 5.40 | 2.39 | **oui** | 3.54 | 0.60 |

**Ce ne sont pas des candidats.** Sous le placebo apparié, **4.4 %** des 6 511 cellules dépassent
|t|=2.5 par pur hasard, soit ~288 cellules attendues. Trois cellules à |t| entre 1.5 et 2.0 sont
**très en dessous** de ce que le hasard produit. Elles sont retenues ici seulement parce qu'elles
sont les **moins mortes** de la carte, et parce que leur horizon 24 h les expose au swap.

### 4.3 Où la structure se concentre — fraction de |t|>2 par heure locale

| classe | heures 00–14 | **15** | **16** | **17** | **18** | heures 19–23 |
|---|--:|--:|--:|--:|--:|--:|
| FX | 0.04 – 0.12 | **0.35** | **0.25** | **0.33** | **0.30** | 0.07 – 0.10 |
| métaux | 0.00 – 0.20 | 0.16 | **0.22** | **0.31** | — | 0.02 – 0.12 |
| indices | 0.03 – 0.19 | 0.02 | 0.02 | 0.04 | 0.07 | 0.06 – 0.08 |
| énergie | 0.00 – 0.13 | 0.00 | 0.04 | 0.00 | 0.07 | 0.04 – 0.13 |

Toute la queue de la carte vit dans **une seule fenêtre de 4 heures — 15:00-19:00 New York** — et
sur **FX + métaux uniquement**. Les indices et l'énergie sont plats partout.

---

## 5. La distribution des t contre H0 — le résultat principal

Placebo apparié : la série de côtés est **pivotée** de k observations à l'intérieur de son propre
sous-échantillon horaire (k ∈ {13, 29, …, 271}, 10 rotations par cellule). L'autocorrélation du
signal et son équilibre long/short sont **préservés** ; seul son alignement avec les rendements
est détruit. Les 65 110 tirages portent donc **la même structure de corrélation inter-cellules**
que le balayage réel.

| seuil | carte réelle | **placebo apparié** | iid N(0,1) | cellules réelles | attendues sous placebo | **excès** |
|--:|--:|--:|--:|--:|--:|--:|
| \|t\| > 1.96 | 10.31 % | 5.69 % | 5.00 % | 671 | 370.5 | **+300** |
| \|t\| > 2.50 | 4.42 % | 1.65 % | 1.24 % | 288 | 107.2 | **+181** |
| \|t\| > 3.00 | 2.13 % | 0.51 % | 0.27 % | 139 | 32.9 | **+106** |
| \|t\| > 3.50 | 1.32 % | 0.21 % | 0.047 % | 86 | 13.8 | **+72** |
| \|t\| > 4.00 | 0.88 % | 0.11 % | 0.006 % | 57 | 7.4 | **+50** |

`sd(t)` réel **1.248**, placebo **1.044**, iid 1.000. `max|t|` réel **12.83**, placebo **8.78**.

**Deux lectures, toutes deux nécessaires :**

- **La carte a bien plus de queue que le hasard.** Ce n'est pas un balayage vide. Il existe une
  asymétrie réelle, réplicable, et elle est localisée.
- **Le placebo lui-même est plus gras que N(0,1)** (5.69 % vs 5.00 % ; 1.65 % vs 1.24 %). Lire ce
  balayage contre une normale iid aurait **surestimé le nombre de découvertes d'environ 35 % au
  seuil 2.5 et de 4× au seuil 3.5**. Le chevauchement des cellules et la sous-estimation résiduelle
  du HAC suffisent à fabriquer cet écart. **Un grand balayage doit se comparer à son propre
  placebo, jamais à une table.**

---

## 6. Le sommet de la carte est un artefact de cotation — et le coût l'attrape tout seul

Les plus grands |t| du balayage entier (jusqu'à **19.7** sur la surface inconditionnelle) sont
concentrés autour de **17:00-18:00 New York**. Test gratuit : la **fourchette cotée à cette heure
précise** (`COST_AUDIT.md` §7 demandait exactement ce dénominateur).

| paire | fourchette médiane, heures normales | **fourchette à l'heure du rollover** | facteur |
|---|--:|--:|--:|
| EURGBP | 1.03 bps | **6.18** | 6.0× |
| USDCHF | 1.00 | **6.81** | 6.8× |
| AUDJPY | 0.87 | **7.14** | 8.2× |
| NZDUSD | 1.48 | **6.25** | 4.2× |

Sur la surface inconditionnelle FX, les cellules qui touchent une heure à fourchette explosée ont
un |t| médian de **2.43** contre **0.80** ailleurs — 3×. **14 des 20 plus gros |t| de la carte y
sont assis.** Le « signal » est un mid calculé sur un carnet 6-8× plus large pendant l'heure la
plus illiquide de la journée : un V de 2-5 bps qui descend avant le rollover et remonte après.
Personne ne le traverse à ce prix.

**Le gate de coût le tue indépendamment** — et c'est le point de méthode : le plancher de coût a
attrapé l'artefact **sans qu'on ait besoin de diagnostiquer l'artefact**. C'est ce que vaut un
dénominateur affiché sur la carte.

---

## 7. Les points chauds propres, et ce qu'ils valaient AVANT 2021

86 cellules conditionnelles à |t|>3.5. **52 sont contaminées au quote** (§6). Restent **34 points
chauds propres** (`hotspots_conditional.csv`) :

- **81/86 sont du FX**, concentrés à 15:00-17:00 NY (26/34 des propres).
- **Le contrôle pré-2021 est massivement passé : 71/86 gardent le même signe**, et sur les propres,
  la plupart ont |t| pré-2021 entre 2 et 7. **Ce n'est pas un phénomène post-2021.**
- Le placebo est battu : 85/86 à p ≤ 0.10.
- **Les 35 points chauds `S1_MOM` ont TOUS un gross négatif** — 35/35, sur 10 paires. Le momentum
  de la fenêtre précédente prédit un **reversal** à ces heures, unanimement. C'est un vrai fait
  structurel, pas un maximum de balayage.
- Et : **gross médian 1.23 bps contre 3.25 bps de coût à l'heure tradée, soit un ratio de 0.38.**

**0 des 86 franchit le gate de coût. 0 survit à l'ensemble des contrôles.**

Le **0.38** est le chiffre à retenir. L43 avait établi, sur le FX intraday-flat, un pré-vol
`gross_per_trade / cost_p95 ≥ 1.5` avec un **meilleur observé de 0.36**. Cette carte, construite
par une méthode entièrement différente (balayage aveugle, sans mécanisme, sans famille), sur une
période différente, retombe sur **0.38**. Ce n'est pas une confirmation cosmétique : c'est une
**réplication indépendante de L43** — et la carte montre que le même verdict tient sur les métaux
et l'énergie, où le gate est 4 à 8× plus haut encore.

---

## 8. La shortlist

**VIDE.** Aucune cellule ne franchit simultanément `gross > 3 × coût` et |t_HAC6| > 2.5.
En relâchant à |t| > 3.5 sans gate de coût : 86 cellules, **0 au-dessus du gate**.
En relâchant au gate de coût sans seuil de t : 3 cellules, **toutes à |t| ≤ 2.0**, toutes tenues
24 h donc redevables du swap.

Les deux ensembles sont **disjoints**. Sur cette surface, la significativité et la viabilité
économique ne se rencontrent nulle part.

---

## 9. Le compromis puissance / fréquence, mesuré

| fréquence | prédicteur | cellules | \|gross\| médian (bps) | \|t\| médian | frac. > gate |
|---|---|--:|--:|--:|--:|
| 60–150 /an | S2_RANGE | 1 970 | **1.00** | 0.84 | 0.15 % |
| 150–260 /an | S1_MOM | 2 108 | 0.64 | 0.76 | 0 |
| 150–260 /an | S3_MA | 1 687 | 0.77 | 0.71 | 0 |
| > 260 /an | S3_MA | 497 | **0.28** | 0.67 | 0 |

Le gross par trade **décroît monotonement avec la fréquence** (1.00 → 0.77/0.64 → 0.28 bps) alors
que le coût par trade est **constant**. La fréquence achète bien de la puissance statistique — mais
ici le |t| médian ne monte pas non plus (0.84 → 0.67), parce que le gross s'érode au moins aussi
vite que √N ne progresse. **Sur cette surface, il n'y a pas de fréquence optimale : il n'y a pas de
fréquence viable.** C'est L33b/L57 mesuré sur 6 511 cellules au lieu d'une famille.

---

## 10. Fichiers

| fichier | contenu |
|---|---|
| `clock_falsification.csv` | test L56, 19 instruments, deux horloges |
| `cost_reference.csv` | plancher de coût, pas de cotation, zéro-inflation, source par instrument |
| `spread_by_hour.csv` | fourchette médiane par instrument × heure locale (dénominateur §7 de COST_AUDIT) |
| `cells_all.csv` | 17 760 cellules brutes (post-2021 + pré-2021) |
| `cells_post2021_annotated.csv` | 8 695 cellules + coût à l'heure + drapeau de contamination |
| `null_placebo_t.csv` | 65 110 tirages placebo appariés |
| `t_distribution_vs_H0.csv` | le résultat principal (§5) |
| `map_headline.csv`, `map_by_instrument.csv`, `map_by_instrument_horizon.csv`, `map_by_class_hour.csv` | la carte |
| `hotspots_conditional.csv` | 86 points chauds + contrôle pré-2021 + p placebo |
| `unconditional_drift_surface.csv` | surface S0 (2 184 cellules) |
| `rollover_artifact.csv` | quantification §6 |
| `power_frequency_tradeoff.csv` | §9 |
| `shortlist.csv`, `shortlist_survivors.csv` | vides, conservés comme preuve |
| `code/` | `build_hourly` → `build_map` → `fix_costs` → `analyze` / `report_tables` |

Caches horaires écrits hors du dépôt (scratchpad privé de session). **Aucun blob data commité.**

---

## 11. Ce que ça NE prouve PAS

1. **Ça ne prouve pas qu'il n'y a pas d'alpha sur ces 19 instruments.** Ça prouve que **quatre
   prédicteurs triviaux, sur une grille heure × horizon, n'en trouvent nulle part au-dessus du
   coût**. Un prédicteur portant de l'information exogène — flux, positionnement, calendrier,
   cross-sectionnel, dose observable — n'est pas testé ici et n'est pas concerné par ce verdict.
2. **Ça ne teste pas les horizons > 24 h.** La carte s'arrête à la journée. Les primes hebdomadaires
   et mensuelles (dont le month-end ZN vivant sur IBKR) sont hors grille par construction.
3. **Ça ne teste pas la géométrie.** Tout est mesuré en entrée-inconditionnelle / sortie-à-horizon-
   fixe. Aucun stop, aucune cible, aucun sizing. L59 est explicite : l'edge peut vivre dans la
   sortie et pas dans le signal — cette carte ne pourrait pas le voir.
4. **Le plancher de coût est une estimation, pas une constante.** Les indices sont posés à 1.80 bps,
   bas de la fourchette honnête [1.8 ; 2.9] de `COST_AUDIT.md` — donc **généreux envers la carte**.
   Le FX est au catalogue parce que sa colonne de fourchette est inutilisable (48.6 % de zéros sur
   EURUSD). XAGUSD/COPPER/UKOIL/USOIL sont mesurés **ici et nulle part ailleurs** : à re-vérifier
   avant toute citation.
5. **COPPER est la série la moins fiable de la carte** (9.1 % de barres à fourchette nulle, test
   d'horloge en égalité). Ses cellules sont à lire avec méfiance, indépendamment du coût.
6. **Le placebo par rotation n'est pas un placebo calendaire.** Il détruit l'alignement signal /
   rendement en préservant l'autocorrélation, ce qui est le bon contrôle pour un balayage — mais il
   ne contrôle **pas** une saisonnalité jour-du-mois du type L58. Une cellule survivante aurait
   encore ce test à passer.
7. **Le contrôle pré-2021 n'est pas un walk-forward.** Il dit « le signe tient dans une autre
   époque », il ne dit pas « ça aurait été tradable en continu ». Il n'y a **aucun fold** dans ce
   document.
8. **Aucun essai n'est consommé et aucun n'est déflaté.** C'est du N0 : le prix de ce balayage se
   paierait au moment où une de ces cellules serait promue en hypothèse — ce qui, en l'état,
   n'arrive pour aucune.

---

## 12. Ce que la carte réoriente

La lecture honnête n'est pas « il n'y a rien » — c'est **« il y a quelque chose, systématiquement,
et c'est systématiquement 2 à 6× trop petit pour le véhicule »**. Le motif est identique sur FX,
métaux, indices et énergie, et il est identique à celui qu'ont rencontré `statarb_pairs`,
`month_end_vehicle` et `overnight_futures` : **le mur n'est pas le signal, c'est le dénominateur.**

Deux directions que cette carte rend défendables — et une qu'elle ferme :

- **FERMÉE** : chercher une sleeve intraday-flat par prédicteur de prix simple sur ces 19
  instruments au tarif CFD. 6 511 cellules, 0 au-dessus du gate, meilleur ratio 0.38. Ré-ouvrir
  exigerait un angle nouveau au sens de la politique de ré-ouverture — et « un autre prédicteur de
  prix » n'en est pas un.
- **Cohérente avec la politique de ré-ouverture (kill sur le COÛT ⇒ ROUVRABLE)** : les cellules à
  0.7-1.0× du gate — GER40 H=4/8, USDJPY H=8/24, XAUUSD H=8/24, US100 H=4/8 — sont mortes **sur le
  tarif CFD**, pas sur le signal. Au coût futures (~0.4 bps RT sur MNQ, soit un gate ~4× plus bas),
  plusieurs franchiraient. C'est le même mécanisme que L53 : **la matrice de véhicule avant le
  backtest.** Le véhicule IBKR, pas FTMO.
- **La fenêtre 15:00-19:00 NY est le seul endroit de la carte où quelque chose se passe** — et une
  moitié en est un artefact de cotation. Toute famille future visant cette fenêtre doit produire sa
  **fourchette à l'heure tradée** avant son Sharpe, pas après.
