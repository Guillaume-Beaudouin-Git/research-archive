# Rapport stratégie 38/109 — Greatest Swing Value - Trend (Filter & Exit) — *court (héritage)*

**Statut :** ❌ **DISCARD (2/4)** — *GSV ORB-stop + filtre tendance = beta long ; ne bat pas le beta.* · **Source :** https://oxfordstrat.com/trading-strategies/greatest-swing-value-trend/ (L. Williams, rating **C**). · **Registre :** #38. · 2026-06-07.

## Spec & archétype (1 ligne)
Entrée **GSV ORB-stop** (Open ± GSV) rendue **directionnelle** par un filtre de tendance (`Close[i−1] > Close[i−Trend_Index]` = long uniquement en hausse). Sortie Time + ATR×6. Sweep `Trend_Index × Time`. Réutilise la GSV de s037 ; `ftmo_lab`+`beta_bench` inchangés. Point Trend=10, Time=10.

## Résultats + chiffres décisifs (réf. Trend=10, Time=10)
**9 763 trades · win 51,4 % · expR +0,0154 · PF 1,096 · Sharpe 0,66 · MaxDD −53,3 %.**

> **DÉLAI+1 :** +0,66 → +0,10 (PASS faible — l'entrée-stop perd l'essentiel au fill réaliste).
> **TWO-SIDED :** long **+0,043** / short **−0,018** → ❌ beta long.  **BETA-MATCHED :** rec +0,73 vs BH +1,01 → ne bat pas le beta.

## Gates — `results/s038_gates.csv` (2/4)
Délai+1 ✅(faible) + OOS ✅ ; FAIL Gate2 (beta long) + DSR (0,66 ≪ 1,52). **DISCARD.** Le filtre de tendance transforme la GSV en simple beta long (et l'entrée-stop reste fragile au fill). **Cluster GSV {#37, #38} : 2/2 DISCARD.** 38ᵉ traitée, **38ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s038_gsv_trend.py` (dépend de s037 + beta_bench). `ftmo_lab.py` inchangé.
