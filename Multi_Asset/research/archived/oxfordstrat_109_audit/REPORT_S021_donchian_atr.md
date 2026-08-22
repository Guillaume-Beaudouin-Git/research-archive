# Rapport stratégie 21/109 — Donchian Channel (Entry & Exit 2) — *court (héritage)*

**Statut :** ❌ **DISCARD (2/4)** — *héritage cluster channel-breakout {#6,#7,#20} : beta long déguisé (Gate 2) + DSR. Gate 1 & OOS PASS.* · **Source :** https://oxfordstrat.com/trading-strategies/donchian-channel-2/ (R. Donchian, rating **C**). · **Registre :** #21. · 2026-06-06.

> ⚠️ **Piège pédagogique :** expR **+1,27** (PF 3,7) a l'air spectaculaire — mais win **7,5 %**, Sharpe **0,48**, MaxDD **−88 %**, et **tout est long**. Les gates démasquent l'illusion. *expR seul ne suffit pas* (thèse v2-gates).

## Spec & archétype (1 ligne)
**Même entrée canal que #20** (buy stop > UpperChannel[i−1] / sell stop < LowerChannel[i−1]), mais **sortie = stop ATR fixe** `Entry ∓ ATR(20)×ATR_Index` (ATR_Index ∈ [1,6]) — **pas de cible, pas de sortie temps** (ATR_Stop=6 ne sert qu'au sizing). Sweep `Channel × ATR_Index`. Sim fidèle `simulate_donchian_atr` (recherche de touche vectorisée) ; `ftmo_lab` v2-gates inchangé. Point Channel=20, ATR_Index=3.

## LES 2 CHIFFRES DÉCISIFS (en tête)

> **DÉLAI+1 (Gate 1) :** natif Sharpe **+0,48** (expR +1,268) → fill réaliste open[i+1] **+0,51** (expR +1,472). **→ PASS : vrai breakout, insensible au fill** (stop au sommet du canal, pas un artefact ORB).
> **TWO-SIDED (Gate 2) :** long **+2,7522** (n=209) / short **−0,4544** (n=180). **→ FAIL : 100 % du profit est long ; le short saigne = beta long pur.**

## Résultats (réf. Channel=20, ATR_Index=3)
**389 trades · win 7,5 % · expR +1,2684 · PF 3,722 · Sharpe 0,48 · MaxDD −87,8 %.** Grille `Channel × ATR_Index` **100 % positive** mais Sharpe max ~0,48 (l'expR gonfle avec ATR_Index car les gagnants « courent jusqu'à la fin des données » = mark-to-EOD, sans amélioration du risque).

## Gates — `results/s021_gates.csv` (2/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | +0,48 → **+0,51** | ✅ PASS — vrai breakout |
| 2 | Two-sided | long +2,75 / short **−0,45** | ❌ FAIL — beta long déguisé |
| 3 | DSR (N=9) | best Sharpe 0,484 < 1,519 | ❌ FAIL — bruit (Sharpe trop faible) |
| 4 | OOS | train +1,52 → test **+0,89** | ✅ PASS — positif OOS |

## Verdict
❌ **DISCARD (2/4).** Identique au #20 dans le mécanisme : vrai breakout (Gate 1 + OOS OK) **mais beta long pur** (long porte tout, short saigne). La sortie « stop ATR sans cible » produit un profil à **win 7,5 % / quelques énormes gagnants** dont l'expR mirobolant (+1,27) est (a) **entièrement long** = beta, (b) **gonflé par le mark-to-EOD** des positions encore ouvertes, (c) assorti d'un **Sharpe 0,48 et d'un MaxDD −88 %** : intradeable. Les gates Gate 2 + DSR capturent exactement cette illusion. 21ᵉ traitée, **21ᵉ DISCARD**.

**Cluster channel-breakout-trend = {#6, #7, #20, #21} : 4/4 DISCARD au Gate 2 (beta long).**

## Suite
**#22 (Combined Donchian Channels — Entry & Exit)** = combinaison de canaux → même archétype → héritage attendu. Puis #23/#24 (Dow Theory).

## Repro
`cd oxfordstrat_109/code && python strat_s021_donchian_atr.py` (Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3). Moteur `ftmo_lab.py` partagé/inchangé. Code faisant foi : `code/strat_s021_donchian_atr.py`.
