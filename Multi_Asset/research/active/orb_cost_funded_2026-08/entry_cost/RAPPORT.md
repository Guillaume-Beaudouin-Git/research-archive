# VOLET A — H1 : combien coûte réellement l'ENTRÉE de l'ORB ?

**Pré-enregistrement** : `../PREREGISTRATION.md` (gelé 2026-08-12). Devise commune §2 respectée
(points / bps / R, toujours avec N, t HAC lag-6, IC block-bootstrap). Aucun paramètre de signal
touché : ce volet mesure un coût et re-price un ledger existant.

**Données** (lecture seule) : ledger `PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet`
(N=4013, 2010-06-07 → 2026-05-29) ; M1 canonique `data/raw/NQ_1min_databento_2010-2026.parquet`.

**Résumé en une ligne** — le canal *gap* de l'entrée est **empiriquement nul sur NQ** :
**11 barres de déclenchement sur 4013 (0.274 %)** ouvrent au-delà du niveau, et **toutes exactement
d'un tick**. L'idéalisation `entry == level` du ledger n'est donc **pas** un problème de gap à
l'entrée — contrairement à la sortie (L59). Le coût d'entrée résiduel est purement
microstructurel : **1 tick = 0.473 bps = 0.0109 R en moyenne**, ce qui consomme déjà **22 % du
gross** (+0.0492 R). Le budget total d'entrée avant mort du sleeve est de **4.53 ticks (1.13 point)**.

---

## 1. Vérification du fuseau et de la fenêtre OR

### 1.1 Recherche empirique (pas de supposition)

Grille balayée : début ∈ {08:00 … 11:00 par pas de 5 min} × durée ∈ {5,10,15,20,25,30,45,60} min,
**dans deux horloges** (`America/New_York` avec son DST natif, et UTC). Reconstruction de
`or_hi`/`or_lo` depuis le M1 et comparaison au ledger au **demi-tick** (0.125 pt).
Échantillon stratifié : 40 dates par année civile → **N = 680**.

| clock | fenêtre | durée | N | exacts | taux |
|---|---|---|---|---|---|
| **ET** | **09:30** | **30 min** | **680** | **680** | **100.00 %** |
| ET | 09:15 | 45 min | 680 | 463 | 68.09 % |
| ET | 09:30 | 25 min | 680 | 419 | 61.62 % |
| ET | 09:00 | 60 min | 680 | 377 | 55.44 % |

Aucune fenêtre en **horloge UTC** n'atteint le top-15 (`out/step1_or_window_grid.csv`) : la fenêtre
est ancrée à l'horloge de l'échange **avec son DST**, conformément à L56.

### 1.2 Confirmation sur les 4013 dates

Reproduction exacte au tick de `(or_hi, or_lo)` : **4013 / 4013 = 100.000 %**
(`out/step2_or_reproduction_full.csv`), 30 barres M1 par OR (médiane).

### 1.3 Corroboration indépendante par le code LIVE

