# Rapport stratégie 35/109 — Gap Pattern Type A (Filter & Exit) — *le plus propre near-miss du projet*

**Statut :** ❌ **DISCARD (1/4)** — *vrai edge gap-momentum BILATÉRAL (passe délai+1 + two-sided + OOS) mais DÉCAYÉ sous le beta récent + DSR.* · **Source :** https://oxfordstrat.com/trading-strategies/gap-pattern/ (Dahlquist & Bauer, rating **B** — le meilleur du registre). · **Registre :** #35. · 2026-06-07.

## Spec & archétype
**Continuation de gap avec filtre de tendance.** Setup long = gap UP (`Low[i] > High[i−1]`) ; short = gap DOWN. Filtre : long seulement si `High[i] > UpperChannel(FLB)[i−1]` (tendance haussière). **Entrée @open** après le setup (pas de stop → pas d'artefact). Sortie Time + Pattern (stop au bord du gap) + ATR×6. Sweep `Filter_LB × Time`. `ftmo_lab`+`beta_bench` inchangés. Point Filter_LB=20, Time=10.

## Résultats + chiffres décisifs (réf. Filter_LB=20, Time=10)
**3 438 trades · win 37,3 % · expR +0,0329 · PF 1,299 · Sharpe 0,99 · MaxDD −43,3 %.** Grille **100 % positive**.

> **DÉLAI+1 :** natif +0,99 → réel **+1,11** (expR +0,033 → +0,038) → ✅ **vrai edge** (entrée@open, robuste, s'améliore même).
> **TWO-SIDED :** long **+0,0425** (n2089) / short **+0,0181** (n1349) → ✅ **les DEUX côtés positifs** = momentum gap symétrique (pas du pur beta).
> **BETA-MATCHED :** full +0,99 vs buy&hold +0,75 (bat en plein) **MAIS rec +0,30 vs buy&hold +1,02** → **ne bat PLUS le beta récemment**.

## Gates — `results/s035_gates.csv` (1/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | +0,99 → **+1,11** | ✅ PASS — vrai edge |
| 2 | Two-sided | long +0,043 / short +0,018 | ✅ **PASS — bilatéral** |
| 3 | DSR (N=9) | best Sharpe **1,389 < 1,519** | ❌ FAIL (de justesse) |
| 4 | OOS | train +0,052 → test +0,013 | ✅ PASS (positif mais décroît) |

## Verdict
❌ **DISCARD (1/4)** — *mais le candidat le plus propre rencontré.* C'est le **seul edge bilatéral non-beta** du projet à passer délai+1 **et** two-sided **et** OOS : un vrai effet de **continuation de gap** (les deux côtés gagnent, robuste au fill). **Pourquoi DISCARD quand même :** (a) il échoue la DSR (1,39 < 1,52, de peu) ; (b) **décisif, leçon S012/re-audit** : il a **décayé** — Sharpe récent **0,30**, bien **sous le buy&hold récent (1,02)**. Plein il battait le beta (0,99 vs 0,75) ; récemment, non. Un edge réel mais en fin de vie sur cet univers. Conformément à la discipline (battre le beta *récent*), **DISCARD** — pas de watchlist (récent < beta). 35ᵉ traitée, **35ᵉ DISCARD**.

> *Note :* le gap-momentum est néanmoins l'archétype le plus prometteur jusqu'ici (bilatéral, mécanisme clair). La fiche suggère de l'intégrer à une stratégie multi-pattern. À recroiser si #36+ (Gap Pattern 2, Hikkake, etc.) confirment un gap-momentum **récent** robuste.

## Repro
`cd oxfordstrat_109/code && python strat_s035_gap_pattern.py` (dépend de `beta_bench`). `ftmo_lab.py` inchangé. Code : `code/strat_s035_gap_pattern.py`.
