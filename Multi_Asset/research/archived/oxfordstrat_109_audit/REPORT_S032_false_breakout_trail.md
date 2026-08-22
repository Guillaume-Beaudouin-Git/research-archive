# Rapport stratégie 32/109 — False Breakout (Setup & Exit 2) — *court (héritage)*

**Statut :** ❌ **DISCARD net (3/4, edge_pos=False)** — *= #31 (même fade), sortie trailing ; net perdant, ne bat pas le beta.* · **Source :** https://oxfordstrat.com/trading-strategies/false-breakout-2/ (rating **C**). · **Registre :** #32. · 2026-06-07.

## Spec & archétype (1 ligne)
**Même setup+entrée fade que #31**, mais sortie = Quick + **trailing Channel_#2** + ATR×6 (pas de Time). Sweep `Channel_#1 × Channel_#2`. `ftmo_lab`+`beta_bench` inchangés. Point C1=20, C2=10.

## Résultats + chiffres décisifs (réf. C1=20, C2=10)
**5 794 trades · win 21,9 % · expR −0,0052 · PF 0,961 · Sharpe −0,15 · MaxDD −38,5 %.** Grille **0 % positive**.

> **DÉLAI+1 :** natif −0,15 → réel open[j+1] **+0,60** (expR −0,005 → +0,022) — l'entrée-stop *nuit* (le fill réaliste est bien meilleur), comme #31.
> **TWO-SIDED :** long **+0,0654** (n2077) / short **−0,0447** (n3717) — long-fade le plus positif du cluster, mais short cassé.
> **BETA-MATCHED :** strat Sh rec **+0,09** vs buy&hold **+1,01** → **ne bat pas le beta**.

## Gates — `results/s032_gates.csv` (edge_pos=False → DISCARD net)
Délai+1 PASS (réel>0) mais **natif négatif** → pas d'edge positif ; Two-sided FAIL (short cassé) ; DSR FAIL ; OOS flip. **DISCARD net.**

## Verdict
❌ **DISCARD net.** La sortie trailing améliore le **long-fade** (+0,065, et fill réaliste Sharpe +0,60) — le « buy-the-washout » a une vraie pulsation — **mais** : (a) la stratégie spécifiée (deux côtés, fill stop) est **net négative** (le short-fade saigne), (b) elle **ne bat pas le beta** (rec +0,09 ≪ buy&hold +1,01). Conformément à la leçon S012, *un long-fade positif qui ne bat pas le beta n'est pas un edge*. **Cluster False Breakout {#31,#32} : 2/2 DISCARD.** Le fade de cassure ne produit pas d'alpha exploitable sur cet univers. 32ᵉ traitée, **32ᵉ DISCARD**.

## Suite
**#33 (FRAMA — Fractal Adaptive MA)** : MA adaptative (type KAMA) → probable trend/beta.

## Repro
`cd oxfordstrat_109/code && python strat_s032_false_breakout_trail.py` (dépend de `beta_bench`). `ftmo_lab.py` inchangé. Code : `code/strat_s032_false_breakout_trail.py`.
