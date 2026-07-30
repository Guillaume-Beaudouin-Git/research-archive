# PRÉ-ENREGISTREMENT — Cycle d'adjudication du Trésor US (concession d'adjudication)

> **Gelé le 2026-07-30, AVANT tout calcul de rendement.**
> Item `E020` de `Multi_Asset/research/active/edge_inventory_2026-07/INVENTORY.md` —
> le seul de la shortlist qui produise de l'information neuve, et donc **le seul qui
> consomme du `n_tests`**.
>
> **Contribution à `n_tests` : +1 hypothèse, 16 cellules déclarées** (ledger §7).
> Aucun chiffre de rendement n'a été produit avant l'écriture de ce fichier. Les seuls
> objets consultés avant gel sont : la fiche B1, le rapport véhicule month-end, l'inventaire,
> l'API TreasuryDirect (structure de champs uniquement), et le *shape* des parquets prix.

---

## 1. Hypothèse et mécanisme

**Mécanisme (Lou, Yan & Zhang 2013, RFS 26(8), « Anticipated and Repeated Shocks in
Liquid Markets »).** Les *primary dealers* sont contractuellement tenus de soumissionner
à chaque adjudication du Trésor. Ils doivent donc absorber, à date connue, un stock de
papier neuf sur un bilan à capacité limitée. Pour se pré-couvrir, ils vendent le secteur
concerné **avant** l'émission — la « concession d'adjudication » — puis la pression
disparaît une fois le papier alloué et distribué, et le prix **récupère**.

C'est **la même famille que B1** : un flux **contraint** (obligation réglementaire de
soumissionner, comme l'obligation de rebalancement des fonds), **daté publiquement**
(calendrier annoncé ~7 jours à l'avance), sur **le même complexe d'instruments**
(Treasury) et le **même véhicule** (ZN sur IBKR, marge ~$1 800).

**Prédiction directionnelle, figée :**

| Jambe | Fenêtre (jours de bourse) | Position | Signe attendu du P&L |
|---|---|---|---|
| **PRE** (concession) | `close(t−3)` → `close(t−1)` | **SHORT ZN** | positif (le prix baisse) |
| **POST** (reprise) | `close(t−1)` → `close(t+2)` | **LONG ZN** | positif (le prix remonte) |

`t` = jour de l'adjudication (l'enchère ferme à 13:00 ET ; le settlement daily ZN est
15:00 ET, donc `close(t)` est **post-adjudication**).

**Stratégie primaire `S_V`** = PRE + POST enchaînées (« vendre la concession, acheter la
reprise »). Un événement = un aller-retour short suivi d'un aller-retour long, soit un
retournement de position à `close(t−1)`.

**Aucune inversion de signe post-hoc ne sera acceptée** (kill-rule K5). Si le signe mesuré
est l'inverse du mécanisme, le dossier est REJECTED, pas « re-spécifié ».

---

## 2. LE PIÈGE N°1 — redondance avec B1, tranché EN PREMIER

Le calendrier du Trésor est **régulier par maturité** et une partie de ce calendrier tombe
mécaniquement dans la fenêtre B1 (3 derniers jours de bourse du mois) :

- **2y / 5y / 7y notes** : adjugées dans la **dernière semaine du mois**, règlement le
  dernier jour calendaire du mois. → **recouvrement attendu ÉLEVÉ avec B1.**
- **3y / 10y / 30y (refunding + reopenings)** : adjugées **mi-mois** (~jours 9-13),
  règlement le 15. → **recouvrement attendu QUASI-NUL avec B1.**

Ceci n'est pas une découverte issue des données : c'est la structure institutionnelle
publique du cycle, connue avant gel. Elle **dicte la spécification primaire**.

### Test 0 — obligatoire, avant tout le reste (3 sous-tests)

- **T0.a — Recouvrement calendaire.** Pour chaque cluster, fraction des jours de position
  `S_V` (t−3 … t+2) qui tombent dans la fenêtre B1 (3 derniers jours de bourse du mois).
- **T0.b — Corrélation des rendements.** `corr(r_B1_daily, r_auction_daily)` sur la série
  quotidienne complète, **et** sur l'union des jours actifs des deux sleeves.
- **T0.c — Effet résiduel hors B1.** Ré-estimation de `S_V` en **retirant** tout événement
  dont la fenêtre intersecte la fenêtre B1.

**Verdict de redondance (K1)** : si recouvrement ≥ 50 % **et** l'effet résiduel hors-B1
est non significatif (`|t| < 2.0`), le dossier est **REJECTED — REDUNDANT**, on l'écrit et
**on s'arrête**. Le repo a déjà payé ce piège deux fois (US30/GER40 ρ 0.54 où le pooling
*baisse* le t ; MGC/SIL ρ 0.86 en janvier).

