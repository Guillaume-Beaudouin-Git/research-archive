# RESULTS — conditionnement croisé de deux edges sous-puissants

**2026-08-03.** Worktree `claude/cross-conditioning`, base `origin/main` @ `72f07c4b`.
Interpréteur **`/usr/bin/python3` explicite** (pandas 2.2.3 / numpy 2.0.2 / statsmodels 0.14.6,
vérifiés au lancement). Données lues en **LECTURE SEULE** depuis
`<HOME>/Desktop/Algo_claude/data/deep_history_utc/` ; caches écrits **hors du
dépôt**, dans un répertoire **privé et estampillé** (`_OWNER.json`, refus de démarrage si un autre
propriétaire est trouvé — un agent frère tourne en parallèle). Aucun blob data dans git, aucun
chemin live touché.

**`PREREGISTRATION.md` a été committé (`af3fde30`) AVANT toute lecture de donnée dans ce
worktree.** Les six états, leurs **directions**, leurs raisons **mécaniques** et leurs règles de
mort chiffrées y sont figés. Les verdicts ci-dessous sont lus dans cette grille, pas construits
après coup.

---

## 0. VERDICT

> **LE GRADIENT EST PLAT SUR LES SIX ÉTATS. Aucun conditionnement ne concentre l'un ou l'autre
> de nos deux edges sous-puissants. Résultat NET, pas résultat nul.**

| | | max \|t\| du gradient | seuil KG1/KU1 | seuil familial Šidák |
|---|---|--:|--:|--:|
| **Section 1 — dérive de réouverture de l'or** | 3 états (+1 proxy) | **0.98** | 2.00 | 2.63 |
| **Section 2 — continuation de clôture US100** | 3 états (+1 variante) | **1.84** | 2.00 | 2.63 |

**Aucun des six gradients primaires n'atteint même le seuil indulgent de 2.0**, et le meilleur
(1.84) est **en dessous de son propre placebo à autocorrélation appariée**. Sur les quatre états
où une direction mécanique était pré-enregistrée et testable, **trois sortent avec le signe
CONTRAIRE**.

**Ce que le travail établit en plus du verdict — et qui vaut plus que lui :**

1. **Le piège n°1 est réel, mesuré, et il aurait fabriqué un faux PASS.** La baseline
   inconditionnelle **dérive massivement avec l'état** : sur l'or elle balaie **−4.42 → +6.52 bps**
   à travers les quintiles de participation, soit **une amplitude de 10.9 bps pour un edge de
   3.67 bps**. Sur cet état, **le gradient de NIVEAU et le gradient d'EXCÈS ont des signes
   OPPOSÉS** (+2.21 contre −6.53). Sans la baseline appariée, on aurait lu un gradient qui n'existe
   pas.
2. **Le placebo à autocorrélation appariée a tué le seul candidat qui franchissait la barre
   économique.** L'état de persistance du P&L propre (US3) sort à **3.96 bps, t 2.22, WF 5/5** à
   d=1 — un **KU7 nominalement PASS**. Son placebo à décalage circulaire rend **p95 = 5.44 bps**.
   Le candidat est **sous son propre placebo**, et il décroît de **6.77 → 1.53 bps** hors
   échantillon. C'est exactement le cas d'école que la contrainte pré-enregistrée visait.
3. **Un état « participation » n'est pas neutre : `tick_volume` est à moitié une amplitude.**
   `corr(volume pré-pause, |rendement pré-pause|) = +0.539` sur l'or. Résidualisé, le gradient
   passe de t 0.49 à **t 0.08**. Un compteur de mises à jour de cotation, lui, est propre
   (`corr = −0.002`) — et reste plat.
4. **Les deux R² côte à côte (L54) racontent la même histoire que `close_momentum_dose`, sur des
   états d'une NATURE DIFFÉRENTE.** Sur l'or : R²(moyenne) **0.00-0.09 %** contre R²(variance)
   **0.37-6.45 %**, avec des t sur la variance de **±2.0 à ±4.2**. Nos états prédisent la
   **dispersion** de la dérive, pas son **espérance** — comme la dose de prix. Ce n'est donc pas
   une propriété de l'amplitude : **c'est une propriété de ces deux edges.**
5. **L'arithmétique du cycle de service tue le conditionnement avant la statistique.** Conditionner
   sur un quintile divise la fréquence par 5. Pour seulement **maintenir** le net annuel de la
   sleeve or (442 bps/an), un quintile doit porter **~11 bps de gross par trade contre 3.67** — un
   facteur **3**. Le meilleur bucket observé (et il est cherry-pické) en porte 7.23 et rend
   **259 bps/an**, soit **−41 %**. Même en supposant l'effet vrai, le conditionnement **coûte** de
   l'EV par unité de temps.

**Conséquence directe pour le dépôt :** nos edges sous-puissants le sont **uniformément**. Il n'y
a pas de « bonnes séances » à isoler. Les leviers restants sont ceux déjà identifiés — **le coût,
le véhicule, l'échantillon** — pas la sélection de régime.

---

## 1. Périmètre, reproduction et hygiène (communs, N0)

**Aucune série n'a été importée de `overnight_futures_2026-07/code/step3_performance.py`** (elle
winsorise à 0.5/99.5 dans son constructeur). Tout est reconstruit du **M1 brut** de
`data/deep_history_utc/`. `data/panels/m5_indices/` n'est jamais ouvert.

**Gate de reproduction contre les dossiers sources**, au GROSS (`cost_rt = 0`) :

