#!/usr/bin/env bash
# Cleanup doublons — généré par l'audit _audit/dedup_audit_2026-06-10.md
# USAGE:  DRY_RUN=1 ./scripts/cleanup_dedup_2026-06-10.sh p0   (défaut: dry-run)
#         DRY_RUN=0 ./scripts/cleanup_dedup_2026-06-10.sh p1   (exécution réelle)
# Phases: p0 (hygiène) | p1 (doublons faible risque) | p2 (consolidation — PRÉ-REQUIS: migration m5_indices)
# P3 (racine live + crons VPS + filter-repo) volontairement ABSENTE de ce script: session dédiée.
set -euo pipefail
cd "$(dirname "$0")/.."
DRY_RUN="${DRY_RUN:-1}"
run() { if [ "$DRY_RUN" = "1" ]; then echo "[DRY] $*"; else echo "[RUN] $*"; eval "$@"; fi; }

guard_tag() {
  if ! git rev-parse "pre-cleanup-2026-06-10" >/dev/null 2>&1; then
    run "git tag pre-cleanup-2026-06-10"
  fi
}

p0() {
  echo "=== P0 — hygiène (zéro risque) ==="
  echo "--- RAPPEL MANUEL AVANT TOUT: commiter le code live untracked:"
  echo "    Futures/live/orb_floor_ftmo/  PropFirms/ftmo*  Forex/research/active/fix_reversal/"
  echo "    + Futures/research/active/nq_intraday/engine.py (modifié, coût \$29 RT post-audit)"
  guard_tag
  find . -path ./.git -prune -o -name ".DS_Store" -print | while read -r f; do run "rm '$f'"; done
  find . -path ./.git -prune -o -type d -name "__pycache__" -print | while read -r d; do run "rm -rf '$d'"; done
  run "rm -rf .pytest_cache data/deep_history_m1/_tool/node_modules"
  # .bak — UNIQUEMENT après commit de engine.py/results.json courants (l'ancien est dans HEAD)
  if git diff --quiet Futures/research/active/nq_intraday/engine.py 2>/dev/null; then
    run "rm 'Futures/research/active/nq_intraday/engine.py.bak_2026-06-07'"
    run "rm 'Futures/research/active/nq_intraday/results.json.bak_2026-06-07'"
  else
    echo "[SKIP] engine.py a des modifs non commitées -> .bak conservés"
  fi
  run "rm 'data/panels/process_raw_filter.py.bak'"
  run "rm 'data/oxfordstrat_109/.git/index.lock.bak'"
}

p1() {
  echo "=== P1 — doublons confirmés, faible risque ==="
  guard_tag
  # 1. alpha_hunt/_raw: sortir de git, ignorer, purger >7 jours, garder les récents pour la cron
  run "git rm -r --cached --quiet _automation/alpha_hunt/_raw"
  grep -q "alpha_hunt/_raw" .gitignore || run "printf '\n# raw scraper pulls — dédup logique dans _seen.json\n_automation/alpha_hunt/_raw/\n' >> .gitignore"
  run "find _automation/alpha_hunt/_raw -type f -mtime +7 -delete"
  echo "[TODO MANUEL] patcher le scraper VPS pour ne plus commiter _raw/"
  # 2. Dukascopy annuels data/raw (subsets des agrégés _2020_2024)
  for s in EURUSD GBPUSD; do for y in 2020 2021 2022 2023 2024; do
    run "rm -f 'data/raw/dukascopy_${s}_${y}.parquet'"
  done; done
  # 3. yfinance daily subsets (couverts par funnel cache 2007-2026)
  run "rm -f data/raw/yf_*_1d_*.parquet"
  # 4. s076 dailies EET (UTC = canonique, gate tz validée)
  run "rm -f research/s076_replication/daily/*_EET.parquet"
  # 5. cip_eoq active = copie exacte de archived (sans POSTMORTEM)
  run "git rm -r --quiet Forex/research/active/cip_eoq"
  # 6. graphify-out (artefact régénérable)
  run "rm -rf graphify-out"
  # 7. caches des programmes FTMO CLOS (PAS fx_intraday_deepdive: actif)
  run "rm -rf research/ftmo_candidate_funnel/cache research/ftmo_candidate_funnel_v2/cache research/paper_triage/cache"
  echo "[FIN P1] commit suggéré: git commit -am 'cleanup P1: dédoublonnage données (audit 2026-06-10)'"
}

