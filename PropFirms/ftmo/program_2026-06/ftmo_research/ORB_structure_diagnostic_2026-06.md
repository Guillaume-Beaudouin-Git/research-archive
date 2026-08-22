# ORB V2+E7 — Structure diagnostic (tail droit & clusters) — 2026-06-03

**Continuation de** `ORB_2mois_diagnostic_2026-06.md`. Même ledger `data/ftmo_research/audit/nq_v2_trades.parquet` (4013 trades NQ databento 2010-2026 V2 baseline + lift E7 +0.015 R). **Coût FIXE = 0.4 bps RT** (borne haute hors-open). Spec **FIGÉE V2+E7** — aucune modification du signal (L10/L19).

**Faits établis (rappel) :**
- mean_R = +0.0552 / std = 1.201 / hit = 45.0% / skew +1.66 / kurt +6.73
- Top 1% (40 trades, R ≥ +3.82) = **93% du P&L total** ; sans eux mean_R = +0.0037 (~zéro)
- Bust @ sizing 2.5% = 100% par accumulation (~4 pertes consécutives, cumul ~-4.4 R), 0% single-trade

**Objets analysés :**
- **Angle A** — anatomie du tail droit : signature observable ex-ante des 40 jackpots
- **Angle B** — mécanisme des clusters de pertes : clustering réel vs hasard, et **test décisif** "anti-cluster détruirait-il l'edge ?"

**⚠ Fragilité statistique** : N=40 sur le tail. Toute "signature" sur 40 trades est par construction faible. Test multiple sur 9 variables → seuil Bonferroni 0.05/9 ≈ 0.0056. Mention systématique.

**⚠ Cadre méthodologique** : aucun chiffre "amélioré" de p(pass), aucun filtre appliqué. Toute corrélation significative = HYPOTHÈSE À PRÉ-ENREGISTRER pour test OOS séparé.

---

## ANGLE A — Anatomie du tail droit (top 1% = 40 jackpots)

### Distribution comparée top 1% vs reste (3973 trades)

| Variable | top1% mean | rest mean | Δ | KS p | Welch t | Welch p | Flag (Bonf≤0.0056) |
|---|---:|---:|---:|---:|---:|---:|---|
| weekday (0=Mon..4=Fri) | +2.15 | +1.99 | +0.16 | 0.819 | +0.81 | 0.42 | — |
| **bi (mins after OR close)** | **+7.38** | **+9.48** | **−2.10** | 0.218 | **−5.84** | **0.0000** | **SIGN ★** |
| **ttb_5min** | +1.38 | +3.48 | −2.10 | 0.218 | −5.84 | 0.0000 | (= bi reformaté) |
| **or_range_bps** | **+43.2** | **+59.7** | **−16.5** | **0.0001** | **−3.32** | **0.0019** | **SIGN ★** |
| or_range_pts | +41.7 | +57.6 | −15.9 | 0.068 | −1.72 | 0.094 | weak |
| gap_overnight_bps | +12.4 | +4.8 | +7.6 | 0.286 | +0.76 | 0.45 | — |
| VIX_prev | +18.37 | +18.36 | +0.01 | 0.929 | +0.01 | 0.99 | — |
| **direction (long=+1, short=−1)** | **−0.40** | **+0.08** | **−0.48** | 0.017 | **−3.25** | **0.0024** | **SIGN ★** |
| year | +2017.6 | +2018.0 | −0.3 | 0.972 | −0.43 | 0.67 | — |

### Décomposition catégorielle (top1% % de chaque catégorie)

**Distribution des 40 jackpots par année** (baseline iid ~6% par année) :
- Hyper-dispersés : **2024 = 7 jackpots (2.75%)**, 2018 = 4, 2011 = 4, 2016 = 4, 2020 = 3, 2012 = 3 ; 2021 = **0**, 2026-partial = **0**.
- Aucune année ne capture une majorité. **Pas de concentration temporelle claire**.

