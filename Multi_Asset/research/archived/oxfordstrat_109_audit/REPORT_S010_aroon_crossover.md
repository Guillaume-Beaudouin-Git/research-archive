# Rapport stratégie 10/109 — Aroon Indicator Crossover (Setup & Exit) — *court (héritage)*

**Statut :** ❌ **DISCARD par héritage du cluster trend-following (S003-S009).** · **Source :** https://oxfordstrat.com/trading-strategies/aroon-indicator-crossover/ (rating site : **D**). · **Registre :** #10. · 2026-06-05.

> Traitée en **mode héritage** : gates exécutés pour de vrai (pas un copier-coller de verdict), mais rapport court car mort identique au cluster.

## Spec & archétype (1 ligne)
Aroon (Chande) : **Long quand AroonUp croise AU-DESSUS d'AroonDown** (short = inverse) ; **entrée market-on-open** ; sorties Time + Stop ATR(20)×6 ; sweep `Aroon_Index × Time_Index`. Archétype = entrée-open (pas d'artefact intrabar), **clone du cluster trend** mais signal = **croisement** au lieu d'un niveau. Moteur `ftmo_lab v2-gates` réutilisé tel quel ; sim = `simulate_aroon` (identique S007-S009) avec `cross_dir`. Univers/coûts/R inchangés.

## Résultats (réf. Aroon_Index=25, Time=20)
**3 148 trades · win 48,2 % · expR −0,0171 · PF 0,933 · Sharpe −0,29 · MaxDD −30,7 %.** Le crossover **whipsaw** (signal à chaque inversion AroonUp/Down) → **pire** que les versions « level » (S007-S009) : edge **négatif** sur la quasi-totalité de la grille.

## Gates constitutionnels — `results/s010_gates.csv` (4/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | opt Sharpe −0,29 → réel −0,38 | ❌ FAIL (edge déjà négatif) |
| 2 | **Two-sided** | **long +0,0461 / short −0,0770** | ❌ **FAIL — beta long** |
| 3 | DSR (N=20) | best Sharpe 0,327 ≪ 1,871 | ❌ FAIL — bruit |
| 4 | OOS | train −0,0219 → test −0,0129 | ❌ FAIL — décay |

`edge_pos = False` ⇒ **DISCARD (pas d'edge après coûts)**, et de surcroît **Gate 2 (beta long)** comme tout le cluster.

## Verdict
❌ **DISCARD.** Tag : *héritage cluster trend-following — pas d'edge (crossover whipsaw) + beta long déguisé (Gate 2) + bruit (DSR) + décay OOS.* 10ᵉ traitée, **10ᵉ DISCARD** ; clôt le sous-cluster Aroon (#7-#10).

## Repro
`cd oxfordstrat_109/code && python strat_s010_aroon_crossover.py` (Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3). Moteur `ftmo_lab.py` partagé/inchangé. Code faisant foi : `code/strat_s010_aroon_crossover.py`.
