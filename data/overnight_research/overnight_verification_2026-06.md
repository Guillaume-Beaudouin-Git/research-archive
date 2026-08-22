# Overnight Indices Drift — Falsification Verification (2026-06-03)

**Source dossier** : `data/ftmo_universe/OVERNIGHT_VERIFICATION_REPORT.md` (Cowork, 2026-06-03).
**Sujet vérifié** : (1) swap réel net, (2) cadrage edge book/funded vs sprint FTMO. **L'EFFET n'est PAS contesté** — Cooper-Cliff-Gulen 2008, Lou-Polk-Skouras 2019 le documentent. La question : tradable net après swap, et sous quel conteneur.

**Protocole** : 6 gates séquentiels, *test indépendant d'abord* (yfinance hors-pipeline), reconstructions indépendantes (sans réutiliser `verify_overnight.py` ni `overnight_sim.py`). **Aucun mining session×jour** au-delà du midweek déjà documenté dans le dossier.

---

## Tableau des gates

| Gate | Statut | Chiffre clé | Verdict |
|---|---|---|---|
| **G0** Test indépendant yfinance QQQ/^NDX/SPY/^GSPC | **PASS** | QQQ overnight ALL = **+4.69 bps, t_HAC=4.20** ; Tue +7.98, Wed +9.03 ; 15/17 années + | Effet répliqué hors pipeline Cowork sur 4 actifs publics |
| **G1** Reconstruction NQ databento, mapping + invariants | **PASS** | NQ ALL = **+4.895 bps, t_HAC=4.45** (vs dossier 4.90/4.04). Tue +7.44, Wed +8.69, Mon +3.18, Thu +2.94, Fri +2.16 — match au centième | Mapping `shift(1)`/weekday-of-open validé ; sondes de falsification confirment que les décalages cassent le résultat |
| **G2** Swap réel make-or-break | **PASS midweek** / **Marginal toutes-nuits** | **swap_long = −3.08 bps/nuit (1x)** unité confirmée (digits=2 → point_size=0.01) ; cross-validée EURUSD (−1.11) et XAUUSD (−2.93). swap_3x_day=Friday | Net midweek **invariant** aux deux conventions 3x : +4.36 / +5.61 bps/nuit. Net toutes-nuits ≈ **+0.57 bps/nuit** (marginal) |
| **G3** Queue gap & DD journalier | **PASS conditionnel** | Worst night midweek **−6.26%** ; p1=−1.96% ; p5=−1.04%. Levier max safe FTMO ≈ **0.5×** (MaxDD historique −8.21%, vs −12.10% à 0.75×) | À L=0.5× : 0 DLL breach, 0 MaxDD>10% sur 16 ans. AnnRet +2.49%/an. SR=0.68 (invariant au levier) |
| **G4** Cadrage 3 conteneurs | **(a) FAIL sprint / (b) PASS unlimited / (c) marginal** | (a) p(pass)<2mo = **<0.1%** à L≤1.0× ; (b) L=0.75× : **p(funded)=82.4%**, bust 5.8%, **median 36 mois** ; (c) SR_net=0.68 < gate 0.7 | (a) NON-véhicule challenge (même verdict que ORB iter_10) ; (b) véhicule plausible mais grind multi-année ; (c) inférieur à A/B/C |
| **G5** Réconciliation L25/L31 | **L25 trigger / L31 OK** | β(strat, NQ buy-hold)=+0.33, corr=+0.57, α=+1.07 bps/nuit (faible) ; IN=+3.52/t=1.75 vs OOS=+6.66/t=2.15, Welch t=0.85 | Beta-proxy (L25) confirmé ; OOS persiste, mais **2023-2024 net négatif (−3.9 / −3.4 bps)** — régime post-hausse Fed à surveiller |

---

## Le chiffre swap résolu — l'unité est confirmée

**Source** : `data/ftmo_research/ftmo_specs_full.csv` (capture MT5 broker FTMO).

```
US100.cash, Index CFD, digits=2, contract_size=1
swap_long = −662.40 points, swap_short = +28.58 points
swap_type = points, swap_3x_day = Friday
```

**Formule MT5 standard** (mode SYMBOL_SWAP_MODE_POINTS) :
```
swap_money = swap_points × 10^(-digits) × contract_size
           = −662.40 × 0.01 × 1
           = −6.624 USD par lot par nuit
swap_bps   = swap_money / (contract_size × ref_price) × 10^4
           = −6.624 / (1 × 21500) × 10^4
           = −3.08 bps par nuit (1x)
```

### Grille de sensibilité demandée

| point_size assumed | swap_money USD/lot/nuit | swap bps/nuit (1x) |
|---:|---:|---:|
| 0.001 | −0.66 | −0.31 |
| **0.01 (digits=2 forcé MT5)** | **−6.62** | **−3.08** |
| 0.1 | −66.24 | −30.81 (edge mort) |
| 1.0 | −662.40 | −308.09 (absurde) |

