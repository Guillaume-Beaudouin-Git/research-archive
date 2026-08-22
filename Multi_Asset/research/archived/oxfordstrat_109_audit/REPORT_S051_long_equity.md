# Rapport stratégie 51/109 — Long Equity Trading System (Filter & Exit) — *court (héritage)*

**Statut :** ❌ **DISCARD (2/4)** — *momentum long-only sur indices = beta long ; "bat le beta" seulement au fill optimiste.* · **Source :** https://oxfordstrat.com/trading-strategies/long-equity-trading-system/ (Bruce Babcock, rating **C**). · **Registre :** #51. · 2026-06-07.

## Spec & archétype (1 ligne)
**Long-only** time-series momentum sur indices actions : setup = momentum 11 j accélère ; filtre Open>typical veille ; entrée buy stop à Close[i−1]+TrueRange[i−1] ; sortie au 1er open profitable + ATR×6. `ftmo_lab`+`beta_bench` inchangés. Point Look_Back=11, N=1 (indices).

## Résultats + chiffres décisifs (réf. Look_Back=11, N=1, indices)
**3 614 trades · win 92,2 % · expR +0,0151 · PF 1,290 · Sharpe 0,72 · MaxDD −22,5 %.** (win 92 % = exit 1er open profitable)

> **DÉLAI+1 :** natif +0,72 → réel **+0,13** (l'entrée-stop porte l'essentiel).  **TWO-SIDED :** long-only (short N/A) → FAIL par construction.
> **BETA-MATCHED :** rec +1,34 vs BH +0,93 « bat le beta »… **mais sur le fill optimiste** ; au délai+1 (+0,13) l'edge s'évapore. Long-only = beta.

## Gates — `results/s051_gates.csv` (2/4)
Délai+1 ✅(mais chute) + OOS ✅ ; FAIL Two-sided (long-only=beta) + DSR (1,11<1,52). Momentum long-only sur indices = **beta long**, fill-sensible. 51ᵉ traitée, **51ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s051_long_equity.py` (dépend de beta_bench). `ftmo_lab.py` inchangé.
