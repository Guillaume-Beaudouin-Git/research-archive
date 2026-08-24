# mc_time_to_pass — Strategy C iter_10 / Tradeify Select $25K

*Generated: 2026-05-26 | N=20,000 | seed=42 | 2 MNQ | eval_DD=$1,000 | target=$1,500*

---

## 1. Distribution temps-pour-passer (toutes fenêtres)

| Time cap | P(pass) | P(bust) | P(unfinished) | E[days|pass] | p25 | p50 | p75 | p95 |
|----------|---------|---------|---------------|--------------|-----|-----|-----|-----|
| Cap (réf: 180j) | 62.8% | 34.1% | 3.1% | 72.7 | 42 | 66 | 97 | 148 |
| 5j | 0.0% | 0.0% | 100.0% | 5.0 | 5 | 5 | 5 | 5 |
| 7j | 0.1% | 0.0% | 99.9% | 6.5 | 6 | 7 | 7 | 7 |
| 14j | 1.0% | 0.0% | 99.0% | 11.5 | 10 | 12 | 13 | 14 |
| 21j | 3.4% | 0.5% | 96.1% | 16.4 | 14 | 17 | 20 | 21 |
| 30j | 8.0% | 3.2% | 88.9% | 22.0 | 18 | 23 | 27 | 30 |
| 60j | 27.8% | 15.7% | 56.5% | 38.7 | 29 | 39 | 50 | 58 |
| 90j | 44.3% | 24.8% | 30.8% | 52.0 | 35 | 52 | 69 | 85 |
| 180j | 62.8% | 34.1% | 3.1% | 72.7 | 42 | 66 | 97 | 148 |

*P(pass) = atteindre +$1,500 AVANT eod_dd ≥ $1,000 dans la fenêtre. P(bust) = eod_dd ≥ $1,000 avant cible. P(unfinished) = ni l'un ni l'autre dans la fenêtre.*

---

## 2. Interprétation sprint vs marathon

**Cadence**: iter_10 est un **MARATHON** (médiane = 66j pour les runs qui passent).

- P(pass ≤ 7j)  = **0.1%** → 0 runs sur 1,000 passent en une semaine
- P(pass ≤ 14j) = **1.0%** → probabilité d'un challenge de 2 semaines
- P(pass ≤ 30j) = **8.0%** → probabilité d'un challenge mensuel
- P(pass ≤ 180j) = **62.8%** → référence sans cap temporel

La stratégie tire sa probabilité de succès essentiellement sur la longue fenêtre (60–180j).
Les quantiles p25=42j / p50=66j / p75=97j / p95=148j
confirment que la moitié des réussites prend plus de 66 jours.

---

## 3. Métrique-clé : P(pass in 30 jours) = 8.0%

**Gate : P(pass in 30d) ≥ 25% pour être viable sur propfirm sprint.**

→ **NON VIABLE pour sprint ≤30j (P=8.0% < gate 25%)**

Comparaison par rapport au gate :
- P(pass in 30d) = 8.0%  |  Gate = 25%
- Ratio = 0.32× le seuil

---

## 4. Conclusion

iter_10 sur Tradeify Select $25K est fondamentalement une stratégie de **longue durée**.

La structure de distribution montre que ~89% des tentatives sont encore en cours à 30 jours
(ni passées ni bustées), ce qui signifie que le résultat reste ouvert — ce ne sont pas des défaites,
mais des runners qui ont besoin de plus de temps.

**Recommandation** : Tradeify Select $25K sans time limit est le bon véhicule pour iter_10.
Si un propfirm impose une limite stricte de 30 jours, iter_10 n'est pas le bon candidat
(P(pass in 30d) = 8.0% est à 0.32× du seuil de 25% — il faudrait ~3× plus de fréquence
de trades ou un sizing hors contrainte DD $1,000 pour atteindre ce gate).

---

*Simulator: Portfolio/risk/trailing_dd_simulator.py (unmodified)*
*Generator: make_iter10_trade_generator(n_mnq=2, seed=42) — trade-based, not Gaussian*
*Config: PropfirmConfig() — Tradeify Select Flex $25K canonical*
