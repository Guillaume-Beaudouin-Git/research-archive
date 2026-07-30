# Data governance — audit 2026-06-10

Sorti de `CLAUDE.md` §Repo layout (2026-07-30) pour tenir sous la limite de chars Claude Code.
Contenu intégral, aucune info perdue. Audit source : `_audit/dedup_audit_2026-06-10.md`.

- `data/raw/` = sources immuables + manifest dans `data/metadata/` ; caches = régénérables,
  gitignorés.
- Une série = un fichier canonique. M1 FX/indices : `data/deep_history_utc/` (true UTC,
  2007→2026-06, MANIFEST.md). La recherche RÉFÉRENCE `data/`, ne copie jamais.
- Jamais de blobs data dans git (.gitignore : `alpha_hunt/_raw`, `deep_history_utc`, `m5_indices`,
  `_cache_duka`, `data/*.txt`).
- Un subset (plage plus courte) se supprime après migration de ses consommateurs — SAUF provenance
  d'une stratégie validée (ex : NQ Kaggle parquet = validation historique de C).
- Cleanup P0+P1+P2 exécutés 2026-06-10 (tag `pre-cleanup-2026-06-10`, .git 2.1Go→~65Mo). P2 : 13 M1
  m5_indices supprimés (⊂ deep_history POST-réparation trous US500/US100/GER40), consolidations
  FTMO/mtf/audits/docs/oxfordstrat. CONSERVÉS sans superset : US2000_M1.csv, panels parquet EET
  (`*_m1_panel.parquet`), binance/. Détail : `_audit/cleanup_recap_2026-06-10.md`.
- deep_history_utc RÉPARÉ 2026-06-10 (trous 2018-2021 US500/US100/GER40 backfillés Dukascopy, seams
  4/4 PASS ≤1.3bps, MANIFEST machine-généré). Originaux : `*_M1.csv.pre_repair_backup` (~1.1Go, à
  conserver — reproductibilité announcement_premium).
