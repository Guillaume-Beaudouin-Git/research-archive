# Phase 2 — Re-mining propre sur dataset clean

> **TL;DR — AUCUN filtre par-trade ne survit honnêtement.** Sur dataset propre
> (NQ futures 2010-2026, exécution next-bar-open, après audit Phase 1 du builder),
> 23 features individuelles testées, 4 hypothèses 2-conditions pré-enregistrées,
> régime decomposition 5 buckets, bootstrap par blocs, stress slip+cost,
> DSR avec n_trials honnête (150). Le meilleur candidat **H1 (long break +
> positive gap + above PDH)** atteint Sharpe annuel 1.05, Δ R=+0.082R sur
> baseline -0.011R, 5/5 régimes positifs, bootstrap CI [+0.013, +0.152]
> exclut 0 — **MAIS** DSR_p = 0.23 (mining trop profond pour Sharpe 1.05),
> stress cost 1.5× + slip 0.05R réduit Sharpe à -0.09, 7/16 années perdantes.
> Le baseline ORB NQ next-bar-open est légèrement négatif (-0.011R/trade) et
> aucun filtre cumulant 2 conditions ne le redresse de façon robuste. La
> nouvelle dimension volume (or_vol_total, vrai VWAP, or_vol_skew) n'apporte
> pas d'edge réplicable. **Phase 2 verdict : NO viable per-trade filter.
> Le baseline nu reste le meilleur — qui est lui-même non-tradable
> intra-jour next-bar-open sur 2010-2026 net de coûts.**

---

## 1. Méthode

Toutes les analyses ici tournent sur `trade_dataset_clean.parquet` (4012 trades
avec `r_exec_nextopen` non-NaN, 2010-06-07 → 2026-05-29, NQ futures 09:30 ET
30-min OR, exécution next-bar-open, cost RT = 1.0 pt). Le dataset est issu de
Phase 1 et garanti correct (cf. `FEATURE_BUILDER_audit.md`).

**Cible standard** : `r_exec_nextopen` (clean exec). On rapporte aussi
`r_exec_level` (same-bar legacy) en stress test.

