# F1 Verification Gate — 3 Inflations Tested

**TL;DR** — Le filtre F1 (`time_to_break_5min ≤ médian`) **PASSE les 3 vérifications** :
1. ✅ **Edge INDÉPENDANT de or_range** (corr ρ=+0.02, le coefficient ttb retient 99.5% après contrôle).
2. ✅ **Slip-robuste en POINTS FIXES** (breakeven ~10-16 pts/side, ~4× headroom vs baseline 2.5-4 pts).
3. ✅ **DSR survit massivement** (raw SR 4.39 → deflated 3.49 à n_trials=78, encore 3.27 à n_trials=500).

**Verdict** : F1 est un **edge structurel indépendant et robuste**. La validation étendue sur NQ/DAX 2008-2025 est **justifiée** (pas un faux signal).

---

## Check 1 — Orthogonaliser time_to_break vs or_range

`audit/f1_check1_orthogonal.py` → `f1_check1_output.txt`.

**Hypothèse à tester** : si F1 boost est juste un artefact de dénominateur (R = move/risk → petit OR → grand R-multiple), alors contrôler pour or_range devrait faire disparaître l'edge ttb.

### 1.1 Corrélation directe

| Variables | ρ Spearman | SE day | p |
|---|---:|---:|---:|
| ttb vs or_range (absolu) | **+0.064** | 0.013 | 0.0004 |
| ttb vs or_range_atr_ratio | **+0.022** | 0.013 | 0.236 |

→ **Quasi-orthogonaux**. Les breakouts rapides ne sont **PAS** sur des ranges étroits.
→ ρ = +0.02 vs or_range_atr_ratio (la version normalisée la plus pertinente) est non-significatif.

### 1.2 Table 3×3 — mean R par (or_range tercile × ttb tercile)

| | fast (ttb low) | mid | slow (ttb high) | Δ fast−slow |
|---|---:|---:|---:|---:|
| **narrow OR** | +0.687 | +0.431 | −0.592 | **+1.28R** |
| **mid OR** | +0.367 | +0.305 | −0.446 | **+0.81R** |
| **wide OR** | +0.230 | +0.285 | −0.341 | **+0.57R** |

→ **L'edge ttb survit dans TOUS les buckets or_range**. Même dans wide OR (où l'artefact dénominateur ne joue PAS), fast bat slow de **+0.57R**. C'est structurellement défendable.

→ L'effet est plus fort dans narrow OR (+1.28) que wide (+0.57) — un peu d'interaction, mais l'effet baseline reste massif partout.

### 1.3 Régression OLS, cluster-by-day SE

| Modèle | coef ttb_z | t ttb | coef or_range_z | t or_range |
|---|---:|---:|---:|---:|
| A : R ~ ttb_z | **−0.384** | **−24.0** | — | — |
| B : R ~ or_range_z | — | — | −0.054 | −2.1 |
| C : R ~ ttb_z + or_range_z | **−0.382** | **−24.5** | −0.030 | −1.27 (n.s.) |
| D : R ~ ttb_z + or_range_z + interaction | −0.402 | −23.2 | −0.026 | −1.07 (n.s.) |

**Lecture critique** :
- **Coefficient ttb retient 99.5%** de sa valeur entre Modèle A et Modèle C. t-stat passe même de −24.0 à −24.5 (effectivement *renforcée* en contrôlant pour or_range).
- **Coefficient or_range chute de t = −2.1 à t = −1.27 (n.s. p=0.20)** quand on contrôle pour ttb.
- **L'interaction est significative (t = +6.4)** — confirme que l'effet est plus fort en narrow OR, mais le main effect ttb domine.

### Verdict Check 1 ✅

**TTB est un edge INDÉPENDANT**. C'était **or_range** le dénominateur artefact, pas TTB.

L'intuition économique tient : breakouts décisifs (rapides) reflètent un déséquilibre d'order-flow non absorbé pendant l'auction → continuation directionnelle, indépendamment de la largeur du range.

---

## Check 2 — Slippage en POINTS FIXES (pas fraction-de-R)

`audit/f1_check2_slip_points.py` → `f1_check2_slip_points.csv` + `f1_check2_breakeven.csv`.

**Hypothèse à tester** : si F1 tilte vers les OR étroits, un slip fixe en points est une fraction plus grande de leur petit R → le "+91pt à 3×" du précédent test (slip_R = 0.15) pourrait s'effondrer en points-fixes.

### 2.1 Médian OR range par sleeve (BASE vs F1)

| Sleeve | BASE médian or_range | F1 médian or_range |
|---|---:|---:|
| US100 16:30 30m | 101.0 pts | **104.4 pts** |
| GER40 16:30 15m | 37.9 pts | 37.0 pts |
| GER40 10:00 30m | 66.0 pts | 65.7 pts |

