# Contexte complet — projets quant de Guillaume Beaudouin (au 2026-09-04)

> À transmettre au chat Claude dédié à la recherche de stage M2.
> Rédigé par l'assistant qui travaille sur le dépôt depuis avril 2026, à partir du code et des
> rapports eux-mêmes. Ce qui n'est pas vérifiable est marqué **[À COMPLÉTER PAR GUILLAUME]**.

---

## 0. Les quatre projets, en une phrase chacun

1. **Book FTMO** *(le projet principal — 5 mois, en production)* — construction d'un portefeuille
   multi-sleeves sous barrière de propfirm, exécuté par un EA MQL5 piloté par un moteur Python sur
   VPS ; challenge $10 000 passé en 23 jours, **compte funded réel depuis le 17 août 2026**.
2. **Book personnel IBKR** — sélection de véhicule et construction d'un book à €13k sous contrainte
   de granularité de contrat ; une sleeve validée (flow month-end sur le 10 ans US), déploiement
   prévu fin 2026.
3. **Crypto — Strategy A (TSMOM) et Strategy B (carry delta-neutre)** — deux stratégies écrites,
   backtestées et **déployées en live** sur Hyperliquid / Binance, avec leur infrastructure
   d'exécution.
4. **Futures — Strategy C (ORB Nasdaq)** — cycle complet recherche → re-baselining honnête →
   annulation, qui est la meilleure démonstration de rigueur du dossier.

Autour : un corpus de recherche de ~350 hypothèses testées, un registre de leçons méthodologiques,
et l'infrastructure qui fait tourner le tout.

---

## 1. Profil académique

- **M2 IEF** (Ingénierie Économique et Financière), Université de Rennes 1 — rentrée septembre 2026.
- **Double diplôme Universität Augsburg** — **[À COMPLÉTER : années, intitulé, statut]**.
- Langues : français, anglais, **allemand** (niveau **[À COMPLÉTER]**).
- Recherche : **stage de fin de M2, semestre 2** — **[À COMPLÉTER : dates, durée minimale validante]**.

---

# PROJET 1 — Book FTMO (le cœur du dossier)

## 1.1 Le problème posé

Une propfirm loue du capital contre un examen : passer deux phases (+10 % puis +5 %) sans jamais
violer deux barrières — perte journalière max 5 % du capital initial (vérifiée sur l'**équité**, pas
la balance) et plancher statique absolu à 90 % du capital initial. Une seule violation efface tout.
Une fois financé, le compte verse 80 % du P&L au trader tous les 14 jours de trading, mais **le
buffer ne grandit jamais** : le plancher reste à 9 000 quel que soit le profit accumulé.

Ce dernier point a une conséquence structurelle que Guillaume a formalisée et qui gouverne tout le
reste : **en funded, il n'y a pas de capitalisation, donc pas de raison de maximiser le Sharpe.** On
maximise le rendement par unité de temps sous un hasard de ruine constant. Ce n'est pas de la
gestion de portefeuille classique, c'est un problème de **franchissement de barrière**.

## 1.2 Le résultat de recherche central, et il est contre-intuitif

Après avoir passé au crible **164 stratégies candidates** dans un programme dédié (avec correction
de multiple testing), le constat est que **presque aucune ne meurt sur son alpha — elles meurent
sur la géométrie et sur le coût de portage.**

Trois découvertes chiffrées, chacune gravée comme leçon :

**(a) La probabilité de passer dépend de la FORME de la distribution quotidienne face à une barrière
symétrique, pas de la taille du compte** ni du Sharpe annuel. Une stratégie à trades rares et gros
(taux de réussite 27,75 %, ratio gain/perte 3,7×) plafonne à **44-54 % de chance de passer** quelle
que soit sa performance moyenne, parce que la barrière tue avant que la moyenne ne se réalise. Le
profil réellement compatible est : **Sharpe quotidien élevé, taux de réussite > 55 %, gain/perte
proche de 1, kurtosis basse, et assez de fréquence pour que l'edge se manifeste en ≤ 40 séances.**

**(b) Le portage overnight agrégé pré-tue toute prime tenue.** Mesuré sur le book complet : environ
**6,75 %/an de swap + 1,25 % de commission**, contre une prime de trend multi-actifs d'environ
**8 %/an**. Net : **Sharpe ≈ 0**. Les seules échappatoires sont d'être plat la nuit, ou d'avoir une
prime très supérieure au portage. Corollaire mesuré ensuite : les swaps sont **asymétriques par
jambe** — sur le compte réel, US100 long coûte **−2,126 bps/nuit** quand US100 short **rapporte
+0,092**. Une stratégie market-neutral sur CFD paie donc deux fois le markup.

