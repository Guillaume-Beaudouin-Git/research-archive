# XAUUSD autour du CPI US — le test confirmatoire sur 232 événements

**2026-08-07. Test CONFIRMATOIRE pré-enregistré. Verdict : REJETÉ (règle R4).**
Spec gelée, seul l'échantillon change. `PREREGISTRATION.md` committé en `30fa8a9a`,
**avant** tout calcul de rendement sur l'échantillon étendu.
Interpréteur `/usr/bin/python3` (pandas 2.2.3 / numpy 2.0.2 / statsmodels 0.14.6), vérifié.
Lecture seule sur tout chemin du répertoire principal. Aucun blob data committé.

---

## 0. En six lignes

1. **Le taux de concordance des dates BLS est de 100 %** contre trois sources indépendantes
   (234/234 documents, 24/24 calendriers ex ante 2007-08, 64/64 scrape tiers) — et de **90.9 %
   seulement contre le fichier utilisé hier**, dont les **7 divergences sont TOUTES postérieures à
   2025-09**. Le fichier d'hier est authentique jusqu'en 2025-08 puis **synthétique**.
2. **Le walk-forward que 65 trades interdisaient existe maintenant : 5 folds sur 232 événements.**
   Frozen (blocs contigus) **4/5 positifs** ; expanding **3/5** ; moyennes de folds
   `[+3.4, −14.3, +8.3, +19.2, +23.0]` bps — l'ordre chronologique est **croissant**, ce qui est le
   dessin d'un effet daté, pas d'un effet stable.
3. **Le hors-échantillon pur 2007-2019 est VIDE.** 168 événements, gross **+3.611 bps, t 0.40**,
   excès contre l'inconditionnel **+0.530 bps**, placebo jour-du-mois **p 0.42**, bootstrap
   **p 0.95**, `gross/coût` **1.08**. La veille de CPI y valait exactement une journée d'or
   quelconque.
4. **Plein échantillon : t_HAC 1.53** ⇒ **kill rule R4 déclenchée** (`t < 2.0`). Bootstrap p 0.339,
   Šidák-80 p 0.99998, **DSR 0.0000**. 4 des 7 conditions de confirmation échouent frontalement.
5. **L'hypothèse de régime pré-enregistrée est RÉFUTÉE, pas confirmée** : le rendement de
   l'événement ne charge **rien** sur le niveau d'inflation connu à l'entrée (β −0.489, **t −0.10**,
   R² 0.0001) ; les quartiles d'inflation donnent 16.8 / 16.5 / **−3.5** / 17.3 bps, aucune
   monotonie. Le pré-enregistrement prévoyait ce cas : **le verdict retombe sur BRUIT.**
6. **Et le trade gelé n'était pas ce qu'on croyait.** Il traverse la publication de 08:30 ET.
   Décomposé : la dérive AVANT le print vaut +8.9 bps en 2007-2019 et +7.3 en 2021-2026
   (**stable, jamais significative**) ; c'est la **RÉACTION** au print qui bascule, **−3.5 → +23.3**.
   **76 % de l'effet « découvert » est du post-publication**, c'est-à-dire une position directionnelle
   ouverte sur une surprise macro, pas une prime d'anticipation.

**Verdict pré-enregistré : REJETÉ. La classe événementielle calendaire se ferme.**

---

## 1. LES DATES — taux de concordance, en tête comme demandé

Récupérées depuis les **communiqués archivés du BLS eux-mêmes**
(`bls.gov/bls/news-release/cpi.htm` → `news.release/archives/cpi_MMDDYYYY.htm`), la date étant
encodée dans le nom du document que le BLS a publié. **234 communiqués, 2007-01-18 → 2026-07-14**,
12 par an sans exception (2025 : 11, cf. infra). `bls.gov` répond **403** à un User-Agent de
navigateur et **200** à un UA descriptif portant une adresse de contact — c'est ce que demande sa
politique robots ; sans ça la source est réputée inaccessible à tort.

| source | nature | fenêtre | concordance exacte |
|---|---|---|--:|
| **A** noms des communiqués archivés | primaire, BLS | 2007-2026, 234 dates | — (référence) |
| **B** en-tête d'embargo **dans le corps** des mêmes documents | champ indépendant | 234 documents | **234 / 234 = 100.00 %** |
| **C** calendriers annuels publiés **d'avance** (`bls2007sched.pdf`, `bls2008sched.pdf`) | ex ante, indépendant | 2007-2008 | **24 / 24 = 100 %** |
| **D** scrape tiers `data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv` | tiers, non-BLS | 2021-2026 | **64 / 64 = 100 %** |
| **E** `data/panels/economic_calendar.csv` — **le fichier utilisé hier** | tiers | 2020-2026 | **70 / 77 = 90.9 %** |

