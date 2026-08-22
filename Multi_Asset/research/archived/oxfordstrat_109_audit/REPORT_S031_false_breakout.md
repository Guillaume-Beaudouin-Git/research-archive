# Rapport stratégie 31/109 — False Breakout (Setup & Exit 1)

**Statut :** ❌ **DISCARD net (4/4)** — *1er fade contrarian vrai ; net perdant, short-fade cassé, entrée-stop = artefact de fill.* · **Source :** https://oxfordstrat.com/trading-strategies/false-breakout-1/ (Wyckoff/Williams/Connors, rating **C**). · **Registre :** #31. · 2026-06-07.

## Spec & archétype
**Contrarian fade (« Specialists Trap »/Turtle Soup)** : un nouveau plus-bas de canal qui clôture **sous** un plus-bas antérieur (≥5 barres) puis **se retourne** → long sur le rachat (buy stop au-dessus du haut de la barre de cassure, <5 barres). Short symétrique (fausse cassure haussière). Sorties Time + Quick (extrême du washout) + ATR×6. Sweep `Channel × Time`. Naturellement **deux côtés / market-neutral**. `ftmo_lab` + `beta_bench` inchangés. Point Channel=20, Time=10.

## Résultats + chiffres décisifs (réf. Channel=20, Time=10)
**7 202 trades · win 27,2 % · expR −0,0260 · PF 0,809 · Sharpe −1,32 · MaxDD −64,0 %.** Grille **0 % positive**.

> **DÉLAI+1 :** natif −1,32 → réel −0,57 (toujours négatif) → ❌ artefact de fill intrabar (l'entrée-stop achète le spike de rachat).
> **TWO-SIDED :** long **+0,0139** (n2641) / short **−0,0491** (n4561) → le short-fade saigne.
> **BETA-MATCHED :** strat Sh rec **−1,52** vs buy&hold **+1,01** → ne bat pas le beta (et de loin).

## Gates — `results/s031_gates.csv` (4/4 FAIL, edge_pos=False → DISCARD net)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | −1,32 → −0,57 | ❌ artefact de fill |
| 2 | Two-sided | long +0,014 / short **−0,049** | ❌ short cassé |
| 3 | DSR | −0,84 ≪ 1,52 | ❌ |
| 4 | OOS | train −0,034 → test −0,018 | ❌ |

## Verdict
❌ **DISCARD net (4/4).** Le fade tel que spécifié **perd** : le short (fade des fausses cassures hautes) est franchement négatif, et l'entrée-stop sur le rachat est un artefact de fill. **Seule lueur** : le **long-fade** (acheter un washout qui se retourne) est légèrement positif (+0,014 plein / **+0,023 récent**) — un soupçon de « buy-the-washout » — mais c'est mince, unidirectionnel, et **loin de battre le beta**. À surveiller sur la variante #32 (autre sortie), sans illusion. 31ᵉ traitée, **31ᵉ DISCARD**.

## Suite
**#32 (False Breakout — Setup & Exit 2)** : même setup, sortie différente → tester si le long-fade s'assainit ; sinon clôt le cluster fade.

## Repro
`cd oxfordstrat_109/code && python strat_s031_false_breakout.py` (dépend de `beta_bench`). Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3. `ftmo_lab.py` inchangé. Code : `code/strat_s031_false_breakout.py`.
