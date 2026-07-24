#!/bin/bash
# start_mt5.sh — lanceur MT5 (wine) pour le book FTMO.
#
# ⚠️  NON DÉPLOYÉ (2026-07-24). La version ACTIVE sur le VPS est l'historique
#     (/home/algo/start_mt5.sh). Ce fichier est versionné pour sortir un script de
#     PRODUCTION du seul disque du VPS, et pour préparer le multi-comptes — il ne
#     doit PAS être copié sans la validation à froid décrite en bas.
#
# VERSIONNÉ le 2026-07-24 (audit desk). Corrections vs la version VPS :
#
#  1. KILL SCOPÉ (prérequis multi-comptes). `pkill -9 -f terminal64` tuait TOUS les
#     terminaux : redémarrer le compte A tuait le terminal du compte B. Wine expose
#     la cmdline en `C:\...\terminal64.exe` (sans WINEPREFIX) -> on scope par
#     l'ENVIRONNEMENT du process (/proc/PID/environ).
#     ⚠️ FAIL-CLOSED : environ illisible/vide (cas d'un process ZOMBIE, précisément
#     la cible du watchdog) -> on tue quand même. Un scoping fail-open laisserait
#     survivre le zombie et rendrait MT5 non relançable = compte non protégé.
#  2. MOTIFS BRACKETÉS ([t]erminal64) — règle maison née de l'incident « pkill
#     auto-suicide » du 2026-06-12, que le script VPS viole encore.
#  3. Variables dédiées MT5_* : ne PAS hériter d'un DISPLAY ambiant (un opérateur en
#     `ssh -X` a DISPLAY=localhost:10.0 -> le script lancerait tout sur le mauvais
#     display et ne tuerait rien de l'instance réelle).
#
# `wait` FINAL OBLIGATOIRE (ligne finale) : le script est lancé par
# `screen -dmS mt5 "$START_SH"`. Sans `wait` il rend la main, la fenêtre screen se
# ferme, et screen envoie SIGHUP au groupe de processus (Xvfb/fluxbox/x11vnc/wine)
# -> MT5 meurt quelques secondes après la relance et le watchdog échoue.
# (Omis par erreur dans la 1re version de ce fichier, rattrapé par l'audit indépendant.)
set -u

MT5_WINEPREFIX="${MT5_WINEPREFIX:-$HOME/.wine}"
MT5_DISPLAY="${MT5_DISPLAY:-:1}"
VNC_PORT="${VNC_PORT:-5900}"
VNC_PASS="${VNC_PASS:?VNC_PASS requis (voir .env) — jamais en dur dans git}"
MT5_EXE="${MT5_EXE:-$MT5_WINEPREFIX/drive_c/Program Files/FTMO Global Markets MT5 Terminal/terminal64.exe}"

export WINEPREFIX="$MT5_WINEPREFIX"
export DISPLAY="$MT5_DISPLAY"
export WINEARCH=win64

# --- kill scopé, FAIL-CLOSED ---------------------------------------------------
# $1 = motif bracketé, $2 = variable d'env discriminante, $3 = valeur attendue.
# Tue si la valeur correspond OU si elle est indéterminable (zombie / environ
# illisible) : on ne laisse jamais survivre un process qu'on n'a pas pu innocenter.
kill_scoped() {
    local pat="$1" var="$2" want="$3" pid val
    for pid in $(pgrep -f "$pat" 2>/dev/null); do
        val=$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null \
              | grep "^${var}=" | head -1 | cut -d= -f2-)
        if [ -z "$val" ] || [ "$val" = "$want" ]; then
            kill -9 "$pid" 2>/dev/null
        fi
    done
}

kill_scoped '[t]erminal64' WINEPREFIX "$MT5_WINEPREFIX"
kill_scoped '[x]11vnc'     DISPLAY    "$MT5_DISPLAY"
kill_scoped '[f]luxbox'    DISPLAY    "$MT5_DISPLAY"
# Xvfb porte le display en ARGUMENT (pas en env) : le motif est déjà discriminant.
pkill -9 -f "[X]vfb ${MT5_DISPLAY}" 2>/dev/null
sleep 2

# --- écran virtuel ------------------------------------------------------------
Xvfb "$MT5_DISPLAY" -screen 0 1280x800x24 &
sleep 2
fluxbox &
sleep 2

# --- VNC (mot de passe requis pour les clients macOS ; bind localhost) --------
x11vnc -display "$MT5_DISPLAY" -bg -rfbport "$VNC_PORT" -localhost -xkb -forever \
       -noxdamage -passwd "$VNC_PASS"

# --- MT5 ----------------------------------------------------------------------
sleep 2
wine "$MT5_EXE" &

# OBLIGATOIRE — garde la session screen vivante (cf. en-tête).
wait

# ── VALIDATION À FROID REQUISE AVANT TOUT DÉPLOIEMENT ─────────────────────────
# Marché fermé, compte flat :
#   1. déposer .env avec VNC_PASS, copier ce script
#   2. bash scripts/run_with_env.sh bash ftmo_live/watchdog_mt5.sh --force
#   3. à +120 s vérifier LES DEUX :  pgrep -f '[t]erminal64'   (MT5 vivant)
#                                    screen -ls | grep mt5     (session vivante)
#   4. vérifier l'INIT de l'EA dans state.json (heartbeat qui avance)
# NB multi-comptes : ce script ne suffit PAS. watchdog_mt5.sh fait encore deux
# `pkill -f '[t]erminal64'` NON scopés et un `pgrep | head -1` — à scoper aussi,
# sinon le watchdog tuera l'autre compte malgré ce fichier.