`ftmo_live/mt5/book_executor.mq5:1027-1035` construit l'OR sur les barres **M5 de 15:30 à 16:00
heure serveur Paris** — soit **09:30-10:00 New York**. Les deux horloges portent leur propre DST et
coïncident sur l'échantillon. Le champ `bi` du ledger vérifie `bi − ttb_5min = 6` sur **4013/4013**
(6 barres M5 = 30 min d'OR), et `ttb_5min ≤ 71` borne la session à **16:00 ET**.

**⇒ Aucun désalignement. La mesure qui suit est faite sur la bonne fenêtre, dans la bonne horloge.**

### 1.4 Localisation de la barre de déclenchement — et deux écarts documentés

La barre M5 de déclenchement est prise **directement du ledger** (`ttb_5min`), ce qui garantit
l'alignement exact des trades re-pricés. La barre M1 de déclenchement est la première barre de
cette fenêtre M5 qui franchit `level`. Trouvée sur **4013/4013**.

Deux écarts constatés, **rapportés, non corrigés** (hors périmètre : on ne touche pas le signal) :

- **Halts COVID** — 2020-03-09 et 2020-03-12 : la barre M5 `ttb_5min` du ledger ne contient aucune
  cotation M1 (interruption). Repli documenté sur la première barre M1 franchissant strictement le
  niveau. **2 trades / 4013.**
- **Touch vs break strict** — le ledger déclenche sur un franchissement **strict** de la borne
  d'OR (le break M1 strict tombe dans la barre `ttb_5min` sur **99.95 %** des jours). Or le LIVE
  place un **ordre STOP AU REPOS** (`ORDER_TYPE_BUY_STOP` @ `or_hi`, `req.price = level`, sans
  offset — `book_executor.mq5:628-648, 1051-1071`), qui se déclenche au **touch**. Un stop au repos
  aurait donc été déclenché **plus tôt que le ledger sur 3.84 % des jours** (154/4013). C'est un
  écart de **fidélité de timing**, pas de prix (le ledger entre à `level` de toute façon) —
  **à remonter au MD**, il n'est pas mesurable dans un exercice de re-pricing à signal gelé.

---

## 2. Fraction de barres de déclenchement ouvrant au-delà du niveau

C'est le chiffre central du volet.

| granularité | N | n_gap | **fraction** | p50 | p75 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|---|---|
| **M1** (barre de déclenchement) | 4013 | **11** | **0.2741 %** | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.25 pt** |
| M5 (barre de déclenchement) | 4013 | 11 | 0.2741 % | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.25 pt |

*(percentiles inconditionnels en points, distribution tronquée à 0 ; `out/gap_distribution.csv`)*

Conditionnellement au gap, la distribution est **dégénérée** : les **11** événements valent
**exactement 0.25 pt = 1 tick** (médiane = p75 = p90 = p95 = max = 0.25). Il n'existe **aucun**
gap d'entrée de plus d'un tick sur 16 ans.

Anatomie des 11 : **tous** ont `ttb_5min = 0` (déclenchement dans la première minute après 10:00
ET), tous ont une barre M1 précédente à exactement 1 minute (aucun trou de cotation), et le saut
depuis la clôture M1 précédente vaut 0.25 à 1.00 pt. Répartition annuelle : 2010 (×2), 2011, 2012,
2019, 2020, 2022 (×2), 2024, 2025 (×2) — **pas de concentration de régime** (`out/gap_by_year.csv`).

**Pourquoi c'est structurel, et non un artefact.** Par construction, la barre M1 qui précède le
déclenchement n'a pas atteint le niveau, donc elle clôture en deçà ; la barre suivante ouvre à ce
prix sauf saut infra-seconde. Sur NQ front-month en RTH, la continuité M1 est quasi parfaite
(gap inter-barres = 1 min sur **4012/4013** ; un seul cas à 3 min). **Le gap d'entrée n'a pas de
support physique sur cet instrument.**

**⇒ H1 dans sa forme « gap » est RÉFUTÉE.** L'entrée ne se comporte pas comme la sortie : L59 vaut
pour le stop de sortie, pas pour le stop d'entrée. Ce contraste est cohérent — un stop de sortie
est franchi par un mouvement adverse qui a de la vitesse ; un stop d'entrée est franchi par un
mouvement qui *commence*.

---

## 3. Coût d'entrée mesuré — points, bps, R

Cinq régimes de remplissage, du plus optimiste au plus pessimiste, plus un diagnostic de contraste.

| régime | définition | pts | bps | **R** | t HAC(6) sur R | IC95 bootstrap sur R |
|---|---|---|---|---|---|---|
| **a_ideal** | `fill = level` (ledger) | 0.0000 | 0.0000 | 0.00000 | — | [0, 0] |
| **b_stop_market** | `max(open_M1, level)` | 0.00069 | 0.00147 | **0.0000287** | 2.19 | [0.000007, 0.000058] |
| **b1_plus1tick** | (b) + 1 tick | 0.2507 | 0.4729 | **0.010881** | 29.7 | [0.00974, 0.01206] |
| **c25_trav** | (b) + 0.25 × excursion M1 | 1.2319 | 1.2651 | **0.023323** | 53.4 | [0.02236, 0.02431] |
| **c50_trav** | (b) + 0.50 × excursion M1 | 2.4630 | 2.5287 | **0.046617** | 53.4 | [0.04469, 0.04859] |
| **c2_delay1_M1** | open de la barre M1 **suivante** | 2.4376 | 2.5683 | **0.046316** | 35.6 | [0.04365, 0.04910] |
| *m5close_bardriven* | *clôture M5 (contrefactuel)* | *4.2199* | *4.4902* | ***0.081875*** | *36.6* | *[0.07757, 0.08628]* |

N = 4013 partout. Détail avec p50/p90/p99/max : `out/entry_cost_by_regime.csv`.
Conversion R : `cost_R = cost_points / |level − stop_eff|` (sizing calculé au niveau déclencheur
à 16:00 Paris, **avant** le fill — c'est la formulation opérationnellement correcte et elle
coïncide avec le haircut linéarisé du prereg §2).

**Lecture des régimes.**

- **(b)** isole le canal *gap pur*. Il est **économiquement nul** : 0.0007 pt, 0.0015 bps,
  0.0000287 R. Le t de 2.19 est statistiquement non trivial (11 événements strictement positifs)
  mais **sans portée économique** — le rapporter sans son ampleur serait trompeur.
- **(b1)** ajoute le plancher physique de traversée : un stop touché devient marketable et paie
  au minimum un tick. C'est le **défaut recommandé du volet A**. ⚠ **Attention au double comptage
  avec le volet C** : sur NQ le tick *est* le spread inside quasi tout le temps en RTH. Si le
  volet C facture un spread RT complet, (b) doit être utilisé, pas (b1).
- **(c25 / c50)** ne sont **pas des estimations** mais des **bornes pessimistes explicites** : elles
  facturent 25 % / 50 % de **toute** l'excursion de la minute au-delà du niveau (médiane 2.25 pt,
  p90 12 pt, max 125 pt). Un ordre stop qui se déclenche au **premier** tick traversant ne subit
  pas mécaniquement un quart de la course d'une minute entière. À traiter comme un plafond.
