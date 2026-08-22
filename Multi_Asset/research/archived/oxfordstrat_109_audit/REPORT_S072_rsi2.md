# Rapport stratégie 72/109 — RSI(2) Model (Connors) — *vraie mean-reversion, mais DÉCAYÉE*

**Statut :** ❌ **DISCARD (alpha réel mais arbitré/mort post-2009)** — *dip-buy Connors RSI2 ; edge couvert-beta significatif sur 2000-2009 puis disparu ; nul en 2019-2026.* · **Source :** https://oxfordstrat.com/trading-strategies/relative-strength-index-1/ (Larry Connors, rating **C**). · **Registre :** #72. · 2026-06-07.

> 🔔 **Signal MR examiné à fond (méthode S060).** RSI2 déclenche le même profil que #60 (long-only, passe délai+1, « bat le beta » via beta_line). Contrairement à #60, il **survit au mark-to-market** — mais l'audit par sous-période montre qu'il est **arbitré depuis la publication de Connors (2009)**.

## Spec & archétype
Connors 2-period RSI, **dip-buy long-only** : Setup `Close > SMA(200)` (régime haussier) + Filtre `RSI(2) < seuil` (survente courte) → achat à l'**open du lendemain** ; sortie sur croisement de tendance `Close>SMA(Exit_LB)` @open + stop ATR×6. Univers : indices actions (5 futures de la fiche → notre classe `indices`). Réf. seuil=10, Exit_LB=10.

## Résultats (réf. seuil=10, Exit_LB=10, indices)
**1 607 trades · win 74,5 % · expR +0,057 · PF 1,567 · Sharpe(trade) 1,33 · MaxDD −34,4 %.**
> **DÉLAI+1 :** open[+1] +1,33 → open[+2] +1,31 → **survit** (entrée @open, pas d'artefact de fill). **DSR :** 1,61 ≈ 1,65 (limite). **OOS :** +0,069 → +0,041 PASS.

## Test décisif — mark-to-market + sous-périodes (la vraie réponse)
Série quotidienne **mark-to-market** (pas de R étalé, cf. leçon S060), régression sur le buy&hold indices, alpha **couvert-beta** (Newey-West) :

| Période | Sharpe MTM | alpha ann. | beta | **t_NW(alpha)** | **Sharpe couvert-beta** |
|---|---|---|---|---|---|
| Plein 2000-2026 | 0,98 | +1,18 % | 0,06 | **+2,62** | **+0,52** |
| 2000-2009 | 1,52 | +1,73 % | 0,03 | +2,86 | **+0,92** |
| 2010-2018 | 0,99 | +1,12 % | 0,11 | +1,45 | +0,47 |
| **2019-2026** | 0,54 | **−0,09 %** | 0,08 | **−0,09** | **−0,04** |

**Lecture :** edge couvert-beta **réel et significatif** sur 2000-2009 (Sharpe couvert 0,92, t=2,9), qui **s'effondre** ensuite et est **mort en 2019-2026** (t=−0,09, alpha nul). Connors a **publié RSI2 en 2009** (*Short Term Trading Strategies That Work*) → l'edge existait avant la publication et a été **arbitré après**. Cas d'école d'alpha public décayé.

## Gates — `results/s072_gates.csv` (2/4)
FAIL two-sided (long-only par construction) + DSR (grille ≈ bruit) ; délai+1 et OOS passent. Mais le **test qui tranche est la décroissance** : un edge nul sur la seule période exploitable (récente) n'est pas déployable.

## Verdict
❌ **DISCARD — alpha réel mais décayé.** Le RSI2 est l'une des rares **vraies mean-reversions** du registre (survit au fill, alpha couvert-beta significatif en plein échantillon), mais c'est un **edge publié et arbitré** : fort avant 2009, mort après 2018. Contrairement au cas où l'on conserverait par excès de prudence, le verdict est clair car la **période récente est nulle** (t=−0,09). 72ᵉ traitée, **72ᵉ DISCARD**. *(À ranger comme « MR authentique mais saturée » — utile comme preuve de concept, pas comme stratégie live.)*

## Repro
`cd oxfordstrat_109/code && python strat_s072_rsi2.py` (gates) ; l'analyse MTM/sous-périodes suit la méthode `s060_audit.py`. `ftmo_lab.py` inchangé.
