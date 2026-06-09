# Security Cleanup Plan — 2026-05-30

**Statut** : propositions de modifications. **AUCUNE n'a été appliquée**. Pas de
commit, pas de filter-repo, pas de modification de la crontab live, pas de push.

**Règle de sécurité** : aucune valeur de secret n'est imprimée dans ce document,
même en passant. Les valeurs sont citées par leur NOM (`PROPR_API_KEY`, etc.) ou
balisées `<REDACTED:KIND>`.

**Contexte** : les clés exposées (Propr `pk_live_*`, HL private key, Telegram pair)
ont été révoquées et régénérées côté dashboards (info fournie par toi). Cette
opération vise à éliminer toute exposition résiduelle dans le repo et sur le VPS.

---

## S1 — Crontab VPS : diff proposé (PRE-APPROVAL)

### Audit de surface du `crontab -l` actuel

10 lignes au total, dont **4 contiennent des secrets en clair** dans la commande :
- Ligne 1 : `--private-key <REDACTED:HL_PRIVKEY>` passé en argument CLI
- Ligne 3 : `PROPR_API_KEY=<REDACTED:PROPR_KEY>` inline
- Ligne 4 : `PROPR_API_KEY=<REDACTED>`, `TELEGRAM_BOT_TOKEN=<REDACTED>`, `TELEGRAM_CHAT_ID=<REDACTED>` (3 secrets inline)
- Ligne 7 : doublon exact de ligne 6 (watchdog_check.sh sans redirection)

Pré-requis pour la migration : ajouter au VPS `~/projects/Algo_claude/.env`
les variables manquantes (noms uniquement) :
```
+PROPR_API_KEY=<paste-new-rotated-key-here>
+PROPR_API_URL=<optional-override-or-leave-blank>
```
(`HYPERLIQUID_TESTNET_KEY`, `BINANCE_TESTNET_*`, `TELEGRAM_*`, `FRED_API_KEY`
sont **déjà présents** dans `~/projects/Algo_claude/.env` côté VPS — vérifié par
`awk -F= '/^[A-Z]/ {print $1}'` sans afficher les valeurs.)

### Diff unifié — crontab actuel → proposé

