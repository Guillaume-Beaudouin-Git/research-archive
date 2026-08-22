# Rapport stratégie 37/109 — Greatest Swing Value (Exits) — *court (héritage ORB-stop)*

**Statut :** ❌ **DISCARD (1/4)** — *ORB-stop pur : artefact de fill intrabar (Gate 1), comme S001/S002.* · **Source :** https://oxfordstrat.com/trading-strategies/greatest-swing-value/ (Larry Williams, rating **D**). · **Registre :** #37. · 2026-06-07.

> ℹ️ Ce travail avait été brouillonné par erreur comme « #20 » lors de la correction de numérotation, puis **parké** ; **#37 est son vrai créneau** (`_parked_drafts/` superseded). Le verdict est inchangé.

## Spec & archétype
**ORB-stop pur, tous les jours** (pas de filtre NR) : buy stop `Open + GSV` / sell stop `Open − GSV` ; GSV = SMA(noise directionnel, 10) × 2. Sorties Target_Index × Time_Index + ATR×6. La fiche la pose en « benchmark GSV vs ORB ». Réutilise `ftmo_lab.simulate_bracket` tel quel (setup = toujours vrai, stretch = GSV). Point Target=3R, Time=10.

## Résultats + chiffres décisifs (réf. Target=3R, Time=10)
**12 548 trades · win 44,6 % · expR +0,0193 · PF 1,140 · Sharpe 1,03 · MaxDD −70,7 %** (fill optimiste).

> **DÉLAI+1 (DÉCISIF) :** natif(stop) Sharpe **+1,03** → fill réaliste open[i+1] **−0,47** (expR +0,019 → −0,009). **→ inversion = artefact de fill intrabar.**
> **TWO-SIDED :** long +0,072 / short +0,010 (les deux positifs). **BETA-MATCHED :** rec +1,08 vs BH +1,01 (mais l'edge entier EST le fill → caduc).

## Gates — `results/s037_gates.csv` (1/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | **Délai+1** | **+1,03 → −0,47** | ❌ **artefact de fill intrabar** |
| 2 | Two-sided | long +0,072 / short +0,010 | ✅ PASS |
| 3 | DSR | 3,15 > 1,87 | ✅ PASS |
| 4 | OOS | +0,019 → +0,020 | ✅ PASS |

## Verdict
❌ **DISCARD (1/4).** Démonstration la plus pure du piège ORB-stop : sous le fill optimiste (au niveau du stop) le GSV passe **3 gates sur 4** (two-sided, DSR, OOS) — mais **tout l'edge est l'exécution au niveau exact du stop intrabar** ; au fill réaliste, Sharpe **+1,03 → −0,47**. MaxDD −71 %. Identique à S001/S002. **Cluster ORB-stop {#1, #2, #37} : 3/3 DISCARD (Gate 1).** 37ᵉ traitée, **37ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s037_gsv.py` (dépend de `beta_bench`). `ftmo_lab.py` inchangé. Code : `code/strat_s037_gsv.py`.