**Conséquence sur la spécification primaire.** Parce que le recouvrement est *structurellement*
nul pour le cluster mi-mois, la **cellule primaire est le 10-year note sur ZN** — c'est
simultanément le test le plus propre du mécanisme (maturité du contrat = maturité adjugée)
et le test le moins contaminé par B1. Le cluster 2/5/7 (month-end) est **secondaire et
suspect par construction**.

---

## 3. LE PIÈGE N°2 — sessions et champs (L51/L52, `month_end_vehicle_2026-07`)

Acquis mesurés, non ré-hypothéqués ici :

- La session CME de ZN va de **18:00 ET (J−1) à 17:00 ET (J)**.
- `ZN=F.Open` (yfinance) = **ouverture Globex 18:00 ET du jour PRÉCÉDENT** (71.6 % exact au tick).
- `ZN=F.Close` = **settlement 15:00 ET** (médiane 1 tick).

**Conséquences figées pour cette étude :**

1. **Tous les rendements sont `Close`→`Close`.** Le champ `Open` de ZN=F est
   **interdit d'usage** dans toute mesure de cette étude. Aucune décomposition
   intraday/overnight ne sera faite à partir du daily.
2. L'adjudication ferme à **13:00 ET**, soit **2 h avant le settlement daily**. Le daily
   **ne peut pas** séparer le pré- du post-adjudication à l'intérieur du jour `t`.
   → Toute affirmation « avant/après 13:00 » exige l'**horaire** (`data/raw/ZN_1h_cache.parquet`,
   2024-07→2025-12 ET ; `month_end_vehicle/data/h1_ZNF.parquet`, 2024-03→2026-07 UTC).
   Cette décomposition est **descriptive et hors-décision** (N ≈ 25 événements → aucune
   puissance) et sera étiquetée comme telle.
3. Le jour `t` est **exclu de la décision primaire** en tant que jambe isolée, précisément
   parce que son contenu est ambigu (concession matinale + reprise post-13:00 mélangées).
   Il est absorbé dans la jambe POST qui démarre à `close(t−1)`.

---

## 4. Données

### 4.1 Calendrier d'adjudication — source et validation
- **Source : API TreasuryDirect publique et gratuite**
  `https://www.treasurydirect.gov/TA_WS/securities/auctioned?format=json&type=<Note|Bond>`
  Champs utilisés : `auctionDate`, `announcementDate`, `securityType`, `securityTerm`,
  `offeringAmount`, `bidToCoverRatio`, `cusip`, `issueDate`.
- **Pas de source payante.** Aucune reconstruction par règle calendaire n'est nécessaire
  puisque l'historique réel est public.
- **Validation obligatoire avant usage** : (a) couverture annuelle (nombre d'adjudications
  10y par an ≈ 12, jamais 0) ; (b) cohérence `announcementDate < auctionDate < issueDate` ;
  (c) tous les `auctionDate` tombent un jour de bourse ; (d) contrôle visuel de la
  distribution du jour-du-mois par maturité contre la structure institutionnelle décrite
  au §2. Un échec ⇒ le calendrier est déclaré non fiable et l'étude s'arrête.

### 4.2 Prix
- `Multi_Asset/research/active/month_end_vehicle_2026-07/data/daily_{ZNF,ZBF,ZFF,TLT,IEF}.parquet`
  (lecture seule, yfinance `ZN=F` / `ZB=F` / `ZF=F`, 2000-09 → 2026-07).
- `data/raw/ZN_1h_cache.parquet` + `month_end_vehicle/data/h1_ZNF.parquet` (horaire, descriptif).
- Aucune re-fetch de prix : on réutilise les caches déjà validés au tick par l'étude véhicule.

### 4.3 Rendements excédentaires
Un future **entièrement collatéralisé** a un rendement de prix qui **est** un rendement
excédentaire (le collatéral rapporte le taux sans risque). Aucune soustraction de DTB3
n'est appliquée sur ZN/ZB/ZF, et c'est **explicitement** la raison. TLT/IEF ne sont pas
utilisés pour la décision.

---

## 5. Protocole statistique (figé)

- **Signal à T−1, trade à T.** Le calendrier est public ~7 jours à l'avance ; contrôle
  **explicite et fail-loud** : tout événement pour lequel `announcementDate > date(t−3)`
  est **exclu** de l'échantillon primaire (l'information n'était pas disponible à l'entrée).
  Le nombre d'exclusions est rapporté.
- **Rendements log**, en bps.
- **Significativité** : t-stat **HAC Newey-West lag 6** sur la régression du rendement
  d'événement sur une constante.