```diff
--- crontab.live (current — secrets redacted)
+++ crontab.proposed
@@ -1,10 +1,12 @@
-5 0 * * * /home/algo/run_tsmom.sh --live --private-key <REDACTED:HL_PRIVKEY> >> /home/algo/logs/tsmom.log 2>&1
-30 0 * * * /home/algo/run_monitor.sh >> /home/algo/logs/monitor.log 2>&1
-5 0 * * 1 cd ~/projects/Algo_claude && source ~/venv/bin/activate && PROPR_API_KEY=<REDACTED:PROPR_LIVE> python -m strategies.tsmom_v2_propfirm.execution.run_rebalance >> logs/tsmom_v2_cron.log 2>&1
-30 8 * * * cd ~/projects/Algo_claude && source ~/venv/bin/activate && PROPR_API_KEY=<REDACTED> TELEGRAM_BOT_TOKEN=<REDACTED> TELEGRAM_CHAT_ID=<REDACTED> python -m strategies.tsmom_v2_propfirm.execution.daily_summary >> logs/tsmom_v2_cron.log 2>&1
-10 0,8,16 * * * cd ~/projects/Algo_claude && /bin/bash -c 'source ~/venv/bin/activate && source .env && /home/algo/run_delta_neutral.sh --live --bn-key $BINANCE_TESTNET_API_KEY --bn-secret $BINANCE_TESTNET_SECRET_KEY --hl-key $HYPERLIQUID_TESTNET_KEY' >> ~/logs/delta_neutral.log 2>&1
-*/2 13-17 * * 1-5 /bin/bash /home/algo/projects/Algo_claude/Futures/live/strategy_c_live/watchdog_check.sh >> /tmp/watchdog_check.log 2>&1
-*/2 13-17 * * 1-5 /bin/bash /home/algo/projects/Algo_claude/Futures/live/strategy_c_live/watchdog_check.sh
-30 6 * * 1-5 /bin/bash /home/algo/projects/Algo_claude/scripts/fetch_arxiv.sh
-*/30 * * * * /bin/bash /home/algo/projects/Algo_claude/scripts/fetch_alpha_sources.sh
-@reboot sleep 30 && /usr/bin/screen -dmS mt5 /home/algo/start_mt5.sh
+# All jobs source ~/projects/Algo_claude/.env for secrets. No values in CLI args.
+# Use single-quotes around the bash -c block so $VAR expansion happens inside
+# the subshell, after `source .env` runs.
+
+# Strategy A — daily HL testnet state/rebalance (places fills if signal flips)
+5 0 * * * cd ~/projects/Algo_claude && /bin/bash -c 'source ~/venv/bin/activate && source .env && /home/algo/run_tsmom.sh --live --private-key "$HYPERLIQUID_TESTNET_KEY"' >> /home/algo/logs/tsmom.log 2>&1
+
+# Strategy A — daily monitor wrapper (no secrets needed)
+30 0 * * * /home/algo/run_monitor.sh >> /home/algo/logs/monitor.log 2>&1
+
+# Strategy A — weekly Propr LIVE rebalance (Monday 00:15, decoupled from 00:05 daily job to avoid race)
+15 0 * * 1 cd ~/projects/Algo_claude && /bin/bash -c 'source ~/venv/bin/activate && source .env && python -m strategies.tsmom_v2_propfirm.execution.run_rebalance' >> ~/projects/Algo_claude/logs/tsmom_v2_cron.log 2>&1
+
+# Strategy A — daily Propr summary (08:30 UTC)
+30 8 * * * cd ~/projects/Algo_claude && /bin/bash -c 'source ~/venv/bin/activate && source .env && python -m strategies.tsmom_v2_propfirm.execution.daily_summary' >> ~/projects/Algo_claude/logs/tsmom_v2_cron.log 2>&1
+
+# Strategy B — delta-neutral 8h (unchanged: already correct pattern)
+10 0,8,16 * * * cd ~/projects/Algo_claude && /bin/bash -c 'source ~/venv/bin/activate && source .env && /home/algo/run_delta_neutral.sh --live --bn-key "$BINANCE_TESTNET_API_KEY" --bn-secret "$BINANCE_TESTNET_SECRET_KEY" --hl-key "$HYPERLIQUID_TESTNET_KEY"' >> ~/logs/delta_neutral.log 2>&1
+
+# Strategy C — watchdog (kept ONCE, not twice); no secrets
+*/2 13-17 * * 1-5 /bin/bash /home/algo/projects/Algo_claude/Futures/live/strategy_c_live/watchdog_check.sh >> /tmp/watchdog_check.log 2>&1
+
+# Automation — alpha hunt + arxiv (no secrets)
+30 6 * * 1-5 /bin/bash /home/algo/projects/Algo_claude/scripts/fetch_arxiv.sh >> ~/projects/Algo_claude/logs/arxiv_fetch.log 2>&1
+*/30 * * * * /bin/bash /home/algo/projects/Algo_claude/scripts/fetch_alpha_sources.sh >> ~/projects/Algo_claude/logs/alpha_hunt_fetch.log 2>&1
+
+# MT5 terminal autostart at reboot (no secrets in command; MT5 reads its own .ini)
+@reboot sleep 30 && /usr/bin/screen -dmS mt5 /home/algo/start_mt5.sh
```

### Changements clés
| # | Avant | Après | Justification |
|---|---|---|---|
| 1 | `--private-key <REDACTED>` en CLI | `source .env && --private-key "$HYPERLIQUID_TESTNET_KEY"` | Secret hors `crontab -l`, hors `ps aux`, hors logs |
| 2 | Monday `5 0 * * 1` (collision avec daily) | Monday `15 0 * * 1` | Décollision : daily HL testnet à 00:05 finit avant que Propr rebalance ne démarre à 00:15 |
| 3 | `PROPR_API_KEY=<REDACTED> python ...` inline | `source .env && python ...` | Secret hors `ps`, hors `crontab -l` |
| 4 | 3 secrets inline `PROPR + TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID` | `source .env && python ...` | idem |
| 5 | unchanged | unchanged + ajout guillemets `"$VAR"` | Plus robuste si valeurs contiennent espaces |
| 6/7 | doublon exact watchdog_check.sh | ligne 7 supprimée | élimine instance dupliquée |
| 8/9 | redirection stderr seulement sur fetch_arxiv (rien sur fetch_alpha) | redirection unifiée vers logs/ | traçabilité |

### Migration : commandes pour TOI à lancer (lecture des étapes seulement)

