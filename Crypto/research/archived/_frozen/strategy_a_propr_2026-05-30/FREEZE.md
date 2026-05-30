# Strategy A (TSMOM Propr) — Freeze 2026-05-30

**Date du gel** : 2026-05-30
**Raison du gel** : pas de stratégie crypto viable (L11 β-dominance, Crypto free-data exhausted)
+ Propr structurellement trop restrictif (3% daily DD plafonne le pass rate à ~39%).

## Sources de vérité

| Affirmation | Preuve |
|---|---|
| Propr compte breach 2026-05-11 | `_audit/verification_2026-05-30.md:25` ; `logs/tsmom_v2_cron.log` file size 15012 bytes inchangé depuis 2026-05-11 16:44 UTC |
| HL testnet daily continue de placer des fills | `_audit/verification_2026-05-30.md:22,25` ; `fills.csv` ligne 2026-05-28 SOL sell ; `tsmom_trades.csv` ligne 2026-05-30 |
| Cron weekly Propr réelle = `5 0 * * 1` (≠ CLAUDE.md:86 `25 0 * * 1`) | `_audit/verification_2026-05-30.md:24,37` (`crontab -l` VPS) |
| Cron daily HL testnet `5 0 * * *` non documentée dans CLAUDE.md | `_audit/verification_2026-05-30.md:35` |
| Plafond structurel Propr 39% pass rate | CLAUDE.md:34 — β_crypto floor + 3% daily DD limit |

## Chemins originaux (CONSERVÉS — retrait manuel après validation)

| Composant frozen | Original |
|---|---|
| `tsmom_v2_propfirm/` | `strategies/tsmom_v2_propfirm/` |
| `tsmom_v3/` | `strategies/tsmom_v3/` |
| `tsmom_live.py` | `tsmom_live.py` (root) |
| `challenge_state.db` | `challenge_state.db` (root, SQLite état Propr) |

**Exclus du freeze (par décision utilisateur 2026-05-30)** :
- `*.png` (3 MB de visualisations backtest, reproductibles via `backtest_v2.py` / `tsmom_v3/backtest.py`)
- `__pycache__/` (bytecode)
- `strategies/tsmom_v2_propfirm/execution/__pycache__/` idem

## Composition figée

### Signal et sizing
- **Signal** : `tanh(cumret_28d / (vol_28d × √28)).clip(lower=0)`, long-only
  → `tsmom_v2_propfirm/signal.py:69` ; `tsmom_v3/signal.py` variant
- **Univers candidat** : 14 tickers (`tsmom_v2_propfirm/config.py:20-35`) ; BTC/ETH/SOL en pratique
  post-filtre liquidité mainnet
- **Vol target live** : 0.18 (`tsmom_v2_propfirm/config.py:46`)
- **Rebalance weekly** : Monday 00:05 UTC sur Propr (cron VPS `5 0 * * 1`)
- **Rebalance daily** : 00:05 UTC sur HL testnet via `tsmom_live.py` (cron `5 0 * * *`)

### Guardrails (Propr-spécifiques)
- `MAX_DAILY_DD = 0.028` (Propr 3% limit, buffer 0.2%) → `execution/__init__.py:46`
- `MAX_TOTAL_DD = 0.055` (Propr 6% limit, buffer 0.5%) → `execution/__init__.py:47`
- ⚠ Doublon non canonique : `config.py:55-56` définit `MAX_DAILY_DRAWDOWN=0.045` et
  `MAX_TOTAL_DRAWDOWN=0.09` (HyroTrader/Breakout-style, jamais consommé par le pipeline
  Propr live). À traiter dans LOT 4 canonicalisation FTMO.

### Métriques OOS documentées (source unique : docstring `signal.py:13`)
- Sharpe 1.33 vs binaire 1.22
- MaxDD −6.9% vs binaire −12.7%
- WF 3/4 folds positifs
- `results.json` formel : **INTROUVABLE** (`_audit/verification_2026-05-30.md:122`)

## Comment redéployer (recette de reprise)

1. **Restauration code stratégie** :
   ```bash
   cp -r Crypto/research/archived/_frozen/strategy_a_propr_2026-05-30/tsmom_v2_propfirm/ \
         strategies/tsmom_v2_propfirm/
   cp -r Crypto/research/archived/_frozen/strategy_a_propr_2026-05-30/tsmom_v3/ \
         strategies/tsmom_v3/
   cp Crypto/research/archived/_frozen/strategy_a_propr_2026-05-30/tsmom_live.py \
      tsmom_live.py
   ```

2. **Restauration état Propr** (à ÉVALUER) :
   ```bash
   cp Crypto/research/archived/_frozen/strategy_a_propr_2026-05-30/challenge_state.db \
      challenge_state.db
   ```
   ⚠ État Propr figé au 2026-05-11 (date du breach). Pour un redémarrage propre sur
   nouvelle propfirm : **repartir d'un état neuf**, ne pas restaurer la DB.

3. **Reconfigurer guardrails selon nouvelle propfirm** :
   - Propr (3%/6%) : valeurs actuelles `execution/__init__.py:46-47` OK
   - FTMO (5%/10%) : voir LOT 4 (canonical) — à appliquer après LOT 4 mergé
   - Tradeify : non applicable (Tradeify = futures CME, pas crypto)

4. **Adaptateur exchange** :
   - Propr-only : code natif `propr_sdk.py`
   - Tout autre exchange : **réécrire l'adaptateur** ; Propr REST ≠ standard CCXT

5. **VPS crons (post-freeze, recommandé)** :
   - Daily HL testnet : `5 0 * * *` (inchangé)
   - Weekly Propr/nouvelle propfirm : **`15 0 * * 1`** (décalé de `5 0 * * 1` pour éliminer
     la collision lundi 00:05 — cf. LOT 7 audit diff cron)

## Limites structurelles (NE PAS oublier en redéployement)

- **L11 β-dominance** : long-only CS crypto = portfolio corrélé ≥ 0.80 à BTC, peu importe l'IC.
  Seule échappée : delta-neutral execution (cf. Strategy B `delta_neutral/`).
- **Propr structural ceiling** : ~39% pass rate (β_crypto floor × 3% daily DD).
- **FTMO ne supporte pas crypto perps** (L22(c), confirmé 2026) : aucun port direct
  Propr→FTMO pour A.
- **Apex EOD trailing, CME futures** : A non portable (CME ≠ crypto). Voir
  `PropFirms/comparison.md` pour la matrice.

## Statut au moment du freeze

- Propr : **gelé depuis 2026-05-11 16:44 UTC**, cron Monday active mais sans effet (compte breach)
- HL testnet : **daily continue de placer des fills** via `tsmom_live.py`, jamais paused
- État sur disque : `challenge_state.db` (Propr), `state.json` (HL testnet, hors freeze car
  partagé avec Strategy B)
- Originaux **NON SUPPRIMÉS** — retrait manuel après validation du gel par l'utilisateur.
