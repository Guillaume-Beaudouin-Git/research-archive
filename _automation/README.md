# _automation/

Outputs générés automatiquement par les Claude Code Routines.
**Ne pas modifier manuellement** — les fichiers sont régénérés par les routines.

## Contenu

| Dossier | Routine | Fréquence | Description |
|---|---|---|---|
| `arxiv/` | `arxiv-daily-scan` | weekdays 09:00 | Scan arxiv q-fin, papers pertinents pour Algo_claude |
| `research_weekly/` | `weekly-research-log` | Friday 20:00 | Synthèse hebdo : tests, archives, lessons, priorités |
| `revisits/` | `archived-strategy-revisit` | Saturday 11:00 | Re-examen d'une stratégie archivée à la lumière de la littérature récente |
| `code_health/` | `repo-hygiene` | Saturday 14:00 | Audit dépendances, fichiers orphelins, drift README |
| `methodology/` | `methodology-audit` | 1st of month | Audit conformité méthodologique des stratégies live |

## Workflow

1. Routines schedulées tournent sur Anthropic cloud (claude.ai/code/routines)
2. Chaque routine ouvre une PR depuis branche `claude/<name>-<date>` vers main
3. Review humaine + merge si OK
4. Output reste comme trace historique

## Backup local

Ces fichiers sont synchronisés via git, donc `git pull` sur le Mac récupère tout.
