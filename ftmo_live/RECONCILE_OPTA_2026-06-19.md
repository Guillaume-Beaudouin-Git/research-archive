# Reconcile Option A — vraie décomposition Δ via m5_today tardif (PRÉPARÉ, NON DÉPLOYÉ)

> 2026-06-19. Préparé sur branche, **dry-run validé sur données réelles 06-18**, en attente
> de GO pour déploiement. Ne touche PAS l'EA / la chaîne gelée / FLAT / targets.json.

## Problème (rappel)

L'EOD on-time (22:58 Paris) est **structurellement impossible** : le rollover serveur halte
TOUS les symboles ~22:54→23:05 Paris, `hm=ParisHM()` (gelé sur `TimeCurrent`) n'atteint jamais
22:58 → `Do2258EOD` ne tire pas. `reconcile_log.csv` n'a JAMAIS eu de décomposition Δ (dégradé
perpétuel). MAIS l'EA écrit le **m5_today.json TARDIF ~21:05 UTC** (1er tick post-reconnexion),
chemin de prix complet jusqu'à 22:50 (prix gelé 22:50→23:05 de toute façon). Les PRIX ne sont
pas contaminés par le swap ; seul le `eod.balance` tardif l'est.

## Conception deux-temps (Option A)

- **Stage 1 — `reconcile.py` à ~21:00 UTC** (timing inchangé) : l'état figé 22:54 (PRÉ-swap)
  → écrit la ligne **dégradée** (PnL réel pré-swap) **EN PREMIER** (garantit toujours un
  résultat) ET fige un snapshot `runtime/eod/preswap_<jour>.json` (equity/balance/positions
  pré-swap + poids/on_day/phase/symbol_specs).
- **Stage 2 — `reconcile.py --upgrade` à ~21:12 UTC** : si le `m5_today.json` du jour est
  arrivé (~21:05) → **replay modèle complet sur ce chemin + clôture pré-swap du snapshot** →
  VRAIE décomposition Δ (signal/coût/timing/micro), et **REMPLACE** la ligne dégradée. Sinon
  no-op (la ligne dégradée reste — **jamais de trou**). Idempotent.
- Le compteur 3-jours utilise le Δ complet quand disponible (sinon le dégradé préserve la série).

## Nouveau timing cron (à appliquer sur GO — `crontab -e` VPS)

```cron
# AVANT
0 21 * * 1-5  …/run_with_env.sh python3 …/reconcile.py            >> …/ftmo_reconcile.log 2>&1
# APRÈS (deux-temps)
0  21 * * 1-5 …/run_with_env.sh python3 …/reconcile.py            >> …/ftmo_reconcile.log 2>&1  # stage 1 (dégradé+snapshot, garanti)
12 21 * * 1-5 …/run_with_env.sh python3 …/reconcile.py --upgrade  >> …/ftmo_reconcile.log 2>&1  # stage 2 (Δ complet via m5 tardif ~21:05)
```
- Stage 1 à 21:00 UTC = **inchangé** ; la ligne dégradée est toujours écrite d'abord.
- Stage 2 à 21:12 UTC = 7 min après l'écriture tardive observée (~21:05). Marge confortable.
- Seam DST 25/10/2026 : décaler les DEUX lignes +1 h (21h→22h, 21h12→22h12), comme la note
  crontab existante pour reconcile.

## Dry-run RÉEL — jeudi 2026-06-18 (le dernier bon m5_today)

Entrées réelles : `m5_today.json` 06-18 (chemin M5 complet) + SOD 06-18 (anchor 9995.50,
départ USDJPY 1.8 long @ 160.752) + clôture pré-swap réelle (target-lock à 21:00 Paris →
**flat, equity=balance=11023.11**) + fills réels 06-18.

```
reconcile 2026-06-18 Δ COMPLET (m5 tardif):
  PnL réel   $+1027.61   ← == gain réel jeudi (11023.11 − 9995.50) ✓
  PnL modèle $+1019.91
  Δtotal     $+7.70
  Δsignal    $+0.00      (pas de rebalance 22:05 — target-lock avant, réel ET modèle)
  Δcost      $+0.62      (slippage des flatten vs half-RT modèle)
  Δtiming    $+0.00
  Δmicro     $-1.56      (micro-ORB réel vs miroir V2+E7)
  résiduel   $+8.64  <  tol $32.16   →  OK (conforme, 0/3)
```

→ **Vraie réconciliation complète sur une journée réelle**, pnl_real exact, résiduel sous
tolérance (les fills réels conforment au sim). Tests : `test_optA_upgrade_full_delta`
(résiduel ~0, ligne remplacée), `test_optA_upgrade_dry_run_matches_pnl` (dry-run n'écrit pas),
`test_optA_upgrade_noop_without_late_m5` (pas de m5 tardif → dégradé intact). Suite : 192 verts.

## Déploiement sur GO (rien d'effectif avant validation)

1. Merge `claude/ftmo-reconcile-optA-2026-06-19` → main, `git pull` VPS.
2. `crontab -e` VPS : ajouter la ligne stage 2 (`12 21 * * 1-5 … --upgrade`).
3. Vérif le 1er soir : `reconcile_log.csv` → ligne du jour `detail_path=…reconcile_<jour>.json`
   (Δ complet) au lieu de `degraded` ; sinon dégradé conservé (m5 tardif manquant ce soir).
4. Garde-fous inchangés : EA/FLAT/targets jamais touchés ; le stage 1 garantit toujours une ligne.