**(c) Le sizing optimal au sens de la croissance est un PLAFOND, pas un levier.** Une optimisation
par programmation dynamique du sizing sur le challenge plafonne à **33 %** de chance de passer en
échantillon complet. Autrement dit : le money management ne crée pas d'edge, il ne fait que ne pas
en détruire.

Ces trois résultats expliquent pourquoi le book final ne ressemble pas à ce qu'un débutant
construirait.

## 1.3 Le book construit — spécification v2.2

Le book déployé est spécifié dans un **YAML unique, versionné et scellé par sha256**, qui sert de
source de vérité unique au simulateur, au moteur de signal et à l'EA. Quatre sleeves :

| Sleeve | Instrument | Signal |
|---|---|---|
| **gold_trend** | XAUUSD | TSMOM, mélange des signes sur 60/120/250 jours, appliqué au **rendement total ajusté du portage** (pas au prix nu), zone morte `\|s\| < 0,34`, vol-target instrument 10 %, plus une **porte d'équité** : exposition pleine si l'équité est au-dessus de sa moyenne mobile 100 jours, ×0,4 sinon |
| **j1** | USDJPY | Momentum 12-1 classique (`p[t-21]/p[t-252] − 1 > 0`), long-only, vol-target 10 % |
| **overnight_midweek** | US100 + GER40 | Long, tenu **uniquement les nuits de lundi et mardi**, sessions calées sur l'horloge de l'échange |
| **ORB** | US100 | Opening range breakout 09:30-10:00 ET, stop au côté opposé de la fourchette, pas de take-profit, sortie au stop ou à la clôture. **Éteint pendant le challenge, allumé en funded** |

Il y a en plus un **micro-ORB à 0,01 lot** dont le rôle n'est pas le P&L : c'est le **compteur de
jours de trading** exigé par la règle des 4 jours minimum. Détail qui montre le niveau de soin : un
*backstop* déclenche une position symbolique si aucun signal n'est apparu, que rien n'est ouvert,
que le minimum de jours n'est pas atteint et que la cible est déjà franchie — cas qui survient dans
**50 jours-tentatives sur 13 068** en simulation.

## 1.4 Le moteur de risque — la partie la plus originale

Ce n'est pas un simple stop-loss. C'est un gouverneur qui module l'exposition en fonction de la
position dans la course :

- **Multiplicateur de volatilité** `vm = 14` en challenge, `vm = 1` en funded. Le même book, deux
  régimes de risque, parce que les deux problèmes sont différents (franchir une cible vs durer).
- **Breaker** : mise à plat immédiate si la marge restante sous la barrière journalière descend sous
  30 % du budget, vérifié toutes les 5 minutes.
- **Taper** : plancher d'exposition à 2 % quand on approche du plancher statique.
- **Glide** : exposition ×0,5 une fois 80 % de la cible atteinte — on ne joue pas les prolongations.
- **Pacing** : exposition ×`clip(1 + retard, 0,8, 2,0)` — on accélère si on est en retard sur le
  rythme, dans une bande bornée.
- **Règle d'abandon** : si l'équité stagne à moins de 2 % au-dessus du plancher pendant 5 jours, on
  relance une tentative plutôt que d'agoniser.
- **Cap de marge à 60 % de l'équité**, avec les taux de marge réels par instrument, appliqué par
  scaling proportionnel de toutes les jambes.
- **Cap de levier par jambe**, ajouté en v2.8 comme overlay de risque.

**La bascule challenge → funded est un événement unique et atomique** : `vm 14→1`, poids overnight
`0,6→0,35`, ORB allumé, micro-ORB éteint, pacing/glide/abandon désarmés. Un seul déclencheur, pas
une dérive de paramètres.

## 1.5 L'architecture d'exécution

```
EA (21:45)  ──▶ export du marché (D1 520 jours × 4 jambes, specs contrats, swaps réels)
                        │
                brain.py (cron 21:50 Paris)
                  charge le YAML épinglé, vérifie le sha, contrôle de dérive,
                  calcule les signaux, applique le gouverneur
                        │
                 targets.json ──▶ book_executor.mq5 (22:05)
                                    ZÉRO logique de signal
                                    invariants en dur : plancher journalier 5 %,
                                    plancher 9 000 + taper, breaker 30 %, marge 60 %
                        │
        ┌───────────────┼────────────────┐
   supervisor.py    fills.csv      reconcile.py (23:00)
   (daemon 60 s,   swaps_billed    rejoue la journée en simulation,
    alertes TG)                    décompose l'écart, STOP après 3 jours de dérive
```

