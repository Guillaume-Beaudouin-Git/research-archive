# PRE-REGISTRATION — Overnight-drift block on CME futures (personal €13k IBKR account)

**Date de gel : 2026-07-30, avant toute mesure de performance.**
**Scope : `Multi_Asset/research/active/overnight_futures_2026-07/**` uniquement.**
**Interpréteur : `/usr/bin/python3`.**

---

## 0. Ce qui est déjà mesuré et n'est PAS re-découvert

Quatre sleeves « overnight-drift » long-only, mesurés sur **CFD retail** (Dukascopy/FTMO true-UTC M1),
archivés parce que le véhicule FTMO les tuait. Chiffres d'origine (source : `yt_strategy_replications/reports/`) :

| Sleeve | Instrument CFD | Fenêtre d'origine | N | Sharpe gross | t_HAC(α) | DSR | R² vs B&H | Skew |
|---|---|---|---|---|---|---|---|---|
| GOLD `ASIA_23_8` | XAUUSD | 23:00→07:00 UTC | 5 018 j | 1.10 net@1.5bp | **4.84** | 0.99 | 0.001 | +0.35 |
| SILVER | XAGUSD (post-2014) | 23:00→07:00 UTC | ~3 000 j | 1.45 | **4.55** | 1.00 | 0.000 | −0.14 |
| WTI | USOIL | 23:00→07:00 UTC | ~3 300 j | 1.09 | **3.64** | 0.94 | 0.002 | +0.43 |
| SOYBEAN | SOYBEAN | 01:00→07:00 UTC | 1 500 j | 1.32@1bp / 1.08@2bp | **4.60** | 0.75 | 0.27 | −1.9 |

**Cette étude ne re-teste pas le signal.** Elle teste **une seule chose** : le passage
*CFD retail → futures CME sur un compte personnel de €13 000*, c.-à-d. (a) l'horloge, (b) le coût,
(c) la matérialité du lot, (d) la diversification mutuelle réelle.

**Budget `n_tests`** : cette étude consomme **1 test par sleeve sur H1** (le contraste DST, qui est une
mesure neuve) = **4**, plus **1** pour le panier = **5**. Aucun balayage de fenêtre, aucune
ré-optimisation. Les fenêtres sont **héritées, jamais re-choisies**.

---

## 1. LE PIÈGE N°1 — mapping de session (H1), test décisif, à faire avant toute mesure de perf

### 1.1 Le fait mécanique

Les fenêtres d'origine sont **fixées en UTC**. Les contrats CME sont **fixés en heure d'échange**
(CT/ET), qui bascule à l'heure d'été américaine (2ᵉ dimanche de mars → 1er dimanche de novembre).
Donc **la fenêtre UTC glisse d'une heure par rapport au contrat deux fois par an.**

