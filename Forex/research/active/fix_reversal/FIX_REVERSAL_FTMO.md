# Fix-reversal FX (flow-anchored) — make-or-break sur coûts FTMO MT5 réels

**Status:** NO-GO (kill empirique au coût net FTMO)
**Date:** 2026-06-02
**Univers:** EURUSD spot, FTMO MT5 panel (`data/panels/m5_indices/EURUSD_M1.csv`), 2018-01-02 → 2026-05-29, 3 132 491 M1 bars.
**Hypothèses pré-enregistrées:** (A) Fix-reversal Krohn-Mueller-Whelan 2024 sur Tokyo / ECB / Londres 16:00 ; (B) Segmentation Ranaldo-Breedon (short EUR 03-11 ET / long 11-16 ET).
**n_tests budget consumé:** 2 (Pattern A + Pattern B, conservatif).
**Lien avec l'archive Strategy E** (Forex/research/archived/strategy_e_fix_flow/) : *confirmation empirique* d'un kill jusque-là posé au stade littérature uniquement (le postmortem E disait "NO full backtest run"). Le test que cette mission complète.

---

## 1. Coûts CFD FTMO MT5 — Étape 0

Surprise contre-intuitive du brief : à FTMO MT5, **les fenêtres de fix Londres et ECB sont les moments les plus liquides de la journée pour EURUSD** (pas les moments de spread élevé). Seul **Tokyo** présente un spread élevé (liquidité asiatique). Tableau empirique sur 8.4 ans :

| Fenêtre                          | N M1   | spread p50 | **spread p95** | spread p99 | bps p95 RT |
|----------------------------------|-------:|-----------:|---------------:|-----------:|-----------:|
| **Unconditional** (ALL)          | 2 110 160 | 3 pts | 13 pts | 40 pts | **1.16 bps** |
| Tokyo fix (00:50-01:00 UTC)      | 21 686 | 17 pts | **46 pts** | 63 pts | **4.07 bps** |
| ECB fix winter (13:10-13:20 UTC) | 5 272 | 2 pts | 8 pts | 9 pts | 0.71 bps |
| ECB fix summer (12:10-12:20 UTC) | 7 419 | 3 pts | 9 pts | 11 pts | 0.80 bps |
| London fix GMT (15:55-16:05 UTC) | 4 766 | 2 pts | 8 pts | 9 pts | 0.71 bps |
| London fix BST (14:55-15:05 UTC) | 12 298 | 2 pts | 8 pts | 11 pts | 0.71 bps |
| Asian thin (00-07 UTC)           | 755 684 | 4 pts | 29 pts | 55 pts | 2.57 bps |

**Cost stack RT (bps) — ce que Step 1 charge sur chaque trade** :

| Fenêtre              | spread p95 | comm $5/lot | slippage (0.5×ATR_M1) | **total markup×1** | total markup×2 (L23b) |
|----------------------|-----------:|------------:|----------------------:|-------------------:|---------------------:|
| London / ECB fix p95 | 0.71       | 0.44        | 1.08                  | **2.23**           | 2.93                 |
| Tokyo fix p95        | 4.07       | 0.44        | 1.08                  | 5.59               | 9.66                 |
| NY / segmentation    | 0.71       | 0.44        | 1.08                  | **2.23**           | 2.93                 |

Constat : FTMO MT5 EURUSD est **entre l'institutionnel (0.5-1.5 bps cité dans Strategy E postmortem) et le retail Dukascopy (6-7 bps)**. Le gate cost est moins meurtrier que ce qu'a vu Strategy E — donc le test mérite d'être fait, et son verdict est plus informatif (on n'est pas auto-killed par le tier-cost).

Artefacts : `step0_cost_calibration.py`, `step0_costs.json`.

---

## 2. Pattern A — Fix-reversal Krohn-Mueller-Whelan — Étape 1

**Construction :**
- `pre_drift(t)  = log(P[T0]) − log(P[T0−30])` : run-up sur 30 min avant T0 (heure du fix).
- `post_ret(t)   = log(P[T0+60]) − log(P[T0])` : reversal sur 60 min post-fix.
- `trade_ret(t) = −sign(pre_drift) × post_ret` : fade.
- Coût RT chargé par fenêtre (Step 0).

**Tableau gross vs net (delay=0, markup=1) :**

