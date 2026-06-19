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

### Strategy A — TSMOM v3 (FROZEN 2026-05-30 — Propr gelé depuis 2026-05-11 ; HL testnet daily place encore des fills)
- Signal: tanh(cumret_28d / (vol_28d × sqrt(28))).clip(lower=0), long-only
- Vol: log returns, 28-bar window, sqrt(365) annualization — MUST match backtest
- Assets: BTC, ETH, SOL | Rebalance: Monday 00:05 UTC (Propr) + daily 00:05 UTC (HL testnet)
- Validation: Sharpe 1.33 OOS, MaxDD -6.9% (source: signal.py:13 docstring ; results.json formel INTROUVABLE)
- VOL_TARGET_LIVE=0.18 | guardrails RUNTIME-ACTIVE: MAX_DAILY_DD=2.8%, MAX_TOTAL_DD=5.5% (Propr, execution/__init__.py:46-47)
  Canonical default for new strategies: Portfolio/risk/propfirm_canonical.py (FTMO 5/10).
  Note: config.py:55-56 défi MAX_DAILY_DRAWDOWN=4.5%, MAX_TOTAL_DRAWDOWN=9% (HyroTrader legacy, sizing.py CHALLENGE_MODE=False par défaut, non consommé en live).
- Status: Propr Monday cron `5 0 * * 1 run_rebalance` installée mais sans fill depuis 2026-05-11 16:44 UTC (compte breach). HL testnet daily cron `5 0 * * *` continue de placer des fills (cf. logs/fills.csv 2026-05-28 SOL sell).
- Structural ceiling: 39% Propr pass rate (β_crypto floor, 3% daily DD limit)
- Apex alternative (EOD trailing, CME futures): [CADUC 2026-06-10 — propfirms retenus: FTMO + Propr] — see PropFirms/comparison.md
- Frozen artifacts: `Crypto/research/archived/_frozen/strategy_a_propr_2026-05-30/` (copie code+state, originaux conservés)

### Strategy B — Delta-neutral carry (HL testnet LIVE since 2026-05-17)
- Active pair au 2026-05-30: HMSTR seule (TST/MEGA historiques, flat). État volatile, ne pas figer dans CLAUDE.md — voir state.json VPS pour pair active courante. Rebalance: every 8h (00:10, 08:10, 16:10 UTC)
- Backtest Sharpe: 4.10, MaxDD: -0.52% | Mainnet proxy Sharpe: 2.0 (per L14)
- VIABLE_ASSETS: TST, MEGA, WLD, STX, WIF, BIO, TRUMP, HMSTR
- MIN_VOL_USD=1_000_000 | CARRY_FLOOR_8H=0.0034/(30×3) | NOTIONAL_USD=50
- Kill switch: checks STOP file on each run
- Status: EXECUTION-VALIDATED, mainnet pending (~60-day live required, ~2026-07-17)

### Strategy C — NQ Opening Momentum iter_10 (Tradeify ANNULÉ 2026-06-10 — pas de véhicule propfirm)
- Signal: direction of 09:30-09:45 ORB, entry at 09:46 ET
- Filters: VWAP confirmation + gap < 1.2% + opening range ≥ 30pts + $400 SL cap
- TP: 1.5R | SL: min(0.5R, 20pts) | Time stop: 12:30 ET
- Backtest HISTORIQUE (Kaggle 2022-2025, $19 RT): Sharpe 1.52, MaxDD -13.4%, WF 78% (7/9), N=346 — PÉRIMÉ
- **RE-BASELINE 2026-06-07** (`iter_10_databento_rebaseline`, Databento 2014-2026, slippage $29 RT per L19):
  Sharpe 0.41 full / 0.69 fenêtre Kaggle 2022-25, maxDD -53.9% acct, N=765 → **sous PROPFIRM_PASS**.
  Source: `Futures/research/active/nq_intraday/results.json` (n_tests=149).
- **Décision 2026-06-10: Tradeify ANNULÉ.** Propfirms retenus: FTMO (futures/CFD) + Propr (crypto).
  FTMO ne supporte pas les futures CME (L22c) → C-sur-NQ n'a plus de véhicule propfirm.
  Piste FTMO CFD distincte: `Futures/live/orb_floor_ftmo/` (voir DEPLOYMENT.md).
- Infra conservée (réutilisable): `Futures/live/strategy_c_live/` (Tradovate client, signal_engine,
  guardrails), sizing_policy.md, PropFirms/tradeify/rules.md.
- [OBSOLÈTE 2026-06-10] Tradeify constants: eval_DD=$1,000 funded_DD=$1,000 lock=$26,100 floor=$25,100 (confirmé 2026-05-25)
- [OBSOLÈTE] VPS cron paper `25 13/14 * * 1-5` — jamais installée (vérifié 2026-05-30)
- Status: projet propfirm ANNULÉ (re-baseline sous gate + Tradeify abandonné). Code et backtests conservés.

