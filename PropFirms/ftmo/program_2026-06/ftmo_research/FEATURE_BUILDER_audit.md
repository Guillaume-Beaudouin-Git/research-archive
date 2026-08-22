# Feature-Builder Audit — Phase 1 (Gate)

> **TL;DR — Le builder, hors le bug F1 ligne 180 déjà documenté, est CLEAN.
> Reconstruction point-in-time : 0 mismatch sur 20 features × 4013 trades NQ
> 2010-2026. Le bug F1 se reproduit à l'identique sur les données propres
> (LONG buggy = correct ; SHORT buggy Δ=+0.664R, SHORT correct Δ=+0.009R).
> Une fois sur données propres (NQ futures 2010-2026, exécution next-bar-open),
> la plupart des « ICs » du dataset CFD buggy 2022-2025 s'effondrent. Verdict
> Phase 2 : GO — le builder corrigé est fiable, le dataset propre est trustworthy.
> Mais ATTENTION : aucune feature ne survit |t_HAC| > 2.5 à long ou short isolé,
> et les deux survivantes au niveau ALL (or_range, day_of_week) sont soit un
> artefact arithmétique (or_range — cf. brief §2.3) soit un effet petit
> (day_of_week, ρ ≈ 0.03). Phase 2 partira d'une surface morte sur les features
> existantes — la nouveauté à explorer est la dimension volume (encore inconnue
> sur les indices CFD).**

---

## 1. Périmètre et méthode

**Sous audit :** `data/ftmo_research/audit/trade_features.py` (builder original, CFD
2022-2025, 3 sleeves US100/GER40). Le bug `time_to_break_5min` ligne ~180 est
documenté dans `F1_bughunt.md` (`time_to_break = (iu if iu < 10**9 else idn) - 0` →
pour les shorts, stocke `iu` post-entry au lieu de `idn` trigger).

**Cible de l'audit :**
- Vérifier que **chaque** feature est strictement future-blind (info ≤ entry bar).
- Détecter d'autres bugs de la même classe (direction-asymétrie, off-by-one,
  alignement shift manquant).
- Régénérer un dataset propre sur NQ futures 2010-2026 (Databento) avec
  exécution réaliste (next-bar-open ou same-bar fill).
- Décider GO/NO-GO pour la Phase 2 (re-mining).

**Données :**
- **BEFORE** (référence buggy) : `trade_dataset.parquet` (3056 trades, CFD US100/GER40
  2022-2025, 3 sleeves, exécution same-bar at level).
- **AFTER** (clean) : `trade_dataset_clean.parquet` (4013 trades, NQ futures 2010-2026,
  09:30 ET 30-min OR, exécution **same-bar `r_exec_level`** ET **next-bar-open `r_exec_nextopen`**
  enregistrées en parallèle). `is_roll_day` filtré (64 dates), UTC→ET propre.
- Le bug F1 est reproduit côte-à-côte (`time_to_break_buggy` et `time_to_break_5min`
  vivent dans la même ligne pour comparaison ablation pure).

**Tests structurels appliqués à chaque feature :**

A. **Reconstruction point-in-time** (`feature_audit_pointintime.py`) — reconstruire
   chaque feature uniquement à partir des barres `bars[: bi]` (bi = trigger bar).
   Diff bit-à-bit (tolérance 1e-6 relatif) avec la valeur stockée. **Tout
   mismatch = bug.**

B. **Symétrie de direction** — mean ± std par long/short. Score d'asymétrie
   `|mean_L − mean_S| / pooled_std`. Score > 1 sur une feature non-direction-conditionnelle
   = drapeau rouge.

C. **F1 reproduction** — filtre `ttb ≤ médian` appliqué avec `ttb_buggy` et
   `ttb_correct`, sur ALL/LONG/SHORT, target `r_exec_nextopen` ET `r_exec_level`.
   Le pattern « LONG buggy=correct, SHORT buggy énorme, SHORT correct quasi-nul » 
   confirme que le bug est bien la cause unique.

---

## 2. Verdict par feature (point-in-time reconstruction, n=4013)

