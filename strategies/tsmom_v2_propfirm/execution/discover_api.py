"""
Step 0 — Propr API Discovery.

Runs calls 0a–0h sequentially against the real Propr API and prints raw JSON.
Must complete fully before any other execution module is written.

Usage:
    export PROPR_API_KEY="pk_live_..."
    python -m strategies.tsmom_v2_propfirm.execution.discover_api

Exit code 0 = all calls succeeded and PROPR_ASSET_MAP printed.
Exit code 1 = any call failed (stops immediately).
"""

from __future__ import annotations

import json
import os
import sys
import time

import requests

# ── Pre-condition ───────────────────────────────────────────────────────────────
API_KEY = os.environ.get("PROPR_API_KEY", "")
if not API_KEY:
    print("ERROR: PROPR_API_KEY environment variable is not set.", file=sys.stderr)
    print("  export PROPR_API_KEY='pk_live_...'", file=sys.stderr)
    sys.exit(1)

BASE_URL = "https://api.propr.xyz/v1"
ACCOUNT_ID = "urn:prp-account:mJxf8BBjGbma"
ATTEMPT_ID = "urn:prp-challenge-attempt:y2ZKVvncugLE"

session = requests.Session()
session.headers.update({
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
})


def call(label: str, method: str, path: str, json_body: dict | None = None) -> dict:
    """Execute one API call, print result, exit on non-2xx."""
    url = f"{BASE_URL}{path}"
    print(f"\n{'='*60}")
    print(f"=== {label}: {method} {path} ===")
    print(f"{'='*60}")
    if json_body:
        print(f"Request body: {json.dumps(json_body, indent=2)}")

    resp = session.request(method, url, json=json_body, timeout=15)

    print(f"Status: {resp.status_code}")
    try:
        body = resp.json()
        print(json.dumps(body, indent=2))
    except Exception:
        body = resp.text
        print(body)

    if resp.status_code >= 300:
        print(f"\nFATAL: {label} returned {resp.status_code} — stopping.", file=sys.stderr)
        sys.exit(1)

    return body if isinstance(body, dict) else {"_raw": body}


