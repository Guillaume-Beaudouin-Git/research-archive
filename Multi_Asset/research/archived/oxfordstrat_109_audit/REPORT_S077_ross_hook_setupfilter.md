# Rapport stratégie 77/109 — Ross Hook with Filter (Setup & Filter) — *court (cluster #76)*

**Statut :** 🟢 **CANDIDAT KEEP (= #76)** — *Ross Hook + filtre de profondeur ; même edge que #76.* · **Source :** https://oxfordstrat.com/trading-strategies/ross-hook-filter-1/ (Joe Ross, rating **C**). · **Registre :** #77. · 2026-06-07.

## Spec & résultats
= #76 + filtre de profondeur du hook (depth ≤ ratio × jambe), balayage Min_Setup × ratio. Le filtre (ratio=1) est permissif → résultats quasi identiques à #76 : **6 462 trades · win 40,9 % · expR +0,047 · Sharpe 1,76 · délai+1 +1,76→+1,68 · two-sided long +0,067/short +0,021 · bat le beta.** **Gates 0/4 = KEEP.**

## Verdict
🟢 **CANDIDAT KEEP, même archétype que #76.** Le filtre de profondeur ne dégrade pas l'edge (confirme la robustesse). Voir l'audit MTM/tendance complet dans `REPORT_S076_ross_hook.md` (β≈0, alpha t_NW 5,4 vs marché+TSMOM, stable récent). Deep-dive groupé avec #76. 77ᵉ traitée.

## Repro
`cd oxfordstrat_109/code && python strat_s077_ross_hook_setupfilter.py`. `ftmo_lab.py` inchangé.
