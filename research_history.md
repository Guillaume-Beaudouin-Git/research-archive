# Algo_claude — Research history (archive)

Extrait de `CLAUDE.md` (§ Research history). Registre **« DO NOT re-propose without strong new evidence »**. Le ledger global (n_tests = 321), la convention de comptage, les milestones séquentiels, les stratégies validées/actives restent dans `CLAUDE.md`.

### ✗ Archived — DO NOT re-propose without strong new evidence

**Crypto (n=159, free-data EXHAUSTED — 7 missions, 11 signal families)**
- All long-only CS: β-dominance (L11) kills every signal regardless of IC
- Delta-neutral: PMR basis (IC real but 912 events/yr → 178%/yr cost drag, L12), OAGF (128/yr sparse, L12 floor), CS-FS (t=1.54), FRA (t=1.01 regime-specific)
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
- Strategy E — WMR Fix + EOM USD Flow (n_reg=175, 0 IC tests): CLOSED at literature stage. E1 W-shape: 1-4bp gross < 6-7bp retail RT post-BIS 2015 reform. E2 EOM USD conditioned: t_HAC≈1.2, N_eff≈35-45 → power collapse (L12). Root: window widening (L23) + TWAP algoisation. Dukascopy M5 infra reusable. `Forex/research/archived/strategy_e_fix_flow/POSTMORTEM.md`
- G1 — Carry G10 conditionnel VXY-vol + Fed-stance (n_reg=180, 0 IC tests): CLOSED at literature stage. L11 3× gate fail (530 vs 540 bps best case, ratio 0.98); Lesson 10 budget épuisé (FX-1→FX-4). G2D pivot: Koijen 2018 carry cross-asset (Tradovate infra réutilisable). `Forex/research/archived/g1_carry_conditional/POSTMORTEM.md`
- **Strategy F2 — Asian Range Breakout London Open (n=181, 0 backtests):** ARCHIVED at L11 preflight. IJR gate_ratio=0.751 (best case N_calendar=94) < 3.0. Root: IJR formula structurally fails for binary TP/SL (ratio = C/√N, decreasing in N; passes only at N≤6 trades/yr at IC=0.05). Alt binary TP/SL gate: ratio=2.565 < 3.0 at IC=0.05; passes at IC≥0.107 (win_rate≥55.3%) but no numerical lit backing. See L11b. Dukascopy Pool(4) infra + news_events_2020_2025.csv reusable. `Forex/research/archived/strategy_f2_asian_breakout/POSTMORTEM.md`
- CIP-EOQ (covered-interest-parity end-of-quarter dislocation): archivé avec POSTMORTEM — `Forex/research/archived/cip_eoq/`. Doublon `active/` supprimé au cleanup 2026-06-10.

**Equities/ETF/Futures**
- D1 (Failed ORB fade, n_test=154): NQ fade when iter_10 signal fires then reverses 0.5R/30min. Sharpe=-0.14, IC_t=1.55 (below gate 2.5), WF=66.7%, corr_C=-0.04. Edge absent post-costs. Decorrelation from C confirmed. Lit: Brock et al. (1992), Lo-Mamaysky-Wang (2000). ARCHIVED.
- D4 (Lunch RSI reversal, n_test=157): NQ 12:00-13:00 30-min RSI mean reversion. Sharpe=-0.70, IC_t=1.61 (below gate 2.5), WF=22.2%, corr_C=-0.02. No edge. Lit: Wilder (1978), Jain & Joh (1988). ARCHIVED.
- Multi-asset TSMOM: Sharpe 0.21 corrected (HAC+excess returns), alpha t=1.31
- Pairs cointegration (0/19 qualify), Gatev distance (Sharpe -0.44, t=-2.5)
- VIX term carry (Sharpe 0.67, alpha t=0.71 insufficient)
- Sector reversal (Sharpe -0.60, t=-3.7 negative alpha)
- Commodity TSMOM ETF (Sharpe 0.39, AMTP p=0.808 — ETF roll drag)
- NQ VWAP MR / afternoon momentum: all FAIL ($19 RT cost kills any edge)
- NQ ORB IVB (Conti/Valentini): Sharpe -0.09/-0.44, 0/5 propfirm gates
- Equity indices_swing Sprint 1+2 (100 tests): IC 0.033-0.075, all fail backtest (best Sharpe 0.45 at futures cost, costs kill at ETF level)
- NQ Pairs ES/NQ: EG p=0.28 (tech premium drift 2024-2026 destroys stationarity)
- Network Momentum GMOM: universe too small (N<35 after quality filter), graph density=1.0 → FAIL, best variant E3 Sharpe=0.293. `Multi_Asset/research/archived/network_momentum/` (déplacé de active/ 2026-05-30).
- jt_momentum_cs (Equities, J-T CS 70 stocks monthly): sharpe=-0.026, max_dd=-0.58, ic_tstat=-0.49, gate=SKIP. `Equities/research/archived/jt_momentum_cs/` (déplacé de passed/ 2026-05-30 — mal classé).
- h31_cs_fs_dn (Crypto CS funding stack delta-neutral, test #160): sharpe_raw=-0.80, wf=25%, all 3 gates FAIL. `Crypto/research/archived/h31_cs_fs_dn/` (déplacé de active/ 2026-05-30 — FAIL net déjà mesuré).

**Options (n=1)**
- SPX VRP Angle C (VIX_z conditional): IC t=-0.144, wrong direction
- BTC VRP Deribit (n=156): gross 4.4%/yr, costs 8.9%/yr (L13)

### Deferred — promising but blocked
- D2 (VWAP touch fade post-noon, n_test=155): NQ 11:30-14:00 momentum exhaustion fade. Sharpe=-1.48, IC_t=-0.86 (wrong direction), corr_C=-0.005. Signal directionally inverted — deferred pending regime-conditional retesting. `Futures/research/active/nq_intraday/analysis/`

### Untested — requires paid data or new infra
- Glassnode stablecoin mint/burn (~$500/mo) — only remaining crypto angle with theoretical zero TSMOM corr
- Apex challenge analysis for Strategy A (EOD trailing, CME futures): [CADUC 2026-06-10 — propfirms retenus: FTMO + Propr] — see PropFirms/comparison.md
- Token unlock cliff shorts (TokenUnlocks.app, free)
- HLP vault flow contrarian, Uniswap V3 LP rebalancing (HL API + The Graph, free)
- GitHub commit velocity as dev proxy (GitHub REST API, free)
- BTC cross-exchange lead-lag Coinbase→Binance (Shu 2023) — multi-venue WebSocket
