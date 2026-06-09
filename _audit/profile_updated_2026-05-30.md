# Algo_claude — Project memory for Claude Code (PROPOSED UPDATE 2026-05-30)

> **NOTE AUDIT** : Version corrigée proposée du `CLAUDE.md` actuel. Les corrections
> factuelles citent leur source `fichier:ligne`. Les zones runtime/externes sont
> balisées `[À CONFIRMER MANUELLEMENT — raison]` et conservent la valeur actuelle
> par défaut. **À VALIDER avant overwrite de CLAUDE.md**.

## Profil
M1 IEF (Ingénierie Économique et Financière), Université de Rennes 1. Solo algo researcher.
Objectif : hedge fund systématique (CFM/Qube/Squarepoint/Jump après M2). Niveau haut :
Python vectorisé, pandas/numpy/statsmodels, VPS Linux, HL REST/WS, Propr (historique, paused),
Tradovate (Strategy C paper), MT5 (Voie B FTMO). Communique en français et en anglais.

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

### Strategy A — TSMOM v2/v3 (PAUSED — Propr account breached)
- Signal: `tanh(cum_log_ret_28d / (vol_28d × √28)).clip(lower=0)`, long-only
  (cf. `strategies/tsmom_v2_propfirm/signal.py:61-72`, lookback=28d)
- Vol intra-fenêtre = std des log-returns × √28 pour normaliser le t-stat
  (annualisation √365 appliquée hors signal, dans `backtest_v2.py`)
- Universe candidats : 14 tickers (BTC, ETH, SOL, AVAX, LINK, DOGE, ADA, DOT, UNI, LTC,
  BCH, MATIC, OP, ARB) cf. `config.py:20-35` ; **filtré à BTC/ETH/SOL en pratique
  (mainnet liquidity filter)**
- Rebalance: Monday 00:05 UTC, weekly (logique dans `signal.py:97-105` via dayofweek)
- Validation: Sharpe 1.33 OOS, MaxDD -6.9%, WF 3/4 folds (commentaire `signal.py:13`)
  ⚠ `results.json` formel **[INTROUVABLE]** — chiffres documentés en commentaire only
- VOL_TARGET_LIVE=0.18 (`config.py:46`)
- Guardrails canoniques (execution layer Propr) : MAX_DAILY_DD=2.8%, MAX_TOTAL_DD=5.5%
  (`execution/__init__.py:46-47`). **NB** : `config.py:55-56` définit aussi
  `MAX_DAILY_DRAWDOWN=4.5%` et `MAX_TOTAL_DRAWDOWN=9%` pour le profil "HyroTrader" —
  doublon à harmoniser ou commenter explicitement comme "non utilisé en live Propr".
- Status: NOT LIVE. **[À CONFIRMER VIA SSH]** que les crons VPS sont effectivement
  en mode "state tracking only" (cf. divergence wrapper `run_tsmom.sh` vs profil).
- Structural ceiling: 39% Propr pass rate (β_crypto floor, 3% daily DD limit)
- Apex alternative (EOD trailing, CME futures): analysis pending — see PropFirms/comparison.md
- FTMO Voie B pivot: `Futures/research/active/voie_b_ftmo/` — full study (reconciliation.md,
  slip_analysis.py, weekly_realtape) ; MT5 EA `Voie_B_EA_fixed.mq5`. **[À CONFIRMER]** :
  sous-jacent ciblé (indices ? FX ?).

### Strategy B — Delta-neutral carry (HL testnet LIVE since 2026-05-17)
- Active pairs : **[À CONFIRMER VIA LOGS VPS]** — state.json absent localement,
  `data/delta_neutral/live_state/` vide ; valeur précédemment documentée : "TST + MEGA"
- Rebalance: every 8h (00:10, 08:10, 16:10 UTC) cf. `run_delta_neutral.sh:6` et
  `live_trader.py:10` (docstring à corriger : indique "08:05/16:05" erronés)
- Backtest Sharpe: 4.10, MaxDD: -0.52% ⚠ **[INTROUVABLE]** — chercher results.json
  d'origine dans `Crypto/research/archived/carry/funding_carry/`