Points d'ingénierie qui méritent d'être racontés en entretien :

- **L'EA refuse de trader** si le sha256 de la spec déposée sur le terminal ne correspond pas à
  celui compilé dans le binaire. Impossible de faire tourner un EA sur une spec qui a dérivé.
- **Le simulateur et le live partagent la même bibliothèque d'invariants** (`ftmo_live/lib/`), et
  une suite de **145 tests** vérifie notamment que le miroir est identique à l'oracle de simulation.
  Le risque classique « le backtest et le live ne calculent pas la même chose » est traité
  structurellement, pas par la confiance.
- **Réconciliation quotidienne automatique** : chaque soir, la journée réelle est rejouée en
  simulation et l'écart est décomposé par cause (signal, exécution, swap, slippage). Trois jours de
  dérive inexpliquée déclenchent un arrêt.
- **Le modèle de swap a été validé au centime** : sur la nuit du 10 au 11 juin (mercredi, portage
  triple sur métaux et FX), les 4 jambes facturées ont été reconstruites exactement à partir des
  spécifications lues sur le serveur.
- **Kill-file** : déposer un fichier `FLAT` met tout à plat et désactive le trading, sans toucher au
  code.
- **Les coûts ne sont jamais supposés.** Les ancres sont mesurées sur le compte réel : coût
  round-trip par jambe (XAUUSD 1,84 bps, USDJPY 1,36, US100 et GER40 2,2) et swap par nuit **et par
  sens**. Une sonde de slippage tourne en continu sur les fills ORB.

## 1.6 Résultats

**Challenge** : phase 1 **+10,06 %**, phase 2 **+5,39 %**, **passé en 23 jours** — avec l'honnêteté
statistique de noter que c'est dans la queue droite de la distribution simulée (la probabilité de
passer la phase 2 en 7 jours était de 33,5 %).

**Compte funded livré le 2026-08-17**, actif, $10 000, sur lequel le book tourne aujourd'hui.

**Simulation du book réellement déployé** (or et USDJPY à poids nul dans le régime actuel, coût ORB
au niveau mesuré en live), sur cohortes historiques 2013-2025 :

| Horizon | P(net > 0) | Net médian | p10 | Risque de ruine | Nature |
|---|---|---|---|---|---|
| 1 an | **94,8 %** | +$379 | +$57 | **0 %** (0/305) | — |
| 5 ans | **95,1 %** | +$1 991 | +$183 | **3,9 %** (8/204) | **100 % via le plancher statique**, jamais la barrière journalière |

Et le caveat que le rapport impose lui-même, qui vaut plus que les chiffres : **les 305 cohortes ne
sont pas 305 tirages indépendants.** Elles démarrent tous les 14 jours sur ~12,7 ans d'historique et
se recouvrent à 95-99 %. Le nombre effectif d'histoires indépendantes est **≈13 à un an et ≈2,6 à
cinq ans**. Le rapport écrit noir sur blanc : *« ne présente jamais le bust% à 5 ans comme une
fréquence sur 204 tirages — c'est une fréquence sur 2-3 »*. C'est ce genre de réflexe qu'un desk
cherche.

**État actuel, sans maquillage** : le compte est en drawdown (solde 9 931,55 au 1er septembre contre
10 000). Deux décisions sont planifiées et **pré-enregistrées**, ce qui est le vrai point à mettre
en avant.

## 1.7 Les deux décisions ouvertes — et pourquoi elles valorisent le dossier

**(a) La sleeve ORB, tranchée en octobre sur un critère écrit à l'avance.**

Les points morts ont été calculés par jambe, en appliquant le coût trade par trade au levier réel de
chaque trade (et non un levier médian uniforme) sur un ledger de **4 013 trades, 2010-2026** :

| jambe | coût round-trip au-delà duquel l'espérance passe sous zéro |
|---|---|
| SHORT | 1,694 bps |
| ALL (agrégé) | 2,189 bps |
| LONG | 2,610 bps |

Le coût réellement mesuré en live vaut **2,11 bps** [IC95 bootstrap 1,56–2,62]. D'où une matrice de
décision à trois bandes, arrêtée avant de connaître le résultat : en dessous de 1,69 on garde les
deux jambes, entre 1,69 et 2,17 on passe long-only, au-dessus de 2,17 on désarme.

