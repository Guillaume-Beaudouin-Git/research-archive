# Rapport stratégie 45/109 — Hook Pattern Bullish (Exits) — *court (héritage)*

**Statut :** ❌ **DISCARD (2/4)** — *jambe long du Hook (#43) ; la plus propre, survit délai+1 + OOS, mais unidirectionnelle (beta) + DSR ; ne bat pas le beta.* · **Source :** https://oxfordstrat.com/trading-strategies/pattern-bull-hook/ (Toby Crabel, rating **D**). · **Registre :** #45. · 2026-06-07.

## Spec & archétype (1 ligne)
Jambe **long** du Hook : long hook (ouvre au-dessus plus-haut veille, clôture sous la clôture, range resserré) + buy stop ORB Open+Stretch. Réutilise `s043` (side='long'). Point Target=3, Time=10.

## Résultats + chiffres décisifs (réf. Target=3, Time=10)
**603 trades · win 30,7 % · expR +0,1053 · PF 1,147 · Sharpe 0,29 · MaxDD −28,7 %.**

> **DÉLAI+1 :** natif +0,29 → réel **+0,06** (PASS — survit, mais le fill porte beaucoup).
> **OOS :** train +0,091 → test **+0,127** ✅ (s'améliore récemment).  **BETA-MATCHED :** rec +0,53 vs BH +1,06 → ne bat pas le beta.

## Gates — `results/s045_gates.csv` (2/4 FAIL)
Délai+1 ✅ + OOS ✅ — mais **FAIL Two-sided** (unidirectionnel = beta long par construction) + **DSR** (0,49<1,52). C'est la **meilleure jambe du Hook** (long, OOS positif récent) mais elle reste **du beta long** (ne bat pas le buy&hold) et non significative (DSR). **Cluster Hook {#43,#44,#45} : 3/3 DISCARD.** 45ᵉ traitée, **45ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s045_hook_bull.py` (dépend de s043). `ftmo_lab.py` inchangé.
