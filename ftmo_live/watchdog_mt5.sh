#!/bin/bash
# watchdog_mt5.sh — relance MT5/Wine si le heartbeat EA (mtime de state.json) se
# fige ALORS QUE la session forex est ouverte.
#
# Cron */3 min via scripts/run_with_env.sh (.env → FTMO_LIVE_MT5_FILES,
# TELEGRAM_* ; venv → python3). Hors session (lib/market_hours.py = source de
# vérité UNIQUE, table UTC datée, seam DST 25/10/2026 dans la table) : exit 0
# sans rien faire — le heartbeat est STRUCTURELLEMENT muet marché fermé
# (WriteState throttlé M1 sur TimeCurrent, book_executor.mq5:1291).
#
# --force : court-circuite calendrier + seuil d'âge (test à froid marché fermé).
#
# Garde-fous :
#  - pkill motif IMMUNISÉ '[t]erminal64' — ne matche jamais sa propre cmdline
#    (leçon pkill -f auto-suicide, RUNBOOK 2026-06-13) ;
#  - anti-boucle : max 2 restarts/h (fichier compteur) → alerte CRITIQUE
#    (cooldown 1 h) et STOP ;
#  - post-restart (attente 120 s) : terminal64 vivant ET EA ré-initialisé —
#    primaire : mtime(state.json) >= T0 (l'OnInit fait WriteState(true) FORCÉ,
#    écrit même marché fermé ; un profil sans book_executor n'écrit PAS) ;
#    secondaire : nouvelle ligne « book_executor v2.2 INIT » dans
#    MQL5/logs/$(date -u +%Y%m%d).log (UTF-16LE). Échec → alerte CRITIQUE.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="${WATCHDOG_LOG:-/home/algo/logs/ftmo_watchdog.log}"
RESTARTS_F=/home/algo/logs/.ftmo_watchdog_restarts
CRIT_F=/home/algo/logs/.ftmo_watchdog_crit
START_SH=/home/algo/start_mt5.sh
STALE_S=240
WAIT_S=120
MAX_RESTARTS_H=2

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

ts() { date -u '+%Y-%m-%d %H:%M:%S UTC'; }
log() { echo "$(ts) $*" >> "$LOG"; }
tgmsg() { python3 "$SCRIPT_DIR/tg.py" "$1" >> "$LOG" 2>&1 || log "TG ÉCHEC: $1"; }

: "${FTMO_LIVE_MT5_FILES:?FTMO_LIVE_MT5_FILES manquant — lancer via run_with_env.sh}"
STATE="$FTMO_LIVE_MT5_FILES/state.json"
MT5_ROOT="$(dirname "$(dirname "$FTMO_LIVE_MT5_FILES")")"

session_open() {
    python3 - "$SCRIPT_DIR" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from datetime import datetime, timezone
from lib.market_hours import fx_session_open
sys.exit(0 if fx_session_open(datetime.now(timezone.utc)) else 1)
PY
}

init_count() {
    local d="$MT5_ROOT/MQL5/logs"
    [ -d "$d" ] || d="$MT5_ROOT/MQL5/Logs"
    local f="$d/$(date -u +%Y%m%d).log"
    [ -f "$f" ] || { echo 0; return; }
    iconv -f UTF-16LE -t UTF-8 "$f" 2>/dev/null | grep -c "book_executor v2.2 INIT"
}

state_age() { echo $(( $(date +%s) - $(stat -c %Y "$STATE" 2>/dev/null || echo 0) )); }

AGE=$(state_age)
if [ "$FORCE" -eq 0 ]; then
    session_open || exit 0                  # marché fermé : silence total
    [ "$AGE" -le "$STALE_S" ] && exit 0     # heartbeat frais : rien à faire
fi

# ---- anti-boucle : max 2 restarts par heure glissante --------------------
NOW=$(date +%s)
touch "$RESTARTS_F"
RECENT=$(awk -v n="$NOW" '$1+0 > n-3600' "$RESTARTS_F" | wc -l)
if [ "$RECENT" -ge "$MAX_RESTARTS_H" ]; then
    if [ $(( NOW - $(stat -c %Y "$CRIT_F" 2>/dev/null || echo 0) )) -gt 3600 ]; then
        touch "$CRIT_F"
        log "CRITIQUE anti-boucle: $RECENT restarts < 1 h — STOP"
        tgmsg "🚨🚨 FTMO MT5 watchdog CRITIQUE — $RECENT restarts en 1 h (anti-boucle) : STOP — intervention manuelle requise"
    fi
    exit 1
fi
echo "$NOW" >> "$RESTARTS_F"
awk -v n="$NOW" '$1+0 > n-86400' "$RESTARTS_F" > "$RESTARTS_F.tmp" \
    && mv "$RESTARTS_F.tmp" "$RESTARTS_F"

# ---- restart -------------------------------------------------------------
PRE_INIT=$(init_count)
T0=$(date +%s)
log "state.json vieux de ${AGE}s (seuil ${STALE_S}s, force=$FORCE) — restart MT5"
tgmsg "⚠️ FTMO MT5 watchdog: restart — state.json vieux de ${AGE}s en session ; screen quit + pkill [t]erminal64 + start_mt5.sh"

screen -S mt5 -X quit 2>/dev/null
sleep 2
pkill -f '[t]erminal64' 2>/dev/null
sleep 3
pkill -9 -f '[t]erminal64' 2>/dev/null
/usr/bin/screen -dmS mt5 "$START_SH"
sleep "$WAIT_S"

# ---- vérifications post-restart ------------------------------------------
ELAPSED=$(( $(date +%s) - T0 ))
if ! pgrep -f '[t]erminal64' > /dev/null 2>&1; then
    log "CRITIQUE: terminal64 ABSENT après relance (${ELAPSED}s)"
    tgmsg "🚨🚨 FTMO MT5 watchdog CRITIQUE — MT5 restart KO — EA non ré-initialisé — intervention manuelle requise (terminal64 absent après ${ELAPSED}s)"
    exit 1
fi
NEW_MTIME=$(stat -c %Y "$STATE" 2>/dev/null || echo 0)
POST_INIT=$(init_count)
if [ "$NEW_MTIME" -ge "$T0" ] || [ "$POST_INIT" -gt "$PRE_INIT" ]; then
    log "OK: MT5 relancé en ${ELAPSED}s — EA ré-initialisé (state mtime $NEW_MTIME >= T0 $T0, init ${PRE_INIT}→${POST_INIT})"
    tgmsg "✅ FTMO MT5 watchdog: MT5 relancé en ${ELAPSED}s — EA book_executor ré-initialisé (init ${PRE_INIT}→${POST_INIT})"
    exit 0
fi
log "CRITIQUE: EA non ré-initialisé (state mtime $NEW_MTIME < T0 $T0, init ${PRE_INIT}→${POST_INIT})"
tgmsg "🚨🚨 FTMO MT5 watchdog CRITIQUE — MT5 restart KO — EA non ré-initialisé — intervention manuelle requise (profil sans book_executor ? state non réécrit, init ${PRE_INIT}→${POST_INIT})"
exit 1
