# Attribution de performance du book FTMO funded — sleeve par sleeve, contre référence

*2026-08-21 · compte <ACCOUNT_ID> ($10 000, funded) · lecture seule, aucune modification live.*
*Artefacts : `serie_mensuelle.csv`, `metriques.csv`, `correlations.csv`, `annuel.csv`,
`daily_raw.csv` (grain journalier), `diagnostics.txt`, `analyse.txt`.
Code : `build_series.py` → `metrics.py` → `analysis.py`, `/usr/bin/python3`.*

---

## 0. Trois corrections au cadrage de départ, à lire avant les chiffres

**[V] La jambe ON US100 ne sort pas à 09:00, elle sort à 15:30 Paris.** Le brief indique
« entrée 22:05, sortie ~09:00 ». Le code et le live disent autre chose, de façon
concordante :

- `book_executor.mq5:1024` — `Do1530() { if(LegLots(2)!=0.0) TradeLegTo(2, 0.0, "us100_off"); }`,
  déclenché à `hm>=1530` (`:1738`). La leg 2 est US100. `Do0900()` (`:1023`) ferme la leg **3**,
  qui est GER40.
- Réconciliation live VPS `runtime/eod/reconcile_2026-08-19.json` : segment 1 (minute 540 =
  09:00) la cible ne garde que US100 ; segment 2 (minute 930 = **15:30**) la cible est vide.
  GER40 est parti à 09:00, US100 à 15:30.

La jambe US100 est donc tenue **~17,4 h** (22:05 → 15:30 J+1), pas 11 h. Toute l'attribution
ci-dessous utilise l'horaire réel. C'est un écart matériel : la fenêtre 09:00→15:30 est la
séance européenne entière.

**[V] Le poids déployé est 0,35 exactement, pas 0,353.** Réconcilié live sur le compte funded :
2026-08-17, balance $10 538,13, cible GER40 à 17:35 = $3 685,8 ⇒ 0,3498 ; 2026-08-18, cible
GER40 $3 398,3 sur une équité de $9 709 ⇒ 0,3500. Le 0,353 du brief est le même chiffre après
quantification au lot de 0,01. J'utilise **0,35 pour la sleeve ET pour son benchmark** — c'est
la seule façon d'avoir une comparaison exacte plutôt qu'approximativement juste.

**[V] Le gouverneur ne module rien dans le régime normal.** Config funded (`spec_v22.yaml`
`/funded/config`) : `vm=1.0`, `glide=1.0`, `pace=0`, `taper=0.02`. `scale = vm × taper × glide
× pace` avec `taper = clip((eq−9000)/10000 / 0,02, 0, 1)` ⇒ à l'équité initiale,
`taper = clip(0,10/0,02)= clip(5) = 1`. **`scale = 1,000` tant que l'équité dépasse $9 200.**
Et le cap de marge (60 %) demande (0,35+0,35) × 6,667 % = **4,67 %** de l'équité, soit 13 fois
moins que le cap. Aucune des deux non-linéarités du moteur ne mord. La reconstruction linéaire
est donc **exacte** pour ce book, pas approximative — ce qui n'aurait pas été vrai à `vm=14`.

---

## 1. Périmètre, sources, et ce qui n'est PAS reconstructible

| Sleeve | Définition retenue | N trades | Fenêtre |
|---|---|---:|---|
| `on_us100` | long US100.cash, 22:05 → 15:30 J+1, lundi + mardi, sans signal | 1 316 | 2013-09 → 2026-06 |
| `on_ger40` | long GER40.cash, 17:35 → 09:00 J+1, lundi + mardi, sans signal | 970 | 2013-09 → 2026-06 |
| `orb` | breakout US100, OR 15:30-16:00, stop = côté opposé, time-stop 22:00 | 3 191 | idem |
| `xauusd` (or) | **poids ZÉRO** en config funded — éteinte | 0 | — |
| `usdjpy` (J1) | **poids ZÉRO** en config funded — éteinte | 0 | — |

**3 299 séances, 154 mois, 2013-09-25 → 2026-06-05.**

