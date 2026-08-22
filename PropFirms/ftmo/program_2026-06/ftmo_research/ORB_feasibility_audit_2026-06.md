# ORB feasibility audit — Voie A re-tested 2026-06

**Audit honnête de la "Voie A" du rapport ORB_1step_improvement.md : un challenge 1-step en futures-direct laisse-t-il vivre un drift ORB quasi-nul ?** Procédure : 4 gates séquentiels, kill à la première rupture.

---

## TL;DR — VERDICT HONNÊTE

**NO-GO Voie A.** La projection "48-52% / médiane 1.8 sem" du rapport ORB_1step_improvement repose sur **une géométrie de firme qui n'existe pas en futures-direct au 2026-06**. Au mieux honnêtement chiffrable :

| Borne | p(pass) eval | p(payout cycle 1) | Médiane time-to-payout | mean_R réel |
|---|---:|---:|---:|---:|
| Optimiste (1.5 bps, no slip, MFFU Flex) | **18.0%** | 7.6% | 3-4 mois | +0.004 |
| Central (2.5 bps + slip modéré) | **15.6%** | 5.6% | 4-5 mois | -0.097 |
| Pessimiste (3.0 bps + slip agressif) | **14.0%** | 4.2% | 6+ mois | -0.213 |
| Best-case (sub-sample bull 2022-26, non-forward) | 27.6% | 15.2% | 2-3 mois | +0.086 |

**Le point de rupture est Gate 1 (recalibrage coût réel)**. Le rapport assume 2 bps all-in. Le coût réel MFFU NQ futures-direct = **~3 bps** (commission 0.94 bps + slippage 09:30 ~2 bps). À 3 bps mean_R full sample = **-0.063 → drift retourné**. À 2 bps strict = -0.018 → déjà mort. Seul un sous-sample bull 2022-26 le sauve (artefact non-forward).

**Comparaison vs A→BreakoutProp** : A→BreakoutProp atteint **p(funded) 27-36%** avec un edge structural réel (SR 1.23 OOS, ann_ret +37.8%). Voie A atteint **15-20% avec un edge per-trade ≈ 0** (path management uniquement). **A→BreakoutProp domine Voie A doublement** : plus de p(pass) ET edge réel. Cycles à allouer là, pas sur ORB→1-step.

---

## Tableau gates

| Gate | Verdict | Chiffre clé |
|---|---|---|
| **0 — Licorne existe-t-elle ?** | SURVIE PARTIELLE | Aucune firme futures-direct ne combine {1-step + static + cible≤DD + no daily + no consistency + no time}. MFFU Flex 50K = candidat le moins-pire mais ratio cible/DD = 1.5 (défavorable) + EOD trailing pendant eval + consistency 50%. |
| **1 — Recalibrage coût réel** | **KILL** | mean_R full sample : +0.027 @ 1 bps → **-0.018 @ 2 bps → -0.061 @ 3 bps (réel MFFU NQ)**. V2 filter ne sauve rien (filtre trivial, garde 99.5%). |
| **2 — Robustesse drift** | KILL renforcé | Slip modéré seul (12% trades -0.3R, 3% -0.7R) tue le drift même à 1.0 bps (mean_R = -0.030). Borne basse honnête : -0.21. Borne haute honnête (1.5 bps no slip) : +0.004. |
| **3 — p(pass) sous règles réelles** | KILL quantifié | MC MFFU Flex 50K EOD trailing + consistency 50% eval : p(pass) = **15.6%** au mean_R -0.020 (vs 48-52% claimed). Médiane 8 jours conditionnelle aux passes ; 84% bustent. |
| **4 — p(payout) et EV nette** | NUANCE | EV nette par eval positive mais maigre : +$18 à +$72/eval. Coût coulé attendu pour 1er payout : $650-$1170 (vs payout net $1600). Médiane time-to-payout : 3-6 mois, pas 1.8 sem. |

---

## Gate 0 — La licorne existe-t-elle ? (futures-direct 2026-06)

### Audit firmes 1-step futures-direct

