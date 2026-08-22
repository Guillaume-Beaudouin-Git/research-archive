# ORB V2+E7 — Régime nowcast & forward predictability — 2026-06-03

**Ledger** : `data/ftmo_research/audit/nq_v2_trades.parquet` (4013 trades, 2010-06-07 → 2026-05-29). V2 baseline + E7 lift +0.015 R, coût 0.4 bps RT.
**Spec figée V2+E7**, aucune modification du signal (L10).
**192 mois** disponibles avec ≥5 trades. **Distribution mean_R mensuel** : mean +0.054, std 0.257, p25=-0.13, p50=+0.036, p75=+0.22.

**Cadre méthodologique** :
- Stage 1 = descriptif (où sommes-nous).
- Stage 2 = falsification d'une petite liste pré-définie de prédicteurs (prior fortement négatif per L15).
- Aucun mining ; rapporter les résultats même négatifs.

---

## STAGE 1 — NOWCAST (où sommes-nous maintenant ?)

### Classification régime mensuel

| Régime | Seuil mean_R | n_mois | % |
|---|---|---:|---:|
| **Favorable** | ≥ +0.08 | 86 | 45% |
| **Neutre** | [0, +0.08) | 23 | 12% |
| **Défavorable** | < 0 | 83 | 43% |

### Distribution historique mensuelle (192 mois)

| Percentile | mean_R |
|---:|---:|
| p5 / p10 / p25 | −0.33 / −0.27 / −0.13 |
| **p50 (médiane)** | **+0.036** |
| p75 / p90 / p95 | +0.22 / +0.37 / +0.49 |
| moyenne / std | +0.054 / 0.257 |

### Position du présent

| Fenêtre | Période | n_trades | mean_R | Percentile historique | Régime |
|---|---|---:|---:|---:|---|
| 3 derniers mois | 2026-03 → 2026-05 | 63 | +0.049 | 52e | **NEUTRAL** |
| 6 derniers mois | 2025-12 → 2026-05 | 125 | +0.077 (weighted +0.076) | 54e | **NEUTRAL** |
| 12 derniers mois | 2025-06 → 2026-05 | 252 | +0.055 (weighted +0.062) | 52e | **NEUTRAL** |

### Détail mois par mois — derniers 12 mois

| Mois | n_trades | mean_R | hit | Régime |
|---|---:|---:|---:|---|
| 2025-06 | 19 | **−0.336** | 32% | unfavorable |
| 2025-07 | 23 | −0.081 | 43% | unfavorable |
| 2025-08 | 21 | +0.175 | 52% | favorable |
| 2025-09 | 21 | −0.030 | 52% | unfavorable |
| 2025-10 | 23 | **+0.636** | 57% | favorable (mois exceptionnel) |
| 2025-11 | 20 | −0.162 | 45% | unfavorable |
| 2025-12 | 21 | −0.004 | 43% | unfavorable |
| 2026-01 | 21 | +0.147 | 57% | favorable |
| 2026-02 | 20 | +0.170 | 75% | favorable |
| 2026-03 | 21 | +0.078 | 48% | neutral |
| 2026-04 | 21 | +0.296 | 52% | favorable |
| **2026-05** | 21 | **−0.226** | 38% | **unfavorable** |

**Observation** : **forte alternance mois-à-mois** (cohérent avec mean-reversion détectée Stage 2). Pas de tendance unifiée. Le mois courant 2026-05 est défavorable, mais la moyenne 6mo reste neutre/légèrement positive grâce à octobre 2025 (+0.64, exceptionnel).

### p(funded) FTMO 2-step CONDITIONNEL au régime actuel

MC block-bootstrap 12000 paths, no time limit, blocs 21 trades, seed=17. Échantillonnage uniquement sur les trades de la fenêtre indiquée.

| Sample | n_trades | mean_R sample | sizing 1.0% | sizing 1.5% | sizing 2.5% |
|---|---:|---:|---:|---:|---:|
| **Full 16y** (baseline) | 4013 | +0.0552 | **57.1%** | 47.4% | 40.0% |
| Last 12mo | 274 | +0.0460 | **66.8%** | 53.1% | 41.4% |
| Last 6mo | 145 | +0.0433 | **94.5%** | 83.4% | **63.9%** |

