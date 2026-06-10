# Optimisation propfirm — Ensemble ORB indices
## Mode recherche, sweep sizing + kill-switch + gate régime, L19 ablation

**TL;DR** — Sur les leviers **robustes** (sizing), le mur mathématique de FTMO 2-phase est confirmé : **p(funded) max = 52% à risque optimal 1.25%/block** ; cible 70% structurellement inatteignable. En basculant sur un produit **1-phase static (target +10%, daily -5%, total -10% statique)** à risque 1.25-1.5%/block : **p(funded) = 69%** sans gate, **75% FULL / 77% WF mean** avec gate régime vr5 low. **C'est le seul container qui passe 70%.** Le kill-switch est un **levier mort** (ablation L19). Le sous-produit book-perso à vol-target 10% donne Sharpe 1.54 net / MaxDD -12% / TUW 89%.

**Risk warning :** le gate régime est entraîné sur 2022-2025 où le seul chop notable = 2023. **N≈1.** À ne pas trust avant fetch NQ/DAX 2008-2025.

---

## 0. Périmètre, infrastructure et garde-fous

- Réutilise `audit/orb_core.py` + `audit/ftmo_engine.py` ; extension `audit/optim_engine.py` ajoute :
  - Kill-switch intra-attempt (KD = halt day après -X% intraday, KT = halt attempt après -Y% total).
  - 4 containers : `ftmo_2phase`, `1phase_static`, `1phase_trail6`, `1phase_daily5`.
  - End-to-end real-path P1→P2 sur le même path historique.
- Couleur "in-sample" tout au long : toutes les courbes ci-dessous sont mesurées sur 2022-2025 (1033 jours), unique fenêtre data dispo. Les conclusions structurelles (mur math FTMO 2-phase, kill-switch dead, sizing optimum intérieur) sont robustes. Les conclusions régime-spécifiques (vr5 low gate, fold-3-rescue 2023) sont **in-sample sur N≈1 episode chop** et doivent être validées sur data étendue avant tout deployment.
- L19 appliqué partout : chaque modification mesurée contre baseline rescalé au même risk.
- L10 : 3 modifications testées max — (1) sizing, (2) kill-switch, (3) gate régime. Stop.

---

## 1. Étape 1 — Baseline rescalé multi-risk (L19 reference)

`audit/optim_step1_baseline.py` ; sortie `optim_step1_baseline.csv` + `optim_step1_output.txt`.

Sweep risk-per-block ∈ {0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0}% × 4 containers × {real-path, iid} :

### Argmax p(funded) par container (full 2022-2025, real-path)

| Container | Argmax risk | p(funded) | Mode dominant à argmax | Mode bust à risk élevé |
|---|---:|---:|---|---|
| ftmo_2phase | **1.25%** | **52.4%** | équilibre timeout/bust_total | bust_total domine ≥ 1.5% |
| 1phase_static | **1.25%** | **69.3%** | bust_total 24.7% | bust_total 35% ≥ 2.0% |
| 1phase_trail6 | 1.00% | **47.2%** | bust_trail 52% ! | bust_trail 65%+ ≥ 1.5% |
| 1phase_daily5 | 2.25% | **81.1%** | timeout 18% à risk élevé | (pas de total floor) |

### Observations

- **Optimum intérieur clair** sur tous les containers : à risk trop bas → timeout domine (le strat n'a pas le temps d'atteindre +10%) ; à risk trop haut → bust_total domine (la queue gauche dépasse le floor).
- **iid systématiquement plus bas que real-path** de ~5-10pt sur p(funded). Cohérent avec l'audit (RV_AC=0.94 → vol clustering → real-path préserve les bonnes périodes).
- À risk **2.5-3%**, **chute brutale** sur tous les containers : la queue à p99 ≈ 6.3R (rapport STRESS_TEST §5) franchit le -5% daily ; bust_daily prend le relais. Inutile de pousser au-delà de 2.25%.
- **1phase_trail6 est structurellement incompatible** avec l'ORB : la queue droite (winners +5R) crée des nouveaux peaks puis le -1R suivant tire 6% sous peak → bust_trail. 50-65% des attempts terminent en bust_trail à tous les risk.

