# Queue gauche à une nuit & calendrier d'événements — sleeves overnight US100/GER40

**Date** : 2026-08-09 · **Périmètre** : risque de queue gauche à 1 nuit face aux barrières FTMO, puis
calendrier à date connue jusqu'au 2026-09-20.
**Statut** : carte de risque. Aucune recommandation de trading, aucun seuil inventé.

---

## 0. Vérification préalable de fuseau — le piège n'a pas mordu, mais il était là

Le projet documente que des panels étiquetés `timestamp_utc` sont en réalité EET/EEST (L52, L56).
J'ai testé au tick avant toute découpe horaire, par la méthode DST (L56) : localiser le pic d'activité
intraday séparément en hiver (DJF) et en été (JJA). Une horloge européenne DST-suiveuse fixe le pic au
même index-minute ; du vrai UTC le décale d'une heure.

| série | pic hiver | pic été | décalage DST | corr. profils H/É | verdict |
|---|---|---|---|---|---|
| `sim_m5_repaired.US100` | 15:30 | 15:30 | **0 min** | 0.988 | **horloge CET/CEST** |
| `sim_m5_repaired.GER40` | 08:00 / 09:00 | 08:00 / 09:00 | **0 min** | — | **horloge CET/CEST** |
| `deep_history_utc.US100` | 14:30 | 13:30 | **−60 min** | 0.549 | **vrai UTC** (conforme au MANIFEST) |

Lecture : sur `sim_m5_repaired`, l'ouverture cash US tombe à 15:30 été comme hiver (= 09:30 ET dans les
deux régimes DST) et Xetra à 09:00 — ce serait 16:30 et 10:00 en EET. **L'index est donc du CET malgré
son nom `timestamp_utc`**, et l'hypothèse du moteur cleanroom (`SCHED_MIN` lus directement sur l'index)
est correcte. `deep_history_utc` est bien du vrai UTC. Les deux sources sont utilisables, mais **pas
avec la même convention** — la conversion est explicite dans `05_calendar.py` (le calendrier du repo est
en UTC, le panel M5 en CET).

Code : `code/01_tz_verify.py` → `out/tz_verify.json`.

---

# VOLET A — LA QUEUE GAUCHE À UNE NUIT

## 1. Géométrie retenue, et une correction à apporter au brief

Sleeve reconstruit d'après `data/ftmo_portfolio/v22/spec_v22.yaml` (`challenge.schedule_cet`) :
GER40 17:35 → 09:00 J+1, US100 22:05 → 15:30 J+1, entrées lundi et mardi uniquement, long, sans signal.
**1 292 nuits** exploitables, 2013-09-30 → 2026-06-02 (US100 n=1 222, GER40 n=945 après masque des
trous 2018-2021).

Arithmétique des barrières sur un compte P2 frais à 10 000, vérifiée contre le code
(`ftmo_live/lib/invariants.py`, tests `test_invariants_governor.py:207`) :

| seuil | valeur | source |
|---|---|---|
| budget quotidien | 500 | `E.DAILY_BUDGET` = 5 % × initial |
| **limite quotidienne (BUST)** | **9 500** | `daily_floor(10000)` |
| plancher statique | 9 000 | `static_floor(10000)` = 90 % initial |
| **limite dure effective** | **9 500** | `lim_eff = max(daily, statique)` |
| ligne de breaker v2.4 | **9 650** | `breaker_line(10000, 0.30)` — **votre arithmétique est exacte** |

**Correction au brief.** Le compte n'est **pas à 1 000 de la mort**, il est **à 500**. Sur un P2 frais,
`lim_eff = max(9 500 ; 9 000) = 9 500` : c'est la **limite quotidienne** qui mord, pas le plancher. Le
plancher 9 000 ne devient la contrainte liante qu'une fois la balance descendue sous 9 500 — c'est-à-dire
après un breach quotidien qui aura déjà tué la tentative. Le « −10 % » n'est donc pas une seconde vie ;
il n'est atteignable qu'en franchissant d'un seul mouvement une barrière située 500 plus haut.

Point de méthode qui simplifie tout : la balance ne bouge que sur du réalisé. Les jambes sont ouvertes
le soir et fermées le lendemain, donc **la balance est inchangée à 00:00 CET** et l'ancre quotidienne
vaut 10 000 les deux jours civils de la nuit. **Une seule barrière effective à 9 500 couvre toute la
détention**, et la perte comptée court depuis l'entrée (17:35 / 22:05), pas depuis minuit.

### 1bis. Le levier est le paramètre le plus incertain du dossier