- **(c2)** — delay+1 M1 — est un **majorant de latence** (60 s de retard sur un ordre serveur qui
  s'exécute en millisecondes). Il est fourni pour borner, pas pour retenir.
- ***m5close_bardriven*** est un **contrefactuel**, pas un coût encouru : c'est ce que paierait un
  système qui détecterait la cassure à la clôture M5 et enverrait un ordre marché. Il coûte
  **4.49 bps / 0.0819 R** et **retourne le signe du sleeve**. Le choix « stop au repos » de l'EA
  vaut donc à lui seul **≈ 8.2 pt de R sur 4.9** — la conception de l'exécution pèse ici **plus
  lourd que l'edge lui-même**.

### 3.1 Échelle de slippage et budget d'entrée

1 tick = **0.01085 R** en moyenne. Le gross vaut +0.0492 R ⇒ **break-even à 4.53 ticks =
1.13 point d'entrée** (`out/entry_slippage_ladder.csv`).

| ticks | pts | bps | mean R | t HAC(6) | IC95 |
|---|---|---|---|---|---|
| 0 | 0.00 | 0.000 | **+0.04916** | 2.74 | [+0.0142, +0.0836] |
| 1 | 0.25 | 0.471 | **+0.03831** | **2.13** | [+0.0033, +0.0730] |
| 2 | 0.50 | 0.943 | +0.02746 | 1.52 | [−0.0078, +0.0625] |
| 3 | 0.75 | 1.414 | +0.01661 | 0.92 | [−0.0188, +0.0520] |
| 4 | 1.00 | 1.886 | +0.00575 | 0.32 | [−0.0301, +0.0414] |
| 5 | 1.25 | 2.357 | −0.00510 | −0.28 | [−0.0415, +0.0309] |
| 8 | 2.00 | 3.772 | −0.03766 | −2.04 | [−0.0752, −0.0006] |

**La règle R2 du prereg (t HAC > 2.0 ET IC excluant 0) tombe entre 1 et 2 ticks d'entrée.**
À 1 tick : t = 2.13, IC95 = [+0.0033, +0.0730] — **franchi de justesse**. À 2 ticks : t = 1.52,
IC contient 0 — **R2 déclencherait ORB_KILL**. Et ceci **avant** tout coût de sortie (volet B) et
tout coût de spread (volet C).

---

## 4. Nouveau `mean(R)` après le seul coût d'entrée réaliste

Référence prereg : `r_gross` moyen = **+0.049162 R** (reproduit au 5e chiffre depuis
`(exit_px − entry)·dir / |entry − stop_eff|`, écart max 5.3e-07 ⇒ le ledger est arithmétiquement
cohérent avec lui-même).

| série | N | mean R | Δ vs gross | t HAC(6) | IC95 bootstrap | σ | SR/trade |
|---|---|---|---|---|---|---|---|
| `r_gross` (référence) | 4013 | **+0.049162** | — | 2.736 | [+0.01425, +0.08359] | 1.2008 | 0.0409 |
| `R_b_stop_market` | 4013 | **+0.049133** | −0.000029 | 2.735 | [+0.01420, +0.08356] | 1.2008 | 0.0409 |
| **`R_b1_plus1tick`** (défaut) | 4013 | **+0.038281** | **−0.010881 (−22.1 %)** | **2.127** | **[+0.00331, +0.07291]** | 1.2009 | 0.0319 |
| `R_c25_trav` | 4013 | +0.025839 | −0.023323 (−47.4 %) | 1.442 | [−0.00885, +0.06010] | 1.1985 | 0.0216 |
| `R_c50_trav` | 4013 | +0.002545 | −0.046617 (−94.8 %) | 0.142 | [−0.03203, +0.03666] | 1.1968 | 0.0021 |
| `R_c2_delay1_M1` | 4013 | +0.002846 | −0.046316 | 0.159 | [−0.03177, +0.03689] | 1.1964 | 0.0024 |
| *`R_m5close_bardriven`* | 4013 | *−0.032713* | *−0.081875* | *−1.849* | *[−0.06684, +0.00093]* | 1.1835 | *−0.0276* |

Variante **sizing adaptatif** (le lot se recalcule sur le fill effectif au lieu du niveau) :
écarts de second ordre, mêmes conclusions (`out/repriced_R_summary.csv`). Elle est **moins**
représentative du live, où le lot est calculé à l'armement 16:00 Paris.

**Conclusion §4 — le coût d'entrée seul ne tue pas l'ORB, mais il consomme le cinquième du gross et
ramène le t HAC de 2.74 à 2.13, à 0.13 de la borne de kill du prereg.** La marge restante pour le
volet B (sortie) et le volet C (spread) est de **3.5 ticks**, soit ≈ **1.4 bps** au niveau d'indice
médian récent. À rapprocher de l'ancre de spec **US100 RT = 2.2 bps** citée au prereg §0 : *si ce
2.2 bps est le bon ordre de grandeur, l'entrée + le spread suffisent à eux seuls à franchir R1/R2.*

---

## 5. Décompositions

### 5.1 Par année (`out/breakdown_by_year.csv`, `out/microstructure_by_year.csv`)

L'effet **dérive fortement, et dans le sens favorable** — pour une raison purement mécanique : **le
tick NQ est fixe à 0.25 pt alors que l'indice a été multiplié par ~13**.

| annee | N | tick (bps) | excursion M1 au-delà, moyenne (bps) | **cost_R 1 tick** | cost_R c25 | r_gross | R_b1 |
|---|---|---|---|---|---|---|---|
| 2010 | 144 | 1.281 | 7.49 | **0.0243** | 0.0315 | −0.0110 | −0.0353 |
| 2013 | 244 | 0.829 | 3.96 | 0.0222 | 0.0255 | −0.0311 | −0.0532 |
| 2016 | 251 | 0.551 | 3.80 | 0.0141 | 0.0215 | +0.0169 | +0.0029 |
| 2019 | 249 | 0.325 | 4.88 | 0.0083 | 0.0259 | +0.0396 | +0.0313 |
| 2022 | 253 | 0.201 | 8.08 | 0.0023 | 0.0216 | +0.1190 | +0.1167 |
| 2024 | 255 | 0.131 | 5.82 | 0.0031 | 0.0301 | +0.1863 | +0.1831 |
| 2026 | 104 | 0.098 | 5.53 | **0.0016** | 0.0208 | +0.0841 | +0.0825 |

Le coût d'un tick d'entrée est passé de **0.0243 R (2010) à 0.0016 R (2026) — un facteur 15**.
En revanche l'**excursion intra-minute au-delà du niveau reste stable en bps** (3-8 bps, sans
tendance), donc `cost_R_c25` est **plat** (0.019-0.032 sur toute la période).