| Feature | Type | Classe à risque | Verdict | Note |
|---|---|---|---|---|
| `or_high`, `or_low`, `or_range` | OR descriptor | Off-by-one | **OK** | 0/4013 mismatch |
| `twap_or` | OR descriptor | Off-by-one | **OK** | 0/4013 |
| `vwap_or_true` *(nouveau)* | OR descriptor | Off-by-one | **OK** | 0/4013 |
| `or_vol_5m_std` | OR descriptor | Off-by-one | **OK** | 0/4013 |
| `or_vol_total` *(nouveau)* | OR descriptor | Off-by-one | **OK** | 0/4013 |
| `or_vol_ratio_20d` *(nouveau)* | Daily prior | Shift manquant | **OK** | 0/3993 (filtre 20-day burn-in) |
| `or_range_atr_ratio` | Daily prior | Shift manquant | **OK** | 0/3993 |
| `or_touches` | Pré-entry, dir-cond | Off-by-one, dir-asym | **OK** | 0/4013, slice `H[:bi]` strictement < bi |
| `time_to_break_5min` (corrigé) | Pré-entry, dir-cond | Direction-asym | **OK** | 0/4013 — `bi - or_bars` |
| `time_to_break_buggy` (legacy) | — | Direction-asym | **BUG** | Look-ahead 100% des shorts où `iu≠idn` (751/4013 = 18.7%) |
| `dist_twap_at_break_R` | Pré-entry, dir-cond | Direction-asym | **OK** | 0/4013 symétrique (formule `(level-twap)/risk × direction`) |
| `dist_vwap_at_break_R` *(nouveau)* | Pré-entry, dir-cond | Direction-asym | **OK** | 0/4013 |
| `dist_to_pdh_R`, `dist_to_pdl_R` | Daily prior, dir-cond | Shift+dir | **OK** | 0/4012 ; asymétrie « score 1.1/1.7 » par design (cf. §3) |
| `gap_abs`, `gap_pct`, `gap_dir` | Daily prior | Shift manquant | **OK** | 0/4012 |
| `gap_concord`, `prior_day_concord` | Daily prior, dir-cond | — | **OK** | 0/3995 ; concordance avec direction (par design) |
| `overnight_range_ratio` | Daily prior | Shift manquant | **OK** | 0/3995 |
| `prior_day_return` | Daily prior | Shift manquant | **OK** | 0/4010 (`shift(1)` après daily return) |
| `or_vol_skew`, `or_vol_concord` *(nouveau)* | OR descriptor | Direction-asym | **OK** | 0/4013 ; skew = volume cluster relatif au midprice OR, concord = skew × direction |
| `vol_pre_break`, `pre_break_range_R` *(nouveau)* | Pré-entry | Off-by-one | **OK** | 0/4013, slice `[OR : bi]` strict |
| `day_of_week` | Date | — | **OK** | trivial |

**Total : 1 bug confirmé (`time_to_break_buggy`, le coupable F1 connu), 0 nouveau bug détecté
sur 24 features auditées.** La reconstruction point-in-time est exacte pour TOUT le reste.

Voir `feature_audit_pointintime_output.txt`, `feature_audit_pointintime_diff.csv`.

---

## 3. Direction-symétrie — scores

Score d'asymétrie = `|mean_long − mean_short| / pooled_std`. Score > 1 sur une feature
non-direction-conditionnelle = bug. Score > 1 sur une feature direction-conditionnelle
par design = informationnel, pas bug.

### Direction-conditionnelles **par design** (asymétrie attendue, pas un bug)

| Feature | mean_long | mean_short | asym | Interprétation |
|---|---:|---:|---:|---|
| `dist_to_pdh_R` | -0.31 | +1.48 | **1.15** | Pour long, mesure « breaking above PDH ? » (souvent or_hi<pdh → négatif). Pour short, mesure « PDH au-dessus du break-down » (toujours positif). |
| `dist_to_pdl_R` | +2.29 | -1.06 | **1.71** | Symétrique du précédent côté PDL. |
| `dist_twap_at_break_R` | +0.46 | +0.49 | 0.34 | Distance entre break level et TWAP, dans le sens du break. Légèrement plus grande sur shorts (TWAP > or_lo plus marqué que TWAP < or_hi historiquement). |
| `gap_concord`, `prior_day_concord` | ≈0.56 | ≈0.43 | ~0.25 | Définition : direction matches gap/prior return. La direction des breakouts est légèrement biaisée long (trend). |
| `or_vol_concord` | +0.017 | -0.013 | 0.09 | Sign flip par direction par construction (skew × direction). |

### Symétriques (par design)