| forme de trade | ici | source | écart |
|---|---|---|---|
| Or, fenêtre 8 h depuis `t0`, full | **4.57 bps, t 6.71**, N 4 928 | 4.93 / 5.10 selon tolérances | tolérances de lookup |
| Or, **post-2021** (échantillon décisionnel) | **3.67 bps, t 2.68**, N 1 311 | **3.79 bps, t 2.74**, N 1 311 | même N, −3 % |
| US100 continuation, d=0 | **2.74 bps, t 2.22** | 2.83 bps, t 2.53 | −3 % |
| US100 continuation, d=1 | **1.84 bps, t 1.73** | 1.96 bps, t 1.88 | −6 % |
| US100 continuation, d=2 | **0.54 bps** | 0.59 bps | — |

Je pars donc bien des **mêmes** objets. Les écarts de 3-6 % viennent des tolérances de recherche
de prix, pas d'une spec différente.

**L60 — barres à fourchette nulle**, par série et par année :

| série | zone d'entrée | zone de sortie | verdict |
|---|---|---|---|
| XAUUSD (5 min autour de l'entrée / de la sortie, post-2021) | **0.00-0.58 %** | **0.00 %** | PASS |
| US100 (barre d'entrée 16:01, barre de sortie 16:11) | **0.00 %** | **0.00 %** | PASS |
| US30 | 0.00 % | 0.00 % | PASS |
| **US500** | 0.80 % | **9.64 % (2019)** | **DISQUALIFIÉ** (hérité, K7 de TEST A) |

**Disponibilité de `tick_volume` — et une modification de spec, déclarée.** La colonne n'est
peuplée qu'à partir de **2018 sur XAUUSD** (100 % 2018-2025) et de **2022 sur US100** (46 % en
2018, 16 % en 2019, 36 % en 2021). L'échantillon décisionnel de l'or est donc couvert ; celui des
indices ne l'est pas. **Modification de spec n° 1 (budget 3, consommée 1)** : j'ajoute un second
opérateur de participation, **le nombre de barres M1 dont la fourchette est non nulle**
(« mises à jour de cotation »), calculable sur tout l'historique et **structurellement orthogonal
à l'amplitude**. Il est rapporté **à côté** de `tick_volume`, jamais à sa place là où
`tick_volume` existe.

---
---

# SECTION 1 — la dérive de réouverture de l'or

Forme de trade **gelée et héritée** : `t0` = premier print exécutable à/après **18:00 ET**
(horloge d'échange avec DST), entrée `t0+d`, sortie `t0+8 h`. Long-only. `d = 0` primaire,
`d = 10` en robustesse pré-enregistrée. Échantillon décisionnel **post-2021** (N = 1 311).
Tout au **GROSS**.

## 1.1 KG1 · LE GRADIENT — plat sur les trois états

| état | nature | direction pré-enreg. | n | pente | **t_HAC** | boot p (blocs) | Spearman | **R² moyenne** | **R² variance** (t) | signe OK ? |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|:--:|
| **GS1** participation (`tick_volume`) | liquidité | DOWN | 1 211 | +2.21 | **+0.49** | 0.642 | +0.032 | **0.02 %** | **4.49 %** (t +3.62) | **NON** |
| **GS1p** mises à jour de cotation | liquidité | DOWN | 1 211 | −11.52 | **−0.98** | 0.318 | −0.052 | **0.09 %** | **6.45 %** (t −4.21) | oui |
| **GS2** durée de fermeture | calendrier | UP | 1 311 | −1.90 | **−0.88** | 0.389 | −0.041 | **0.08 %** | **1.11 %** (t +3.84) | **NON** |
| **GS3** position de clôture (CLV) | position scale-free | UP | 1 211 | −0.44 | **−0.09** | 0.927 | +0.010 | **0.00 %** | **0.37 %** (t +2.04) | **NON** |

**KG1 est échouée par les quatre, et de très loin** : le meilleur `|t|` vaut **0.98** pour un seuil
de 2.0 et un seuil familial de 2.63. Les p de bootstrap par blocs (0.32 à 0.93) concordent avec les
t HAC. Le Spearman — insensible à la forme — est **entre −0.05 et +0.03** : il n'y a pas de
relation monotone cachée qu'une pente linéaire raterait.

**KG5 (L54) est le résultat le plus informatif de la table.** Pour **les quatre états**,
R²(variance) est **20 à 200 fois** R²(moyenne), et significatif (|t| 2.0 à 4.2) là où la moyenne
ne l'est jamais. `close_momentum_dose_2026-08` avait établi ce motif pour l'**amplitude de prix**
(R² 7-11 % sur la variance, 0.03-1.4 % sur la moyenne). **Je le retrouve identique sur des états
de liquidité, de calendrier et de position.** La conclusion se déplace donc : ce n'est pas que
l'amplitude est un mauvais conditionneur, **c'est que la dispersion de cette dérive est prévisible
et son espérance ne l'est pas**.

## 1.2 KG3 · LA BASELINE APPARIÉE — elle inverse le signe, et c'est le résultat de méthode

Baseline **BL-A**, pré-enregistrée : la même forme de trade (8 h) ancrée sur les **deux autres
blocs de 8 h du même cycle de 24 h**, donc appariée **au jour**. `excès = R_réouverture − BL-A`.

| GS1 · quintile de participation | n | niveau (bps) | t | **excès BL-A** | **BASELINE elle-même** |
|---|--:|--:|--:|--:|--:|
| Q1 (le moins actif) | 243 | 1.44 | 0.83 | **+5.86** | **−4.42** |
| Q2 | 243 | 3.71 | 1.13 | +4.74 | −1.03 |
| Q3 | 241 | 4.74 | 1.53 | +2.14 | +2.60 |
| Q4 | 247 | 5.12 | 1.89 | −1.41 | **+6.52** |
| Q5 (le plus actif) | 237 | 3.27 | 0.76 | +2.15 | +1.12 |

**Lire la dernière colonne avant toute autre chose.** La baseline inconditionnelle — ce que l'or
fait pendant les **16 autres heures** du même jour — balaie **−4.42 → +6.52 bps** à travers les
quintiles, une amplitude de **10.9 bps** contre un edge de sleeve de **3.67 bps**. Les jours de
forte participation pré-pause sont, tout simplement, des jours où l'or monte **partout ailleurs**.

Conséquence : **le gradient de niveau et le gradient d'excès pointent en sens opposés** — pente
**+2.21** sur le niveau, **−6.53** sur l'excès. Aucun des deux n'est significatif ici, ce qui rend
le point purement méthodologique — mais **sur le full sample, où la puissance existe, le gradient
d'excès sort à t = −2.93 quand le gradient de niveau n'est qu'à −1.58**. La baseline appariée
n'est pas un raffinement : **c'est ce qui décide du signe.**

| GS3 · quintile de CLV pré-pause | n | niveau | t | excès BL-A | baseline |
|---|--:|--:|--:|--:|--:|
| Q1 (clôture en bas de fourchette) | 248 | 4.63 | 1.42 | +1.92 | +2.72 |
| Q2 | 237 | **6.98** | **2.22** | +8.42 | −1.44 |
| Q3 | 245 | **−2.27** | −0.47 | −6.39 | +4.12 |
| Q4 | 240 | 1.86 | 0.53 | +4.31 | −2.45 |
| Q5 (clôture en haut de fourchette) | 241 | **7.23** | 1.94 | +5.46 | +1.77 |

**C'est le piège « pic isolé » du mandat, en grandeur nature.** Q5 vaut 7.23 bps, boot p 0.021,
walk-forward **5/5**, et il serait très facile d'en faire un titre. Mais **il n'y a pas de
gradient** (pente t −0.09), **Q2 vaut autant que Q5** (6.98, t 2.22) et **Q3 est franchement
négatif**. La courbe est en U, pas monotone : la monotonie nominale 3/4 est un artefact de
comptage sur une forme qui n'est pas monotone. **Q5 n'est pas revendiqué.** Un pic sans gradient
est du bruit sélectionné, et il l'est encore quand le bootstrap l'aime.

## 1.3 GS2 · la fermeture longue — direction pré-enregistrée FALSIFIÉE

| niveau structurel | n | médiane heures d'obscurité | niveau (bps) | t | excès BL-A |
|---|--:|--:|--:|--:|--:|
| pause de règlement en semaine (~1 h) | 1 009 | 1.18 | **+4.39** | **+2.99** | +4.07 |
| lendemain de férié (~25 h) | 40 | 3.52 | +7.48 | 0.93 | +14.54 |
| **réouverture du dimanche (~49 h)** | 262 | 49.18 | **+0.31** | **+0.08** | **−2.46** |

L'hypothèse mécanique écrite d'avance — *le déséquilibre non absorbé s'accumule pendant la
fermeture, donc la concession croît avec sa durée* — est **falsifiée dans le sens fort** : la
fermeture **la plus longue** (le week-end) porte une dérive **rigoureusement nulle** (0.31 bps,
t 0.08) et un excès apparié **négatif**, tandis que la pause d'une heure porte **toute** la dérive
de la sleeve (4.39 bps, t 2.99). Le lendemain de férié est non citable (n = 40, t 0.93).

C'est une information de valeur pour ce dépôt, indépendante du verdict : **la dérive de
réouverture de l'or est un phénomène de la pause de RÈGLEMENT quotidienne, pas un phénomène de
fermeture en général.** Elle survit à une coupure de 76 minutes et disparaît sur une coupure de
49 heures. Toute future tentative de la relier à « l'accumulation de flux pendant la fermeture »
part d'un fait contraire.

## 1.4 Contrôles imposés

**Contamination par l'amplitude — et un état sur deux est contaminé.**

| état | corr avec \|rendement pré-pause\| | verdict |
|---|--:|---|
| **GS1** (`tick_volume`) | **+0.539** | **contaminé** — c'est en partie une amplitude |
| GS1p (mises à jour de cotation) | −0.002 | propre |
| GS3 (CLV) | −0.002 | propre — la position n'est pas la largeur |

| régression du rendement de fenêtre sur… | pente | t | R² moyenne |
|---|--:|--:|--:|
| GS1 rang brut | +2.211 | 0.49 | 0.017 % |
| **GS1 résidualisé sur \|rendement pré-pause\|** | +0.334 | **0.08** | 0.000 % |
| \|rendement pré-pause\| seul | +0.051 | 0.44 | 0.019 % |

Le peu qu'il y avait dans GS1 était de l'amplitude, et il n'y avait presque rien. **Le contrôle de
contamination doit être systématique pour tout état de « participation » construit sur un volume
de broker** : `tick_volume` corrèle à 0.54 avec la taille du mouvement, ce qui en fait un
conditionneur ambigu par construction.

**KG4 · walk-forward et KG6 · DSR — les deux filtres, orthogonaux.**

| cellule (post-2021, d=0) | n | trades/an | gross | t | SR gross | **WF folds +** | **DSR** | R² vs buy&hold disjoint |
|---|--:|--:|--:|--:|--:|:--:|--:|--:|
| **sleeve INCONDITIONNELLE** | 1 311 | 242 | 3.67 | 2.68 | 1.07 | **4/5** | **0.865** | **0.0 %** |
| GS1 carrier (Q1) | 243 | 48 | 1.44 | 0.83 | 0.34 | 4/5 | 0.301 | 0.0 % |
| GS1p carrier (Q1) | 254 | 52 | 6.88 | 1.50 | 0.54 | 4/5 | 0.481 | 0.0 % |
| GS2 carrier (week-end) | 262 | 49 | 0.31 | 0.08 | 0.03 | 2/5 | 0.109 | 0.4 % |
| GS3 carrier (Q5) | 241 | 48 | 7.23 | 1.94 | 0.80 | 5/5 | 0.697 | 0.0 % |

*(DSR par `dsr.py` de la racine, `std_sr_trials = 0.437` **déclaré** via
`estimate_std_sr_trials` sur la famille de 6 cellules, `n_trials = 6`.)*

⚠ **Ces DSR ne sont PAS comparables au 0.284 hérité**, qui est calculé à `n_trials = 95`. Le mien
défie 6 essais, pas 95 : il est **structurellement plus indulgent** et ne peut pas servir à
réhabiliter quoi que ce soit. Il est rapporté parce que la règle l'exige, et il ne franchit
**aucun** seuil de PASS pour les cellules conditionnelles (0.11 à 0.70).

**L38 · orthogonalité au beta : PASS et sans ambiguïté.** Régressée contre un buy-and-hold
**disjoint** (les 16 autres heures du même cycle), la sleeve donne **R² = 0.0 %**. Cette sleeve
n'est pas du timing sur du beta or. *(Un R² de 28 % apparaît si on la régresse contre le
rendement 24 h du même ancrage — mais ce dernier **contient** la fenêtre : c'est une corrélation
mécanique, rapportée seulement pour empêcher qu'on la cite comme un test.)*

## 1.5 KG7 · l'économie — pourquoi le conditionnement coûte de l'EV

Coûts mesurés (`cost_denominator_2026-07`, jamais la colonne `spread`) : **1.84 bps** au centre,
**3.88 bps** en queue.

| cellule | trades/an | gross | **net @1.84** | **net bps/AN** | SR net | net @3.88 |
|---|--:|--:|--:|--:|--:|--:|
| **INCONDITIONNELLE d=0** | 242 | 3.67 | **+1.83** | **+442** | 0.53 | −0.21 |
| INCONDITIONNELLE d=10 | 242 | 2.92 | +1.08 | +262 | 0.34 | −0.96 |
| GS3 carrier Q5 (le meilleur, non revendiqué) | 48 | 7.23 | +5.39 | **+259** | 0.60 | +3.35 |
| GS1p carrier Q1 | 52 | 6.88 | +5.04 | +260 | 0.40 | +3.00 |
| GS1 carrier Q1 | 48 | 1.44 | −0.40 | **−19** | −0.09 | −2.44 |
| GS2 carrier week-end | 49 | 0.31 | −1.53 | **−75** | −0.16 | −3.57 |

**L'arithmétique du cycle de service, écrite noir sur blanc.** Prendre un quintile divise la
fréquence par 5. Pour seulement **maintenir** les 442 bps/an nets de la version inconditionnelle,
il faut **~11 bps de gross par trade**, soit **3× le gross inconditionnel**. Le meilleur bucket —
et il est cherry-pické, sans gradient — en porte **7.23** et rend **259 bps/an : −41 %**. En
Sharpe annualisé (L47, `√(obs/an)`), il passe de 0.53 à 0.60 : un gain de **7 points de Sharpe
payé par 41 % du rendement annuel** et par un allongement mécanique de la durée de challenge.

**KG7 est donc échouée même dans l'hypothèse la plus favorable au conditionnement.** C'est une
conclusion qui ne dépend d'aucune statistique : elle tient à la fréquence.

## 1.6 Verdict — SECTION 1

| règle | GS1 | GS1p | GS2 | GS3 |
|---|:--:|:--:|:--:|:--:|
| KG0 hygiène L60 | ✓ | ✓ | ✓ | ✓ |
| **KG1 gradient** (\|t\|≥2.0 **et** signe prédit) | **✗** (t 0.49, signe ✗) | **✗** (t 0.98) | **✗** (t 0.88, signe ✗) | **✗** (t 0.09, signe ✗) |
| KG2 monotonie | ✗ 1/4 | ✗ 2/4 | ✗ 1/2 | (3/4 mais courbe en U) |
| KG3 baseline appariée | ✗ (signe inversé) | ✗ | ✗ | ✗ |
| KG4 walk-forward 5 folds | 4/5 | 4/5 | ✗ 2/5 | 5/5 |
| **KG5 variance vs moyenne (L54)** | **✗ vol-scaler** | **✗ vol-scaler** | **✗ vol-scaler** | **✗ vol-scaler** |
| KG6 DSR ≥ 0.90 | ✗ 0.30 | ✗ 0.48 | ✗ 0.11 | ✗ 0.70 |
| KG7 économie | ✗ −19 bps/an | ✗ −41 % d'EV/an | ✗ −75 bps/an | ✗ −41 % d'EV/an |
| **VERDICT** | **REJECTED** | **REJECTED** | **REJECTED (direction falsifiée)** | **REJECTED (pic sans gradient)** |

> **SECTION 1 : aucun état ne concentre la dérive de réouverture de l'or.** Le candidat E002 reste
> **UNDERPOWERED, famille OUVERTE**, exactement où `overnight_sleeve_reopen` et
> `close_continuation_gold_subwindows` l'avaient laissé. **Le budget d'essais de la famille n'est
> pas consommé** : ce travail teste des états, pas la sleeve.

**Nature du kill des trois états : MÉCANIQUE** (gross ≈ 0, gradient absent, direction falsifiée) ⇒
au registre de la politique de ré-ouverture, **ces trois états RESTENT FERMÉS**. Recalibrer une
statistique ne ressuscite pas une pente de 0.00.

## 1.7 Ce que la SECTION 1 ne prouve PAS

1. **Elle ne prouve pas qu'aucun état n'existe.** Elle prouve que **ces trois-là** — participation
   pré-pause, durée de fermeture, position de clôture — sont plats sur 1 311 séances. Un état
   construit sur une donnée **non de prix** (positionnement, flux d'ETF physiques, calendrier
   macro) n'est pas testé ici et ne l'est par aucun de ces résultats.
2. **Elle ne résout pas la question du coût, qui reste la seule qui décide.** À 1.84 bps la sleeve
   vaut 442 bps/an nets ; à 3.88 bps elle est négative. **La recommandation n°1 de
   `overnight_sleeve_reopen` — mesurer le spread réel de XAUUSD à la réouverture sur le compte —
   reste la recommandation n°1**, et rien ici ne s'y substitue.
3. **La puissance est limitée par construction.** 1 311 séances découpées en quintiles laissent
   ~240 observations par cellule pour un edge de ~4 bps sur un écart-type de ~46 bps. L'effet
   minimum détectable par cellule est de l'ordre de **±6 bps** à 95 % ; un vrai gradient de faible
   amplitude serait invisible. **Ce n'est pas un REJECTED de puissance forte**, c'est un
   « rien de gros ne s'y cache ».
4. **BL-A n'est pas une baseline tradable.** Les blocs d'ancrage alternatifs contiennent la pause
   de règlement suivante et ne sont pas exécutables comme tels. C'est un **contrôle**, pas une
   sleeve, et il est utilisé uniquement pour retirer la dérive du jour.
5. **Elle ne dit rien de l'admission au livre.** Aucun Δp(pass), aucune corrélation au book FTMO
   déployé (`Portfolio/admission/` non lancé — l'escalade était pré-enregistrée comme
   conditionnelle à un PASS au gross, qui n'a pas eu lieu).
6. **Le lendemain de férié n'est pas testé**, seulement observé : n = 40, t 0.93. Son excès apparié
   de +14.54 bps est le genre de chiffre qu'il ne faut pas citer.

---
---

# SECTION 2 — la continuation de pression de clôture sur indices US

**Section strictement séparée** : compteur séparé, verdict séparé, aucun résultat de la section 1
n'entre ici.

## 2.0 Le point de départ, qui n'est pas de moi

Le signe de cette continuation a **déjà été pré-enregistré et jugé** par
`close_continuation_gold_subwindows_2026-08` TEST A : **mécanisme CONFIRMÉ sur US100** (gradient
sans seuil t 3.53, quintiles 4/4, 1ᵉʳ sur 12 ancres, hors-échantillon t 2.10) et **edge REJECTED
sur l'EXÉCUTION** (2.83 → 1.96 → 0.59 bps à d = 0/1/2, demi-vie ≈ 1 min, fourchette de la barre
d'entrée 7.66 bps = 2.7× l'edge). **Je ne re-revendique pas ce signe** : je prends ce verdict pour
acquis et je pose la seule question qui reste ouverte — **un conditionnement fait-il franchir la
barre d'exécution ?** — chiffrée d'avance en **KU7 : ≥ 2.8 bps de gross et t ≥ 2.0 à d = 1**.

Forme de trade gelée : `z` = z-score causal 250 j des 15 dernières minutes avant la clôture cash ;
`z > +1 ⇒ LONG`, `z < −1 ⇒ SHORT`, **jambes disjointes** (L25) ; entrée à l'open de **16:01+d ET**,
sortie à l'open de **16:11 ET**. US100 seul porte la preuve (US500 disqualifié L60, US30
disqualifié par le momentum générique de TEST A).

## 2.1 KU1 · LE GRADIENT à d = 1 (le retard décisionnel) — plat

| état | nature | direction | pente | **t_HAC** | boot p | **R² moyenne** | **R² variance** | t excès | mono | signe OK ? |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|:--:|
| **US1** mises à jour de cotation (t−1) | liquidité | DOWN | −58.1 | **−0.10** | 0.989 | 0.00 % | 0.00 % | −0.08 | 1/1 ⚠ | oui |
| **US1_tv** `tick_volume` (t−1, 2023+) | liquidité | DOWN | +1.06 | **+0.36** | 0.723 | 0.00 % | 1.2 % | +0.36 | 1/3 | **NON** |
| **US2** jours ouvrés à la fin de mois | calendrier | UP | +0.06 | **+0.37** | 0.741 | 0.00 % | 0.2 % | +0.34 | 1/4 | oui |
| **US3** P&L propre des 5 séances | autocorr. inventaire | UP | +5.09 | **+1.84** | 0.057 | **1.0 %** | 0.0 % | +1.85 | 2/4 | oui |

**Aucun n'atteint 2.0**, aucun n'approche le seuil familial 2.63. Le meilleur, US3, est à 1.84 —
et §2.3 montre qu'il est **sous son placebo**.

**⚠ US1 est DÉGÉNÉRÉ et je le dis plutôt que de le compter.** Le compteur de mises à jour de
cotation sur une fenêtre de **15 minutes** d'indice n'a presque aucune dispersion (les 15 barres
bougent quasiment toujours) : `qcut` ne produit que **2 buckets, de 347 et 34 trades**. Ce n'est
pas un quintile, c'est un déséquilibre. **L'opérateur qui fonctionnait sur les 60 minutes
pré-pause de l'or ne transfère pas à une fenêtre de 15 minutes d'indice.** La variante
`tick_volume` est mieux résolue (4 buckets) mais n'existe qu'à partir de 2023 après l'amorce de
250 séances — soit ~380 trades sur un sous-échantillon qui est déjà la seconde moitié de
l'échantillon d'origine.

## 2.2 KU3 · les buckets et leur baseline appariée (d = 1, US100)

Baseline **BL-B** pré-enregistrée : dans chaque bucket, le rendement post-clôture **inconditionnel
en signal** (tous les jours du bucket, sans condition sur `z`).

| US3 · quintile de P&L propre | n | niveau (bps) | t | excès BL-B | baseline BL-B |
|---|--:|--:|--:|--:|--:|
| Q1 | 85 | −0.23 | −0.12 | −0.18 | −1.53 |
| Q2 | 63 | −1.23 | −0.68 | −1.24 | +0.19 |
| Q3 | 48 | +3.01 | 0.99 | +3.00 | −0.09 |
| Q4 | 75 | +2.54 | 1.24 | +2.65 | −0.60 |
| **Q5** | **110** | **+3.96** | **2.22** | +3.96 | −0.18 |

| US2 · proximité de la fin de mois | n | niveau | t | excès BL-B | baseline BL-B |
|---|--:|--:|--:|--:|--:|
| ≥ 7 jours ouvrés | 251 | +2.15 | 1.68 | +2.17 | −0.21 |
| 4-6 jours | 52 | −1.36 | −0.49 | −1.58 | **−1.84** |
| 2-3 jours | 32 | +5.53 | 1.71 | +5.56 | +0.48 |
| 1 jour | 18 | +3.27 | n.c. | +3.26 | +0.04 |
| **dernier jour ouvré du mois** | **35** | **+0.28** | **0.09** | +0.33 | +0.58 |

**L'hypothèse mécanique de US2 est falsifiée par sa propre cellule cible** : le **dernier jour
ouvré du mois** — celui qui porte l'enchère de rééquilibrage la plus grosse — donne **+0.28 bps,
t 0.09**, le plus faible de la colonne, contre +2.15 pour les jours « loin de la fin de mois ». La
non-monotonie est complète (1/4). Et le découpage est fragile : deux buckets ont n = 18 et n = 32.

**La baseline appariée mord ici aussi**, mais moins fort que sur l'or : BL-B balaie **−1.84 →
+0.58 bps**, soit ~2.4 bps d'amplitude. C'est mécaniquement attendu — la forme de trade est
**two-sided**, donc une dérive commune se compense partiellement entre les deux jambes. Le
correctif change peu les niveaux (excès ≈ niveau à ±0.2 bps), ce qui **valide la construction**
plutôt que le contraire : le test L58 était nécessaire, il ne mord simplement pas sur une forme
two-sided. **C'est une observation opératoire à retenir : le piège de la baseline dérivante est
un piège de sleeve DIRECTIONNELLE.**

## 2.3 KU7 et le placebo — le seul candidat qui passe la barre économique meurt sur le placebo

| instrument | état | n carrier | gross d=1 | t | **net @1.8** | **KU7** | **placebo p95** | **bat le placebo ?** | WF | 2018-21 → 2022+ |
|---|---|--:|--:|--:|--:|:--:|--:|:--:|:--:|---|
| **US100** | **US3** | 110 | **3.96** | **2.22** | **+2.16** | **PASS** | **5.44** | **NON** | 5/5 | **6.77 → 1.53** |
| US100 | US1 | 347 ⚠ | 2.09 | 1.89 | +0.29 | FAIL | 2.46 | non | 3/5 | 2.19 → 2.04 |
| US100 | US1_tv | 107 | 0.80 | 0.52 | −1.00 | FAIL | 3.87 | non | 3/5 | — |
| US100 | US2 | 35 | 0.28 | 0.09 | −1.52 | FAIL | 4.96 | non | 0/5 | 6.65 (n=9) → −1.92 |
| *US500* ✗L60 | *US3* | *109* | *4.95* | *3.57* | *+3.15* | *PASS* | *4.68* | *oui* | *5/5* | — |
| *US30* ✗TEST A | *US3* | *114* | *0.86* | *0.54* | *−0.94* | *FAIL* | *3.69* | *non* | *3/5* | — |

**Le cas US3 sur US100 est la démonstration la plus utile du dossier.** Pris isolément il a tout
d'un candidat : **3.96 bps à d=1** (soit +115 % sur les 1.84 bps inconditionnels), **t 2.22**, net
**+2.16 bps** contre +0.04 inconditionnel, **walk-forward 5/5**, et il franchit **KU7**, la règle
que j'avais écrite comme décisive.

Il est **mort sur deux contrôles pré-enregistrés, tous deux indispensables** :

1. **Placebo à autocorrélation appariée.** L'état est construit sur le **P&L propre de la sleeve**,
   donc structurellement persistant. En décalant l'état **circulairement** (400 tirages, la
   persistance de l'état ET du P&L préservées, leur alignement détruit), le **p95 des carriers
   placebo vaut 5.44 bps** — **au-dessus des 3.96 mesurés**. Un état persistant quelconque atteint
   ce niveau plus d'une fois sur vingt. **Le candidat est sous son propre placebo.**
2. **Hors-échantillon.** 2018-2021 : **6.77 bps, t 2.36** (n = 51). 2022-2026 : **1.53 bps,
   t 0.85** (n = 59). **−77 %.** Le walk-forward 5/5 ne l'avait pas vu parce que ses folds sont
   des tranches égales d'un échantillon dont la première moitié porte tout — précisément le mode
   de défaillance que le piège n° 2 décrit.

Et le gradient, lui, n'était **jamais** là : t 1.84, monotonie **2/4** (Q1 et Q2 négatifs, Q3 et Q4
plats). **Un carrier fort sans gradient, au-dessus de KU7 et sous son placebo** : c'est le profil
exact d'un bucket sélectionné.

