# Weekly Research Synthesis

Cross-paper synthesis produced every Sunday evening by routine `arxiv-weekly-synthesis`.

## Inputs
- 7 last days of arxiv selection (`_automation/arxiv/*.md`)
- 7 last days of alpha analysis (`_automation/arxiv/*_analysis.md`)
- Previous weekly syntheses (continuity)
- Algo_claude research archives (historical context)

## Output structure
Each `YYYY-WW.md` contains:
1. Emerging themes (cross-paper clusters)
2. Declining themes (literature saturation)
3. Live strategy convergence (papers validating/invalidating current strategies)
4. Orthogonal hypotheses (gaps in literature exploitable for new research)
5. Priority for next week (1-2 actionable items)

## State
`_state.json` tracks themes longitudinally:
- Theme → first seen week, n_papers, current_status (emerging/saturated/declined)
- Open hypotheses awaiting test
