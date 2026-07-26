# ftmo_live — exécution automatisée du book CHALLENGE v2.2 + reporting Telegram

Spec exécutable : `data/ftmo_portfolio/v22/spec_v22.yaml` **v2.2.2** (sha `3e7626f6d3fd…`,
v2.2 + overlay risque leg_leverage_cap : POLICY, change les cibles ; challenge.config/funded.config inchangés). Pins baseline : **605f4a4 + 4e1bac5 + ad403ce +
79c6912** + commit recost v2.2.1 (pin de déploiement, `v22/RECOST_v2.2.1.md`).
Cible : **compte démo FTMO neuf** ; bascule démo→challenge = changement de login MT5 uniquement.
Aucune constante manuelle : brain charge le yaml (loader épinglé `v22/ea/brain.py`, drift-check),
l'EA inclut `v22/ea/spec_v22.mqh` généré (sha `d8d3dcb1ad88…`) et refuse de trader sans
`MQL5/Files/spec_v22.sha256` identique (**à re-déposer : contenu = nouveau sha yaml**).
`ORB_RT_BPS` reste `era` — **aucun ré-ancrage avant le verdict N=60 du 2026-06-15**
(procédure : `NONREGRESSION_v2.2.md`, branche kill RETIRÉE).
v2.2.1 : l'EA lit les specs LIVE (swap pts, rollover3days, marge `OrderCalcMargin`) à l'init
+ au rebalance, **enforce le cap marge 60 % au taux live**, et alerte hors bornes datées
(`measured_specs`). ⚠ **Headline re-cost : si le levier serveur Swing = officiel
(1:30/1:15/1:9), le cap de-leverage vm14 ×0.24 et p(pass) −15.6 pt — gate déploiement.**

## Architecture

```
EA 21:45 market_export.json ──▶ brain.py (cron 21:50 Paris)
   (D1 520j x 4 jambes,            │  spec pin + drift-check (v22/ea/brain.py)
    specs contrats, swaps)         │  panels gelés + extension D1 → E.build_signals()
                                   │  (cleanroom, code path 462 cohortes, WT.loc[T] causal)
                                   │  gouverneur = sondes E._target_for_segment
                                   ▼
                            targets.json (clés plates ea_*, sha spec, prévision swaps)
                                   │
book_executor.mq5 ◀────────────────┘
  22:05 rebalance (quantize 0.01, stale >26 h = gestion seule + alerte)
  09:00 GER40 off | 15:30 US100 off | 17:35 GER40 on | 22:05 US100 on (lun+mar)
  micro-ORB 16:00→22:00 (compteur de jours, OCO stops, V2+E7) | backstop 21:30
  invariants M5 : daily floor 5%, floor 9000 + taper 2%, breaker 30%, marge 60%
  fills ASYNC (slippage_probe2 v1.11 : POSITION_PRICE_OPEN / scan DEAL_ENTRY_OUT,
  jamais Result*, latence 2-19 s) — kill-file FLAT = flatten + disable
        │
        ├─ state.json (M1) ──▶ supervisor.py (screen, 60 s) → alertes TG
        ├─ fills.csv, swaps_billed.csv
        └─ m5_today.json + EOD 22:58 ──▶ reconcile.py (cron 23:00) → Δ, gate 3 j
```

Note de spec : le brief nommait `audit_stack.load_audited()` ; ce module importe `config.py`
aux chemins sandbox morts (`/sessions/keen-clever-clarke`). Le code path réellement exécuté
pour les 462 cohortes (`run_battery.py`) est `engine_v22.load_stack` + cleanroom
`E.build_signals` / `E._target_for_segment` — c'est lui qui est importé partout ici.

## Fichiers

| Fichier | Rôle |
|---|---|
| `brain.py` | cron 21:50 Paris : signaux → `targets.json` (+ `--check`, `--dry-run`) |
| `mt5/book_executor.mq5` | EA exécuteur, zéro logique de signal, invariants hard-codés via mqh |
| `supervisor.py` | daemon 60 s (alertes) + `--report morning\|evening` + `--add-fee` |
| `reconcile.py` | cron 23:00 : replay sim de la journée, Δ décomposé, gate STOP 3 j |
| `tg.py` | envoi Telegram, refuse le token compromis (blocklist sha256) |
| `lib/` | spec (loader épinglé), marketdata, signals, governor (sondes sim), invariants (miroir EA), swaps, replay, statefiles |
| `tests/` | 145 tests : chaîne de gel, miroir==oracle sim, dry-run 10 j, V2+E7, swaps, protocole fichiers, reconcile e2e |

