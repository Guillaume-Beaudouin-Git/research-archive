# Alpha Hunt

Multi-source alpha hunting pipeline. Three stages:

1. **Raw fetch** (VPS cron, ~30 min): `scripts/fetch_alpha_sources.sh` pulls
   Reddit/HN/Quantocracy/GitHub Trending/SSRN/FRED into `_raw/`.

2. **Filtering** (routine `alpha-hunt-collector`, every 2h 06:00-20:00 UTC):
   reads `_raw/`, applies multi-level filters:
   - L0 exclusion (noise removal)
   - L1 signal of substance (metrics, code, methodology, macro signals)
   - L2 retail quant accessibility (rejects items requiring institutional data feeds,
     prime brokers, HFT colo, or capital > $100K minimum)
   Promising items → `promising/`. Dedup via `_seen.json`.

3. **Feasibility testing** (routine `alpha-hunt-feasibility`, daily 21:30 UTC):
   triages new `promising/` items, deep-tests top 2-3 with WF + block bootstrap
   + DSR + sanity checks. Results → `tested/`. PASS items flagged in weekly
   synthesis.

## State files
- `_seen.json`: dedup index
- `tested/_results.json`: longitudinal record of test verdicts

## Manual review
Items in `promising/` with `Action: TEST_NOW` are queued for feasibility.
Items in `tested/` with verdict PASS deserve human review for deployment.
