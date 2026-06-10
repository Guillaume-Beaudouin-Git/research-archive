# Migration tz fix_reversal → deep_history_utc — memo avant/après

**Date :** 2026-06-10
**Nature :** fix de SOURCE DE DONNÉES uniquement — `PANEL` repointé de
`data/panels/m5_indices/EURUSD_M1.csv` (EET/EEST broker mislabelé `timestamp_utc`, 2018-2026,
fichier aujourd'hui supprimé) vers `data/deep_history_utc/EURUSD_M1.csv` (TRUE UTC, 2007→2026-06,
spread calibré, MANIFEST machine-généré). **Aucune ligne de logique stratégie modifiée**
(fenêtres, signaux, coûts, stats inchangés — 1 ligne `PANEL` par script + docstring).
**Budget 3 mods : 0 consommé** — un fix de données n'est pas une modification d'hypothèse
(les hypothèses pré-enregistrées Krohn/Ranaldo sont enfin testées telles qu'écrites).

---

## 1. Root cause (audit checklist `_audit/m5_indices_migration_checklist_2026-06-10.md`)

`load_panel()` de step0 et step1 fait `tz_localize("UTC")` sur `timestamp_utc` **sans aucune
compensation** → cas 1 de la checklist. L'ancienne source étant en EET (UTC+2) / EEST (UTC+3),
toutes les fenêtres étaient décalées de **2-3 h en temps réel** :

| Fenêtre codée (« UTC ») | Heure réelle mesurée (hiver/été) | Ce que c'était vraiment |
|---|---|---|
| Tokyo fix 00:50-01:00 | 22:50-23:00 / 21:50-22:00 UTC | **Spike de rollover broker** (minuit serveur MT5 ≈ 17h NY) |
| ECB fix 13:10-13:20 (w) | 11:10-11:20 UTC | Fin de matinée Londres |
| London fix 15:55-16:05 (w) | 13:55-14:05 UTC | Open NY |
| Segmentation 03/11/16 ET | décalée −2/−3 h | Sessions déplacées |

Les résultats du 2026-06-02 (rapport `FIX_REVERSAL_FTMO.md`) sont **INVALIDES en tant que test
des hypothèses pré-enregistrées** : aucun fix réel n'a été mesuré. Anciens outputs préservés en
`*.pre_tz_migration.{json,csv}` — ne rien supprimer.

## 2. Vérification empirique de la nouvelle source (`tz_verification.py`, 3/3 PASS)

1. **Rollover** : top-8 minutes par spread médian toutes dans **21:03-21:58 UTC** (17h NY) — plus rien à minuit.
2. **Fix WMR Londres (volume)** : bump hiver 15:55-16:05 ratio **1.38** (contrôle 14:55 : 1.08) ;
   bump été 14:55-15:05 ratio **1.17** (contrôle 15:55 : 0.91) — suit exactement la saison DST.
3. **Vrai Tokyo fix 00:50-01:00 UTC** : spread med 3 / p95 13 pts — l'ancien « med 17 / p95 46 pts »
   était l'artefact rollover.

## 3. Avant / après

### step0 — cost stack RT (bps, markup×1)

| Fenêtre | EET-era (2018-2026) | TRUE UTC (2007-2026) | Lecture |
|---|---|---|---|
| London/ECB fix | 2.23 | **2.48** | spread p95 identique (8 pts) ; slippage ATR 1.08→1.33 (échantillon 19 ans) |
| Tokyo fix | 5.59 | **2.92** | l'ancien 4.07 bps de spread p95 était le rollover ; réel = 1.15 bps |

L'unconditional (p95 1.15 bps RT) reste comparable — seule stat de l'ancien run indépendante de l'heure.

### step1 Pattern A — fix-reversal (delay=0, markup×1)

| | N | gross bps | gross t | net bps | net SR |
|---|--:|--:|--:|--:|--:|
| **EET-era pooled** | 6 468 | 0.22 | 1.62 | -3.11 | -4.43 |
| **TRUE UTC pooled** | 15 039 | **0.07** | **0.59** | -2.55 | -2.74 |

Sur les vraies fenêtres, le gross résiduel disparaît (London 0.45→0.05 ; ECB 0.19→-0.03 ;
Tokyo 0.03→0.19). **Il n'y a pas de fix-reversal mesurable sur EURUSD.**

### step1 Pattern B — segmentation Ranaldo (delay=0, markup×1, cost 2.48/leg)

| Leg | EET-era gross (t) | TRUE UTC gross (t) | TRUE UTC net SR |
|---|---|---|--:|
| short 03-11 ET | 1.37 (2.23) | 1.31 (**2.55**) | -0.48 |
| long 11-16 ET | -0.13 (-0.24) † | 0.76 (**2.62**) | -1.17 |
| combined | 1.23 (1.54) | **2.07 (3.55)**, SR gross 0.73 | **-1.02** |

† L'« asymétrie L25 » (long-leg dead) du rapport original était un artefact tz : avec les vraies
heures ET, **l'edge est two-sided propre** (les deux jambes t>2.5). Mais gross 2.07 < coût 4.96
(2 RT/jour) → mort au coût, proprement cette fois.

### step1b — EOM up-sizing : l'angle disparaît

EET-era : London EOM gross 1.42 bps (×3.2 vs ALL) — interprété « mécanisme flow EOM réel ».
TRUE UTC : London EOM **-0.27** ; meilleur subset toutes combinaisons = 0.18 bps. **Artefact tz.**

### step1c — splits temporels (périmètre 2018-2026 constant → isole l'effet tz pur)

EET-era : « London gross émerge 2023-2026 (1.35, t=1.87) ». TRUE UTC : 2023-24 = 0.35 (t=0.78),
2025-26 = -0.11 (t=-0.21). Max tous splits = London 2021-22 : 0.86 (t=1.61, sous gate). **Artefact tz.**
(Les splits 1c restent bornés à 2018+ par construction — le pré-2018 du nouvel échantillon
n'y figure pas, bornes du script inchangées par discipline de non-modification.)

## 4. Verdict post-migration

**NO-GO inchangé sur les deux patterns — désormais établi sur des fenêtres valides.**
Corrections matérielles au narratif du rapport original :
- Pattern A : la mort n'est plus « gross 5× plus petit que la littérature » mais **absence totale
  de signal au fix** (pooled t=0.59 sur N=15k, 19 ans).
- Le coût Tokyo cité (5.59 bps) était un artefact (réel : 2.92).
- L'angle EOM et l'« émergence 2023+ » disparaissent.
- Pattern B : seul survivant gross (two-sided, t=3.55, SR gross 0.73) — tué uniquement par le
  tier de coût retail (besoin < ~1 bps RT/leg pour net positif). Cœur du candidate **L34
  (tier institutionnel uniquement) : CONFIRMÉ et renforcé** ; sa clause sur l'asymétrie L25
  doit être retirée/reformulée (l'asymétrie était l'artefact, pas le pattern).

**n_tests : aucun nouveau test consommé** (re-run des hypothèses pré-enregistrées sur source
corrigée). Échantillon étendu 2007→2026 = bonus checklist (d).

## 5. Artefacts

- `tz_verification.py` — vérification empirique de la convention horaire (à re-runner si la
  source canonique change).
- `*.pre_tz_migration.{json,csv}` — anciens résultats EET-era (2026-06-02), préservés, INVALIDES.
- `step0_costs.json`, `step1_results.json`, `step1b_eom_results.csv`, `step1c_oos_split.csv` —
  régénérés 2026-06-10 sur TRUE UTC.
- `FIX_REVERSAL_FTMO.md` — rapport original conservé avec banner d'invalidation en tête ;
  ses tableaux restent l'état EET-era documenté.