Deux résultats de robustesse s'ajoutent : **la jambe short échoue à coût nul** (t = 1,26 en brut) —
elle n'a donc jamais eu d'edge, indépendamment du coût ; et la « rupture de régime 2022 » qui la
justifiait **ne survit pas à un test de rupture endogène** (Bai-Perron ajusté du nombre de dates
balayées : p = 0,266, soit le 73ᵉ percentile du bruit). Enfin, l'objection « long-only = simple
exposition au marché » a été testée et **partiellement confirmée** : β annuel de +31,7 (t = 3,03,
significatif), R² 17,8 % — sous le seuil disqualifiant de 30 %, mais réel, et le rapport le dit.

**(b) La restriction du calendrier overnight aux nuits de lundi et mardi.**

C'était une **dette méthodologique assumée** : la concentration en milieu de semaine avait été
découverte *post-hoc*, sans pré-enregistrement, et gravée dans la spec en portant un échec de
Deflated Sharpe Ratio (0,29) sur sa propre grille de sélection à 40 cellules. Signalée « à trancher
avant signature » dans cinq documents pendant deux mois.

La résolution est un bon exemple de raisonnement : la restriction n'est **pas une sélection de
signal, c'est une contrainte de coût**. La haie à franchir (swap + spread) vaut 3,17 bps sur US100 et
2,58 sur GER40, elle est **mesurée sur le compte et connue avant de regarder les rendements**. Or les
nuits de mercredi et jeudi rapportent 1,26 et 1,48 bps — il leur faudrait tripler. Il n'y a pas de
choix entre plusieurs bons candidats : **une seule configuration franchit la haie**. Le DSR punit la
recherche parmi des alternatives positives ; ici « toutes les nuits » rapporte **−0,17 bps sur GER40**.
La restriction est maintenue, et la justification est désormais écrite.

---

# PROJET 2 — Book personnel IBKR

## 2.1 Le problème

Faire croître ~€13k le plus vite possible sans risque de ruine, hors propfirm. La difficulté n'est
pas de trouver un edge, c'est que **la granularité des contrats** rend la plupart des stratégies
indéployables : un contrat ou rien, donc pas de vol-targeting.

## 2.2 Une contradiction interne, et sa résolution — bon exemple de raisonnement

Deux études du dépôt se contredisaient frontalement :

| | verdict |
|---|---|
| Étude « growth engine » (18 juillet) | **NO-GO à €13k** — meilleure config Sharpe 0,25, +2,8 %/an ; le flow month-end est **plat** (+$208 sur 7 ans) |
| Étude « month-end vehicle » (30 juillet) | **+17,6 %/an, Sharpe 0,92**, marge $1 800 = 14 % du compte |

Ce n'était pas une divergence statistique mais **une divergence de véhicule**. La première étude
avait supposé que le contrat ZN (10 ans US) était inaccessible à €13k et s'était rabattue sur un
micro-contrat de rendement au DV01 de $10/point de base — trop petit pour que l'effet existe. Or ZN
est trop gros **en notionnel** ($115k), pas **en marge** : les futures de taux ont une marge faible
parce que leur volatilité est faible, soit **~$1 800, c'est-à-dire 14 % du compte**. Son DV01 vaut
6,5× celui du micro.

La leçon qui en est sortie : **si la marge du lot minimum tient dans le capital personnel, un
propfirm n'apporte rien** — il vend du levier sur du capital qu'on n'a pas. Chiffré sur cette même
stratégie : compte personnel **+$2 275/an à 100 % du P&L**, sans barrière ni horloge ; route
propfirm, 11 mois, $639, 80 % du P&L d'un seul contrat, sous une barrière qu'un événement historique
a déjà franchie. **Strictement dominée.** Corollaire de process : la matrice de véhicule passe
**avant** le backtest.

## 2.3 La sleeve validée

**Flow month-end sur le 10 ans américain** — long 1 ZN sur les trois derniers jours ouvrés du mois.