**⚠ Caveat critique sur le 94.5%** :
- Sample 145 trades sur 6 mois, blocs bootstrap 21 trades → **seulement ~7 blocs distincts à recombiner**. Variance MC élevée.
- Le sample inclut **octobre 2025 (+0.64 mean_R)** qui domine et est échantillonné en boucle dans les paths.
- **C'est une borne haute optimiste, pas une estimation fiable**. Le 12-mois sample (66.8%) est plus crédible.
- Si on avait une vraie probabilité 94% à sizing 1% en régime actuel, le challenge serait quasi-acquis. Méfiance : **N=145 + bootstrap clustering = sur-estimation probable**.

### Verdict Stage 1

> **Régime actuel ≈ NEUTRE** (52-54e percentile historique, alternance mois-à-mois marquée). Le mois courant 2026-05 est défavorable mais la moyenne 6mo reste légèrement positive. Le p(funded) conditionnel au régime récent est **66.8% à 1% sizing sur 12mo (modérément supérieur au 57% baseline)** ; le 94.5% sur 6mo est statistiquement non fiable (N=145, ~7 blocs distincts).

---

## STAGE 2 — FORWARD PREDICTABILITY (falsification)

**Prior fortement négatif** (L15). Liste de prédicteurs pré-définie, AUCUN mining post-hoc. Régressions OLS univariées avec t-HAC Newey-West lag 6, sur 181 mois (après lead M+1/M+2).

### Régression mean_R(M+1) ~ feature(M)

| Prédicteur | β | t_HAC6 | R² | n | Gate (\|t\|>2.5 ET R²>2%) |
|---|---:|---:|---:|---:|:---:|
| VIX_eom | +0.0007 | +0.30 | 0.04% | 191 | ❌ |
| VIX_term_slope (VIX/VIX3M) | −0.081 | −0.31 | 0.06% | 184 | ❌ |
| NQ_vol_20d | +0.033 | +0.23 | 0.02% | 182 | ❌ |
| NQ_dist_MA200 | +0.124 | +0.56 | 0.13% | 182 | ❌ |
| NQ_above_MA200 (binary) | −0.002 | −0.06 | 0% | 182 | ❌ |
| **ORB_mean_R_M (auto-persistance)** | **−0.120** | **−2.12** | **1.46%** | 191 | ❌ (\|t\|<2.5, R²<2%) — weak |

### Régression mean_R(M+2) ~ feature(M)

| Prédicteur | β | t_HAC6 | R² | n | Gate |
|---|---:|---:|---:|---:|:---:|
| VIX_eom | −0.001 | −0.49 | 0.08% | 190 | ❌ |
| VIX_term_slope | −0.126 | −0.57 | 0.14% | 183 | ❌ |
| NQ_vol_20d | +0.059 | +0.38 | 0.06% | 181 | ❌ |
| NQ_dist_MA200 | +0.316 | +1.31 | 0.88% | 181 | ❌ |
| NQ_above_MA200 | +0.040 | +0.77 | 0.35% | 181 | ❌ |
| ORB_mean_R_M | −0.027 | −0.37 | 0.08% | 190 | ❌ |

### Split OOS — train month <2019, test ≥2019 (M+1 only)

| Prédicteur | β_IS | t_IS | R²_IS | β_OOS | t_OOS | R²_OOS | Sign holds ? |
|---|---:|---:|---:|---:|---:|---:|:---:|
| VIX_eom | +0.003 | +0.60 | 0.3% | −0.003 | −1.17 | 0.8% | FLIP |
| VIX_term_slope | +0.26 | +0.94 | 0.5% | −0.39 | −1.21 | 1.9% | FLIP |
| NQ_vol_20d | −0.36 | −1.31 | 1.1% | +0.05 | +0.34 | 0.1% | FLIP |
| NQ_dist_MA200 | +0.27 | +0.75 | 0.3% | +0.04 | +0.18 | 0% | hold (t<2) |
| NQ_above_MA200 | +0.07 | +1.57 | 0.9% | −0.05 | −1.15 | 0.6% | FLIP |
| **ORB_mean_R_M (auto)** | **−0.158** | **−2.01** | 2.5% | **−0.121** | **−1.65** | 1.4% | **✓ HOLD** |

### Lecture

