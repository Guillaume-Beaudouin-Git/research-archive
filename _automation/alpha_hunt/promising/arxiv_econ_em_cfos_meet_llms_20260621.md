# CFOs Meet LLMs

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.13812
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 82004776f2aefe41

## Summary
LLM embeddings of CFO earnings call transcripts can nowcast GDP growth and industrial production at quarterly frequency, achieving R² of 0.42-0.51 in rolling OOS validation from 2010 to 2024. The signal outperforms bag-of-words methods and is complementary to survey-based measures. Signal strength is highest in the first week after earnings calls and decays within 30 days.

## Why it might be useful
This paper validates earnings call NLP as a macroeconomic nowcasting tool with strong OOS performance, relevant to the sector_hothand_propfirm research (which uses equity sector data) and tangentially to L42 (pre-FOMC drift, post-event momentum). The 30-day decay timeline suggests the signal is useful for weekly/monthly rather than intraday strategies. The LLM embedding approach requires API access (not free), and GDP-frequency quarterly nowcasting does not map to Algo_claude's daily/intraday strategy cadence. More relevant as context for earnings call sentiment features in paper #7 (Predicting Stock Price Direction on Earnings Announcement Days).

## Extracted content
- Claims: R² 0.42-0.51 in rolling OOS (2010-2024) for GDP growth and industrial production nowcasting
- Signal decay: strongest in first week post-earnings, decays within 30 days
- Benchmark: LLM embeddings > bag-of-words, complementary to surveys

No verbatim code or formulas in the excerpt.

## Action proposed
REFERENCE
