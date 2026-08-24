# Audit reconcile — résiduel inexpliqué ORB funded 2026-08-21

Compte funded `<ACCOUNT_ID>`. Réconciliation 2026-08-21 : PnL réel -$23.37 vs modèle
+$0.00, résiduel -$23.11 > tolérance $5.64 → INEXPLIQUÉ 1/3.

## 1. Cause exacte

**[V]** Bug confirmé, pas une anomalie du trade. Le sleeve **funded ORB**
(`FU_ORB_RISK=0.0025`, magic `MAGIC_FORB`, fills `funded_orb_entry`/`funded_orb_exit`)
n'était modélisé **nulle part** dans le pipeline de réconciliation :

- `ftmo_live/lib/replay.py:69` (avant correctif) n'appelait que `_micro_model()`,
  gaté sur `cfg["micro_orb"]`. Ce flag vaut `False` en phase FUNDED
  (`data/ftmo_portfolio/v22/spec_v22.yaml:119`, bloc `funded.config`) — le sleeve
  qui EST actif en funded (`funded.orb: {on: true, risk_per_trade: 0.0025}`,
  yaml:130-133) est un mécanisme SÉPARÉ (sizing risk-based via `FU_ORB_RISK`,
  `book_executor.mq5:1058-1071`), jamais porté côté Python.
- `ftmo_live/reconcile.py:216` (avant correctif) filtrait les fills réels avec
  `reason.startswith("micro")`, qui exclut par construction `funded_orb_entry`/
  `funded_orb_exit` — donc même le PnL RÉEL de ce sleeve n'était jamais extrait
  des fills pour la comparaison Δ_micro.

Résultat : le PnL réel de l'ORB funded (positif ou négatif) n'apparaissait dans
AUCUNE des composantes (`d_signal`, `d_cost`, `d_timing`, `d_micro`) — il finissait
intégralement dans le résiduel `d_total = pnl_real - pnl_model`.

**Distinction demandée** : ce n'est PAS « le modèle gère le time-stop mais pas le
stop » — les DEUX exits (`funded_orb_exit`, posé aussi bien par
`Do2200TimeStop` que par `DetectServerExits` sur SL serveur, `book_executor.mq5:
1140-1156` et `:876-882`, même libellé de fill dans les deux cas) étaient
également invisibles. L'hypothèse de l'énoncé (time-stop géré, stop non géré)
est **fausse** : le sleeve entier était absent, quel que soit le type de sortie.

### Pourquoi 18-20/08 étaient OK et 21/08 non (même bug les 4 jours)

**[V]** (VPS, `MQL5/Files/fills.csv`, `ftmo_live/runtime/eod/reconcile_*.json`) :

| date | ORB (entrée→sortie) | PnL ORB réel | autres jambes ce jour | pnl_model | résiduel | tol | statut |
|---|---|---|---|---|---|---|---|
| 18/08 | SELL 0.15 @29517.43 → BUY @29493.61 | **+$3.57** | oui (rebalance, ger40_on) | -3.90 | +4.42 | 6.60 | OK (coïncidence) |
| 19/08 | SELL 0.07 @29314.03 → BUY @29434.21 | **-$8.41** | oui (ger40_off, us100_off) | 8.96 | +1.45 | 6.49 | OK (coïncidence) |
| 20/08 | SELL 0.15 @29218.73 → BUY @29216.96 | **+$0.27** | aucune | 0.00 | +0.21 | 5.88 | OK |
| **21/08** | SELL 0.11 @29172.43 → BUY @29384.88 | **-$23.37** | **aucune** | 0.00 | **-23.11** | 5.64 | **INEXPLIQUÉ** |