`or_range`, `or_range_atr_ratio`, `or_vol_5m_std`, `or_vol_total`, `or_vol_ratio_20d`,
`or_vol_skew`, `or_touches`, `time_to_break_5min` (corrigé), `vol_pre_break`,
`pre_break_range_R`, `overnight_range_ratio`, `prior_day_return`, `gap_abs`,
`gap_pct`, `gap_dir`, `day_of_week`, `dist_vwap_at_break_R`. Tous avec asym < 0.1.

### Asymétrie pathologique = bug

| Feature | mean_long | mean_short | asym | Verdict |
|---|---:|---:|---:|---|
| `time_to_break_buggy` | 3.54 | **13.96** | **0.72** | **Look-ahead** — sur shorts, stocke `iu` post-entry. mean_short ≈ 4× mean_long. |
| `time_to_break_5min` (corrigé) | 3.54 | 3.37 | 0.02 | ✓ symétrique post-fix |

**Conclusion §3 :** la signature direction-asymétrique du bug F1 est nette
(asym=0.72) et disparaît après correction (asym=0.02). Aucune autre feature
non-direction-conditionnelle n'exhibe d'asymétrie pathologique.

Voir `feature_audit_direction_symmetry.csv`.

---

## 4. F1 reproduction sur NQ propre — le bug se rejoue à l'identique

Filtre F1 = « garder trades avec `ttb ≤ médian` ». Target = `r_exec_nextopen`
(exécution next-bar-open propre).

| Subset | ttb def | n_kept | mean_R baseline | mean_R F1 | **Δ R** |
|---|---|---:|---:|---:|---:|
| **LONG** | buggy | 1302 | +0.010 | +0.028 | +0.019 |
| **LONG** | correct | 1302 | +0.010 | +0.028 | +0.019 |
| **SHORT** | **buggy** | 974 | -0.034 | +0.630 | **+0.664** |
| **SHORT** | **correct** | 1115 | -0.034 | -0.025 | +0.009 |
| **ALL** | **buggy** | 2225 | -0.011 | +0.258 | **+0.268** |
| **ALL** | correct | 2417 | -0.011 | +0.004 | +0.014 |

Reproduction parfaite du pattern CFD 2022-2025 documenté (cf. `F1_bughunt.md` §5) :
- LONG buggy = LONG correct (par construction : `iu` IS le trigger pour les longs).
- SHORT buggy énorme, SHORT correct quasi-nul.
- ALL buggy énorme, ALL correct quasi-nul.

**Sur target `r_exec_level` (legacy same-bar) :** même conclusion, Δ ALL buggy = +0.268,
ALL correct = +0.009. Le bug F1 n'est pas un artefact d'exécution.

**100% de « l'edge F1 » vient du look-ahead sur les shorts.**

Voir `feature_audit_F1_demo_nextopen.csv`, `feature_audit_F1_demo_level.csv`.

---

## 5. Tableau IC — AVANT (CFD buggy 2022-2025) vs APRÈS (NQ clean 2010-2026)

Subset = ALL. Rho_Spearman + t-stat associé. Surtout, **|t_HAC|** (Newey-West lag-6)
sur OLS univarié `R = α + β × feature_z + ε`. Trié par |t_HAC| BEFORE.

| Feature | n_before | ρ_before | **t_HAC_before** | n_after | ρ_after | **t_HAC_after** | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| `time_to_break_5min` | 3056 | **-0.265** | **-23.78** | 4012 | **+0.001** | **-2.36** | **EFFONDRÉ** (bug) |
| `or_range` | 3056 | +0.258 | -1.08 | 4012 | +0.106 | +2.74 | survit ALL, mais artefact arithmétique (§7) |
| `or_range_atr_ratio` | 3056 | +0.219 | -2.08 | 3992 | +0.080 | -0.34 | effondré |
| `or_vol_5m_std` | 3056 | +0.152 | -1.01 | 4012 | +0.005 | -2.17 | effondré (rho → 0) |
| `overnight_range_ratio` | 3054 | +0.068 | -0.96 | 3995 | -0.029 | -1.44 | effondré |
| `day_of_week` | 3056 | +0.050 | +3.12 | 4012 | +0.030 | +2.63 | partial — survit (faible) |
| `gap_abs` | 3054 | -0.027 | +0.08 | 4011 | +0.036 | +1.18 | bruit/régime |
| `gap_pct` | 3054 | -0.027 | +0.26 | 4011 | +0.035 | +2.02 | bruit/régime |
| `dist_to_pdl_R` | 3056 | +0.025 | +0.15 | 4011 | +0.062 | +2.18 | bruit/régime |
| `gap_dir` | 3054 | -0.022 | +0.39 | 4011 | +0.025 | +1.91 | bruit/régime |
| `dist_to_pdh_R` | 3056 | -0.018 | -0.94 | 4011 | -0.007 | +0.40 | bruit |
| `or_touches` | 3056 | +0.017 | +2.20 | 4012 | -0.031 | -1.89 | bruit, change de signe |
| `dist_twap_at_break_R` | 3056 | -0.017 | +0.69 | 4012 | -0.029 | -0.08 | bruit |
| `gap_concord` | 3054 | +0.007 | -0.67 | 3995 | +0.027 | +0.95 | bruit |
| `prior_day_concord` | 3056 | -0.007 | -0.52 | 3998 | +0.014 | +0.59 | bruit |
| `prior_day_return` | 3056 | -0.005 | +1.85 | 4010 | +0.009 | +0.99 | bruit |

