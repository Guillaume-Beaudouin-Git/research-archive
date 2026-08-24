# ZN Intraday Momentum (Baltussen 2021) — Pre-registered spec

**Date**: 2026-05-26  
**Branch**: feature/zn-baltussen-feasibility  
**Reference**: Baltussen, Da, Lammers, Martens (2021) *JFE* 142(1), 377-403  
**n_tests prior to this spec**: 322 (global register)

---

## Universe
- ZN (10-Year T-Note futures, CBOT/CME)
- Contract specs: 1 point = $1,000, tick = 1/64 pt = $15.625, face value $100,000
- Backtest period: 2018-01-01 → 2025-12-31 (8 years)
- Walk-forward: 5 expanding folds

## Signal (Baltussen pure)
- `return_rtd = (price_1500 - price_0930) / price_0930`
  - `price_0930`: ZN price at 09:30 ET (equity market open)
  - `price_1500`: ZN price at 15:00 ET
- Direction at 15:00 ET: `+1` if `return_rtd > 0`, `-1` if `return_rtd < 0`
- Entry: 15:00 ET (market order at open of the 15:00-15:30 bar)
- Exit: 15:30 ET (fixed time exit)
- Hold period: 30 minutes

## Event-day conditioning (H2)
Days classified as event-days if at least one macro announcement:

| Type | Release time | Frequency | Source |
|------|-------------|-----------|--------|
| NFP  | 08:30 ET (1st Fri of month) | ~12/yr | BLS |
| CPI  | 08:30 ET (~13th of month)   | ~12/yr | BLS |
| FOMC | 14:00 ET (~8 meetings/yr)   | ~8/yr  | Fed |
| PCE  | 08:30 ET (last Fri of month)| ~12/yr | BEA |

Total events: ~44/yr. Calendar hardcoded from official sources 2018-2025.

## Risk filters
- Hard SL: 8 ticks per trade = $125 per ZN contract
- Skip day if VIX close > 25 (proxy for MOVE > 130 when MOVE data unavailable)
- FOMC days at 14:00: signal window modified to exclude the spike (H2 uses full FOMC signal)

## Hypotheses (pre-registered, cannot be modified post-run)

### H1 — Baltussen pure (all days, 2018-2025)
- Gross Sharpe ≥ 1.0 (Baltussen aggregate bonds SR ≈ 1.62, applying 40% decay for retail/2018-2025)
- Win rate ≥ 53%
- N_trades ≥ 1,800 (8yr × 252 sessions ≈ 2,016)

### H2 — Event-conditional only (2018-2025)
- Gross Sharpe ≥ 1.3 (amplification hypothesis)
- Win rate ≥ 55%
- N_trades ≥ 350 (~44/yr × 8yr = 352)

### H3 — Sub-period stability (decay test)
- Sub-period A: 2018-2021 (low-rates, QE regime)
- Sub-period B: 2022-2025 (QT/inflation regime)
- Pass: Sharpe_B ≥ 0.6 × Sharpe_A (decay < 40%)

## Gates PASS/FAIL

| Scenario | Decision |
|----------|----------|
| H1 PASS + H2 PASS + H3 PASS | Proceed to tail-risk stress test → RESEARCH_PASS candidate |
| H1 PASS + H3 FAIL | Significant regime decay — mark for monitoring; DO NOT trade live |
| H2 PASS + H1 FAIL | Event premium real but base signal absent — event-only strategy possible |
| H1 FAIL | Archive — Baltussen mechanism doesn't transfer to ZN retail 2018-2025 |

## Cost model
- Commission: $2.25/side = $4.50 RT (Tradovate)
- Spread/slippage: 0.5 tick = $7.81/side = $15.62 RT
- **Total: $20.12 RT (base), $35 RT (conservative)**
- Code uses `COST_RT_USD = 20.0` base; stress-test at 35.0

## Tail-risk flag threshold
If max single-day loss > 50% of expected annual profit → FLAG as tail-risk binding.

## Data resolution note
- **Canonical**: 1-min ZN RTH bars, 2018-2025 (FirstRateData ~$99 or Databento)
- **Canary mode**: yfinance 1h bars (lookback ~730 days from run date, ≈Jun 2024+)
  - `price_0930_proxy` = Open of the 10:00 ET hourly bar
  - `price_1500` = Open of the 15:00 ET hourly bar
  - Exit proxy = midpoint of 15:00-16:00 bar = (Open + Close) / 2
  - All canary results are APPROXIMATE; SL intra-bar approximation using bar High/Low

## Modification budget
This spec is iteration 0. Maximum 3 modifications permitted before archiving (CLAUDE.md rule).