**[V] Horloge.** Le panel M5 `sim_m5_repaired.parquet` porte un index nommé `timestamp_utc`
qui n'est **pas** de l'UTC (L52 : ne jamais faire confiance au nom d'un champ). Contrôle
gratuit, profil de volatilité par demi-heure sur 2023-2026 : US100 pique à **15:30-15:59**
(ouverture cash US) et GER40 à **09:00-09:29** (ouverture Francfort). Le fichier source
`US100_m5_close.parquet` porte d'ailleurs un index tz-aware `Europe/Paris` explicite. C'est
donc bien l'horloge de Paris, celle que l'EA utilise (`ParisHM`). Aucune correction requise.

**[V] Validation croisée de source de prix.** J'ai reconstruit la jambe ON US100 une seconde
fois depuis une source **indépendante** — `data/deep_history_utc/US100_M1.csv`, barres M1
vrai-UTC avec OHLC, 4 081 739 barres — reconvertie en Europe/Paris. Sur les **N = 940** jours
ON communs : corrélation **0,952**, moyenne **10,34 bps (M1)** contre **9,99 bps (M5)**, soit un
écart de 0,35 bps sur une moyenne de 10. Le signe et l'ordre de grandeur tiennent sur deux
sources. **Mais l'écart médian par trade est de 11,1 bps (p90 : 31,6 bps)** — six fois le gain
moyen par trade de la sleeve. Cela ne casse pas l'estimation de la *moyenne* (N=940), mais
interdit toute lecture trade-par-trade.

**[V] Contrôle L60 (barres à fourchette nulle).** 1 opening-range de largeur strictement nulle
sur 3 260. Aucune contamination par des prints de règlement.

**[V] Ce qui n'est PAS reconstructible proprement — je le dis plutôt que de l'approximer :**

1. **Les données s'arrêtent au 2026-06-05.** Le cache M5 audité (`sim_m5_repaired.parquet`)
   ne va pas plus loin, et le cache live du VPS (`cache_live/2026-08-18/`) ne contient que
   des panels **journaliers** — inutilisables pour des fenêtres intraday. Il n'existe donc
   **aucune** série reconstructible sur les 2,5 mois de vie funded réelle du compte. Tout ce
   qui suit est une reconstruction historique de la spec déployée, **pas** un relevé du compte.
2. **26,5 % des jours ON n'ont pas de jambe GER40** (349 / 1 319), concentrés en 2018-2021
   (48 / 94 / 104 / 103 par an) : ce sont les trous de données GER40 masqués par le moteur
   cleanroom. `on_ger40` est donc mécaniquement sous-estimée sur ces quatre années.
   Hors 2018-2021 la jambe rend **$13,38/mois (t_HAC6 2,37)** contre $9,66 sur tout
   l'échantillon — l'écart est un artefact de données, pas un fait de marché.
3. **Le mois 2026-06 est partiel** (3 séances). Il est présent dans `serie_mensuelle.csv` mais
   il ne faut pas le lire comme un mois.
4. **[NV] Le notionnel ORB est un calcul, pas un relevé.** `lots = floor(risque / largeur_OR /
   0,01) × 0,01` reproduit `Do1600Arm` (`:1063`), avec la largeur OR mesurée sur les vraies
   barres M1 OHLC. Je n'ai aucune facture pour la vérifier. Médiane **0,49× l'équité**,
   p10-p90 **0,24×–0,97×** — soit **1,4 à 2,8 fois le notionnel d'une jambe ON**, ce qui est
   contre-intuitif pour une sleeve « à 0,25 % de risque » et mérite d'être su.

---

## 2. La convention de comparaison — le point qui décide de tout le reste

C'est ici que l'on peut truquer une attribution sans écrire un seul chiffre faux, alors je
pose la convention explicitement.

### 2.1 Pourquoi le buy-and-hold à MÊME NOTIONNEL, et pas à même risque

Une jambe ON porte $3 500 de notionnel sur un compte de $10 000. La question opérationnelle
est : *ces $3 500 exposés deux nuits par semaine rapportent-ils plus que les mêmes $3 500
exposés en permanence ?* Le comparateur doit donc être un **long US100 de $3 500 tenu en
continu**, soit `bh_us100 = 0,35 × rendement quotidien de US100`. Même instrument, même
taille, même compte — seule l'**horloge** diffère. C'est la seule différence qu'on veut
mesurer, et c'est ce que la convention isole.

Une comparaison à **même risque** (vol-matchée) fait autre chose : elle rescale le benchmark
pour égaliser les volatilités, ce qui revient à supposer qu'on peut acheter du levier gratuit.
Sur un compte funded, c'est **faux par construction** : le plancher est à −10 % de l'initial et
ne bouge jamais, donc le risque n'est pas un paramètre libre — il est rationné. Rescaler le
benchmark ×2,8 pour l'amener à la vol de la sleeve, c'est comparer la sleeve à un portefeuille
qui n'aurait jamais passé la barrière.

Mais la convention à même notionnel a un défaut symétrique, et il est massif : **la sleeve
n'est en marché que 29,2 % du temps coté** (US100 : 100,5 trades/an × 17,4 h ≈ 1 751 h sur
~6 000 h) et **19,0 %** pour GER40. Lui demander de battre en *rendement* un benchmark exposé
3,4 fois plus longtemps, c'est une comparaison perdue d'avance qui ne dit rien.