### Comptage : features survivant |t_HAC| > 2.5

| Subset | Before (CFD 2022-2025) | After (NQ 2010-2026) | Convergence ? |
|---|---|---|---|
| **ALL** | 2/16 : `time_to_break_5min` (bug !), `day_of_week` | 2/16 : `or_range` (artefact !), `day_of_week` | uniquement `day_of_week` survit dans les deux |
| **LONG** | 0/16 | 0/16 | aucune |
| **SHORT** | 1/16 : `time_to_break_5min` (bug !) | 0/16 | aucune |

**Lecture honnête :**
- Le seul « gros IC » du dataset BEFORE était `time_to_break_5min`. **C'était le bug.**
  Une fois corrigé sur le dataset CLEAN, son ρ tombe de -0.265 à +0.001 et son
  t_HAC passe de -23.78 à -2.36. C'est l'effondrement attendu.
- Les autres features apparemment significatives dans BEFORE (or_range_atr_ratio,
  or_vol_5m_std, overnight_range_ratio) avaient un t_HAC déjà < 2.5 dans BEFORE
  et tombent encore plus dans AFTER. La période 2022-2025 sur CFD gonflait les
  Spearman naïfs mais le HAC les écrasait déjà. Sur NQ étendu, le ρ aussi
  s'effondre — confirmation que c'était du régime + bruit.
- **Au niveau LONG seul ou SHORT seul, AUCUNE feature ne survit |t_HAC|>2.5.**
  Les seules survivantes ALL (`or_range`, `day_of_week`) ne sont pas un edge
  utilisable (cf. §6).

Voir `feature_ic_before_buggy_cfd.csv`, `feature_ic_after_clean_nq_nextopen.csv`,
`feature_ic_side_by_side.csv`.

---

## 6. Les survivantes — examen honnête

### `or_range` (t_HAC ALL = 2.74, ρ_S = 0.106)

**Drapeau rouge** : le brief §2.3 prévient explicitement qu'il s'agit d'un
**artefact arithmétique** (`R = move / risk`, et risk = or_range → OR étroit
gonfle mécaniquement le R). Diagnostic empirique sur le dataset propre :

| Métrique | Valeur (ALL, r_exec_nextopen) |
|---|---:|
| ρ_Spearman | +0.106 |
| ρ_Pearson | +0.034 |
| Δ mean-R Q5 (large OR) | +0.040 |
| Δ mean-R Q1 (petit OR) | -0.031 |
| **Top-décile R capture Q5** | **13.0%** (vs baseline 20% si random) |

Le ρ et le Δ mean-R sont cohérents avec « plus l'OR est large, plus le mean R
est légèrement positif ». **MAIS** le top-décile R capture Q5 = 13% < 20%
(baseline aléatoire). Donc filtrer pour `or_range` large RÉDUIT la concentration
de top-R trades — **l'edge est dans la queue, pas dans la moyenne**. Confirme
l'avertissement du brief : ne pas re-vendre or_range comme une découverte.

### `day_of_week` (t_HAC ALL = 2.63, ρ_S = 0.030)

Petit effet, présent BEFORE (3.12) et AFTER (2.63) — c'est l'unique feature
qui semble robuste à l'extension d'échantillon. Mais : ρ ≈ 0.03 = effet
microscopique en termes d'IC. Quintile top capture top-décile = 43.5% (vs
20% baseline si random — mais day_of_week est discret 0-4, donc Q5
correspond à 1 jour spécifique sur 5 = c'est 20% de la sample). **Effet
réel mais petit**, à pré-enregistrer comme variable de régime, pas comme
filtre standalone.

