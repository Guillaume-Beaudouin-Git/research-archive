# Admission marginale — combien de diversifieurs le mauvais gate a-t-il fait perdre ?

**2026-08-02.** Chantier A4 : faire du **portefeuille** l'unité de recherche. Aucun signal n'est
recherché ici. On applique un **critère de décision différent** à des mesures qui existent déjà.

> **Comptabilité des essais : N0, non déflateur.** 79 séries évaluées, zéro backtest, zéro
> hypothèse nouvelle. Deux re-dérivations mécaniques (désinsorisation de la famille overnight ;
> conversion de trois ledgers trade/événement en série quotidienne) sont des transformations
> d'une mesure existante, pas des essais. Le DSR de tout candidat futur est intact.
> Reproduire : `rebuild_overnight_raw.py` → `build_extra.py` → `harvest.py` →
> `run_admission.py 1` → `null_control.py` → `run_admission.py 2` → `summarise.py`
> (`/usr/bin/python3` explicitement).

---

## 0. Le résultat en un paragraphe

Sur 118 edges catalogués, **29 seulement sont atteignables** par un test marginal — les 89 autres
n'ont **aucune série de rendements sauvegardée** et sont donc hors de portée de toute décision de
portefeuille, quelle que soit leur force statistique. Sur les **79 séries** effectivement testées,
le critère de Sharpe marginal ne tranche **rien** : son effet minimum détectable médian est de
**0.360** de Sharpe alors que **54/79** des ΔSR observés sont plus petits que ça en valeur absolue,
et **un seul** candidat franchit Šidák. Le critère de barrière tranche, lui — mais un **contrôle
nul** montre qu'il est **achetable sans edge** : une série à moyenne exactement nulle et à
persistance de 10 jours achète **Δp(pass) = +14.95 points**. Contre son propre placebo décalé
(qui préserve moyenne, distribution et autocorrélation, et ne détruit que l'alignement calendaire),
**un seul candidat propre survit : B1 month-end Treasury** — celui que le repo avait déjà trouvé
et déployé par une autre voie. **Réponse à la question posée : le mauvais gate n'a pas fait perdre
un gisement de diversifieurs. Il en a fait perdre au plus un, et il a été récupéré autrement.**

Le résultat secondaire est plus utile que le premier : **la variable explicative attendue n'explique
rien**. Le taux de recouvrement de calendrier corrèle à **−0.06** avec Δp(pass), quand le Sharpe
solo du candidat corrèle à **+0.82** et son autocorrélation à **+0.51**. Sur ce livre-là, à ce
levier-là, « remplir les jours plats » n'est pas le canal actif.

---

## 1. Le livre de référence

Le livre **RÉELLEMENT DÉPLOYÉ**, pas un livre théorique : `w_xau = 0`, J1 coupé, ORB challenge-off,
donc seule la sleeve overnight trade. Construit par `build_book.py` de la session L54 sur le moteur
cleanroom audité, au levier live `vm = 14`, à risque constant (aucune barrière appliquée en amont).

| | |
|---|--:|
| Période | 2013-10-01 → 2026-06-05 (n = 3 295) |
| Jours **plats** | **40.6 %** |
| Sharpe (au levier déployé) | 1.152 |
| Vol annualisée | 77.5 % |
| **p(pass) 2-step, seul** | **0.1733** |
| Durée médiane jusqu'au funded | **19 jours** |
| **Part des échecs sur le stop journalier −5 %** | **80.2 %** |

Barrières (non négociables, confirmées 2026-08-01) : daily **−5 %** du solde d'ouverture, plancher
**STATIQUE −10 %** du capital initial, **aucune limite de temps**. Bootstrap **stationnaire
Politis-Romano** (bloc moyen 10 j), jamais iid. Chemins **appariés** : même graine pour les deux
branches, donc le Δ est attribuable à la sleeve et non au bruit MC.

> **Le chiffre qui organise tout le reste : 80.2 % des échecs sont des breachs du stop
> JOURNALIER.** Ce livre ne meurt pas de ne pas atteindre la cible ; il meurt d'une seule mauvaise
> journée. Toute la sensibilité de p(pass) porte donc sur la **forme de la queue gauche à un jour**,
> pas sur le rendement espéré. C'est ce qui rend la métrique puissante — et manipulable (§4).

---

## 2. Ce qu'on récupère, ce qu'on perd

`crosswalk_inventory.csv` — mapping manuel et conservateur des 118 entrées de
`edge_inventory_2026-07`.

| Statut | N | % |
|---|--:|--:|
| **RECOVERED** — série quotidienne de la construction exacte | **20** | 16.9 % |
| **PROXY** — même edge, implémentation fidèle mais non identique | **9** | 7.6 % |
| **NON_DAILY** — série mensuelle/événementielle, inutilisable pour une barrière quotidienne | 5 | 4.2 % |
| **NO_SERIES** — mesuré, mais seuls des résumés ont été persistés | **84** | **71.2 %** |

**29 edges sur 118 (24.6 %) sont atteignables. 89 ne le sont pas.** Et la perte est **la plus
coûteuse exactement là où elle fait le plus mal** — dans la tranche `t ≥ 3` identifiée par
l'inventaire comme le gisement d'erreurs de type II :

| `t ≥ 3` | atteignable | perdu faute de série |
|---|---|---|
| E001 month-end · E002/E003/E004/E005 overnight · E012 gap A · M001 CS macro · M047 TSMOM | **7** | |
| **E006/E007/E008 précieux-Q1 · E014 VRP QQQ · E016 reversal 1j SPX · M043 filtres TSMOM · R015 fix WMR** | | **7** |

Le cas **E014 (S1 VRP, `t_HAC(IC) 3.59`)** est le plus net : son POSTMORTEM contient déjà le
Sharpe net-futures **0.454**, et l'inventaire le désigne comme recalé par un gate depuis abandonné.
Il ne reste ni série de rendements, ni scan IC exploitable — **seulement des PNG et un scalaire**.
Il est donc impossible de lui appliquer le bon test sans le régénérer. Idem pour les trois cellules
de saisonnalité précieux-Q1, qui n'ont jamais été écrites sous forme de flux quotidien.

**Recommandation de processus, à coût nul :** toute étude qui produit un Sharpe doit persister la
**série quotidienne** qui l'a produit. Sans elle, l'edge est définitivement hors d'atteinte de
toute décision de portefeuille — et 71 % du catalogue est dans ce cas.

Trois ledgers ont pu être **convertis** en séries quotidiennes (`build_extra.py`) et rendent trois
dossiers de shortlist testables pour la première fois : **E012/E013 Gap Pattern** (ledger de trades,
P&L imputé à la date de **sortie**) et **E020 cycle d'adjudication Treasury** (251 événements).
Réserve honnête sur la convention : imputer à la sortie rend le flux plus grumeleux que le vrai
chemin d'equity — conservateur sur la fréquence, anti-conservateur sur la queue.

---

## 3. Le critère ΔSR ne tranche rien — c'est mesurable

`decision_table.csv`, colonne `mde_dsr` : effet minimum détectable de ΔSR à 95 %, une queue,
par block-bootstrap.

| | |
|---|--:|
| MDE(ΔSR) médian | **0.360** |
| Candidats dont **\|ΔSR\| < MDE** | **54 / 79** |
| ΔSR > 0 | 25 / 79 |
| Verdict `admit()` : PASS / MARGINAL / FAIL | **1** / 24 / 54 |
| α effectif (Šidák, 79 essais) | **0.00065** |

Le seul PASS est `voie_b_ftmo` (ΔSR +1.323, IC95 [+0.925, +1.739]) — dont `CLAUDE.md` dit que le
**sous-jacent est « À CONFIRMER MANUELLEMENT »** et dont le Sharpe solo (2.43 en daily) viole L21.
Ce n'est pas un résultat, c'est un drapeau rouge de provenance.

**Lecture.** Sur un livre de SR 1.15 avec 3 295 observations, le block-bootstrap ne peut certifier
qu'un ΔSR ≥ 0.36 — c'est-à-dire un candidat qui ferait passer le livre de 1.15 à 1.51. Aucun
diversifieur réaliste ne fait ça. **Le gate ΔSR n'est pas sévère : il est aveugle.** Remplacer
`1.10 × SR_book` par `ΔSR > 0 significatif` corrige la *direction* de l'erreur (on n'exige plus
d'un diversifieur qu'il amplifie le rendement) mais **ne restaure pas la puissance**. C'est
précisément pourquoi `CLAUDE.md` demande de trancher un challenge sur Δp(pass) et Δdurée.