### 2.2 Donc : les deux, et chacune répond à une question différente

| Convention | Question à laquelle elle répond | Colonnes |
|---|---|---|
| **Même notionnel** (primaire) | *Vaut-il mieux tenir cette taille tout le temps ?* | `bh_us100`, `bh_ger40`, `bh_orb` |
| **Même risque** (vol-matchée) | *À budget de variance égal, l'horloge est-elle efficace ?* | `bh_volmatch_*` dans `metriques.csv` |
| **Prix brut vs prix net** | *Le carry mange-t-il la prime ?* (L36) | `bh_*` vs `bh_*_net` |

**[V] Le benchmark par défaut (`bh_*`) est un buy-and-hold de PRIX, sans coût ni swap.**
C'est délibéré : un benchmark net de swap est un adversaire artificiellement affaibli. Un long
US100 CFD tenu en continu paie 2,24 bps/nuit × 365 = **8,2 %/an de notionnel**, soit
**2,86 %/an d'équité** au poids 0,35. Sur un book qui rend 4,4 %/an, faire porter cette facture
au benchmark suffirait à fabriquer une surperformance sans le moindre alpha. Les colonnes
`bh_*_net` donnent la version réaliste — elle est dans le CSV, elle n'est pas le juge.

**[D] Prix issus de la MÊME source pour la sleeve et pour son benchmark.** Les rendements
quotidiens du sous-jacent sont recalculés depuis le panel M5 (dernière barre à dernière barre),
pas depuis `panel_px.parquet` : ces deux séries divergent de **14 bps en moyenne absolue**
(convention de clôture différente), ce qui suffirait à polluer un β.

---

## 3. Attribution — d'où vient l'argent

