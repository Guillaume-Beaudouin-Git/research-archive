# La sleeve overnight tient-elle la bonne moitié de la journée ?

**2026-08-04.** Worktree `claude/overnight-vs-intraday`, base `a3b1f8e6`. Interpréteur
`/usr/bin/python3` explicite. **Diagnostic — aucun chemin live touché, aucune modification de
spec proposée à ce stade.** Données `data/deep_history_utc/` (vrai UTC vérifié), lues en
lecture seule depuis le répertoire principal ; caches hors repo.

Question posée par le propriétaire du compte : *« Pourquoi sort-on en journée ? On vient de
manquer une forte hausse. »* Contexte : le papier NY Fed *The Disappearing Overnight Drift*
(juillet 2026) mesure le drift overnight ES/NQ/YM à **zéro depuis 2021**.

---

## 0. Le tableau demandé

**BOOK = les deux jambes au poids du spec (0.6 US100 + 0.6 GER40), jours d'entrée lundi+mardi,
bps par événement, net de coûts (1.8 bps RT + swap long mesuré).**

| | pré-2021 | | | post-2021 | | |
|---|--:|--:|--:|--:|--:|--:|
| | **moy.** | **t_HAC6** | **N** | **moy.** | **t_HAC6** | **N** |
| **TENU** (22:05→15:30 / 17:35→09:00) | **+5.73** | **2.45** | 652 | **+4.73** | **1.66** | 513 |
| **ESQUIVÉ** (la séance cash) | +2.56 | 0.84 | 652 | +1.24 | 0.31 | 513 |
| **24 H** (ne jamais sortir) | **+10.45** | **2.76** | 652 | **+8.13** | **1.59** | 513 |

En gross (pour lire le signal sans le dénominateur) :

| | pré-2021 | | post-2021 | |
|---|--:|--:|--:|--:|
| | **moy.** | **t_HAC6** | **moy.** | **t_HAC6** |
| TENU | +10.11 | **4.33** | +9.10 | **3.19** |
| ESQUIVÉ | +4.72 | 1.55 | +3.40 | 0.85 |
| 24 H | +14.83 | 3.92 | +12.50 | 2.44 |

### La réponse en une phrase

**Oui — la sleeve tient bien la moitié qui porte l'alpha (la nuit rapporte 2 à 3× la séance,
avec un t double), mais cet alpha a fondu et ne franchit plus seul le seuil de significativité
depuis 2021 ; et la sortie en journée ne coûte pas du carry, elle achète de la survie sous
barrière.**

Trois nuances, chacune chiffrée plus bas :

1. **Le drift overnight n'est PAS mort ici** — contrairement à ES/NQ/YM dans le papier NY Fed.
   Gross, il perd 10 % et garde **t 3.19** post-2021. Le papier mesure une fenêtre de 1 h
   (02:00-03:00 ET) sur des futures ; cette sleeve tient 17 h de CFD. Ce n'est pas le même objet.
   **Ne pas transposer le kill.**
2. **Le propriétaire a raison sur les faits** : tenir 24 h aurait rapporté **+4.14 bps/événement
   de plus** (t 1.69, bootstrap 90 % [+0.31 ; +8.14]) — réel, mais faible.
3. **Et il a tort sur la cause.** Ce n'est pas gratuit : tenir 24 h **double la queue** face à des
   barrières que le compte est en train de longer.

---

## 1. La prémisse du brief sur le swap est FAUSSE — et c'est vérifiable en trois lignes

> *« Tenir 24 h ajoute une nuit de swap — c'est peut-être toute la réponse. »*

**Non.** Le rollover FTMO est à 00:00 serveur (EET) = **23:00 CET toute l'année** (Prague et
Bucarest partagent le DST européen, l'écart est invariablement de 1 h). Or :

- `22:05(D) → 15:30(E)` franchit **un** rollover : celui de la nuit de D.
- `22:05(D) → 22:05(E)` franchit **le même et unique** rollover.