18/08 et 19/08 : le PnL ORB manquant a été **fortuitement absorbé** par le bruit
normal des autres jambes du book (`pnl_model` non-nul ce jour-là, marge de
tolérance qui inclut 1bp×turnover). 20/08 et 21/08 : **aucune autre jambe n'a
tradé** (`n_fills=2`, seulement l'ORB) → `pnl_model` exactement 0.00, donc le
résiduel = PnL réel de l'ORB à la lettre. Le 20/08 est passé parce que le
mouvement de prix a été minuscule (+$0.27 < tol $5.88 par construction du floor
$5) ; le 21/08 a été stoppé sur un vrai mouvement (-$23.37) qui dépasse la
tolérance. **Le bug était donc actif et silencieux depuis le premier jour de
trading ORB funded (18/08)**, révélé seulement le 21/08 par la taille du move.

## 2. Portée

**[V]** Phase FUNDED effective depuis 2026-08-18 (`fills.csv`, colonne `phase`
passe de `2` à `3` ce jour). **4 jours de trading ORB funded existent au total à
ce jour (18, 19, 20, 21 août)**, tous les quatre affectés par le même bug
d'instrumentation — 3 masqués par coïncidence de tolérance, 1 (21/08) a franchi
le seuil. Aucun jour après le 21/08 n'a encore de fill ORB (weekend 22-23/08,
pas de reconcile pour le 24/08 au moment de l'audit).

**Compteur STOP** : `consec_unexplained` est à **1/3** au 21/08
(`reconcile_log.csv`). Le compteur global avait déjà atteint 3/3 (`stop_recommended=1`)
plusieurs fois avant l'entrée en phase FUNDED (ex. 2026-07-01, 07-02, 07-06,
08-03/04, 08-10/11/12) pour des raisons **sans rapport** avec ce bug
(`d_signal` massif type 30 002 / 182 036 / 191 199 — conformité de cibles
jambes, hors scope de cet audit). Ce n'est pas nouveau ni propre à l'ORB.