Dérivé de la spec : notionnel/équité par jambe = `on_w × vm × p2_mult` = 0.6 × 14 × 1.2 = **10.08×**
(les multiplicateurs taper/glide/pace valent 1 sur un compte neuf). Votre 10.6× est cohérent. **Mais
les deux jambes se chevauchent de 22:05 à 09:00**, donc le brut du livre atteint **≈ 21× l'équité**.

Le cap de marge à 60 % ne tranche pas dans le même sens selon le taux appliqué :

- taux **policy** du moteur (2 %) : 2 × 10.6 × 0.02 = 0.42 ≤ 0.60 → **ne mord pas**, 10.6×/jambe tient ;
- taux **Swing mesurés sur le compte armé** <ACCOUNT_ID> (6.667 %, `spec_v22.yaml:margin_rates.swing_measured`,
  lu 2026-07-24) : 2 × 10.6 × 0.066667 = 1.41 > 0.60 → **scaling ×0.446 → 4.5×/jambe**.

La spec le dit elle-même : « la grille de lots vm14 est de-levée ×0.3-0.5 par le cap 60% »
(`recost_v221.headline_margin_swing`, Δp(pass) −15.6 pt). Et l'EA enforce au taux **serveur** via
`OrderCalcMargin`. **Il est donc probable que le compte tourne à ~4.5×/jambe et non 10.6×.** Tout ce qui
suit est produit aux deux leviers ; l'écart entre les deux est un facteur ~2.5 sur la fréquence de mort.
C'est le premier chiffre à faire confirmer avant d'utiliser le reste.

## 2. Distribution des rendements de nuit

En bps de notionnel par jambe. « MAE » = minimum du P&L flottant combiné le long du chemin M5 — c'est
**lui** que la barrière mord, pas le rendement de clôture.

| objet | n | moy | σ | skew | kurt. exc. | p5 | p1 | p0.1 | min |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| US100 nuit (entrée→sortie) | 1 222 | +8.96 | 74.4 | 0.91 | 7.2 | −103.9 | −185.6 | −260.6 | −294.7 |
| GER40 nuit (entrée→sortie) | 945 | +6.71 | 60.6 | 0.43 | 8.0 | −90.2 | −157.3 | −262.4 | −286.0 |
| **combiné brut** | 1 292 | +13.4 | 101.9 | 0.87 | 7.2 | −138.0 | −254.2 | −375.5 | −384.7 |
| **combiné net** (RT 2.2 bps + swap) | 1 292 | **+6.54** | 101.9 | 0.86 | 7.2 | −146.0 | −261.5 | −383.6 | −392.8 |
| **combiné MAE (chemin M5)** | 1 292 | **−60.2** | 73.7 | **−3.44** | **21.6** | −205.3 | −318.9 | −710.0 | **−846.8** |
| pire saut M5 unique | 1 292 | −55.3 | 69.1 | −4.07 | 27.2 | −187.5 | −349.4 | −513.2 | −902.2 |
| saut du halt 22:45→00:05 | 1 292 | +0.03 | 13.4 | 2.10 | 65.7 | −11.6 | −35.3 | −112.1 | **−134.9** |

Trois choses à retenir. (a) Le rendement de clôture est **positif en moyenne et positivement skewé** ;
la MAE est **fortement négativement skewée** (−3.44) et **leptokurtique** (21.6). L'edge et le risque ne
vivent pas dans le même objet : on gagne à la sortie, on meurt en chemin. (b) Le coût all-in mange la
moitié de la moyenne (+13.4 → +6.5 bps), dont le swap long sur deux indices. (c) Le saut du halt a une
kurtose de **65.7** : un objet quasi toujours nul, avec une queue extrême.

## 3. Réponses aux trois questions, en chiffres

Seuils exprimés en mouvement **combiné** requis (somme des deux jambes), à L = 10.6×/jambe :

| seuil | mouvement combiné requis | % des nuits — **MAE** (chemin) | % des nuits — clôture | fréquence |
|---|--:|--:|--:|---|
| **1. breaker 9 650** (−3.5 % équité) | **−0.330 %** | **51.5 %** | 28.6 % | ~1 nuit sur 1.9 |
| **2. daily/BUST 9 500** (−5 %) | **−0.472 %** | **40.5 %** | 22.5 % | ~1 nuit sur 2.5 |
| **3. plancher 9 000** (−10 %) | **−0.943 %** | **20.0 %** | 10.5 % | ~1 nuit sur 5 |

Autrement dit : à 10.6×/jambe, **il suffit d'un mouvement combiné de 47 points de base pour tuer la
tentative** — soit environ −0.24 % en moyenne sur chacune des deux jambes. C'est un mouvement banal :
la médiane de la MAE est déjà à −36.6 bps, soit −3.9 % d'équité, les trois quarts du budget quotidien
consommés une nuit sur deux.