**MT5 force point_size = 10^(-digits) = 0.01.** Toute autre valeur contredit le spec du symbol. La conversion du dossier est donc CORRECTE.

### Cross-validation indépendante sur 2 autres symboles FTMO

| Symbol | digits | swap_long pts | calc bps/nuit | Industrie attendue | Match |
|---|---:|---:|---:|---|---:|
| EURUSD | 5 | −12.17 | −1.11 | −1 à −2 bps (carry USD>EUR) | ✓ |
| XAUUSD | 2 | −88.00 | −2.93 | −2 à −5 bps (gold financing) | ✓ |

→ Le modèle de conversion est cohérent sur 3 symbols indépendants. **L'unité 0.01 sur US100.cash n'est pas une hypothèse — c'est imposé par le spec.**

### Convention swap_3x_day = Friday — invariant midweek

Deux interprétations possibles, mais **midweek (Tue+Wed open-day) est 1x dans les DEUX** :

| Open-day | Conv A (industry CFD)<br>Fri-night → Mon-open = 3x | Conv B (dossier)<br>Thu-night → Fri-open = 3x | Gross bps | **Net (1x)** |
|---|:---:|:---:|---:|---:|
| Mon | 3x = −9.24 bps | 1x = −3.08 | +3.18 | A: −6.06 / B: +0.10 |
| **Tue (Mon-night)** | **1x = −3.08** | **1x = −3.08** | +7.44 | **+4.36** ✓ |
| **Wed (Tue-night)** | **1x = −3.08** | **1x = −3.08** | +8.69 | **+5.61** ✓ |
| Thu | 1x = −3.08 | 1x = −3.08 | +2.94 | −0.14 |
| Fri | 1x = −3.08 | 3x = −9.24 | +2.16 | A: −0.92 / B: −7.08 |

**Conclusion swap** : midweek-only survit (+4.36 / +5.61 bps/nuit net). Toutes-nuits est marginal (+0.57 bps en moyenne, peu importe la convention).

---

## Verdict par conteneur

### (a) FTMO 2-step SPRINT <2 mois — NON-véhicule challenge

| Lev | p(pass) | p(bust) | median days |
|---:|---:|---:|---:|
| 0.50 | **0.000%** | 0.0% | n/a |
| 0.75 | 0.000% | 0.0% | n/a |
| 1.00 | 0.030% | 0.95% | 58 |
| 1.50 | 1.020% | 1.21% | 55 |
| 2.00 | 3.230% | 7.28% | 49 |

**Interprétation** : à des leviers sustainables (≤1.0×), la P(pass) en <42 jours/phase est **virtuellement nulle**. Le dossier annonçait p(<2mo)~5-10% — mon MC indépendant donne <1%. **Le bonus contre le dossier est plus pessimiste**, pas plus optimiste.

**Conclusion** : **NON-véhicule challenge sprint**, exactement comme l'ORB iter_10 / Strategy C (memory `strategy_c_iter10_validation_2026-06`). L'overnight midweek attend 2-3 ans en moyenne pour le pass — n'a aucun sens dans un sprint 2 mois.

### (b) FTMO 2-step UNLIMITED time (réalité post-2023) — véhicule plausible mais peu pratique

| Lev | p(funded) | p(bust) | median days | median months |
|---:|---:|---:|---:|---:|
| 0.25 | 17.6% | 0.0% | 1690 | 80.5 |
| 0.50 | **68.6%** | 1.1% | 1077 | 51.3 |
| 0.75 | **82.4%** | 5.8% | 753 | **36** |
| 1.00 | 74.3% | 22.9% | 523 | 25 |
| 1.50 | 69.3% | 30.5% | 301 | 14.3 |
| 2.00 | 53.2% | 46.8% | 178 | 8.5 |

**Sweet spot L=0.75×** : 82.4% p(funded), bust 5.8%, median **3 ans avant funded**.

→ Match parfait avec `OVERNIGHT_drift_hardening.md` ("82% à 0.75×, 88% à 0.5×, ~2.3-3.5 ans").

**Caveats pratiques** :
- 3 ans median pour passer phase 1+2 — *multi-year commitment*. Inactivity / monthly-fees FTMO à vérifier (rules.md §inactivity).
- 9-12% des paths ne finissent jamais dans le sample 16 ans.
- Tail-risk crash-from-highs non-couvert (-6.26% worst-night observé déjà sur 16 ans ; pire jamais vu dans le sample, type 2008/octobre 1987, briserait L=0.5× et plus).

### (c) Personal book sleeve — pas un candidat