p2() {
  echo "=== P2 — consolidation structurelle ==="
  echo "PRÉ-REQUIS BLOQUANT: les 5 consommateurs de m5_indices migrés vers deep_history_utc"
  echo "  (pairs_btceth_D, ftmo_twoSided_makeOrBreak, fix_reversal, _breakoutprop_fit, ftmo_portfolio_audit)"
  echo "  + test non-régression tz EET->UTC passé. Confirmer puis relancer avec P2_CONFIRM=1."
  [ "${P2_CONFIRM:-0}" = "1" ] || return 0
  guard_tag
  # 1. m5_indices: M1 FX/indices dupliqués (deep_history_utc = canonique) + panels dérivés
  for f in data/panels/m5_indices/{AUDJPY,AUDUSD,EURGBP,EURJPY,GBPUSD,GER40,NZDUSD,US100,US2000,US30,US500,USDCAD,USDCHF,USDJPY}_M1.csv \
           data/panels/m5_indices/m1_close.csv data/panels/m5_indices/m5_{open,high,low,close}.csv; do
    run "rm -f '$f'"
  done
  # garder: binance/ (seule copie crypto M1), *_M5.csv (consommés? vérifier), samples
  # 2. Cache M5 (consommateurs archivés uniquement; re-DL ~12min/paire-an si besoin)
  run "rm -rf Forex/data/cache/dukascopy_m5"
  # 3. Archive externe du cache M1 source (à adapter: chemin du disque)
  echo "[MANUEL] rsync -av data/deep_history_m1/_cache_duka/ /Volumes/<DISQUE>/algo_archive/_cache_duka/ && rm -rf data/deep_history_m1/_cache_duka"
  # 4. Consolidation FTMO -> un seul home
  run "mkdir -p PropFirms/ftmo/program_2026-06"
  for d in research/PROGRAM_DECISION_MEMO.md research/ftmo_candidate_funnel research/ftmo_candidate_funnel_v2 \
           research/ftmo_portfolio_audit research/ftmo_survivors_book research/b1_feasibility research/edge_improvement \
           research/commodity_carry_feasibility research/container_eval research/paper_triage research/positive_dsr_register \
           research/propfirm_scan research/s076_replication data/ftmo_research data/ftmo_universe \
           Futures/research/active/ftmo_3strats_audit_2026-06 PropFirms/ftmo_alpha_program \
           PropFirms/ftmo_decorrelated_portfolio PropFirms/ftmo_paper_edges PropFirms/propfirm_pass_plan; do
    run "mv '$d' PropFirms/ftmo/program_2026-06/ 2>/dev/null || true"
  done
  # fx_intraday_deepdive = ACTIF -> home par classe d'actif
  run "mv research/fx_intraday_deepdive Forex/research/active/fx_intraday_deepdive"
  run "rmdir research 2>/dev/null || true"
  # 5. mtf éclaté -> un seul dossier archivé
  run "mkdir -p Multi_Asset/research/archived/mtf_a1_tsmom"
  run "mv code/mtf Multi_Asset/research/archived/mtf_a1_tsmom/code"
  run "mv data/mtf_survey Multi_Asset/research/archived/mtf_a1_tsmom/data"
  run "mv outputs/mtf Multi_Asset/research/archived/mtf_a1_tsmom/outputs"
  run "rmdir code 2>/dev/null || true"
  # 6. audits -> _audit/
  run "mkdir -p _audit/2026-06_instrument_schema"
  run "mv audit/* audit-fetch-B/* _audit/2026-06_instrument_schema/ 2>/dev/null || true"
  run "rmdir audit audit-fetch-B 2>/dev/null || true"
  # 7. docs stales + readme legacy
  run "mkdir -p docs/archive/2026-04"
  run "git mv docs/strategy_*.md docs/archive/2026-04/ 2>/dev/null || mv docs/strategy_*.md docs/archive/2026-04/"
  run "mv readme docs/archive/legacy_crypto_readme.md"
  # 8. oxfordstrat: sortir de data/, retirer le .git imbriqué
  run "mkdir -p Multi_Asset/research/archived"
  run "rm -rf data/oxfordstrat_109/.git"
  run "mv data/oxfordstrat_109 Multi_Asset/research/archived/oxfordstrat_109_audit"
  # 9. recherche NQ: verdicts FAIL -> archived
  run "mv Futures/research/active/nq_intraday_vwap Futures/research/archived/nq_intraday_vwap"
  # 10. strategy_d_nq -> fusion dans strategy_d
  run "mkdir -p Futures/research/active/strategy_d/infra"
  run "mv Futures/research/active/strategy_d_nq/infra/* Futures/research/active/strategy_d/infra/"
  run "rm -rf Futures/research/active/strategy_d_nq"
  echo "[FIN P2] mettre à jour CLAUDE.md (§7 du rapport) + commit"
}

case "${1:-}" in
  p0) p0 ;;
  p1) p1 ;;
  p2) p2 ;;
  all) p0; p1; p2 ;;
  *) echo "usage: DRY_RUN=0 $0 {p0|p1|p2|all}  (DRY_RUN=1 par défaut)"; exit 1 ;;
esac
