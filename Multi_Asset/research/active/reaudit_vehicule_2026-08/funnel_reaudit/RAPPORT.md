# PROGRAMME 1 — Ré-audit du funnel `top10_test` sur pile d'instruments réparée

**Exécuté le 2026-08-13**, sous le pré-enregistrement gelé
`reaudit_vehicule_2026-08/PREREGISTRATION.md` (§1.1-§1.5, règles P1-R1→P1-R4).
`PropFirms/ftmo/program_2026-06/top10_test/` n'a jamais été modifié : toute réparation
est une **copie** dans `funnel_reaudit/code/`.

## Verdict en une ligne

**Le ré-audit ne ressuscite personne.** Sur la pile entièrement réparée, **0 candidat sur 162**
franchit P1-R1. Trois candidats atteignent RESEARCH_PASS (SR 0.79-0.86) mais tous échouent le
**DSR corrigé**, avec un t HAC plafonné à 2.16 et un AMTP p = 1.00. Le défaut le plus lourd n'est
aucun de ceux que le pré-enregistrement classait « faux négatifs » : c'est le **fuseau horaire**
(|ΔSR| moyen **0.46**, max **2.51**), et il joue **dans les deux sens** — il tue autant de
candidats qu'il en fabrique. Les trois défauts attendus comme générateurs de faux négatifs
(**DSR**, **plancher à cliquet**, **type d'ordre**) ne changent **aucun verdict**, et deux d'entre
eux ne déplacent **aucun Sharpe d'un seul chiffre significatif**.

---

## 1. Reproduction du funnel d'origine — le préalable

### 1.1 Les entrées du funnel n'existent plus

Vérifié le 2026-08-13, les trois répertoires que `data_loaders.py` et `batch_strategies.py`
adressent en dur ont été supprimés par le nettoyage P2 du 2026-06-10 :

| chemin cité par le funnel | état |
|---|---|
| `data/panels/m5_indices/{US500,US100,US30,GER40,EURUSD,USDJPY,…}_M1.csv` | **SUPPRIMÉ** (13 M1 EET ; seul `US2000_M1.csv` subsiste) |
| `data/ftmo_research/EURUSD_m5.parquet` | **RÉPERTOIRE ABSENT** |
| `Forex/data/cache/dukascopy_m5/*.parquet` (UK100, XAGUSD, GBPJPY, USOIL, UKOIL) | **RÉPERTOIRE ABSENT** |
| `Forex/research/archived/strategy_f2_asian_breakout/news_events_2020_2025.csv` | présent (760 événements, 12 types) |
| `data/panels/vix.csv` | présent |

Substituts utilisés, **même flux MT5**, jamais une reconstruction :
`m1_panel.parquet` (US500/US100/US30) et `{GER40,XAUUSD,EURUSD}_m1_panel.parquet` pour les
instruments à panel survivant ; `data/deep_history_utc/*_M1.csv` (canonique, vrai UTC, réparé)
pour les 11 autres. `GBPJPY` et `UK100` n'existent nulle part ⇒ 1 spec sur 142
(`pr_EURJPY_GBPJPY_z1.5_h3`) est **non rejouable** et sort en n=0.

**Horloge des panels vérifiée au tick** (discipline L52/L56, et c'est précisément le défaut n°2) :
sur EURUSD, l'index du panel colle à `deep_history_utc` décalé de **+2 h en janvier** et
**+3 h en juillet** (|erreur| médiane 0.4 pip aux bons décalages, 4-20 pips aux autres) ⇒ le label
`timestamp_utc` des panels est **Europe/Athens**, pas UTC. Confirmé.

### 1.2 Taux de reproduction — `out/reproduction.csv`

| famille | n | **bit-exact** (ΔSR < 1e-6 et même n_trades) | à ΔSR < 0.05 | ΔSR médian | Δn_trades médian |
|---|--:|--:|--:|--:|--:|
| event_drift | 48 | 18 | 5 | 0.059 | 0 |
| post_event_rev | 36 | 12 | 6 | 0.050 | 0 |
| intraday_mom | 16 | 11 | 0 | 0.000 | 0 |
| multi_event | 8 | 3 | 1 | 0.064 | 0 |
| gap_variant | 12 | 0 | 9 | 0.040 | 56 |
| pair_mr | 12 | 0 | 0 | 0.392 | 87 |
| calendar | 10 | 0 | 3 | 0.135 | 103 |
| **TOTAL tier 1 (142 specs)** | **142** | **44** | **24** | **0.057** | **5** |
| **TOTAL tier 2 (20 candidats « rigoureux »)** | **20** | **20** | 0 | **0.000** | **0** |

**64/162 candidats sont reproduits au bit près, et le motif des échecs est entièrement expliqué —
il n'y a aucun résidu méthodologique.** Dans les familles événementielles, la reproduction exacte
est **30/30 sur les instruments dont le panel a survécu** (US500 15/15, XAUUSD 9/9, GER40 2/2,
US100 2/2, US30 2/2) et **0/54 sur ceux dont le fichier a été supprimé** (EURUSD 0/20, USDJPY 0/17,
GBPUSD 0/9, EURGBP 0/4, EURJPY 0/4). Les familles à ré-échantillonnage journalier (gap, calendar,
pair) diffèrent par la **fenêtre** et non par le calcul : le funnel disposait d'indices depuis
**~2018-01** (2 176 jours ouvrés) là où le panel survivant démarre au **2020-01-01**, et de FX
depuis **~2023** seulement (830-860 jours) là où ma pile en a depuis 2020.

Le **tier 2 est reproduit à 20/20 exactement** parce que le funnel avait sauvegardé les carnets de
trades complets (`results/trades_*.csv` : `gross_bps`, `cost_bps`, `swap_bps`, `n_nights`, `asset`,
`side`) et l'index de PnL journalier exact (`daily_pnl_*.csv`). Le gross y est figé ⇒ les défauts
1, 3, 4, 5 et 6 se ré-appliquent **exactement**. Le défaut 2 (horloge), lui, modifie le **signal**
et non le coût : il est **inapplicable au tier 2** sans les séries de prix disparues, et le rapport
le signale partout.

**Conclusion du préalable : la reproduction est acquise là où les entrées existent encore.**
Le harnais est donc fidèle. Toutes les contributions marginales ci-dessous sont mesurées
**à l'intérieur de ma propre pile**, base et réparations sur exactement les mêmes données —
c'est de toute façon la seule façon correcte d'isoler un effet marginal.

### 1.3 Écart de périmètre déclaré (ce n'est pas une réparation)

Fenêtre unique **2020-01-01 → 2026-05** pour les 142 specs (`--sample-floor 2020-01-01`).
Elle **raccourcit** les familles indices/or (le funnel partait de 2018) et **allonge** les familles
FX (le funnel partait de 2023). C'est une contrainte de disponibilité, pas un des 6 défauts, et
elle est constante entre `base` et toutes les réparations, donc elle **ne contamine aucun ΔSR**.

---

## 2. La table des deltas — livrable principal (`out/deltas.csv`)

8 configurations complètes de 142 specs + 7 configurations de 20 carnets :
`base`, `D1_dsr`, `D2_clock`, `D3_costs`, `D4_floor`, `D5_swaps`, `D6_order`, `ALL`.
Un défaut à la fois, jamais groupés ; `ALL` n'est publié qu'en supplément.
Toutes les lignes, changement de verdict ou non : `out/marginal_all.csv`.

### 2.1 Amplitude marginale, par défaut (142 specs)

| # | défaut réparé | sens attendu (préreg.) | ΔSR moyen \|·\| | ΔSR max \|·\| | n specs touchées | Δp(FTMO) moyen | **verdicts changés** |
|---|---|---|--:|--:|--:|--:|--:|
| 1 | DSR `std_sr_trials=1.0` | faux négatifs | **0.0000** | 0.0000 | 0/142 | +0.0000 | **0** |
| 2 | **fuseau EET étiqueté UTC** | fenêtres jamais explorées | **0.4605** | **2.5128** | **141/142** | −0.0106 | **5** |
| 3 | table de coûts de catalogue | faux négatifs métaux+indices | 0.0339 | 0.4062 | 69/142 | +0.0069 | **1** |
| 4 | plancher à CLIQUET | faux négatifs sur chemins gagnants | **0.0000** | 0.0000 | 0/142 | +0.0036 (max +0.0385) | **0** |
| 5 | swap indices −3.1, aveugle au côté | faux négatifs familles tenues | 0.0469 | **1.3089** | 44/142 | +0.0087 | **1** |
| 6 | coût aveugle au type d'ordre | re-tri gratuit | **0.0000** | 0.0000 | **0/142** | +0.0000 | **0** |

### 2.2 Les 5 candidats qui changent de verdict, et par quel défaut

| id | famille / classe | n | SR base | verdict base | ΔSR D2 horloge | ΔSR D3 coûts | ΔSR D5 swaps | **défaut responsable** | verdict après |
|---|---|--:|--:|---|--:|--:|--:|---|---|
| `ed_fomc_US30_LO` | event_drift / index | 49 | **0.960** | RESEARCH_PASS | **−0.589** | +0.020 | +0.032 | **D2 (horloge)** | **REJECT** |
| `me_fom_nfp_cpi_XAUUSD_+1` | multi_event / or | 187 | **0.790** | RESEARCH_PASS | **−0.707** | +0.172 | +0.144 | **D2 (horloge)** | **REJECT** |
| `ed_cpi_us_XAUUSD_LO` | event_drift / or | 71 | 0.637 | REJECT | −0.099 | **+0.120** | **+0.100** | **D3 (or 3.50→1.84)**, et D5 seul suffit aussi | RESEARCH_PASS |
| `ed_fomc_USDJPY_LO` | event_drift / FX | 49 | 0.515 | REJECT | **+0.310** | 0.000 | −0.008 | **D2 (horloge)** | RESEARCH_PASS |
| `ed_boj_rate_USDJPY_LO` | event_drift / FX | 48 | **−0.709** | REJECT | **+1.413** | 0.000 | +0.148 | **D2 (horloge)** | RESEARCH_PASS |

`ed_fomc_GER40_LO` ne figure pas ici : il est RESEARCH_PASS dans **toutes** les configurations
(SR 0.795 base → 0.863 sur la pile complète). Il est traité au §3 avec les autres.

### 2.3 Ce que chaque défaut fait vraiment

**Défaut 2 — le fuseau : de loin le premier contributeur, et il n'est pas un « faux négatif ».**
Mécanisme, propre et vérifiable : `news_events_2020_2025.csv` porte des heures en **vrai UTC**
(FOMC 19:00, CPI/NFP 13:30, BOJ 03:00, ECB 13:15 — tous cohérents avec les heures officielles),
tandis que l'index des barres est en **Europe/Athens**. `_bar_at_time_or_close(intraday, 13:30)`
cherchait donc la première barre à ou après *13:30 Athènes* = **11:30 UTC l'hiver, 10:30 UTC l'été**.
**Le funnel sortait systématiquement 2 h (hiver) à 3 h (été) AVANT la publication qu'il prétendait
mesurer.** Réparé, cela déplace 141 specs sur 142, de **0.46 de Sharpe en moyenne** et jusqu'à
**2.51**, et **dans les deux sens** : `ed_boj_rate_USDJPY_LO` passe de −0.71 à +0.70 (la
publication BOJ à 03:00 UTC tombait à 00:00-01:00 sur l'horloge fausse), tandis que
`ed_fomc_US30_LO` et `me_fom_nfp_cpi_XAUUSD_+1` — les deux seuls RESEARCH_PASS du funnel —
**s'effondrent** une fois mesurés à la vraie heure. Le défaut 2 n'était donc pas un filtre trop
sévère : c'était un **bruit d'appariement**, qui donne autant de faux positifs que de faux négatifs.
*Résidu connu, non corrigé* : le fichier d'événements fige une heure UTC constante toute l'année
(FOMC 19:00), donc il reste **1 h de retard en été** — même signature L56, un cran plus fin.

**Défaut 3 — les coûts : réel, ciblé, petit.** Exactement les classes annoncées par
`COST_AUDIT.md` bougent, et rien d'autre : or **+0.150 de Sharpe en moyenne** (max +0.406,
16 specs), indices **+0.046** (max +0.218, 53 specs), **FX_major, FX_cross et Commodity_CFD
strictement 0.000** — le `FX_major = 1.5` a été **laissé inchangé**, conformément au
pré-enregistrement (§1.1) : la colonne de spread du cache est zéro-inflée sur le FX
(EURUSD 33.2 % de jours à spread nul), donc 1.5 n'est **pas** démontré trop sévère et pourrait être
**optimiste**. Ce défaut ressuscite **un** candidat, et c'est bien un candidat **or**
(`ed_cpi_us_XAUUSD_LO`) — le réservoir d'erreurs de type II que l'audit de coût avait nommé.

**Défaut 5 — les swaps : c'est le CÔTÉ, pas la magnitude.** Le funnel facture −3.1 bps/nuit à un
indice **quel que soit le sens**. Les mesures `spec_v22.yaml:cost_anchors` (reconstruites au
centime sur 4/4 des débits de la nuit 10→11/06) sont **asymétriques** : US100 long −2.126 mais
**short +0.092**, GER40 −1.564 / −0.193, XAUUSD −1.518 / −0.336, USDJPY **+0.060** / −1.267.
Le maximum de ΔSR (**+1.309**) tombe sur une jambe **short d'indice** que le funnel taxait comme
une jambe longue. Effet moyen +0.089 sur les indices, +0.072 sur l'or, **+0.011 sur le FX** (seul
USDJPY est mesuré ; les autres paires restent au tarif de catalogue).

**Défaut 1 — le DSR : le bug est réel, sa contribution est nulle, et pour une raison qui compte.**
`framework.py:118` compare un Sharpe **annualisé** à `E[max SR]` exprimé en unités de σ_SR, avec
σ_SR implicitement fixé à 1.0 : à n_trials = 142 le seuil vaut **2.571**, d'où les colonnes `dsr`
à −11.6, −24.5, −32.3 du CSV publié. La version saine est `dsr.py` **à la racine** (défaut `rf`
bien à **0.0**, aucun défaut silencieux pour `std_sr_trials`) ; `_automation/feasibility/stats/dsr.py`
n'a jamais porté le bug (il utilisait implicitement le plancher de bruit d'échantillonnage).
Le bug est **dans `top10_test/framework.py`**, une troisième implémentation maison.
Mais réparé, le seuil ne descend pas comme le pré-enregistrement l'anticipait :

