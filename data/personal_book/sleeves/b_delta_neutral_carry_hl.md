# Strategy B — Delta-neutral carry HL (pointer)

> **Statut** : LIVE HL testnet depuis 2026-05-17. Mainnet pending (~60-day live required, ~2026-07-17).
> **Cette fiche est un POINTEUR**, pas la source canonique.

## Pourquoi dans personal_book

Delta-neutral funding carry sur perpetuals Hyperliquid (long spot proxy + short perp ou inversement, fonction du signe du funding 8h). **Aucun équivalent FTMO** : FTMO ne propose ni HL, ni perps avec funding, ni spot crypto à shorter contre. Le mécanisme **EST** la dislocation funding entre venues — par construction hors-FTMO.

## Pointeurs canoniques

- **Code live** : `strategies/delta_neutral/live_trader.py`, `hl_perp_client.py`, `universe.py`
- **État de référence** : `CLAUDE.md` § « Strategy B — Delta-neutral carry »
- **VPS** : cron `10 0,8,16 * * *` (toutes 8h aligned funding).
- **Kill switch** : checks `STOP` file each run.

## Métriques officielles (source CLAUDE.md, ne pas re-mesurer)

| Champ | Valeur |
|---|---|
| Univers viable | TST, MEGA, WLD, STX, WIF, BIO, TRUMP, HMSTR |
| Active 2026-05-30 | HMSTR seule (TST/MEGA flat, état volatile — voir VPS state.json) |
| Rebalance | toutes 8h (00:10, 08:10, 16:10 UTC) |
| MIN_VOL_USD | 1 000 000 |
| CARRY_FLOOR_8H | 0,0034 / (30 × 3) |
| NOTIONAL_USD | 50 |
| Sharpe backtest | **4,10** |
| MaxDD backtest | **−0,52 %** |
| Mainnet proxy SR (L14) | **2,0** (testnet N<250, proxy conservateur) |

## Gate-0 FTMO

- ❌ Pas de Hyperliquid sur FTMO.
- ❌ Pas de perps avec funding sur FTMO (CFD spot uniquement).
- ❌ Le mécanisme exige short-leg (CFD short sans funding ≠ short perp avec funding ≠ même P&L).

→ FTMO structurellement incompatible. Pas de proxy.

## Caveats

- **Testnet N<250** → L14 limite à proxy SR=2,0 pour portfolio sim. Backtest 4,10 inadmissible cité tel quel.
- **Funding artificiel sur testnet** : mainnet pourrait diverger. La validation 60 jours mainnet est la barrière de promotion.
- Pair active volatile : NE PAS figer dans CLAUDE.md, lire `state.json` VPS pour la pair courante.

## Corrélations connues

- vs Strategy A : non explicitement mesurée, attendue faible (mécanismes orthogonaux : A = momentum directionnel, B = carry delta-neutre).
- vs equity beta : par construction ~0 (delta-neutre).