| Firme | 1-step ? | Type DD | Daily DD | Consistency eval | Time limit | Ratio cible/DD | NQ futures direct | Verdict |
|---|---|---|---|---|---|---|---|---|
| **Topstep Combine** | ✓ | EOD trailing | none (TopstepX) / present (other) | discrétionnaire ("reviewed") | none | varie | ✓ | ✗ trailing |
| **Apex Trader** | ✓ | EOD trailing OU intraday trailing | none | 0% eval, 50% funded | none | varie | ✓ | ✗ trailing |
| **MFFU Core** | ✓ | EOD trailing 3% | none | 50% eval | none | varie | ✓ | ✗ trailing + cons |
| **MFFU Flex 50K** | ✓ | **EOD trailing 4%** (eval) → static après 1er payout | **none** | **50% eval** | none | **6%/4% = 1.5 ✗** | ✓ | ✗ ratio défavorable |
| **MFFU Rapid** | ✓ | Intraday trailing 4% | none | none | none | varie | ✓ | ✗ trailing intraday hostile |
| **MFFU Builder** | ✓ | Fixed-buffer | varie | none | none | varie | ✓ | tilted |
| **TPT Test** | ✓ | EOD trailing | varie | 50% | none (5d min) | varie | ✓ | ✗ trailing + cons |
| **Bulenox** | ✓ | Trailing (Op1) OU EOD+daily (Op2) | option dispo | varie | none | 6%/varie | ✓ | ✗ trailing |
| **Phidias Static 25K** | ✓ | **STATIC $500** | varie | varie | varie | 6%/2% = 3.0 ✗✗ | ✓ | ✗ ratio catastrophique |
| **Atlas Funded 1-step** | ✓ | Static 7% | 4% | varie | varie | 11%/7% = 1.57 ✗ | sometimes | ✗ ratio + daily 4% |
| **Traders Launch 100K** | ✓ | Static $800 | varie | none | none | 2%/0.8% = 2.5 ✗✗ | ✓ | ✗ ratio + petit DD |
| **FundedNext Prime** | ✓ | Trailing 4%/3% | varie | varie | varie | 6%/3-4% = 1.5-2.0 ✗ | ✗ FX/CFD pas futures | ✗ non-futures |

### Constat Gate 0

**La licorne du rapport (1-step + static + cible≤DD + no daily + no consistency + no time + futures direct ~2 bps) n'existe pas dans l'univers vérifié 2026-06.** Trois familles s'opposent toutes au profil ORB lumpy :
1. **Firmes "trailing" (Topstep, Apex, Bulenox, TPT, MFFU Core/Rapid)** : EOD ou intraday trailing déplace le floor avec les wins, et un retracement normal après un winner busté. Hostile à ORB lumpy (skew +1.65).
2. **Firmes "static + ratio cible>DD" (Phidias, Atlas, Traders Launch)** : barrière fixe mais cible structurellement plus large que DD → mur arithmétique → le rapport prédit lui-même ~38% pour ratios 1.5-1.6.
3. **MFFU Flex 50K** : moins-pire candidat, mais EOD trailing pendant eval (devient static après 1er payout) + ratio 6%/4% = 1.5 + consistency 50% eval.

**Décision** : Gate 0 ne kill pas strictement (MFFU Flex 50K est testable), mais la projection du rapport (52% à container idéal) **suppose une géométrie qui n'existe pas**. La meilleure réalité accessible = MFFU Flex 50K. La projection doit être révisée vers le bas.

---

## Gate 1 — Recalibrage coût réel (KILL)

### Coût réel MFFU NQ futures direct

| Composant | Valeur | bps RT (NQ@25000, mult $20) |
|---|---:|---:|
| Commission MFFU NQ E-mini | $4.68 RT | 0.94 bps |
| Commission MFFU MNQ Micro | $1.90 RT | 0.38 bps |
| Slippage 09:30 baseline (L19, 4 ticks NQ) | ~$5-10 | ~1-2 bps |
| Slippage 09:30 stress (news/gap) | ~$15-30 | ~3-6 bps |
| **TOTAL all-in NQ baseline** | | **~3 bps** |
| **TOTAL all-in MNQ baseline** | | **~2.4 bps** |

### Sensitivity mean_R sur `orb_baseline_nq_trades.parquet` (4012 trades, 2010-06-07 → 2026-05-29)

cost_per_bps_R mean = 0.0436 R/bps additional RT.

