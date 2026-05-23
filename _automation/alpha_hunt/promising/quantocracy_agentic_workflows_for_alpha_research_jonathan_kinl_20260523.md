# Agentic Workflows for Alpha Research [Jonathan Kinlay]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=091HZbL53Y&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: d7731e95ac654dac9c02a71b1abf20db

## Summary
Jonathan Kinlay contrasts the vendor-hype narrative ("AI agents will run hedge funds") with on-the-ground experience of actually using agentic workflows in quantitative research. The article identifies where LLM-based agents genuinely accelerate research (data pipeline construction, code generation, literature synthesis) and where they remain unreliable (strategy logic validation, statistical testing, live execution judgment).

## Why it might be useful
Directly relevant to the _automation/ infrastructure in Algo_claude: the alpha_hunt pipeline itself is an agentic workflow (VPS crons → raw data → filter → LLM MD generation → PR). Kinlay's framing of where agents are reliable (data pipeline, code generation) vs unreliable (statistical testing) matches the current architecture — the filter script (process_raw_filter.py) handles deterministic filtering while the LLM handles summarization. The synthesis/ and code_health/ planned routines in CLAUDE.md would benefit from Kinlay's framework to avoid over-relying on LLM judgment for strategy validation. No strategy modification path — this is infrastructure-relevant.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Practical framing of agentic research workflows. Useful input for designing synthesis/ and code_health/ automation routines. Read before expanding _automation/ infrastructure.
