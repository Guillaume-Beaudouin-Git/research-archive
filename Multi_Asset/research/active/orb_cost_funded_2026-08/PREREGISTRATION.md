# PRÉ-ENREGISTREMENT — Coût réel de l'ORB funded + sizing funded (P0/P1)

**Gelé le 2026-08-12, AVANT tout accès aux données de mesure.** Rédigé par le MD, exécuté par 4 volets indépendants.

## 0. Contexte et déclencheur

Le compte P2 a atteint sa cible le 2026-08-12. La bascule funded applique `CFG_FUNDED`
(`vm 1.0`, `on_w 0.35`, **`orb_risk 0.0025` → l'ORB s'allume comme sleeve de P&L**).

Deux faits motivent ce travail :

1. **P1 — le paramètre de coût de l'ORB n'a jamais été mesuré.** `config_v22.py:22` porte
   `ORB_RT_BPS = "era"` avec une procédure de verdict pré-enregistrée (N=60 fills actifs
   16:00-16:30, échéance 2026-06-15) **jamais exécutée**. Le ledger de branches
   (`spec_v22.yaml:137-151`) chiffre l'ORB à 0.61 / 1.0 / 1.5 bps et `era` — or l'ancre de coût
   de la même spec donne **US100 RT = 2.2 bps**, hors grille du côté pessimiste. L'ORB pèse
   `funded_oos_2y` **2632 avec** contre **1262 sans** : plus de la moitié de la valeur funded.

2. **Le ledger est idéalisé sur SES DEUX JAMBES** (constaté 2026-08-12 sur
   `nq_v2_trades.parquet`, N=4013, 2010-06→2026-05) :
   - `entry == level` **exactement, 4013/4013** ;
   - `exit_px == stop_eff` **exactement, 1590/1590** des sorties STOP (39.6 % des trades).

   C'est la signature exacte de **L59**. Le modèle de coût actuel est un **haircut plat et
   symétrique** (`r = r_gross − ORB_RT_BPS × 1e-4 × lev + 0.015`) alors que la structure réelle
   d'un système stop-entry / stop-exit est **asymétrique et pilotée par les gaps**.

**Sensibilité de référence, calculée avant mesure** : `lev = entry/|entry − stop_eff|`, médiane
**195** ⇒ **1 bps de RT = 0.0195 R**. `r_gross` moyen = **+0.0492 R**. Le ledger lui-même donne
+0.0267 R à 1 bps, +0.0042 à 2 bps, **−0.0182 à 3 bps**. **La frontière de mort est entre 2 et 3
bps**, ce qui reproduit indépendamment le « 3 bps » déjà gravé pour la famille ORB.

## 1. Hypothèses testées

- **H1 (entrée)** — un ordre stop d'entrée ne se remplit pas au niveau déclencheur. Mesurer la
  distribution du fill réaliste et son coût en R.
- **H2 (sortie, L59)** — une part matérielle des barres de stop **ouvre au-delà du stop**. Mesurer
  cette part et l'ampleur, re-pricer, et rapporter l'effet sur le R moyen et le Sharpe.
- **H3 (spread)** — le 2.2 bps est un défaut codé en dur, pas une mesure ; le coût de spread réel
  d'US100.cash diffère, et diffère **entre l'entrée (16:00-16:30) et la sortie (stop intraday /
  time-stop 22:00)**.
- **H4 (véhicule, L33)** — le ledger est construit sur des prix **NQ futures** alors que
  l'exécution se fait sur **US100.cash CFD**. Documenter l'écart de structure de coût et de
  granularité, et dire explicitement ce qui transfère et ce qui ne transfère pas.
- **H5 (sizing funded, P0)** — le vm funded optimal n'est pas 1.0. Deux études antérieures
  concluent zone **[0.80-0.90]** mais **régime-dépendante** ; une troisième indique que le tail
  intra-barre au funded vm1 est **4.7-10× pire** que la sim M5-close.

## 2. Devise commune — OBLIGATOIRE

