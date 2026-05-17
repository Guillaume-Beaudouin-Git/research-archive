"""
hyperliquid_client.py

Minimal wrapper around hyperliquid-python-sdk.
Supports testnet and mainnet, opens/closes USD-notional perp positions.

Install: pip install hyperliquid-python-sdk eth_account
Testnet UI: https://app.hyperliquid-testnet.xyz

Fill logging (logs/fills.csv):
    Every market open/close appends one row:
    timestamp, symbol, side, size, expected_price, actual_price,
    slippage_bps, fill_latency_ms

    slippage_bps = (actual - expected) / expected * 10 000
    Positive = paid more than mid-price (typical for market buy).
    Negative = received more than mid-price (favourable fill).

Funding logging (logs/funding.csv):
    get_funding_paid(symbol, since) appends one row per payment:
    timestamp, symbol, coin, funding_usd, position_size, funding_rate
"""
import csv
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_LOGS_DIR       = Path("logs")
_FILLS_CSV      = _LOGS_DIR / "fills.csv"
_FUNDING_CSV    = _LOGS_DIR / "funding.csv"

_FILLS_HEADER   = [
    "timestamp", "symbol", "side", "size",
    "expected_price", "actual_price", "slippage_bps", "fill_latency_ms",
]
_FUNDING_HEADER = [
    "timestamp", "symbol", "coin",
    "funding_usd", "position_size", "funding_rate",
]


def _ensure_logs_dir() -> None:
    """Create logs/ directory if it does not exist."""
    _LOGS_DIR.mkdir(exist_ok=True)


def _extract_fill_price(resp: dict) -> Optional[float]:
    """
    Safely extract the average fill price from a Hyperliquid order response.

    Expected path (SDK ≥ 0.2):
        resp["response"]["data"]["statuses"][0]["filled"]["avgPx"]

    Returns None if the path is absent or malformed so callers can fall
    back to expected_price rather than crashing.
    """
    try:
        avg_px = resp["response"]["data"]["statuses"][0]["filled"]["avgPx"]
        return float(avg_px)
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _extract_fill_size(resp: dict) -> Optional[float]:
    """
    Safely extract the total filled size from a Hyperliquid order response.

    Returns None on any parse failure.
    """
    try:
        total_sz = resp["response"]["data"]["statuses"][0]["filled"]["totalSz"]
        return float(total_sz)
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _log_fill(
    symbol: str,
    side: str,
    size: float,
    expected_price: float,
    resp: dict,
    latency_ms: float,
) -> None:
    """
    Append one fill record to logs/fills.csv.

    Args:
        symbol:         Yahoo Finance ticker, e.g. "BTC-USD".
        side:           "buy" or "sell" (direction of the order, not position).
        size:           Filled size in base asset (e.g. BTC).
        expected_price: Mid-price captured immediately before order submission.
        resp:           Raw Hyperliquid API response dict.
        latency_ms:     Round-trip time from submission to response receipt.
    """
    _ensure_logs_dir()

    actual_price = _extract_fill_price(resp)
    if actual_price is None:
        logger.warning(
            f"_log_fill: could not extract fill price from response for {symbol}; "
            f"logging expected_price as actual_price. Response: {resp}"
        )
        actual_price = expected_price

    slippage_bps = (
        (actual_price - expected_price) / expected_price * 10_000
        if expected_price > 0 else 0.0
    )

    write_header = not _FILLS_CSV.exists()
    with open(_FILLS_CSV, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FILLS_HEADER)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp":       datetime.now(timezone.utc).isoformat(),
            "symbol":          symbol,
            "side":            side,
            "size":            f"{size:.6f}",
            "expected_price":  f"{expected_price:.4f}",
            "actual_price":    f"{actual_price:.4f}",
            "slippage_bps":    f"{slippage_bps:.3f}",
            "fill_latency_ms": f"{latency_ms:.1f}",
        })

    logger.info(
        f"Fill logged | {symbol} {side} {size:.6f} | "
        f"expected={expected_price:.4f} actual={actual_price:.4f} "
        f"slippage={slippage_bps:+.1f}bps latency={latency_ms:.0f}ms"
    )


SYMBOL_MAP = {
    "BTC-USD": "BTC",
    "ETH-USD": "ETH",
    "SOL-USD": "SOL",
    "ADA-USD": "ADA",
    "AVAX-USD": "AVAX",
    "LINK-USD": "LINK",
    "DOT-USD": "DOT",
}