**Désaccord entre les deux critères, chiffré :** **26/79** candidats ont **ΔSR ≤ 0** et pourtant un
**Δp(pass) au-dessus de la bande nulle iid**. L'inverse ne se produit que **2** fois. Le critère de
Sharpe et le critère de barrière ne classent pas la même chose — sur un tiers du panel.

---

## 4. Le contrôle nul — et pourquoi il change la conclusion

Question préalable, sans laquelle le classement n'est pas interprétable : **quel Δp(pass) produit
une sleeve SANS edge ?** Le livre combiné est re-levé à la volatilité de l'incumbent
(`normalize_vol=True`), donc ajouter n'importe quelle série faiblement corrélée modifie la **forme**
de la distribution quotidienne même à rendement nul — et le stop journalier est une barrière sur la
queue gauche d'un seul jour.

`null_control.py`, 20 réplications, moyenne **exactement** nulle imposée :

| Null | Δp(pass) moyen | p95 | Δdurée |
|---|--:|--:|--:|
| `gauss_zero` — bruit iid | −0.0084 | +0.0190 | −7.4 j |
| `flat_filler` — bruit **uniquement les jours où le livre est plat** | −0.0114 | +0.0122 | −7.2 j |
| **`gauss_block` — bruit à persistance 10 jours** | **+0.1495** | +0.1757 | −8.8 j |

