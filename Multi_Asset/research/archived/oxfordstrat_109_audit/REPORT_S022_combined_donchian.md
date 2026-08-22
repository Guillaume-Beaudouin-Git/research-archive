# Rapport stratégie 22/109 — Combined Donchian Channels (Entry & Exit) — *court (héritage)*

**Statut :** ❌ **DISCARD (1/4)** — *héritage cluster channel-breakout {#6,#7,#20,#21} ; meilleure construction du lot mais beta long déguisé (Gate 2 seul).* · **Source :** https://oxfordstrat.com/trading-strategies/combined-donchian-channels/ (R. Donchian, rating **C**). · **Registre :** #22. · 2026-06-06.

> **Le « vrai » Turtle** (entrée canal long + **sortie trailing** canal court). Le mieux construit des 3 Donchian : **passe 3 gates sur 4** (Gate 1, DSR, OOS). Tué uniquement par le Gate 2 (beta long).

## Spec & archétype (1 ligne)
Système **dual-channel Turtle** : entrée = buy stop > `UpperChannelOne[i−1]` (Channel#1, long) ; **sortie trailing** = sell stop < `LowerChannelTwo[i−1]` (Channel#2 = #1 × C2 %, plus court) **+ stop ATR×6** (catastrophe + sizing). Sweep `Channel#1 × Channel#2 %`. Point canonique **#1=20 / #2=50 %** → sortie 10 j (Turtle classique 20/10). Sim fidèle `simulate_combined_donchian` (sortie trailing vectorisée) ; `ftmo_lab` v2-gates inchangé.

## LES 2 CHIFFRES DÉCISIFS (en tête)

> **DÉLAI+1 (Gate 1) :** natif Sharpe **+0,97** (expR +0,0433) → fill réaliste open[i+1] **+0,65** (expR +0,0290). **→ PASS : vrai breakout, survit au fill réaliste.**
> **TWO-SIDED (Gate 2) :** long **+0,1001** (n=2922) / short **−0,0207** (n=2591). **→ FAIL : le long porte tout, le short perd = beta long déguisé.**

## Résultats (réf. Channel#1=20 / #2=50 % → exit 10 j)
**5 513 trades · win 39,5 % · expR +0,0433 · PF 1,252 · Sharpe 0,97 · MaxDD −69,7 %.** Grille `#1 × #2 %` **100 % positive**, Sharpe croissant avec Channel#1 (les canaux longs captent mieux la tendance séculaire).

## Gates — `results/s022_gates.csv` (1/4 FAIL — le seul du cluster à passer la DSR)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | +0,97 → **+0,65** | ✅ PASS — vrai breakout |
| 2 | Two-sided | long +0,100 / short **−0,021** | ❌ **FAIL — beta long déguisé** |
| 3 | DSR (N=9) | best Sharpe **1,643 > 1,519** | ✅ **PASS** — grille significative |
| 4 | OOS | train +0,051 → test **+0,037** | ✅ PASS — positif OOS |

## Verdict
❌ **DISCARD (1/4).** C'est la **meilleure** des cinq variantes channel-breakout : la sortie *trailing* (vrai exit Donchian, contrairement au %-cible du #20 et au stop ATR fixe du #21) produit un signal **robuste** — il survit au délai+1, bat le seuil multiple-testing (DSR 1,64), et reste positif OOS. **Mais ce n'est pas un edge symétrique** : tout le profit vient du *long* (+0,10) tandis que le *short* perd (−0,02). C'est du **beta long** (capture de la dérive haussière indices/crypto), pas une stratégie market-neutral exploitable côté FTMO. MaxDD −70 %. Conformément à la règle v2-gates (beta déguisé ⇒ pas de KEEP), **DISCARD**. 22ᵉ traitée, **22ᵉ DISCARD**.

**Cluster channel-breakout-trend = {#6, #7, #20, #21, #22} : 5/5 DISCARD au Gate 2 (beta long).** Constat solide : *sur cet univers, le breakout de canal est un vrai signal de tendance mais structurellement long-beta.*

> *Note honnête :* si l'objectif était un **sleeve long-only de suivi de tendance** (en assumant que c'est du beta), le Turtle 20/10 (#22) serait le candidat le plus robuste du lot (DSR + OOS OK). Hors-cadre ici (on cherche un edge symétrique), mais à garder en tête.

## Suite
Fin du bloc Donchian (#20-#22). Prochain : **#23 (Dow Theory – Multiple Time Frames, Entry)** puis **#24 (Dow Theory – Trend)** — archétype tendance multi-échelle à vérifier.

## Repro
`cd oxfordstrat_109/code && python strat_s022_combined_donchian.py` (Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3). Moteur `ftmo_lab.py` partagé/inchangé. Code faisant foi : `code/strat_s022_combined_donchian.py`.
