# VERDICT — Calendar Spreads CME

Date : 2026-05-25
Status : KILL
Sharpe net retail attendu : 0.4–0.7 (Bianchi 2023, Fan 2024 — commodity monthly basket)
Capital minimum requis : $50K+ (margin requirements for spread legs)
Décorrélation portfolio existant : moyenne (commodity cycle, faible corr avec A/B/C)
Propfirm-fit : non

## Verdict tranché

KILL pour tout contexte propfirm Tradeify. Trois raisons indépendantes rendent
l'edge inexploitable : ambiguïté réglementaire sur les positions hedgées, cap
daily binding sur contrats mini, et restriction API Tradovate sur les Sim/Funded
accounts. Même si le signal est réel, l'infrastructure d'exécution est bloquante.

## Pourquoi cette conclusion

- **Rule no-hedging ambiguë** : Tradeify Select Flex interdit explicitement le
  hedging simultané L/S sur le même sous-jacent (règles 2026). Un calendar spread
  CL near/far constitue deux positions simultanées sur CL — classification ambiguë
  qui expose à une disqualification ex post sans recours.
- **Cap daily binding** : À 1 mini-contract (MNQ/MCL), le P&L moyen d'un calendar
  spread est < $50/jour net de costs ($19 RT × 2 legs). La consistency cap
  Tradeify ($600/jour) n'est pas la contrainte — c'est l'impossibilité d'atteindre
  $1,500 profit target en temps utile avec une seule position mini.
- **API Tradovate Sim/Funded restreinte** : les spreads calendar ne sont pas
  supportés nativement dans l'API REST Tradovate (pas d'ordre type SPREAD).
  Exécution en deux ordres séparés expose au leg risk (fill partiel).
- **Stanley 2019 QuantRocket intraday CL** : stratégie spreads intraday CL réelle
  documentée → -91% CAGR une fois les coûts réels intégrés. Confirme que le
  gross edge académique (Bianchi 2023) ne survit pas aux costs retail.

## Valeur pour CV / Interview

Démontre la maîtrise du cadre méthodologique L7 (propfirm-rule compatibility check
avant tout backtest). Avoir identifié trois contraintes indépendantes — règles,
sizing, API — avant même de lancer un backtest est exactement le filtre que les
desks systématiques (CFM, Squarepoint) attendent d'un chercheur junior. L'edge
académique est réel (papers Bianchi, Fan) ; la rigueur est dans la séparation
entre "edge existe" et "edge exploitable dans mon contexte".

## Conditions de réactivation

- Capital personnel ≥ $50K + compte propriétaire (pas propfirm) permettant le
  vrai hedging sur compte réel → réévaluer l'exécution en deux legs séparés.
- Accès à l'API Tradovate Pro (native spread orders) ou broker alternatif
  (Interactive Brokers TWS avec spread combos natifs).

## Lien vers deep research

[deep_research.md](deep_research.md)
