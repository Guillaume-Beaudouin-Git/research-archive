"""
run_daily.py — Strategy C Daily Execution (with propfirm guardrails)
=====================================================================
Supports BROKER='mt5' (FTMO US100 CFD) and BROKER='ibkr' (/MNQ paper).

Flow:
  0. Halt sentinel check — abort if HALTED file present
  1. Load challenge state (must be initialized) + connect broker
  2. Read account balance, record day open
  3. Pre-flight guardrail check — skip today if DD already too high
  4. Sleep until 09:45:02 ET, fetch 1-min bars, compute signal
  5. If no signal → Telegram skip + log + exit
  6. Sleep until 09:46, place bracket order
  7. monitor_loop: 30s poll → TP/SL/guardrails/time-stop
  8. Log trade, update challenge state, send Telegram exit summary
  9. Disconnect

Run:
  python3 -m Futures.live.strategy_c_live.run_daily

Cron (Mac, summer UTC+2: 09:25 ET = 13:25 UTC = 15:25 Paris):
  25 13 * * 1-5  cd ~/Desktop/Algo_claude && \\
    caffeinate -i /usr/bin/python3 -m Futures.live.strategy_c_live.run_daily \\
    >> /tmp/strategy_c.log 2>&1

Cron (Mac, winter UTC+1: 09:25 ET = 14:25 UTC = 15:25 Paris):
  25 14 * * 1-5  cd ~/Desktop/Algo_claude && \\
    caffeinate -i /usr/bin/python3 -m Futures.live.strategy_c_live.run_daily \\
    >> /tmp/strategy_c.log 2>&1
"""
from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parents[4]))

from Futures.live.strategy_c_live.challenge_state import ChallengeState
from Futures.live.strategy_c_live.config import (
    BROKER,
    LOG_LEVEL,
    SYMBOL,
    LOT_SIZE,
    IBKR_CLIENT,
    IBKR_HOST,
    IBKR_PORT,
    N_CONTRACTS,
    N_CONTRACTS_DEFAULT,
)
from Futures.live.strategy_c_live.guardrails import (
    GuardrailTriggered,
    PropfirmGuardrails,
    check_halt_sentinel,
)
from Futures.live.strategy_c_live.log_trade import log_trade
from Futures.live.strategy_c_live.monitor_loop import monitor_position
from Futures.live.strategy_c_live.signal_engine import compute_signal

if BROKER == 'tradovate':
    from Futures.live.strategy_c_live.tradovate_client import TradovateClient as BrokerClient
    _QUANTITY = N_CONTRACTS_DEFAULT  # updated at runtime from challenge_state.get_n_contracts()
    _CONTRACT = None                 # resolved via get_mnq_contract()
elif BROKER == 'mt5':
    from Futures.live.strategy_c_live.mt5_client import MT5Client as BrokerClient
    _QUANTITY = LOT_SIZE
    _CONTRACT = SYMBOL
else:
    from Futures.live.strategy_c_live.ibkr_client import IBKRClient as BrokerClient
    _QUANTITY = N_CONTRACTS
    _CONTRACT = None

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

ET_TZ = ZoneInfo("America/New_York")


# ─────────────────────────────────────────────────────────────────────────────
# Telegram
# ─────────────────────────────────────────────────────────────────────────────

