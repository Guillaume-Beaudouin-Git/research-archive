#!/bin/bash
# watchdog_mt5.sh — relance MT5/Wine si le lien MT5↔broker est RÉELLEMENT rompu
# alors que la session forex est ouverte.
#
# Le heartbeat EA (mtime de state.json) FIGÉ ne suffit PLUS à déclencher un restart :
# le tick se tarit ~5 min au rollover serveur (00:00 EEST = 21:00 UTC) et dans les
# creux nocturnes ALORS QUE MT5 est sain et se reconnecte seul (journal "connection
# lost"→"authorized" ~50 s). On distingue donc, heartbeat gelé en session :
#   - terminal vivant ET connecté au broker (socket :443 établi) → trou de ticks
#     normal → PAS de restart ;
#   - process mort (DEAD) OU plus aucun socket courtier (DISCONNECTED) → vraie panne
#     → restart.
# Source de "connecté", la plus fiable au-dessus du heartbeat : socket TCP courtier
# TEMPS RÉEL (l'EA n'expose aucun flag TERMINAL_CONNECTED ; le journal est
# évènementiel/périmable, gardé en corroboration). cf. WATCHDOG_INCIDENT.
#
# Cron */3 min via scripts/run_with_env.sh (.env → FTMO_LIVE_MT5_FILES,
# TELEGRAM_* ; venv → python3). Hors session (lib/market_hours.py = source de
# vérité UNIQUE, table UTC datée, seam DST 25/10/2026 dans la table) : exit 0
# sans rien faire — le heartbeat est STRUCTURELLEMENT muet marché fermé
# (WriteState throttlé M1 sur TimeCurrent, book_executor.mq5:1291).
#
# --force : court-circuite calendrier + seuil d'âge + check de connexion (restart
#   inconditionnel — test à froid). --check : dry-run, imprime session/âge/lien/verdict
#   SANS jamais agir (vérification sûre, compte armé). Surcharges test (env) :
#   FTMO_WATCHDOG_STALE_S, FTMO_WATCHDOG_GRACE_S, FTMO_WATCHDOG_LOCK.
#   ⚠ --force SAUTE session_state ET link_state — ne teste donc PAS ces chemins
#   (pour les exercer : kill no-force en session, ou --check).
#
# Garde-fous :
#  - heartbeat-DU-watchdog (beat → $ALIVE_F) écrit à chaque run : le supervisor
#    alerte si périmé en session (le superviseur surveille le gardien) ;
#  - session_state renvoie 0/1/2 : une ERREUR INTERNE (rc=2 : venv/chemin/import)
#    n'est JAMAIS confondue avec « marché fermé » → Telegram BRUYANT + fail-safe
#    OUVERT (un garde ne meurt pas en silence) ;
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
ALIVE_F="${FTMO_WATCHDOG_ALIVE:-/home/algo/logs/watchdog_alive}"
RESTARTS_F=/home/algo/logs/.ftmo_watchdog_restarts
CRIT_F=/home/algo/logs/.ftmo_watchdog_crit
ERR_F=/home/algo/logs/.ftmo_watchdog_err
START_SH=/home/algo/start_mt5.sh
STALE_S="${FTMO_WATCHDOG_STALE_S:-240}"      # surchargeable (tests / nuit creuse)
WAIT_S=120
MAX_RESTARTS_H=2
GRACE_S="${FTMO_WATCHDOG_GRACE_S:-60}"       # ré-poll socket : absorbe le blip de
                                             # reconnexion rollover (~49 s observé)
LOCKF="${FTMO_WATCHDOG_LOCK:-/home/algo/logs/.ftmo_watchdog.lock}"
PID_PAT='[t]erminal64'                       # motif immunisé (jamais sa propre cmdline)

FORCE=0; MODE=run
case "${1:-}" in
    --force) FORCE=1 ;;                      # restart inconditionnel (test à froid)
    --check) MODE=check ;;                   # dry-run : diagnostique, n'agit jamais
esac

ts() { date -u '+%Y-%m-%d %H:%M:%S UTC'; }
log() { echo "$(ts) $*" >> "$LOG"; }
tgmsg() { python3 "$SCRIPT_DIR/tg.py" "$1" >> "$LOG" 2>&1 || log "TG ÉCHEC: $1"; }

