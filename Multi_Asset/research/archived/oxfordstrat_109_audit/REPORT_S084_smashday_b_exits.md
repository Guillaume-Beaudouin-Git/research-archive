# Rapport stratégie 84/109 — Smash Day Type B (Exits) — *court (variante #83, rating B)*

**Statut :** ❌ **DISCARD (3/4)** — *même setup que #83, étude de sortie (Time=20) ; rating B non confirmé.* · **Source :** https://oxfordstrat.com/trading-strategies/smash-day-pattern-b2/ (Williams, rating **B**). · **Registre :** #84. · 2026-06-07.

## Résultats (réf. Trend=20, Time=20)
**5 816 trades · win 18,8 % · expR −0,0012 · Sharpe −0,04** (net plat/négatif). DÉLAI+1 −0,04→+0,83 (artefact inverse de fill). TWO-SIDED long +0,019/short −0,025. BETA rec −0,00 < BH 1,01. **Gates 3/4 FAIL (`edge_positive=False`).** Comme #83 : pas d'edge robuste, le rating B de la source ne se traduit pas. Cluster Smash Day Type B {#83,#84} = 2/2 DISCARD. 84ᵉ traitée, **84ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s084_smashday_b_exits.py`. `ftmo_lab.py` inchangé.
