"""
mt5_client.py — MetaTrader 5 broker client for Strategy C (FTMO US100 CFD)
===========================================================================
Drop-in replacement for ibkr_client.py.  Same method signatures so
signal_engine.py, monitor_loop.py, run_daily.py require minimal changes.

macOS note: MetaTrader5 (pip) is Windows-only.  On Mac/Linux use mt5linux
which provides an identical API via an rpyc bridge to MT5 running in Wine.

    try:
        import MetaTrader5 as mt5          # Windows (native)
    except ImportError:
        from mt5linux import MetaTrader5 as mt5  # Mac/Linux (Wine bridge)

The mt5linux bridge requires the companion server running inside Wine:
    wine python mt5_server.py
See mt5linux docs: https://pypi.org/project/mt5linux/
"""
from __future__ import annotations

import logging
import time as _time_module
from datetime import datetime, timedelta, time as _time
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)

try:
    import MetaTrader5 as mt5
    _MT5_BACKEND = "native"
except ImportError:
    try:
        from mt5linux import MetaTrader5 as mt5
        _MT5_BACKEND = "mt5linux"
    except ImportError:
        mt5 = None
        _MT5_BACKEND = "unavailable"

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from Futures.live.strategy_c_live.config import (
    SYMBOL,
    MT5_LOGIN,
    MT5_PASSWORD,
    MT5_SERVER,
    RECONNECT_RETRIES,
    RECONNECT_WAIT_SECS,
)

MAGIC    = 20260522   # unique Strategy C identifier in MT5
_ET      = ZoneInfo("America/New_York")
_RTH_OPEN  = _time(9, 30)
_RTH_CLOSE = _time(16, 0)


def _require_mt5() -> None:
    if mt5 is None:
        raise ImportError(
            "MetaTrader5 not available.\n"
            "Windows: pip install MetaTrader5\n"
            "Mac/Linux: pip install mt5linux  (MT5 must run in Wine, start mt5_server.py)"
        )


