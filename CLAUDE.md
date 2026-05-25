# Algo_claude — Project memory for Claude Code

## Profil
M1 IEF (Ingénierie Économique et Financière), Université de Rennes 1. Solo algo researcher.
Objectif : hedge fund systématique (CFM/Qube/Squarepoint/Jump après M2). Niveau haut :
Python vectorisé, pandas/numpy/statsmodels, VPS Linux, HL REST/WS, Propr/Tradovate API.
Communique en français et en anglais.

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
- Crypto: 0.17% | Futures MNQ: ~$2.15 RT (Tradovate) | Equities: 0.05-0.10%
- FX: 0.15% | Commodity futures: 0.015%

## Live strategies snapshot

### Strategy A — TSMOM v3 (PAUSED — Propr account breached)
- Signal: tanh(cumret_28d / (vol_28d × sqrt(28))).clip(lower=0), long-only
- Vol: log returns, 28-bar window, sqrt(365) annualization — MUST match backtest
- Assets: BTC, ETH, SOL | Rebalance: Monday 00:05 UTC
- Validation: Sharpe 1.33 OOS, MaxDD -6.9%
- VOL_TARGET_LIVE=0.18 | guardrails: MAX_DAILY_DD=2.8%, MAX_TOTAL_DD=5.5%
- Status: NOT LIVE. VPS crons active (state tracking only). Awaiting new propfirm.
- Structural ceiling: 39% Propr pass rate (β_crypto floor, 3% daily DD limit)
- Apex alternative (EOD trailing, CME futures): analysis pending — see PropFirms/comparison.md

### Strategy B — Delta-neutral carry (HL testnet LIVE since 2026-05-17)
- Active pairs: TST + MEGA | Rebalance: every 8h (00:10, 08:10, 16:10 UTC)
- Backtest Sharpe: 4.10, MaxDD: -0.52% | Mainnet proxy Sharpe: 2.0 (per L14)
- VIABLE_ASSETS: TST, MEGA, WLD, STX, WIF, BIO, TRUMP, HMSTR
- MIN_VOL_USD=1_000_000 | CARRY_FLOOR_8H=0.0034/(30×3) | NOTIONAL_USD=50
- Kill switch: checks STOP file on each run
- Status: EXECUTION-VALIDATED, mainnet pending (~60-day live required, ~2026-07-17)

### Strategy C — NQ Opening Momentum iter_10 (Tradeify $25K, paper NOT started)
- Signal: direction of 09:30-09:45 ORB, entry at 09:46 ET
- Filters: VWAP confirmation + gap < 1.2% + opening range ≥ 30pts + $400 SL cap
- TP: 1.5R | SL: min(0.5R, 20pts) | Time stop: 12:30 ET
- Backtest: Sharpe 1.52, MaxDD -13.4%, WF 78% (7/9), N=346
- Sizing: risk-managed — see Futures/live/strategy_c_live/sizing_policy.md
- Broker: Tradeify Select Flex $25K via Tradovate REST API
- Propfirm config: PropFirms/tradeify/rules.md | Simulator: Portfolio/risk/trailing_dd_simulator.py
- Tradeify constants: eval_DD=$1,000 funded_DD=$1,000 lock=$26,100 floor=$25,100  # confirmed 2026-05-25 DO NOT revert to $1,500/$26,600
- VPS cron (été UTC+2): 25 13 * * 1-5 | (hiver UTC+1): 25 14 * * 1-5
- Guardrail: GUARDRAIL_TRAILING_DD_USD — see sizing_policy.md and PropFirms/tradeify/rules.md
- KNOWN GAP: verify VWAP 1-min granularity in Tradovate client before paper start
- Status: BACKTEST-VALIDATED, Tradovate infra built, execution not started

## Portfolio context
- Personal book: A (TSMOM, paused) + B (HL testnet, mainnet ~Jul 2026)
- Propfirm book: C (NQ, Tradeify) + potential D (decorrelated to C)
- A+B+C theoretical: Sharpe 2.24, MaxDD -1.0% (ERC: A=10%, B=68%, C=22% at SR_B=2.0)
- New strategy D gate: Sharpe(A+B+C+D) > 1.10 × 2.24 = 2.46 required
- Propfirms do NOT accept crypto/delta-neutral → A and B stay personal book