| | |
|---|---|
| Validation | t HAC **4,76**, 24 ans (2002-2026), placebo apparié **p = 0,000** |
| Décroissance | **aucune** — Sharpe 0,90 avant 2022, **0,89** après (le « déclin » observé ailleurs était un artefact de l'ETF TLT) |
| Contrôle | les autres jours du mois rapportent **−0,71 bps** ⇒ effet concentré = flux, pas exposition au marché |
| Espérance | **+$2 275/an (+17,6 %)**, Sharpe **0,92 net de coûts** |
| Pire événement historique | −$2 009 (−15,5 %) |
| Exposition | **14 % des jours** — plat 86 % du temps |

Le point analytique intéressant : **c'est l'intermittence qui autorise le levier, pas le money
management.** Un book continu levé 8× encaisse −73 % de drawdown ; une sleeve exposée 14 % du temps
reste peu profonde à levier comparable.

Et une contrainte honnête : **c'est tout le book déployable à €13k. Une sleeve.** Le book diversifié
(ZN + ZF + trend simultanément) exige €30-50k. La formulation exacte du problème est donc : *on ne
peut pas activer le book diversifié à €13k, mais on peut activer sa meilleure sleeve.*

## 2.4 Vérification du courtier Eightcap

Demandée parce qu'un ami la recommandait. Conclusion nuancée : **le courtier est réellement bon
marché** — EURUSD à ~0,11 pip de spread + $7 de commission par lot round-trip, soit **~0,75 bps**,
contre 2,48 bps mesurés chez FTMO. Mais **il n'a pas de futures CME**, donc il ne peut pas héberger
la seule sleeve validée, et il ne ressuscite pas le FX intraday (le critère `gross/coût ≥ 1,5` reste
inatteignable). Recommandation du courtier juste, sans effet sur le plan.

---

# PROJET 3 — Crypto : deux stratégies en production

## 3.1 Strategy A — TSMOM crypto

Momentum de série temporelle sur BTC/ETH/SOL, avec un signal continu plutôt que binaire :

```
vol_28d(t) = std(log_returns[t-28 : t-1]) × √365
t_stat(t)  = cum_log_ret(t) / (vol_28d(t) × √28)
signal(t)  = tanh(t_stat(t))          puis clip à [0, +∞) pour la version long-only
```

L'idée (d'après Zarattini 2025) est que le t-stat continu dimensionne naturellement la position
selon la conviction : tendance faible → position partielle. Gain mesuré contre le `sign()` binaire :
Sharpe out-of-sample **1,33 contre 1,22**, drawdown max **−6,9 % contre −12,7 %**, 3 folds de
walk-forward sur 4.

La docstring du module contient une **garantie explicite d'absence de look-ahead** — le `.shift(1)`
dans les fenêtres glissantes est documenté et justifié ligne à ligne. C'est le genre de détail qu'un
relecteur technique remarque.

Autour du signal : un module de sizing, un filtre de pics de volatilité, un simulateur de challenge
propfirm, et un optimiseur de paramètres de challenge.

**Statut et honnêteté** : déployée en live (compte propfirm crypto + testnet Hyperliquid), **gelée
depuis mai 2026** après avoir touché un plafond structurel identifié — le bêta crypto rend le respect
d'une limite de drawdown journalière de 3 % improbable, taux de passage plafonné à **39 %**. Et le
Sharpe de 1,33 a été **rétracté par Guillaume lui-même** : c'est un brut avant taux sans risque sur
un univers de 14 coins, alors que la configuration réellement déployée (3 coins) donne **0,57 en
excès, avec un intervalle de confiance à 95 % qui contient zéro**.

## 3.2 Strategy B — Carry delta-neutre sur funding

Arbitrage de taux de financement : **long le spot sur Binance, short le perpétuel équivalent sur
Hyperliquid**, exposition directionnelle nulle par construction, revenu = les paiements de funding
toutes les 8 heures.

**Sélection d'univers** : actifs cotés sur les deux plateformes, ≥ $10M de volume 24h, ≥ 180 jours
d'historique de funding, et un carry sur 7 jours supérieur à **0,34 %** — seuil qui n'est pas
arbitraire, c'est exactement ce qu'il faut pour couvrir les deux round-trips (0,17 % spot + 0,17 %
perp).

**Le contrôle de risque le plus intéressant du dossier** est la prévention des positions à une seule
jambe, qui est le vrai danger de cette stratégie (si une jambe passe et pas l'autre, on se retrouve
avec une exposition directionnelle non voulue). L'ordre des opérations est explicite et asymétrique :

- **À l'ouverture** : achat spot d'abord, puis short perp. Si l'achat échoue → rien à défaire. Si le
  short échoue → **revente immédiate au marché du spot**.
- **À la fermeture** : fermeture du short d'abord, puis vente du spot. Si la fermeture du short
  échoue → **on garde le spot ouvert** (ce qui préserve la couverture) et on alerte. Si la vente du
  spot échoue → alerte d'urgence, l'état reste ouvert pour revue manuelle.

C'est du raisonnement d'exécution, pas du backtest. Avec en plus un kill switch par fichier, un
capital borné ($50 par actif, 5 actifs max), et un rebalancement en cron décalé de 5 minutes de
celui de la Strategy A pour éviter la contention de ressources.

