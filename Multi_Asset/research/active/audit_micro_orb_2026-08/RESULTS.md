# Audit du micro-ORB compteur de jours — la quatrième sleeve qui n'en est pas une

*2026-08-04 · worktree `claude/audit-micro-orb` · diagnostic seulement, aucune modification live.*

Objet audité : `challenge.micro_orb_day_counter` de `spec_v22.yaml`, implémenté par
`ftmo_live/mt5/book_executor.mq5` (`Do1600Arm` / `MicroManage` / `Do2130Backstop`) et
modélisé par `data/ftmo_portfolio/v22/engine_v22.py:run_phase`. 0.01 lot US100.cash,
raison d'être : satisfaire `min_trading_days = 4`.

**Harnais** : clone instrumenté de `run_phase`/`run_funnel`
(`code/mo_engine.py`), hooks OFF ⇒ **462/462 cohortes identiques** au moteur committé,
sur les deux configs. Ancres reproduites **exactement** : `micro_fires = 9,248` et
`backstop = 50` (ancre #13), `p(campagne) v2.2 = 87.01 %` (ancre #1), `micro-OFF =
88.31 %` (ancre #15). Deux configs partout : **v2.2** (pinnée, marge Standard) et
**v2.8** (`CFG_CHALLENGE_V28`, marge Swing mesurée + cap J1 12× = le book réellement
déployé). Interpréteur `/usr/bin/python3`.

---

## 1. La réponse : fait-il son travail ?

**Oui, et de façon quasi-dégénérée.** Le compteur atteint 4 jours de trading en
**4 séances — le minimum arithmétique — dans 94,3 % / 94,5 % des tentatives.**

| Séances pour atteindre 4 jours de trading | v2.2 | v2.8 (déployé) |
|---|---:|---:|
| N tentatives de phase | 2 169 | 1 936 |
| min / **médiane** / p75 / **p90** / p99 / max | 4 / **4** / 4 / **4** / 5 / 6 | 4 / **4** / 4 / **4** / 5 / 5 |
| exactement 4 séances | 94,3 % | 94,5 % |
| 5 séances | 5,6 % | 5,5 % |
| 6 séances | 0,1 % | 0 % |

**Taux d'échec du compteur : 0,00 % (0 / 2 169 et 0 / 1 936).**

Aucune tentative n'a jamais survécu 20 séances sans atteindre ses 4 jours. Contrôle
plus dur : parmi les tentatives survivant ≥ 10 séances (N = 235 / 417), **100,00 %**
atteignent 4 jours. Les 353 / 184 tentatives qui n'y arrivent pas sont **à 100 % des
comptes déjà morts** (`bust_daily` + `bust_floor`) — le compte a explosé avant, ce
n'est pas une défaillance de comptage.

**Coût résiduel de la contrainte elle-même** (pas du micro) : sur les tentatives
gagnantes, la règle des 4 jours retarde la clôture de la phase de **1,03 j en moyenne
(médiane 1 j, max 3 j)** en v2.2 et **0,63 j (médiane 0, max 3)** en v2.8 ; 55,8 % /
37,0 % des tentatives gagnantes sont retardées d'au moins un jour. C'est le prix de la
règle FTMO, pas du support choisi pour la satisfaire.

---

## 2. Le couplage « seulement si rien d'autre n'est ouvert » : il ne coûte aucun jour

**Zéro jour de comptage perdu, par construction.** La condition ne se déclenche que
lorsqu'une autre jambe a déjà ouvert — et ce jour-là **le compteur avance déjà**.

| | v2.2 | v2.8 |
|---|---:|---:|
| jours-candidats (signal ORB présent) | 12 160 (96,4 %) | 14 543 (96,6 %) |
| micro **posté** | 9 247 (76,0 % des candidats) | 9 150 (62,9 %) |
| micro **supprimé** par la condition | 2 913 (24,0 %) | 5 393 (37,1 %) |
| … dont jour **déjà marqué par le livre** | 2 411 (82,8 %) | 4 344 (80,5 %) |
| … dont **jour perdu pour le comptage** | **0** | **0** |

Les 502 / 1 049 lignes restantes ne sont pas des jours perdus par la condition, elles
sont ventilées ainsi : **bust** (240 / 612 — le compte est mort), **passage intraday**
(180 / 330 — la phase est validée, le compteur était déjà satisfait), **abandon**
(2 / 0), et **80 / 107 jours où le segment 22:05 est VIDE** dans le panel. Ces
derniers correspondent à 26 dates distinctes (35 sur tout le panel, **1,06 %**), qui
tombent sur les semaines de bascule DST et les fins de mois : le micro ne peut
matériellement pas être posté ces jours-là. C'est un artefact de découpage de session,
pas la condition.

Qui marque le jour, au total : **micro 73,3 % / 60,8 %**, jambe ON 17:35 19,8 % /
29,8 %, rebalance 22:05 0,7 % / 1,0 %, backstop 0,4 % / 0,3 %.

**Un déclenchement inconditionnel serait strictement pire** : il ajouterait une
position concurrente sur 24 % / 37 % des jours pour **zéro** gain de comptage. Une
autre heure n'apporte rien non plus — le mécanisme qui répondrait à cette question
existe déjà et est traité au §5.

---

## 3. Le risque réellement apporté : bruit, mais pas nul

### 3.1 P&L

| micro posté | v2.2 (N = 9 247) | v2.8 (N = 9 150) |
|---|---:|---:|
| P&L moyen / pose | +$0,047 | +$0,033 |
| écart-type | $0,94 | $0,87 |
| **pire séance** | **−$3,40** | **−$3,30** |
| meilleure séance | +$17,18 | +$17,18 |
| p1 / p99 | −$1,96 / +$3,18 | −$1,80 / +$2,98 |
| cumulé, toutes tentatives | +$436 | +$305 |

Pire séance = **0,68 % du budget journalier** ($500) et **0,34 % du buffer floor**
($1 000). Borne dure du modèle : risque maximum posé $6,23 ⇒ excursion de règle
1,31 R maximum **$8,16 = 1,63 % du budget daily**.

### 3.2 Coût — L57 ne mord PAS ici, et c'est mesurable

À 0,01 lot US100.cash (contract = 1 ⇒ notionnel = 0,01 × prix ≈ **$150–300**), le
coût aller-retour est **2,2 bps ≈ $0,03–0,07**. Décisif : `rt_bps_legs_allin.US100 =
2.2` est **identique** à `rt_bps_legs.US100 = 2.2`, et `MEASURED_SPECS["US100"]` porte
`comm_side_frac = 0.0` **et** `comm_side_usd_lot = 0.0` — **les indices FTMO n'ont
aucune commission**. Il n'y a donc **aucun terme de coût fixe** à diluer : contrairement
au micro-future de L57 ($1,70 fixe = 2,3–2,8 bps à lui seul), le coût de cette pièce est
purement proportionnel et reste à 2,2 bps quelle que soit la taille. **L57 est le bon
réflexe mais la mauvaise leçon pour ce véhicule** ; c'est précisément l'argument
« CFD fractionnable > micro-future » de TAXONOMY.md §3, ici vérifié sur les specs.

### 3.3 Peut-il contribuer à un franchissement ? OUI — mesuré, petit, réel

Contrefactuel déterministe : sur chaque bust, marge de franchissement
(`lim_eff − equité au barreau de brèche`) comparée à l'excursion micro active.

| | v2.2 | v2.8 (déployé) |
|---|---:|---:|
| busts | 386 | 857 |
| micro exposé au moment du franchissement | 250 (64,8 %) | 685 (79,9 %) |
| marge de franchissement médiane | $167,3 | $27,3 |
| marge p5 / min | $6,27 / $0,40 | $1,41 / **$0,035** |
| **busts PIVOTAUX** (marge < excursion micro) | **4 (1,04 %)** | **23 (2,68 %)** |
| busts dont la marge < borne dure $8,16 | 5,44 % | **26,72 %** |

**Ce n'est donc pas du bruit pur.** Le micro n'a jamais *causé* un échec — mais sur
**2,68 % des busts du book déployé**, la barrière n'aurait pas été franchie *à ce
barreau-là* sans son excursion. Le book v2.8 est franchement plus serré que le v2.2
(marge médiane $27 contre $167), ce qui rend cette contribution structurellement plus
grande dans la configuration réellement déployée.

Bout-en-bout, l'effet reste sous le bruit : voir §5, tous les CI95 englobent 0. Mais le
**signe est constant** : les 8 bras qui retirent le risque du micro (`pnl_off`,
`placebo`, `backstop_étroit`, `token`, × 2 configs) sont **tous ≥ base**. Individuellement
du bruit ; conjointement, 8/8 dans la même direction.

### 3.4 L59 — re-pricing honnête de la sortie : FAIT, et immatériel ici

Le piège est confirmé à sa source : **1 590 / 1 590 (100 %) des sorties STOP du ledger
`nq_v2_trades.parquet` sont remplies au prix EXACT du stop** (`exit_px == stop_eff`),
81,6 % ont `r_gross = −1,000000` au tick, et les entrées sont à 100 % remplies
exactement à `level`. La série R consommée par le sim (`orb_e7_Rera.parquet`) hérite
intégralement de cette convention (37,8 % de R = −1,0 exact).

Re-pricing sur les barres M1 canoniques `NQ_1min_databento_2010-2026.parquet`
(couverture 100 % du ledger), fill honnête = `min(open, stop)` :

| | résultat |
|---|---|
| barres de stop qui **ouvrent au-delà** — M1 | **1,5 %** |
| idem — **M5** (la résolution du ledger) | **1,5 %** |
| dépassement conditionnel | moyenne 0,395 R, p50 0,231, p90 0,783, max 1,808 |
| dépassement inconditionnel | 0,0060 R / sortie STOP |
| effet sur la série R | moyenne −0,0024 R/trade ; Sharpe per-trade 0,000 → −0,030 |
| jours du panel touchés | **18 / 3 295** ; effet $ max sur une séance : **$0,74** |
| **Δp(campagne)** | **+0,00 pt, exactement, dans les deux configs** |

**Le « 25 % » de L59 est une valeur de FAMILLE, pas une constante.** Elle a été mesurée
sur `gap_pattern` — des sorties bracket sur barres daily incluant le gap overnight. Sur
un stop **intraday d'indice** à M1/M5, le taux est un ordre de grandeur plus bas (1,5 %).
La leçon reste juste — *re-pricer la sortie séparément* — mais son chiffre ne se
transporte pas ; c'est la re-mesure qui compte, et elle est faite.

### 3.5 L60 et L56 — contrôles gratuits, tous deux propres

**L60** (barres à fourchette nulle) : NQ M1 fenêtre 16:00–22:00 Paris **0,14 %** global
(pire année 2010 : 0,67 %) ; **US100.cash M1** (`data/deep_history_utc/`, l'instrument
réellement tradé, 4 081 738 barres 2013→2026) **0,10 %** global — 0,9 % en 2013, 0,4 %
en 2014, puis **≤ 0,1 % chaque année depuis 2015**. Aucune contamination par des prints
de règlement. `data/panels/m5_indices/` n'a pas été utilisé.

**L56** (horloge d'échange) : le décalage Paris↔New-York vaut 6 h la plupart du temps,
mais les deux zones ne basculent pas les mêmes semaines — **275 / 4 112 jours = 6,7 %,
soit ~16 jours/an**, où le décalage est de 5 h. Ces jours-là, l'OR « 15:30–16:00 Paris »
tombe **une heure à côté** de l'ouverture cash 09:30 ET. L'EA est cohéremment ancré
Paris (`ServerOfParisHM`), donc il n'y a pas d'incohérence sim↔live *interne* ; mais le
signal mesuré ces 16 jours n'est pas un opening-range d'ouverture américaine. Pour un
compteur, la conséquence est bornée (le jour bascule au pire dans le seau « sans
signal », §4) ; pour tout usage de l'ORB comme signal, c'est un défaut de définition.

---

## 4. Robustesse : les jours sans breakout

Le micro ne peut pas se poster s'il n'y a pas de signal ORB ce jour-là.

| | v2.2 | v2.8 |
|---|---:|---:|
| jours-tentatives **sans signal ORB** | 449 (3,56 %) | 511 (3,39 %) |
| … dont marqués quand même par le livre | 223 (49,7 %) | 349 (68,3 %) |
| jours **non marqués** (compteur n'avance pas) | 728 (5,8 %) | 1 211 (8,0 %) |
| backstop $1 déclenché | **50** | 52 |

Le compteur n'en souffre pas : ~3,4 % de jours sans signal, dont la moitié à deux tiers
sont couverts par le livre lui-même, et il reste **87 séances utilisables sur un mur de
91 jours** pour en trouver 4. C'est exactement ce que montre la distribution du §1
(p99 = 5 séances).

**Le vrai filet est le backstop 21:30, pas le micro** — et il est étroit. `Do2130Backstop`
(mq5:1113-1128) exige `!g_opened_today && g_open_days < 4 && bal >= TargetEq() &&
!OurPositionsExist()`. La condition `bal >= TargetEq()` en fait un **débloqueur de
deadlock de fin de phase** (« cible atteinte, jours manquants »), pas un filet de
couverture générale : 50 déclenchements sur 12 609 jours-tentatives.

### Deux verrous du live que le sim ne modélise PAS

1. **`InpMicroMinWidthBps = 10.0`** (mq5:56, 1041) : l'EA n'arme pas le micro si la
   largeur de l'OR est < 10 bps. Le sim n'a aucun équivalent. Mesuré : **0,63 % des
   jours à signal** (20 / 3 187 dans la fenêtre du sim ; largeur médiane 51 bps, min
   3,7 bps). Écart réel mais mineur.
2. **`g_targets_status != "OK"`** (mq5:1046-1048) : un `targets.json` périmé bloque
   **à la fois** l'entrée ON de 17:35 **et** l'armement du micro. Ce jour-là rien ne
   marque le jour, et le backstop ne rattrape pas (il exige `bal >= TargetEq()`). Le sim
   n'a pas cet état. Ce n'est pas hypothétique : `targets_status` latché à `MISSING` est
   un incident déjà rencontré en live (mémoire `vps_autopull_deploy_order_2026-07`), et
   `supervisor.py:328` en fait une alerte.
3. **Sémantique de la condition** : le yaml dit « posté seulement si aucun autre trade
   ouvert **à 21:30** ». Le sim l'évalue à 22:05 sur l'état **réalisé**. L'EA la décide à
   **16:00** sur une **prévision** (`IsONDay() || g_opened_today`, mq5:1044-1049) : il
   suppose que la jambe GER40 de 17:35 va bien s'ouvrir. Si elle échoue, le micro a déjà
   été renoncé. Sim et live ne posent pas la même question au même moment.

---

## 5. Existe-t-il un compteur strictement dominant ? Oui — et il est déjà dans le code

Six bras, deltas **appariés par cohorte**, block-bootstrap (blocs de 10 cohortes
contiguës, jamais iid), 462 cohortes.

### v2.2 (pinnée)

| bras | p(campagne) | essais | durée méd. | Δp vs base | CI95 bloc |
|---|---:|---:|---:|---:|---|
| **base (micro-ORB)** | **87,01 %** | 3,24 | 33 j | — | — |
| pnl_off (marque le jour, P&L = 0) | 88,10 % | 3,19 | 32 j | +1,08 | [−0,65 ; +3,25] |
| l59 (sortie re-pricée) | 87,01 % | 3,24 | 33 j | +0,00 | [+0,00 ; +0,00] |
| **placebo** (R décalé circulairement) | 88,10 % | 3,22 | 34 j | +1,08 | [−0,22 ; +3,25] |
| backstop étroit seul (micro OFF) | 88,31 % | 3,17 | 32 j | +1,30 | [−1,95 ; +4,98] |
| **token $1 généralisé** | 87,23 % | 3,23 | 32 j | +0,22 | [−2,16 ; +2,81] |
| **aucun compteur du tout** | **2,81 %** | 2,35 | 33 j | **−84,20** | [−88,96 ; −79,00] |

### v2.8 (live-fidèle)

| bras | p(campagne) | essais | durée méd. | Δp vs base | CI95 bloc |
|---|---:|---:|---:|---:|---|
| **base (micro-ORB)** | **80,52 %** | 2,84 | 35 j | — | — |
| pnl_off | 81,17 % | 2,84 | 35 j | +0,65 | [−1,30 ; +2,60] |
| l59 | 80,52 % | 2,84 | 35 j | +0,00 | [+0,00 ; +0,00] |
| **placebo** | 81,17 % | 2,82 | 35 j | +0,65 | [−1,30 ; +2,81] |
| backstop étroit seul | 80,95 % | 2,85 | 35 j | +0,43 | [−2,16 ; +3,03] |
| **token $1 généralisé** | 80,95 % | 2,81 | 35 j | +0,43 | [−1,95 ; +2,81] |
| **aucun compteur du tout** | **14,50 %** | 2,33 | 37 j | **−66,02** | [−74,24 ; −57,14] |

### Le placebo à autocorrélation appariée

Décalage circulaire de la série R du micro (SHIFT = 617 jours ouvrés) : marginale et
autocorrélation préservées, alignement aux dates détruit. Résultat : **le placebo est
indiscernable du bras `pnl_off`** (88,10 % vs 88,10 % ; 81,17 % vs 81,17 %), et les
deux sont **au-dessus** du micro réel. Traduction : **le P&L du micro ne porte aucune
information exploitable** — le remplacer par du bruit apparié donne le même résultat que
de le mettre à zéro. C'est la conclusion attendue pour une pièce de conformité, et elle
est ici positivement établie, pas supposée.

### Ce que le chiffre « +81,8 pt » désigne vraiment

Le **+81,8 pt marginal** cité dans `Multi_Asset/research/active/strategy_taxonomy_2026-08/
TAXONOMY.md:77` est **la valeur de la FONCTION compteur**, mesurée ici à **+84,20 pt**
(v2.2) / **+66,02 pt** (v2.8) contre l'absence totale de compteur. Ce chiffre est
substantiellement correct — sans compteur, un book qui atteint sa cible en 2–3 séances
échoue à 97 % / 86 % faute de pouvoir clôturer.

**Mais il n'appartient pas au micro-ORB.** Il appartient à la *règle*. Le support ORB
est, lui, **négatif ou nul** face à toutes les alternatives :

- vs **token $1 idéalisé** : **+0,22 / +0,43 pt en faveur du token**, CI95 ⊃ 0 ;
- vs **backstop étroit seul** : +1,30 / +0,43 pt en faveur du backstop, CI95 ⊃ 0 ;
- vs **son propre P&L mis à zéro** : +1,08 / +0,65 pt, CI95 ⊃ 0.

C'est exactement ce que `PORTFOLIOS_v2.2.md:67` documente déjà honnêtement (« le
micro-ORB coûte **−1,3 pt** vs le compteur $1 idéalisé, 87,0 vs 88,3 ») et que
`NONREGRESSION_v2.2.md` ancre en #17. **Le +81,8 pt de TAXONOMY.md attribue à l'ORB une
valeur qui est celle de la contrainte réglementaire** ; la citation est à corriger, pas
la pièce.

### Verdict de dominance

Sur **p(pass) et durée, il n'y a pas de dominance statistique** : tous les CI95
englobent 0, et 462 cohortes (N_eff bien inférieur) n'ont pas la puissance de résoudre
±1 pt.

Sur le **risque, la dominance est déterministe et ne demande aucun test** : un token
ouvert-fermé au marché à 0.01 lot porte **exactement le même coût de spread**
($0,03–0,07, sans commission, §3.2) pour une **exposition directionnelle nulle et une
excursion de règle nulle**, contre $6,23 de risque posé et $8,16 d'excursion maximale
pour le micro-ORB — et 23 busts pivotaux mesurés en v2.8. Le sim facture d'ailleurs le
token **$1,00**, soit **15 à 30× son coût réel** : le token est donc évalué ici sous une
hypothèse franchement défavorable et fait quand même jeu égal ou mieux.

**Le mécanisme dominant est déjà écrit et déjà déployé** : `Do2130Backstop`. Le
transformer en compteur principal ne demanderait qu'à **retirer sa condition
`bal >= TargetEq()`** — pas de nouveau code, pas de nouveau signal, pas de nouvelle
dépendance de données. C'est le bras `token $1 généralisé` ci-dessus.

**Ce n'est pas une recommandation de changement.** Le gain en p(pass) est
indiscernable de zéro, le gain en risque est réel mais petit (2,68 % des busts), et
toute modification toucherait `ftmo_live/mt5/book_executor.mq5` — chaîne de gel, pin
mqh, fenêtre du samedi, avec la certitude documentée qu'un lot de spec mal séquencé
coûte une journée de trading. **Le rapport bénéfice/risque opérationnel de la
modification est défavorable.** La pièce fait son travail ; elle n'est simplement pas
le meilleur support possible pour ce travail, et cela ne justifie pas d'y toucher.

---

## 6. Ce que ça ne prouve pas

1. **Tout est mesuré à l'intérieur de la comptabilité du sim.** Les trois verrous du
   live (§4) — largeur d'OR 10 bps, `targets_status`, décision à 16:00 sur prévision —
   n'y existent pas. Les 0,00 % d'échec de comptage sont un résultat *du modèle*. En
   live, un `targets.json` périmé perd un jour de comptage **sans filet**, et cet état
   s'est déjà produit.
2. **Le P&L du micro roule sur un ledger NQ futures appliqué à un CFD US100.cash.**
   Aucune base cash/futures, aucun spread broker, aucune différence de fill n'est
   modélisée. Je n'ai **pas** re-dérivé l'ORB sur `US100_M1` — c'eût été refaire le
   signal, hors mission.
3. **Le re-pricing L59 couvre la sortie STOP seulement.** Il ne couvre ni le
   remplissage d'entrée (100 % à `level` exact, non re-pricé), ni le fill du trail-to-BE,
   ni le slippage broker CFD. Il est fait sur NQ, à M1 et M5. Résidu signalé : **1,0 %
   des sorties `TIME_STOP` touchent pourtant leur stop d'origine en intraday** (~24
   trades) — incohérence de chemin mineure du ledger, non expliquée ici.
4. **Aucun overlay flash intra-M5.** L'effet connu (−3,9 pt single / −1,7 pt campagne,
   `p2_flash_tail_2026-07`) n'est pas inclus : tous les p(pass) ci-dessus restent des
   **bornes hautes**.
5. **La définition d'un « jour de trading » n'est pas sourcée dans le dépôt.** Toute la
   pièce existe pour satisfaire `min_trading_days = 4`, mais `PropFirms/ftmo/rules.md:27`
   se contente de « ✓ ≥4 trading days » sans jamais **citer** ce qui compte comme un jour
   — position ouverte ? fermée ? ordre passé ? Chaque autre règle du fichier est citée
   verbatim ; celle-ci ne l'est pas. La stratégie « ouvrir-fermer 0.01 lot pour marquer
   le jour » repose donc sur une lecture non vérifiée à la source primaire. **C'est le
   défaut le plus sérieux de cette pièce de conformité, et il est documentaire, pas
   quantitatif.**
6. **Ambiguïté de barrière héritée, non résolue ici.** `rules.md:66` cite un floor
   *high-water-marké* (« highest balance … or, if higher, Initial Capital ») tandis que
   tous les sims utilisent un floor **statique** à $9 000 (`E.FLOOR`). Pour un compte en
   gain, le floor statique est **optimiste**. Hors périmètre — je l'hérite, je ne le
   tranche pas.
7. **Puissance.** Tous les Δp ont un CI95 qui traverse zéro. L'absence de différence
   détectable n'est pas une preuve d'équivalence : 462 cohortes chevauchantes ne
   résolvent pas ±1 pt. Le seul argument de dominance qui tienne est **déterministe**
   (risque directionnel nul), pas statistique.
8. **Aucune conclusion sur l'ORB comme source de rendement.** La famille reste
   DSR-FAIL ; `orb_e7_Rera` a une moyenne de **−0,0000 R** sur 4 013 trades. Rien ici ne
   rouvre cette question, et rien ici ne devrait servir à la rouvrir.

---

## Reproduction

```
cd Multi_Asset/research/active/audit_micro_orb_2026-08/code
/usr/bin/python3 mo_nonreg.py         # 462/462 identiques + ancre 87.01
/usr/bin/python3 mo_q1_counter.py     # Q1/Q2/Q4  (ancres 9,248 poses / 50 backstop)
/usr/bin/python3 mo_q3_l59.py         # L59 M1  -> out/mR_l59.npy
/usr/bin/python3 mo_q3b_bars.py       # L59 M5 + L60 + L56
/usr/bin/python3 mo_q3_risk.py        # 6 bras + placebo apparié + P&L
/usr/bin/python3 mo_pivot.py          # busts pivotaux
/usr/bin/python3 mo_q5_counter_value.py
```

Caches et parquets intermédiaires en `out/` (gitignoré, régénérable). Les données
d'entrée sont lues **en lecture seule** au chemin absolu du répertoire principal
(`<HOME>/Desktop/Algo_claude/data/...`). Aucun chemin live modifié.