## Repo layout
- Live crypto: `strategies/{tsmom_v2_propfirm, delta_neutral}`
- NQ live: `Futures/live/strategy_c_live/` (config, tradovate_client, signal_engine, guardrails)
- Active research: `<AssetClass>/research/active/`
- Archived research: `<AssetClass>/research/archived/`
- Portfolio state: `Portfolio/state/portfolio_state.py`
- Automation:
  - `_automation/alpha_hunt/`: scraper pipeline, `promising/` items staged for feasibility
  - `_automation/feasibility/`: 3-level gate orchestrator + 4 handlers (SkipMonth, ExitRule,
    RegimeFilter, Generic)
  - `_automation/arxiv/`: daily q-fin scan | `_automation/synthesis/`: weekly cross-paper

## Python envs
- Research: /usr/bin/python3
- Live VPS: ~/venv/
- Local venv: <HOME>/Desktop/Unholy returns/Python3.12.9/myenv/

## VPS
- Hetzner CX22, <VPS_IP>, user algo
- SSH: ssh -i ~/.ssh/hetzner_algo_claude algo@<VPS_IP>
- Active crons: TSMOM state (25 0 * * 1), delta-neutral (10 0,8,16 * * *),
  NQ paper (25 13 * * 1-5 summer UTC+2 | 25 14 winter UTC+1)

## Code style
- Production-quality Python: typed, vectorized, pandas/numpy
- No matplotlib in core logic — separate plotting module
- Tests for any function in strategies/ or Portfolio/
- No comments stating the obvious; docstrings for public APIs

## Methodology lessons

### Core (toujours appliquer, 1-10 universels)
1. Signal at T-1, trade at T. No exceptions.
2. Walk-forward > single split. AMTP for multiple-testing correction.
3. Vol scaling essential. Always compute cost drag first.
4. β-dominance: need L/S or multi-asset to avoid beta exposure.
5. ETFs ≠ futures: roll drag contaminates momentum signals on commodity ETFs.
6. Small universe + AMTP = everything fails. N≥30 instruments minimum.
7. Propfirm match: align frequency, sizing, DD model type, consistency cap, DLL (or absence),
   min trading days and lock mechanism to strategy profile. Run trailing_dd_simulator.py
   with firm-specific PropfirmConfig before any purchase. Config: PropFirms/<firm>/rules.md.
8. Excess returns + HAC lag-6 + daily vol targeting mandatory.
9. Crypto fees 0.17% RT | futures ~0.01% RT | equities 0.05-0.10% RT.
10. 3 modifications maximum per strategy to avoid overfitting.

### Crypto structural — registre L (canonique depuis README §6.50)
L11. Long-only CS crypto = β-dominated (port corr_A ≥ 0.80 regardless of IC).
     Only escape: delta-neutral execution.
L12. Event-count ceiling gate: pre-flight must compute [N_floor, N_ceiling] interval.
     At 0.17% RT, ceiling ≈ 29 events/yr per position for 5%/yr net edge.
L12b. Autocorrelation HAC deflation: persistent regime signals (half-life > 30d) →
      N_eff << N_nominal. ETH netflow: naive t=2.58 → HAC t=0.11 (N_eff≈73 from 3398).
L13. VRP unit error: academic VRP magnitude is in variance units, not % notional.
     B-S conversion: BTC gross ~4.4%/yr vs costs 8.9%/yr → net -4.46%/yr.
L14. Testnet Sharpe inadmissible (N<250). SR(B)=9.64 → proxy SR=2.0 for portfolio sim.
L15. Regime overlays on high-Sharpe (SR>1.0) strategies: sub-threshold lift (~1.7%/yr,
     Δ=+0.022%/day). Only useful for strategies with MaxDD>20%.
L17. F&G velocity divergence = momentum proxy (wrong direction). Existing-holder
     sentiment branch CLOSED.
L18. Wikipedia attention velocity = zero IC, momentum proxy direction. New-buyer
     attention branch CLOSED. Both Da et al. taxonomy pathways exhausted.

### Propfirm structural — registre L (à partir de L19)
L19. NQ propfirm market impact: at-market entry 09:46 ET, baseline slippage ≈ 4 ticks RT
     ($2/MNQ). Adverse fills during gap opens or thin pre-mkt: up to 3× baseline. Slippage
     is asymmetric: losing trades near SL suffer most (no recovery room). Apply ≥1.5×
     stress in sizing_analysis.py; 3× for conservative bound. Slippage model validated in
     sizing_analysis.py; full non-linear model (OFI + momentum_velocity) deferred to Topic 3.
