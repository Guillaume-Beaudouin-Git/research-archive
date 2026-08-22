# Rapport stratégie 18/109 — Doji Pattern Trend (Setup & Filter) — *court (héritage)*

**Statut :** ❌ **DISCARD (4/4)** — *héritage : artefact Doji-stop (Gate 1) + biais long trend (Gate 2) ; net perdant.* · **Source :** https://oxfordstrat.com/trading-strategies/doji-trend-1/ (rating **C**). · **Registre :** #18. · 2026-06-05.

## Spec & archétype (1 ligne)
**Même Doji + entrée STOP + sorties Time/Quick/ATR que #16**, mais **filtre INVERSÉ** : Long si `Close[s] > Close[s−Trend_Index]` (Doji après une **hausse** → breakout de **continuation** en tendance) ; Short si baisse. ⇒ **usage trend-following** du Doji (≠ counter-trend #16/#17). Réutilise `s016.simulate_doji` ; `ftmo_lab` v2-gates inchangé.

## Résultats (réf. Body=0,10, Trend=10)
**4 232 trades · win 18,6 % · expR −0,0108 · PF 0,909 · Sharpe −0,39 · MaxDD −28,9 %.** **Grille 0 % positive** (toutes cellules −0,005 à −0,018). 7/30 positifs.

## Gates — `results/s018_gates.csv` (4/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | natif −0,39 → réel **−1,53** | ❌ FAIL — **artefact Doji-stop** (s'effondre) |
| 2 | Two-sided | long +0,0189 / short **−0,0495** | ❌ FAIL — biais long (trend) |
| 3 | DSR (N=20) | best Sharpe −0,167 ≪ 1,871 | ❌ FAIL |
| 4 | OOS | train −0,0078 → test −0,0134 | ❌ FAIL |

`edge_pos=False` → **DISCARD net.**

## Verdict & constat
❌ **DISCARD (4/4).** Tag : *héritage — artefact de fill Doji-stop (Gate 1) + biais long trend (Gate 2) ; net perdant.*

**Constat dual (important) :** le Doji échoue dans les **deux** sens — **counter-trend (#16/#17)** ET **trend (#18)**. Le maillon faible n'est donc **pas le filtre** (sens de la tendance) mais le **mécanisme « Doji + entrée sur stop »** lui-même : un breakout au-delà d'une **bougie d'indécision** produit un **whipsaw** (win ~18 %) et un **artefact de fill** (délai+1 s'effondre). Quelle que soit la direction du filtre, c'est perdant. 18ᵉ traitée, **18ᵉ DISCARD**.

## Suite
**#19 (Doji – Trend, Filter & Exit)** = variante du #18 (Body fixe, sweep Trend×Time) → héritage attendu (même mécanisme Doji-stop). **Clôt le cluster Doji** (#16-#19) après #19.

## Repro
`cd oxfordstrat_109/code && python strat_s018_doji_trend.py` (dépend de `strat_s016_doji_reversal.py`). Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3. Moteur `ftmo_lab.py` partagé/inchangé. Code faisant foi : `code/strat_s018_doji_trend.py`.
