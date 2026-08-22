# Rapport stratégie 17/109 — Doji Pattern Reversal / Counter-Trend (Filter & Exit) — *court (héritage)*

**Statut :** ❌ **DISCARD par héritage du Doji counter-trend (#16, mort 4/4, alpha négatif).** · **Source :** https://oxfordstrat.com/trading-strategies/doji-countertrend-2/ (rating **D**). · **Registre :** #17. · 2026-06-05.

## Spec & archétype (1 ligne)
**Même Doji counter-trend que #16** (setup Doji, filtre contre-tendance, **entrée STOP** au-dessus/dessous du Doji, sorties Time/Quick/ATR). Seule différence : **`Body_Index=0,05` fixe** (Doji strict) et sweep **`Trend_Index × Time_Index`** (au lieu de Body×Trend). Réutilise `s016.doji_dir` + `simulate_doji` ; `ftmo_lab` v2-gates inchangé.

## Résultats (réf. Trend=10, Time=20)
**2 550 trades · win 16,8 % · expR −0,0210 · PF 0,830 · Sharpe −0,61 · MaxDD −30,5 %.** **Grille de sensibilité 0 % positive** (toutes les cellules entre −0,010 et −0,024). Le Doji strict (Body=0,05) est même légèrement **pire** que le #16.

## Gates — `results/s017_gates.csv` (4/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | natif **−0,61** → réel **−0,94** | ❌ FAIL |
| 2 | Two-sided | long +0,0147 / short **−0,0502** | ❌ FAIL |
| 3 | DSR (N=16) | best Sharpe −0,280 ≪ 1,778 | ❌ FAIL |
| 4 | OOS | train −0,0199 → test −0,0219 | ❌ FAIL |

`edge_pos=False` → **DISCARD net.**

## Verdict
❌ **DISCARD (4/4).** Tag : *héritage Doji counter-trend — stratégie perdante (négatif partout, fill artefact, asymétrique, décayé).* Confirme le #16 sur les **deux** variantes de test : le **counter-trend Doji ne fonctionne pas** (win ~17 %, grille 100 % négative). 17ᵉ traitée, **17ᵉ DISCARD**. **Clôt le sous-cluster Doji counter-trend (#16/#17).**

## Suite
**#18/#19 = Doji – Trend** : usage **différent** (Doji dans le **sens** de la tendance, pas contre) → archétype distinct, **probablement héritage du cluster TREND (Gate 2 beta long)**, pas du Doji counter-trend. À vérifier à la lecture de la fiche.

## Repro
`cd oxfordstrat_109/code && python strat_s017_doji_reversal_exit.py` (dépend de `strat_s016_doji_reversal.py`). Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3. Moteur `ftmo_lab.py` partagé/inchangé. Code faisant foi : `code/strat_s017_doji_reversal_exit.py`.
