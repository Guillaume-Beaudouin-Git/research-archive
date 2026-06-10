# PRESPEC — Signature jackpot ORB V2+E7

**Date de figeage** : 2026-06-03
**Statut** : PRÉ-ENREGISTREMENT FALSIFIABLE — aucun test exécuté
**Auteur** : Guillaume Beaudouin
**Cadre méthodologique** : L10 (max 3 modifs), L19 (rescaling temps-en-marché obligatoire), L20 (DSR Bailey-LdP avec N_mod déflaté), L25 (two-sided check sur direction unilatérale).

> **Contrat figé.** Aucune des valeurs ci-dessous ne peut être modifiée après visualisation de quelque donnée OOS que ce soit. Toute modification post-OOS = invalidation du test, archivage automatique en overfit in-sample.

---

## 0. Provenance — diagnostic in-sample (référence non-modifiable)

Source : `data/ftmo_research/ORB_structure_diagnostic_2026-06.md`. Ledger canonique `data/ftmo_research/audit/nq_v2_trades.parquet` (N=4013 trades NQ databento 2010-2026 V2 baseline + lift E7 +0.015 R, coût 0.4 bps RT).

**Faits in-sample observés** :
- Top 1% des trades par R (N=40) = **93% du P&L total** (+206.6 R sur +221.4 R)
- Mean_R sans le top 1% = +0.004 R/trade (~zéro)
- 3 variables observables AVANT entrée franchissent Bonferroni Welch p ≤ 0.0056 :
  - `bi` (break minutes after OR close) : Welch t=−5.84
  - `or_range_bps` (largeur OR en bps du sous-jacent) : Welch t=−3.32
  - `direction` (long/short) : Welch t=−3.25

**Limites in-sample inscrites au contrat** :
- N=40 sur le tail → puissance statistique minimale ; toute signature N=40 est fragile.
- Signature capture **20/40 jackpots seulement (50%)** in-sample lorsque les 3 conditions sont appliquées en intersection — donc **le filtre coupe 50% du tail qui porte 93% du P&L**.
- Retention in-sample = 16.6% des trades (666/4013). OOS retention ≈ 17%.
- N_mod cumulé après ce filtre = 8 (existants V2+E7+...) + 3 (les trois conditions ci-dessous) = **11**. DSR Bailey-LdP doit être déflaté à N_trials=11.

---

## 1. Hypothèse (figée, falsifiable, une phrase)

> **H₁** : « Les trades ORB V2+E7 sur NQ/US100 satisfaisant simultanément {break ≤ 15 minutes après OR close} ET {OR_range ≤ 45.3166 bps du sous-jacent} ET {direction = short} ont un mean_R net (coût 0.4 bps RT) OOS strictement supérieur au mean_R net OOS de l'ensemble des trades V2+E7 non filtrés, sur données post-2026-07-01. »

**Null falsifiable H₀** : mean_R_filtré ≤ mean_R_baseline_OOS.

---

## 2. Mécanisme économique (pourquoi ça DEVRAIT tenir, pas juste corréler)

### 2.1 Break ≤ 15 minutes — momentum d'ouverture authentique

L'ouverture NY 09:30-10:00 ET est la fenêtre d'absorption du flux d'ordres overnight + macro-news. Un break d'OR dans les 15 premières minutes post-close du OR (donc 10:00-10:15 ET pour un OR 09:30-10:00) signale qu'**un flux unidirectionnel persistant traverse la consolidation initiale immédiatement** — c'est le pattern Cooper-Cliff-Gulen (2008) de "auction-imbalance momentum" : la friction de l'auction est rompue par un déséquilibre réel, pas par du bruit de mid-session. Inversement, un break tardif (bi > 30 min) signale qu'aucune force dominante n'a porté l'OR ; le break éventuel relève plus d'un re-test technique que d'un flux conviction.

**Mécanisme défendable** : OUI. Cohérent avec littérature opening-range breakout (Crabel 1990 ; Fisher 2018) et microstructure (Conti-Valentini 2009).

### 2.2 OR_range ≤ 45.3 bps — conviction propre, journée non-bruitée

Un OR étroit (≤45 bps = 40e percentile in-sample) signale une **journée à faible asymétrie d'information préalable** : le marché ne sait pas où aller pendant les 30 premières minutes, et l'OR reflète une consolidation balanced. Le break subséquent dans une telle journée représente une **arrivée d'information nouvelle** (institutional flow, macro release, etc.), pas un mouvement noisy continuant la volatilité préexistante. Mécanisme inverse pour un OR large (≥80 bps) : la journée a déjà absorbé un choc volatil, le break est un noise add-on dans une distribution déjà large → tail droit écrasé par la variance ambiante.