**Décomposition cumulée sur la vie (% d'une équité de référence de $10 000) :**

| Sleeve | Gross | Coût RT | Swap (panel) | Swap (mesuré) | **Net** |
|---|---:|---:|---:|---:|---:|
| `on_us100` | +37,02 % | −4,81 % | −8,09 % | −7,38 % | **+24,12 %** |
| `on_ger40` | +23,16 % | −3,45 % | −4,53 % | −4,72 % | **+15,18 %** |
| `orb` | — (ledger era, déjà costé) | — | — | — | **+17,41 %** |
| **portefeuille** | | | | | **+56,70 %** |

**[V] Le swap prend 20 à 22 % du gross, le coût de transaction 13 à 15 %.** Ensemble,
**33-35 % de la prime brute** part en frais. C'est L36 mesuré et non supposé — mais contrairement
aux familles tuées par L36, ici il en reste **deux tiers**, parce que la sleeve ne tient que
~104 nuits par an au lieu de 365.

### 3.1 Les deux versions du swap demandées

**[V] Ancre mesurée sur la facture réelle** (`swaps_billed_live.csv`, 4 nuits par symbole,
2026-07-21 → 2026-08-04, aucune n'étant un jour de swap triple) :

| | Panel (dernière valeur) | Facture réelle | Écart | σ de la mesure |
|---|---:|---:|---:|---|
| **GER40** | −1,607 bps/nuit | **−1,673 bps/nuit** | panel **optimiste de 4,1 %** | 0,004 (N=4) |
| **US100** | −2,241 bps/nuit | **−2,045 bps/nuit** | panel **pessimiste de 9,6 %** | 0,180 (N=4) |

Je mesure GER40 à **−1,673** et non −1,708 comme l'indiquait le brief ; la dispersion des 4
nuits est de 0,004 bps, donc l'écart n'est pas du bruit de mesure mais une différence de
périmètre (nuits retenues, ou notionnel au dénominateur). Je rapporte ma mesure.

**Effet sur le résultat : négligeable, et il joue dans les DEUX sens.** Les colonnes
`*_swapcorr` de `serie_mensuelle.csv` et les lignes correspondantes de `metriques.csv`
donnent la version re-ancrée :

- `on_ger40` : Sharpe **0,717 → 0,708** (vie) ; $9,85 → $9,73 /mois. Le panel flattait la jambe.
- `on_us100` : Sharpe **0,832 → 0,857** (vie) ; $15,66 → $16,12 /mois. Le panel la pénalisait.
- **portefeuille : 0,8327 → 0,8403.** Les deux erreurs se compensent presque exactement.

**Conclusion : l'ancre de swap périmée ne change aucune décision.** Elle déplace le Sharpe du
book de +0,008. Ce n'est pas là qu'est le risque de modèle.

### 3.2 En revanche, le coût RT du simulateur est faux d'un facteur 2

**[V]** `data/ftmo_portfolio/outputs/phase0_rt_cost_bps.csv` facture **2,2 bps RT** à tous les
indices. Mesuré en natif cette semaine : **1,045** (US100) et **1,017** (GER40). Le simulateur
qui produit les cartes d'EV **sur-pénalise les jambes ON d'un facteur 2,1**, soit :

- US100 : (2,2 − 1,045) × 0,35 × 100,5 trades/an = **+40,6 bps/an** d'équité rendus
- GER40 : (2,2 − 1,017) × 0,35 × 74,1 trades/an = **+30,7 bps/an**
- **Total ≈ +0,71 %/an** sur un book qui rend 4,42 %/an en vie et 11,84 %/an sur 2 ans.

**C'est ~16 % de l'EV du book, effacée par une constante de catalogue.** C'est le même motif
que celui déjà relevé dans `COST_AUDIT.md` (or sur-pénalisé 1,9×). Cette table mérite d'être
corrigée avant la prochaine décision d'EV — mais c'est hors périmètre ici, et je n'ai touché
à rien.

---

## 4. Métriques (`metriques.csv` — toutes les colonnes, ici l'essentiel)

### Vie complète — 154 mois, 2013-09 → 2026-06

| | `on_us100` | `on_ger40` | `orb` | **portefeuille** |
|---|---:|---:|---:|---:|
| N trades | 1 316 | 970 | 3 191 | 3 236 j |
| $/mois | **15,66** | **9,85** | **11,30** | **36,82** |
| %/mois | 0,157 % | 0,099 % | 0,113 % | 0,368 % |
| Rendement annualisé | 1,88 % | 1,18 % | 1,36 % | **4,42 %** |
| Vol annualisée | 2,26 % | 1,65 % | 4,57 % | 5,31 % |
| **Sharpe ann. (√12)** | **0,83** | **0,72** | **0,30** | **0,83** |
| Sharpe ann. (base trade) | 0,71 | 0,64 | 0,28 | 0,73 |
| Hit rate mensuel | 53,2 % | 41,6 % | 50,6 % | **61,0 %** |
| Meilleur / pire mois | +2,79 / −1,31 % | +2,41 / −1,59 % | +4,36 / −2,83 % | +4,72 / −4,02 % |
| MaxDD mensuel | −3,96 % | −1,81 % | −20,84 % | −15,02 % |
| MaxDD journalier | −5,26 % | −2,39 % | **−21,63 %** | **−15,65 %** |
| Skew mensuel | +0,71 | +1,28 | +0,33 | +0,07 |
| **Skew journalier** | **+1,52** | **+1,07** | **+1,76** | **+1,05** |
| **β vs sous-jacent** | **0,023** | **0,006** | **−0,010** | **0,029** |
| Corrélation au sous-jacent | 0,182 | 0,053 | −0,040 | 0,084 |
| **R² vs sous-jacent** | **3,33 %** | **0,28 %** | **0,16 %** | **0,71 %** |
| α HAC lag-6, $/mois | 11,95 | 9,38 | 12,94 | 32,83 |
| **t(α) HAC lag-6** | 1,74 | **2,83** | 1,01 | **2,67** |
| Excédent vs B&H même notionnel | −0,41 %/mois | −0,18 %/mois | −0,82 %/mois | −1,40 %/mois |
| **Excédent vs B&H vol-matché** | **−0,047 %/mois** | **+0,010 %/mois** | −0,298 %/mois | **−0,105 %/mois** |

### Deux dernières années — 24 mois, 2024-06 → 2026-05

| | `on_us100` | `on_ger40` | `orb` | **portefeuille** |
|---|---:|---:|---:|---:|
| N trades | 208 | 208 | 504 | 512 j |
| $/mois | 14,71 | **27,58** | **56,42** | **98,70** |
| Rendement annualisé | 1,76 % | 3,31 % | 6,77 % | **11,84 %** |
| Vol annualisée | 2,00 % | 2,17 % | 4,78 % | 6,21 % |
| **Sharpe ann. (√12)** | 0,88 | **1,53** | **1,42** | **1,91** |
| Hit rate mensuel | 62,5 % | 66,7 % | 66,7 % | **70,8 %** |
| MaxDD journalier | −2,45 % | −2,20 % | −4,64 % | **−4,11 %** |
| **R² vs sous-jacent** | **14,01 %** | 3,95 % | 5,66 % | **0,50 %** |
| **t(α) HAC lag-6** | 0,47 | 1,95 | **2,74** | **2,80** |
| **Excédent vs B&H vol-matché** | −0,118 %/mois | +0,019 %/mois | −0,070 %/mois | **+0,092 %/mois** |

### 4.1 Le fossé vie / 2 ans est le fait le plus important du tableau

**[V] Le portefeuille passe de Sharpe 0,83 à 1,91 et de 4,4 %/an à 11,8 %/an selon la fenêtre.**
Ce n'est pas du bruit, c'est structurel (`annuel.csv`) :

| Sous-période | $/mois | t_HAC6 (journalier) | N séances |
|---|---:|---:|---:|
| 2013-2017 | **−9,07** | −0,42 | 1 111 |
| 2018-2021 | +41,27 | 2,16 | 1 038 |
| 2022-2026 | **+75,06** | 3,29 | 1 150 |

**Le book perd de l'argent sur ses cinq premières années.** L'ORB en est le principal
responsable : **−6,77 % (2014), −8,76 % (2015), −2,06 % (2016)**, contre +7,39 / +6,68 / +10,53 /
+4,04 % en 2022-2025. Le MaxDD journalier de −21,63 % de l'ORB sur la vie est presque
entièrement logé là.

**[D] C'est la signature d'une spec sélectionnée sur son échantillon récent.** Je ne peux pas
prouver le data-snooping depuis cette étude — la sélection s'est faite ailleurs et le ledger
`orb_e7_Rera` est « era-costé », donc les vieux coûts y sont plus lourds, ce qui explique une
*partie* du creux. Mais **le Sharpe citable pour ce book est 0,83, pas 1,91**, et la fenêtre
2 ans doit être lue comme in-sample vis-à-vis du processus qui a choisi la config.

### 4.2 Ce que ça donne sur un compte funded réel

**[V] Trajectoire arithmétique depuis $10 000** (sizing en % d'équité, gains retirés, le
buffer ne grandit jamais) :

- Équité minimale : **$8 745,45**. Équité finale : $15 670,48.
- **93 séances sur 3 299 passent sous $9 000**, la première le **2015-09-03**.
- **Un compte funded réel aurait été TERMINÉ le 2015-09-03.** Le plancher statique −10 % est
  la contrainte liante.
- Pire journée : **−$160,71**. **Zéro** séance dépasse la perte quotidienne max de $500.
  **La règle des −5 % quotidiens n'a jamais mordu, pas une fois en 3 299 séances.**

**[V] Et le skew joue dans le bon sens sur les deux horizons** — ce qui est rare et mérite
d'être dit (L39 : le daily lie la barrière FTMO, le monthly le book perso ; les deux doivent
être rapportés). Skew **journalier +1,05** pour le portefeuille (+1,52 / +1,07 / +1,76 pour les
sleeves) et skew **mensuel +0,07**. Le book n'a pas le profil « ramasse-miettes devant le
rouleau compresseur » qui tue les comptes à barrière : ses queues sont à droite.

C'est une dissociation utile : ce book meurt d'accumulation lente, jamais d'un choc quotidien.
Toute protection intraday (breaker M5, cap de taille journalier) protège contre un risque qui
ne s'est jamais matérialisé, tandis que le risque réel — la dérive vers le plancher — n'est
adressé que par le taper.

### 4.3 Bootstrap par blocs (21 séances, 5 000 tirages — jamais iid)

| | Vie : moyenne [IC95] | 2 ans : moyenne [IC95] |
|---|---|---|
| `on_us100` | 15,35 [**5,57 ; 26,37**] | 14,34 [−11,28 ; 40,99] **contient zéro** |
| `on_ger40` | 9,66 [**2,61 ; 17,60**] | 26,88 [0,71 ; 59,12] |
| `orb` | 11,08 [−8,57 ; 30,56] **contient zéro** | 55,00 [9,57 ; 114,40] |
| **portefeuille** | **36,10 [12,34 ; 59,56]** | **96,22 [28,05 ; 176,26]** |

**Le portefeuille exclut zéro sur les deux fenêtres. Aucune sleeve individuelle n'exclut zéro
sur les deux.** L'agrégation fait le travail — ce qui est cohérent avec la matrice de
corrélation ci-dessous, et c'est le seul argument solide en faveur du book tel qu'il est.

---

## 5. Corrélations (`correlations.csv` — 3 blocs : mensuel vie, mensuel 2 ans, journalier vie)

**Mensuel, vie complète :**

| | `on_us100` | `on_ger40` | `orb` | `und_us100` | `und_ger40` |
|---|---:|---:|---:|---:|---:|
| `on_us100` | 1,000 | 0,280 | −0,060 | 0,182 | −0,048 |
| `on_ger40` | 0,280 | 1,000 | −0,091 | 0,146 | 0,053 |
| `orb` | −0,060 | −0,091 | 1,000 | −0,040 | 0,050 |
| `portefeuille` | 0,461 | 0,352 | **0,807** | 0,089 | 0,039 |

**[V] Trois observations :**

1. **Les sleeves sont quasi orthogonales entre elles.** Les deux jambes ON corrèlent à 0,28
   (même facteur : la prime overnight actions) ; l'ORB corrèle à **−0,06 / −0,09** avec elles.
2. **Aucune sleeve ne corrèle à son sous-jacent** au-delà de 0,18. Au niveau journalier c'est
   encore plus net : 0,065 / 0,074 / −0,015.
3. **L'ORB domine la variance du book** (ρ = 0,807 avec le portefeuille, contre 0,46 et 0,35
   pour les jambes ON) et porte **57,2 % de la valeur sur 2 ans** (30,7 % sur la vie). Ce
   chiffre reproduit indépendamment le « l'ORB porte la moitié de la valeur funded » déjà
   consigné en mémoire — cross-check utile sur deux calculs sans rapport.