- Mainnet proxy Sharpe: 2.0 (per L14, l.127)
- VIABLE_ASSETS: TST, MEGA, WLD, STX, WIF, BIO, TRUMP, HMSTR (`live_trader.py:88`) ✓
- MIN_VOL_USD=1_000_000 | CARRY_FLOOR_8H=0.0034/(30×3) | NOTIONAL_USD=50 | MAX_ASSETS=5
- Kill switch: checks `STOP` file on each run (`live_trader.py:90` — STOP_PATH)
- Status: EXECUTION-VALIDATED, mainnet pending (~60-day live required, ~2026-07-17)
  **[À CONFIRMER VIA LOGS VPS]** que la cron tourne effectivement depuis 2026-05-17

### Strategy C — NQ Opening Momentum iter_10 (Tradeify $25K, paper NOT started)
- Signal: direction of 09:30-09:45 ORB, entry at 09:46 ET (`config.py:69-71`)
- Filters: VWAP confirmation (`signal_engine.py:152-158`) + gap < 1.2% (`config.py:80`)
  + opening range ≥ 30pts (`config.py:81`) + $400 SL cap (`config.py:77`)
- TP: 1.5R | SL: min(0.5R, 20pts) | Time stop: 12:30 ET (`config.py:72,75-78`)
- Backtest iter_10 (`nq_intraday/results.json` l.966-990) : Sharpe 1.52, MaxDD -13.4%,
  WF extended 78% (7/9), WF raw 100% (9/9), n_trades=346
- Sizing: 2 MNQ all phases (PHASE_CONTRACTS = {2,2,2}, `config.py:58-63`)
  cf. `sizing_policy.md` (2026-05-24)
- Broker: Tradeify Select Flex $25K via Tradovate REST API (`config.py:41`)
- Propfirm config: `PropFirms/tradeify/rules.md` | Simulator: `Portfolio/risk/trailing_dd_simulator.py`
- Tradeify constants : eval_DD=$1,000 funded_DD=$1,000 lock=$26,100 floor=$25,100
  (`config.py:101-107`, confirmé 2026-05-25)
- VPS cron (été UTC+2): `25 13 * * 1-5` | (hiver UTC+1): `25 14 * * 1-5`
  (`config.py:22-26`) **[À CONFIRMER VIA SSH]** présence effective
- Guardrails : GUARDRAIL_TRAILING_DD_USD=850 ($150 buffer avant $1,000 limit, `config.py:122`),
  GUARDRAIL_POST_LOCK_FLOOR=25_175 (`config.py:123`), GUARDRAIL_DAILY_SELF_LIMIT=400 (l.125)
- KNOWN GAPS (cf. `_meta/current_focus.md:10-15`):
  - BLOCKER 1: verify VWAP 1-min granularity in `tradovate_client.py`
  - BLOCKER 2: Tests 1+3 (connexion live/demo) non exécutés
- Status: BACKTEST-VALIDATED, Tradovate infra built, execution not started

## Portfolio context
- Personal book: A (TSMOM, paused) + B (HL testnet, mainnet ~Jul 2026)
- Propfirm book: C (NQ, Tradeify) + potential D (decorrelated to C)
- A+B+C theoretical: Sharpe 2.24, MaxDD -1.0% (ERC: A=10%, B=68%, C=22% at SR_B=2.0)
- New strategy D gate: Sharpe(A+B+C+D) > 1.10 × 2.24 = 2.46 required
- Propfirms do NOT accept crypto/delta-neutral → A and B stay personal book

## Repo layout
- **Asset classes** (8) : `Crypto/`, `Futures/`, `Forex/`, `Commodities/`, `Equities/`,
  `Multi_Asset/`, `ETF_Vol/`, `Options_Vol/` — chacune avec `research/{active,archived,passed?}/`
- **Live crypto** : `strategies/{tsmom_v2_propfirm, delta_neutral, tsmom_v3}/`
  - `tsmom_v3/` = variante recherche dérivée v2 (signal.py + backtest.py, MAJ 2026-05-16)
- **NQ live/paper** : `Futures/live/strategy_c_live/` (canonical, voir `## Parallel session`),
  `Futures/live/strategy_c_paper/` (log infra historique uniquement)
- **Active research** : `<AssetClass>/research/active/` — voir `## Active research` (synchronisé)
- **Archived research** : `<AssetClass>/research/archived/`
- **Passed research** : ⚠ `Equities/research/passed/` et `Forex/research/passed/` contiennent
  des stratégies **failed mal classées** (jt_momentum_cs, fx_carry_trend) — à reclasser.
- **Portfolio** : `Portfolio/{state, risk, validation, reporting, integration}/`
  - state: `portfolio_state.py` | risk: `trailing_dd_simulator.py`, `sizing.py`, `correlation.py`
