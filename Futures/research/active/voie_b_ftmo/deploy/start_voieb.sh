#!/usr/bin/env bash
# start_voieb.sh — Launch MT5 under Xvfb
# Run inside a detached screen session: screen -dmS mt5 ~/start_voieb.sh
# When MT5 exits (intentionally or crashes), the script ends → screen dies
# → watchdog.sh detects missing terminal64.exe and calls this again.

set -euo pipefail

export WINEPREFIX="$HOME/.wine_mt5"
export WINEARCH=win64
export WINEDEBUG=-all
export DISPLAY=:99

MT5_EXE="$WINEPREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"
LOG="$HOME/voieb_mt5.log"

ts() { date '+%Y-%m-%d %H:%M:%S UTC'; }
echo "[$(ts)] start_voieb.sh — starting" >> "$LOG"

# Kill stale Xvfb from a previous run
pkill -u "$(whoami)" -f "Xvfb :99" 2>/dev/null || true
sleep 1

# Virtual display
Xvfb :99 -screen 0 1024x768x24 -nolisten tcp &
XVFB_PID=$!
echo "[$(ts)] Xvfb started (pid $XVFB_PID)" >> "$LOG"
sleep 2

# Launch MT5 (blocking — script stays alive until MT5 exits)
wine "$MT5_EXE" /portable >> "$LOG" 2>&1

echo "[$(ts)] MT5 exited" >> "$LOG"

# Cleanup
kill "$XVFB_PID" 2>/dev/null || true
wineserver -k 2>/dev/null || true
