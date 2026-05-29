## Infra non catégorisée (2026-05-29)

- Fichiers : `run_manual_signal.sh` + `com.algo_claude.manual_signal.plist`
- Trouvés dans : `Futures/live/strategy_c_live/` (placement erroné — jamais mergé sur main avant ce nettoyage)
- Sauvegardés sur : branche `origin/claude/crypto-audit-2026-05-28`
- Actuellement sur main : `Futures/research/active/strategy_d_nq/infra/` (mergé via PR #48, auto-merge CI déclenché sur pattern `claude/*`)

### Mystère
Le `.sh` appelle `Futures.live.strategy_c_live.manual_signal` (= engine iter_10 de C),
mais a été supposé être de la Strategy D lors du nettoyage du repo.

### À trancher
- Infra C mal nommée (paper launcher pour iter_10 qui n'avait pas sa place dans live/) ?
- OU brouillon D réutilisant provisoirement l'engine C ?

### Vérifications à faire
- `launchctl list | grep algo_claude` — vérifier si jamais installé
- Chercher logs du module : `~/Desktop/Algo_claude/Futures/live/strategy_c_live/logs/manual_signal*.log`
- Confirmer si Strategy D a un signal propre ou n'est qu'une intention pour l'instant

### Chemins stale à corriger avant tout usage
Le `.plist` et le `.sh` pointent encore vers `Futures/live/strategy_c_live/`.
`REPO_ROOT` dans le `.sh` est aussi cassé (3 niveaux au lieu de 5 depuis le nouvel emplacement).

### NE PAS merger dans live/ tant que non résolu.