L20. DSR (Deflated Sharpe Ratio) mandatory for any strategy with N_modifications ≥ 2.
     Bailey-LdP: SR_DSR = SR × correction(T, N_trials, ρ). iter_10: N_mod=10, T=756d →
     SR_DSR ≈ 1.0-1.1 from reported SR=1.52. Above PROPFIRM_PASS gate (1.0) ✓.
     Apply before citing Sharpe in any research document or propfirm submission.
L21. Sharpe reality check by category (live, post-costs, post-DSR):
     CS academic daily (N≥100 instruments): SR 0.3–1.2.
     Single-instrument day-trade live (NQ ORB class): SR 0.8–2.0 sustainable.
     Delta-neutral crypto carry (mainnet, N<500): SR 1.5–4.0 with high estimation uncertainty.
     Backtest SR >2× expected category range → mandatory DSR/cherry-pick audit before citing.
     iter_10 post-DSR SR ≈ 1.1 ∈ [0.8, 2.0] → consistent with category prior ✓.
L22. MC propfirm eval simulation mandatory before any propfirm purchase (Claude Code session,
     2026-05-24). Four findings: (a) canonical config matters — eval DD=$1,000, funded DD=$1,000,
     lock trigger=$26,100 (capital+DD+$100), simulate both phases separately; (b) consistency cap ($600/day) is binding
     at 4 MNQ (avg winner $628 > cap), reduces P(pass) relative to uncapped; (c) FTMO does not
     support CME futures (NQ/ES/ZN/CL) — confirmed 2026, use Tradeify/Apex/Topstep/MFFU; (d)
     Gaussian generator materially overestimates bust for SL-capped strategies — use calibrated
     trade-based generator. Tool: Portfolio/risk/trailing_dd_simulator.py +
     Futures/research/active/nq_intraday/sizing_analysis.py.

## Methodology toolkit
- **Significance**: HAC Newey-West (lag-6) t-stat, threshold t > 2.5 for IC feasibility
- **Multiple testing**: AMTP when n_tests > 1; DSR (Bailey-LdP) for n_mod > 5
- **Bootstrap**: block bootstrap (Politis-Romano) — iid forbidden when trade clusters exist
- **Walk-forward**: expanding window ≥5 folds (single split forbidden)
- **IC → net Sharpe** (Israel-Jiang-Ross 2017): expected_gross_alpha ≈ 0.40 × IC × √breadth
  × σ_target; require gross > 3×cost_drag. Daily ETF (0.10% RT): IC>0.08. Daily futures
  (0.01% RT): IC>0.04. Monthly-rebal (breadth ~12): cost gate essentially absent.
- **FX carry regime-dependence**: 2005-2007 pre-GFC drives all G10 carry IC. Always check
  per-decade IC breakdown before calling carry feasible.
- **5 mandatory script fixes**:
  1. Excess returns: subtract daily RF (FRED DTB3) from all asset returns
  2. HAC SE: sm.OLS().fit(cov_type='HAC', cov_kwds={'maxlags': 6})
  3. Daily vol targeting: 63d rolling std × √252, sampled at month-ends
  4. TSMOM diagnostics: dir accuracy ≥53%, quintile monotonicity, convexity β test
  5. Honest naming: approx_multi_test_penalty (not "DSR")

## Data sources
- Crypto OHLCV: Binance daily klines (free, unlimited) + HL 4h/1h snapshots
- Funding rates: Hyperliquid 8h, cached CSV in data/funding_carry/
- NQ 1-min: Dataset_NQ_1min_2022_2025.csv (Kaggle, local only, gitignored)
- Commodity futures: yfinance =F tickers (CL=F, GC=F, …) — continuous front-month
- FX M5: Dukascopy bi5 custom decoder in strategy_e_fix_flow/data_setup.py
  Cache: Forex/data/cache/dukascopy_m5/. DL speed: ~12min/pair-year, 4 threads.
- Equities: yfinance + Tiingo (limited free tier)
- FRED: DTB3 (RF daily), interbank rates monthly
- HL API constraint: no candle data before Nov 2022; gap Dec 2022–Dec 2023