**Conséquence : ce book funded n'est PAS mono.** La qualification « livre MONO » de la mémoire
porte sur la config *challenge* (ORB éteint comme sleeve P&L, or à 0, J1 off) ; en funded,
`orb_risk = 0,0025` est actif et apporte un troisième moteur décorrélé. C'est visible dans les
métriques : hit rate mensuel 61,0 % pour le portefeuille contre 53,2 / 41,6 / 50,6 % pour les
sleeves prises isolément, et Sharpe 0,83 pour un book dont deux composantes sont à 0,72 et 0,30.

---

## 6. La question qui compte : bêta ou alpha ?

### 6.1 Le test L38, littéralement

| Sleeve | β vs sous-jacent | **R²** | Verdict L38 (seuil 30 %) |
|---|---:|---:|---|
| `on_us100` | 0,023 (t 2,08) | **3,33 %** | orthogonal |
| `on_ger40` | 0,006 (t 0,68) | **0,28 %** | orthogonal |
| `orb` | −0,010 (t −0,48) | **0,16 %** | orthogonal |
| `portefeuille` | 0,029 (t 1,04) | **0,71 %** | orthogonal |

**[V] Aucune sleeve n'approche le seuil de 30 %.** Sur 2 ans le maximum est `on_us100` à
**14,0 %** — toujours sous le seuil, mais quatre fois la valeur de long terme, ce qui indique
que la jambe US100 est devenue nettement plus bêta récemment.

