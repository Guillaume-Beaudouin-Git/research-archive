# Rapport stratégie 99/109 — Wyckoff MR (Risk-Reward) — *court (variante #98)*

**Statut :** ❌ **DISCARD (3/4)** — *étude Risk/Reward sur l'entrée Wyckoff perdante ; toujours négatif.* · **Source :** https://oxfordstrat.com/trading-strategies/richard-wyckoff-mean-reversion-2/ (rating **C**). · **Registre :** #99. · 2026-06-07.

## Résultats (réf. Risk=1, Reward=3)
**10 668 trades · win 28,5 % · expR −0,0049 · Sharpe −0,27.** BETA rec −0,20 < BH 1,01. **Gates 3/4 FAIL (`edge_positive=False`).** Faire varier le ratio risque/récompense ne sauve pas une entrée à espérance négative (cf #98). 99ᵉ traitée, **99ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s099_wyckoff_rr.py`. `ftmo_lab.py` inchangé.
