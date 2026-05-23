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

### Strategy A — TSMOM v3 (PAUSED — Propr breach)
- Signal: tanh(cumret_28d / (vol_28d × sqrt(28))).clip(lower=0) — long-only
- Vol: log returns, 28-bar window, sqrt(365) annualization (MUST match backtest)
- Assets: BTC, ETH, SOL | Rebalance: Monday 00:05 UTC
- Validation: Sharpe 1.33 OOS, MaxDD -6.9%
- Status: NOT LIVE (Propr account breached). Methodology validated, awaiting new propfirm deployment.
- VPS crons still active for state tracking but not trading live capital.

### Strategy B — Delta-neutral carry (LIVE on HL testnet since 2026-05-17)
- Active pairs: TST + MEGA | Rebalance: every 8h (00:10, 08:10, 16:10 UTC)
- Backtest Sharpe: 4.10, MaxDD: -0.52%
- Cumulative carry to date: ~$16.43 (testnet, artificial rates)
- Status: EXECUTION-VALIDATED, CARRY-PROXIED (mainnet pending, 60-day live required)

### Strategy C — NQ opening momentum iter_10 (IN PROGRESS, paper trade pending)
- Signal: direction of 09:30-09:45 ORB, entry at 09:46 ET
- Filters: VWAP confirmation + gap < 1.2% + opening range ≥ 30pts + $400 SL cap
- TP: 1.5R | SL: min(0.5R, 20pts) | Time stop: 12:30 ET
- Sizing target: 5-10 /MNQ on $50K (pending block bootstrap P(bust) analysis)
- Backtest: Sharpe 1.52, MaxDD -13.4% rel / -9.5% on $50K, WF 78% positive (7/9), N=346
- Cross-validated: ES + YM directionally confirm (60-day yfinance sample)
- Data: Kaggle NQ 1-min 2022-2025 (Dataset_NQ_1min_2022_2025.csv, gitignored)
- KNOWN GAP: backtest uses VWAP 1-min, live infra uses VWAP 5-min — to reconcile before paper start
- Target propfirm: Tradeify (Topstep abandoned, Propr breached)
- Status: BACKTEST-VALIDATED, paper infra built, execution not started

  ## Portfolio context
- A+C theoretical: Sharpe 1.5-1.7, corr(A,C) ≈ 0.015 (validated)
- A+B+C theoretical: Sharpe 2.24, MaxDD -1.0% (ERC sizing, B backtest-proxied)
- Two narratives:
  - Personal book: A (crypto TSMOM) + B (HL delta-neutral, mainnet pending)
  - Propfirm book: C (NQ momentum) + potential D (decorrelated NQ strategy)
- Propfirms do NOT accept crypto/delta-neutral → A and B stay personal

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
11. IC → net Sharpe translation requires turnover-aware cost gate, NOT IC threshold alone. Empirical translation factor: SR_real / (IC × √breadth × σ_target) ≈ 0.35–0.45 (Israel-Jiang-Ross 2017, "Craftsmanship Alpha"). Before launching a full backtest: (1) expected_gross_alpha ≈ 0.40 × IC × √breadth × σ_target; (2) expected_cost_drag = avg_turnover_per_year × cost_per_RT; (3) require gross_alpha > 3 × cost_drag. Daily-rebal ETF signals (0.10% RT): require IC > 0.08. Daily-rebal futures (0.01% RT): require IC > 0.04. Monthly-rebal (breadth ~12): cost gate essentially absent.
12. FX carry IC is regime-dependent: 2005-2007 pre-GFC boom drives all positive carry IC in G10. Always check per-decade IC breakdown before calling carry feasible.
13. BIS trade-weighted REER ≠ bilateral USD valuation: unsuitable as carry signal modifier for USD-base FX positions.

## Methodology toolkit
- **Significance**: HAC lag-6 (Newey-West) t-stat, threshold t > 2.5 for IC feasibility
- **Multiple testing**: AMTP (Adjusted Multiple-Testing P-value) when n_tests > 1
- **Sharpe deflation**: DSR (Deflated Sharpe Ratio) for backtests >5 modifications
- **Bootstrap**: block bootstrap (Politis-Romano) for serially-correlated P&L,
  iid bootstrap forbidden when trade clusters exist (e.g. Strategy C max 1 trade/day)