### 6.2 Sauf que ce test seul est trompeur ici, et il faut le dire

**L'α HAC dégénère quand β ≈ 0.** Avec β = 0,023, l'α de la régression vaut mécaniquement
`moyenne(sleeve) − 0,023 × moyenne(bh)`, soit **99 % de la moyenne de la sleeve elle-même**.
Son t de 2,83 (`on_ger40`) ou 2,67 (portefeuille) ne teste **pas** « la sleeve bat son
benchmark » : il teste « la moyenne de la sleeve est non nulle ». Ce sont deux affirmations
différentes, et présenter la seconde comme la première serait le tour de passe-passe classique
d'une attribution. **Un R² bas et un α significatif ne prouvent pas de l'alpha ; ils prouvent
seulement que la sleeve gagne un peu d'argent en étant peu exposée.**

### 6.3 Le vrai test : la fenêtre bat-elle le fait de tenir à travers ?

C'est le test qui tranche, et il ne coûte rien : sur les **mêmes jours ON**, au **même
notionnel**, comparer le rendement de la fenêtre effectivement tenue à celui d'un buy-and-hold
24 h couvrant le même intervalle. Prix bruts, sans coût : si la fenêtre n'ajoute rien, il n'y a
pas de timing — seulement moins de bêta.

| | `on_us100` (N=1 316) | `on_ger40` (N=970) |
|---|---:|---:|
| Fenêtre tenue | **+8,04 bps** (t_HAC6 **4,39**) | **+6,82 bps** (t_HAC6 **3,83**) |
| 24 h, même intervalle | **+11,58 bps** (t_HAC6 3,68) | **+8,12 bps** (t_HAC6 2,57) |
| **Différence** | **−3,54 bps** (t_HAC6 **−1,28**) | **−1,30 bps** (t_HAC6 **−0,43**) |
| Part de la variance 24 h captée | **34,1 %** | **29,9 %** |
| Corrélation fenêtre / 24 h | 0,422 | 0,275 |

