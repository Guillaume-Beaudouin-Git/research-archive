# Sentiment is Not One Signal [Tommi Johnsen]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=jEsujLOjUx&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: d3a91e3bc876e3cc2d59dba561b715f0

## Summary
Most financial sentiment research treats "sentiment" as a single aggregate signal — classify news as positive/negative/neutral, aggregate to daily, correlate with returns. Tommi Johnsen argues this approach conflates distinct phenomena: analyst sentiment, retail investor sentiment, institutional flow sentiment, and earnings surprise sentiment all behave differently and mix poorly in a single classifier. Disaggregating sentiment by type and source produces more stable predictive relationships.

## Why it might be useful
None of the current Algo_claude strategies (A, B, C) use sentiment signals — all are price/vol-based. The disaggregation insight would be relevant if a future NQ strategy D incorporated earnings surprise or news sentiment as a filter for the ORB signal. However, building disaggregated sentiment pipelines would require NLP infrastructure and historical news data beyond current data sources. The "How to Break a Financial Sentiment Model" item (item 20) in this run addresses related robustness concerns. No near-term test path.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Sentiment disaggregation methodology. Not applicable to current price-vol strategies. File for future NLP/sentiment research if NQ news filter is explored.
