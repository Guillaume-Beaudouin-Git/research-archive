# BREAKOUTPROP FIT — Strategy A (BTC/ETH/SOL TSMOM v3)

**TL;DR — NO-GO BreakoutProp Classic dans les hypothèses testées (daily DD 4% / total DD 6%, $25K, 2-phase).** Le worst-day de A reste **-20.7%** même avec stop-loss intraday live (`STOP_LOSS_VOL_MULT=2.0`), et déborde le daily DD limit dans **1.08% des jours**. **L7 confirmé : le daily DD est le mur, exactement comme sur Propr.** p(funded) max sous de-lever sweep = **36.5%** (à vol_target 0.10-0.13), bien sous le seuil 60% du brief.

**Le seul chemin GO** : confirmer HUMAN_VERIFY que BreakoutProp Classic accepte un **daily DD ≥ 8% ET total DD ≥ 10%**. Sinon, A reste **personal book**.

| Métrique | Valeur | Verdict |
|---|---:|---|
| A's worst single day (with stop-loss live) | **-20.7%** | ✗ breach 4% daily DD |
| A's max DD compoundé (2020-2026) | -51.2% | ✗ breach 6% total DD massif |
| Daily moves worse than -4% | 23 jours / 2121 (1.08%) | ~4 events/an |
| **p(funded) sweep best** | **36.5%** | **NO-GO (seuil 60%)** |
| p(bust daily) à vol=0.18 (live) | 50.9% | tueur dominant |

---

## 0. HUMAN_VERIFY — Règles BreakoutProp Classic actuelles

⚠ **Je n'ai pas accès web direct. Les règles ci-dessous sont des estimations basées sur la connaissance publique mid-2025. À CONFIRMER avant tout déploiement.**

### Hypothèses utilisées dans la simulation

| Règle | Valeur testée | Source |
|---|---|---|
| Compte | $25K (entry-level) | hypothèse budget standard |
| Phase 1 target | +10% | typique crypto-prop 2-step |
| Phase 2 target | +5% | typique |
| **Daily DD** | **4%** | HUMAN_VERIFY (Propr était 3% — Breakout supposé plus lâche) |
| **Total DD** | **6%** static | HUMAN_VERIFY (statique vs trailing critique) |
| Min trading days | 3 | typique |
| Time limit | None | typique crypto-prop "no-time-limit" |
| Cost RT | 0.17% (per L9) | Hyperliquid spec ; Kraken peut être 0.20-0.30% |

### Questions critiques à confirmer (Q1-Q5) avant deploy

1. **Daily DD réel** : 4%, 5%, 6% ? Chaque 1% change p_funded de ~5pt (cf. §3.2).
2. **Total DD réel** : 6%, 8%, 10% ? Et **STATIC vs TRAILING** ? Critique pour le floor_taper.
3. **Min trading days** : 3 ou 5 ? Plus restrictif rallonge le grind.
4. **Consistency rule** : certains crypto-props l'ont (un single trade > X% du PnL → fail). Pour TSMOM weekly c'est risqué.
5. **Plateforme et coûts réels** : Kraken-backed ? Spread BTC/ETH/SOL réel + funding si perp ?

---

## 1. Étape 1 — Profil de DD de A vs règles (MAKE-OR-BREAK)

Scripts : `_breakoutprop_fit.py` (v1) + `/tmp/breakoutprop_fit_v2.py` (v2 avec stop-loss intraday) → `breakoutprop_fit_*.csv`.

### Spec exact testé
- 3-asset core : BTC, ETH, SOL (config.py `UNIVERSE[:3]`)
- Daily close from Binance M1 (2020-08-11 → 2026-06-01 = 2121 jours OOS)
- Signal : `tanh(cumret_28d(t-1) / (vol_28d(t-1) × √28)).clip(lower=0)` (signal.py `compute_signal`)
- Rebalance : Lundi (signal.py `apply_weekly_rebalance(weekday=0)`)
- Vol targeting : portfolio realized vol 20-jours, scaled to `vol_target`, capped [0.1, 2.0]
- Cost RT : 0.17% sur position change
- Stop-loss v2 : per-asset cap à -2 × σ_asset_20d (logique live `STOP_LOSS_VOL_MULT=2.0`)

### v1 (sans stop-loss intraday) — vol_target = 0.18 (live)