## Portfolio context
- Personal book: A (TSMOM, paused) + B (HL testnet, mainnet ~Jul 2026)
- Propfirm book (décision 2026-06-10): **FTMO uniquement (futures/CFD) + Propr (crypto)**.
  Tradeify annulé; C-sur-NQ sans véhicule (L22c). Potential D: decorrelated, propfirm-targeted.
- **Book de référence = A+B (recalc 2026-06-10)** : SR analytique **2.31** (ERC risk-units 50/50 ;
  SR_A=1.33, SR_B=2.0 proxy L14, ρ_AB=0.039 full-sample). Sensibilité A+B+C au re-baseline C :
  SR_C=0.41 → 2.08 | 0.69 → 2.24 → **C dilutif sur tout l'intervalle** (breakeven ERC : SR_C≈0.81)
  → C hors book personnel aussi. L'ancien « 2.24, MaxDD -1.0% (10/68/22) » est caduc : méthodo
  série avec B-backtest SR 9.64, L14-inadmissible (le 2.238→2.238 est une coïncidence fortuite).
  MaxDD book : à mesurer sur ≥60 j live B mainnet (série B backtest 92% zéros, solveur ERC série
  dégénère). Détail : `_audit/portfolio_recalc_2026-06-10.md`.
- New strategy D gate: Sharpe(book+D) > 1.10 × 2.31 = **2.54** required
- Propfirms do NOT accept crypto/delta-neutral → A and B stay personal book

## Repo layout
- Live crypto: `strategies/{tsmom_v2_propfirm, delta_neutral}`
- NQ live: `Futures/live/strategy_c_live/` (config, tradovate_client, signal_engine, guardrails)
- Active research: `<AssetClass>/research/active/`
- Archived research: `<AssetClass>/research/archived/`
- Programmes propfirm (clos): `PropFirms/<firm>/program_<date>/` — le programme FTMO 10k juin 2026
  (memo + funnel v1/v2 + portfolio_audit + survivors_book + ftmo_research + alpha_program + …)
  est consolidé dans `PropFirms/ftmo/program_2026-06/` (P2 2026-06-10 ; anciens chemins
  `research/`, `data/ftmo_research/`, `PropFirms/ftmo_*` — citations historiques non réécrites).
- Portfolio state: `Portfolio/state/portfolio_state.py`
- Automation:
  - `_automation/alpha_hunt/`: scraper pipeline, `promising/` items staged for feasibility
  - `_automation/feasibility/`: 3-level gate orchestrator + 4 handlers (SkipMonth, ExitRule,
    RegimeFilter, Generic)
  - `_automation/arxiv/`: daily q-fin scan | `_automation/synthesis/`: weekly cross-paper
- Data governance (audit 2026-06-10, `_audit/dedup_audit_2026-06-10.md`):
  - `data/raw/` = sources immuables + manifest dans `data/metadata/` ; caches = régénérables, gitignorés.
  - Une série = un fichier canonique. M1 FX/indices : `data/deep_history_utc/` (true UTC, 2007→2026-06,
    MANIFEST.md). La recherche RÉFÉRENCE `data/`, ne copie jamais.
  - Jamais de blobs data dans git (.gitignore : `alpha_hunt/_raw`, `deep_history_utc`, `m5_indices`,
    `_cache_duka`, `data/*.txt`).
  - Un subset (plage plus courte) se supprime après migration de ses consommateurs — SAUF provenance
    d'une stratégie validée (ex : NQ Kaggle parquet = data de validation historique de C).
  - Cleanup P0+P1+P2 exécutés 2026-06-10 (tag `pre-cleanup-2026-06-10`, .git 2.1Go→~65Mo).
    P2 : 13 M1 m5_indices supprimés (vérifiés ⊂ deep_history POST-réparation des trous US500/US100/
    GER40), consolidations FTMO/mtf/audits/docs/oxfordstrat. CONSERVÉS sans superset : US2000_M1.csv,
    panels parquet EET (`*_m1_panel.parquet`), binance/. Détail : `_audit/cleanup_recap_2026-06-10.md`.
  - deep_history_utc RÉPARÉ 2026-06-10 (trous 2018-2021 US500/US100/GER40 backfillés Dukascopy,
    seams 4/4 PASS ≤1.3bps, MANIFEST machine-généré). Originaux : `*_M1.csv.pre_repair_backup`
    (~1.1Go, à conserver — reproductibilité announcement_premium).

## Python envs
- Research: /usr/bin/python3
- Live VPS: ~/venv/
- Local venv: <HOME>/Desktop/Unholy returns/Python3.12.9/myenv/