- **Bootstrap par blocs** (Politis-Romano stationnaire / circulaire, bloc moyen = 3
  événements, 40 000 tirages). **iid interdit** — les événements se regroupent en régimes
  de taux.
- **Placebo calendaire apparié (L49) — obligatoire.** Pour chaque événement réel, le pool
  de placebos est constitué des jours de bourse qui (i) ont le **même jour de semaine**,
  (ii) ont un **jour-du-mois à ±3 jours calendaires**, (iii) sont dans une **année
  différente**, et (iv) ne sont **pas** à moins de 3 jours de bourse d'une adjudication de
  coupon du même secteur. 2 000 calendriers placebo complets sont tirés ; on compare l'effet
  réel à la **médiane et au p95** de la distribution placebo. C'est le test qui a tué la
  famille unlock (L49).
- **Two-sided (L25)** : les deux jambes (PRE short, POST long) doivent être
  **individuellement positives**. Si seule la jambe POST fonctionne, c'est de la dérive
  obligataire (beta), pas un flux — le dossier tombe. Contrôle additionnel : chaque jambe
  est aussi rapportée **demeaned** (rendement d'événement moins le drift moyen de ZN ×
  nombre de jours de la jambe, calculé **within-régime**).
- **Split de régime (L31)** — découpage **non arbitraire**, fixé avant mesure :
  - **QE / ZIRP : 2008-12-16 → 2021-12-31** (de la première ZIRP à la fin des achats nets
    du Fed). Le Fed achetait le papier — la capacité de bilan des dealers n'était pas la
    contrainte marginale ⇒ mécanisme *a priori* affaibli.
  - **Pré-QE : 2000-09 → 2008-12-15** et **Normalisation/QT : 2022-01-01 → 2026-07**
    (hausse rapide, QT, déficits records ⇒ mécanisme *a priori* renforcé).
- **DSR (Bailey-López de Prado)** : `n_trials = 16` (ledger §7). `std_sr_trials` est
  **mesuré** comme l'écart-type transversal des Sharpe annualisés des 16 cellules
  effectivement calculées, et **déclaré** dans RESULTS.md. Pas de σ implicite (l'audit
  oxfordstrat a montré qu'un σ mal posé invalide le gate — INVENTORY §3.1).
- **Annualisation (L47)** : `√(obs/an)`. Le sleeve tire ~12 événements/an ⇒ le Sharpe
  par événement s'annualise en `√12`. La série **quotidienne** (rendement les jours en
  position, 0 sinon) s'annualise en `√252` et c'est **elle** qui alimente
  `Portfolio/admission/marginal.py`.

---

## 6. Coûts — futures réels, en ticks et en dollars

ZN : contrat 100 000 $ de nominal ; 1 point = 1 000 $ ; **1 tick = 1/64 de point = 15,625 $** ;
nominal ≈ 110 000 $ au prix 110.

| Poste | Central | Stress |
|---|---|---|
| Slippage par côté | 0,5 tick = 7,81 $ | 1,0 tick = 15,63 $ |
| Commission all-in par aller-retour (IBKR + frais exch./reg.) | 2,30 $ | 2,30 $ |
| **Coût par aller-retour** | **17,93 $ ≈ 1,63 bps** | **33,55 $ ≈ 3,05 bps** |
| **Coût par événement `S_V`** (2 A/R : short puis long) | **≈ 3,3 bps** | **≈ 6,1 bps** |

**Gate de coût (K4)** : brut par événement ≥ **3 × coût central = 9,8 bps**.
Rapport également au coût de stress (gate = 18,3 bps).

**Effet minimal détectable (MDE), calculé avant mesure.** Vol quotidienne ZN ≈ 30 bps ⇒
vol d'un aller-retour de 3 jours ≈ 52 bps, d'une fenêtre `S_V` de 5 jours ≈ 67 bps.
À N ≈ 300 événements, `SE ≈ 67/√300 ≈ 3,9 bps` ⇒ **MDE(t=2,5) ≈ 9,7 bps/événement**.
La MDE et le gate de coût coïncident à ~1 bps près : **cette étude n'a pas la puissance de
distinguer un edge marginal d'un zéro** — tout résultat entre 0 et ~10 bps sera déclaré
**UNDERPOWERED**, pas PASS.

---

## 7. Ledger des cellules déclarées (`n_trials = 16` pour le DSR)