- **PropFirms** : `PropFirms/{apex,mffu,phidias,topstep,tradeify}/{rules.md,sources.md}` +
  `comparison.md`, `README.md`
- **Meta/audit** : `_meta/{current_focus.md, open_questions.md}` | `_audit/` (audit reports)
- **Data caches** : `data/panels/` (CSV alpha-hunt panels), `data/funding_carry/`,
  `data/delta_neutral/`, `Forex/data/cache/dukascopy_m5/` (gitignored)
- **Legacy root scripts** (MLP deprecated) : `hyperliquid_client.py`, `monitor.py`,
  `notifier.py`, `dsr.py`, `Dataset_NQ_1min_2022_2025.csv` (72 MB, gitignored)
- **Automation** :
  - `_automation/alpha_hunt/` : scraper VPS (Reddit/HN/Quantocracy/SSRN/GitHub/arxiv),
    `_raw/ → _staging/ → promising/`. Dedup `_seen.json`. ✓ opérationnel.
  - `_automation/feasibility/` : 3-level gate orchestrator + 4 handlers
    (SkipMonth 548 l., ExitRule 111 l., RegimeFilter 119 l., Generic 498 l.).
    ⚠ ExitRule + RegimeFilter sont flaggés `REQUIRES_HUMAN` (cf. `current_focus.md:33-35`).
  - `_automation/arxiv/` : daily q-fin scan (dernier `2026-05-25_analysis.md`)
  - `_automation/synthesis/` : weekly cross-paper (`2026-W21.md`)
  - **PLANNED/EMPTY** : `_automation/{code_health, methodology, research_weekly, revisits}/`
- **CI** : `.github/workflows/auto-merge.yml` — squash-merge auto pour PRs `claude/*`
  **uniquement si tous fichiers sont sous `_automation/`** ; chemins sensibles
  (`Futures/live/`, `Portfolio/`, `strategies/`, `.github/`, `*.mq5`) → hard-fail.

## Python envs
- Research: /usr/bin/python3
- Live VPS: ~/venv/
- Local venv: <HOME>/Desktop/Unholy returns/Python3.12.9/myenv/

## VPS
- Hetzner CX22, <VPS_IP>, user algo
- SSH: `ssh -i ~/.ssh/hetzner_algo_claude algo@<VPS_IP>`
- Active crons (déclarés) **[À CONFIRMER VIA SSH `crontab -l`]** :
  - TSMOM state : `25 0 * * 1` (Monday 00:25 UTC, state tracking only)
    ⚠ Le script wrapper `run_tsmom.sh:6` annonce `5 0 * * *` (daily) — divergence à résoudre.
  - Delta-neutral : `10 0,8,16 * * *` (cohérent avec `run_delta_neutral.sh:6`)
  - NQ paper été : `25 13 * * 1-5` (UTC+2 = 09:25 ET) — ⚠ pas de script wrapper local
  - NQ paper hiver : `25 14 * * 1-5` (UTC+1)
  - Alpha hunt : commits toutes les ~30 min (visible dans `git log`), schedule réel à confirmer

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
L11b. IJR cost gate misapplied to binary TP/SL strategies (breakout, event-driven):
      gross_alpha ∝ √N but cost ∝ N → gate_ratio = C/√N, DECREASING in N. For IC=0.05
      and FX intraday costs, gate passes only at N ≤ 6 trades/yr, which reveals the formula's
      miscalibration for binary TP/SL regimes rather than economic infeasibility of the strategy class.
      Correct gate for binary TP/SL: E[gross/trade] > 3 × cost/trade (N-independent).
      MUST pre-register IC justified by numerical literature (win_rate by regime/filter),
      never adjust post-failure. First case identified: F2 Asian Range Breakout archived 2026-05-26.
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

### FX structural — registre L (à partir de L23)
L23. Regulatory-window kill: when an edge depends on a fixing/auction window subsequently
     widened or restructured by regulators (BIS WMR Feb 2015: 1min→5min; MiFID II 2018),
     pre-reform documented magnitudes are NOT predictive post-reform. Pre-flight check:
     does the cited paper cover ≥2 years of post-regulatory-change data? If not → treat
     edge as non-tradable until re-documented on post-reform sample.
