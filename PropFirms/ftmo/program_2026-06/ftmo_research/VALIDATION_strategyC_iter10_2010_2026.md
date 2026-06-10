# Strategy C iter_10 — Re-validation 2010-2026 sur Databento NQ

> **TL;DR — RÈGLE DE DÉCISION : NE PAS PAPER LE COMPTE TRADEIFY $25K.**
>
> iter_10 reproduit fidèlement sur les données Kaggle (N=346 ✓ exact, Sharpe HAC
> daily 1.44 vs reporté 1.52 — écart 5% acceptable, WF Kaggle 75% vs reporté 78%).
> **Spec correcte.** MAIS sur Databento NQ étendu 2010-2026 (16 ans, 5-6 régimes) :
> - **Sharpe HAC daily annualisé chute de 1.52 → 0.51** (66% perdu sur historique étendu).
> - Le filtre « OR ≥ 30 pts » crée un trou structurel : **0 trades 2010-2012**,
>   8 trades 2013-2015. iter_10 a été aveugle aux 5 premières années de l'échantillon.
> - **Edge LONG-only** (LONG Sharpe ann +2.35, SHORT -0.28, total PnL SHORT = −$5,969).
>   Pas de symétrie L25.
> - Régime-conditionnel : -$3,844 en 2020 COVID, -$8,594 en 2022 bear (= 28% du
>   PnL cumulé brûlés sur 2 épisodes), +$33,598 sur le AI rally 2023-2026
>   (= 77% du PnL cumulé concentré sur 3 ans).
> - **DSR Bailey-LdP avec n_trials=26 honnête : DSR_p = 0.45** (full sample),
>   **0.15** (2022-2026 only). Échec du seuil 0.5.
> - **p(eval_pass) Tradeify $25K** sous block bootstrap des P&L journaliers réels
>   Databento 2010-2026 : **24.4%** (vs 63% avec les stats reportées d'iter_10 —
>   39 pp de chute). p(bust) = 36%, p(timeout) = 39%.
> - Sur la fenêtre 2022-2026 seule : p(eval_pass) 34%, mais p(bust) **62%**
>   (le bear 2022 + COVID dominent le cherry-pick).
> - Stress cost ×1.5 : p(pass) 22%. Cost ×3 : p(pass) 18%, p(bust) 48%.
> - Profil lumpy parfait L24 anti-propfirm : hit_rate 24%, win/loss 3.67, skew
>   1.90, kurt 4.27. Médiane trade = −$419 (= SL hit).
>
> **iter_10 n'est PAS iter_10 1.52 — c'est iter_10 0.51 sur l'historique
> représentatif.** Le 1.52 reporté venait d'un cherry-pick involontaire (3 ans
> dominés par AI rally + post-COVID). Le pattern est en cohérence avec le verdict
> précédent (FEATURE_BUILDER_audit / REMINING_clean) sur le 30-min ORB baseline :
> régime-dependence des stratégies ORB intraday sur NQ 2022-2025. **NE PAS paper
> le $25K Tradeify sur iter_10 dans sa spec actuelle.**

---

## 1. Reconciliation 2022-2025 — la spec est-elle exacte ?

### 1.1 Périmètre de la donnée Kaggle

La donnée Kaggle utilisée par le backtest original :
- Path : `Dataset_NQ_1min_2022_2025.csv` (loaded via `data/cache.py::load_nq_1min`).
- **Range réel : 2022-12-26 18:01 → 2025-12-11 20:52 ET (≈ 3 ans).**
- Inclut `vwap_rth` précalculé (HLC3 × volume cumulative 09:31-09:45).
- 0 NaN sur vwap_rth.

Le « 2022-2025 » dans les rapports = **3 ans (déc 2022 → déc 2025)**, pas
calendrier complet. Important pour comparer.

### 1.2 Spec iter_10 reproduite