## VPS
- Hetzner CX22, <VPS_IP>, user algo
- SSH: ssh -i ~/.ssh/hetzner_algo_claude algo@<VPS_IP>
- Crons réelles vérifiées 2026-05-30 (cf. _audit/verification_2026-05-30.md V2) :
  - `5 0 * * *` — Strategy A daily HL testnet (`run_tsmom.sh --live --private-key <REDACTED>`) — places des fills
  - `30 0 * * *` — Strategy A monitor wrapper (`run_monitor.sh`)
  - `5 0 * * 1` — Strategy A weekly Propr rebalance (inline `PROPR_API_KEY=<REDACTED>`) — gelée 2026-05-11
  - `30 8 * * *` — Strategy A daily Propr summary (inline `PROPR_API_KEY + TELEGRAM_*`)
  - `10 0,8,16 * * *` — Strategy B delta-neutral (source .env pattern, propre)
  - `*/2 13-17 * * 1-5` — Strategy C watchdog_check.sh (×2 lignes — DOUBLON, à dédupliquer)
  - `30 6 * * 1-5` — `fetch_arxiv.sh` (sans redirection log, silent fail)
  - `*/30 * * * *` — `fetch_alpha_sources.sh` — PATCHÉ 2026-06-10 : distillation sur le VPS
    (process_raw_filter.py après fetch), push limité à `_seen/` + `_staging/` (anti-churn _stats.json),
    XML VPS-local purge >7j. La chaîne n'a JAMAIS été en panne (le "dernier XML 02/06" = repo local
    pas pullé). Reddit ×3 en 429 chronique (UA bloqué). Log : `logs/alpha_hunt_fetch.log` (VPS).
    TODO : `fetch_arxiv.sh` pousse encore du raw XML (`_automation/arxiv/_raw/`, 1/j) — même patch applicable.
  - `@reboot sleep 30 && screen -dmS mt5 start_mt5.sh`
- Crons MANQUANTES vs ce qu'annonçait CLAUDE.md historique :
  - aucune cron NQ paper `25 13 * * 1-5` / `25 14 * * 1-5` n'existe — Strategy C n'est pas automatisée (cohérent avec "execution not started").
- Cleanup proposé non appliqué : voir `_audit/lot7_crontab_diff_2026-05-30.txt` + wrapper `scripts/run_with_env.sh`.