## Install VPS (Hetzner, MT5 sous wine en screen — `@reboot start_mt5.sh` existant)

1. **Repo + env** : `cd ~/projects/Algo_claude && git pull` ; compléter `.env` du projet avec
   les variables de `ftmo_live/.env.example` (token Telegram NEUF — voir §Secrets).
2. **MT5** : copier `ftmo_live/mt5/book_executor.mq5` + `data/ftmo_portfolio/v22/ea/spec_v22.mqh`
   dans `MQL5/Experts/ftmo_live/` ; **déposer `data/ftmo_portfolio/v22/ea/spec_v22.sha256` dans
   `MQL5/Files/`** ; compiler (MetaEditor) ; vérifier le log `SPEC OK v2.2 sha dd6ab1268020…`.
   Sans ce fichier l'EA refuse de trader (ancre #20).
3. **Attacher l'EA** (n'importe quel graphique, login démo) avec :
   - `InpServerTZOffsetMin=60` — VÉRIFIER : `TimeCurrent()` − heure Paris doit faire +60 min
     (FTMO = EET = CET+1 constant, mesure Paris+1 du 04/06) ; re-vérifier aux DST (mars/oct).
   - `InpPhase=1`, `InpAttemptStart=<date du jour 00:00>` (ancre pace — à RE-SAISIR à chaque
     nouvelle tentative/phase), symboles (`US100.cash`/`GER40.cash` selon Market Watch).
   - Trading algo autorisé (bouton AutoTrading).
4. **Crons** (crontab algo ; `CRON_TZ` exige cron ≥ 3.0pl1-128, sinon utiliser des timers
   systemd — vérifier avec `grep CRON_TZ /var/log/syslog` après le premier tir) :
   ```cron
   CRON_TZ=Europe/Paris
   50 21 * * 1-5  /home/algo/projects/Algo_claude/scripts/run_with_env.sh /usr/bin/python3 /home/algo/projects/Algo_claude/ftmo_live/brain.py >> /home/algo/logs/ftmo_brain.log 2>&1
   0  23 * * 1-5  /home/algo/projects/Algo_claude/scripts/run_with_env.sh /usr/bin/python3 /home/algo/projects/Algo_claude/ftmo_live/reconcile.py >> /home/algo/logs/ftmo_reconcile.log 2>&1
   30 8  * * *    /home/algo/projects/Algo_claude/scripts/run_with_env.sh /usr/bin/python3 /home/algo/projects/Algo_claude/ftmo_live/supervisor.py --report morning >> /home/algo/logs/ftmo_supervisor.log 2>&1
   20 22 * * *    /home/algo/projects/Algo_claude/scripts/run_with_env.sh /usr/bin/python3 /home/algo/projects/Algo_claude/ftmo_live/supervisor.py --report evening >> /home/algo/logs/ftmo_supervisor.log 2>&1
   ```
5. **Supervisor daemon** (heartbeat 60 s) :
   ```bash
   screen -dmS ftmo_supervisor ~/projects/Algo_claude/scripts/run_with_env.sh \
       /usr/bin/python3 ~/projects/Algo_claude/ftmo_live/supervisor.py --daemon
   ```
6. **Smoke test** : `run_with_env.sh python3 ftmo_live/brain.py --check` (spec OK + pins +
   export présent après 21:45) ; `supervisor.py --test-alert` (message TG) ;
   `supervisor.py --add-fee 96 "P1 tentative 1"` (suivi budget ~$400).

## Secrets

- Token Telegram : l'ancien token (exposé, rotation 2026-05-30) est BLOCKLISTÉ par hash —
  ajouter son sha256 dans `ftmo_live/config/token_blocklist.sha256` :
  `python3 -c "import hashlib,getpass;print(hashlib.sha256(getpass.getpass('old: ').encode()).hexdigest())"`.
  `tg.py`/`supervisor.py` refusent de démarrer si `TELEGRAM_BOT_TOKEN` matche la blocklist.
- Rotation : @BotFather `/revoke` → nouveau token dans `.env` → blocklister l'ancien →
  `supervisor.py --test-alert`. Jamais de secret dans crontab/ps/logs (run_with_env.sh).
- Login MT5 : saisi dans le terminal uniquement (jamais dans le repo).

## Procédure KILL

`touch <MQL5/Files>/FLAT` → l'EA flatten tout, annule les ordres, se désarme (state `kill=1`,
alerte TG) ; le heartbeat continue. Reprise : supprimer FLAT (l'EA réarme au tick suivant ;
les flags du jour restent — pas de ré-entrée avant le prochain événement de schedule).
Kill total : retirer l'EA du graphique + `pkill -f supervisor`.