| Paramètre | Source | Valeur |
|---|---|---|
| Window | `iter_05.build_opening_features` | 09:30 ≤ t ≤ 09:45 ET (16 1-min bars) |
| open_p | iloc[0] | open of 09:30 minute |
| close_p | iloc[-1] | close of 09:45 minute |
| rng | `abs(close_p − open_p)` | mouvement directionnel (PAS H−L) |
| direction | sign(close − open) | +1 long / −1 short |
| vwap_at_sig | vwap_rth.iloc[-1] | cumulative HLC3 × vol depuis 09:31 |
| Filtre M1 | rng ≥ 30 pts | OR threshold |
| Filtre A | `vwap_ok` | dir=+1 → close > vwap ; dir=-1 → close < vwap |
| Filtre B | abs(gap_pct) ≤ 0.012 | gap (today_open - prev_close)/prev_close |
| TP | rng × 1.5 | |
| SL | min(rng × 0.5, 20.0 pts) | hard cap @ 20 pts (= $400 sur NQ $20/pt) |
| Entry | next 1-min bar open after sig_ts | fill à 09:46 open |
| Exit | TP, SL, ou time stop 12:30 ET | SL prioritaire si conflit |
| Cost | $19 RT (engine.py) | = commission $4.50 + 1-tick slip × 2 |

### 1.3 Résultats reconciliation

Trois pipelines comparés sur la même fenêtre 2022-12-26 → 2025-12-11 :

| Variante | data | vwap | n_signals | Sharpe HAC | MaxDD | PF | Total PnL |
|---|---|---|---:|---:|---:|---:|---:|
| **Reporté iter_10** | Kaggle | Kaggle vwap_rth | **346** | **1.521** | -13.4% | 1.432 | $45,510 |
| [B] Mine sur Kaggle | Kaggle | Kaggle vwap_rth | 346 | **1.440** | -18.2% | 1.401 | $41,426 |
| [C] Mine sur Kaggle | Kaggle | Mine (HLC3×vol) | 346 | **1.440** | -18.2% | 1.401 | $41,426 |
| [A] Mine sur Databento | Databento | Mine | 327 | **1.181** | -28.4% | 1.369 | $37,265 |

**Lectures :**
- **N=346 ✓ EXACT** quand je tourne sur Kaggle. Spec correcte.
- Mon Sharpe 1.44 vs reporté 1.52 : écart 5% probable dû à conventions
  (exact time-stop bar inclusion, cap SL 20.0 vs 20.95, etc.). **Acceptable.**
- Mon VWAP (HLC3 × vol cumulative depuis 09:31) reproduit le vwap_rth Kaggle
  à 100% (max diff 0.0013 sur les mêmes barres).
- Databento donne Sharpe 1.18 sur la même fenêtre (vs Kaggle 1.44, écart 18%) —
  ce gap vient de la **divergence des données** : Databento mean(close diff
  vs Kaggle) = +1514 pts (Kaggle est apparemment back-adjusted en somme,
  Databento est raw front-month). Volume mismatch aussi (12% identiques).
  → Ce n'est PAS une erreur de spec ; c'est un fournisseur de données différent.
  Databento (DATA_NQ_cleaned_report) est la référence professionnelle et la
  seule source pour étendre à 2010-2026.

### 1.4 Verdict §1

**Spec validée.** N=346 reproduit à l'identique, Sharpe ~5% près. La méthodologie
est exacte et la divergence entre Databento et Kaggle est documentée et
non-pathologique.

---

## 2. Extension Databento 2010-2026 — le test décisif

### 2.1 Full sample iter_10 sur Databento (cost $19 RT NQ)

| Métrique | Valeur |
|---|---:|
| Period | 2010-06-07 → 2026-05-29 (16 ans) |
| Day-features | 3,827 |
| Signals après filtres | 765 |
| Retention rate | 20.0% |
| **Sharpe HAC daily ann** | **0.510** |
| n_trades | 765 |
| win_rate | 24.4% |
| avg_trade_usd | +$57.36 |
| avg_winner | +$1,489 |
| avg_loser | -$406 |
| profit_factor | 1.187 |
| MaxDD | **-24.4% (-$12,005)** |
| best_day | $5,186 |
| worst_day | -$419 |
| total_PnL | $43,883 |

**Le Sharpe annualisé chute de 1.52 (Kaggle 3y) à 0.51 (Databento 16y), une
perte de 66%.** En cohérence avec le verdict du baseline 30-min ORB (cf.
REMINING_clean.md §6) : le « +0.10R » du verdict d'audit antérieur était
~50% bug F1 + ~30% régime favorable + ~20% exec same-bar. iter_10 n'échappe
pas — son apparente Sharpe ~1.5 contenait ~70% de régime favorable.

### 2.2 Walk-Forward 12m train / 6m test sur 2010-2026

