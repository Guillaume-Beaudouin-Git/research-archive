# Double 7 (Connors) — Réplication & backtest institutionnel

Réplication de la stratégie *Double 7* de Larry Connors (testée dans la vidéo
YouTube `4TTb0f9fk1U` d'Unbiased Trading) et évaluation indépendante sur
2005–2026 : réplication à un trade près, verdict hors échantillon, robustesse
(paramètres, coûts, source de données, convention d'exécution) et trois axes
d'amélioration quantifiés.

**→ Rapport complet : [`rapport_double7_connors.md`](rapport_double7_connors.md)**

## Reproduire

```bash
python3 research_grid.py    # grille de paramètres, coûts, cross-check CFD
python3 improvements.py     # axes d'amélioration
python3 figures.py          # figures du rapport
```

Dépendances : pandas, numpy, matplotlib (+ duckdb pour ré-agréger le M1).
Les chemins de données pointent vers les panels locaux du dossier parent
(`panels/`, `deep_history_utc/`) — voir `data.py`.

## Résultats clés (sleeves 7/7/200, 5 bps/side)

| Fenêtre | CAGR | Sharpe | MaxDD | WR | Trades |
|---|---|---|---|---|---|
| 2020–2026 (vidéo) | 6.9 % | 0.85 | −10.5 % | 75.7 % | 181 |
| 2005–2026 | 4.6 % | 0.60 | −17.7 % | 73.8 % | 606 |
| 2009–2026 (OOS) | 5.8 % | 0.72 | −10.6 % | 73.7 % | 509 |

t-stat Newey-West OOS : 3.6 — IC bootstrap 95 % du Sharpe : [0.35 ; 1.13].