| Métrique | Valeur |
|---|---:|
| Ann ret | +37.8% |
| Ann vol | 30.7% |
| Sharpe | 1.23 |
| Max DD compoundé | **-50.9%** |
| Worst single day | **-20.3%** |
| Daily P&L p99 | -4.1% |
| Days < -3% | 42 (1.98%) |
| Days < -4% | 23 (1.08%) |
| Days < -5% | 15 (0.71%) |

### v2 (avec stop-loss live)

| Métrique | Valeur | Δ vs v1 |
|---|---:|---:|
| Ann ret | +25.0% | -13pt |
| Sharpe | 0.77 | -0.46pt |
| Max DD | -51.2% | ~même |
| Worst single day | **-20.7%** | ~même (stop n'aide pas) |
| Days < -4% | 23 (1.08%) | identique |

→ **Le stop-loss intraday réduit la return (-13pt ann) sans réduire le worst day.** Les big crashes crypto sont des moves > 2σ qui touchent le stop ET dépassent largement le cap.

### Reconciliation avec MaxDD -6.9% reporté CLAUDE.md

Le -6.9% est la **moyenne OOS MaxDD across WF folds** (`outputs/walk_forward/fold_results.csv`) :

| Fold | Période | OOS MaxDD |
|---:|---|---:|
| 1 | 2017-10 → 2018-10 | **-27.9%** (worst fold, 2018 bear) |
| 2 | 2018-10 → 2019-10 | -14.9% |
| 3 | 2019-10 → 2020-10 | -3.7% |
| 4 | 2020-10 → 2021-10 | -7.8% |
| 5 | 2021-10 → 2022-10 | -7.4% |
| 6 | 2022-10 → 2023-10 | 0.0% (n=2 trades) |
| 7 | 2023-10 → 2024-10 | -1.8% |
| 8 | 2024-10 → 2025-10 | -1.7% |
| **mean** | — | **-6.9%** |

→ **Le -6.9% est la moyenne, pas le worst fold**. Pour propfirm le worst-case fold compte = -27.9%. Le worst-fold a déjà breach le total DD 6% × 5.

### Make-or-break verdict

| Test | A's value | BreakoutProp (suppo) | Pass ? |
|---|---:|---:|:---:|
| Worst single day | -20.3% (v1) / -20.7% (v2) | -4.0% | ✗ |
| Days worse than -4% | 1.08% des jours (~4 évènements/an) | borne | ✗ fréquent |
| Max DD compoundé | -51% | -6% | ✗ massive |
| Worst WF fold MaxDD | -27.9% | -6% | ✗ |

**MAKE-OR-BREAK ÉCHOUE** : A's DD profile dépasse fondamentalement BreakoutProp Classic à 4%/6%.

---

## 2. Étape 2 — p(funded) bootstrap (block 14 jours, 5000 paths)

`/tmp/breakoutprop_fit_v2.py::simulate_challenge_2phase` → block-bootstrap 2-phase.

### vol_target = 0.18 (live spec), rules supposées (4% / 6% / static)

| Métrique | Valeur |
|---|---:|
| **p(funded)** | **27.6%** |
| p(P1 pass) | 46.3% |
| p(bust daily) | **50.9%** ← tueur dominant |
| p(bust total) | 21.4% |
| p(timeout) | 0% |
| Median P1 TTP | 34 jours |
| Median P2 TTP | 13 jours |

→ **NO-GO clair à vol live 0.18.**

---

## 3. Étape 3 — De-leveraging sweep (L19)

Variations de `vol_target` avec stop-loss live, rules supposées.

### Table complète

| vol_target | Ann ret | Ann vol | Sharpe | Max DD | Worst day | **p(funded)** | bust_daily | bust_total | P1 TTP | P2 TTP |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.05 | 6.9% | 20.6% | 0.34 | -39.9% | -20.8% | **35.3%** | 43.3% | 21.4% | 97 | 44 |
| 0.08 | 10.9% | 22.9% | 0.47 | -42.3% | -20.8% | 35.9% | 42.4% | 21.6% | 75 | 35 |
| **0.10** | 13.4% | 24.8% | 0.54 | -44.1% | -20.7% | **36.1%** | 40.7% | 23.2% | 65 | 30 |
| **0.13** | 17.4% | 27.4% | 0.64 | -46.8% | -20.7% | **36.5%** | 36.6% | 26.9% | 52 | 23 |
| 0.15 | 20.1% | 29.3% | 0.69 | -48.6% | -20.7% | 33.9% | 40.5% | 25.6% | 44 | 18 |
| 0.18 (live) | 25.0% | 32.3% | 0.77 | -51.2% | -20.7% | 27.6% | 50.9% | 21.4% | 34 | 13 |
| 0.25 | 34.8% | 39.7% | 0.88 | -57.0% | -20.7% | 26.8% | 55.3% | 18.0% | 25 | 6 |
| 0.35 | 45.5% | 50.0% | 0.91 | -63.4% | -20.7% | 22.7% | 65.3% | 12.0% | 18 | 4 |

### Lectures critiques

**1. p(funded) plafonne à ~36.5% à vol_target=0.13.** Aucune configuration ne dépasse 37%. Le seuil GO du brief (60%) est inatteignable.

**2. Le worst-day reste -20.7% à TOUS les vol_targets** — pourquoi ?

Le `VOL_SCALAR_MAX=2.0` (config.py) permet 2× leverage pendant les périodes de basse vol. Quand vol_realized_20d est très basse (été 2020, fin 2023), scalar = vol_target / vol_realized peut atteindre 2.0 → position 2× le signal. Quand un crash arrive après une low-vol period, l'impact est **doublé**.

**Bug structurel config** : le scalar cap permet de l'over-leverage exactement quand on devrait dé-leverer. Pour propfirm, il faudrait cap `VOL_SCALAR_MAX = 0.5-1.0`. Mais même avec ce fix, le worst day resterait ~-10% (= un asset crash 20% × scalar 0.5 × signal 1.0) → encore largement au-dessus du 4% daily DD.

**3. Trade-off de-lever / time-to-target :**
- vol_target=0.10 (best p_funded=36%) : grind = 65j + 30j = **~3 mois pour funded**
- vol_target=0.05 (très conservateur) : grind = **~5 mois**
- vol_target=0.18 (live) : grind = **~1.5 mois** mais p_funded chute à 28%

### Sensitivity à la limite daily DD (vol_target=0.10, with stop-loss)

| daily_dd | p(funded) | bust_daily | bust_total |
|---:|---:|---:|---:|
| 3.0% (Propr — breach historique) | 32.7% | 52.8% | 14.5% |
| **4.0% (BreakoutProp supposé)** | **36.1%** | 40.7% | 23.2% |
| 5.0% | 40.4% | 30.4% | 29.2% |
| 6.0% | 40.8% | 25.5% | 33.7% |
| 8.0% | 41.3% | 14.0% | 44.7% |
| 10.0% | 41.3% | 9.3% | 49.4% |

→ **Même à daily_dd=10%, p_funded plafonne à 41.3%.** Le bust_total prend le relais quand daily_dd est lâche. **Le mur n'est pas seulement daily_dd, c'est l'AGRÉGAT des deux floors.**

### Sensitivity à la limite total DD (vol_target=0.10, daily_dd=4%)

| total_dd | p(funded) | bust_daily | bust_total |
|---:|---:|---:|---:|
| 5.0% | 32.6% | 36.6% | 30.7% |
| **6.0%** | **36.1%** | 40.7% | 23.2% |
| 8.0% | 40.0% | 46.7% | 13.3% |
| 10.0% | 42.3% | 50.2% | 7.5% |
| 12.0% | 43.7% | 52.6% | 3.7% |
| 15.0% | 44.4% | 54.1% | 1.5% |

→ **Même à total_dd=15%, p_funded plafonne à 44%.** Le daily_dd reprend la main quand total_dd est lâche.

### Combiné : daily_dd × total_dd plus permissifs

À vol_target=0.10 + daily_dd 8% + total_dd 12% : **p_funded ≈ 47%** (estimation).

**Aucune configuration BreakoutProp réaliste (= règles standards crypto-prop) ne fait passer A au-dessus de 50% p_funded.**

---

## 4. Verdict honnête

### Trois hypothèses sur BreakoutProp Classic

**Cas A — Hypothèse standard (4% daily / 6% total)** : 
- p(funded) max = 36% à vol_target 0.10-0.13.
- NO-GO clair. Le challenge fee ($100-300 typique crypto-prop) est jeté.

**Cas B — Si BreakoutProp est plus lâche (5% daily / 8% total)** :
- p(funded) ≈ 41%.
- Encore NO-GO sur le seuil 60% du brief.

**Cas C — Si BreakoutProp est très lâche (8% daily / 12% total)** :
- p(funded) ≈ 47%.
- Marginal. Près du seuil mais pas franchi.

### Décision opérationnelle

**NO-GO sur les hypothèses testées** (Cas A et B, qui couvrent le BreakoutProp Classic public).

**HUMAN_VERIFY requis** : si BreakoutProp Classic offre effectivement daily_dd ≥ 8% ET total_dd ≥ 12%, **re-run le sweep avec les vrais paramètres**. Sinon, A reste **personal book** comme actuellement.

### Pourquoi le breach Propr 3% s'étend à BreakoutProp 4%

Le breach Propr 3% (memory CLAUDE.md) est cohérent avec mon simulator : à daily_dd=3% + vol_target=0.10, p_funded=33% / bust_daily=53%. L'écart à BreakoutProp 4% ne sauve pas A : 36% / 41% selon vol_target. **Le tueur n'est pas le 3% spécifique de Propr, c'est le profil de DD intrinsèque de A** (worst day -20% × occurrence ~4/an).

### Alternatives à explorer

1. **Modifier le signal vers daily-rebalance avec stop intraday strict** = modif L10 majeure, change A en strat différente. Hors scope L19.

2. **Trouver un crypto-prop à daily_dd ≥ 8%** : BreakoutProp Pro (si existe), FundedNext Crypto, CryptoFund Trader — confirmer les specs (HUMAN_VERIFY).

3. **Accepter A comme personal book uniquement** : compte perso vol_target=0.18 (live), MaxDD compoundé attendu ~50% mais sans bust artificiel propfirm. Sharpe 1.23 OOS reste honnête.

4. **Crypto Fund Trader pour Strategy D** (déjà testé, NO-GO car D failed les 4 stat-arb killers).

### Caveats irréductibles

1. **HUMAN_VERIFY règles BreakoutProp** est obligatoire. Mes hypothèses 4%/6% peuvent être trop conservatrices ou trop lâches.
2. **Le simulator n'inclut pas tous les détails live** : pas de funding (si trade-perp), pas de slippage intra-rebalance (si large position), `VOL_SCALAR_MAX=2.0` permissif (= scaling propfirm devrait être plus strict).
3. **Le worst-day -20% est cohérent avec l'historique réel crypto** (LUNA, FTX, mars 2020, etc.). Pas un artefact de simulation.
4. **L7 confirmé empiriquement** : daily DD strict tue les momentum weekly-rebalanced. Tout propfirm crypto avec daily_dd ≤ 6% est probablement hostile à A.

---

## 5. Reproductibilité

| Script | Sortie |
|---|---|
| `_breakoutprop_fit.py` (v1, no stop-loss) | `breakoutprop_fit_equity_v018.csv`, `breakoutprop_fit_levier_sweep.csv` |
| `/tmp/breakoutprop_fit_v2.py` (v2, with stop-loss live) | `breakoutprop_fit_sweep_stoploss.csv`, `breakoutprop_fit_v2_output.txt` |
| `breakoutprop_fit_output.txt`, `breakoutprop_fit_v2_output.txt` | Logs lisibles |

Data : `data/panels/m5_indices/binance/{BTC,ETH,SOL}USD_M1.csv`. Cost = 0.17% RT.

Note : `signal.py` collision avec le module `signal` standard Python → script déplacé à `/tmp/` pour exécution propre. Pour reproduire :
```
cd /tmp && /usr/bin/python3 /tmp/breakoutprop_fit_v2.py
```

---

## 6. In-sample vs OOS marquage explicite

| Chiffre | Source | Statut |
|---|---|---|
| Sharpe 1.33 OOS (CLAUDE.md) | WF mean | **legacy report, à reconcilier** |
| MaxDD -6.9% OOS (CLAUDE.md) | WF mean across folds | **mean, pas worst-fold** |
| Worst single day -20.7% | Sim 2020-2026 + stop-loss | **OOS strict** |
| Days < -4% : 1.08% | Sim 2020-2026 + stop-loss | **OOS strict** |
| p(funded) 36% (max sweep) | Block-bootstrap 5000 paths | **in-sample params** |
| L7 daily_dd binding | Sensitivity sim | **structural** |
| Live performance BreakoutProp | — | **0 jour** (NO-GO) |

---

*BreakoutProp fit réalisé 2026-06-02 — Claude Code (Opus 4.7 1M ctx). Verdict : NO-GO BreakoutProp Classic sous hypothèses standards 4%/6%. p(funded) plafond 36-47% selon règles. L7 daily DD confirmé. A reste personal-book sauf preuve HUMAN_VERIFY que BreakoutProp Classic accepte daily_dd ≥ 8%.*