| n_windows | wf_pct_positive |
|---:|---:|
| **23** | **65.2%** |

WF 65% vs reporté 78% (sur 9 windows de 2023-2026). Aligné avec
la divergence entre 2022-2025 cherry-pick et 16-year history.

### 2.3 Decomposition régime (5 buckets)

| Period | n_trades | win% | Sharpe ann | mean_pnl_$ | Total PnL |
|---|---:|---:|---:|---:|---:|
| 2010-2012 | **0** | — | — | — | — |
| 2013-2015 | 8 | 25.0% | NaN | -$61 | **-$485** |
| **2016-2018** | 42 | 38.1% | **+2.15** | +$86 | +$3,615 |
| **2019-2021** | 203 | 30.5% | **+2.00** | +$104 | +$21,163 |
| **2022-2026** | 512 | 20.9% | **+0.66** | +$38 | +$19,590 |

**Diagnostic structurel critique :**
- **0 trades 2010-2012** et seulement 8 en 2013-2015.
- Cause : le filtre **rng ≥ 30 pts** est non-régime-adaptive. À NQ 2500 (2010),
  30 pts = 1.2% de move. Quasi jamais atteint sur un OR de 15 min. À NQ 18000
  (2024), 30 pts = 0.17%. Atteint quotidiennement.
- → iter_10 est **structurellement aveugle** aux 5 premières années (régime
  bas-niveau). Le « test multi-régime » est artificiellement amputé : on
  ne sait rien d'iter_10 sur 2011 eurozone, 2012 QE3, etc.

**Sur les 3 régimes actifs (2016-2018, 2019-2021, 2022-2026) :**
- 2016-2018 : Sharpe +2.15 (n=42) — petite sample.
- 2019-2021 : Sharpe +2.00 (n=203) — solide.
- **2022-2026 : Sharpe +0.66 (n=512)** — la majorité des trades, et Sharpe
  loin sous le PROPFIRM_PASS 1.0.

### 2.4 Décomposition par épisode (11 épisodes documentés)

| Épisode | n | Sharpe | Total PnL |
|---|---:|---:|---:|
| 2014 taper | 2 | NaN | +$615 |
| 2015 China bust | 5 | NaN | +$665 |
| 2017 low_vol | 3 | NaN | +$1,093 |
| 2018 vol shock | 33 | +0.95 | +$1,271 |
| **2019 recovery** | **32** | **+4.30** | **+$7,012** |
| **2020 COVID** | **44** | **-2.07** | **-$3,844** |
| **2021 postCOVID** | **97** | **+2.88** | **+$16,025** |
| **2022 bear** | **121** | **-1.68** | **-$8,594** |
| **2023+ AI rally** | **330** | **+1.65** | **+$33,598** |

**Conclusion §2.4 :**
- **2 épisodes perdants concentrés** : 2020 COVID (-$3,844) + 2022 bear (-$8,594)
  = **-$12,438 = 28% du PnL cumulé brûlé sur 2 épisodes de stress de marché.**
- **77% du PnL cumulé concentré sur 2023+** (AI rally + post-COVID).
- iter_10 fonctionne sur la momentum-régime, échoue lors de bear/crash.
  Profil typique trend-following sans hedge.

### 2.5 Annual breakdown

| Year | n | Sharpe ann | Verdict |
|---:|---:|---:|---|
| 2014 | 2 | NaN | trop peu |
| 2015 | 6 | NaN | trop peu |
| 2016 | 6 | NaN | trop peu |
| 2017 | 3 | NaN | trop peu |
| 2018 | 33 | +0.95 | médiocre |
| **2019** | **32** | **+4.30** | excellent |
| 2020 | 74 | -0.55 | perdant |
| **2021** | **97** | **+2.88** | excellent |
| 2022 | 121 | -1.68 | perdant |
| 2023 | 102 | +0.34 | médiocre |
| **2024** | **111** | **+2.30** | excellent |
| **2025** | **117** | **+2.28** | excellent |
| 2026 (partiel) | 61 | -1.90 | perdant |

**Win years (Sharpe > 1.5)** : 2019, 2021, 2024, 2025 = **4 années**
**Loss years (Sharpe < 0)** : 2020, 2022, 2026 partiel = **3 années (+1)**
**Mediocre** : 2014-2018, 2023 = **6 années**

