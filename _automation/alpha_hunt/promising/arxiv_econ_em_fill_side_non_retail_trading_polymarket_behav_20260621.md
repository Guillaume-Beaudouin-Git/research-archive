# Non-Retail Microstructure on Polymarket: Behavioral Tiers and Quote Attribution Artifacts

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.11640
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 5c0f5c2f77da89c0fa1817dcb40d943b

## Summary
Using 13 million OrderFilled events on Polymarket from 2026-04-21 to 2026-04-27 across 77,204 addresses and 43,116 markets, this paper characterizes the supply-side microstructure of a prediction market for the first time at on-chain scale. Three findings: a small set of high-frequency addresses dominate non-retail activity at tight spreads; market-maker profitability tracks information asymmetry rather than volume; and one-address-per-fill quote attribution constraints create systematic microstructure artifacts requiring correction for inference. The paper provides empirical grounding for prediction market microstructure theory.

## Why it might be useful
The information-asymmetry-over-volume finding for prediction market maker profitability has a structural parallel to Strategy B's delta-neutral carry: on Hyperliquid, the most profitable funding rate trades are likely concentrated in markets with genuine information asymmetry (large open interest, directional trader demand) rather than simply high volume. The 8h carry floor CARRY_FLOOR_8H=0.0034/(30×3) in Strategy B is a volume-independent minimum, but if HL perp market-making profitability follows the same pattern as Polymarket, the active pair selection (currently HMSTR) should screen for information asymmetry indicators (e.g., funding rate persistence, OI/volume ratio) rather than just raw volume above MIN_VOL_USD=1,000,000. The one-address attribution artifact is also a DEX microstructure data quality issue analogous to the fill quality concerns in `logs/fills.csv`.

## Extracted content
Specific numeric claims: 13 million OrderFilled events, 77,204 addresses, 43,116 markets, 2026-04-21 to 2026-04-27 observation window.

## Action proposed
REFERENCE

Polymarket prediction market context; not directly applicable to HL perp trading. The information-asymmetry insight is suggestive for Strategy B pair selection but requires reformulation as a concrete HL-specific screening criterion.