À L = 4.5×/jambe (hypothèse marge Swing) les mêmes seuils demandent −0.778 % / −1.111 % / −2.222 %, et
la mortalité tombe d'un facteur ~2.5 (tableau §4).

### Question 3 en détail — le gap tue-t-il avant le breaker ?

**Oui, et le mécanisme est celui du breach 531358816.** J'ai classé, pour chaque nuit qui touche 9 500,
si le breaker avait une barre M5 pour agir :

| mécanisme | n (sur 523 nuits qui touchent 9 500 @10.6×) | part |
|---|--:|--:|
| **graduel** — l'équité franchit 9 650 sur une barre, puis 9 500 sur une barre ultérieure : le breaker avait la main | 349 | 66.7 % |
| **saut** — la barre précédente était au-dessus de 9 650, la suivante déjà sous 9 500 : aucune barre exploitable | 135 | 25.8 % |
| **halt** — le saut se produit à travers la pause de cotation (~22:45→00:05 CET), où il n'existe littéralement aucune barre | 39 | 7.5 % |

**Un tiers des morts (174/523, 33.3 %) ne laisse aucune fenêtre d'armement au breaker discret.** Ces
sauts se concentrent à l'horodatage 23:00 (55 cas, fermeture de session CFD), 08:00 (19 cas, ouverture
européenne) et 00:05 (9 cas, reprise post-halt) — c'est-à-dire **aux frontières de session, exactement
là où la sleeve tient une position**.

Le saut du halt seul — intradable par construction, personne ne peut sortir pendant une pause de
cotation — suffit à consommer tout le budget quotidien sur **9 nuits** de l'échantillon (0.70 %), et à
franchir le plancher 9 000 sur **3 nuits**. Pire réalisation : **−134.9 bps combinés**, soit **−14.3 %
d'équité en un seul saut** à 10.6× : au-delà des deux barrières simultanément.

**Le même mécanisme s'applique bien à un gap d'indice.** Le post-mortem <ACCOUNT_ID> établit que le moniteur
FTMO est **continu** alors que le breaker EA n'évalue que sur la grille M5 (`InvariantCheckM5`,
`OnTimer:1499`) : sur le flash USDJPY, la dernière lecture M5 voyait le compte 32 pips au-dessus de la
ligne d'armement, la suivante arrivait 19 s après la liquidation FTMO. Rien dans ce mécanisme n'est
spécifique au FX. Il est **plus sévère** sur un gap d'ouverture d'indice, parce que le trou de cotation
y est structurel (pause quotidienne, week-end) et non accidentel.

**Caveat majeur, dans le sens défavorable.** Mon calcul est lui aussi M5-discret : il ne voit pas ce qui
se passe *entre* deux barres, et il suppose un fill au prix de la barre suivante. Le post-mortem conclut
explicitement que « le sim sous-estime cette queue ». **Les 13.2 % de bust-malgré-breaker ci-dessous sont
donc un plancher, pas une estimation centrale.**

## 4. Fréquence historique, par sous-période

Nuits lundi/mardi, sur 1 292 nuits (~103/an). « sans breaker » = l'équité touche 9 500 à un moment du
chemin ; « malgré breaker » = le breaker s'est armé mais le fill (barre suivante) est déjà sous 9 500.

**L = 10.6× / jambe (géométrie spec, marge policy)**

| période | n nuits | breaker armé | bust sans breaker | **bust malgré breaker** | plancher 9 000 franchi |
|---|--:|--:|--:|--:|--:|
| 2013-2017 | 440 | 186 (42.3 %) | 143 | **41 (9.3 %)** | 9 |
| 2018-2019 | 197 | 105 (53.3 %) | 86 | **44 (22.3 %)** | 21 |
| 2020-2021 | 198 | 97 (49.0 %) | 74 | **39 (19.7 %)** | 14 |
| 2022-2023 | 206 | 136 (66.0 %) | 116 | **23 (11.2 %)** | 0 |
| 2024-2026 | 251 | 142 (56.6 %) | 104 | **24 (9.6 %)** | 3 |
| **total** | **1 292** | **666 (51.6 %)** | **523 (40.5 %)** | **171 (13.2 %)** | **47** |

**L = 4.5× / jambe (cap marge Swing mesuré)**