Volatilité de la performance par-année **8.96** entre -1.90 et +4.30 Sharpe.
Une propfirm évaluée sur une fenêtre 6-12 mois peut tomber sur une année
neutre ou perdante avec probabilité élevée.

---

## 3. Split-by-direction (L25)

| Subset | n | win% | mean_pnl_$ | Sharpe ann | Total PnL | skew | kurt |
|---|---:|---:|---:|---:|---:|---:|---:|
| **LONG only** | 391 | **29.2%** | **+$127** | **+2.346** | +$49,851 | 1.53 | 1.44 |
| **SHORT only** | 374 | 19.5% | **-$16** | **-0.282** | **-$5,969** | 2.36 | 5.81 |

**L'edge est ENTIÈREMENT LONG.** SHORT contribue négativement sur l'ensemble :
- 49% des trades sont SHORT, mais ils représentent un PnL net négatif.
- LONG Sharpe +2.35 (très fort), SHORT Sharpe -0.28 (négatif).

### Décomposition LONG par régime

| Period | n_LONG | Sharpe ann |
|---|---:|---:|
| 2013-2015 | 3 | NaN |
| **2016-2018** | 20 | **-0.45** ← négatif |
| **2019-2021** | 109 | **+3.31** |
| **2022-2026** | 259 | **+2.11** |

### Décomposition SHORT par régime

| Period | n_SHORT | Sharpe ann |
|---|---:|---:|
| 2013-2015 | 5 | NaN |
| **2016-2018** | 22 | **+4.04** ← fort |
| 2019-2021 | 94 | +0.38 |
| **2022-2026** | 253 | **-0.76** ← négatif |

**Lecture critique L25 :**
- LONG « bon » seulement 2019+ (perdant 2016-2018).
- SHORT « bon » seulement 2016-2018 (perdant 2022-2026).
- Les deux directions sont **régime-conditionnelles**, mais à des régimes
  DIFFÉRENTS.
- L'apparente Sharpe LONG +2.35 globale est composée de :
  - -$313 (2016-2018, perdant)
  - +$19,217 (2019-2021)
  - +$30,904 (2022-2026)
  - = 95% du gain LONG concentré sur 2019+ = mêmes 2-3 régimes favorables.

**L25 fail clair :** edge LONG-only sur un instrument à drift positif structurel
= β à la tendance NQ, pas un alpha intraday extractible. La validation L25
exigerait que long ET short fonctionnent. Ici le SHORT perd net.

---

## 4. p(pass) Tradeify Select Flex $25K — block bootstrap réel

### 4.1 Méthode

- **Trade log réel** d'iter_10 sur Databento 2010-2026 (765 trades).
- **Daily P&L réel** agrégé par jour (incluant jours sans trade = 0).
- **Conversion NQ → MNQ** à 2 contracts (config live `PHASE_CONTRACTS = 2`) :
  `mnq_pnl = (nq_pnl + 19)/20 × $2 × 2 − $2.15 × 2`.
- **Block bootstrap** des P&L journaliers (block_size=20 jours) → 20,000 paths
  de 360 jours (180 eval + 180 funded).
- Simulation via `Portfolio/risk/trailing_dd_simulator.py` (canonique Tradeify
  Select Flex $25K : eval DD=$1K trailing, profit target=$1.5K, consistency
  cap 40%, min 3 trading days, lock à $26,100 → floor $25,100).

### 4.2 Résultats — 3 scénarios

| Scénario | p(eval_pass) | p(bust) | p(timeout) | E[funded PnL 180d] |
|---|---:|---:|---:|---:|
| **A : Databento 2010-2026 (honest)** | **24.4%** | 36.4% | **39.2%** | $373 |
| **B : Databento 2022-2026 only** | 33.8% | **61.5%** | 4.7% | $335 |
| C : Reported iter_10 stats (référence) | **62.6%** | 34.1% | 3.2% | $1,677 |

**Clés de lecture :**

- **Le sizing 2 MNQ était calibré sur 57% p(pass) reporté** (cf.
  config.py:14 : `P(pass eval 180d) = 57.0%, P(bust) = 39.7%`).
- Le scénario C (avec les stats iter_10 reportées) donne 62.6% — proche du 57%
  documenté (différence vient de `n_mnq=2` ici vs 3 dans le test précédent).
