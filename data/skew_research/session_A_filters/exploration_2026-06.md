# Skew research — session_A_filters (combinaisons indicateurs + filtres directionnels)
### Exploration 2026-06. Objectif : briques skew+ / faible DD, portefeuille L7, univers FTMO.
*Discipline anti-mining : 1 spec canonique/candidat (pas de sweep, L10), mécanisme pré-spécifié AVANT test, filtré-vs-nu sur SR ET skew, **additionnalité au TSMOM nu**, **DSR déflaté pour N_tests**, two-sided (L25), GATE-0 FTMO, skew à l'horizon. VM légère (xs_universe daily seul, pas de NQ 5M).*

> **Réconciliation** : #1 (MA200) et #2 (Donchian-vol) recoupent `session_regime_filters` — re-tournés ici proprement (DSR + two-sided + additionnalité), cohérents. #3/#4/#5 neufs. Baseline TSMOM nu t=4,70 cohérent `IDEA_TSMOM` (t=4,76) / CTA 31-marchés.

---

## Univers GATE-0 (FTMO-tradeable, 19 instruments, 4 classes)
FX (EURUSD/GBPUSD/USDJPY/AUDUSD/USDCAD/NZDUSD) · Indices (SP500/NAS100/DAX/FTSE/NIKKEI) · Commodités (GOLD/SILVER/COPPER/BRENT) · Crypto (BTC/ETH/LTC/XRP). Portefeuille = moyenne equal-risk des PnL vol-targetés (10% ann, cap levier 3). Signal T-1→trade T.

## Résultats — chaque variante vs sa base nue

| variante | SR | skewM | MaxDD | t | **addl corr TSMOM** | two-sided L/S (bp) | filtré-vs-nu |
|---|---:|---:|---:|---:|---:|---:|---|
| **TSMOM_naked** (réf) | **+0,82** | +0,02 | −18,2% | +4,70 | +1,00 | — | edge trend réel |
| shorttrend_naked | +0,43 | +0,37 | −13,9% | +2,53 | +0,21 | — | |
| **#1 MA200-filt** | +0,65 | +0,47 | −12,1% | +3,77 | +0,44 | +1,22 / **−0,06** | ✅ GARDE (bat base) |
| donchian_naked | +0,30 | +0,76 | −13,7% | +1,73 | +0,12 | — | |
| **#2 Donch-lowvol** | +0,23 | +0,66 | −12,6% | +1,36 | +0,13 | +0,68 / −0,35 | ❌ REJETTE |
| fastmom_naked | +0,42 | +0,70 | −13,4% | +2,45 | +0,11 | — | |
| **#3 persist5** | +0,34 | +0,76 | −13,7% | +1,95 | +0,15 | +1,04 / −0,43 | ❌ REJETTE |
| **#4 strongclass** | +0,79 | −0,01 | −22,4% | +4,32 | **+0,69** | +2,47 / −0,36 | ❌ REJETTE (tuning) |
| **#5 DD-size (vol égale)** | **+0,90** | **+0,42** | −17,6% | +5,12 | **+0,95** | — | ⚠ bat nu MAIS tuning |

## DSR déflaté (Bailey-López de Prado, N_trials=9)
- N_trials=9, benchmark déflaté SR*(daily)=**+0,024** (≈ max attendu de 9 stratégies-bruit), best = #5 SR_daily +0,0565 (ann +0,90).
- **DSR = 0,998 → PASS (>0,95).** MAIS : le best est une **variante de TSMOM** (corr 0,95). Le DSR confirme que **l'edge trend est réel** (on le savait, t=4,70) — il **ne crée pas de brique neuve**. L'additionnalité (ci-dessous) est le filtre décisif, pas le DSR.

## Mécanisme tenu / rejeté + verdict brique (par candidat)

**#1 — Trend court filtré MA200.** Mécanisme (pas de signal contre-tendance majeure) : **TENU sur sa base nue** (SR 0,43→0,65, skew 0,37→0,47 — seul filtre qui bat sa base sur les deux). **MAIS brique = NON** : (a) short-leg morte (+1,22/−0,06) = tilt beta, (b) SR 0,65 **< TSMOM nu 0,82**, (c) corr-TSMOM 0,44 (chevauche). C'est un TSMOM beta-tilté inférieur, pas un sleeve décorrélé.

**#2 — Breakout filtré vol-régime.** Mécanisme (breakouts en chop = bruit) : **REJETÉ** — dégrade (SR 0,30→0,23). Donchian daily déjà mort (t 1,73), le filtre n'a rien à sauver. Cohérent `session_regime_filters` + `breakout_deepdive`. Brique = NON.

