# M3 — Réalignement D1 indices (US100/GER40) sur la frontière EEST — AVANT/APRÈS (EN ATTENTE DE GO)

> 2026-06-19. **Préparé sur branche, NON déployé.** Suite de
> `SEAM_GER40_INVESTIGATION_2026-06-16.md`. Outil : `data/tools/realign_index_d1_eest.py`
> (défaut dry-run ; `--apply` réécrit le cache gelé). Le panneau alimente le brain →
> **rien n'est appliqué sans GO**.

## Correction d'un point de l'investigation (important)

L'investigation §4 disait que le seam « biaise le poids GER40 via le momentum ». **C'est
inexact pour le book v2.2** : `build_signals` (cleanroom) ne produit de poids que pour
**XAUUSD + USDJPY** ; **GER40/US100 ne sont PAS dans WT** — ce sont des tenues overnight à
**poids fixe `on_w=0.6`** (gouverneur `_target_for_segment`), pas du momentum. Donc :
- le réalignement des indices est **SIGNAL-INVARIANT** (prouvé ci-dessous : WT inchangé) ;
- le notionnel indices `= on_w×scale×eq` est **prix-indépendant** (inchangé) ;
- les lots live sont quantifiés au **prix LIVE** (`state.symbol_specs`), pas au panneau ;
- le **reconcile = 0** (investigation §3 ✓, jamais le panneau gelé).

⇒ Impact réel du seam sur le sizing : **quasi-nul**. Le panneau indices ne sert qu'au
**seam-warn** (cosmétique), au **forecast de swap** (reporting), et au **px-fallback** du
brain (uniquement si le prix live manque). Le réalignement est donc **propre mais à faible
enjeu** — fait sur GO explicite par souci d'hygiène/cohérence.

## Cause racine (mesurée)

Le **M5 source du sim** (`sim_m5_repaired.parquet`) est **déjà en EEST** : son dernier bar
du jour **== la clôture D1 du broker** (export EA). Vérifié sur **511 dates** :

| légs | M5-dernier-bar vs EA (médiane) | (max) |
|---|---|---|
| GER40 | **0.000 bps** | 17.2 |
| US100 | **0.000 bps** | 36.4 |

Mais `panel_px.parquet` (panneau 25-instruments, autre pipeline) construit ses colonnes
indices avec une **autre convention d'heure de clôture** → seam systématique vs EA :

| légs | panel actuel vs EA (médiane) | (max) | tail_max (seam loggé) |
|---|---|---|---|
| GER40 | 15.95 bps | 921.7 | **96.7** |
| US100 | 8.76 bps | 279.5 | **30.5** |

**Le fix = reconstruire `panel_px[US100,GER40]` depuis le dernier bar M5 du jour** (= EEST
= EA). On NE touche PAS XAUUSD/USDJPY (ils alimentent le signal).

## AVANT / APRÈS (dry-run `realign_index_d1_eest.py`, 2026-06-19)

| métrique | AVANT | APRÈS | note |
|---|---|---|---|
| Seam GER40 (tail_max / médiane vs EA) | 96.7 / 15.95 bps | **17.2 / 0.000** bps | sous le warn 30 bps ✓ |
| Seam US100 (tail_max / médiane vs EA) | 30.5 / 8.76 bps | 36.4 / **0.000** bps | médiane→0 ; le tail 36 = bruit de granularité M5 5-min sur 1-2 dates récentes, pas le seam de convention |
| Couverture US100 | …→2026-05-27 | …→**2026-06-05** | +7 jours (trou comblé) |
| Couverture GER40 | …→2026-05-26 | …→**2026-06-05** | +8 jours (trou comblé) |
| **WT (XAUUSD,USDJPY) build_signals** | — | **IDENTIQUE** | signal-invariant ✓ |
| ON (jours ON) | — | **IDENTIQUE** | ✓ |
| Notionnel GER40/US100 (on_w×scale×eq) | — | **inchangé** | prix-indépendant |

Preuve d'invariance reproduite indépendamment (perturbation +1 % de
GER40/US100/US500/US30 → WT byte-identique), `build_signals` ne lisant que XAU/JPY.

## Caveats & chemin de déploiement (sur GO)

1. **Changement du panneau GELÉ** : `panel_px`/`panel_rets` sont la donnée de validation des
   462 cohortes — MAIS les cohortes (`load_market`) lisent le **M5**, pas les colonnes indices
   du panneau ; et `build_signals` ne lit pas les indices → réalignement sans effet cohortes/signal.
2. **`sim_m5_repaired.parquet` est LOCAL, ABSENT du VPS** (cf. test_brain_dryrun en échec VPS).
   Donc `--apply` se lance **en local** (où le M5 existe) → puis **scp** `panel_px.parquet` +
   `panel_rets.parquet` vers `~/projects/Algo_claude/data/ftmo_portfolio/cache/` du VPS. Les
   parquet sont gitignorés (data-governance : pas de blob data en git) → non commitables.
3. **Backups** : `--apply` écrit `*.pre_realign_backup` avant de réécrire.
4. **Vérif post-déploiement** : `brain.py --dry-run` → `audit.data.seams_bps` GER40 < 30
   (US100 peut rester ~30-36 par bruit M5 ; le seam de convention systématique est résolu).
5. **US100 tail 36 bps** : si gênant, augmenter `SEAM_WARN_BPS` (lib/marketdata) à ~40, ou
   accepter (le warn US100 résiduel = bruit M5 5-min, pas une dérive de convention).

## Recommandation

Le seam de convention est **réel et corrigé proprement** par cet outil (médiane→0, couverture
comblée, signal-invariant). Mais l'**enjeu sizing est quasi-nul** (indices = poids fixe, prix
live pour les lots, reconcile insensible). **Décision suggérée** : appliquer (hygiène + le
px-fallback/forecast deviennent corrects + couverture complète) OU accepter en l'état (le
seam-warn documente). À votre GO pour `--apply` + scp VPS.