## Research history (n_tests = 321 global)
<!-- Sequential global milestones (README §6.55 authoritative, confirmed line 1594):
     = 83  equities/ETF/options sub-total (README §10): includes crypto-era tests 1–53,
           FX carry 4, multi-asset 5+1, NQ ORB IVB 3, equities 14, options 1
     = 142 crypto V1 OHLCV missions complete (6.01–6.36, README §6.51 missions table)
     = 159 all crypto missions complete (V1+V2+V3, README §6.55 cumulative)
     = 170 FX London ORB v1 archived (+28 from base = 142)
     = 175 Strategy E pre-registration (+1 after Strategy D closure at n=174)
     = 180 Round Number Cascade complete (+5 EUR/GBP IC horizons, n=175→180)
     = 321 final: after NQ iter_1–10 (~82+ NQ sub-count), indices_swing Sprint 1+2 (100),
           and remaining crypto V2/V3 + options VRP phases
     IMPORTANT: sub-counts (83 equities, 159 crypto, 180 FX) overlap — the
     53 crypto-era equities count in both the equities 83 AND the crypto 159.
     Do NOT add sub-counts; only the sequential milestones above are additive. -->

### ✓ Validated and live/ready
- Crypto TSMOM v3 (Strategy A, Sharpe 1.33 OOS)
- Delta-neutral carry HL (Strategy B, proxy Sharpe 2.0)
- NQ opening momentum iter_10 (Strategy C, Sharpe 1.52)

### Active research (in progress)
- **Strategy D — D3+D5 portfolio** (Futures, propfirm-targeted, decorrelated to C):
  D3 (Opening range mid-fade 09:45-11:00, n_test=156, corr_C=-0.21) +
  D5 (Afternoon BB squeeze breakout 14:00-15:30, n_test=158, corr_C=-0.05).
  Both failed individually (Sharpe=-1.08/-1.32); portfolio combination + regime filter
  under study. Pre-registration in progress.
  `Futures/research/active/nq_intraday/analysis/` | Budget: 3 mods, 0 consumed.
- **Strategy E — WMR Fix + EOM USD Flow** (FX, n_reg=175): H1 = fade 30-min pre-fix
  drift at 15:57 London; H2 = short USD EOM when SPX MTD > MSCI ex-US by 2%.
  BLOCKER: Dukascopy M5 download ~12h (6 pairs × 10 years).
  `Forex/research/active/strategy_e_fix_flow/` | Budget: 3 mods, 0 consumed.
- **Commodities XS — Basis + TSMOM** (n≤279): S_TSMOM (Moskowitz 2012) + S_BASIS
  (Erb-Harvey 2006), 24 continuous contracts, monthly CS IC scan.
  Phase A (data fetch + roll validation) not yet complete.
  `Commodities/research/active/xs_basis_tsmom/`

### ✗ Archived — DO NOT re-propose without strong new evidence

**Crypto (n=159, free-data EXHAUSTED — 7 missions, 11 signal families)**
- All long-only CS: β-dominance (L11) kills every signal regardless of IC
- Delta-neutral: PMR basis (IC real but 912 events/yr → 178%/yr cost drag, L12),
  OAGF (128/yr sparse, L12 floor), CS-FS (t=1.54), FRA (t=1.01 regime-specific)
- On-chain: MVRV (momentum proxy, corr_A=0.73), netflow (HAC deflation, L12b)
- Options VRP Deribit: gross 4.4%/yr, costs 8.9%/yr (L13). 0/13 WF folds positive.
- Macro overlay, FGVD sentiment (L17), Wikipedia attention (L18)
- Remaining viable paths: Glassnode stablecoin (~$500/mo) or maker rebate execution

**FX (running total at closure: n=180)**
- G10 carry (FX-1 to FX-4): dead post-GFC (2005-2007 artifact, IC=-0.028 on 2013-2023)
- CS momentum, TSMOM G10: dead post-Menkhoff (central bank anchoring)
- London ORB v1 (n=170): best t_HAC=1.01 (GBPUSD), below gate 1.65
- Round Number Cascade (n=180): all IC horizons FAIL (EUR: t=1.167→-2.357; GBP: all FAIL)
- BIS REER ≠ bilateral USD valuation: unsuitable as carry signal modifier