class MT5Client:
    """
    MT5 broker client for Strategy C.
    Interface matches IBKRClient (drop-in replacement).
    MT5 manages SL/TP natively — no separate OCA orders needed.
    """

    def __init__(self) -> None:
        _require_mt5()
        self._connected = False

    # ── Connection ──────────────────────────────────────────────────────────

    def connect(self) -> None:
        """
        Initialise connection to the local MT5 terminal (named pipe / rpyc).
        Calls mt5.login() if MT5_LOGIN is set.
        Raises RuntimeError on failure.
        """
        if not mt5.initialize():
            raise RuntimeError(
                f"mt5.initialize() failed: {mt5.last_error()} "
                f"(backend={_MT5_BACKEND})"
            )
        if MT5_LOGIN:
            ok = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
            if not ok:
                raise RuntimeError(
                    f"mt5.login({MT5_LOGIN}) failed: {mt5.last_error()}"
                )
        info = mt5.terminal_info()
        if info is None:
            raise RuntimeError("mt5.terminal_info() returned None after initialize()")
        self._connected = True
        acct = mt5.account_info()
        log.info(
            "MT5 connected (backend=%s) | login=%s | balance=%.2f | server=%s",
            _MT5_BACKEND,
            acct.login if acct else "?",
            acct.balance if acct else 0.0,
            acct.server if acct else "?",
        )

    def disconnect(self) -> None:
        """mt5.shutdown(). Always call at end of session."""
        mt5.shutdown()
        self._connected = False
        log.info("MT5 disconnected.")

    def is_connected(self) -> bool:
        """Return True if MT5 terminal is connected and responsive."""
        if not self._connected:
            return False
        info = mt5.terminal_info()
        return info is not None and info.connected

    def reconnect(self) -> bool:
        """
        3 attempts × RECONNECT_WAIT_SECS.
        mt5.shutdown() → sleep → mt5.initialize() → verify terminal_info.
        Returns True on success.
        """
        for attempt in range(1, RECONNECT_RETRIES + 1):
            try:
                mt5.shutdown()
            except Exception:
                pass
            _time_module.sleep(RECONNECT_WAIT_SECS)
            try:
                if mt5.initialize():
                    if MT5_LOGIN:
                        mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
                    info = mt5.terminal_info()
                    if info is not None:
                        self._connected = True
                        log.info("MT5 reconnected on attempt %d/%d", attempt, RECONNECT_RETRIES)
                        return True
            except Exception as e:
                log.warning("MT5 reconnect attempt %d/%d: %s", attempt, RECONNECT_RETRIES, e)
        log.error("All %d MT5 reconnect attempts failed", RECONNECT_RETRIES)
        self._connected = False
        return False

    # ── Account ─────────────────────────────────────────────────────────────

    def get_account_value(self) -> float:
        """
        Return account equity (includes unrealized P&L).
        Raises RuntimeError if account_info() returns None.
        """
        acct = mt5.account_info()
        if acct is None:
            raise RuntimeError(f"mt5.account_info() returned None: {mt5.last_error()}")
        return float(acct.equity)

    # ── Market data ─────────────────────────────────────────────────────────

    def get_1min_bars(self, symbol: str, n_days: int = 2) -> pd.DataFrame:
        """
        1-min RTH bars (09:30-16:00 ET strict) for the past n_days.
        MT5 returns UTC server time → convert to America/New_York.

        Returns pd.DataFrame:
            Index: DatetimeTZDtype(tz=America/New_York)
            Columns: open, high, low, close, volume (float64)
        """
        n_bars = 400 * n_days   # generous buffer for RTH filtering

        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, n_bars)
        if rates is None or len(rates) == 0:
            log.warning("get_1min_bars: no data returned for %s (error=%s)",
                        symbol, mt5.last_error())
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        # MT5 'time' column is POSIX UTC
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.tz_convert(_ET)
        df = df.set_index("time").sort_index()
        df = df.rename(columns={"tick_volume": "volume"})
        df = df[["open", "high", "low", "close", "volume"]].astype(float)

        # Filter to RTH only
        t = df.index.time
        rth = (t >= _RTH_OPEN) & (t < _RTH_CLOSE)
        df  = df[rth].dropna()
        return df

    def get_current_price(self, symbol: str) -> float:
        """Return last bid/ask mid for symbol."""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"mt5.symbol_info_tick({symbol}) returned None")
        return (tick.bid + tick.ask) / 2.0

    # ── Order management ────────────────────────────────────────────────────

    def place_bracket_order(
        self,
        symbol:   str,
        action:   str,
        volume:   float,
        tp_price: float,
        sl_price: float,
    ) -> dict:
        """
        Market order with embedded SL and TP.  MT5 manages exits natively.

        action: 'BUY' or 'SELL'

        Returns:
            {
              'ticket':       int,    # position ticket (used for status checks)
              'entry_price':  float,  # actual fill price
              'action':       str,
              # aliases for monitor_loop IBKR-style access:
              'entry': ticket,  'tp': ticket,  'sl': ticket
            }

        Raises RuntimeError if retcode != TRADE_RETCODE_DONE.
        """
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"Cannot get tick for {symbol}")

        order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
        price      = tick.ask if action == "BUY" else tick.bid

        request = {
            "action":        mt5.TRADE_ACTION_DEAL,
            "symbol":        symbol,
            "volume":        float(volume),
            "type":          order_type,
            "price":         price,
            "sl":            float(sl_price),
            "tp":            float(tp_price),
            "deviation":     20,
            "magic":         MAGIC,
            "comment":       "StratC ORB",
            "type_time":     mt5.ORDER_TIME_GTC,
            "type_filling":  mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            retcode = result.retcode if result else "None"
            comment = result.comment if result else mt5.last_error()
            raise RuntimeError(
                f"place_bracket_order failed: retcode={retcode}, comment={comment}"
            )

        ticket = result.order
        fill   = float(result.price)
        log.info(
            "Bracket placed: %s %.2f lots @ %.5f  TP=%.5f  SL=%.5f  ticket=%d",
            action, volume, fill, tp_price, sl_price, ticket,
        )
        return {
            "ticket":      ticket,
            "entry_price": fill,
            "action":      action,
            # monitor_loop compatibility aliases
            "entry": ticket,
            "tp":    ticket,
            "sl":    ticket,
        }

    # ── Fill / status helpers ────────────────────────────────────────────────

    def get_fill_price(self, ticket: int) -> Optional[float]:
        """
        Return exit price if the position is closed, None if still open.

        Logic:
          1. If a position with magic=MAGIC exists → return None (still open)
          2. Search history deals for ticket + DEAL_ENTRY_OUT → return deal.price
          3. Otherwise None
        """
        # Step 1: check open positions
        positions = mt5.positions_get(symbol=SYMBOL)
        if positions:
            for pos in positions:
                if pos.magic == MAGIC:
                    return None  # still open

        # Step 2: check closed deals
        from_dt = datetime.now() - timedelta(hours=8)
        to_dt   = datetime.now() + timedelta(minutes=1)
        deals   = mt5.history_deals_get(from_dt, to_dt)
        if deals:
            for deal in deals:
                if deal.position_id == ticket and deal.entry == mt5.DEAL_ENTRY_OUT:
                    return float(deal.price)

        return None

    def get_order_status(self, ticket: int) -> str:
        """
        Return bracket integrity status for guardrails.check_all().

        'Submitted'  — position open with SL and TP set
        'Filled'     — position closed (no longer in positions_get)
        'Cancelled'  — position open but sl=0 or tp=0 (bracket corrupted)
        """
        positions = mt5.positions_get(symbol=SYMBOL)
        if positions:
            for pos in positions:
                if pos.magic == MAGIC:
                    if pos.sl != 0 and pos.tp != 0:
                        return "Submitted"
                    else:
                        return "Cancelled"   # bracket missing
        return "Filled"   # not in positions → must be closed

    def get_open_positions(self) -> list:
        """Return MT5 positions for SYMBOL.  Empty list if flat."""
        result = mt5.positions_get(symbol=SYMBOL)
        return list(result) if result else []

    def wait_for_fill(self, ticket: int, timeout_secs: int = 30) -> Optional[float]:
        """
        Poll until position closes (TP/SL/manual) or timeout.
        Returns exit price or None on timeout.
        Used by monitor_loop time-stop flatten.
        """
        deadline = _time_module.time() + timeout_secs
        while _time_module.time() < deadline:
            price = self.get_fill_price(ticket)
            if price is not None:
                return price
            _time_module.sleep(1.0)
        log.warning("wait_for_fill: timeout after %ds for ticket=%d", timeout_secs, ticket)
        return None

    # ── Emergency / flatten ──────────────────────────────────────────────────

    def emergency_close(self) -> None:
        """
        Close all open positions for SYMBOL at market (fire-and-forget).
        Called by guardrails.emergency_flat().  Never raises.
        """
        try:
            positions = mt5.positions_get(symbol=SYMBOL)
            if not positions:
                log.info("emergency_close: no open positions")
                return
            for pos in positions:
                close_type = (mt5.ORDER_TYPE_SELL
                              if pos.type == mt5.ORDER_TYPE_BUY
                              else mt5.ORDER_TYPE_BUY)
                tick  = mt5.symbol_info_tick(SYMBOL)
                price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask
                req   = {
                    "action":       mt5.TRADE_ACTION_DEAL,
                    "symbol":       SYMBOL,
                    "volume":       pos.volume,
                    "type":         close_type,
                    "price":        price,
                    "position":     pos.ticket,
                    "deviation":    50,
                    "magic":        MAGIC,
                    "comment":      "EMERGENCY CLOSE",
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                result = mt5.order_send(req)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    log.info("emergency_close: ticket=%d closed @ %.5f", pos.ticket, result.price)
                else:
                    log.error("emergency_close: ticket=%d FAILED retcode=%s",
                               pos.ticket, result.retcode if result else "None")
        except Exception as e:
            log.error("emergency_close exception: %s", e)

    def cancel_all_for_contract(self, symbol: str) -> None:
        """
        No-op for MT5: SL and TP are embedded in the position (no separate orders).
        Kept for monitor_loop interface compatibility.
        """
        log.debug("cancel_all_for_contract: MT5 manages exits natively, nothing to cancel")

    def flatten_position(self, symbol: str) -> Optional[dict]:
        """
        Flatten all open positions for symbol at market.
        Returns {'ticket': int} for wait_for_fill(), or None if already flat.
        Used by monitor_loop time-stop.
        """
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            log.info("flatten_position: no open positions for %s", symbol)
            return None

        last_ticket = None
        for pos in positions:
            if pos.magic != MAGIC:
                continue
            close_type = (mt5.ORDER_TYPE_SELL
                          if pos.type == mt5.ORDER_TYPE_BUY
                          else mt5.ORDER_TYPE_BUY)
            tick  = mt5.symbol_info_tick(symbol)
            price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask
            req   = {
                "action":       mt5.TRADE_ACTION_DEAL,
                "symbol":       symbol,
                "volume":       pos.volume,
                "type":         close_type,
                "price":        price,
                "position":     pos.ticket,
                "deviation":    50,
                "magic":        MAGIC,
                "comment":      "TIME STOP",
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(req)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                last_ticket = pos.ticket
                log.info("flatten_position: ticket=%d closed @ %.5f", pos.ticket, result.price)
            else:
                log.error("flatten_position: ticket=%d FAILED retcode=%s",
                           pos.ticket, result.retcode if result else "None")

        return {"ticket": last_ticket} if last_ticket is not None else None