## Burn-in démo (gate de bascule challenge)

Critères de sortie (TOUS) :
- **GATE MARGE SWING (v2.2.1, AVANT tout le reste)** : lire `margin_rate_live` dans
  state.json/market_export sur le compte SWING visé. Si ≈ Standard (1 %/2 %/3.33 %) → OK.
  Si ≈ Swing officiel (3.33 %/6.67 %/11.1 %) → **STOP comité** : vm14 inexécutable tel quel
  (cap 60 % bind 56 %, p(pass) −15.6 pt — `v22/RECOST_v2.2.1.md`) ;
- ≥ 1 cycle hebdo complet couvrant lun+mar overnight (GER40 17:35→09:00, US100 22:05→15:30),
  vendredi triple-swap indices, week-end tenu ;
- réconciliation : compteur Δ inexpliqué **0/3** sur toute la période ;
- swaps facturés vs modèle ±20% chaque nuit (gate live yaml — sinon STOP) ;
- zéro invariant violé (breaker/floors/marge/caps jamais en défaut non justifié) ;
- zéro heartbeat perdu > 15 min ;
- les 2 rapports quotidiens corrects sans intervention.
Pendant le burn-in, le micro-ORB démo alimente la mesure `ORB_RT_BPS` (fills actifs
16:00-16:30, ≥ 60 trades → verdict 2026-06-15, re-run section funded SEULE, ancres #4/#5/#18).

## Bascule démo → challenge

1. Burn-in validé + verdict swap ±20% OK.
2. Changer le LOGIN du terminal MT5 vers le compte challenge (rien d'autre ne change).
3. Ré-attacher l'EA : `InpPhase=1`, `InpAttemptStart=<jour 1 du challenge>` ; vérifier
   `SPEC OK` au log + premier state.json + rapport du soir.
4. P1→P2 : nouveau login FTMO + `InpPhase=2` + `InpAttemptStart=<début P2>` (vm ×1.2 auto).
5. Funding : `InpPhase=3` — le switch yaml s'applique (vm 1.0, on_w 0.35, ORB ON 0.25%
   taper, micro OFF, pace/glide/abandon OFF, compteur retraits wd14 → alerte supervisor).
   **Ne pas oublier** : verdict `ORB_RT_BPS` AVANT le funding si N=60 atteint (15/06).

## Divergences sim↔live documentées (assumées, bornées)

- **Micro-ORB trail-to-BE** : le yaml spécifie le trail (l'EA l'implémente) ; le cache sim
  `orb_e7_Rera` est no-trail (0/1590 STOP sauvés, vérifié). Impact micro ≤ ~$2/jour, isolé
  par reconcile dans Δ_micro. Le P&L funded-ORB (0,25 %) suit la même règle yaml.
- **GER40 en EUR** : le sim quantise au prix-index (EURUSD≈1) ; l'EA dimensionne au notionnel
  USD vrai (tick_value/tick_size) — grille de lots décalée ~8 %, dans la tolérance de
  quantization ; le cap marge utilise le notionnel vrai (plus conservateur).
- **Jour ON sans fill GER40** (taper→0, quantize→0) : le sim compte `opened` quand même
  (sémantique 605f4a4) ; le live compte les FILLS (FTMO réel). Cas ~mort (equity au floor).
- **Arrondi lots** : sim `np.round` (half-even) vs EA `MathRound` (half-away) — ≤ 1 step,
  uniquement sur les demi-pas exacts.
- **Redémarrage EA intra-jour** : le 1er swaps_billed peut agréger plusieurs nuits pour des
  positions tenues (delta POSITION_SWAP) → faux positif possible du gate ±20% une nuit.
- **MQL5 non compilé sur ce Mac** : compiler dans MetaEditor au déploiement ; le miroir
  Python (`lib/invariants.py`) est validé contre l'oracle sim par `tests/` (145 PASS) et
  l'EA le porte 1:1 — toute divergence résiduelle est attrapée par reconcile (gate 3 j).

## Audit trail

Chaque message Telegram et chaque ligne de `fills.csv` se reconstruisent depuis :
`targets.json` (poids+gouverneur+prévision swaps, horodaté, sha spec) ; `state.json`
(M1, gouverneur live, floors, positions) ; `runtime/sod|eod/` (snapshots) ;
`runtime/reconcile_log.csv` + `runtime/eod/reconcile_*.json` (Δ décomposé) ;
`runtime/brain_status.json` ; `swaps_billed.csv` ; logs cron (pattern `_automation/`).
