# Code Review Fixes — 2026-05-25

Branch: `fix/review-codebase-pre-paper`
Reviewed scope: `Futures/live/strategy_c_live/` (plus `Portfolio/risk/` for #5)
Suite: 41 tests, all pass.

---

## Finding #1 — VWAP NaN bypass ✓ FIXED (commit 2b54506)

**File**: `signal_engine.py`
**Bug**: `compute_vwap` returned `float(bars["close"].mean())` on empty frame → `nan` as
side-effect (no explicit contract). NaN comparisons in the VWAP filter (both branches false)
allowed a signal to fire with an indeterminate direction.
**Fix**:
- `compute_vwap`: explicit `return float("nan")` for empty frames (contract now explicit).
- `compute_signal`: added `orb_1m_for_vwap.empty` guard + `math.isnan(vwap_at_945)` guard.
**Tests**: `TestComputeVwap.test_zero_volume_fallback` (existing, unchanged);
  `test_compute_vwap_returns_nan_on_empty_frame`,
  `test_compute_signal_skips_when_vwap_returns_nan`,
  `test_compute_signal_skips_on_nan_in_price_data` (all new, all pass).

---

## Finding #2 — mark_payout_requested() missing is_funded guard ✓ FIXED (commit 11c1eca)

**File**: `challenge_state.py`
**Bug**: `mark_payout_requested()` would fire in eval phase, setting `lock_triggered=True`
on an eval account and corrupting `get_phase()` / `get_n_contracts()`.
**Fix**: Added `if not self.is_funded: log.warning(...); return` guard.
**Tests**: `TestMarkPayoutRequested.test_mark_payout_sets_lock_trigger_reason` (new).

---

## Finding #3 — check_lock_trigger() called intraday ✗ INVALIDATED

**File**: `monitor_loop.py`
**Status**: The intraday `check_lock_trigger` call was present only in unstashed working-tree
edits that were never committed. Call-graph confirmed (grep across entire repo):

```
check_lock_trigger — call sites
  challenge_state.py:167   <- function definition
  run_daily.py:299-300     <- ONLY call site, post-trade EOD:
      state.increment_trade_count()   (trade logged)
      final_balance = client.get_account_value()
      state.update_balance(final_balance)
      state.check_lock_trigger(final_balance)  <- HERE
```

Fires **1x per day when there is a trade**, after exit fill confirmed. **0x on no-trade days**
(no session-start call exists yet; `TestSessionStartLockSync` describes a planned but
unimplemented future use case).
No intraday call anywhere in the codebase. The code review correctly identified a stash-only
risk that was never merged.

Note: `run_daily.py:298` has a stale comment (`# EOD balance >= $26,100 + payout requested`)
predating both the $26,600 correction and the OR-logic fix. Minor cleanup, not a safety issue.

---

## Finding #4 — _atr15 receives 2-day frame ✓ FIXED (commit b50b56f)

**File**: `manual_signal.py`
**Bug**: Line 253 `atr15 = _atr15(bars)` passed the full 2-day yfinance fetch.
`_atr15` filters on ORB time range (09:30-09:45) but both days share the same time
range -> yesterday's wider ORB range contaminated the ATR context in Telegram alert and CSV.
**Fix**: `_atr15(today_bars)`.
**Tests**: `TestAtr15Scope.test_full_2day_inflates_atr` (documents bug),
  `test_today_only_gives_correct_atr` (documents fix).

---

## Finding #5 — trailing_dd_simulator.py consistency denominator ✗ INVALIDATED

**File**: `Portfolio/risk/trailing_dd_simulator.py`
**Status**: False positive on stash diff, not on committed code.

The code review flagged a stash change that would have replaced `cum_capped` with
`cum_profit = equity - capital`. That change was never committed. Current committed code:

```python
cum_capped = 0.0                              # line 101 — monotone, init 0
# ...
if pnl > 0:                                   # positive days only
    cum_capped += min(pnl, consistency_cap)   # capped at $600/day, never decreases
if cum_capped >= config.profit_target         # must accumulate $1,500 of capped wins
   and equity >= config.capital + config.profit_target:  # AND net equity must be positive
```

This is **correct**: monotone accumulation of capped positive contributions. The alternative
`cum_profit = equity - capital` would incorrectly allow losing days to reduce cumulative
progress and would not match Tradeify's documented consistency rule.

---

## Finding #6 — Lock trigger AND→OR + reason field ✓ FIXED (commit 11c1eca)

**File**: `challenge_state.py`
**Bugs**:
1. `check_lock_trigger` used AND (balance AND payout) instead of OR (Tradeify: EITHER
   EOD balance >= $26,600 OR first payout -> lock fires).
2. No `lock_trigger_reason` field -> impossible to audit which condition fired.
3. No `is_funded` guard -> eval accounts could lock.
**Fix**:
- Changed condition from AND to OR with separate reason tracking (`"balance"` | `"payout"`).
- Added `if not self.is_funded: return False` guard.
- Added `lock_trigger_reason` field to `__init__`, `_save()`, `load()`.
**Tests**: All 9 `TestLockTrigger` + `TestSessionStartLockSync` + `TestMarkPayoutRequested`
  tests pass.

---

## Config corrections (bundled with #2/#6, commit 11c1eca)

**File**: `config.py`

| Field | Was | Now | Authority |
|-------|-----|-----|-----------|
| `TRADEIFY_LOCK_BALANCE` | 26,100 | **26,600** | rules.md: capital + funded_DD_$1,500 + $100 |
| `N_CONTRACTS_DEFAULT` | 3 | **2** | MC simulation (see Sizing section) |
| `PHASE_CONTRACTS` | {all: 3} | {all: 2} | MC simulation |
| `TRADEIFY_TRAILING_DD_FUNDED` | missing | 1,500 | rules.md |
| `LOCK_TRIGGER_EXCESS` | missing | 100 | rules.md |
| `LOCKED_FLOOR_OFFSET` | missing | 100 | rules.md |
| `CONSISTENCY_RATIO_EVAL` | missing | 0.40 | rules.md |
| `MIN_TRADING_DAYS_EVAL` | missing | 3 | rules.md |
| `PAYOUT_THRESHOLD_DAYS` | missing | 5 | rules.md |
| `WIN_DAY_MIN_PNL` | missing | 100.0 | rules.md |
| `MAX_PAYOUT` | missing | 1,250.0 | rules.md |
| `PAYOUT_PCT_OF_PROFIT` | missing | 0.50 | rules.md |

`test_tradeify_constants.py` (17 tests) + `test_config_sizing_alignment.py` (4 tests) pin
all values against `PropFirms/tradeify/rules.md` and `sizing_policy.md`.

---

## Sizing decision — quantitative backing

Fresh simulation: N=20,000 runs, seed=42, **corrected config** (eval_DD=$1,000,
target=$1,500, consistency_cap=40%, max_eval_days=180):

| MNQ | P(eval pass) | P(bust) | P(timeout) | E[days] | Note |
|-----|-------------|---------|------------|---------|------|
| 1   | 37.5%       | 5.1%    | 57.4%      | 122.6d  | Under-sized: most paths time out |
| **2** | **62.6%** | **34.1%** | **3.2%** | **72.4d** | **Maximizes P(pass)** |
| 3   | 53.7%       | 46.2%   | 0.0%       | 38.4d   | -8.9pp vs 2 MNQ |
| 4   | 47.4%       | 52.5%   | 0.0%       | 23.6d   | Majority bust; cap binds (avg winner $628 > $600) |

**Why 2 MNQ > 3 MNQ despite -33% capacity:**
- Avg daily loss: 3 MNQ ~$127 -> $1,000 DD = 7.9 average-loss-days of runway
- Avg daily loss: 2 MNQ ~$85  -> $1,000 DD = 11.8 average-loss-days of runway
- 72% of trading days are losers -> DD runway determines survival, not capacity
- At 4 MNQ: avg winner ($628) > consistency cap ($600) -> cap binds on all winning days

**Comparison with previous 66%/27%**: That figure used `BASELINE_CONFIG`
(eval_DD=$1,500, max_eval_days=120, 3 MNQ) -- the old wrong config. Under the correct
$1,000 eval DD, 3 MNQ degrades to 53.7%/46.2%. The 2 MNQ choice is robust to config
correction: 62.6% under correct config.

**Slippage sensitivity** (per sizing_policy.md via prior run):
- 2 MNQ x1.5: P(pass)=54.1%, P(bust)=42.5% (still strictly best vs 3 MNQ)
- 3 MNQ x1.5: degrades further

Re-evaluation trigger: N_live >= 30 trades AND funded floor locked ($25,100 reached).

---

## GO / NO-GO for Tradovate Demo Paper Trading

**Recommendation: CONDITIONAL GO**

Blockers cleared:
- [x] VWAP NaN bypass -- signal cannot fire on corrupted data
- [x] Lock trigger logic correct (OR, $26,600) -- funded floor protected
- [x] Config sizing: 2 MNQ -- quantitatively optimal (+8.9pp vs 3 MNQ under $1,000 eval DD)
- [x] Lock threshold correct ($26,600 per rules.md)
- [x] ATR context field scoped to today_bars

Remaining blockers before ANY execution:
- [ ] Tradovate API secrets must be regenerated (current secrets compromised)
- [ ] Run `validate_tradovate.py` -- verify 1-min bar granularity (KNOWN GAP in CLAUDE.md)
- [ ] Manual paper mode: run `manual_signal.py --test-telegram` before first session
- [ ] Fix stale comment in `run_daily.py:298` before live (shows wrong threshold + AND logic)