→ **F1 ne tilte PAS vers les narrow OR**. Le médian est essentiellement identique (voire légèrement plus large pour US100). Cohérent avec Check 1.1 (ρ ≈ 0).

### 2.2 Slippage points-fixes sweep (per side, applied to entry + exit)

| slip (pts/side) | meanR BASE | meanR F1 | hit BASE | hit F1 | p_funded BASE @0.75% | **p_funded F1 @0.75%** |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | +0.10 | +0.44 | 41.8% | 53.0% | 67.6% | 100% |
| 2 | +0.03 | +0.36 | 40.6% | 51.7% | 43.2% | **94.3%** |
| **4** | **−0.05** | **+0.28** | 39.6% | 50.8% | **10.0%** | **81.6%** |
| 6 | −0.13 | +0.20 | 38.7% | 49.7% | 1.8% | 70.0% |
| **8** | **−0.20** | **+0.12** | 37.9% | 49.2% | **0.5%** | **67.2%** |
| 10 | −0.28 | +0.04 | 36.8% | 47.6% | 0.3% | 46.7% |
| 12 | −0.36 | −0.04 | 35.5% | 45.9% | 0% | 31.1% |

### 2.3 Breakeven slip pts/side (where mean R = 0)

| Sleeve | Config | mean R baseline | médian or_range | **Breakeven pts/side** |
|---|---|---:|---:|---:|
| US100 16:30 30m | BASELINE | +0.09 | 101 | **4.25** |
| US100 16:30 30m | **F1** | +0.35 | 104 | **16.25** |
| GER40 16:30 15m | BASELINE | +0.13 | 38 | 2.50 |
| GER40 16:30 15m | **F1** | +0.58 | 37 | **10.00** |
| GER40 10:00 30m | BASELINE | +0.08 | 66 | 2.50 |
| GER40 10:00 30m | **F1** | +0.35 | 66 | **10.25** |

### Verdict Check 2 ✅

**F1 a ~4× plus de headroom slippage** :
- US100 baseline meurt à 4.25 pts/side (= typique bid-ask CFD). F1 supporte 16.25 pts.
- GER40 baseline meurt à 2.5 pts/side. F1 supporte 10 pts.

À slip 4 pts/side (réaliste CFD live) :
- Baseline mean R = −0.05 (négatif), p_funded 10% → **mort**.
- F1 mean R = +0.28, p_funded 81.6% → **vivante**.

L'avantage F1 n'est pas un artefact du modèle slip-fraction-de-R. **F1 transforme une stratégie slip-fragile en stratégie slip-robuste**, exactement parce qu'elle quadruple l'espérance R sans tilter vers narrow OR.

---

## Check 3 — DSR Bailey-LdP

`audit/f1_check3_dsr.py` → `f1_check3_output.txt`.

**Hypothèse à tester** : le Sharpe 4.39 et la mean R ×4.2 sont-ils statistiquement valides après déflation du budget de recherche ?

### Stats brutes

| Strategy | n_days | Sharpe ann | Skew | Excess Kurt |
|---|---:|---:|---:|---:|
| BASELINE | 1033 | 1.54 | 1.84 | 6.67 |
| **F1** | 1033 | **4.39** | **2.99** | **20.68** |

### Scénarios DSR

`n_trials` = nombre de stratégies considérées dans le programme de recherche. Couverture :
- **Microstructure-only** : 15 features × ~4 cutoff variants = **60 trials**.
- **+ 18 familles antérieures** (CHALLENGE_REPORT) : **78 trials total**.
- **Pessimiste** : sleeves × directions × interactions × paires de features = **200**.
- **Très pessimiste** : couvre toute la session de l'année + sweeps optim sizing/gate = **500**.

| Scenario | n_trials | SR0 threshold (annualisé) | **SR_deflated** | z | DSR P(real) |
|---|---:|---:|---:|---:|---:|
| Microstructure-only | 60 | 0.86 | **3.53** | 9.62 | 1.000 |
| Microstructure + 18 prior | 78 | 0.90 | **3.49** | 9.52 | 1.000 |
| Pessimistic | 200 | 1.01 | **3.37** | 9.20 | 1.000 |
| Very pessimistic | 500 | 1.12 | **3.27** | 8.91 | 1.000 |

### Baseline (no filter) comparison

| Scenario | n_trials | SR0 thr | SR_deflated | DSR P(real) |
|---|---:|---:|---:|---:|
| Baseline @ 18 families | 18 | 0.84 | 0.70 | 0.940 |
| Baseline @ 78 (incl micro) | 78 | 1.10 | **0.44** | 0.833 (FAIL gate 1.0) |