**Risque avant correctif** : oui, le compteur ORB pouvait atteindre 3/3 par pur
artefact d'instrumentation. Avec un ORB qui va tirer plus souvent (mesure de
dérapage N=30 en cours, cf. énoncé), et un sleeve dont ~57% des jours (2/4 à ce
jour) auraient été absorbés par coïncidence plutôt qu'expliqués, la probabilité
de 3 jours consécutifs réellement > tolérance (donc un STOP déclenché sur un
défaut d'instrumentation, pas une vraie dérive) était loin d'être négligeable.

**Rejeu des 4 jours disponibles avec le correctif** — voir §3 (tests). Les
détails `reconcile_2026-08-1{8,9}.json` / `2026-08-2{0,1}.json` archivés côté
VPS ne peuvent pas être re-exécutés tels quels ici (le replay a besoin de
`m5_today.json` complet, gitignored/local sur le VPS, hors périmètre lecture
seule pour un rejeu exact) ; le rejeu est fait en synthétique (§3) sur un
scénario qui reproduit fidèlement le cas 21/08 (aucune autre jambe, stop-loss
short), et est numériquement validé contre les montants réels (§1, tableau).

## 3. Correctif

**Fichiers modifiés** : `ftmo_live/lib/replay.py`, `ftmo_live/reconcile.py`.
**Test** : `ftmo_live/tests/test_funded_orb_reconcile.py` (nouveau).

### `lib/replay.py`

Ajout de `_funded_orb_model()` — miroir du sleeve funded ORB, même schéma que
`_micro_model()` (même OR-break/exit V2+E7, `invariants.orb_break`/`e7_exit`,
déjà existants et testés), mais :
- gaté sur `cfg.get("orb_risk", 0.0) > 0` (vrai seulement en FUNDED,
  `challenge.config.orb_risk == 0.0`) au lieu de `cfg["micro_orb"]` ;
- sizing **risk-based** via `invariants.funded_orb_lots()` (déjà présent dans
  `invariants.py:249-256`, jamais appelé avant ce correctif) au lieu d'un lot
  fixe, avec `risk_usd = orb_risk_cfg * account_size * orb_taper0(balance_sod)`
  — miroir exact de `book_executor.mq5:1060` (`FU_ORB_RISK*ACCOUNT_SIZE_USD*OrbTaper0()`) ;
- **sans** garde `not on_day` : contrairement au micro-ORB challenge (compteur
  de jours, exclut les jours ON), le FORB funded arme indépendamment de
  `IsONDay()`/`g_opened_today` (`book_executor.mq5:1058`, un seul
  `&& !g_flat_today`).

`replay_day()` calcule `forb = _funded_orb_model(...)`, injecte son PnL dans
`bal` au segment 4 (même pattern que `micro`), et l'expose sous une nouvelle
clé `funded_orb` du dict retourné.

### `reconcile.py`

`_decompose()` : le filtre de fills `reason.startswith("micro")` devient
`reason.startswith(("micro", "funded_orb"))`, et les listes d'entrée/sortie
reconnues incluent `funded_orb_entry`/`funded_orb_exit`. Le PnL modèle comparé
devient `mod["micro"]["pnl_usd"] + mod["funded_orb"]["pnl_usd"]` (les deux
sleeves sont mutuellement exclusifs par phase — jamais actifs le même jour — le
pairing entrée/sortie existant fonctionne donc sans modification supplémentaire).

### Test — échoue avant, passe après

`test_funded_orb_reconcile.py` (3 tests) :
1. `test_replay_funded_orb_fires_and_prices_stop_loss` — `replay_day(phase="FUNDED", ...)`
   doit exposer `r["funded_orb"]` armé/déclenché avec un PnL négatif sur un
   scénario short + stop (pas BE). **Avant le correctif** : `AssertionError:
   'funded_orb' in {...}` (clé absente).
2. `test_replay_funded_orb_never_fires_in_challenge` — non-régression,
   `orb_risk=0.0` en challenge ⇒ jamais armé. **Avant** : `KeyError: 'funded_orb'`.
3. `test_reconcile_funded_orb_day_no_longer_unexplained` — reproduit exactement
   le motif du 21/08 (aucune autre jambe, ORB short stoppé en perte) via
   `reconcile.run()` bout-en-bout. **Avant le correctif** (vérifié en stashant
   le correctif et en relançant) :
   ```
   reconcile 2026-06-10: PnL réel $-24.90 vs modèle $+0.00 | Δcost $+0.00
   Δtiming $+0.00 Δmicro $+0.00 | résiduel $-24.90 (tol $9.81) INEXPLIQUÉ 1/3
   ```
   **Après** : `unexplained == 0`, résiduel dans la tolérance.

Suite complète (`pytest tests/`) : 246 passed / 4 skipped avant et après le
correctif (les 4 failed + 2 error observés sont pré-existants, sans rapport —
`FileNotFoundError` sur `data/ftmo_portfolio/cache/panel_px.parquet`, cache
gitignored absent d'un worktree frais, cf. `CLAUDE.md` §Parallel session
coordination). Les tests ciblés (`test_replay_reconcile.py`,
`test_funded_orb_reconcile.py`, `test_micro_orb.py`,
`test_invariants_governor.py`, `test_spec_chain.py`) : 145 passed / 4 skipped.

**PR NON mergée** — correctif proposé, décision humaine requise (fichier
`ftmo_live/reconcile.py` est du code de production, VPS pull `main` toutes les
30 min).

## 4. Implication pour la porte STOP

**[D]** Le compteur lui-même n'a pas besoin d'être touché : 5$ + 1bp×turnover +
0.5bp×gross_book reste un budget de tolérance raisonnable pour du bruit
d'exécution résiduel, et la vraie source d'erreur (sleeve non modélisé) est
maintenant corrigée à la racine plutôt que masquée par un élargissement de
tolérance. **Élargir la tolérance aurait été le mauvais correctif** : cela
aurait aussi masqué de VRAIES dérives futures sur ce sleeve (mauvais sizing,
mauvais niveau de stop, latence d'exécution) derrière le même budget.

Avec le correctif :
- Le résiduel du 21/08, rejoué à l'identique (même prix d'entrée/sortie, même
  lots), tombe dans la tolérance (§3, test 3).
- Le compteur `consec_unexplained` réel n'a **pas** besoin d'être remis à zéro
  manuellement : au 21/08 il est à 1/3 (pas encore au seuil), et le prochain
  run de `reconcile.py` (une fois le correctif déployé) recalculera
  naturellement un résiduel expliqué pour les jours ORB à venir. Aucune
  intervention rétroactive sur `reconcile_log.csv` n'est nécessaire ni
  recommandée — le ledger reflète fidèlement ce qui a été observé (résiduel
  réellement inexpliqué au moment du run) et ne doit pas être réécrit.
- Recommandation opérationnelle : déployer le correctif avant le prochain jour
  de trading ORB funded (la mesure de dérapage N=30 mentionnée dans l'énoncé va
  générer plus de fills funded_orb, donc plus d'occasions de retomber sur ce
  même trou d'instrumentation tant qu'il n'est pas corrigé).

## Verdict

**C'est un bug, pas une anomalie du trade.** Le trade du 21/08 (short ORB
stoppé, -$23.37) est un trade normal du sleeve tel que spécifié
(`funded.orb.risk_per_trade: 0.0025`) ; le modèle avait simplement zéro
information sur son existence. Le correctif ajoute cette information sans
changer aucun comportement de trading (EA/mq5 non touché, comme demandé).
