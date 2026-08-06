# Les prédicteurs EXOGÈNES — la dernière dimension ouverte du véhicule CFD

**2026-08-06. N0 — SCREENING + une candidate instruite. Aucun PASS revendiqué.**
Interpréteur `/usr/bin/python3` (pandas 2.2.3 / numpy 2.0.2 / statsmodels 0.14.6), vérifié.
Lecture seule sur tout chemin du répertoire principal. Aucun blob data commité.

`gross_surface_map_2026-08` a balayé 8 695 cellules de prédicteurs de **PRIX** et déclaré son §11
non testé : « les prédicteurs exogènes (flux, calendrier, cross-sectionnel) ». Ce dossier occupe
ce terrain, sur les deux sleeves en sommeil, avec les données exogènes **gratuites déjà au dépôt**.

---

## 0. Résultat en cinq lignes

1. **Les prédicteurs exogènes gratuits ne franchissent le gate économique nulle part.** 241 cellules
   post-2021, **0** clôt simultanément le gate de coût et le seuil de significativité.
2. **Le ratio `gross / coût` de la formulation intraday-flat est 0.336** — contre **0.38** pour la
   carte des prédicteurs de prix et **0.36** pour L43. **Troisième réplication indépendante**, cette
   fois avec de l'information NON-PRIX. L'exogénéité ne déplace pas le dénominateur.
3. **La cellule la plus significative de toute l'étude a t_HAC = 5.02 et perd de l'argent**
   (gross 1.214 bps contre 1.50 de coût). Et son t est **faux** : son placebo à autocorrélation
   appariée rend un |t| médian de **2.96** et p = 0.13. Le bootstrap par blocs, lui, donnait
   p = 0.0000.
4. **Pour l'OR, le problème du portage n'est pas soluble par un signal exogène** : conditionner ne
   réduit la facture de portage qu'en échangeant du swap contre du spread. La meilleure cellule
   coûte **515 bps/an contre 397 bps/an pour détenir l'or sans rien faire** (1.30×), et **aucune**
   cellule ne bat le long inconditionnel détenu (+1 086 bps/an, SR 0.62).
5. **Une seule candidate survit au filtre statistique — et elle est INADMISSIBLE** : XAUUSD la
   **veille de la publication du CPI US** (+38.07 bps, t 3.86, Šidák-76 p 0.0086, placebo
   jour-du-mois p 0.0012). Elle échoue sur la **règle dure du walk-forward** (65 trades, 5 folds
   impossibles), n'a **aucun hors-échantillon** (le cache calendrier commence en 2020) et son DSR
   vaut **0.637**. Elle est **UNDERPOWERED de justesse** contre son propre MDE.

---

## 1. CE QUE CONTIENNENT RÉELLEMENT LES CACHES (fait avant toute construction)

`data/metadata/*.json` ne contient **aucune donnée** : ce sont des manifestes de ~400 octets qui
pointent vers `data/raw/*.parquet`. C'est là que vivent les séries.

`cache_inventory.csv` / `cache_inventory_calendars.csv`. Quatre défauts trouvés, deux fatals :

| série | ce qui est annoncé | ce qu'il y a **réellement** | verdict |
|---|---|---|---|
| **BAMLH0A0HYM2** (spread crédit HY) | demandé depuis 2007/2010/2018/2020 dans 4 fichiers | **786 obs, 2023-05-23 → 2026-05-21 dans LES QUATRE**, quelle que soit la date de début demandée | **TRONQUÉ à 3 ans — INUTILISABLE** (ni pré-2021, ni puissance) |
| **CBOE put/call** (equity + total) | 3 253 obs | **se termine le 2019-10-04** | **MORT pour toute étude post-2021** |
| **NAAIM** exposure | 1 039 obs hebdo | index stocké **en ordre DÉCROISSANT** + **2 labels dupliqués** (2006-07-05 / 07-12, deux scrapes à arrondis différents) ⇒ `.reindex()` **lève une exception** | utilisable après `sort_index` + dédup |
| **economic_calendar.csv → NFP** | 77 dates 2020-2026 | **100 % des dates = premier vendredi du mois** (77/77) | **RÈGLE GÉNÉRÉE, pas le calendrier BLS réel** (déc. 2019 publié le 10 janv. 2020, pas le 3) — à ne pas utiliser |
| economic_calendar.csv → **CPI** | 77 dates | jour du mois 9-15, mardi-jeudi ; 2020-01-14 / 02-13 / 03-11 / 04-10 **= vraies dates BLS** | **AUTHENTIQUE** |
| economic_calendar.csv → FOMC | 52 dates | **50/52 coïncident** avec `fomc_events.csv` (source indépendante) | authentique |
| `fx_rates_3m.csv` | « taux 3 mois FX » | **MENSUEL** (257 lignes, fins de mois), JPY s'arrête au **2026-03-31**, EUR/GBP au 2026-01-31 | utilisable en marche d'escalier, jamais en daily |
| FRED T10Y2Y / DGS3MO / DTB3 / DTWEXBGS / VIXCLS | — | daily propre, 2003/2006/2007 → **2026-05** | utilisable |

