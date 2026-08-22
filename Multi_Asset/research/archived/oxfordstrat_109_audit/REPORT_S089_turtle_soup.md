# Rapport stratégie 89/109 — Turtle Soup (Setup & Exit 1) — *fade false-breakout (Raschke)*

**Statut :** ❌ **DISCARD (3/4)** — *fade du breakout Turtle 20j ; net perdant, ne bat pas le beta.* · **Source :** https://oxfordstrat.com/trading-strategies/turtle-soup-plus-1/ (Connors/Raschke, rating **D**). · **Registre :** #89. · 2026-06-07.

## Spec & archétype
**Turtle Soup** (fade contre le système Turtle) : setup long = nouveau plus-bas Channel_#1 (20j) dont la **clôture est ≤ l'ancien plus-bas** et l'ancien plus-bas date d'≥3 barres ; entrée : buy stop au **niveau de l'ancien breakout** → si le prix le reconquiert, la cassure a échoué → long. Short = miroir. Sorties : quick-stop + canal Channel_#2 (trailing) + ATR. Moteur `turtlesoup.simulate_turtlesoup`. Réf. Ch1=20, Ch2=10.

## Résultats (réf. Ch1=20, Ch2=10)
**1 868 trades · win 12,3 % · expR −0,0030 · PF 0,962 · Sharpe −0,07 · MaxDD −15,3 %.** (net perdant)
> **DÉLAI+1 :** natif −0,07 → open[i+1] +0,81 (**artefact inverse de fill** : le buy stop au niveau de l'ancien plus-bas se remplit au pire prix intrabar).  **TWO-SIDED :** long +0,009 / short −0,012.  **BETA :** rec 0,09 < BH 1,01.

## Gates — `results/s089_gates.csv` (3/4 FAIL, `edge_positive=False`)
Le fade de false-breakout **ne passe pas net de coûts** sur l'univers FTMO (cohérent avec False Breakout #31/#32, déjà DISCARD, qui référençaient Turtle Soup ; et avec le rating D de la source). Win rate très bas (12 %) non compensé. 89ᵉ traitée, **89ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s089_turtle_soup.py` (dépend de `turtlesoup` + `beta_bench`). `ftmo_lab.py` inchangé.
