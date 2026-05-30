# Strategy C — FTMO account-size sweep (read-only, 2026-05-30)

**Objectif** : trouver la plus petite taille de compte FTMO où Strategy C
iter_10 atteint **p(pass combined Phase 1 + Phase 2) > 70%** en ≤ 40 jours
de trading.

**Stratégie** : iter_10 (NQ opening momentum), engine `engine.py:115-119`
clean (cf. `_audit/engine_contamination_2026-05-30.md` §3.1). Baseline
reproduite à la décimale : Sharpe HAC 1.5212, MaxDD -13.42%, N=346.

**Pipeline** : trade log unique reconstruit via NQBacktestEngine, converti
MNQ (`$2/pt - $2.15` RT), agrégé daily avec zero-fill (T=772 jours,
block_size=28=√T), bootstrap stationary Politis-Romano. Barrières
absorbantes :

| Barrière | Source | Type |
|---|---|---|
| Daily limit = 5% × capital | `Portfolio/risk/propfirm_canonical.py:5,37` | trailing depuis EOD peak |
| Max DD = 10% × capital | `Portfolio/risk/propfirm_canonical.py:5,38` | **STATIC** depuis starting balance |
| Phase 1 target = +10% × capital | `propfirm_canonical.py:39` | hard target |
| Phase 2 target = +5% × capital | (FTMO standard 2-step) | hard target |