| # | Cellule | Rôle |
|---|---|---|
| 1 | `S_V` — 10y sur ZN, échantillon complet | **PRIMAIRE** |
| 2 | jambe PRE seule — 10y/ZN | diagnostic L25 |
| 3 | jambe POST seule — 10y/ZN | diagnostic L25 |
| 4 | `S_V` — 10y/ZN, **hors événements chevauchant B1** | T0.c |
| 5 | `S_V` — cluster month-end 2y/5y/7y sur ZN | secondaire (suspect B1) |
| 6 | `S_V` — 30y sur ZB | secondaire (transfert de maturité) |
| 7 | `S_V` — 3y sur ZF | secondaire (transfert de maturité) |
| 8 | `S_V` — 10y/ZN, régime **pré-QE** 2000-2008 | L31 |
| 9 | `S_V` — 10y/ZN, régime **QE/ZIRP** 2009-2021 | L31 |
| 10 | `S_V` — 10y/ZN, régime **QT** 2022-2026 | L31 |
| 11-13 | `S_V` — fenêtre PRE à k ∈ {2, 4, 5} jours (k = 3 est la primaire) | robustesse |
| 14-16 | `S_V` — fenêtre POST à m ∈ {1, 3, 4} jours (m = 2 est la primaire) | robustesse |

Toute cellule non listée ici et calculée quand même sera **signalée comme exploratoire**
dans RESULTS.md et exclue des conclusions.

---

## 8. Kill rules (verdict mécanique, décidé avant mesure)

| # | Règle | Déclenchement | Verdict |
|---|---|---|---|
| **K1** | **Redondance B1** | recouvrement ≥ 50 % **et** `|t|` résiduel hors-B1 < 2,0 | **REJECTED — REDUNDANT**, arrêt immédiat |
| **K2** | **Placebo apparié (L49)** | effet réel ≤ **p95** de la distribution placebo appariée | **REJECTED** |
| **K3** | **Régime (L31)** | effet porté par un seul régime **et** `\|t\| < 1,5` dans les deux autres | **REJECTED — REGIME ARTEFACT** |
| **K4** | **Coût** | brut/événement < 3 × coût central (9,8 bps) | **REJECTED — COST-DEAD** |
| **K5** | **Signe (mécanisme)** | signe opposé à la prédiction §1 sur la jambe primaire | **REJECTED** (pas de re-spécification) |
| **K6** | **Two-sided (L25)** | une des deux jambes négative **après demean** | **REJECTED — BETA** |
| **K7** | **Roll de contrat** | l'effet disparaît en excluant les semaines de roll ZN (fin fév./mai/août/nov.) | **REJECTED — ARTEFACT** |
| **K8** | **Marge (admission)** | `ΔSR ≤ 0` au poids ERC, **ou** IC bootstrap de `ΔSR` contenant 0 | **UNDERPOWERED** (jamais PASS) |
| **K9** | **DSR** | `DSR < 0,95` avec `n_trials = 16` et `std_sr_trials` mesuré | **REJECTED — MULTIPLE TESTING** |

**Règle de scepticisme explicite.** Un flux calendaire régulier, public et connu depuis 45 ans
est *a priori* arbitragé. Si l'effet mesuré est **large et propre** (> 25 bps/événement,
`t > 5`), la première hypothèse à écarter n'est pas « edge » mais **artefact** : roll de
contrat (K7), chevauchement B1 (K1), ou stitching de la série continue yfinance. Un tel
résultat déclenche un audit d'artefact **avant** toute conclusion positive.

---

## 9. Métrique de décision (compte personnel — ni barrière, ni horloge)

Le véhicule est **ZN sur IBKR** : marge ~1 800 $ ≈ 14 % d'un compte de 13 k€, pas de
barrière journalière, pas d'horloge de challenge. La décision se prend donc sur :

1. **Croissance annualisée** et **Sharpe net** du sleeve seul (annualisation L47).
2. **MaxDD** de la courbe de P&L par événement.
3. **Sizing Kelly fractionnaire** (¼ et ½ Kelly) sur 13 k€, contraint par la granularité
   d'**1 contrat ZN minimum** (le notionnel, pas la marge, est le vrai plafond — même
   diagnostic que MGC dans l'inventaire).
4. **Δ apporté au book existant** = B1 implémenté sur ZN, via
   `Portfolio/admission/marginal.py::admit` (poids ERC, bootstrap stationnaire par blocs,
   `n_trials` déclaré) → `ΔSR`, son IC, et l'**effet minimum détectable**.

**Un `ΔSR` positif dans le bruit est UNDERPOWERED, pas PASS.** (K8)

---

## 10. Verdicts possibles

- **PASS** — toutes les kill rules franchies, `ΔSR > 0` avec IC excluant 0, DSR ≥ 0,95.
- **UNDERPOWERED** — signe correct, mécanisme cohérent, mais effet indistinguable de zéro
  à la puissance disponible. Le dossier est documenté et **fermé sans déploiement**.
- **REJECTED** — au moins une kill rule déclenchée. Motif nommé.

---

*Figé 2026-07-30. Interpréteur : `/usr/bin/python3`. Aucun commit.*