```bash
# 1. Backup la crontab actuelle (sécurité : tu peux revert)
ssh -i ~/.ssh/hetzner_algo_claude algo@<VPS_IP> \
  'crontab -l > ~/crontab.backup-pre-cleanup-$(date +%Y%m%d).txt && \
   echo "Backed up to ~/crontab.backup-pre-cleanup-$(date +%Y%m%d).txt"'

# 2. AVANT d'installer le nouveau crontab : ajoute les nouvelles vars au .env VPS
#    (édition manuelle — ne PAS scripter pour éviter d'écrire des valeurs dans l'historique shell)
ssh -i ~/.ssh/hetzner_algo_claude algo@<VPS_IP> 'nano ~/projects/Algo_claude/.env'
#    → ajoute : PROPR_API_KEY=<paste-rotated-key>  et PROPR_API_URL=<value-or-blank>
#    → Ctrl-O, Ctrl-X

# 3. Copie le crontab proposé sur le VPS et installe-le
#    (option A : éditer en place)
ssh -i ~/.ssh/hetzner_algo_claude algo@<VPS_IP> 'EDITOR=nano crontab -e'
#    → colle le contenu proposé ci-dessus (section "diff" partie + uniquement)

# 4. Vérifie installation
ssh -i ~/.ssh/hetzner_algo_claude algo@<VPS_IP> 'crontab -l | grep -cE "^[#0-9*]"'

# 5. Test à sec une cron sans attendre minuit : déclenche manuellement run_rebalance
ssh -i ~/.ssh/hetzner_algo_claude algo@<VPS_IP> \
  'cd ~/projects/Algo_claude && bash -c "source ~/venv/bin/activate && source .env && python -m strategies.tsmom_v2_propfirm.execution.run_rebalance --dry-run" 2>&1 | tail -20'

# 6. Si OK : rotate à nouveau les clés Propr / HL si la rotation n'est pas faite,
#    puis update le .env VPS avec les nouvelles valeurs.
```

---

## S2 — Scrubbing logs + correction des prints de secrets dans le code

### S2.a — Vérification : les logs sont-ils contaminés ?

Mesure faite côté VPS (compte d'occurrences, sans afficher les valeurs) :

| Log | Pattern recherché | Compte | Action |
|---|---|---|---|
| `~/projects/Algo_claude/logs/tsmom_v2_cron.log` | `pk_live_[A-Za-z0-9]{30,}` (vraies clés Propr) | **0** | ✓ propre |
| `~/projects/Algo_claude/logs/tsmom_v2_cron.log` | `pk_live_XXX` (placeholder) | 3 | informatif (template inoffensif) |
| Tous logs (`~/logs/`, `~/projects/.../logs/`) | `[0-9a-f]{64}` (HL privkey hex 64 chars) | **0** | ✓ propre |
| Tous logs | `[0-9]{9,12}:[A-Za-z0-9_-]{30,}` (Telegram bot token) | **0** | ✓ propre |

**Verdict S2.a** : aucun log VPS ne contient de vrai secret en clair. Pas de
scrubbing nécessaire — l'inquiétude initiale (drift #11) était une fausse alarme.
Le "PROPR_API_KEY=pk_live_XXX" observé dans `tsmom_v2_cron.log:48` est en réalité
un **template** imprimé par le code source, où "XXX" est littéralement les 3
caractères X (pas la vraie clé).

### S2.b — Code source qui imprime le template — proposition de correctif

Deux fichiers impriment "PROPR_API_KEY=pk_live_XXX" en log d'aide post-exécution.
Le placeholder est inoffensif mais peut être confondu avec un vrai secret, et il
**suggère** aux opérateurs que c'est la bonne façon de configurer la cron (alors
que la bonne façon est `source .env`).

#### Diff — `strategies/tsmom_v2_propfirm/execution/run_rebalance.py`

```diff
@@ -131,11 +131,11 @@ def main(...):
     logger.info("Run complete.")
     logger.info(
         "\nCron line for VPS deployment:\n"
-        "  5 0 * * 1 cd ~/Desktop/Algo_claude && "
-        'source "<HOME>/Desktop/Unholy returns/Python3.12.9/myenv/bin/activate" && '
-        "PROPR_API_KEY=pk_live_XXX python -m "
-        "strategies.tsmom_v2_propfirm.execution.run_rebalance "
-        ">> logs/tsmom_v2_cron.log 2>&1"
+        "  15 0 * * 1 cd ~/projects/Algo_claude && \\\n"
+        "    /bin/bash -c 'source ~/venv/bin/activate && source .env && \\\n"
+        "      python -m strategies.tsmom_v2_propfirm.execution.run_rebalance' \\\n"
+        "    >> ~/projects/Algo_claude/logs/tsmom_v2_cron.log 2>&1\n"
+        "  (PROPR_API_KEY must be set in ~/projects/Algo_claude/.env, never inline.)"
     )
```