Les **7 divergences de E sont TOUTES postérieures à 2025-09** :

| E (fichier d'hier) | A (BLS réel) | cause |
|---|---|---|
| 2025-09-10 | 2025-09-11 | — |
| 2025-10-14 | **2025-10-24** | shutdown 2025, publication repoussée |
| 2025-11-12 | **aucune publication** | shutdown 2025, CPI d'octobre **annulé** |
| 2025-12-10 | 2025-12-18 | rattrapage |
| 2026-01-14 | 2026-01-13 | — |
| 2026-02-11 | 2026-02-13 | — |
| 2026-04-09 | 2026-04-10 | — |

⇒ **La queue récente du fichier d'hier est générée, pas observée.** Effet mesuré (§3, colonne
`REPLICATION`) : corriger les dates fait passer l'ère de découverte de **38.07 → 31.59 bps**
(**−17 %**), t **3.86 → 3.21**, taux de réussite **0.677 → 0.594**, DSR **0.637 → 0.341**.

**Les dates CPI ne suivent aucune règle.** Jour du mois **10 à 30** ; jours de semaine Mer 82 /
Jeu 53 / Mar 50 / Ven 49, **aucun lundi** ; décalage fin-du-mois-de-référence → publication de
**10 à 30 jours** (médiane 15). Les extrêmes sont des événements réels (2013-10-30 et 2025-10-24 =
shutdowns ; 2015-02-26 / 03-24 / 05-22). Contrôle structurel : le mois de référence extrait du corps
des communiqués (**147/234** parsables, les formats anciens diffèrent) donne **0 doublon** et une
séquence mensuelle consécutive.

**Contrôle croisé qui valide la méthode d'hier** : les vraies dates BLS de l'*Employment Situation*
(239, 2007-2026) sont **premier-vendredi à 83.3 %**, pas 100 %. Le champ `NFP` de
`economic_calendar.csv` était bien une **règle générée** — hier avait raison de l'écarter, et le même
défaut vient d'être trouvé sur la queue du champ CPI.

Fichiers : `bls_cpi_release_dates.csv`, `bls_date_source_concordance.csv`.

---

## 2. OÙ LE TRADE COUPE — mesuré, pas supposé

La barre quotidienne de `panel_px.parquet` datée `d` **coïncide au tick avec la dernière minute M1
de la journée `d`** : concordance exacte **80.9 %** (`|Δ| < 0.01` USD) contre **0.2 %** avec la
dernière minute de `d−1`. La dernière minute cotée est **20:59 / 21:59 UTC** (halt de règlement,
L52/L56). La publication est à **08:30 ET** (vérifié sur les documents : *« embargoed until
8:30 a.m. (EDT/EST) »*), soit 12:30/13:30 UTC.

⇒ **La spec gelée entre à la clôture de la veille (~21:00 UTC) et sort à la clôture du jour CPI, en
TRAVERSANT la publication.** Ce n'est pas une dérive pré-annonce. Une seule nuit tenue, un seul
rollover broker (22:00 UTC) ⇒ **un seul swap**, la facture gelée est correcte. Le swap ne s'annualise
pas ici : il est facturé **une fois par trade**, pas 365 fois par an.

**Look-ahead : aucun.** Les dates sont publiées un an à l'avance — les calendriers annuels source C
le prouvent matériellement.

⚠ **Correction au dénominateur d'hier.** Le `gross/coût = 20.7` de `exogenous_predictors_2026-08`
divise par le seul RT (1.84). La position est **tenue une nuit** : le coût est
`1.84 + |−1.518| = 3.358 bps` (queue provisionnée `3.88 + 1.518 = 5.398`). Sur les **mêmes** données,
`gross/coût` vaut **11.34**, pas 20.7.

