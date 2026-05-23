# Algo_claude — Project memory for Claude Code

## Hard rules (NEVER violate)
- Signal at T-1, trade at T. No exceptions.
- Excess returns (vs cash rate), HAC lag-6, AMTP if n_tests > 1.
- Walk-forward ≥5 folds — never single split.
- Daily vol targeting.
- N ≥ 30 instruments for cross-sectional strategies.
- Max 3 modifications per strategy hypothesis.

## Two-tier gates
- RESEARCH_PASS: Sharpe>0.7, MaxDD<-25%, WF>50%
- PROPFIRM_PASS: Sharpe>1.0, MaxDD<-10%, WF>60%

## Costs (round-trip)
- Crypto: 0.17% | Futures: ~0.01% | Equities: 0.05-0.10%

## Live strategies snapshot

### Strategy A — TSMOM v3 propfirm (LIVE on Propr)
- Signal: tanh(cumret_28d / (vol_28d × sqrt(28))).clip(lower=0)
- Assets: BTC, ETH, SOL | Rebalance: Monday
- Validation: Sharpe 1.33 OOS, MaxDD -6.9%

### Strategy B — Delta-neutral carry (LIVE on HL testnet)
- Active pairs: TST + MEGA | Rebalance: every 8h
- Backtest Sharpe: 4.10, MaxDD: -0.52%
- Caveat: testnet funding artificial, mainnet deployment pending

### Strategy C — NQ opening momentum (BACKTEST ONLY, paper imminent)
- Signal: direction of 09:30-09:45 ORB
- Filters: VWAP confirmation + gap≤1.2% + opening range≥30pts + $400 SL cap
- TP: 1.5R | SL: min(0.5R, 20pts) | Time stop: 12:30 ET
- Backtest: Sharpe 1.52, MaxDD -13.4% rel / -9.5% on $50K, WF 78%, N=346

## Repo layout
- Live code: `strategies/{tsmom_v2_propfirm, delta_neutral}`
- Active research: `<AssetClass>/research/active/`
- Archived: `<AssetClass>/research/archived/`
- Portfolio state: `Portfolio/state/portfolio_state.py`
- Routine outputs: `_automation/` (do not modify manually)

## Python envs
- Research: /usr/bin/python3
- Live VPS: ~/venv/

## VPS
- Hetzner CX22, <VPS_IP>, user algo
- SSH from Mac: ssh -i ~/.ssh/hetzner_algo_claude algo@<VPS_IP>

## Code style
- Production-quality Python: typed, vectorized, pandas/numpy
- No matplotlib in core logic — separate plotting module
- Tests for any function in strategies/ or Portfolio/
- No comments stating the obvious; docstrings for public APIs

## Methodology lessons (key ones)
1. Signal at T-1, trade at T. No exceptions.
2. Walk-forward > single split. AMTP for multiple-testing correction.
3. Vol scaling essential. Always compute cost drag first.
4. β-dominance: need L/S or multi-asset to avoid beta exposure.
5. ETFs ≠ futures: roll drag contaminates momentum signals on commodity ETFs.
6. Small universe + AMTP = everything fails. N≥30 instruments minimum.
7. Propfirm match: align strategy frequency and sizing to propfirm rules.
8. Excess returns + HAC lag-6 + daily vol targeting mandatory.
9. Crypto fees 0.17% RT | futures ~0.01% RT | equities 0.05-0.10% RT.
10. 3 modifications maximum per strategy to avoid overfitting.
