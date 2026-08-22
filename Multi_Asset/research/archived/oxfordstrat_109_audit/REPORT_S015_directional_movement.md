# Rapport stratégie 15/109 — Directional Movement (Wilder DI-cross) — *court (héritage)*

**Statut :** ❌ **DISCARD par héritage du cluster trend-following.** · **Source :** https://oxfordstrat.com/trading-strategies/directional-movement/ (Wilder, rating **C**). · **Registre :** #15. · 2026-06-05.

## Spec & archétype (1 ligne)
**Trend-following** (Wilder DMI) : entrée sur **croisement +DI/−DI** confirmé par cassure du **point extrême** de la barre de croisement (stop) ; sortie sur **croisement inverse** (à l'open suivant) + stop ATR(20)×6 ; filtre **ADXR ≥ seuil** ; sweep `ADXR_Look_Back × ADXR_Threshold`. Clone du cluster trend (Donchian/Aroon/Bollinger-momentum). Sim `simulate_dmi` dédiée ; `ftmo_lab` v2-gates inchangé.

## Résultats (réf. ADXR_Look_Back=14, ADXR_Threshold=0 — base, filtre off)
**4 425 trades · win 31,3 % · expR +0,0180 · PF 1,124 · Sharpe 0,40 · MaxDD −38,0 %.**
**ADXR value-add :** colonne seuil=0 +0,022 vs « best » seuil>0 +0,080 — mais les cellules à seuil élevé sont **sparse** (LB60/T30 sparse) ; aux réglages denses, un seuil >0 **dégrade** (LB14/T20 −0,016, T30 −0,032). ⇒ **l'ADXR n'ajoute aucune valeur robuste** (confirme la fiche, qui ajoute que ce DI-cross fait *pire* que les autres modèles momentum).

## Gates — `results/s015_gates.csv` (2/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | natif +0,40 → réel **+0,18** | ✅ PASS (faible) |
| 2 | **Two-sided** | long **+0,0598** / short **−0,0337** | ❌ **FAIL — beta long** |
| 3 | DSR (N=20) | best Sharpe 0,404 ≪ 1,871 | ❌ FAIL — bruit |
| 4 | OOS | train +0,0133 → test +0,0222 | ✅ PASS |

## Verdict
❌ **DISCARD (2/4).** Tag : *héritage cluster trend — beta long déguisé (Gate 2) + bruit (DSR) ; ADXR inutile.* Le croisement DI capte de la tendance longue (Gate 1 faible + OOS OK) mais asymétrique (shorts perdent) et noyé statistiquement. 15ᵉ traitée, **15ᵉ DISCARD** (dont 2 watchlist MR). **Clôt le bloc tendance/momentum** (#1-#11, #14-#15) avant le 2ᵉ mean-reversion (Doji).

## Repro
`cd oxfordstrat_109/code && python strat_s015_directional_movement.py` (Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3). Moteur `ftmo_lab.py` partagé/inchangé. Code faisant foi : `code/strat_s015_directional_movement.py`.