**Mécanisme défendable** : OUI. Cohérent avec littérature volatilité-momentum (Moskowitz-Ooi-Pedersen 2012 : "high-vol regimes diluate momentum signal").

### 2.3 Direction = short — asymétrie de panique baissière

Les krachs intraday sur indices ont structurellement un **tail droit plus brutal côté shorts** (= mouvement baissier rapide où le short P&L gonfle) pour deux raisons :
1. **Asymétrie volatilité-rendement** (Black 1976 ; Christie 1982) : la volatilité réalisée s'amplifie dans les drawdowns, donc un break baissier dans une journée small-OR connaît une explosion de vol favorable au short.
2. **Liquidation forcée long** : un break baissier déclenche des stops longs, qui amplifient le mouvement non-linéairement (gamma effect chez les market-makers). Inversement, un break haussier est rare absorbant — short squeezes existent mais sont moins fréquents que les selling cascades.

**Mécanisme défendable** : OUI MAIS attention L25 — il faut vérifier OOS que la sur-représentation des shorts dans le tail n'est pas juste du **beta short d'un régime baissier in-sample** (le sample 2010-2026 contient COVID-2020 et bear 2022). Si la signature OOS ne tient QUE pendant 2026-08 bear period, c'est juste du market-timing baissier déguisé.

### 2.4 Honnêteté du mécanisme

Les 3 mécanismes sont **défendables individuellement** mais l'INTERSECTION (break early × small OR × short) ne dispose pas d'un mécanisme intégré dans la littérature. On suppose qu'ils s'**ajoutent** — c'est une hypothèse pas une démonstration. Si OOS ne valide pas, **ne pas inventer de mécanisme post-hoc pour sauver la signature** — c'est exactement l'overfit que ce PRESPEC essaie de prévenir.

---

## 3. Seuils figés (GELÉS — toute modif = invalidation)

| Condition | Valeur figée | Méthode de calcul (in-sample) | Verrou |
|---|---|---|---|
| `bi` (break minutes after OR close) | **≤ 15 min** | Choix discret, cohérent avec bucket [6-15] qui contient 39/40 jackpots | GELÉ |
| `or_range_bps` | **≤ 45.3166 bps** | 40e percentile de la distribution in-sample des or_range_bps (Q2 upper bound). Calcul = `np.percentile(or_range_bps, 40)` sur 4013 trades 2010-2026 | GELÉ |
| `direction` | **= -1 (short uniquement)** | Choix discret | GELÉ |

**Verrouillage explicite** :
- Ces 3 valeurs sont **les seules** acceptées pour le test OOS.
- Aucune ré-optimisation post-hoc ("essayons 14 min", "essayons 50 bps", "essayons +/- direction") = invalidation immédiate.
- Aucune ajout de variable ("ajoutons VIX_prev>20", "ajoutons gap_overnight<0") = invalidation immédiate. `weekday`, `gap_overnight`, `VIX_prev`, `year`, `or_range_pts` ont été TESTÉES in-sample, NON-significatives → définitivement exclues du PRESPEC, ne peuvent pas être réintroduites.
- Aucun ajustement de la grille V2+E7 sous-jacente (V2 dust filter OR ≥ 10 bps, E7 trail-to-BE après +1R, OR 30 min, RTH close).

**Retention attendue** : ~17% des trades OOS (in-sample : 16.6% = 666/4013).

---

## 4. Gate de décision (binaire, pré-défini)

Le filtre signature est **ACCEPTÉ pour déploiement** ssi, sur sample OOS post-2026-07-01 avec N_OOS ≥ N_min (cf. §6), TOUTES les conditions suivantes sont réunies :

### 4.1 Performance différentielle

- **mean_R_filtré_OOS > mean_R_baseline_OOS** (strictement supérieur, pas égal).
- **mean_R_baseline_OOS** = mean_R des trades V2+E7 OOS NON filtrés (i.e. les ~83% de trades skipés par le filtre + les 17% retenus).
- **mean_R_filtré_OOS** = mean_R des trades V2+E7 OOS retenus (les ~17%).

### 4.2 Significativité statistique HAC

- **t-HAC6 sur le différentiel ≥ 1.5** (lag Newey-West = 6).
- Régression : `R_trade = α + β × signature_indicator + ε`, où `signature_indicator = 1 si filtre passé, 0 sinon`. t-stat sur α + β attendue ≥ 1.5.
- Seuil 1.5 (et non 2.0) parce que N=40 in-sample → faible puissance ; trop strict serait punitif. Mais |t|<1.5 = noise.

### 4.3 DSR déflaté

