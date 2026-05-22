#!/bin/bash
# watchdog_check.sh — VPS cron: alert if Mac heartbeat dead during trading hours
#
# Runs every 2 minutes during market hours.
# Sends Telegram CRITICAL if heartbeat has been silent for > 3 minutes.
#
# Cron (summer, ET=UTC-4: 09:00-13:00 ET = 13:00-17:00 UTC):
#   */2 13-17 * * 1-5  /bin/bash /home/algo/projects/Algo_claude/Futures/live/strategy_c_live/watchdog_check.sh
#
# Cron (winter, ET=UTC-5: 09:00-13:00 ET = 14:00-18:00 UTC):
#   */2 14-18 * * 1-5  /bin/bash /home/algo/projects/Algo_claude/Futures/live/strategy_c_live/watchdog_check.sh
#
# Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in environment.
# Add to /home/algo/.env and source it in cron via EnvironmentFile or:
#   */2 13-17 * * 1-5  source /home/algo/.env && /bin/bash ...watchdog_check.sh

set -euo pipefail

HEARTBEAT_FILE="/tmp/strategy_c_heartbeat.json"
SILENCE_THRESHOLD=180   # 3 minutes

# No heartbeat file = watchdog hasn't received a ping yet (pre-market OK)
if [ ! -f "$HEARTBEAT_FILE" ]; then
    exit 0
fi

NOW=$(date +%s)

# Parse last_seen timestamp from JSON
LAST_SEEN=$(python3 - <<'EOF'
import json, datetime, sys
try:
    with open("/tmp/strategy_c_heartbeat.json") as f:
        d = json.load(f)
    t = datetime.datetime.fromisoformat(d["last_seen"])
    print(int(t.timestamp()))
except Exception as e:
    print(0)
EOF
)

DELTA=$((NOW - LAST_SEEN))

if [ "$DELTA" -gt "$SILENCE_THRESHOLD" ]; then
    python3 - <<EOF
import os, requests
token   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
if token and chat_id:
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": f"🚨 NQ-C WATCHDOG: no heartbeat for ${DELTA}s.\nMac / IB Gateway down?\nCheck position manually.",
            },
            timeout=10,
        )
    except Exception as e:
        print(f"Telegram failed: {e}", file=__import__("sys").stderr)
else:
    print("WATCHDOG: Telegram not configured", file=__import__("sys").stderr)
EOF
fi