#### Diff — `strategies/tsmom_v2_propfirm/execution/daily_summary.py`

```diff
@@ -187,8 +187,8 @@ def main(...):
     print(
         "\nCron line for VPS deployment:\n"
-        "  30 8 * * * cd ~/projects/Algo_claude && source ~/venv/bin/activate && \\\n"
-        "  PROPR_API_KEY=pk_live_XXX python -m \\\n"
-        "  strategies.tsmom_v2_propfirm.execution.daily_summary \\\n"
-        "  >> logs/tsmom_v2_cron.log 2>&1"
+        "  30 8 * * * cd ~/projects/Algo_claude && \\\n"
+        "    /bin/bash -c 'source ~/venv/bin/activate && source .env && \\\n"
+        "      python -m strategies.tsmom_v2_propfirm.execution.daily_summary' \\\n"
+        "    >> ~/projects/Algo_claude/logs/tsmom_v2_cron.log 2>&1\n"
+        "  (PROPR_API_KEY + TELEGRAM_* must be set in ~/projects/Algo_claude/.env, never inline.)"
     )
```

### S2.c — Recherche exhaustive d'autres prints/log de secrets

| Pattern | Résultat | Lieu |
|---|---|---|
| `print(...api_key...)` | 1 occurrence en contexte safe ("free_tier_key" dans une docstring ascii art) | `Crypto/research/archived/other/strategy_c_search/__main__.py:129` — pas un vrai secret |
| `print(...PROPR_API_KEY...)` | 2 occurrences (run_rebalance.py:136, daily_summary.py:191) — traitées en S2.b | — |
| `print(...HYPERLIQUID...PRIVATE...)` | 0 | — |
| `print(...TELEGRAM_BOT_TOKEN...)` | 0 | — |
| `log.info(...api_key...)` etc | 0 | — |
| f-strings avec `{api_key}`, `{secret}`, `{private_key}`, `{TELEGRAM_BOT}` | 0 | — |
| `mt5.login({MT5_LOGIN})` (login imprimé dans error) | 1 | `Futures/live/strategy_c_live/mt5_client.py:98` — affiche le LOGIN (numéro de compte), pas le password. Risque faible mais à masquer (cf. ci-dessous). |

#### Diff — `Futures/live/strategy_c_live/mt5_client.py` (mineur)

```diff
@@ -96,7 +96,7 @@ class MT5Client:
         if MT5_LOGIN:
             ok = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
             if not ok:
-                raise RuntimeError(f"mt5.login({MT5_LOGIN}) failed: {mt5.last_error()}")
+                raise RuntimeError(f"mt5.login(login=<redacted>) failed: {mt5.last_error()}")
```

**Aucune correction urgente ailleurs.** Le repo est globalement propre en termes
de logging de secrets.

---

## S3 — `.env.example` régénéré (proposition)

Variables réellement consommées (grep `os.getenv` + `os.environ` sur tout le repo,
hors `__pycache__` et `_audit/`) : **19 variables au total**, réparties en
**6 groupes fonctionnels**.

### Diff — `.env.example`