L23b. Institutional ≠ retail microstructure edge: persistence of an HFT-mediated edge in
      literature does not imply retail tradability. Any microstructure edge whose mechanism
      is HFT-mediated requires explicit cost-tier check (institutional 0.5-1.5bp RT vs
      retail 2-7bp RT). Default: skeptical.

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
- FX M5: Dukascopy bi5 custom decoder in `Forex/research/archived/strategy_e_fix_flow/data_setup.py`
  Cache: Forex/data/cache/dukascopy_m5/. DL speed: ~12min/pair-year, 4 threads.
- Equities: yfinance + Tiingo (limited free tier)
- FRED: DTB3 (RF daily), interbank rates monthly
- HL API constraint: no candle data before Nov 2022; gap Dec 2022–Dec 2023
- **Alpha-hunt panels** : `data/panels/*.csv` (16 fichiers récents non-trackés cf. git status) —
  cache du pipeline `_automation/alpha_hunt/` (commodity_panel, crypto_panel, equity_panel,
  fx_panel, ff5, vix, vol_etf_panel, etc.)

## Research history (n_tests = 321 global)
<!-- Sequential global milestones (README §6.55 authoritative).
     Note 2026-05-30 audit : la valeur "322" précédemment affichée contredisait
     le commentaire interne qui dit "321 final" et le header README "321 signals/variants
     tested". Harmonisé à 321. Si la branche `claude/h31-cs-fs-dn-test-160` clôt
     un test #160, recompter et passer à 322 explicitement.

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
- Crypto TSMOM v3 (Strategy A, Sharpe 1.33 OOS — chiffre commentaire `signal.py:13`,
  results.json formel **[INTROUVABLE]**)
- Delta-neutral carry HL (Strategy B, proxy Sharpe 2.0 ; backtest Sharpe 4.10 source
  **[INTROUVABLE]** dans le repo)
- NQ opening momentum iter_10 (Strategy C, Sharpe 1.52 — `Futures/research/active/nq_intraday/results.json` l.966-990)

### Active research (en cours, état arbre 2026-05-30)
- **Strategy D — D3+D5 portfolio** (Futures, propfirm-targeted, decorrelated to C):
  D3 (Opening range mid-fade 09:45-11:00, n_test=156, sharpe=-1.0761, corr_C=-0.21) +
  D5 (Afternoon BB squeeze breakout 14:00-15:30, n_test=158, sharpe=-1.3171, corr_C=-0.05).
  Both failed individually ; portfolio combination + regime filter under study.
  Pre-registration in progress.
  Dirs : `Futures/research/active/nq_intraday/analysis/` (canonical signals) ;
  `Futures/research/active/strategy_d/` (hypotheses_preregistered.md) ;
  `Futures/research/active/strategy_d_nq/infra/` (manual_signal launcher — voir
  `_meta/open_questions.md` pour le statut "à trancher")
  Budget: 3 mods, 0 consumed.
- **Commodities XS — Basis + TSMOM** (n≤279): S_TSMOM (Moskowitz 2012) + S_BASIS
  (Erb-Harvey 2006), 24 continuous contracts, monthly CS IC scan.
  Phase A (data fetch + roll validation) not yet complete.
  `Commodities/research/active/xs_basis_tsmom/`
- **Voie B FTMO (Strategy A pivot)** : MT5 EA + reconciliation + slippage analysis +
  weekly real-tape test. `Futures/research/active/voie_b_ftmo/` (commit `16eb3be`,
  branches `claude/voie-b-*`). **[À CONFIRMER]** sous-jacent ciblé.
- **Sector Hothand propfirm** (Equities) : data_audit, engine, phase1_baseline + MC.
  `Equities/research/active/sector_hothand_propfirm/` (branches `claude/sector-hothand-phase*`).
- **ZN Baltussen** (Futures) : sigma_estimation/, tests/. `Futures/research/active/zn_baltussen/`
  (branche `feature/zn-baltussen-feasibility`).
