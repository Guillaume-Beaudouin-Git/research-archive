# Synthèse — lot #24 → #30 (oxfordstrat 109, pipeline v2-gates)

**Date :** 2026-06-06 · **Traité en autonomie :** 7 stratégies (#24-#30) · **Résultat : 7/7 DISCARD** · **État registre : 30/109** (0 KEEP, 1 watchlist, 29 DISCARD).

> Rappel des 4 gates constitutionnels : un KEEP exige `edge_net>0` **ET** les 4 gates. **Gate 1** délai+1 (fill réaliste vs stop intrabar) · **Gate 2** two-sided (long vs short séparés ; rejette le beta déguisé) · **Gate 3** DSR (Sharpe déflaté sur la grille) · **Gate 4** OOS (train ≤2015 / test ≥2016).

## Tableau récapitulatif

| # | Stratégie | Archétype | Délai+1 (Gate 1) | Two-sided (Gate 2) | DSR | OOS | Verdict |
|---|---|---|---|---|---|---|---|
| 24 | Dow Theory – Trend | pivots DeMark (mono-échelle) | +0,41→+0,09 ✅ | L +0,087 / S −0,056 ❌ | ❌ | ✅ | **DISCARD 2/4** |
| 25 | Dual Momentum & ROC | momentum absolu double (CTA) | +0,59→+0,52 ✅ | L +0,21 / S −0,11 ❌ | ❌ | ✅ | **DISCARD 2/4** |
| 26 | Dual Momentum & Vortex | momentum absolu (Vortex) | +0,58→+0,48 ✅ | L +0,21 / S −0,12 ❌ | ❌ | ✅ | **DISCARD 2/4** |
| 27 | Bearish Engulfing | ORB-stop + bougie (short) | −0,55→−0,08 ❌ | L −0,003 / S −0,150 ❌ | ❌ | ❌ | **DISCARD net 4/4** |
| 28 | Bullish Engulfing | ORB-stop + bougie (long) | −0,02→+0,49 | one-sided | ❌ | — | **DISCARD net** (edge<0) |
| 29 | Bullish Engulfing Type A | bougie + range engulf | +0,16→+0,32 ✅ | beta long ❌ | ❌ | ✅ | **DISCARD 2/4** |
| 30 | Bullish Engulfing A + dip-filter | bougie + filtre MA (dip) | +0,25→+0,31 ✅ | beta long ❌ | ❌ | ✅ | **DISCARD 2/4** |

*(L = long, S = short, en R-multiples nets.)*

## Deux méta-constats décisifs

### 1. Tendance/continuation = beta long déguisé (Gate 2), systématiquement
#24, #25, #26 rejoignent les clusters déjà jugés : **tout détecteur de « force » à acheter** capte la dérive haussière séculaire (indices/crypto) en long, tandis que le short perd. Le signal est souvent *réel* (passe Gate 1 + OOS) mais ce n'est **pas un edge symétrique** — c'est du beta.

**Bilan « acheter la force » sur cet univers — 9 mécanismes indépendants, 9 morts au Gate 2 :**
KAMA · ADX/Donchian · Aroon · Bollinger-breakout · DI-cross · channel-breakouts (Donchian/Turtle) · pivots Dow · **Dual Momentum ROC** · **Dual Momentum Vortex**. L'archétype change, le verdict non.

### 2. Patterns de bougie = aucun alpha de reversal exploitable
Le cluster **Engulfing (#27-#30)** complète le cluster **Doji (#16-#19)** : **8/8 DISCARD**. Point méthodologique important : les « engulfing » d'oxfordstrat ne sont **pas** des mean-reversion à l'entrée close — l'entrée est l'**ORB-stop de Crabel** filtré par un pattern. J'ai décomposé le **pur pattern** (rendement forward 10 j, sans ORB) :

- Bullish engulfing → long : **+0,37 %** (≈ la simple dérive marché sur 10 j = beta).
- Bearish engulfing → short : **−0,44 %** (négatif : après le pattern, le prix monte → shorter perd).

→ Le pattern **ne prédit aucun reversal**. La variante la plus flatteuse (#30, dip-filtré : expR +0,51 / PF 1,71) est un **mirage** : 255 trades, Sharpe 0,25, DSR catastrophique, strictement long. *expR élevé ≠ KEEP.*

## Note de rigueur
- **Correction de numérotation** : la session précédente avait traité « Greatest Swing Value » comme #20 ; le vrai #20 du registre figé est **Donchian Channel (E&E1)**. Corrigé ; le brouillon GSV est **parké** (`_parked_drafts/`) pour son vrai numéro (bloc « G »).
- **Hypothèse réfutée par les données** : j'attendais une mort Gate 1 (artefact de fill) pour l'Engulfing-ORB ; en réalité le long *survit* au délai+1 (le pattern est rare, pas du spam intrabar). Le vrai tueur est l'absence d'alpha (short perdant, long = beta). Reporté tel quel.
- `ftmo_lab.py` (moteur + 4 gates) **inchangé** depuis le commit v2-gates ; repro S001 intacte. 7 commits atomiques (le cluster Engulfing en 1 commit).

## État global à 30/109
- **0 KEEP.** **1 watchlist** : Bollinger %b (#12) — seul **alpha mean-reversion bilatéral réel** trouvé (dip-buy +0,019 vs neutre, rip-sell +0,012, Sharpe élevé), mais **décayé** (Sharpe 1,6→0,2) et concentré indices → DISCARD-watchlist, pas KEEP.
- **29 DISCARD.** Taxonomie stable : artefact de fill ORB-stop (S001/S002/GSV) · beta long (tout le trend) · bougies sans edge (Doji + Engulfing).

## Suite
**#31-#32 (False Breakout, Setup & Exit 1/2)** — archétype **fade de faux breakout** = potentiellement le vrai mean-reversion à surveiller (vendre l'échec d'un breakout). Puis #33+ (Keltner, etc.). Les False Breakout méritent un test à fond (entrée contre-tendance, pas ORB) — à signaler fort s'ils montrent un alpha bilatéral robuste récent.