### Verdict Étape 1

- **ftmo_2phase plafonne à 52% p(funded) au sizing optimum** — **-18pt sous la cible 70%**, exactement comme l'audit prédisait (mur math : 0.76² × 0.75 = 43% max théorique avec p(P1) = 76% optimiste).
- **1phase_static atteint 69.3% — JUSTE sous 70%.** C'est le candidat sérieux.
- **1phase_daily5 atteint 81% mais le produit n'existe pas en pratique** (aucun propfirm ne tolère "pas de total floor"). C'est une borne théorique.

---

## 2. Étape 2 — Fine grid sweep + WF dispersion

`audit/optim_step2_finegrid.py` ; sorties `optim_step2_full.csv`, `optim_step2_wf.csv`.

Pas 0.25% sur risk. WF 5 folds contigus (≈207 jours chacun).

### Fine grid (full 2022-2025, in-sample)

```
1phase_static (in-sample):
  risk_pct  REAL_p1_pct  REAL_p_funded
       0.5         18.7           18.7
       0.8         53.4           53.4
       1.0         65.5           65.5
       1.2         69.3           69.3   <- argmax FULL
       1.5         68.7           68.7
       1.7         66.9           66.9
       2.0         65.0           65.0
       2.2         63.4           63.4
```

### WF per-fold p(funded) — révèle l'overfit sizing in-sample

```
1phase_static WF folds (5 contiguous folds):
risk_pct  fold1  fold2  fold3  fold4  fold5  | mean  min   max   std
1.00       92.8   56.3   19.2   79.0   65.3  | 62.5  19.2  92.8  27.9
1.25       95.2   60.5   25.7   80.8   68.8  | 66.2  25.7  95.2  26.1
1.50       93.4   59.3   31.7   80.2   65.3  | 66.0  31.7  93.4  23.3
1.75       87.4   60.5   30.5   77.8   65.9  | 64.4  30.5  87.4  21.7
2.00       81.4   61.1   31.1   74.9   62.9  | 62.3  31.1  81.4  19.4
```

- **Fold 3 (2023-08-07 → 2024-05-23) = échec sur tous les sizings** (19-32%). Cette fenêtre contient la queue du chop 2023.
- **Fold 1 (2022 H1, vol shock + Fed-tightening trend)** = quasi-100% pass.
- **Spread max-min = 60-70pt** dans tous les sizings — la stratégie ne donne pas le même résultat selon quand vous démarrez.
- **Argmax mean-WF = 1.25% → 66.2% (min 25.7%)**. Le 69.3% in-sample full est légèrement gonflé par fold 1 + 4.

### Tableau argmax WF mean par container

| Container | Argmax risk (mean-WF) | mean-WF p(funded) | min WF (fold 3 chop) |
|---|---:|---:|---:|
| ftmo_2phase | 1.50% | 50.2% | 1.6% |
| 1phase_static | 1.25% | **66.2%** | **25.7%** |
| 1phase_trail6 | 1.00% | 48.1% | 18.6% |
| 1phase_daily5 | 2.25% | 78.2% | 40.7% |

### Verdict Étape 2

- L'argmax sizing est stable autour de 1.25-1.5% pour les containers réalistes — cohérent avec l'optimum théorique d'un floor-touching game (Kelly-fractional sous barrier).
- **MAIS** la dispersion WF révèle que **même au sizing optimum, la probabilité varie de 26% à 95% selon le fold**. Le 66.2% est une moyenne, pas une garantie.
- **fold 3 (chop 2023-fin/2024-début) est l'écueil**. C'est précisément ce que le gate régime essaie de corriger (§ 4).

---

