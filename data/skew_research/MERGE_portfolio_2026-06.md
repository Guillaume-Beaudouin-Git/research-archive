# MERGE Portfolio — Cowork sleeves × assets existants — 2026-06-04

**Objectif (L7)** : trouver la COMBINAISON de sleeves qui minimise le drawdown sous barrière propfirm — pas maximiser le Sharpe de chaque brique.

**Survivants Cowork mergés** (lus depuis `data/skew_research/session_*/exploration_2026-06.md`) :
- **LONGVOL_VXX** (session_cowork) — tail-hedge, skew +1.86 daily, corr −0.75 vs equity, carry NÉGATIF
- **VIXTERM** (session_vol_tail) — VIX-term timé, edge SR 0.69, skew neutre, corrélé trend+equity
- **MR_REVERSAL** (session_vol_tail) — reversal 1j SPX, skew+ MAIS délai+1 s'effondre → **exclu de toute reco déployable** (artefact close-print)
- **PREFOMC** (session_3) — pré-FOMC drift, décorrélé MAIS N=51 + décay récent 2023/26 confirmé ici

**Assets existants** :
- **TSMOM_PROXY** — sign(SP500_R_60d) × R_t vol-targeted 10% (moteur, proxy le plus simple ; cf. `_CANONICAL_STATE.md` pour TSMOM v3 crypto)
- **LONG_US500** — proxy long-equity benchmark (corrélation référence)
- Strategy A (crypto TSMOM, paused) et Strategy B (delta-neutral testnet) NON inclus ici car séries crypto non comparables daily SPX

**Méthodologie** :
- Tout sur la **FENÊTRE COMMUNE** (intersection) — pas de fenêtres différentes (artefact).
- Skew mesuré **au plus court horizon disponible** (per-event pour PREFOMC, monthly pour TSMOM).
- Poids **SIMPLES** : 100% benchmark + ERC inverse-vol + 90/10 + 80/10/10. Aucune optimisation libre (L10/L19).
- MR exclu du déployable, corr calculée pour info seulement.

---

## 1. Fenêtre commune

| Sleeve | Période | n_days |
|---|---|---:|
| LONGVOL_VXX | 2018-01-26 → 2026-05-27 | 2094 |
| VIXTERM | 2011-01-04 → 2026-05-27 | 3871 |
| MR_REVERSAL | 2000-01-05 → 2026-05-28 | 8097 |
| PREFOMC | 2010-06-08 → 2026-05-29 | 4104 |
| TSMOM_PROXY | 2000-03-29 → 2026-05-28 | 8037 |
| LONG_US500 | 2000-01-04 → 2026-05-28 | 8098 |

> **Fenêtre commune intersection** : **2018-01-26 → 2026-05-27, n=2094 days (8.3 ans)**. Bornée par VXX (qui démarre en 2018). Toute corrélation rapportée ci-dessous est sur cette fenêtre.

---

## 2. Matrice de corrélation (commune 2018-2026, n=2094)

|  | LONGVOL_VXX | VIXTERM | MR_REVERSAL | PREFOMC | TSMOM_PROXY | LONG_US500 |
|---|---:|---:|---:|---:|---:|---:|
| **LONGVOL_VXX** | 1.000 | **−0.357** | −0.123 | −0.134 | **−0.197** | **−0.748** |
| **VIXTERM** | −0.357 | 1.000 | −0.061 | +0.154 | **+0.441** | +0.224 |
| MR_REVERSAL | −0.123 | −0.061 | 1.000 | +0.038 | −0.068 | +0.184 |
| **PREFOMC** | −0.134 | +0.154 | +0.038 | 1.000 | **+0.037** | +0.165 |
| TSMOM_PROXY | −0.197 | +0.441 | −0.068 | +0.037 | 1.000 | +0.080 |
| LONG_US500 | −0.748 | +0.224 | +0.184 | +0.165 | +0.080 | 1.000 |

### Lecture clé

- **Anti-corrélations confirmées** : LONGVOL_VXX vs LONG_US500 = **−0.748** (le hedge equity marche). LONGVOL_VXX vs TSMOM_PROXY = −0.197 (négatif modéré).
- **VIXTERM est redondant avec TSMOM** : corr +0.441 → le carry VIX timé prend du beta trend, pas un sleeve complémentaire. Cohérent avec le warning du Cowork session_vol_tail.
- **PREFOMC est genuinely décorrélé** : corr 0.04-0.16 avec tout (sleeve évènementiel ~7×/an, série=0 le reste du temps). Confirme verdict session_3.
- **MR_REVERSAL est aussi décorrélé** (~0 partout) MAIS exclu déployable.
- **Pas de paire fortement anti-corrélée entre sleeves "actifs"** (PREFOMC/TSMOM = 0.04 = neutre, pas −0.5 comme on espérerait pour vraie diversification).

