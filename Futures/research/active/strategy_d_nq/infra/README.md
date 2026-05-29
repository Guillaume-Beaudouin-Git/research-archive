Infra paper Strategy D (NQ décorrélée). NON validée.
Relogée depuis Futures/live/strategy_c_live/ (placement erroné).
Ne pas traiter comme live tant que D n'a pas passé PROPFIRM_PASS.

## Contenu

- `run_manual_signal.sh` — script shell déclenchant le signal paper NQ (09:43 ET)
- `com.algo_claude.manual_signal.plist` — agent launchd correspondant (non installé)

## Chemins stale à corriger avant tout usage

Le `.sh` et le `.plist` référencent encore `Futures/live/strategy_c_live/`.
À mettre à jour vers le nouvel emplacement si déployés.
`REPO_ROOT` dans le `.sh` doit aussi être recalculé (5 niveaux depuis ce dossier,
pas 3).