**#3 — Momentum filtré persistance (5j).** Mécanisme (filtrer les faux départs) : **REJETÉ** — dégrade le SR (0,42→0,34). **C'est l'ADX bis** : exiger 5 jours de confirmation **coupe les entrées précoces gagnantes** ; les « faux départs » filtrés étaient net positifs. Skew quasi-inchangé (0,70→0,76). Brique = NON.

**#4 — Trend sur classes fortes (crypto+commodités).** Mécanisme (efficience varie par classe) : **REJETÉ par additionnalité** — **corr-TSMOM 0,69** = c'est un *sous-ensemble* du même TSMOM (tuning moteur, ton drapeau), pas une brique. Et il **dégrade** : SR 0,82→0,79, skew →−0,01, **MaxDD −18%→−22%** (perte de diversification). Restreindre l'univers ≠ nouvel edge. Brique = NON.

**#5 — Trend + sizing-drawdown (vol égale, L19).** Mécanisme (negative-autocorrelation L7 : couper après pertes) : **TENU en performance** — SR 0,82→0,90, skew +0,02→**+0,42** à vol égale (le sizing tronque la queue gauche pendant les drawdowns → skew+, effet mécanique réel ; entrée propre, mult = roll5(base).shift(1), pas de look-ahead ; rescale full-sample = cosmétique scale-only). **MAIS brique = NON : corr-TSMOM 0,95.** Ce n'est pas un sleeve décorrélé, c'est un **raffinement du moteur trend existant**.

## VERDICT FINAL (session_A_filters)
**0 brique L7 neuve.** Mais deux résultats actionnables/nets :
1. **L'additionnalité est le juge, pas le DSR.** Les deux meilleures variantes (#4 corr 0,69 ; #5 corr 0,95) sont des **TSMOM déguisés** — le DSR passe (l'edge trend est réel) mais l'additionnalité dit « tuning moteur, pas brique ». Toute combinaison qui finit corr>~0,5 au TSMOM est du réglage moteur.
2. **Distinguer overlay de RISQUE vs filtre de SIGNAL.** Le seul à améliorer le profil du TSMOM nu est un **overlay de sizing** (#5 DD-sizing : +skew à vol égale), pas un filtre de signal (#1-#4 : dégradent ou tunent). → **Recommandation hors-L7 : verser le sizing-DD au book trend J1/G1** comme raffinement de skew (à valider en robustesse avant adoption — ici 1 config canonique, pas de sweep). Ce n'est pas une nouvelle brique, c'est une meilleure façon de courir le trend qu'on a déjà.

→ Cohérent avec le mur du projet : la seule chose qui survit au DSR est la famille trend (déjà le book J1/G1) ; les filtres de signal n'en extraient pas de sleeve décorrélé.

## Candidats-leçons (NOMMÉS, pas numérotés — tranché au merge)
- **« L'additionnalité (corr au TSMOM) juge la brique, pas le DSR »** — #4 (0,69) et #5 (0,95) passent/approchent le DSR mais sont des variantes de TSMOM. corr>~0,5 au moteur existant = tuning, pas sleeve décorrélé. Le DSR valide que l'edge trend est réel, pas qu'une brique neuve existe.
- **« Overlay de RISQUE améliore le skew ; filtre de SIGNAL ne fabrique pas de brique »** — #5 sizing-DD : skew +0,02→+0,42 à vol égale (tronque la queue gauche) ; #1-#4 filtres de signal dégradent ou tunent. Les overlays de sizing/risk (principled risk mgmt) aident le profil ; les filtres de signal n'ajoutent pas d'alpha.
- **« Filtre de persistance = ADX bis »** — exiger N jours de confirmation coupe les entrées précoces gagnantes (#3 : SR 0,42→0,34), comme l'ADX. Les faux départs filtrés sont net positifs.
- **« Restreindre l'univers ≠ nouvel edge (et coûte la diversification) »** — #4 strongclass : corr 0,69 au TSMOM, MaxDD −18%→−22%. Sélectionner les classes fortes = sous-échantillon du même signal, profil dégradé.
- **« Two-sided : la jambe short du trend court/fast est morte = tilt beta »** — #1 +1,22/−0,06, #3 +1,04/−0,43. Battre sa base nue (#1) ne fait pas une brique si le short-leg est mort et SR < TSMOM nu.

---
*session_A_filters, 5 candidats + bases nues (9 variantes, DSR N=9). Données : xs_universe (daily 2000-2026, 19 instruments FTMO 4 classes), book_JG. Tout backtest, 0 jour live. DSR déflaté Bailey-LdP. Réconcilié archive (session_regime_filters, breakout_deepdive, IDEA_TSMOM — pas de re-preuve). Rien figé, rien mergé. Écrit uniquement dans ce périmètre ; non touché aux autres sessions ni overnight_research/.*