**Une série à edge strictement nul achète +14.95 points de p(pass) si elle est autocorrélée.** Le
mécanisme est réel, pas numérique : face à une cible cumulée **+10 %** et un stop **journalier**
−5 %, la persistance convertit de la variance en probabilité d'atteindre la cible avant une mauvaise
journée. Confirmation sur le panel : **corr(autocorrélation moyenne lags 1-10, Δp) = +0.511**.

⚠ **Conséquence directe : « Δp(pass) > 0 » n'est pas une preuve d'admission.** Et le
`flat_filler` — l'archétype exact du brief, une sleeve qui ne trade *que* quand le livre est plat —
rend **−0.011** à edge nul. Le canal « remplissage de calendrier » n'apporte rien **par lui-même**
sur ce livre.

Le bon contrôle est donc **par candidat** : sa propre série **décalée circulairement**, ce qui
préserve sa moyenne, sa distribution marginale **et son autocorrélation**, et ne détruit que son
alignement avec le livre. L'excès sur ce placebo isole le canal calendaire.

---

## 5. Classement — Δp(pass) puis Δdurée

79 candidats. Tableau complet : `decision_table.csv`. Bande nulle iid = **+0.0190**.

| # | Candidat | SR solo | ρ | recouvr. | ac10 | ΔSR | **Δp(pass)** | ±sd | placebo moy / max | Δdurée | **Verdict** |
|--:|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| 1 | `s060_oxford` | 2.75 | +0.089 | 0.406 | **0.517** | +1.493 | **+0.2590** | 0.019 | 0.227 / 0.231 | −10 j | PASS ⚠ |
| 2 | `voie_b_ftmo` | 2.43 | +0.045 | 0.420 | 0.019 | +1.323 | **+0.0915** | 0.005 | 0.078 / 0.090 | −4 j | PASS ⚠ |
| 3 | `gapA_S035_best` (E012) | 1.16 | +0.031 | 0.406 | 0.031 | +0.456 | +0.0877 | 0.002 | 0.077 / **0.101** | −2 j | UNDERPOWERED |
| 4 | `ovn_GOLD_winsorised` | 1.26 | −0.016 | 0.255 | 0.017 | +0.571 | +0.0837 | 0.008 | 0.074 / **0.084** | −5 j | UNDERPOWERED |
| 5 | `top10_ang_047_mod3` | 0.86 | +0.025 | 0.468 | 0.119 | +0.181 | +0.0653 | 0.003 | 0.062 / **0.080** | +2 j | UNDERPOWERED |
| 6 | `btc_proxy_A` (R001) | 1.37 | +0.031 | 0.388 | 0.028 | +0.576 | +0.0648 | 0.006 | 0.070 / **0.078** | −5 j | UNDERPOWERED |
| 7 | **`ovn_GOLD_fut` (E002)** | 1.34 | −0.017 | 0.255 | 0.011 | +0.628 | +0.0558 | 0.009 | 0.060 / **0.071** | −6 j | UNDERPOWERED |
| 8 | `top10_lit_013` | 0.65 | +0.124 | **0.025** | 0.000 | −0.026 | +0.0552 | 0.003 | 0.060 / **0.064** | +5 j | UNDERPOWERED |
| 9 | `crypto_trend_cfd` (R003) | 0.59 | −0.036 | 0.407 | 0.025 | +0.102 | +0.0497 | 0.003 | 0.042 / **0.051** | −4 j | UNDERPOWERED |
| 10 | **`B1_month_end_bonds` (E001)** | **0.87** | **−0.006** | **0.472** | 0.009 | +0.281 | **+0.0468** | 0.008 | **0.023 / 0.028** | **−3 j** | **PASS** |
| 11 | `dec_pisteC_best` (M007) | 0.33 | +0.100 | 0.419 | 0.020 | −0.152 | +0.0463 | 0.005 | 0.038 / 0.043 | +1 j | PASS ⚠ |
| 12 | `gold_trend_cfd` | 0.39 | +0.027 | 0.410 | 0.012 | −0.077 | +0.0390 | 0.007 | 0.031 / **0.054** | +2 j | UNDERPOWERED |