| fix     | cost RT | N    | gross bps | **net bps** | gross t_HAC6 | **net t_HAC6** | gross SR | **net SR** | WR    |
|---------|--------:|-----:|----------:|------------:|-------------:|---------------:|---------:|-----------:|------:|
| London  | 2.23    | 2171 | 0.45      | **-1.78**   | 1.35         | -5.27          | 0.46     | **-1.82**  | 0.512 |
| ECB     | 2.23    | 2164 | 0.19      | **-2.04**   | 0.96         | -10.39         | 0.32     | **-3.45**  | 0.521 |
| Tokyo   | 5.59    | 2133 | 0.03      | **-5.56**   | 0.20         | -41.24         | 0.07     | **-15.13** | 0.516 |
| **POOLED** | varie | 6468 | **0.22**  | **-3.11**   | **1.62**     | **-20.86**     | **0.32** | **-4.43**  | -     |

Stress markup×2 (retail-vs-feed, L23b) : net pooled = -4.93 bps, SR=-6.79.

**Observation centrale :** la magnitude **gross** mesurée empiriquement sur EURUSD 2018-2026 est **~5× plus petite que les chiffres de Krohn-Mueller-Whelan 2024** (qui citent ~2-4 bps gross par fix). Sur London, gross 0.45 bps (t=1.35, marginal, sous gate 1.65). Sur ECB, gross 0.19 bps (t=0.96). Sur Tokyo, gross 0.03 bps (no signal).