Tenir 24 h ne paie **pas un centime de swap de plus**. Pire pour la thèse du carry : en chaîne
(lundi 22:05 → mercredi 15:30 d'un trait), la version 24 h paie **un seul aller-retour au lieu
de deux**. Le `1 RT/événement` facturé ici **sur-estime** son coût d'environ 50 %.

⇒ **Le carry n'explique rien de la sortie en journée.** Toute la justification, si elle existe,
doit être ailleurs. Elle l'est — §4.

*(Le triple swap indices est bien modélisé — `triple_dow: 4` = vendredi dans le spec — mais il ne
touche aucune nuit lundi/mardi. Il ne concerne que le tableau des cinq nuits, §5.)*

---

## 2. Étape 0 — les bornes, avant toute conclusion (L52, L56, L60)

Ce dossier est exactement celui où une décomposition overnight/intraday se trompe de journée.
Contrôles faits **avant** de regarder le moindre rendement (`results/step0_*.csv`) :

| Contrôle | Mesure | Verdict |
|---|---|---|
| **L56** — profil horaire hiver vs été, horloge **CET** (celle du schedule EA) | corr **0.991** (US100) / **0.971** (GER40) | **PASS** |
| **L56** — même profil, horloge **ET** (Nasdaq) | corr **0.991** / **0.971** | **PASS** |
| **L56** — même profil, **UTC** | corr **0.785** / **0.703** | l'UTC serait la mauvaise horloge |
| **L52** — 15:30 CET tombe-t-il sur l'ouverture cash US ? | 8.22 bps de \|ret\| moyen, **99.79ᵉ pct** de la journée | **PASS** |
| **L52** — 09:00 CET sur l'ouverture cash DE ? | 7.68 bps, **99.79ᵉ pct** | **PASS** |
| **L52** — 22:05 CET (entrée US100) | 3.09 bps, 88ᵉ pct, et l'activité **décroît** après (4.09 → 2.04) | cohérent avec un post-clôture |
| Couverture de barre à l'horodatage exact | US100 22:05 : **69.1 %** exact, **92.5 %** à ±20 min ; les 3 autres bornes ≥ 98.8 % | tolérance 20 min appliquée |
| **L60** — barres `high==low`, US100 | ≤ 0.03 % depuis 2016 (0.00 % depuis 2022) | **PASS** |
| **L60** — barres `high==low`, GER40 | 1-2 % post-2015 (11.8 % en 2013) | acceptable, 2013 écarté de fait |
| **L56 corollaire** — part du gap de halt CFD (23:00 CET) dans le segment tenu | **+0.55 bps sur 9.58** (5.7 %) US100, **+0.39 sur 8.22** (4.8 %) GER40 | **PASS — l'edge n'est pas un gap** |

Deux points méritent d'être notés :

- **Les deux horloges plausibles donnent la même réponse ici**, parce que CET et ET basculent
  quasiment ensemble. Le test n'était pas superflu pour autant : l'UTC, lui, aurait décalé la
  moitié de l'échantillon d'une heure (L56 verbatim).
- **Mais pas tout à fait ensemble.** Il existe 2 à 3 semaines par an (mars, fin octobre) où
  l'Europe et les États-Unis ne sont pas en phase : **4.2 % des jours d'entrée US100 et 7.1 %
  des GER40**. Sur ces jours-là, `22:05 CET` vaut **17:05 ET**, pas 16:05 ET — la sleeve entre
  **une heure après** ce qu'elle croit, et sort à 10:30 ET au lieu de 09:30 ET. C'est dans le
  code de production. Effet mesuré : ces jours rapportent **plus** (+19.4 / +17.5 bps contre
  +7.1 / +7.7), mais sur N = 92 / 52. **Curiosité à surveiller, pas un résultat** — et en tout
  cas pas un dommage.

---

## 3. Le drift overnight a décayé, il n'est pas mort

Par instrument, gross, jours lundi+mardi (`results/step2_head_era.csv`) :

| | pré-2021 | | post-2021 | | décroissance |
|---|--:|--:|--:|--:|--:|
| | moy. | t | moy. | t | |
| US100 TENU | 9.14 | 3.96 | **6.65** | **2.22** | −27 % |
| GER40 TENU | 8.62 | 3.73 | **7.02** | **2.84** | −19 % |
| US100 ESQUIVÉ | 4.95 | 1.71 | 3.34 | 0.69 | — |
| GER40 ESQUIVÉ | 0.49 | 0.16 | 1.52 | 0.43 | — |

**Le drift perd 19-27 % de son gross et garde t 2.2-2.8. Ce n'est pas le zéro du papier NY Fed.**
Ce que le papier tue est une fenêtre d'une heure sur des futures, avec un mécanisme précis
(transmission d'inventaire après le déséquilibre de clôture). La sleeve tient une fenêtre 17×
plus large sur un autre véhicule. **Citer le papier, ne pas lui faire dire ce qu'il ne dit pas.**

**Ce qui fait mal n'est pas la décroissance, c'est que le coût, lui, ne décroît pas.** 4.4 bps
de coût fixe (1.8 RT + 2.6 de swap sur les deux jambes) prélevés sur un gross qui passe de 10.1
à 9.1 : le net passe de 5.73 à 4.73 et le **t tombe de 2.45 à 1.66**. Post-2021, la sleeve seule
**ne franchit plus le seuil**, avec un bootstrap par blocs à 90 % de **[+0.16 ; +9.54]** qui
frôle zéro et un **DSR de 0.437** (n_trials = 12, `std_sr_trials` au plancher d'échantillonnage,
`rf = 0.0` comme exigé).

### Concentration de régime (le DSR ne la voit pas — d'où le walk-forward)

Walk-forward, 6 folds chronologiques égaux (`results/step3_walkforward.csv`), moyenne bps, BOOK :

| fold | période | ESQUIVÉ | TENU | 24 H |
|---|---|--:|--:|--:|
| 1 | 2013-01 → 2015-06 | +1.43 | **−1.78** | +1.80 |
| 2 | 2015-06 → 2017-08 | +3.76 | +4.72 | +10.64 |
| 3 | 2017-08 → 2019-11 | +2.27 | +0.33 | +4.76 |
| 4 | 2019-11 → 2022-01 | −1.17 | **+16.37** | +17.36 |
| 5 | 2022-01 → 2024-03 | +2.72 | +2.87 | +7.75 |
| 6 | 2024-04 → 2026-06 | +2.78 | +7.18 | +12.12 |
| | **folds positifs** | 83 % | **83 %** | **100 %** |

**TENU : 5/6 folds positifs — au-dessus du gate WF > 60 %.** Mais le fold 4 (COVID) porte le
triple des autres. Contrôle explicite hors 2020 (`results/step4_ex2020.csv`) :

| net, bps | full | hors 2020 |
|---|--:|--:|
| US100 TENU | 4.17 (t 2.27) | **1.64 (t 0.94)** |
| GER40 TENU | 4.57 (t 2.70) | **2.77 (t 1.82)** |

⇒ **une part substantielle de la significativité full-sample est du COVID.** L'échantillon
décisionnel reste le post-2021, qui exclut 2020 par construction et donne 2.73 / 3.66 : le signal
survit, sa marge est mince.

---

## 4. Le contrefactuel : pourquoi sortir, alors, si 24 h rapporte plus ?

Différence appariée `24H − TENU` (= exactement la séance esquivée, mêmes jours, mêmes coûts) :

| | moy. bps | t_HAC6 | N | bootstrap blocs 90 % |
|---|--:|--:|--:|---|
| BOOK, pré-2021 | +4.72 | 1.55 | 652 | [−0.43 ; +9.56] |
| BOOK, post-2021 | +3.40 | 0.85 | 513 | [−2.81 ; +10.14] |
| BOOK, total | **+4.14** | 1.69 | 1165 | [+0.31 ; +8.14] |

**Le propriétaire a factuellement raison** : on laisse ~4 bps/événement sur la table. Mais le
gain n'est significatif ni post-2021 ni pré-2021 pris séparément, et l'essentiel vient d'US100
(+4.28, t 1.63) — GER40 n'apporte rien (+0.93, t 0.40 : la séance de Francfort est **plate à
négative**, exactement le tug-of-war du papier Lou-Polk-Skouras).

### Et voici ce que ces 4 bps coûtent

Excursion adverse **du book entier** (2 jambes, grille 5 min, MTM depuis le prix d'entrée), **au
levier réellement déployé** — `on_w 0.6 × vm 14 = 8.4×` de notionnel par jambe (L54 : toute
condition de drawdown s'évalue au levier déployé) :

| | N | exc. moyenne | p05 | p01 | pire | **% évts < −5 %** | **% évts < −10 %** |
|---|--:|--:|--:|--:|--:|--:|--:|
| **TENU**, total | 1165 | **−3.29 %** | −10.2 % | −17.3 % | −43.8 % | **20 %** | **5 %** |
| **24 H**, total | 1165 | **−5.78 %** | −18.3 % | −28.6 % | −43.8 % | **42 %** | **18 %** |
| TENU, post-2021 | 513 | −3.54 % | −10.8 % | −16.1 % | −39.0 % | 24 % | 6 % |
| 24 H, post-2021 | 513 | −6.04 % | −18.1 % | −27.1 % | −39.0 % | 43 % | 20 % |

Apparié, événement par événement : **24 H est strictement pire 57 % du temps, de −2.50 pt
d'equity en moyenne**, jusqu'à −24 pt.

**Rappel des barrières : daily −5 %, floor −10 %.**

⇒ **La sortie en journée n'achète pas du rendement, elle achète de la survie.** Tenir 24 h
double presque le rendement moyen (+9.43 vs +5.29 bps net) **et** double l'exposition à la
barrière journalière (42 % vs 20 %) et la **triple et demie** à la barrière de mort (18 % vs 5 %).
La séance cash est aussi là où vit la queue : sur US100, kurtosis **13.0** contre **4.5** pour la
nuit, et pire excursion de jambe −57 % contre −38 % d'equity.

**Deux réserves d'honnêteté sur ce tableau, à ne pas escamoter :**

1. Ces excursions sont **brutes de machinerie de risque** : ni taper, ni breaker M5 à 30 % de
   room, ni vol-derisk, ni cap de marge 60 % — le compte n'a évidemment pas explosé 20 % des
   lundis. **C'est une comparaison RELATIVE entre variantes à machinerie identique, pas une
   prévision de breach.** Le rapport 2.1× et 3.6× est le résultat ; les niveaux ne le sont pas.
2. **Il n'existe pas d'échappatoire par le reset de minuit.** Vérifié dans le moteur qui pilote
   le live (`cleanroom/engine.py:249`) : `limit = bal − DAILY_BUDGET` avec `bal` = **balance**
   (positions closes) et `eq = bal + MTM depuis le prix d'ENTRÉE`. La perte latente accumulée
   depuis l'entrée compte **intégralement** contre le budget du jour suivant, sans remise à zéro
   à 00:00 Prague. L'excursion depuis l'entrée est donc bien la métrique de barrière correcte —
   c'est ce qui est mesuré ici. *(Contrôle fait précisément parce que l'intuition inverse — L51,
   « un jour de trading n'est pas un jour calendaire » — était plausible et se serait révélée
   fausse ici.)*

---

## 5. Les cinq nuits : la restriction lundi+mardi tient, mais lundi est en train de lâcher

Jamais audité jusqu'ici. TENU **net**, par nuit d'entrée et par ère (`results/step4_dow.csv`) :

| | GER40 pré-2021 | GER40 post-2021 | US100 pré-2021 | US100 post-2021 |
|---|--:|--:|--:|--:|
| **lundi** | **+9.34** (t 1.79) | **−1.15** (t −0.32) | **+3.50** (t 0.96) | **−0.46** (t −0.10) |
| **mardi** | +1.29 (t 0.44) | **+8.38** (t 1.82) | +6.81 (t 1.89) | **+5.61** (t 1.24) |
| mercredi | −4.80 | +0.30 | −2.91 | +3.04 |
| jeudi | −1.14 | −5.93 | −2.23 | −4.97 |
| vendredi | −3.51 | −9.22 | −3.13 | −6.17 |

**Deux lectures, de force très inégale :**

- **La restriction elle-même est justifiée et le reste.** Jeudi et vendredi sont franchement
  négatifs dans les deux ères et sur les deux instruments (jusqu'à −9.2 bps). Tenir les cinq
  nuits serait nettement pire. *(Le vendredi cumule d'ailleurs le triple swap, correctement
  modélisé ici.)*
- **Mais lundi a changé de signe post-2021 sur les deux instruments**, pendant que mardi tient.
  Écart mardi − lundi post-2021 : **+9.53 bps sur GER40 (t 1.82)**, +6.07 sur US100 (t 0.88).

**C'est un DRAPEAU, pas un mandat.** Aucun de ces écarts n'est significatif isolément ; on
regarde 5 nuits × 2 instruments × 2 ères, donc la correction multiple s'applique et rien ne
survit à un Šidák honnête. **La conclusion défendable est : « lundi mérite une ré-évaluation
pré-enregistrée », pas « couper lundi ».** Couper lundi sur ces chiffres serait précisément le
data-mining que la politique de ré-ouverture interdit.

---

## 6. Sensibilité au coût

Fourchette `COST_AUDIT.md` pour les indices : centre ~0.9 bps RT, queue 2.3 (p95), le sim v22
facture 2.2 uniformément. BOOK net, bps (`results/step4_cost_sensitivity.csv`) :

| RT bps | 0.9 | 1.8 | 2.2 | 2.9 |
|---|--:|--:|--:|--:|
| TENU total | 6.37 (t 3.52) | 5.29 (t 2.92) | 4.81 (t 2.66) | 3.97 (t 2.19) |
| TENU post-2021 | 5.81 (t 2.04) | **4.73 (t 1.66)** | 4.25 (t 1.49) | 3.41 (t 1.19) |
| ESQUIVÉ post-2021 | 2.32 (t 0.58) | 1.24 (t 0.31) | 0.76 (t 0.19) | **−0.08 (t −0.02)** |
| 24 H post-2021 | 9.21 (t 1.80) | 8.13 (t 1.59) | 7.65 (t 1.49) | 6.81 (t 1.33) |

**La conclusion est invariante sur toute la fourchette** : TENU reste positif partout, ESQUIVÉ
passe sous zéro dès le haut de fourchette. Le classement des trois variantes ne change jamais.
Aucun résultat de ce dossier ne dépend du choix du dénominateur.

---

## 7. Ce qu'il faut retenir, et ce qu'il ne faut PAS faire

**Réponse à la question posée : oui, la sleeve tient la bonne moitié.** La nuit rapporte 9.66 bps
gross (t 5.34) contre 4.14 (t 1.69) pour la séance ; net, 5.29 (t 2.92) contre 1.98 (t 0.81). Le
choix de design est le bon, et il l'est encore post-2021.

**Trois réserves, par ordre d'importance décroissante :**

1. **Post-2021, la sleeve seule ne franchit plus le seuil** (t 1.66, DSR 0.437, IC bootstrap
   [+0.16 ; +9.54]). Elle n'est pas morte — le kill NY Fed ne transfère pas — mais la marge est
   mince, et une part importante de la significativité full-sample vient de 2020.
   **Conséquence directe : le livre est MONO sur une sleeve qui ne prouve plus rien seule.** Le
   remède est d'**ajouter des moteurs**, pas de retoucher celui-ci (cohérent avec
   `nightly_us100_investigation_2026-07`).
2. **La question du propriétaire est légitime et sa prémisse factuelle est juste** : oui, on
   laisse ~4 bps/événement. Mais le prix est de doubler l'exposition à la barrière journalière
   et de tripler et demi celle au floor — sur un compte **à 723 $ de son plancher**. Ce n'est pas
   un arbitrage à faire en challenge.
3. **La justification par le swap, elle, ne tient pas** et il vaut mieux ne plus la répéter :
   tenir 24 h ne coûte **aucune** nuit de swap supplémentaire, et économise même un aller-retour.
   La bonne justification est géométrique, pas comptable.

**Recommandation de modification de spec : AUCUNE.** Les chiffres ne portent aucun changement.
Le seul point qui mérite un travail pré-enregistré est **la nuit du lundi** (§5) — et il devrait
l'être comme une hypothèse écrite avant de retoucher la donnée, avec correction multiple.

**Et si un jour un changement était porté par les chiffres**, il passerait par la chaîne de gel
et la **fenêtre du samedi** : le VPS pull `main` toutes les 30 min, donc merger *est* un
déploiement Python — merger avant de déployer le binaire produit un BAD_SHA et coûte une journée
de trading (`vps_autopull_deploy_order_2026-07`, `spec_chain_v28_ready_2026-07`).

---

## Annexe — reproduction

```
/usr/bin/python3 code/step0_integrity.py        # L52 / L56 / L60, couverture des bornes
/usr/bin/python3 code/step1_segments.py         # décomposition additive TENU/ESQUIVÉ/24H
/usr/bin/python3 code/step2_tables.py           # ère, année, jour de semaine, gap de halt
/usr/bin/python3 code/step3_contrefactuel.py    # 3 séries, diff appariée, bootstrap, DSR, WF
/usr/bin/python3 code/step4_robustesse.py       # hors-2020, nuits, coût, excursions par jambe
/usr/bin/python3 code/step5_book_excursion.py   # excursion de book au levier déployé
```

Conventions : log-returns en bps, additivité `TENU + ESQUIVÉ = 24H` vérifiée à 3e−12 ;
t de Newey-West lag 6 ; bootstrap **par blocs** circulaire (blocs de 10, 5 000 tirages) ;
annualisation en **√(événements/an) = √102** (L47) ; DSR via `dsr.py` racine avec
`std_sr_trials` au plancher d'échantillonnage et **`rf = 0.0`**.

**Compteur local d'essais de ce diagnostic : 12** (3 segments × 2 instruments × 2 ères), à
réconcilier au ledger global à la clôture. Aucun blob de données commité.
