# Rapport stratégie 44/109 — Hook Pattern Bearish (Exits) — *court (héritage)*

**Statut :** ❌ **DISCARD net (4/4)** — *jambe short du Hook (#43) ; artefact de fill.* · **Source :** https://oxfordstrat.com/trading-strategies/pattern-bear-hook/ (Toby Crabel, rating **D**). · **Registre :** #44. · 2026-06-07.

## Spec & archétype (1 ligne)
Jambe **short** du Hook : short hook (ouvre sous plus-bas veille, clôture au-dessus, range resserré) + sell stop ORB Open−Stretch. Réutilise `s043` (side='short'). Point Target=3, Time=10.

## Résultats + chiffres décisifs (réf. Target=3, Time=10)
**480 trades · win 29,2 % · expR +0,0743 · PF 1,101 · Sharpe 0,18 · MaxDD −22,8 %.**

> **DÉLAI+1 (DÉCISIF) :** natif +0,18 → réel **−0,01** (expR +0,074 → −0,006). **→ artefact de fill intrabar.**  OOS flip (+0,154→−0,030).

## Gates — `results/s044_gates.csv` (4/4 FAIL)
Le short-hook ORB s'effondre au fill réaliste (artefact) et flippe en OOS. **DISCARD net.** 44ᵉ traitée, **44ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s044_hook_bear.py` (dépend de s043). `ftmo_lab.py` inchangé.
