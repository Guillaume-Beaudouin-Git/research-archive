# Incident MT5 watchdog / supervisor — 2026-06-15

Burn-in FTMO Swing, VPS algo@<VPS_IP>. EA `book_executor` GELÉ, désarmé par FLAT
(aucune position en jeu pendant tout l'incident et le re-test).

## 1. Symptôme
Week-end du 13-14/06 : MT5 zombifié (déconnecté du serveur, « scanning network, not
authorized » depuis ven ~23:56), heartbeat EA (`state.json`) figé, **aucune relance** et
**aucune alerte** jusqu'à un redémarrage manuel le lundi 15/06 ~13:18 UTC.

## 2. Cause racine (diagnostic corrigé)
Le diagnostic initial (« le watchdog appelle `market_hours.is_open()` qui n'existe pas →
AttributeError silencieuse ») est **FAUX** :
- `lib/market_hours.py` n'expose QUE `fx_session_open(now)` (+ `_shift_h` privé). `is_open`
  n'a jamais existé. Le `m.is_open(now)` du diagnostic était un appel manuel erroné.
- watchdog (`watchdog_mt5.sh:50`) **et** supervisor (`supervisor.py:38,75,107`) appellent
  déjà tous deux `fx_session_open` — la SOURCE DE VÉRITÉ unique. Reproduit sur le VPS :
  `fx_session_open(now)=True`, rc=0, aucune erreur. Le check de session fonctionne.

Les **deux vrais défauts** :
1. **watchdog fail-silent-to-no-op.** `session_open || exit 0` traitait *tout* exit non nul
   du check Python — y compris un crash venv/chemin/import — comme « marché fermé → exit 0
   muet ». Et le watchdog n'écrivait dans son log *que* sur action → aucune trace par run,
   impossible de savoir si le cron `*/3` tournait.
2. **Couche d'alerte morte.** Le daemon `supervisor.py --daemon` n'était **pas lancé**
   (uptime VPS 60 j, son seul démarrage auto est `@reboot` dont la ligne est postérieure au
   dernier boot ; les lancements manuels n'avaient pas persisté). Un daemon non lancé
   n'envoie aucune alerte heartbeat — indépendamment de tout `market_hours`.

Le **déclencheur exact côté watchdog le week-end n'est pas prouvable** depuis les logs :
`algo` ne lit pas `syslog`/journal cron (owner `syslog:adm`, pas de sudo sans mot de passe)
et le watchdog est muet par design sur les états sains/fermés. Le re-test (§4) prouve que le
chemin de relance fonctionne *maintenant* de bout en bout ; les correctifs (§3) rendent toute
récidive immédiatement visible et alertée.

Note `--force` : le test du 12/06 utilisait `--force`, qui **saute** l'appel `session_state`
(le gate de session est dans `if [ "$FORCE" -eq 0 ]`). Il n'a donc exercé que le chemin de
*relance*, jamais le chemin de *session* — d'où un défaut latent non détecté.

## 3. Correctifs (commit f7895b6 + keepalive)
**watchdog_mt5.sh**
- `session_state()` renvoie **0=ouvert / 1=fermé / 2=ERREUR** (traceback→log). `case` explicite :
  fermé→no-op ; ouvert→poursuit ; **erreur→`err_internal` (Telegram BRUYANT, cooldown 1 h) +
  FAIL-SAFE OUVERT**. Une erreur interne n'est plus jamais confondue avec « marché fermé ».
- `beat()` : **heartbeat-DU-watchdog** réécrit dans `~/logs/watchdog_alive` à chaque run utile.

**supervisor.py**
- Alerte **`watchdog_dead`** si `watchdog_alive` absent/périmé (>10 min) EN SESSION, évaluée
  **avant** le mtime-gate → jamais masquée par un state figé (méta-surveillance : le
  superviseur surveille le gardien).

**Déploiement** : `supervisor_keepalive.sh` + cron `*/5` → la couche d'alerte se relance seule
si absente (le défaut #2 ne peut plus durer 60 jours).

Tests : 169 → 174 (suite verte ; le seul échec VPS, `test_brain_dryrun`, est un cache data
gitignoré manquant, orthogonal).

## 4. Re-test RÉEL en session ouverte (Mission 3) — 2026-06-15
Marché ouvert (`fx_session_open=True`), `pkill -9 -f [t]erminal64` SANS `--force`, FLAT en place.

| Horodatage UTC | Événement |
|---|---|
| 14:06:02 | `watchdog_alive` mis à jour par le cron `*/3` → **le cron exécute bien le watchdog** |
| 14:09:07 | **T0 — KILL** terminal64 (no --force). FLAT présent, init=1, equity 10000 |
| 14:12 tick | watchdog : state âgé ~175s < 240s → **no-op correct** (pas de fausse relance) |
| **14:15:01** | watchdog (cron, **force=0**) : « state.json vieux de 356s (seuil 240s) — restart MT5 » → **⚠️ Telegram envoyé** |
| 14:15:25 | MT5 relancé, EA OnInit → `state.json` réécrit (≈24 s après start_mt5.sh) |
| **14:17:07** | watchdog vérif : « OK: MT5 relancé en 126s — EA ré-initialisé (init 1→2) » → **✅ Telegram envoyé** |

POST : terminal64 up (PID 1239242), `kill=1` (re-désarmé par FLAT), `positions=[]`, equity
10000 inchangé, **FLAT intact**, anti-boucle = 1 entrée (pas de faux déclenchement).
**Résurrection ≈ 6,3 min** (≈354 s = attente by-design que le state dépasse 240 s + phase
cron ; relance→EA-reinit ≈ 24 s). `force=0` ⇒ le chemin de session a bien été exercé.

## 5. Mission 4 — anti-spam ne masque pas une panne en session
L'alerte heartbeat (`supervisor.py:119`) est évaluée **avant** le mtime-gate (`:127`) qui ne
gate que les alertes de *contenu*. Un state GELÉ en session ouverte alerte donc toujours.
Vérifié par `test_heartbeat_not_masked_by_mtime_gate` (state figé, mtime-gate fermé → heartbeat
toujours `fired`). Le silence du week-end venait du daemon NON LANCÉ (§2.2), pas d'un masquage.

## 6. Caveats / suivi
- Déclencheur exact du week-end côté watchdog non prouvable (logs cron illisibles sans sudo).
  Atténué : `watchdog_alive` rend désormais l'exécution du cron observable en continu.
- Le cron daemon lui-même reste le socle non auto-surveillé (si cron meurt, l'absence des
  rapports 08:30/22:20 est le signal). Acceptable.
