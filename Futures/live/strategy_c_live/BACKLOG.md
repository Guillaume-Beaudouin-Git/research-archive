# BACKLOG.md — Strategy C live infrastructure

Items are deferred improvements, NOT deployment blockers for current sizing (2 MNQ).
Each entry includes: priority, prereq, description, estimated impact.

---

## strat_c_winner_cap_feature

**Priority**: deferred — do NOT implement before N ≥ 30 live trades  
**Prereq**: N ≥ 30 live trades on Tradeify Select Flex AND DD locked at $25,100  
**Status**: unstarted

**Description**: Implement winner-capping logic in signal_engine.py to reduce or close
position when intraday P&L approaches the eval consistency cap ($600/day). During eval
phase only — no cap applies in funded phase.

Implementation sketch:
```python
# In run_daily.py eval phase check (after each bar update):
if phase == "eval" and intraday_pnl_today >= WINNER_CAP_THRESHOLD:
    # Flatten position — cap contribution at $600
    exit_position()
WINNER_CAP_THRESHOLD = 590  # $10 buffer below $600 cap
```

**Why deferred**:
- Current sizing (2 MNQ): avg winner = $314 << $600 cap → cap effectively never binds.
  CapViol rate = 1% (analytical). No execution risk at 2 MNQ.
- Capping winners reduces edge per L10 (modifications budget). Backtest required to
  confirm net effect on Sharpe before deploying to funded.
- Risk of premature exit on rare high-value trades ($1,572 avg winner at 1 NQ) if
  threshold set too conservatively.

**Estimated impact when implemented**:
- Unlocks sizing upgrade to 3 MNQ: effective P(pass∞) from ~5.9% → ~45% (under strict
  consistency cap interpretation)
- Unlocks 4 MNQ: effective P(pass∞) from ~0% → ~44% (requires backtest validation first)
- See sizing_analysis_results.md §"Effective P(pass∞) under 40% consistency enforcement"

**Before implementing**:
1. VERIFY with Tradeify: does a single day > $600 = immediate eval failure, or just
   capped contribution? Contact support with specific question.
2. Run backtest of winner-capped strategy (new iteration, counts against modification budget)
3. Re-run sizing_analysis.py with winner-cap mechanics modeled

---

## vwap_1min_granularity_verification

**Priority**: P0 — BLOCKING for paper trade start  
**Prereq**: none  
**Status**: known gap (documented in CLAUDE.md)

**Description**: Verify VWAP computed from 1-min bars in tradovate_client.py matches
the VWAP used in iter_10 backtest. If Tradovate only provides session VWAP (not custom
anchor), signal reproduction may differ.

Action: compare live VWAP feed vs manual 1-min VWAP computation on 5 days of data
before paper trade start.

---
