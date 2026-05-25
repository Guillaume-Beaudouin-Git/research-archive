# Code Review Fixes — 2026-05-25

Branch: `fix/review-codebase-pre-paper`
Reviewed scope: `Futures/live/strategy_c_live/` (plus `Portfolio/risk/` for #5)
Suite: 41 tests, all pass.

---

## Finding #1 — VWAP NaN bypass ✓ FIXED (commit 2b54506)

**File**: `signal_engine.py`
**Bug**: `compute_vwap` returned `float(bars["close"].mean())` on empty frame → `nan` as
side-effect, but no explicit contract. NaN comparisons in the VWAP filter (both branches
false) allowed a signal to fire with an indeterminate direction.
**Fix**:
- `compute_vwap`: explicit `return float("nan")` for empty frames (contract now explicit).
- `compute_signal`: added `orb_1m_for_vwap.empty` guard + `math.isnan(vwap_at_945)` guard.
**Tests**: `TestComputeVwap.test_zero_volume_fallback` (existing, unchanged),
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
edits that were lost when the fix branch was created. The committed code does NOT call
`check_lock_trigger` in `monitor_loop.py`. Call sites are EOD-only in `run_daily.py:299`.
No action needed. Guard: do NOT add intraday `check_lock_trigger` calls in future edits.

---

## Finding #4 — _atr15 receives 2-day frame ✓ FIXED (commit b50b56f)

**File**: `manual_signal.py`
**Bug**: Line 253 `atr15 = _atr15(bars)` passed the full 2-day yfinance fetch.
`_atr15` filters on ORB time range (09:30-09:45) but both days share the same time
range → yesterday's wider ORB range contaminated the ATR context value in the
Telegram alert and CSV log.
**Fix**: Changed to `_atr15(today_bars)`.
**Tests**: `TestAtr15Scope.test_full_2day_inflates_atr` (documents bug),
  `test_today_only_gives_correct_atr` (documents fix).

---

## Finding #5 — trailing_dd_simulator.py consistency denominator ✗ INVALIDATED

**File**: `Portfolio/risk/trailing_dd_simulator.py`
**Status**: The problematic change (replacing monotone `cum_capped` with `cum_profit =
equity - capital`) was in unstashed working-tree edits, lost during branch creation.
The committed code correctly uses `cum_capped` (monotone accumulator, positive days only,
capped at 40% × target per day) — which matches Tradeify's documented rule.
No action needed.

---

## Finding #6 — Lock trigger dual-reason recording ✓ FIXED (commit 11c1eca)

**File**: `challenge_state.py`
**Bugs**:
1. `check_lock_trigger` used AND (balance AND payout) instead of OR (Tradeify rule: EITHER
   EOD balance ≥ $26,600 OR first payout requested triggers the lock).
2. No `lock_trigger_reason` field → impossible to audit which condition fired.
3. No `is_funded` guard in `check_lock_trigger` → eval accounts could lock.
**Fix**:
- Changed condition from AND to OR; each branch records `lock_trigger_reason = "balance"`
  or `"payout"`.
- Added `if not self.is_funded: return False` guard.
- Added `lock_trigger_reason` field to `__init__`, `_save()`, `load()`.
**Tests**: All 9 `TestLockTrigger` + `TestSessionStartLockSync` + `TestMarkPayoutRequested`
  tests pass.

---

## Config corrections (bundled with #2/#6)

**File**: `config.py`

| Field | Was | Now | Authority |
|-------|-----|-----|-----------|
| `TRADEIFY_LOCK_BALANCE` | 26,100 | 26,600 | rules.md: capital+funded_DD+$100 |
| `N_CONTRACTS_DEFAULT` | 3 | 2 | sizing_policy.md 2026-05-24 |
| `PHASE_CONTRACTS` | {all: 3} | {all: 2} | sizing_policy.md 2026-05-24 |
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

## GO / NO-GO for Tradovate Demo Paper Trading

**Recommendation: CONDITIONAL GO**

Blockers cleared:
- [x] VWAP NaN bypass — signal can no longer fire on corrupted data
- [x] Lock trigger logic correct (OR, not AND) — funded floor protected properly
- [x] Config sizing: 2 MNQ live (matches sizing_policy.md, consistency cap not binding)
- [x] Tradeify lock threshold: $26,600 (correct per rules.md)
- [x] ATR context field correct in Telegram / CSV

Remaining known gaps before LIVE:
- [ ] Tradovate REST API secrets must be regenerated before any live/demo execution
- [ ] `KNOWN GAP` from CLAUDE.md: verify Tradovate client delivers 1-min granularity
  for VWAP computation (not resampled to 5-min); run `validate_tradovate.py`
- [ ] Manual paper trade mode (`manual_signal.py`) in use until API secrets regenerated
  — run `--test-telegram` to confirm Telegram delivery before first session
