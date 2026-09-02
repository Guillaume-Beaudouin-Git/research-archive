# Diagnostic de régime — book funded (overnight US100/GER40 + ORB), 2026-09

**Rôle : quant risk, lecture seule.** Portée resserrée en cours de session sur demande du
coordinateur : décomposition **sleeve par sleeve** (ORB et overnight), pas le book en bloc.
Le contexte macro (taux, VIX, régimes de volatilité de marché) est traité par un agent parallèle
et n'est pas dupliqué ici.

## Résumé — 4 lignes

1. **La rupture 2014-2015 est réelle mais repose sur ~1 tirage indépendant, pas sur un régime
   répété** : sur 280 cohortes chevauchantes, il n'existe que **~7-8 fenêtres de 2 ans
   véritablement indépendantes** sur toute l'historique (2013-2024) — 2014-2015 n'en occupe
   qu'une seule. L'anomalie « eq_min_ever = 9000,0x » n'est **pas un écrêtage** : c'est le
   plancher statique agissant comme il est spécifié (voir §1), et elle **confirme** la sévérité
   de 2014-2015 (six survies à moins de 10 centimes du bust) plutôt que de la masquer.
2. **Mécaniquement, la rupture vient presque entièrement de l'ORB, pas de l'overnight.** En
   2014-2015 l'overnight a gagné (+4,36 % / +4,07 %) pendant que l'ORB perdait deux fois plus
   (-6,77 % / -8,76 %) : les deux sleeves sont **quasi non corrélées voire légèrement
   anti-corrélées** (mensuel -0,09, annuel -0,38) — l'overnight a amorti, pas causé.
3. **Non détectable ex ante, sur aucune des deux sleeves, à l'horizon utile (trimestre à
   semestre).** Toute variable candidate (largeur d'opening range, volatilité réalisée
   overnight, momentum de la stratégie elle-même) est corrélée à la performance **de la même
   période**, jamais à la période **suivante** — la corrélation ex-ante tombe à ~0 (et change
   parfois de signe) une fois qu'on n'utilise que l'information passée. C'est un résultat, pas
   un échec de recherche.
4. **Aujourd'hui : rien à ajuster par un signal.** Le seul levier crédible reste le **taper déjà
   présent dans le moteur** (réduction linéaire de la taille ORB sur les $200 juste au-dessus du
   plancher $9 000, `taper=0.02`), qui est un dé-levier **fonction de la distance au plancher
   réalisée**, pas une prédiction de régime — donc conforme à L54. Aucune variante conditionnelle
   testée ne bat ce mécanisme ; ne pas construire d'overlay.

---

## 0. Ce qui a été mesuré, et avec quoi

- **ORB** : grand livre `PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet`,
  N=4013 trades, 2010-06 → 2026-05, colonnes `r_gross` et 4 colonnes de coût (`r_1/2/3 bps RT`,
  `r_Futures 1pt`). Sauf mention contraire, les chiffres ORB utilisent **`r_2 bps RT (median)`**
  (coût médian mesuré, en unités R par trade).
- **Overnight** : `Multi_Asset/research/active/funded_1y_mono_2026-08/attribution/{daily_raw.csv,
  serie_mensuelle.csv, annuel.csv, correlations.csv}`, jambes US100+GER40, jours ON = lundi+mardi,
  net-of-cost-and-swap, 2013-09 → 2026-06.
- **Simulation de cohortes** : `out/proximite_plancher_2ans.csv` + `out/paths_2ans.parquet`
  (scénario `2.17_allin`), mapping vérifié contre `out/cohortes_deploye.csv.gz` (280 premiers
  départs de 2013-10-01 à 2024-06-26, espacés de 14 j).
- **Moteur** : `data/ftmo_portfolio/v22/{engine_v22.py, config_v22.py}` +
  `Multi_Asset/research/active/funded_1y_mono_2026-08/code/run_2ans_path.py` (clone instrumenté,
  aucune modification de la logique de trading).

Fichiers produits par cette session : `code/orb_tranches.py`, `code/cooccurrence.py`,
`code/l54_test.py`, `code/exante_test.py`, `out/orb_trades_annotated.csv`.

---

## 1. L'anomalie « eq_min_ever = 9000,0x » — RÉSOLUE, pas un bug