**Hygiène d'échantillon** (`sample_hygiene.csv`) : 234 dates BLS → **232 entrées tradées**.
2 perdues (2026-06-09, 2026-07-13 : au-delà de la couverture de prix, qui s'arrête au 2026-06-05).
**230 sorties tombent bien sur le jour CPI** ; 2 non (2017-04-14 et 2020-04-10, **Vendredis saints**)
et couvrent alors le week-end — conservées, la spec est gelée, l'écart est déclaré.

**L60** (`l60_zero_range.csv`) : barres M1 XAUUSD à fourchette nulle, **par an**, 2007-2026 :
maximum **1.62 %** (2012), médiane ~0.6 %, **0.01 %** depuis 2024. Série propre, aucun contaminant
de type XPTUSD.
**L59** : entrée et sortie sont deux clôtures, sans stop ni bracket — il n'y a **aucune géométrie de
sortie à re-pricer**. Déclaré dans le pré-enregistrement pour que l'absence de ce test soit un fait.

---

## 3. LE WALK-FORWARD, PUIS LE HORS-ÉCHANTILLON, PUIS L'ENSEMBLE

`eras.csv`. Coût = 1.84 RT + 1.518 swap. **Fréquence : 12 événements/an dans les quatre colonnes.**

| | **OOS PUR 2007-2020** | **DÉCOUVERTE 2021-2026** | **PLEIN 2007-2026** | *REPLICATION (fichier d'hier)* |
|---|--:|--:|--:|--:|
| N | **168** | 64 | **232** | *65* |
| fréq/an | 12.0 | 11.8 | 11.9 | *12.0* |
| bande jour-du-mois | 9-29 | 9-23 | 9-29 | *8-14* |
| **gross bps** | **+3.611** | +31.590 | **+11.329** | *+38.07* |
| **t_HAC6** | **0.40** | 3.21 | **1.53** | *3.86* |
| moyenne inconditionnelle | 3.082 | 5.722 | 3.816 | *5.722* |
| **excès vs inconditionnel** | **+0.530** | +25.868 | **+7.513** | *+32.348* |
| MDE à \|t\|=2.5 | 21.52 | 34.01 | **18.19** | *33.75* |
| puissance | UNDERPOWERED | UNDERPOWERED | **UNDERPOWERED** | *UNDERPOWERED* |
| **placebo jour-du-mois** | **0.4242** | 0.0130 | **0.0994** | *0.0012* |
| bootstrap par blocs | 0.9542 | 0.0388 | **0.339** | *0.0056* |
| Šidák (n=80) | 1.0 | 0.0999 | **0.99998** | *0.0086 (n=76)* |
| **gross / coût** | **1.08** | 9.41 | **3.37** | *11.34* |
| gross / coût (queue) | 0.67 | 5.85 | 2.10 | *7.05* |
| net bps / net ann. | +0.253 / **+3.0** | +28.232 / +333.8 | +7.971 / +95.2 | *+34.71 / +416.8* |
| taux de réussite | 0.5476 | 0.5938 | 0.5603 | *0.6769* |
| **WF gelé, folds positifs** | **2 / 5** | *impossible (N<100)* | **4 / 5** | *impossible* |
| WF gelé, moyennes | [13.2, −14.6, −10.7, 14.9, −1.4] | — | **[3.4, −14.3, 8.3, 19.2, 23.0]** | — |
| **WF expanding, folds positifs** | 2 / 5 | 4 / 5 | **3 / 5** | *4 / 5* |
| WF expanding, moyennes | [−0.9, −19.2, 10.3, −3.5, 16.3] | [38.2, 5.9, −4.1, 55.5, 5.8] | **[−12.4, 15.3, −4.1, 41.1, 16.1]** | *[38.2, 5.9, −4.1, 55.5, 50.2]* |
| Sharpe net | **0.008** | 1.062 | 0.249 | *1.363* |
| **DSR** | **0.0000** | 0.341 | **0.0000** | *0.6374* |

**La colonne REPLICATION reproduit hier au chiffre près** (38.07 / 3.86 / DSR 0.637) : la chaîne est
la même, seul l'échantillon a changé.

### 3.1 Le walk-forward — le point n°1 du dossier
Il existe enfin, et il ne sauve rien. Le **4/5** du plein échantillon est produit par un **ordre
chronologique croissant** : `[+3.4, −14.3, +8.3, +19.2, +23.0]`. Les deux derniers folds (à partir de
2020-11) portent tout ; le fold 2012-2015 est à **−14.3**. C'est le dessin d'un effet **daté**, pas
d'un effet stable — et la version expanding, qui score les mêmes données autrement, rend **3/5**.
Sur le hors-échantillon pur, **2/5**.

### 3.2 Le hors-échantillon pur 2007-2019 : vide, pas faible
168 événements, **excès de +0.53 bps** contre l'espérance inconditionnelle d'une journée d'or.
Le placebo jour-du-mois rend **p 0.42**, le bootstrap **p 0.95** : les deux contrôles, qui ne testent
pas la même chose, sont d'accord. `gross/coût = 1.08` — sous le gate `3×` de L11b **avant même** toute
discussion statistique.

⚠ **Note de méthode sur L58, à graver.** Mon critère de validité du pool
(`|biais| ≤ excès/3`) marque **BIASED** sur l'ère OOS. C'est un **artefact de division par zéro** :
le biais absolu du pool (**−0.968 bps** sur un inconditionnel de 3.082) est parfaitement normal ;
c'est l'**excès** qui est nul (0.530), donc le ratio explose. **Le contrôle L58 doit se lire en
ABSOLU (biais du pool contre l'inconditionnel), jamais en ratio de l'effet mesuré** — sinon il
déclare invalide exactement les cas où il n'y a rien à invalider. Sur les ères où l'effet existe
(découverte, plein), le pool est propre (**−0.835** et **−1.447** bps).

### 3.3 Étendre l'échantillon a bien résolu la question de puissance
Le MDE tombe de **33.75 → 18.19 bps** (√N). Mais l'excès tombe de **32.35 → 7.51**. L'effet a
rétréci **plus vite** que la barre d'erreur : la candidate reste UNDERPOWERED à N=232, non parce que
l'échantillon manque, mais **parce qu'il n'y a rien à mesurer**. C'est le contraire d'un blocage de
puissance — c'est une réfutation.

### 3.4 Année par année (`by_year.csv`)
**14 / 20 années positives**, mais l'amplitude dit tout : 2008 **−43.8**, 2010 **−34.2**,
2014 **−39.0**, 2018 **−32.2** contre 2009 **+90.4**, 2021 **+53.6**, 2022 **+47.5**, 2025 **+44.8**.
Les 3 plus gros mouvements en valeur absolue font **−22 %** du P&L total (ils *coûtent*) ; sans eux
la moyenne monte à **+14.04 bps, t 2.01** — toujours sous le seuil, et un trim qui *augmente* la
moyenne est un signe de queue à deux côtés, pas de robustesse.

---

## 4. LE CONTRÔLE DE VOISINAGE — la spécificité au CPI s'inverse

`neighbourhood.csv`. **Même spec gelée**, autres calendriers de publication, mêmes ères. FOMC =
`fomc_events.csv` (source indépendante) ; PPI et NFP = **vraies dates BLS**, récupérées par la même
méthode que le CPI (jamais le champ `NFP` du fichier d'hier).

| événement | ère OOS PURE 2007-2020 (N) | gross | t | | ère PLEINE (N) | gross | t |
|---|--:|--:|--:|---|--:|--:|--:|
| **CPI** | 168 | **+3.611** | **0.40** | | 232 | **+11.329** | 1.53 |
| PPI | 168 | +6.509 | 0.78 | | 232 | +4.667 | 0.54 |
| NFP (*Employment Situation*) | 168 | +11.985 | 1.48 | | 233 | +10.350 | 1.55 |
| **FOMC** | 114 | **+17.214** | **1.78** | | 157 | **+14.747** | **1.62** |

**Sur les 14 ans jamais vus, l'ordre est exactement l'INVERSE de l'argument d'hier.**
Hier : « la veille de FOMC ne donne rien (+8.2 bps, t 0.39) alors que le CPI donne +38 ⇒ l'effet est
spécifique à l'inflation, l'or est l'actif d'inflation ». Sur le hors-échantillon :
**FOMC +17.2 > NFP +12.0 > PPI +6.5 > CPI +3.6**. La veille de CPI est la **PLUS FAIBLE des quatre**.

Le chiffre qui manquait tenait en une ligne : `exogenous_predictors_2026-08` cite lui-même
« FOMC-eve pré-2021 : +17.21 bps, t 1.78, N=114 » — je le reproduis à la troisième décimale
(**17.214, t 1.78, N=114**) — et le lit comme « une corrélation faible en faveur d'un effet réel ».
Il ne pouvait **pas** calculer le CPI sur la même fenêtre : son fichier calendrier commençait en
2020. **La statistique qui tuait l'hypothèse était le même calcul, sur l'autre calendrier.**

**R6 n'est pas formellement déclenchée** (mon critère exigeait `gross ≥ 50 % du CPI` **ET**
`t_HAC ≥ 2.0` ; aucun voisin n'atteint 2.0). Mais c'est parce que **rien** n'est significatif sur le
plein échantillon, ce qui est le fond de l'affaire. Le mécanisme « l'or est l'actif d'inflation,
donc la veille de CPI est spéciale » est **réfuté** : il n'y a ni effet CPI, ni spécificité au CPI.

---

## 5. L'HYPOTHÈSE DE RÉGIME, TESTÉE ET RÉFUTÉE

Pré-enregistrée : *« l'inflation est redevenue un risque macro de premier plan à partir de 2021 ;
avant cela le CPI n'était pas un événement pour l'or »*, avec le test associé — **régresser le
rendement de l'événement sur le niveau d'inflation connu à l'entrée** ; pente nulle ⇒ régime rejeté
⇒ **BRUIT**.

Le niveau d'inflation est le **y/y de tête publié par le BLS**, extrait du corps des communiqués
(**212 / 234** parsés), **décalé d'une publication** pour n'utiliser que ce qui est connu le soir de
l'entrée.

`d2_regime_regression.csv` :

| spec | N | R² | β(y/y connu) | t | β(VIX veille) | t |
|---|--:|--:|--:|--:|--:|--:|
| y/y seul | 209 | **0.0001** | −0.489 | **−0.10** | — | — |
| VIX seul | 232 | 0.0005 | — | — | −0.275 | −0.17 |
| les deux | 209 | 0.0023 | +0.217 | 0.05 | −0.608 | −0.39 |

`d2_regime_quartiles.csv`, non paramétrique :

| quartile du y/y connu à l'entrée | N | plage | gross bps | t |
|---|--:|---|--:|--:|
| Q1 bas | 56 | −2.9 .. 1.5 | +16.84 | 1.11 |
| Q2 | 50 | 1.6 .. 2.3 | +16.50 | 1.20 |
| Q3 | 52 | 2.4 .. 3.3 | **−3.50** | −0.18 |
| Q4 haut | 51 | 3.4 .. 9.1 | +17.35 | 0.87 |

**Aucune monotonie, aucune pente, R² ≈ 0.** Le régime d'inflation **n'explique pas** la concentration
post-2021. La déflation de 2009 (Q1, y/y jusqu'à −2.9 %) rend autant que le choc de 2022 (Q4).
Le pré-enregistrement tranche : **verdict BRUIT**, pas RÉGIME.

---

## 6. CE QUE LE TRADE GELÉ MESURAIT VRAIMENT (diagnostic, non décisionnel)

`d1_intraday_decomposition.csv` — la fenêtre gelée coupée à l'embargo, sur M1 vrai UTC converti en
**heure d'échange ET avec son DST** (L56). La dernière barre pré-publication est vérifiée à
`08:29 EST` en hiver et `08:29 EDT` en été, sur toute la période.

| ère | N | **avant 08:30 ET** | t | **après 08:30 ET** | t | total | t |
|---|--:|--:|--:|--:|--:|--:|--:|
| OOS 2007-2020 | 166 | **+8.904** | 1.46 | **−3.535** | −0.51 | +5.369 | 0.60 |
| DÉCOUVERTE 2021-2026 | 64 | **+7.288** | 1.52 | **+23.252** | **2.31** | +30.540 | 3.07 |
| tout | 230 | **+8.454** | **1.84** | +3.919 | 0.64 | +12.373 | 1.69 |

**La jambe d'anticipation est STABLE et jamais significative** : +8.90 puis +7.29 bps, t 1.46 et
1.52, t 1.84 sur l'ensemble. **La jambe qui bascule est la RÉACTION** : −3.54 → **+23.25**.
**76 % de l'effet « découvert » en 2021-2026 est post-publication.**

Autrement dit, la spec gelée n'est pas une prime d'anticipation : c'est **une position longue
directionnelle ouverte à l'aveugle sur une surprise macro**, qui a payé pendant cinq ans où l'or a
monté sur les prints. Le nom « veille de CPI » désignait la **date d'entrée** ; le P&L, lui, est
celui du **jour de publication**.

*(Ce diagnostic ne promeut rien : la jambe pré-publication seule n'est ni pré-enregistrée comme
candidate, ni significative — t 1.84 sur 230 événements, et le coût d'un aller-retour intraday
XAUUSD 1.84 bps mange 22 % de ses 8.45 bps de gross.)*

---

## 7. FRÉQUENCE, ET POURQUOI 12 ÉVÉNEMENTS/AN NE SONT PAS UN MOTEUR

Le pré-enregistrement conditionnait le calcul de barrière à « si le gross tient ». **Il ne tient
pas.** Ce qui suit est donc une **BORNE SUPÉRIEURE sur une candidate rejetée**, calculée avec
`Portfolio/admission/barrier.py` importé sans modification (daily −5 % sur l'équité, plancher
**STATIQUE** −10 %, horizon 182 j), et non un résultat d'admission. `d3_barrier_upper_bound.csv` :

| échantillon | vm | duty cycle | trades/an | net ann. | **Sharpe solo** | **p(pass)** | échec daily | durée médiane |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| PLEIN 2007-2026 | 1 | **4.63 %** | 12.0 | +95.8 bps | **0.246** | **0.000** | 4.0 % | — |
| PLEIN 2007-2026 | 14 | 4.63 % | 12.0 | +95.8 bps | 0.246 | **0.048** | 95.0 % | 166 j |
| DÉCOUVERTE (borne haute) | 1 | 4.59 % | 12.0 | +339.3 bps | **1.013** | 0.001 | 0.0 % | 274 j |
| DÉCOUVERTE (borne haute) | 14 | 4.59 % | 12.0 | +339.3 bps | 1.013 | **0.145** | 84.4 % | 166 j |

**Même dans l'hypothèse la plus favorable qui soit** — l'ère de découverte prise pour argent
comptant, à vm 14 — la sleeve seule plafonne à **14.5 % de p(pass)** contre **53.7 %** pour le livre
déployé, et fait échouer **84 % des chemins sur la limite daily**. Un duty cycle de **4.6 %** signifie
que sur les 182 jours de l'horizon, elle agit **~6 fois**. La décorrélation n'achète pas de p(pass)
(corr −0.06 contre +0.82 pour le Sharpe solo) : **le jugement se fait sur le Sharpe solo (0.246 en
plein échantillon) et il est disqualifiant.** Une sleeve à 12 trades/an ne remplace pas un moteur —
au mieux elle en décore un.

---

## 8. VERDICT contre les règles pré-enregistrées

| condition de CONFIRMATION | requis | mesuré | |
|---|---|--:|---|
| 1. WF ≥ 4/5 folds nets positifs | ≥ 4/5 | 4/5 gelé, **3/5 expanding** | ⚠ ambigu |
| 2. OOS 2007-2019 : gross>0 **et** t ≥ 2.0 | t ≥ 2.0 | **t 0.40** | ✗ |
| 3. plein échantillon t_HAC ≥ 2.5 | ≥ 2.5 | **1.53** | ✗ |
| 4. placebo p ≤ 0.05 et pool L58 valide | ≤ 0.05 | **0.0994** | ✗ |
| 5. bootstrap par blocs p ≤ 0.05 | ≤ 0.05 | **0.339** | ✗ |
| 6. DSR ≥ 0.95 (n_trials 80, rf 0) | ≥ 0.95 | **0.0000** | ✗ |
| 7. gross/coût ≥ 3 | ≥ 3 | 3.37 (queue 2.10) | ~ |

| kill rule | seuil | mesuré | |
|---|---|--:|---|
| R1 gross OOS ≤ 0 | ≤ 0 | +3.611 | non déclenchée (de justesse) |
| R2 WF ≤ 2/5 | ≤ 2/5 | 4/5 plein, **2/5 OOS** | non déclenchée sur le plein |
| R3 placebo p > 0.10 | > 0.10 | 0.0994 | non déclenchée (de justesse) |
| **R4 t_HAC plein < 2.0** | **< 2.0** | **1.53** | **✅ DÉCLENCHÉE** |
| R5 gross/coût < 3 | < 3 | 3.37 | non déclenchée |
| R6 voisinage générique | 2/3 voisins ≥50 % ET t≥2.0 | 2/3 ≥50 %, t max 1.62 | non déclenchée *formellement* |

**REJETÉ par R4.** Et le repli « RÉGIME » prévu par le pré-enregistrement est explicitement fermé
par §5 : la pente sur le niveau d'inflation est nulle ⇒ **BRUIT**.

Je note que **R1, R3 et R5 passent de justesse** (+3.6 bps, p 0.0994, ratio 3.37). Ce n'est pas un
« presque ». Trois quasi-frontières simultanées sur un effet dont l'excès hors-échantillon vaut
**+0.53 bps** décrivent exactement une statistique qui flotte autour de zéro. La conclusion ne
dépend d'aucune d'elles : elle repose sur t 0.40 sur 168 événements jamais vus.

---

## 9. Ce que ça NE PROUVE PAS

1. **Ça ne prouve pas que le CPI ne bouge pas l'or.** Il le bouge — beaucoup, et dans les deux sens :
   le gagnant moyen fait +83.3 bps, le perdant −80.4. Ce qui est réfuté, c'est qu'une position
   **longue systématique** prise la veille ait une espérance positive. La **volatilité** de
   l'événement est réelle et non testée ici (straddle, vol implicite, options — hors véhicule CFD).
2. **Ça ne teste qu'un seul sens et un seul instrument.** Aucune jambe short, aucun conditionnement
   sur la surprise (non disponible ex ante), aucun autre actif. L'argent, les taux réels (TIPS), le
   dollar ne sont pas concernés.
3. **La jambe pré-publication (+8.45 bps, t 1.84, N=230) n'est pas réfutée — elle n'est pas
   testée comme candidate.** Elle n'était pas pré-enregistrée, son t est sous le seuil, et la
   promouvoir maintenant serait exactement le data-mining que le pré-enregistrement interdit. Si
   quelqu'un veut l'ouvrir, ce sera un **angle nouveau, écrit avant la donnée**, et il devra
   affronter un coût intraday de 1.84 bps sur 8.45 bps de gross (`gross/coût 4.6`, sans swap) et une
   fréquence de 12/an. **Elle n'est pas relancée dans ce dossier.**
4. **La barrière de §7 est une borne supérieure sur une candidate rejetée**, pas une admission.
   Aucun placebo à autocorrélation appariée n'a été couru sur ces p(pass), parce que le gross ne
   tenait pas — le pré-enregistrement le conditionnait à ça.
5. **Le contrôle L58 par ratio est cassé quand l'effet est nul** (§3.2). Le verdict de ce dossier ne
   repose pas dessus, mais tout `BIASED` produit par ce critère ailleurs doit être relu en absolu.
6. **2 sorties sur 232 (Vendredis saints 2017 et 2020) couvrent un week-end** au lieu d'une nuit.
   Conservées parce que la spec est gelée ; leur retrait ne change rien à 168 événements OOS.
7. **`n_trials = 80` est une déclaration, pas une mesure.** Le DSR à 0.0000 ne dépend pas de ce
   choix : le Sharpe net plein échantillon est 0.249.
8. **Le calendrier PPI/NFP sert de contrôle, pas de candidat.** Les cellules PPI et NFP du §4 sont
   des témoins ; aucune n'est promue, et NFP-eve (+12.0 bps, t 1.48 OOS) reste un non-résultat.
9. **La couverture de prix s'arrête au 2026-06-05.** Les publications de juin et juillet 2026 sont
   dans le calendrier BLS mais hors échantillon.

---

## 10. Ce que ça réoriente

**FERMÉE : la classe ÉVÉNEMENTIELLE CALENDAIRE sur XAUUSD au tarif CFD.**
`exogenous_predictors_2026-08` avait fermé les prédicteurs d'**ÉTAT** exogènes (165 cellules, ratio
médian `gross/coût` 0.336) et laissé ouverte la famille **ÉVÉNEMENT**, « trouvée sous-échantillonnée
par un fichier d'entrée qui commence en 2020 ». Elle a été correctement sous-échantillonnée ; elle
est maintenant **correctement mesurée sur 232 événements et 14 ans jamais vus, et elle est vide**.
Le kill est **MÉCANIQUE** au sens de la politique de ré-ouverture : gross ≈ inconditionnel à coût
nul sur l'ère OOS, mécanisme réfuté par le voisinage, régime réfuté par sa propre régression.
**Non rouvrable sans un mécanisme nouveau, et pas au même angle.**

**Ce que la politique de ré-ouverture a bien fait.** Le kill d'hier était de nature **PUISSANCE**,
donc rouvrable, et le geste de déblocage était identifié, gratuit et exécutable en une session.
**Les deux issues étaient bonnes et c'est la seconde qui est sortie** : la classe se ferme
proprement, avec 232 événements et un hors-échantillon de 14 ans, au lieu de rester un « peut-être »
qu'on rouvre tous les six mois. Coût : une session. Bénéfice : plus jamais ce candidat.

**Trois leçons candidates** (nommées, non numérotées — la numérotation se fait à la réconciliation) :

- **CAND-A — « la queue récente d'un calendrier tiers est souvent synthétique ; vérifie-la contre la
  source primaire, elle est gratuite. »** 7 dates fausses sur 77, **toutes postérieures à 2025-09**,
  valant **17 %** de l'effet mesuré (38.07 → 31.59, t 3.86 → 3.21). Le début d'un fichier scrapé est
  historique et vrai ; sa fin est une **prévision** que personne n'a rebasée. Contrôle à coût nul :
  comparer les 24 derniers mois à la source officielle. Corollaire opératoire : `bls.gov` répond
  **403** à un UA de navigateur et **200** à un UA descriptif portant une adresse de contact — une
  source officielle réputée « inaccessible » l'est parfois seulement mal demandée.
- **CAND-B — « une fenêtre d'événement bookée depuis la clôture précédente n'est PAS une dérive
  pré-annonce : dis où tu coupes, et décompose des DEUX côtés du print. »** La spec s'appelait
  « veille de CPI » et traversait la publication de 08:30 ET. Décomposée : l'anticipation est stable
  et non significative (+8.9 → +7.3 bps), c'est la **réaction** qui bascule (−3.5 → **+23.3**) et qui
  porte **76 %** de l'effet « découvert ». Sans cette coupe, on aurait attribué à une prime
  d'anticipation ce qui est une **exposition directionnelle à une surprise macro**.
- **CAND-C — « le contrôle de voisinage doit être couru sur la MÊME fenêtre que le candidat, sinon
  il argumente à l'envers. »** Hier : « FOMC-eve ne donne rien en 2021-2026 (t 0.39) ⇒ l'effet est
  spécifique au CPI ». Sur 14 ans jamais vus : **FOMC +17.2 > NFP +12.0 > PPI +6.5 > CPI +3.6** — la
  veille de CPI est la plus faible des quatre. Le voisinage n'a de valeur probante que s'il partage
  l'échantillon du candidat ; comparé sur une fenêtre plus courte, il fabrique de la spécificité.

**Ledger.** Ce dossier est un **test CONFIRMATOIRE pré-enregistré**, pas un balayage : **4 essais
consommés** (les 3 ères + le contrôle de voisinage groupé), déclarés `n_trials = 80` avec les 76
cellules calendrier d'hier. Aucune cellule supplémentaire n'a été balayée. Delta à réconcilier au
compteur global à la clôture.

---

## 11. Fichiers

| fichier | contenu |
|---|---|
| `PREREGISTRATION.md` | spec gelée, kill rules chiffrées, sources de dates — **committé en `30fa8a9a`, avant toute donnée étendue** |
| `bls_cpi_release_dates.csv` | les 234 dates de publication CPI du BLS, 2007-2026 |
| `bls_date_source_concordance.csv` | source A (nom de document) vs source B (en-tête d'embargo), 234 lignes |
| `sample_hygiene.csv` | 234 → 232 entrées, sorties tombant ou non sur le jour CPI |
| `eras.csv` | les 3 ères + la réplication de 2026-08-06, batterie complète |
| `by_year.csv` | 20 années, moyenne / N / taux de réussite / net |
| `neighbourhood.csv` | CPI vs PPI vs NFP vs FOMC × 3 ères, même spec gelée |
| `d1_intraday_decomposition.csv`, `intraday_events.csv` | coupe à 08:30 ET, 230 événements |
| `d2_regime_regression.csv`, `d2_regime_quartiles.csv`, `d2_regime_inputs.csv` | l'hypothèse de régime, testée |
| `d3_barrier_upper_bound.csv` | borne supérieure p(pass) / durée sur une candidate rejetée |
| `l60_zero_range.csv` | barres M1 à fourchette nulle, par an, 2007-2026 |
| `code/` | `cpi_lib` (spec gelée recopiée verbatim) → `fetch_bls_dates` → `main_test` → `diagnostics` |

Caches de session hors dépôt (scratchpad privé) : documents BLS, M1 XAUUSD en parquet.
**Aucun blob data committé** (132 Ko au total).