Queue du classement (rejetés) : `paper_rev_book` −0.1192, `top10_ang_018` −0.0692,
`dec_H2_resid_port` −0.0642, `Long_vol_VXX` −0.0608, `paper_im_book` −0.0525, `top10_ang_025`
−0.0425. La métrique **discrimine** : elle produit des Δ franchement négatifs, elle ne récompense
pas tout ce qu'on lui donne.

**Répartition : 4 PASS · 45 UNDERPOWERED · 30 REJECTED.**

### 5.1 Les quatre PASS, un par un

**`B1_month_end_bonds` (E001) — le seul PASS propre.**
Δp(pass) **+0.0468 ± 0.0084** contre un placebo à **+0.0227** (max **+0.0275**) : l'excès sur le
placebo est **+0.0241**, soit **t ≈ 5.0** sur les graines appariées, et le réel vaut **1.7× le
maximum** du placebo. C'est le **seul** candidat du panel dont l'apport n'est pas reproduit par sa
propre série décalée. Profil cohérent : ρ = **−0.006**, autocorrélation **0.009** (aucun artefact
de persistance), **recouvrement de calendrier 0.472** — le plus élevé de tous les survivants,
au-dessus du taux de base 0.406. Orthogonalité L38 : R² = 0.06 % / 0.32 % / 2.1 % contre
buy-and-hold vol-targeté US500 / XAUUSD / USDJPY — **très en-dessous du seuil de 30 %**.
Durée médiane du livre 19 j → **16 j**.
*Et c'est l'edge que le repo avait déjà identifié et déployé sur IBKR.* Le mauvais gate ne l'a pas
perdu — il l'a retardé de deux rejets sur le véhicule.

**`s060_oxford` — PASS nominal, STOP sur la provenance.**
Le plus gros Δp du panel (+0.2590), mais : Sharpe solo **2.75 en daily** (viole L21 : >2× la
fourchette de la catégorie ⇒ audit DSR/cherry-pick obligatoire), autocorrélation **0.517** —
exactement le profil que le nul `gauss_block` montre achetable **sans edge** —, et la série vient
de l'audit oxfordstrat 109, dont **L59 établit que toute la famille stop-entry est validée de façon
incomplète** (sorties remplies au stop exact alors que 25 % des barres de stop ouvrent au-delà :
SR 0.99 → 0.49). **Non citable avant re-dérivation des sorties.**

**`voie_b_ftmo` — PASS nominal, STOP sur la provenance.**
Seul PASS du gate Sharpe, seul ΔSR à franchir Šidák. Mais `CLAUDE.md` porte explicitement
« sous-jacent [À CONFIRMER MANUELLEMENT] », et SR solo 2.43 daily viole L21. L'excès sur placebo
(+0.0135) est réel statistiquement (t ≈ 4.9) mais **on ne sait pas ce que cette série mesure**.
**Identifier le sous-jacent avant toute autre chose.**

