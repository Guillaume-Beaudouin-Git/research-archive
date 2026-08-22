# Rapport stratégie 64/109 — ORBP with Momentum Filter (Filter & Exit)

**Statut :** ❌ **DISCARD (1/4)** — *survit au fill ET à la DSR ET à l'OOS, mais c'est du beta long déguisé : ne bat pas le buy&hold.* · **Source :** https://oxfordstrat.com/trading-strategies/orbp-trend/ (Crabel, rating **C**). · **Registre :** #64. · 2026-06-07.

> 🔎 **Cas instructif.** Premier ORB de la famille à **réparer l'artefact de fill** (le filtre tendance survit au délai+1). C'est précisément le **5ᵉ test (beta-apparié)** — pas les 4 gates — qui le démasque.

## Spec & archétype
Entrée **ORB-stop** restreinte au côté **tendance (momentum)** : mode haussier `Close[t] > Close[t−(Look_Back−1)]` → **long only** ; mode baissier → **short only**. Stretch = SMA(min(H−O,O−L),10)×1. Sortie : Time_Index + stop ATR×6. Côté sur t, trade t+1 (no look-ahead). `orb_filtered.simulate_orb_filtered`. Réf. Look_Back=50, Time=10.

## Résultats + chiffres décisifs (réf. Look_Back=50, Time=10)
**10 429 trades · win 51,4 % · expR +0,0179 · PF 1,112 · Sharpe 0,80 · MaxDD −61,1 %.**

> **DÉLAI+1 :** +0,80 → **+0,30** (**survit** — le filtre tendance aligne l'entrée avec la dérive, donc le fill open-suivant reste favorable).
> **DSR :** 2,07 > 1,78 → **PASS**.  **OOS :** +0,018 → +0,018 → **PASS** (stable).
> **TWO-SIDED :** long **+0,043** / short **−0,016** → **asymétrique = beta long**.
> **BETA-MATCHED :** full 0,80 vs 0,74 / rec **0,82 < BH 1,01** → **ne bat PAS le beta**.

## Gates — `results/s064_gates.csv` (1/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|------|----------|---------|
| 1 | Délai+1 | +0,80 → **+0,30** | ✅ PASS — fill réparé par le filtre |
| 2 | Two-sided | long +0,043 / short −0,016 | ❌ **FAIL — beta long déguisé** |
| 3 | DSR | 2,07 > 1,78 | ✅ PASS |
| 4 | OOS | +0,018 → +0,018 | ✅ PASS |
| +5 | **Beta-apparié** | rec **0,82 < 1,01** | ❌ **ne bat pas le buy&hold** |

## Verdict
❌ **DISCARD (mais le plus « propre » de la famille ORB).** Le filtre de momentum fait ce que la fiche revendique — *« le filtre de tendance améliore l'ORB »* — et il **élimine l'artefact de fill** (délai+1 reste +0,30, DSR et OOS passent). Mais l'« amélioration » consiste à **ne prendre que les ruptures dans le sens de la tendance dominante** : le short ne gagne rien (−0,016), tout vient du long, et le Sharpe récent (0,82) **reste sous le buy&hold apparié (1,01)**. Autrement dit, le filtre transforme l'ORB en **proxy de tendance long** — un beta, pas un alpha. Sans le 5ᵉ test (exposition/vol-apparié, leçon S012), on aurait pu le sur-créditer. 64ᵉ traitée, **64ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s064_orbp_trend.py` (dépend de `orb_filtered` + `beta_bench`). `ftmo_lab.py` inchangé.