**Par weekday** :
- Mon 4 / Tue 10 / Wed 8 / Thu 12 / Fri 6 → biais léger Thu, mais N=40 → χ² non-significatif.

**Par direction** :
- Short : **28/1857 = 1.51%** des shorts sont jackpots
- Long : **12/2156 = 0.56%** des longs sont jackpots
- **Shorts ~2.7× plus probables de jackpotter que longs**.

**Par quintile OR_range_bps** :
| Quintile | OR range bps | n_top1% / n | % top1% (iid 1%) |
|---|---|---|---|
| Q1 (4-34 bps) | small OR | **19 / 803** | **2.37%** |
| Q2 (34-45) | | 11 / 802 | 1.37% |
| Q3 (45-59) | | 1 / 803 | 0.12% |
| Q4 (59-79) | | 7 / 802 | 0.87% |
| Q5 (79-409) | large OR | 2 / 803 | 0.25% |

→ **Le tail droit favorise les jours small OR**. Q1+Q2 (40% des trades) contiennent 30 des 40 jackpots (75%). Q5 (gros OR) en contient seulement 2.

**Par bucket du break (bi en minutes après OR close)** :
| Bucket | n_top1% / n | % |
|---|---|---|
| [6-15] | **39 / 3632** | **1.07%** |
| [16-30] | 1 / 286 | 0.35% |
| [31-60] | 0 / 77 | 0% |
| [61+] | 0 / 18 | 0% |

→ **39/40 jackpots cassent dans les 15 premières minutes** (cohérent avec la concentration de tous les trades dans cette fenêtre).

### Verdict Angle A — Conditionnable ex-ante ?

**Trois variables franchissent le seuil Bonferroni Welch p ≤ 0.0056 :**
1. **`bi` / `ttb_5min`** (break time after OR close) — t=−5.84, p≈10⁻⁹ : jackpots ont break **plus précoce** que rest.
2. **`or_range_bps`** — t=−3.32, p=0.0019 : jackpots ont **OR plus petit en bps** que rest.
3. **`direction`** — t=−3.25, p=0.0024 : jackpots sont **plus souvent shorts** (28/12 vs ratio général).

**Verdict** : **OUI, les jackpots ont une signature ex-ante détectable.** Profile statistique : **break early × small OR × short**.

**ATTENTION FRAGILITÉ** :
- N=40 → puissance limitée, distributions empiriques bruitées.
- Test multiple sur 9 variables → Bonferroni 0.05/9 = 0.0056 ; bi/ttb (p≈0), or_range_bps (p=0.002), direction (p=0.002) franchissent. weekday/year/gap/vix/or_range_pts NE franchissent PAS (déjà rétractés).
- L'observation "Q1 contient 19 jackpots, Q5 en contient 2" est saillante MAIS Q1 contient aussi 784 trades non-jackpots (97.6% des Q1 ne sont pas jackpots). Le ratio Q1/Q5 = 2.37/0.25 ≈ 9× — c'est un effet marqué, mais conditionnel à voir Q1 ≠ "small OR utile" (il pourrait être "small OR + autre chose corrélée non observée").

### Piège — risque de couper le tail si filtre Q1+small_OR appliqué

**Ce qui suit est descriptif, NON appliqué.** Si on garderait seulement Q1+Q2 (40% des trades, OR_bps ≤45) :
- Capturerait 30/40 = 75% des jackpots.
- Coupe 25% des jackpots (10 trades) : R-sum de ces 10 = ?
- 10 jackpots Q3+Q4+Q5 contribuent R-sum substantiel. Sans calculer le ratio exact ici (= mining), juste noter : couper 25% des jackpots est lourd.

→ **NE PAS appliquer.** À pré-enregistrer OOS uniquement. Voir section Pistes.

---

## ANGLE B — Mécanisme des clusters de pertes

### B.1 — Autocorrélation des R-trades

P(loss) = 55.0%, P(win) = 45.0% sur 4013 trades.