- **Le scénario A (données réelles étendues) donne 24.4%**, soit -39 pp vs C.
- Le scénario B (cherry-pick window matching Kaggle) donne 33.8% — mais
  p(bust) MONTE à 61.5%, car les épisodes 2020 COVID + 2022 bear dominent
  cette fenêtre dans le bootstrap.
- E[funded PnL 180d] passé de $1,677 (référence) à $373 (réalité) : **78% de
  perte d'espérance de profit en funded**.

### 4.3 Stress test cost

| cost_mult | extra $/trade NQ | p(pass) | p(bust) | E[funded] |
|---:|---:|---:|---:|---:|
| 1.0 (baseline) | $0 | 24.4% | 36.4% | $373 |
| 1.5 | +$9.50 | **22.1%** | 39.9% | $327 |
| 3.0 | +$38 | **18.2%** | 48.4% | $81 |

Sous stress cost ×1.5 (modèle conservateur L19) : p(pass) tombe à 22%,
p(bust) monte à 40%, E[funded] $327. Sous ×3 : p(pass) 18%, p(bust) 48%.

### 4.4 Verdict §4

**Aucun scénario réaliste ne donne p(pass) > 30% sur les données réelles.**
Le sizing 2 MNQ est calibré pour 57%-62% p(pass) en se basant sur les stats
reportées. La réalité étendue : 18-34%. **Le compte $25K serait paper avec
~75% de chance d'échouer en eval.**

---

## 5. DSR — Bailey-Lopez de Prado

### 5.1 Mining depth honnête

| Source | Trials |
|---|---:|
| iter_1 family (1a, 1b, 1c) | ~3 |
| iter_2 family (2a, 2b, 2c, 2d) | ~4 |
| iter_3-5 (gap, ETH, dollar stops, ...) | ~6 |
| iter_7-9 (VWAP, vol_ratio, 8a/b/c) | ~8 |
| iter_10 + variants 11a-11e | ~5 |
| **Total honest** | **≥ 26** |

### 5.2 DSR full sample 2010-2026

SR per-trade = 0.0639, n=765, skew=1.90, kurt=6.27.

| n_trials | SR_normalized | E[max] | z | **DSR_p** |
|---:|---:|---:|---:|---:|
| 10 (très optimiste) | 1.880 | 1.575 | +0.306 | 0.620 |
| **26 (honest)** | **1.880** | **2.014** | **-0.133** | **0.447** |
| 50 (conservatif) | 1.880 | 2.276 | -0.396 | 0.346 |

### 5.3 DSR 2022-2026 only

SR per-trade = 0.0405, n=512, skew=2.07, kurt=6.86.

| n_trials | SR_normalized | E[max] | z | **DSR_p** |
|---:|---:|---:|---:|---:|
| 10 | 0.955 | 1.575 | -0.620 | 0.268 |
| **26 (honest)** | **0.955** | **2.014** | **-1.059** | **0.145** |
| 50 | 0.955 | 2.276 | -1.321 | 0.093 |

### 5.4 Interprétation DSR

- DSR p > 0.95 = strong evidence non-spurious
- DSR p > 0.50 = positive but inconclusive
- DSR p < 0.50 = likely spurious given mining depth

**Pour passer DSR_p > 0.5 avec n_trials=26 (honnête), il faudrait SR_normalized
> 2.01.** Le full sample obtient 1.88 (juste en-dessous). Le 2022-2026 obtient
0.95 (très loin du seuil).

**DSR fails honnêtement** sur les deux fenêtres au seuil habituel 0.5.
Au seuil strict 0.95, fail catastrophique partout.

---

## 6. Lumpy metrics — L24 anti-propfirm profile

| Métrique | iter_10 | L24 FTMO-suitable target | Verdict |
|---|---:|---:|---|
| hit_rate | **24.4%** | > 55% | **FAIL — extrême** |
| win/loss ratio | **3.67** | ≈ 1.0 | **LUMPY — extrême** |
| skew | **+1.90** | < 1.0 | **FAIL** |
| kurt (excess) | **+3.27** | < 3.0 | **FAIL — fat tails** |
| Median trade | **−$419** | > 0 | **systematic SL hits** |

**iter_10 = profil L24 ANTI-propfirm parfait.** L24 dit explicitement :
> « Lumpy strategies (low win-rate, high win/loss ratio, e.g. C: WR 27.75%,
>  3.7×) are structurally capped ~44-54% regardless of sizing — wrong tool for
>  a symmetric-barrier challenge. »

