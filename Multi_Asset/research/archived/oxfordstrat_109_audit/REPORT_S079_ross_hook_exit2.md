# Rapport stratégie 79/109 — Ross Hook with Filter (Filter & Exit 2) — *cluster #76, rating B*

**Statut :** 🟢 **CANDIDAT KEEP (= #76)** — *2ᵉ étude de sortie (holding plus long) ; edge confirmé, même renforcé.* · **Source :** https://oxfordstrat.com/trading-strategies/ross-hook-filter-3/ (Joe Ross, rating **B**). · **Registre :** #79. · 2026-06-07.

## Spec & résultats
= #78 avec sortie temporelle plus longue (Time=20). **5 213 trades · win 36,2 % · expR +0,067 · PF 1,481 · Sharpe 1,87 · délai+1 +1,87→+1,59 · two-sided long +0,100/short +0,025 · bat le beta.** **Gates 0/4 = KEEP.** Le holding plus long augmente l'expR (cohérent avec une continuation de tendance : laisser courir les gagnants).

## Verdict
🟢 **CANDIDAT KEEP** — confirme la **robustesse aux variantes de sortie** (rating B). Cluster Ross Hook {#76,#77,#78,#79} = **4/4 candidats KEEP** (gates 0/4, bat le beta), audit MTM/tendance OK (cf. `REPORT_S076`). Deep-dive groupé. 79ᵉ traitée.

## Repro
`cd oxfordstrat_109/code && python strat_s079_ross_hook_exit2.py`. `ftmo_lab.py` inchangé.