*(US500 est le seul cellule de la table qui bat son placebo — mais US500 est **disqualifié à
l'hygiène L60** (barre de sortie figée 9.64 % des séances en 2019) et avait **déjà échoué le
hors-échantillon** dans TEST A. Il est listé pour exhaustivité et **ne porte aucune preuve**.)*

## 2.4 Verdict — SECTION 2

| règle | US1 | US1_tv | US2 | US3 |
|---|:--:|:--:|:--:|:--:|
| KU0 hygiène L60 (US100) | ✓ | ✓ | ✓ | ✓ |
| **KU1 gradient** | **✗** t 0.10 (état dégénéré) | **✗** t 0.36, signe ✗ | **✗** t 0.37 | **✗** t 1.84 |
| KU2 monotonie | n.a. (2 buckets) | ✗ 1/3 | ✗ 1/4 | ✗ 2/4 |
| KU3 baseline appariée BL-B | ✗ | ✗ | ✗ | (excès ≈ niveau) |
| KU4 walk-forward / OOS | 3/5 | 3/5 | ✗ 0/5 | 5/5 mais **−77 % OOS** |
| KU5 variance vs moyenne | plat des deux côtés | ✗ | ✗ | ✓ (R² moyenne 1.0 %) |
| **placebo à autocorrélation appariée** | ✗ | ✗ | ✗ | **✗ sous le p95** |
| **KU7 exécutabilité (d=1)** | ✗ 2.09 | ✗ 0.80 | ✗ 0.28 | **nominalement PASS, annulé par le placebo** |
| **VERDICT** | **REJECTED** | **REJECTED** | **REJECTED (cellule cible falsifiée)** | **REJECTED (sous placebo + décay OOS)** |

