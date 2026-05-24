# Feasibility Pipeline — Improvements TODO

Issues identified during first night of operation (2026-05-24):

## P0 — Reduce REQUIRES_HUMAN rate (currently 84%)

Decompose REQUIRES_HUMAN into 3 sub-categories to find the testable ones:
- IRREDUCIBLE (methodology, meta-frameworks): ~30% — no handler can automate
- HANDLER_MISSING (regime, exit rule, portfolio, stress test): ~30% — build dedicated handlers
- DATA_UNAVAILABLE (options chains, sentiment NLP, tick L2/L3): ~20% — explicit flag, not generic REQUIRES_HUMAN
- NOISE (mal classé par collector): ~5% — tighten L0/L1/L2 at collector level

Target: 40-50% PASS/FAIL automated, 20-30% IRREDUCIBLE, 20-30% DATA_UNAVAILABLE, <10% noise.

## P1 — Data accessibility filter

Add L3 filter at collector level: reject hypotheses requiring data we don't have.
- Paid feeds (RavenPack, Bloomberg terminal, OptionMetrics, Refinitiv)
- Tick data L2/L3
- Earnings call transcripts
- Macro alternative data (satellite, credit card)

Add metadata "data_required" in each promising/.md.

In feasibility GenericHandler, add DATA_UNAVAILABLE category with structured verdict
(not generic REQUIRES_HUMAN).

## P2 — Build 3 dedicated handlers (week 1-3)

1. StressTestHandler: tests "apply Backtests Lie stress framework to Strategy X"
   - Tests known: Concretum dispersion, look-ahead detection
   - Applies to: Strategy A/B/C before any deployment decision
   
2. RegimeFilterHandler (complete, not stub):
   - Markov-switching with TVTP
   - HMM (Gaussian, Viterbi smoothing)
   - VIX threshold conditioning
   - Verdict: regime-conditional IC + persistence
   
3. PortfolioAllocationHandler:
   - Risk parity / ERC
   - Risk-weighted vs capital-weighted comparison
   - Correlation matrix stability under stress

## Realistic limits acknowledged

The retail quant universe is constrained by data availability. Strategies feasible:
- Crypto perp TSMOM/carry (exchange APIs)
- Futures intraday momentum (Kaggle/IBKR/Polygon basic)
- FX daily macro overlay (Dukascopy + FRED)
- Equity daily without options (yfinance)

NOT feasible without paid data:
- News-sentiment alpha
- Options-implied factors
- Tick-level microstructure
- Cross-asset event-driven (M&A, spinoffs)

Pipeline should EXPLICITLY flag these in DATA_UNAVAILABLE category, not pretend
to test them.
