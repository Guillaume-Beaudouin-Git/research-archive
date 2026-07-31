# RESULTS — Ré-ouverture du sleeve overnight or (E002) contre les barrières FTMO réelles

**2026-07-31.** Worktree `claude/overnight-sleeve-reopen`. Interpréteur `/usr/bin/python3`
explicite. Aucune écriture hors de ce répertoire, aucun chemin live touché.

Ré-ouverture instruite au titre de la politique du 2026-07-30 : le kill de juin 2026 était
de nature **GÉOMÉTRIE + VÉHICULE**, donc rouvrable. L'angle nouveau, écrit avant de toucher
la donnée : *le mur de 91 jours était auto-imposé, le coût de l'or était sur-facturé 1.9×,
et le panier détruisait le Sharpe — que devient p(pass) quand on retire les trois ?*

---

## 0. Verdict

**UNDERPOWERED — pas PASS, pas REJECTED.** La ré-ouverture était **justifiée** : les trois
corrections annoncées sont toutes réelles et toutes chiffrées. Mais le candidat ne franchit
pas la ligne, pour une raison qui n'était dans aucune des hypothèses de départ.

Ce qui se confirme : lever le mur de 91 jours vaut **+42 points** de p(pass), corriger le
coût en vaut **+10 à +31** selon l'horizon, et le sleeve autonome domine le panier. Le
véhicule passe nettement — contrairement au soja, **le CFD XAUUSD de FTMO cote bien la
réouverture Globex** (99.78 % des séances tradées ont un print FTMO dans les 15 premières
minutes) — et, géométrie non remarquée jusqu'ici, la fenêtre s'ouvre **exactement à l'heure
de reset du plafond journalier FTMO** (00:00 Prague), 93.2 % des jours.

Ce qui bloque : deux découvertes faites en route.

1. **La série héritée est winsorisée à 0.5/99.5** (`step3_performance.py:tradable_series`),
   ce qui est anodin pour un Sharpe et **disqualifiant pour une simulation de barrière** :
   le clip transformait la pire séance de **−6.77 % en −1.65 %** et le skew de séance de
   **−0.49 en +0.20**. Toute la lecture « ce sleeve a un skew positif » est un artefact de
   clip au niveau de la séance. Ce travail utilise la série **brute**.
2. **Sur l'échantillon décisionnel post-2021, la marge fond.** Le gross survit — 3.79 bps,
   **t_HAC 2.74**, il ne va **pas** à zéro comme le drift ES/NQ/YM du papier NY Fed — mais
   il ne perd que 28 % pendant que le coût, lui, ne bouge pas : **1.84 bps sur 3.79 bps de
   gross, c'est 49 % du signal**. Net, SR 0.848, **t_HAC 1.90**, **DSR 0.284** (n_trials=95).
   Au coût catalogue : SR 0.178, DSR 0.017.

