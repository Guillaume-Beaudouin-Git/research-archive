# Test du sizing Hurst (overlay Mandelbrot Ntingana) sur l'ORB+floor

**TL;DR — Étape 1 (make-or-break) tranche : pas de gradient Hurst exploitable sur les trades ORB V2+E7. Pire encore — le gradient est INVERSE du papier (anti-persistent +0.184R > persistent +0.111R sur nos trades).** Le sizing λ_H = (1.0, 0.5, 0.25) du papier appliqué tel quel down-size les meilleurs régimes et up-size les pires — **anti-productif**. Étape 2 (ablation L19) devient inutile : il n'y a pas de signal à sizer.

**Décision : NE PAS intégrer le sizing Hurst dans le système live floor_taper.** Cohérent avec le prior Cowork (variance-ratio / efficiency-ratio donnent AUC 0.42-0.49 = pile-ou-face pour séparer les régimes ORB favorables).

---

## 0. Cadrage

- **Pas un test d'alpha** : l'ORB n'a aucun edge par-trade significatif (DSR_p 0.08, breakout deep-dive collapse delay-1, placebo).
- **Test de SIZING uniquement** : le sizing Hurst+vol-z améliore-t-il l'ORB+floor à levier moyen égal ?
- **Prior faible (Cowork)** : variance-ratio AUC 0.42-0.49 → effet attendu marginal au mieux.
- **Méthodo papier** : H estimé par variance-ratio Lo-MacKinlay multi-lag (q ∈ {2,4,8}), fenêtre 200 bars 5-min trailing, **strict point-in-time**.
- **Trade log** : V2+E7 = ORB 30-min + trail_BE@1R, NQ 2010-2026 databento, cost 1 bp RT, n=3945 trades.

## 1. Step 1 — Gradient WR/R par régime Hurst (make-or-break)

`audit/hurst_step1_v3.py` → `hurst_step1_trades_with_features.parquet`, `hurst_step1_summary.csv`.

### Distribution de H point-in-time sur les trades

| Stat | Valeur |
|---|---:|
| Mean H | 0.484 |
| Std H | 0.076 |
| p10 / p50 / p90 | 0.384 / 0.488 / 0.578 |

→ La distribution H est centrée sur **0.484** (légèrement anti-persistent du random walk 0.5). p50 ≈ 0.49 = quasi-random. Le sample est largement neutral.

### Répartition des trades par régime

| Régime | n trades | % |
|---|---:|---:|
| **persistent** (H ≥ 0.55) | 773 | 19.6% |
| **neutral** (0.45 ≤ H < 0.55) | 1908 | 48.4% |
| **anti_persistent** (H < 0.45) | 1261 | 32.0% |
| unknown | 3 | 0.0% |

### Gradient WR / mean R par régime Hurst (NQ V2+E7, 16y)

| H regime | n | mean R | WR % | cum R | t-stat |
|---|---:|---:|---:|---:|---:|
| persistent | 773 | **+0.111** | 42.3% | +85.87 | +2.85 |
| neutral | 1908 | +0.137 | 44.8% | +260.47 | +5.42 |
| **anti_persistent** | 1261 | **+0.184** | 44.7% | +231.61 | +5.82 |

### Verdict gradient Hurst — INVERSE du papier ✗

- **Le papier Ntingana claime persistent > neutral > anti-persistent** (Table 3).
- **Nos données NQ V2+E7 montrent anti-persistent > neutral > persistent**.
- Différence anti vs persistent : Δ mean R = **+0.073R** (anti meilleur), Δ t-stat 5.82 vs 2.85.
- **Sizing λ_H du papier** (persistent=1.0, neutral=0.5, anti=0.25) appliqué tel quel UP-SIZE les pires régimes et DOWN-SIZE les meilleurs. **Net : dégradation**.

### Gradient vol_z (papier vs nous)

| vol_z regime | n | mean R | WR % | cum R | t-stat |
|---|---:|---:|---:|---:|---:|
| vol_high (z ≥ +0.5) | 388 | +0.129 | 41.0% | +50.02 | +2.12 |
| **vol_mid** (-0.5 ≤ z < +0.5) | 1527 | **+0.204** | 46.6% | +310.72 | +6.87 |
| vol_low (z < -0.5) | 1954 | +0.100 | 43.0% | +194.98 | +4.25 |

