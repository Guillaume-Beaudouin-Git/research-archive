# mc_sizing_vs_time — Strategy C iter_10 / Tradeify Select $25K

*Generated: 2026-05-26 | N=20,000 | seed=42 | eval_DD=$1,000 | target=$1,500 | 8 sizings*

> **Note technique** : 1 NQ = $20/point = 10 MNQ (ratio 10:1, pas 5:1).
> Entrées `10 MNQ (cap / ~1NQ)` et `15 MNQ (~1NQ+5MNQ)` reflètent les équivalences correctes.

---

## 1. P(pass) par sizing × time_cap

| Sizing                       | 7j | 14j | 21j | 30j | 60j | 180j |
|------------------------------|------ | ------ | ------ | ------ | ------ | ------|
| 1 MNQ                        |   0.0% |   0.0% |   0.0% |   0.1% |   1.9% |  37.2% |
| 2 MNQ (baseline)             |   0.1% |   1.0% |   3.4% |   8.0% |  27.8% |  62.8% |
| 3 MNQ                        |   1.4% |   7.1% |  14.2% |  23.8% |  44.4% |  52.9% |
| 4 MNQ                        |   3.6% |  14.7% |  25.1% |  34.8% |  45.6% |  46.6% |
| 5 MNQ                        |   4.6% |  19.4% |  30.9% |  38.4% |  42.6% |  42.7% |
| 7 MNQ                        |   5.0% |  22.0% |  32.3% |  35.8% |  36.4% |  36.4% |
| 10 MNQ (cap / ~1NQ)          |   5.0% |  18.5% |  23.6% |  24.4% |  24.4% |  24.4% |
| 15 MNQ (~1NQ+5MNQ)           |   4.3% |  10.2% |  11.2% |  11.3% |  11.3% |  11.3% |

## 2. P(bust) par sizing × time_cap

| Sizing                       | 7j | 14j | 21j | 30j | 60j | 180j |
|------------------------------|------ | ------ | ------ | ------ | ------ | ------|
| 1 MNQ                        |   0.0% |   0.0% |   0.0% |   0.0% |   0.2% |   5.4% |
| 2 MNQ (baseline)             |   0.0% |   0.0% |   0.5% |   3.2% |  15.7% |  34.1% |
| 3 MNQ                        |   0.0% |   2.6% |  10.7% |  21.0% |  40.1% |  47.1% |
| 4 MNQ                        |   0.6% |  13.8% |  28.1% |  40.3% |  52.3% |  53.4% |
| 5 MNQ                        |   3.6% |  25.6% |  41.7% |  51.8% |  57.2% |  57.3% |
| 7 MNQ                        |  12.9% |  42.8% |  57.6% |  62.6% |  63.6% |  63.6% |
| 10 MNQ (cap / ~1NQ)          |  32.3% |  65.0% |  74.0% |  75.6% |  75.6% |  75.6% |
| 15 MNQ (~1NQ+5MNQ)           |  64.1% |  86.2% |  88.5% |  88.7% |  88.7% |  88.7% |

## 3. P(unfinished) par sizing × time_cap

| Sizing                       | 7j | 14j | 21j | 30j | 60j | 180j |
|------------------------------|------ | ------ | ------ | ------ | ------ | ------|
| 1 MNQ                        | 100.0% | 100.0% | 100.0% |  99.9% |  97.9% |  57.5% |
| 2 MNQ (baseline)             |  99.9% |  99.0% |  96.1% |  88.9% |  56.5% |   3.1% |
| 3 MNQ                        |  98.6% |  90.3% |  75.0% |  55.3% |  15.5% |   0.0% |
| 4 MNQ                        |  95.8% |  71.5% |  46.8% |  24.9% |   2.1% |   0.0% |
| 5 MNQ                        |  91.8% |  55.0% |  27.4% |   9.9% |   0.2% |   0.0% |
| 7 MNQ                        |  82.1% |  35.2% |  10.1% |   1.6% |   0.0% |   0.0% |
| 10 MNQ (cap / ~1NQ)          |  62.7% |  16.5% |   2.4% |   0.1% |   0.0% |   0.0% |
| 15 MNQ (~1NQ+5MNQ)           |  31.6% |   3.6% |   0.3% |   0.0% |   0.0% |   0.0% |

---

## 4. Sweet spot optimal par time_cap

| Time cap | Sizing optimal | P(pass) optimal | Gate 25% |
|----------|---------------|----------------|---------|
| 7j | 7 MNQ | 5.0% | ✗ FAIL |
| 14j | 7 MNQ | 22.0% | ✗ FAIL |
| 21j | 7 MNQ | 32.3% | ✓ PASS |
| 30j | 5 MNQ | 38.4% | ✓ PASS |
| 60j | 4 MNQ | 45.6% | ✓ PASS |
| 180j | 2 MNQ (baseline) | 62.8% | ✓ PASS |

---

## 5. Analyse : gate P(pass in 30d) ≥ 25%

Maximum P(pass in 30d) observé : **38.4%** (sizing : 5 MNQ)

**Gate PASSED** : 5 MNQ atteint 38.4% ≥ 25%.

Profil du trade iter_10 (invariant au sizing) :
- Fréquence : 0.458 trades/jour → ~14 trades sur 30j
- Win rate : 27.75% → E[wins in 30d] ≈ 3.9 trades gagnants
- avg_winner ≈ $314 × (n_mnq/2) ; avg_loser ≈ $85 × (n_mnq/2)
- Pour atteindre $1,500 en 30j il faut E[P&L 30j] >> $1,500
- E[P&L 30j] = 14 × avg_trade ≈ 14 × $66 × (n_mnq/2) à 2 MNQ baseline = $924
- Mais E[P&L] est insuffisant sans P&L variance favorable : path-dependance élevée

---

## 6. Conclusion

iter_10 peut être sauvable comme stratégie propfirm sprint via sizing scaling. Le sweet spot est 5 MNQ avec P(pass in 30d)=38.4%, au-dessus du gate 25%. Cependant, le P(bust) correspondant doit être évalué pour vérifier si le coût en tentatives reste acceptable.

---

*Simulator: Portfolio/risk/trailing_dd_simulator.py (unmodified)*
*Generator: make_iter10_trade_generator — CRN seed=42 per sizing*
