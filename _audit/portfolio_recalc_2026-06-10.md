# Recalcul portefeuille A+B / A+B+C — 2026-06-10

**Déclencheur :** caveat CLAUDE.md 2026-06-10 — le « Sharpe 2.24, MaxDD -1.0% (ERC 10/68/22) »
était calculé avec C = iter_05 (SR série 1.32, étiqueté 1.52) ; re-baseline 2026-06-07 :
SR_C = 0.41 full / 0.69 fenêtre Kaggle, et C n'a plus de véhicule propfirm (Tradeify annulé).

## 1. Calcul d'origine (retrouvé)

`Portfolio/integration/initial_summary.md` (2026-05-21) + `initial_analysis.py` :
ERC sur SÉRIES journalières (A backtest TSMOM, B backtest carry **SR série 9.64**, C iter_05),
overlap 2023-11-18→2025-06-18 (579 j), corr full-sample ρ_AB=0.0388, ρ_AC=0.0149, ρ_BC=0.0528
→ poids capital 10/68/22, **Sharpe HAC 2.238, MaxDD -1.0%**.
Vice rétrospectif : la série B backtest porte SR 9.64 — exactement ce que **L14** déclare
inadmissible (proxy 2.0 obligatoire pour toute sim de portefeuille). L'annotation CLAUDE.md
« at SR_B=2.0 » ne correspondait pas au calcul réellement exécuté.

## 2. Recalcul 2026-06-10 — analytique, L14-compatible (référentiel retenu)

Inputs : SR_A=1.33 (OOS), SR_B=2.0 (proxy L14), matrice de corr existante (§1, full-sample),
unités vol-normalisées, ERC exact (solveur itératif sur la matrice de corr ; avec ces corr
quasi-nulles, poids de risque ≈ 1/3 : 0.336/0.330/0.334 ; A+B : 50/50).
SR_port = w·SR / √(wᵀΡw).

| Configuration | SR portefeuille |
|---|---:|
| **(i) A+B seul** | **2.310** |
| (ii) A+B+C, SR_C=0.41 (full Databento) | 2.082 |
| (ii) A+B+C, SR_C=0.55 (mid) | 2.160 |
| (ii) A+B+C, SR_C=0.69 (fenêtre Kaggle) | 2.238 |
| contrôle : SR_C=1.52 (ancien chiffre) | 2.702 |

Lectures :
- **C est dilutif sur tout l'intervalle re-baseliné** : 2.08–2.24 < 2.31 (A+B seul).
  Breakeven ERC : le book n'absorbe C que si **SR_C > ≈0.81**.
- La valeur 2.238 @ SR_C=0.69 ≈ l'ancien 2.238 est une **coïncidence numérique fortuite**
  (méthodologies différentes) — preuve : le même cadre à SR_C=1.52 donne 2.70, pas 2.24.
- Gate D : la référence devient A+B → **Sharpe(book+D) > 1.10 × 2.31 = 2.54**.

## 3. Volet séries (transparence — non retenu comme référence)

- A∩B jours non-nuls (94 obs) : ERC capital 26/74, SR HAC **5.85** — inadmissible L14
  (dominé par B backtest 9.64).
- Méthodo d'origine (B zéro-fillée sur 579 j) : le solveur `Portfolio/risk/sizing.py::
  equal_risk_contribution` **dégénère** (w = A:1.0 / B:0.0) sur la série B sparse (92 % de
  zéros) → le « portefeuille » est A seule (SR 1.32, MaxDD -6.94%). Bug de robustesse connu
  par ce doc ; non corrigé (aucun consommateur live ; à corriger si l'ERC série repasse en prod —
  avec test, per code style).
- Conséquence : **pas de MaxDD book honnête disponible** tant que B n'a pas ≥60 j live mainnet.
  Le « MaxDD -1.0% » legacy meurt avec sa méthodo.

## 4. Reproduction

```python
# ERC analytique (cf. session 2026-06-10)
import numpy as np
def erc(C, it=10000):
    w = np.ones(len(C))/len(C)
    for _ in range(it):
        rc = w*(C@w); w2 = np.clip(w*(rc.mean()/rc),1e-9,None); w2/=w2.sum()
        if np.abs(w2-w).max()<1e-12: break
        w = w2
    return w
C3 = np.array([[1,.0388,.0149],[.0388,1,.0528],[.0149,.0528,1]])
w = erc(C3); sr = np.array([1.33,2.0,0.69])
print(w@sr/np.sqrt(w@C3@w))   # 2.238
```
Séries : `Portfolio/integration/load_returns.py` (A yfinance backtest, B data/metadata/
delta_neutral_backtest.csv) + `initial_analysis.py::sharpe_hac/maxdd` — imports sans modification.
