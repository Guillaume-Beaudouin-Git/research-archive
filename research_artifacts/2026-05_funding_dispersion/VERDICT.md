# VERDICT — Funding Dispersion

Date : 2026-05-25
Status : CONDITIONAL GO (DEX-DEX uniquement)
Sharpe net retail attendu : 0.8–1.6 (estimé sur $25K USDC, 2-leg DEX arbitrage)
Capital minimum requis : $25K USDC (HL + Drift simultanés)
Décorrélation portfolio existant : élevée (Strategy B = sign(HL_funding), F7 = spread entre fundings)
Propfirm-fit : non (crypto, pas accepté propfirm)

## Verdict tranché

NO-GO sur CEX-CEX (Binance/Bybit futures géo-fencés pour résidents EU post-MiCA
2024). CONDITIONAL GO sur DEX-DEX : Hyperliquid ↔ Drift/Lighter/Paradex. Le
spread de funding rate entre deux DEX perps est décorrélé du signe absolu de
HL funding (Strategy B), ce qui en fait un vrai diversificateur au sein du
livre crypto personnel. Implémentation pilot Q3 2026 à prévoir.

## Pourquoi cette conclusion

- **MiCA 2024 + ESMA ban CEX** : depuis janvier 2025, les résidents EU ne peuvent
  plus accéder légalement aux contrats perpétuels Binance/Bybit (applic. ESMA
  guidelines). Toute stratégie CEX-CEX (Binance ↔ Bybit funding arb) est hors
  scope réglementaire pour un résident France.
- **DEX-DEX réglementairement neutre** : les DEX non-custodials (HL, Drift,
  Lighter, Paradex) opèrent sous protocole décentralisé — non visés par
  l'interdiction MiCA sur les "crypto-asset service providers" centralisés.
  Position défendable jusqu'à clarification réglementaire 2026-2027.
- **Décorrélation avec Strategy B** : B exploite sign(HL_funding_rate) en
  delta-neutral. F7 exploite le spread(HL_rate − Drift_rate), orthogonal au
  niveau absolu. Corrélation théorique ≈ 0 (confirmé par construction).
- **Sharpe estimé 0.8-1.6** : basé sur spreads observés HL↔Drift 2024-2025,
  coûts taker 0.045% × 2 legs × 3 rebal/jour ≈ 0.27%/jour. Sur spreads moyens
  observés 0.05-0.15% par période 8h, edge ≥ costs quand spread > 0.09%.

## Valeur pour CV / Interview

Démontre la compréhension du paysage réglementaire crypto EU post-MiCA 2024 —
une évolution majeure que beaucoup de praticiens retail ignorent encore en 2026.
La distinction CEX-CEX (mort) versus DEX-DEX (viable) illustre la capacité à
adapter une thèse d'investissement aux contraintes légales, compétence clé pour
un poste dans un fonds réglementé (AIFM, AMF).

## Conditions de réactivation

- Implémentation pilot HL ↔ Drift DEX-DEX, $25K USDC, Q3 2026.
- Pré-requis : vérifier que l'API Drift on-chain (Solana) supporte l'exécution
  programmatique des orders perp (WebSocket ou RPC Solana).
- Gate d'activation : spread moyen observé live ≥ 0.09% / 8h sur 30 jours
  consécutifs avant déploiement full capital.

## Lien vers deep research

[deep_research.md](deep_research.md)
