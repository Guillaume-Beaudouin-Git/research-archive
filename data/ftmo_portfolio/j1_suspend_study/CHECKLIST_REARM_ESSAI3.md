# VOLET 3 — Checklist de réarmement compte #3 (FTMO $10k SWING)

Comptes morts : <ACCOUNT_ID> (02/07, post-mortem repo), <ACCOUNT_ID> (03/07, rapporté opérateur — pas
encore au dépôt). **Ops MANUELLES en VNC — rien exécuté ici.** Réfs : `book_executor.mq5`,
`RUNBOOK_BURNIN_SWING.md §Armement propre` (incident 2026-06-16).

## A. Purger l'état hérité (AVANT d'armer)
`ea_state.json` est PARTAGÉ (MQL5/Files, per-terminal) → hérité au switch de compte. `LoadState`
est date-gardé : `if(anchor_date != ParisDate()) return` (mq5:1410). **Danger si armement le MÊME
jour qu'un breach** : recharge l'ancre morte (anchor_balance post-perte → `DailyFloor=ancre−500`
décalé → breach immédiat) + `open_days`.
- [ ] Archiver puis **`rm ea_state.json`** (LoadState no-op → globals à false → OnInit ré-ancre).
      ⚠ ré-init aussi anchor_balance/open_days/zombie — OK uniquement compte neuf (eq 10000, open_days 0).
- [ ] `FLAT` **absent** (retirer le `touch FLAT` d'observation).

## B. attempt_start (input EA, PAS dans ea_state.json)
- [ ] `InpAttemptStart = <date d'armement, 00:00>` — **REQUIS en challenge** (OnInit:1444
      `INIT_FAILED` si 0 ; ancre `pace`). Re-saisir en VNC **et persister le profil**.

## C. Piège ProfileLast (common.ini) — VPS MT5-GUI, hors repo
MT5 n'écrit `ProfileLast` qu'à une **fermeture PROPRE** (jamais au `kill -9`, runbook L181-186).
`ProfileLast=ftmo_swing` alors que le profil actif = `FTMO_2ème_essai` → un restart watchdog
rechargerait mauvais profil + mauvaise date.
- [ ] **Fermeture propre de MT5** (hors créneau, **sans position ouverte**), bon profil actif →
      ProfileLast se fige dessus.
- [ ] Test de survie `kill -9` + relance → vérifier ligne INIT `book_executor v2.2 INIT` au log
      (le watchdog vérifie exactement ça).

## D. Algo/Auto-Trading ON
Après toute manip VNC / rechargement de profil, Algo Trading peut repasser OFF (ret=10027 vécu → book paralysé).
- [ ] Vérifier **AutoTrading ON** ; au log Experts : `SPEC OK v2.2.2 sha 3e7626f6d3fd…`,
      4× `UPU <sym>: … usd_per_unit>0`, `book_executor v2.2 INIT — phase 1…`. `INIT REFUSÉ` = STOP.

## E. flat_today collé (incident 2026-06-16)
`touch FLAT` pose `g_flat_today=true`, purgé UNIQUEMENT par le rollover 00:00 Paris ; `rm FLAT` en
journée **ne ré-arme PAS** (17:35/22:05 court-circuitent en silence, mq5:992/1055 ; LoadState
recharge flat_today=1 si anchor_date inchangé, mq5:1410,1414).
- [ ] **Ne jamais `touch FLAT` en mode armé.** Armer **hors créneau 15:30-21:00 UTC, sans position
      ouverte** ; si latch (`flat_today=1 && kill=0`) → attendre rollover OU `rm ea_state.json` +
      restart hors créneau. Filet `supervisor.py` alerte `flat_latched`.

## F. Vérif fin d'armement (state.json, compte neuf 10000) — recalculé sur le code EA
| Champ | Attendu | Source |
|---|---|---|
| anchor_balance | **10000** | DayRollover:1105 |
| open_days | **0** | globals init + ea_state purgé |
| phase (InpPhase) | **P1 (1)** | input |
| attempt_start | **jour d'armement** | InpAttemptStart |
| kill | **0** | FLAT absent |
| flat_today | **0** | non collé |
| static_floor | **9000** | `10000·(1−0.10)`, mq5:168 |
| daily_floor | **9500** | `anchor−500`, mq5:170 |
| breaker_line | **9650** | `LimEff+0.30·500`, mq5:172 |
| Algo Trading | **ON** | log INIT |
(Le post-mortem citait 9427/9577 — ancre érodée ~9927 ; compte neuf ancré 10000 ⇒ 9500/9650.)

## G. Décision sizing — À TRANCHER EN PARALLÈLE (hors périmètre suspension, mais bloquant)
Le breach = **sizing** (J1 16.8× / $173k sur floor $1k). LCAP8 + suspension **ne suffisent pas**
à un gap multi-yen (levcap Q4 : survivre 3-yen exige ≤5.4×). La suspension coupe l'exposition **en
zone** ; hors zone, J1 reste sizé par le gouverneur (vol-target inverse → gros notionnel low-vol).
- [ ] Décider : (a) déployer le gate suspension (ce dossier, GO requis), **ET** (b) trancher LCAP8
      (levcap study, ADOPT) / réduction de sizing J1. Les deux sont complémentaires, pas alternatifs.
- [ ] Tant que USDJPY ≥ 161.95 défendu et J1 non capé/suspendu déployé : **ne pas armer J1** (ou
      armer avec gate + cap actifs). Le book tourne sur XAUUSD + US100 + GER40 (les 3 autres sleeves).