**[V] La réponse est franche : ce n'est pas de l'alpha. C'est du bêta tranché à l'horloge.**

La fenêtre tenue **sous-performe** le fait de simplement tenir à travers, des deux côtés
(−3,54 et −1,30 bps), sans significativité. Il n'y a **aucun timing** : l'horloge ne sélectionne
pas de rendement. Le prédicteur du gain de la sleeve est le rendement du sous-jacent sur
l'intervalle, point.

**Ce que l'horloge fait, en revanche, est réel et mesurable :** elle achète **69 % / 84 % du
rendement** pour **34 % / 30 % de la variance**. Rapporté en ratio de Sharpe, la fenêtre est
**1,19× (US100) et 1,54× (GER40)** plus efficace par unité de risque que la tenue continue sur
le même intervalle. Ce n'est pas rien — sur un compte à barrière c'est précisément la bonne
monnaie — mais **c'est une propriété de compression de risque, pas une prime**.

D'où le paradoxe apparent des lignes « excédent » du §4, maintenant résolu :

- **Contre le B&H à même notionnel, les trois sleeves PERDENT** (−0,41 / −0,18 / −0,82 %/mois,
  et −1,40 %/mois pour le book). C'est arithmétique : le benchmark est en marché 3,4 fois plus
  longtemps. Ce chiffre ne condamne rien, il mesure juste l'écart d'exposition.
- **Contre le B&H vol-matché, elles font jeu égal** : −0,047 %/mois (`on_us100`), **+0,010 %/mois**
  (`on_ger40`), −0,105 %/mois (portefeuille) sur la vie ; **+0,092 %/mois** (portefeuille) sur
  2 ans. À budget de variance égal, le book ne bat **pas** un long US100/GER40 dé-levié.

### 6.4 Ce que ça implique, sans détour

**Les jambes ON sont exactement ce que l'hypothèse par défaut prévoyait : une prime de risque
overnight actions, capturée sur une fenêtre horaire, sans signal.** Elles ne créent pas de
rendement — elles en prélèvent une fraction efficace. La bonne façon de les nommer est
« exposition calendaire vol-efficiente au bêta actions », pas « sleeve ». C'est la même
discipline que L37 (nommer une sleeve pour ce qu'elle est).

**Trois conséquences opérationnelles [D] :**

1. **Ces jambes ne diversifient rien contre un book actions.** Leur R² au sous-jacent est bas
   *parce qu'elles sont peu exposées*, pas parce qu'elles sont d'une autre nature. Contre un
   long actions, elles sont du bêta à 0,023 — mais du bêta pur.
2. **Le seul argument qui tient pour elles est la géométrie de barrière, pas le rendement.**
   Compresser 66-70 % de la variance en gardant 69-84 % du rendement est exactement ce qu'une
   barrière FTMO récompense. C'est cohérent avec le constat déjà consigné que ~60 % du p(pass)
   vient de la géométrie et non de l'alpha.
3. **L'ORB, lui, est la seule composante réellement orthogonale** (β −0,010, ρ −0,06/−0,09 avec
   les jambes ON, ρ −0,015 au sous-jacent en journalier). Mais c'est aussi la seule dont l'IC95
   bootstrap **contient zéro sur la vie** [−8,57 ; +30,56], et celle qui porte le MaxDD de
   −21,63 %. Le book funded est donc : **deux tranches de bêta efficaces mais sans prime propre,
   plus un moteur orthogonal dont la significativité repose sur les quatre dernières années.**