⚠ **Le panel de prix va jusqu'au 2026-06-05, l'exogène s'arrête vers le 2026-05-21.** L'échantillon
joint se termine donc mi-mai 2026, pas aujourd'hui.

⚠ **Le calendrier économique commence le 2020-01-03.** Il n'existe **aucun hors-échantillon
pré-2021** pour la famille calendrier, sauf via `fomc_events.csv` (182 événements, 2004-2026).

---

## 2. LE MÉCANISME, ÉCRIT AVANT DE MESURER

Les signes sont pré-enregistrés dans `code/exog_lib.py:MECHANISM_SIGN`, avant tout calcul.

**OR — actif réel à duration.** L'or est une créance réelle perpétuelle sans coupon : sa valeur est
l'inverse du taux réel d'actualisation. Hausse du taux court ⇒ coût d'opportunité de détenir un
actif sans rendement ⇒ or baisse (E1 signe **−**). Courbe pentue ⇒ assouplissement anticipé ⇒ taux
réels futurs plus bas ⇒ or monte (E2/E3 signe **+**). Prime de refuge ⇒ VIX haut = or haut (E5 **+**),
exposition actions élevée = pas de bid refuge (E7 **−**).

**USDJPY — différentiel de taux.** L'échec de l'UIP fait que la devise à haut taux s'apprécie :
différentiel US-JPY qui s'élargit ⇒ USDJPY monte (E1, E6, E6b signe **+**). Le yen est la devise de
financement : risk-off ⇒ débouclage ⇒ USDJPY baisse (E5 signe **−**).

⚠ **E4 (dollar) est signalé d'avance comme quasi-tautologique** (L38) et, plus fondamentalement,
**ce n'est pas un prédicteur exogène : c'est un PRIX.** Il est conservé comme témoin, pas comme
candidat. Il ne compte pas dans la conclusion sur l'exogénéité.

**Look-ahead macro.** T10Y2Y, DGS3MO, DTB3, DTWEXBGS, VIXCLS sont des **cotations de marché**
(H.15 / CBOE), pas des statistiques révisées : la valeur du jour T est définitive et publiée le soir
même. Tout est décalé de **T-1** malgré cela. NAAIM est une enquête du mercredi publiée le jeudi :
le `ffill` + `shift(1)` garantit qu'on n'utilise jamais la valeur du jour de l'enquête.
`fx_rates_3m` est mensuel, propagé en marche d'escalier — **la date de publication n'est pas
établissable**, donc E6/E6b sont à traiter comme une **borne haute**. Les dates de calendrier sont
connues des années à l'avance : aucun problème de publication.

**Puissance, déclarée AVANT les conclusions.** Post-2021 = 5.4 ans. Le MDE per-trade à |t| = 2.5 est
`2.5 × σ / √N`. Il est rapporté **cellule par cellule** dans `robustness_battery.csv`. Sur les 7
cellules passées à la batterie, **5 sont UNDERPOWERED** et les 2 « powered » sont celles dont le net
est **négatif**.

---

## 3. FORMULATION 1 — prédicteur exogène → position TENUE

`f1_held_all.csv` (179 lignes, **83 cellules post-2021**), `f1_held_legs.csv` (307 jambes disjointes).
2 instruments × 7-9 prédicteurs × horizons 1/5/20 j × {médiane, quintile}, entrées non chevauchantes,
baseline L58 appariée à la répartition long/short que l'état produit réellement.