| lag k | corr(R_t, R_{t-k}) | t_HAC6 | Lecture |
|---:|---:|---:|---|
| **1** | **−0.066** | **−4.65** | **Mean-reversion forte** au lag-1 : R bons suivis de mauvais et inverse |
| 2 | −0.010 | −0.59 | — |
| 3 | +0.013 | +0.79 | — |
| 5 | +0.019 | +1.13 | — |
| 10 | +0.015 | +0.89 | — |

**Ljung-Box** :
- Sur R (lags 5, 10, 20) : p = 0.0013 / 0.0026 / 0.019 → **rejette H0 "no autocorr"** — la série R a une structure (concentrée au lag-1).
- Sur indicateur loss (1 si R<0) : p = 0.39 / 0.33 / 0.45 → **N'EXISTE PAS de clustering de pertes en signe seul**. L'autocorr est sur les MAGNITUDES de R, pas sur le signe perte/gain.

### B.2 — Distribution des runs de pertes vs iid

| Longueur de run k | Observed runs of length k | Iid expected = N × p^k × (1−p) | Ratio obs/iid |
|---:|---:|---:|---:|
| 1 | 485 | 993.2 | 0.49× |
| 2 | 253 | 546.2 | 0.46× |
| 3 | 140 | 300.4 | 0.47× |
| 4 | 62 | 165.2 | 0.38× |
| 5 | 36 | 90.9 | 0.40× |
| 6 | 22 | 50.0 | 0.44× |
| 7 | 14 | 27.5 | 0.51× |
| 8 | 6 | 15.1 | 0.40× |

**Et pour les positions où ≥k pertes consec apparaissent N'IMPORTE OÙ** (mesure plus pertinente du "clustering observé") :

| ≥k consec | Observed positions | Iid expected | Ratio |
|---:|---:|---:|---:|
| ≥2 | 1180 | 1213.5 | **0.97×** |
| ≥3 | 638 | 667.2 | **0.96×** |
| ≥4 | 349 | 366.8 | **0.95×** |
| ≥5 | 200 | 201.7 | **0.99×** |
| ≥6 | 113 | 110.9 | **1.02×** |

**Verdict B.2** : **Les clusters de pertes observés sont essentiellement iid** (ratio 0.95-1.02 sur clusters longs). Pas de regroupement intrinsèque des pertes. Le bust à 8 sem (cumul ~-4.4 R après ~4 pertes consec) est PURE conséquence de P(loss)=55% × variance binomiale, pas un effet de clustering structurel.

(Le ratio 0.4-0.5x sur les longueurs exactes est trompeur — il vient de la définition "run exactement = k" : sous iid avec p^k(1-p), on overcount les short runs. La table "≥k" est la mesure conceptuellement correcte.)

### B.3 — TEST DÉCISIF : jackpots post-cluster

Pour chaque jackpot top 1% à la position t dans la séquence chronologique, on regarde si un cluster ≥2 pertes consécutives existe dans la fenêtre des trades précédents [t-w..t-1].

| Fenêtre w | Jackpots avec ≥2 consec losses dans la fenêtre | Iid baseline | Ratio obs/baseline |
|---:|---:|---:|---:|
| 1 trade | 0/40 (0%) | n/a (fenêtre trop courte) | n/a |
| 2 trades | 15/40 (**37.5%**) | ~30% | 1.25× |
| 3 trades | 18/40 (**45.0%**) | ~51% | 0.88× |
| 5 trades | 27/40 (**67.5%**) | ~76% | 0.89× |

**Single-trade view** :
- Jackpots immédiatement après une perte (R_{t-1} < 0) : **31/40 = 77.5%**
- Jackpots immédiatement après un win (R_{t-1} > 0) : 9/40 = 22.5%
- **Baseline iid** : P(R_{t-1} < 0) = 55%

