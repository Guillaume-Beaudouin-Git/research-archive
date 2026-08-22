# ORB V2+E7 — Verdict 2 mois (cap dur) + diagnostic descriptif — 2026-06-03

**Ledger canonique** : `data/ftmo_research/audit/nq_v2_trades.parquet` (4013 trades V2 baseline) + E7 lift +0.015 R uniform. **Coût FIXE = 0.4 bps RT** (borne haute mesurée hors-open). Spec **FIGÉE V2+E7** — aucune modification du signal (L10/L19).

**Distribution R utilisée** : mean = +0.0552 R/trade, std = 1.201, skew = +1.66, kurt(excess) = +6.73, hit_rate = 45.0%, max win = +13.74 R, max loss = -1.094 R.

---

## PARTIE 1 — Verdict binaire à 8 semaines (cap dur)

Règles : block-bootstrap blocs 21 trades, 12000 paths, seed=17. FTMO 2-step SETTLED. **Cap dur = 40 trades total P1+P2**. Tout path qui n'a pas atteint la cible (P1 ≥+10% PUIS P2 ≥+5%) à 40 trades = FAIL (même s'il aurait passé plus tard).

| Sizing | **% PASSED ≤ 8 sem** | % BUST ≤ 8 sem | **% NI-NI à 8 sem** |
|---:|---:|---:|---:|
| 1.0% | **4.97%** | 7.63% | **87.40%** |
| 1.5% | **16.72%** | 25.63% | **57.66%** |
| 2.5% | **33.43%** | 52.37% | 14.20% |
| 3.0% | **34.48%** | 59.23% | 6.29% |
| 4.0% | **32.35%** | 66.72% | 0.92% |

**Lecture** :
- À sizing 1% : 87% des paths sont encore en course à 8 sem → cap dur transforme 57% (terminal no-time) en **5% (sprint 2 mois)**.
- L'optimum sizing pour un sprint 2 mois est ~3.0% (34.48% passed), pas 1% — mais 59% bust et 0% de retraite (NI-NI tombe à 6%).
- À sizing 4% : tout est décidé en 8 sem (NI-NI < 1%) — mais 67% bust.
- Le sprint 2 mois est structurellement défavorable au sizing prudent. **Conclusion identique au délivrable précédent** : sans time limit, ORB V2+E7 a un edge ; en sprint 2 mois, il devient un coin-flip biaisé négatif.

`sanity check` : `passed + busted + neither = 100.00%` pour tous les sizings (bug original corrigé : un path qui passe la cible AVANT bust n'est plus compté dans bust quand bust arrive après pass dans la même fenêtre).

Artéfact : `data/ftmo_research/audit/orb_2mois_hardcap8w.csv`

---

## PARTIE 2 — Diagnostic descriptif (analyses brutes, AUCUN tuning)

> **Cadre méthodologique strict** : ces analyses décrivent la structure du ledger. Aucun filtre n'est appliqué, aucun chiffre de p(pass) "amélioré" n'est rapporté. Si une variable corrèle au R, elle est listée comme **hypothèse à pré-enregistrer et tester OOS** dans la section finale — pas comme un résultat actionnable.

### 2.1 Distribution des R par trade — où vient le P&L ?

| Percentile | R |
|---|---:|
| p1 / p5 / p10 / p25 | −1.007 / −0.999 / −0.996 / −0.992 |
| **p50 (médiane)** | **−0.203** |
| p75 / p90 / p95 / p99 | +0.768 / +1.615 / +2.181 / +3.765 |
| Max win / Max loss | +13.744 / −1.094 |

**Contribution au P&L total (R cumulés sur 4013 trades = +221.4 R) :**

| Tranche | n_trades | Contrib (R) | % du total |
|---|---:|---:|---:|
| Top 1% winners | 40 | **+206.6** | **93%** |
| Top 5% winners | 200 | +649.2 | 293% (!) |
| Bottom 5% losers | 200 | −201.1 | −91% |
| **Sans top 5%** | 3813 | **−427.8** | mean **−0.112 R/trade** |
| **Sans top 1%** | 3973 | **+14.9** | mean **+0.004 R/trade** |

**Lecture** : l'edge est **entièrement concentré dans le top 1% des trades**. Sans ces 40 trades sur 4013, le mean_R tombe à +0.004 R (≈ zéro). Sans le top 5%, le P&L devient nettement négatif. **C'est une distribution lourdement skewed** (skew +1.66, kurt +6.73) : profil typique d'une stratégie de momentum à TP non-bornée (E7 trail jusqu'à RTH close) + stop borné à -1R.