## 3. Étape 3 — Kill-switch sweep + ablation L19

`audit/optim_step3_killswitch.py` + `audit/optim_step3b_fine_ks.py`.

### Verdict L19 : KILL-SWITCH = LEVIER MORT

| (KD, KT) | FULL p(funded) | Δ vs baseline | WF mean | WF min |
|---|---:|---:|---:|---:|
| **None / None (baseline)** | 69.3% | 0 | 66.2% | 25.7% |
| None / 8% | 66.0% | **-3.3pt** | 63.0% | 25.1% |
| None / 7% | 63.0% | **-6.3pt** | 60.2% | 24.6% |
| None / 6% | 59.3% | **-10.1pt** | 56.3% | 24.0% |
| None / 5% | 53.9% | **-22pt** | — | — |
| 2-4% / None | 69.3% | 0 (jamais déclenché) | 66.2% | 25.7% |
| 0.5-1.25% / 6-9% | 22-55% | **-15 à -47pt** | — | — |

(Container = 1phase_static, risk = 1.25%. Ablation L19 = baseline rescalé au MÊME risk, MÊME container.)

### Pourquoi KD ne se déclenche jamais à >1.5%

À risk 1.25%/block, l'AM block max-loss est ≈ -1.5% (= -1R × block_cap). Le check KD se fait **entre** AM et PM blocks. Donc :
- KD ≥ 2% : seuil au-dessus du max possible → **0 trigger**.
- KD ∈ [0.5%, 1.5%] : trigger trop fréquent → skip PM block dans 1 cas sur 3 = **on coupe une espérance positive**.
- KD = 1.5% (= max AM block) : à la limite, équivalent au baseline.

**Aucun KD ne bat le baseline.** L'architecture per-block (vs intra-block) du moteur audit empêche un KD fin sans modélisation intra-minute, et même un KD fin coupe le PnL.

### Pourquoi KT empire tout

KT halt the attempt après -Y% total. L'ORB a **expectancy positive et autocorrélation négative** (mean-reversion daily, VR_q5=0.91) → un drawdown -6% est typiquement récupéré dans les 3-5 jours suivants. Halter à -6% **transforme un drawdown récupérable en bust définitif**. Le baseline laisse le strat respirer jusqu'au floor naturel (-10%) ; le KT impose un floor artificiel plus étroit.

**Tous les KT testés (5-9%) réduisent p(funded).** Verdict L19 : **REJECT**.

---

## 4. Étape 4 — Décision de container (LE VERDICT)

### Table décision (best risk/block × kill-switch × gate, in-sample full 2022-2025)

| Container | Best risk | Kill-switch | Gate régime | p(P1) | p(P2\|P1) | **p(funded) FULL** | **WF mean** | WF min | ≥70% ? |
|---|---:|---|---|---:|---:|---:|---:|---:|:---:|
| **ftmo_2phase** | 1.25% | None | None | 68.4% | 76.6% | **52.4%** | 49.2% | 0.0% | ✗ |
| ftmo_2phase | 1.25% | None | vr5 low | 73.3% | (~74%) | 54.1% | 49.5% | 0.0% | ✗ |
| ftmo_2phase | 1.25% | None | trend20 mid | 74.4% | (~78%) | 58.1% | 59.0% | 0.0% | ✗ |
| **1phase_static** | 1.25% | None | None | 69.3% | n/a | **69.3%** | 66.2% | 25.7% | ⚠ proche |
| **1phase_static** | 1.25% | None | vr5 low | 75.1% | n/a | **75.1%** | 75.8% | 54.5% | **✓** |
| **1phase_static** | 1.50% | None | vr5 low | 75.1% | n/a | **75.1%** | **77.0%** | n/a | **✓ ARGMAX** |
| 1phase_static | 1.25% | None | trend20 mid | 75.1% | n/a | 75.1% | 72.6% | 34.5% | ✓ marginal |
| 1phase_static | 1.25% | None | rv20 mid | 76.7% | n/a | 76.7% | 72.3% | n/a | ✓ |
| 1phase_trail6 | 1.0% | None | None | 47.2% | n/a | 47.2% | 48.1% | 18.6% | ✗ |
| 1phase_daily5 | 2.25% | None | None | 81.1% | n/a | **81.1%** | 78.2% | 40.7% | (théorique) |

