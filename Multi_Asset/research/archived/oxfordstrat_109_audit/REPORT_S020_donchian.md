# Rapport stratégie 20/109 — Donchian Channel (Entry & Exit 1)

**Statut :** ❌ **DISCARD (2/4)** — *beta long déguisé (Gate 2) + grille = bruit (DSR). Gate 1 & OOS PASS.* · **Source :** https://oxfordstrat.com/trading-strategies/donchian-channel-1/ (Richard D. Donchian, rating **C**). · **Registre :** #20. · 2026-06-06.

> ⚠️ **Correction de numérotation :** la #20 du registre figé est **Donchian Channel (E&E1)**, pas « Greatest Swing Value ». La GSV est dans le bloc « G » (bien plus loin) ; son brouillon est **parké** (`_parked_drafts/`) pour son vrai numéro. Voir note en bas.

## LES 2 CHIFFRES DÉCISIFS (en tête)

> **DÉLAI+1 (Gate 1) :** natif(stop) Sharpe **+0,67** (expR +0,166) → fill réaliste open[i+1] Sharpe **+0,64** (expR +0,152). **→ PASS : l'edge survit au fill réaliste.**
> **TWO-SIDED (Gate 2) :** long **+0,4321** (n=601) / short **−0,2010** (n=436). **→ FAIL : tout le profit est long ; le short saigne = beta long déguisé.**

**Contraste clé avec l'ORB (S001/S002) :** ici le stop d'entrée est posé **au sommet du canal** (niveau significatif, loin du prix de la veille) → c'est un **vrai déclencheur de momentum**, robuste au délai+1. L'ORB pose le stop à `Open ± petit stretch` (franchi *intrabar presque chaque jour*) → artefact de fill. **Toutes les entrées-stop ne se valent pas :** le Donchian passe le Gate 1 ; l'ORB/GSV s'y effondrent.

## Spec & archétype
**Donchian channel breakout, sans filtre** (R. Donchian, ancêtre du système Turtle). `UpperChannel(L)` = plus-haut sur L ; `LowerChannel(L)` = plus-bas sur L. **Entrée :** long = buy stop 1 tick au-dessus de `UpperChannel[i−1]` ; short = sell stop sous `LowerChannel[i−1]`. **Sortie :** *%-Target au close* (`Close ≥ Entrée×(1+T/100)` en long) **+ stop ATR(20)×6**. Pas de sortie en temps. **Sweep :** `Channel_Length [2,100] × Target_Exit% [2,100]`. Même **archétype d'entrée** que S006/S011 (channel breakout = trend-following), mais version **canonique** (pas d'ADX) à sortie %-cible.

Implémentation : `simulate_donchian_pct()` (entrée-stop au canal, sortie %-cible/ATR, leviers de fill pour Gate 1), R-multiples & coûts FTMO via `ftmo_lab` v2-gates (inchangé). Point canonique **Channel=20** (Turtle), **Target=20 %**.

## Résultats (réf. Channel=20, Target=20 %)
**1 037 trades · win 41,9 % · expR +0,1659 · PF 1,288 · Sharpe 0,67 · MaxDD −60,2 %** (fill natif).

Grille `Channel × Target%` (expR) — `results/s020_sensitivity_expectancy.csv` — **100 % positive** mais Sharpes faibles (max 0,90) :

| | T10 % | T20 % | T40 % |
|---|---|---|---|
| **C20** | 0,085 | 0,166 | 0,382 |
| **C40** | 0,090 | 0,207 | 0,308 |
| **C80** | 0,124 | 0,201 | 0,493 |

## Gates — `results/s020_gates.csv`

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | natif +0,67 → réel **+0,64** | ✅ **PASS** — vrai breakout (pas un artefact de fill) |
| 2 | Two-sided | long +0,432 / short **−0,201** | ❌ **FAIL** — beta long déguisé |
| 3 | DSR (N=9) | best Sharpe 0,899 < 1,519 | ❌ **FAIL** — grille = bruit |
| 4 | OOS (2015/16) | train +0,290 → test **+0,058** | ✅ PASS — positif OOS, pas de flip |

## Verdict
❌ **DISCARD (2/4).** Le breakout de canal Donchian est un **vrai signal de momentum** (survit au délai+1, reste positif OOS), mais ce n'est **pas un edge symétrique** : il capte la **dérive haussière séculaire** des indices/crypto en *long* (expR +0,43) tandis que le *short* perd structurellement (−0,20). C'est du **beta long déguisé en stratégie** — exactement le mode de mort de S006 (#6) et S011 (#7). La sortie %-cible ne change pas l'asymétrie ; et la grille, malgré 100 % de cellules positives, a un Sharpe trop faible pour battre le seuil multiple-testing (DSR). MaxDD −60 %. 20ᵉ traitée, **20ᵉ DISCARD**.

**Cluster channel-breakout-trend = {#6, #7, #20} : 3/3 DISCARD au Gate 2 (beta long).**

## Suite
**#21 (Donchian Channel — Entry & Exit 2)** et **#22 (Combined Donchian)** = mêmes entrées de canal → héritage attendu (Gate 2 beta long). Puis #23/#24 Dow Theory.

## Note — brouillon GSV parké
Le travail « Greatest Swing Value » (réalisé par erreur d'aiguillage comme « #20 ») est valide et **conservé** dans `_parked_drafts/` (`gsv_strat_DRAFT.py`, `REPORT_gsv_DRAFT.md`, résultats). Résultat GSV : ORB-stop pur → **DISCARD 1/4 (Gate 1, artefact de fill)** ; il sera re-numéroté et committé à sa vraie position (bloc « G » du registre).

## Repro
`cd oxfordstrat_109/code && python strat_s020_donchian.py` (Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3). Moteur `ftmo_lab.py` partagé/inchangé. Code faisant foi : `code/strat_s020_donchian.py`.
