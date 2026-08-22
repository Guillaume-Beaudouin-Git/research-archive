# Rapport stratégie 14/109 — Bollinger Bands Momentum Model (Setup) — *court (héritage)*

**Statut :** ❌ **DISCARD par héritage du cluster trend-following.** · **Source :** https://oxfordstrat.com/trading-strategies/bollinger-band/ (J. Bollinger, rating **C**). · **Registre :** #14. · 2026-06-05.

> Gates exécutés pour de vrai (pas un copier-coller), mais rapport court car mort identique au cluster trend (Gate 2 beta long).

## Spec & archétype (1 ligne)
**Trend-following** (la fiche le dit) : **breakout de bande** — Long si `Close[i−1] > Upper_Band`, Short si `Close[i−1] < Lower_Band` ; **entrée market-on-open** ; sortie *Trend Exit* (retour `Close < MA` long / `> MA` short, à l'open suivant) + stop ATR(20)×6. Sweep `MA_Length × St_Dev`. Archétype = entrée-open (pas d'artefact intrabar), **clone du cluster trend** (Donchian/Aroon) avec des bandes Bollinger au lieu de canaux. Sim `simulate_bandmom` dédiée ; `ftmo_lab` v2-gates réutilisé tel quel.

## Résultats (réf. MA_Length=100, St_Dev=2 — région recommandée par la fiche : MA>60, St_Dev>0)
**1 171 trades · win 32,4 % · expR +0,0726 · PF 1,195 · Sharpe 0,33 · MaxDD −39,9 %.** 16/30 positifs.
**Par instrument :** XAUUSD (+1,16), ETHUSD (+0,86), BTCUSD (+0,67), USDJPY (+0,50) en tête ; FX en bas (EURUSD −0,21, NZDUSD −0,35). **Signature trend classique** (commodities/crypto portent, FX perd) — inverse du MR #12.

## Gates — `results/s014_gates.csv` (2/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | natif +0,33 → réel +0,34 | ✅ PASS (entrée open) |
| 2 | **Two-sided** | long **+0,2982** / short **−0,1803** | ❌ **FAIL — beta long** (shorts saignent) |
| 3 | DSR (N=20) | best Sharpe 0,594 ≪ 1,871 | ❌ FAIL — bruit |
| 4 | OOS | train +0,1240 → test +0,0315 | ✅ PASS |

Cellule favorable (MA200/SD3) : expR +0,34 mais two-sided **long +0,92 / short −0,26** → beta long extrême.

## Verdict
❌ **DISCARD (2/4).** Tag : *héritage cluster trend-following — beta long déguisé (Gate 2) + bruit (DSR).* Breakout de bande = momentum long sur un univers haussier (crypto/métaux portent, shorts perdent). Gate 1 OK et OOS OK (vrai signal de tendance), mais asymétrique (beta) et statistiquement noyé — même profil que la #6/#9/#11. 14ᵉ traitée, **14ᵉ DISCARD** (dont 2 watchlist MR).

## Repro
`cd oxfordstrat_109/code && python strat_s014_bollinger_momentum.py` (Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3). Moteur `ftmo_lab.py` partagé/inchangé. Code faisant foi : `code/strat_s014_bollinger_momentum.py`.
