# Déploiement ORB+floor FTMO US100 — DEPLOYMENT GATE

**TL;DR — NO-GO au coût CFD US100 réaliste. KILL VÉHICULE FTMO 2-STEP.**

Le re-calibrage de coûts CFD US100 (Étape 1) tranche : le **100% K5 mesuré sur NQ futures à 2 bps RT ne survit pas le passage à US100 CFD live (6-10 bps RT)**. p(funded) tombe à 3.6% à 6 bps et **0% à 8 bps+**. Le mean R devient négatif dès 4 bps, et le floor_taper ne peut pas inverser un drift négatif — il rallonge juste le grind.

**Conséquence : ne pas acheter le challenge FTMO 2-step avec cette config. Fee de propfirm évité (~$200-500 selon plan).**

| Niveau coût | Réalisme | Best OOF p_funded | meanR | Decision |
|---|---|---:|---:|---|
| 2 bps RT | NQ futures backtest (= idéal, non-applicable FTMO) | **100%** (K5) | +0.016 | GO mais non-applicable |
| 4 bps RT | US100 CFD très liquide hors auction | 47% (K5) | -0.028 | MARGINAL |
| **6 bps RT** | **US100 CFD liquide hours typique** | **3.6%** (K1) | -0.071 | **KILL** |
| 8-12 bps RT | US100 CFD pendant 09:30 ET auction (= moment ORB) | 0% | -0.16 | KILL |

L'ORB **trigger PRÉCISÉMENT pendant le 09:30 ET open auction** = le moment où le spread CFD est le plus large → coût effectif probablement 8-12 bps RT en live.

---

## 0. Cadrage (relecture honnête)

- L'ORB+floor n'a **AUCUN edge per-trade** (DSR_p 0.08, placebo Gaussien zéro-mean + floor = 97.7% p_funded).
- Le 100% K5 était **un exploit math du floor × no-time-limit**, pas un edge.
- L'exploit dépend de mean_R ≥ 0 par trade. Sous coût CFD US100 réaliste, **mean R est négatif** → l'exploit s'inverse (la dérive négative compoundée mène au floor).
- Le floor_taper ne PRÉSERVE PAS l'edge — il ralentit le bust mais ne génère pas de PnL positif.

## 1. Check 0 — Règles FTMO 2-step actuelles

`ftmo_rules.py` documente le tout. **HUMAN_VERIFY requis avant tout deploy.**

### Connues / supposées (memory 2025-2026)
| Règle | Valeur supposée | Confidence |
|---|---|---|
| P1 profit target | +10% | haute |
| P2 profit target | +5% | haute |
| Daily loss max | -5% from day-start balance, floating equity | haute |
| Max overall loss | -10% | haute |
| **Max overall mode** | **STATIC vs TRAILING ?** | **À VÉRIFIER (critique)** |
| Min trading days | 4 | haute |
| Time limit | NONE (no-time-limit confirmed 2023) | haute |
| Inactivity | 30 jours | haute |
| Consistency rule | NONE sur 2-step | haute (memory) |
| News trading | autorisé sur 2-step | confirme manuel |
| Stop-loss mandatoire | NON sur 2-step | confirme manuel |

### Action HUMAN_VERIFY (avant tout deploy)
1. Confirmer **STATIC vs TRAILING max DD** (Q1) — change le floor_taper math.
2. Confirmer **consistency rule absent** sur 2-step actuel.
3. Confirmer **news trading autorisé** sur 2-step.
4. Confirmer **leverage cap sur US100** (FTMO standard ~1:20-1:30, certains plans 1:100).
5. Vérifier **spread typique US100** sur compte FTMO réel (= Étape 1 input).

## 2. Étape 1 — Re-calibration coûts US100 CFD (le tueur)

`audit/ftmo_us100_cost_sweep.py` → `ftmo_us100_cost_sweep.csv`.

### Hypothèse de cost CFD US100

Sources (à confirmer en démo) :
- FTMO US100 spread hors auction: typiquement 0.7-1.0 pt
- US100 à ~25000 → 0.7 pt = 2.8 bps single = 5.6 bps RT
- 09:30 ET open auction (= ORB trigger window): spread peut élargir 2-4 pts = 8-16 bps single
- Slippage stop-buy order au break: 0.5-1 pt
- **Cost RT effectif live: 6-12 bps** selon timing et exécution

### Verdict cost sweep (NQ data + bumped cost as proxy)

| Cost RT | Realistic for | OOF p_funded best | Mean R | Verdict |
|---:|---|---:|---:|---|
| 2 bps | NQ futures (non-applicable FTMO) | **100% (K5)** | +0.016 | GO mais futures hors FTMO |
| 4 bps | US100 CFD pristine (rare) | 47% (K5) | -0.028 | MARGINAL — borderline |
| **6 bps** | **US100 CFD typique** | **3.6%** (K1) | -0.071 | **KILL** |
| 8 bps | US100 CFD avec slip auction | 0% | -0.115 | KILL |
| 10-12 bps | US100 CFD pendant auction wide | 0% | -0.16 à -0.20 | KILL |