### 3.1 Le gate est vide, et la queue est plate

| seuil sur `t_excess` | cellules réelles | attendu iid |
|---|--:|--:|
| \|t\| > 1.96 | **1 / 83 (1.2 %)** | 5.0 % |
| \|t\| > 2.50 | **0 / 83** | 1.24 % |
| max \|t\| | **2.31** | — |

**La formulation tenue produit MOINS de queue que le hasard.** Il n'y a rien à expliquer.
Gate `net_bps > 0 ET |t_excess| > 2.5` : **VIDE**.

### 3.2 La meilleure cellule est un long-leg-only (L25)

`XAUUSD / E2_slope / H=1 / quintile`, post-2021 : gross 7.84 bps, t 2.29, net +4.95, 178 trades/an.
Séparée en **jambes disjointes** :

| jambe | N | gross | t | baseline appariée | excès | t |
|---|--:|--:|--:|--:|--:|--:|
| **long** | 583 | **+13.199** | 2.77 | **+5.722** | +7.478 | 1.57 |
| **short** | 382 | **−0.339** | **−0.07** | −5.722 | +5.383 | 1.18 |

La jambe short est **plate à zéro**. Son « excès » de +5.38 n'est pas un edge : c'est le crédit
comptable d'avoir été absent pendant un marché haussier. Le mécanisme « courbe plate ⇒ or baisse »
est **falsifié sur la jambe qui le teste**. Et 43 % du gross de la jambe long est la baseline
inconditionnelle.
**Contrôle pré-2021 : la même cellule rend gross 1.77, t 0.74, net −0.91 bps.** Le signe du net
s'inverse hors de l'ère post-2021.

### 3.3 Le seul |t| > 2 de F1 est un prédicteur de PRIX, et à l'envers

`USDJPY / E4_d_dollar / H=1 / médiane` : t_excess **−2.31**, c'est-à-dire le signe **opposé** au
mécanisme pré-enregistré (le momentum du dollar prédit un *reversal* d'USDJPY, pas une continuation).
Placebo apparié p 0.0225 — donc probablement réel. Mais : (a) le dollar est un **prix**, pas un
exogène ; (b) net_ann **−1 480 bps** ; (c) pré-2021 t +0.56, signe inversé. Rien à en tirer.

---

## 4. FORMULATION 2 — état exogène à T-1 → trade INTRADAY-FLAT à T

`f2_intraday_all.csv` (200 lignes, **82 cellules conditionnelles post-2021** + 10 benchmarks
inconditionnels), `f2_hour_diagnostics.csv`. Barres H1 en vrai UTC (cache `gross_surface_map`,
lecture seule) converties en **heure d'échange America/New_York avec son DST** (L56).
Trois formes pré-enregistrées : A = 18:00→19:00 (heure de réouverture Globex), B = 09:00→16:00,
C = 15:00→17:00 (la seule fenêtre où la carte du gross trouvait de la structure).

**Swap = 0 par construction.** Le portage qui tue l'or est retiré. C'est le test le plus favorable
possible.

### 4.1 Deux formes tombent avant d'être lues

- **XAUUSD forme A n'existe pas.** L'heure locale 17 ne compte que **112 barres post-2021 contre
  1 400** aux autres heures : c'est la pause de settlement CME. Un prix d'entrée « à 18:00 » se lit
  sur la barre 17, qui est un trou. La forme est retirée, pas mesurée à l'aveugle. (L52 : la barre
  agrège le gap de halt, que personne ne trade.)
- **USDJPY forme A est un artefact de cotation.** La fourchette médiane à l'heure d'entrée vaut
  **22.3× la médiane journalière** (33.5 points contre 1.0). C'est exactement le §6 de
  `gross_surface_map`, réplique indépendante. Le `t_gross = 6.09` de son benchmark inconditionnel
  est **le rollover, pas un edge**. Les 4 cellules conditionnelles de cette forme sont **mortes par
  contamination**, indépendamment de leur t.

### 4.2 La cellule la plus significative de l'étude — et pourquoi son t est faux

`USDJPY / C_afternoon_15_17 / E6_us_jpy_diff / quintile`, post-2021 :

