# FICHE-SLEEVE — Rebond intraday de fin de mois (BTC / crypto, FTMO CFD)

**Statut :** candidate validée · edge réel, lent (~8/an) · destinée à une **sleeve diversifiante** du book existant (pas un algo standalone rapide). Date : 2026-07-12. Source : programme `btc_intraday_ftmo`, N_ledger step "alpha-vs-beta" + "sizing".

---
  
  ## 1. Thèse en une ligne
  Le dernier vendredi du mois, un flux de rebalancing market-wide fait **rebondir la crypto en séance US** : si le marché a baissé entre 04:00 et 08:00 UTC, il tend à remonter d'ici midi. **Intraday-flat → zéro swap.**

## 2. Règle exacte (gelable)
- **Univers :** BTCUSD (primaire). Effet market-wide (confirmé sur ETH/SOL/DOGE/XRP/BNB) → un panier est possible mais **corrélé** (≈ 1 pari) ; pour FTMO, garder **1 instrument** (BTCUSD) suffit.
- **Jour :** dernier vendredi calendaire de chaque mois.
- **Signal (connu à 08:00) :** `pre = open(08:00 UTC) / open(04:00 UTC) − 1`. Trader **seulement si `pre < 0`** (baisse en pré-séance).
- **Entrée :** LONG à l'`open` de 08:00 UTC.
- **Sortie :** `close` de 11:59 UTC (hold ~4h), **flat avant tout rollover** → pas de swap.
- **Stop dur recommandé (risk-mgmt live) :** −2,5 % intraday. Historiquement 1 trade/28 l'aurait touché (MAE min −3,37 %) ; il borne la queue contre la barrière −5 %/jour sans couper l'edge.
- **Fréquence :** ~8 trades/an (les mois où `pre ≥ 0` ne tradent pas).

## 3. Métriques (BTC, régime 2023+, N=28, net de coût CFD ~11,5 bps RT)
| Métrique | Valeur |
|---|---|
| Win-rate | **0,75** |
| Win/loss ratio | **~1,37** |
| Net moyen / trade | **+0,47 %** (bounce brut +0,59 %) |
| t-stat (HAC) | **+2,55** |
| Meilleur / pire bounce | +3,30 % / (MAE min −3,37 %) |
| **MAE intraday moyen** | **−0,36 %** (queue gauche minuscule) |
| ETH confirmation | N=24, WR 0,75, net +0,42 % (t 1,58) |

## 4. Front de sizing (moteur barrière path-aware, FTMO 2-step 10k)
| Levier | p(pass 2 phases, ≤800 j) | ~mois médian (P1) | P(bust, ~P1) |
|--:|--:|--:|--:|
| 1,0 | 31 % | 20 | 0 % |
| 2,0 | 52 % | 12 | 31 % |
| 3,0 | 63 % | 8,5 | 24 % |
| **3,33 (max FTMO crypto)** | **65 %** | **7,9** | **23 %** |

**Lecture sizing :** la MAE minuscule permet de sizer **près du levier max** — ça accélère (moins de temps exposé à la barrière) sans exploser le bust. Le levier max (3,33) est ~EV/vitesse-optimal ici. **La contrainte est la FRÉQUENCE, pas le sizing** : même à levier max, phase 1 ≈ 8 mois (→ ~12 mois jusqu'à funded). Passer un challenge « en < 1 mois » avec ce sleeve **seul est impossible** (structurel, ~8/an).

## 5. Validation (pourquoi c'est un vrai edge)
- **Pas du beta générique** (placebo temporel) : acheter le dip un **jour ordinaire** PERD −8,9 bps (t −2,98, N=594) ; seul le dernier vendredi rebondit (+47 bps). L'edge est **spécifique au calendrier**.
- **Pas du gamma d'options** (placebo cross-asset, L44) : DOGE/XRP/BNB (~pas d'options) montrent l'effet **aussi fort** → ce n'est pas le hedging de dealers, c'est un flux **market-wide de fin de mois**.
                                                                        - **Profil L24-idéal** : WR élevé + win/loss > 1 + kurtosis basse + queue gauche bornée = le profil que la barrière symétrique FTMO récompense.
                                                                        
                                                                        ## 6. Risques & caveats (à surveiller)
                                                                        - **Récent-only :** effet fort en 2023+ ; **négatif pré-2022** (last-Fri −26 bps). Probablement lié à la structure de marché actuelle (ère ETF/institutionnalisation) → **surveiller la décroissance** trimestre par trimestre.
                                                                        - **N=28, ~8/an :** échantillon mince, DSR marginal → incertitude large sur p(pass). Déployer **petit d'abord**, ré-évaluer après ~6-8 trades live.
- **Corrélé cross-crypto :** pas de diversification en poolant des cryptos (≈ 1 pari) ; la vraie diversification vient de sleeves *décorrélés* (autres mécanismes).
- **Régime-dépendant (beta timé) :** peut flipper en bear market → gate de régime recommandé (ex : ne pas trader si BTC < MA200 daily).

## 7. Recommandation de déploiement
**Sleeve diversifiante** dans le book existant : timing fin-de-mois **décorrélé** des sleeves Nightly/J1/Or/ORB, +~8 paris/an, intraday-flat (pas de swap), queue gauche minuscule (sizable). **Pas** un moteur de challenge standalone. Intégration à décider via le process habituel (pré-registration, author≠auditor, EA gelé non touché).

## 8. Reproduction
Code : `outputs/btc_intraday_ftmo/` — `alpha_vs_beta.py` (test placebo), extraction month-end + front de sizing (scripts session). Data : `data/panels/m5_indices/binance/BTCUSD_M1.csv`. Moteur barrière : `ftmo_barrier.py`. Détail chronologique : `N_ledger.md`.