### 6.5 Marge au coût — le gate qui a tué les familles précédentes

| | gross/trade (bps de notionnel) | coût total/trade | **ratio** |
|---|---:|---:|---:|
| `on_us100` | 8,04 | 2,80 (RT 1,045 + swap 1,756) | **2,87** |
| `on_ger40` | 6,82 | 2,35 (RT 1,017 + swap 1,335) | **2,90** |

**[V] Les deux jambes sont juste SOUS le gate L11b (`E[gross] > 3 × coût`).** Elles ne sont pas
cost-dead — le ratio 2,9 est très loin des 0,36-0,38 mesurés à répétition sur le FX (L43, qui
est **strictement FX** et que je ne cite ici que comme échelle, jamais comme verdict). Mais la
marge est mince : **un doublement du swap ou du spread annule l'edge**. C'est aussi pour ça
que l'erreur de 2,1× sur la table de coût du simulateur (§3.2) n'est pas anodine.

---

## 7. Limites — ce que ce rapport ne prouve pas

1. **[NV] Rien ici n'est un relevé du compte funded.** Les données s'arrêtent au 2026-06-05, le
   compte est funded depuis le 2026-08-12. C'est une reconstruction historique de la spec.
2. **[V] Le live montre déjà un écart non expliqué.** `reconcile_log.csv` VPS, 2026-08-17 :
   `pnl_real −538,93` contre `pnl_model −7,14`, **`unexplained = −532,59`**, avec
   `consec_unexplained = 1`. Le solde passe de $10 538 à $9 999 en une séance ON. Diagnostic
   hors périmètre, mais aucun chiffre de ce rapport ne doit être présenté comme validant le
   modèle contre le live tant que cette ligne n'est pas élucidée.
3. **[D] La fenêtre 2 ans est in-sample** vis-à-vis du processus qui a sélectionné la config
   (§4.1). Le Sharpe citable est **0,83**, pas 1,91.
4. **[V] `on_ger40` est sous-estimée** de par les trous 2018-2021 (26,5 % des jours ON) :
   $9,66/mois publié contre $13,38/mois hors trous.
5. **[NV] Le ledger ORB reste une entrée exogène.** Il est era-costé et je ne l'ai pas
   reconstruit. Le point L59 (sorties remplies au stop exact) a été re-mesuré ailleurs sur ce
   même ledger : **1,5 %** de barres de stop ouvrant au-delà, effet **−0,0024 R/trade**,
   Δp(campagne) **+0,00 pt**. Le piège existe, il est quantifié, il est immatériel ici.
6. **Multiplicité.** Ce travail est une **attribution**, pas une recherche d'edge : aucune
   hypothèse nouvelle n'a été testée, aucun paramètre n'a été balayé, le compteur n_tests
   n'est pas incrémenté.

---

## Reproduction

```
cd Multi_Asset/research/active/funded_1y_mono_2026-08/attribution
/usr/bin/python3 build_series.py    # -> daily_raw.csv          (~5 s + lecture M1 300 Mo)
/usr/bin/python3 metrics.py         # -> serie_mensuelle.csv, metriques.csv, correlations.csv
/usr/bin/python3 analysis.py        # -> analyse.txt, annuel.csv
```

Entrées (toutes en lecture seule) : `data/ftmo_portfolio/cache/{sim_m5_repaired,sim_m5,
panel_swapL,panel_mult,orb_e7_Rera}.parquet`, `data/ftmo_portfolio/swaps_billed_live.csv`,
`data/deep_history_utc/US100_M1.csv`, `data/ftmo_portfolio/v22/spec_v22.yaml`,
`ftmo_live/mt5/book_executor.mq5`, et en lecture SSH `ftmo_live/runtime/eod/*.json` +
`reconcile_log.csv` du VPS.