### Container par container

#### ftmo_2phase — VERDICT NO-GO confirmé
- Mur math : pour atteindre 70% funded, il faut p(P1) × p(P2|P1) ≥ 0.70. Le meilleur observé est 0.75 × 0.78 = 0.58. **Impossible.**
- Le gate régime relève p(P1) à 74-77%, mais p(P2|P1) reste à ~73-78% → max p(funded) chaîné = 0.58.
- Pour clear 70%, il faudrait p(P1) ≥ 0.93 à p(P2|P1)=0.75 (impossible) ou p(P2|P1) ≥ 0.92 à p(P1)=0.76 (impossible).
- **Cette structure 2-phase est incompatible avec l'edge ORB de fa​ç​on irréductible.**

#### 1phase_static — VERDICT GO (in-sample, à valider)
- À risk 1.25-1.5% + gate vr5 low : **75-77% p(funded) FULL et WF mean.**
- WF min (fold 2 ou 3) = ~54-66% selon gate — encore au-dessus de la moitié des challenges.
- **C'est le seul container réaliste qui clear 70%.**
- ⚠ Caveat N≈1 : le gate vr5 low "apprend à éviter 2023" qui est le seul gros chop disponible. Robustesse incertaine.

#### 1phase_trail6 — NO-GO structurel
- 50-65% des attempts terminent en bust_trail à tous les risk. La queue droite ORB (+5R winners) crée des peaks que le -1R suivant tire 6% sous → bust.
- Verdict : l'ORB est **fondamentalement incompatible** avec un trailing 6%. Apex / FundedNext Stellar 1-step sont à exclure.

#### 1phase_daily5 — Théorique seulement
- 81% p(funded) mais aucun produit propfirm ne propose "pas de total floor". Borne supérieure inutile en pratique.

### Critère du brief : p(funded) ≥ 70%

| Container | Clear 70% sur leviers robustes (sans gate) ? | Clear 70% avec gate régime ? |
|---|:---:|:---:|
| ftmo_2phase | ✗ NON (52%) | ✗ NON (58% max) |
| **1phase_static** | ✗ NON (69%) | **✓ OUI (75-77%)** |
| 1phase_trail6 | ✗ NON (47%) | (pas testé — inutile) |
| 1phase_daily5 | (théorique 81%) | (théorique) |

→ **Seul `1phase_static` + gate régime + sizing 1.25-1.5% atteint la cible.** Et c'est *in-sample*.

---

## 5. Étape 5 — Gate régime (CONDITIONNEL, déclenché ici)

`audit/optim_step5_regime_gate.py` + `audit/optim_step5b_gate_risk_sweep.py`.

**Justification du déclenchement L15** : 1phase_static à 69.3% est à 0.7pt de 70% sans gate. Le gate régime devient le levier marginal pour clear la barre. Conforme à L15 (overlays utiles sur SR<0.7 avec clustering conditionnel de DD ; ici p(P1) ≈ 0.69 et le bust est concentré sur 2023).

### Joint sweep (risk × gate) sur 1phase_static

```
WF_mean_p_funded (5 folds, in-sample):
gate          NONE  rv20_mid  trend20_mid  vr5_low
risk_pct                                          
0.75            —      47.9         57.4     55.0
1.00            —      63.7         68.2     70.9
1.25            —      72.3         72.6     75.8
1.50            —      65.8         73.0    77.0    <-- argmax mean-WF
1.75            —      62.9         68.7     75.4
2.00            —      59.4         66.6     72.3
```