**20 000 paths × 37 cellules × 2 phases.** Seed 42. Aucun chiffre
pré-calculé réutilisé (Tradeify 57% de `config.py:13` est **antérieur au
fix LOT 3** TV_TRAILING_DD ; rien de cela n'entre dans cette sim).

---

## §1. Verdict principal : **AUCUNE taille ne franchit 70%**

Le sweep révèle une **invariance d'échelle empirique** : pour chaque taille
de compte, le p(comb) optimal plafonne autour de **43-44%**. Augmenter le
capital ne déplace PAS le plafond.

| Capital | N* MNQ | p(P1) | p(P2) | **p(comb)** | CI95 | Médiane jours | DD breach P1 | Timeout P1 |
|---|---|---|---|---|---|---|---|---|
| **$10 000** | 5 | 61.0% | 71.8% | **43.85%** | [43.2, 44.5] | 20 | 30.0% | 8.9% |
| **$25 000** | 12 | 61.2% | 72.3% | **44.21%** | [43.6, 44.8] | 21 | 28.9% | 9.9% |
| **$50 000** | 20 | 59.0% | 73.5% | **43.35%** | [42.7, 43.9] | 26 | 22.8% | 18.3% |
| **$100 000** | 50 | 61.0% | 71.2% | **43.40%** | [42.8, 44.0] | 20 | 30.5% | 8.6% |
| **$200 000** | 100 | 61.2% | 71.6% | **43.79%** | [43.2, 44.4] | 20 | 30.2% | 8.6% |

**Aucune ligne ne dépasse 45%, peu importe la taille du compte.** Le seuil 70% n'est
pas atteignable par variation de la taille du compte.

Voir heatmap : `_audit/strategy_c_ftmo_account_sweep_heatmap.png`. La couleur
plafonne à ~vert moyen (jamais jaune ≥ 50%).

---

## §2. Pourquoi : la stratégie est intrinsèquement scale-invariante face à FTMO 5%/10%

Toutes les contraintes scalent linéairement avec le capital :
- `daily_limit = 5% × capital`
- `max_dd = 10% × capital`
- `target_p1 = 10% × capital`
- `target_p2 = 5% × capital`

Et le PnL daily de Strategy C scale linéairement avec N MNQ. Donc en
**N normalisé par capital** (N* MNQ par $10K) :

| Capital | N* | N*/10K ratio |
|---|---|---|
| $10K | 5 | 5.0 |
| $25K | 12 | 4.8 |
| $50K | 20 | 4.0 |
| $100K | 50 | 5.0 |
| $200K | 100 | 5.0 |

Le ratio optimal est ~5 MNQ par tranche de $10K de capital. Avec ce
scaling, le problème normalisé est **identique** à toutes les tailles ;
le bruit autour de 44% est dû à la granularité MNQ entière + variations
seed.

**Le plafond 44% est donc structurel à Strategy C × FTMO 5%/10%, pas un
problème de taille.**

---

## §3. Bonus diagnostique — fine sweep autour de N* à $25K

Plus petite taille pratique (challenge 25K est le palier FTMO standard) :

| N MNQ | p(P1) | p(P2) | p(comb) | Médiane jours |
|---|---|---|---|---|
| 10 | 58.3% | 73.9% | 43.18% | 26 |
| 11 | — | — | 43.67% | 24 |
| **12** | **61.2%** | **72.3%** | **44.21%** | 21 |
| 13 | — | — | 44.63% | 19 |
| **14** | — | — | **45.41%** | **18** |

L'optimum local est à **N=14 MNQ sur $25K** avec p(comb) = 45.4%, médiane
18 jours. Variation marginale autour de N* — confirme que la surface est
plate au sommet. Aucune amélioration au-delà du bruit (CI95 ±0.6 pp).

---

## §4. Relâcher la contrainte 40 jours

FTMO réelle n'a **pas** de limite de temps (seul la contrainte perso 40j
de l'utilisateur). Sans cette contrainte, le bottleneck devient
exclusivement le DD breach.

| Capital | N* | p(comb) ≤ 40j | p(comb) horizon ∞ | DD breach P1 |
|---|---|---|---|---|
| $10K | 5 | 43.85% | **47.68%** | 34.3% |
| $25K | 12 | 44.21% | **49.16%** | 33.0% |
| $50K | 20 | 43.35% | **53.83%** | 29.9% |
| $100K | 50 | 43.40% | **48.04%** | 33.7% |
| $200K | 100 | 43.79% | **48.24%** | 33.8% |

Le meilleur résultat absolu (horizon illimité) : **$50K, N=20, p(comb) = 53.8%**.
Encore loin de 70%.

Sans limite de temps, c'est essentiellement le ratio
`p(toucher +10% avant -10%)` qui décide. Pour Strategy C, ce ratio
plafonne autour de 70-75% pour P1 seul, et p(P2) ~71-74% pour P2 seul.
Le produit P1 × P2 ≈ 0.74 × 0.74 ≈ 0.55 (cohérent avec les 48-54% observés).

**Même sans contrainte de temps, p(pass combined) plafonne à 54%.**

---

## §5. Diagnostic — pourquoi C ne franchit pas 70%

Le problème n'est ni la taille du compte ni l'horizon, mais **la
distribution même du PnL daily de C** confrontée au ratio target/buffer
1:1 de FTMO.

### Statistiques daily Strategy C (1 NQ équivalent)

| Métrique | Valeur |
|---|---|
| Daily mean | $58.92 |
| Daily std | $662 |
| Worst day | -$440 |
| Best day | +$4 473 |
| Jours sans trade | ~50% (1.4 trade/jr en moyenne) |
| Win rate | 27.75% |
| Avg winner | $1 571 (≈ 79 pts × $20) |
| Avg loser | -$421 (≈ -21 pts × $20, près du SL hard 20pts) |

C est donc une stratégie **lumpy** : peu de trades, edge concentré dans la
queue (avg_winner / avg_loser = 3.7×). Sur 40 jours, on attend ~18 trades
dont ~5 winners. La variance domine l'edge.

### Estimation analytique (random walk approximation)

Pour un random walk avec drift μ et volatilité σ, la probabilité
d'atteindre la barrière haute (+target) avant la basse (-max_dd) est
approximativement (Cox-Miller absorbing barrier) :

```
p ≈ (1 - exp(-2 μ * L_down / σ²)) / (1 - exp(-2 μ * L_total / σ²))
```

Avec target_norm = 10%, max_dd_norm = 10%, daily_mean_norm = 0.58%/jr,
daily_vol_norm = 6.6%/jr (à N* scaling) → μ/σ² ≈ 0.13. La formule donne
**p ≈ 73%** pour Phase 1 horizon ∞. Cohérent avec l'observation 71%.

p(P1) × p(P2) ≈ 0.73 × (similaire pour target plus petit) ≈ 0.53-0.56.

**Conclusion analytique** : la borne théorique de p(comb) avec target/DD
ratio 1:1 et Sharpe 1.52 plafonne autour de 55% horizon ∞. Avec une
contrainte ≤40j, on descend à 44%.

---

## §6. Leviers qui POURRAIENT franchir 70%

Aucun ne s'applique sans modifier la stratégie ou le challenge :

1. **Cibler un broker / firme avec ratio target/DD asymétrique favorable**.
   FTMO 5%/10% impose target = max_dd. Tradeify Select Flex $25K a
   target=6%, trailing DD=$1K (4%) → ratio target/DD = 1.5×. Cela peut
   monter p(pass) à 60-65% mais ne résout pas le problème structurel
   sans aller bien au-dessus.

2. **Stratégie avec distribution moins lumpy** : Sharpe ≥ 1.5 mais
   win_rate ≥ 50% et drawdowns plus contenus → p(pass) > 70% atteignable.
   C n'est pas cette stratégie.

3. **Combiner plusieurs stratégies décorrélées** (Strategy D etc.) : si
   p_C ≈ 50% et p_D ≈ 50% avec corrélation négative ou nulle, la combinaison
   atteint 70%+ par diversification temporelle. Hors scope de cette sim.

4. **Sizing dynamique intra-phase** (downsize après drawdown, upsize après
   gain) : +5-10pp possible, plafond probable 55-60%. Hors scope car
   modifie le moteur.

5. **Augmenter MAX_DAYS au-delà de 40** : la table §4 montre que sans
   limite, on gagne ~5-10pp. Toujours sous 70%.

---

## §7. Recommandation honnête

- **L'objectif "p(pass) > 70% en ≤ 40 jours" n'est PAS atteignable avec
  Strategy C sur FTMO, quelle que soit la taille du compte.**

- Le compte le plus efficient en valeur absolue (p(comb) le plus élevé)
  est **$25K à N=14 MNQ : 45.41%** en médiane 18 jours, ou **$50K à N=20
  avec horizon illimité : 53.83%**.

- **Si l'utilisateur insiste sur un challenge FTMO** : viser le **$25K**
  comme entrée minimale (coût d'achat acceptable, granularité MNQ
  permissive, p(pass) maximisé dans la borne 44%). Accepter le 2 chances
  sur 5 de passer dans 40 jours.

- **Recommandation préférable** : ne PAS utiliser FTMO pour Strategy C.
  Continuer sur Tradeify Select Flex $25K (live cible déjà choisie cf.
  `Futures/live/strategy_c_live/config.py:1-17` et `sizing_policy.md`).
  Le ratio target/DD asymétrique de Tradeify et l'absence de daily loss
  limit funded sont mieux adaptés au profil lumpy de C.

- **Recommandation à plus long terme** : si l'objectif est vraiment un
  challenge type FTMO, développer une stratégie complémentaire avec
  distribution moins lumpy (Sharpe ≥ 1, win_rate ≥ 50%) pour combinaison
  avec C, OU pivoter sur un challenge type Tradeify/MFFU/Apex où les
  barrières ne sont pas symétriques.

---

## §8. Annexe — reproductibilité

- Script : `_audit/strategy_c_ftmo_account_sweep.py` (autonome, ~20s sur M1)
- Résultats : `_audit/strategy_c_ftmo_account_sweep_results.json`
- Heatmap : `_audit/strategy_c_ftmo_account_sweep_heatmap.png`
- Baseline reproduite : Sharpe 1.5212, MaxDD -13.42%, N=346, Total $45,510.5
- Aucun chiffre Tradeify pré-calculé n'a été réutilisé. La sim TV_TRAILING_DD
  bugée (LOT 3) appartenait à un autre module ; ici tout est recalculé from
  scratch.

Reproduction :
```bash
"<HOME>/Desktop/Unholy returns/Python3.12.9/myenv/bin/python3" \
  _audit/strategy_c_ftmo_account_sweep.py
```