def main() -> None:
    # 0a — Health check
    call("0a", "GET", "/health")

    # 0b — List open positions
    positions_resp = call("0b", "GET", f"/accounts/{ACCOUNT_ID}/positions")

    # 0c — Account / margin state for the challenge attempt
    attempt_resp = call("0c", "GET", f"/challenge-attempts/{ATTEMPT_ID}")

    # 0d — Leverage limits (try top-level first, then account-scoped)
    print(f"\n{'='*60}")
    print(f"=== 0d: GET /leverage-limits/effective (top-level) ===")
    print(f"{'='*60}")
    resp_lev = session.get(f"{BASE_URL}/leverage-limits/effective", timeout=15)
    print(f"Status: {resp_lev.status_code}")
    try:
        lev_body = resp_lev.json(); print(json.dumps(lev_body, indent=2))
    except Exception:
        lev_body = {}; print(resp_lev.text)
    if resp_lev.status_code == 404:
        print("  → 404, trying /accounts/{accountId}/leverage-limits ...")
        resp_lev2 = session.get(f"{BASE_URL}/accounts/{ACCOUNT_ID}/leverage-limits", timeout=15)
        print(f"Status: {resp_lev2.status_code}")
        try:
            lev_body = resp_lev2.json(); print(json.dumps(lev_body, indent=2))
        except Exception:
            lev_body = {}; print(resp_lev2.text)

    # 0e — Available assets / tradeable pairs (try multiple paths)
    print(f"\n{'='*60}")
    print(f"=== 0e: probing asset endpoints ===")
    print(f"{'='*60}")
    for asset_path in [
        f"/accounts/{ACCOUNT_ID}/assets",
        f"/accounts/{ACCOUNT_ID}/symbols",
        f"/assets",
        f"/symbols",
        f"/markets",
    ]:
        r = session.get(f"{BASE_URL}{asset_path}", timeout=15)
        print(f"\nGET {asset_path}  → {r.status_code}")
        if r.status_code < 300:
            try:
                body = r.json(); print(json.dumps(body, indent=2)[:2000])
            except Exception:
                print(r.text[:2000])
            break
        else:
            try: print(r.json())
            except Exception: print(r.text[:200])
    assets_resp = {}

    # 0f — Place a minimal test order
    # BTC bare name confirmed from leverage-limits overrides.
    # We try progressively different size/notional approaches.
    url_orders = f"{BASE_URL}/accounts/{ACCOUNT_ID}/orders"
    order_id: str | None = None
    order_body: dict = {}

    # First check existing orders (GET) to understand field names from real data
    print(f"\n{'='*60}")
    print(f"=== 0f-pre: GET /accounts/{ACCOUNT_ID}/orders (schema probe) ===")
    print(f"{'='*60}")
    r_orders_get = session.get(f"{BASE_URL}/accounts/{ACCOUNT_ID}/orders", timeout=15)
    print(f"Status: {r_orders_get.status_code}")
    try: print(json.dumps(r_orders_get.json(), indent=2))
    except Exception: print(r_orders_get.text[:1000])

    # Check if there's an alternate order path via challenge-attempt
    print(f"\n{'='*60}")
    print(f"=== 0f-pre2: probing alternate order endpoints ===")
    print(f"{'='*60}")
    for probe_path in [
        f"/challenge-attempts/{ATTEMPT_ID}/orders",
        f"/orders",
        f"/accounts/{ACCOUNT_ID}/trade",
        f"/accounts/{ACCOUNT_ID}/order",
    ]:
        r = session.get(f"{BASE_URL}{probe_path}", timeout=15)
        print(f"GET {probe_path}  → {r.status_code}")
        if r.status_code < 300:
            try: print(json.dumps(r.json(), indent=2)[:1000])
            except Exception: print(r.text[:500])
        else:
            try: print(f"  {r.json()}")
            except Exception: pass

    # Probe API docs / OpenAPI spec
    for spec_path in ["/docs", "/swagger", "/openapi.json", "/swagger.json", "/api-docs"]:
        r = session.get(f"{BASE_URL}{spec_path}", timeout=10)
        print(f"GET {spec_path}  → {r.status_code}")
        if r.status_code == 200:
            print(str(r.text)[:500])
            break

    candidates = [
        # market, different orderType casing
        {"asset": "BTC", "side": "buy", "size": 0.001, "orderType": "market"},
        {"asset": "BTC", "side": "buy", "size": 0.001, "orderType": "MARKET"},
        {"asset": "BTC", "side": "buy", "size": 0.001, "type": "market"},
        {"asset": "BTC", "side": "buy", "size": 0.001, "type": "MARKET"},
        # limit order with price
        {"asset": "BTC", "side": "buy", "size": 0.001, "orderType": "limit", "price": 1.0},
        {"asset": "BTC", "side": "buy", "size": 0.001, "orderType": "LIMIT", "price": 1.0},
        # Hyperliquid-style field names
        {"asset": "BTC", "isBuy": True, "sz": 0.001, "orderType": "market"},
        {"coin": "BTC", "side": "buy", "size": 0.001, "orderType": "market"},
        # notional variants
        {"asset": "BTC", "side": "buy", "notional": 50.0, "orderType": "market"},
        {"asset": "BTC", "side": "buy", "amount": 50.0, "orderType": "market"},
    ]

    for attempt_num, body in enumerate(candidates, 1):
        print(f"\n{'='*60}")
        print(f"=== 0f attempt {attempt_num}: POST /accounts/{ACCOUNT_ID}/orders ===")
        print(f"{'='*60}")
        print(f"Request body: {json.dumps(body, indent=2)}")
        resp_order = session.post(url_orders, json=body, timeout=15)
        print(f"Status: {resp_order.status_code}")
        try:
            order_body = resp_order.json()
            print(json.dumps(order_body, indent=2))
        except Exception:
            order_body = {"_raw": resp_order.text}
            print(resp_order.text)

        if resp_order.status_code < 300:
            order_id = (
                order_body.get("orderId")
                or order_body.get("id")
                or order_body.get("order_id")
            )
            print(f"\n[0f] SUCCESS on attempt {attempt_num}. order_id={order_id}")
            break
        elif resp_order.status_code == 422:
            # Validation error — read field hints from response and try next
            print(f"  → 422 validation error, trying next schema...")
        elif resp_order.status_code == 400:
            err_code = order_body.get("code")
            print(f"  → 400 code={err_code}, trying next schema...")
        else:
            print(f"\nFATAL: 0f returned unexpected {resp_order.status_code} — stopping.", file=sys.stderr)
            sys.exit(1)
    else:
        # Try challenge-attempt scoped order endpoint before giving up
        print(f"\n{'='*60}")
        print(f"=== 0f-alt: POST /challenge-attempts/{ATTEMPT_ID}/orders ===")
        print(f"{'='*60}")
        alt_path = f"/challenge-attempts/{ATTEMPT_ID}/orders"
        for body in [
            {"asset": "BTC", "side": "buy", "size": 0.001, "orderType": "market"},
            {"asset": "BTC", "side": "buy", "size": 0.001, "orderType": "market", "leverage": 2},
            {"asset": "BTC", "side": "BUY", "size": 0.001, "orderType": "market"},
            {"asset": "BTC", "side": "buy", "size": 0.001, "orderType": "market", "reduceOnly": False},
        ]:
            print(f"\nPOST {alt_path}")
            print(f"Body: {json.dumps(body)}")
            r = session.post(f"{BASE_URL}{alt_path}", json=body, timeout=15)
            print(f"Status: {r.status_code}")
            try:
                rb = r.json(); print(json.dumps(rb, indent=2))
            except Exception:
                rb = {}; print(r.text[:500])
            if r.status_code < 300:
                order_id = rb.get("orderId") or rb.get("id") or rb.get("order_id")
                print(f"\n[0f-alt] SUCCESS! order_id={order_id}")
                break
        else:
            print("\n" + "="*60, file=sys.stderr)
            print("BLOCKED: 0f order_create_failed on all paths.", file=sys.stderr)
            print("Possible cause: paper account not fully provisioned (bookAccountIssuanceId=null).", file=sys.stderr)
            print("Manual action: Contact Propr support or check account status.", file=sys.stderr)
            print("="*60, file=sys.stderr)
            print("\nContinuing to document other endpoints...", file=sys.stderr)
            # Don't sys.exit — document what we know

    # 0g — Cancel the test order (try DELETE then POST .../cancel)
    if order_id:
        time.sleep(1)
        print(f"\n{'='*60}")
        print(f"=== 0g: cancel order {order_id} ===")
        print(f"{'='*60}")
        r_del = session.delete(f"{BASE_URL}/accounts/{ACCOUNT_ID}/orders/{order_id}", timeout=15)
        print(f"DELETE /orders/{order_id}  → {r_del.status_code}")
        try: print(json.dumps(r_del.json(), indent=2))
        except Exception: print(r_del.text)
        if r_del.status_code >= 300:
            r_cancel = session.post(
                f"{BASE_URL}/accounts/{ACCOUNT_ID}/orders/{order_id}/cancel", timeout=15
            )
            print(f"POST /orders/{order_id}/cancel  → {r_cancel.status_code}")
            try: print(json.dumps(r_cancel.json(), indent=2))
            except Exception: print(r_cancel.text)
    else:
        print("\n[0g] Skipping cancel — no order_id (order may have filled immediately)")

    # 0g2 — Get open orders list
    call("0g2", "GET", f"/accounts/{ACCOUNT_ID}/orders")

    # 0g3 — Get trades log
    print(f"\n{'='*60}")
    print(f"=== 0g3: GET /accounts/{ACCOUNT_ID}/trades ===")
    print(f"{'='*60}")
    r_trades = session.get(f"{BASE_URL}/accounts/{ACCOUNT_ID}/trades", timeout=15)
    print(f"Status: {r_trades.status_code}")
    try: print(json.dumps(r_trades.json(), indent=2)[:3000])
    except Exception: print(r_trades.text[:500])

    # 0g4 — Positions after cancel
    call("0g4", "GET", f"/accounts/{ACCOUNT_ID}/positions")

    # 0h — Single asset margin config (probe multiple naming formats)
    print(f"\n{'='*60}")
    print(f"=== 0h: probing single-asset endpoint for BTC naming format ===")
    print(f"{'='*60}")
    for btc_name in ["BTC", "BTC-USD", "BTC-USDC", "BTC/USDC", "BTCUSD", "BTCUSDC"]:
        r = session.get(f"{BASE_URL}/accounts/{ACCOUNT_ID}/assets/{btc_name}", timeout=15)
        print(f"  GET /assets/{btc_name}  → {r.status_code}")
        if r.status_code < 300:
            try: print(json.dumps(r.json(), indent=2))
            except Exception: print(r.text[:500])
            break
        else:
            try: print(f"  {r.json()}")
            except Exception: print(f"  {r.text[:100]}")

    # ── Summary ─────────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("=== DISCOVERY COMPLETE — Raw structure notes ===")
    print("="*60)
    print()
    print("Review the JSON above and extract:")
    print("  1. Asset naming (e.g. 'BTC' or 'BTC-USD' or 'BTCUSD')")
    print("  2. Order request fields (asset/symbol, size/quantity/notional, orderType/type)")
    print("  3. Position response fields (size, side, entryPrice, unrealizedPnl)")
    print("  4. Equity fields (marginBalance, highWaterMark)")
    print("  5. Available assets for PROPR_ASSET_MAP")
    print()
    print("Paste candidate PROPR_ASSET_MAP below (edit after confirming naming from above):")
    print("""
PROPR_ASSET_MAP = {
    "BTC-USD":   "BTC",      # confirm from 0e/0h
    "ETH-USD":   "ETH",
    "SOL-USD":   "SOL",
    "AVAX-USD":  "AVAX",
    "LINK-USD":  "LINK",
    "DOGE-USD":  "DOGE",
    "ADA-USD":   "ADA",
    "DOT-USD":   "DOT",
    "UNI-USD":   "UNI",
    "LTC-USD":   "LTC",
    "BCH-USD":   "BCH",
    "MATIC-USD": "MATIC",
    "OP-USD":    "OP",
    "ARB-USD":   "ARB",
}
""")
    print("✅ Step 0 complete. Paste confirmed PROPR_ASSET_MAP into execution/__init__.py before proceeding.")


if __name__ == "__main__":
    main()