| période | n nuits | breaker armé | bust sans breaker | **bust malgré breaker** | plancher franchi |
|---|--:|--:|--:|--:|--:|
| 2013-2017 | 440 | 84 (19.1 %) | 49 | **20 (4.6 %)** | 2 |
| 2018-2019 | 197 | 57 (28.9 %) | 32 | **19 (9.6 %)** | 6 |
| 2020-2021 | 198 | 52 (26.3 %) | 32 | **14 (7.1 %)** | 4 |
| 2022-2023 | 206 | 76 (36.9 %) | 53 | **12 (5.8 %)** | 1 |
| 2024-2026 | 251 | 69 (27.5 %) | 39 | **4 (1.6 %)** | 0 |
| **total** | **1 292** | **338 (26.2 %)** | **205 (15.9 %)** | **69 (5.3 %)** | **13** |

Traduit en durée de campagne — la règle FTMO impose **4 jours de trading minimum**, soit au moins
**4 nuits ON** (deux semaines de lundis/mardis) :

| levier | p(bust) par nuit | survie à 4 nuits | survie à 8 nuits |
|---|--:|--:|--:|
| 10.6×/jambe | 13.24 % | **56.7 %** | 32.1 % |
| 4.5×/jambe | 5.34 % | **80.3 %** | 64.5 % |

2018-2019 est la pire sous-période (22.3 % de mort par nuit à 10.6×), pas 2020-2021 : la queue n'est pas
là où la mémoire collective la place. 2022-2023 affiche le taux d'armement le plus haut (66 %) mais **zéro**
franchissement du plancher — beaucoup de bruit, peu de sauts.

## 5. Le régime prédit-il la queue ? Oui — et la variable utile est gratuite

Tout est décalé à T−1, donc connu à la pose du risque. Le print VIX de 16:15 ET est **postérieur** à
l'entrée US100 de 22:05 CET (= 16:05 ET) : seule la clôture de la veille est utilisable, c'est ce qui
est fait.

**Structure par terme VIX/VIX3M (T−1)** — le conditionneur le plus net :

| VIX/VIX3M | n | MAE moy (bps) | MAE p5 | MAE p1 | **% bust** | % plancher |
|---|--:|--:|--:|--:|--:|--:|
| ≤ 0.85 (contango marqué) | 445 | −43.0 | −154.6 | −249.8 | **8.3 %** | 1.8 % |
| 0.85 – 0.95 | 600 | −56.7 | −191.7 | −289.8 | **13.2 %** | 3.7 % |
| 0.95 – 1.00 | 149 | −86.5 | −237.6 | −358.6 | **16.8 %** | 4.7 % |
| **> 1.00 (backwardation)** | 98 | **−128.0** | **−370.6** | **−791.6** | **30.6 %** | **10.2 %** |

Le taux de mort passe de 8.3 % à **30.6 %** — un facteur 3.7 — entre contango marqué et backwardation.
Le p1 de la MAE triple (−250 → −792 bps). C'est **la variable la plus discriminante du dossier**, et elle
est publique et gratuite.

**Volatilité réalisée 20j US100 (T−1)** — monotone mais plus mou :

| quartile | n | MAE moy | MAE p1 | % breaker | % bust |
|---|--:|--:|--:|--:|--:|
| Q1 (bas) | 343 | −44.8 | −250.0 | 42.0 % | 9.9 % |
| Q2 | 308 | −56.6 | −305.5 | 46.4 % | 12.3 % |
| Q3 | 316 | −58.4 | −307.6 | 54.1 % | 12.7 % |
| Q4 (haut) | 323 | −84.4 | −370.7 | 64.1 % | 18.3 % |

**Distance au plus haut historique US100 (T−1)** — et le signe est contre-intuitif :

| distance au plus haut | n | MAE moy | MAE p1 | % breaker | % bust | clôture moy |
|---|--:|--:|--:|--:|--:|--:|
| > 10 % sous le plus haut | 366 | −75.8 | −376.2 | 60.1 % | 12.8 % | +20.8 bps |
| 5 – 10 % sous | 236 | −72.4 | −326.1 | 59.3 % | **16.1 %** | +5.9 |
| 2 – 5 % sous | 234 | −61.1 | −377.3 | 48.7 % | 15.0 % | +1.9 |
| **au plus haut (< 2 %)** | 456 | **−42.8** | −236.9 | **42.1 %** | **11.2 %** | −2.2 |

**Être au plus haut est le régime le PLUS sûr de l'échantillon**, pas le plus fragile : MAE moyenne
presque deux fois plus faible qu'à −10 %, et le taux de bust le plus bas. En contrepartie, c'est aussi le
seul bucket où le rendement de clôture moyen est **négatif** (−2.2 bps) : la prime overnight est payée
dans les régimes stressés, pas au sommet. C'est la signature exacte de L54 — le régime qui prédit la
variance prédit la moyenne **dans le même sens**, donc couper le risque en régime stressé retranche
précisément les nuits qui paient.