**Sub-sample EOM up-sizing** (last 3 b-days, le mois où l'edge est censé être maximal) :

| fix    | subset      | N   | gross bps | gross t | **net bps** | net t  | gross SR | **net SR** |
|--------|-------------|----:|----------:|--------:|------------:|-------:|---------:|-----------:|
| London | EOM         | 303 | **1.42**  | 1.60    | **-0.81**   | -0.91  | **1.45** | -0.83      |
| London | QoQ-EOM     | 99  | 0.85      | 0.53    | -1.38       | -0.86  | 0.82     | -1.32      |
| ECB    | EOM         | 303 | 0.77      | 1.37    | -1.46       | -2.60  | 1.23     | -2.34      |
| Tokyo  | EOM         | 303 | 0.34      | 1.40    | -5.25       | -21.66 | 1.19     | -18.46     |

Le levier EOM **multiplie le gross London par 3.2× (0.45 → 1.42)** — donc le mécanisme de flow concentré en fin de mois est réel — mais **gross 1.42 < cost 2.23** → net toujours négatif. Le levier ne suffit pas.

**Sub-sample temporel** (gross uniquement — diagnostic L23/L31) :

| fix    | period    | N   | gross bps | gross t | gross SR |
|--------|-----------|----:|----------:|--------:|---------:|
| London | 2018-2020 | 773 | -0.12     | -0.24   | -0.14    |
| London | 2021-2022 | 519 | 0.06      | 0.08    | 0.05     |
| London | 2023-2024 | 518 | **1.35**  | 1.87    | 1.31     |
| London | 2025-2026 | 361 | 0.96      | 1.12    | 1.02     |
| ECB    | 2018-2020 | 774 | 0.17      | 0.53    | 0.29     |
| ECB    | 2021-2022 | 514 | 0.41      | 0.97    | 0.62     |
| ECB    | 2023-2024 | 513 | -0.19     | -0.57   | -0.39    |
| ECB    | 2025-2026 | 363 | 0.44      | 0.80    | 0.72     |

**Diagnostic :** ni L23 (regulatory-window kill — pas de décrochage net post-2015 dans l'échantillon — déjà fait, on est entièrement post-BIS-2015), ni L31 (alpha-decay post-publication — en fait c'est l'inverse, gross London émerge faiblement 2023-2026). Cause de mort = **gross < cost uniformément**. Même dans le meilleur sous-échantillon (London 2023-2024 gross 1.35 bps), le cost FTMO 2.23 bps reste au-dessus.

---

## 3. Pattern B — Segmentation Ranaldo / Breedon-Ranaldo — Étape 1

**Construction :**
- `short_leg(t) = −log(P[11:00 ET] / P[03:00 ET])` (vendre EUR pendant heures Euro)
- `long_leg(t)  = +log(P[16:00 ET] / P[11:00 ET])` (acheter EUR pendant heures US)
- Coût RT chargé par jambe (entry+exit = 1 full RT par jambe).

**Tableau gross vs net (delay=0, markup=1, cost RT 2.23 bps) :**

| Leg              | N    | gross bps | **net bps** | gross t_HAC6 | **net t_HAC6** | gross SR | **net SR** | WR    |
|------------------|-----:|----------:|------------:|-------------:|---------------:|---------:|-----------:|------:|
| short_0311ET     | 2185 | **1.37**  | **-0.86**   | **2.23**     | -1.40          | **0.77** | **-0.48**  | 0.518 |
| long_1116ET      | 2185 | -0.13     | -2.36       | -0.24        | -4.19          | -0.08    | -1.33      | 0.492 |
| **combined**     | 2185 | 1.23      | **-3.23**   | 1.54         | -4.02          | 0.49     | **-1.29**  | 0.511 |

**Observation centrale :**
1. **L25 violation (split-by-direction) :** seule la jambe SHORT a un gross significatif (t=2.23, SR=0.77). La jambe LONG est dead (gross t=-0.24, SR=-0.08). Un edge "two-sided" qui ne tient que d'un côté n'est pas un edge two-sided — c'est une *direction asymétrique = potentiel look-ahead ou beta-disguised*.
2. **Le QuantRocket "Sharpe 0.70 net" citait des spreads IB institutionnels ~0.15 bps RT.** Sur FTMO MT5 à 2.23 bps RT, l'edge short (gross 1.37 bps) est **éclairée par le coût** : 1.37 − 2.23 = -0.86 bps net.
3. **Même optimiste à p50 spread :** cost = 0.27 + 0.44 + 1.08 = 1.79 bps. Net short = 1.37 − 1.79 = -0.42 bps. **Pas viable même au scénario coût optimal FTMO.**
4. **Même sans slippage** (cost = 0.71 bps spread p95 + 0.44 comm = 1.15 bps) : net short = 1.37 - 1.15 = 0.22 bps positif, mais **net Sharpe ≈ 0.22/sd(28 bps)×√252 = 0.12** — sous le gate 0.5 même au scénario coût no-slip.

Markup×2 stress : net combined SR=-1.85.

---

## 4. Réponse aux questions de l'Étape 2 (non-exécutée — STOP atteinte)

Per brief : "**Verdict make-or-break :** si net Sharpe ≤ ~0.3 ou négatif (l'attendu ~70%) → c'est un edge gross qui meurt au turnover comme tout le reste → **NO-GO, documente**. Si net survit (Sharpe ≥ ~0.5 net FTMO) → continue à l'Étape 2."

**Pattern A pooled net SR = -4.43. Pattern B combined net SR = -1.29. Pattern B short-only net SR = -0.48.** Toutes les variantes ≪ 0.3. **STOP atteinte. Étape 2 non exécutée** (two-sided spécifique L25 — déjà fait sur B, FAIL ; delay-1 L26 ; OOS post-2019 — diagnostic descriptif fait en §2 sans WF formel ; swap-sign L30 — N/A car intraday-flat).

Note : la condition "tout net > 1.5 = red flag look-ahead" du brief ne s'applique pas (gross pooled SR = 0.32, net = -4.43).

---

## 5. Verdict GO/NO-GO

**NO-GO sur les deux patterns.** L'edge flow-anchored à mécanisme économique réel (dealer inventory + rebalancing benchmark) **existe statistiquement faiblement sur EURUSD MT5 2018-2026** — pattern A pooled gross t=1.62, pattern B short-leg gross t=2.23 — mais sa **magnitude (0.22 bps pooled, 1.42 bps EOM London, 1.37 bps segmentation short) est inférieure au coût FTMO MT5 réaliste (2.23 bps RT au p95 spread + commission + slippage)**. Le pattern survit uniquement à un cost tier institutionnel < 1 bps RT (cité IB QuantRocket 0.15 bps) — qui n'est pas accessible en propfirm retail.

**Cause de mort :** **turnover × cost — l'edge gross meurt au tier de cost retail propfirm, comme le carry commodity (L32), l'overnight indices (L30 swap), et l'ORB+floor (slippage + DD intraday)**.

**Prior validé :** le brief estimait 70% de NO-GO. Confirmé.

**Pas d'alpha-decay (L31) ni de regulatory-window kill (L23) à diagnostiquer.** Le gross 2018-2020 (post-BIS-2015 mais pré-publication Krohn 2024) est déjà ≤ 0 — donc le pattern n'a jamais été grand sur ce sample. La littérature Krohn-Mueller-Whelan 2024 documente probablement un edge **principalement attribuable à des paires non-EUR (JPY/NOK/AUD avec leurs flux commodity/safe-haven plus pointus)** ; sur EURUSD spécifiquement le mécanisme est dilué.

---

## 6. Candidate L-number (proposé) — L34

> **L34 — Flow-anchored FX edge à tier institutionnel uniquement.**
>
> Le pattern fix-reversal (Krohn-Mueller-Whelan 2024) et la segmentation (Ranaldo / Breedon-Ranaldo)
> sur EURUSD MT5 2018-2026 produisent un gross drift mesurable (~0.5-1.4 bps/trade au London fix,
> pic EOM ~1.4 bps ; short_03-11_ET gross t=2.23). **Ce gross est inférieur au coût RT FTMO MT5 au
> p95 spread + commission + slippage (~2.23 bps RT au fix Londres / NY hours).** L'edge n'est
> tradable qu'à un tier-cost institutionnel ≤ 1 bps RT (spread IB type, dark pool, brokerprime).
> Conséquence opérationnelle :
> - Tout nouveau test d'un mécanisme flow-anchored FX (carry conditionné, rebalancing, fix flow,
>   segmentation horaire) doit, en pré-flight, comparer la magnitude gross **publiée**
>   au cost p95 FTMO MT5 de la fenêtre d'entrée (cf. `step0_costs.json` ici, ~2.2 bps RT au fix
>   Londres / NY hours, ~5.6 bps RT à Tokyo).
> - Magnitude gross publiée / cost p95 < 1.5 → SKIP avant tout backtest.
> - L'asymétrie L25 d'un pattern intraday FX (short-side significatif, long-side dead) doit être
>   traitée comme red flag direction-asymétrique = beta-disguised ou look-ahead, **pas** comme
>   "demi-edge tradable".
>
> Complète et raffine L11 (cost-aware breakeven) et L23b (institutional ≠ retail).

