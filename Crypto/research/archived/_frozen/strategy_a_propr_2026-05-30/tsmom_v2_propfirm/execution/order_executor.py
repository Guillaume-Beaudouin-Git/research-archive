"""
Order executor for TSMOM v2 — wraps ProprClient from propr_sdk.py.

Correct order schema (official SDK, confirmed 2026-05-11):
    POST /accounts/{accountId}/orders
    {"orders": [{
        "accountId": ..., "intentId": <ULID>, "exchange": "hyperliquid",
        "type": "market", "side": "buy", "positionSide": "long",
        "productType": "perp", "timeInForce": "IOC",
        "asset": "BTC", "base": "BTC", "quote": "USDC",
        "quantity": "0.001",   ← string, not float
        "reduceOnly": false, "closePosition": false
    }]}

    Cancel: POST /accounts/{accountId}/orders/{orderId}/cancel
"""

from __future__ import annotations

import logging
import math
import sqlite3
import time
from datetime import datetime, timezone

import requests
import yfinance as yf

from . import ORDERS_DB_PATH, REVERSE_ASSET_MAP
from .propr_sdk import ProprAPIError, ProprClient

logger = logging.getLogger(__name__)

# ── Quantity precision (decimal places) per asset ──────────────────────────
# Hyperliquid lot sizes — floor-round to avoid over-sizing.
_ASSET_PRECISION: dict[str, int] = {
    "BTC": 5, "ETH": 4, "SOL": 2, "AVAX": 2, "LINK": 2,
    "DOGE": 0, "ADA": 0, "DOT": 1, "UNI": 2, "LTC": 3,
    "BCH": 3, "MATIC": 0, "POL": 0, "OP": 1, "ARB": 0,
}

# ── DB setup ───────────────────────────────────────────────────────────────

_CREATE_ORDERS_LOG = """
CREATE TABLE IF NOT EXISTS orders_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ts             TEXT NOT NULL,
    method         TEXT NOT NULL,
    endpoint       TEXT NOT NULL,
    request_body   TEXT,
    status_code    INTEGER,
    response_body  TEXT,
    order_id       TEXT
);
"""


def _init_orders_db() -> None:
    with sqlite3.connect(ORDERS_DB_PATH) as conn:
        conn.execute(_CREATE_ORDERS_LOG)
        conn.commit()


def _log_order(
    method: str,
    endpoint: str,
    request_body: str | None,
    status_code: int,
    response_body: str,
    order_id: str | None,
) -> None:
    _init_orders_db()
    with sqlite3.connect(ORDERS_DB_PATH) as conn:
        conn.execute(
            "INSERT INTO orders_log"
            " (ts, method, endpoint, request_body, status_code, response_body, order_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                method,
                endpoint,
                request_body,
                status_code,
                response_body,
                order_id,
            ),
        )
        conn.commit()


# ── Internal helpers ───────────────────────────────────────────────────────

def _make_client(account_id: str, api_key: str) -> ProprClient:
    """Instantiate a ProprClient with account_id set."""
    client = ProprClient(api_key=api_key)
    client.account_id = account_id
    return client


def _with_retry(fn, retries: int = 3):
    """
    Call fn() with exponential backoff (1s → 2s → 4s).
    Re-raises immediately on 4xx (definitive client errors).
    """
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return fn()
        except ProprAPIError as exc:
            if 400 <= exc.status_code < 500:
                raise   # definitive — don't retry
            last_exc = exc
        except requests.RequestException as exc:
            last_exc = exc
        if attempt < retries - 1:
            wait = 2 ** attempt
            logger.warning("Attempt %d/%d failed. Retrying in %ds.", attempt + 1, retries, wait)
            time.sleep(wait)
    raise last_exc  # type: ignore[misc]


def _get_current_price(propr_asset: str) -> float:
    """Fetch latest close price from yfinance for quantity conversion."""
    yf_ticker = REVERSE_ASSET_MAP.get(propr_asset)
    if not yf_ticker:
        raise ValueError(f"No yfinance ticker for Propr asset: {propr_asset!r}")
    data = yf.Ticker(yf_ticker).history(period="2d")
    if data.empty:
        raise RuntimeError(f"yfinance returned no data for {yf_ticker}")
    return float(data["Close"].iloc[-1])


def _to_quantity(notional_usd: float, price: float, asset: str) -> float:
    """Convert target notional USD → base asset quantity (floor-rounded)."""
    precision = _ASSET_PRECISION.get(asset, 3)
    raw = notional_usd / price
    factor = 10 ** precision
    return math.floor(raw * factor) / factor


# ── Public API ─────────────────────────────────────────────────────────────