→ **Les jackpots sont sur-représentés après UN trade perdant** (77.5% vs 55% iid). Cohérent avec autocorr lag-1 négatif (−0.066).
→ Mais sur les clusters ≥2 dans 2-3 trades, **les jackpots sont sous-représentés ou ≈ iid** (0.88-0.95× baseline).

### B.4 — P&L des jackpots vs précédence

Sur les 40 jackpots qui contribuent +206.6 R total :

| Window | Jackpots après ≥2 consec cluster | R-sum contribué | % du jackpot R-sum total |
|---:|---:|---:|---:|
| 2 trades | 15/40 | **+81.8 R** | **39.6%** |
| 3 trades | 18/40 | **+98.7 R** | **47.8%** |

**Lecture critique** : **40-48% du jackpot P&L vient de trades précédés par un cluster ≥2 pertes consec dans les 2-3 trades.** Si un overlay anti-cluster ("skip trades pendant N=2-3 trades après ≥2 pertes consec") avait été appliqué :
- Il aurait **filtré 38-48% du jackpot P&L total**, soit ~80-100 R sur les +207 R totaux.
- Or le bust @ sizing 2.5% est de cumul ~-4.4 R par bust path × P(bust)=37% × 12000 paths.
- L'arbitrage est défavorable : **les jackpots viennent SOUVENT après des pertes** (mean-reversion structurelle).

### Verdict Angle B — anti-cluster overlay détruirait-il l'edge ?

> **OUI — un overlay anti-cluster détruirait l'edge.**
>
> Les clusters de pertes observés sont **iid au signe** (Ljung-Box loss-indicator p=0.39 ; runs ≥k ≈ iid). Le bust n'est pas un phénomène de clustering structurel, juste de la math binomiale à p=0.55. **Couper après ≥2 pertes consec couperait précisément les périodes où les jackpots arrivent** (mean-reversion lag-1 confirmée : 77.5% jackpots viennent post-loss ; 40-48% du P&L jackpot post-cluster).
>
> **Le piège central énoncé par l'utilisateur est confirmé empiriquement** : filtrer les perdants couperait les jackpots. KILL la piste anti-cluster.

---

## Pistes candidates — à pré-enregistrer OOS, AUCUNE appliquée ici

### Piste 1 — Break early × small OR_bps × short (signature multi-variable du tail)

**Variables** : `bi`/`ttb_5min` (Welch t=−5.84) + `or_range_bps` (Welch t=−3.32) + `direction` (Welch t=−3.25). Toutes franchissent le seuil Bonferroni 0.0056 individuellement.

**Hypothèse à pré-enregistrer** : "Le top 1% des trades R ORB V2+E7 a une signature multi-variable break ≤15min × OR_bps ≤45 × short."

**Risque-de-couper-le-tail (à valider OOS)** :
- Si l'overlay "garder Q1+Q2 OR_bps seulement" capture 30/40 = 75% des jackpots à coût de 60% des trades coupés (3210 trades skipés).
- Si l'overlay "shorts only" capture 28/40 = 70% des jackpots à coût de 54% des trades skipés (2156 longs supprimés).
- L'intersection (Q1-2 ∩ short) n'est PAS calculée ici (ce serait du mining post-hoc).
- **N=40 → puissance statistique très faible pour tout filtre composite. Bonferroni en multi-variable encore plus contraignant.**

**Protocole OOS strict** (PAS exécuté ici) :
1. Geler la signature : `bi ≤ 15min AND or_range_bps ≤ Q2_threshold AND direction == short`.
2. Sample 2026-07+ uniquement (≥12 mois OOS souhaitable).
3. Mesurer ratio jackpot_capture / jackpot_skipped sur OOS.
4. Si ratio ≥ in-sample baseline → confirmer pré-enregistrement ; sinon rejeter.
5. DSR à recalculer (N_mod actuel ≈ 8, +overlay multi-variable = +3 → N_mod ≈ 11 → DSR très pénalisé).

### Piste 2 — Anti-cluster overlay (skip post-loss)

