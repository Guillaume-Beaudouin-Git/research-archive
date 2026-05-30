# LOT 3 — Simulations impactées par TV_TRAILING_DD=2_000 (à recomputer)

**Fix appliqué** : `Futures/research/active/nq_intraday/analysis/propfirm_compat_v2.py:750`
`TV_TRAILING_DD = 2_000` → `1_000` (aligné sur la valeur live confirmée 2026-05-25 dans
`Futures/live/strategy_c_live/config.py:103`).

**Impact** : tous les outputs de `tradeify_eval_90d` (et fonctions sœurs `_simulate_tradeify_eval`)
exécutés AVANT le fix utilisaient un coussin trailing DD deux fois plus large que le live
($2,000 vs $1,000 réel). Effet directionnel : **bust rate sous-estimé, pass rate surestimé**.
Les chiffres archivés sont donc trop optimistes.

## Entries `results.json` à recomputer

Fichier : `Futures/research/active/nq_intraday/results.json`

| Index | Iteration | n_tests | Champs Tradeify pollués | Verdict actuel (à revérifier post-fix) |
|---|---|---|---|---|
| `[41]` | iter_11a | 143 | `p_pass_30d=2.90, p_pass_90d=28.95, p_bust_90d=9.43` | IMPROVE |
| `[42]` | iter_11b | 144 | `p_pass_30d=3.78, p_pass_90d=31.83, p_bust_90d=7.10` | RESEARCH_PASS |
| `[43]` | iter_11c | 145 | `p_pass_30d=2.98, p_pass_90d=27.74, p_bust_90d=5.83` | RESEARCH_PASS |
| `[44]` | iter_11d | 146 | `p_pass_30d=5.53, p_pass_90d=38.18, p_bust_90d=12.47` | IMPROVE |
| `[45]` | iter_11e | 147 | `p_pass_30d=3.55, p_pass_90d=31.95, p_bust_90d=10.51` | IMPROVE |

Note : `p_eval_90d=NaN` aux entries [47]-[51] suggère que la simulation Tradeify a échoué
pour ces variantes (pas de pollution numérique mais signal d'un bug de pipeline orthogonal).

## Cohérence sémantique du module post-fix

⚠ Le fix aligne uniquement `TV_TRAILING_DD`. Les autres constantes du module reflètent
encore la cible Tradeify Select Flex **$50K** (obsolète) :
- `TV_INITIAL = 50_000` (live = 25_000)
- `TV_LOCK_BALANCE = 52_100` (live = 26_100)
- `TV_LOCKED_FLOOR = 50_100` (live = 25_100)
- `TV_EVAL_TARGET = 3_000` (live = 1_500 pour 6% de $25K)

Conséquence : le module simule un compte hybride incohérent ($50K notional mais coussin
$1,000). Cela rend les outputs post-fix **également inutilisables** tant que le refactor
$50K → $25K complet n'est pas effectué.

## Recommandation (hors scope LOT 3)

1. **Refactorer le bloc `# Tradeify Select Flex` de `propfirm_compat_v2.py:745-770`** en
   $25K (TV_INITIAL=25_000, TV_LOCK_BALANCE=26_100, TV_LOCKED_FLOOR=25_100, TV_EVAL_TARGET=1_500,
   TV_TRAILING_DD=1_000) — OU mieux : importer directement depuis
   `Futures/live/strategy_c_live/config.py` (TRADEIFY_INITIAL_BALANCE, TRADEIFY_TRAILING_DD,
   TRADEIFY_LOCK_BALANCE, TRADEIFY_LOCKED_FLOOR) pour éviter la duplication.
2. Re-runner `iter_11_propfirm.py` et `iter_d_pairs.py` / `iter_d2_mr.py` post-refactor.
3. Mettre à jour les entries [41]-[45] de `results.json` avec les nouveaux p_pass / p_bust.
4. Réévaluer les verdicts (RESEARCH_PASS pour iter_11b/c notamment — le seuil pourrait basculer).

## Scripts importateurs (n'utilisent que TV_TRAILING_DD, donc impactés par le fix)

- `Futures/research/active/nq_intraday/analysis/iter_11_propfirm.py:50,206,210`
- `Futures/research/active/nq_intraday/analysis/iter_d_pairs.py:47,669,672`
- `Futures/research/active/nq_intraday/analysis/iter_d2_mr.py:45,167,959`

Aucun output `.json`/`.md` archivé n'a été trouvé pour iter_d_pairs et iter_d2_mr — leurs
résultats étaient en console seulement.

## Status

- [x] Fix appliqué `propfirm_compat_v2.py:750` (2_000 → 1_000)
- [x] Fix appliqué `iter_11_propfirm.py:193` (docstring)
- [x] Entries impactées identifiées et listées ci-dessus
- [ ] Recompute des sims — **NON APPLIQUÉ ICI** (hors scope LOT 3, à programmer)
- [ ] Refactor full $50K → $25K — **NON APPLIQUÉ ICI** (hors scope LOT 3)