**À valider par l'utilisateur** avant promotion dans `CLAUDE.md`. Dernier consommé = L33 (crypto-CFD TSMOM two-sided, session précédente).

---

## 7. Artefacts

- `step0_cost_calibration.py` + `step0_costs.json` : calibration cost FTMO MT5 EURUSD session-conditionnelle.
- `step1_backtest.py` + `step1_results.json` : backtest vectorisé Pattern A + Pattern B (gross/net, markup×1 et ×2).
- `step1b_eom_test.py` + `step1b_eom_results.csv` : sub-sample EOM / QoQ-EOM up-sizing.
- `step1c_oos_split.py` + `step1c_oos_split.csv` : sub-sample temporel 2018-2026 (diagnostic L23/L31).
- Données source : `data/panels/m5_indices/EURUSD_M1.csv` (FTMO MT5 panel, 2018-01 → 2026-05).
- Lien archive Strategy E : `Forex/research/archived/strategy_e_fix_flow/POSTMORTEM.md` (kill au stade littérature ; cette session = test empirique manquant).

---

## 8. Cases FTMO restantes après cette session

| Classe d'actifs FTMO momentum/carry hebdo-quotidien | Statut | Source |
|------|--------|--------|
| FX carry G10 | CLOSED | L23, L23b (postmortem strategy_e + g1_carry_conditional) |
| FX fix-reversal / segmentation | **CLOSED (cette session)** | L34 proposé |
| Indices overnight | CLOSED | L30 swap-sign + L32 |
| Commodity carry CFD | CLOSED | L32 |
| Crypto CFD weekly TSMOM two-sided | CLOSED | L33 (session 2026-06-02 précédente) |
| ORB intraday-flat indices | **SURVIVANT** | K5 (orb_pushpass), V2+E7 (orb_deepening) |
| NQ momentum (Strategy C iter_10) | NO-GO Tradeify | strategy_c_iter10_validation |

**Recommandation :** revenir sur le matériel ORB-deepening déjà validé (V2+E7 mid-vol 49% sur FTMO Indices CFD) ou le K5 push-pass (98.6% mid-vol mais path-management driven, à valider stricte sous time-limited eval). Pas de nouveau hunt FX/carry/fix dans les conditions FTMO MT5 actuelles.