Tout effet de coût est rapporté dans **les trois unités** : (i) points d'indice, (ii) **bps de
prix**, (iii) **R** via `lev = entry/|entry − stop_eff|` du trade concerné. Toute moyenne de R est
accompagnée de **N**, d'un **t HAC lag-6**, et d'un **IC par block bootstrap** (Politis-Romano —
iid interdit). Aucun chiffre agrégé sans N.

## 3. Règles de kill — GELÉES

Soit `R_net` la série de R par trade après re-pricing L59-conforme **et** au coût de spread
mesuré, sur les 4013 trades.

- **R1 — ORB_KILL** si `mean(R_net) ≤ 0` sur l'échantillon complet.
- **R2 — ORB_KILL** si `mean(R_net) > 0` mais **t HAC ≤ 2.0**, ou si l'IC bootstrap à 95 % contient 0.
- **R3 — ORB_UNDERPOWERED** (ni keep ni kill) si R1 et R2 passent mais que la **valeur funded avec
  ORB** n'excède pas la valeur **sans ORB** au-delà de la bande bootstrap appariée.
- **R4 — ORB_KEEP** seulement si R1, R2, R3 sont tous franchis **et** que le résultat tient
  hors-échantillon sur un split ≥5 folds (walk-forward expanding, hard rule projet).
- **R5** — DSR obligatoire (`n_mod ≥ 2`), avec la version corrigée de `dsr.py` (défaut `rf = 0.0`).

**Aucune de ces règles ne se renégocie après avoir vu les chiffres.** Un résultat qui déplaît se
publie tel quel.

## 4. Ce qui n'est PAS en jeu ici

Le budget de 3 modifications de la stratégie n'est **pas** entamé : ce travail **mesure un coût**
et **re-price un ledger existant**, il ne modifie aucun signal. Aucun paramètre de signal (OR
window, stop, trail-to-BE, time-stop) ne doit être touché, optimisé ou balayé. Toute proposition
de ce type est hors périmètre et doit être remontée, pas exécutée.

## 5. Volets

| Volet | Question | Dossier |
|---|---|---|
| A | H1 — coût d'**entrée** mesuré sur M1 réel | `entry_cost/` |
| B | H2 — coût de **sortie**, re-pricing L59 | `exit_cost/` |
| C | H3 + H4 — **spread** réel entrée vs sortie, et véhicule NQ→CFD | `spread_measure/` |
| D | H5 — **sweep vm funded** × grille de coût ORB | `funded_vm/` |

Le volet D est conçu pour être **indépendant** des volets A-C : il produit une table 2-D
(vm × ORB_RT_BPS) dans laquelle la valeur mesurée se branche à la fin. Aucun volet n'attend
un autre.

## 6. Garde-fous d'exécution

- Écriture **uniquement** dans le sous-dossier du volet. Interdiction d'écrire dans
  `ftmo_live/`, `Portfolio/`, `strategies/`, `data/raw/`, `data/ftmo_portfolio/v22/`,
  `audit_v2_independent/cleanroom/`, ou le dossier d'un autre volet.