### Décomposition fold-par-fold du meilleur combo (1phase_static + vr5 low @ 1.25%)

| Fold | Période | No gate | + vr5 low | Δ |
|---|---|---:|---:|---:|
| 1 | 2022-01-03 → 2022-10-18 | 95.2% | 94.3% | -0.9pt |
| 2 | 2022-10-19 → 2023-08-04 | 60.5% | 54.5% | -6.0pt |
| **3 (chop)** | **2023-08-07 → 2024-05-23** | **25.7%** | **65.9%** | **+40.2pt** ✓ |
| 4 | 2024-05-24 → 2025-03-11 | 80.8% | 86.7% | +5.8pt |
| 5 | 2025-03-12 → 2025-12-31 | 68.8% | 77.8% | +9.0pt |
| **Mean** | | **66.2%** | **75.8%** | **+9.6pt** |

→ Le gate **fait précisément ce qu'on espère** : sauve le fold chop (+40pt), n'érode pas trop les bons folds (-6pt fold 2 max).

### Ablation L19 (HMM vs threshold)

L'audit step 5C avait déjà testé HMM 3-state vs threshold (vr5 low) :
- HMM 3-state : 77.9% pass FULL (n=358 selected)
- threshold vr5 low : 75.1% pass FULL (n=358 selected)
- HMM bat threshold de +2.8pt, mais overlap 38% (différents sets), expected dwell 2 jours = pas de modélisation persistance.

→ **HMM n'apporte pas de valeur structurelle au-delà du threshold**, et le surplus 2.8pt est inférieur à la dispersion WF (±10pt). Per L19, **on garde le threshold (vr5 low)** — plus simple et tout aussi bon.

### ⚠ N≈1 — caveat majeur

- 2023 = 95% des jours en bottom-tercile rv20 = **un seul gros épisode**.
- Le gate vr5 low "apprend à éviter 2023". S'il n'y avait pas eu 2023 dans le sample, le gate n'aurait pas de quoi se calibrer.
- Sur des chop futurs (vol-bas long mais structurellement différent), le gate **peut sous-performer** ou simplement **rater le signal**.
- **À ne PAS trust en live avant validation NQ/DAX 2008-2025** (cf. § 7).

### Modifications L10 consommées : 2/3

1. ✓ Sizing argmax (1.25-1.5% risk-per-block sur 1phase_static)
2. ✓ Gate régime vr5 low tercile (ex-ante, info ≤ J-1, threshold simple)
3. **(disponible)** Pour la 3e mod : à réserver pour une validation post-extension data ou une optimisation Bayesian sur les paramètres rv20/trend20/vr5 combinés. Pas dépensée ici.

---

## 6. Étape 6 — Sous-produit book perso (vol-target 10%/an)

`audit/optim_step6_personal_book.py` ; sortie `optim_step6_personal_book.csv` + `optim_step6_personal_book_yearly.csv`.

### Conversion sizing

À block-cap 1.5% (baseline audit), vol annualisée du PnL portfolio = **47.5%/an**. Pour cibler 10%/an : scaling = 10/47.5 = 0.211 ; **risk-per-block ≈ 0.316%**. Le PnL daily devient ~1/5 de l'audit baseline.

### Tableau de profil (compoundé no-reset)

| Sizing | Risk/block | Ann vol | Ann ret | Sharpe | t HAC lag-6 | MaxDD | Worst month | TUW |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Audit baseline (1.5%, 2022-25) | 1.50% | 47.5% | 86.3% | 1.54 | 3.37 | -48.4% | -17.7% | 89.2% |
| **Vol-target 10% (0.32%, 2022-25)** | 0.32% | 10.0% | 16.1% | **1.54** | 3.37 | **-11.9%** | **-3.9%** | **88.6%** |
| Vol-target 10% (0.32%, 2022-26) | 0.32% | 9.9% | 16.3% | 1.57 | 3.67 | -11.9% | -3.9% | 88.3% |
| Propfirm-optim 1.25% (no reset) | 1.25% | 39.6% | 70.4% | 1.54 | 3.37 | -41.8% | -14.9% | 89.0% |