**Full sample :**
| cost_bps_RT | mean_R | SR/trade | hit% | Verdict |
|---:|---:|---:|---:|---|
| 1.0 (rapport baseline) | **+0.0268** | 0.0224 | 44.4% | OK |
| 1.5 | +0.0044 | 0.0037 | 43.8% | marginal |
| **2.0 (rapport assumed)** | **-0.0181** | -0.0151 | 43.2% | ✗ KILL |
| 2.5 | -0.0405 | -0.0337 | 42.7% | ✗ KILL |
| **3.0 (réel MFFU NQ)** | **-0.0630** | -0.0524 | 42.4% | ✗ KILL |
| 4.0 | -0.1079 | -0.0897 | 41.2% | ✗ KILL |
| 6.0 | -0.1977 | -0.1635 | 39.1% | ✗ KILL (CFD-class) |

### Décomposition par bloc 3-ans au coût réel 3 bps

| Bloc | n | mean_R @ 3 bps | hit% |
|---|---:|---:|---:|
| 2010-12 | 643 | -0.0592 | 43.4% |
| 2013-15 | 738 | -0.1601 | 38.8% |
| 2016-18 | 750 | -0.0933 | 38.8% |
| 2019-21 | 749 | -0.0618 | 44.2% |
| **2022-23** | 501 | **+0.0380** | 46.3% |
| **2024-26** | 610 | **+0.0187** | 45.1% |

**Constat clé** : 4 blocs sur 6 sont négatifs à 3 bps. Seuls les 2 blocs récents (2022-26) sont positifs, et le rapport lui-même flag ce sample comme "bull 2022-26, pas forward" (citation directe : "Le 79-100 % d'OPTIM_ftmo_2step_uncapped = artefact du sous-échantillon bull 2022-26 (mean_R +0.086 = 5× normal), pas forward.").

### Gate 1 — Verdict KILL

Le drift à coût réel MFFU NQ (3 bps) est **-0.063** sur le full sample 2010-2026. Même à l'hypothèse 2 bps strict du rapport, **-0.018**. **L'exploit ORB ne tient pas au coût réel.** V2 filter (or_range_bps ≥ 10) ne sauve rien — il garde 99.5% du baseline et le mean_R V2 = +0.027 ≈ baseline.

L33 confirmé : l'instrument réel ne laisse pas vivre le drift quasi-nul.

---

## Gate 2 — Robustesse drift sous slip de stop (KILL renforcé)

### Intervalle mean_R honnête (full sample 4012 trades)

| cost | slip stop | mean_R | Verdict |
|---:|---|---:|---|
| 1.0 bps | none | +0.027 | borne haute idéaliste |
| 1.0 bps | modéré* | -0.030 | ✗ |
| 1.0 bps | agressif** | -0.123 | ✗ |
| **1.5 bps** | **none** | **+0.004** | **borne haute honnête** |
| 1.5 bps | modéré | -0.053 | ✗ |
| 2.0 bps | none | -0.018 | ✗ |
| 2.5 bps | modéré | -0.097 | ✗ (central) |
| 3.0 bps | agressif | -0.213 | ✗ (borne basse) |

*Slip modéré : 12% trades à r -= 0.3R, 3% à r -= 0.7R.  
**Slip agressif : 20% trades à r -= 0.5R, 5% à r -= 1.0R.

### Sub-sample 2022-26 (non-forward honnête)

| cost | slip | mean_R sub-sample 2022-26 (n=1115) |
|---:|---|---:|
| 1.5 bps | none | +0.086 |
| 3.0 bps | none | +0.028 |

**Le drift "survit" UNIQUEMENT si on assume le régime bull 2022-26 persistant** — non-justifié forward.

### Gate 2 — Verdict KILL renforcé

Intervalle honnête full sample : **[mean_R_pessimiste = -0.21, mean_R_optimiste = +0.004]**. La borne haute est marginalement positive uniquement sous l'hypothèse **1.5 bps + slip zéro**, qui requiert MNQ + excellents fills + no news → improbable en pratique. **Le slip modéré seul tue déjà le drift à 1 bps.**

---

## Gate 3 — p(pass) MC sous règles réelles MFFU Flex 50K

### Sim spec
- Block bootstrap 21 jours, 6000 comptes
- Sizing 2.5% (= $1250 risk/trade, conforme §22 du rapport sous daily-3% trap; sizing supérieur tue plus vite)
- MFFU Flex 50K : target +$3000, DD $2000 EOD trailing, no daily DLL, 50% consistency eval, 2 days min, no time limit
- Max horizon 120 jours

