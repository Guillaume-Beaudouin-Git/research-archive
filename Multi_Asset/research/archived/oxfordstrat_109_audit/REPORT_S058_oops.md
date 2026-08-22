# Rapport stratégie 58/109 — Oops Pattern (Exits) — *gap-failure fade*

**Statut :** ❌ **DISCARD (2/4)** — *gap-fade two-sided ; long-dominé, ne bat pas le beta. MAIS la jambe long (#60) ressort fort.* · **Source :** https://oxfordstrat.com/trading-strategies/oops-pattern/ (Larry Williams, rating **D**). · **Registre :** #58. · 2026-06-07.

## Spec & archétype
**Gap-failure fade** (Williams) : long si Open<Low veille (gap down) → buy stop à Low[veille] (reprise) ; short si Open>High veille → sell stop à High[veille]. Sorties Time + stop ATR×ATR_Index. `ftmo_lab`+`beta_bench`. Point ATR_Index=3, Time=10.

## Résultats + chiffres décisifs (réf. ATR_Index=3, Time=10)
**5 704 trades · win 49,8 % · expR +0,0232 · PF 1,145 · Sharpe 0,79 · MaxDD −49,3 %.**

> **DÉLAI+1 :** +0,79 → +0,58 (PASS — reclaim-stop à un niveau réel, pas un artefact).  **TWO-SIDED :** long **+0,061** / short **−0,006** → asymétrique (le long porte tout).  **BETA-MATCHED :** rec 0,74 < BH 1,01.

## Gates — `results/s058_gates.csv` (2/4)
Délai+1 ✅ + OOS ✅ ; FAIL Gate2 (short ne marche pas) + DSR (1,10<1,52). Le **gap-down-fade (long) marche, le gap-up-fade (short) non** → la version bilatérale est diluée par le short. **→ voir #60 (jambe long isolée), qui bat le beta.** 58ᵉ traitée, **58ᵉ DISCARD** (mais cf. #60).

## Repro
`cd oxfordstrat_109/code && python strat_s058_oops.py` (dépend de beta_bench). `ftmo_lab.py` inchangé.
