# Bankruptcy Prediction from 10-K Narratives: Incremental Early Warning Beyond Accounting Ratios

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.05623
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: dfc351b9ec182a058eaaec11cc0c6bf3

## Summary
Using bag-of-words and BERT-based text scores on 10-K annual filings for US public firms from 1994-2022, this study finds that narrative text adds modest incremental predictive power for bankruptcy beyond accounting ratios (AUC improvement ~1-3%), declining post-COVID as narrative language homogenized. Text-based scores are more useful for distress flagging than for clean probability calibration. The incremental gain is statistically significant but economically modest, and the approach requires labeled data and substantial NLP infrastructure.

## Why it might be useful
The sector_hothand strategy at `Equities/research/active/sector_hothand_propfirm/` could potentially use a simple text-distress filter to avoid holding sector ETFs during periods of elevated corporate distress signaling in the filing narratives, reducing the left-tail risk that causes MDD -13.3% to breach the FTMO 10% floor. However, the 1-3% AUC improvement is likely too small to materially shift the MDD given the strategy's current structural problems (t_HAC=10.38 red flag flagged in `_audit/sector_hothand_audit_2026-05-30.md`). The post-COVID language homogenization finding is also a warning: the sample period most relevant to the strategy (2022-2026) is exactly when the text signal degrades. This is not a priority addition before the sector_hothand audit is completed.

## Extracted content
Specific numeric claims: AUC improvement 1-3% from text scores beyond accounting ratios, on US public firms 1994-2022 sample; declining post-COVID.

## Action proposed
REFERENCE

Text-based distress signal with modest AUC improvement; not worth implementing before sector_hothand fundamental audit is completed. Post-COVID degradation makes it low-priority for current sample windows.