- **DSR_filtré > 0.95** (Bailey-Lopez de Prado 2014) avec **N_trials = 11** : 8 modifs existantes V2+E7 (V2 dust, E7 trail, OR 30min, stop opposite side, etc.) + 3 modifs nouvelles (bi ≤15, OR ≤45.3 bps, short).
- Si DSR_filtré ≤ 0.95 → REJET (le filtre n'est pas robuste à multiple-testing déflation).
- DSR ≤ 1 = pas statistiquement distinguable de zéro après correction Bailey-LdP.

### 4.4 Rescaling temps-en-marché (L19)

- **Le comparatif baseline DOIT être rescalé au même temps-en-marché que le filtré.**
- Le filtre retient 17% des trades : si on compare brutalement mean_R_filtré vs mean_R_baseline non rescalé, on compare 17% des opportunités vs 100%. Honnêtement il faut sizer le baseline pour le même nombre de trades (= mêmes contraintes de capital déployé), OU comparer Sharpe annualisé sur le même horizon temporel.
- Méthodologie L19 : Sharpe = mean_per_trade × sqrt(trades_per_year_filtré) / std_per_trade. Comparer Sharpe_filtré OOS vs Sharpe_baseline OOS, PAS mean_per_trade brute.

### 4.5 Two-sided check L25

- **Décomposer la performance signature OOS par régime macro** (au minimum : bull / bear / sideways selon SP500 trend ou VIX régime).
- Si la performance signature OOS provient **exclusivement** d'un régime baissier (bear OOS = forcément si OOS commence ~2026-07), alors c'est du **beta short** déguisé, pas un alpha intrinsèque. L25 rejet.
- Critère opérationnel : `mean_R_filtré_OOS_bull ≥ 0` requis (pas seulement bear).

### 4.6 Verdict final

| Condition | Pass requis |
|---|:---:|
| §4.1 mean_R_filtré > mean_R_baseline | ✓ |
| §4.2 t-HAC6 ≥ 1.5 sur différentiel | ✓ |
| §4.3 DSR_filtré > 0.95 (N_trials=11) | ✓ |
| §4.4 Comparatif rescalé L19 (Sharpe filtré > Sharpe baseline) | ✓ |
| §4.5 Two-sided L25 (mean_R_filtré_bull ≥ 0) | ✓ |

**TOUTES** doivent être satisfaites pour ACCEPTÉ. Si **une seule** échoue → **REJETÉ**, et la signature est archivée comme overfit in-sample N=40, à ne PLUS jamais re-tester.

---

## 5. Règles anti-mining (inscrites dans le contrat)

### 5.1 Verrouillage des seuils

- **Une seule passe OOS** autorisée. Le sample OOS, une fois vu, est consommé.
- **Aucun re-test itératif** avec des seuils modifiés. Si bi=15 échoue, on n'essaie PAS bi=10 ou bi=20.
- **Aucune introduction de nouvelle variable** après visualisation OOS. Les 3 sont définitives.
- **Aucun changement de cut-off de période OOS** (date début = 2026-07-01 strict). Pas de "essayons à partir de 2026-09 plutôt".

### 5.2 Risque de couper le tail explicitement signalé

- **Le filtre coupe 50% des jackpots in-sample** (20/40). Ce n'est pas un détail : si le tail OOS suit la même structure non-conditionnable, le filtre **manquera 50% des trades qui font 93% du P&L baseline**.
- Implication : le filtre doit avoir un **mean_R_filtré >> mean_R_baseline** (pas juste +ε) pour compenser le tail coupé. Si Δ_mean ≤ +0.05 R/trade OOS, le filtre est probablement destructif net.
- Surveillance obligatoire : sur OOS, calculer **n_jackpots_capturés / n_jackpots_total** où jackpot OOS = R_OOS ≥ p99 OOS. Si ratio ≤ 50% → flag rouge.

### 5.3 Pas de p(pass) "amélioré" rapporté ailleurs avant validation OOS

- Aucun document, aucune mémoire, aucune communication ne doit citer un chiffre p(funded) sous signature appliquée tant que le gate §4 n'est pas validé.
- Les chiffres existants (p(funded) terminal 57%, sprint 8w 5%/17%/33%) sont les chiffres NON-filtré ORB V2+E7 baseline. Ils restent les références.

### 5.4 Archivage en cas de rejet

- Si le gate §4 échoue : `data/ftmo_research/PRESPEC_orb_signature_2026-06.md` reçoit un suffixe `__REJECTED_<date>` et est déplacé dans `data/ftmo_research/archived/`.
- La signature est marquée "overfit N=40 in-sample" dans STRATEGY_RESEARCH_LOG.md.
- **Aucune ré-ouverture avant** : (a) nouveau sample ≥ N_min indépendant disponible, (b) hypothèse alternative pré-enregistrée séparément avec mécanisme nouveau et seuils dérivés d'un cadre théorique externe (pas re-mining du sample).

---

## 6. Données OOS requises avant test

### 6.1 Période OOS

- **Date début** : 2026-07-01 (strict). Aucun trade avant cette date n'entre dans le test.
- **Date fin minimum** : 2027-07-01 (12 mois minimum). Idéalement 2028-01-01 (18 mois).

### 6.2 N minimum OOS

ORB ≈ 1 trade par RTH-day après V2 filter (252 trades/an environ).

Avec retention 17% du filtre :
- **n_filtered_OOS ≈ 252 × 0.17 = 43 trades / an OOS**.

Puissance statistique requise (test t ≥ 1.5 sur Δmean) :
- Δ_OOS hypothétique = +0.10 R/trade (effet modéré) : n_filtered ≥ (1.5 × 1.2 / 0.10)² = **324 trades**, soit **~7.5 ans OOS** — impraticable.
- Δ_OOS = +0.20 R/trade (effet large) : n_filtered ≥ **81 trades**, soit **~22 mois OOS**.
- Δ_OOS = +0.30 R/trade (effet très large, in-sample ~+0.45 R) : n_filtered ≥ **36 trades**, soit **~10 mois OOS**.

**N_min figé** : **n_filtered_OOS ≥ 80 trades** ET **N_total_OOS ≥ 480 trades** (= ~22 mois OOS, mid-2028). Plus court = puissance insuffisante pour détection robuste, on attend.

### 6.3 Conditions d'admissibilité du sample OOS

- Sample ORB V2+E7 reconstruit avec **exactement la même méthodologie** que `nq_v2_trades.parquet` (M1 NQ databento, OR 09:30-10:00 ET RTH, V2 dust filter ≥ 10 bps, E7 trail-to-BE +1R, stop opposite side, RTH close exit, coût 0.4 bps RT).
- Pas de modification de la grille ORB sous-jacente entre temps.
- Si la grille évolue (autre coût, autre OR window) : nouveau PRESPEC requis, ce PRESPEC est invalidé.

---

## 7. Honnêteté résiduelle

- **N=40 in-sample** est extrêmement faible pour 3 variables Bonferroni. P(le filtre soit faux positif) reste élevé même si gate §4 passe — la décision OOS doit être interprétée prudemment.
- **Le filtre coupe 50% du tail in-sample**. C'est probablement le risque dominant : couper plus de jackpots que d'éviter de bust paths.
- **La mesure de coût à 15h30 reste l'item dominant**. Si bps_RT ≥ 3 à l'open, p(funded) ≈ placebo container → l'edge est mort AVANT tout filtre, et ce PRESPEC devient sans objet. Vérifier la mesure de coût AVANT de consommer le sample OOS pour le test signature.
- **Pas de promesse de gain de p(funded)**. Si gate §4 passe, l'amélioration de p(funded) reste à mesurer séparément avec un nouveau MC bootstrap sur la série filtrée OOS — et ce calcul, lui aussi, devra être pré-enregistré.

---

## 8. Métadonnées du contrat

- **Date de figeage** : 2026-06-03
- **Hash de référence du diagnostic** : `ORB_structure_diagnostic_2026-06.md` (auteur du diagnostic in-sample)
- **Hash du ledger canonique in-sample** : `data/ftmo_research/audit/nq_v2_trades.parquet` (4013 trades, 2010-2026)
- **Seuils figés numériquement** :
  - `bi_threshold = 15` (minutes)
  - `or_range_bps_threshold = 45.3166` (= np.percentile(or_range_bps_in_sample, 40))
  - `direction_filter = -1` (short only)
- **N_min OOS figé** : `n_filtered ≥ 80 ET N_total ≥ 480`
- **Date OOS début** : 2026-07-01
- **Date OOS fin minimum** : 2028-05-01 (22 mois)
- **N_mod cumulé pour DSR** : **11**

---

## 9. Engagement

> Ce contrat est figé au 2026-06-03. Toute modification, ajustement, ré-optimisation ou ré-interprétation post-OOS = invalidation automatique du test et archivage en `data/ftmo_research/archived/PRESPEC_orb_signature_2026-06__INVALIDATED_<date>.md`. Aucune décision d'allocation propfirm ne sera prise sur la base de la signature sans avoir validé l'ENSEMBLE des critères §4 sur le sample OOS spécifié §6. Si le gate échoue, la signature est définitivement abandonnée — pas re-mining, pas re-essai sur sample re-cut.