- **Aucune commande git.**
- Interpréteur `/usr/bin/python3`.
- Les caches sous `data/ftmo_portfolio/cache/` et `data/raw/` sont **lecture seule**.
- La colonne `spread` de `data/deep_history_utc/` est **inutilisable seule** (massivement
  non peuplée, sous-estime le RT FTMO réel d'environ 2.4×). Ne pas l'employer comme mesure de coût.
- Vérifier le fuseau **avant** toute découpe horaire (L52/L56 : ne jamais faire confiance au nom
  d'un champ ; corréler les profils hiver/été si un doute subsiste).

---

# AMENDEMENT n°1 — 2026-08-21

**Statut du sleeve ORB en production : ARMÉ** (`FU_ORB_RISK = 0.0025`, compte funded <ACCOUNT_ID>
depuis le 2026-08-17), **alors que le verdict pré-enregistré est `ORB_KILL`.**

Cet amendement existe parce que l'écart n'était documenté nulle part. Un audit indépendant
(2026-08-21) a relu `RESULTS.md`, retrouvé `ORB_KILL`, et classé la contradiction comme
**priorité opérationnelle n°1** — preuve que le dépôt tendait un piège à quiconque le lit.

## 1. Ce qui a changé dans les FAITS

**L'entrée de coût de R2 était mesurée sur le mauvais véhicule.** Le `1.80 bps RT` provient de
`cache/US100_daily_cet.parquet`, c'est-à-dire d'**un autre broker**, appliqué à une stratégie
exécutée chez FTMO. C'est la violation que **L33** interdit explicitement.

Mesure **native FTMO** depuis le 2026-08-17 (`spread_log_202608.csv`, échantillonneur passif
embarqué dans l'EA, >13 000 lignes, n≈3 280 par symbole sur 3 séances) :

| | US100 RT |
|---|---|
| médiane toutes heures | **1.045 bps** |
| **fenêtre ORB (15:30-16:05 Paris)** | **0.962 – 0.982 bps** |
| ancienne entrée de R2 | 1.80 bps |
| constante codée en dur du pipeline | 2.20 bps |

## 2. Ce que ça change au verdict — ET CE QUE ÇA NE CHANGE PAS

Le tableau pré-enregistré (`RESULTS.md` §1) donne, à la ligne **0.94 bps** :

> mean R **+0.02805** · **t HAC(6) = 1.56** · IC95 block-bootstrap **[−0.0070, +0.0629]**

⇒ Le t passe de **0.48 à 1.56**. C'est un mouvement considérable. **Mais R2 exige t > 2.0, et
l'IC95 contient encore zéro.**

> ## **R2 TIRE TOUJOURS. LE VERDICT `ORB_KILL` TIENT DANS SES TERMES PRÉ-ENREGISTRÉS.**

⚠ **Ce qui ferait passer l'ORB — et qui est REFUSÉ ici.** Sur le sous-échantillon **2018-2026**,
t = 2.58, IC [+0.017, +0.102], walk-forward 5/5. Ce sous-échantillon a été **choisi après avoir
constaté qu'il fonctionnait**. L'invoquer serait de la sélection post hoc. **Il est consigné, il
n'est PAS une justification**, et aucune décision ne s'y appuie.

## 3. Pourquoi le sleeve est néanmoins ARMÉ — dérogation explicite

Le maintien n'est **pas** une réhabilitation. C'est une **dérogation opérationnelle assumée**, sur
trois motifs chiffrés :

1. **Le coût d'avoir tort est borné et proche de zéro.** Risque **$25/trade** (0.25 % taperisé).
   Au coût tout-compris mesuré (~2.17 bps, n=12), le ledger de sensibilité donne
   **≈ +0.000 R/trade** — ni gagnant ni perdant. Le sleeve n'est pas *rentable*, il est *neutre*.
2. **Les fills sont la SEULE route vers la mesure manquante.** Le dérapage au-delà de la cotation
   ne se mesure pas sans ordres. Le logger passif donne le spread ; **seul le trading donne le
   dérapage**. Désarmer, c'est renoncer définitivement à trancher.
3. **La mesure a une valeur asymétrique.** L'ORB porte ~57 % de la valeur funded simulée. Le coût
   de l'ignorance dépasse largement $25/trade.

## 4. Règles de sortie de la dérogation — GELÉES, non renégociables

- **A1** — à **N = 30 fills décomposés** (`ask_au_déclenchement − niveau`) + (`fill − ask`) : si le
  coût **tout-compris** dépasse **2.5 bps RT**, **désarmer** par ré-gel de spec (`FU_ORB_RISK = 0`).
  Échéance attendue : **~octobre 2026** (~1 fill/jour ouvré).
- **A2** — si la perte cumulée attribuable à l'ORB dépasse **$150** (6 fois le risque unitaire)
  avant d'atteindre N=30, désarmer **sans attendre** la mesure.
- **A3** — la dérogation **ne se renouvelle pas par défaut**. À N=30, soit A1 désarme, soit un
  **nouvel amendement** est écrit avec un verdict R2 recalculé sur l'échantillon **complet**.
- **A4** — le sous-échantillon 2018-2026 **ne peut être invoqué dans aucun amendement futur**
  comme justification de maintien. Seul un test **forward**, pré-enregistré avec sa date de départ
  fixée sur un critère de **régime de coût** décidé avant de regarder la performance, le pourrait.

## 5. Ce qui reste vrai et non résolu

- La **concentration de régime** du gross ORB (t 0.62 / 0.10 / 1.05 / **3.72** par période de
  4 ans, **avant tout coût**). Aucune mesure de frais n'y répond.
- Le ledger `nq_v2_trades.parquet` est **idéalisé sur ses deux jambes** (`entry == level`
  4013/4013 ; `exit_px == stop_eff` 1590/1590). Un audit du 2026-08-21 juge cette idéalisation
  empiriquement justifiée **sur futures NQ** (taux de gap 0.27 % / 0 %) — mais la production
  s'exécute en **CFD**. L'écart n'est pas mesuré.
- **`Δn_tests = 0`** : cet amendement ne teste aucune hypothèse nouvelle. Il corrige une entrée de
  coût et documente une dérogation.

## 6. Complément à A1 — la règle tranche DEUX décisions, pas une (2026-08-21)

Question posée par l'opérateur : *l'ORB ne serait-il pas meilleur en long-only ?* Origine :
4 trades ORB sur le compte funded, **tous shorts**, −$4.57 sur 3 clos.

**L'observation ne porte pas.** L'ORB poste deux stops opposés et prend celui qui déclenche ;
4 shorts consécutifs = US100 passé de 29 517 à 29 172 en 4 séances. **Régime de marché de 4 jours,
N=3 clos, et zéro observation de la jambe longue en réel.**

**Mesure sur le ledger (N=4013, R brut avant coût) :**

| sens | n | R moyen | t | taux de gain |
|---|---|---|---|---|
| long | 2 156 | +0.0589 | **2.49** | 48.3 % |
| short | 1 857 | +0.0378 | 1.25 | 40.3 % |

**Les DEUX jambes sont positives ⇒ le test L25 PASSE.** Sur un indice à dérive haussière, un
signal sans contenu ferait perdre les shorts. Ils gagnent : le breakout porte de l'information
au-delà du bêta.

**Levier médian 195 ⇒ 1 bps RT = 0.0195 R.** Total en R selon le coût :

| coût RT | long | short | long-only vs two-sided |
|---|---|---|---|
| 0 bps | 127.0 | **+70.3** | −36 % |
| **0.96** (spread natif mesuré) | 86.6 | **+35.4** | **−29 %** |
| **2.17** (tout-compris, n=12) | 35.6 | **−8.5** | **+31 %** |

> ### **Point mort de la jambe courte : 1.94 bps RT.**
> Il tombe **entre** le spread mesuré (0.96) et l'estimation tout-compris (2.17).

⇒ **A1 tranche désormais deux décisions avec le même seuil et la même mesure** :
- coût tout-compris **< 1.94 bps** ⇒ garder **two-sided** (et l'ORB vit) ;
- **1.94 – 2.5 bps** ⇒ basculer **long-only**, l'ORB survit amputé ;
- **> 2.5 bps** ⇒ **désarmer** (A1 d'origine).

**Interdits, pour éviter la sélection post hoc :**
- basculer en long-only **sur la performance observée d'une jambe** — sur un indice à dérive
  haussière, c'est le piège bêta manuel de L25, qui a déjà tué plusieurs familles du dépôt ;
- couper une jambe **faible mais positive** : le sizing est à **risque fixe** ($25/trade), donc ce
  qui compte est **Σ R**, pas la moyenne. Long-only monte la moyenne de 20 % en supprimant 1 857
  trades ⇒ **−29 % de P&L total** au coût mesuré aujourd'hui.

La bascule ne peut se décider que **sur le coût mesuré à N=30**, jamais sur la performance des jambes.