**`dec_pisteC_best` (M007) — PASS sur la métrique, REJETÉ sur le mécanisme.**
Excès sur placebo +0.0084, t ≈ 2.9 — le plus mince des quatre. Surtout : M007 a été tué
**mécaniquement** (jambe short négative sur **48/48** cellules ; le tueur est la dérive, pas le
coût). La politique de ré-ouverture est sans ambiguïté : **un kill mécanique reste fermé**. Un
Δp(pass) favorable ne ressuscite pas un signal inexistant — il indique seulement que cette forme de
distribution quotidienne s'entend bien avec la barrière. **Ne pas rouvrir.**

### 5.2 Ce qui est arrivé aux dossiers phares de l'inventaire

- **E002 `ovn_GOLD_fut` (or overnight, `t_HAC(α) 4.82`, le dossier n°1 de la shortlist)** :
  Δp(pass) **+0.0558**, mais son propre placebo décalé fait **+0.0604 en moyenne et +0.0710 au
  maximum**. ⇒ **UNDERPOWERED**. Ce n'est **pas** un kill de l'edge : ρ = −0.017, ΔSR +0.628,
  −6 jours de durée. C'est un constat précis — **son apport à CE livre n'est pas calendaire**. Le
  décalage circulaire fait aussi bien. Il reste un excellent candidat pour un véhicule sans
  barrière (compte perso, L53), où la question posée n'est pas celle-ci.
- **E003 argent (+0.0283), E004 WTI (−0.0075), E005 soja (+0.0075, n = 427 seulement)** : sous ou
  près de la bande nulle iid. Le WTI et le soja sont **REJECTED** ; l'argent **UNDERPOWERED**.
  Le soja mérite une mention : SR solo 1.61 et ΔSR +0.586, mais **n = 427** — la fenêtre CFD
  n'existe que depuis 2017-12, et le MDE(ΔSR) monte à **0.945** sur cet échantillon. C'est le cas
  d'école du UNDERPOWERED-par-échantillon, pas du signal absent.
- **E012 Gap Pattern** : `gapA_S035_best` +0.0877 mais sous son placebo max (+0.1010) ; la version
  **pré-enregistrée** `gapA_S035_point` (celle qui compte, N = 3 438) tombe à **+0.0408** avec
  ΔSR **+0.002**. La différence entre les deux versions est du **choix de grille**, pas de l'edge.
- **E020 cycle d'adjudication Treasury** — mesuré ici pour la première fois comme sleeve :
  Δp **+0.0425** mais **ΔSR −0.392**, SR solo **−0.074**, et **Δdurée +2 jours** (il *ralentit* la
  campagne). Recouvrement 0.029 : il ne trade quasiment jamais quand le livre est plat. Cohérent
  avec L58 (le placebo pré-enregistré de ce dossier avait fabriqué un faux PASS). **UNDERPOWERED,
  et sans attrait.**
- **M001 CS macro momentum** (fermé mécaniquement 07-29) : Δp +0.0408, ΔSR −0.075. Le kill
  mécanique tient ; rien à rouvrir.

---

## 6. Le piège de winsorisation, quantifié

`overnight_futures_2026-07/code/step3_performance.py:47` clippe à 0.5/99.5 **dans le constructeur
de série**, donc tous ses consommateurs héritent de queues tronquées. `rebuild_overnight_raw.py`
reconstruit la même spec sans le clip (`winsorisation_audit.csv`) :

| Sleeve | min brut (bps) | min clippé | max brut | max clippé | kurtosis brute → clippée | obs censurées |
|---|--:|--:|--:|--:|--:|--:|
| GOLD | **−677.2** | −165.1 | +522.4 | +178.4 | 24.3 → 3.6 | 50 |
| SILVER | **−1 236.6** | −325.3 | +613.2 | +369.2 | 24.7 → 4.7 | 32 |
| WTI | **−1 633.4** | −373.7 | +1 067.4 | +326.3 | **61.5 → 5.8** | 34 |
| SOYBEAN | −155.8 | −144.7 | +206.0 | +155.5 | 3.9 → 2.6 | 4 |

Effet sur la décision, même edge, deux versions de la même série :

| | Sharpe solo | ΔSR | **Δp(pass)** | ratio de queue |
|---|--:|--:|--:|--:|
| `ovn_GOLD_winsorised` (tel que publié) | 1.265 | +0.571 | **+0.0837** | 4.59 |
| `ovn_GOLD_fut` (queues brutes) | 1.345 | +0.628 | **+0.0558** | **15.01** |