> **SECTION 2 : aucun état ne sauve la continuation de clôture de son kill d'exécution.** Le
> verdict de `close_continuation_gold_subwindows` TEST A — **mécanisme confirmé, edge rejeté sur
> l'exécution** — est **inchangé**, et il est maintenant confirmé qu'il ne se contourne pas par
> conditionnement de liquidité, de calendrier ou de persistance.

**Nature du kill : EXÉCUTION** (héritée) **+ MÉCANIQUE** pour les trois états testés ici ⇒ la
famille reste close, et ces trois angles de ré-ouverture sont **consommés**.

## 2.5 Ce que la SECTION 2 ne prouve PAS

1. **Elle ne teste pas le mécanisme, qui reste confirmé.** Rien ici ne conteste le gradient
   d'intensité (t 3.53) ni le placebo d'ancre (1ᵉʳ sur 12) de TEST A. La continuation existe ;
   elle n'est pas prenable, et aucun de mes trois états ne la rend prenable.
2. **US1 n'a pas été correctement testé sur les indices.** L'opérateur de participation propre à
   l'amplitude (mises à jour de cotation) est **dégénéré** à 15 minutes, et `tick_volume` n'existe
   qu'à partir de 2022. **La question « la continuation de clôture est-elle plus forte quand la
   clôture est mince ? » reste ouverte** et demanderait un opérateur de profondeur, pas d'activité
   — donc une donnée que nous n'avons pas. C'est un **UNDERPOWERED de mesure**, pas un REJECTED.
