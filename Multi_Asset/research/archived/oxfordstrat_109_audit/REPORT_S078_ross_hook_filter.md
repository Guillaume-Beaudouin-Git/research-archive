# Rapport stratégie 78/109 — Ross Hook with Filter (Filter & Exit 1) — *cluster #76, rating B*

**Statut :** 🟢 **CANDIDAT KEEP (= #76)** — *Ross Hook + filtre profondeur + sortie temporelle ; rating B confirmé côté gates.* · **Source :** https://oxfordstrat.com/trading-strategies/ross-hook-filter-2/ (Joe Ross, rating **B**). · **Registre :** #78. · 2026-06-07.

## Spec & résultats
= #76 + filtre `hook ≤ Max_Hook(ratio) × jambe` (Min_Setup=10), balayage ratio × Time. Réf. ratio=1, Time=10 : **6 462 trades · win 40,9 % · expR +0,047 · Sharpe 1,76 · délai+1 +1,76→+1,68 · two-sided long +0,067/short +0,021 · bat le beta.** **Gates 0/4 = KEEP.** La grille ratio×Time est positive partout (cf. `results/s078_sensitivity_expectancy.csv`).

## Verdict
🟢 **CANDIDAT KEEP** — c'est la version **notée B** par la source, et elle confirme l'edge Ross Hook (mêmes chiffres que #76/#77 à ce point de réf.). Audit MTM/tendance complet : voir `REPORT_S076_ross_hook.md`. Deep-dive groupé. 78ᵉ traitée.

## Repro
`cd oxfordstrat_109/code && python strat_s078_ross_hook_filter.py`. `ftmo_lab.py` inchangé.