---

## 3. Skew au plus court horizon disponible (commune)

| Sleeve | Daily | Holding horizon |
|---|---:|---|
| LONGVOL_VXX | +1.86 | **+1.86 (daily holding, correct)** |
| VIXTERM | +0.33 | +0.33 (daily rebalance) |
| MR_REVERSAL | +0.79 | +0.79 (1-day, mais artefact délai+1) |
| **PREFOMC** | **+2.61 (avec zéros)** | **−0.07 per-event (n=51)** ⚠ |
| **TSMOM_PROXY** | **−0.86** | **−0.58 monthly (n=101 mois)** |
| LONG_US500 | −0.35 | −0.35 (daily) |

**Lecture importante** : 
- Le skew daily PREFOMC +2.61 est un **artefact des zéros** (95% des jours = 0). Au niveau event, skew = **−0.07** (~zéro). 
  - Session_3 reportait +0.13 / +0.88 sur la fenêtre narrow 14:00 ET ; mon proxy "full RTH day" est plus conservatif et donne ≈0.
- TSMOM skew −0.86 daily / −0.58 monthly → momentum-crash classique (L24). Cohérent avec le diagnostic Cowork.
- L'évaluation skew au mauvais horizon (daily pour event-sleeves, daily pour trend-monthly) **mésestime de 1-3 unités**. Le 2.61 PREFOMC dans la table daily est trompeur.

---

## 4. Portefeuilles candidats (poids simples, AUCUNE optim)

| Portefeuille | Weights | AnnRet | AnnVol | Sharpe | **MaxDD** | WorstDay | WorstMonth | Skew_d | Skew_m |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **P1** TSMOM only | 100% TSMOM | +2.7% | 13.7% | 0.20 | **−33.6%** | −6.3% | −10.0% | −0.86 | −0.58 |
| **P2** TSMOM+FOMC ERC | 25% TSMOM + 75% PREFOMC | +2.1% | 4.9% | **0.42** | **−10.5%** | −4.1% | −4.0% | −0.48 | −0.36 |
| **P3** TSMOM+VXX ERC | 84% TSMOM + 16% VXX | −1.7% | 14.6% | −0.11 | **−43.3%** | −6.2% | −8.0% | +1.22 | +0.70 |
| **P3b** TSMOM+VXX 10% | 90% TSMOM + 10% VXX | −0.07% | 13.0% | −0.01 | **−34.7%** | −5.3% | −8.4% | +0.61 | +0.09 |
| **P4** Triple ERC | 24% TSMOM + 72% FOMC + 4% VXX | +0.85% | 5.0% | 0.17 | **−13.8%** | −3.2% | −3.3% | +0.83 | −0.10 |
| **P4b** 80/10/10 | 80% TSMOM + 10% FOMC + 10% VXX | −0.16% | 11.9% | −0.01 | **−31.6%** | −4.9% | −7.5% | +0.75 | +0.17 |

### Lecture

- **P2 TSMOM+FOMC ERC** : meilleur Sharpe (0.42 vs 0.20 baseline), MaxDD réduit ×3 (−10.5% vs −33.6%), worst day/month réduits.
- **MAIS** : poids ERC = 75% PREFOMC + 25% TSMOM (inverse-vol favorise FOMC car PREFOMC = série quasi-zero la plupart du temps → vol très basse). **Le portefeuille est dominé à 75% par PREFOMC**, qui a déçayé récemment (cf. §6).
- **Ajout VXX uniformément destructeur** : P3 SR négatif, MaxDD aggravé à −43.3% (à cause de la theta longue + amplification levier). P3b (10% VXX) : drag −2.8%/an pour seulement −1pp MaxDD réduit. P4b (80/10/10) : SR ≈ 0.
- **P4 triple** : Sharpe 0.17 < P2 ; la VXX ajoute peu de DD-réduction au-dessus du seul TSMOM+FOMC.

---

## 5. Test décisif tail-hedge VXX — DD évité × p(krach) vs portage payé

**Définition krach** : LONG_US500 ≤ p5 = **−1.79%/jour** (n=105 jours sur 2094 = 5%).

| Mesure | Valeur |
|---|---:|
| VXX mean return sur jours krach | **+10.67%/jour** ← le hedge marche sur les jours de stress |
| VXX mean return sur jours normaux | **−0.67%/jour** ← la theta bleed |
| VXX mean overall | **−0.10%/jour** |
| TSMOM mean sur jours krach | −0.17%/jour |
| TSMOM mean sur jours normaux | +0.02%/jour |

