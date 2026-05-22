"""
watchdog.py — VPS heartbeat endpoint for Strategy C
====================================================
Deploy on VPS (Hetzner <VPS_IP>) as a systemd service.

Mac run_daily.py (via monitor_loop) POSTs heartbeat every 30s.
watchdog_check.sh (cron */2) reads HEARTBEAT_FILE and alerts via
Telegram if heartbeat has been silent for more than 3 minutes.

This service cannot flat positions — its only role is out-of-process
alerting when the Mac or IB Gateway dies silently during a trade.

Deploy:
  # On VPS:
  pip install flask
  sudo cp watchdog.service /etc/systemd/system/strategy_c_watchdog.service
  sudo systemctl daemon-reload
  sudo systemctl enable strategy_c_watchdog
  sudo systemctl start strategy_c_watchdog

Run directly:
  python3 -m Futures.live.strategy_c_live.watchdog
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from flask import Flask, jsonify, request
except ImportError:
    raise ImportError("flask not installed. Run: pip install flask")

app = Flask(__name__)

HEARTBEAT_FILE = Path("/tmp/strategy_c_heartbeat.json")


@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    """Receive heartbeat from Mac monitor_loop. Write to file."""
    data = request.json or {}
    HEARTBEAT_FILE.write_text(json.dumps({
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "status":    data.get("status", "unknown"),
        "dd_pct":    data.get("dd_pct", None),
    }))
    return jsonify({"ok": True})


@app.route("/status", methods=["GET"])
def status():
    """Return last heartbeat data. Used by watchdog_check.sh and manual inspection."""
    if not HEARTBEAT_FILE.exists():
        return jsonify({"status": "NO_DATA", "last_seen": None, "dd_pct": None})
    return jsonify(json.loads(HEARTBEAT_FILE.read_text()))


@app.route("/health", methods=["GET"])
def health():
    """Liveness check for the watchdog service itself."""
    return jsonify({"service": "strategy_c_watchdog", "ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765)
