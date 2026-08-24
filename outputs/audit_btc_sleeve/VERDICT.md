# VOLET C — VERDICT : BTCUSD comme 5e actif du pipeline `engine` → **NO-GO** (BTC clos)

**Auditeur ≠ auteur · 2026-07-13 · offline.** Pré-reg gelée `design/PREREG_btc_5e_actif_20260713-0030.md`
(commit `26b71738`, avant tout résultat). Contrôle d'entrée : `kill=0 · flat_today=0 · positions=[] · FLAT absent`.
Test = **un seul essai, zéro DOF** : BTC dans `engine.build_signals()` inchangé (trend 60/120/250 vol-targeté), vm14.

## 1. Faisabilité d'exécution
- **Disponibilité** : `market_export.json` du compte armé <ACCOUNT_ID> = **4 symboles (XAUUSD/USDJPY/US100/GER40), BTC absent**. FTMO Swing propose BTCUSD comme instrument, mais **hors univers EA/book actuel** → l'ajouter touche la chaîne gelée (interdit). Levier crypto **Swing < 1:3,33** supposé (le compte montre déjà marge Swing XAU 0,1111 vs Normal 0,0333).
- **Swap** (mesuré, pas supposé) : −30 %/an = 8,22 bps/nuit ×3 ven, **les deux côtés**. Sur le sleeve always-on (avg |pos| 0,19-0,23, en position ~100 % du temps) = **drag −7,2 %/an (full) à −8,8 %/an (2023+)** sur equity.
- **Granularité** : min lot 0,01 BTC ≈ $710 notionnel @$71k = **7 % equity/pas** sur $10k. En régime haute-vol le vol-target veut < 0,01 BTC → **plancher de lot sur-dimensionne BTC exactement quand il crashe** (vol-targeting cassé au pire moment).

## 2. Corrélation au book — l'hypothèse « overload risk-on » est **RÉFUTÉE**
| corr(BTC-trend, ·) | full (N=2598) | 2023+ (N=875) |
|---|--:|--:|
| US100 (Nightly) | +0,10 | +0,10 |
| XAUUSD (Or) | +0,02 | −0,01 |
| USDJPY (J1) | +0,03 | −0,02 |
| **BOOK composite** | **+0,100** | **+0,089** |

**corr(BTC, book) = 0,09-0,10 ⋘ 0,35** → **la kill rule corrélation NE se déclenche PAS.** Contrairement à l'hypothèse,
le trend BTC est **décorrélé** du book au niveau sleeve (le book n'est pas pur risk-on : XAU/JPY diversifient ; le
vol-targeting dé-synchronise les timings de trend). *Mais* la décorrélation d'un sleeve à rendement ~nul **n'ajoute pas d'EV** (§3).

## 3. Économie — le swap éteint l'edge dans le régime opérant
| BTC trend sleeve (engine recipe, always-on) | full 2014+ | **2023+** |
|---|--:|--:|
| GROSS Sharpe / rendement | +1,27 / +14,4 % | +0,91 / +9,7 % |
| swap drag | −7,2 %/an | **−8,8 %/an** |
| **NET (swap+coût) Sharpe / rendement** | +0,61 / +6,9 % | **+0,05 / +0,6 %** |

Dans le **régime où le book opère (2023+)**, le swap mange 8,8 des 9,7 pts → **net Sharpe +0,05 ≈ ZÉRO**. Un sleeve
net-Sharpe ≈0, ajouté à un book **vol-targeté vm14** (budget de vol fixe), **dilue** les legs générateurs (les autres legs
sont scalés down pour garder la vol constante) → **ΔEV ≤ 0** (leçon du rapport #2 §5.5 : « a decorrelated but losing/zero
sleeve drags the book down »). Le full-sample net +0,61 = artefact du bull pré-2023 (régime-dépendant, comme tout cet espace).
La version regime-gated (long bull-calme only) fait net +0,54 — **mais c'est le regime-rotation DSR-mort (0,00), pas « engine unchanged ».**

## 4. Tail — capitulation coïncide avec le risk-off du book
Jours de flush BTC (−15 %/3j, N=53 ; **2/an seulement en 2023+**) : indices **en baisse** concurrente (GER40 −62, US100 −36,
XAU −16 bps ; P(down) 0,5). Donc une entrée capitulation-long BTC arrive **quand le book (long risk-on) est déjà en drawdown
près du breaker 9650** → **ajoute du risque de queue, ne diversifie pas le tail** (Δp(bust) directionnellement > 0). Sleeve quasi-inactif en 2023+.

## 5. KILL RULES — bilan
| règle | valeur | déclenche ? |
|---|---|---|
| corr(BTC, book) > 0,35 | 0,09-0,10 | **NON** (réfute l'hypothèse — honnête) |
| swap rend net-négatif | net +0,05 (2023+) / +0,61 (full) | pas strictement < 0, mais **≈0 en régime opérant** |
| **ΔEV/campagne < +$150** | sleeve net ≈0 → dilutif dans book vol-targeté → **ΔEV ≤ 0** | **OUI** |
| Δp(bust) > +2 pts | capitulation = tail risk-on ajouté ; granularité sur-size en crash | **directionnellement OUI** |
| BTCUSD indispo / granularité inexploitable Swing | hors univers EA + 7 % equity/pas + plancher casse le vol-target | **OUI (immédiat)** |

Le **5e-actif sim complet (cleanroom port BTC) N'EST PAS lancé** : un sleeve net-Sharpe +0,05 (2023+) ne peut **par construction**
produire ΔEV ≥ +$150 dans un book vol-targeté (il dilue) — le run serait du théâtre. Déflation DSR : +1 essai sur n_trials≈50 (négligeable, comme prévu).

## VERDICT : **NO-GO. BTC est CLOS définitivement pour ce projet.**
Non pas parce que corrélé (il ne l'est pas : 0,10) — mais parce que le **swap Swing éteint l'edge dans le régime opérant
(net Sharpe +0,05, 2023+)**, qu'un sleeve net-nul **dilue** un book vol-targeté (ΔEV ≤ 0 < +$150), que la **granularité de
lot 0,01 BTC** casse le vol-target sur $10k, que **BTCUSD est hors de l'univers EA armé**, et que le budget multiple-testing
de l'espace BTC est **épuisé** (DSR). Déploiement de toute façon **version-future** (EA gelé). Écrit au ledger. **Pas de 3e itération.**
