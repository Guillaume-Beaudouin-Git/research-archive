# Manual Paper Trade Protocol — iter_10 on Tradovate Demo

## Phase active: 2026-05-25 → ~2026-06-05 (target N≥5 trading days)

**Goal**: Validate that the live signal engine, yfinance data feed, and manual execution
produce results consistent with iter_10 backtest expectations before purchasing Tradeify
Select Flex $25K challenge (~$199 with promo code PHIDIAS2.0 or SOPF).

---

## One-time setup (first day only)

1. **Open Tradovate Demo**: https://trader.tradovate.com  
   Login → switch to Demo account if not default (account <ACCOUNT_ID>).

2. **Enable launchd (optional, automated trigger)**:
   ```bash
   cp ~/Desktop/Algo_claude/Futures/live/strategy_c_live/com.algo_claude.manual_signal.plist \
      ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.algo_claude.manual_signal.plist
   ```
   Or use cron (see `run_manual_signal.sh` header) or run manually each morning.

3. **Test Telegram pipeline**:
   ```bash
   cd ~/Desktop/Algo_claude
   /usr/bin/python3 -m Futures.live.strategy_c_live.manual_signal --test-telegram
   ```
   Expect a test message in Telegram within 5s.

---

## Daily workflow

### 15:40-15:43 Paris (09:40-09:43 ET)

- Laptop on, internet connected.
- Open Tradovate Demo web interface.
- Ensure MNQ front-month chart visible.
- If running manually: `cd ~/Desktop/Algo_claude && ./Futures/live/strategy_c_live/run_manual_signal.sh`

### 15:43-15:46 Paris (09:43-09:46 ET)

- Wait for Telegram alert.
- **yfinance delay warning**: free tier for MNQ=F can have 5-15min data lag.
  If the Telegram arrives after 15:47 Paris (09:47 ET), skip the day — log `data_lag`.

### 15:46 Paris (09:46 ET) — READ BEFORE CLICKING

| Telegram says | Action |
|---|---|
| **NO TRADE** | Close laptop. Day done. |
| **SIGNAL: BUY** | Click Buy in Tradovate, 2 MNQ, Market order. |
| **SIGNAL: SELL** | Click Sell in Tradovate, 2 MNQ, Market order. |

After market order fills:
- Set bracket OCO immediately:
  - TP: Limit order @ price shown in Telegram
  - SL: Stop Market order @ price shown in Telegram
- Confirm both legs are active in the Orders panel.

### 15:46-18:30 Paris (09:46-12:30 ET)

- Bracket OCO handles exit automatically.
- At **18:30 Paris (12:30 ET) time stop**: if position still open, flatten manually (Market).

### Post-session (any time after 18:30 Paris)

Open `logs/manual_paper_trades.csv` and fill the empty columns for today's row:

| Column | Source |
|---|---|
| `actual_entry_time_et` | Tradovate order history |
| `actual_entry_price` | Fill price from Tradovate |
| `actual_exit_time_et` | Exit fill time |
| `actual_exit_price` | Exit fill price |
| `actual_exit_reason` | `TP` / `SL` / `time_stop` / `manual` |
| `user_notes` | Anything unusual (slippage, lag, fat finger, etc.) |

---

## Decision criteria after N=5 trades

### Continue → Tradeify Eval purchase

All three conditions met:
1. **Slippage within model CI**: mean(actual_entry − entry_trigger) < 5 ticks ($1 MNQ)
2. **Win rate within ±10pp**: count(TP) / count(SIGNAL days) ∈ [17.75%, 37.75%] (backtest 27.75%)
3. **No data_lag row in CSV** (or < 2 lag events in 5 days)

### Stop / investigate

Any of:
- ≥3 consecutive days with `actual_entry − entry_trigger` > 5 ticks → slippage issue
- Win rate 0/5 or 5/5 (both are statistical outliers, warrant review)
- yfinance lag causing ≥3 `data_lag` days → needs Polygon/AlphaVantage fallback

### Abort paper trade entirely

- Signal direction mismatches observed systematically (VWAP regression)
- `actual_exit − tp_price` > 10 ticks on TP days (fill quality issue in Demo)

---

## Tradeify Eval purchase prerequisites

| # | Prerequisite | Status |
|---|---|---|
| 1 | Manual paper trade N≥5 with slippage within model CI | ⏳ pending |
| 2 | VWAP 1-min canonical confirmed (Phase 2) | ✅ done 2026-05-25 |
| 3 | Sizing config = 2 MNQ (Phase 2.5) | ✅ done 2026-05-25 |
| 4 | Lock balance = $26,100 (Phase 2.6) | ✅ done 2026-05-25 |
| 5 | Lock trigger OR semantics (Phase 2.7) | ✅ done 2026-05-25 |
| 6 | Verification video from personal device | ⏳ pending (Tradeify requirement) |
| 7 | Promo code PHIDIAS2.0 or SOPF available | ⏳ check at purchase time |

---

## Signal window and yfinance latency

`manual_signal.py` enforces a 09:43-09:47 ET signal window. Outside this window the
script exits silently (safe to call at any time). yfinance free tier for MNQ=F is
adequate for the 09:30-09:43 window with occasional 5-15min delays. If delays become
systematic, replace `_fetch_bars()` with Polygon.io free tier (15-min delayed, same
structure) or Alpha Vantage.

---

## CSV file location

```
Futures/live/strategy_c_live/logs/manual_paper_trades.csv
```
(gitignored — `logs/` is in `.gitignore`)
