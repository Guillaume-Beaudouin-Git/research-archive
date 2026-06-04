# MACD fast-trend diversifier (shape brick)

> **Statut** : VALIDÉ comme brique de combinaison. **NE PAS déployer seul.** Valeur = shape/decorrelation dans le portefeuille combiné, pas return engine.
> **Source canonique** : `data/skew_research/session_basic_trend/exploration_2026-06.md` (decisive test) + `session_basic_trend/MACD_brick_registry_card.md` + `session_basic_trend/exploration_mechanism_2026-06.md`.
> **Code repro** : `session_basic_trend/trend_profile.py`.

---

## Ce que c'est

Brique de **risk-shaping / diversification** par-dessus le moteur TSMOM — pas un edge, pas un crash-hedge. Fast-trend MACD (12/26/9) sur le basket FTMO-tradeable (indices, crypto, gold/silver CFD).

## Spec figée

| Champ | Valeur |
|---|---|
| Signal | MACD cross (12-EMA / 26-EMA / signal 9) |
| Direction | two-sided (long sur cross-up, short sur cross-down) |
| Univers FTMO-tradeable | US500, US100, GER40 (indices CFD) ; BTC, ETH (crypto CFD) ; XAUUSD, XAGUSD (gold/silver CFD, proxy GLD/SLV au backtest) |
| Médiane hold | **9 jours** |
| Trades / sample | 3010 (2000-2026) |
| Allocation envisagée | **30 %** du book (vol-matched contre TSMOM) |

## Métriques mesurées (sample 2000-2026, n=7971)

| Métrique | Valeur |
|---|---:|
| Trade-skew (entry→exit) | **+4,2** |
| Win rate | 33 % |
| Mean R / trade | +0,4 % |
| Daily Sharpe | 0,33 |
| Corr → equity (LONG_US500) | **−0,18** |
| **Corr → TSMOM** | **+0,08** (additionnel) |
| Corr → Donchian | 0,00 |
| Corr → EMA / Momentum (slow trend) | −0,18 / +0,05 |

### Test décisif — overlay sur TSMOM (brick vol-matched)

| Portfolio | maxDD | worst-day |
|---|---:|---:|
| TSMOM seul | −13,7 % | −5,9 % |
| +15 % MACD | **−10,5 %** | −5,1 % |
| **+30 % MACD** | **−9,1 %** (sous floor −10 %) | **−4,3 %** |

Sur les 20 pires jours TSMOM : TSMOM −3,11 % moyenne, **MACD −0,95 %** (cushion — less-down, sans gain → diversificateur, pas hedge).

### Carry (transparent)

- Gross : +0,40 %/mo
- Swap mesuré equity ~4,46 bps/jour ≈ 0,47 %/mo
- **Net : −0,07 %/mo (near-free)**
- Sur challenge 2-6 mois : −0,1 à −0,4 % total carry — supportable vs DD-avoided.

## Gate-0 FTMO

✅ **FTMO-tradeable.** Tout l'univers est dans les classes FTMO autorisées (indices CFD, crypto CFD, XAUUSD/XAGUSD CFD). Pas d'ETF, pas de bonds, pas de spot.

→ Contrairement à VXX (perso-only, ETN exclu), MACD-on-FTMO-instruments donne convexité + décorrélation **dans l'univers FTMO**, au prix du swap held-notional.

## ⚠ DEUX LIMITES EXPLICITES (à ne JAMAIS perdre de vue)

> **(a) Réduit le maxDD CUMULÉ (drift vers le floor total −10 %), PAS le cap journalier 5 %.**
> Le cap daily FTMO 5 % est le mode de bust le plus fréquent. MACD **ne le couvre pas** : sur jour corrélé baissier, il est aussi baissier (juste moins). Les deux modes de bust (floor total vs cap daily) sont **distincts** ; MACD aide le premier uniquement.

> **(b) La queue krach-corrélé d'un seul jour reste NON COUVERTE en FTMO.**
> MACD et TSMOM sont tous deux trend → tous deux perdent sur le jour krach. Le seul vrai hedge = long-vol = **perso-only (échoue Gate-0)**. Donc la queue daily-cap / crash-day n'a **aucun hedge FTMO-tradeable** dans le set actuel.

**→ MACD aide le floor TOTAL, pas le cap DAILY. Ne PAS le déployer comme protection krach.**

## Pourquoi dans personal_book (et pas dans le pipeline FTMO seul)

C'est une **brique de combinaison** : son entier value est *dans* la matrice de corrélation avec TSMOM. Standalone, c'est un Sharpe 0,33 modeste. Combiné à TSMOM avec un allocation 30 %, il abaisse le maxDD cumulé sous le floor. Le sleeve **N'EST PAS** un sleeve à déployer seul ; il est documenté ici comme composant du portefeuille combiné perso (qui inclut aussi A, B, B1, et potentiellement Commodity Seasonality).

## Pre-requis avant tout merge / construction de portefeuille (NE PAS merger maintenant)

1. **Mesure ORB 15:30 spread** (en attente).
2. **CRITIQUE — valider le swap CRYPTO de TSMOM.** L'architecture combinée pivote autour de TSMOM comme moteur, et son net depend d'un swap jamais mesuré (equity mesuré −3,08 bps/nuit ; **crypto non mesuré, et crypto est le swing**). **Un overlay qui pull le maxDD sous le floor est worthless si le moteur est net-négatif après swap.** Valider le moteur avant d'optimiser son overlay.

## Réconciliation archive

- Distinct de Donchian / EMA / Momentum (corr 0,55-0,76 entre eux **et avec TSMOM** → redondants, droppés).
- Distinct de Pullback-in-uptrend (négatif skew −5,4 + equity +0,27 → convexity-seller, rejeté).
- L'angle « profile » (skew+décorrélation) est neuf vs l'archive qui jugeait MACD sur Sharpe standalone seul.

## Leçons (candidates)

- *« naked trend = profile skew+ même quand standalone ne gagne pas »* — EMA/Donchian/Momentum/MACD ont tous trade-skew +4 à +26 à Sharpe modeste. Le profil est le livrable, pas le P&L.
- *« MACD = brique fast-trend décorrélée, distincte du trio slow »* (corr 0,01-0,05 avec EMA/Donch/Mom) → seconde dimension trend genuine.
- *« trend-on-FTMO-instruments = la brique convexité FTMO-tradeable »* — là où long-vol VXX échouait Gate-0 (perso-only), trend-FTMO donne skew+ et décorrélation **dans l'univers FTMO**, au prix du swap held-notional.
