#!/bin/bash
# supervisor_keepalive.sh — garantit que le daemon supervisor (couche d'ALERTE)
# tourne. Cron */5. Idempotent : ne relance QUE s'il est absent.
#
# Pourquoi : le supervisor n'avait QUE @reboot pour démarrer ; sans reboot (uptime
# 60 j observé 2026-06-15) la couche d'alerte est restée morte → aucune alerte
# heartbeat le week-end où MT5 a zombifié. Le daemon lui-même fonctionne (il
# bloque correctement, persiste sous screen -dmS) — il manquait juste un re-launch
# fiable. Ce keepalive EST ce filet. (Le @reboot reste, pour un démarrage rapide.)
#
# pgrep IMMUNISÉ '[s]upervisor.py --daemon' : ne matche jamais sa propre cmdline
# ni celle de pgrep (leçon pkill/pgrep -f auto-match, cf. watchdog [t]erminal64).
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="${SUPERVISOR_KEEPALIVE_LOG:-/home/algo/logs/ftmo_supervisor_keepalive.log}"
RUN_WITH_ENV="${RUN_WITH_ENV:-/home/algo/projects/Algo_claude/scripts/run_with_env.sh}"
ts() { date -u '+%Y-%m-%d %H:%M:%S UTC'; }
log() { echo "$(ts) $*" >> "$LOG"; }

pgrep -f '[s]upervisor.py --daemon' >/dev/null 2>&1 && exit 0   # vivant : no-op

log "supervisor daemon ABSENT — relance (screen -dmS ftmo_supervisor)"
/usr/bin/screen -dmS ftmo_supervisor "$RUN_WITH_ENV" python3 "$SCRIPT_DIR/supervisor.py" --daemon
sleep 5
if pgrep -f '[s]upervisor.py --daemon' >/dev/null 2>&1; then
    log "OK — supervisor daemon relancé"
else
    log "ÉCHEC — supervisor daemon NON relancé"
    "$RUN_WITH_ENV" python3 "$SCRIPT_DIR/tg.py" \
        "🚨🚨 FTMO supervisor keepalive — daemon NON relancé (couche d'alerte DOWN) — intervention manuelle requise" \
        >> "$LOG" 2>&1 || log "TG ÉCHEC (alerte keepalive)"
fi