→ Implication structurelle : la stratégie dépend de quelques "trades miracle" qui font tout le travail. Un sprint 8 semaines (= 40 trades) a donc une probabilité élevée de NE PAS contenir un de ces 40 trades top 1% (40 trades sur 4013 = ratio 0.01 → P(au moins 1 top 1% dans 40 trades) ≈ 1 − 0.99^40 ≈ 33%). Cohérent avec le 34% passed à sizing 2.5-3%.

### 2.2 Mécanisme de bust (MC paths busted ≤ 8 sem @ sizing 2.5%)

12000 paths simulés, **4497 bustés (37.5%)**. Analyse de la séquence trade-par-trade des bust paths :

| Mesure | Valeur |
|---|---|
| **Trade trigger** (dernier R avant bust) | mean = −0.95 R / médiane = −0.99 R / min = −1.09 / max = −0.02 |
| P(trigger ≤ −1R) | 13.0% (= un stop normal qui tombe pile sur le seuil cumulé) |
| P(trigger ≤ −1.5R) | **0.0%** (jamais — le ledger n'a pas de R en dessous de −1.094) |
| P(trigger ≤ −2R, gap fail) | **0.0%** |
| **Run de pertes consécutives** juste avant bust | mean = 3.7 / médiane = 4 |
| P(≥ 2 pertes consec) | 89.9% |
| P(≥ 3 consec) | 70.6% |
| P(≥ 5 consec) | 36.4% |
| P(≥ 8 consec) | 2.1% |
| **Cumul R au moment du bust** | mean = −4.44 / médiane = −4.40 / min = −5.08 |
| P(bust via accumulation, cumsum ≤ −3R) | **100%** |
| Single-trade trigger (R ≤ −1.5) | **0.0%** |
| Accumulation pure | **100.0%** |

**Lecture mécanisme** :
- À sizing 2.5%, 1 stop = 2.5% loss → **un seul trade ne peut JAMAIS déclencher la DLL (5%)** ou le floor (10%). Le bust est **purement path-dependent par accumulation**.
- Le path moyen busté connait **~4 pertes consécutives** dans la séquence finale, atteignant un cumul de **−4.4 R** ≈ **−11% sur le compte** (4.4 × 2.5%), ce qui dépasse la limite Max Total Loss de 10%.
- 36% des bust paths ont une séquence ≥ 5 pertes consécutives juste avant le bust.
- **Pas de fat-tail de bust par gap** : le ledger réel n'a pas de R en-dessous de −1.094 (stop respecté ≥99% des cas, slippage léger sur la dernière 1%).

→ Implication : le risque de bust à sizing 2.5% est **purement clustering de losses**, pas tail-event. Un sizing plus bas (≤ 1.5%) écraserait massivement ce risque mais payerait en bust→neutral (NI-NI explose, 57% à 1.5%).

### 2.3 Corrélations descriptives R vs variables observables AVANT entrée

Toutes les variables sont calculables AVANT l'entrée du trade. Régressions univariées OLS avec t-stat HAC Newey-West lag 6, sur 4013 trades.

| Variable | corr(R, X) | t_HAC6 | n | Flag (seuil \|t\|≥2.5) |
|---|---:|---:|---:|---|
| `or_range_bps` (taille OR en bps) | −0.018 | −1.10 | 4013 | — |
| `bi` (index break après OR close) | −0.022 | −2.29 | 4013 | weak |
| `ttb_5min` (time-to-break en 5-min bars) | −0.022 | −2.29 | 4013 | weak |
| `gap_overnight_bps` (gap close→open bps) | +0.028 | +1.80 | 4012 | weak |
| **`weekday` (0=Mon..4=Fri)** | **+0.038** | **+2.55** | 4013 | **STRONG (\|t\|≥2.5)** |
| `VIX_prev` (close VIX jour J−1) | −0.006 | −0.37 | 3925 | — |
| `direction` (1=long, −1=short) | +0.009 | +0.55 | 4013 | — |

**Lecture** :
- Une seule variable franchit |t|≥2.5 HAC : **weekday** (+0.038, t=+2.55). Direction : R augmente du lundi vers le vendredi (corr +0.038).
- **Mais R² = 0.038² = 0.14%**. L'effet est statistiquement détectable mais économiquement très faible — il explique 0.14% de la variance des R-trades.
- `bi`/`ttb_5min` et `gap_overnight` ont des t-stats entre 1.65 et 2.5 (weak) — NON significatifs au seuil strict.
- `or_range_bps`, `VIX_prev`, `direction` : **rien**.

Artéfact : `data/ftmo_research/audit/orb_2mois_correlations.csv`

### 2.4 Structure 3 pires années (2010, 2013, 2015) vs 3 meilleures (2022, 2023, 2024)

| Variable | Worst (2010,2013,2015) | Best (2022,2023,2024) | Δ (best − worst) |
|---|---:|---:|---:|
| mean_R | −0.039 | +0.151 | **+0.190** |
| hit_rate | 42.5% | 47.8% | +5.3 pp |
| skew | 1.165 | 1.188 | ≈0 |
| p95_R | 1.96 | 2.40 | +0.44 |
| **or_range_med (en POINTS)** | **15.4** | **97.9** | **+82.5 (×6.4)** |
| or_range_bps_med (en bps) | 50.4 | 67.3 | +17 |
| ttb_5min_med | 0.5 | 0.0 | −0.5 |
| vix_med | 17.1 | 19.0 | +1.9 |

**Lecture** :
- Différence dominante structurelle : **or_range en points absolus ×6.4** dans les bonnes années. Mais en bps du sous-jacent, la différence n'est que +17 bps (50 → 67). C'est surtout la **hausse du niveau NQ** (de ~2000 à ~21000) qui élargit le range absolu, pas une vraie hausse de volatilité relative.
- Hit_rate +5.3 pp : les bonnes années ont 47.8% de trades positifs vs 42.5% les pires.
- p95_R +0.44 : queue droite plus large dans les bonnes années (gros gagnants plus gros).
- Skew quasi identique (~1.18) → la forme distribution est stable, ce sont les **niveaux** qui bougent.
- VIX très proche (17 vs 19) — ce n'est PAS un proxy régime utile.
- ttb_5min : break un peu plus rapide dans les bonnes années (0 vs 0.5 minutes).

→ Le différentiel **ne se laisse pas réduire à une seule variable observable**. C'est un cocktail (hit + queue droite) qui se déplace avec le régime macro non capturé par OR_bps, VIX, ou gap.

---

## Pistes candidates — à pré-enregistrer et tester OOS séparément

> **NON appliquées ici, NON tunées sur in-sample.** Liste des variables qui ont franchi le seuil |t|≥2.5 HAC dans 2.3 — à enregistrer comme HYPOTHÈSES, à valider sur sample post-2026 indépendamment, avant tout déploiement.

### Piste 1 — Effet weekday (|t|=2.55, corr=+0.038)

**Hypothèse à pré-enregistrer** : "Le R d'un trade ORB V2+E7 est plus élevé en fin de semaine qu'en début (corr weekday-R = +0.038, monotone)."

**Caractéristiques** :
- Statistiquement significatif au seuil 2.5 HAC sur 2010-2026 in-sample.
- Très faible amplitude économique (R² = 0.14% expliqué).
- Direction Mon → Fri (lundi le moins favorable, vendredi le plus favorable).

**Protocole OOS** (à exécuter SÉPARÉMENT, pas dans ce délivrable) :
1. Geler la grille V2+E7 + ajouter une variable `weekday`.
2. Sur sample 2026-07+ uniquement, mesurer corr(R, weekday) et t_HAC.
3. Si |t|≥2.5 sur OOS ET amplitude économique cohérente avec in-sample → hypothèse confirmée, considérer overlay weekday.
4. Si |t|<1.65 sur OOS → hypothèse rejetée, ne pas déployer.

**ATTENTION (L19/L20)** :
- L'effet est faible (R² 0.14%) — économiquement peu transformatif même si confirmé.
- Pré-enregistrement strict obligatoire avant de re-toucher le ledger in-sample.
- DSR à recalculer si on ajoute weekday comme modification : N_mod actuel ≈ 8 (cf. ORB_reconciliation L20), +1 = 9 → DSR encore plus pénalisé.

### Pistes weak (|t| entre 1.65 et 2.5) — pas de candidat OOS

- `bi` / `ttb_5min` (t=−2.29) : break plus tardif corrèle légèrement négatif. **Pas de pré-enregistrement** (seuil |t|≥2.5 non franchi).
- `gap_overnight_bps` (t=+1.80) : gap up corrèle légèrement positif. **Pas de pré-enregistrement**.

Ces deux variables sont notées pour future référence si le sample s'agrandit (et donc le t-stat) — mais aucune action présente.

### Variables NON candidates (rien)

- `or_range_bps` (t=−1.10) : la taille de l'OR en bps ne corrèle pas au R. Confirme que filtrer sur or_range_bps n'est pas une voie évidente.
- `VIX_prev` (t=−0.37) : VIX préalable inutile comme prédicteur.
- `direction` (t=+0.55) : pas de biais long/short.

---

## Honnêteté résiduelle

- Spec FIGÉE V2+E7. **Aucun filtre n'a été appliqué.** Les corrélations descriptives ne sont PAS des filtres. Le délivrable conclut "weekday franchit |t|≥2.5" — sans recalculer un quelconque p(funded) sous overlay weekday, ce qui serait du mining.
- Si on testait un overlay weekday in-sample maintenant, le p(funded) "amélioré" obtenu serait par construction biaisé (test sur le même sample qui a sélectionné la variable). C'est exactement ce que L10/L19 interdisent.
- L'amplitude économique de l'effet weekday (R²=0.14%) suggère que même OOS-validé, son impact pratique sera marginal — pas un game changer.
- 3 pires années / 3 meilleures : la différence est dominée par le hit_rate (+5pp) et la queue droite (p95 +0.44 R). Aucune variable observable AVANT entrée ne capture ce différentiel — c'est un régime macro non-observable au moment du trade.

---

## Synthèse en 1 paragraphe

> À cap dur 8 semaines, sizing 1% donne **5% passed et 87% NI-NI** (encore en course mais sans avoir atteint la cible) ; l'optimum sprint est sizing ~3% (34% passed, 59% bust). **L'edge ORB est ENTIÈREMENT concentré dans le top 1% des trades (93% du P&L)** — distribution lourdement skewed avec 40 trades miracles sur 4013. **Le bust à sizing 2.5% est 100% par accumulation** (cumul ~−4.4R, ~4 pertes consécutives, jamais par gap single-trade). **Aucune variable observable AVANT entrée n'explique > 0.14% de la variance des R** ; seul `weekday` franchit |t|≥2.5 HAC, à pré-enregistrer comme hypothèse OOS pour test futur indépendant.

---

## Artéfacts

- `data/ftmo_research/audit/orb_2mois_diagnostic.py` — script (PART 1 + PART 2)
- `data/ftmo_research/audit/orb_2mois_diagnostic_log.txt` — log d'exécution complet
- `data/ftmo_research/audit/orb_2mois_hardcap8w.csv` — table PART 1 (5 sizings × passed/bust/neither)
- `data/ftmo_research/audit/orb_2mois_correlations.csv` — table 2.3 corrélations avec t_HAC6
- Réutilise ledger : `data/ftmo_research/audit/nq_v2_trades.parquet` + `data/overnight_research/nq_rth_daily.parquet` (pour gap) + `data/panels/vix.csv` (pour VIX_prev)
- Cohérent avec : `ORB_at_0p4bps_2026-06.md` + `ORB_ppass_grid_2026-06.md` + `ORB_reconciliation_2026-06.md`
