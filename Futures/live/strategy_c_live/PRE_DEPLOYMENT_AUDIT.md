# PRE-DEPLOYMENT AUDIT — Strategy C Tradeify Select Flex $25K
**Audited:** 2026-05-23  
**Config:** iter_10 | VWAP + gap≤1.2% + rng≥30pt + $400 SL cap | 3 MNQ all phases  
**Broker:** Tradovate REST (demo → live)  
**Methodology:** Read-only. No code modified during audit.

---

## Verdict: FIX FIRST

**2 blockers** must be resolved before going live. 4 additional warnings documented below.

| Blocker | File | Line | Summary |
|---------|------|------|---------|
| B1 | `run_daily.py` | 302–303 | Lock trigger Telegram says `$52,100` / `5 MNQ` (stale $50K values) |
| B2 | `validate_tradovate.py` | T5 | Guardrail commit gate uses $50K state → **FAILS** on $25K config |

---

## AXE 1 — Backtest Reproduction ✅ PASS

Reproduced iter_10 from scratch on full 2022-12-26 → 2025-12-11 dataset.

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| N trades | 346 | 346 | ✓ |
| Sharpe HAC | 1.5212 | 1.5212 | ✓ |
| MaxDD | -13.4% | -13.4% | ✓ |

**No implementation drift.** Signal builder, backtest engine, and cost model are consistent.

---

## AXE 2 — Signal Engine vs Backtest TP/SL ⚠️ WARN

**Finding:** `signal_engine.py` computes TP/SL prices from `entry_estimate = close_price` (09:45 bar close), but the backtest engine (`engine.run()`, line 119) uses `entry_price = future.iloc[0]["open"]` (09:46 open).

Live bracket orders will be placed at TP/SL levels anchored to 09:45 close, not actual 09:46 fill.

**Quantified on 346 signal days:**

| Statistic | Value |
|-----------|-------|
| Mean directional gap | -0.025 pts |
| Median gap | 0.000 pts |
| MAE | 0.452 pts |
| P95 | 0.8 pts |
| Max (any single day) | 6.0 pts |
| Days with gap > 5 pts | 3 (0.9%) |

**Assessment:** Negligible systematic impact. Median gap is 0 pts; 95% of days within 0.8 pts vs ORB range ≥30 pts. P&L calculation in `monitor_loop._build_exit()` uses **actual broker fill prices** — not the estimate — so realized P&L is correct. The TP/SL level shift only affects fill probability on extreme-gap days (0.9% of trades).

**Non-blocking.** No fix required before go-live.

---

## AXE 3 — P&L Conservation ✅ PASS

Traced the full P&L flow:

```
place_bracket_order() → open_trade.entry_price (fill from /fill/list poll, 2s after placeOSO)
   ↓
monitor_position() → _build_exit(entry_price, exit_price) → pnl_net = pnl_gross - COST_RT × n
   ↓
run_daily.py → log_trade(actual_entry_price, actual_exit_price) → pnl_usd in CSV
   ↓
state.update_balance(client.get_account_value()) → uses ACTUAL broker balance (not computed P&L)
```

All three P&L paths (monitor_loop, log_trade, challenge_state) are consistent:
- `monitor_loop`: uses `POINT_VALUE=2.0`, `TRADE_COST_PER_UNIT=2.15` from config
- `log_trade.py`: hardcodes `mnq_pv=2.0`, `mnq_cost=2.15` — consistent
- `challenge_state`: reads actual broker NAV — ground truth

**Minor WARN:** `open_trade.get("entry_price")` may be `None` if the 2-second post-fill poll in `_resolve_bracket_ids()` misses the fill. In that case `pnl_net` is `None` in the exit log. Challenge state still reads correct balance from broker. Occurs if Tradovate `/fill/list` is slow — unlikely but possible.

---

## AXE 4 — Guardrail Scenarios ❌ FAIL → Blocker B2

**Test:** `validate_tradovate.py T5` (offline, no broker connection required).

**Result:**
```
FAIL T5 — TRAILING_DD_BREACH: $1,500.00 from peak $51,500.00 >= $1,300 guardrail
           (Tradeify limit $2,000, phase=pre_lock)
```

**Root cause:** T5 sets `state.peak_balance = 51_500`, `current = 50_000` → trailing DD = $1,500. This was designed to PASS when `GUARDRAIL_TRAILING_DD_USD = 1,750` ($50K config), but now fails because the guardrail was tightened to `$1,300` ($25K config).