class HyperliquidClient:
    """Wrapper for Hyperliquid perps. All sizes are USD notional."""

    def __init__(self, private_key: str, testnet: bool = True,
                 leverage: int = 1):
        from hyperliquid.utils import constants
        from hyperliquid.exchange import Exchange
        from hyperliquid.info import Info
        import eth_account

        self.testnet = testnet
        self.leverage = leverage
        base_url = (constants.TESTNET_API_URL if testnet
                    else constants.MAINNET_API_URL)

        account = eth_account.Account.from_key(private_key)
        self.wallet_address = account.address
        self.info = Info(base_url, skip_ws=True)
        self.exchange = Exchange(account, base_url)

        env = "TESTNET" if testnet else "MAINNET"
        logger.info(f"Hyperliquid {env} ready | wallet: {self.wallet_address}")
        self._sz_cache: dict[str, int] = {}   # coin → szDecimals, populated lazily

    def _coin(self, symbol: str) -> str:
        if symbol not in SYMBOL_MAP:
            raise ValueError(f"Unknown symbol: {symbol}")
        return SYMBOL_MAP[symbol]

    def _sz_decimals(self, coin: str) -> int:
        """
        Return the HL-required decimal places for `coin` order size.
        Fetched once from the meta endpoint and cached for the session.
        Falls back to 4 on any API failure.
        """
        if coin not in self._sz_cache:
            try:
                meta = self.info.meta()
                for asset in meta.get("universe", []):
                    self._sz_cache[asset["name"]] = int(asset.get("szDecimals", 4))
                logger.info(f"szDecimals cache populated: {len(self._sz_cache)} assets")
            except Exception as exc:
                logger.warning(f"_sz_decimals: meta fetch failed ({exc}); "
                               f"defaulting to 4 for {coin}")
                return 4
        return self._sz_cache.get(coin, 4)

    def _check_order_response(self, resp: dict, coin: str, action: str) -> None:
        """
        Raise ValueError if the HL order response contains an error.

        Checks two levels:
          1. Top-level {"error": "..."} — auth failures, invalid size, etc.
          2. Per-status {"statuses": [{"error": "..."}]} — order-level rejection.
        """
        if isinstance(resp, dict) and "error" in resp:
            raise ValueError(f"HL {action} {coin} rejected: {resp['error']}")
        try:
            statuses = resp["response"]["data"]["statuses"]
            for status in statuses:
                if "error" in status:
                    raise ValueError(
                        f"HL {action} {coin} order status error: {status['error']}"
                    )
        except (KeyError, IndexError, TypeError):
            pass  # missing statuses path means success in normal SDK responses

    def get_mid_price(self, symbol: str) -> float:
        coin = self._coin(symbol)
        mids = self.info.all_mids()
        return float(mids[coin])

    def get_account_value(self) -> float:
        state = self.info.user_state(self.wallet_address)
        return float(state["marginSummary"]["accountValue"])

    def get_position(self, symbol: str) -> dict:
        """Returns {'side': 'long'|'short'|'flat', 'size': float, 'entry_price': float}."""
        coin = self._coin(symbol)
        state = self.info.user_state(self.wallet_address)
        for p in state.get("assetPositions", []):
            pos = p.get("position", {})
            if pos.get("coin") == coin:
                szi = float(pos.get("szi", 0))
                if szi == 0:
                    return {"side": "flat", "size": 0.0, "entry_price": 0.0}
                return {
                    "side": "long" if szi > 0 else "short",
                    "size": abs(szi),
                    "entry_price": float(pos.get("entryPx", 0)),
                }
        return {"side": "flat", "size": 0.0, "entry_price": 0.0}

    def _size_from_usd(self, symbol: str, usd: float) -> float:
        coin     = self._coin(symbol)
        mid      = self.get_mid_price(symbol)
        decimals = self._sz_decimals(coin)
        return round(usd / mid, decimals)

    def open_long(self, symbol: str, usd_size: float) -> dict:
        """
        Open a long position sized in USD notional. Logs fill to fills.csv.

        Args:
            symbol:   Yahoo Finance ticker, e.g. "BTC-USD".
            usd_size: Notional USD to deploy (e.g. 300.0 for $300).

        Returns:
            dict with keys: response, expected_price, size, latency_ms.
        """
        coin = self._coin(symbol)
        size = self._size_from_usd(symbol, usd_size)
        expected = self.get_mid_price(symbol)
        t0 = time.time()
        resp = self.exchange.market_open(coin, True, size)
        latency_ms = (time.time() - t0) * 1000
        self._check_order_response(resp, coin, "open_long")
        _log_fill(symbol, "buy", size, expected, resp, latency_ms)
        return {"response": resp, "expected_price": expected,
                "size": size, "latency_ms": latency_ms}

    def open_short(self, symbol: str, usd_size: float) -> dict:
        """
        Open a short position sized in USD notional. Logs fill to fills.csv.

        Args:
            symbol:   Yahoo Finance ticker, e.g. "BTC-USD".
            usd_size: Notional USD to deploy.

        Returns:
            dict with keys: response, expected_price, size, latency_ms.
        """
        coin = self._coin(symbol)
        size = self._size_from_usd(symbol, usd_size)
        expected = self.get_mid_price(symbol)
        t0 = time.time()
        resp = self.exchange.market_open(coin, False, size)
        latency_ms = (time.time() - t0) * 1000
        self._check_order_response(resp, coin, "open_short")
        _log_fill(symbol, "sell", size, expected, resp, latency_ms)
        return {"response": resp, "expected_price": expected,
                "size": size, "latency_ms": latency_ms}

    def close_position(self, symbol: str, side: str = "unknown") -> dict:
        """
        Close the entire open position for symbol. Logs fill to fills.csv.

        Args:
            symbol: Yahoo Finance ticker, e.g. "BTC-USD".
            side:   Current position direction ("long" or "short"). Used to
                    determine the close order direction for the fill log:
                    closing a long → "sell", closing a short → "buy".
                    Defaults to "unknown" if caller doesn't provide it.

        Returns:
            dict with keys: response, expected_price, latency_ms.
        """
        coin = self._coin(symbol)
        expected = self.get_mid_price(symbol)
        t0 = time.time()
        resp = self.exchange.market_close(coin)
        latency_ms = (time.time() - t0) * 1000
        self._check_order_response(resp, coin, "close_position")

        # Infer close-order direction from position side
        close_side = {"long": "sell", "short": "buy"}.get(side, "unknown")
        fill_size   = _extract_fill_size(resp) or 0.0
        _log_fill(symbol, close_side, fill_size, expected, resp, latency_ms)

        return {"response": resp, "expected_price": expected,
                "latency_ms": latency_ms}

    def get_funding_paid(
        self,
        symbol: str,
        since: datetime,
    ) -> list[dict]:
        """
        Query Hyperliquid funding payment history and append to logs/funding.csv.

        Funding on Hyperliquid accrues every 8 hours.  This method fetches all
        payments for `symbol` from `since` to now and appends one row per
        payment to funding.csv.  Rows are deduplicated by timestamp on append
        so calling this multiple times per day is safe.

        Args:
            symbol: Yahoo Finance ticker, e.g. "BTC-USD".
            since:  UTC datetime from which to fetch payments (inclusive).

        Returns:
            List of dicts, one per funding event appended (empty if none).
        """
        # TODO (resilience): 24h lookback in caller assumes daily cron. If bot
        # is halted >24h, funding events will be missed. Consider persisting
        # last_funding_fetch_utc to state.json and using that as `since`.
        coin      = self._coin(symbol)
        since_ms  = int(since.timestamp() * 1000)

        try:
            raw = self.info.user_funding_history(self.wallet_address, since_ms)
        except Exception as exc:
            logger.error(f"get_funding_paid: API error for {symbol}: {exc}")
            return []

        # Filter to this coin and build records
        records: list[dict] = []
        for item in raw:
            if item.get("coin") != coin:
                continue
            ts_ms   = int(item.get("time", 0))
            ts_iso  = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()
            records.append({
                "timestamp":     ts_iso,
                "symbol":        symbol,
                "coin":          coin,
                "funding_usd":   str(item.get("usdc", "0")),
                "position_size": str(item.get("szi", "0")),
                "funding_rate":  str(item.get("fundingRate", "0")),
            })

        if not records:
            logger.info(f"get_funding_paid: no funding payments for {symbol} since {since.date()}")
            return []

        _ensure_logs_dir()

        # Read existing timestamps to avoid duplicate rows
        existing_ts: set[str] = set()
        if _FUNDING_CSV.exists():
            with open(_FUNDING_CSV, newline="") as fh:
                for row in csv.DictReader(fh):
                    existing_ts.add(row.get("timestamp", ""))

        new_records = [r for r in records if r["timestamp"] not in existing_ts]

        if new_records:
            write_header = not _FUNDING_CSV.exists()
            with open(_FUNDING_CSV, "a", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=_FUNDING_HEADER)
                if write_header:
                    writer.writeheader()
                writer.writerows(new_records)
            logger.info(
                f"Funding logged | {symbol}: {len(new_records)} new payment(s) "
                f"appended to {_FUNDING_CSV}"
            )
        else:
            logger.info(f"get_funding_paid: all {len(records)} record(s) already in {_FUNDING_CSV}")

        return new_records