- **Walk-forward**: expanding window ≥5 folds (single split forbidden)
- **TSMOM diagnostics**: cumulative return decomposition, vol scaling impact
- **IC feasibility**: 30-min budget, Spearman cross-sectional IC + t-stat on mean

  ## Data sources
- Crypto prices: cached parquet in data/raw/, Hyperliquid 8h OHLCV + funding
- NQ 1-min: Dataset_NQ_1min_2022_2025.csv (Kaggle, local only, gitignored)
- ES/YM cross-validation: yfinance (60-day intraday limit, partial only)
- FX: FRED 3M interbank rates (monthly, forward-filled to weekly)
- Equities: yfinance + Tiingo (limited free tier)
- Funding rates: Hyperliquid 8h, stored in data/funding_carry/


## Automation infrastructure
- VPS crons (active): see VPS `crontab -l` (do NOT modify from routine sessions)
- Routine outputs: `_automation/<category>/YYYY-MM-DD.md`
  - `arxiv/`: daily q-fin scan + alpha analysis (deduplicated via _seen.json)
  - `synthesis/`: weekly cross-paper synthesis (to be created)
  - `code_health/`, `methodology/`: planned
- VPS data fetchers: `scripts/*.sh` push raw data to repo (e.g. arxiv XML)
- Routines run on Anthropic cloud, restricted network (use repo data, not external APIs)
- Each routine commits to `claude/<routine-name>-<date>` branch and opens a PR

## Research history (n_tests = 274)

### ✓ Validated and live/ready
- Crypto TSMOM tanh + vol scaling (Strategy A)
- Delta-neutral carry HL (Strategy B)
- NQ opening momentum iter_10 (Strategy C)

### ✗ Archived with reason (DO NOT re-propose without strong new evidence)
- FX carry G10 (4 tests): t < 2.5 with FRED 3M rates, edge insufficient post-2018
- FX carry G10+EM, FX CS momentum, FX TSMOM: similar — all archived
- Modified FX carry G10 à la Macrosynergy (n=173-174, Phase 1 IC FAIL): raw carry IC +0.022 is entirely a 2005-2007 pre-GFC artifact (IC=-0.028 on 2013-2023). BIS REER modification reduces IC further (-0.010). G10 carry is structurally dead post-GFC. DO NOT re-propose without strong evidence of post-2020 carry recovery.
- Equity momentum 73 large caps (8+ tests): β-dominance, edge dies after costs
- Equity pairs cointegration (Gatev distance + Engle-Granger): ADF rejects everything 2024-2025
- Sector reversal, multi-asset TSMOM equities: archived
- VIX term structure carry (3 tests): edge died post-2020
- Network Momentum GMOM (4 tests): universe too small (N<64), graph density=1.0
- TSMOM on commodity ETFs (4 tests): ETF roll drag contaminates momentum signal
- NQ VWAP mean reversion (4 iter): NQ afternoon is momentum-continuation, not MR
- NQ afternoon momentum (4 iter): edge insufficient after costs
- Equities indices swing IC scan (100 tests: 92 IC + 8 backtest): 12 IC-GO signals (S1 VRP + S2 VIX term), ALL fail full backtest. Root cause: IC 0.033–0.075 too small; daily turnover 33–72×/yr; gross Sharpe 0.18–0.47 eaten by 2–5%/yr cost drag. Even at futures costs (0.01% RT), best achievable = 0.45 Sharpe (S1 QQQ). DO NOT re-propose without IC > 0.10 (ETF) or IC > 0.06 (futures).


## Parallel session coordination (READ BEFORE LAUNCHING /goal)
- This repo is accessed by multiple Claude.ai chats AND Claude Code sessions.
- Before any /goal: run `git pull origin main` and read this CLAUDE.md.
- Never create parallel infrastructure folders without checking existing live/ first.
- Strategy C canonical live infra: Futures/live/strategy_c_live/ (NOT strategy_c_paper/).
- strategy_c_paper/ contains ONLY pre-existing log infra (log_trade.py, paper_trade_log.csv).
- For new asset classes, check the Research history section before assuming nothing was tested.