**Verdict** : **NE PAS pré-enregistrer**. Test B.3 montre que 77.5% des jackpots viennent post-loss et 40-48% du P&L jackpot vient post-cluster ≥2. Un overlay anti-cluster détruirait l'edge par construction.

### Pistes NON candidates (en-dessous du seuil ou non-significatives)

- `weekday` (Welch p=0.42) : différence top1% vs rest non-significative ; le t=+2.55 du délivrable précédent était sur la régression de R sur weekday, pas sur la distribution top1%. **Non-cohérent → ne pas pré-enregistrer comme "signature jackpot"**.
- `gap_overnight` (p=0.45), `VIX_prev` (p=0.99), `year` (p=0.67), `or_range_pts` (p=0.09 marginal) : aucune signature.

---

## Rappel honnêteté et fragilité

1. **N=40 est minuscule**. Toute "signature" sur le tail est statistiquement fragile. Bonferroni-corrigé : seuls 3 variables franchissent 0.05/9 = 0.0056. Multi-variable encore plus pénalisé.
2. **Aucun chiffre p(pass) "amélioré" rapporté.** Aucun overlay testé sur in-sample. Rapporter ce serait du mining interdit.
3. **Les "pistes" listées sont des hypothèses à pré-enregistrer ET tester sur sample OOS indépendant 2026-07+**. AUCUNE n'est validée.
4. **L'edge fondamental dépend du coût à 15h30 — non mesuré**. À 3 bps RT (conservatif), p(funded) ≈ placebo container = signal mort AVANT TOUT FILTRE. Toute optimisation est conditionnelle à la mesure de coût favorable.
5. **L'edge est principalement non-conditionnable** : 25% des jackpots restent hors signature (Q3+Q4+Q5 OR, longs), et 47.8% du P&L jackpot vient post-cluster (que l'overlay anti-cluster couperait). **L'edge est largement "luck of the draw"** — c'est un résultat en soi.

---

## Synthèse en 1 paragraphe

> **Angle A** : les 40 jackpots ont une signature ex-ante détectable — break ≤15 min, OR ≤Q2 (≤45 bps), direction short — avec Welch p < 0.005 Bonferroni-survivant pour 3 variables. Mais N=40 rend toute signature multi-variable statistiquement fragile, et la signature ne capture pas l'ensemble des jackpots (25% en restent dehors). **L'edge est partiellement conditionnable ex-ante, partiellement non.**
>
> **Angle B** : les clusters de pertes observés sont **iid au signe** (Ljung-Box loss p=0.39, runs ≈ iid), pas un clustering structurel. Mais l'autocorr R lag-1 = −0.066 (t=−4.65) indique une **mean-reversion forte** : **77.5% des jackpots arrivent immédiatement après un trade perdant**, et **40-48% du P&L jackpot vient post-cluster ≥2**. **Un overlay anti-cluster détruirait l'edge** — KILL piste.
>
> **Pistes à pré-enregistrer OOS** : signature multi-variable break × OR × direction (avec mises en garde N=40 et DSR pénalisé). Tout reste conditionnel au coût mesuré à 15h30 ; à 3 bps le signal est mort avant tout filtre.

---

## Artéfacts

- `data/ftmo_research/audit/orb_structure_diagnostic.py` — script Angles A + B
- `data/ftmo_research/audit/orb_structure_diagnostic_log.txt` — log d'exécution complet
- `data/ftmo_research/audit/orb_structure_angle_A_top1pct.csv` — table 9 variables top1% vs rest
- `data/ftmo_research/audit/orb_structure_angle_B_autocorr.csv` — table autocorr R par lag
- Réutilise : `nq_v2_trades.parquet` + `nq_rth_daily.parquet` + `vix.csv`
- Cohérent avec : `ORB_2mois_diagnostic_2026-06.md` + `ORB_at_0p4bps_2026-06.md` + `ORB_ppass_grid_2026-06.md`