**The guardrail CODE is correct** — it reads `GUARDRAIL_TRAILING_DD_USD` from config and fires at $1,300 as intended. The **TEST** is broken: all 5 T5 sub-scenarios use $50K-scale state parameters that no longer match the $25K guardrail thresholds.

T5 is the pre-deployment commit gate (`COMMIT GATE: T1-T5 must PASS`). This gate is currently broken and must be fixed.

**Fix required:** Rewrite T5 with $25K-calibrated state parameters.

---

## AXE 5 — Constant Coherence ❌ FAIL → Blocker B1 + WARNs

Full grep for stale dollar amounts and contract counts across all live files.

### B1 — `run_daily.py` lock trigger message (BLOCKER)

**File:** `run_daily.py:297-303`
```python
# EOD lock trigger check (Tradeify: EOD balance >= $52,100 + payout requested)
if state.check_lock_trigger(final_balance):
    _send_telegram(
        f"NQ-C | {trade_date} | LOCK TRIGGERED\n"
        f"EOD balance ${final_balance:,.2f} >= $52,100 + payout requested.\n"   # ← WRONG
        f"Floor locked at ${state.lock_floor:,.0f}. Phase → post_lock (5 MNQ)."  # ← WRONG
    )
```

Both hardcoded strings are stale $50K values:
- `$52,100` should be `$26,100` (config: `TRADEIFY_LOCK_BALANCE = 26_100`)
- `5 MNQ` should be `3 MNQ` (config: all phases = 3 MNQ)

Note: `state.check_lock_trigger()` itself uses `TRADEIFY_LOCK_BALANCE` from config → logic is correct. Only the **Telegram notification text** is wrong, but it will confuse the operator at a critical moment.

### Additional WARNs (non-blocking)

| # | File | Line | Stale value | Should be |
|---|------|------|-------------|-----------|
| W1 | `guardrails.py` | 120 | `${2_000:,}` in exception message | `${TRADEIFY_TRAILING_DD_USD:,}` = $1,500 |
| W2 | `challenge_state.py` | 207 | log: `3 MNQ → 4 MNQ` | `3 MNQ → 3 MNQ` |
| W3 | `guardrails.py` | 7–8, 102–103 | docstring: `$1,750`, `$800`, `5 MNQ`, `$50,175`, `$50,100` | $1,300, $400, 3 MNQ, $25,175, $25,100 |
| W4 | `challenge_state.py` | 2–11, 46, 170 | docstring: `$50K`, `$52,100`, `$50,100`, `4 MNQ`, `5 MNQ` | $25K values throughout |
| W5 | `run_daily.py` | 2–4 | docstring mentions IBKR / MT5 as primary | Tradovate is primary |

---

## AXE 6 — End-to-End Dry Run ⏭️ PENDING (manual)

Requires live Tradovate Demo credentials. Tests T1–T4 in `validate_tradovate.py`.

**Instructions (post-market, 16:00+ ET):**
```bash
# 1. Set credentials in .env
export TRADOVATE_USERNAME=...
export TRADOVATE_PASSWORD=...
export TRADOVATE_CID=...
export TRADOVATE_SECRET=...
export TRADOVATE_ENV=demo

# 2. Run T1-T4 automated tests
python3 -m Futures.live.strategy_c_live.validate_tradovate T1 T2 T3

# 3. T4 requires market hours (RTH 09:30–16:00 ET) — skip if post-market
# 4. T6 dry run:
python3 -m Futures.live.strategy_c_live.run_daily
# Expected: connects, no signal (market closed), Telegram "SKIPPED", exit 0
```

T5 cannot be run until Blocker B2 is fixed.

---

## AXE 7 — SPOF Audit ✅ PASS (with WARN)

| Failure scenario | Defense | Assessment |
|-----------------|---------|------------|
| VPS reboot mid-day | Per-day cron restart; challenge_state.json persists; HALTED sentinel survives | ✅ OK |
| Token expiry (80min) | `_refresh_token_if_needed()` before every API call | ✅ OK |
| Telegram down | Non-blocking `try/except`; falls back to log | ✅ OK |
| Bad fill (fill not in /fill/list) | entry_price=None → pnl_net=None; challenge_state reads actual broker balance | ✅ OK |
| Connection lost intraday | 3 reconnect attempts × 15s; then RECONNECT_FAILED + emergency_flat + HALT sentinel | ✅ OK |
| Time stop at 12:30 | Fires regardless of loop state; cancel_all + flatten_position | ✅ OK |
| Rollover (front month) | `get_mnq_contract()` called fresh each day via `/contract/suggest` | ✅ OK |

