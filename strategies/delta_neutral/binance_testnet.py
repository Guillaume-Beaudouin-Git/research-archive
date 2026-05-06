"""
binance_testnet.py — Binance Testnet REST client for spot market orders.

Base URL: https://testnet.binance.vision
Auth: HMAC-SHA256 signed requests (X-MBX-APIKEY header + signature param).

Usage:
    client = BinanceTestnetClient(api_key=..., secret_key=...)
    order  = client.market_buy("WLDUSDT", usdt_amount=50.0)
    # order = {"qty": 58.82, "avg_price": 0.850, "raw": {...}}
"""
from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode

import requests

TESTNET_BASE = "https://testnet.binance.vision"


class BinanceTestnetClient:
    """Minimal Binance testnet client for spot market orders."""

    def __init__(self, api_key: str, secret_key: str) -> None:
        self.api_key    = api_key
        self.secret_key = secret_key
        self.session    = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": api_key})

    def _sign(self, params: dict) -> dict:
        query_string = urlencode(params)
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _ts(self) -> int:
        return int(time.time() * 1000)

    def market_buy(self, symbol: str, usdt_amount: float) -> dict:
        """
        Buy `symbol` using quoteOrderQty (spend exactly `usdt_amount` USDT).
        Returns {"qty": float, "avg_price": float, "raw": dict}.
        """
        params = {
            "symbol":        symbol,
            "side":          "BUY",
            "type":          "MARKET",
            "quoteOrderQty": f"{usdt_amount:.2f}",
            "timestamp":     self._ts(),
        }
        r = self.session.post(
            f"{TESTNET_BASE}/api/v3/order",
            params=self._sign(params),
            timeout=15,
        )
        r.raise_for_status()
        raw  = r.json()
        qty  = float(raw.get("executedQty", 0))
        usdt = float(raw.get("cummulativeQuoteQty", usdt_amount))
        avg  = usdt / qty if qty > 0 else 0.0
        return {"qty": qty, "avg_price": avg, "raw": raw}

    def market_sell(self, symbol: str, qty: float) -> dict:
        """
        Sell exactly `qty` of `symbol` at market.
        Returns {"qty": float, "avg_price": float, "raw": dict}.
        """
        # Format qty: strip trailing zeros, keep enough precision
        qty_str = f"{qty:.8f}".rstrip("0").rstrip(".")
        params = {
            "symbol":    symbol,
            "side":      "SELL",
            "type":      "MARKET",
            "quantity":  qty_str,
            "timestamp": self._ts(),
        }
        r = self.session.post(
            f"{TESTNET_BASE}/api/v3/order",
            params=self._sign(params),
            timeout=15,
        )
        r.raise_for_status()
        raw        = r.json()
        filled_qty = float(raw.get("executedQty", 0))
        usdt       = float(raw.get("cummulativeQuoteQty", 0))
        avg        = usdt / filled_qty if filled_qty > 0 else 0.0
        return {"qty": filled_qty, "avg_price": avg, "raw": raw}

    def get_asset_balance(self, asset: str) -> float:
        """Return free balance of `asset` in the testnet account."""
        params = {"timestamp": self._ts()}
        r = self.session.get(
            f"{TESTNET_BASE}/api/v3/account",
            params=self._sign(params),
            timeout=15,
        )
        r.raise_for_status()
        for b in r.json().get("balances", []):
            if b["asset"] == asset:
                return float(b["free"])
        return 0.0

    def get_current_price(self, symbol: str) -> float:
        """Return last traded price for `symbol` (no auth needed)."""
        r = requests.get(
            f"{TESTNET_BASE}/api/v3/ticker/price",
            params={"symbol": symbol},
            timeout=15,
        )
        r.raise_for_status()
        return float(r.json()["price"])