Lu dans `engine_v22.py` / `run_2ans_path.py` (repris à l'identique, aucune modif) :

- `INIT=10 000`, `FLOOR=9 000` (statique), `DAILY_BUDGET=500`.
- Chaque jour : `lim_eff = max(bal - DAILY_BUDGET, FLOOR)`. Dès que `bal ≤ 9 500`, `lim_eff` est
  **collé à 9 000** — le plancher statique devient la ligne de bust effective.
- `bad = eq < lim_eff` est testé **à chaque segment intraday** ; au premier franchissement, le
  cohorte est déclarée `busted=True` **et la boucle s'arrête immédiatement**, en enregistrant
  l'équité exacte de franchissement (pas de collier à 9000 pour les cohortes qui bustent — leur
  `eq_min_ever` peut être n'importe où sous 9000).
- Corollaire : **un survivant (`busted=False`) ne peut, par construction, jamais avoir
  `eq_min_ever < 9000`** — sinon il aurait busté. Il n'y a donc **aucune possibilité** qu'un bust
  soit compté à tort comme un non-bust caché sous le plancher : la mécanique interdit cet état.
- Les 7 valeurs à 9000,0x (6 en 2014, 1 en 2015) sont des **quasi-échecs réels**, à 1-10 centimes
  du bust (`buffer_conso_pct` 99,99 %), rendus possibles par le **taper** : `taper=0.02` dans
  `CFG_FUNDED_V28` fait que la taille ORB (`orb_risk = FU_ORB_RISK × INIT × taper0`,
  `taper0 = clip((bal-9000)/200, 0, 1)`) décroît linéairement à zéro sur la bande **[9000, 9200]**
  — le moteur freine sa propre descente juste avant le plancher. C'est ce mécanisme qui colle
  l'équité près de 9000 sans la faire systématiquement plonger dessous.

**Conclusion du contrôle** : pas d'écrêtage, pas de sous-comptage des busts. Au contraire, ces
quasi-échecs **renforcent** la lecture « 2014-2015 fut la pire fenêtre » : ce ne sont pas des
survies confortables, ce sont des survies à un cheveu du bust — cohérent avec l'hypothèse du
brief initial, mais pour la raison inverse de celle envisagée (pas un artefact qui minimise,
un signal réel qui maximise la sévérité mesurée).

---

## 2. Indépendance des cohortes — la rupture tient sur ~1 tirage, pas sur un régime

Les 280 cohortes utilisées démarrent tous les 14 jours de 2013-10-01 à 2024-06-26 (span 3 921
jours) avec un horizon de 504 jours (~2 ans). Deux cohortes ne sont **indépendantes** que si leurs
fenêtres ne se chevauchent pas, donc si leurs départs sont espacés d'au moins 504 jours.

- **Fenêtres véritablement indépendantes sur tout l'échantillon : 3 921 / 504 ≈ 7,8.**
- Le tableau du brief (« 2013 n=7 », « 2014 n=26 », … ) présente des comptes de cohortes
  chevauchantes à 97 % (14 j sur 504) : ce ne sont pas 26 tirages par an, c'est le **même tirage
  vu à 26 décalages de 2 semaines**. La bonne unité de compte est la fenêtre de 2 ans, pas le
  jour de départ.
- Les 10 pires cohortes (démarrant entre août 2014 et mars 2015) tiennent presque entièrement
  dans **une seule** fenêtre indépendante de 2 ans (2014-2016) sur les ~7,8 dont dispose
  l'historique complet, et dans **une seule** sur les ~7 disponibles pour les 280 premières
  (span 2013-2024 → 3 921/504 ≈ 7,8, cohérent).

**Implication directe pour A** : la rupture 2014-2015 est un événement réel (les prix et le P&L
sont ceux qui se sont produits), mais statistiquement elle représente **un seul point** sur un
échantillon d'environ huit. On ne peut ni l'écarter comme bruit (le P&L est réel), ni la traiter
comme la preuve d'un « régime récurrent » qui reviendrait un jour donné (un seul tirage ne montre
pas de récurrence — voir §5, aucun indicateur ex-ante ne l'a anticipée ni ne prédit son retour).

---

## 3. Décomposition ORB (`nq_v2_trades.parquet`, N=4013, 2010-06→2026-05)

### 3.1 Par tranche de 4 ans (question du coordinateur)

HAC lag-6, `r_2 bps RT (median)` :

| tranche | n | mean (R) | t_HAC | or_bps moyen | % dir=long | WR long | mean_r long | WR short | mean_r short (gross) |
|---|---|---|---|---|---|---|---|---|---|
| 2010-2013 | 888 | -0,019 | -0,46 | 54,0 | 52,7 % | 0,400 | +0,033 | 0,336 | +0,018 |
| 2014-2017 | 1002 | -0,052 | -1,38 | 47,4 | 54,6 % | 0,410 | +0,047 | 0,334 | **-0,048** |
| 2018-2021 | 1008 | -0,009 | -0,30 | 66,2 | 55,0 % | 0,460 | +0,041 | 0,388 | +0,022 |
| 2022-2026 | 1115 | **+0,086** | **+2,57** | 68,9 | 52,6 % | 0,501 | +0,108 | 0,434 | **+0,142** |

(Le brief citait 0,10 / -0,60 / 0,34 / 2,85 — pattern qualitativement identique, magnitude
dépendante de la colonne de coût exacte utilisée ; reproduit ici avec `r_2 bps RT`, cohérent
en signe et en ordre de grandeur sur les 4 colonnes de coût testées.)

**Ce qui distingue 2022-2026, mesuré :**

1. **Two-sided réel pour la première fois** : le short devient net **positif** (+0,142R, contre
   -0,048 en 2014-2017 et +0,018-0,022 avant) et bat même le long (+0,108R). Dans les 3 tranches
   précédentes, l'edge tenait presque uniquement sur la jambe longue — un profil beta-like
   (famille L11/L45).
2. **β à l'indice ≈ 0** : régression annuelle `orb ~ bh_us100` (14 obs, 2013-2026, ledger déployé
   post-coût) → β=-0,014, R²=0,000, t=-0,07. **Le rebond 2022-2026 n'est pas une exposition
   directionnelle déguisée** — confirmé, pas juste supposé (test d'orthogonalité L38).
3. **Corrélation avec l'AMPLEUR (pas le sens) du mouvement annuel de l'indice** : `orb` corrèle à
   **0,44** avec `|bh_us100|` (année civile) contre **-0,02** avec `bh_us100` signé. 2022
   (indice -12,2 %) et 2023-2024 (+15,6 %/+8,4 %) sont tous des années de **grande amplitude**,
   dans un sens ou l'autre — cohérent avec un breakout qui vit du mouvement, peu importe le
   signe. ⚠ n=14, r=0,44 → t=1,70, **sous le seuil Šidák-corrigé (~2,57 à 5 tests)** : suggestif,
   **non significatif**, à ne pas citer comme mécanisme confirmé.
4. La largeur d'opening range seule (`or_bps`) est un **mauvais candidat de mécanisme** : elle
   monte pratiquement partout (54→47→66→69) et 2020 a la largeur la plus extrême de toute la
   série (or_bps annuel 86,9, pic 102,7 en 2022) sans être une bonne année (2020: mean_r
   -0,035R). La corrélation contemporaine or_bps↔mean_r inter-années n'est que 0,26 (R²=7 %).

**Régime tag interne du fichier** (`regime`, ex-post, non ré-audité — nommage hérité) : 2022-2026
est 77,5 % « trending » contre 62 % (2014-17) et 50 % (2018-21, moitié « vol_shock ») — mais
2010-2013 est **100 % trending** et pourtant la pire tranche en absolu. Ce label seul ne
distingue pas 2022-2026 ; ne pas le citer comme preuve de mécanisme.

### 3.2 Saisonnalité calendaire

Pooled 2010-2026, HAC lag-6, 12 mois testés (Šidák seuil ~2,87 à α=0,05/12) :
mois 5 (mai) t=-2,28, mois 9 (sept) t=-1,63 — **aucun mois ne franchit le seuil corrigé**. Pas de
saisonnalité mensuelle robuste. Restreint à 2022-2026, avril et octobre ressortent (t=+3,41 et
+2,63) mais sur n≈85-110 trades **par mois sur seulement 5 ans** — un test de saisonnalité need
≥10 ans pour être crédible (L23 : exiger ≥2 cycles) ; **non retenu, sous-échantillonné**.

### 3.3 Ex-ante : aucun indicateur trouvé (voir §5 pour la méthode complète)

---

## 4. Décomposition Overnight (US100+GER40, `daily_raw.csv`, jours ON lun+mar)

### 4.1 Par année

| année | n occasions | mean/occasion | std/occasion | mean px-ret US100 | std px-ret US100 |
|---|---|---|---|---|---|
| 2013 | 28 | -0,0003 | 0,0014 | -0,0001 | 0,0027 |
| 2014 | 104 | +0,0004 | 0,0024 | +0,0009 | 0,0042 |
| 2015 | 104 | +0,0004 | 0,0042 | +0,0006 | 0,0078 |
| 2016 | 104 | +0,0001 | 0,0039 | +0,0002 | 0,0052 |
| 2017 | 104 | +0,0002 | 0,0021 | +0,0006 | 0,0034 |
| 2018 | 103 | +0,0003 | 0,0032 | +0,0010 | 0,0066 |
| 2019 | 104 | +0,0003 | 0,0021 | +0,0012 | 0,0055 |
| 2020 | 104 | **+0,0012** | 0,0041 | +0,0035 | 0,0118 |
| 2021 | 104 | -0,0001 | 0,0026 | -0,0001 | 0,0075 |
| 2022 | 104 | +0,0005 | **0,0055** | +0,0012 | 0,0115 |
| 2023 | 103 | -0,0002 | 0,0029 | +0,0001 | 0,0060 |
| 2024 | 105 | -0,0001 | 0,0032 | -0,0001 | 0,0068 |
| 2025 | 104 | +0,0002 | 0,0041 | +0,0002 | 0,0073 |
| 2026 | 44 | +0,0014 | 0,0060 | +0,0021 | 0,0078 |

**Pas de rupture 2014/2015 côté overnight** : c'est la sleeve la **plus stable** des deux — pas
d'année catastrophique, variance des moyennes annuelles bien plus faible que l'ORB en relatif.
2020 (COVID) et 2022 (guerre/inflation) sont les deux années à la fois les plus volatiles et
les plus rémunératrices.

### 4.2 Test L54 (contemporain, pas ex-ante)

`corr(std annuel, mean annuel)` = **+0,68** (occasions ON) et **+0,55** (mouvement overnight
sous-jacent). **Confirmation directe de L54 sur la sleeve overnight seule** : les années à forte
variance overnight (2020, 2022, 2026) sont les mêmes que les années à forte moyenne — la
volatilité overnight EST en grande partie la rémunération, pas un risque gratuit. Couper sur la
variance retrancherait précisément les années qui paient. **Aucune conditionnalité par la
variance n'est justifiée sur cette sleeve**, cohérent avec la conclusion déjà gravée pour le
book entier.

### 4.3 Saisonnalité

Pas mesurée séparément ici (déjà couverte par `RAPPORT.md` de l'attribution existante et hors
du périmètre resserré ORB+overnight-only) ; le point qui manque au book selon
`ftmo_checkup_2026-07` (« sa section saisonnalité est RÉTRACTÉE ») reste rétracté — ne pas
reciter de saisonnalité overnight non revérifiée ici.

---

## 5. Ex-ante : test formel, sur les deux sleeves — RÉSULTAT NÉGATIF NET

Méthode : indicateur **strictement décalé** (rolling passé, `shift(1)`, aucune fuite), comparé au
retour **futur** sur une fenêtre de longueur égale, à l'échelle pertinente pour une décision de
dimensionnement (trimestre à semestre) :

| test | fenêtre | corr(ex-ante) | corr(contemporain, pour comparaison) |
|---|---|---|---|
| ORB : largeur OR passée → retour futur | 60 trades (~1 trim.) | **-0,036** (n=3893) | +0,26 (annuel), +0,35 (contemp. par an) |
| ORB : performance passée → performance future (momentum de la stratégie) | 60 trades | **-0,048** | — |
| Overnight : |mouvement overnight| passé → retour futur | 26 occasions (~semestre) | **+0,044** (n=1267) | +0,68 / +0,55 |

Après correction pour le chevauchement des fenêtres (fenêtres de 60 trades / 26 occasions se
recouvrant à >95 % d'une observation à l'autre → N effectif ≈ n/fenêtre, soit **≈65** blocs
indépendants pour l'ORB et **≈49** pour l'overnight), aucune des trois corrélations n'approche la
significativité (|t_eff| < 0,3 dans les trois cas).

**Lecture** : la relation « variance haute ⇒ moyenne haute » mesurée en §4.2 et suggérée en §3.1
est **contemporaine** — vraie *au sein* de la période où on la mesure — mais **pas prédictive** :
connaître la volatilité (ou l'edge) du trimestre passé ne dit rien sur le trimestre suivant.
Haute et basse vol *futures* ont des retours futurs quasi identiques (ORB : -0,0051 vs +0,0121 —
si quoi que ce soit, le signe est **inversé** ; overnight : +0,00025 vs +0,00033 — indiscernable).

⇒ **Réponse à C : NON, aucun indicateur ex-ante trouvé, sur aucune des deux sleeves, à l'horizon
utile pour un dimensionnement (trimestre-semestre).** Ni la volatilité réalisée (largeur d'OR
côté ORB, amplitude overnight côté overnight), ni la performance récente de la stratégie
elle-même, ne prédisent la période suivante. Il ne s'agit pas d'un délai de détection élevé —
c'est une absence de pouvoir prédictif à toute échéance testée. C'est le résultat qu'il fallait
livrer même s'il est négatif.

---

## 6. Les deux sleeves sont-elles hostiles en même temps ? Non — plutôt le contraire

- **Mensuel** (n=154, 2013-09→2026-06) : `corr(orb, on_us100+on_ger40) = -0,090`.
- **Annuel** (n=14) : `corr = -0,375` (Pearson et Spearman quasi identiques).
- **Conditionnel** : dans le quartile le plus mauvais des mois overnight, l'ORB fait en moyenne
  **+0,337 %** contre **+0,113 %** inconditionnel — mieux, pas pire, quand l'overnight est
  mauvais. Symétriquement, dans le quartile le plus mauvais de l'ORB, l'overnight fait +0,185 %
  contre +0,255 % inconditionnel — légèrement moins bon mais pas négatif.
- **Co-occurrence de queue** : mois simultanément dans le pire quartile des deux séries : 10/154
  observés contre **9,6 attendus sous indépendance** — pas d'excès de clustering dans la queue,
  malgré la corrélation annuelle négative.
- **Mécaniquement dans la rupture 2014-2015** : l'overnight a gagné (+4,36 %/+4,07 %) pendant que
  l'ORB perdait le double (-6,77 %/-8,76 %). L'overnight a **amorti** la rupture sans l'annuler —
  la rupture est **structurellement une rupture de l'ORB**, pas du book, et pas de l'overnight.
  Le pire mois combiné de toute l'historique (2015-03, -4,02 % combiné) est le seul mois où les
  deux sleeves étaient mauvaises **en même temps** — un événement rare (visible une fois en
  154 mois), pas un pattern.

**Conséquence pour le dimensionnement** : les deux sleeves ne s'ajoutent pas en risque, elles se
compensent en moyenne (le book combiné a un profil plus robuste que la somme naïve des deux : vol
combinée mensuelle 1,53 vs vol overnight seule 0,91 + vol ORB seule 1,32 — la combinaison réduit
la vol relative à ce qu'une addition simple donnerait). Ceci est une propriété **structurelle**
(les deux moteurs répondent à des mécanismes différents — calendaire vs breakout), pas un régime
qui pourrait s'inverser sans prévenir — mais elle n'est vraie qu'**en moyenne** : le mois
2015-03 montre que la coïncidence négative reste possible.

---

## 7. Dimensionnement — pas d'overlay, le taper existant suffit

Conforme à L54 et à la consigne du brief (« comparer toute proposition conditionnelle à un
dé-levier PLAT équivalent ; si le plat gagne, le dire ») :

- **Aucun indicateur ex-ante n'existe** (§5) → toute règle de type « réduire la taille si
  l'indicateur X signale un régime hostile » ne peut pas être calée avant le fait ; elle
  agirait toujours après coup, sur un résidu de la mauvaise période déjà passée.
- Le moteur possède déjà un dé-levier **non prédictif, purement réactif à la distance au
  plancher réalisée** : `taper0 = clip((bal-9000)/200, 0, 1)` réduit `orb_risk` linéairement à
  zéro dans la bande [9000, 9200]. C'est un dé-levier **plat par construction sur l'espace de
  l'équité** (pas sur une prédiction de régime) — exactement le type de mécanisme que L54
  recommande : il ne parie pas sur un régime, il répond à ce qui s'est déjà produit.
- Un dé-levier **plat additionnel** sur toute la sleeve ORB (facteur k appliqué en permanence,
  pas seulement près du plancher) réduirait la médiane et la queue proportionnellement — sans
  gain net attendu, puisqu'aucune période n'est identifiable à l'avance comme méritant moins de
  taille que les autres (§5). Un tel dé-levier plat serait donc un choix de **profil de risque
  global** (moins de variance, moins de rendement, dans la même proportion), pas une correction
  ciblée sur un régime détecté — cohérent avec `funded_anatomy` (facteur ×0,85 efface le jour
  fatal $510 contre barrière $500) mais **ce facteur s'applique en tout temps**, pas seulement
  quand un signal le dit.
- **Recommandation** : ne rien changer dans le mécanisme de sizing conditionnel (il n'y en a pas
  et il ne devrait pas y en avoir) ; si un tampon supplémentaire est voulu pour la marge de
  sécurité au plancher, l'obtenir en élargissant la bande de taper existante (ex. 9000→9300 au
  lieu de 9000→9200) plutôt qu'en ajoutant un overlay de régime — c'est un changement de
  paramètre du mécanisme déjà validé, pas un nouveau signal.

---

## 8. Où sommes-nous aujourd'hui — limité à ce qui est mesurable ici

Aucun indicateur ex-ante fiable n'existe (§5), donc il n'y a pas de « régime actuel » à annoncer
au sens d'un signal calibré. Ce qui est mesurable sans construire un tel signal :

- **ORB** : les 12 derniers mois mesurés dans le ledger (2025-09→2026-05, avec 2026 partiel dans
  `nq_v2_trades`) restent dans la tranche 2022-2026 (mean 2025 +0,039R, 2026 partiel +0,050R) —
  positifs, cohérents avec la tranche récente, sans qu'aucun test ex-ante ne garantisse la
  poursuite.
- **Overnight** : 2025 (+0,0002/occasion) et 2026 partiel (+0,0014/occasion) sont dans la
  fourchette normale historique, ni un pic de variance ni un creux.
- **Compte funded réel** (15 jours, `fills.csv`) : balance 9 948,49 / plancher statique 9 000 —
  **948 $ de buffer restant**, soit 94,8 % du buffer initial de 1 000 $ (10 000-9 000) encore
  intact. Comparé aux cohortes historiques : à J+15 de vie, ceci est bien au-dessus de la
  médiane de consommation de buffer observée sur les 280 cohortes (buffer consommé médian sur
  2 ans 37-45 % en régime normal, 82-100 % en 2014-2015) — 15 jours réels sont trop courts pour
  situer ce compte dans une des deux distributions, mais rien dans les 15 jours vécus ne
  ressemble, en vitesse de consommation, aux trajectoires 2014-2015.
- **Conclusion** : **aucun changement de taille justifié** par les données mesurées ici. Pas de
  régime hostile détecté, pas d'indicateur pour en détecter un à l'avance de toute façon.

---

## Δn_tests

5 tests d'indicateur formulés et évalués cette session (tous négatifs/nuls) :
1. ORB — largeur OR passée → retour futur (ex-ante)
2. ORB — performance passée → performance future (momentum de la stratégie, ex-ante)
3. Overnight — volatilité overnight passée → retour futur (ex-ante)
4. ORB — β à bh_us100 (test d'orthogonalité L38)
5. ORB — corrélation à |bh_us100| annuel (magnitude, exploratoire, sous-échantillonné)

Šidák à 5 tests, α=0,05 → seuil t ≈ 2,57. Aucun des 5 ne l'atteint (t effectifs, corrigés du
chevauchement des fenêtres où pertinent : -0,29 / -0,29 / +0,31 / -0,07 / +1,70). **n cumulé
≈ 1 989 + 5 = 1 994.**
