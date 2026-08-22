# FTMO research — session handoff (resume here)
*Read this one file to restore context in a fresh chat. Created 2026-06-02 because the prior session hit the length limit.*

> **⚠ AUTHORITY (2026-06-03): `_CANONICAL_STATE.md` is now the single source of truth — read it first.** Verdict: **FTMO = CONFIRMÉ-CLOS** (no accessible retail edge after real costs). Both the ORB (killed by spread, L33) and the overnight harvester (killed by overnight swap — reconciled in `_RECONCILIATION_overnight.md`) are idealized-cost mirages that sign-flip at real cost. The optimistic numbers in the two `*_metrics/` dossiers are **idealized-cost**, not deployable. Do not allocate cycles to FTMO without the hard re-open conditions in canonical §6. The notes below are historical context.

## How to resume
Start a new chat and paste: *"Read `Algo_claude/data/ftmo_research/_HANDOFF.md` and continue the OVERNIGHT_drift_hardening mission from where it left off."*

## User profile
Quant-finance student, GitHub/CV projects. Wants: production-grade Python (pandas/numpy/sklearn), quant rigor (no look-ahead, OOS, stat validity), concise, realistic industry methods, intellectual honesty ("no signal" is a valid result). French/English mix OK.

## The goal
Strategies to pass an **FTMO 2-step challenge**, $10k account: P1 +10%, P2 +5%, 5% max daily DD ($500), 10% max total DD ($9k floor), min 4 trading days, **NO time limit** (30-day cap removed — confirmed).

## Where the research converged (the bottom line)
- Liquid intraday price-pattern families (ORB, mean-reversion, carry, stat-arb, intraday-momentum) on FX majors / indices / crypto: **no robust two-sided all-regime +EV edge.** All cost-killed, shape-failed (symmetric barrier punishes both skews), or revealed as beta. Documented in `SCAN_ftmo_families.md`.
- **The one robust positive thing = the overnight equity risk premium (beta).** Best vehicle found: a **200-day-MA-gated overnight-drift harvester on NQ**, small size, no time limit.
- Clean contiguous NQ databento 2010-2026, net ~2bps/night: **p(funded) 88% @0.5× (0% bust, ~3.5yr) / 82% @0.75× (9% bust, ~2.3yr) / 67% @1.0× (29% bust, ~1.5yr).** Survived COVID-2020 + 2022 bear. Documented in `OVERNIGHT_drift_findings.md`.
- Independent verification confirmed the signal: overnight-gated Sharpe ~1.35, +5.6 bps/night gross, positive ~13/15 yrs, gate sat out 2022. **Signal existence is settled — do NOT re-test it.**
- A prior "82% is a bull-market artifact / 4-15%" claim was **retracted** — it used an IID bootstrap (destroys regime clustering) + a contaminated daily panel. User correctly pushed back. The 82-88% is in-sample, pre-financing, no-crash-tail.

## CURRENT MISSION (in progress): OVERNIGHT_drift_hardening.md
Price the **deployable** number — net of financing at TODAY's rate, crash-tail-aware, time-aware, replicated. It's beta; price it as such. Target deliverable: `OVERNIGHT_drift_hardening.md` with 5 sections + verdict (does honest p(funded) stay >70% or fall?).

### Check 1 — Financing/swap (PRIORITY, binary). PARTIAL ANSWER ALREADY FOUND:
- FTMO **charges standard overnight swap on indices** (US500/US100/US30 rolling contracts are commission-free but swaps still apply; dividends folded into swap). **Swap-free Islamic accounts exist on request.** The **2-Step Swing account** allows holding overnight + over weekend with no limits (leverage capped 1:30). Sources: ftmo.com/en/blog/what-is-a-swap-and-for-whom-is-it-important, ftmo.com/en/faq/ftmo-swing-account-type, invezz.com/reviews/ftmo, fundedtradingplus best-swap-free list.
- **STILL TODO:** exact index swap rate (ref rate + broker spread); recompute net p(funded) **by rate era** — swap ≈0 in ZIRP (2010-21), ≈2bps/night at 5% (2022-26). Gross gated ~5.6bps → recent net ~3-4bps. Re-run p(funded) at TODAY's rate held for years (not the 16yr avg). Binary upshot: swap-free/Islamic or Swing acct → risk evaporates; standard swap → drag. CONFIRM whether challenge accounts can be swap-free.