- **Crypto H31 — CS-FS-DN** : nouvelle direction (test #160). `Crypto/research/active/h31_cs_fs_dn/`
  (branche `claude/h31-cs-fs-dn-test-160`, non-trackée ; à formaliser).
- **VRP short gamma crypto** : `Crypto/research/active/vrp_short_gamma/` (distinct du VRP
  Deribit long carry archivé, cf. L13).
- **FX CIP EOQ** : `Forex/research/active/cip_eoq/`. **[À CONFIRMER]** statut.
- **NQ intraday VWAP** : `Futures/research/active/nq_intraday_vwap/` séparé de nq_intraday.
  **[À CONFIRMER]** différence vs nq_intraday/.

### ✗ Archived — DO NOT re-propose without strong new evidence

**Crypto (n=159, free-data EXHAUSTED — 7 missions, 11 signal families)**
- All long-only CS: β-dominance (L11) kills every signal regardless of IC
- Delta-neutral: PMR basis (`Crypto/research/archived/other/pmr_basis/`, IC real but 912 events/yr
  → 178%/yr cost drag, L12), OAGF (`other/oagf/`, 128/yr sparse, L12 floor),
  CS-FS (t=1.54) — **[INTROUVABLE]** dans archived ; FRA (t=1.01) — idem **[INTROUVABLE]**
- On-chain: MVRV (`sentiment/mvrv/` + `other/eth_mvrv_netflow/`, momentum proxy, corr_A=0.73),
  netflow (HAC deflation, L12b)
- Options VRP Deribit (`options/vrp_deribit/`): gross 4.4%/yr, costs 8.9%/yr (L13). 0/13 WF folds positive.
- Macro overlay (`etf_regime_overlay/`), FGVD sentiment (`other/fgvd_h1/`, L17),
  Wikipedia attention (L18) **[INTROUVABLE]** comme dossier dédié
- Remaining viable paths: Glassnode stablecoin (~$500/mo) or maker rebate execution

**FX (running total at closure: n=181)**
- G10 carry (FX-1 to FX-4): dead post-GFC (2005-2007 artifact, IC=-0.028 on 2013-2023)
- CS momentum, TSMOM G10: dead post-Menkhoff (central bank anchoring)
- London ORB v1 (`Forex/research/archived/london_orb_v1/`, n=170): best t_HAC=1.01 (GBPUSD), below gate 1.65
- Round Number Cascade (`archived/round_number_cascade/`, n=180): all IC horizons FAIL
- BIS REER ≠ bilateral USD valuation: unsuitable as carry signal modifier
- Strategy E — WMR Fix + EOM USD Flow (`archived/strategy_e_fix_flow/POSTMORTEM.md`, n_reg=175,
  0 IC tests): CLOSED at literature stage. Root: window widening (L23) + TWAP algoisation.
- G1 — Carry G10 conditionnel VXY-vol + Fed-stance (`archived/g1_carry_conditional/POSTMORTEM.md`,
  n_reg=180): L11 3× gate fail. G2D pivot: Koijen 2018.
- Strategy F2 — Asian Range Breakout London Open (`archived/strategy_f2_asian_breakout/POSTMORTEM.md`,
  n=181): ARCHIVED at L11 preflight. IJR gate_ratio=0.751 < 3.0.
  ⚠ **DUPLICATION** : copie aussi présente en `Forex/research/active/strategy_f2_asian_breakout/` —
  à supprimer.

**Equities/ETF/Futures**
- D1-D5 (n_test 154-158) — verdicts dans `Futures/research/active/nq_intraday/results.json` :
  D1 (sharpe=-0.14, IC_t=1.55, WF=66.7%, corr_C=-0.04), D2 (-1.48, IC_t=-0.86, deferred),
  D3 (-1.08, corr_C=-0.21), D4 (-0.70, IC_t=1.61, WF=22.2%, corr_C=-0.02), D5 (-1.32, corr_C=-0.05).
  ⚠ **ARCHIVED en prose, pas en arbre** — dossiers `archived/d1`, `archived/d4` n'existent pas.
- Multi-asset TSMOM (`Equities/research/archived/multi_asset_tsmom/`): Sharpe 0.21 corrected, alpha t=1.31
- Pairs cointegration (`archived/pairs_cointegration/`, 0/19 qualify), Gatev distance (
  `archived/pairs_distance_gatev/`, Sharpe -0.44, t=-2.5)
- VIX term carry (`ETF_Vol/research/archived/vix_term_carry/`, Sharpe 0.67, alpha t=0.71 insufficient)
- Sector reversal (`Equities/research/archived/sector_reversal_cs/`, Sharpe -0.60, t=-3.7 negative alpha)
- Commodity TSMOM ETF (`Commodities/research/archived/commodity_tsmom/`, Sharpe 0.39, AMTP p=0.808 — ETF roll drag)
- NQ VWAP MR / afternoon momentum: all FAIL ($19 RT cost kills any edge)
- NQ ORB IVB (`Futures/research/archived/orb_ivb_nq/`, Conti/Valentini): Sharpe -0.09/-0.44, 0/5 propfirm gates
- Equity indices_swing Sprint 1+2 (`Equities/research/archived/indices_swing/`, 100 tests):
  IC 0.033-0.075, all fail backtest
- NQ Pairs ES/NQ : EG p=0.28 — vit dans `nq_intraday/results.json` iter_D_pairs_es_nq, pas dossier dédié
- Network Momentum GMOM : universe too small (N<64), graph density=1.0 → FAIL.
  ⚠ **DRIFT** : dossier est en `Multi_Asset/research/active/network_momentum/`, pas archived/.
  À déplacer.

**Options (n=1)**
- SPX VRP Angle C (`Options_Vol/research/archived/vrp_spx_angle_c/`): IC t=-0.144, wrong direction
- BTC VRP Deribit (n=156): gross 4.4%/yr, costs 8.9%/yr (L13)

### Misclassified (failed but in passed/)
- `Equities/research/passed/jt_momentum_cs/results.json` : sharpe=-0.026, max_dd=-0.58 — **failed**
- `Forex/research/passed/fx_carry_trend/results.json` : sharpe_hac=-0.15, max_dd=-0.53 — **failed**
  → action : déplacer vers `archived/`.

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
  — `Crypto/research/active/token_unlocks/` contient seulement _bootstrap_notes.md
- HLP vault flow contrarian, Uniswap V3 LP rebalancing (HL API + The Graph, free)
- GitHub commit velocity as dev proxy (GitHub REST API, free)
- BTC cross-exchange lead-lag Coinbase→Binance (Shu 2023) — multi-venue WebSocket

## Automation infrastructure
- `_automation/alpha_hunt/`: VPS cron scrapes Reddit/HN/Quantocracy/SSRN/GitHub,
  applies L0/L1/L2 filters, stages items in `promising/`. Dedup via `_seen.json`.
- `_automation/feasibility/`: 3-level gate pipeline (A: IC; B: WF+bootstrap+DSR;
  C: sanity checks). Handlers dispatch by hypothesis type (SkipMonth, ExitRule,
  RegimeFilter, Generic fallback). ⚠ ExitRule + RegimeFilter handlers marqués
  `REQUIRES_HUMAN` (cf. `_meta/current_focus.md:33-35`).
- Routines run on Anthropic cloud — no external API access, repo data only.
- Each routine commits to `claude/<routine-name>-<date>` and opens a PR.
- **CI auto-merge** (`.github/workflows/auto-merge.yml`) : auto-squash uniquement si
  tous les fichiers modifiés sont sous `_automation/` ; hard-fail sur `Futures/live/`,
  `Portfolio/`, `strategies/`, `.github/`, `*.mq5`.

## Secrets
- Variables runtime stockées dans `.env` (gitignored cf. `.gitignore:2`).
- État actuel `.env` : 5 variables (`MT5_SERVER, MT5_LOGIN, MT5_PASSWORD,
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID`).
- `.env.example` : ⚠ désynchronisé — manque `MT5_*`, `TRADOVATE_*` (consommés par
  `Futures/live/strategy_c_live/config.py:44-51`), `PROPR_API_KEY`, `BINANCE_*`,
  `HYPERLIQUID_PRIVATE_KEY` (référencés dans README §3 et live_trader.py).
  À mettre à jour avec la liste exhaustive des variables consommées.
- **[À CONFIRMER MANUELLEMENT]** : statut rotation "5 secrets compromis, regen pending" —
  les 5 du .env correspondent aux 5 visés ; confirmer que la rotation est effectuée.

## Current focus
→ see `_meta/current_focus.md` (updated each session; contains blockers, in-progress work,
  next priorities — séparé de ce fichier constitutionnel pour éviter la dette de maintenance)

## Parallel session coordination (READ BEFORE LAUNCHING /goal)
- Before any /goal: run `git pull origin main` and read this CLAUDE.md.
- Never create parallel infrastructure folders without checking existing live/ first.
- Strategy C canonical live infra: `Futures/live/strategy_c_live/` (NOT `strategy_c_paper/`).
- `strategy_c_paper/`: ONLY pre-existing log infra (log_trade.py, paper_trade_log.csv).
- For new asset classes, check Research history before assuming nothing was tested.
- **CI auto-merge** : toute PR `claude/*` modifiant des fichiers hors `_automation/`
  est auto-bloquée (label `needs-human-review`). Pour les PRs touchant `Futures/live/`,
  `Portfolio/`, `strategies/`, `.github/` ou `*.mq5` : hard-fail CI obligatoire.