| mesure | valeur |
|---|--:|
| N / fréquence | 1 170 / **216 par an** |
| gross par trade | **1.214 bps** |
| t_HAC6 | **4.86** |
| excès vs baseline L58 | +1.255, **t 5.02** |
| bootstrap par blocs | **p = 0.0000** |
| coût RT | 1.50 |
| **net par trade** | **−0.286** |
| **net annualisé** | **−61.7 bps** |
| **longueur moyenne de plage** | **390 jours** |
| **placebo à autocorrélation appariée : \|t\| médian** | **2.96** |
| **placebo : \|t\| p95** | **5.20** |
| **p_placebo** | **0.1325** |

Deux lectures, toutes deux nécessaires :

**(a) Économiquement, c'est mort avant toute discussion statistique.** 1.214 bps de gross contre
1.50 de coût. `gross/coût = 0.81`. Le gate `3×` demande 4.50.

**(b) Statistiquement, le t de 5.02 est une illusion de persistance.** Le différentiel de taux
US-JPY est une **marche d'escalier mensuelle** qui, post-2021, est une fonction quasi monotone du
temps (Fed à 0 → 5.5 %, BoJ immobile). Son côté change de signe **3 fois en 5.4 ans** : la longueur
moyenne de plage est de **390 jours**. Le HAC lag-6 ne voit pas ça — il croit avoir 1 170
observations quand il en a l'équivalent de 3. Le placebo par rotation circulaire, qui **préserve
l'autocorrélation et la répartition long/short** et ne détruit que l'alignement, rend un |t| médian
de **2.96** et un p95 de **5.20**. Un t de 4.86 est **banal** dans cette famille.

> **Le bootstrap par blocs donne p = 0.0000 sur la même série.** C'est la loi 1 du sprint 2026-08-04
> mesurée à nouveau, sur un cas où l'écart est maximal : `p_bootstrap 0.0000` contre
> `p_placebo 0.1325`. Le bloc rééchantillonne le **rendement** en préservant sa structure ; il ne
> touche pas à la persistance du **signal**. Les deux contrôles ne testent pas la même chose et le
> bootstrap ne remplace pas le placebo.

La version médiane du même prédicteur (plage moyenne **469 jours**) est encore plus nette :
t observé 3.18, placebo |t| médian **3.02**, **p_placebo = 0.46**. Indiscernable du bruit.

### 4.3 L'excès de queue de F2 est entièrement expliqué par la persistance

| seuil sur \|t_excess\| | cellules réelles F2 | attendu iid |
|---|--:|--:|
| > 1.96 | 8 / 82 (9.8 %) | 5.0 % |
| > 2.50 | **5 / 82 (6.1 %)** | 1.24 % |

5 % contre 1.24 % ressemble à une découverte. Ce n'en est pas une : **les 5 cellules concernées ont
toutes une longueur de plage > 65 jours**, et le placebo apparié reproduit leur |t| médian. Un état
macro lent gonfle mécaniquement le t d'un facteur 3-4 sans rien prédire.

### 4.4 Le compromis gross / fréquence, mesuré (jamais l'un sans l'autre)

| cellule | fréq/an | gross | net/trade | **net annualisé** |
|---|--:|--:|--:|--:|
| USDJPY C, E6, **quintile** | 216.0 | 1.214 | −0.286 | **−61.7** |
| USDJPY C, E6, **médiane** | 259.6 | 0.822 | −0.678 | **−176.0** |
| USDJPY C, **inconditionnel long** | 259.6 | 0.219 | −1.281 | **−332.7** |
| XAUUSD C, E5b_vix, quintile | 88.1 | 2.365 | +0.525 | **+46.2** |
| XAUUSD C, **inconditionnel long** | 250.0 | 0.709 | −1.131 | −282.8 |

Le conditionnement **fait bien ce qu'on attend de lui** : il multiplie le gross par trade
(0.219 → 0.822 → 1.214 en resserrant le filtre) en divisant la fréquence. Le mécanisme fonctionne.
**Il ne fonctionne simplement pas assez** : il faudrait un facteur 7 sur le gross pour atteindre le
gate `3×`, et le resserrement en donne 5.5 en épuisant déjà le quintile.

