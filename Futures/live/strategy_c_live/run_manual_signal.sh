#!/bin/bash
# run_manual_signal.sh — Daily launcher for iter_10 manual paper trade signal
#
# Usage (manual):
#   cd ~/Desktop/Algo_claude
#   ./Futures/live/strategy_c_live/run_manual_signal.sh
#
# Usage (cron Mac, Paris summer UTC+2):
#   43 15 * * 1-5  cd ~/Desktop/Algo_claude && ./Futures/live/strategy_c_live/run_manual_signal.sh
#
# Usage (cron Mac, Paris winter UTC+1):
#   43 14 * * 1-5  cd ~/Desktop/Algo_claude && ./Futures/live/strategy_c_live/run_manual_signal.sh
#
# Usage (launchd): see com.algo_claude.manual_signal.plist
#
# Triggers at 15:43 Paris (09:43 ET summer) — signal must arrive before 09:46 entry.
# Exit window 09:43-09:47 ET enforced inside manual_signal.py.

set -e

# Resolve repo root regardless of where the script is called from
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

# Load .env (Telegram creds; no TRADOVATE_* needed in manual_paper_trade mode)
if [ -f .env ]; then
    set -a
    # shellcheck source=.env
    source .env
    set +a
fi

# Create logs directory if absent
mkdir -p "$SCRIPT_DIR/logs"

LOG_FILE="$SCRIPT_DIR/logs/manual_signal.log"

/usr/bin/python3 -m Futures.live.strategy_c_live.manual_signal \
    >> "$LOG_FILE" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] run_manual_signal.sh complete" >> "$LOG_FILE"