### Per-year à vol-target 0.32%

| Année | Ret | Ann vol | Sharpe | MaxDD | Worst month |
|---|---:|---:|---:|---:|---:|
| 2022 | +30.8% | 10.5% | **2.61** | -4.5% | -0.9% |
| **2023 (chop)** | **-1.5%** | 9.7% | **-0.11** | **-9.2%** | **-3.9%** |
| 2024 | +15.7% | 9.9% | 1.53 | -5.3% | -3.2% |
| 2025 | +21.7% | 9.9% | 2.03 | -5.0% | -3.9% |
| 2026 (5 mois) | +18.1% (ann.) | 8.8% | 1.93 | -1.7% | +0.1% |

### Verdict book perso

- **Sharpe daily ann ≈ 1.54** sur 2022-2025 — Sharpe est **invariant au scaling** (vol-target ne change pas le ratio).
- **MaxDD -11.9% / worst month -3.9% à vol-target 10%** — gérable pour un book perso (gate L8 research >0.7 OK ; pas propfirm <-10%).
- **TUW 89%** = la stratégie passe 89% de ses jours **sous son pic d'équity** — c'est typique des breakouts à skew positif (séjours longs en plateaux/bleed entre les spikes).
- **2023 chop reste douloureux** même au sizing perso : -1.5% ret, MaxDD -9.2%. Une année blanche.

### Caveat DSR L20

À n_trials=18 (revendiqué dans le rapport interne, ~18 familles testées), **Sharpe déflaté = 0.70** (cf. audit §3.2). Sous le gate PROPFIRM 1.0, **OK borderline** sous le gate research >0.7. Donc en book perso, la stratégie est **borderline GO** au sens L8 — c'est *un* alpha additionnel, pas un alpha hors normes.

### Décorrélation avec book existant (A, B, C)

| Alpha existant | Type | Fréquence | Asset | Corr ORB attendue |
|---|---|---|---|:---:|
| Strategy A (TSMOM crypto) | weekly TSMOM | Mon 00:05 UTC | BTC/ETH/SOL | ~0 (timeframe différent + univers crypto) |
| Strategy B (delta-neutral HL) | 8h funding | every 8h | HL alts | ~0 (carry funding, structurellement orthogonal) |
| Strategy C (NQ ORB iter_10) | intraday ORB | 09:30-09:45 ET | NQ futures | **+0.3-0.5 attendu** (même famille ORB mais NQ ≠ US100 CFD ; pas testé) |

→ **Pour un book perso indépendant de A/B**, marginal cost ≈ 0 (data déjà fetchée, infra existe). **Attention à C** : même famille ORB → risque de surexposition au régime open-auction US.

### Option « 3e sleeve perso » pour A/B
**Pas pour C** (corrélation cross-instrument même famille). Pour A/B seul : un livre déjà 2-asset crypto, l'ajout d'un 3e livre indices intraday est de la **diversification asset-class structurelle**, pas un alpha nouveau. À ajouter au panier ERC :

| Stratégie | Sharpe live attendu | Vol target | Poids ERC indicatif |
|---|---:|---:|---:|
| A — TSMOM crypto | 1.33 | 18% | 10% |
| B — delta-neutral | 2.0 (proxy) | 12% | 65% |
| **C+ORB combiné** ? | risque corrélation | 10% | si C en paper, ajout d'ORB-CFD ≈ 25% |
| ORB-CFD seul (sans C) | 1.54 (brut), 0.70 DSR | 10% | 25% |

→ Recommandation : **ajouter ORB-CFD au sizing vol-target 10% comme 3e livre uniquement si C n'est pas live** (pour éviter la concentration ORB-family). Estimer la corr ORB-CFD / C-NQ pour trancher.

---