→ **Baseline FAIL le PROPFIRM gate 1.0 même à n_trials=78**. F1 PASSE largement.

### Verdict Check 3 ✅

- F1 deflated Sharpe = **3.49** à n_trials=78 (≥ 3× le seuil PROPFIRM 1.0).
- Même à n_trials = 500 (couverture aggressive du programme de recherche entier), F1 deflated = **3.27**.
- z-stat = 8.9, P(real) = 1.000 → astronomiquement significatif.

**Pourquoi ça marche** : le Sharpe brut F1 = 4.39 est tellement élevé qu'aucune correction réaliste ne le réduit sous 1.0. La variance(SR) reste petite vu T = 1033 days, et même un EmaxN à n_trials=500 ne grimpe qu'à ~3.4 σ, soit ~1.1 SR pénalité.

---

## 4. Verdict final consolidé

| Check | Hypothèse anti-F1 | Résultat | Pass ? |
|---|---|---|:---:|
| **1. Orthogonalisation** | F1 = artefact dénominateur or_range | corr=+0.02, coef ttb retient 99.5%, edge présent dans wide OR (+0.57R) | ✅ |
| **2. Slip points-fixes** | F1 tilte vers narrow OR → effondrement en points | médian or_range identique, breakeven 4× supérieur (16 pts vs 4 pts) | ✅ |
| **3. DSR Bailey-LdP** | F1 = sélection multiple sur 60-500 features | deflated SR ≥ 3.27 même à n_trials=500, z=8.9 | ✅ |

### F1 est un edge structurel défendable

Les 3 inflations testées (artefact, modèle slip, sélection multiple) **ne tiennent pas**. F1 :
- Survit le contrôle pour or_range (l'effet est dans TTB, pas dans le ratio R = move / risk).
- Survit le slip réaliste en points fixes (breakeven ~10-16 pts/side, vs 2-4 pts baseline).
- Survit la déflation Sharpe même avec n_trials = 500.

**L'extension data NQ/DAX 2008-2025 est désormais JUSTIFIÉE** — pas une exploration spéculative, mais la validation d'un edge qui passe ces 3 gates rigoureux.

### Limites résiduelles (non-couvertes par ces 3 checks)

1. **N≈1 régime persistance** : tous ces tests sont sur 2022-2025. La généralisation à 2010-2025 reste à valider (chop episodes 2014, 2015-16, 2018, 2020).
2. **Live execution fidelity** : le test slip-points modélise des points absolus, mais en live le slip peut être asymétrique (worse on stop fills than on entries). Paper-trade obligatoire avant fees.
3. **Mécanisme microstructure stable ?** Le mécanisme « breakouts décisifs (rapides) = order-flow imbalance » est plausible mais pourrait être altéré par changes de microstructure (algo trading evolves, HFT participation, etc.).
4. **Feature drift** : si l'algorithme du broker ou la microstructure venue change la signification de "5 minutes après OR close", le filtre fail. Re-fit annuel recommandé.

### Recommandation actionnable

**Le gate est passé.** Actions :
1. **Procéder à la validation NQ/DAX 2008-2025** (firstratedata + Dukascopy, ~$200, 2 semaines). Objectif : confirmer F1 sur N=5-7 chop episodes distincts.
2. **Paper-trade simultané sur live broker** (2-3 mois minimum) pour calibrer slip réel et le mécanisme exact "5 min après OR close" (vs M1 broker time precision).
3. **Si validation OK** : deploy live à 0.75% block-cap, F1 active.

### Caveats à reporter explicitement dans tout doc futur

- "F1 deflated SR = 3.49 à n_trials=78" (in-sample 2022-2025)
- "À paper en live et valider sur N=5+ régimes distincts avant trust"
- "Edge time_to_break peut décayer si microstructure auction évolue"

---

## 5. Reproductibilité

Tous scripts dans `data/ftmo_research/audit/` :

| Check | Script | Sortie |
|---|---|---|
| 1 — Orthogonalisation | `f1_check1_orthogonal.py` | `f1_check1_output.txt` |
| 2 — Slip points fixes | `f1_check2_slip_points.py` | `f1_check2_slip_points.csv`, `f1_check2_breakeven.csv`, `f1_check2_output.txt` |
| 3 — DSR Bailey-LdP | `f1_check3_dsr.py` | `f1_check3_output.txt` |

Tous seeded, déterministes. `cd audit && /usr/bin/python3 f1_checkX.py`.

Data utilisée : `trade_dataset.parquet` (3056 trades, 2022-2025, généré par `trade_features.py`).

---

*Vérification réalisée 2026-06-01 — Claude Code (Opus 4.7 1M ctx). 3 checks indépendants pour gater la validation étendue. F1 passe les 3.*