**La série clippée surestime Δp(pass) de +2.8 points, soit +50 % en relatif** — et le Sharpe, lui,
bouge à peine (1.26 vs 1.34, dans le mauvais sens en plus). C'est la démonstration exacte de la
mise en garde : *anodin pour un Sharpe, disqualifiant pour une barrière.* Le détecteur de clipping
(`clipping_signature`, valeurs extrêmes répétées) a **isolé cette seule série** sur les 79.

Un second garde-fou a servi : `double7_connors/eq_cfd_sleeves.csv` est une **courbe d'equity en
USD**, pas des rendements ; passée telle quelle elle produisait ΔSR **+43.3** et Δp **+0.809**.
Détectée par la garde « niveau strictement positif de moyenne ≫ 0 » (`_coerce_returns`).

---

## 7. Ce que ce travail NE prouve PAS

1. **Ne prouve pas que les edges testés sont morts.** UNDERPOWERED ≠ REJECTED. E002 (or overnight),
   E012 (gap pattern), E003 (argent) gardent leurs statistiques d'origine intactes. Le test dit
   uniquement : *leur apport marginal à CE livre, à CE levier, n'est pas séparable de ce que produit
   leur propre série décalée.*
2. **Ne prouve rien sur un autre véhicule.** Toute la mesure est conditionnée aux barrières FTMO
   2-step et au livre mono à vm = 14. Sur le compte IBKR — pas de barrière, pas d'horloge — la
   question n'est pas p(pass) mais croissance ; le classement y serait différent, et E002 y reste un
   candidat de premier plan (L53).
3. **La barrière est simulée en clôture quotidienne.** `barrier.py` lit des rendements journaliers ;
   le stop −5 % s'applique en réalité sur l'**équité intrabar**. L'étude P2 flash-tail chiffre
   l'écart à −3.9 pt en single-attempt. Tous les p(pass) absolus sont donc **optimistes** ; les Δ
   appariés le sont beaucoup moins, mais pas nuls.
4. **ERC est un choix, pas une vérité.** À ERC le candidat reçoit **la moitié du budget de risque**.
   Le hurdle marginal infinitésimal (`ρ × SR_book`) et le hurdle ERC
   (`SR_book × (√(2(1+ρ)) − 1)`) sont tous deux rapportés dans `decision_table.csv` ; à une
   allocation plus petite les Δ rétrécissent proportionnellement.
5. **Invariance d'échelle — à connaître.** À poids ERC avec re-normalisation de vol, multiplier une
   série candidate par une constante positive **ne change rien** au résultat. Δp(pass) ne mesure
   donc **pas** la taille du candidat : il mesure sa **forme** et sa **corrélation**. Corollaire
   inconfortable : il ne dit rien du levier auquel on pourrait réellement le déployer.
6. **Les coûts sont hérités, pas re-mesurés.** 76 des 79 séries sont nettes des coûts appliqués par
   leur étude d'origine. `COST_AUDIT.md` établit que l'or a été sur-facturé **1.9×** dans le funnel
   à 164 tests et que les indices y sont conservateurs de 20-33 % ; les lignes `top10_*` de ce
   classement en héritent, dans le sens **pessimiste**. Trois séries sont **gross** et signalées
   comme telles (`ovn_GOLD_winsorised`, `tsmom_chosen`, `tsmom_swapfree_full`) : leur Δ est une
   borne haute — et pour le premier, c'est le contraste de winsorisation du §6 qui compte, pas son
   niveau.
7. **L58 n'a pas été appliqué à chaque candidat.** Le contrôle « la baseline du placebo doit égaler
   l'espérance inconditionnelle » n'a été mené qu'au niveau global (le placebo décalé, qui préserve
   la moyenne par construction). Un candidat calendaire dont le pool serait biaisé passerait au
   travers.

---

## 8. Conclusion, et ce qu'il faut en faire

**Combien de diversifieurs le mauvais gate a-t-il fait perdre ? Au plus un, et il a été récupéré.**
C'est le résultat, et il faut le dire tel quel. L'hypothèse « le gate ratio a laissé le livre mono
en jetant des diversifieurs valables » n'est **pas** confirmée à l'échelle du repo : sur 79 séries,
un seul apport survit à son propre placebo, et c'est B1 month-end — déjà déployé.

