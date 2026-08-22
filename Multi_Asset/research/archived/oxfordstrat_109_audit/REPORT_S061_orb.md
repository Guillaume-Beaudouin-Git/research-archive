# Rapport stratégie 61/109 — Opening Range Breakout (Exits)

**Statut :** ❌ **DISCARD (1/4)** — *l'ORB canonique : edge = pur artefact de fill intrabar.* · **Source :** https://oxfordstrat.com/trading-strategies/opening-range-breakout/ (Toby Crabel, rating **D**). · **Registre :** #61. · 2026-06-07.

> 🧭 **Stratégie-pilier.** C'est l'**ORB de référence** dont dérivent GSV (#37-38), NR (#55), NR7 (#56) et les ORBP (#62-65). Le verdict ici fixe l'archétype « ORB-stop » pour toute la famille.

## Spec & archétype
**Opening Range Breakout pur**, tous les jours, aucun setup/filtre : buy stop à **[Open + Stretch]**, sell stop à **[Open − Stretch]** ; le **1er stop touché = position**, l'autre = stop de protection (les deux touchés le même jour → perdant, par spec). Stretch = SMA(Noise, 10) × 2, Noise = min(H−O, O−L) (bruit symétrique de Crabel). Sorties : Target_Index (R) + Time_Index + stop ATR×6. Réutilise `ftmo_lab.simulate_bracket` **inchangé** (setup = tous True). Point de réf. Target=3R, Time=10.

## Résultats + chiffres décisifs (réf. Target=3R, Time=10)
**13 272 trades · win 42,8 % · expR +0,0206 · PF 1,158 · Sharpe 1,17 · MaxDD −74,2 %.**

> **DÉLAI+1 :** natif (stop intrabar) Sharpe **+1,17** → fill réaliste open[i+1] **−0,65** (expR +0,021 → **−0,011**). **→ INVERSION = artefact de fill pur.**
> **TWO-SIDED :** long +0,078 / short +0,017 (les deux positifs *sur fill optimiste seulement*).
> **DSR :** 3,70 > 1,87 — mais sur la grille au **fill optimiste**, donc non probante une fois le délai+1 fatal.
> **BETA-MATCHED :** rec 1,08 < BH 1,01 ? non — full 1,17 vs 0,74 / rec 1,08 vs 1,01 → marge nulle, **ne bat pas le beta** en réaliste.

## Gates — `results/s061_gates.csv` (1/4 FAIL, décisif)

| # | Gate | Résultat | Verdict |
|---|------|----------|---------|
| 1 | Délai+1 | +1,17 → **−0,65** | ❌ **FAIL — artefact de fill intrabar** |
| 2 | Two-sided | long +0,078 / short +0,017 | ✅ PASS (fill optimiste) |
| 3 | DSR | 3,70 > 1,87 | ✅ PASS (fill optimiste) |
| 4 | OOS | +0,023 → +0,018 | ✅ PASS |

## Verdict
❌ **DISCARD.** L'ORB canonique illustre **exactement** le piège L26 : poser un stop des deux côtés de l'ouverture et se remplir **au niveau du stop intrabar** fabrique un Sharpe de 1,17 ; dès qu'on se remplit à l'**open du lendemain** (le seul fill exécutable sur données journalières), l'edge **s'inverse** (−0,65). Il ne reste rien — ni edge réaliste, ni capacité à battre le buy&hold. C'est le **gabarit de la famille ORB** : tout dérivé qui garde l'entrée stop-intrabar hérite de l'artefact (cf. #62, #63, #65) ; seul un **filtre directionnel de tendance** peut le masquer — mais en se contentant alors de capter du beta long (cf. #64). 61ᵉ traitée, **61ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s061_orb.py` (dépend de `orb_filtered.crabel_stretch` + `beta_bench`). `ftmo_lab.py` inchangé (9dea332). Code : `code/strat_s061_orb.py`.
