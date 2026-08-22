# Rapport stratégie 82/109 — Smash Day Type A (Exits) — *court (variante #81)*

**Statut :** ❌ **DISCARD (3/4)** — *même setup que #81, étude de sortie (Time=20) ; toujours pas d'edge.* · **Source :** https://oxfordstrat.com/trading-strategies/smash-day-pattern-a2/ (Williams, rating **C**). · **Registre :** #82. · 2026-06-07.

## Résultats (réf. Trend=20, Time=20)
**1 025 trades · win 15,4 % · expR −0,0079 · Sharpe −0,12** (net perdant). DÉLAI+1 −0,12→+0,26 (fill optimiste pire que réaliste). TWO-SIDED long +0,019/short −0,042. BETA rec −0,06 < BH 1,01. **Gates 3/4 FAIL (`edge_positive=False`).** Allonger la détention ne sauve pas le Type A. 82ᵉ traitée, **82ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s082_smashday_a_exits.py`. `ftmo_lab.py` inchangé.