| paramétrage de σ_SR | σ_SR | E[max SR] (n=162, T=1542) | SR observé requis DSR≥0.5 | requis DSR≥0.95 |
|---|--:|--:|--:|--:|
| funnel (implicite 1.0) | 1.000 | **2.613** | ~2.61 | ~2.63 |
| plancher de bruit `sqrt(252/T)` | 0.404 | **1.090** | 1.09 | **1.76** |
| dispersion **observée** de la famille (`estimate_std_sr_trials`) | **0.862** | **2.325** | 2.33 | **2.99** |

La dispersion réelle des 162 Sharpes du funnel est **0.862** — les essais sont génuinement
hétérogènes, donc la barre honnête est **plus haute** que le plancher de bruit, et à peine plus
basse que la barre cassée. **Et surtout : le Sharpe maximum de tout le funnel est 0.960**
(p95 = 0.483, médiane = −0.606). Aucun des trois seuils n'est atteignable, ni de loin.
**Le DSR cassé n'a éliminé personne qui aurait survécu au DSR sain** : il n'était pas liant.

**Défaut 4 — le plancher : la géométrie ne vaut pas grand-chose ici.** `framework.py:55` documente
`FTMO_MLL_PCT` comme « trailing, EOD high-watermarked, never decreases » et l'applique
(`mll_floor = max(1−MLL, hwm−MLL)`), alors que le 2-step FTMO est **STATIQUE** à −10 % du solde
initial (le cliquet est le produit 1-step, écarté deux fois dans ce repo). Ce défaut ne touche
**que** la simulation Monte-Carlo, jamais le Sharpe : ΔSR ≡ 0.0000 sur 142/142. Le gain de
p(pass P1) est de **+0.36 point en moyenne, +3.85 points au maximum**. **P1-R4 : aucun candidat
n'est ressuscité par le seul passage cliquet → statique.** Le biais avait le sens annoncé — il
favorise bien les chemins gagnants — mais son amplitude ne renverse aucune décision.