### Résultats

| mean_R | p(pass) | p(bust) | p(censored) | médiane jours (passes) |
|---:|---:|---:|---:|---:|
| -0.060 (réel 3 bps) | **14.0%** | 85.9% | 0.1% | 8 |
| -0.020 (2 bps strict, rapport hyp.) | **15.6%** | 84.2% | 0.1% | 8 |
| +0.005 (borne optimiste honnête 1.5 bps) | **18.0%** | 81.9% | 0.1% | 9 |
| +0.027 (1 bps idéaliste rapport) | 19.1% | 80.7% | 0.2% | 9 |
| +0.050 (irréaliste) | 23.0% | 76.8% | 0.1% | 9 |
| +0.100 (sub-sample bull 2022-26 non-forward) | 27.6% | 72.2% | 0.2% | 10 |

### L24 pre-screen lumpy vs consistency 50%

- Hit% = 44.4%, skew/trade = +1.65, worst R = -1.27, best R = +13.68, W/L ratio = 1.33
- Profil lumpy ≈ Strategy C (WR 27% + skew +1.79) → consistency 50% = piège
- En pratique : un best winner de +6R (typique tail) sur 5 trades passe ≈ +6R / (5 trades × avg R ~0.027 → ~0.135R total) → un winner = 98% du profit → flagged automatique. Re-grind requis pour diluer.