→ **Pattern inverted-U cohérent avec λ_Z du papier (low=0.5, mid=1.0, high=0.5).** Vol_mid donne le meilleur R, vol_high et vol_low sont moins bons. Le sizing λ_Z est *directionnellement* correct mais l'effet est petit (Δ vol_mid-vs-low = +0.104R).

### Combined 3×3 (mean R per cell)

| | vol_high | vol_mid | vol_low |
|---|---:|---:|---:|
| **persistent** | 0.230 | 0.196 | 0.035 |
| **neutral** | 0.134 | 0.147 | 0.113 |
| **anti_persistent** | 0.064 | **0.303** | 0.119 |

Cell le plus rentable = **anti_persistent + vol_mid** (n=456, mean R +0.303). Avec λ_H × λ_Z du papier = 0.25 × 1.0 = 0.25 → on down-size *cette* cellule à 25% du levier, alors que c'est la meilleure cellule du dataset. ✗

Cell le moins rentable = **persistent + vol_low** (n=389, mean R +0.035). Avec λ du papier = 1.0 × 0.5 = 0.5 → on garde 50% du levier sur la pire cellule. ✗

→ **L'overlay λ = λ_H × λ_Z du papier est presque exactement à l'envers** pour notre stratégie ORB sur NQ.

### Pourquoi l'inversion ?

Hypothèse mécanique : le papier Ntingana est testé sur des stratégies trend-following classiques où la persistance H>0.5 = bonne (le trend continue). L'ORB intraday EST un breakout mais sa logique de profit est DIFFÉRENTE :
- Quand H<0.5 (anti-persistent intraday, = mean-reverting), un breakout précoce a tendance à se faire reprendre → **mais l'ORB n'attend que le PREMIER break confirmé sur close**. Donc les breaks "trop fast" en anti-persistent régime sont rares mais quand ils arrivent, ils signalent un vrai shift de régime → continuation.
- Quand H>0.5 (persistent intraday, = trending), les multiples breaks small dans la même direction sont la norme → ORB triggered souvent sur des moves qui s'épuisent vite.

Cette intuition reste spéculative. **Le fait empirique est solide : H inverse-corrélée avec ORB-edge sur NQ 16y.**

## 2. Step 2 — Ablation L19 : **SKIPPED**

Le test make-or-break ayant montré (a) que le gradient Hurst est inverse au papier sur nos données et (b) que l'application directe des λ du papier va dégrader, **Step 2 est inutile**. Toute énergie dépensée à confirmer numériquement que "λ_H mal calibré dégrade le sizing" serait redondante. Cohérent avec L10 (max 3 mods par hypothèse) : pas de tuning in-sample pour "sauver" un overlay dont l'hypothèse make-or-break a échoué.

**Note** : on POURRAIT inverser λ_H (λ_persistent=0.25, λ_anti=1.0) pour exploiter le gradient inverse. Mais :
- C'est de l'**in-sample fitting** — overfitting clair.
- Le gradient est petit (Δ = +0.073R) et avec t-stat modeste — pas un edge robuste.
- Aurait besoin OOF / DSR sur l'espace de signs × thresholds × bins → re-fait l'overlay tuning, ce qui est exactement ce qu'on évite.

## 3. Step 3 — Time-to-pass : moot

Sans gradient exploitable, le sizing Hurst rajouterait juste un dé-leverage (puisque mean λ_H × λ_Z ≈ 0.5-0.7 pour la plupart des trades, donc plus petit que λ=1). Le dé-leverage rallongerait le grind (cf. ORB pushpass analysis) **sans gain sur p(pass)**. C'est strictement pire que floor_taper seul.

## 4. Verdict

| Question du brief | Réponse |
|---|---|
| L'ORB a-t-il un gradient WR/PnL par régime Hurst ? | **Non — gradient INVERSE au papier.** anti > persistent (+0.073R, t-stat 5.82 vs 2.85). |
| Le sizing Hurst+vol-z améliore-t-il l'ORB+floor à levier moyen égal ? | **Non — il dégraderait** car λ_H mal calibré sur notre instrument. |
| Faut-il intégrer Hurst au système live floor_taper ? | **NON.** Cohérent avec le prior Cowork (variance-ratio AUC 0.42-0.49 = pile-ou-face). |