**Statut et honnêteté** : live sur testnet Hyperliquid depuis mai 2026. **Le Sharpe backtest de 4,10
a été rétracté** : le backtest décrivait une rotation lente, alors que la configuration live tourne
en 8 heures — aux coûts réels, la seuil de rentabilité exige une tenue ≥ 10 jours, et à la rotation
de 8 h le Sharpe est très négatif. Le walk-forward disponible (3 folds) est sous la règle maison de
5 folds. **Conclusion assumée : aucun Sharpe n'est citable pour cette stratégie.** L'hypothèse
vivante est une variante à rotation lente, les données sont là.

---

# PROJET 4 — Futures : Strategy C (ORB Nasdaq), le cycle complet

Momentum d'ouverture sur le Nasdaq : direction de la fourchette 09:30-09:45, confirmation VWAP,
filtre de gap ≤ 1,2 %, fourchette minimale de 30 points, plafond de stop à $400, take-profit à 1,5R,
sortie forcée à 12:30 ET.

**Backtest initial** : Sharpe **1,52**, drawdown −13,4 %, walk-forward 78 %, N = 346, sur données
Kaggle 2022-2025.

**Re-baselining honnête** : après achat de données Databento propres 2014-2026 et mesure réelle du
slippage ($29 round-trip au lieu de $19 supposé), le Sharpe tombe à **0,41** sur l'échantillon
complet (0,69 sur la fenêtre Kaggle d'origine), drawdown −53,9 %, N = 765. Les deux causes sont
isolées : **fenêtre d'échantillon favorable + hypothèse de coût optimiste**. En parallèle, la
déflation du Sharpe pour tenir compte du nombre de modifications testées ramenait déjà le 1,52 à
1,0-1,1 avant même de changer les données.

**Annulation en juin 2026**, non pas sur la performance mais sur le **véhicule** : FTMO ne supporte
pas les futures CME, donc il n'existait pas de compte pour l'héberger. Le code et l'infrastructure
sont conservés.

C'est probablement **la meilleure histoire courte du dossier pour un entretien** : elle montre un
chercheur qui achète des données pour vérifier son propre résultat, isole proprement les deux causes
de l'écart, et tue son propre projet.

---

# CE QUI SOUTIENT TOUT ÇA

## 5.1 Le dépôt, en chiffres vérifiés (`git`, 2026-09-04)

| | |
|---|---|
| Commits | **2 115** en 5 mois (depuis le 2026-04-14) |
| Python | 1 591 fichiers, **~303 000 lignes** |
| Rapports de recherche (Markdown) | 1 950 fichiers |
| MQL5 | 13 fichiers, ~5 000 lignes |
| Tests | 49 fichiers (dont 145 tests sur le seul module live) |
| Dossiers de recherche | **115** (78 actifs, 37 archivés) |
| Classes d'actifs | Crypto, FX, Futures, Actions, Commodités, Multi-Asset |

## 5.2 Le registre de leçons — l'artefact le plus distinctif

Une **soixantaine de leçons numérotées (L11 → L67)**, chacune un verdict + un chiffre opérationnel +
un chemin vers sa dérivation. Ce ne sont pas des généralités de manuel : ce sont des pièges
**mesurés sur ce dépôt**. Échantillon utile pour un entretien technique :

- **L43** — Le FX intraday retail est mort au coût. Critère pré-flight : `gross/coût_p95 ≥ 1,5`.
  Meilleur ratio jamais observé sur ~1 500 configurations : **0,36**, **répliqué quatre fois de
  façon indépendante**, y compris hors FX — c'est devenu une constante empirique du tier retail.
- **L52** — Ne jamais faire confiance au nom d'un champ de fournisseur. Le champ `Open` du contrat
  ZN chez yfinance est l'ouverture Globex 18:00 ET **de la veille** (71,6 % de correspondance exacte
  au tick). Toute décomposition intraday/overnight bâtie dessus est fausse.
- **L56** — Un drift de session est ancré à l'horloge de l'échange **avec son DST**, pas à UTC. Test
  de falsification gratuit : corréler le profil horaire hiver/été dans les deux horloges — ici 0,70
  en heure de New York contre **0,04 en UTC**. La fenêtre héritée était juste en hiver et une heure
  en retard tout l'été.
- **L59** — Le décalage d'un pas de temps ne certifie que **l'entrée**. Les sorties au stop exact
  sont irréalistes : 25 % des barres de stop ouvrent au-delà. Re-pricer les sorties fait passer un
  Sharpe de 0,99 à **0,49** — ce qui invalide partiellement toute une famille classique.
