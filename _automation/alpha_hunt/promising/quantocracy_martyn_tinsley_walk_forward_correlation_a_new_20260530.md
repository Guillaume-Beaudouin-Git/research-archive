# Walk Forward Correlation: A New Robustness Metric for Strategy Design — Martyn Tinsley

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=YsJgBGr9HJ&source=feedburner
**Captured**: 2026-05-30 18:06 UTC
**Filters passed**: L1=[trading_topic, methodology], L2_OK
**Hash**: 280c5d4a76ba0a5b863d52382bc284c7

## Summary
The article introduces "Walk Forward Correlation" (WFC) as a diagnostic to measure whether in-sample (IS) period profits predict out-of-sample (OOS) performance magnitudes across walk-forward folds, rather than simply counting how many folds pass a profitability threshold. The core argument is that the standard WF pass rate is a coarse binary metric: a strategy could pass 7/9 folds by thin margins while failing 2 by wide margins, producing an inflated apparent robustness. WFC instead computes the cross-fold correlation between IS Sharpe and OOS Sharpe, flagging strategies where IS optimization extracts noise rather than a persistent edge. The excerpt is truncated and the full article is required to extract the specific formula and empirical validation.

## Why it might be useful
CLAUDE.md mandates walk-forward ≥5 folds (RESEARCH_PASS: WF>50%, PROPFIRM_PASS: WF>60%). Strategy C (NQ ORB iter_10) passed at 78% (7/9 folds, Sharpe 1.52), but the 78% figure hides whether the IS-to-OOS magnitude relationship is consistent — a point WFC directly addresses. Concretely: re-run the Strategy C WF results and compute the IS vs OOS Sharpe cross-fold Pearson correlation using the existing fold data in `Futures/research/active/nq_intraday/analysis/`; if WFC is low (e.g., r < 0.5), it would flag iter_10 as potentially overfitted despite the pass rate. More urgently, Strategy D (D3+D5 portfolio, active, 0/3 modifications consumed) needs a regime filter tested across folds — WFC would be a cleaner diagnostic than the raw pass rate for a negative-Sharpe base strategy where fold-level magnitudes matter. Implementation: add `wfc_score = np.corrcoef(is_sharpes, oos_sharpes)[0,1]` alongside the existing WF fold summary in the analysis notebooks.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — Directly applicable to Strategy C validation and Strategy D active research. Requires fetching the full article to obtain the WFC formula before implementing. One-hour implementation once formula is confirmed: add to existing WF fold analysis in `Futures/research/active/nq_intraday/analysis/`.