3. **US2 est testé sur des cellules minuscules** (18 à 35 trades). Le kill de la cellule cible est
   net (t 0.09) mais la puissance ne permettrait de détecter qu'un effet énorme.
4. **Aucun p(pass), aucune simulation de barrière.** L'escalade était pré-enregistrée comme
   conditionnelle au franchissement du gate au gross (§1.4 du pré-enregistrement) ; il n'a pas eu
   lieu. Aucun chiffre de p(pass), de durée ou d'EV par challenge n'est produit **ni cité**, et le
   80.2 % qui traîne dans d'anciens rapports n'est pas repris (ce livre est FLOOR-DOMINATED à
   49.7 %).
5. **La déflation n'a jamais eu à mordre.** Le seuil familial Šidák (|t| ≥ 2.63 sur 6 essais) n'a
   pas été le facteur décisif : **aucun candidat n'a atteint 2.0**. Si un jour l'un d'eux y arrive,
   c'est ce seuil-là qui s'appliquera.

---
---

# 3. Comptabilité des essais — compteurs **N1 SÉPARÉS**

Aucun n'est fusionné au ledger global (**321, figé**) ; réconciliation à la clôture de programme.

**N1_OR = 3 essais primaires** (GS1, GS2, GS3), un test de gradient chacun.
GS1p est **le même essai que GS1** sous un second opérateur de mesure (modification de spec n° 1,
déclarée §1) et n'est pas compté deux fois.