**Equities/ETF/Futures**
- D1 (Failed ORB fade, n_test=154): NQ fade when iter_10 signal fires then reverses 0.5R/30min.
  Sharpe=-0.14, IC_t=1.55 (below gate 2.5), WF=66.7%, corr_C=-0.04. Edge absent post-costs.
  Decorrelation from C confirmed. Lit: Brock et al. (1992), Lo-Mamaysky-Wang (2000). ARCHIVED.
- D4 (Lunch RSI reversal, n_test=157): NQ 12:00-13:00 30-min RSI mean reversion.
  Sharpe=-0.70, IC_t=1.61 (below gate 2.5), WF=22.2%, corr_C=-0.02. No edge detected.
  Lit: Wilder (1978), Jain & Joh (1988) intraday seasonality. ARCHIVED.
- Multi-asset TSMOM: Sharpe 0.21 corrected (HAC+excess returns), alpha t=1.31
- Pairs cointegration (0/19 qualify), Gatev distance (Sharpe -0.44, t=-2.5)
- VIX term carry (Sharpe 0.67, alpha t=0.71 insufficient)
- Sector reversal (Sharpe -0.60, t=-3.7 negative alpha)
- Commodity TSMOM ETF (Sharpe 0.39, AMTP p=0.808 — ETF roll drag)
- NQ VWAP MR / afternoon momentum: all FAIL ($19 RT cost kills any edge)
- NQ ORB IVB (Conti/Valentini): Sharpe -0.09/-0.44, 0/5 propfirm gates
- Equity indices_swing Sprint 1+2 (100 tests): IC 0.033-0.075, all fail backtest
  (best Sharpe 0.45 at futures cost, costs kill at ETF level)
- NQ Pairs ES/NQ: EG p=0.28 (tech premium drift 2024-2026 destroys stationarity)
- Network Momentum GMOM: universe too small (N<64), graph density=1.0 → FAIL

**Options (n=1)**
- SPX VRP Angle C (VIX_z conditional): IC t=-0.144, wrong direction
- BTC VRP Deribit (n=156): gross 4.4%/yr, costs 8.9%/yr (L13)

### Deferred — promising but blocked
- D2 (VWAP touch fade post-noon, n_test=155): NQ 11:30-14:00 momentum exhaustion fade.
  Sharpe=-1.48, IC_t=-0.86 (wrong direction), corr_C=-0.005. Signal directionally inverted —
  deferred pending regime-conditional retesting. `Futures/research/active/nq_intraday/analysis/`

### Untested — requires paid data or new infra
- Glassnode stablecoin mint/burn (~$500/mo) — only remaining crypto angle with
  theoretical zero TSMOM corr
- Apex challenge analysis for Strategy A (EOD trailing, CME futures): expected pass rate
  improvement over Propr — see PropFirms/comparison.md
- Token unlock cliff shorts (TokenUnlocks.app, free)
- HLP vault flow contrarian, Uniswap V3 LP rebalancing (HL API + The Graph, free)
- GitHub commit velocity as dev proxy (GitHub REST API, free)
- BTC cross-exchange lead-lag Coinbase→Binance (Shu 2023) — multi-venue WebSocket

## Automation infrastructure
- `_automation/alpha_hunt/`: VPS cron scrapes Reddit/HN/Quantocracy/SSRN/GitHub,
  applies L0/L1/L2 filters, stages items in `promising/`. Dedup via `_seen.json`.
- `_automation/feasibility/`: 3-level gate pipeline (A: IC; B: WF+bootstrap+DSR;
  C: sanity checks). Handlers dispatch by hypothesis type (SkipMonth, ExitRule,
  RegimeFilter, Generic fallback).
- Routines run on Anthropic cloud — no external API access, repo data only.
- Each routine commits to `claude/<routine-name>-<date>` and opens a PR.

## Current focus
→ see `_meta/current_focus.md` (updated each session; contains blockers, in-progress work,
  next priorities — séparé de ce fichier constitutionnel pour éviter la dette de maintenance)

## Parallel session coordination (READ BEFORE LAUNCHING /goal)
- Before any /goal: run `git pull origin main` and read this CLAUDE.md.
- Never create parallel infrastructure folders without checking existing live/ first.
- Strategy C canonical live infra: Futures/live/strategy_c_live/ (NOT strategy_c_paper/).
- strategy_c_paper/: ONLY pre-existing log infra (log_trade.py, paper_trade_log.csv).
- For new asset classes, check Research history before assuming nothing was tested.