Mais trois trouvailles de méthode valent plus que le comptage :

1. **Le gate ΔSR est aveugle, pas sévère.** MDE médian **0.360** contre 54/79 des ΔSR sous ce seuil.
   Le remplacer par « ΔSR > 0 significatif » corrige la direction de l'erreur sans restaurer la
   puissance. **Sur ce livre, ΔSR ne peut pas servir de gate.**
2. **Δp(pass) est achetable sans edge.** +14.95 points pour une série à moyenne nulle et persistance
   de 10 jours ; corr(autocorrélation, Δp) = **+0.511**. Tout Δp(pass) cité sans **placebo décalé
   apparié en autocorrélation** est ininterprétable. C'est une extension directe de L49/L58 à la
   métrique de barrière.
3. **Le recouvrement de calendrier n'est pas le canal actif** : corr = **−0.06** contre **+0.82**
   pour le Sharpe solo. Le nul `flat_filler` — la sleeve idéale du brief, active uniquement les
   jours plats — rend **−0.011** à edge nul. L'intuition « remplir les jours plats accélère le
   challenge » est fausse sur ce livre : ce qui accélère, c'est du rendement et de la persistance.

**Et le fait structurel qui domine tout :** 80.2 % des échecs de ce livre sont des breachs du stop
**journalier** à vm = 14. Le levier de p(pass) le moins cher n'est pas une sleeve supplémentaire —
c'est la géométrie (cohérent avec « ~60 % du p(pass) vient de la géométrie, pas de l'alpha »).

### Pré-enregistrement N2 requis avant toute confirmation

Aucun candidat n'est admis sur la base de ce travail. Un seul mérite un test confirmatoire, et il
doit être **pré-enregistré en N2** avec sa kill rule écrite AVANT de toucher la donnée :

> **N2-01 — B1 month-end Treasury comme sleeve du livre FTMO** (et non comme sleeve IBKR).
> *Hypothèse* : ajouté au livre mono à poids ERC, B1 relève p(pass) d'un montant qui excède son
> placebo décalé.
> *Kill rule* : ÉCHEC si, sur ≥ 8 graines appariées à n_paths ≥ 5 000 **et** avec la barrière
> journalière appliquée en **intrabar** (données M5, pas en clôture), l'excès de Δp(pass) sur la
> **moyenne** du placebo décalé tombe sous **+0.010**, ou si l'IC95 apparié contient le **maximum**
> du placebo. ÉCHEC également si le véhicule échoue au test L53 (si la marge du lot minimum ZN tient
> dans le capital perso, le propfirm n'apporte rien — et le compte perso reste dominant).
> *Essais* : 1. *Réserve* : ce test ne peut pas être « re-tenté » avec une autre géométrie sans
> déflater le DSR de tous les candidats suivants.

Deux dossiers sont **bloqués sur la provenance**, pas sur la statistique — à instruire avant tout
test : `voie_b_ftmo` (identifier le sous-jacent) et `s060_oxford` (re-dériver les sorties sous L59).

### Dette de données identifiée

**84 edges sur 118 sont hors d'atteinte faute de série sauvegardée**, dont 7 de la tranche `t ≥ 3`.
Régénérer **E014 (VRP QQQ)** et les trois cellules **précieux-Q1** — les seuls de la tranche haute
dont l'inventaire dit qu'ils ont été recalés par un gate depuis abandonné — coûterait un travail
borné et rendrait quatre dossiers testables. C'est la suite la plus rentable de ce chantier.

---

## Fichiers

| Fichier | Contenu |
|---|---|
| `decision_table.csv` | **79 candidats × 34 colonnes** — le tableau de décision |
| `stage1_all_candidates.csv` | screen complet (ΔSR + Δp single-seed) |
| `stage2_shortlist.csv` | 12 finalistes : graines multiples + placebo décalé |
| `null_control.csv` | 3 nulls × 20 réplications |
| `crosswalk_inventory.csv` | 118 entrées d'inventaire × statut d'atteignabilité |
| `winsorisation_audit.csv` | queues brutes vs clippées, 4 sleeves overnight |
| `harvest_manifest.csv` | provenance de chaque série (chemin, colonne, statut coût) |

Caches et pickles régénérables : `cache/`, gitignoré. Aucun blob data commité.
