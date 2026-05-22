"""
monitor_loop.py — Intraday position monitor for Strategy C
===========================================================
30-second polling loop from entry (09:46) to exit (TP/SL/time-stop/guardrail).

States:
  WAITING_ENTRY  — bracket placed, waiting for entry market fill
  POSITION_OPEN  — entry confirmed, monitoring TP/SL/guardrails/time-stop

Defenses (in order per tick):
  L0: IBKR connection check + reconnect (3 attempts × 15s)
  L1/L2/L3: PropfirmGuardrails.check_all() → emergency_flat on trigger
  Time stop: flatten at 12:30 ET regardless of outcome

VPS heartbeat: fire-and-forget POST every 30s to watchdog.py.

Returns exit_result dict:
  exit_reason : 'TP' | 'SL' | 'TIME_STOP' | 'GUARDRAIL:{reason}' | 'RECONNECT_FAILED'
  exit_price  : float | None
  exit_time   : datetime (ET)
  entry_price : float | None
  pnl_gross   : float | None
  pnl_net     : float | None (after commission)
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

from Futures.live.strategy_c_live.config import (
    MONITOR_INTERVAL_SECS,
    RECONNECT_RETRIES,
    RECONNECT_WAIT_SECS,
    TIME_STOP,
    VPS_WATCHDOG_URL,
    POINT_VALUE,
    TRADE_COST_PER_UNIT,
)
from Futures.live.strategy_c_live.guardrails import (
    GuardrailTriggered,
    PropfirmGuardrails,
)

ET_TZ = ZoneInfo("America/New_York")


# ─────────────────────────────────────────────────────────────────────────────
# Telegram helper
# ─────────────────────────────────────────────────────────────────────────────

def _send_telegram(msg: str) -> None:
    token   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
            timeout=10,
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# VPS heartbeat (fire-and-forget)
# ─────────────────────────────────────────────────────────────────────────────

def _send_heartbeat_async(dd_pct: float, status: str = "RUNNING") -> None:
    """POST heartbeat to VPS watchdog in a daemon thread. Never blocks."""
    def _post() -> None:
        try:
            import requests
            requests.post(
                VPS_WATCHDOG_URL,
                json={"status": status, "dd_pct": round(dd_pct * 100, 2)},
                timeout=5,
            )
        except Exception:
            pass  # VPS watchdog is secondary defense — silent failure OK

    threading.Thread(target=_post, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# Exit reason inference (MT5: TP and SL share the same ticket)
# ─────────────────────────────────────────────────────────────────────────────

def _infer_exit_reason(exit_price: float, signal: dict) -> str:
    """
    Infer TP vs SL from exit price when a single ticket covers both (MT5).
    Tolerates 5-pt difference from theoretical TP/SL levels.
    """
    tolerance = 5.0
    tp = signal["tp_price"]
    sl = signal["sl_price"]
    if signal["direction"] == "BUY":
        return "TP" if exit_price >= tp - tolerance else "SL"
    else:
        return "TP" if exit_price <= tp + tolerance else "SL"


# ─────────────────────────────────────────────────────────────────────────────
# Exit result builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_exit(
    reason:       str,
    exit_price:   Optional[float],
    dt:           datetime,
    entry_price:  Optional[float],
    signal:       dict,
    n_contracts:  float,   # lots for MT5, int contracts for IBKR
) -> dict:
    pnl_gross = None
    pnl_net   = None
    if entry_price is not None and exit_price is not None:
        pnl_pts   = signal["dir_int"] * (exit_price - entry_price)
        pnl_gross = pnl_pts * POINT_VALUE * n_contracts
        pnl_net   = pnl_gross - TRADE_COST_PER_UNIT * n_contracts
    return {
        "exit_reason": reason,
        "exit_price":  exit_price,
        "exit_time":   dt,
        "entry_price": entry_price,
        "pnl_gross":   pnl_gross,
        "pnl_net":     pnl_net,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main monitor function
# ─────────────────────────────────────────────────────────────────────────────

def monitor_position(
    client,
    contract,
    open_trade:   dict,
    signal:       dict,
    guardrails:   PropfirmGuardrails,
    n_contracts:  float,             # lots (MT5) or int contracts (IBKR)
    entry_price:  Optional[float] = None,  # MT5: fill from place_bracket_order (skip WAITING_ENTRY)
) -> dict:
    """
    30-second polling loop. Blocks until position exits.

    Parameters
    ----------
    client      : IBKRClient (must be connected)
    contract    : qualified MNQ Contract
    open_trade  : {'entry': Trade, 'tp': Trade, 'sl': Trade, 'oca_group': str}
    signal      : dict from compute_signal() — needs dir_int, tp_price, sl_price
    guardrails  : PropfirmGuardrails instance
    n_contracts : number of /MNQ contracts open

    Returns
    -------
    exit_result dict (see module docstring)
    """
    now_et = lambda: datetime.now(ET_TZ)

    # MT5 market orders fill synchronously — skip WAITING_ENTRY if fill provided
    if entry_price is not None:
        loop_state  = "POSITION_OPEN"
        fill_price: Optional[float] = entry_price
    else:
        loop_state  = "WAITING_ENTRY"
        fill_price  = None

    # Track most recently known balance for heartbeat (avoid extra IBKR call)
    last_known_balance = guardrails.state.balance_at_day_open

    log.info(
        "Monitor loop started | state=WAITING_ENTRY | time-stop=%s ET",
        TIME_STOP.strftime("%H:%M"),
    )

    while True:
        time.sleep(MONITOR_INTERVAL_SECS)
        now = now_et()

        # ── L0: Connection check (broker-agnostic) ───────────────────────
        connected = (client.is_connected() if hasattr(client, "is_connected")
                     else client.ib.isConnected())
        if not connected:
            log.warning("Connection lost at %s — trying reconnect", now.strftime("%H:%M:%S"))
            if not client.reconnect():
                guardrails.emergency_flat(
                    contract, n_contracts, signal["direction"], "RECONNECT_FAILED"
                )
                return _build_exit(
                    "RECONNECT_FAILED", None, now, fill_price, signal, n_contracts
                )

        # ── Account balance update ───────────────────────────────────────
        try:
            last_known_balance = client.get_account_value()
            guardrails.state.update_balance(last_known_balance)
        except Exception as e:
            log.warning("Balance read failed (non-fatal): %s", e)
            # Use stale balance for guardrail check — conservative

        # ── Heartbeat (non-blocking) ─────────────────────────────────────
        _send_heartbeat_async(
            guardrails.state.fixed_dd_pct(last_known_balance),
            status=loop_state,
        )

        # ── Guardrail check ──────────────────────────────────────────────
        try:
            guardrails.check_all(
                last_known_balance,
                open_trade if loop_state == "POSITION_OPEN" else None,
            )
        except GuardrailTriggered as e:
            log.critical("Guardrail triggered at %s: %s", now.strftime("%H:%M:%S"), e)
            guardrails.emergency_flat(
                contract, n_contracts, signal["direction"], str(e)
            )
            return _build_exit(
                f"GUARDRAIL:{e}", fill_price, now, fill_price, signal, n_contracts
            )
        except Exception as e:
            log.warning("Guardrail check error (non-fatal): %s", e)

        # ── Time stop ────────────────────────────────────────────────────
        if loop_state == "POSITION_OPEN" and now.time() >= TIME_STOP:
            log.info("Time stop triggered at %s ET", now.strftime("%H:%M:%S"))
            try:
                client.cancel_all_for_contract(contract)
            except Exception as e:
                log.warning("Cancel orders at time stop failed: %s", e)
            flat_result = client.flatten_position(contract)
            exit_price  = None
            if flat_result is not None:
                # MT5: flat_result is {'ticket': int}; IBKR: Trade object
                ticket = (flat_result.get("ticket") if isinstance(flat_result, dict)
                          else flat_result)
                exit_price = client.wait_for_fill(ticket, timeout_secs=30)
            if exit_price is None:
                try:
                    exit_price = client.get_current_price(contract)
                except Exception:
                    exit_price = fill_price   # last resort
            return _build_exit("TIME_STOP", exit_price, now, fill_price, signal, n_contracts)

        # ── State: WAITING_ENTRY ─────────────────────────────────────────
        if loop_state == "WAITING_ENTRY":
            entry_fill = client.get_fill_price(open_trade["entry"])
            if entry_fill is not None:
                fill_price = entry_fill
                loop_state = "POSITION_OPEN"
                log.info("Entry filled @ %.2f — state → POSITION_OPEN", fill_price)
                _send_telegram(
                    f"NQ-C | FILLED @ {fill_price:.2f} | "
                    f"TP={signal['tp_price']:.2f}  SL={signal['sl_price']:.2f}"
                )

        # ── State: POSITION_OPEN ─────────────────────────────────────────
        elif loop_state == "POSITION_OPEN":
            # MT5: open_trade['tp'] == open_trade['sl'] == ticket (same position)
            # IBKR: separate TP/SL Trade objects
            # Check TP first; if same ticket, get_fill_price returns exit price for either
            tp_fill = client.get_fill_price(open_trade["tp"])
            if tp_fill is not None:
                # Infer reason from exit price (MT5 can't distinguish via get_fill_price alone)
                if open_trade["tp"] == open_trade.get("ticket"):
                    reason = _infer_exit_reason(tp_fill, signal)
                else:
                    reason = "TP"
                log.info("%s filled @ %.2f", reason, tp_fill)
                return _build_exit(reason, tp_fill, now, fill_price, signal, n_contracts)

            if open_trade["sl"] != open_trade.get("tp"):
                # IBKR: check SL order separately
                sl_fill = client.get_fill_price(open_trade["sl"])
                if sl_fill is not None:
                    log.info("SL filled @ %.2f", sl_fill)
                    return _build_exit("SL", sl_fill, now, fill_price, signal, n_contracts)
