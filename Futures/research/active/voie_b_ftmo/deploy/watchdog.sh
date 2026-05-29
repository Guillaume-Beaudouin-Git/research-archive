#!/usr/bin/env bash
# watchdog.sh — Monitor MT5 and restart if terminal64.exe absent.
#
# Cron (as mt5user, add via crontab -e):
#   */15 12-23 * * 1-5 ~/watchdog.sh
#   @reboot sleep 30 && screen -dmS mt5 ~/start_voieb.sh
#
# Window 12:00-23:59 UTC covers:
#   EDT entry  13:31 UTC  (gap to prev fire: 1 min)
#   EST entry  14:31 UTC  (gap to prev fire: 1 min)
#   EDT exit   19:58 UTC  (gap to prev fire: 13 min)
#   EST exit   20:58 UTC  (gap to prev fire: 13 min)
#   Forced EOD 23:00 UTC  (gap to prev fire: 0 min)
#
# Orphan position safety: handled inside EA OnInit (orphan-recovery).
# The watchdog restarts MT5; the EA closes orphan positions autonomously.
#
# Usage:
#   ~/watchdog.sh              Normal cron mode (restarts MT5 if absent)
#   ~/watchdog.sh --dry-run    Log-only mode (no restart — use for 48h coverage test)

set -euo pipefail

SCREEN_SESSION="mt5"
LOG="$HOME/watchdog.log"
DRY_RUN=false

[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# UTC timestamp — explicit -u avoids server timezone issues
ts() { date -u '+%Y-%m-%d %H:%M:%S UTC'; }

if pgrep -u "$(whoami)" -f "terminal64.exe" > /dev/null 2>&1; then
    PID=$(pgrep -u "$(whoami)" -f "terminal64.exe" | head -1)
    echo "[$(ts)] UP   terminal64.exe pid=$PID" >> "$LOG"
else
    if $DRY_RUN; then
        echo "[$(ts)] DOWN terminal64.exe absent [DRY-RUN — no restart]" >> "$LOG"
    else
        echo "[$(ts)] DOWN terminal64.exe absent — restarting MT5" >> "$LOG"

        # Kill any stale screen session
        screen -S "$SCREEN_SESSION" -X quit 2>/dev/null || true
        sleep 2

        # Start fresh detached session
        screen -dmS "$SCREEN_SESSION" "$HOME/start_voieb.sh"
        echo "[$(ts)] INFO screen session '$SCREEN_SESSION' started" >> "$LOG"

        # Verify recovery after 30s
        sleep 30
        if pgrep -u "$(whoami)" -f "terminal64.exe" > /dev/null 2>&1; then
            PID=$(pgrep -u "$(whoami)" -f "terminal64.exe" | head -1)
            echo "[$(ts)] OK   MT5 recovered (pid=$PID)" >> "$LOG"
        else
            echo "[$(ts)] ERR  MT5 still absent after restart — manual intervention needed" >> "$LOG"
        fi
    fi
fi

# Rotate log if > 10 MB
LOG_SIZE=$(stat -c%s "$LOG" 2>/dev/null || echo 0)
if [[ "$LOG_SIZE" -gt 10485760 ]]; then
    mv "$LOG" "${LOG}.1"
    echo "[$(ts)] INFO log rotated (was >10 MB)" >> "$LOG"
fi