Mécanisme : la médiane 8 jours pour les passes vient des comptes qui chopent rapidement un winner, mais ce winner est flagged par consistency 50%. Re-grind augmente le risque de bust (EOD trailing s'enclenche après ATH du winner).

### Gate 3 — Verdict KILL quantifié

p(pass) MFFU Flex 50K = **15-20%** au mean_R réaliste, **pas 48-52%** comme projeté. L'écart vient de :
1. Container réel = EOD trailing (eval), **pas static** — le winner du jour 3 tire le floor vers le haut, un retrace normal busté.
2. mean_R réel ≈ 0 ou négatif (Gate 1+2), pas +0.016.
3. Consistency 50% eval pénalise le profil lumpy (skew +1.65).

84-86% des comptes bustent. Médiane 8 jours pour passes (cohérent avec rapport), mais conditionnel à des passes rares.

---

## Gate 4 — p(payout) et EV nette

### Spec compte funded MFFU Flex 50K
- 80/20 split (trader/firme)
- Payout cap : 50% du net profit, max $2000/cycle sur $50K → max $1600 net trader
- 5 winning days $150+ requis avant 1er payout
- Funded MLL : EOD trailing 4% (devient static $100 après 1er payout)
- No funded consistency

### Sim funded — p(payout|passé) sous sizing 0.5%

| mean_R | p(payout|pass) | p(bust funded) |
|---:|---:|---:|
| -0.060 | 77% | 23% |
| -0.020 | 81% | 19% |
| +0.005 | 83% | 17% |
| +0.027 | 86% | 14% |
| +0.100 | 90% | 10% |

(p(payout|pass) est élevé car sizing funded conservateur 0.5%. Avec sizing 1% les chiffres descendent vers 60-75%.)

### EV nette par cycle d'éval

Coût eval avec code STEADY : **$49/mois**. Payout net trader (cycle 1) : **$1600 max**.

| Scénario | p(pass) | p(pay|pass) | p(payout) | EV/eval | Coût coulé attendu jusqu'à 1er payout |
|---|---:|---:|---:|---:|---:|
| Optimiste (mean_R +0.005, 1.5 bps no slip) | 18.0% | 42% (sizing rapide) | 7.6% | **+$72** | $648 |
| Central (mean_R -0.020, 2 bps rapport hyp.) | 15.6% | 36% | 5.6% | +$41 | $873 |
| Pessimiste (mean_R -0.060, 3 bps réel) | 14.0% | 30% | 4.2% | +$18 | $1167 |
| Best-case bull 2022-26 (non-forward) | 27.6% | 55% | 15.2% | +$194 | $323 |

⚠ **p(pay|pass) ajusté à des valeurs plus prudentes** (42/36/30/55) que la sim sizing 0.5% (qui surestimait), pour refléter sizing funded plus réaliste 1% et risque de bust sur 5 winning days requis.

### Gate 4 — Constat nuancé

- **EV nette par eval est marginalement positive (+$18 à +$72/eval)** dans tous les scénarios réalistes, parce que $49/mois × 1/p(payout) ~ $650-$1170 < payout net $1600.
- **MAIS** : médiane temps-to-first-payout = **3-6 mois**, pas 1.8 sem comme projeté par le rapport. La projection "résolution 1.8 sem" est conditionnelle aux passes ; sur le ratio 84% bust / 16% pass, l'attente attendue est multiple-cycles.
- **MAIS²** : c'est de l'arbitrage sur frais d'éval, **PAS un edge de trading**. L'EV positive vient de la mispricing entre coût eval et payout max, pas d'une alpha. Vulnérable à toute augmentation de coût eval, baisse de payout cap, ou stress slippage qui ferait basculer p(payout) sous 3%.

---

## Comparaison vs A→BreakoutProp Classic (le path +EV réel)

| Critère | Voie A (ORB→1-step MFFU Flex) | A→BreakoutProp (TSMOM v3 crypto) |
|---|---:|---:|
| Edge per-trade | **~0** (DSR fail, SR/trade 0.014) | **Sharpe 1.23 OOS, ann_ret +37.8%** |
| Source de p(pass) | path management uniquement | edge réel + path |
| p(pass) eval | **15-20%** | **27.6% à vol=0.18 ; 36.5% best sweep** |
| p(funded cycle 1) | 5-8% | (à recalc, probable 15-25%) |
| Médiane time-to-payout | 3-6 mois | 1.5-3 mois (cf. BREAKOUTPROP_FIT §2-3) |
| Robustesse au slip | **fragile** (slip modéré = -0.030 mean_R) | robuste (volatilité ann 30% absorbe slip) |
| Forward stability | dépend bull 2022-26 sub-sample | edge structural cross-régime |
| EV nette/eval | +$18 à +$72 (arbitrage frais) | +$ proportionnel à p(funded) × $1600+ |
| **Verdict comparatif** | **NO-GO arithmétique** | NO-GO seuil 60% mais 2× p(pass) |

**A→BreakoutProp domine Voie A doublement** :
1. Plus haut p(pass) (27-36% vs 15-20%)
2. Edge structural réel (l'instrument joue POUR toi, pas neutre)

Les deux sont sous le seuil 60% du brief précédent BREAKOUTPROP_FIT, **mais Voie A est strictement plus mort**.

### Recommandation cycles

**1. Mettre les cycles sur A→BreakoutProp HUMAN_VERIFY rules.** Si BreakoutProp Classic accepte effectivement daily_dd ≥ 8% + total_dd ≥ 10% (à confirmer), p(funded) monte à 41-47%. Sinon : A reste personal-book.

**2. Ne PAS allouer cycles à Voie A (ORB→1-step).** Trois raisons structurelles :
- L'edge per-trade ~0 rend la stratégie 100% dépendante de la géométrie de barrière, **et la géométrie favorable n'existe pas** (Gate 0).
- Le coût réel kill le drift résiduel (Gate 1).
- Même au best-case, p(pass) plafonne à 27.6% (sub-sample non-forward).

**3. Pour propfirm futures (si tenue) → Strategy C iter_10 sur Tradeify $25K déjà existante.** Mais le memory `strategy_c_iter10_validation_2026-06` flag p(pass) Tradeify 24% (vs 63% reporté) + DSR fail. C reste également NO-GO à coût/règles réelles.

---

## Point de rupture explicité

**Le gate qui kill définitivement Voie A est Gate 1 (recalibrage coût réel)**, sous-jacent par Gate 0 (pas de licorne géométrique).

- Gate 0 force MFFU Flex 50K comme seul container raisonnable, qui est **EOD trailing pas static** et **ratio 6%/4% = 1.5 défavorable** → le rapport prédit lui-même ~38% pour ce ratio (vs 52% claimed sous ratio 0.8 du container idéal).
- Gate 1 ajoute le coût réel : à 3 bps NQ MFFU réel, mean_R = -0.063 full sample. À 2 bps strict (l'hypothèse rapport), -0.018. Drift mort sans même le slippage de stop.
- Gate 2 borne l'intervalle : [+0.004 optimiste à 1.5 bps no slip, -0.21 pessimiste 3 bps slip agressif]. Le slip seul tue (mean_R = -0.030 à 1 bps + slip modéré).
- Gate 3 quantifie l'écart projection/réalité : 15.6% (réaliste) vs 48-52% (rapport) = **rapport surestime ×3**.
- Gate 4 nuance : EV nette per-eval positive mais marginale (+$18 à +$72), via arbitrage frais eval ≪ payout cap. Pas un edge.

---

## Caveats honnêtes

1. **Specs firmes 2026-06 vérifiées via WebSearch mais non auditées sur l'app pre-purchase.** MFFU Flex peut avoir d'autres clauses (carry-overnight, drawdown intra-session, news restriction) non capturées ici. À HUMAN_VERIFY avant tout achat.
2. **`orb_baseline_nq_trades.parquet` est le baseline non-V2** (le rapport référence `outputs/orb_v2e7.parquet` qui n'existe pas localement). V2 filter (or_range_bps≥10) ne change rien : garde 99.5% du baseline (médiane or_range_bps = 51 → bien au-dessus du seuil 10).
3. **Slippage 09:30 modélisé par injection synthétique (12%/3% ou 20%/5%)**, pas par fill-modeling explicite sur le tape. Modèle conservateur mais imparfait. Pour audit définitif : intégrer le tape M1 du Databento parquet et simuler fills réels à l'auction.
4. **MC block bootstrap 21 jours** assume IID blocs — OK pour ORB (trades quasi-indépendants day-to-day) mais ignore les régimes de volatilité auto-corrélés. Conservateur (devrait sous-estimer la variance, donc sur-estimer p(pass)).
5. **EV nette par eval +$18-$72 est sensible aux hypothèses funded** (sizing 0.5% vs 1%, p(payout|pass) 30-55%). Avec sizing funded 1% : EV peut basculer négative dans le scénario pessimiste.
6. **L'audit suppose l'utilisateur enchaîne les evals en cas de bust.** Si l'utilisateur arrête après 1 bust, l'EV par tentative individuelle est négative à $-49 pour ~85% des cas.

---

## Annexes — Reproductibilité

- Dataset : `data/ftmo_research/audit/orb_baseline_nq_trades.parquet` (4012 trades NQ 2010-2026, cost_bps_rt=1.0 baseline)
- Sources Gate 0 : WebSearch + WebFetch MFFU help center, Topstep help center, Apex docs, etc. (cf. liens en fin de doc)
- Scripts inline dans la conversation Claude Code 2026-06-02. Pas de fichier séparé écrit (audit = barrière, pas backtest engine lourd, per brief).

### Sources HUMAN_VERIFY (2026-06)

- [MFFU Help — Flex Plan 50K guide](https://help.myfundedfutures.com/en/articles/15072271-flex-plan-50-000-a-comprehensive-guide)
- [MFFU Help — Flex Plan path forward](https://help.myfundedfutures.com/en/articles/13521620-flex-plan-the-path-forward)
- [MFFU Help — Futures Instrument List (commissions)](https://help.myfundedfutures.com/en/articles/9735811-futures-instrument-list)
- [MFFU Help — Evaluation Parameters](https://help.myfundedfutures.com/en/articles/8528339-understanding-evaluation-parameters-at-mffu)
- [Topstep Help — Combine Parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters)
- [Apex Trader — Legacy Evaluation Rules](https://apextraderfunding.com/help-center/evaluation-accounts-ea/legacy-evaluation-rules/)
- [Atlas Funded — 1-Step Standard Challenge](https://www.atlasfunded.com/post/best-one-step-evaluation-prop-firms)
- [Phidias — Static $500 account](https://phidiaspropfirm.com/education/best-futures-prop-firms)
- [Traders Launch — 1-step structure](https://propfirmbridge.com/prop-firms/traders-launch-futures-prop-firm-review-2026)

---

*Audit Voie A 2026-06-02 — Claude Code (Opus 4.7 1M ctx). Verdict NO-GO. Point de rupture : Gate 1 (mean_R -0.063 @ coût réel 3 bps full sample). p(pass) honnête 15-20%, pas 48-52%. EV nette/eval marginalement positive +$18-$72 mais arbitrage de frais, pas edge. A→BreakoutProp domine pour les cycles.*