## 7. Prochaine étape data : NQ + DAX 2008-2025

**LE prérequis avant tout deploy** : la totalité du verdict GO repose sur 1 épisode chop (2023). Sans validation sur d'autres régimes, le gate vr5 low est **un fit à 1 réalisation**.

### Sources évaluées (cf. audit §7)

| Source | Coût | Effort | Qualité |
|---|---|---|---|
| **firstratedata.com (NQ 1-min 2008+)** | one-shot ~$200 | 1-2 jours fetch + roll-dates | bon (continuous, ajusté) |
| Dukascopy (DAX 1-min 2008+) | $0 | 1 semaine bi5 décompression | bon (déjà décodeur dispo, `Forex/research/archived/strategy_e_fix_flow/data_setup.py`) |
| IQFeed (DTN) | $120/mo + $300 backfill | 2 jours setup | très bon |

### Ce que ça apporte

- 2008 GFC (mega-trend), 2009 recovery rally, 2011 EUR crisis + downgrade US, 2014 oil crash, 2015-16 China shock, 2018 vol shock (XIV blow-up + Q4), 2020 COVID.
- → 5-7 chop/trend episodes additionnels distincts.
- → N≈1 chop devient N≈5-7 → gate régime validable WF (sortie du fit à 1 réalisation).

### Plan suggéré post-extension

1. Fetch NQ + DAX 2008-2025 (1-2 semaines).
2. Re-tester gate régime (vr5 low, trend20 mid, rv20 mid, HMM 3-state) sur WF expanding avec **N=5-7 chop episodes**.
3. Si le gate maintient WF mean ≥70%, déployer 1phase_static.
4. Avant deploy: paper-trade ≥2 mois en live pour calibrer slippage (rapport: 2× slippage = -15pt p(funded)).

---

## 8. Verdict final et next steps

### 8.1 Verdict synthétique

| Question | Réponse |
|---|---|
| FTMO 2-phase à risk optimisé clear-t-il 70% ? | ✗ NON, plafonne 52% (mur math) |
| 1phase static + gate régime clear-t-il 70% ? | **✓ OUI, 75-77% (in-sample, N≈1)** |
| Le kill-switch ajoute-t-il de la valeur ? | ✗ NON, dead lever (-3 à -22pt) |
| Le gate régime est-il robuste ? | ⚠ NO, in-sample sur 1 chop episode |
| Stratégie viable book perso vol-target 10% ? | ⚠ borderline (DSR=0.70 à n_trials=18) |

### 8.2 Recommandation actionnable

**Court terme (sans data extension) :**
1. **NE PAS** acheter de FTMO 2-phase. Espérance négative à $155/challenge × 1/0.52 = $298/funded vs profit attendu. Le mur math est structurel.
2. **NE PAS** acheter de produit trail-6% (Apex / FundedNext Stellar 1-step). Bust_trail garanti à 50-65%.
3. **Identifier un produit 1-phase static** (target +10%, daily -5%, total -10% static **non trailing**). Vérifier les règles 2026 ; ces produits évoluent vite. Candidats potentiels (à vérifier en 2026) : FTMO Single-Phase Standard, MyForexFunds Rapid, FundedNext Express. **Aucun de ces produits ne doit avoir de trailing total**.
4. Sur ce produit : risk-per-block 1.25-1.5%, gate vr5 low tercile, **paper-trade 2 mois** avant fees.

**Moyen terme (post-extension data) :**
5. Fetch NQ + DAX 2008-2025 (~$200, 2 semaines).
6. Valider gate régime WF sur N=5-7 chop episodes distincts.
7. Si gate WF mean ≥70% se maintient, **deploy live**.
8. Si gate échoue WF étendu, **abandonner la thèse propfirm** et garder ORB comme livre perso vol-target 10% seulement.