| bloc | cellules mesurées |
|---|--:|
| Gradients (4 états × 2 échantillons × {niveau, excès, variance}) | 24 |
| Buckets (4 états × 5 × 2 échantillons × {niveau, excès}) | 68 |
| Économie carrier (4 états × 2 retards × {gross, net×2, SR×2, WF}) | 48 |
| Contamination, résidualisation, DSR, L38 | 17 |
| **TOTAL OR mesuré** | **157** |

**N1_IDX = 3 essais primaires** (US1, US2, US3). `US1_tv` est **le même essai que US1** sous un
second opérateur.

| bloc | cellules mesurées |
|---|--:|
| Gradients (3 instruments × 3 retards × 4 états × {niveau, excès, variance}) | 108 |
| Buckets à d=1 (3 instruments × 4 états × ~5 × {niveau, excès, baseline}) | 156 |
| Placebos à décalage circulaire (36 carriers × 400 tirages) | 36 |
| Référence inconditionnelle + split OOS | 12 |
| **TOTAL INDICES mesuré** | **312** |

**Réserve de comptage honnête** : ces cellules ne sont pas des hypothèses indépendantes. Ce sont
des **balayages de robustesse** autour de **6 tests de gradient pré-enregistrés**, et le verdict
est porté par ces 6 seuls. La déflation qui compte est le Šidák sur 6 (|t| ≥ 2.63) ; le maximum
observé est **1.84**.

