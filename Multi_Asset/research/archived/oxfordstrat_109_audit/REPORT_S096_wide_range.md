# Rapport stratégie 96/109 — Wide Range N-Day Pattern (Crabel)

**Statut :** ❌ **DISCARD (2/4)** — *ORB-stop sur jours wide-range ; artefact de fill (la source le donne perdant à −88 % DD).* · **Source :** https://oxfordstrat.com/trading-strategies/wide-range-pattern/ (Crabel, rating **D**). · **Registre :** #96. · 2026-06-07.

## Spec & archétype
Logique **inverse** du Narrow Range : setup = la plage N-jours la plus large sur Look_Back, puis **entrée ORB-stop** (buy/sell stop à Open±Stretch Crabel). Même famille fill-artefact que NR (#55), NR7 (#56), GSV (#37), ORB (#61). Réutilise `simulate_bracket` + `crabel_stretch`. Réf. N=2, Look_Back=20.

## Résultats (réf. N=2, LB=20)
**4 434 trades · win 41,5 % · expR +0,033 · PF 1,261 · Sharpe 1,04 · MaxDD −51,5 %.**
> **DÉLAI+1 :** natif (stop intrabar) +1,04 → open[i+1] **−0,11** (expR +0,033 → **−0,004**) = **inversion = artefact de fill**.  **DSR :** grille = bruit.  *(« BEATS beta » sur fill optimiste, mais moot une fois délai+1 fatal.)*

## Gates — `results/s096_gates.csv` (2/4 FAIL)
Artefact de fill intrabar + grille non significative — identique au reste de la famille ORB-stop. La source elle-même le classe **perdant** (Sharpe −1,45, MaxDD −88 %) et pire que le Narrow Range. 96ᵉ traitée, **96ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s096_wide_range.py` (dépend de `orb_filtered` + `beta_bench`). `ftmo_lab.py` inchangé.