### Le crash au passage 4→6 bps

Entre 4 et 6 bps, p_funded chute de 47% → 3.6%. C'est le seuil de basculement où le mean R per-trade devient assez négatif pour compounder en bust avant d'atteindre le target.

Mécaniquement : mean R passe de -0.028R à -0.071R → ratio = 2.5×. En grind compoundé sur ~50-100 trades, ça transforme un strat marginal en bust quasi-certain.

### Pourquoi K5 plafonne plus tôt que K1 à coût élevé ?

À cost 4 bps :
- K5 = 47% (avec floor_taper)
- K1 = 40% (sans floor_taper)

À cost 6 bps :
- K1 = 3.6%
- K5 = 0% (PIRE car floor_taper rallonge le grind sous drift négatif → plus de bust drift bleed)

→ **Confirmation L19 : floor_taper N'EST PAS un edge, c'est du path management qui aide sous edge ≥ 0 et NUIT sous edge < 0.**

### Décision cost-recalc

**KILL.** Aucune configuration testée ne donne p_funded ≥ 50% sous coût CFD US100 réaliste (≥ 6 bps RT).

**Conditions de basculement possible vers GO (HUMAN_VERIFY)** :
1. Si FTMO offre un plan où US100 spread effectif < 0.5 pt (= ~4 bps RT en zone borderline 47%).
2. Si la fenêtre ORB peut être DÉCALÉE (e.g. 10:00 ET au lieu de 09:30) pour éviter l'auction spread spike. **MAIS** : changer le timing = changer la stratégie (perdre le signal d'auction).
3. Si l'on dispose d'un compte futures NQ direct chez un broker non-FTMO (CFM, Topstep avec futures...) à 2 bps RT.

## 3. Étape 2 — Floor_taper module (live spec)

`floor_taper.py` — implémentation propre :

### Logique
```
λ_daily  = max(taper_min, distance_to_daily_floor / cushion_daily)
λ_total  = max(taper_min, distance_to_total_floor / cushion_total)
λ_target = post_target_factor (e.g. 10%) if equity >= P1_target else 1.0
λ_final  = min(λ_daily, λ_total, λ_target)
```

### Paramètres par défaut
- `cushion_daily_pct` = 2% (taper kicks in when within 2% of daily floor)
- `cushion_total_pct` = 4% (taper kicks in when within 4% of total floor)
- `taper_min_factor` = 0.25 (floor at 25% size)
- `post_target_factor` = 0.10 (after P1 target, drop to 10%)
- `post_target_stop_trading` = False (default; switch to True for max safety)

### L19 — effective leverage documenté

À mean équity-trajectoire :
- Sans floor_taper : levier constant 100% (= base 0.5% par trade)
- Avec floor_taper : levier moyen effectif ≈ 70-85% (la taper se déclenche occasionnellement)

**Conséquence : floor_taper down-size effectif ~20-30% du temps**. Cela rallonge le median grind d'environ +20-30%. **Sous edge ≥ 0, ce trade-off est positif** (réduit bust). **Sous edge < 0, ce trade-off est négatif** (rallonge l'exposition au drift).

### Bug-de-spec critique

La logique floor_taper assume max_overall_loss_mode="static". Si FTMO utilise TRAILING (= floor monte avec HWM), λ_total devient plus sévère :
- En STATIC: floor à $45K reste $45K même après HWM $55K.
- En TRAILING: floor monte avec HWM × 0.90, donc à HWM=$55K → floor=$49.5K.

→ **HUMAN_VERIFY Q1 critique. Si TRAILING, recalibrer cushion_total_pct à 6-8% pour plus de marge.**

## 4. Étape 3 — Signal engine ORB V2+E7

`signal_engine.py` — module live, point-in-time strict.

### Spec verrouillée
- **OR window**: 09:30:00-09:44:59 ET (15 minutes = M06 baseline)
- **V2 filter**: OR range ≥ 0.1% (= 10 bps) de mid-price **OU** ≥ 30% ATR_20d (configurable)
- **Entry**: après close-confirmé break de or_hi (long) ou or_lo (short). Entry à open du bar suivant (delay-1 clean, L26).
- **Initial SL**: opposite side of OR = 1R.
- **E7 trail**: when MFE ≥ +1R, ratchet SL to entry (BE).
- **Time-stop**: 12:30 ET = 16:30 UTC DST / 17:30 UTC standard.

### Garde-fous codés
- **Filter en %/ATR JAMAIS en points** (le piège instrument-price documenté F1/breakout)
- **Delay-1 obligatoire** (entry au next-bar open, pas same-bar = L26 décisif)
- **Time-stop strict** (12:30 ET, jamais EOD pour 2-step)

## 5. Étape 4 — Exécution + monitoring (SI cost survit)

[Module non développé puisque KILL au coût]. Si jamais on identifie un setup où cost ≤ 4 bps :