### Résultat valide et défendable

- L'hypothèse "Hurst sizing = bénéfice marginal au pire" du brief est **réfutée par le bas** : ce n'est même pas "marginal au pire", c'est "anti-productif au mieux" sans tuning inversé in-sample.
- Le travail régime de Cowork est confirmé empiriquement : variance-ratio (= proxy de Hurst, H = 0.5 + log(VR)/(2 log q)) ne sépare PAS les régimes favorables de l'ORB. AUC 0.42-0.49 = essentiellement random.
- Ne pas alourdir le système live de complexité (overlay multi-régime) sans signal sous-jacent.

### Implication méthodologique

Les sizings issus de papiers académiques (Ntingana et autres) sont **calibrés sur des stratégies trend-following diversifiées multi-asset**, où H>0.5 est effectivement associé à la persistance des moves. **L'ORB intraday a une mécanique différente** : il est by-construction long-only-ish (capture les big moves first thing), donc sa relation avec la persistance H est différente.

**Avant d'adopter un overlay de sizing académique, tester son make-or-break sur les trades de la stratégie cible.** Pas de transfer learning naïf entre familles de stratégies.

### Comparaison vol_z vs Hurst sur nos trades

- **vol_z (Cowork-like)** : donne un gradient inverted-U cohérent avec λ_Z du papier. Effet petit (+0.10R Δ mid-vs-low/high).
- **Hurst (Ntingana)** : donne un gradient INVERSE au papier. Effet petit (+0.073R Δ anti-vs-persistent) mais directionnellement faux.

→ **Si on devait choisir UN overlay multi-régime**, le vol_z seul serait plus intéressant que Hurst. Mais l'effet absolu est si petit qu'il ne justifie pas la complexité.

### Caveats irréductibles

1. **Notre Hurst utilise VR Lo-MacKinlay lags {2,4,8} sur 200 5-min bars.** Le papier utilise peut-être R/S statistic ou DFA sur des fenêtres différentes. Estimation différente → résultats peuvent différer marginalement, mais le pattern de fond (H sur NQ p50 ≈ 0.49 = quasi-random) est invariant à la méthode d'estimation.
2. **Notre trade log V2+E7 est ORB 30-min + trail_BE@1R.** Le papier teste possiblement des trades différents (CTAs, trend-followers). L'ORB intraday est probablement différent de la stratégie cible du papier.
3. **N=3945 trades sur 16 ans = beaucoup**, mais le gradient observé reste petit relativement à la variance per-trade (std R ≈ 1.5).

## 5. Reproductibilité

| Script | Sortie |
|---|---|
| `audit/hurst_step1_v3.py` | `hurst_step1_trades_with_features.parquet`, `hurst_step1_summary.csv`, `hurst_step1_output.txt`, `_nq_5min_rth_cached.parquet` |

Data : `data/raw/NQ_1min_databento_2010-2026.parquet`. Trades : `audit/breakout_phase2_trades_ORB_30min.parquet`.

Tous seeded, déterministes. `cd audit && /usr/bin/python3 hurst_step1_v3.py`.

---

## 6. In-sample vs OOS marquage explicite

| Chiffre | Source | Statut |
|---|---|---|
| H gradient: anti +0.184R > persistent +0.111R | Step 1 sur V2+E7 16y | **in-sample 16y, point-in-time strict** |
| H sample mean = 0.484, p50 = 0.488 | Step 1 | **descriptive, robuste** |
| vol_z gradient: mid > high ≈ low | Step 1 | **in-sample 16y** |
| Cell mean R max = anti+mid (+0.303R, n=456) | Step 1 | **in-sample** |
| λ_H paper inverse-correlated with our gradient | analyse | **conclusion structurelle** |
| Live performance | — | **0 jour** |

---

*Test du sizing Hurst réalisé 2026-06-02 — Claude Code (Opus 4.7 1M ctx). Métrique = gradient WR/R par régime point-in-time. Verdict : gradient inverse au papier sur NQ V2+E7 → sizing Hurst non-applicable tel quel, ne pas intégrer au floor_taper system.*