def _send_telegram(msg: str) -> None:
    token   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        log.warning("TELEGRAM credentials not set — skipping: %s", msg[:80])
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
            timeout=10,
        )
        log.info("Telegram sent: %s", msg[:80])
    except Exception as e:
        log.warning("Telegram send failed: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# Time helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now_et() -> datetime:
    return datetime.now(ET_TZ)


def _today_et_at(h: int, m: int, s: int = 0) -> datetime:
    d = _now_et().date()
    return datetime(d.year, d.month, d.day, h, m, s, tzinfo=ET_TZ)


def _sleep_until(target_dt: datetime) -> None:
    remaining = (target_dt - _now_et()).total_seconds()
    if remaining <= 0:
        return
    log.info("Sleeping %.0fs until %s ET", remaining, target_dt.strftime("%H:%M:%S"))
    while _now_et() < target_dt:
        time.sleep(1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    trade_date = _now_et().strftime("%Y-%m-%d")

    # ── Step 0: Pre-flight ────────────────────────────────────────────────
    check_halt_sentinel()   # sys.exit(1) if HALTED

    try:
        state = ChallengeState.load()
    except FileNotFoundError as e:
        log.error("Challenge state missing: %s", e)
        print(str(e))
        sys.exit(1)

    # Sizing from challenge state phase
    quantity  = state.get_n_contracts() if hasattr(state, 'get_n_contracts') else _QUANTITY
    qty_label = f"{quantity} MNQ"
    log.info("=== Strategy C run_daily start | %s | BROKER=%s | %s | phase=%s ===",
             trade_date, BROKER, qty_label,
             state.get_phase() if hasattr(state, 'get_phase') else 'n/a')

    # ── Step 1: Connect ───────────────────────────────────────────────────
    if BROKER == 'tradovate':
        client   = BrokerClient()
        contract = None   # resolved via get_mnq_contract()
    elif BROKER == 'mt5':
        client   = BrokerClient()
        contract = SYMBOL
    else:
        client   = BrokerClient(host=IBKR_HOST, port=IBKR_PORT, client_id=IBKR_CLIENT)
        contract = None

    try:
        client.connect()
    except Exception as e:
        log.error("%s connection failed: %s", BROKER.upper(), e)
        _send_telegram(f"NQ-C | {trade_date} | SKIP — {BROKER} connect failed: {e}")
        sys.exit(1)

    if BROKER in ('tradovate', 'ibkr'):
        contract = client.get_mnq_contract()
        name     = contract['name'] if isinstance(contract, dict) else contract.localSymbol
        log.info("Contract: %s", name)
    else:
        log.info("Symbol: %s", contract)

    try:
        # ── Step 2: Read balance + record day open ─────────────────────────
        try:
            current_balance = client.get_account_value()
            state.record_day_open(current_balance)
            log.info(
                "Account balance: $%,.2f | Challenge DD: %.2f%%",
                current_balance,
                state.fixed_dd_pct(current_balance) * 100,
            )
        except Exception as e:
            log.error("Cannot read account balance: %s", e)
            _send_telegram(f"NQ-C | {trade_date} | SKIP — cannot read account: {e}")
            return

        guardrails = PropfirmGuardrails(state, client)

        # ── Step 3: Pre-flight guardrail check ────────────────────────────
        try:
            guardrails.check_all(current_balance)
        except GuardrailTriggered as e:
            log.warning("Guardrail at day open — skipping today: %s", e)
            _send_telegram(f"NQ-C | {trade_date} | SKIP — guardrail at open: {e}")
            return

        # ── Step 4: Wait for ORB + compute signal ─────────────────────────
        _sleep_until(_today_et_at(9, 45, 2))

        bars_1min = client.get_1min_bars(contract, n_days=2)
        if bars_1min.empty:
            log.error("No 1-min bars from %s", BROKER.upper())
            _send_telegram(f"NQ-C | {trade_date} | SKIP — no market data")
            return

        signal = compute_signal(bars_1min)

        # ── Step 5: No signal ─────────────────────────────────────────────
        if signal is None:
            log.info("No signal today — filter(s) rejected")
            _send_telegram(f"NQ-C | {trade_date} | SKIPPED [filter(s) rejected]")
            return

        log.info(
            "Signal: %s  ORB=%.1fpts  gap=%.2f%%  TP=%.2f  SL=%.2f  [%s]",
            signal["direction"], signal["opening_range"], signal["gap_pct"],
            signal["tp_price"], signal["sl_price"], signal["signal_strength"],
        )

        # ── Step 6: Sleep until 09:46 + place bracket ─────────────────────
        _sleep_until(_today_et_at(9, 46, 0))
        entry_time_str = _now_et().strftime("%H:%M:%S")

        _send_telegram(
            f"NQ-C | {trade_date} | {signal['direction']} {qty_label}\n"
            f"ORB={signal['opening_range']:.0f}pts  gap={signal['gap_pct']:+.2f}%\n"
            f"TP={signal['tp_price']:.2f}  SL={signal['sl_price']:.2f}\n"
            f"Challenge DD: {state.fixed_dd_pct(current_balance):.1%}"
        )

        open_trade = client.place_bracket_order(
            contract,
            signal["direction"],
            quantity,
            signal["tp_price"],
            signal["sl_price"],
        )

        # ── Step 7: Monitor loop ──────────────────────────────────────────
        exit_result = monitor_position(
            client      = client,
            contract    = contract,
            open_trade  = open_trade,
            signal      = signal,
            guardrails  = guardrails,
            n_contracts = quantity,
            entry_price = open_trade.get("entry_price"),
        )

        # ── Step 8: Log + Telegram + update state ─────────────────────────
        exit_reason   = exit_result["exit_reason"]
        exit_price    = exit_result["exit_price"]
        entry_price   = exit_result.get("entry_price")
        pnl_net       = exit_result.get("pnl_net")
        exit_time_str = (
            exit_result["exit_time"].strftime("%H:%M:%S")
            if exit_result.get("exit_time") else "?"
        )

        account_type_map = {'tradovate': 'tradeify_tradovate', 'mt5': 'ftmo_mt5'}
        account_type = account_type_map.get(BROKER, 'paper_ibkr')
        log_trade(
            trade_date           = trade_date,
            direction            = signal["direction"],
            entry_time           = entry_time_str,
            exit_time            = exit_time_str,
            exit_reason          = exit_reason,
            signal               = signal,
            n_contracts          = quantity,
            actual_entry_price   = entry_price,
            actual_exit_price    = exit_price,
            ibkr_fill_time_entry = entry_time_str,
            ibkr_fill_time_exit  = exit_time_str,
            account_type         = account_type,
        )
        state.increment_trade_count()

        final_balance = None
        try:
            final_balance = client.get_account_value()
            state.update_balance(final_balance)
        except Exception as e:
            log.warning("Cannot read final balance: %s", e)

        # EOD lock trigger check (Tradeify: EOD balance >= $52,100 + payout requested)
        if final_balance is not None and hasattr(state, 'check_lock_trigger'):
            if state.check_lock_trigger(final_balance):
                _send_telegram(
                    f"NQ-C | {trade_date} | LOCK TRIGGERED\n"
                    f"EOD balance ${final_balance:,.2f} >= $52,100 + payout requested.\n"
                    f"Floor locked at ${state.lock_floor:,.0f}. Phase → post_lock (5 MNQ)."
                )

        if final_balance is not None and hasattr(state, 'trailing_dd_usd'):
            trail_dd = state.trailing_dd_usd(final_balance)
            dd_str = f"trailing_dd=${trail_dd:,.0f}"
        else:
            dd_str = f"{state.fixed_dd_pct(final_balance):.1%}" if final_balance is not None else "N/A"

        pnl_str = f"${pnl_net:+.0f}" if pnl_net is not None else "N/A"
        ep_str  = f"{exit_price:.2f}" if exit_price is not None else "N/A"

        _send_telegram(
            f"NQ-C | {trade_date} | {exit_reason.upper()} @ {ep_str}\n"
            f"P&L={pnl_str}  |  {dd_str}"
        )

        log.info(
            "Trade complete: %s → %s @ %s  (P&L=%s, DD=%s)",
            signal["direction"], exit_reason, ep_str, pnl_str, dd_str,
        )

    except KeyboardInterrupt:
        log.warning("KeyboardInterrupt — flattening and exiting")
        try:
            client.cancel_all_for_contract(contract)
            client.flatten_position(contract)
        except Exception:
            pass
    except Exception as e:
        log.exception("run_daily unhandled exception: %s", e)
        _send_telegram(f"NQ-C | {trade_date} | ERROR: {e}")
    finally:
        # ── Step 9: Disconnect ─────────────────────────────────────────────
        client.disconnect()
        log.info("=== Strategy C run_daily complete ===")


if __name__ == "__main__":
    main()