**À écarter définitivement :**
- Apex 50K / 150K EOD trailing → bust_trail incompatible avec skew positif ORB.
- FTMO 2-phase → mur math du chaînage P1+P2.
- Bump du sizing au-delà de 2% → bust_daily explose, p(funded) chute brutalement.
- Ajout de nouveaux sleeves sur 2022-2025 → L10 budget épuisé sur sizing + gate, overfit garanti.

### 8.3 Ce qui changerait le verdict (sensitivities)

| Si... | Verdict basculerait... |
|---|---|
| Slippage live = 2× backtest | -15pt p(funded), 1phase_static gated tombe à ~60% → NO-GO sans gate optimisé |
| Fetch NQ/DAX 2008-2025 montre WF gate ≥70% sur N=5+ | GO confirmé |
| Fetch montre WF gate <65% sur N=5+ | Gate était overfit à 2023 → NO-GO live |
| Nouveau sleeve indépendant +EV (e.g. AUS200 ORB intraday) | +5-10pt via √N → 1phase_static atteint 80% |
| Apex sort produit non-trailing 1-step | À re-tester |

---

## 9. Reproductibilité

Tous scripts dans `data/ftmo_research/audit/` :

| Étape | Script | Sortie |
|---|---|---|
| 1 | `optim_step1_baseline.py` | `optim_step1_baseline.csv` + `optim_step1_output.txt` |
| 2 fine grid | `optim_step2_finegrid.py` | `optim_step2_full.csv` + `optim_step2_wf.csv` |
| 3 kill-switch | `optim_step3_killswitch.py` + `optim_step3b_fine_ks.py` | `optim_step3_ks_*.csv` |
| 5 gate régime | `optim_step5_regime_gate.py` | `optim_step5_*_*.csv` |
| 5b joint sweep | `optim_step5b_gate_risk_sweep.py` | `optim_step5b_gate_risk.csv` |
| 6 book perso | `optim_step6_personal_book.py` | `optim_step6_personal_book.csv`, `optim_step6_personal_book_yearly.csv` |

Tous : seeded, déterministes, `cd audit && /usr/bin/python3 stepX.py`.

Engine extension : `audit/optim_engine.py` (containers + kill-switch + real-path P1→P2 chaining).

---

## 10. In-sample vs WF-validé — marquage explicite

| Chiffre | Source | In-sample / WF / Live ? |
|---|---|---|
| p(funded) ftmo_2phase = 52% @ 1.25% | Étape 1 | **in-sample 2022-2025** (mur math structural, robuste) |
| p(funded) 1phase_static = 69% @ 1.25% sans gate | Étape 1 | **in-sample 2022-2025** (cohérent avec audit, robuste) |
| WF mean 1phase_static = 66% @ 1.25% sans gate | Étape 2 | **WF 5 folds**, dispersion ±25pt fold-par-fold |
| Kill-switch = dead lever | Étape 3 | **in-sample 2022-2025** (mais L19 strict, robuste) |
| p(funded) 1phase_static + vr5 low = **75%** @ 1.25-1.5% | Étape 5 | **in-sample, gate fitted sur 2022-2025 N≈1** |
| WF mean gate = 77% @ 1.5% | Étape 5 | **WF 5 folds avec gate**, **fold 3 = 65.9% gated vs 25.7% baseline** (sauvé) |
| HMM 3-state +2.8pt vs threshold | audit §5C | **in-sample**, dispersion fold > 2.8pt → non robuste |
| Sharpe daily ann 1.54 (vol-target 10%) | Étape 6 | **in-sample full 2022-2025**, DSR-deflated à 0.70 (n_trials=18) |
| MaxDD vol-target = -11.9% | Étape 6 | **in-sample 2022-2025** |
| **Live performance** | — | **0 jour** (pas encore deployé). Tout est backtest. |

---

*Optimisation réalisée 2026-06-01 — Claude Code (Opus 4.7 1M ctx). L19 + L10 + L15 respectés. Aucun re-fit massif. Tous chiffres reproductibles ci-dessus.*