## 6. Les 20 pires nuits

MAE combinée en bps ; `min_eq` = équité minimale atteinte à 10.6×/jambe sans aucun stop.

| date | jour | US100 | GER40 | MAE | pire saut M5 | halt | RV20 | dist. plus haut | VIX(T−1) | VIX/3M | min_eq | contexte |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| 2016-11-08 | mar | −62.7 | −286.0 | **−846.8** | −902.2 | 0.0 | 13.6 | −2.8 % | 18.7 | 1.03 | **1 024** | élection présidentielle US |
| 2025-04-08 | mar | +1.6 | −261.0 | −789.9 | −121.3 | 0.0 | 35.9 | −21.4 % | 47.0 | 1.27 | 1 627 | choc tarifaire |
| 2018-10-09 | mar | −75.8 | −10.8 | −515.3 | −513.9 | −4.7 | 12.9 | −4.0 % | 15.7 | 0.95 | 4 538 | correction oct. 2018 |
| 2016-01-19 | mar | −126.6 | −258.1 | −508.5 | −401.8 | 0.0 | 14.0 | −12.3 % | 27.0 | 1.01 | 4 610 | choc Chine/pétrole |
| 2015-08-31 | lun | −210.7 | −171.0 | −461.9 | −434.7 | 0.0 | 32.4 | −8.0 % | 26.0 | 1.03 | 5 103 | suite du 24/08 |
| 2026-03-02 | lun | −181.1 | −179.6 | −411.0 | −33.4 | 0.0 | 21.9 | −4.4 % | 19.9 | 0.92 | 5 644 | — |
| 2022-05-23 | lun | −229.8 | −119.9 | −388.7 | −252.1 | 0.0 | 46.3 | −28.6 % | 29.4 | 0.95 | 5 880 | bear market 2022 |
| 2020-03-17 | mar | −131.3 | — | −385.2 | −86.4 | **−115.3** | 7.7 | −27.8 % | 82.7 | 1.22 | 5 917 | COVID |
| 2022-06-21 | mar | −61.9 | −161.1 | −371.4 | −66.8 | 0.0 | 44.1 | −32.0 % | 31.1 | 0.96 | 6 063 | — |
| 2020-03-31 | mar | −240.6 | — | −368.0 | −367.0 | −39.2 | 95.0 | −18.8 % | 57.1 | 1.11 | 6 099 | COVID |
| 2025-04-15 | mar | −183.2 | −54.8 | −361.2 | −155.3 | 0.0 | 57.0 | −15.2 % | 30.9 | 1.04 | 6 171 | choc tarifaire |
| 2022-03-07 | lun | −0.1 | −43.5 | −344.7 | −55.0 | −11.0 | 34.1 | −16.5 % | 32.0 | 0.99 | 6 346 | invasion Ukraine |
| 2018-10-22 | lun | −170.3 | −155.6 | −339.5 | −46.0 | +5.0 | 25.6 | −7.2 % | 19.9 | 1.00 | 6 401 | — |
| 2025-11-03 | lun | −178.0 | −147.7 | −336.3 | −39.1 | 0.0 | 20.3 | −1.0 % | 17.4 | 0.85 | 6 435 | — |
| 2020-03-10 | mar | −242.3 | — | −333.0 | −73.0 | **−134.9** | 7.7 | −18.2 % | 54.5 | 1.27 | 6 470 | COVID |
| 2018-12-03 | lun | −50.6 | −18.4 | −332.3 | −342.2 | −34.0 | 34.4 | −9.3 % | 18.1 | 0.96 | 6 478 | déc. 2018 |
| 2026-03-23 | lun | −40.8 | −129.5 | −314.6 | −62.5 | 0.0 | 17.6 | −8.5 % | 26.8 | 0.98 | 6 665 | — |
| 2018-11-19 | lun | −222.7 | −63.9 | −312.9 | −210.6 | −47.6 | 32.7 | −10.4 % | 18.1 | 0.94 | 6 683 | — |
| 2025-11-17 | lun | −64.3 | −146.2 | −308.8 | −59.0 | 0.0 | 19.6 | −4.3 % | 19.8 | 0.92 | 6 726 | — |
| 2018-06-18 | lun | −99.6 | −158.6 | −308.0 | −59.0 | −8.1 | 15.9 | −0.3 % | 12.0 | 0.83 | 6 735 | — |