| | Réouverture Globex (heure d'échange) | UTC en **hiver** (US EST/CST) | UTC en **été** (US EDT/CDT) |
|---|---|---|---|
| GC / MGC, SI / SIL (COMEX) | 17:00 CT = 18:00 ET | **23:00 UTC** | **22:00 UTC** |
| CL / MCL (NYMEX) | 17:00 CT = 18:00 ET | **23:00 UTC** | **22:00 UTC** |
| ZS / MZS (CBOT ag) | 19:00 CT = 20:00 ET | **01:00 UTC** | **00:00 UTC** |
| Pause quotidienne (settlement) | 16:00–17:00 CT | 22:00–23:00 UTC | 21:00–22:00 UTC |

⇒ **L'entrée héritée tombe pile sur la réouverture en HIVER et une heure APRÈS en ÉTÉ**, pour les
quatre sleeves simultanément (le gold à 23:00 UTC, le soja à 01:00 UTC).

C'est décisif parce que la due-diligence gold rapporte elle-même : **« enter 1h late → Sharpe 0.37 »**
(contre 1.10). Et la due-diligence soja rapporte le pic à **01:00–02:00 UTC (+5.3 / +3.5 bp)** — la
première heure post-réouverture *d'hiver*.

### 1.2 Les deux mécanismes concurrents font des prédictions OPPOSÉES (L44)

- **H_asia — ancre UTC.** Le mécanisme revendiqué est la *demande physique asiatique* : Tokyo ouvre
  09:00 JST = **00:00 UTC toute l'année**, Shanghai 09:00 CST = **01:00 UTC toute l'année** (ni le
  Japon ni la Chine n'observent l'heure d'été). ⇒ **aucune dépendance DST**.
- **H_reopen — ancre heure d'échange.** Le mécanisme alternatif est le *re-hedging post-settlement /
  vide d'information de la pause*, ancré à 17:00/19:00 CT. ⇒ **la fenêtre héritée est alignée en
  hiver, décalée d'1h en été**, donc **été ≪ hiver** sous la spec héritée.

### 1.3 Test H1 — pré-enregistré

Pour chaque sleeve, sur la série CFD M1 → H1 canonique (`data/deep_history_utc/`, lecture seule) :

1. Indicateur `us_dst(date)` = heure d'été US (2ᵉ dim. mars 02:00 → 1er dim. nov. 02:00).
2. **Spec A (héritée)** : fenêtre fixe en UTC (23:00→07:00 ; soja 01:00→07:00).
3. **Spec B (horloge d'échange)** : **même fenêtre en heure d'échange** — c.-à-d. décalée de **−1 h en
   UTC pendant l'été US** (22:00→06:00 ; soja 00:00→06:00), inchangée en hiver.
   *Spec B n'est pas un nouveau paramètre : c'est la MÊME fenêtre, exprimée dans l'horloge du contrat.*
4. Mesures rapportées, séparément pour DST=été et DST=hiver, pour A et pour B :
   drift brut moyen (bp/jour), t_HAC(lag 6), Sharpe brut, N.
5. **Profil horaire** : rendement horaire moyen indexé (i) sur l'heure UTC, (ii) sur l'heure d'échange
   (ET), séparément été/hiver. La bonne ancre est celle qui **superpose** les deux profils.

**Règles de décision (figées) :**

- **D1 — l'ancre est l'horloge d'échange** si, en été, `Sharpe(B) − Sharpe(A) > 0` avec p < 0.10
  (bootstrap par blocs stationnaire apparié, Politis–Romano, moyenne de bloc 10 j, 5 000 tirages)
  **ET** le profil horaire se superpose mieux en heure d'échange qu'en UTC.
  ⇒ la spec futures devient **Spec B** et TOUTES les mesures aval l'utilisent.
- **D2 — l'ancre est UTC** si `Sharpe(A_été) ≈ Sharpe(A_hiver)` (écart non significatif à p<0.10) et
  B ne bat pas A en été. ⇒ la spec héritée tient telle quelle.
- **D3 — indéterminé / cassé** si aucune des deux specs ne produit un drift positif significatif dans
  l'un des deux régimes DST. ⇒ **le sleeve est déclaré non-transférable et l'étude s'arrête pour lui.**

**⚠ Garde-fou anti-victoire facile (pré-enregistré).** Spec B est *une* variante. Si B bat A **des
deux côtés du DST** (donc aussi en hiver, où B ≡ A par construction — impossible), ou si le gain de B
en été s'accompagne d'une **perte** en hiver, on conclut à du bruit, pas à une horloge. **Une seule
variante de spec est autorisée (A vs B). Aucune troisième.** (Lesson 10, budget de modifications.)

---

## 2. LE PIÈGE N°2 — validation L52 sur données futures réelles (H2)

**On ne fait confiance à aucun nom de champ.** Avant toute conclusion :

1. Télécharger `GC=F`, `SI=F`, `CL=F`, `ZS=F` en **barres horaires** (Yahoo, `interval=1h`,
   plage maximale ≈ 730 j), horodatage converti en UTC explicite depuis le fuseau déclaré par l'API.
2. **Vérification de calendrier** : histogramme des barres par heure UTC × régime DST. On DOIT
   observer un **trou d'exactement 1 h** à 22:00–23:00 UTC (hiver) / 21:00–22:00 UTC (été) pour
   GC/SI/CL, et un trou long 19:20→01:00 UTC (hiver) / 18:20→00:00 UTC (été) pour ZS.
   Si le trou n'est pas là où la théorie le met, **le mapping est faux et l'étude s'arrête**.
3. **Tick-match CFD ↔ futures** : sur la période de recouvrement, corrélation du rendement de fenêtre
   futures vs CFD, et différence de moyenne (bp/j).

**Règles de décision (figées) :**
- **K1** — si, pour un sleeve, > 10 % des jours n'ont pas de fenêtre complète sur le futures
  (barres manquantes) ⇒ **REJECTED (fenêtre inexistante sur le véhicule)**.
- **K2** — si `corr(window_ret_futures, window_ret_CFD) < 0.80` ⇒ le CFD n'est pas un proxy du
  contrat sur cette fenêtre ⇒ **REJECTED (proxy invalide)**, et on le dit sans chercher plus loin.
- **K3** — si le drift moyen mesuré sur le futures est **du signe opposé** au CFD sur la même période
  ⇒ REJECTED.
- L'échantillon futures (~730 j) est **explicitement sous-dimensionné pour un Sharpe** ; il sert de
  **contrôle de mapping et de proxy**, jamais de preuve de performance. Tout Sharpe futures est
  rapporté comme *indicatif, N insuffisant*.

---

## 3. Contraintes matérielles — L53 (H3), déjà relevées

Compte : **€13 000 × 1.1522 (EURUSD, `data/deep_history_utc/EURUSD_M1.csv`, 2026-06-05) = $14 980**
→ **arrondi à $15 000**. (Risque de change assumé, non couvert.)

Prix de référence : `data/raw/yf_*_1d_*.parquet`, dernier close 2026-07-08.

| Contrat | Taille | Prix réf. | **Notionnel** | Tick | Marge overnight | **% de $15 000** | **Notionnel / compte** |
|---|---|---|---|---|---|---|---|
| MGC micro or | 10 oz | 4 070.9 | **$40 709** | $1.00 | $2 308 | 15.4 % | **2.71×** |
| SIL micro argent | 1 000 oz | 58.16 | **$58 164** | $5.00 | $6 469 | 43.1 % | **3.88×** |
| MCL micro WTI | 100 bbl | 73.52 | **$7 352** | $1.00 | $840 | 5.6 % | **0.49×** |
| MZS micro soja | 500 bu | 1 195 c | **$5 975** | $0.625 | ~$210 | 1.4 % | **0.40×** |
| *PL platine (réf.)* | *50 oz* | *1 576.4* | *$78 820* | *$0.50* | *~9 % notionnel ≈ $7 094* | *47 %* | *5.25×* |

*(marges : `emini-watch.com` table live rafraîchie 2026-07-30 11:42 UTC, source déclarée
TradeStation/IBKR ; MZS depuis les specs CME micro-ag. Marges = variables, à re-vérifier avant tout
ordre. Aucune remise intraday supposée : la fenêtre ne traverse pas le settlement 17:00 ET mais on
prend la marge pleine, conservateur.)*

**Règles de décision (figées) :**
- **M1 — marge** : un sleeve seul dont la marge > **35 %** du compte est **REJECTED (matériel)**.
  Un panier dont la somme des marges > **60 %** est rejeté comme panier.
- **M2 — granularité / notionnel** : le lot minimum impose un notionnel plancher. Le sleeve
  d'origine tourne à ~1.05× de son notionnel pour ~6.5–9.6 % de vol annualisée. Si
  `notionnel/compte > 3.0×`, la vol et le MaxDD du sleeve sont multipliés d'autant ⇒ **REJECTED
  (granularité)** : on ne peut pas descendre sous un contrat.
- **M3** : le vol-targeting continu de la recherche devient **entier** (0 ou 1 contrat) sur futures.
  L'implémentation entière est mesurée **explicitement** et rapportée à côté de la version continue.
  L'écart continu→entier est un coût de véhicule, pas une modification de stratégie.

---

## 4. Coûts futures réels (H4) — modèle figé AVANT mesure

Coût aller-retour = **1 tick de spread bid-ask** (crossé une fois par aller-retour) **+ commission
aller-retour**. Commission IBKR retail *fixed* : **$0.85 par contrat et par côté**, tout compris
(exécution + frais d'échange + réglementaire) ⇒ **$1.70 RT**. Sensibilité rapportée à $0.50/côté
(tiered, gros volume) et à **2 ticks** de spread (réouverture illiquide).

| Contrat | 1 tick (bps) | Comm. RT (bps) | **RT base (bps)** | RT stress (2 ticks) | Break-even publié |
|---|---|---|---|---|---|
| MGC | 0.246 | 0.418 | **0.66** | 0.91 | — (gold net@1.5bp = 1.10) |
| SIL | 0.860 | 0.292 | **1.15** | 2.01 | 5.3 bps |
| MCL | 1.360 | 0.231 | **1.59** | 2.95 | **3.5 bps** |
| MZS | 1.046 | 0.285 | **1.33** | 2.38 | **~2 bps** (Sharpe>1) |

*(chiffres calculés à la main dans cette pré-registration à partir des notionnels du §3 ; ils seront
recalculés par le code et toute divergence sera signalée.)*

**Règle de décision (figée) — K4 :** un sleeve dont le **coût RT base > break-even publié** est
**REJECTED (coût)** sans backtest supplémentaire. Un sleeve dont le coût RT **stress** dépasse le
break-even est au mieux **UNDERPOWERED**.

⚠ **Hypothèse fragile explicitement nommée** : « 1 tick de large » à la réouverture Globex. MZS
(micro-ag, lancé 2022, volume faible) et MCL à 23:00 UTC sont les deux plus douteux. Le stress 2 ticks
est donc le scénario de référence pour ces deux-là.

---

## 5. Métrique de décision (H5) — compte personnel, pas de propfirm

Il n'y a **ni barrière, ni horloge, ni frais de challenge**. On rapporte donc, par sleeve et par panier :

- **Sharpe net** de coûts futures réels, annualisé par **√(obs/an) mesuré empiriquement** (L47),
  jamais √252 en dur.
- **t_HAC (Newey-West lag 6)** de la moyenne nette, et **DSR** (`engine/stats.py`, calibré) avec
  `n_trials` = 5 (le budget de cette étude) *en plus* des essais d'origine.
- **Croissance annualisée géométrique** et rappel `g ≈ SR²/2` (mémoire growth-law 2026-07).
- **MaxDD** (sur la série nette, à la taille réellement implémentable en lots entiers).
- **Sizing Kelly fractionnaire ¼ et ½** : `f* = μ/σ²` sur les rendements nets du sleeve, converti en
  nombre de contrats sur $15 000, puis **arrondi à l'entier** — et on rapporte l'écart.
- **Bootstrap par blocs stationnaire partout** (Politis–Romano, moyenne de bloc 10 j, 5 000 tirages).
  **Aucun bootstrap iid.**

**Seuils (figés) :**
- **PASS** : Sharpe net ≥ **0.70**, t_HAC ≥ 2.5, DSR ≥ 0.50, **et** M1+M2 satisfaits, **et** K1–K4 passés.
- **UNDERPOWERED** : signal présent (t_HAC ≥ 2.0) mais bute sur le coût stress, la granularité, ou
  N insuffisant.
- **REJECTED** : n'importe quelle règle K ou M déclenchée, ou Sharpe net < 0.40.

---

## 6. Corrélation mutuelle (H6) — panier interdit avant mesure

L'audit d'origine donne déjà **corr moyenne 0.26, PC1 = 45 %, ≈2.5 paris effectifs sur 4**, et
gold↔silver **0.57**. L'inventaire signale par ailleurs MGC↔SIL **0.86 en janvier**.

Test : matrice de corrélation des **quatre séries nettes de sleeve, sur leurs jours actifs communs**,
plus PCA (part de PC1) et **nombre de paris effectifs** `N_eff = (Σλ)² / Σλ²`.

**Règle de décision (figée) — P1 :** aucun panier n'est proposé si `N_eff < 2.0`, ou si une paire
retenue a `corr > 0.50` (US30/GER40 à 0.54 a *réduit* le t en pooling — précédent gravé). Un panier
n'est recommandé que si **au moins deux sleeves passent PASS individuellement** et que leur corrélation
mutuelle est **< 0.35**. Sinon on dit : *il n'existe pas de panier défendable*, et on s'arrête là.

---

## 7. Kill rules globales — ordre d'exécution

L'ordre est **véhicule d'abord** (L53), puis horloge, puis coût, puis performance :

```
Étape 0  L53 matériel (M1, M2)          -> élimine sans mesurer
Étape 1  H1 mapping de session (D1/D2/D3) -> fixe la spec
Étape 2  H2 validation futures (K1,K2,K3) -> valide le proxy
Étape 3  H4 coût (K4)                     -> élimine sans backtest
Étape 4  H5 performance nette             -> chiffre ce qui reste
Étape 5  H6 corrélation / panier (P1)     -> panier seulement si défendable
```

Un sleeve éliminé à l'étape *n* **n'est pas mesuré aux étapes suivantes** — et son verdict est
rapporté avec l'étape qui l'a tué.

**Scepticisme pré-engagé.** Si un sleeve paraît **meilleur en futures qu'en CFD**, la première
hypothèse retenue est une **erreur de session** (fenêtre décalée capturant un gap de réouverture,
barre manquante comptée comme rendement nul, ou horodatage mal converti), pas une victoire. Il faudra
un tick-match explicite avant d'écrire quoi que ce soit de positif.

---

## 8. Ce qui n'est PAS dans le périmètre

- Le bloc **saisonnalité précieux-Q1** (or/argent/platine janvier) : famille différente, non traitée
  ici. Seule remarque de véhicule reportée : **PL = 50 oz, $78 820 de notionnel, 5.25× le compte** ⇒
  matériellement mort à €13 000, ce qui réduit « précieux-Q1 » à or+argent (corr 0.86 en janvier).
- Aucune modification des fenêtres autre que le contraste A/B du §1.
- Aucun commit, aucun accès SSH, aucune écriture hors de ce répertoire.
