# Rapport stratégie 54/109 — Multiple Time Frames - Babcock (Entry) — *court (héritage trend)*

**Statut :** ❌ **DISCARD net (4/4)** — *alignement de tendance 3 échelles ; net perdant.* · **Source :** https://oxfordstrat.com/trading-strategies/multiple-time-frames-1/ (Babcock/Freeburg, rating **C**). · **Registre :** #54. · 2026-06-07.

## Spec & archétype (1 ligne)
Long si (Close>MA) ET (MA>MA[−MA_Length]) ET (Close>Close[−4×MA_Length]) — 3 horizons alignés ; entrée@open + ATR×6. Réutilise `trend_lab`. Point MA_Length=10 (Trend_Index=40).

## Résultats + chiffres décisifs (réf. MA=10)
**11 589 trades · win 34,8 % · expR −0,0017 · PF 0,983 · Sharpe −0,11 · MaxDD −26,3 %.** (net perdant)

> **DÉLAI+1 :** −0,11 → −0,18.  **TWO-SIDED :** long +0,013 / short −0,020.  **BETA-MATCHED :** rec +0,09 < BH 1,01.

## Gates — `results/s054_gates.csv` (4/4 FAIL, edge_pos=False)
L'alignement multi-échelle court (MA=10) sur-trade et perd net après coûts. DISCARD net. 54ᵉ traitée, **54ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s054_mtf.py` (dépend de trend_lab + beta_bench). `ftmo_lab.py` inchangé.