Diagnostics **N0**, non comptés (ils ne mesurent aucune performance) : L60 par série et par année,
disponibilité de `tick_volume` par année, gate de reproduction contre les dossiers sources,
corrélations de contamination, audit du schéma de cache.

**Budget de modifications de spec : 3 maximum, 1 consommée** (ajout de l'opérateur « mises à jour
de cotation » là où `tick_volume` est absent — justification et date en §1).

---

# 4. Corrections et leçons candidates (NON numérotées — pas de minting en session)

1. **`baseline-appariée-obligatoire-pour-toute-sleeve-DIRECTIONNELLE`.** Sur l'or, la baseline
   inconditionnelle balaie **10.9 bps** à travers les quintiles d'un état, pour un edge de
   **3.67 bps**, et **le gradient de niveau et le gradient d'excès ont des SIGNES OPPOSÉS**. Sur
   la forme two-sided des indices, la même baseline ne balaie que 2.4 bps et ne change rien
   (excès ≈ niveau à ±0.2 bps). ⇒ **Le piège de la baseline dérivante est proportionnel à la
   directionnalité de la sleeve.** Corollaire opératoire : sur une sleeve long-only, rapporter
   l'excès apparié **avant** le niveau ; sur une sleeve two-sided, le contrôle est bon marché mais
   rarement liant.