**Baseline** : mean R = -0.0105, std = 1.178, Sharpe daily ann = -0.142,
skew = +1.54, hit rate = 43.2%, top-décile R = 2.43. Le **baseline est
légèrement négatif net de coûts sur 2010-2026** (cf. §6 du Phase 1 audit
pour la décomposition vs le verdict d'audit antérieur). **Tout filtre doit
améliorer cela de façon robuste pour avoir une chance.**

**Garde-fous (issus de Phase 1 §8) :**
1. Split-by-direction obligatoire (L25).
2. Évaluation sur R + top-décile preserved, pas win-rate.
3. Filtres ≤ 2 conditions (L10).
4. Exécution propre.
5. Régime decomposition 5 buckets sur 2010-2026.
6. DSR avec n_trials honnête.
7. Ablation L19 obligatoire.
8. Bootstrap par blocs pour CI sur delta R.
9. NE PAS re-vendre comme edge : `or_range` / `or_range_atr_ratio` (artefact
   arithmétique), `time_to_break` (bug F1), daily/régime pour timing inter-jour.

---

## 2. Univariate scan — surface de features (Phase 2 §2.1)

23 features auditées, 3 subsets (ALL / LONG / SHORT), target r_exec_nextopen.
Métriques : ρ_Spearman, t_HAC lag-6, Δ mean-R Q5, Δ mean-R Q1, top-décile capture
dans Q5 du feature (référence = kept_pct ≈ 20% pour une feature continue).

### 2.1 Compte des survivants par filtre logique

| Filtre | ALL | LONG | SHORT |
|---|---:|---:|---:|
| `|hac_t| > 2.5` | 4 features* | 0 | 1 (day_of_week) |
| `|hac_t| > 1.5` + `dQ5_R > 0` + `topdec ≥ 20` | 4 | 6 | 2 |
| `|hac_t| > 2.5` + `dQ5_R > 0` + `topdec ≥ 25` | 1 (day_of_week) | 0 | 0 |

*`or_range` et `or_range_atr_ratio` retirés (artefact arithmétique). Autres :
`or_vol_total`, `day_of_week`, `time_to_break_5min` (négatif), `dist_to_pdl_R`.

### 2.2 Top candidats LONG (par |t_HAC|)

| Feature | n | ρ_S | t_HAC | Δ Q5 R | Δ Q1 R | topdec_capt% |
|---|---:|---:|---:|---:|---:|---:|
| `gap_pct` | 2155 | +0.055 | **+2.46** | +0.124 | -0.039 | 23.1 |
| `dist_to_pdl_R` | 2155 | +0.023 | +2.30 | +0.111 | -0.024 | 27.3 |
| `dist_to_pdh_R` | 2155 | +0.054 | +2.17 | **+0.158** | +0.029 | **27.3** |
| `or_vol_5m_std` | 2156 | -0.017 | -2.11 | -0.033 | +0.077 | 16.2 |
| `gap_dir` | 2155 | +0.044 | +2.00 | +0.041 | -0.052 | 58.8 |
| `gap_concord` | 2146 | +0.044 | +2.00 | +0.040 | -0.052 | 59.1 |
| `pre_break_range_R` | 2156 | -0.041 | -1.97 | -0.035 | +0.041 | 16.7 |

### 2.3 Top candidats SHORT (par |t_HAC|)

| Feature | n | ρ_S | t_HAC | Δ Q5 R | Δ Q1 R | topdec_capt% |
|---|---:|---:|---:|---:|---:|---:|
| `day_of_week` | 1856 | +0.043 | **+2.18** | +0.064 | -0.049 | 45.2 |
| `or_vol_total` | 1856 | +0.104 | +2.11 | +0.092 | -0.129 | 18.3 |
| `time_to_break_5min` | 1856 | +0.016 | -2.03 | -0.071 | -0.015 | 14.5 |
| `or_vol_concord` | 1856 | -0.020 | -1.32 | -0.122 | +0.049 | 16.1 |

### 2.4 Lecture honnête du scan

- **Aucun feature LONG-only ni SHORT-only ne survit |t_HAC| > 2.5** au seuil
  strict habituel pour IC feasibility.
- Les meilleurs candidats sont tous à |t_HAC| 1.97-2.46 — région d'incertitude.
- `dist_to_pdh_R` long est le plus prometteur sur top-décile capture (27.3%)
  et magnitude (+0.158 Q5 vs Q5 baseline).
- L'asymétrie LONG/SHORT est massive : tous les Q5 R positifs sont sur LONG.
  Sur SHORT, seul `or_vol_total` a Q5 R clairement positif (+0.092). Le NQ
  futures sur 2010-2026 a un drift positif clair qui rend les short breakouts
  structurellement défavorables (mean_R SHORT baseline = -0.034 vs LONG +0.010).
- Ceci n'est PAS une violation de L25 en soi (split-by-direction obligatoire) —
  mais ça contraint les hypothèses : on cherchera surtout des filtres long-only
  ou des filtres symétriques qui compensent l'asymétrie de drift.

### 2.5 Régime decomposition des top candidats

Buckets 5 ans : 2010-12, 2013-15, 2016-18, 2019-21, 2022-26. t_HAC par bucket
(target r_exec_nextopen, Q5 de chaque feature) :

| Feature | 10-12 | 13-15 | 16-18 | 19-21 | 22-26 | regime sign-flip |
|---|---:|---:|---:|---:|---:|---|
| `or_vol_total` | +0.36 | +1.66 | -1.15 | -1.02 | +0.54 | **OUI 2/5 négatifs** |
| `day_of_week` | +0.40 | +1.95 | +0.66 | -0.09 | +2.54 | 1/5 |
| `time_to_break_5min` | +0.02 | +0.20 | **-2.46** | -1.16 | -1.27 | persistent négatif |
| `dist_to_pdl_R` | +0.81 | **+2.33** | -0.07 | **+2.08** | +0.58 | 2/5 t > 2 |
| `or_vol_5m_std` | -0.91 | +0.14 | **-2.44** | **-2.87** | -1.12 | persistent négatif (4/5) |
| `gap_pct` | +1.48 | -0.52 | +1.38 | **+2.53** | +0.20 | 1/5 t > 2 |
| `pre_break_range_R` | -0.76 | -0.63 | **-2.10** | -1.25 | +0.62 | inconsistent |
| `gap_dir` | +1.09 | 0.00 | +0.86 | +1.81 | +0.78 | jamais t > 2 |

**Conclusion §2.5 :**
- Aucun feature ne maintient |t_HAC| > 2 dans ≥ 3 buckets sur 5.
- Les seuls features avec direction *cohérente* à travers les régimes :
  - `or_vol_5m_std` (toujours négatif, 4/5 t < -1 ou t < -2)
  - `pre_break_range_R` (toujours négatif, 3/5 t < -1 ou t < -2)
- Ces deux features partagent la même direction sémantique :
  « moins d'agitation pendant l'OR, moins de range avant le break = meilleurs R ».
  Ce sont des candidats H2 (decisive_OR) ci-dessous.

---

## 3. Hypothèses pré-enregistrées (≤ 2 conditions)

Pré-enregistrées avant tout test approfondi, à partir de la théorie + du
scan §2 :

| ID | Filtre | Théorie |
|---|---|---|
| **H0** | `breakout_dir == 1` | Long-only baseline : NQ a un drift positif structurel |
| **H1** | `dir==1` ET `gap_pct>0` ET `dist_to_pdh_R>0` | Long break momentum : positive gap + above PDH = trend continuation |
| **H2** | `or_vol_5m_std < med` ET `pre_break_range_R < med` | Decisive OR : low intra-OR vol + decisive break = high-conviction structural move |
| **H3** | `or_vol_total > med` ET `dist_twap_at_break_R > med` | Vol confirmation : high volume + break far from TWAP = institutional |
| **H4** | `gap_concord==1` ET (long : `dist_to_pdh_R>0` ; short : `dist_to_pdl_R>0`) | Symmetric trend-aligned (L25-compliant : tested both directions) |

Chaque hypothèse a **2 ablations L19** (drop each condition one at a time)
sauf H0 (1 condition) et H4 (gap_concord est central, voir below).

### 3.1 Summary par hypothèse

Target = r_exec_nextopen. ΔR = mean_R(filt) − mean_R(baseline = -0.0105).
Bootstrap par blocs de 20 jours, 500 iterations, CI 95%.

| Hypothèse | n | kept% | mean_R | **ΔR** | std_R | Sharpe_ann | skew | hit% | top_dec R | topdec_capt% | boot CI lo | boot CI hi |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BASELINE | 4012 | 100 | -0.011 | 0 | 1.18 | -0.14 | 1.54 | 43.2 | 2.43 | 100 | — | — |
| **H0 long-only** | 2156 | 53.7 | +0.010 | **+0.020** | 1.08 | +0.14 | 0.95 | 46.8 | 2.16 | 47.8 | -0.013 | +0.055 |
| **H1 long momentum** | 803 | 20.0 | +0.072 | **+0.082** | 1.08 | **+1.05** | 0.85 | 50.4 | 2.19 | 19.9 | **+0.013** | **+0.152** |
| H1 ablate gap | 933 | 23.3 | +0.063 | +0.073 | 1.06 | +0.94 | 0.83 | 50.0 | 2.14 | 22.1 | +0.011 | +0.138 |
| H1 ablate pdh | 1209 | 30.1 | +0.051 | +0.061 | 1.09 | +0.74 | 0.88 | 48.6 | 2.20 | 28.9 | +0.009 | +0.116 |
| H2 decisive OR | 1033 | 25.7 | +0.040 | +0.051 | 1.30 | +0.49 | 2.00 | 44.4 | 2.70 | 28.6 | -0.006 | +0.106 |
| H2 ablate vol | 2005 | 50.0 | +0.012 | +0.022 | 1.22 | +0.16 | 1.65 | 43.8 | 2.50 | 53.2 | -0.011 | +0.054 |
| H2 ablate range | 2006 | 50.0 | +0.002 | +0.012 | 1.24 | +0.02 | 1.83 | 43.2 | 2.58 | 52.2 | -0.020 | +0.044 |
| H3 vol directional | 983 | 24.5 | +0.037 | +0.048 | 1.20 | +0.49 | 1.42 | 43.6 | 2.55 | 28.1 | -0.019 | +0.113 |
| H3 ablate vol | 2006 | 50.0 | -0.003 | +0.008 | 1.22 | -0.04 | 1.38 | 42.8 | 2.58 | 56.5 | -0.027 | +0.043 |
| H3 ablate dist | 2006 | 50.0 | +0.045 | +0.056 | 1.14 | +0.63 | 1.33 | 45.2 | 2.41 | 50.7 | +0.022 | +0.090 |
| **H4 sym trend-aligned** | 1247 | 31.1 | +0.044 | **+0.054** | 1.10 | +0.63 | 0.88 | 47.5 | 2.23 | 33.6 | **+0.005** | **+0.106** |

### 3.2 Critères de filtrage des candidats

Pour qu'un candidat soit retenu :
- (a) ΔR > 0 robuste
- (b) Bootstrap CI exclut 0
- (c) ≥ 4/5 régimes ΔR > 0
- (d) Ablation L19 : chaque condition apporte > 0
- (e) DSR avec n_trials honnête > 0.5
- (f) Survit stress 1.5×cost + slip
- (g) Top-décile capture ≥ kept_pct (préservation)

**Survivants de (a)(b)(c) :** H1 et H4.
**H2, H3 échouent (b)** (CI incluent 0).
**H0** : CI inclut 0, ΔR=+0.02 marginal.

### 3.3 Régime decomposition H1 et H4 (les survivants partiels)

| Hypothèse | 10-12 ΔR (n) | 13-15 ΔR (n) | 16-18 ΔR (n) | 19-21 ΔR (n) | 22-26 ΔR (n) | régime stable ? |
|---|---|---|---|---|---|---|
| **H1** | +0.137 (131) | +0.114 (152) | +0.018 (156) | +0.126 (161) | +0.052 (203) | **5/5 positifs** |
| **H4** | +0.072 (202) | +0.162 (222) | +0.018 (234) | +0.027 (237) | +0.015 (352) | 5/5 positifs |
| H2 | +0.077 | -0.050 | +0.138 | +0.120 | +0.025 | **4/5** (2013-15 négatif) |
| H3 | -0.004 | +0.013 | -0.151 | -0.045 | +0.055 | **2/5** (régime-unstable) |

H1 et H4 passent (c). H2 borderline (1 régime négatif). H3 fail catastrophique.

### 3.4 Ablation L19 — H1

| Variant | n | ΔR | topdec_capt% | Interprétation |
|---|---:|---:|---:|---|
| H1 full (dir=1 + gap_pct>0 + dist_to_pdh_R>0) | 803 | **+0.082** | 19.9 | base |
| H1 ablate gap (dir=1 + dist_to_pdh_R>0) | 933 | +0.073 | 22.1 | dropping gap_pct → ΔR de +0.082 à +0.073 (gap contribue +0.009) |
| H1 ablate pdh (dir=1 + gap_pct>0) | 1209 | +0.061 | 28.9 | dropping dist_to_pdh_R → ΔR de +0.082 à +0.061 (pdh contribue +0.021) |
| H0 dir=1 only | 2156 | +0.020 | 47.8 | dropping les deux → ΔR=+0.020 |

Les deux conditions ajoutent de la valeur, dist_to_pdh_R plus que gap_pct.
**H1 ablation passe.** Mais la décomposition montre que la majorité du gain
vient de « LONG + above PDH » (Δ +0.061), avec gap_pct ajoutant juste
+0.021 supplémentaire — fragile.

---

## 4. Stress test — coûts et slippage

Re-extraction du dataset avec `cost_mult × {1, 1.5, 3}` et `slip_R × {0, 0.05}`.
slip_R=0.05 = adverse slip de 5% du R (~3 pts par côté sur OR moyen de 55 pts).

| cost_mult | slip_R | BASE Sharpe_ann | **H1 Sharpe_ann** | H4 Sharpe_ann |
|---:|---:|---:|---:|---:|
| 1.0 | 0.00 | -0.14 | **+1.05** | +0.63 |
| 1.0 | 0.05 | -0.85 | **+0.25** | -0.15 |
| 1.5 | 0.00 | -0.43 | **+0.70** | +0.33 |
| 1.5 | 0.05 | -1.14 | **-0.09** | -0.45 |
| 3.0 | 0.00 | -1.30 | **-0.34** | -0.57 |
| 3.0 | 0.05 | -1.99 | **-1.12** | -1.34 |

**Interprétation :**
- Sous le scénario réaliste **cost=1.5× + slip=0.05R** (modèle conservateur
  L19), **H1 Sharpe = -0.09**, breakeven au mieux.
- H1 ne survit pas le seuil PROPFIRM_PASS (Sharpe > 1.0) sous **aucun**
  scénario stress crédible.
- Sous slip 0.05R seul (cost=1×) : H1 Sharpe tombe de 1.05 à 0.25 — **80%
  d'érosion** par le slippage. Edge structurellement fragile.

**Conclusion §4 : H1 ne résiste pas au stress slippage.**

---

## 5. DSR — Deflated Sharpe Ratio Bailey-Lopez de Prado

### 5.1 Honest n_trials estimate

| Source de trial | Count |
|---|---:|
| Univariate scan (23 features × 3 subsets × 2 sides above/below median) | 138 |
| Hypothèses pré-enregistrées (H0-H4 × variants + ablations) | 12 |
| **Total honest** | **150** |
| Conservatif (incluant pairs implicitement explorés) | 500 |

### 5.2 H1 DSR

| n_trials | SR_obs/trade | SR_normalized | E[max] threshold | z vs threshold | **DSR_p** |
|---:|---:|---:|---:|---:|---:|
| 50 (très optimiste) | 0.0662 | 1.927 | 2.276 | -0.350 | 0.363 |
| **150 (honest)** | **0.0662** | **1.927** | **2.670** | **-0.743** | **0.229** |
| 500 (conservatif) | 0.0662 | 1.927 | 3.053 | -1.125 | 0.130 |

Pour qu'un H1 « passe » le DSR, il faudrait n_trials ≤ ~12 (DSR_p > 0.5),
ce qui n'est pas réaliste vu la mining depth réelle.

### 5.3 H4 DSR

| n_trials | SR_normalized | E[max] | z | **DSR_p** |
|---:|---:|---:|---:|---:|
| 150 (honest) | 1.432 | 2.670 | -1.238 | **0.108** |

H4 fail encore plus fort.

### 5.4 Interprétation

Sharpe per-trade 0.066 (annual 1.05) sur 803 trades. Le bruit pur autour de
zéro pour 150 backtests indépendants produit en attendu un Sharpe normalisé
~2.67. H1 obtient 1.93 → en-dessous du seuil de bruit.

**DSR fail.** L'apparent edge de H1 est compatible avec une découverte par
mining.

---

## 6. Annual breakdown H1 — volatilité de la performance

| Year | n_base | n_H1 | mean_R_base | mean_R_H1 | Sharpe_H1 | hit_H1% | sign |
|---:|---:|---:|---:|---:|---:|---:|---|
| 2010 (H2) | 144 | 31 | -0.17 | -0.09 | -1.70 | 54.8 | LOSS |
| 2011 | 253 | 50 | -0.06 | +0.06 | +1.06 | 52.0 | WIN |
| 2012 | 247 | 50 | -0.02 | +0.16 | +1.82 | 50.0 | WIN |
| 2013 | 244 | 57 | -0.14 | -0.16 | -2.33 | 42.1 | **LOSS** |
| 2014 | 244 | 50 | -0.08 | +0.25 | +4.06 | 58.0 | WIN |
| 2015 | 254 | 45 | -0.14 | -0.11 | -1.59 | 42.2 | LOSS |
| 2016 | 251 | 52 | -0.05 | -0.13 | -2.18 | 40.4 | LOSS |
| 2017 | 253 | 51 | -0.02 | +0.22 | +3.37 | 58.8 | WIN |
| 2018 | 252 | 53 | -0.02 | -0.12 | -1.76 | 37.7 | **LOSS** |
| 2019 | 248 | 50 | -0.02 | +0.17 | +2.73 | 56.0 | WIN |
| 2020 | 254 | 57 | -0.04 | -0.00 | -0.02 | 49.1 | BREAKEVEN |
| 2021 | 253 | 54 | +0.06 | +0.22 | +4.01 | 61.1 | WIN |
| 2022 | 253 | 36 | +0.09 | +0.02 | +0.33 | 50.0 | BREAKEVEN |
| 2023 | 251 | 49 | +0.10 | +0.19 | +2.36 | 51.0 | WIN |
| 2024 | 255 | 44 | +0.17 | +0.49 | +5.12 | 61.4 | WIN |
| 2025 | 252 | 49 | +0.08 | -0.18 | -3.39 | 40.8 | **LOSS** |
| 2026 (H1) | 104 | 25 | +0.09 | +0.38 | +5.57 | 60.0 | WIN |

**Résumé annual :**
- WIN : 8 années (2011, 2012, 2014, 2017, 2019, 2021, 2023, 2024) + 2 partielles (2026)
- LOSS : 6 années (2010 partiel, 2013, 2015, 2016, 2018, 2025)
- BREAKEVEN : 2 années (2020, 2022)
- **W:L ratio ≈ 8:6 = 1.33** (excluding partials)
- Volatilité par-année du Sharpe H1 : -3.39 à +5.57 — **range 8.96**.

Le « +1.05 Sharpe » global est une moyenne très volatile. Une propfirm
trading H1 sur une fenêtre 6-12 mois aurait une probabilité non-négligeable
d'être dans une année perdante.

---

## 7. Volume features — la nouvelle dimension

L'apport principal du dataset propre vs CFD était l'accès à la dimension
volume. Features volume testées :

| Feature | t_HAC ALL | t_HAC LONG | t_HAC SHORT | Verdict |
|---|---:|---:|---:|---|
| `or_vol_total` | **+2.82** | +1.94 | +2.11 | régime-unstable (2/5 t<-1, 1/5 t>2) |
| `or_vol_ratio_20d` | -0.54 | -0.54 | -0.35 | rien |
| `or_vol_skew` | +0.92 | +0.14 | +1.32 | rien |
| `or_vol_concord` | -0.89 | +0.14 | -1.32 | rien |
| `dist_vwap_at_break_R` | -0.30 | -0.64 | +0.38 | rien (vs TWAP version) |
| `vol_pre_break` | -0.61 | -0.11 | -0.74 | rien |

`or_vol_total` est le seul candidat « intéressant » mais sa décomposition
régime (§2.5) montre du sign-flipping (2010-12 +0.36, 2016-18 -1.15,
2022-26 +0.54). **La dimension volume ne révèle pas un edge robuste sur NQ
2010-2026**.

Possibles explications :
1. **Microstructure HFT-dominated post-2010** : le volume contient peu
   d'information directionnelle au-delà de ce que le price action contient
   déjà. Le L23b (institutional ≠ retail microstructure edge) s'applique :
   ce qui est extractible par les algos HFT n'est pas exploitable retail.
2. **Mode de calcul du volume sur futures continues** : le sum des volumes
   au sein de 5-min bars masque la composition (large blocks vs small).
3. **Pas de volume profile / footprint** dans les features : on capture
   uniquement les agrégats, pas la distribution.

→ Pour aller plus loin il faudrait des **données market-by-order** ou
**footprint charts** (volume par tick à l'intérieur de la barre).
Pas dans le scope.

---

## 8. Verdict honnête

### 8.1 Y a-t-il un vrai filtre par-trade qui améliore l'espérance à travers les régimes ?

| Critère | H1 | H4 | H2 | H3 |
|---|---|---|---|---|
| (a) ΔR > 0 robuste | ✓ +0.082 | ✓ +0.054 | ✓ +0.051 | ✓ +0.048 |
| (b) Bootstrap CI exclut 0 | ✓ [+0.013, +0.152] | ✓ [+0.005, +0.106] | ✗ [-0.006, +0.106] | ✗ [-0.019, +0.113] |
| (c) ≥ 4/5 régimes ΔR > 0 | ✓ 5/5 | ✓ 5/5 | ⚠ 4/5 (1 négatif) | ✗ 2/5 |
| (d) Ablation chaque condition apporte > 0 | ✓ +0.021 (pdh) +0.009 (gap) | n/a | ✓ +0.030 (vol) +0.040 (range) | ⚠ +0.040 (vol) -0.010 (dist) |
| (e) DSR > 0.5 (n_trials=150) | ✗ DSR_p=0.23 | ✗ DSR_p=0.11 | n/a | n/a |
| (f) Stress 1.5×cost + slip 0.05R Sharpe > 0 | ✗ -0.09 | ✗ -0.45 | n/a | n/a |
| (g) Top-décile capture ≥ kept_pct | ≈ 19.9 vs 20.0 | ✓ 33.6 vs 31.1 | ✓ 28.6 vs 25.7 | ✓ 28.1 vs 24.5 |

**Aucune hypothèse ne passe TOUS les critères. H1, le meilleur candidat,
fail DSR et stress test. Verdict : NO valid filter.**

### 8.2 Pourquoi ce résultat est attendu (et acceptable)

Le brief prévient :
> « la plupart des features étaient du bruit ou buggées » est un résultat
> attendu et précieux, pas un échec.

Le baseline NQ ORB 2010-2026 à exécution next-bar-open est ~-0.011R/trade
net. C'est en cohérence avec :
- L20 (DSR mandatory pour Sharpe sustainability)
- L21 (Sharpe reality check : single-instrument day-trade live 0.8-2.0
  sustainable post-DSR)
- L22 (MC propfirm eval = tool obligatoire avant tout achat)
- L24 (lumpy strategies à WR<30% structurellement ≤44% p(pass) sur propfirm
  symmetric-barrier).

NQ ORB est exactement la stratégie *lumpy* que L24 décrit : LONG hit_rate
46.8%, mais avec une queue droite +1.5 skew. Pour une propfirm avec barrier
symétrique, **même un mean R légèrement positif ne convertit pas en
p(pass) suffisant**. L'edge n'est pas dans la moyenne — il est dans la
queue, qui est précisément ce qui se fait massacrer par les drawdown caps.

### 8.3 Que conserver vs jeter

**À jeter (non-edges identifiés) :**
- `time_to_break_5min` corrigé : ρ=0.001, t_HAC=-2.36, mais aucun pouvoir
  prédictif positif. (Le bug F1 était la totalité du signal apparent.)
- `or_range`, `or_range_atr_ratio` : artefact arithmétique (Phase 1 §6),
  top-décile capture catastrophique (13%).
- `or_vol_total` standalone : régime-unstable, sign-flip.
- H2 (decisive OR), H3 (vol directional) : bootstrap CI incluent 0,
  régime-unstable pour H3.

**À conserver pour analyse future éventuelle :**
- **H1 (long momentum)** comme *paper-research curiosity*, PAS pour
  trading : un filtre dont le mean R apparent +0.08R est entièrement
  compatible avec le bruit pour la profondeur de mining réalisée.
- **`dist_to_pdh_R` long** comme variable de **régime / context**, jamais
  comme filtre standalone : « ouvrir long ORB à condition d'être au-dessus
  de PDH » est un standard du livre de jeu institutionnel mais ici son
  Sharpe propre n'est pas extractible.
- **Méthodologie split-by-direction (L25)** vient d'être validée empiriquement
  comme outil de détection bug + asymétrie de drift.

### 8.4 Recommandation actionnable

1. **NE PAS deployer** H1 ou H4 en paper ou live propfirm sur NQ.
2. **Le baseline ORB NQ next-bar-open n'est pas tradable** : mean R net
   -0.011 sur 16 ans, Sharpe -0.14. Le verdict d'audit antérieur
   (`AUDIT_VERDICT_ftmo_orb.md`) qui rapportait +0.10R/trade était
   contaminé à hauteur de 50% par le bug F1, 30% par le régime favorable
   2022-2025, 20% par l'exécution same-bar optimiste.
3. **Strategy C (iter_10, $25K Tradeify, paper imminent)** doit être
   re-évaluée à la lumière de ces résultats. La config Strategy C utilise :
   - 1 sleeve NQ (mais 09:46 ET entry, donc 15-min OR de 09:30-09:45 ET),
   - VWAP confirmation,
   - gap ≤ 1.2%,
   - opening range ≥ 30pts,
   - $400 SL cap.

   Ces filtres-là **n'ont pas été testés sur 2010-2026 dans le scope de
   cette audit** (le focus était sur le builder Phase 1 + un re-mining
   propre par-trade). À la prochaine session : reproduire iter_10 exact
   sur NQ Databento 2010-2026 et vérifier que le Sharpe 1.52 et la WF
   78% (sur 2022-2025 Kaggle) tiennent sur l'historique étendu et propre.
   Risque élevé d'effondrement sur la même structure que ci-dessus.

4. **L25 confirmé par la pratique** : ajouter à la constitution / methodology
   lessons :
   > **L25 (révisé)** — Features de breakout strategy doivent être validées
   > par split-by-direction (point-in-time + symmetry test). Toute feature
   > non-direction-conditionnelle dont le score d'asymétrie long/short
   > > 0.5 est suspecte. Au-delà : tout filtre intraday breakout doit
   > satisfaire **simultanément** : bootstrap CI exclut 0, régime stability
   > 5/5, DSR honnête > 0.5, stress 1.5×cost + slip 0.05R Sharpe > 0,
   > top-décile capture ≥ kept_pct. Si l'un manque : pas d'edge utilisable.
   > Application : Phase 2 audit 2026-06-02, NQ ORB 09:30 ET.

---

## 9. Fichiers produits Phase 2

| Fichier | Rôle |
|---|---|
| `audit/phase2_univariate_scan.py` | Scan univariate + régime decomp |
| `audit/phase2_univariate_main.csv` | Univariate IC complet |
| `audit/phase2_univariate_regime.csv` | Régime decomp top 8 candidats |
| `audit/phase2_univariate_output.txt` | Output complet |
| `audit/phase2_filter_hypotheses.py` | 4 hypothèses pré-enregistrées + ablations + bootstrap |
| `audit/phase2_hypotheses_summary.csv` | Summary table |
| `audit/phase2_hypotheses_regime.csv` | Régime par hypothèse |
| `audit/phase2_hypotheses_output.txt` | Output complet |
| `audit/phase2_stress_dsr.py` | Stress cost/slip + DSR + annual breakdown |
| `audit/phase2_stress.csv` | Stress table |
| `audit/phase2_annual_breakdown_H1.csv` | Annual H1 vs baseline |
| `audit/phase2_stress_dsr_output.txt` | Output complet |
| **`REMINING_clean.md`** | **Ce livrable** |

---

## 10. Honnêteté finale

Ce qui a été **rigoureusement testé** :
- 23 features × 3 subsets × 2 sides = 138 univariate tests.
- 4 hypothèses pré-enregistrées × 3 variants (full + 2 ablations) = 12 hyp tests.
- 5-buckets régime decomposition sur chaque candidat.
- Block bootstrap 500 iter × 11 hypothèses = 5500 bootstrap simulations.
- Stress test 6 scénarios (cost×slip) × 3 sets (base, H1, H4) = 18 evals.
- DSR à n_trials = 50, 150, 500.
- 17 années breakdown.

Ce qui **n'a pas été** testé (et hors scope honnête de cette mission) :
- Filtres ≥ 3 conditions (L10 cap).
- Features inter-jour (les daily/régime pour timing inter-jour sont une
  branche fermée par scans antérieurs).
- Re-test iter_10 (Strategy C, scope CHALLENGE_REPORT_FINAL) sur Databento étendu.
- Re-test avec entry à 09:46 ET (configuration Strategy C live).
- Features microstructure ultra-fine (footprint, order-flow imbalance).

Ce qui est **structurellement vrai** sur le dataset clean :
- Le baseline NQ ORB 09:30 ET 30-min OR next-bar-open est **non-tradable**
  net de coûts sur 2010-2026.
- Aucun filtre 2-conditions des hypothèses pré-enregistrées ne produit un
  edge robuste passant DSR + stress.
- Le bug F1 du builder est entièrement diagnostiqué et fixé.

*Phase 2 re-mining réalisé 2026-06-02 — Claude Code (Opus 4.7 1M ctx).
Verdict honnête : aucun filtre par-trade viable. Baseline lui-même négatif
net sur l'historique étendu. Le verdict d'audit ORB antérieur reposait sur
bug F1 (50%) + régime favorable 2022-2025 (30%) + exécution same-bar
optimiste (20%). Le reste : zéro.*