La pire nuit de l'échantillon est **l'élection présidentielle américaine du 8 novembre 2016** — une nuit
de mardi, entrée à 22:05 CET soit 16:05 ET, avant la fermeture des bureaux de vote. À 10.6×/jambe elle
laisse l'équité à **1 024** : le compte est effacé, plusieurs fois. Elle n'était **pas** signalée par la
volatilité réalisée (RV20 à 13.6, quartile bas) ni par la distance au plus haut (−2.8 %). **Seule la
structure VIX/VIX3M était en backwardation (1.03)** — ce qui, avec les 4 autres nuits du top-6 également
au-dessus de 0.95, est cohérent avec le tableau §5.

Point notable : sur les 20 pires nuits, **12 sont des lundis** — l'entrée du lundi n'est pas plus sûre
que celle du mardi malgré une durée de détention identique.

---

# VOLET B — CALENDRIER À DATE CONNUE (2026-08-09 → 2026-09-20)

## 7. Amplitude historique par type d'événement, mesurée sur les données du repo

`data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv` (événements HIGH, horodatés en
vrai UTC) croisé avec le panel M5 CET. `|move|` = |close(T+60 min) / close(T−10 min) − 1| ;
`amplitude` = (max − min)/open sur la même fenêtre.

| événement | jambe | n | move médian | move p90 | amplitude p90 | amplitude max |
|---|---|--:|--:|--:|--:|--:|
| **CPI US** | US100 | 269 | **36.6** | **127.8** | 163.0 | **441.4** |
| | GER40 | 195 | 17.7 | 68.7 | 102.5 | 273.4 |
| **FOMC décision** | US100 | 28 | 30.2 | **131.7** | **178.3** | 266.8 |
| | GER40 | 27 | 12.5 | 50.9 | 76.9 | 89.8 |
| **NFP** | US100 | 103 | 33.0 | 80.9 | 118.8 | 211.1 |
| | GER40 | 73 | 16.9 | 61.3 | 85.8 | 128.6 |
| **PPI US** | US100 | 52 | 24.0 | 77.0 | 84.0 | 155.1 |
| | GER40 | 51 | 18.7 | 55.2 | 74.2 | 99.2 |
| **PCE US** | US100 | 40 | 19.9 | 60.8 | 71.7 | 129.2 |
| | GER40 | 40 | 12.2 | 30.8 | 42.5 | 86.9 |
| **FOMC minutes** | US100 | 43 | 19.8 | 64.1 | 127.1 | 161.0 |
| | GER40 | 36 | 11.0 | 40.5 | 55.8 | 136.5 |
| **BCE décision** | GER40 | 28 | **31.4** | 64.5 | 81.4 | 163.7 |
| | US100 | 28 | 23.2 | 53.4 | 62.6 | 82.2 |
| **ifo** | GER40 | 63 | 17.4 | 49.9 | 68.8 | 91.8 |
| | US100 | 102 | 12.6 | 38.9 | 61.3 | 155.3 |
| **ZEW** | GER40 | 61 | 12.7 | 42.8 | 52.7 | 83.0 |
| | US100 | 101 | 9.9 | 30.0 | 42.3 | 303.7 |
| **HICP flash EZ** | GER40 | 54 | 13.7 | 34.1 | 55.7 | 92.4 |
| | US100 | 57 | 5.8 | 25.3 | 35.1 | 78.1 |

Mise à l'échelle : le seuil de bust à 10.6×/jambe est un mouvement **combiné** de 47 bps. Un CPI au p90
sur la seule jambe US100 (**128 bps**) le dépasse **2.7 fois**. Un CPI au maximum observé (441 bps) le
dépasse **9 fois**. À 4.5×/jambe le seuil est 111 bps et un CPI au p90 le franchit encore.

## 8. Calendrier croisé avec les fenêtres de détention