**WARN — Time stop exit price (monitor_loop.py:250):**

`flatten_position()` returns `{'orderId': id}` but monitor_loop does `flat_result.get("ticket")` → returns `None` (wrong key). `wait_for_fill(None)` returns immediately. Fallback: `get_current_price()` (bid/ask mid) used as exit price.

**Financial impact: none.** Position is correctly closed via `/order/liquidatePosition`. Only the logged exit price and P&L are approximate (bid/ask mid vs actual fill — typically <1 pt difference at time stop). Challenge state reads actual broker balance regardless.

Fix: change line 250 from `flat_result.get("ticket")` to `flat_result.get("orderId")`.

---

## Fix List (before go-live)

### Blockers (must fix)

**B1 — `run_daily.py:302-303`**
```python
# BEFORE
f"EOD balance ${final_balance:,.2f} >= $52,100 + payout requested.\n"
f"Floor locked at ${state.lock_floor:,.0f}. Phase → post_lock (5 MNQ)."

# AFTER
f"EOD balance ${final_balance:,.2f} >= ${TRADEIFY_LOCK_BALANCE:,} + payout requested.\n"
f"Floor locked at ${state.lock_floor:,.0f}. Phase → post_lock ({state.get_n_contracts()} MNQ)."
```
Also fix import: add `TRADEIFY_LOCK_BALANCE` to the config imports at top of `run_daily.py`.

**B2 — `validate_tradovate.py:T5`**
Rewrite T5 with $25K parameters:
- `initial_balance = 25_000`, `peak_balance = 26_000`, `balance_at_day_open = 25_200`
- `lock_floor = 25_100`
- T5.1: current=25_000, trailing_dd=1,000 < 1,300 → PASS
- T5.2: current=24_500, trailing_dd=1,500 >= 1,300 → TRAILING_DD
- T5.3: day_open=26_000, current=25_550, daily_loss=450 >= 400 → DAILY_SELF_LIMIT
- T5.4 post-lock: current=25_200 > 25,175 guardrail → PASS
- T5.5 post-lock: current=25_100 < 25,175 guardrail → POST_LOCK_FLOOR

### Recommended (before go-live, low risk)

**W1 — `guardrails.py:120`**
```python
# BEFORE
f"(Tradeify limit ${2_000:,}, phase={phase})"
# AFTER
f"(Tradeify limit ${TRADEIFY_TRAILING_DD_USD:,}, phase={phase})"
```
Add `TRADEIFY_TRAILING_DD_USD` to imports in `guardrails.py`.

**W2 — `challenge_state.py:207`**
```python
log.info("Marked funded. Phase: eval → pre_lock. Sizing: 3 MNQ → 3 MNQ.")
```

**W3 (AXE 7 WARN) — `monitor_loop.py:250`**
```python
ticket = (flat_result.get("orderId") if isinstance(flat_result, dict) else flat_result)
```

### Deferred (post go-live, cosmetic)

- Docstring updates in `guardrails.py`, `challenge_state.py`, `run_daily.py`

---

## Pre-Deployment Checklist (human actions)

- [ ] **Fix B1** — run_daily.py lock trigger message
- [ ] **Fix B2** — validate_tradovate.py T5 scenarios for $25K
- [ ] Fix W1, W2, W3 (recommended)
- [ ] Buy Tradeify Select Flex $25K → get funded account credentials
- [ ] Register Tradovate developer account → obtain CID + SECRET
- [ ] Set `.env` on VPS: `TRADOVATE_USERNAME`, `TRADOVATE_PASSWORD`, `TRADOVATE_CID`, `TRADOVATE_SECRET`, `TRADOVATE_ENV=demo` initially
- [ ] Run `python3 -m Futures.live.strategy_c_live.challenge_state init` (reads balance from broker)
- [ ] Run T1–T3 (offline), T4 during market hours, T5 (after B2 fix), T6 dry run post-market
- [ ] Flip `TRADOVATE_ENV=live` in `.env` only after all tests pass on Demo
- [ ] Set crontab on VPS (UTC+2 summer: `25 13 * * 1-5`; UTC+1 winter: `25 14 * * 1-5`)
- [ ] Confirm Tradeify policy: VPS headless execution allowed (FTA §6.6)
- [ ] First live day: monitor Telegram alerts actively
- [ ] Upon EOD balance ≥ $26,100: request first payout, then run `mark-payout-requested`