⇒ Le p(pass) full-sample (jusqu'à 0.66) **n'est pas citable**. Le p(pass) décisionnel est
celui de post-2021 : **0.286 sous l'ancien mur de 91 jours, 0.708 à horizon illimité** —
et une fois la simulation emboîtée dans un bootstrap par blocs **de l'histoire** (§5), il
devient **0.593, IC90 [0.321 ; 0.817]** à `vm` 2, pour une **durée médiane de 185 séances
(~9 mois)** et un p90 de 549 séances.

**Tout le dossier se réduit alors à une seule mesure non faite.** Au coût **mesuré**
(1.84 bps), 1.5 % seulement des histoires alternatives ont un Sharpe négatif et le 5ᵉ
percentile de p(pass) — **0.321** — bat encore le taux single-challenge du book FTMO
déployé (~0.23-0.25). Au coût **catalogue** (3.50 bps), **39.5 % des histoires n'ont aucun
edge**. Or le 1.84 bps est un spread médian **toutes heures confondues**, alors que ce
sleeve entre à la réouverture après une pause d'une heure — le pire moment de la journée
pour un spread. **Le candidat est suspendu à un chiffre que personne n'a relevé.**

**Ce que ce test établit sans ambiguïté**, en revanche : le verdict « FTMO NON-VIABLE » de
juin 2026 était **mal motivé**. Il n'a pas été produit par l'absence d'edge ni par le
véhicule, mais par un mur d'horizon inexistant dans le règlement FTMO et par un coût
sur-facturé de 90 %. C'est une erreur de type II documentée, pas un signal mort.

---

## 1. Étape 0 — le véhicule passe (et c'est ce qui a tué le soja)

`results/step1_vehicle_gates.csv`. Source : `data/ftmo_portfolio/cache/XAUUSD_m5_close.parquet`
— **le flux du broker FTMO-Demo** (provenance : MEMORY `mt5_data_provenance_2026-06`), pas
une reconstruction tierce. C'est le bon test : la question n'est pas « le marché bouge-t-il
à cette heure » mais « **mon broker cote-t-il cette heure** ».

| Contrôle | Mesure | Verdict |
|---|---|---|
| **V1** créneaux M5 cotés dans l'heure de réouverture | **9.53/12 (hiver), 9.16/12 (été)** | **PASS** |
| **V1** séances **tradées** avec un print FTMO dans les **15 premières minutes** | **4 890 / 4 901 = 99.78 %** | **PASS** |
| V1 créneaux cotés pendant la pause de settlement | 3.0-3.4 / 12 | cohérent avec les 33 % archivés |
| **V2** reset DLL FTMO (00:00 Prague) ≡ début de fenêtre | **5 642 / 6 053 = 93.2 %** | **PASS** |
| **V3 (L60)** barres H1 à fourchette nulle | 0.23 % (0.51 % dans la fenêtre) | **PASS** |
| **V3 (L60)** prints M1 identiques consécutifs | 4.18 % (7.55 % dans l'heure de réouverture) | PASS, à noter |

**Le contraste avec le soja est total** : là-bas le CFD ne cote **jamais** la réouverture
CBOT (`N = 0` séances communes, `overnight_futures_2026-07/RESULTS.md §6`). Ici le flux
FTMO cote 9 créneaux M5 sur 12. Le véhicule n'est pas le problème de ce candidat.

**Géométrie non remarquée jusqu'ici, et elle est favorable.** Le plafond de perte
journalière FTMO se recalcule à 00:00 CE(S)T = **23:00 UTC en hiver / 22:00 UTC en été**
(`PropFirms/ftmo/rules.md:46`). La réouverture Globex 18:00 ET tombe **aux mêmes heures
UTC**, parce que les deux horloges suivent leur propre DST. Résultat : le sleeve ouvre sa
position au moment précis où le budget journalier de 5 % est remis à neuf, et la referme
8 h plus tard sans qu'aucun autre trade ne partage la journée. **Le sleeve dispose de la
totalité du budget journalier, tous les jours.** Les 6.8 % de jours désalignés sont les
2-3 semaines/an où les calendriers DST américain et européen divergent ; sur ces jours la
fenêtre est coupée en deux jours FTMO, ce qui **réduit** l'exposition de chaque moitié à
la barrière — la modélisation alignée est donc la conservatrice.

---

## 2. Le défaut de mesure trouvé dans la série héritée

Le reproduction gate passe à la précision machine (**max |diff| = 1.0e-16** sur les séances
non clippées, N = 4 901) : ma chaîne EST celle de `overnight_futures_2026-07`. Contrôle
croisé sur les têtes de gondole archivées : full-sample au coût futures 0.66 bps je
retrouve **SR 1.733** (archivé 1.733) et sur 2020-2026 **SR 1.290 brut / 1.357 winsorisé**
(archivé 1.313, entre les deux).

Mais `tradable_series` termine par `s.clip(*s.quantile([0.005, 0.995]))`. Effet :

| | mean bps | sd bps | **skew** | kurtosis | **pire séance** |
|---|--:|--:|--:|--:|--:|
| `ret` **BRUT** | 4.850 | 47.72 | **−0.49** | 24.31 | **−6.77 %** |
| `ret` winsorisé (série archivée) | 4.934 | 42.09 | **+0.20** | 3.61 | **−1.65 %** |

Le clip ne change le Sharpe que de +0.06. Il change **la queue d'un facteur 4** — et une
simulation de premier passage n'est qu'une machine à intégrer cette queue. Le « skew +0.99,
la propriété la plus précieuse du sleeve » du rapport de juillet est mesuré après ce clip.

**Ajout indispensable : le chemin intra-fenêtre.** FTMO applique le plafond journalier sur
l'**équity**, pas sur la clôture. J'ai donc reconstruit, sur M1 (médiane 475 prints par
fenêtre), l'excursion adverse maximale de chaque séance et je la fais voyager dans le
**même index de bootstrap** que la clôture. Écart médian excursion↔clôture : **11.1 bps** ;
p01 de l'excursion **−1.72 %** contre **−1.16 %** en clôture ; pire excursion **−8.99 %**.
Ignorer le chemin sous-estimerait la mort par barrière journalière d'environ moitié.

---

## 3. Le test de régime imposé — « The Disappearing Overnight Drift » (NY Fed, 07/2026)

`results/step2b_regime_split.csv`. Séries **brutes**, coupure **2021-01-01**, t_HAC lag-6.

| Sleeve | ère | N | gross bps | t_HAC | SR gross | net@**1.84** | t_HAC | SR | net@**3.50** | t_HAC | SR |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **GOLD** | full | 4901 | 4.85 | **7.11** | 1.614 | 3.01 | **4.41** | 1.002 | 1.35 | 1.98 | 0.449 |
| **GOLD** | pré-2021 | 3590 | 5.24 | **6.70** | 1.842 | 3.40 | **4.35** | 1.195 | 1.74 | 2.22 | 0.611 |
| **GOLD** | **post-2021** | **1311** | **3.79** | **2.74** | **1.108** | **1.95** | **1.41** | **0.570** | **0.29** | **0.21** | **0.085** |
| SILVER | pré-2021 | 1770 | 4.71 | 2.65 | 1.067 | 2.87 | 1.61 | 0.650 | 1.21 | 0.68 | 0.274 |
| SILVER | post-2021 | 1398 | 4.84 | 1.77 | 0.688 | 3.00 | 1.09 | 0.426 | 1.34 | 0.49 | 0.191 |
| WTI | pré-2021 | 1934 | −0.99 | −0.45 | −0.149 | −2.83 | −1.29 | −0.428 | −4.49 | −2.05 | −0.679 |
| WTI | post-2021 | 1399 | 2.31 | 1.09 | 0.407 | 0.47 | 0.22 | 0.082 | −1.19 | −0.56 | −0.211 |

**Réponse au point 2 du mandat : NON, l'effet n'est pas concentré avant 2021, donc le
candidat n'est pas REJECTED sur décroissance d'alpha.** Le drift or post-2021 reste
**significatif en gross** (t_HAC 2.74) — il ne disparaît pas comme le drift indiciel du
papier. Le gross perd **28 %** (5.24 → 3.79 bps), pas 100 %.

**Réponse au point 3 : le niveau auquel il survit ne suffit pas.** Ce sont **1.84 bps de
coût sur 3.79 bps de gross** : le coût mange **49 %** du signal post-2021 (contre 35 %
pré-2021). Net, le t tombe à **1.41** et le DSR (n_trials=95, cohérent avec l'étude source)
à **0.284**. Au coût catalogue de 3.50 bps, DSR **0.017**. Même au coût **futures** de
0.66 bps, le DSR post-2021 n'est que **0.714** — sous n'importe quel seuil du repo.

Le WTI reste mort dans les deux ères. L'argent post-2021 n'est pas significatif et reste
tué par trois voies indépendantes (marge, gap 59 %, capture 0.18).

### 3.1 Le mécanisme du papier NY Fed ne se réplique PAS sur nos instruments

`results/step2b_flow_dispersion.csv`. Proxy gratuit demandé : dispersion annuelle du
rendement **signé** de l'heure pré-pause (l'impact prix est monotone dans le flux signé,
donc un close découpé plus finement doit comprimer cette dispersion), plus le CV du volume
tick pré-pause.

| Sleeve | dispersion signée pré-2021 | post-2021 | Δ | CV(volume tick) |
|---|--:|--:|--:|---|
| GOLD | 11.5 bps | 12.5 bps | **+8 %** | 2.44 → 0.77 |
| SILVER | 17.7 bps | 29.3 bps | **+65 %** | 0.99 → 1.30 |
| WTI | 34.1 bps | 33.0 bps | −3 % | 5.71 → 11.62 |

Le papier mesure une compression de **6.5 % → 2.9 %** sur les indices. **Rien de tel ici :
la dispersion du flux de clôture ne se comprime sur aucun des trois.** (La chute du CV du
volume tick sur l'or est une rupture de flux broker en 2021, pas une propriété de marché :
elle est absente des deux autres et va dans le sens inverse sur le WTI.)

⇒ **Conclusion honnête et à double tranchant.** Le mécanisme chiffré du papier n'est pas
détectable sur or/argent/WTI, donc on ne peut PAS conclure « le mécanisme se ferme aussi
chez nous ». Mais on ne peut pas non plus s'en servir pour défendre le candidat : la
décroissance de 28 % de l'or est **réelle et mesurée**, elle n'est simplement pas expliquée
par ce mécanisme-là. Et un proxy nul est un test faible — il ne discrimine rien.

---

## 4. Le test décisif — p(pass) contre les barrières FTMO réelles

Moteur : sampler stationnaire Politis-Romano de
`PropFirms/ftmo/program_2026-06/ftmo_alpha_program/engine/ftmo_first_passage.py`,
**réutilisé** ; l'unique ajout est de faire voyager l'excursion intra-séance dans le même
index de bootstrap, ce que `simulate_empirical_phase` ne sait pas exprimer.

Barrières (`PropFirms/ftmo/rules.md:20-56`, modèle **statique** confirmé par l'utilisateur
2026-07-20) : P1 +10 %, P2 +5 %, plancher total **−10 % statique** depuis le solde initial,
plafond journalier **−5 % en équity** (donc testé sur l'**excursion**, pas la clôture),
**aucune limite de durée**. Absorption dans l'ordre réel : l'excursion d'abord, la clôture
ensuite. 20 000 chemins par phase, horizon = longueur de l'échantillon.

### 4.1 Post-2021, coût MESURÉ 1.84 bps — le tableau décisionnel

Sizing = multiplicateur vol-target causal hérité (cap 3), `vm` = notionnel/équity.

| `vm` | SR net | vol/an | pire excursion | p1 | p2 | **p(pass)** | **médiane** | **p90** | mort DLL | mort plancher |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 1.0 | 0.853 | 5.4 % | −1.9 % | 0.922 | 0.957 | **0.882** | **525 s.** | 1359 s. | 0.000 | 0.039 |
| 1.5 | 0.853 | 8.1 % | −2.9 % | 0.886 | 0.908 | **0.804** | 294 s. | 849 s. | 0.000 | 0.110 |
| 2.0 | 0.853 | 10.8 % | −3.9 % | 0.824 | 0.859 | **0.708** | 185 s. | 549 s. | 0.000 | 0.175 |
| 2.5 | 0.853 | 13.5 % | −4.8 % | 0.768 | 0.814 | **0.625** | 127 s. | 375 s. | 0.000 | 0.232 |
| **3.0** | 0.853 | 16.2 % | −5.8 % | 0.709 | 0.775 | **0.549** | **93 s.** | 272 s. | 0.028 | 0.264 |
| 4.0 | 0.853 | 21.6 % | −7.7 % | 0.587 | 0.703 | 0.412 | 55 s. | 158 s. | 0.109 | 0.305 |
| 5.0 | 0.853 | 27.0 % | −9.7 % | 0.468 | 0.614 | 0.287 | 36 s. | 100 s. | 0.291 | 0.241 |
| 7.0 | 0.853 | 37.8 % | −13.5 % | 0.388 | 0.561 | 0.218 | 20 s. | 53 s. | 0.497 | 0.115 |
| 10.0 | 0.853 | 54.0 % | −19.3 % | 0.316 | 0.477 | 0.151 | 11 s. | 27 s. | 0.638 | 0.046 |
| 14.0 | 0.853 | 75.6 % | −27.0 % | 0.248 | 0.421 | 0.105 | 6 s. | 15 s. | 0.738 | 0.013 |

*(s. = séances. `mort DLL` / `mort plancher` = décomposition des morts de la phase 1.)*

**Décomposition des morts — la réponse directe à la question posée.** À basse taille, on
meurt **exclusivement du plancher statique −10 %** (mort DLL = 0.000 jusqu'à vm 2.5) : le
sleeve s'érode, il n'explose pas. La barrière journalière **ne devient liante qu'à partir
de vm ≈ 4** et domine complètement au-delà de vm 7 (0.50 → 0.74). C'est exactement le
diagnostic de juin — « barrière −5 % percée à VT 3× » — **mais il portait sur le NIVEAU de
levier, pas sur le vol-targeting**, dont c'est le contraire du rôle.

**Le vol-targeting AIDE, il ne nuit pas.** À taille égale il domine le sizing fixe partout
(SR net post-2021 **0.853 vs 0.570** ; à p(pass) 0.50 il économise ~30 % de durée). Baisser
le cap de 3 → 2 → 1.5 ne change **rien** (p(pass) 0.549 / 0.549 / 0.544 à vm 3) : le cap ne
mord presque jamais. Le levier de sizing est `vm`, pas le cap.

### 4.2 Le mur de 91 jours — ce qu'il coûtait

`results/step4_horizon_gradient.csv`, **meilleur `vm` à chaque horizon** (à horizon court on
doit forcer la taille, donc la comparaison à `vm` fixe surestimerait le coût du mur) :

| horizon par phase | post-2021 @**1.84** | post-2021 @**3.50** | full @1.84 |
|---|--:|--:|--:|
| **65 séances (~91 j — le mur de juin)** | **0.286** (vm 4) | 0.188 (vm 4) | 0.301 |
| 130 séances (~182 j) | 0.423 (vm 3) | 0.269 (vm 3) | 0.443 |
| 260 séances (~1 an) | 0.545 (vm 2) | 0.334 (vm 3) | 0.592 |
| **illimité** (le règlement réel) | **0.708** (vm 2) | 0.397 (vm 2) | 0.656 |

**Lever le mur vaut +42 points de p(pass)** (0.286 → 0.708). **Corriger le coût en vaut +10
points au mur et +31 à horizon illimité.** Les deux corrections annoncées dans le mandat
sont donc réelles et de première grandeur — et c'est bien la **géométrie**, pas le coût,
qui portait l'essentiel du kill.

Réserve qui compte : « illimité » n'est gratuit qu'en règlement. À `vm` 2 la **médiane est
de 185 séances (~9 mois) et le p90 de 549 séances (~2 ans et 2 mois)** pour un compte. Le
p(pass) élevé s'achète en immobilisation de capital et en temps de vie.

---

## 5. Le risque de paramètre — l'intervalle qui décide

L'IC binomial des tableaux ci-dessus (±0.007) est du bruit Monte-Carlo sur une série
**fixée**. Ce n'est pas l'incertitude qui compte : post-2021 le drift net n'est qu'à
t_HAC 1.90. J'ai donc emboîté la simulation dans un bootstrap par blocs **de l'histoire**
(200 histoires alternatives de 5 ans × 2 000 chemins chacune) — `results/step4_parameter_risk.csv`.

| échantillon | coût | `vm` | SR p05 | SR méd. | SR p95 | **% d'histoires à SR ≤ 0** | p(pass) p05 | **p(pass) méd.** | p(pass) p95 | **% < 0.25** |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **post-2021** | **1.84** | **2.0** | 0.128 | 0.784 | 1.587 | **1.5 %** | **0.321** | **0.593** | 0.817 | **1.0 %** |
| post-2021 | 1.84 | 3.0 | 0.128 | 0.784 | 1.587 | 1.5 % | 0.236 | 0.439 | 0.651 | 7.0 % |
| post-2021 | 1.84 | 4.0 | 0.128 | 0.784 | 1.587 | 1.5 % | 0.158 | 0.305 | 0.462 | 28.5 % |
| **post-2021** | **3.50** | **2.0** | **−0.532** | 0.136 | 0.917 | **39.5 %** | **0.125** | **0.329** | 0.619 | **32.5 %** |
| post-2021 | 3.50 | 3.0 | −0.532 | 0.136 | 0.917 | 39.5 % | 0.123 | 0.263 | 0.475 | 48.0 % |
| full | 1.84 | 2.0 | 0.766 | 1.144 | 1.556 | **0.0 %** | 0.512 | 0.669 | 0.789 | 0.0 % |
| full | 3.50 | 2.0 | 0.069 | 0.477 | 0.911 | 2.5 % | 0.294 | 0.440 | 0.583 | 1.5 % |

*(La médiane bootstrap est systématiquement sous le point estimate de §4.1 — 0.593 contre
0.708 — parce que p(pass) est concave dans la dérive : la dispersion supplémentaire des
histoires rééchantillonnées coûte du p(pass) par inégalité de Jensen. C'est la valeur
honnête.)*

**C'est ce tableau qui contient le verdict, et il tient en une ligne : tout dépend du coût,
et le coût n'est pas mesuré au bon endroit.**

- **Au coût mesuré (1.84 bps)**, le sleeve post-2021 est **robuste** : seulement 1.5 % des
  histoires alternatives ont un Sharpe négatif, et le 5ᵉ percentile de p(pass) à `vm` 2 est
  **0.321** — au-dessus du taux single-challenge du book FTMO déployé (~0.23-0.25, source
  `p2_flash_tail_2026-07`). Le pire décile du candidat bat le book déployé.
- **Au coût catalogue (3.50 bps)**, il est **cassé** : **39.5 % des histoires n'ont aucun
  edge** (SR ≤ 0), et une histoire sur trois donne p(pass) < 0.25.

**Pourquoi le DSR et le p(pass) ne disent pas la même chose** — et ce n'est pas une
contradiction. Le DSR demande « ce Sharpe se distingue-t-il du meilleur de 95 essais ? » ;
p(pass) demande « ce processus touche-t-il +10 % avant −10 % ? ». À `vm` 2 le plancher est
à **14.4 unités de vol quotidienne** (0.695 %/séance) : un Sharpe médiocre mais positif
suffit largement à
franchir une barrière aussi lointaine, et c'est la durée — pas la probabilité — qui en paie
le prix. Le repo a déjà tranché la question de la métrique (« pour un challenge, trancher
sur Δp(pass) et Δdurée, PAS sur ΔSR ») ; je ne cite donc aucun Sharpe comme critère. Mais
un DSR de 0.284 reste ce qui interdit d'appeler ce résultat un **PASS** : il dit que
l'estimation de dérive qui alimente toute la simulation est fragile.

### 5.1 Un avantage inattendu du véhicule CFD sur le véhicule futures

`month_end_vehicle` et `overnight_futures` ont tous deux buté sur la **granularité de lot**
(1 MGC ou rien ⇒ vol-targeting impossible ⇒ −0.35 de Sharpe, skew +0.99 → −0.49, queue à
−18.4 % en une séance). Sur le CFD, le pas est de **0.01 lot = 1 oz ≈ $4 071 de notionnel**,
soit **Δ`vm` ≈ 0.41 sur un compte de $10 000** : à `vm` 2 on cote 0.05 lot, l'erreur
d'arrondi est de ~2 %. **Le vol-targeting reste pleinement implémentable** — et il vaut
ici 0.28 de Sharpe (0.853 vs 0.570). C'est le seul point sur lequel le CFD domine
franchement le futures pour cette famille ; il ne compense pas l'écart de coût
(1.84 vs 0.66 bps), mais il doit figurer dans la matrice de véhicule.

---

## 6. Verdict

| | |
|---|---|
| **Véhicule (L53)** | **PASS** — FTMO cote la réouverture (99.78 % des séances tradées), reset DLL aligné 93.2 % |
| **Qualité de donnée (L60)** | **PASS** — 0.23 % de barres à fourchette nulle |
| **Gap de halt (L56)** | **PASS** — exclu par construction (entrée = 1er print après réouverture) |
| **Régime post-2021 (L31)** | **gross SURVIT** (t 2.74) — pas de mort de mécanisme |
| **Net post-2021, coût mesuré** | **FRAGILE** — SR 0.570-0.853, t_HAC 1.41-1.90, **DSR 0.284** |
| **p(pass) post-2021 @1.84 bps, `vm` 2** | **0.593, IC90 [0.321 ; 0.817]**, médiane **185 séances** |
| **p(pass) post-2021 @3.50 bps, `vm` 2** | 0.329, IC90 [0.125 ; 0.619], **39.5 % d'histoires sans edge** |
| **Géométrie (mur, panier, taille)** | **le kill de juin était mal motivé** — +42 pts d'horizon, +10 à +31 pts de coût |
| **VERDICT** | **UNDERPOWERED — décidable, et gaté sur UNE mesure** |

**UNDERPOWERED, donc le budget d'essais n'est pas consommé** et la famille reste ouverte.

Ce n'est pas un **PASS** : le DSR post-2021 de 0.284 dit que l'estimation de dérive qui
alimente toute la simulation est fragile, et l'IC90 de p(pass) — [0.321 ; 0.817] — est trop
large pour engager du capital. La durée médiane de **~9 mois par challenge** (p90 > 2 ans)
est une objection pratique de plein droit, indépendante de la statistique.

Ce n'est pas un **REJECTED** : le gross post-2021 reste significatif (t_HAC 2.74), le
véhicule passe nettement, le mécanisme de mort du papier NY Fed ne se réplique pas ici, et
les trois défauts géométriques invoqués en juin sont confirmés comme des défauts — pas
comme des propriétés du signal.

**Ce qui rendrait ce dossier décidable, par ordre de coût croissant :**

1. **Mesurer le spread réel de XAUUSD à 22:00/23:00 UTC sur le compte FTMO** (§7 de
   COST_AUDIT : la médiane journalière n'est pas le bon dénominateur pour une famille qui
   trade à une heure précise — et la réouverture après une pause d'une heure est *le pire
   moment de la journée pour le spread*). Tout le verdict tient entre 1.84 et 3.50 bps :
   p(pass) illimité 0.708 contre 0.397. **C'est la mesure la plus rentable du dossier, et
   elle ne consomme aucun essai.**
2. **Re-poser la question sur le véhicule futures** (MGC, 0.66 bps) : le DSR post-2021 y
   remonte à 0.714 contre 0.284 en CFD. Mais L53 s'applique — et `month_end_vehicle` a déjà
   montré qu'un compte perso domine un propfirm dès que la marge du lot minimum y tient.
3. **Attendre.** Le seul vrai remède à un UNDERPOWERED est de l'échantillon.

---

## 7. Ce que ce test ne prouve PAS

- **Il ne prouve pas que l'edge est mort.** Le gross post-2021 est à t_HAC 2.74 sur 1 311
  séances. Il prouve que l'edge **net du coût CFD** n'est pas mesurable sur ce sous-échantillon.
- **Il ne prouve pas que le coût est 1.84 bps.** Ce chiffre est un spread médian **toutes
  heures confondues** + un dérapage provisionné, jamais mesuré à l'heure de réouverture ni
  sur ce symbole en live. La fourchette [1.84 ; 3.50] n'est pas résolue, et c'est elle qui
  décide.
- **Il ne prouve pas que le mécanisme du papier NY Fed est absent.** Mon proxy (dispersion
  du rendement signé pré-pause) est un proxy pauvre du flux signé de clôture ; ne rien voir
  n'est pas voir que rien n'est là. Le vrai test demanderait du volume signé (payant).
- **Il ne dit rien de l'admission au book.** Le critère du repo pour une sleeve de challenge
  est **Δp(pass) et Δdurée contre le book déployé**, pas p(pass) autonome. Ce test est
  **standalone par construction** (le mandat l'exigeait). La corrélation de ce sleeve au
  book FTMO déployé n'a pas été mesurée ; `Portfolio/admission/` existe et n'a pas été
  lancé. Sans ça, on ne peut pas dire si le sleeve est accrétif — et un sleeve dont
  p(pass) autonome est inférieur au book peut parfaitement l'être.
- **Il ne modélise pas les 6.8 % de jours où les DST US et UE divergent**, où la fenêtre est
  coupée en deux jours FTMO. Le sens de l'erreur est conservateur (chaque moitié est moins
  exposée), mais ce n'est pas exact.
- **Il ne modélise pas le tick.** L'excursion est mesurée sur des **clôtures M1** (médiane
  475 par fenêtre). L'étude `p2_flash_tail` a montré qu'un overlay intra-M5 exact retire
  encore ~3.9 points de p(pass) single-challenge. Les p(pass) ci-dessus sont donc encore
  **légèrement optimistes** dans la queue.
- **Il ne conteste pas les autres kills du bloc.** Argent et WTI restent morts ; le panier
  reste indéfendable (or↔argent 0.69-0.76, panier équi-risque SR 1.096 < 1.279 pour l'or seul).

---

## 8. Honnêteté de méthode

- **Aucun signal n'a été recalculé, aucune fenêtre re-choisie, aucun paramètre ré-optimisé.**
  Spec, tolérances de lookup et multiplicateur vol-target sont copiés de
  `overnight_futures_2026-07`. Le reproduction gate vaut **1.0e-16**.
- **Signal à T-1, trade à T.** Le multiplicateur vol-target décale `rv` **avant** la médiane
  expanding : tout ce qui entre dans la taille du jour t est connu à la clôture de t−1.
  Entrée et sortie sont à heure fixe, au marché — **il n'y a ni stop-entry ni bracket-exit**,
  donc le piège L59 (sortie remplie au prix exact du stop) ne s'applique pas ici ; le coût
  aller-retour est facturé sur le notionnel tenu, dans les deux jambes.
- **Bootstrap par blocs stationnaire (Politis-Romano) partout**, longueur moyenne √T, y
  compris pour le risque de paramètre. Aucun bootstrap iid.
- **Le balayage de taille ne consomme pas le budget d'essais** (instruction du mandat : le
  sizing n'est pas une modification de stratégie). Le **split de régime** en consomme **1**.
  Budget de modifications de la spec : **0 consommé** — la spec n'a pas bougé.
- **Réserve de sélection assumée** : les p(pass) « meilleur vm à chaque horizon » sont des
  maxima sur une grille. Ils sont rapportés comme des frontières, pas comme des estimations
  ponctuelles d'une politique pré-enregistrée.
- **Deux erreurs trouvées dans le matériau hérité et signalées** : la winsorisation de
  `tradable_series` (non mentionnée dans `RESULTS.md §5.3`, qui annonce des séries « non
  winsorisées »), et l'absence de modélisation du chemin intra-fenêtre alors que le plafond
  journalier FTMO est enforce en équity.
- **Tension documentée non tranchée** : `PropFirms/ftmo/rules.md:53` cite verbatim une perte
  maximale **high-water-markée** (« can only increase »), alors que le modèle canonique du
  repo — confirmé par l'utilisateur le 2026-07-20 — est **statique**. J'ai utilisé le
  statique. Si le HWM était le bon modèle, tous les p(pass) ci-dessus seraient **surestimés**
  (un plancher qui remonte avec le profit est plus dur à franchir en montant vers +10 %).

## 9. Ce qui a été produit

```
RESULTS.md                        ce document
code/common_reopen.py             chargement, DST US/UE, vol-target causal, constantes FTMO
code/step1_vehicle.py             V1 flux FTMO / V2 alignement DLL / V3 L60
code/step2_series.py              série brute + excursion intra-fenêtre (M1) + gate de repro
code/step2b_regime.py             split 2021 (or/argent/WTI) + proxy de dispersion de flux
code/step3_barrier.py             balayage p(pass) x taille x coût x échantillon
code/step4_horizon_uncertainty.py gradient d'horizon + risque de paramètre
results/*.csv                     6 tables
```
