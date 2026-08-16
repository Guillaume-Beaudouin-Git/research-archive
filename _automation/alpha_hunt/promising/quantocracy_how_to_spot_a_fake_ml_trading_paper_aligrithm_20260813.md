# How to Spot a Fake ML Trading Paper

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=V0TS94xkks&source=feedburner
**Captured**: 2026-08-13 08:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 27ec5d0b19c86f49e992da64b867d92b

## Summary
Aligrithm reviews three ML trading papers that crossed the author's desk in one month, using them as case studies in spotting fabricated or overstated results. The first paper claims to detect market manipulation with a graph neural network at 98.7% accuracy and 8.3 milliseconds per decision; a second paper from an overlapping author cluster reportedly makes a similarly suspicious claim. The excerpt cuts off before the actual red-flags checklist is stated, but the framing (implausibly high accuracy, implausibly low latency, repeat author clusters) signals the piece is building a skepticism heuristic for evaluating ML-in-finance claims.

## Why it might be useful
This maps directly onto two project mechanisms: the daily arxiv scan (`_automation/arxiv/`) that feeds candidate ideas into the same pipeline this note is part of, and the "5 mandatory script fixes" honesty rule that already forbids overstating a correction as "DSR" when it's only an approximation. A concrete red-flags checklist (implausible accuracy, suspicious latency claims, repeat author clusters publishing near-identical results) would give `_automation/feasibility/`'s gate pipeline (or a human pre-screen before Level A) a cheap first filter to reject arxiv q-fin submissions before spending IC/HAC compute on them — directly relevant since L48 stresses that every avoided wasted test protects the DSR of all subsequent candidates. It's also a useful cross-check against the project's own historical over-claims, e.g. the now-corrected NQ iter_10 Sharpe (1.52 naive → 0.41 re-baselined per L19/L20), which is exactly the "too good, under-scrutinized" pattern this article is warning about.

## Extracted content
"One detects market manipulation with graph neural networks and reports 98.7% accuracy at 8.3 milliseconds per decision." The author claims a second paper, from an overlapping author cluster, makes a comparably questionable claim, but the specifics are cut off in the excerpt.

## Action proposed
REFERENCE — a methodology/skepticism checklist for evaluating incoming ML papers, not a tradable idea; useful as a screening heuristic for the arxiv/feasibility pipeline but has no direct backtest to run.