# heartbeat-DU-watchdog : timestamp réécrit à CHAQUE run utile (après validation
# de l'env), même marché fermé. Le supervisor alerte si ce fichier est périmé EN
# SESSION (méta-surveillance : le superviseur surveille le gardien). Volontairement
# APRÈS le check FTMO_LIVE_MT5_FILES : un watchdog mal configuré laisse son
# heartbeat se périmer (→ alerte) au lieu d'écrire un battement trompeur.
beat() { echo "$(date -u '+%s %Y-%m-%dT%H:%M:%SZ') $*" > "$ALIVE_F" 2>/dev/null \
    || log "ALIVE write KO: $ALIVE_F"; }

# Un garde ne meurt jamais en silence : toute erreur interne (import/venv/chemin
# du check de session…) → Telegram BRUYANT, cooldown 1 h (anti-spam) + log.
err_internal() {
    log "ERREUR INTERNE: $*"
    if [ $(( $(date +%s) - $(stat -c %Y "$ERR_F" 2>/dev/null || echo 0) )) -gt 3600 ]; then
        touch "$ERR_F"
        tgmsg "🚨🚨 FTMO MT5 watchdog — ERREUR INTERNE — garde inopérant : $*"
    fi
}

: "${FTMO_LIVE_MT5_FILES:?FTMO_LIVE_MT5_FILES manquant — lancer via run_with_env.sh}"
STATE="$FTMO_LIVE_MT5_FILES/state.json"
MT5_ROOT="$(dirname "$(dirname "$FTMO_LIVE_MT5_FILES")")"

# 0 = session OUVERTE, 1 = FERMÉE, 2 = ERREUR INTERNE (trace sur stderr → log).
# market_hours.fx_session_open = SOURCE DE VÉRITÉ unique (identique au supervisor).
session_state() {
    python3 - "$SCRIPT_DIR" <<'PY'
import sys, traceback
sys.path.insert(0, sys.argv[1])
try:
    from datetime import datetime, timezone
    from lib.market_hours import fx_session_open
    rc = 0 if fx_session_open(datetime.now(timezone.utc)) else 1
except Exception:
    traceback.print_exc()
    rc = 2
sys.exit(rc)
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

# --- état du lien MT5 ↔ broker (pour ne PAS confondre « trou de ticks » et panne) ---
# L'EA n'expose AUCUN flag TERMINAL_CONNECTED dans state.json (schéma vérifié) ; le
# journal terminal est ÉVÈNEMENTIEL (peut être périmé). Signal le PLUS fiable, TEMPS
# RÉEL : le socket TCP courtier (terminal64 → access server :443). Le journal sert de
# corroboration loggée. (cf. WATCHDOG_INCIDENT — rollover serveur 21:00 UTC.)

# Socket courtier ÉTABLI du pid donné (remote :443 non-loopback) → imprime le peer, rc 0.
broker_socket_up() {
    local pid="$1"
    [ -n "$pid" ] || return 1
    ss -tnp 2>/dev/null | awk -v p="$pid" '
        $1=="ESTAB" && $0 ~ ("pid=" p "[,)]") {
            peer=$5
            if (peer ~ /:443$/ && peer !~ /^127\./ && peer !~ /^\[::1\]/) { print peer; f=1 }
        }
        END { exit (f ? 0 : 1) }'
}

# Dernier évènement réseau du journal terminal (UTF-16LE) : conn | lost | unknown.
journal_link() {
    local d f
    d="$MT5_ROOT/logs"; [ -d "$d" ] || d="$MT5_ROOT/Logs"
    f="$d/$(date -u +%Y%m%d).log"
    [ -f "$f" ] || { echo unknown; return; }
    iconv -f UTF-16LE -t UTF-8 "$f" 2>/dev/null | awk '
        /Network/ && /authorized/                            { st="conn" }
        /Network/ && (/connection.*lost/ || /no connection/) { st="lost" }
        END { print (st=="" ? "unknown" : st) }'
}

# Imprime "VERDICT\tdiag" — VERDICT ∈ {DEAD, DISCONNECTED, CONNECTED}.
# Un blip de reconnexion (rollover) est absorbé par un ré-poll du socket ≤ GRACE_S
# avant de conclure DISCONNECTED (le socket est rétabli ~50 s après la perte).
link_state() {
    local pid jl peer waited=0
    pid=$(pgrep -f "$PID_PAT" | head -1)
    jl=$(journal_link)
    if [ -z "$pid" ]; then
        printf 'DEAD\tprocess terminal64 ABSENT ; journal=%s' "$jl"; return
    fi
    if peer=$(broker_socket_up "$pid"); then
        printf 'CONNECTED\tpid=%s socket=%s ; journal=%s' "$pid" "$peer" "$jl"; return
    fi
    while [ "$waited" -lt "$GRACE_S" ]; do
        sleep 5; waited=$((waited+5))
        if peer=$(broker_socket_up "$pid"); then
            printf 'CONNECTED\tpid=%s socket=%s (reconnecté après %ss) ; journal=%s' \
                   "$pid" "$peer" "$waited" "$jl"; return
        fi
    done
    printf 'DISCONNECTED\tpid=%s AUCUN socket courtier :443 après %ss ; journal=%s' \
           "$pid" "$GRACE_S" "$jl"; return
}

AGE=$(state_age)
beat "run age=${AGE}s force=$FORCE mode=$MODE"   # preuve de vie du watchdog (chaque run)

# --- --check : diagnostic pur, n'agit JAMAIS (ni session ni socket modifiés) -----
if [ "$MODE" = check ]; then
    session_state; SS=$?
    LR=$(link_state); LINK=${LR%%$'\t'*}; LDIAG=${LR#*$'\t'}
    case "$SS" in 0) sess=OUVERTE ;; 1) sess=FERMÉE ;; *) sess=ERREUR ;; esac
    verdict=NO-RESTART
    if [ "$SS" = 0 ] && [ "$AGE" -gt "$STALE_S" ] \
       && { [ "$LINK" = DEAD ] || [ "$LINK" = DISCONNECTED ]; }; then verdict=RESTART; fi
    echo "session=$sess(rc=$SS) age=${AGE}s/seuil=${STALE_S}s link=$LINK [$LDIAG] -> $verdict"
    exit 0
