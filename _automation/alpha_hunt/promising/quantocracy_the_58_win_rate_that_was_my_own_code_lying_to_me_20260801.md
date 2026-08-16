# The 58% Win Rate That Was My Own Code Lying to Me (Jan Heger)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=D1C5R2EGBt&source=feedburner
**Captured**: 2026-08-01 06:00 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: 1330195c87073075ce9f5a73747026c2

## Summary
The author recounts a day-trading idea that survived four validation checks defined in advance and reported an attractive 58% win rate, only to fail a fifth check added after the fact — a check the author now runs first, before any of the original four. The framing ("my own code lying to me") implies the earlier "pass" was an artifact of a bug or methodological gap in the first four checks, one that let a false positive through undetected until the fifth, stricter test exposed it. The excerpt does not specify what the fifth check actually measures.

## Why it might be useful
This directly parallels the project's hard rule "signal at T-1, trade at T" and the feasibility pipeline's 3-level gate (`_automation/feasibility/`, Level C sanity checks): it is a live example of check ORDER mattering, where a later-added check caught what earlier checks structurally could not — the same reasoning behind why the repo enforces look-ahead and cost checks before ever quoting a Sharpe. It also connects to L46 (checklist d'honnêteté propfirm: canonical ledger + measured real cost + frozen spec + full-sample regime eliminates sign-flips between reports) — this anecdote is the same failure mode playing out at the individual-check level rather than the report level.

## Extracted content
The author reports a "58% win rate" that passed four pre-registered checks before dying on a fifth. No code, formula, or further numeric detail is given in the excerpt beyond the win-rate figure.

## Action proposed
REFERENCE — a generic methodological anecdote about validation-check ordering; no specific rule or data to port into repo code without the full article's definition of the fifth check.