**Conséquence méthodologique** : un coût d'entrée exprimé en *ticks fixes* et calibré sur les
années 2010-2015 **sur-pénalise massivement** le régime actuel. Un coût exprimé en *bps* le
sous-pénalise si on le calibre sur la même période. Le paramètre `ORB_RT_BPS = "era"` de
`config_v22.py:22` a donc une justification empirique réelle **du côté de l'entrée** — mais la
dérive va dans le sens d'un coût qui **diminue**, pas qui augmente.

Test de dérive formel (`cost_bps ~ année`, HAC lag-6) :
- `b_stop_market` : pente **−0.00033 bps/an (t −1.69)** — non significative, gaps quasi absents.
- `c25_trav` : pente **+0.021 bps/an (t +2.90)** — attention, la trajectoire est en **U** (minimum
  0.74 bps en 2017, remontée à 1.4-1.6 depuis 2022), pas une dérive monotone ; l'ajustement linéaire
  est trompeur ici et ne doit pas être cité seul.

### 5.2 Par `regime_tag` (`out/breakdown_by_regime_tag.csv`)

| regime_tag | N | frac_gap | r_gross | R_b1 | t HAC(6) sur R_b1 | R_c25 |
|---|---|---|---|---|---|---|
| trending | 2877 | 0.348 % | +0.06548 | **+0.05328** | **+2.47** | +0.04100 |
| chop | 630 | 0.000 % | +0.00592 | −0.00323 | −0.07 | −0.01524 |
| vol_shock | 506 | 0.198 % | +0.01025 | +0.00470 | +0.10 | −0.00922 |