## CI / GitHub Actions
- `.github/workflows/auto-merge.yml` (170 lignes) : squash-merge automatique des PR `claude/*` après tous checks verts.
- **Hard-fail paths** (PR est étiquetée `needs-human-review` au lieu d'être auto-mergée si les changements touchent) :
  - `Futures/live/`
  - `Portfolio/`
  - `strategies/`
  - `.github/`
  - `*.mq5`
- **Restriction `_automation/`-only** : si une PR contient des modifications HORS `_automation/`, elle n'est pas éligible.
- Notification Telegram on failure (lignes 158-170).
- Source vérité : _audit/verification_2026-05-30.md V12.

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
     Artefacts archivés : `Crypto/research/archived/other/wav_h3/` (POSTMORTEM.md
     + data/wiki/*.parquet 10+ tickers ADA/ALGO/AVAX/…).

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
L24. Propfirm pass-probability is driven by the SHAPE of the daily-return distribution against a
     SYMMETRIC barrier (target ≈ max DD), NOT by account size — the problem is scale-invariant
     (verified: Strategy C plateaus ~44% p(pass) across $10k-$200k, account_sweep 2026-05-30).
     Lumpy strategies (low win-rate, high win/loss ratio, e.g. C: WR 27.75%, 3.7×) are structurally
     capped ~44-54% regardless of sizing — wrong tool for a symmetric-barrier challenge.
     FTMO-SUITABLE profile = high DAILY Sharpe + win-rate >55% + win/loss ratio ≈1 + low kurtosis
     + high trade frequency (edge must materialize in ≤40 trading days without variance dominating).
     Momentum/trend families are inherently lumpy → poor propfirm fit. Mean-reversion / regular-
     grind families fit better but face the L11/L12 cost-ceiling + left-tail kurtosis caps.
     Note de numérotation : "L19" proposé en pré-registration entre en collision avec L19 existant
     (NQ market impact) ; promu en L24 pour préserver les références.

### CFD/FTMO execution & structure — registre L (L25-L36, gravé 2026-06-10, réconciliation)
L25. Two-sided test: a real directional edge is positive on BOTH legs. Every FTMO directional family
     tested was long-leg-only = equity/carry up-drift = beta. Mandatory gate on any directional claim.
     (Origin: FTMO_decision_memo 2026-06-02.)
L26. Delay-1 / same-bar discipline: overlapping-window and same-bar-fill screens inflate intraday
     edges; validate with non-overlapping trades + a 1-bar execution-delay test (decisive). Any
     timestamp ambiguity resolves to the NEXT bar. (FTMO_decision_memo 2026-06-02.)
L27. Market-neutral *by construction* ≠ two-sided *in spread*: a cointegrated spread inherits a
     relative drift, so stat-arb still fails L25. The beta trap survives hedging. (Statarb arc 06-02.)
L28. A market-neutral CFD pair pays 2× broker markup in financing (benchmark cancels across legs)
     ≈ 1.5 bps/night in every rate era → fatal to weeks-to-revert spreads. (Statarb arc 06-02.)
L29. Half-life-matched holding is necessary but not sufficient: fixing the exit removes a confound
     so the true "no" can be seen; it does not manufacture EV. (Statarb arc 06-02.)
L30. Swap-sign rule (Dédale, codified ftmo_swaps.py): real FTMO swaps are ASYMMETRIC (pay more than
     fair on the costly side, receive less on the carry side). Never hold the negative-swap side
     overnight; long-premium and short-positive-swap cannot be collected together. Decisive: US100
     long −3.31 bps/night ⇒ overnight harvester 82%→31%. Measured capture: US100.cash long −662.4 /
     short +28.58 (asymmetric, units broker-quoted). (FTMO_decision_memo 2026-06-02.)
L31. Carry / short-term-reversal alpha-decay: edges real *in their regime* (JPY carry 2022-24, US-idx
     STR pre-2013, EURGBP 2022-23) decay out of it; OOS / post-regime split is MANDATORY before citing
     any carry or reversal edge; unwind tails (−15/−20%) breach the 10% floor. (FTMO_decision_memo
     06-02; confirmed backwardation_oil, announcement_premium, session_G sign-flips.)
L32. Retail-CFD commodity carry is one-sided-uncollectable: the short-contango leg needed for most of
     history costs −46+ bps/month in swap — "collect the roll" is structurally unavailable to retail.
     (commod_carry thread; confirmed CARRY_FEASIBILITY 2026-06-09.)
L32b. The collectable side is a credit, not an edge: long-only oil gated on real backwardation nets
     ≈0 over 19y (+0.96%/yr swap credit cancelled by −1.03%/yr conditioned price beta); basis gating
     protects only contango-led crashes, rides backwardation-led ones (2008/2014/2022). Both CFD
     carry sides closed. (backwardation_oil 2026-06-10, registry T109.)
L33. The real instrument's COST STRUCTURE, not the signal, decides whether a barrier-exploit lives:
     a 2-bps backtest does not transfer to a 6-10 bps CFD; ORB mean_R sign-flips between 2 and 3 bps
     RT; swap is charged on HELD NOTIONAL per leg, both directions. Measure the book-level cost,
     never assume. (ETAT_CANONIQUE §7 2026-06-03; session_F held-notional clause 06-04.)
L33b. Spread is the intraday-flat executioner: in zero-swap (intraday-flat) structures the binding
     cost becomes the spread — Gao time-of-day ≈0 gross → −3 bps net (t −6) at a conservative 3 bps
     RT. An intraday-flat signal needs >3 bps gross to exist. (session_G 2026-06-04; cited "L33-bis".)
L34. Flow-anchored FX is institutional-tier only: the only gross survivor at the fix/session level
     (Ranaldo segmentation, two-sided, t=3.55, gross 2.07 bps/d) dies solely on the retail cost tier
     (needs <~1 bp RT/leg vs measured 2.48). Pre-2015-reform fix magnitudes stay non-tradable (L23).
     Reformulated 2026-06-10 WITHOUT the asymmetry clause (tz artifact). (fix_reversal 06-02 →
     true-UTC re-validation 06-10.)
L35. DP-optimal sizing is the CEILING of every sizing policy, not a heuristic: ORB single-attempt
     FTMO 2-step ceiling = 33% full-sample. Money management is not the lever — the edge is.
     (ORB_reconciliation 2026-06.)
L36. Aggregate overnight carry pre-kills every held premium on FTMO: book-level all-in carry
     (~6.75%/yr swap + ~1.25% commission) ≈ the entire multi-asset trend premium (~8%/yr) → net
     Sharpe 0.0; the killer is the AGGREGATE multi-leg carry (low-vol large-notional legs dominate),
     not the scary single-instrument rate. Carry-immune escapes only: intraday-flat (then L33b binds)
     or prime ≫ carry (precious-Q1 class). (session_F 2026-06-04; numbered by session_G usage.)

### Trend/book & FX intraday — registre L (L37-L44)
L37. Filter sanity check: for any conditionally-filtered sleeve, count the fraction of time
     sign(filter) ≠ native signal. If <5%, the filter is cosmetic — name the sleeve by what it really
     is (J1 = TSMOM long-only USDJPY, not "carry-aligned trend"). (trend arc, STRATEGY_RESEARCH_LOG 06-06.)
L38. Beta-orthogonal test: regress any "structural premium" sleeve on a vol-targeted buy-and-hold of
     its primary asset; report (β, α HAC, R²). R² > 30% ⇒ not an orthogonal edge — it is timing on
     beta, present it as such. (trend arc 06-06.)
L39. Daily vs monthly skew dissociation: on trend/carry, daily skew can be negative while monthly
     skew is positive. Daily skew binds on the FTMO 5% daily barrier; monthly skew binds on the
     personal book. Always report both. (trend arc 06-06.)
L40-L41. RÉSERVÉS — top10-rigorous arc (2026-06); originating report not in repo (session memory
     only). Do NOT reassign; engrave when the report lands.
L42. Pre-FOMC drift is real on equity indices (confirmed on 8 instruments, top10 arc) and post-event
     REVERSAL is the wrong direction — post-event momentum continues (25/142 AMTP-significant
     negative-reversal cells). [Origin report not in repo; engraved from citing artifacts:
     paper_triage/PAPER_TRIAGE.md, fx_intraday PRE_REGISTRATION §H2.]
L43. Retail FX intraday-flat microstructure is cost-dead across reversal, drift, and seasonality:
     exploitable gross is sub-bps vs ~2-5 bps CFD RT (2007-2026, 10 majors, true-UTC, 3 orthogonal
     angles). Generalizes L34 from fix windows to the whole retail FX intraday-flat space. Pre-flight:
     gross_per_trade / cost_p95 ≥ 1.5 or dead — best observed 0.36. (fx_intraday SYNTHESIS 2026-06-10.)
L44. The mechanism-driven cross-sectional contrast is the cheap decisive IC falsifier: split the
     universe by where the mechanism should/shouldn't apply and pre-register the contrast pool —
     a weak pooled t became a clean verdict (European t 2.11 vs Asia-native −0.57: signal real,
     death = cost). (fx_intraday SYNTHESIS 2026-06-10.)

### Renumérotés & nouveaux — réconciliation 2026-06-10 (L45-L50)
L45. Crypto-CFD TSMOM two-sided is structurally infeasible on FTMO (3-axis kill): short leg not
     significant even at swap=0 counterfactual (BTC t 0.28, N=205); the long leg of any two-sided
     crypto TSMOM ≡ Strategy A long-only (clip ⇒ L11 β-long in disguise); 7-night holds × FTMO crypto
     swap ≈ 19 bps/trade eats the rest. Weekly-crypto-momentum class CLOSED on CFD; non-CFD execution
     (Propr) or intraday-flat only. (ftmo_twoSided_makeOrBreak POSTMORTEM §5 — cited there as "L33
     candidate", renumbered.)
L46. Propfirm honesty checklist: one canonical ledger + measured real cost + frozen spec +
     full-sample regime. When all four are present, sign-flips between reports disappear — every
     historical ORB sign-flip was a cost-hypothesis difference on the same ledger. (ETAT_CANONIQUE §7
     + ORB_reconciliation — cited there as "L34 (proposé)", renumbered.)
L47. Annualize by √(obs/an), not √252: a once-a-week edge annualizes in √52 — using √252 inflates
     Sharpe ×2.2 (Monday-sleeve case). (ETAT_CANONIQUE annexe 2026-06-03 — the "phantom L36";
     never previously engraved.)
L48. Registry-check-must-sweep-consolidated-paths: a Phase-0 sweep that greps only historical paths
     (data/ftmo_research/…) after a consolidation returns false "file deleted" and nearly downgrades
     a STOP into a caveat. Sweep BOTH old cited paths AND the consolidated program dirs AND
     data/skew_research/session_* AND funnel CSVs before any Phase-0 verdict. Every avoided trial at
     high N protects the DSR of all future candidates. (session_H 2026-06-10.)
L49. Unlock-drift-is-short-alt-beta: a calendar-event claim on a structurally bleeding universe must
     clear a MATCHED PLACEBO CALENDAR, not just significance/decay/DSR gates — the unlock short shows
     net +337 bps/event, t 2.90, N=578, undecayed, DSR 0.94, and sits BELOW the placebo median of
     random vol-matched days on the same tokens (p95 +539). Flat dose-response + zero insider
     gradient + linear event-time escalator complete the falsification. Family: L11; same signature
     as announcement_premium "drift accrues off-event". (session_I 2026-06-10.)
L50. Funding-extremes-confirm-momentum-across-exchange-and-cycle: README §6.35 (HL, z-score, 2023-26)
     replicated independently (Binance, trailing-1y percentile, 2020-26, 13 perps, 2,195 events) —
     extreme-high funding precedes CONTINUATION (+20/+30/+113 bps at 8h/24h/72h; +239 @72h in
     2020-21). The funding-contrarian family is closed at the exchange-perp tier; funding-percentile
     carry-sizing overlays have no IC foundation. (session_I 2026-06-10.)

### Aliases historiques (citations dans les artefacts ≠ numéro gravé — artefacts JAMAIS réécrits)
| Cité comme | Où | Gravé comme |
|---|---|---|
| "L33 candidate" (crypto-CFD TSMOM kill) | `Crypto/research/active/ftmo_twoSided_makeOrBreak/POSTMORTEM.md` §5 | **L45** |
| "L34 (proposé)" (honesty checklist) | `ftmo_research/_FTMO_ETAT_CANONIQUE.md` §7, `ORB_reconciliation_2026-06.md` | **L46** |
| "L36 existant (√52)" (phantom — jamais gravé) | `FTMO_LOG_overnight_candidate.md` NB, `_FTMO_ETAT_CANONIQUE.md` annexe | **L47** |
| "L33-bis" | `data/skew_research/session_G_intraday_flat/` | **L33b** |
| "L16" | jamais gravé (2 candidats flottants non ratifiés ; g1 audit : « L16 n'existe pas ») | vacant — ne pas réattribuer |
| L40/L41 | top10 arc, rapport hors-repo | réservés |

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
- NQ 1-min: `data/raw/NQ_1min_databento_2010-2026.parquet` (CANONIQUE, source GLBX dbn.zst) +
  `data/raw/NQ_1min_2022-12-26_2025-12-11.parquet` (ex-Kaggle — provenance de la validation
  historique de C, à conserver ; le CSV Kaggle d'origine n'existe plus)
- FX/indices M1 canonique: `data/deep_history_utc/` (true UTC 2007→2026-06, spread calibré,
  MANIFEST machine-généré, trous 2018-2021 réparés 2026-06-10).
  m5_indices (P2 fait) : 13 M1 EET supprimés ; restent `US2000_M1.csv` (pas de superset),
  `binance/` (crypto M1), panels parquet EET (`*_m1_panel.parquet`, consommés par code actif —
  migration tz à prévoir, cf. `_audit/m5_indices_migration_checklist_2026-06-10.md`).
- Commodity futures: yfinance =F tickers (CL=F, GC=F, …) — continuous front-month
- FX M5: Dukascopy bi5 custom decoder in `Forex/research/archived/strategy_e_fix_flow/data_setup.py`
  + `Forex/data/dukascopy_downloader_m5.py`. DL speed: ~12min/pair-year, 4 threads.
  Cache dukascopy_m5 SUPPRIMÉ 2026-06-10 (P2 partiel) — régénérable, ou resampler deep_history_utc M1.
- Equities: yfinance + Tiingo (limited free tier)
- FRED: DTB3 (RF daily), interbank rates monthly
- HL API constraint: no candle data before Nov 2022; gap Dec 2022–Dec 2023

## Research history (n_tests = 321 global — ledger canonique)
<!-- Convention n_tests (2026-06-10) : DEUX registres.
  (1) GLOBAL = 321 — ledger historique canonique, FIGÉ 2026-05-30 (ce fichier).
  (2) PROGRAMME (depuis 2026-06) : chaque programme/étude tient un compteur cumulatif
      LOCAL nommé — ex: fx_intraday_deepdive N_ledger 108→240, backwardation_oil
      « program N 112→115 », ftmo_candidate_funnel 97→103 — avec la règle d'incrément
      du N_ledger (toute CONFIGURATION backtestée compte ; data-validation pure ne
      compte pas ; « if swapping it could have been the winner, it counts »).
      Les corrections multi-tests (AMTP/DSR) d'une étude utilisent le compteur de
      SON programme, pas le global.
  Jonction : global_courant = 321 + Σ deltas des programmes post-2026-05-30
  (non-overlapping par construction — tout test post-05-30 passe par UN registre
  programme). Réconcilier à la CLÔTURE de chaque programme en ajoutant son delta ici.
  Ne JAMAIS additionner les sous-totaux pré-2026-05-30 (overlap, cf. note ci-dessous). -->
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
     Do NOT add sub-counts; only the sequential milestones above are additive.
     2026-05-30: tranché 321 (majoritaire, cohérent avec README §1 header).
     h31_cs_fs_dn (test #160) déjà consommé, archivé 2026-05-30 (test FAIL). -->

### ✓ Validated and live/ready
- Crypto TSMOM v3 (Strategy A, Sharpe 1.33 OOS)
- Delta-neutral carry HL (Strategy B, proxy Sharpe 2.0)
- NQ opening momentum iter_10 (Strategy C) — ⚠ re-baseline 2026-06-07 : Sharpe 0.41 ($29 RT,
  Databento 2014-2026) ; le 1.52 historique (Kaggle, $19 RT) est périmé. Tradeify annulé 2026-06-10.

### Active research (in progress) — inventaire vérifié 2026-05-30

- **Strategy D — D3+D5 portfolio** (Futures, propfirm-targeted, decorrelated to C):
  D3 (Opening range mid-fade 09:45-11:00, n_test=156, corr_C=-0.21) +
  D5 (Afternoon BB squeeze breakout 14:00-15:30, n_test=158, corr_C=-0.05).
  Both failed individually (Sharpe=-1.08/-1.32); portfolio combination + regime filter
  under study. Pre-registration in progress.
  `Futures/research/active/nq_intraday/analysis/` (canonique signals)
  Pré-registration : `Futures/research/active/strategy_d/hypotheses_preregistered.md`
  Infra paper fusionnée (P2 2026-06-10) : `Futures/research/active/strategy_d/infra/` (ex strategy_d_nq).
  Budget: 3 mods, 0 consumed.
- **Commodities XS — Basis + TSMOM** (n≤279): S_TSMOM (Moskowitz 2012) + S_BASIS
  (Erb-Harvey 2006), 24 continuous contracts, monthly CS IC scan.
  Phase A (data fetch + roll validation) not yet complete.
  `Commodities/research/active/xs_basis_tsmom/`
- **Voie B FTMO (Strategy A pivot)** — full study EA mq5 + slip_analysis + reconciliation.md.
  `Futures/research/active/voie_b_ftmo/` (26 fichiers, dernière modif 2026-05-29 ;
  results/slip_report.csv visible dans git status, à commiter ou ignorer).
  [À CONFIRMER MANUELLEMENT] sous-jacent ciblé (mq5 = MT5 = quel symbole ?).
- **sector_hothand_propfirm (Equities)** — phase 1 baseline + Monte Carlo.
  `Equities/research/active/sector_hothand_propfirm/` (12 fichiers).
  Métriques rapportées : t_HAC alpha=10.38, SR_net=2.05, DSR=2.01, WF 5/5, MDD -13.3%.
  ⚠ t-stat 10 = drapeau rouge → audit obligatoire avant promotion (cf. _audit/sector_hothand_audit_2026-05-30.md).
  Note MDD -13% > limite FTMO 10% → en l'état BREACH du challenge.
- CIP-EOQ (FX) — **ARCHIVÉ** : `Forex/research/archived/cip_eoq/` (POSTMORTEM.md).
  La copie `active/cip_eoq` était un doublon exact de l'archivé — supprimée au cleanup 2026-06-10.
- **FX intraday deepdive (sub-60min FX/XAU/BTC)** — `Forex/research/active/fx_intraday_deepdive/`
  (déplacé en P2 depuis research/, cache intact, chemins exécutables relatifs ✓). Suite de l'axe
  laissé ouvert par le decision memo FTMO 2026-06-08 (`PropFirms/ftmo/program_2026-06/
  PROGRAM_DECISION_MEMO.md` : do-not-fund sur free price data / 16 instruments / N≈100).
- **ZN Baltussen (Futures)** — bond futures momentum.
  `Futures/research/active/zn_baltussen/` (tests/, sigma_estimation/).
- NQ intraday VWAP (Strategy D iter_01) — **ARCHIVÉ en P2** : `Futures/research/archived/nq_intraday_vwap/`
  (verdict "FAIL — INSUFFICIENT SAMPLE, N=19 over 3 years", n_tests=130).
- **Token unlocks (Crypto)** — bootstrap seul, vide.
  `Crypto/research/active/token_unlocks/_bootstrap_notes.md`.
- **VRP short gamma (Crypto)** — bootstrap seul, vide.
  `Crypto/research/active/vrp_short_gamma/_bootstrap_vrp_notes.md`.

### ✗ Archived — DO NOT re-propose without strong new evidence

**Crypto (n=159, free-data EXHAUSTED — 7 missions, 11 signal families)**
- All long-only CS: β-dominance (L11) kills every signal regardless of IC
- Delta-neutral: PMR basis (IC real but 912 events/yr → 178%/yr cost drag, L12),
  OAGF (128/yr sparse, L12 floor), CS-FS (t=1.54), FRA (t=1.01 regime-specific)
- On-chain: MVRV (momentum proxy, corr_A=0.73), netflow (HAC deflation, L12b)
- Options VRP Deribit: gross 4.4%/yr, costs 8.9%/yr (L13). 0/13 WF folds positive.
- Macro overlay, FGVD sentiment (L17), Wikipedia attention (L18)
- Remaining viable paths: Glassnode stablecoin (~$500/mo) or maker rebate execution

**FX (running total at closure: n=181)**
- G10 carry (FX-1 to FX-4): dead post-GFC (2005-2007 artifact, IC=-0.028 on 2013-2023)
- CS momentum, TSMOM G10: dead post-Menkhoff (central bank anchoring)
- London ORB v1 (n=170): best t_HAC=1.01 (GBPUSD), below gate 1.65
- Round Number Cascade (n=180): all IC horizons FAIL (EUR: t=1.167→-2.357; GBP: all FAIL)
- BIS REER ≠ bilateral USD valuation: unsuitable as carry signal modifier
- Strategy E — WMR Fix + EOM USD Flow (n_reg=175, 0 IC tests): CLOSED at literature stage.
  E1 W-shape: 1-4bp gross < 6-7bp retail RT post-BIS 2015 reform. E2 EOM USD conditioned:
  t_HAC≈1.2, N_eff≈35-45 → power collapse (L12). Root: window widening (L23) + TWAP algoisation.
  Dukascopy M5 infra reusable. `Forex/research/archived/strategy_e_fix_flow/POSTMORTEM.md`
- G1 — Carry G10 conditionnel VXY-vol + Fed-stance (n_reg=180, 0 IC tests): CLOSED at literature stage.
  L11 3× gate fail (530 vs 540 bps best case, ratio 0.98); Lesson 10 budget épuisé (FX-1→FX-4).
  G2D pivot: Koijen 2018 carry cross-asset (Tradovate infra réutilisable). `Forex/research/archived/g1_carry_conditional/POSTMORTEM.md`
- **Strategy F2 — Asian Range Breakout London Open (n=181, 0 backtests):** ARCHIVED at L11 preflight.
  IJR gate_ratio=0.751 (best case N_calendar=94) < 3.0. Root: IJR formula structurally fails for
  binary TP/SL strategies (ratio = C/√N, decreasing in N; passes only at N≤6 trades/yr at IC=0.05).
  Alt binary TP/SL gate: ratio=2.565 < 3.0 at IC=0.05; passes at IC≥0.107 (win_rate≥55.3%) but
  no numerical lit backing available. See L11b. Dukascopy Pool(4) infra + news_events_2020_2025.csv
  reusable. `Forex/research/archived/strategy_f2_asian_breakout/POSTMORTEM.md`
- CIP-EOQ (covered-interest-parity end-of-quarter dislocation): archivé avec POSTMORTEM —
  `Forex/research/archived/cip_eoq/`. Doublon `active/` supprimé au cleanup 2026-06-10.

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
- Network Momentum GMOM: universe too small (N<35 after quality filter), graph density=1.0 → FAIL
  best variant E3 Sharpe=0.293. `Multi_Asset/research/archived/network_momentum/` (déplacé de active/ 2026-05-30).
- jt_momentum_cs (Equities, J-T cross-sectional 70 stocks monthly):
  sharpe=-0.026, max_dd=-0.58, ic_tstat=-0.49, gate=SKIP. `Equities/research/archived/jt_momentum_cs/`
  (déplacé de passed/ 2026-05-30 — mal classé).
- h31_cs_fs_dn (Crypto cross-sectional funding stack delta-neutral, test #160):
  sharpe_raw=-0.80, wf=25%, all 3 gates FAIL. `Crypto/research/archived/h31_cs_fs_dn/`
  (déplacé de active/ 2026-05-30 — FAIL net déjà mesuré).

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
- Apex challenge analysis for Strategy A (EOD trailing, CME futures): [CADUC 2026-06-10 —
  propfirms retenus: FTMO + Propr] — see PropFirms/comparison.md
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
- **Worktree isolation — un worktree = une session ; JAMAIS deux sessions dans le même répertoire**
  (le `.git/HEAD` est partagé → un checkout/commit déplace le HEAD sous l'autre session ; incident
  2026-06-19 : commit asia_23_8 atterri sur la branche soybean, réparé par cherry-pick + `branch -f`).
  Lancer toute nouvelle tâche dans un worktree dédié, branche neuve depuis `origin/main` :
  `git fetch origin && git worktree add ../Algo_claude_<tache> -b claude/<tache> origin/main && cd ../Algo_claude_<tache>`
  (puis lancer la session Claude dans ce répertoire). Branche existante :
  `git worktree add ../Algo_claude_<tache> claude/<branche>`. Inspecter `git worktree list` ; nettoyer
  après merge `git worktree remove ../Algo_claude_<tache>`. Toujours brancher depuis `origin/main` (pas
  depuis la branche d'une autre session → PR propre). Ne jamais `branch -f`/rebaser la branche d'une
  session ACTIVE sans la prévenir (son HEAD devient incohérent).
- Never create parallel infrastructure folders without checking existing live/ first.
- Strategy C canonical live infra: Futures/live/strategy_c_live/ (NOT strategy_c_paper/).
- strategy_c_paper/: ONLY pre-existing log infra (log_trade.py, paper_trade_log.csv).
- For new asset classes, check Research history before assuming nothing was tested.
- **Phase-0 / lesson sweeps (L48)**: grep BOTH the historical cited paths (`data/ftmo_research/`,
  `research/`, `data/oxfordstrat_109/` — non réécrits) AND the consolidated dirs
  (`PropFirms/ftmo/program_2026-06/**`) AND `data/skew_research/session_*` AND funnel CSVs.
  The L-registry above (L11-L50) is the constitution; session reports may cite aliases — see the
  aliases table. Lesson minting in sessions = NAMED candidates only; numbers are engraved here
  at reconciliation (no number minting inside a session).
- **Worktree + artefacts locaux (gitignored)** : le moteur cleanroom (`audit_v2_independent/cleanroom/`),
  les caches (`data/ftmo_portfolio/cache/`, `data_cache/`) et certains dirs cités dans REGISTER.md sont
  **locaux/gitignored** → absents d'un worktree frais (checkout off main). Une session en worktree les
  **importe du main dir par chemin absolu** (`<HOME>/Desktop/Algo_claude/…`), read-only :
  le code d'étude vit dans le worktree, le moteur + caches restent référencés dans le main dir.
- **Session close (obligatoire)**: `python3 tools/check_register_integrity.py` (fail-loud: cited
  paths exist + git-tracked, N chain monotonic) — fix findings BEFORE the closing commit. **Lancer ce check
  dans le MAIN working dir, JAMAIS dans un worktree** : un worktree n'a pas les dirs locaux/gitignored cités
  → faux `MISSING` (l'intégrité canonique se vérifie là où vivent les artefacts locaux).
