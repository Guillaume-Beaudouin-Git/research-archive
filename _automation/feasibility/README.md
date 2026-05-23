# Pipeline de Faisabilité des Hypothèses Alpha

Ce pipeline teste les hypothèses accumulées dans `_automation/alpha_hunt/promising/*.md`
via trois niveaux de gates statistiques, du moins au plus coûteux en n_tests.

---

## Vue d'ensemble des 3 niveaux

### Niveau A — IC Feasibility (gate légère, ~30 min)
**Fichier** : `stats/ic_check.py`  
**Objectif** : vérifier que le signal a un pouvoir prédictif minimal avant tout backtest.

| Métrique | Gate PASS | Comportement si FAIL |
|---|---|---|
| IC Spearman cross-sectionnel | t_HAC > 2.5 | → ARCHIVED (coûte 1 n_test) |
| Event count | ≥ 50 événements/an | → ARCHIVED directement |
| Orthogonalité signal A | \|ρ\| < 0.5 | → ARCHIVED (β-dominance) |

Si FAIL : le handler génère un rapport POSTMORTEM, archive le `.md` dans `tested/`, et incrémente n_tests d'1.

### Niveau B — Backtest Walk-Forward + Bootstrap + DSR (gate lourde, ~2-4 h)
**Fichiers** : `stats/backtest_wf.py`, `stats/bootstrap.py`, `stats/dsr.py`  
**Déclenchement** : uniquement si Niveau A PASS.

| Métrique | Gate RESEARCH_PASS | Gate PROPFIRM_PASS |
|---|---|---|
| Sharpe OOS (WF ≥ 5 folds) | > 0.7 | > 1.0 |
| MaxDD | < -25% | < -10% |
| WF positivity | > 50% | > 60% |
| DSR (Bailey-Lopez de Prado 2014) | > 0.05 | > 0.10 |
| Bootstrap p-value (Politis-Romano) | < 0.10 | < 0.05 |

Si FAIL : incrémente n_tests de 3 (WF × 5 folds = 1 test, bootstrap = 1, DSR = 1).

### Niveau C — Sanity Checks (validation croisée, ~1 h)
**Fichier** : `stats/sanity_checks.py`  
**Déclenchement** : uniquement si Niveau B PASS.

| Check | Critère |
|---|---|
| Adjacent asset replication | même signe SR sur asset proche |
| Shuffle null | SR_shuffled < SR_réel (p < 0.05) |
| OOS decade isolation | SR > 0.3 sur chaque décennie testée |

---

## Dispatch des handlers

L'`orchestrator.py` lit le `.md` de l'hypothèse et appelle `classify()` sur chaque handler
enregistré **dans l'ordre de priorité** (`HANDLER_REGISTRY` dans `handlers/__init__.py`).
Le premier handler dont `classify()` retourne `True` est instancié et exécuté.

```
promising/*.md
    → orchestrator.py
        → SkipMonthHandler.classify()   → si True, dispatch
        → ExitRuleHandler.classify()    → si True, dispatch
        → RegimeFilterHandler.classify()→ si True, dispatch
        → GenericHandler.classify()     → fallback (toujours True)
```

Chaque handler hérite de `base.HypothesisHandler` et implémente `run_level_A/B/C`.

---

## Comment ajouter un nouveau handler

**1. Créer le fichier** dans `handlers/` :
```
handlers/mon_handler.py
```

**2. Hériter de `base.HypothesisHandler`** et implémenter les 4 méthodes :
```python
from .base import HypothesisHandler

class MonHandler(HypothesisHandler):
    @classmethod
    def classify(cls, promising_md_path: str) -> bool:
        # retourner True si ce handler est compétent pour cette hypothèse
        ...

    def run_level_A(self) -> dict:
        # appeler stats/ic_check.py, retourner {"pass": bool, "metrics": {...}}
        ...

    def run_level_B(self) -> dict:
        # appeler stats/backtest_wf.py + bootstrap.py + dsr.py
        ...

    def run_level_C(self) -> dict:
        # appeler stats/sanity_checks.py
        ...

    def generate_report(self) -> str:
        # retourner le markdown du rapport final
        ...
```

**3. Enregistrer dans `handlers/__init__.py`** :
```python
from .mon_handler import MonHandler
HANDLER_REGISTRY = [MonHandler, ..., GenericHandler]  # avant GenericHandler
```

**4. Tester** :
```bash
python -m _automation.feasibility.orchestrator _automation/alpha_hunt/promising/mon_hypothese.md --dry-run
```

---

## Outputs

- Rapport texte dans `tested/<hypothesis_slug>_report.md`
- Index mis à jour dans `tested/_index.json`
- État global dans `_state.json` (last_run, processed_promising)
- n_tests incrémenté dans `CLAUDE.md` (manuel, après validation humaine)
