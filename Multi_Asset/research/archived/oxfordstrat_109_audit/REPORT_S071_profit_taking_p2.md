# Rapport stratégie 71/109 — Profit-Taking: Kaufman (Test Period 2) — *court (jumeau de #70)*

**Statut :** ❌ **DISCARD (= #70)** — *strictement la même stratégie que #70, seule la période de test diffère (2000-2011 vs 1980-2011).* · **Source :** https://oxfordstrat.com/trading-strategies/profit-taking-2/ (Perry Kaufman, rating **N/A**). · **Registre :** #71. · 2026-06-07.

## Note
La fiche #71 est **identique** à #70 (entrée EMA-turn @close, sortie cible-% + stop ATR×6, même grille EMA_Length × Target_Exit) ; seule la fenêtre de test change (2000-2011). Sur notre store FTMO (indices depuis 2000, commodités 2005+), la période est **déjà couverte** par le run #70 → résultat identique.

**Verdict réutilisé (cf. `REPORT_S070_profit_taking.md`) :** DISCARD 4/4. Le système EMA-turn est un trend-MA **net perdant** (Sharpe −0,71, `edge_positive=False`), et l'étude reproduit le résultat de la fiche **qui contredit Kaufman (1995)** : les cibles de profit **dégradent** le résultat (expR sans cible −0,092 > cible 20 % −0,115). Conclusion identique sur la sous-période 2000-2011. 71ᵉ traitée, **71ᵉ DISCARD**.

## Repro
Voir `code/strat_s070_profit_taking.py` (stratégie identique ; restreindre les dates d'entrée à 2000-2011 pour la sous-période exacte). `ftmo_lab.py` inchangé.