Le coût d'entrée est **homogène** entre régimes (0.30-0.52 bps à 1 tick) : il ne discrimine pas.
Ce que la décomposition révèle est **antérieur au coût** — **l'intégralité du gross ORB vit dans
`trending`** ; `chop` et `vol_shock` (1136 trades, 28 %) sont déjà nuls avant tout coût et passent
en négatif dès le premier tick. C'est un constat sur le ledger, pas sur H1 ; **hors périmètre
d'action ici** (aucun filtre de régime ne doit être proposé — prereg §4), mais à remonter.

### 5.3 Par délai de cassure (`out/breakdown_by_ttb.csv`)

| ttb_5min | N | frac_gap | cost_bps (b) | cost_bps (c25) | R_b1 |
|---|---|---|---|---|---|
| 0 | 1891 | 0.582 % | 0.0031 | 1.527 | +0.0472 |
| 1 | 526 | 0 | 0 | 1.065 | +0.0464 |
| 2-3 | 579 | 0 | 0 | 1.070 | +0.0925 |
| 4-8 | 581 | 0 | 0 | 1.063 | +0.0084 |
| >8 | 436 | 0 | 0 | 0.898 | −0.0423 |

**100 % des gaps d'entrée sont concentrés sur `ttb_5min = 0`** — la première minute après 10:00 ET,
qui porte 47 % des trades. C'est le seul endroit où l'ouverture peut sauter (transition de la fin
de l'OR vers la cassure immédiate). Ailleurs, le gap est strictement nul.

### 5.4 Par outcome (`out/breakdown_by_outcome.csv`)

STOP (N=1590) : R passe de −1.0000 à **−1.0120** à 1 tick. TIME_STOP (N=2423) : de +0.7376 à
**+0.7275**. Le coût d'entrée est **symétrique** entre gagnants et perdants (0.0120 vs 0.0102 R) —
il n'y a pas de sélection adverse mesurable **sur le prix d'entrée**.

En revanche, une statistique de qualité d'exécution mérite d'être versée au dossier :
**39.17 % des barres M1 de déclenchement clôturent du mauvais côté du niveau** (43.1 % sur les
trades STOP, 36.6 % sur les TIME_STOP). Le fill est bon, mais 2 fois sur 5 le marché est déjà
revenu sous le niveau à la fin de la minute d'entrée. C'est de la sélection adverse **de signal**,
pas de prix — hors H1, mais utile aux volets B et D.

---

## 6. Livrable pour le volet D

`out/R_repriced_entry.parquet` — **N = 4013**, indexé par `date` (2010-06-07 → 2026-05-29),
49 colonnes.

- `R_entry_default` = **`R_b1_plus1tick`**, moyenne **+0.038281**. C'est la série recommandée.
- Colonnes disponibles pour chaque régime `r` ∈ {`a_ideal`, `b_stop_market`, `b1_plus1tick`,
  `c25_trav`, `c50_trav`, `c2_delay1_M1`, `m5close_bardriven`} :
  `cost_pts_{r}`, `cost_bps_{r}`, `cost_R_{r}`, `R_{r}` (sizing au niveau, **recommandé**),
  `Radapt_{r}` (sizing sur fill effectif, sensibilité).
- Colonnes de contexte : `direction`, `level`, `stop_eff`, `exit_px`, `outcome`, `regime_tag`,
  `ttb_5min`, `risk_pts`, `lev`, `r_gross`, `is_gap`, `open_beyond_pts`, `excursion_beyond_pts`.

**Avertissement d'usage au volet D** : ne pas empiler `R_b1_plus1tick` avec un spread RT complet
issu du volet C — sur NQ le tick *est* le spread inside. Empiler `R_b_stop_market` (gap pur, coût
≈ 0) avec le spread mesuré du volet C est la composition correcte.

---

## 7. Limites, et ce qui ne transfère PAS

1. **Le ledger est en NQ futures, le live exécute US100.cash CFD (prereg H4/L33).** Tout ce qui
   précède mesure la microstructure du **future**. Le tick NQ vaut 0.098 bps en 2026 ; un CFD
   indice n'a ni ce pas de cotation, ni ce carnet, ni cette règle de déclenchement (le BUY STOP
   MT5 se déclenche sur l'**Ask**, donc le prix bid doit atteindre `level` + spread). **La conclusion
   « le gap d'entrée est nul » est établie sur NQ et ne se transporte pas telle quelle sur le CFD.**
   Ce transfert est la charge du **volet C**.
2. **M1 OHLC ne résout pas l'infra-minute.** Le régime (b) est un **plancher** de coût : il exclut
   par construction toute traversée à l'intérieur de la minute de déclenchement. Les régimes (c)
   bornent par le haut, mais avec un modèle volontairement grossier (fraction d'excursion). Le vrai
   coût est entre les deux et **plus près de (b1) que de (c25)** sur un instrument aussi liquide,
   pour un ordre de la taille d'un sleeve à 0.25 % de risque sur un compte 10k.
3. **Le déclenchement au *touch* du stop au repos réel** aurait produit un ledger différent sur
   3.84 % des jours. Non corrigé (signal gelé), remonté.
4. **Aucun walk-forward, aucun DSR ici** : R4 et R5 du prereg s'évaluent sur le `R_net` final,
   après composition des volets A+B+C. Le volet A ne produit pas de verdict de kill.

---

## 8. Verdict du volet A

- **H1 sous sa forme « gap » : RÉFUTÉE.** 0.274 % (11/4013), tous d'exactement 1 tick, tous
  concentrés sur `ttb_5min = 0`. L'entrée ne reproduit pas la signature L59 de la sortie.
- **H1 sous sa forme « le fill n'est pas gratuit » : CONFIRMÉE, et matérielle.** Le plancher
  physique d'un tick coûte **0.473 bps / 0.0109 R**, soit **22.1 % du gross**, et fait tomber le
  t HAC de **2.74 à 2.13**.
- **Budget restant pour les volets B et C : 3.5 ticks ≈ 0.87 point ≈ 1.4 bps.** Le sleeve franchit
  R2 avec le seul coût d'entrée ; il ne le franchit plus dès **2 ticks** de coût total d'entrée.
- **Résultat défavorable publié tel quel** : la sensibilité de référence du prereg (« la frontière
  de mort est entre 2 et 3 bps ») est **confirmée par le bas** — l'entrée seule en consomme déjà
  0.47, et la moitié du chemin est faite avant que la sortie et le spread n'aient été facturés.

---

### Reproduction

```
/usr/bin/python3 code/step1_verify_or_window.py      # grille fuseau × fenêtre OR
/usr/bin/python3 code/step2_entry_fill.py            # localisation + fills + table enrichie
/usr/bin/python3 code/step3_stats.py                 # HAC, bootstrap, décompositions, parquet
/usr/bin/python3 code/step4_microstructure_drift.py  # dérive tick/excursion en bps
```

Bootstrap : **block bootstrap circulaire (Politis-Romano 1992)**, blocs fixes de 20 trades,
10 000 réplications, graine 20260812. iid jamais utilisé. t : OLS sur constante,
`cov_type='HAC'`, `maxlags=6`. Console complète : `out/step3_console.txt`.