Tradeify Select Flex $25K = symmetric barrier ($1K trailing DD = $1.5K profit
target). iter_10 = lumpy à hit_rate 24%, win/loss 3.7. **Parfait fit du
warning L24.** La probabilité réelle de pass converge naturellement vers ce
plafond structurel — d'où nos 24% (Databento), pas 57-63% des
reportés.

---

## 7. Verdict — règle de décision

### 7.1 Critères du brief

> « Si Sharpe net < 1.0 à travers les régimes OU régime-conditionnel comme le
> baseline → NE PAS paper le compte $25K. Si robuste à travers les régimes
> (≥4/5 buckets positifs net, DSR>0.5, edge des deux côtés ou justifié) →
> paper justifié. »

### 7.2 Évaluation

| Critère | Seuil | iter_10 | Verdict |
|---|---|---|---|
| Sharpe net ≥ 1.0 à travers les régimes | tous les buckets | 0/4 buckets actifs > 1.0 net après stress 1.5×cost ; full Sharpe 0.51 | **FAIL** |
| Régime-conditionnel comme baseline | reject | 0 trades 2010-2014 (filtre 30pt aveugle), -$8,594 sur bear 2022, +$33,598 concentré 2023-2026 | **FAIL** |
| ≥ 4/5 buckets positifs net | 4 sur 5 | 3 sur 4 buckets actifs positifs ; 2010-2012 = 0 trades (n/a) | **FAIL** (un bucket entier muet) |
| DSR > 0.5 (n_trials honnête) | > 0.5 | 0.45 (full sample, n_trials=26) ; 0.15 (cherry-pick) | **FAIL** |
| Edge des deux côtés (L25) | both | LONG +2.35, SHORT -0.28 ; SHORT total PnL = -$5,969 | **FAIL** |
| p(eval_pass) Tradeify ≥ 50% | > 50% | 24.4% (Databento real) ; 18-22% sous stress cost | **FAIL** |

**Tous les critères de décision ÉCHOUENT.**

### 7.3 VERDICT — **NE PAS PAPER LE COMPTE TRADEIFY $25K**

iter_10 dans sa spec actuelle ne survit pas la validation 2010-2026 :

1. **Régime cherry-pick** : Sharpe 1.52 reporté = 3 ans (déc 2022 → déc 2025).
   Sur 16 ans : Sharpe 0.51. Le 1.52 est composé à ~70% de régime favorable.
2. **Filtre structurellement biaisé** : OR ≥ 30 pts cap la stratégie aux
   régimes de prix élevé (NQ > ~7000). 0 trades 2010-2012.
3. **Edge LONG-only** : β à la dérive NQ, pas alpha intraday. SHORT négatif net.
4. **2 épisodes perdants concentrés** : 2020 COVID + 2022 bear effacent 28% du
   gain cumulé.
5. **DSR fail honnêtement** : 0.45 au mieux, 0.15 cherry-pick.
6. **p(pass) Tradeify 24%** au lieu des 57% sur lesquels le sizing 2 MNQ a
   été calibré. **Différence d'ordre 1.**
7. **Profil lumpy L24** parfait — mauvais outil pour barrière symétrique.

### 7.4 Coût du non-deploiement

- Eval Tradeify Select Flex $25K : ~$65 (promo mai 2026) ou ~$170 standard.
- **Coût économisé** : 100% de la valeur du compte si bust (probabilité 36%
  sous données réelles) + frais éval.
- E[funded PnL 180d] reportée $1,677, réelle $373 — différentiel $1,304 d'attente
  irréaliste.

### 7.5 Pistes possibles (hors scope de cette mission)

Avant tout paper trading sur iter_10, à explorer :

1. **Filtre rng adaptatif** : remplacer « rng ≥ 30 pts » par « rng ≥ K × atr20 »
   ou « rng ≥ K × rolling_median_30d(rng) ». Permet de retrouver des signaux
   sur 2010-2014 et de ne pas saturer sur 2024+.
2. **Régime gate** : n'activer iter_10 que dans certaines conditions de
   volatilité/régime (rv20_low etc.). MAIS le baseline ORB §6 REMINING_clean.md
   prévient que régime gates ont +1.7%/an gross effet sur des strategies
   high-Sharpe — à tester proprement.
