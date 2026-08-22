# Rapport stratégie 88/109 — The Livermore System Part 2 (Filters) — *court (variante #87)*

**Statut :** ❌ **DISCARD (2/4)** — *2ᵉ étude de filtres ; même momentum-beta que #87.* · **Source :** https://oxfordstrat.com/trading-strategies/livermore-system-2/ (Livermore/Kaufman, rating **C**). · **Registre :** #88. · 2026-06-07.

## Spec & résultats
Variante de filtre du système Livermore (proxy momentum Donchian-régime, N=60). **1 346 trades · expR +0,072 · Sharpe 0,23 · MaxDD −41,0 %.** DÉLAI+1 +0,23→+0,22. **TWO-SIDED : long +0,378 / short −0,250** → beta long (le short perd). DSR bruit. BETA rec 0,35 < BH 1,01. **Gates 2/4 FAIL.** Même conclusion que #87 : momentum = beta long, ne bat pas le buy&hold. Cluster Livermore {#87,#88} = 2/2 DISCARD. 88ᵉ traitée, **88ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s088_livermore2.py`. `ftmo_lab.py` inchangé.
