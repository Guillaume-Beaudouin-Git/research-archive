"""
ibkr_client.py — IBKR TWS connection layer for Strategy C
===========================================================
Uses ib_insync (synchronous wrapper around IB API).
Paper trading port: 7497. Live trading port: 7496.
"""
from __future__ import annotations

import logging
import time as _time_module
from datetime import datetime, timezone
from typing import Dict, List, Optional

import pandas as pd

log = logging.getLogger(__name__)

try:
    from ib_insync import (
        IB, Future, MarketOrder, LimitOrder, StopOrder,
        BracketOrder, Trade, Contract,
    )
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    log.error("ib_insync not installed. Run: pip install ib_insync")


class IBKRClient:
    """
    Thin wrapper around ib_insync for Strategy C /MNQ paper trading.
    All methods are synchronous (uses ib.sleep() internally).
    """

    def __init__(self, host: str = '127.0.0.1', port: int = 7497, client_id: int = 1):
        if not IB_AVAILABLE:
            raise ImportError("ib_insync not installed. Run: pip install ib_insync")
        self.host      = host
        self.port      = port
        self.client_id = client_id
        self.ib        = IB()
        self._connected = False

    # ── Connection ──────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Connect to TWS/IB Gateway."""
        log.info("Connecting to IBKR %s:%s (clientId=%s)", self.host, self.port, self.client_id)
        self.ib.connect(self.host, self.port, clientId=self.client_id)
        self._connected = True
        log.info("Connected. Accounts: %s", self.ib.managedAccounts())

    def disconnect(self) -> None:
        """Disconnect cleanly."""
        if self._connected:
            self.ib.disconnect()
            self._connected = False
            log.info("Disconnected from IBKR.")

    def _check_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("Not connected. Call connect() first.")

    # ── Contract ────────────────────────────────────────────────────────────

    def get_mnq_contract(self) -> Contract:
        """
        Get the front-month /MNQ contract (Micro E-mini NQ).
        Qualifies the contract via IBKR to get the exact expiry.
        """
        self._check_connected()
        contract = Future(symbol='MNQ', exchange='CME', currency='USD')
        qualified = self.ib.qualifyContracts(contract)
        if not qualified:
            raise ValueError("Could not qualify MNQ contract. TWS may not have market data.")
        # Use nearest expiry (first in list, ib_insync returns sorted)
        return qualified[0]

    # ── Market data ─────────────────────────────────────────────────────────

    def get_current_price(self, contract: Contract) -> float:
        """Get last traded price (or mid if no trade)."""
        self._check_connected()
        ticker = self.ib.reqMktData(contract, '', False, False)
        self.ib.sleep(1.0)
        price = ticker.last
        if price is None or price != price:  # NaN check
            price = ticker.close
        self.ib.cancelMktData(contract)
        if price is None or price != price:
            raise ValueError("Could not get current price for contract.")
        return float(price)

    def get_5min_bars(self, contract: Contract, n_days: int = 2) -> pd.DataFrame:
        """
        Fetch 5-min OHLCV bars for the past n_days, RTH only.
        Returns DataFrame with columns: open, high, low, close, volume
        Indexed by tz-aware US/Eastern datetime.
        """
        self._check_connected()
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=f'{n_days} D',
            barSizeSetting='5 mins',
            whatToShow='TRADES',
            useRTH=True,
            formatDate=1,
        )
        if not bars:
            return pd.DataFrame()

        df = pd.DataFrame([{
            'date':   b.date,
            'open':   float(b.open),
            'high':   float(b.high),
            'low':    float(b.low),
            'close':  float(b.close),
            'volume': int(b.volume),
        } for b in bars])

        df['date'] = pd.to_datetime(df['date'])
        if df['date'].dt.tz is None:
            df['date'] = df['date'].dt.tz_localize('US/Eastern')
        else:
            df['date'] = df['date'].dt.tz_convert('US/Eastern')
        df = df.set_index('date').sort_index()
        return df

    def get_1min_bars(self, contract: Contract, n_days: int = 2) -> pd.DataFrame:
        """
        Fetch 1-min OHLCV bars for the past n_days, RTH only.
        Used instead of get_5min_bars so signal_engine can compute VWAP
        on 1-min data (matches iter_10 backtest computation).
        Returns DataFrame with columns: open, high, low, close, volume
        Indexed by tz-aware US/Eastern datetime.
        """
        self._check_connected()
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=f'{n_days} D',
            barSizeSetting='1 min',
            whatToShow='TRADES',
            useRTH=True,
            formatDate=2,   # UTC epoch → convert to US/Eastern
        )
        if not bars:
            return pd.DataFrame()

        df = pd.DataFrame([{
            'date':   b.date,
            'open':   float(b.open),
            'high':   float(b.high),
            'low':    float(b.low),
            'close':  float(b.close),
            'volume': int(b.volume),
        } for b in bars])

        df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_convert('US/Eastern')
        df = df.set_index('date').sort_index()
        return df

    # ── Order management ────────────────────────────────────────────────────

    def place_market_order(self, contract: Contract, action: str, qty: int) -> Trade:
        """
        Place a market order.

        Parameters
        ----------
        action : 'BUY' or 'SELL'
        qty    : number of contracts (positive)

        Returns ib_insync Trade object.
        """
        self._check_connected()
        order = MarketOrder(action=action, totalQuantity=qty)
        trade = self.ib.placeOrder(contract, order)
        log.info("Market order placed: %s %d %s", action, qty, contract.localSymbol)
        return trade

    def place_bracket_order(self,
                             contract: Contract,
                             action: str,
                             qty: int,
                             tp_price: float,
                             sl_price: float) -> Dict[str, Trade]:
        """
        Place entry market order + TP limit + SL stop (bracket).

        Parameters
        ----------
        action   : 'BUY' (long) or 'SELL' (short)
        qty      : number of contracts
        tp_price : take-profit limit price
        sl_price : stop-loss stop price

        Returns dict with keys 'entry', 'tp', 'sl'.
        """
        self._check_connected()

        exit_action = 'SELL' if action == 'BUY' else 'BUY'

        # Round prices to nearest tick (0.25 pts)
        tick = 0.25
        tp_price = round(tp_price / tick) * tick
        sl_price = round(sl_price / tick) * tick

        entry_order = MarketOrder(action=action, totalQuantity=qty)
        tp_order    = LimitOrder(action=exit_action, totalQuantity=qty, lmtPrice=tp_price,
                                  outsideRth=False, tif='GTC')
        sl_order    = StopOrder(action=exit_action, totalQuantity=qty, stopPrice=sl_price,
                                 outsideRth=False, tif='GTC')

        # Link TP and SL as OCA group
        oca_group = f"StratC_{int(_time_module.time())}"
        tp_order.ocaGroup = oca_group
        tp_order.ocaType  = 1   # cancel remaining on fill
        sl_order.ocaGroup = oca_group
        sl_order.ocaType  = 1

        entry_trade = self.ib.placeOrder(contract, entry_order)
        self.ib.sleep(0.5)   # brief wait for entry to be acknowledged

        tp_trade = self.ib.placeOrder(contract, tp_order)
        sl_trade = self.ib.placeOrder(contract, sl_order)

        log.info(
            "Bracket placed: %s %d @ MKT  TP=%.2f  SL=%.2f  OCA=%s",
            action, qty, tp_price, sl_price, oca_group
        )
        return {'entry': entry_trade, 'tp': tp_trade, 'sl': sl_trade,
                'oca_group': oca_group}

    def cancel_order(self, trade: Trade) -> None:
        """Cancel an open order."""
        self._check_connected()
        self.ib.cancelOrder(trade.order)
        log.info("Order cancelled: %s", trade.order.orderId)

    def cancel_all_for_contract(self, contract: Contract) -> None:
        """Cancel all open orders for a given contract."""
        self._check_connected()
        open_trades = self.ib.openTrades()
        for t in open_trades:
            if t.contract.symbol == contract.symbol:
                self.ib.cancelOrder(t.order)
        log.info("All open orders cancelled for %s", contract.symbol)

    # ── Fill / status helpers ────────────────────────────────────────────────

    def get_fill_price(self, trade: Trade) -> Optional[float]:
        """
        Return average fill price for a trade, or None if not yet filled.
        """
        self.ib.sleep(0.1)
        fills = trade.fills
        if not fills:
            return None
        total_qty   = sum(f.execution.shares for f in fills)
        total_value = sum(f.execution.price * f.execution.shares for f in fills)
        return float(total_value / total_qty) if total_qty > 0 else None

    def get_order_status(self, trade: Trade) -> str:
        """Return order status string: 'Filled', 'Submitted', 'Cancelled', etc."""
        self.ib.sleep(0.1)
        return trade.orderStatus.status

    def wait_for_fill(self, trade: Trade, timeout_secs: int = 30) -> Optional[float]:
        """
        Wait up to timeout_secs for a market order to fill.
        Returns fill price or None on timeout.
        """
        start = _time_module.time()
        while _time_module.time() - start < timeout_secs:
            status = self.get_order_status(trade)
            if status == 'Filled':
                return self.get_fill_price(trade)
            if status in ('Cancelled', 'Inactive'):
                log.warning("Order %s (status=%s)", trade.order.orderId, status)
                return None
            self.ib.sleep(0.5)
        log.warning("Timeout waiting for fill on order %s", trade.order.orderId)
        return None

    def get_account_value(self) -> float:
        """
        Return Net Liquidation Value (USD) for the connected account.
        NLV includes unrealized P&L — preferred over CashBalance for DD tracking.
        """
        self._check_connected()
        vals = self.ib.accountValues()
        nlv = next(
            (v for v in vals if v.tag == "NetLiquidation" and v.currency == "USD"),
            None,
        )
        if nlv is None:
            raise RuntimeError(
                "Cannot read NetLiquidation from account values. "
                "Check TWS API subscriptions and account permissions."
            )
        return float(nlv.value)

    def get_open_positions(self) -> list:
        """Return list of Position objects for the connected account. Empty if flat."""
        self._check_connected()
        return self.ib.positions()

    def reconnect(self) -> bool:
        """
        Attempt reconnect after connection loss.
        Returns True if reconnected successfully within RECONNECT_RETRIES attempts.
        """
        from Futures.live.strategy_c_live.config import RECONNECT_RETRIES, RECONNECT_WAIT_SECS
        for attempt in range(1, RECONNECT_RETRIES + 1):
            try:
                self.ib.disconnect()
            except Exception:
                pass
            _time_module.sleep(RECONNECT_WAIT_SECS)
            try:
                self.ib.connect(self.host, self.port, clientId=self.client_id)
                if self.ib.isConnected():
                    self._connected = True
                    log.info("Reconnected on attempt %d/%d", attempt, RECONNECT_RETRIES)
                    return True
            except Exception as e:
                log.warning(
                    "Reconnect attempt %d/%d failed: %s",
                    attempt, RECONNECT_RETRIES, e,
                )
        log.error("All %d reconnect attempts failed", RECONNECT_RETRIES)
        self._connected = False
        return False

    def get_position(self, contract: Contract) -> int:
        """Return net position for contract (positive = long, negative = short)."""
        self._check_connected()
        for pos in self.ib.positions():
            if pos.contract.symbol == contract.symbol:
                return int(pos.position)
        return 0

    def flatten_position(self, contract: Contract) -> Optional[Trade]:
        """Flatten any open position in contract at market."""
        pos = self.get_position(contract)
        if pos == 0:
            log.info("No position to flatten for %s", contract.symbol)
            return None
        action = 'SELL' if pos > 0 else 'BUY'
        return self.place_market_order(contract, action, abs(pos))