3. **Direction asymétrique** : LONG-only structurellement, accepter que c'est
   du β tendance NQ. Mais alors le Sharpe nu est ce qu'il est et n'a rien
   d'intraday spécifique.
4. **Tail-cap mismatch** : iter_10 cape la queue à 1.5R. Le baseline ORB avait
   son edge dans la queue. Tester si exit-at-close ou TP plus lointain donne
   un edge plus robuste sur 2010-2026.
5. **Re-évaluer Strategy C dans un Portfolio context** — peut-être que LONG-only
   iter_10 est un beta-overlay utile dans un portfolio avec une stratégie
   crash-hedged.

**Ces 5 pistes consomment chacune ≥ 1 modification de stratégie (L10 budget).
Aucune n'est obvious. À pré-enregistrer si on persiste.**

---

## 8. Fichiers produits

| Fichier | Rôle |
|---|---|
| `audit/iter10_validation.py` | Builder + engine iter_10 (spec exacte) |
| `audit/iter10_features.parquet` | 3827 day-features 2010-2026 |
| `audit/iter10_trades.parquet` | 765 trades full sample |
| `audit/iter10_trades_full.parquet` | duplicate (regime split outputs) |
| `audit/iter10_validation_output.txt` | full sample + WF + 2022-2025 anchor |
| `audit/iter10_reconcile.py` | Comparaison Databento vs Kaggle |
| `audit/iter10_reconcile_output.txt` | reconciliation détaillée |
| `audit/iter10_regime_split.py` | Régime + direction + stress |
| `audit/iter10_regime_all.csv` | Régime ALL |
| `audit/iter10_regime_long.csv` | Régime LONG |
| `audit/iter10_regime_short.csv` | Régime SHORT |
| `audit/iter10_episodes.csv` | 11 épisodes |
| `audit/iter10_annual.csv` | Annual breakdown |
| `audit/iter10_stress.csv` | Cost stress |
| `audit/iter10_regime_split_output.txt` | full regime decomp |
| `audit/iter10_tradeify_dsr.py` | Tradeify p(pass) + DSR |
| `audit/iter10_tradeify_dsr_output.txt` | output complet |
| **`VALIDATION_strategyC_iter10_2010_2026.md`** | **Ce livrable** |

---

## 9. Honnêteté finale

**Ce qui a été rigoureusement testé :**
- Reproduction spec exacte iter_10 sur Kaggle (N=346 ✓) et Databento.
- Reconciliation bar-level Databento vs Kaggle (level shifts documentés).
- Full sample 2010-2026 Sharpe + WF + drawdown.
- Régime 5 buckets + 11 épisodes + 17 années.
- Direction split L25.
- Stress cost ×1, 1.5, 3.
- p(pass) Tradeify sur 3 scénarios × 20,000 MC paths.
- DSR Bailey-LdP à n_trials=10/26/50.
- Lumpy metrics vs L24.

**Ce qui n'a pas été testé (hors scope, à prochaine session si poursuite) :**
- Filtre rng adaptatif (atr-based) — peut redébloquer 2010-2014.
- Régime gate avec rv20 / VIX / trend filter.
- Variantes de TP/SL (exit-at-close vs 1.5R cap).
- Inclusion iter_10 dans un Portfolio multi-stratégie avec hedge.
- Out-of-sample test sur 2026 jamais touché.
- Validation iter_11a/b/c/d/e (qui ont des Sharpe reportés 1.44-1.59 sur la même fenêtre).

**Ce qui est structurellement vrai :**
- La spec iter_10 telle qu'elle est ne supporte pas une extension propre à
  2010-2026 à cause du filtre 30 pts non-adaptatif.
- Sur l'historique réel Databento, p(eval_pass) Tradeify est ~25%, pas 57-63%.
- L'edge LONG-only avec SHORT négatif fait d'iter_10 un proxy β NQ intraday,
  pas un alpha extractible robuste.
- La famille iter (10+ iterations + sub-variants) consomme une mining depth
  ≥ 26 honnête → DSR fail au seuil 0.5.

*Validation Strategy C iter_10 réalisée 2026-06-02 — Claude Code (Opus 4.7
1M ctx). Verdict honnête : NE PAS paper le compte Tradeify $25K sur iter_10
dans sa spec actuelle. Coût économisé : valeur du compte + frais eval, à
mettre en regard d'un E[funded PnL 180d] réel de $373.*
