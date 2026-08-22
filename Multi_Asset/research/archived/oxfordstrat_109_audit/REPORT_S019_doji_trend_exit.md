# Rapport stratégie 19/109 — Doji Pattern Trend (Filter & Exit) — *court (héritage)*

**Statut :** ❌ **DISCARD (4/4)** — *héritage Doji-trend (#18) ; clôt le cluster Doji.* · **Source :** https://oxfordstrat.com/trading-strategies/doji-trend-2/ (rating **C**). · **Registre :** #19. · 2026-06-05.

## Spec & archétype (1 ligne)
**Même Doji-trend que #18** (continuation breakout, filtre `Close[s]>Close[s−TI]` = long en hausse), avec **`Body_Index=0,05` fixe** et sweep **`Trend_Index × Time_Index`**. Entrée STOP au Doji, sorties Time/Quick/ATR. Réutilise `s018.doji_trend_dir` + `s016.simulate_doji` ; `ftmo_lab` v2-gates inchangé.

## Résultats (réf. Trend=10, Time=20)
**2 474 trades · win 18,6 % · expR −0,0092 · PF 0,924 · Sharpe −0,24 · MaxDD −19,2 %.** Grille **6 % positive** (1 cellule marginale, reste négatif).

## Gates — `results/s019_gates.csv` (4/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | natif −0,24 → réel **−1,32** | ❌ FAIL — artefact Doji-stop |
| 2 | Two-sided | long +0,0206 / short **−0,0497** | ❌ FAIL — biais long |
| 3 | DSR (N=16) | best Sharpe 0,056 ≪ 1,778 | ❌ FAIL |
| 4 | OOS | train −0,0051 → test −0,0126 | ❌ FAIL |

`edge_pos=False` → **DISCARD net.**

## Verdict — clôture du cluster Doji
❌ **DISCARD (4/4).** Identique au #18. **Bilan du cluster Doji (#16-#19) : 4 variantes, 4 DISCARD nets.** Le pattern Doji + entrée-stop **ne fonctionne dans aucune configuration** — ni counter-trend (#16/#17) ni trend (#18/#19), ni en variant setup ni en variant exit. Le **mécanisme commun (breakout d'une bougie d'indécision via stop)** est le maillon défaillant : whipsaw (win ~18 %) + artefact de fill (délai+1 s'effondre systématiquement). 19ᵉ traitée, **19ᵉ DISCARD**.

## Suite
Cluster Doji clos. Prochain : **#20 (Greatest Swing Value)** — un autre archétype (volatilité/breakout intraday).

## Repro
`cd oxfordstrat_109/code && python strat_s019_doji_trend_exit.py` (dépend de s016/s018). Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3. Moteur `ftmo_lab.py` partagé/inchangé. Code faisant foi : `code/strat_s019_doji_trend_exit.py`.