3 cellules sur 82 ont un net positif. La meilleure, `XAUUSD C / E5b_vix_level / quintile`, vaut
**+46 bps/an** — avant toute déflation, avec t_excess 2.13, MDE 2.72 (**UNDERPOWERED**), placebo
p 0.18, et un contrôle pré-2021 à **−130 bps/an**.

---

## 5. L'OR : le portage n'est pas soluble par un signal exogène

C'est la question posée. Réponse en trois tableaux.

### 5.1 Aucun état exogène ne met l'or SHORT de façon rentable

Le swap short vaut **−0.336/nuit contre −1.518 en long** : 4.5× moins cher. Déplacer du poids sur la
jambe short serait la seule façon structurelle de résoudre le portage.
`gold_short_leg_inventory.csv`, 29 jambes short post-2021 :

**2 sur 29 ont un gross positif** (t 0.49 et 0.42, donc du bruit). **2 sur 29 ont un net positif.**
Le reste va de −0.3 à −143 bps par trade. Les deux jambes short les plus significatives en |t| sont
**négatives** (E5_d_vix médiane H=5, t −2.73 ; E5b_vix_level médiane H=5, t −2.27) — c'est-à-dire
que les états censés annoncer un or faible annoncent un or **fort**.
**La porte du short-or est fermée par la mesure, pas par le coût.**

### 5.2 Conditionner ne réduit pas la facture, ça l'échange contre du spread

`gold_annual_cost_bill.csv`. **Détenir l'or en continu coûte 397 bps/an** (260 nuits × 1.518 + un
aller-retour). Facture annuelle des cellules conditionnées :

| régime | fréq/an | facture annuelle | **vs détenir sans rien faire** |
|---|--:|--:|--:|
| quintile H=20 (E2_slope) | 9.5 | 216 | **0.54×** |
| quintile H=5 (divers) | 19-36 | 117-255 | 0.29-0.64× |
| **quintile H=1 (E2_slope, la meilleure cellule)** | 178.3 | **515** | **1.30×** |
| médiane H=1 (toutes) | 258.5 | 699-757 | **1.76-1.91×** |

Les seuls régimes moins chers que la détention passive sont ceux qui tradent **9 à 36 fois par an** —
et à cette fréquence, N tombe à 50-193 et les t à 0.2-2.1. **Le portage n'est esquivé qu'en
détruisant la puissance.** C'est L57 (« le coût fixe domine sur petit notionnel ») transposé à
l'axe temps : le coût fixe par trade domine dès qu'on trade.

### 5.3 Rien ne bat le long inconditionnel détenu

`head_to_head_vs_unconditional.csv`, post-2021, net de tout :

| | net annualisé | Sharpe net |
|---|--:|--:|
| **XAUUSD long inconditionnel, détenu** | **+1 085.9 bps** | **0.621** |
| meilleure F1 conditionnée (E2_slope H=20 quintile, **N=50**, t 1.91) | +1 192.7 | — |
| **USDJPY long inconditionnel, détenu** | **+830.0 bps** | **0.866** |
| meilleure F1 conditionnée (E7_naaim H=20 médiane, **N=70**, t 0.83) | +297.1 | — |

Sur USDJPY, la meilleure sleeve conditionnée fait **2.8× moins** que ne rien faire. Sur l'or, elle
« gagne » de 10 % avec **50 trades** et un t de 1.91 — c'est-à-dire pas du tout.

⚠ Ces deux longs inconditionnels ne sont pas des stratégies : ce sont les marchés haussiers 2021-2026
de l'or et du yen-carry. C'est précisément le point de L58 — **c'est la baseline appariée qu'il faut
battre, et personne ne la bat.**

### 5.4 Et J1 (USDJPY) ? Le diagnostic est différent, la conclusion est la même

J1 meurt d'**absence de signal** (β 0.656 ≈ duty cycle, R² 65.6 %). Un remplaçant doit apporter un
vrai signal. Les prédicteurs exogènes sur USDJPY, eux, **ne sont PAS du beta déguisé** :
R² contre un buy-and-hold vol-targeté de la même forme de trade = **0.00 % à 12.5 %**, tous très
en dessous du seuil L38 de 30 %. Ils sont bien orthogonaux.
**Ils sont orthogonaux et vides.** Le mode d'échec n'est pas celui de J1 — c'est pire : J1 au moins
capturait du beta.