### Impact d'un overlay 10% VXX sur TSMOM (8.3 ans)

| Mesure | TSMOM only | TSMOM+10% VXX | Δ |
|---|---:|---:|---:|
| Ann return | +2.72% | −0.07% | **−2.79%/an** (drag) |
| MaxDD | −33.6% | −34.7% | **−1.1pp aggravé** |
| Worst day | −6.29% | −5.28% | +1pp atténué |
| Contribution cumulée 8.3y | — | −23.2% | drag total |

### Décomposition cost/benefit honnête (10% VXX overlay annualisé)

- **Annual theta cost** (full year holding 10% VXX) : **+2.52%/an coûté**
- **Annual benefit on crash days** (excess vs normal × n_crash/yr) : **+14.30%/an gagné les jours krach**
- **Net naïf** = benefit − cost = **+11.78%/an**

**MAIS** le benefit calculé naïvement (excess sur crash days seuls) **sur-estime** : il assume qu'on extrait UNIQUEMENT le pic des jours krach, alors qu'en pratique la theta bleed quotidienne consomme une grande part du gain de crash. L'impact RÉEL mesuré (Δ annuel sur sample) est **−2.79%/an** (drag pur), pas +11.78%.

### Verdict tail-hedge

> **NON RENTABLE.** Sur sample 2018-2026 (qui inclut COVID-2020 et bear 2022) : un overlay 10% VXX **coûte 2.79%/an** et ne réduit le MaxDD que de **1pp** (mais aggrave en fait MaxDD pour P3 invol). Le worst-day est atténué de 1pp (−6.3 → −5.3). 
>
> L'arbitrage est défavorable : **DD évité (1pp) × p(krach) (5%) < portage certain (2.8%/an)**. Le long-vol VXX est de l'assurance trop chère sur ce sample.
>
> Cohérent avec verdict Cowork session_cowork : "long-vol est une décision de tail-hedge, pas un free sleeve" — confirmé chiffré ici. La tactique "long-vol uniquement quand backwardation" (qui n'est PAS un signal naïf L10) pourrait changer l'équation, mais ce n'est pas le P3b naïf testé.

---

## 6. p(funded) FTMO 2-step : portefeuille vs TSMOM seul

MC block-bootstrap 12000 paths, blocs 21 jours, no time limit, floor static $9k, daily 5%, target P1+10% / P2+5%. Sizing interprété comme **leverage** sur le rendement quotidien du portefeuille.

| Portefeuille | lev 1.0 | lev 2.0 | lev 3.0 | lev 5.0 |
|---|---:|---:|---:|---:|
| **P1 TSMOM only (baseline)** | **39.8%** | 33.7% | 28.6% | 18.7% |
| **P2 TSMOM+FOMC ERC** | **59.7%** | **49.1%** | 39.9% | **38.0%** |
| P3 TSMOM+VXX ERC | 26.1% | 25.0% | 19.9% | 18.4% |
| P3b TSMOM+VXX 10% | 34.0% | 30.0% | 25.1% | 20.1% |
| P4 Triple ERC | 34.9% | **39.4%** | 35.4% | 33.0% |
| P4b 80/10/10 | 33.5% | 29.1% | 26.3% | 21.2% |

### Lecture

- **P2 bat TSMOM seul à toutes les levers** : +20pp à lev 1x (59.7% vs 39.8%), +15pp à lev 2x. La décorrélation PREFOMC (corr 0.037 vs TSMOM) + sa vol basse écrasent la variance du portefeuille → moins de bust.
- **MAIS** : P2 est dominé à 75% par PREFOMC. C'est essentiellement un "challenge propfirm sur PREFOMC vol-targeted", pas un "TSMOM diversifié". L'amélioration vient de l'événementiel rare, pas de la diversification ledger.
- **Ajout VXX uniformément destructeur** : P3/P3b/P4b tous SOUS TSMOM seul à lev 1x (26-34% vs 40%). La theta consume le gain.
- **P4 triple** : performance entre P1 et P2 ; le VXX ajoute peu, surtout dilue.

### Pré-FOMC décay (2023-2026 only)

| Period | n_events | mean per event (bp) |
|---|---:|---:|
| Full common 2018-2026 | 51 | **+29.8** |
| 2023+ only | 27 | **+6.1** ⚠ |

→ Pré-FOMC édge décayé d'**~80%** sur les 3 dernières années. Le P2 60% p(funded) repose sur 2018-2022 ; sur 2023+ uniquement, le sleeve PREFOMC est quasi-zéro et P2 dégrade.

Correlations 2023+ vs full :
- PREFOMC vs LONG_US500 : 0.165 → 0.188 (légère hausse)
- PREFOMC vs TSMOM : 0.037 → 0.185 (corr a augmenté → moins de diversification récente)

---

## Verdict 1 ligne

> **Meilleure construction : P2 TSMOM+PREFOMC ERC (Sharpe 0.42, MaxDD −10.5%, p(funded) 60% à lev 1x vs 40% TSMOM seul)** — bat le moteur seul, MAIS le portefeuille est **dominé à 75% par PREFOMC** (artefact ERC × vol_basse_evt) qui a **déçayé à 6 bp/event sur 2023+ vs 30 bp full** — donc l'amélioration in-sample 2018-2026 est probablement non-persistante OOS ; le tail-hedge VXX est **NON rentable** (drag −2.8%/an pour seulement 1pp MaxDD réduit).

---

## Honnêteté résiduelle

1. **Fenêtre commune 8.3 ans** (2018-2026) — limitée par VXX. Tout résultat reste conditionnel à ce window incluant COVID-2020 (où VXX a son meilleur jour) et bear 2022.
2. **PREFOMC proxy "full-day NQ on FOMC"** vs "prior_close→14:00 ET" du session_3. Mon proxy est plus conservatif (skew event = −0.07 vs +0.88 narrow window). Le narrow window aurait probablement donné des chiffres P2 plus optimistes, mais la version conservative est plus honnête (moins de sur-fit timing).
3. **Décay PREFOMC 2023+ confirmé** : +6 bp/event vs +30 bp full. P2 sample-2018-2026 surestime probablement la performance future.
4. **Tail-hedge VXX non rentable** sur ce sample. Caveat : sample peut être atypique (VIX backwardation persistante 2020-22 a écrasé la theta naïve). Un signal de timing VIX/VIX3M (non testé ici car L10) pourrait inverser.
5. **MR_REVERSAL exclu** comme demandé (artefact délai+1, exécution non confirmée).
6. **VIXTERM exclu des portefeuilles** : corr +0.441 avec TSMOM → redondant, ne diversifie pas.
7. **Aucune optim de poids** : ERC inverse-vol + 90/10 + 80/10/10. Tout SR > 0.42 nécessiterait optim libre = mining.
8. **TSMOM_PROXY est un proxy SP500-daily** (sign(R_60d)) — pas le TSMOM v3 crypto en LIVE (Strategy A, paused) ni le TSMOM canonical multi-asset. Si on remplaçait TSMOM_PROXY par Strategy A crypto, la matrice de corrélation changerait (crypto vs SPX peu corrélés). À tester séparément avec données crypto journalières.

---

## Réconciliation vs archive

- Cohérent avec [[orb-structure-diagnostic-2026-06]] : "anti-cluster overlay détruit l'edge" — ici tail-hedge VXX comparable : intuition séduisante, drag réel.
- Cohérent avec session_cowork verdict : "long-vol = portfolio insurance, not profit edge" — confirmé chiffré.
- Cohérent avec session_vol_tail : "VIXTERM = bon edge, mauvais profil" — confirmé (+0.44 corr TSMOM, redondant).
- Cohérent avec session_3 caveats : "pré-FOMC décay récent" — confirmé +6 bp/event 2023+ vs +30 bp full.
- **L15 confirmé** : "overlays de régime sur SR bas = lift sous-seuil attendu" — VXX overlay lift = négatif. PREFOMC overlay lift = positif IN-SAMPLE mais dépendant du sample qui inclut 2018-2022 (avant décay).
- Note : Strategy A et B (crypto) non-testées ici faute de série SPX-daily comparable. Le portfolio personal book existant (A+B Sharpe ~2.24) n'est pas remplacé/menacé par cette analyse — c'est une analyse séparée pour un sleeve propfirm-compatible.

---

## Artéfacts

- `data/skew_research/MERGE_portfolio.py` — script complet
- `data/skew_research/MERGE_portfolio_log.txt` — log d'exécution
- `data/skew_research/MERGE_correlations.csv` — matrice corr commune
- `data/skew_research/MERGE_portfolio_returns.csv` — séries quotidiennes des 6 portefeuilles
- `data/skew_research/MERGE_ppass.csv` — p(funded) par portefeuille × leverage
- Réutilise : `series_Long-vol_VXX.csv`, `series_Long-US500.csv` (session_cowork) + `vix_term_structure.csv` + `economic_calendar.csv` + `nq_rth_daily.parquet`