Fenêtres : **US100** lun/mar 22:05 → J+1 15:30 CET · **GER40** lun/mar 17:35 → J+1 09:00 CET.
Toutes les heures en CET (= CEST, DST actif jusqu'au 25/10/2026). Fichier :
`out/calendrier_2026-08-09_2026-09-20.csv`.

| date | h. CET | jour | événement | zone | statut date | **jambe exposée** | ordre de grandeur (repo) |
|---|---|---|---|---|---|---|---|
| 2026-08-11 | 11:00 | mar | ZEW (août) | DE | **estimé** (2e mardi ; alt. 18/08) | **US100** | méd. 10 / p90 30 bps |
| 2026-08-12 | 14:30 | mer | **CPI US** (juillet) | US | confirmé | **US100** | **méd. 37 / p90 128 bps** |
| 2026-08-13 | 14:30 | jeu | PPI US (juillet) | US | confirmé | — | — |
| 2026-08-19 | 20:00 | mer | Minutes FOMC (réunion 28-29/07) | US | confirmé | — | — |
| 2026-08-25 | 10:30 | mar | ifo (août) | DE | confirmé | **US100** | méd. 13 / p90 39 bps |
| 2026-08-26 | 14:30 | mer | **PCE** (juillet) + PIB T2 2e est. | US | confirmé | **US100** | méd. 20 / p90 61 bps |
| 2026-08-26 | ~22:20 | mer | **NVDA T2 FY27** (après clôture US) | US | confirmé | — | — |
| 2026-08-27 | — | jeu | Jackson Hole, jour 1 (27-29/08) | US | confirmé | — | — |
| 2026-08-28 | ~16:00 | ven | Jackson Hole — discours du président Fed | US | date confirmée, **heure estimée** | — | — |
| 2026-08-31 | 14:00 | lun | CPI flash Allemagne (août) | DE | **estimé** | — | — |
| 2026-09-01 | ~11:00 | mar | HICP flash zone euro (août) | EU | date estimée, **heure à vérifier** | **US100** | méd. 6 / p90 25 bps |
| 2026-09-02 | ~22:15 | mer | AVGO T3 (après clôture US) | US | **estimé** (fournisseur) | — | — |
| 2026-09-04 | 14:30 | ven | **NFP** (août) | US | confirmé | — | — |
| 2026-09-10 | 14:15 | jeu | **BCE** décision (+ conf. 14:45) | EU | confirmé | — | — |
| 2026-09-11 | 14:30 | ven | **CPI US** (août) | US | confirmé | — | — |
| 2026-09-15 | 11:00 | mar | ZEW (septembre) | DE | **estimé** (3e mardi ; alt. 08/09) | **US100** | méd. 10 / p90 30 bps |
| 2026-09-16 | 14:30 | mer | PPI US (août) | US | **estimé** (fenêtre 15-17/09) | **US100** | méd. 24 / p90 77 bps |
| 2026-09-16 | 20:00 | mer | **FOMC** décision + projections (conf. 20:30) | US | confirmé | — | — |

**7 événements sur 18 tombent dans une fenêtre de détention.**

### Ce que la géométrie du sleeve rate, et ce qu'elle attrape

Le résultat le plus structurel du volet B : **aucun événement de la fenêtre n'expose la jambe GER40**, et
**le sleeve manque systématiquement les événements US les plus violents**.

- **GER40 sort à 09:00 CET**, avant *toutes* les publications européennes de la journée (ifo 10:30,
  ZEW 11:00, HICP 11:00, BCE 14:15). La jambe allemande ne porte aucun événement à date connue sur ces
  six semaines.
- **US100 sort à 15:30 CET**, donc **avant les 20:00 CET** : les **minutes FOMC du 19/08** et surtout la
  **décision FOMC du 16/09** (l'événement de plus fort p90 du tableau §7 avec le CPI) tombent
  **4 h 30 après** la sortie de la jambe du mardi soir. Idem pour les résultats après clôture : **NVDA le
  26/08 à ~22:20** arrive presque 7 h après la sortie.
- Ce que la sleeve **attrape** : les publications US de **14:30 CET les mardis et mercredis** — CPI du
  12/08, PCE du 26/08, PPI du 16/09 — et les données européennes de **10:30-11:00 CET les mardis**, qui
  tombent dans la fenêtre US100 ouverte depuis le lundi 22:05.

Le point d'exposition le plus chargé de la période est le **mercredi 12/08 à 14:30**, CPI US, sur la
position US100 ouverte depuis le mardi 11/08 22:05 : c'est l'événement de plus grand p90 du tableau §7
(128 bps sur US100 seul) tombant dans une fenêtre de détention. Le **16/09** cumule deux items le même
jour (PPI 14:30 exposé, FOMC 20:00 non exposé), mais la date du PPI est **estimée**.

### Concentration du NDX — et pourquoi elle ne mord pas ce trimestre

Le brief note à juste titre qu'un résultat de méga-cap est un événement de gap d'indice, pas de
single-name. Vérification (`yfinance .calendar`, 2026-08-09) :

| société | date de résultats | statut | dans la fenêtre 09/08 → 20/09 ? |
|---|---|---|---|
| **NVDA** | **2026-08-26**, après clôture (call 17:00 ET) | **confirmé** — communiqué NVIDIA | oui, mais **mercredi 22:20 → non exposé** |
| AVGO | 2026-09-02, après clôture | **estimé** (fournisseur) | oui, mercredi 22:15 → non exposé |
| AAPL | 2026-10-29 | estimé | non |
| MSFT | 2026-10-28 | estimé | non |
| GOOGL | 2026-10-28 | estimé | non |
| META | 2026-10-28 | estimé | non |
| AMZN | 2026-10-29 | estimé | non |
| TSLA | 2026-10-21 | estimé | non |

**La fenêtre de six semaines tombe dans le creux du cycle de publication du NDX** : les cinq autres
méga-caps publient toutes fin octobre, hors horizon. Le seul événement de gap d'indice réel est **NVDA
le 26/08**, et il tombe un **mercredi après la clôture US** — hors de toute fenêtre de détention, la
jambe US100 du mardi soir étant sortie à 15:30 le même jour. La réaction se joue le jeudi 27/08, jour
sans position.

Deux réserves à porter au dossier. (1) Les dates de résultats des autres méga-caps sont des **estimations
de fournisseur**, pas des confirmations d'entreprise ; seule NVDA est confirmée par un communiqué.
(2) Une publication non exposée n'est pas un risque nul : le repricing peut se prolonger sur la séance
suivante et donc sur la nuit du lundi suivant, ce que ce croisement calendaire ne capture pas.

---

## 9. Limites

1. **Le levier réel n'est pas établi.** 10.6×/jambe (marge policy) contre 4.5×/jambe (marge Swing mesurée
   sur le compte armé) : facteur ~2.5 sur toutes les fréquences de mort. À confirmer par lecture de
   `OrderCalcMargin` serveur avant d'utiliser les chiffres du §4.
2. **Analyse M5-discrète, donc optimiste.** Le moniteur FTMO est continu (post-mortem <ACCOUNT_ID>) ; les
   taux de bust-malgré-breaker sont des planchers.
3. **Marginale, pas de campagne.** Chaque nuit est évaluée sur un compte P2 frais à 10 000 — le pire cas
   demandé. Un compte avec coussin de profit a une géométrie différente ; l'effet du taper et du pacing
   sur le levier n'est pas modélisé nuit par nuit.
4. **Couverture GER40 incomplète** : 945 nuits contre 1 222 pour US100 (démarrage 2013-09-30 + masque des
   trous 2018-2021, miroir de `engine.load_market`). Les nuits mono-jambe sont conservées et signalées
   (`n_legs`) ; elles sous-estiment mécaniquement la MAE combinée.
5. **Dates estimées** : ZEW ×2, PPI de septembre, CPI flash allemand, heure du HICP, heure du discours de
   Jackson Hole, résultats AVGO. Marquées comme telles dans le CSV, colonne `statut_date`.
6. La colonne `spread` de `deep_history_utc` n'a **pas** été utilisée (non peuplée, sous-estime le RT réel
   d'environ 2.4×). Les coûts viennent du panel mesuré de `spec_v22.yaml` (RT 2.2 bps/jambe, swaps longs
   US100 −2.126 et GER40 −1.564 bps/nuit).

