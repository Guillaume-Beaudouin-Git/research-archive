# RUNBOOK — burn-in compte SWING $10k (build 2026-06-11)

Baseline gelée 1947163 (chaîne yaml `56fbdde7…` / mqh `2fc65503…`). EA v1.01.

## Déjà fait (session build 2026-06-11)

| Étape | Preuve |
|---|---|
| Chaîne spec régénérée ×2 byte-identique (ancre #20) | mqh sha `2fc65503ef666d52…`, sha256 fichier = `56fbdde78a2e…` |
| mqh placé à côté de l'EA | `ftmo_live/mt5/spec_v22.mqh` |
| Compilation MetaEditor (wine, VPS) | **0 errors, 0 warnings**, `mt5/build_2026-06-11.log` |
| `.ex5` déployé | VPS `…/MQL5/Experts/ftmo_live/book_executor.ex5` sha `3670906b1f7e…` (= copie repo `mt5/book_executor.ex5`) |
| `spec_v22.sha256` déposé | VPS `…/MQL5/Files/spec_v22.sha256` = `56fbdde7…` |
| Fix runtime tick_value=0 (lu serveur Swing 2026-06-11, 4/4 symboles) | `UsdPerUnitFallback()` = contract_size × 10^-digits **devise de cote → USD** (sémantique `measured_specs.swap_type` du yaml, même arithmétique que la validation swap : JPY ÷px, GER40 ×EURUSD) ; diag `UPU …` à l'init ; `ArmAssertUPU` à 17:35 / 22:05 / funded-ORB — aucun risque dimensionné si UPU≤0 |
| Specs live vs bornes (v2.2.1) | déjà câblé : `ReadLiveSpecs()` lit SWAP_LONG/SHORT + ROLLOVER3DAYS + OrderCalcMargin à l'init + 22:05 + 21:45, bornes datées ±25 % (mqh) |

## margin_rate_live — lecture serveur Swing FTMO 2026-06-11 (gate marge RÉSOLU)

| Symbole | Lu (levier implicite) | Ancre Swing mqh | Verdict |
|---|---|---|---|
| USDJPY | 3.33 % (1:30) | 3.33 % | ✓ |
| US100 | 6.67 % (1:15) | 6.67 % | ✓ |
| GER40 | 7.2 % (~1:15, EUR→USD) | 6.67 % | ✓ (±25 %) |
| XAUUSD | **6.30 % (1:16)** | 11.11 % (1:9) | **hors borne ±25 % des DEUX ancres → `spec_bounds_breach=1` ATTENDUE** |

Monde Swing officiel confirmé (PAS Standard). L'or réel ≈ 57 % de la marge supposée →
container arm A **conservateur**, p(pass) réel ≥ 71.4. **NE PAS re-fit** (v222_swing_fit
pré-enregistré = NULL, arm A reste) ; le clip dynamique + l'enforcement au taux
`OrderCalcMargin` LIVE absorbent l'écart. L'alerte XAUUSD marge dans state.json est
**informative, non bloquante** — ne pas retoucher les bornes (yaml gelé).

## Étapes restantes — manuelles (ordre strict)

1. **Compte SWING $10k** : free trial Swing ou challenge payé (le serveur du trial lu le
   2026-06-11 est déjà le monde Swing). Récupérer login/password/serveur.
2. **Login MT5 (VNC)** :
   `ssh -i ~/.ssh/hetzner_algo_claude -L 5900:localhost:5900 algo@<VPS_IP>`
   → client VNC sur `localhost:5900` (mdp dans `~/start_mt5.sh` du VPS) →
   File → Login to Trade Account (compte Swing).
   **Lire le nom du serveur** au Journal (`authorized on FTMO-…`) et le noter ici :
   `server = ________` ; vérification côté shell :
   `iconv -f UTF-16LE -t UTF-8 "…/FTMO Global Markets MT5 Terminal/logs/$(date +%Y%m%d).log" | grep -i authoriz`
3. **Attacher l'EA** (graphique quelconque, ex. US100.cash M5) — AutoTrading ON :
   - `InpPhase=1`
   - `InpAttemptStart=<date d'ARMEMENT 00:00>` (ancre pace — re-saisir si l'armement glisse)
   - `InpServerTZOffsetMin=60` (FTMO=EET=CET+1 constant) — **à CONFIRMER sur CE serveur** :
     dans `state.json`, `ts_server − ts_paris` doit faire **exactement +60 min** ; sinon
     corriger l'input (jamais les constantes).
   - Symboles : défauts mqh (`US100.cash`, `GER40.cash`, `XAUUSD`, `USDJPY`) — vérifier le
     Market Watch du compte Swing, ajuster les inputs si suffixes différents.
   - Attendu au log Experts : `SPEC OK v2.2.1 sha 56fbdde78a2e…` ; 4 lignes `UPU <sym>: …
     (live|FALLBACK)` toutes avec `usd_per_unit>0` ; `book_executor v2.2 INIT — phase 1…`.
     `INIT REFUSÉ` = spec_v22.sha256 absent/différent → STOP.
4. **Soir 1 = OBSERVATION (sans armer)** : le kill-file `MQL5/Files/FLAT` est PRÉ-DÉPOSÉ →
   l'EA tourne désarmé (`kill=1`), zéro ordre. Vérifier :
   - `state.json` : heartbeat M1 (`heartbeat_epoch` avance), `kill=1`, `live_specs` remplis,
     `spec_bounds_breach=1` avec détail XAUUSD marge (ATTENDU, cf. supra) ;
   - supervisor daemon : alertes TG si heartbeat perdu ;
   - les 2 rapports Telegram : 08:30 (morning) + 22:20 (evening).
   NB : FLAT bloque aussi l'export 21:45 → ce soir-là `brain.py` 21:50 alerte « export
   manquant/stale » = ATTENDU (preuve que la chaîne d'alerte marche). La chaîne complète
   export→brain→targets→rebalance ne se valide qu'armé.
5. **ARMER** : `rm "…/MQL5/Files/FLAT"` avant 15:30 Paris (journée pleine) ; vérifier
   `InpAttemptStart` = date du jour d'armement. Premiers événements : 21:45 export →
   21:50 brain (targets.json, `ea_spec_sha256` = `56fbdde7…`) → 22:05 rebalance (fills
   XAUUSD/USDJPY ; lun+mar : +US100 22:05, GER40 17:35) ; micro-ORB dès le prochain jour
   OFF (mer-ven) 16:00.
6. **Noter `margin_rate_live`** (state.json / market_export.json) dans ce runbook au premier
   soir armé — gate burn-in README §Burn-in (validé pour le monde lu le 2026-06-11, à
   re-confirmer sur le compte définitif).
7. **Gates burn-in** : inchangés (`ftmo_live/README.md` §Burn-in) — cycle hebdo complet,
   Δ inexpliqué 0/3, swaps ±20 %/nuit, zéro invariant violé, zéro heartbeat >15 min,
   2 rapports corrects. Puis bascule challenge = changement de login + ré-attach
   (`InpAttemptStart` = jour 1).

## Infra VPS posée par la session (2026-06-11)

- `.env` : `FTMO_LIVE_MT5_FILES="/home/algo/.wine/drive_c/Program Files/FTMO Global Markets
  MT5 Terminal/MQL5/Files"` (terminal PORTABLE — data dir = Program Files).
- venv : `pyyaml` installé (`~/venv`).
- Fichiers untracked requis par brain/reconcile copiés :
  `data/ftmo_portfolio/cache/{panel_px,panel_rets,panel_swapL,panel_swapS,panel_mult,
  orb_e7_Rera,orb_e7_R15}.parquet`, `data/ftmo_portfolio/audit_v2_independent/cleanroom/`,
  `PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet`.
- Crons (fin de crontab, `CRON_TZ=Europe/Paris` en DERNIER bloc pour ne pas re-fuseauter
  les jobs existants ; `python3` nu = venv via `run_with_env.sh`, PAS `/usr/bin/python3`
  — le README §4 prédate ce point) :
  ```cron
  CRON_TZ=Europe/Paris
  50 21 * * 1-5  /home/algo/projects/Algo_claude/scripts/run_with_env.sh python3 /home/algo/projects/Algo_claude/ftmo_live/brain.py >> /home/algo/logs/ftmo_brain.log 2>&1
  0  23 * * 1-5  /home/algo/projects/Algo_claude/scripts/run_with_env.sh python3 /home/algo/projects/Algo_claude/ftmo_live/reconcile.py >> /home/algo/logs/ftmo_reconcile.log 2>&1
  30 8  * * *    /home/algo/projects/Algo_claude/scripts/run_with_env.sh python3 /home/algo/projects/Algo_claude/ftmo_live/supervisor.py --report morning >> /home/algo/logs/ftmo_supervisor.log 2>&1
  20 22 * * *    /home/algo/projects/Algo_claude/scripts/run_with_env.sh python3 /home/algo/projects/Algo_claude/ftmo_live/supervisor.py --report evening >> /home/algo/logs/ftmo_supervisor.log 2>&1
  @reboot sleep 60 && /usr/bin/screen -dmS ftmo_supervisor /home/algo/projects/Algo_claude/scripts/run_with_env.sh python3 /home/algo/projects/Algo_claude/ftmo_live/supervisor.py --daemon
  ```
- Supervisor daemon démarré : `screen -dmS ftmo_supervisor … supervisor.py --daemon`.
- Kill-file observation : `touch "…/MQL5/Files/FLAT"`.

### Crons — note fuseau 2026-06-12 (le bloc `CRON_TZ` ci-dessus est PÉRIMÉ)

Le cron du VPS est vixie (paquet Ubuntu `cron` 3.0pl1) : **`CRON_TZ` est IGNORÉ** —
traité comme simple variable d'env exportée aux jobs, jamais comme re-fuseautage.
La crontab réelle est donc écrite en **UTC** (TZ système du VPS) :
brain `50 19`, reconcile `0 21`, morning `30 6`, evening `20 20`
(= 21:50 / 23:00 / 08:30 / 22:20 Paris en heure d'été).

**Seam DST 25/10/2026** (fin de l'heure d'été en Europe, Paris passe à UTC+1) :
décaler les **4 lignes ftmo de +1 h UTC** — brain `50 20`, reconcile `0 22`,
morning `30 7`, evening `20 21` — pour conserver les horaires Paris.
La ligne `@reboot` n'est pas concernée. Snapshot de référence :
`infra/crontab_vps_2026-06-12.txt` (capture `crontab -l`, aucun secret inline).

### Leçons exploitation 2026-06-13 (nuit du 12 au 13)

**Heartbeat : silences structurels (calendrier).** Toutes les horloges Paris de
l'EA dérivent de `TimeCurrent()` (mq5:129) = heure du dernier tick du Market
Watch ; `WriteState` est throttlé M1 dessus (mq5:1291) et il n'existe AUCUN
`OnTick`. state.json se FIGE donc dès que plus rien ne tick : du vendredi
~20:55 UTC été (dernier tick USDJPY 23:54:59 serveur, observé 2026-06-12
20:54:59.551 UTC) à la reprise dimanche ~21:55 UTC — plus fériés de place.
Lun-jeu : ticks FX en continu la nuit (observé 02:11 serveur). Les écritures
FORCÉES (OnInit, SetError, fills, `WriteState(true)`) passent même marché
fermé — un EA qui se (re)charge écrit state.json : c'est le critère de vie du
watchdog. Conséquence : toute alerte de fraîcheur est gatée par
`lib/market_hours.py` (fenêtre conservatrice dim 22:05 → ven 20:50 UTC été,
+1 h au seam DST 25/10/2026, table datée à étendre avant 2027-03-28).

**Vendredi : EOD 22:58 structurellement impossible.** `hm=ParisHM()`
(tick-clock) gèle à 22:54 Paris < 2258 → `Do2145Export` (21:45) passe, mais
`Do2258EOD` (m5_today.json + bloc eod du state) ne tire JAMAIS le vendredi —
armé ou pas (FLAT bloque en plus avant la grille, mq5:1475-1486). Le reconcile
du vendredi 23:00 Paris (`RuntimeError: snapshot EOD 22:58 absent`) échouera
TOUS les vendredis tant que l'EA reste gelé. Correctif possible côté Python
uniquement (tolérance vendredi dans reconcile.py) — PROPOSÉ, non appliqué.

**pkill -f auto-suicide (motifs immunisés).** `pkill -f <motif>` matche la
cmdline de TOUT processus — y compris le shell appelant si le motif y figure
EN CLAIR (ssh `bash -c`, labels echo, messages TG). Immuniser l'argument de
pkill (`[t]erminal64`) ne suffit pas : aucune occurrence en clair ne doit
exister dans la cmdline appelante — le banc de test du 12/06 23:55 UTC a tué
sa propre session ssh via un simple label `echo "kill -9 terminal64"`. Règle :
motif bracketé PARTOUT + labels assainis (« t64 »).

**Profil MT5 écrit seulement à la sortie propre.** Après un kill -9, MT5
recharge le dernier profil SAUVÉ (sortie propre antérieure) — potentiellement
obsolète : EA absent/étranger (observé 2026-06-12 ~23:25 UTC). Test de survie
OBLIGATOIRE après tout re-attach : kill -9 + relance + vérifier l'INIT
book_executor (state.json réécrit / ligne INIT au log). Le watchdog vérifie
exactement cela à chaque relance (CRITIQUE « restart KO » sinon).

**Watchdog MT5** : `ftmo_live/watchdog_mt5.sh`, cron `*/3` (UTC), market-aware,
anti-boucle 2 restarts/h, vérif post-restart 120 s (mtime state ≥ T0 OU ligne
INIT fraîche MQL5/logs UTF-16LE). Test réel 12/06 23:55 UTC marché fermé :
résurrection 125 s, EA INIT à T0+24 s, TG ⚠️/✅ reçus. Snapshot crontab à
jour : `infra/crontab_vps_2026-06-13.txt`.

## Recompilation future

Chemin SANS espaces obligatoire (le quoting wine casse sur « Program Files ») :
```bash
cp ftmo_live/mt5/{book_executor.mq5,spec_v22.mqh} → ~/.wine/drive_c/build/   # (scp)
ssh … 'export WINEPREFIX=$HOME/.wine DISPLAY=:1 WINEDEBUG=-all; \
  cd "/home/algo/.wine/drive_c/Program Files/FTMO Global Markets MT5 Terminal" && \
  wine ./MetaEditor64.exe /compile:C:\\build\\book_executor.mq5 /log'
iconv -f UTF-16LE -t UTF-8 ~/.wine/drive_c/build/book_executor.log   # 0 errors attendu
cp ~/.wine/drive_c/build/book_executor.ex5 → MQL5/Experts/ftmo_live/
```
Toute modif de spec = ré-gel complet (config_v22 → yaml → nouveau sha → mqh → re-dépôt
sha256 → recompile) — jamais d'édition manuelle du mqh (ancre #20).

## Kill

- Soft : `touch "…/MQL5/Files/FLAT"` → flatten + désarmé, heartbeat continue.
- Total : détacher l'EA + `pkill -f supervisor.py`.