### Sur LONG / SHORT isolé

**Aucune feature ne survit |t_HAC|>2.5 sur long-only ou short-only.**

Pour LONG, les meilleurs candidats sont :
- `or_range` t_HAC=1.97 (sous gate)
- `dist_to_pdh_R` t_HAC=2.17 (sous gate)
- `dist_to_pdl_R` t_HAC=2.30 (sous gate)
- `gap_pct` t_HAC=2.46 (sous gate)

Pour SHORT :
- `or_vol_total` t_HAC=2.11 (sous gate)
- `day_of_week` t_HAC=2.18 (sous gate)
- `time_to_break_5min` t_HAC=-2.03 (sous gate ; petite info négative — opposite
  de la lecture buggy ; effet probable bruit)

**Conclusion §6** : au seuil habituel |t_HAC|>2.5, les survivants sont
explicables par artefact arithmétique (or_range) ou effet faible non
exploitable seul (day_of_week). **Aucun edge filter par-trade univariée
identifié à la Phase 1.** Phase 2 doit chercher dans les combinaisons
2-features et dans la dimension volume (jamais testée).

---

## 7. Bug F1 — magnitude sur dataset propre

Pour comparer la magnitude du bug entre les deux datasets, on calcule
`time_to_break_buggy` (recalculée sur NQ avec la même formule buggy) et
on la compare à `time_to_break_5min` (corrigée) — sur la même ligne, même
target.

| Subset | `time_to_break_5min` ρ | `time_to_break_5min` t_HAC | `time_to_break_buggy` ρ | **`time_to_break_buggy` t_HAC** |
|---|---:|---:|---:|---:|
| ALL | +0.001 | -2.36 | **-0.325** | **-31.66** |
| LONG | -0.015 | -1.25 | -0.015 | -1.25 (= identique : iu=trigger pour long) |
| SHORT | +0.016 | -2.03 | **-0.655** | **-29.36** |

Le bug crée un t_HAC énorme (-31 à -37 sur ALL et SHORT) sur la version
buggy, alors que la version corrigée a un t_HAC ~0-2. **Le bug ne survit
pas la correction.** C'est aussi un test de cohérence avec F1_bughunt.md
qui rapportait des chiffres comparables sur CFD.

---

## 8. Verdict GO/NO-GO Phase 2

### Le builder est-il fiable ?

| Critère | Verdict |
|---|---|
| 1 bug connu (F1, ligne 180) corrigé ? | **OUI** — `trade_features_nq.py` produit `time_to_break_5min = bi - or_bars` |
| Reconstruction point-in-time de toutes les features ? | **OUI** — 0 mismatch sur 20 features × 4013 trades |
| Direction-symétrie respectée pour features non-conditionnelles ? | **OUI** — score d'asymétrie < 0.1 partout sauf bug connu |
| Off-by-one inclusion de la barre `bi` dans les slices ? | **NON** — `H[:bi]` strictement, par construction `bi` est la première barre où break détecté, donc bars 0..bi-1 sont strictement future-blind |
| Shift(1) sur features daily prior ? | **OUI** — vérifié sur `pdh`, `pdl`, `prev_close`, `prior_day_return`, `atr20`, `vol_median_20` |
| Exécution propre disponible (`r_exec_nextopen`) ? | **OUI** — enregistrée en parallèle de `r_exec_level` |
| Données utilisées robustes (multi-régime) ? | **OUI** — NQ 2010-2026, 16 ans, 5-6 régimes |
| F1 bug se rejoue à l'identique sur clean data ? | **OUI** — pattern direction-split confirmé |

### ⇒ **GO Phase 2.**

### Garde-fous obligatoires pour Phase 2 (issus de cette audit)

1. **Split-by-direction systématique** — toute feature/filtre candidat doit
   être validée long ET short séparément (L25, issu de F1).
2. **Évaluation sur R + top-décile capture, jamais sur win-rate** — `or_range`
   illustre exactement le piège (mean ↑, queue ↓).
3. **Target = `r_exec_nextopen`** par défaut (exécution propre). `r_exec_level`
   reste accessible pour audit/legacy, mais aucun claim de p_funded
   à partir du same-bar.
