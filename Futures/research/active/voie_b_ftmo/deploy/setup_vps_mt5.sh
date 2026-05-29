#!/usr/bin/env bash
# setup_vps_mt5.sh — Dedicated MT5 VPS setup (Ubuntu 22.04)
#
# USAGE:
#   Phase 1 — run as root on the fresh VPS:
#     bash setup_vps_mt5.sh --system
#
#   Phase 2 — run as mt5user after Phase 1:
#     bash setup_vps_mt5.sh --user
#
# WHAT IT DOES:
#   --system : installs Wine staging, Xvfb, x11vnc, screen, fluxbox;
#              creates mt5user; copies this repo's deploy scripts.
#   --user   : initialises Wine prefix (win64 / Windows10), installs
#              vcrun2019 + corefonts, downloads and silently installs MT5.
#
# INTERACTIVE STEPS (after script):
#   A. Connect VNC and open an FTMO trial account in MT5 GUI.
#   B. In MetaEditor: open Voie_B_EA_fixed.mq5 → F7 (compile, 0 errors).
#   C. Attach EA on US500.cash M1 with inputs from §7 of vps_deploy.md.

set -euo pipefail

MT5_USER="mt5user"
WINEPREFIX_DIR="/home/$MT5_USER/.wine_mt5"
# Official MT5 installer (MetaQuotes CDN — use FTMO's own link if they provide one)
MT5_URL="https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe"
DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"

# ────────────────────────────────────────────────────────────────────
# Phase 1 — system (run as root)
# ────────────────────────────────────────────────────────────────────
phase_system() {
    echo "=== Phase 1: system packages + mt5user ==="
    [[ "$EUID" -ne 0 ]] && { echo "ERROR: run --system as root"; exit 1; }

    # Wine staging (official WineHQ repo for Ubuntu 22.04 jammy)
    dpkg --add-architecture i386
    mkdir -pm755 /etc/apt/keyrings
    wget -qO /etc/apt/keyrings/winehq-archive.key \
        https://dl.winehq.org/wine-builds/winehq.key
    wget -qNP /etc/apt/sources.list.d/ \
        https://dl.winehq.org/wine-builds/ubuntu/dists/jammy/winehq-jammy.sources
    apt-get update -qq
    apt-get install -y --install-recommends winehq-staging

    # Display + GUI utilities
    apt-get install -y xvfb x11vnc screen fluxbox xdotool wget unzip

    # winetricks (not in apt)
    wget -qO /usr/local/bin/winetricks \
        https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
    chmod +x /usr/local/bin/winetricks

    # Dedicated user
    if ! id "$MT5_USER" &>/dev/null; then
        useradd -m -s /bin/bash "$MT5_USER"
        echo "Created user $MT5_USER"
    fi

    # Copy deploy scripts to mt5user home
    cp "$DEPLOY_DIR/start_voieb.sh" "/home/$MT5_USER/"
    cp "$DEPLOY_DIR/watchdog.sh"    "/home/$MT5_USER/"
    chmod +x "/home/$MT5_USER/start_voieb.sh" "/home/$MT5_USER/watchdog.sh"
    chown "$MT5_USER:$MT5_USER" \
        "/home/$MT5_USER/start_voieb.sh" \
        "/home/$MT5_USER/watchdog.sh"

    # SSH: copy authorized_keys from root to mt5user if present
    if [[ -f /root/.ssh/authorized_keys ]]; then
        mkdir -p "/home/$MT5_USER/.ssh"
        cp /root/.ssh/authorized_keys "/home/$MT5_USER/.ssh/"
        chown -R "$MT5_USER:$MT5_USER" "/home/$MT5_USER/.ssh"
        chmod 700 "/home/$MT5_USER/.ssh"
        chmod 600 "/home/$MT5_USER/.ssh/authorized_keys"
    fi

    echo "=== Phase 1 done. Run as $MT5_USER: bash setup_vps_mt5.sh --user ==="
}

# ────────────────────────────────────────────────────────────────────
# Phase 2 — Wine + MT5 (run as mt5user)
# ────────────────────────────────────────────────────────────────────
phase_user() {
    echo "=== Phase 2: Wine prefix + MT5 install ==="
    [[ "$(whoami)" != "$MT5_USER" ]] && { echo "ERROR: run --user as $MT5_USER"; exit 1; }

    export WINEPREFIX="$WINEPREFIX_DIR"
    export WINEARCH=win64
    export WINEDEBUG=-all   # suppress debug noise

    # 2a. Initialise Wine prefix (win64)
    echo "--- Initialising Wine prefix (win64) ---"
    xvfb-run -a wineboot --init
    # Set Windows version to 10 (registry key, avoids winecfg GUI)
    WINEPREFIX="$WINEPREFIX_DIR" wine reg add \
        "HKCU\\Software\\Wine" /v "Version" /t REG_SZ /d "win10" /f 2>/dev/null || true

    # 2b. Windows runtime + fonts
    echo "--- Installing vcrun2019 + corefonts via winetricks ---"
    xvfb-run -a winetricks -q vcrun2019 corefonts

    # 2c. Download MT5 installer
    echo "--- Downloading MT5 installer ---"
    wget -q --show-progress -O "$HOME/mt5setup.exe" "$MT5_URL"

    # 2d. Silent install
    echo "--- Installing MT5 silently (this takes ~60s) ---"
    xvfb-run -a wine "$HOME/mt5setup.exe" /auto
    sleep 5
    wineserver -k 2>/dev/null || true

    # 2e. Copy EA to Experts folder
    # MT5 data dir: find active terminal instance
    MT5_DATA="$WINEPREFIX_DIR/drive_c/users/$MT5_USER/AppData/Roaming/MetaQuotes/Terminal"
    if [[ -d "$MT5_DATA" ]]; then
        TERMINAL=$(ls "$MT5_DATA" | head -1)
        EXPERTS="$MT5_DATA/$TERMINAL/MQL5/Experts/VoieB"
        mkdir -p "$EXPERTS"
        echo "EA target: $EXPERTS"
        echo "(Copy Voie_B_EA_fixed.mq5 here manually or via scp after this step)"
    else
        echo "WARN: MT5 data dir not found yet — copy EA after first MT5 launch"
    fi

    echo "=== Phase 2 done. Next steps ==="
    echo "  1. ~/start_voieb.sh  — launch MT5 (runs via screen in start_voieb.sh)"
    echo "  2. Set up VNC tunnel: ssh -L 5900:localhost:5900 mt5user@<VPS_IP>"
    echo "     Then: x11vnc -display :99 -rfbport 5900 -passwd <VNC_PASS> -once"
    echo "  3. In MT5 GUI: File → Open Account → FTMO → create trial account"
    echo "  4. MetaEditor: open EA → F7 → 0 errors → attach on US500.cash M1"
    echo "  5. crontab -e — add lines from vps_deploy.md §10"
}

# ────────────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────────────
case "${1:-}" in
    --system) phase_system ;;
    --user)   phase_user   ;;
    *)
        echo "Usage: $0 --system  (as root)"
        echo "       $0 --user    (as $MT5_USER)"
        exit 1
        ;;
esac