| Lev | AnnRet | AnnVol | SR | MaxDD | WorstMonth | WorstNight |
|---:|---:|---:|---:|---:|---:|---:|
| 0.25 | 1.26% | 1.85% | 0.68 | −4.17% | −1.13% | −1.56% |
| **0.50** | **2.49%** | **3.69%** | **0.68** | **−8.21%** | −2.26% | −3.13% |
| 1.00 | 4.90% | 7.39% | 0.68 | −15.86% | −4.49% | −6.26% |
| 2.00 | 9.44% | 14.78% | 0.68 | −29.60% | −8.88% | −12.52% |

**SR_net = 0.68 invariant au levier** (Sharpe est scale-invariant). Sous **RESEARCH_PASS gate 0.7** (marginal fail).

**vs portefeuille existant** :
- Strategy A : SR 1.33 (TSMOM v3, crypto)
- Strategy B : SR proxy 2.0 (delta-neutral carry HL)
- Strategy C : *validation rebattue* SR 0.51 sur 16 ans, NO-GO Tradeify $25K (`strategy_c_iter10_validation_2026-06`)

Le sleeve overnight midweek L=0.5× est **clairement inférieur à A et B**. Adding-it dilue le book existant.

**β=+0.33 corr=+0.57 avec NQ buy-hold** → L25 trigger : c'est **principalement du beta long-equity déguisé**, pas un alpha indépendant. α brut = +1.07 bps/nuit (faible significativité). Cohérent avec `PropFirms/ftmo_alpha_program/README.md` Family-5 verdict : "Net of financing ≈ zero, directional beta, gap tail-DD 17%".

---

## L25 / L31 / FTMO_SYNC

- **L25 (two-sided)** : corr +0.57, β +0.33 → strat ≈ 1/3 beta NQ + 2/3 résiduel ; **alpha mince**, edge ≠ structural alpha. Tag beta-proxy admis (cohérent avec le dossier qui dit "It is beta, not alpha").
- **L31 (OOS/post-regime)** : OOS=+6.66 bps t=2.15 ≥ IN=+3.52 bps t=1.75 ; Welch t=0.85 → différence non significative, **OOS holds**. Cependant **2023-2024 net négatif (−3.9 / −3.4 bps)** = soft regime change, à surveiller. 2026 partiel +14.5 bps (gros rebond OOS récent).
- **vs FTMO_SYNC** : conteneur (a) sprint → même verdict que ORB / Strategy C iter_10 = "non-véhicule challenge". (b) unlimited-time est une option, mais pas dans la philosophie de Strategy C/D actuelle (FTMO testé en sprint 2-step et non en grind multi-année).

---

## Verdict final

> **L'edge overnight midweek indices est RÉEL et RÉPLIQUÉ** (G0 indépendant + G1 reconstruction NQ). **Le swap est correctement résolu à −3.08 bps/nuit (1x)** sur US100.cash (G2). **Le midweek-only survit nettement net** (+4.36/+5.61 bps/nuit Tue/Wed open). **MAIS** :
>
> 1. **Conteneur sprint FTMO 2-step <2mo** : p(pass)<1% à leviers safe → **NON-véhicule challenge**, exactement comme l'ORB iter_10. Inutile de purchaser une FTMO pour cette stratégie.
> 2. **Conteneur unlimited-time FTMO** : véhicule plausible à L=0.75× (82% p_funded, bust 5.8%), mais **median 3 ans avant funded** → engagement multi-année, sensibilité tail-crash. Faisable mais pratiquement marginal vs ROI temporel.
> 3. **Conteneur personal book** : SR_net=0.68 < gate 0.7, β=+0.33 corr=+0.57 = beta-proxy, **inférieur à Strategy A (SR 1.33) et B (SR 2.0)**. Pas un candidat book.
>
> **Recommandation** : ne pas déployer sous aucun des 3 conteneurs en l'état. Si on insiste pour faire un essai FTMO unlimited-time à L=0.75×, accepter explicitement le 3-ans-median + 5.8% bust + dégradation 2023-2024 comme prix d'entrée.

---

## Artéfacts (reproductibles, indépendants)

- `data/overnight_research/g0_independent_yfinance.py` — test yfinance (NE PAS importer verify_overnight.py)
- `data/overnight_research/g1_nq_mapping_check.py` — reconstruction NQ + validation invariants + sondes de falsification
- `data/overnight_research/g2_swap_unit_check.py` — unité swap + cross-validation EURUSD/XAUUSD + grille sensibilité
- `data/overnight_research/g3_gap_tail_leverage.py` — queue de gap + levier soutenable
- `data/overnight_research/g4_three_containers.py` — 3 conteneurs : sprint / unlimited / personal book
- `data/overnight_research/g5_reconciliation.py` — L25 beta-test + L31 OOS hold + comparaison A/B/C

Sorties : `g0_yfinance_summary.csv`, `g2_swap_summary.csv`, `g3_leverage_sweep.csv`, `g4_containers.csv`, `nq_rth_daily.parquet`, + logs `g{0..5}_log.txt`.