2. **`un-état-de-participation-construit-sur-un-volume-de-broker-est-à-moitié-une-amplitude`.**
   `corr(tick_volume, |rendement|) = +0.539` sur l'or ; résidualisé, le gradient passe de t 0.49 à
   **0.08**. Un compteur de **mises à jour de cotation** est propre (corr −0.002) mais **dégénère
   sur une fenêtre courte** (2 buckets sur 15 minutes d'indice). ⇒ Mesurer `corr(état, |mouvement|)`
   **avant** de déclarer qu'un état est « d'une autre nature que l'amplitude », et vérifier la
   dispersion du bucketing avant de lire un quintile.
3. **`le-placebo-à-autocorrélation-appariée-est-le-seul-filtre-qui-attrape-un-état-persistant`.**
   Le seul candidat franchissant la barre économique pré-enregistrée (US3 : 3.96 bps, t 2.22,
   WF **5/5**, KU7 PASS) est **sous le p95 de son propre placebo à décalage circulaire (5.44)** et
   décroît de **−77 %** hors échantillon. **Ni le t, ni le bootstrap par blocs, ni le walk-forward
   ne l'ont attrapé** — seul le placebo l'a fait. Étend L49 des états **calendaires** aux états
   **auto-référentiels** (construits sur le P&L de la sleeve elle-même).
4. **`conditionner-coûte-un-facteur-de-fréquence-qu-il-faut-chiffrer-AVANT-de-tester`.** Prendre un
   quintile divise la fréquence par 5 : pour maintenir l'EV annuelle il faut **3× le gross par
   trade** (or : ~11 bps contre 3.67). Le meilleur bucket observé en porte 7.23 et perd **41 %** de
   l'EV annuelle tout en gagnant 7 points de Sharpe. ⇒ **Calculer le facteur de concentration
   requis avant d'ouvrir la donnée** ; il transforme souvent la question en non-question.
5. **Fait à verser au dossier or, indépendant du verdict :** la dérive de réouverture est un
   phénomène de la **pause de règlement quotidienne**, pas de la fermeture en général — la coupure
   de 49 h du week-end porte **+0.31 bps, t 0.08** et un excès apparié **négatif**, quand la pause
   de ~1 h porte **+4.39 bps, t 2.99**. Toute lecture « le flux s'accumule pendant la fermeture »
   part d'un fait contraire.

---

# 5. Reproduire

```
SC=<un répertoire de cache PRIVÉ>          # refuse de démarrer s'il appartient à un autre agent
/usr/bin/python3 code/prep_cache.py  $SC   # M1 BRUT + tick_volume, 4 séries        (~6 min)
/usr/bin/python3 code/sec1_gold.py   $SC   # SECTION 1 : or, 3 états + 1 proxy      (~4 min)
/usr/bin/python3 code/sec2_index.py  $SC   # SECTION 2 : indices, 3 états + placebos (~5 min)
```

Sources M1 lues en **lecture seule** dans le répertoire principal. Caches et tables écrits
**hors du dépôt**. Aucun chemin live touché (`ftmo_live/`, `strategies/`, `Futures/live/`,
`Portfolio/`, `.github/`, `*.mq5`) ; `Portfolio/admission/barrier.py` n'a **pas** été appelé
(l'escalade p(pass) était conditionnelle à un PASS au gross, qui n'a pas eu lieu).