### Check 2 — Crash-from-highs tail (TODO)
MA200 gate lags; a bearish overnight gap while above MA busts before it reacts. Quantify worst overnight close→open gap while above MA200 across NQ + US500 + GER40 (daily panel 2000-2026 captures 2008/COVID; cite 1987 −20% SPX as catastrophic ref). Bust threshold at 0.5×/0.75×. Is the tail a smooth 5-10pt haircut or a rare binary total bust? Does a fixed catastrophe stop or ≤0.5× sizing make it non-fatal without over-extending the grind? (COVID survived at 0.5×.)

### Check 3 — Time + FTMO multi-year rules (TODO)
Median 2.3-3.5yr, 9-12% never finish. Web-search: does FTMO allow a 2-3yr hold? Inactivity rules, recurring account fees, expiration? Opportunity cost vs activating other strategies on a funded account.

### Check 4 — √N replication on a 2nd index (TODO)
Same overnight-gated harvester on ES/SPX + DAX. Clean intraday available: MT5 m1_panel has US500 + GER40 (2020-2026, incl COVID+2022). Does Sharpe / p(funded) replicate? Beta-equity edge should replicate — if not, flag.

### Verdict to write
Honest deployable p(funded) net-of-financing-at-current-rate + queue-aware + temps-aware. State clearly vs in-sample 82-88%. Expected shape of answer: "current-rate swap + crash tail bring deployable to ~X%."

## Key data files (all under Algo_claude/data/)
- `raw/NQ_1min_databento_2010-2026.parquet` — clean, UTC index, cols incl open/close/is_rth/is_roll_day, 5.1M rows. THE clean source.
- `panels/m5_indices/m1_panel.parquet` — US100/US500/US30/US2000 M1, 2020-2026 (MT5). + GER40 panel. Use for Check 4 replication.
- `panels/ftmo_close.csv` / `ftmo_open.csv` — daily indices 2000-2026 (yfinance opens unreliable pre-2010 for small gaps, but BIG gaps 2008/COVID are real → usable for Check 2 tail magnitude only).
- `panels/fx_rates_3m.csv`; uploaded FX M1 (GBPUSD/USDJPY/etc) + crypto.
- `code/`: data.py, costs.py, strategy_orb.py (EET sessions, ENSEMBLE dict), ftmo_sim_ensemble.py (day-block bootstrap MC).

## Reusable methodology notes
- Contiguous **real-path** sim, NOT IID bootstrap (IID destroys regime clustering — wrong for a gate that sits out clustered bears). Block/stationary bootstrap if resampling.
- Delay-sensitivity test catches look-ahead artifacts (real edge survives 1-bar entry delay; artifacts collapse).
- Nowcast (concurrent) ≠ forecast (predictive). Regime is weakly nowcastable (vol AUC 0.60), persistent (daily P_stay 0.95), NOT transition-forecastable → only a +3-8pt sizing tilt. (`REGIME_modeling_NQ.md`)
- Timezone: MT5 exports = broker EET (UTC+2/+3); US cash open = 16:30 EET in MT5 data, DAX = 10:00. NQ databento = true UTC w/ is_rth flag.
- First-passage math: for μ>0, dividing sizing by k scales p(pass)→1 (conditional on μ>0; ~50% at μ=0, <50% w/ costs).
- Sandbox: /tmp is RAM-backed tmpfs — large parquet/npy caches there → OOM (exit 137). `rm -f /tmp/*.parquet /tmp/*.npy` to free. Use memory-frugal numpy/pyarrow.
- Sandbox 45s timeout: avoid pandas groupby-lambda on 5M rows → vectorize / single linear pass.

## Other reports in this folder (context, not all need re-reading)
SCAN_ftmo_families.md, OVERNIGHT_drift_findings.md, REGIME_modeling_NQ.md, OPTIM_execution_realism.md, OPTIM_regime_timing_intraday.md, OPTIM_regime_landscape_freedata.md, CHALLENGE_REPORT_FINAL.md, RISK_REVIEW_ensemble.md, REPORT_strategy1/2*.md, RESEARCH_no_time_limit.md, STRESS_TEST_strategy2.md.