---

## 6. LA FAMILLE CALENDRIER — et la seule candidate de l'étude

`calendar_tests.csv`, 97 cellules (**76 post-2021**). FOMC (182 événements 2004-2026), CPI, NFP, GDP
× {veille, jour, lendemain} × {tenue 1j, formes intraday}. NFP écarté (dates générées par règle, §1).

- 32 / 76 cellules ont `|gross| / coût ≥ 3` — mais **1 seule** dépasse aussi |t| > 2.5.
- Le calendrier est la seule famille de l'étude où le gate de coût est *facile* : les événements sont
  rares (8-12/an), donc le coût annuel est négligeable et le gross par trade est grand.
  **C'est la seule structure de coût favorable trouvée dans tout ce travail.**

### 6.1 XAUUSD, la VEILLE de la publication du CPI US

`cpi_candidate.csv`, `cpi_by_year.csv`, `xauusd_day_of_month_profile.csv`.

| | valeur |
|---|--:|
| N / fréquence | **65** / 12.0 par an |
| gross | **+38.07 bps** |
| t_HAC6 | **3.86** |
| moyenne inconditionnelle (baseline L58) | +5.722 |
| **excès** | **+32.35** |
| net par trade / annualisé | +34.71 / **+416.8 bps** |
| `gross / coût` | **20.7** |
| taux de réussite | **67.7 %** (gagnant +83.4 / perdant −56.9) |

**Ce qu'elle PASSE :**
- **Placebo apparié au JOUR DU MOIS (L58) : p = 0.0012.** Le CPI sort entre le 9 et le 15 ; la veille
  tombe donc dans une bande étroite. Le pool des jours 8-14 **hors** veilles de CPI rend +2.909 bps
  (t 0.47) — et son **biais contre l'espérance inconditionnelle n'est que −2.81 bps**, donc le
  placebo lui-même est propre. C'est le contrôle gratuit exigé par L58, et il est **réussi**, pas
  contourné.
- Šidák sur les 76 cellules calendrier : **p = 0.0086**. Bootstrap par blocs : **p = 0.0056**.
- Robuste aux extrêmes : les 3 plus gros mouvements font 31 % du P&L ; sans eux, moyenne **+27.6 bps,
  t 3.49**.
- 6 années sur 6 positives.

**Ce qu'elle ÉCHOUE — et c'est décisif :**
- **Walk-forward IMPOSSIBLE.** 65 trades. La règle dure exige ≥ 5 folds ; 5 folds de 13 trades ne
  sont pas un walk-forward. **INADMISSIBLE en l'état**, au même titre que Strategy B.
- **Aucun hors-échantillon.** `economic_calendar.csv` commence en 2020-01 : 12 événements pré-2021.
  Toute la mesure vit dans la fenêtre de découverte.
