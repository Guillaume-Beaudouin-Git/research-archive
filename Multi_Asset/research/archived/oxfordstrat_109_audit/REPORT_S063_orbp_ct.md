# Rapport stratégie 63/109 — ORBP Counter-Trend (Filter & Exit) — *court (héritage ORB)*

**Statut :** ❌ **DISCARD (2/4)** — *ORB côté contre-tendance ; artefact de fill + beta long déguisé.* · **Source :** https://oxfordstrat.com/trading-strategies/orbp-countertrend/ (Crabel, rating **D**). · **Registre :** #63. · 2026-06-07.

## Spec & archétype
Entrée **ORB-stop** restreinte au côté **contre-tendance** : mode baissier `Close[t] < Close[t−Trend_Index]` → **long only** (buy stop Open+Stretch) ; mode haussier `Close[t] > Close[t−Trend_Index]` → **short only** (sell stop Open−Stretch). Stretch = SMA(min(H−O,O−L),10)×2. Sortie : Time_Index + stop ATR×6. Côté calculé sur barre t, trade sur t+1 (zéro look-ahead). Réutilise `orb_filtered.simulate_orb_filtered`. Réf. Trend_Index=20, Time=10.

## Résultats + chiffres décisifs (réf. Trend_Index=20, Time=10)
**10 046 trades · win 50,7 % · expR +0,0097 · PF 1,059 · Sharpe 0,43 · MaxDD −38,8 %.**

> **DÉLAI+1 :** +0,43 → **−0,12** (inversion = **artefact de fill**).  **TWO-SIDED :** long +0,047 / short −0,020 → **beta long déguisé**.  **BETA-MATCHED :** rec **−0,10** < BH 1,01 → ne bat pas le beta.  DSR ✅ / OOS ✅ mais non décisifs.

## Gates — `results/s063_gates.csv` (2/4 FAIL)
Le filtre **contre-tendance n'ajoute rien** : l'entrée reste un stop intrabar (artefact L26) et le edge résiduel est du beta long. Fader le mouvement de Trend_Index jours ne crée pas de réversion exploitable. 63ᵉ traitée, **63ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s063_orbp_ct.py` (dépend de `orb_filtered` + `beta_bench`). `ftmo_lab.py` inchangé.