fi

# Verrou : grace + WAIT_S peuvent dépasser l'intervalle cron */3 — jamais 2 runs en
# parallèle (sinon double kill/restart). FAIL-OPEN : un verrou indisponible NE doit
# JAMAIS désactiver le garde — on ne saute QUE sur contention réelle (fd ouvert + pris).
exec 9>"$LOCKF" 2>/dev/null || true
if ! flock -n 9 2>/dev/null; then
    if { : >&9; } 2>/dev/null; then
        log "run concurrent ignoré (verrou $LOCKF détenu)"; exit 0   # fd OK → vraie contention
    fi
    log "verrou $LOCKF indisponible — poursuite SANS verrou (fail-open)"  # fd KO → on poursuit
fi

if [ "$FORCE" -eq 0 ]; then
    session_state; SS=$?
    case "$SS" in
        1) exit 0 ;;                         # marché fermé : no-op silencieux (normal)
        0) : ;;                              # marché ouvert : on poursuit
        *) err_internal "check de session rc=$SS (venv/chemin/market_hours) — FAIL-SAFE: marché supposé OUVERT" ;;
    esac
    [ "$AGE" -le "$STALE_S" ] && exit 0     # heartbeat frais : rien à faire

    # Heartbeat GELÉ en session : NE PAS conclure « MT5 mort » sur ce seul critère.
    # Le tick se tarit ~5 min au rollover serveur (00:00 EEST = 21:00 UTC) et dans les
    # creux nocturnes ALORS QUE MT5 est sain et se reconnecte seul (cf. WATCHDOG_INCIDENT,
    # journal "connection lost"→"authorized" ~50 s). On NE redémarre QUE si le lien broker
    # est réellement rompu : process mort (DEAD) OU plus de socket courtier (DISCONNECTED).
    LR=$(link_state); LINK=${LR%%$'\t'*}; LDIAG=${LR#*$'\t'}
    case "$LINK" in
        CONNECTED)
            log "heartbeat gelé ${AGE}s (seuil ${STALE_S}s) MAIS terminal vivant ET connecté [$LDIAG] — trou de ticks normal (rollover/creux) — PAS de restart"
            beat "stale ${AGE}s connecté no-restart"
            exit 0 ;;
        DEAD|DISCONNECTED)
            log "heartbeat gelé ${AGE}s ET lien $LINK [$LDIAG] — vraie panne — restart" ;;
        *)
            err_internal "link_state indéterminé ($LINK) [$LDIAG] — FAIL-SAFE: restart" ;;
    esac
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