```diff
--- .env.example (current, 13 lignes, 3 templates)
+++ .env.example (proposed, ~80 lignes, 19 variables)
@@ -1,12 +1,86 @@
-# ── Telegram alerting ────────────────────────────────────────────────────────
-# Get your token from @BotFather on Telegram.
-# Get your chat ID by messaging @userinfobot or from the Telegram API.
-# For a private channel, the ID is negative and starts with -100.
-TELEGRAM_BOT_TOKEN=123456789:ABCDEFghijklmnopqrstuvwxyz01234567890
-TELEGRAM_CHAT_ID=-1001234567890
-
-# ── Hyperliquid wallet ────────────────────────────────────────────────────────
-# Private key for the dedicated trading wallet (hex, with or without 0x prefix).
-# Use a TESTNET wallet for testnet deployment — never reuse a mainnet key.
-HYPERLIQUID_PRIVATE_KEY=0xabc123...
+# ─────────────────────────────────────────────────────────────────────────────
+# Algo_claude — .env template
+# Copy to .env (gitignored), fill values, never commit values.
+# Consumed by code (verified via grep os.getenv / os.environ across repo).
+# ─────────────────────────────────────────────────────────────────────────────
+
+# ── Telegram alerting (notifier.py, daily_summary.py, run_daily.py,
+#    monitor_loop.py, guardrails.py) ─────────────────────────────────────────
+TELEGRAM_BOT_TOKEN=
+TELEGRAM_CHAT_ID=
+
+# ── Hyperliquid (strategies/delta_neutral/live_trader.py, tsmom_live.py) ────
+# TESTNET key (used by B + A daily). Hex string, with or without 0x prefix.
+HYPERLIQUID_TESTNET_KEY=
+# Mainnet key — set ONLY when mainnet deployment is approved (~2026-07-17).
+HYPERLIQUID_PRIVATE_KEY=
+
+# ── Binance testnet (strategies/delta_neutral/live_trader.py) ───────────────
+BINANCE_TESTNET_API_KEY=
+BINANCE_TESTNET_SECRET_KEY=
+
+# ── Propr (strategies/tsmom_v2_propfirm/execution/*) ─────────────────────────
+# pk_live_* for live, pk_test_* for testnet. Rotate after any exposure.
+PROPR_API_KEY=
+# Optional URL override (defaults baked into propr_sdk.py:64). Leave blank
+# unless instructed by Propr support.
+PROPR_API_URL=
+
+# ── Tradeify / Tradovate (Futures/live/strategy_c_live/config.py) ───────────
+# 'demo' or 'live'
+TRADOVATE_ENV=demo
+TRADOVATE_USERNAME=
+TRADOVATE_PASSWORD=
+TRADOVATE_CID=
+TRADOVATE_SECRET=
+# App identification (defaults exist in config.py; override only if Tradovate
+# instructs).
+TRADOVATE_APP_ID=StratC
+TRADOVATE_APP_VERSION=1.0
+TRADOVATE_DEVICE_ID=
+
+# ── MT5 (Futures/live/strategy_c_live/mt5_client.py — legacy / Voie B FTMO) ─
+MT5_SERVER=
+MT5_LOGIN=
+MT5_PASSWORD=
+
+# ── Data providers (research only) ──────────────────────────────────────────
+# FRED (data/cache.py:284) — for risk-free rate (DTB3)
+FRED_API_KEY=
+# Glassnode (Crypto/research/archived/sentiment/mvrv/feasibility.py:386)
+# Only needed for re-running MVRV research. Leave blank in normal use.
+GLASSNODE_API_KEY=
```

**Comptage final** : 19 variables couvertes (vs 3 actuellement). Groupes :
- Telegram (×2), Hyperliquid (×2), Binance (×2), Propr (×2), Tradovate (×8), MT5 (×3), Data (×2).

---

## S4 — Scan historique gitleaks

### Statut au moment de l'écriture
- `gitleaks detect` (working tree) : RUNNING — déclenché à `01:46`, 19+ min CPU
- `gitleaks git` (full history) : RUNNING — déclenché à `01:48`, 18+ min CPU

Les deux scans pèsent sur le repo (~3000 fichiers tracés + historique). **Résultats
détaillés seront ajoutés à la fin de ce document** dès que les scans terminent.

En attendant, recherche manuelle ciblée :

| Pattern recherché | Commande | Verdict |
|---|---|---|
| `.env` jamais commit | `git log --diff-filter=A --name-only \| grep "^\.env$"` | **0 commits** — `.env` jamais ajouté à l'historique ✓ |
| Préfixe `pk_live_` (Propr live key) dans l'historique | `git log -S "pk_live" --pretty=oneline` | **3 commits** matchent : `4189da3, 33cd26a, 92bf9dc`. Sans afficher les valeurs, on ne peut distinguer entre (a) une vraie clé leakée (b) le préfixe en commentaire/example. **À investiguer** ci-dessous. |
| Variable `PROPR_API_KEY` dans l'historique | `git log -S "PROPR_API_KEY" --pretty=oneline` | 4 commits (`4189da3, e079489, 33cd26a, 92bf9dc`). Ces commits ajoutent du **code** qui lit la variable (`os.environ.get("PROPR_API_KEY")`), pas la valeur. |
| Variable `HYPERLIQUID_PRIVATE_KEY` | `git log -S "HYPERLIQUID_PRIVATE_KEY" --pretty=oneline` | 1 commit (`a97dacf` "Initial commit: hardened live trader"). Référence le nom. |

### Investigation ciblée des 3 commits suspects (pk_live)

