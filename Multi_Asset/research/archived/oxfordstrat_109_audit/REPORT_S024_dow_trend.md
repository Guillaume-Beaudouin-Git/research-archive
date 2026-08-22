# Rapport stratégie 24/109 — Dow Theory – Trend (Entry & Exit) — *court (héritage)*

**Statut :** ❌ **DISCARD (2/4)** — *héritage pivot/Dow (#23) : beta long déguisé (Gate 2) + DSR. Gate 1 (marginal) & OOS PASS.* · **Source :** https://oxfordstrat.com/trading-strategies/dow-theory-trend/ (Charles Dow, rating **C**). · **Registre :** #24. · 2026-06-06.

> Le **cas de base** que la #23 (MTF) benchmarke : mêmes pivots DeMark, **sans filtre de tendance primaire**, **sortie en temps** (au lieu du trailing). Même verdict.

## LES 2 CHIFFRES DÉCISIFS (en tête)

> **DÉLAI+1 (Gate 1) :** natif Sharpe **+0,41** (expR +0,0210) → fill réaliste **+0,09** (expR +0,0047). **→ PASS mais marginal** (sans le filtre primaire ni le trailing, le signal est plus faible que #23).
> **TWO-SIDED (Gate 2) :** long **+0,0870** (n=2413) / short **−0,0559** (n=2071). **→ FAIL : beta long.**

## Spec & archétype (1 ligne)
Pivots DeMark (Pivot_Size), **pas de filtre primaire**. Entrée = buy stop au-dessus du dernier swing-high (supply pivot) / sell stop sous le dernier swing-low (demand pivot). Sortie = **Time Exit** (Time_Index j) + ATR×6. Sweep `Pivot_Size × Time_Index`. Réutilise le moteur de fractals de S023 ; `ftmo_lab` v2-gates inchangé. Point Pivot_Size=3 / Time=21.

## Résultats (réf. Pivot_Size=3, Time=21)
**4 484 trades · win 50,1 % · expR +0,0210 · PF 1,087 · Sharpe 0,41 · MaxDD −38,8 %.** Grille `PS × Time` 100 % positive (Sharpe faible partout).

## Gates — `results/s024_gates.csv` (2/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | +0,41 → +0,09 | ✅ PASS (marginal) |
| 2 | Two-sided | long +0,087 / short **−0,056** | ❌ FAIL — beta long |
| 3 | DSR (N=9) | best Sharpe 1,012 < 1,519 | ❌ FAIL — bruit |
| 4 | OOS | train +0,025 → test +0,018 | ✅ PASS |

## Verdict
❌ **DISCARD (2/4).** Identique au #23 (même cœur pivot/Dow). Sans le filtre multi-échelle ni la sortie trailing, le signal est même **plus faible** (délai+1 ne laisse que +0,09). Toujours du **beta long** (long +0,087 / short −0,056). Confirme que la #23 (MTF) n'améliore le cas de base que marginalement, sans changer la nature beta. 24ᵉ traitée, **24ᵉ DISCARD**.

**Cluster pivot/Dow = {#23, #24} : 2/2 DISCARD au Gate 2.** Taxonomie trend inchangée (7ᵉ mécanisme).

## Suite
**#25 (Dual Momentum & Rate of Change)** puis **#26 (Dual Momentum & Vortex)** — momentum absolu/ROC, archétype distinct.

## Repro
`cd oxfordstrat_109/code && python strat_s024_dow_trend.py` (dépend de s023). Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3. Moteur `ftmo_lab.py` partagé/inchangé. Code : `code/strat_s024_dow_trend.py`.