**Défaut 6 — le type d'ordre : l'axe de re-tri est vide côté tier 1, et coûteux côté tier 2.**
Les 142 specs entrent et sortent **toutes** au marché à heure fixe : `event_drift` et
`multi_event` entrent à la clôture T−1 et sortent sur l'ouverture d'une barre datée,
`intraday_mom` sur des barres à (h,m) fixes, `calendar` et `pair_mr` sur open/close journaliers,
et les 12 specs `gap_variant` sont **toutes** en `exit_mode="close"` — le chemin
`exit_mode="fill"` du code (qui, lui, utilise un stop) n'est instancié par **aucune** spec.
Toutes tombent donc dans le tier bon marché (~0.0-0.1 bps de dérapage médian, n=32) ⇒
**ΔSR ≡ 0 sur 142/142.** Ce n'est pas un non-résultat : ça dit que **le funnel n'a jamais testé
une seule famille à déclenchement sur stop**, donc que le tri par type d'ordre ne peut rien y
libérer. En revanche, **7 des 20 candidats du tier 2** ont une **sortie en bracket/stop**
(`ang_025`, `ang_025_flip`, `ang_025_flip_mod2/3`, `ang_019`, `lit_021`, `lit_020` —
`run_tests.py:87-123, 177-191`) : facturés au tier « stop au repos » (+2.169 bps sur la jambe
de sortie, borne haute assumée), ils perdent **0.082 de Sharpe en moyenne, jusqu'à −0.457**.
C'est L59 en vigueur : la famille à sortie sur stop du funnel est validée de façon **incomplète**,
et dans le sens **défavorable**.

