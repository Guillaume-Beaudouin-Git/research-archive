# Ledger n_tests — convention et milestones

Sorti de `CLAUDE.md` (2026-07-30) pour tenir sous la limite de chars Claude Code. Contenu intégral,
aucune info perdue. Référence : `CLAUDE.md` §Research history.

## Convention n_tests (2026-06-10) — DEUX registres
1. **GLOBAL = 321** — ledger historique canonique, FIGÉ 2026-05-30.
2. **PROGRAMME (depuis 2026-06)** — chaque programme tient un compteur cumulatif LOCAL nommé
   (ex : fx_intraday_deepdive N_ledger 108→240 ; backwardation_oil « program N 112→115 » ;
   ftmo_candidate_funnel 97→103). Règle d'incrément : toute CONFIGURATION backtestée compte ;
   data-validation pure ne compte pas ; « if swapping it could have been the winner, it counts ».
   Les corrections multi-tests (AMTP/DSR) d'une étude alimentent le compteur de SON programme,
   pas le global.

**Jonction** : `global_courant = 321 + Σ deltas des programmes post-2026-05-30` (non-overlapping —
tout test post-05-30 passe par UN registre programme). Réconcilier à la CLÔTURE de chaque programme
en ajoutant son delta. Ne JAMAIS additionner les sous-totaux pré-2026-05-30 (overlap).

## Milestones globaux séquentiels
Source autoritative : README §6.55 (confirmed line 1594).

| N | Signification |
|---|---|
| 83 | sous-total equities/ETF/options (README §10) : crypto-era tests 1–53, FX carry 4, multi-asset 5+1, NQ ORB IVB 3, equities 14, options 1 |
| 142 | crypto V1 OHLCV missions complete (6.01–6.36, README §6.51) |
| 159 | all crypto missions complete (V1+V2+V3, README §6.55 cumulative) |
| 170 | FX London ORB v1 archived (+28 from base 142) |
| 175 | Strategy E pre-registration (+1 after Strategy D closure at n=174) |
| 180 | Round Number Cascade complete (+5 EUR/GBP IC horizons, 175→180) |
| 321 | final : after NQ iter_1–10 (~82+ NQ sub-count), indices_swing Sprint 1+2 (100), remaining crypto V2/V3 + options VRP phases |

⚠ **IMPORTANT** : les sous-totaux (83, 159, 180) SE CHEVAUCHENT / OVERLAP — les 53 tests crypto-era
equities comptent dans 83 ET 159. Ne PAS additionner les sous-totaux ; seuls les milestones
séquentiels ci-dessus sont additifs.

2026-05-30 : tranché **321** (majoritaire, cohérent README §1 header). h31_cs_fs_dn (test #160) déjà
consommé, archivé 2026-05-30 (FAIL).
