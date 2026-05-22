"""
tradovate_client.py — Tradovate REST API client for Strategy C
==============================================================
Drop-in replacement for mt5_client.py / ibkr_client.py.
Identical positional interface: place_bracket_order(contract, action, qty, tp, sl).

Auth: OAuth2 access token via /auth/accessTokenRequest.
      Tokens expire ~80 min; auto-refreshed before each request.
      Separate md_token for market data endpoints.

Market data: REST /md/getChart (1-min bars).
Orders: /order/placeOSO (bracket with TP+SL in one call).

Credentials must be in .env — never hardcoded:
  TRADOVATE_USERNAME, TRADOVATE_PASSWORD, TRADOVATE_CID, TRADOVATE_SECRET,
  TRADOVATE_ENV ('demo' | 'live'), TRADOVATE_DEVICE_ID
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, time as _time

import pandas as pd
import requests as _requests

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

from Futures.live.strategy_c_live.config import (
    TRADOVATE_ENV,
    TRADOVATE_USERNAME,
    TRADOVATE_PASSWORD,
    TRADOVATE_CID,
    TRADOVATE_SECRET,
    TRADOVATE_APP_ID,
    TRADOVATE_APP_VERSION,
    TRADOVATE_DEVICE_ID,
    RECONNECT_RETRIES,
    RECONNECT_WAIT_SECS,
)

ET_TZ = ZoneInfo("America/New_York")

BASE_URLS = {
    'demo': 'https://demo.tradovateapi.com/v1',
    'live': 'https://live.tradovateapi.com/v1',
}
MD_URLS = {
    'demo': 'https://md-demo.tradovateapi.com/v1',
    'live': 'https://md.tradovateapi.com/v1',
}

MAGIC_COMMENT = 'StratC_ORB'

# Tradovate ordStatus → our canonical status
_STATUS_MAP = {
    'Working':     'Submitted',
    'PendingNew':  'Submitted',
    'Accepted':    'Submitted',
    'Filled':      'Filled',
    'Cancelled':   'Cancelled',
    'Rejected':    'Cancelled',
    'Expired':     'Cancelled',
    'Completed':   'Filled',
}


class TradovateClient:
    """
    Tradovate REST client with the same interface as MT5Client and IBKRClient.

    Usage:
      c = TradovateClient()
      c.connect()
      contract = c.get_mnq_contract()
      bars = c.get_1min_bars(contract, n_days=2)
      trade = c.place_bracket_order(contract, 'BUY', 3, tp_price, sl_price)
      c.disconnect()
    """

    def __init__(self) -> None:
        self.base_url    = BASE_URLS[TRADOVATE_ENV]
        self.md_url      = MD_URLS[TRADOVATE_ENV]
        self.token       = None
        self.md_token    = None
        self.token_expiry: datetime | None = None
        self.account_id  = None
        self.session     = _requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    # ── Auth ─────────────────────────────────────────────────────────────────

    def connect(self) -> None:
        """
        OAuth2 access token via /auth/accessTokenRequest.
        Also fetches md_token and account_id.
        Raises RuntimeError on failure.
        """
        payload = {
            'name':       TRADOVATE_USERNAME,
            'password':   TRADOVATE_PASSWORD,
            'appId':      TRADOVATE_APP_ID,
            'appVersion': TRADOVATE_APP_VERSION,
            'cid':        int(TRADOVATE_CID),
            'sec':        TRADOVATE_SECRET,
            'deviceId':   TRADOVATE_DEVICE_ID,
        }
        r = self.session.post(f'{self.base_url}/auth/accessTokenRequest', json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()

        if 'accessToken' not in data:
            raise RuntimeError(f"Auth failed: {data.get('errorText', data)}")

        self.token     = data['accessToken']
        self.md_token  = data.get('mdAccessToken', self.token)
        self.token_expiry = datetime.now() + timedelta(minutes=75)
        self.session.headers.update({'Authorization': f'Bearer {self.token}'})

        accounts = self.session.get(f'{self.base_url}/account/list', timeout=10).json()
        if not accounts:
            raise RuntimeError("No accounts found on Tradovate")
        self.account_id = accounts[0]['id']
        log.info(
            "Tradovate connected — env=%s, account_id=%s, user=%s",
            TRADOVATE_ENV, self.account_id, TRADOVATE_USERNAME,
        )

    def disconnect(self) -> None:
        self.token       = None
        self.md_token    = None
        self.account_id  = None
        self.token_expiry = None
        self.session     = _requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def is_connected(self) -> bool:
        if not self.token:
            return False
        try:
            r = self.session.get(f'{self.base_url}/account/list', timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def reconnect(self) -> bool:
        for attempt in range(1, RECONNECT_RETRIES + 1):
            try:
                self.disconnect()
                time.sleep(RECONNECT_WAIT_SECS)
                self.connect()
                if self.token:
                    log.info("Reconnected on attempt %d", attempt)
                    return True
            except Exception as e:
                log.warning("Reconnect attempt %d/%d failed: %s", attempt, RECONNECT_RETRIES, e)
        return False

    def _refresh_token_if_needed(self) -> None:
        if self.token_expiry and datetime.now() >= self.token_expiry:
            log.info("Token expired — re-authenticating")
            self.connect()

    # ── Account ──────────────────────────────────────────────────────────────

    def get_account_value(self) -> float:
        """
        Net liquidation value.
        Uses /cashBalance/getCashBalanceSnapshot: totalCashValue + openPL.
        """
        self._refresh_token_if_needed()
        r = self.session.post(
            f'{self.base_url}/cashBalance/getCashBalanceSnapshot',
            json={'accountId': self.account_id},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return float(data.get('totalCashValue', 0)) + float(data.get('openPL', 0))

    # ── Contract ─────────────────────────────────────────────────────────────

    def get_mnq_contract(self) -> dict:
        """
        Returns front-month MNQ contract dict.
        Uses /contract/suggest?t=MNQ — returns active tradable contracts.
        """
        self._refresh_token_if_needed()
        r = self.session.get(
            f'{self.base_url}/contract/suggest',
            params={'t': 'MNQ', 'l': 10},
            timeout=10,
        )
        r.raise_for_status()
        contracts = r.json()
        active = [c for c in contracts if c.get('status') in ('ActiveTradable', None)]
        if not active:
            active = contracts
        if not active:
            raise RuntimeError("No active MNQ contract found via /contract/suggest")
        return sorted(active, key=lambda c: c.get('contractMaturityId', 0))[0]

    # ── Market data ──────────────────────────────────────────────────────────

    def get_1min_bars(self, symbol_or_contract, n_days: int = 2) -> pd.DataFrame:
        """
        1-min RTH bars (09:30–16:00 ET) for last n_days trading days.
        Uses POST /md/getChart with md_token.
        Returns DataFrame: index=DatetimeTZ(ET), cols=[open,high,low,close,volume].
        """
        self._refresh_token_if_needed()

        if isinstance(symbol_or_contract, str):
            contract = self.get_mnq_contract()
        else:
            contract = symbol_or_contract

        payload = {
            'symbol': contract['name'],
            'chartDescription': {
                'underlyingType':    'MinuteBar',
                'elementSize':       1,
                'elementSizeUnit':   'UnderlyingUnits',
                'withHistogram':     False,
            },
            'timeRange': {
                'asMuchAsElements': 400 * n_days,
            },
        }
        md_session = _requests.Session()
        md_session.headers.update({
            'Content-Type':  'application/json',
            'Authorization': f'Bearer {self.md_token}',
        })
        r = md_session.post(f'{self.md_url}/md/getChart', json=payload, timeout=20)
        r.raise_for_status()
        data = r.json()

        bars_raw = data.get('bars', data.get('historicalData', []))
        if not bars_raw:
            raise RuntimeError(f"No bars returned for {contract['name']}")

        df = pd.DataFrame(bars_raw)
        # Tradovate timestamps: milliseconds UTC
        ts_col = 'timestamp' if 'timestamp' in df.columns else df.columns[0]
        df['time'] = pd.to_datetime(df[ts_col], unit='ms', utc=True)
        df = df.set_index('time').tz_convert(ET_TZ)

        rename = {
            'openPrice': 'open', 'highPrice': 'high',
            'lowPrice': 'low',   'closePrice': 'close',
        }
        for old, new in rename.items():
            if old in df.columns:
                df = df.rename(columns={old: new})
        # volume: use upVolume + downVolume or upVolume alone
        if 'upVolume' in df.columns and 'downVolume' in df.columns:
            df['volume'] = df['upVolume'].fillna(0) + df['downVolume'].fillna(0)
        elif 'upVolume' in df.columns:
            df['volume'] = df['upVolume']
        elif 'volume' not in df.columns:
            df['volume'] = 0

        df = df[['open', 'high', 'low', 'close', 'volume']].dropna()
        df = df[(df.index.time >= _time(9, 30)) & (df.index.time < _time(16, 0))]
        return df

    # ── Orders ───────────────────────────────────────────────────────────────

    def place_bracket_order(
        self,
        contract: dict,
        action: str,
        qty: int,
        tp_price: float,
        sl_price: float,
    ) -> dict:
        """
        OSO bracket order via /order/placeOSO.
        Returns dict with orderId, entry_price, tp_orderId, sl_orderId.
        Compatible with monitor_loop.py open_trade interface.
        """
        self._refresh_token_if_needed()

        side     = 'Buy'  if action == 'BUY'  else 'Sell'
        opposite = 'Sell' if action == 'BUY'  else 'Buy'

        payload = {
            'accountId': self.account_id,
            'action':    side,
            'symbol':    contract['name'],
            'orderQty':  int(qty),
            'orderType': 'Market',
            'isAutomated': True,
            'text':      MAGIC_COMMENT,
            'bracket1': {
                'action':    opposite,
                'orderType': 'Limit',
                'price':     float(tp_price),
            },
            'bracket2': {
                'action':    opposite,
                'orderType': 'Stop',
                'stopPrice': float(sl_price),
            },
        }

        r = self.session.post(f'{self.base_url}/order/placeOSO', json=payload, timeout=15)
        r.raise_for_status()
        result = r.json()

        if 'orderId' not in result:
            raise RuntimeError(f"placeOSO failed: {result}")

        order_id = result['orderId']
        log.info("placeOSO → orderId=%s (%s %d %s TP=%.2f SL=%.2f)",
                 order_id, action, qty, contract['name'], tp_price, sl_price)

        # Poll for fill + child order IDs (market orders fill quickly)
        time.sleep(2)
        entry_price, tp_id, sl_id = self._resolve_bracket_ids(order_id, tp_price, sl_price)

        return {
            'orderId':    order_id,
            'entry_price': entry_price,
            'tp_orderId': tp_id,
            'sl_orderId': sl_id,
            'action':     action,
            # monitor_loop aliases
            'entry': order_id,
            'tp':    tp_id,
            'sl':    sl_id,
        }

    def _resolve_bracket_ids(
        self,
        parent_order_id: int,
        tp_price: float,
        sl_price: float,
    ) -> tuple[float | None, int | None, int | None]:
        """Poll fills and order list to resolve entry fill + TP/SL child IDs."""
        entry_price = None
        tp_id       = None
        sl_id       = None

        # Entry fill
        fills = self.session.get(f'{self.base_url}/fill/list', timeout=10).json()
        if isinstance(fills, list):
            fill = next((f for f in fills if f.get('orderId') == parent_order_id), None)
            if fill:
                entry_price = float(fill.get('price', 0)) or None

        # Child orders (TP=Limit, SL=Stop)
        orders = self.session.get(f'{self.base_url}/order/list', timeout=10).json()
        if isinstance(orders, list):
            children = [
                o for o in orders
                if o.get('linkedOrderId') == parent_order_id
                or o.get('ocoId') == parent_order_id
            ]
            for o in children:
                ot = o.get('orderType', '')
                if ot == 'Limit':
                    tp_id = o['id']
                elif ot in ('Stop', 'StopLimit'):
                    sl_id = o['id']

        return entry_price, tp_id, sl_id

    # ── Fill / status polling ─────────────────────────────────────────────────

    def get_fill_price(self, order_id: int | None) -> float | None:
        """
        Returns fill price if order is filled, None if still open.
        Compatible with monitor_loop: check TP fill → returns exit price.
        """
        if order_id is None:
            return None
        self._refresh_token_if_needed()
        fills = self.session.get(f'{self.base_url}/fill/list', timeout=10).json()
        if not isinstance(fills, list):
            return None
        fill = next((f for f in fills if f.get('orderId') == order_id), None)
        return float(fill['price']) if fill else None

    def get_order_status(self, order_id: int | None) -> str:
        """
        Returns canonical status: 'Submitted' | 'Filled' | 'Cancelled'.
        """
        if order_id is None:
            return 'Cancelled'
        self._refresh_token_if_needed()
        r = self.session.get(
            f'{self.base_url}/order/item',
            params={'id': order_id},
            timeout=10,
        )
        if r.status_code == 404:
            return 'Cancelled'
        r.raise_for_status()
        status = r.json().get('ordStatus', '')
        return _STATUS_MAP.get(status, 'Cancelled')

    def get_open_positions(self) -> list:
        """GET /position/list filtered for non-zero positions."""
        self._refresh_token_if_needed()
        positions = self.session.get(f'{self.base_url}/position/list', timeout=10).json()
        return [p for p in (positions or []) if p.get('netPos', 0) != 0]

    # ── Position management ───────────────────────────────────────────────────

    def get_current_price(self, contract: dict) -> float | None:
        """Best bid/ask mid for current price estimate."""
        self._refresh_token_if_needed()
        r = self.session.get(
            f'{self.base_url}/md/quote',
            params={'symbol': contract['name']},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        bid = data.get('bid', 0)
        ask = data.get('ask', 0)
        if bid and ask:
            return (bid + ask) / 2
        return data.get('last') or None

    def cancel_all_for_contract(self, contract: dict) -> None:
        """Cancel all open orders for the given contract symbol."""
        self._refresh_token_if_needed()
        orders = self.session.get(f'{self.base_url}/order/list', timeout=10).json()
        if not isinstance(orders, list):
            return
        symbol = contract['name'] if isinstance(contract, dict) else contract
        for o in orders:
            if o.get('symbol') == symbol and o.get('ordStatus') in ('Working', 'PendingNew'):
                try:
                    self.session.post(
                        f'{self.base_url}/order/cancelOrder',
                        json={'orderId': o['id']},
                        timeout=10,
                    )
                    log.info("Cancelled order %s", o['id'])
                except Exception as e:
                    log.warning("Cancel order %s failed: %s", o['id'], e)

    def flatten_position(self, contract: dict) -> dict | None:
        """
        Close all open positions for contract via /order/liquidatePosition.
        Returns {'orderId': int} or None on failure.
        """
        self._refresh_token_if_needed()
        symbol   = contract['name'] if isinstance(contract, dict) else contract
        positions = self.get_open_positions()
        pos = next((p for p in positions if p.get('symbol') == symbol), None)
        if pos is None or pos.get('netPos', 0) == 0:
            log.info("No open position to flatten for %s", symbol)
            return None

        payload = {
            'accountId': self.account_id,
            'contractId': pos.get('contractId'),
            'admin':      False,
        }
        r = self.session.post(
            f'{self.base_url}/order/liquidatePosition',
            json=payload,
            timeout=15,
        )
        if r.status_code not in (200, 201):
            log.error("liquidatePosition failed: %s %s", r.status_code, r.text[:200])
            return None
        data = r.json()
        order_id = data.get('orderId')
        log.info("Flatten order placed: orderId=%s", order_id)
        return {'orderId': order_id}

    def wait_for_fill(self, order_id: int | None, timeout_secs: int = 30) -> float | None:
        """Poll until order fills or timeout. Returns fill price or None."""
        if order_id is None:
            return None
        deadline = time.time() + timeout_secs
        while time.time() < deadline:
            price = self.get_fill_price(order_id)
            if price is not None:
                return price
            time.sleep(2)
        return None

    def emergency_close(self) -> None:
        """
        Emergency close: liquidate all open positions for this account.
        Also cancels all open orders. Never raises.
        """
        try:
            self._refresh_token_if_needed()
            # Cancel all orders first
            orders = self.session.get(f'{self.base_url}/order/list', timeout=10).json()
            for o in (orders or []):
                if o.get('ordStatus') in ('Working', 'PendingNew'):
                    try:
                        self.session.post(
                            f'{self.base_url}/order/cancelOrder',
                            json={'orderId': o['id']},
                            timeout=10,
                        )
                    except Exception:
                        pass
            # Liquidate all positions
            positions = self.get_open_positions()
            for pos in positions:
                if pos.get('netPos', 0) != 0:
                    try:
                        self.session.post(
                            f'{self.base_url}/order/liquidatePosition',
                            json={
                                'accountId':  self.account_id,
                                'contractId': pos.get('contractId'),
                                'admin':      False,
                            },
                            timeout=15,
                        )
                        log.info("Emergency liquidated position: %s", pos.get('symbol'))
                    except Exception as e:
                        log.error("Emergency liquidate failed for %s: %s", pos.get('symbol'), e)
        except Exception as e:
            log.error("emergency_close failed: %s", e)
