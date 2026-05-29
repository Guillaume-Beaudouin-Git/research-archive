# Voie B — Déploiement VPS MT5 dédié

**Cible :** Hetzner CX22 dédié MT5 (Ubuntu 22.04), IP `<MT5_VPS_IP>`, user `mt5user`  
**EA :** `Voie_B_EA_fixed.mq5` v1.20  
**Compte :** FTMO trial (gratuit, €0 capital)  
**Statut mécanique :** 5/5 tests confirm_fixes.py ✅ — orphan recovery v1.20 ✅

---

## Architecture — VPS dédié (décision définitive)

**Décision : 2e Hetzner CX22 (~4€/mois), dédié MT5 uniquement.**

| Raison | Détail |
|--------|--------|
| MT5 + Wine + Xvfb | ~1–2 GB RAM en live |
| CX22 existant (<VPS_IP>) | crons Python TSMOM + delta-neutral actifs |
| Contention RAM | OOM-kill possible pendant position ouverte → kill-switch mort |
| Isolation opérationnelle | panne MT5 n'affecte pas les stratégies A/B |

**Résumé infrastructure :**
- `<VPS_IP>` (CX22 #1) — Python crons : TSMOM + delta-neutral + NQ paper
- `<MT5_VPS_IP>` (CX22 #2, MT5 dédié) — Voie B EA uniquement

---

## 1. Provisionner le CX22 dédié

Dans la console Hetzner Cloud :
1. Create Server → Location : Nuremberg (ou Falkenstein)
2. Image : Ubuntu 22.04
3. Type : CX22
4. SSH key : `hetzner_algo_claude` (déjà dans le compte Hetzner)
5. Nommer : `mt5-voieb`
6. Créer → noter l'IP : `<MT5_VPS_IP>`

```bash
# Connexion depuis Mac
ssh -i ~/.ssh/hetzner_algo_claude root@<MT5_VPS_IP>
```

---

## 2. Installation système (Phase 1 — root)

```bash
# Depuis Mac : copier le script de setup sur le VPS
scp -i ~/.ssh/hetzner_algo_claude \
    <HOME>/Desktop/Algo_claude/Futures/research/active/voie_b_ftmo/deploy/setup_vps_mt5.sh \
    root@<MT5_VPS_IP>:/root/

# Sur le VPS (root)
bash setup_vps_mt5.sh --system
```

Ce que fait `--system` :
- Wine staging (repo WineHQ officiel pour Ubuntu 22.04 jammy)
- `xvfb x11vnc screen fluxbox xdotool winetricks`
- Crée `mt5user` + copie `start_voieb.sh` / `watchdog.sh` dans `~mt5user/`
- Copie `authorized_keys` de root → mt5user (même clé SSH)

```bash
# Vérifier connexion mt5user
ssh -i ~/.ssh/hetzner_algo_claude mt5user@<MT5_VPS_IP>
```

---

## 3. Installation Wine + MT5 (Phase 2 — mt5user)

```bash
# Sur le VPS (mt5user)
bash ~/setup_vps_mt5.sh --user
# → copier setup_vps_mt5.sh dans ~mt5user/ si absent :
#   scp -i ~/.ssh/hetzner_algo_claude \
#       .../deploy/setup_vps_mt5.sh mt5user@<MT5_VPS_IP>:~/
```

Ce que fait `--user` :
- WINEPREFIX `~/.wine_mt5` win64, winecfg Windows 10 (registry silent)
- `winetricks -q vcrun2019 corefonts`
- Télécharge MT5 (MetaQuotes CDN) + installe en headless (`/auto`)

Durée : ~5 min.

---

## 4. Connexion compte FTMO trial via VNC

```bash
# Terminal 1 (Mac) — tunnel VNC
ssh -i ~/.ssh/hetzner_algo_claude -L 5900:localhost:5900 mt5user@<MT5_VPS_IP>

# Terminal 2 (VPS, mt5user)
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 -nolisten tcp &
sleep 1
x11vnc -display :99 -rfbport 5900 -passwd <VNC_PASS> -once -noxdamage &
wine "$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe" /portable &
```

Depuis Mac : ouvrir **Finder → Aller → Se connecter au serveur → `vnc://localhost:5900`**  
(ou `open vnc://localhost:5900` dans Terminal).

Dans MT5 GUI :
1. File → Open Account → rechercher **FTMO-Server** (ou FTMO-MT5-1)
2. Créer un compte démo/trial → noter login + password → sauvegarder dans `~/.voieb_credentials` (chmod 600)
3. Fermer MT5 : File → Exit

---

## 5. Déployer l'EA

```bash
# Depuis Mac : copier l'EA sur le VPS
MT5_DATA="$HOME/.wine_mt5/drive_c/users/mt5user/AppData/Roaming/MetaQuotes/Terminal"
# Note : le répertoire contient un hash généré par MT5 — exécuter sur VPS pour le trouver :
# ssh mt5user@<MT5_VPS_IP> "ls ~/.wine_mt5/drive_c/users/mt5user/AppData/Roaming/MetaQuotes/Terminal/"
TERMINAL_HASH=<hash>

scp -i ~/.ssh/hetzner_algo_claude \
    <HOME>/Desktop/Algo_claude/Futures/research/active/voie_b_ftmo/Voie_B_EA_fixed.mq5 \
    "mt5user@<MT5_VPS_IP>:/home/mt5user/.wine_mt5/drive_c/users/mt5user/AppData/Roaming/MetaQuotes/Terminal/$TERMINAL_HASH/MQL5/Experts/VoieB/"
```

---

## 6. Compiler l'EA (MetaEditor, 0 erreur)

Lancer MT5 via VNC (voir §4), puis dans MT5 :
1. Tools → MetaEditor (ou F4)
2. File → Open → `MQL5/Experts/VoieB/Voie_B_EA_fixed.mq5`
3. **F7** (Build) → vérifier `0 errors, 0 warnings`
4. Fermer MetaEditor

---

## 7. Attacher l'EA sur US500.cash M1

Dans MT5 :
1. Ouvrir US500.cash M1 (clic droit MarketWatch → Chart Window)
2. Navigator → Expert Advisors → Voie_B_EA_fixed → glisser sur le chart
3. Cocher "Allow live trading" + "Allow DLL imports"
4. Configurer les inputs :

| Paramètre | Valeur | Note |
|-----------|--------|------|
| Symbol_1..4 | US500.cash / US100.cash / US30.cash / US2000.cash | |
| GapThresholdBps | 15 | baseline |
| MinConfirmation | 2 | baseline |
| UseVolTarget | true | aligné Python |
| VolTargetAnnual | 0.10 | 10% vol annuelle cible |
| VolLookbackDays | 60 | |
| MaxLeverage | **3.75** | conservateur pour trial |
| BaseLeverage | 2.5 | |
| KillSwitchUnlev | -0.012 | -1.2% unlev stop |
| VerboseLog | true | activer J1–J14 |

5. Vérifier que le smiley EA passe de ⚠️ à 😊 dans le coin du chart.

---

## 8. Watchdog cron + @reboot (mt5user)

```bash
# Sur VPS (mt5user)
crontab -e
```

Ajouter :
```
# @reboot : lancer MT5 au démarrage du VPS (délai 30s pour réseau)
@reboot sleep 30 && screen -dmS mt5 ~/start_voieb.sh

# Watchdog : surveiller MT5 toutes les 15min, jours ouvrés 12h-23h59 UTC
*/15 12-23 * * 1-5 ~/watchdog.sh
```

**Mécanique orphan recovery (v1.20) :**  
Quand le watchdog redémarre MT5, `OnInit` scanne `PositionsTotal()`.  
Si une position avec `MagicNumber=20260601` existe (laissée ouverte lors du crash) :
- `CloseAllPositions("orphan-recovery")` est appelé immédiatement
- Log PrintFormat dans Experts Journal
- `g_entered_today` reste false → la journée courante est ignorée
- Une position levée sans kill-switch actif = risque max-loss -10% = bust → fermée sans délai.

---

## 9. Vérification J1 — checklist complète

Après la première session de trading (14:00–20:00 UTC est window) :

### a. Gaps non-figés (confirmation cross-instrument réelle)

```bash
# Sur VPS (mt5user)
MT5_DATA="$HOME/.wine_mt5/drive_c/users/mt5user/AppData/Roaming/MetaQuotes/Terminal"
TERMINAL=$(ls "$MT5_DATA" | head -1)
cat "$MT5_DATA/$TERMINAL/MQL5/Files/VoieB_decisions.csv" | column -t -s,
```

Vérifier : `gap_bps` pour US500/US100/US30/US2000 **non tous à 0** sur les jours avec signal.  
→ Si tous zéro : données secondaires manquantes → vérifier MarketWatch (US100.cash, US30.cash, US2000.cash actifs).

### b. Heure d'entrée DST correcte

Dans Experts Journal MT5 (ou voieb_mt5.log) :
```
ENTRY LONG US500.cash 1.00 lots (gap=22.3bp lev=2.13x fill=5042.3500 spr=0.9bp)
```
L'heure de la ligne doit être **13:31 UTC** (été EDT, UTC-4), **pas 14:31**.  
→ Fix DST confirmé en conditions réelles.

### c. CSV live correctement rempli

Si un signal a été pris, le CSV doit contenir **une ligne par symbole tradé** :
```
date_utc, symbol, direction, gap_bps, leverage, lots,
mid_signal≠0, fill_entry≠0, spread_signal_bps, ts_entry_utc,
mid_exit≠0, fill_exit≠0, ts_exit_utc, exit_reason, pnl_points, pnl_account_pct
```
`mid_signal` et `fill_entry` non-nuls = prix capturés correctement.

### d. slip_analysis.py parse sans erreur

```bash
# Depuis Mac : télécharger le CSV live
scp -i ~/.ssh/hetzner_algo_claude \
    "mt5user@<MT5_VPS_IP>:$MT5_DATA/$TERMINAL/MQL5/Files/VoieB_decisions.csv" \
    ./Futures/research/active/voie_b_ftmo/results/voieb_live_J1.csv

cd <HOME>/Desktop/Algo_claude
/usr/bin/python3 Futures/research/active/voie_b_ftmo/slip_analysis.py \
    --csv Futures/research/active/voie_b_ftmo/results/voieb_live_J1.csv
```

→ Doit afficher stats slip sans erreur Python. Verdict cible : VIABLE (≤ 3 bp).

---

## 10. Parity check (après 4–6 semaines démo)

```bash
# Télécharger le CSV live complet
scp -i ~/.ssh/hetzner_algo_claude \
    "mt5user@<MT5_VPS_IP>:$MT5_DATA/$TERMINAL/MQL5/Files/VoieB_decisions.csv" \
    ./Futures/research/active/voie_b_ftmo/results/voieb_live_decisions.csv

# Parity check direction + sizing vs Python backtest
/usr/bin/python3 -m Futures.research.active.voie_b_ftmo.parity_check \
    --mt5_csv Futures/research/active/voie_b_ftmo/results/voieb_live_decisions.csv
```

Gates :
- ≥ 95% concordance direction
- ≥ 90% concordance sizing (tolérant arrondi lot MT5)

---

## 11. Décision go/no-go challenge FTMO €99

| Critère | Source | Gate | Bloquant |
|---------|--------|------|----------|
| Direction concordance | parity_check.py | ≥ 95% | ✅ OUI |
| Sizing concordance | parity_check.py | ≥ 90% | ✅ OUI |
| Pas de crash EA (4–6 sem) | watchdog.log + Experts Journal | 0 incident non-récupéré | ✅ OUI |
| Gaps non-nuls sur 4 instruments | VoieB_decisions.csv | tous jours actifs | ✅ OUI |
| DST correct (bascule mar/nov) | décisions log autour 2026-11-01 | offset 4↔5 | ✅ OUI |
| slip_rt médian | slip_analysis.py | ≤ 5 bp (VIABLE ou MARGINAL) | ✅ OUI |
| SR démo | calcul sur decisions.csv | ≥ 0.5 annualisé | non bloquant |
| MaxDD démo | MT5 Account History | < 5% | non bloquant |

Si critères 1–6 OK → **go challenge FTMO €99**.