- **L61** — Un sizing dépendant du chemin (entrée échelonnée) **fabrique un t-stat positif sur du
  bruit pur** : 18 cellules sur 18 au-dessus de 2,5 sur des données aléatoires. Le HAC ne le voit
  pas, parce que le biais est dans le sizing, pas dans le résidu.
- **L64** — Une rupture temporelle doit être **estimée** (Bai-Perron, CUSUM), jamais imposée, et
  corrigée du nombre de dates balayées.
- **L66** — Ré-échantillonner des instruments cotés indépendamment sur un horodatage commun
  **fabrique de la prédictibilité cross-instrument** (effet Epps, Lo-MacKinlay).
- **L67** — Dans `IR = TC × IC × √BR`, BR compte les **paris indépendants**, pas les observations.

Il existe aussi une **politique écrite de ré-ouverture** des familles archivées, qui classe les
rejets par nature : un rejet *mécanique* (le signal n'existe pas) reste fermé ; un rejet *véhicule*,
*coût*, *puissance* ou *géométrie* est ré-ouvrable, mais uniquement avec un angle nouveau **écrit
avant** de retoucher aux données.

## 5.3 Méthodologie effectivement implémentée

t-stat HAC Newey-West (lag 6) ; correction de multiple testing systématique et **Deflated Sharpe
Ratio** (Bailey–López de Prado) dès deux modifications, adossés à un **ledger de comptage de tests**
tenu à l'échelle du dépôt ; **bootstrap par blocs** (Politis-Romano), l'iid étant interdit quand les
trades cluster ; **walk-forward à fenêtre expansive, 5 folds minimum** (le split unique est interdit
par la constitution du dépôt) ; **CPCV** ; **gate IC → Sharpe net** d'Israel-Jiang-Ross qui tue la
majorité des candidats avant tout backtest ; **placebos appariés** (calendaires, à autocorrélation
appariée, à duty cycle identique) ; **MDE calculé avec puissance** ; rendements en excès du taux sans
risque, vol-targeting quotidien, coûts mesurés et jamais supposés.

## 5.4 Ingénierie et opérations

- **CI/CD** GitHub Actions, 201 lignes, auto-merge après checks verts, avec trois gardes qui
  bloquent durement toute PR touchant du code live, du portefeuille ou la CI elle-même.
- **Gouvernance de données formelle** : sources brutes immuables avec manifeste, caches régénérables
  exclus du versionnement, règle « une série = un fichier canonique ». Un audit a fait passer le
  `.git` de **2,1 Go à 65 Mo**.
- **Détection d'un bug de fuseau horaire** dans l'historique : des panneaux étiquetés `timestamp_utc`
  étaient en EET/EEST (vérifié au tick, −2 h), ce qui signifiait que **38,7 % de la séance
  américaine n'avait jamais été testée**. Migration complète vers un historique en vrai UTC.
- **Réparation de trous de données** 2018-2021 sur un historique M1, vérifiée aux jointures.
- **Décodeur binaire Dukascopy `.bi5`** écrit à la main (ordre des octets non documenté, trouvé par
  rétro-ingénierie) pour construire 19 ans d'historique FX.
- **Pipelines de veille automatisés** : scraping quotidien de sources d'idées, scan arXiv q-fin,
  synthèse hebdomadaire cross-papers, et un orchestrateur de faisabilité à trois portes
  (IC → walk-forward/bootstrap/DSR → sanity checks).
- **Isolation des sessions par git worktree**, après un incident réel de commit atterri sur la
  mauvaise branche.
- **Post-mortems écrits** sur les incidents live : une violation de compte sur un flash move USDJPY
  (cause racine identifiée : le sizing, pas le breaker), un latch d'état non purgé au rollover, un
  problème de réalignement de série sur GER40.

## 5.5 Un dossier annexe qui fait une bonne anecdote (mais reste annexe)

Audit du code d'un EA commercialisé par un tiers, affichant +60,33 % sur 6,5 ans et un Sharpe de
1,56. En reverse-engineering des 806 lignes de MQL5 : **biais d'anticipation structurel** (le filtre
lit le swap *actuel* du courtier, constant sur toute la passe — MT5 n'a aucun historique de swaps,
donc le backtest applique rétroactivement le portage du jour de l'exécution), **vérifié
empiriquement** en relançant sur un courtier aux paramètres différents (**zéro trade pris**) ; un
veto direction-aveugle qui **rejette toutes les ventes** (0 acceptée sur 30, mesuré au binaire) ; et
un Sharpe calculé avec les défauts de `quantstats` sur une série indexée par trade (correction :
**0,68 brut, 0,48 en excès**). Reproduction non biaisée en Python : **+16 à 21 %** au lieu de +60 %.

C'est une bonne histoire de validation de modèle, mais c'est deux semaines de travail — à raconter
en entretien, pas à mettre au centre du CV.

---

# 6. Garde-fous — ce qu'il ne faut PAS écrire

Le dépôt a rétracté plusieurs de ses propres chiffres. Le CV doit rester défendable ligne par ligne :

| ❌ Ne pas écrire | ✅ Le chiffre honnête |
|---|---|
| « Sharpe 1,33 » (TSMOM crypto) | **0,57 en excès** sur la config déployée, IC95 contenant zéro |
| « Sharpe 4,10 » (carry delta-neutre) | **Aucun Sharpe citable** — walk-forward insuffisant, config live négative |
| « Sharpe 1,52 » (ORB Nasdaq) | **0,41** après données propres et coût mesuré |
| « Sharpe 2,31 » (portefeuille) | Démontré fabriqué au niveau composant, retiré |

Le compte funded est actuellement en drawdown. **Le dire si on est interrogé**, avec le critère de
désarmement pré-enregistré — c'est plus impressionnant que de l'esquiver.

**Formulations sûres et vraies :**

> « Conception et mise en production d'un portefeuille multi-sleeves sous contrainte de barrière
> (perte journalière 5 %, plancher −10 %) : recherche, spécification versionnée scellée par hash,
> moteur de signal Python et exécution MQL5 sur VPS Linux supervisé, avec réconciliation
> quotidienne sim-vs-live. Challenge $10 000 passé en 23 jours ; compte financé en production depuis
> août 2026. »

> « Stratégie d'arbitrage de financement delta-neutre spot/perpétuel (Binance / Hyperliquid) :
> sélection d'univers par seuil de carry couvrant les coûts de transaction, exécution séquencée avec
> défaisage automatique en cas d'échec d'une jambe, kill switch. »

> « ~350 hypothèses testées sur 6 classes d'actifs, la quasi-totalité rejetées, chaque rejet
> documenté par sa cause mécanique dans un registre de ~60 leçons méthodologiques numérotées. »

> « Re-validation d'une stratégie interne : Sharpe 1,52 → 0,41 après achat de données propres et
> mesure réelle du slippage ; les deux causes de l'écart isolées et chiffrées séparément. »

---

# 7. À compléter par Guillaume — **[HORS DÉPÔT]**

Ces éléments existent mais ne sont pas dans le dépôt, je ne peux donc pas les documenter :

- **Hawkline** — rôle, stack, ce qui tourne réellement, taille d'équipe, dates.
- **Pipeline crypto ML** — modèles, features, horizon, résultat honnête.
- **Framework EV** — de quoi il s'agit.
- **Activité de développement quant facturée** — clients, missions, volume, période. C'est le seul
  élément qui prouve que quelqu'un a **payé** pour ce travail : à ne pas enterrer.
- Cursus Augsburg (dates, intitulé), et compétences non couvertes ici (C++, SQL, Rust, ML en
  production…).

---

# 8. Lecture stratégique

1. **Le repo public ne peut pas être `Algo_claude` tel quel** — clés redigées, états de compte live,
   post-mortems d'incidents, constitution interne. Il faut en extraire un dépôt vitrine. Le meilleur
   candidat n'est pas l'audit du code tiers, c'est **le dossier de décision ORB** ou **le
   re-baselining 1,52 → 0,41** : ce sont les démonstrations les plus pures de « backtest honnête »,
   et elles sont sur du travail propre.
2. **Le registre de leçons, publié seul et proprement rédigé**, est le document qui fait qu'un desk
   se souvient d'un nom. Aucun risque concurrentiel : ce sont des méthodes, pas des signaux.
3. **La cible crypto prop / market making est bien alignée** — le travail Hyperliquid (API,
   arbitrage de funding, exécution séquencée, réconciliation d'état) est directement pertinent, et
   c'est le segment où l'expérience live pèse plus que le pedigree.
4. **Francfort en priorité, pas en option.** Augsburg + l'allemand transforment un dossier français
   ordinaire en dossier local différenciant, et le format stage long y est compris — ce qui contourne
   entièrement les deux obstacles identifiés côté américain (visa J-1, format 8-12 semaines).
5. **Le goulot réel n'est ni le CV ni le niveau, c'est la durée validante et le visa.** Tant que la
   scolarité de Rennes n'a pas répondu, une partie des candidatures est du travail potentiellement
   perdu. C'est le premier appel à passer.