def place_market_order(
    account_id: str,
    asset: str,
    side: str,
    notional_usd: float,
    api_key: str,
) -> str:
    """
    Place a market order and return the order_id.

    Parameters
    ----------
    account_id   : Propr account URN.
    asset        : Propr asset name (e.g. "BTC").
    side         : "buy" or "sell".
    notional_usd : Target notional in USD; converted to base-asset quantity.
    api_key      : Propr API key.
    """
    price = _get_current_price(asset)
    qty = _to_quantity(notional_usd, price, asset)
    if qty <= 0:
        raise ValueError(
            f"Computed qty={qty} for {asset} notional={notional_usd:.2f} "
            f"price={price:.4f} — increase notional or check precision."
        )
    qty_str = str(qty)

    client = _make_client(account_id, api_key)
    endpoint = f"/accounts/{account_id}/orders"
    req_summary = repr({"asset": asset, "side": side, "quantity": qty_str, "type": "market"})

    logger.info("Placing market order: %s %s qty=%s (~$%.2f)", side.upper(), asset, qty_str, notional_usd)

    try:
        if side == "buy":
            orders = _with_retry(lambda: client.market_buy(base=asset, quantity=qty_str))
        else:
            orders = _with_retry(lambda: client.market_sell(base=asset, quantity=qty_str))

        order_id = orders[0].get("orderId") if orders else None
        _log_order("POST", endpoint, req_summary, 200, str(orders), order_id)

        if not order_id:
            raise RuntimeError(f"No orderId in response: {orders}")

        logger.info("Order placed: order_id=%s (~$%.2f)", order_id, notional_usd)
        return str(order_id)

    except ProprAPIError as exc:
        _log_order("POST", endpoint, req_summary, exc.status_code, exc.message, None)
        raise RuntimeError(
            f"place_market_order failed [{exc.status_code}] {exc.code}: {exc.message}"
        ) from exc


def cancel_order(account_id: str, order_id: str, api_key: str) -> bool:
    """
    Cancel an open order via POST .../cancel.
    Returns True if cancelled, False if already filled/cancelled.
    """
    client = _make_client(account_id, api_key)
    endpoint = f"/accounts/{account_id}/orders/{order_id}/cancel"

    try:
        result = _with_retry(lambda: client.cancel_order(order_id))
        _log_order("POST", endpoint, None, 200, str(result), order_id)
        cancelled = result is not None  # None = already filled/cancelled
        if cancelled:
            logger.info("Order cancelled: %s", order_id)
        else:
            logger.info("Cancel: order %s already filled/cancelled", order_id)
        return cancelled

    except ProprAPIError as exc:
        _log_order("POST", endpoint, None, exc.status_code, exc.message, order_id)
        logger.warning("Cancel failed for %s: [%s] %s", order_id, exc.status_code, exc.message)
        return False


def get_positions(account_id: str, api_key: str) -> dict[str, dict]:
    """
    Return all open positions keyed by Propr asset name.

    Returns
    -------
    {
        "BTC": {
            "quantity": 0.00012,
            "side": "long",
            "entry_price": 80980.0,
            "mark_price": 80991.5,
            "unrealized_pnl": 0.14,
            "notional_value": 9.72,
        },
        ...
    }
    """
    client = _make_client(account_id, api_key)
    raw = _with_retry(lambda: client.get_open_positions())

    return {
        pos["asset"]: {
            "quantity": float(pos["quantity"]),
            "side": pos.get("positionSide", "long"),
            "entry_price": float(pos.get("entryPrice", 0)),
            "mark_price": float(pos.get("markPrice", 0)),
            "unrealized_pnl": float(pos.get("unrealizedPnl", 0)),
            "notional_value": float(pos.get("notionalValue", 0)),
        }
        for pos in raw
    }


def close_position(account_id: str, asset: str, api_key: str) -> bool:
    """
    Close the full open position for `asset`. Returns True if flat afterwards.

    Uses ProprClient.close_position() which:
    - Detects positionSide automatically from open positions
    - Places market sell with closePosition=True, reduceOnly=True
    - Returns [] if already flat (treated as success)
    """
    client = _make_client(account_id, api_key)
    logger.info("Closing position: %s", asset)

    try:
        orders = _with_retry(lambda: client.close_position(base=asset))
        if orders:
            order_id = orders[0].get("orderId")
            _log_order(
                "POST", f"/accounts/{account_id}/orders",
                repr({"closePosition": True, "asset": asset}),
                200, str(orders), order_id,
            )
            logger.info("Position close order placed: %s order_id=%s", asset, order_id)
        else:
            logger.info("close_position: %s already flat", asset)
        return True

    except ProprAPIError as exc:
        _log_order(
            "POST", f"/accounts/{account_id}/orders",
            repr({"closePosition": True, "asset": asset}),
            exc.status_code, exc.message, None,
        )
        logger.error("close_position failed for %s: [%s] %s", asset, exc.status_code, exc.message)
        return False


def flatten_all(account_id: str, api_key: str) -> None:
    """
    Close every open position. Never raises — logs errors and continues.
    """
    logger.warning("flatten_all: closing all open positions")
    client = _make_client(account_id, api_key)

    try:
        positions = _with_retry(lambda: client.get_open_positions())
    except Exception as exc:
        logger.error("flatten_all: could not fetch positions: %s", exc)
        return

    if not positions:
        logger.info("flatten_all: no open positions found")
        return

    for pos in positions:
        asset = pos["asset"]
        try:
            _with_retry(lambda p=pos: client.close_position(base=p["asset"]))
            logger.info("flatten_all: closed %s", asset)
        except Exception as exc:
            logger.error("flatten_all: exception closing %s: %s", asset, exc)