### 2.4 Le tier 2 (20 candidats « rigoureux ») — aucun mouvement

Aucun des 20 n'atteint SR > 0.7 dans **aucune** configuration. Meilleurs sur la pile réparée
(`out/tier2_ALL.csv`) : `lit_013` **0.421**, `ang_047_mod3` 0.363, `ang_024` 0.176. Contributions
marginales : D3 +0.036 en moyenne (max +0.127), D5 +0.109 (max **+1.569** — la jambe short de
`ang_048` US100-US500, taxée −3.1/nuit alors que le short d'indice mesuré est **positif**),
D6 **−0.082** (défavorable), D1 et D4 exactement 0. **0 changement de verdict.**

---

## 3. Les candidats qui atteignent RESEARCH_PASS — diagnostic complet

`out/survivor_diagnostics.csv`. Walk-forward **expanding, 5 folds** (min_train 1.5 an) pour tous ;
HAC Newey-West lag-6 ; **block bootstrap Politis-Romano, 5 000 tirages, blocs de 5** (iid jamais
utilisé) ; DSR corrigé sous les deux dispersions défendables.

> **Annualisation — écart mesuré, conservé pour la comparabilité (L47).** Le funnel annualise en
> **√252 en dur** ; la grille réelle (`freq="B"`, jours ouvrés sans calendrier de fériés) donne
> **261.06 observations par an mesurées**. Les Sharpes ci-dessous sont donc **sous-estimés d'un
> facteur 1.0178** — je les publie à l'identique du funnel pour que les deltas restent comparables,
> et je rapporte la sensibilité : au √261 mesuré, le meilleur du funnel passe de 0.960 à **0.977**,
> et **un seul** candidat franchirait un seuil supplémentaire, `ed_cpi_us_XAUUSD_LO` sur la pile
> complète (0.688 → **0.700**). Il échoue P1-R1 de toute façon, son IC95 contenant zéro. **Aucun
> verdict de ce rapport ne dépend du choix d'annualisation.**

| id | config | n_tr | N jours | gross bps/tr | gross/coût | **SR** | MaxDD | t HAC | WF | SR par fold OOS | IC95 bootstrap | **DSR (disp. obs.)** | DSR (plancher) | miroir SS | **ρ overnight** |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|---|---|--:|--:|--:|--:|
| `ed_fomc_US30_LO` | base | 49 | 1531 | 29.41 | 6.39 | **0.960** | −6.8 % | 2.41 | 5f 100 % | 1.43 / 0.56 / 0.41 / 1.04 / 1.93 | [+0.353, +1.604] | **1.4e−06** | 0.328 | −1.656 | **+0.185** |
| `ed_fomc_GER40_LO` | base | 37 | 1498 | 21.31 | 4.63 | 0.795 | −3.3 % | 1.96 | 5f 80 % | 1.76 / 0.84 / 0.09 / 1.64 / −1.31 | [+0.135, +1.295] | 1.4e−08 | 0.142 | −1.411 | +0.175 |
| `me_fom_nfp_cpi_XAUUSD_+1` | base | 187 | 1549 | 17.14 | 2.68 | 0.790 | −13.7 % | 2.02 | 5f 80 % | −0.39 / 0.95 / 1.79 / 1.24 / 0.94 | [+0.036, +1.466] | 2.7e−05 | 0.215 | −1.673 | +0.012 |
| `ed_cpi_us_XAUUSD_LO` | D3 | 71 | 1542 | 17.86 | 3.77 | 0.757 | −9.8 % | 1.90 | 5f 80 % | 0.56 / −0.42 / 1.77 / 0.92 / 1.85 | **[−0.076, +1.358]** | 4.7e−06 | 0.174 | −1.881 | +0.050 |
| `ed_fomc_GER40_LO` | **ALL** | 48 | 1531 | 16.98 | 6.89 | **0.863** | −8.6 % | 2.16 | 5f 80 % | 1.81 / 1.06 / 0.45 / 1.70 / −1.73 | [+0.153, +1.355] | 2.7e−07 | 0.218 | −1.418 | +0.161 |
| `ed_fomc_USDJPY_LO` | **ALL** | 49 | 1531 | 25.80 | 9.32 | 0.818 | −11.9 % | 2.04 | 5f 60 % | −0.87 / 2.25 / 1.69 / 1.73 / −1.33 | [+0.111, +1.490] | 5.3e−06 | 0.213 | −1.526 | +0.055 |
| `ed_boj_rate_USDJPY_LO` | **ALL** | 48 | 1544 | 16.11 | 10.33 | 0.785 | −1.4 % | 1.98 | 5f 60 % | 0.78 / 1.38 / 1.88 / −0.24 / −0.66 | [+0.244, +1.304] | 8.3e−11 | 0.103 | −1.835 | +0.016 |

### 3.1 Corrélation à la sleeve overnight déployée — c'est l'objet de la recherche

Sleeve de référence reconstruite depuis les panels : **US100 + GER40 LONG, lundi et mardi**,
entrée **17:35 CET (GER40)** / **22:05 CET (US100)**, sortie **09:00** / **15:30 CET**, équipondérée,
nette du coût RT mesuré (0.9 bps) et du swap long mesuré (US100 −2.126, GER40 −1.564).
Athènes = CET + 1 h toute l'année, donc la conversion est exacte.
Résultat : **N = 1 392 jours ouvrés, 538 jours actifs, 2021-05 → 2026-05, SR 0.656**
(`out/overnight_sleeve_daily.csv`). *Réserve* : les barres 17:35/22:05 CET n'existent dans les
panels qu'à partir de 2021, la sleeve démarre donc 16 mois après les candidats ; le recouvrement
utilisé pour ρ est de **490-492 jours ouvrés**.

**Tous les candidats sont décorrélés** : ρ ∈ [**+0.012** ; **+0.185**], donc **|ρ| < 0.3 pour 7/7**.
La condition de décorrélation de **P1-R2 est satisfaite par tout le monde**. Ce n'est pas la
décorrélation qui manque à ce funnel — c'est le signal. Les deux candidats or et les deux USDJPY
sont quasi orthogonaux (ρ ≤ 0.055) ; les deux candidats indices, qui partagent le beta actions de
la sleeve, montent seulement à +0.17/+0.18. Le second membre de P1-R2 (ΔSR_book > 0 au poids ERC,
significatif au block-bootstrap) **n'est pas évalué** : P1-R2 ne s'applique qu'à un *survivant*
de P1-R1, et il n'y en a aucun.

### 3.2 Aucun support two-sided — et le test miroir du funnel ne teste rien (L42 répliquée)

Les colonnes `_SS` du funnel sont construites `side = -side_long` sur **les mêmes événements**.
Vérifié numériquement : `gross_SS + gross_LO = 0.00e+00` **exactement**, sur 4/4 des paires
contrôlées (US30, GER40, XAUUSD, USDJPY). Le « miroir » à SR −1.4 / −1.9 n'est donc pas une
falsification indépendante, c'est la même série changée de signe et taxée deux fois les coûts.
**Les 24 paires LO/SS du bloc `event_drift` ne contiennent que 24 hypothèses distinctes**, et
**aucun** de ces candidats n'a de support two-sided au sens L25. Ce sont des jambes longues de
calendrier — de l'exposition, pas un edge à deux faces.

### 3.3 Sensibilité FX — l'exception du pré-enregistrement, appliquée

Deux des trois candidats de la pile complète sont **FX**, la classe où le coût a été laissé
**inchangé** faute de mesure crédible. Sensibilité mesurée sur la pile `ALL` :

| `FX_major` (bps RT) | 1.5 (retenu) | 2.5 | 3.5 | 5.0 |
|---|--:|--:|--:|--:|
| `ed_fomc_USDJPY_LO` SR | 0.818 | 0.773 | 0.728 | **0.658** ✗ |
| `ed_boj_rate_USDJPY_LO` SR | 0.785 | 0.715 | **0.643** ✗ | 0.532 ✗ |

Ils ne meurent pas au premier bps, mais ils sortent de RESEARCH_PASS entre **3.5 et 5 bps** —
c'est-à-dire dans la fourchette exacte du tier retail que L43 documente. **Toute conclusion FX de
ce ré-audit est donc conditionnelle à un chiffre de coût qui n'est pas mesuré**, et le sens de
l'incertitude est **défavorable**.

---

## 4. Application des règles de kill P1

**P1-R1 — SURVIVANT = RESEARCH_PASS + DSR corrigé + IC bootstrap excluant 0. → 0/162.**

Le pré-enregistrement écrit « DSR corrigé > 0 », formulation héritée de la colonne `dsr` du funnel,
qui est un **z-score** (« Sharpe observé au-dessus du benchmark de déflation »). Sous la
paramétrisation saine (Bailey-PSR), le DSR est une **probabilité dans (0,1)** et « > 0 » serait
vide de sens. Les deux lectures défendables sont donc :

* **traduction fidèle du z-score** : `SR observé > E[max SR]` ⟺ **DSR > 0.50** ;
* **seuil conventionnel** du module : **DSR ≥ 0.95**.

**Les sept candidats échouent sous les deux, et sous les deux calibrations de σ_SR.** Le meilleur
DSR observé est **2.7e−05** (dispersion observée) et **0.328** (plancher de bruit) — contre 0.50
requis. Ce n'est pas un échec de justesse : il faudrait un Sharpe de **2.33** (ou 1.09 au plancher)
là où le meilleur du funnel est **0.960**. Un candidat échoue en plus sur l'IC :
`ed_cpi_us_XAUUSD_LO`, IC95 = **[−0.076, +1.358]**, qui **contient zéro** — c'est justement le
candidat que le défaut 3 avait ressuscité. Le t HAC plafonne à **2.41** (aucun > 2.5) et
**l'AMTP-Bonferroni rend p = 1.000 pour les 162**.

> **Verdict P1-R1 : 0 survivant. Le funnel avait raison sur le fond, pour de mauvaises raisons.**

**P1-R2 — admissibilité au book.** Sans objet : aucun survivant P1-R1. Mesuré quand même parce
que c'est l'objet de la recherche — **la condition de décorrélation |ρ| < 0.3 est satisfaite 7/7**
(§3.1).

**P1-R3 — les kills MÉCANIQUES restent fermés.** Aucun des 5 candidats à verdict changé n'avait un
kill d'origine mécanique : gross **16.1 à 29.4 bps par trade**, ratio gross/coût **2.7 à 10.3**,
et aucun n'est « sous placebo » ou « négatif à coût nul » — leurs kills d'origine étaient de nature
**COÛT** (or à 1.9× le réel) et **INSTRUMENT** (fuseau). La règle n'a donc bloqué aucune
résurrection ici ; elle reste applicable telle quelle. **Réserve L42** : le funnel n'ayant jamais
produit de test two-sided réel (§3.2), aucun de ces candidats n'a jamais été soumis au falsificateur
« négatif à coût nul des deux côtés » — leur statut « non mécanique » n'est **pas démontré**, il est
seulement **non réfuté**.

**P1-R4 — résurrections par pure géométrie.** **Aucune.** Le passage cliquet → statique laisse
ΔSR ≡ 0 et ne déplace p(pass P1) que de **+0.36 point en moyenne (+3.85 au maximum)** ; il ne fait
franchir aucun seuil à personne. Rien à signaler à part.

---

## 5. Comptage des essais — le ledger n'est PAS incrémenté

Conformément au §1.5 du pré-enregistrement : re-passer une hypothèse **déjà pré-enregistrée et
déjà comptée** avec des instruments réparés est une **CORRECTION**, pas un nouvel essai.
**Δn_tests = 0.** Le DSR des candidats futurs n'est pas déflaté par ce travail.

Réconciliation du périmètre : **142** (`run_batch.py`, `summary_batch_142.csv`) **+ 20**
(`run_tests.py` 10 + `strategies_v2.py:NEW_STRATEGIES` 10, `summary_full_3paths.csv`)
= **162 hypothèses distinctes**. Les 5 lignes `*_fixed` de `summary_full_3paths.csv` sont des
**re-dimensionnements** d'hypothèses déjà comptées, pas des hypothèses. Le « 164 » du ledger
excède donc l'artefact de **2** ; l'écart n'est pas reconstructible depuis les fichiers survivants,
et je ne l'ai pas corrigé — **le ledger reste à 321, inchangé**.

### Hypothèses nouvelles croisées en chemin — NOTÉES, NON TESTÉES (hors périmètre)

1. **Le drift pré-BOJ sur USDJPY, mesuré à la vraie heure de publication (03:00 UTC).** Le funnel
   l'a mesuré 2-3 h trop tôt et l'a vu à SR −0.71 ; à l'heure correcte il vaut +0.70 (n=48).
   Ce n'est **pas** la même hypothèse que celle qui a été pré-enregistrée. Non testée ici.
2. **Le résidu d'été du calendrier d'événements** : `news_events_2020_2025.csv` fige une heure UTC
   constante toute l'année (FOMC 19:00), donc reste 1 h en retard d'avril à octobre — même
   signature que L56. Un recalage DST du fichier est une hypothèse d'instrument, non testée.
3. **La famille à sortie en bracket/stop du tier 2 re-tarifée au tier « stop au repos »** :
   mesurée ici comme un coût (−0.082 de Sharpe moyen), jamais comme une hypothèse à part entière.

---

## 6. Ce que ce ré-audit établit, et ce qu'il ne peut pas établir

**Établi.**
1. **0 survivant P1-R1 sur 162, pile entièrement réparée.** La question ouverte du funnel
   contaminé est **fermée** — proprement, et sans consommer d'essai.
2. **Le classement des défauts est inversé par rapport à l'attente.** Le pré-enregistrement
   attendait des faux négatifs de 1 (DSR), 3 (coûts), 4 (plancher), 5 (swaps). Mesuré :
   1, 4 et 6 changent **zéro** verdict ; 3 et 5 en changent **un** chacun ; **2, qui n'était même
   pas classé comme un générateur de faux négatifs, en change 5 et domine d'un ordre de grandeur.**
3. **Un bug de fuseau est un bruit d'appariement, pas un filtre.** Il détruit autant qu'il crée
   (2 candidats tués, 2 ressuscités, 1 amélioré). Un défaut d'instrument ne se classe pas « faux
   négatif » ou « faux positif » avant d'être mesuré dans les deux sens.
4. **Un gate de sélection n'est liant que si la distribution le touche.** Le DSR cassé exigeait
   SR 2.63 ; le DSR sain en exige 2.33 (dispersion observée) ou 1.76 (plancher). Comme le maximum
   du funnel est 0.960, **les trois barres sont équivalentes en pratique**. Réparer un gate
   non liant ne rend rien.
5. **Décorrélé ≠ admissible.** 7/7 des candidats passent |ρ| < 0.3 contre la sleeve déployée.
   La contrainte qui a vidé ce funnel n'a jamais été la corrélation.
6. **Le funnel n'a jamais testé une famille à déclenchement sur stop** (0/142), donc le défaut 6
   n'y libère rien ; il **coûte** en revanche 0.082 de Sharpe aux 7 candidats du tier 2 à sortie
   en bracket (L59, sens défavorable).

**Non établi / limites dures.**
- **Reproduction partielle** : 64/162 au bit près. Les 98 autres portent sur des specs dont le
  fichier d'entrée a été supprimé (substitution de flux) ou dont l'échantillon d'origine
  commençait avant le panel survivant. Les verdicts d'origine de ces 98 ne peuvent pas être
  ré-audités sur des données identiques — seulement ré-estimés.
- **Le défaut 2 est inapplicable au tier 2** (les prix ont disparu) : les 20 candidats
  « rigoureux » sont ré-audités sur 5 défauts sur 6.
- **Le coût FX reste non mesuré** ; les deux candidats FX de la pile complète meurent entre
  3.5 et 5 bps RT (§3.3).
- **`GBPJPY` et `UK100` n'existent nulle part** : `pr_EURJPY_GBPJPY_z1.5_h3` n'est pas rejouable.
- Le p(pass) Monte-Carlo diffère du funnel de **0.5 à 1.7 point** (flux RNG vectorisé, blocs de
  fin de série tronqués vs répétés). Sans effet sur les gates, qui ne dépendent pas de p(pass).
- **Un 7ᵉ défaut, non listé au pré-enregistrement et laissé en place** : le funnel annualise en
  √252 sur une grille qui vaut **261 obs/an** (L47, biais de −1.8 % sur tous les Sharpes). Corrigé,
  il ne déplace qu'un seuil et aucun verdict (§3).

---

## Fichiers

```
funnel_reaudit/
  code/  build_cache.py         caches M1 depuis data/deep_history_utc (lecture seule)
         data_layer.py          deux horloges, un flux par instrument ; sleeve overnight
         costs.py               tables catalogue vs mesurées (défauts 3, 5, 6)
         strategies_repaired.py copie des 7 handlers + 142 specs, avec les commutateurs
         engine.py              copie de framework.py + commutateurs DSR (D1) et plancher (D4)
         run_reaudit.py         8 configurations x 142 specs
         run_tier2.py           7 configurations x 20 carnets de trades sauvegardés
         make_deltas.py         assemblage des contributions marginales
         survivors.py           WF/HAC/bootstrap/DSR/miroir/rho overnight
  out/   deltas.csv                   <- LIVRABLE PRINCIPAL (5 changements de verdict)
         marginal_all.csv             162 lignes, tous les DeltaSR par defaut
         reproduction.csv             taux de reproduction par famille
         survivor_diagnostics.csv     les 7 RESEARCH_PASS, diagnostic complet
         dsr_calibration.json         sigma_SR, benchmarks, metriques de la sleeve
         overnight_sleeve_daily.csv   la sleeve deployee reconstruite
         summary_{base,D1..D6,ALL}.csv        142 specs x 8 configurations
         tier2_{base,D1,D3..D6,ALL}.csv       20 carnets x 7 configurations
```

Aucune commande git. Interpréteur `/usr/bin/python3`.
`top10_test/`, `ftmo_live/`, `Portfolio/`, `strategies/`, `data/`, `data/ftmo_portfolio/v22/`
et `vehicule/` n'ont reçu aucune écriture.