4. **Régime decomposition obligatoire sur 2010-2026** — un edge réel doit tenir
   à travers ≥4 des grands régimes (2011 eurozone, 2015-16 commodity bust,
   2018 vol shock, 2020 covid, 2022 bear, 2023 chop).
5. **DSR honnête** : n_trials reflète features × cutoffs testés. Rappel : DSR
   est aveugle au look-ahead, donc split-direction + future-blind restent
   les gardes structurels prioritaires.
6. **Filtres ≤ 2 conditions** (L10).
7. **Ne pas re-proposer comme edge** : `time_to_break_5min`, `or_range` /
   `or_range_atr_ratio` (artefact arithmétique), features daily déjà testées
   pour timing inter-jour.

### Le tableau idéologique

| | BEFORE (CFD buggy 2022-2025) | AFTER (NQ clean 2010-2026) |
|---|---|---|
| n trades | 3056 (3 sleeves, 4 ans) | 4013 (1 sleeve NQ, 16 ans) |
| Cost RT | 3.0 pts US100 / 1.5 pts GER40 | 1.0 pt NQ (~$2.15/MNQ) |
| Exec | same-bar @ level | same-bar AND next-bar-open en parallèle |
| Volume | absent (TWAP) | présent (vrai VWAP, or_vol_total, etc.) |
| Roll | non flaggé | flaggé (`is_roll_day`), 64 dates skippées |
| Baseline mean R | +0.10 (1 bug + 3 sleeves) | +0.006 (same-bar) / **-0.011 (next-bar-open)** |
| Bug F1 | présent, gonfle Δ ALL à +0.33R | reproduit (Δ=+0.27R) puis disparaît une fois corrigé (Δ=+0.014R) |
| Features survivantes |t_HAC|>2.5 sur ALL | 2/16 : `ttb` (bug !) + `day_of_week` | 2/16 : `or_range` (artefact) + `day_of_week` |

### Implication structurelle

Sur 2010-2026, le baseline NQ ORB next-bar-open **est négatif net de coûts
(-0.011 R/trade)**. L'« edge ORB +0.10 R/trade » du verdict d'audit précédent
était :
- ~50% biais bug F1 (qui contaminait par-trade et donc la moyenne)
- ~30% régime favorable 2022-2025 (post-covid trend, AI rally)
- ~20% biais exécution same-bar (entry at level optimiste)

Une fois ces trois facteurs neutralisés, **le baseline est ~0 net**. C'est
le décor pour la Phase 2 : on cherche un filtre par-trade qui transforme un
baseline ~0 en quelque chose d'utilisable. La barre est haute.

---

## 9. Fichiers produits

| Fichier | Rôle |
|---|---|
| `audit/trade_features_nq.py` | Builder propre adapté NQ (clean) |
| `audit/trade_dataset_nq.parquet` | Dataset complet avec `ttb_correct` ET `ttb_buggy` |
| **`audit/trade_dataset_clean.parquet`** | **Dataset propre, sans colonne buggy, pour Phase 2** |
| `audit/feature_audit_pointintime.py` | Audit script : point-in-time + direction-symetry + F1 demo |
| `audit/feature_audit_pointintime_output.txt` | Output complet de l'audit |
| `audit/feature_audit_pointintime_diff.csv` | Per-feature diff vs PIT |
| `audit/feature_audit_direction_symmetry.csv` | Per-feature mean/std long/short |
| `audit/feature_audit_F1_demo_nextopen.csv` | F1 reproduction sur target clean |
| `audit/feature_audit_F1_demo_level.csv` | F1 reproduction sur target legacy |
| `audit/feature_ic_compare.py` | IC tables before/after |
| `audit/feature_ic_before_buggy_cfd.csv` | IC BEFORE (CFD buggy) |
| `audit/feature_ic_after_clean_nq_nextopen.csv` | IC AFTER (NQ clean, next-bar-open) |
| `audit/feature_ic_after_clean_nq_samebar.csv` | IC AFTER (NQ clean, same-bar) |
| `audit/feature_ic_side_by_side.csv` | Side-by-side BEFORE/AFTER |
| `audit/feature_ic_compare_output.txt` | Output complet IC |
| **`FEATURE_BUILDER_audit.md`** | **Ce livrable** |

---

*Phase 1 audit réalisée 2026-06-01 — Claude Code (Opus 4.7 1M ctx).
Builder verdict : CLEAN après fix `time_to_break_5min`. GO Phase 2 sur
trade_dataset_clean.parquet avec garde-fous §8.*