- **5 des 6 prédicteurs externes échouent complètement** sur M+1 (|t|<1, R²<0.15%). Sur M+2 idem (max |t|=1.31).
- **L'unique candidat marginal est l'ORB auto-persistance** : mean_R(M+1) ~ mean_R(M) donne β=−0.12, t=−2.12, R²=1.5%. Sur OOS, β=−0.12 (hold sign), t=−1.65 (juste sous le seuil 1.65).
- **Direction = négative** : un bon mois prédit un MOIS SUIVANT MOYEN (mean-reversion mensuelle), pas un bon mois. Cohérent avec l'autocorrélation R lag-1 négative trouvée au niveau trade (orb_structure_diagnostic).
- **R² = 1.5%** : 1.5% de la variance mensuelle expliquée. Économiquement marginal.

### Test post-hoc important — cohérence avec diagnostic précédent

Dans `ORB_2mois_diagnostic_2026-06.md`, on avait :
- VIX_prev (sur R des trades, lag 1 jour) : |t|=−0.37 → aucune corr.
- Cohérent : **VIX inutile à toutes les échelles** (trade lag 1 jour, mois lag 1 mois). Confirmé.

### Verdict Stage 2

> **Aucun prédicteur ne franchit le gate strict** (t-HAC>2.5 ET hold OOS ET R²>2%). Le seul candidat marginal est l'**auto-persistance ORB** (β=−0.12, t=−2.12 IS, t=−1.65 OOS, R²=1.5%), de signe négatif (mean-reversion). **Aucune variable externe** (VIX, vol NQ, trend MA200) ne prédit le régime ORB forward. **L15 confirmé empiriquement** : le régime n'est pas prévisible avec les indicateurs macro standards.

---

## VERDICT 2 LIGNES (réponse à la question utilisateur)

> **(a) Régime actuel : NEUTRE** (52-54e percentile historique, mois courant 2026-05 défavorable mais 6mo positif sur octobre 2025 exceptionnel) ; p(pass) conditionnel honnête = **66.8% à sizing 1% sur sample 12mo** (le 94.5% sur 6mo est sur-estimé par bootstrap clustering N=145).
>
> **(b) Peut-on prédire le régime du challenge à venir : NON.** Aucun prédicteur externe ne passe le gate (VIX/term-structure/vol_NQ/MA200 tous |t|<1.5, R²<1%). Seule l'auto-persistance ORB mois-à-mois (β=−0.12, mean-reversion) tient OOS mais sous le seuil strict (|t|=1.65 OOS, R²=1.5%). **Le régime ne se télégraphie pas.** L15 confirmé.

---

## Caveats / honnêteté

1. **N=181 mois** pour les régressions — sample modéré, puissance pour détecter des effets faibles mais limitée.
2. **6 prédicteurs testés** → Bonferroni 0.05/6 = 0.0083 → aucun n'aurait franchi le seuil corrigé.
3. **Le p(funded) conditionnel 94.5% sur 6mo est statistiquement faible** — block-bootstrap sur 145 trades avec block=21 ne crée que ~7 blocs distincts. Le 12mo (66.8%) est la borne honnête.
4. **L'auto-persistance négative (mean-reversion mensuel)** est connue dans la littérature TSMOM/short-term reversal. Pas exploitable comme "edge" — c'est une caractéristique structurelle qui dit juste que les bons mois ne se suivent pas.
5. **Le challenge ORB est conditionnel au coût à 15h30 NON MESURÉ**. Toute discussion régime est conditionnelle à cette mesure ; à 3 bps RT, p(funded) ≈ placebo container avant tout effet régime.
6. **Le résultat "régime non prévisible"** est un résultat en soi, pas un échec. Il signifie : tu ne peux pas timer le challenge sur la base de variables macro standards. Tu peux juste prendre la moyenne 16 ans (57% sizing 1%) comme estimation ex-ante, sans bonus régime.

---

## Artéfacts

- `data/ftmo_research/audit/orb_regime_2026.py` — script Stage 1 + Stage 2
- `data/ftmo_research/audit/orb_regime_2026_log.txt` — log d'exécution complet
- `data/ftmo_research/audit/orb_regime_ppass_conditional.csv` — p(funded) par sample
- `data/ftmo_research/audit/orb_regime_forward_predictors.csv` — table régressions M+1 et M+2
- Réutilise : `nq_v2_trades.parquet` + `nq_rth_daily.parquet` + `vix.csv` + `vix_term_structure.csv`
- Cohérent avec : `ORB_2mois_diagnostic_2026-06.md` (VIX_prev |t|=0.37 sur R), `ORB_structure_diagnostic_2026-06.md` (autocorr R lag-1 négatif), `PRESPEC_orb_signature_2026-06.md`