## 10. Reproduction

```
code/01_tz_verify.py     vérification de fuseau au tick (DST comme discriminant)
code/02_nightly.py       reconstruction des rendements de nuit -> out/nightly.parquet
code/03_barrier.py       marche de barrière M5 aux 3 seuils, 3 leviers -> out/barrier_L*.csv
code/04_tail.py          distributions, traduction en euros, pires nuits, régimes
code/05_calendar.py      amplitudes historiques par événement + croisement des fenêtres
events_raw.csv           calendrier forward saisi à la main, avec source et statut par ligne
```

Sorties : `out/tz_verify.json`, `out/barrier_summary.json`, `out/percentile_thresholds.csv`,
`out/translation_L10.6.csv`, `out/worst20.csv`, `out/regime_table.csv`,
`out/event_impact_historical.csv`, `out/calendrier_2026-08-09_2026-09-20.csv`.

**Sources externes** (consultées le 2026-08-09) :
[BLS release schedule](https://www.bls.gov/schedule/) ·
[Federal Reserve — FOMC calendars](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) ·
[BEA release schedule](https://www.bea.gov/news/schedule) ·
[Kansas City Fed — Jackson Hole](https://www.kansascityfed.org/research/jackson-hole-economic-symposium/) ·
[ECB — Governing Council calendar](https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html) ·
[ifo Business Climate Index](https://www.ifo.de/en/survey/ifo-business-climate-index-germany) ·
[NVIDIA Q2 FY2027 earnings call](https://www.streetinsider.com/Corporate+News/Nvidia+schedules+Q2+fiscal+2027+earnings+call+for+August+26/26836264.html) ·
[Destatis](https://www.destatis.de/EN/Themes/Economy/Prices/Consumer-Price-Index/_node.html) ·
[Eurostat euro indicators](https://ec.europa.eu/eurostat/news/euro-indicators)