- **DSR = 0.637** (n_trials 76, rf 0, dispersion déclarée 0.5). Loin de 0.95.
- **UNDERPOWERED de justesse** : excès +32.35 contre un MDE de **33.75** à |t| = 2.5.
- **Ne généralise pas à l'événement voisin.** Dans la MÊME ère, la veille de FOMC sur l'or rend
  **+8.21 bps, t 0.39** (N=43). Si le mécanisme était « dérive avant une publication macro US
  programmée », la veille de FOMC devrait la montrer. Elle ne la montre pas. *(À noter : la veille de
  FOMC est **+17.21 bps, t 1.78, N=114 en PRÉ-2021** — même signe, sur 20 ans. C'est une corrélation
  faible en faveur d'un effet réel, pas une preuve.)*
- Deux années sur six sont plates (2023 +15.1, 2024 +1.1) ; tout vient de 2021, 2022 et 2025.
- Famille adjacente à `announcement_premium_2026-06` (NO-GO) et à L42.

**Verdict : PAS un candidat. Une hypothèse instruite, bloquée sur la puissance.**
Le blocage est de nature **PUISSANCE** au sens de la politique de ré-ouverture — donc rouvrable, et
le geste qui débloque est identifié et gratuit : **étendre le calendrier des publications CPI du BLS
à 2007-2019** (public, gratuit). N passerait de **65 à ~230**, ce qui rend un walk-forward 5 folds
possible et fournit un hors-échantillon de 14 ans. C'est le seul next step à valeur positive
identifié par ce dossier.

---

## 7. LE CHIFFRE QUI FERME LA DIMENSION

`gross_over_cost_ratio.csv` :

| source | cellules | **médiane `gross / coût`** | p90 | meilleure |
|---|--:|--:|--:|--:|
| **F2 intraday-flat, exogène** (ce dossier) | 82 | **0.336** | 0.955 | 1.721 |
| F1 tenue, coût = RT + swap payé | 83 | 0.881 | 3.266 | 6.528 |
| `gross_surface_map` — prédicteurs de **PRIX** | 6 511 | **0.38** | — | — |
| **L43** — FX intraday-flat, méthode entièrement différente | — | **0.36** | — | — |

**0.336 contre 0.38.** Quatre prédicteurs de prix triviaux sur 19 instruments, et neuf prédicteurs
macro exogènes sur deux instruments, produisent **le même ratio**. L'information exogène — courbe des
taux, taux court, dollar, VIX, différentiel de taux, positionnement des gérants — **ne déplace pas le
dénominateur d'un pouce** sur une forme intraday-flat.

La colonne F1 (0.881 médiane) est plus haute uniquement parce qu'une position tenue accumule du gross
sur H jours contre **un seul** aller-retour ; son p90 de 3.27 et son meilleur de 6.53 sont des
cellules à H=20 avec **N = 50-70**. Dès qu'on rapporte cette facture à l'année (§5.2), l'avantage
disparaît.

---

## 8. Ce que ça NE PROUVE PAS

1. **Ça ne prouve pas que les prédicteurs exogènes sont inutiles en général.** Ça prouve que **les
   séries exogènes GRATUITES DÉJÀ AU DÉPÔT** — 6 séries FRED daily, un sondage hebdomadaire, un
   panel de taux mensuel, deux calendriers d'événements — n'ajoutent rien au-dessus du coût sur
   **XAUUSD et USDJPY** au tarif CFD. Les données exogènes qui portent réellement du flux (COT/CFTC,
   positionnement des dealers, flux ETF or, options, ordre-flow) **ne sont pas testées ici** et ne
   sont pas concernées.
2. **Ça ne teste que deux instruments.** Le mandat portait sur les deux sleeves en sommeil. Rien ici
   ne dit ce que ces mêmes prédicteurs feraient sur les indices ou l'énergie.
3. **Le cache de spread crédit est tronqué, pas absent.** BAMLH0A0HYM2 sur 3 ans ne permet aucune
   inférence, mais le spread crédit **reste un prédicteur non testé**, pas un prédicteur réfuté.
   Idem pour le put/call CBOE (mort après 2019) : la famille sentiment options est **non mesurée**,
   pas fermée.
4. **E6/E6b reposent sur une série mensuelle dont la date de publication n'est pas établissable.**
   Leurs résultats sont des **bornes hautes**. Ils sont négatifs, donc la borne ne change rien — mais
   un futur résultat positif sur cette série exigerait d'établir la publication d'abord.
5. **Le placebo par rotation n'est pas un placebo calendaire**, et le placebo jour-du-mois de la
   candidate CPI n'est pas un placebo par rotation. Chaque cellule n'a passé que le contrôle adapté à
   sa forme ; aucune n'a passé les deux.
6. **La candidate CPI n'est pas réfutée — elle est non testable avec le calendrier présent.** Ne pas
   lire « −1 » sur cette hypothèse : lire « bloquée sur N=65 ». Et ne pas la relancer sans avoir
   d'abord étendu le calendrier : re-tester le même angle sur les mêmes 65 événements serait du
   data-mining et déflaterait le DSR de tous les candidats suivants.
7. **Aucun contrôle de barres à fourchette nulle (L60) n'a été refait ici** : je m'appuie sur le
   diagnostic de `gross_surface_map` (XAUUSD 0.5 % de barres M1 à fourchette nulle, série propre).
   USDJPY n'y était pas isolé sur ce critère.
8. **Les coûts sont ceux de `COST_AUDIT.md`** (XAUUSD 1.84 mesuré, FX major 1.50 catalogue). La
   colonne `spread` du FX est zéro-inflée à 30 % sur USDJPY, donc **1.50 est probablement optimiste**.
   Les verdicts négatifs en sortent renforcés ; la candidate CPI, elle, a une marge de 20× et n'en
   dépend pas.
9. **241 cellules post-2021 ont été balayées. Aucun essai n'est encore consommé au sens du ledger** :
   ce dossier est N0. Le prix se paierait à la promotion de la candidate CPI en hypothèse.
10. **Les 5.4 ans post-2021 restent 5.4 ans.** Le contrôle pré-2021 est un contrôle d'époque, pas un
    walk-forward : il dit « le signe tient / ne tient pas ailleurs », jamais « ç'aurait été tradable
    en continu ». Il n'y a **aucun fold** dans ce document, sauf ceux déclarés impossibles.

---

## 9. Fichiers

| fichier | contenu |
|---|---|
| `cache_inventory.csv` | 19 séries exogènes : couverture réelle, fréquence, troncature, verdict |
| `cache_inventory_calendars.csv` | les 5 listes d'événements, couverture pré/post-2021 |
| `f1_held_all.csv` / `f1_held_legs.csv` | formulation 1, 179 cellules + 307 jambes disjointes |
| `f2_intraday_all.csv` | formulation 2, 200 cellules (dont 10 benchmarks inconditionnels) |
| `f2_hour_diagnostics.csv` | couverture de barres + ratio de fourchette par heure locale, 2 instruments |
| `robustness_battery.csv` | 7 cellules × {placebo apparié, L38, bootstrap blocs, WF, DSR, MDE} |
| `gold_carry_ledger.csv` | part du swap dans le gross, 36 cellules or |
| `gold_short_leg_inventory.csv` | les 29 jambes short or — la porte du portage |
| `gold_annual_cost_bill.csv` | facture annuelle vs détenir sans rien faire (397 bps/an) |
| `head_to_head_vs_unconditional.csv` | §5.3 |
| `calendar_tests.csv` | 97 cellules calendrier |
| `cpi_candidate.csv`, `cpi_by_year.csv`, `xauusd_day_of_month_profile.csv` | la candidate et ses contrôles |
| `gross_over_cost_ratio.csv` | §7, le chiffre de clôture |
| `code/` | `exog_lib` → `inventory` → `f1_held` / `f2_intraday` → `analysis` → `robust` / `cpi_candidate` |

Caches de session écrits hors dépôt (scratchpad privé). **Aucun blob data commité.**

---

## 10. Ce que ça réoriente

**FERMÉE** : chercher une sleeve dans les **séries macro exogènes gratuites du dépôt**, sur XAUUSD ou
USDJPY, au tarif CFD, en état continu (formulations 1 et 2). 165 cellules d'état, ratio médian 0.336
en intraday-flat, 0 au-dessus du gate, et la meilleure statistique de l'étude s'effondre sous son
propre placebo. Le kill est **MÉCANIQUE** au sens de la politique de ré-ouverture pour la jambe short
de l'or (gross ≈ 0 à coût nul) et **de COÛT** pour le reste.

**OUVERTE, et c'est la seule** : la famille **CALENDRIER**. C'est le seul endroit de cette étude où la
structure de coût est favorable par construction — 8 à 12 événements par an, donc un coût annuel
négligeable et un gross par trade grand. La candidate CPI-veille sur l'or y est bloquée sur la
**PUISSANCE**, pas sur le signal ni sur le coût, et le déblocage est gratuit : **étendre les dates de
publication CPI du BLS à 2007-2019**.

**Le résultat de premier ordre demandé est confirmé, avec une réserve.** « Les prédicteurs exogènes
gratuits n'ajoutent rien au-delà du prix » est **vrai pour les prédicteurs d'ÉTAT** — et le 0.336
contre 0.38 le dit sans ambiguïté. Ce n'est **pas** établi pour les prédicteurs d'**ÉVÉNEMENT** : la
famille calendrier n'a pas été fermée, elle a été trouvée sous-échantillonnée par un fichier
d'entrée qui commence en 2020. C'est exactement le motif que la politique de ré-ouverture décrit
pour pre-FOMC (« échantillon tronqué par un fichier d'entrée : 49 événements au lieu de 102
disponibles »). **Le même piège, une deuxième fois, sur un fichier différent.**