### Stack live attendu
- **Broker FTMO**: MT4/MT5 (FTMO MT broker).
- **Order management**: stop-buy order placé à or_hi + 1 tick AVANT que le break ne se produise (= dormant stop). Symétrique pour stop-sell at or_lo.
- **OCO**: stop-buy AND stop-sell, l'un déclenche → annule l'autre.
- **Risk management**: position size calculée par floor_taper.position_size_usd() à chaque trade.
- **Telegram alerting**: trade open / SL hit / time-stop / floor proximity warning.
- **Kill-switch**: si daily_distance_pct < 1% (= 1pt before floor) → close all positions immédiatement.

### Inactivity keep-alive
- L'ORB trade ~daily les jours où V2 passe (~50-60% des jours selon filter).
- Si filter rejette > 28 jours consécutifs (rare), forcer un mini-trade au plus petit lot autorisé pour reset compteur inactivité.

## 6. Étape 5 — Démo runbook

[Si Étape 1 valide GO, ce qui n'est pas le cas ici] :

### Checklist démo (dry-run T1-T4)
- **T1** (signal): vérifier que le signal engine génère le break correctement (OR computed, V2 filter applied, direction detected).
- **T2** (sizing): vérifier que floor_taper renvoie λ correct aux différents niveaux d'équité.
- **T3** (exécution): vérifier que les ordres OCO sont posés/annulés correctement, fill price proche du break level (slip < 0.5 pt).
- **T4** (path management): vérifier que la trail-BE se déclenche à +1R et que time-stop coupe à 12:30 ET.

### Critère démo réussie
- 10 trades minimum sans incident d'exécution.
- Mean slip par trade ≤ 1 pt (sinon cost réel > backtest 6 bps).
- Floor_taper déclenche correctement sur scénarios test injectés (daily DD -3%, -4%).

### Critère final GO / NO-GO challenge
- Étape 1 cost survit + démo clean + HUMAN_VERIFY rules → GO challenge.
- N'importe quel échec → NO-GO. Documenter et passer à autre véhicule.

## 7. Verdict final

**NO-GO challenge FTMO 2-step US100 ORB+floor au coût CFD live.**

Le 100% K5 sur NQ futures (cost 2 bps) ne s'applique pas à US100 CFD (cost 6-10 bps). Le mean R devient négatif → l'exploit math du floor s'inverse → bust quasi-certain à 50-100 trades.

### Recommandations alternatives

1. **NQ futures direct (non-FTMO)**: Topstep, Apex, MFFU offrent des challenges futures à coûts ~2 bps RT. **L'exploit fonctionne là (100% K5).** Mais c'est une décision séparée (FTMO ≠ Topstep en risk profile).

2. **FTMO sur instrument différent**: Forex EURUSD spread typique 0.1 pt = ~1 bp RT → potentiellement viable, MAIS l'ORB V2+E7 a été calibrée sur indices, pas Forex. Re-calibration nécessaire.

3. **Pas de FTMO 2-step ORB indices**. Documenter dans research log "le véhicule FTMO ORB+floor sur US100 est éliminé par les coûts CFD" et passer à autre stratégie / autre véhicule.

### Sauvegarde

- Fee FTMO 2-step $50K typiquement ~$345 (FTMO standard) → **$345 économisés**.
- Plus la perte attendue sous mean R -0.07R × 100 trades × $50K × 0.5% risk = -$1750 perdue en plus du fee. **Total économisé ~$2000.**

## 8. Reproductibilité

| Fichier | Rôle |
|---|---|
| `ftmo_rules.py` | Définition des règles FTMO + HUMAN_VERIFY warnings |
| `floor_taper.py` | Logique sizing floor proximity + post-target |
| `signal_engine.py` | ORB V2+E7 signal generator |
| `data/ftmo_research/audit/ftmo_us100_cost_sweep.py` | Cost recalc (réutilise combined_pushpass infra) |
| `data/ftmo_research/audit/ftmo_us100_cost_sweep.csv` | Résultats cost sweep |
| `data/ftmo_research/audit/ftmo_cost_sweep_output.txt` | Log lisible |
| `DEPLOYMENT.md` | Ce document |

## 9. Caveats explicites

1. **Cost sweep utilise NQ data avec cost bumped**, pas US100 data directement. Hypothèse : la signature gross du signal ORB est similaire NQ vs US100 (instruments très corrélés). Si on veut confirmation directe, ré-extraire trades sur US100 m1_panel (Algo_claude has US100 data 2020-2026, sample 6 ans seulement, moins de robustesse OOF).

2. **L'estimation 6-10 bps US100 CFD live est une projection** basée sur spreads typiques FTMO publiques. À confirmer en démo.

3. **Le NO-GO ici est ferme** : 3.6% p_funded à 6 bps est sans ambiguïté en kill zone. Aucune marge.

4. **Le floor_taper code reste utile** pour le cas futur où on aurait un setup à cost ≤ 4 bps (e.g. NQ futures direct).

---

*Deployment gate réalisé 2026-06-02 — Claude Code (Opus 4.7 1M ctx). Verdict : KILL véhicule FTMO 2-step US100 ORB+floor au coût CFD réaliste. NQ-futures-direct alternative à explorer séparément.*