Pour distinguer une vraie clé d'un simple match du préfixe `pk_live_`, voici la
commande SAFE à exécuter (compte SEULEMENT, n'affiche pas la valeur) :

```bash
# Renvoie 1 ligne par commit, comptant les patterns "pk_live_" suivis de ≥30
# alphanumériques (signature d'une vraie clé). 0 = match en commentaire seulement.
for c in 4189da3 33cd26a 92bf9dc; do
  echo -n "commit $c: real-key matches = "
  git show "$c" -- ':!_audit' 2>/dev/null | grep -cE 'pk_live_[A-Za-z0-9]{30,}'
done
```

Le résultat te donnera, pour chaque commit, le nombre de matches "vraie clé".
**Tu peux exécuter cette commande sans risque** (aucune valeur affichée). Si un
commit retourne > 0, alors il y a fuite réelle et `git filter-repo` est nécessaire.

### Recommandation `git filter-repo` — conditionnelle

| Si scan révèle… | Recommandation |
|---|---|
| Tous matches sont des templates (`pk_live_XXX`) ou des références au préfixe en docstring | **PAS DE FILTER-REPO** — les commits ne contiennent pas de vraies valeurs. La rotation côté Propr suffit. |
| Au moins un commit contient une vraie clé `pk_live_<30+ chars>` | **FILTER-REPO RECOMMANDÉ**. Commande à exécuter MANUELLEMENT par toi : `git filter-repo --replace-text <(printf 'regex:pk_live_[A-Za-z0-9]{30,}==><REDACTED:PROPR_KEY>\n')` puis force-push (DANGEREUX : coordonne avec collaborateurs si applicable, et conserve un mirror du repo original). |
| HL private key (64 hex chars) trouvée dans un commit | Idem filter-repo, regex `regex:0?x?[0-9a-f]{64}==><REDACTED:HEX64>`. |
| Telegram bot token trouvé | Idem, regex `regex:[0-9]{9,12}:[A-Za-z0-9_-]{30,}==><REDACTED:TG_TOKEN>`. |

**Important** : `git filter-repo` réécrit l'historique. Même après filter-repo,
**toute valeur déjà téléchargée par un tiers reste compromise** — la rotation
côté dashboard est la seule mitigation réelle. Filter-repo limite seulement
l'exposition future via le repo public ou shared.

### Liste des chemins potentiellement à filtrer (à confirmer après gitleaks)

À ce stade, candidats probables (en attente confirmation gitleaks) :
- `strategies/tsmom_v2_propfirm/execution/discover_api.py` (manipule PROPR_API_KEY)
- `strategies/tsmom_v2_propfirm/execution/propr_sdk.py`
- `strategies/tsmom_v2_propfirm/execution/run_rebalance.py`
- `strategies/tsmom_v2_propfirm/execution/daily_summary.py`
- `strategies/delta_neutral/live_trader.py`
- `tsmom_live.py` (root)
- N'importe quel `.env` accidentellement commit (vérifié : aucun ✓)
- Documentation `*.md` qui contiendrait un example concret

---

## Récapitulatif — ce qui est PROPOSÉ vs ce qui est FAIT

| Item | Statut | À FAIRE par toi |
|---|---|---|
| Crontab VPS rewrite (S1) | **PROPOSÉ — non appliqué** | Approuver le diff ; ajouter `PROPR_API_KEY` au `.env` VPS ; lancer `crontab -e` et coller le nouveau contenu |
| Backup crontab actuelle | **non fait** | `ssh ... 'crontab -l > ~/crontab.backup-...'` (commande fournie en S1) |
| Logs scrub (S2.a) | **CONSTAT — pas nécessaire** | RAS (logs propres) |
| Correction code prints (S2.b) | **DIFF PROPOSÉ — non appliqué** | Approuver puis lancer Edit sur les 3 fichiers (run_rebalance.py, daily_summary.py, mt5_client.py) |
| .env.example regen (S3) | **DIFF PROPOSÉ — non appliqué** | Approuver puis lancer Write sur `.env.example` |
| Gitleaks scan (S4) | **EN COURS** — résultats partiels (manuel grep) | Attendre fin de scan ; lancer la commande d'investigation S4 pour départager les 3 commits suspects |
| `git filter-repo` | **non lancé** — décision conditionnelle | À lancer toi-même UNIQUEMENT si commande d'investigation S4 retourne `> 0` matches sur au moins un commit |
| Rotation des clés | déjà faite (confirmé par toi) | RAS — sauf si filter-repo non lancé : rester vigilant que les vieilles clés ne soient pas réutilisables |

---

## Annexe — résultats gitleaks (à compléter quand scan terminé)

*(Section vide en attendant)*
