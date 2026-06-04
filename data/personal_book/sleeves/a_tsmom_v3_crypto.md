# Strategy A — TSMOM v3 crypto (pointer)

> **Statut** : LIVE personal book, gelé Propr depuis 2026-05-11 (compte breach 3% daily DD). HL testnet daily place encore des fills.
> **Cette fiche est un POINTEUR**, pas la source canonique. Ne pas modifier les chiffres ici sans synchronisation amont.

## Pourquoi dans personal_book

FTMO n'a **pas d'instrument crypto-perp tradeable** au sens du backtest (univers FTMO crypto = CFD spot, pas perps avec funding ; pas de SOL ; pas de leverage 3-5×). Le sleeve est **structurellement hors-FTMO**. Déployable uniquement sur prop spécialisée crypto (Propr — gelé), HL testnet/mainnet, ou compte perso Binance/HL/Bybit.

## Pointeurs canoniques

- **Code live** : `strategies/tsmom_v2_propfirm/signal.py`, `strategies/tsmom_v2_propfirm/execution/`
- **Frozen artifacts (2026-05-30)** : `Crypto/research/archived/_frozen/strategy_a_propr_2026-05-30/`
- **État de référence** : `CLAUDE.md` § « Strategy A — TSMOM v3 »
- **VPS** : cron `5 0 * * *` (HL testnet daily) + `5 0 * * 1` (Propr weekly, gelée). Voir `_audit/verification_2026-05-30.md`.

## Métriques officielles (source CLAUDE.md, ne pas re-mesurer)

| Champ | Valeur |
|---|---|
| Signal | `tanh(cumret_28d / (vol_28d × sqrt(28))).clip(lower=0)` (long-only) |
| Univers | BTC, ETH, SOL |
| Rebalance | Monday 00:05 UTC (Propr) + daily 00:05 UTC (HL testnet) |
| Sharpe OOS | **1,33** |
| MaxDD OOS | **−6,9 %** |
| Vol target live | 0,18 (annualized) |
| Guardrails Propr | daily 2,8 %, total 5,5 % (`execution/__init__.py:46-47`) |
| Ceiling structurel | **~39 % Propr pass rate** (β_crypto floor sous 3 % daily DD) |

## Gate-0 FTMO

- ❌ **Pas de SOL** sur FTMO (univers crypto FTMO ne couvre pas SOL au 2026).
- ❌ **Pas de funding-rate perps** sur FTMO (CFD spot uniquement).
- ❌ Levier insuffisant pour vol-target 0,18 sur compte 2-step.

→ FTMO incompatible structurellement. Pas de proxy fidèle (FX/Indices ne reproduit pas crypto-perp).

## Corrélations connues (à vérifier)

- vs Strategy B (delta-neutral HL) : non explicitement mesurée — devraient être faibles (B = funding carry, A = momentum).
- vs LONG_US500 : crypto vs SPX peu corrélés mais non quantifié dans ce repo.

## Status alternatives propfirm

Voir `PropFirms/comparison.md` pour analyse Apex (EOD trailing, CME futures — potentiel mais analyse pending) vs Propr (gelé).
