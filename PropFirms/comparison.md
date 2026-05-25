# Propfirm Comparison Table

last_updated: 2026-05-24
✓ = confirmed from official source or session context | ⚠️ = unverified (training data pre-Aug 2025)

> Tradeify official URLs returned 403 Forbidden (2026-05-24). Tradeify ✓ values come from
> session context. All other firms: training data (⚠️).
> FTMO excluded: does not support CME futures (NQ, ES, ZN, CL) — confirmed.

---

## $25K (or nearest equivalent) comparison

| Firm | Product | DD model | DD eval | DD funded | DLL eval | DLL funded | Consistency eval | Consistency funded | Lock | Min days eval | CME futures | Platform | Price (one-time) | In scope |
|------|---------|----------|---------|-----------|----------|------------|-----------------|-------------------|------|---------------|-------------|----------|-----------------|----------|
| Tradeify | Select Flex 25K | ✓ EOD trail, intraday enforced | ✓ $1,000 | ✓ $1,000 | ✓ None | ✓ None | ✓ 40% ($600/d) | ✓ None | ✓ EOD≥$26,100 or 1st payout → floor $25,100 | ✓ 3 | ✓ YES | Tradovate | ⚠️ ~$170 | **PRIMARY** |
| Tradeify | Growth 25K | ⚠️ INSUFFICIENT_DATA | ⚠️ ~$1,500 | ⚠️ ~$1,500 | ⚠️ ~$500 | ⚠️ ~$500 | ⚠️ ~30% | ⚠️ ~30% | ⚠️ UNKNOWN | ⚠️ ~5 | ✓ YES | Tradovate | ⚠️ monthly sub | secondary |
| Apex | EOD Trailing 25K | ⚠️ INSUFFICIENT_DATA | ⚠️ ~$1,500 | ⚠️ ~$1,500 | ⚠️ ~$1,000 | ⚠️ ~$1,000 | ⚠️ ~30% | ⚠️ None | ⚠️ None | ⚠️ 7 | ✓ YES | Rithmic/Tradovate | ⚠️ ~$147 | candidate |
| Apex | Static 25K | ⚠️ INSUFFICIENT_DATA | ⚠️ ~$1,500 fixed | ⚠️ ~$1,500 fixed | ⚠️ ~$1,000 | ⚠️ ~$1,000 | ⚠️ ~30% | ⚠️ None | ⚠️ N/A | ⚠️ 7 | ✓ YES | Rithmic/Tradovate | ⚠️ ~$130 | candidate |
| Topstep | 50K (min) | ⚠️ INSUFFICIENT_DATA | N/A | ⚠️ $2,000 | ⚠️ ~$1,000 | ⚠️ ~$1,000 | ⚠️ ~40% | ⚠️ None | ⚠️ YES | ⚠️ 5 | ⚠️ YES | Rithmic/Tradovate | ⚠️ ~$165 | candidate |
| MFFU | Core 25K | ⚠️ INSUFFICIENT_DATA | ⚠️ ~$2,000 fixed | ⚠️ ~$2,000 fixed | ⚠️ ~$500 | ⚠️ ~$500 | ⚠️ None | ⚠️ None | ⚠️ N/A | ⚠️ 5 | ✓ YES | ⚠️ Rithmic | ⚠️ ~$150 | candidate |
| Phidias | Fundamental 50K | ⚠️ INSUFFICIENT_DATA | ⚠️ PLACEHOLDER | ⚠️ PLACEHOLDER | ⚠️ PLACEHOLDER | ⚠️ PLACEHOLDER | ⚠️ PLACEHOLDER | ⚠️ PLACEHOLDER | ⚠️ UNKNOWN | ⚠️ UNKNOWN | ⚠️ UNKNOWN | ⚠️ UNKNOWN | ⚠️ UNKNOWN | requires research |

---

## Key structural differences for Strategy C (NQ ORB, 1 trade/day, $400 SL cap)

### Trailing EOD (Tradeify Select Flex) — Primary
- Floor updates at EOD with equity peak. Intraday bust only when daily loss > DD limit.
- For Strat C: max daily loss = $127 (3 MNQ) or $85 (2 MNQ) vs $1,000 DD → 7-11× buffer.
- Lock at $26,100 provides breakeven protection once funded.

### Static EOD (MFFU) — Candidate
- Fixed floor from day 1. No trailing risk.
- More lenient for high-intraday-variance strategies. Larger DD ($2,000) helps.
- No consistency rule is a major advantage for Strat C (single large winner days).

### EOD Trailing (Apex Standard, Topstep) — Candidate
- Floor trails upward at EOD. No intraday bust risk.
- Moderate protection. Topstep requires $50K minimum.

### Intraday trailing (Tradeify — note)
> The DD model is "EOD trailing" not "intraday trailing" per updated understanding.
> Previous comparison.md incorrectly listed "intraday trailing" for Tradeify.
> Intraday bust is only possible if a single trade's loss exceeds the EOD DD gap.
> For Strat C with $400 SL: this requires the floor to be within $400 of current equity,
> which only occurs in early eval days before any profitable trades.

---

## Challenge costs (approximate, unverified unless noted)

| Firm | Product | Eval cost | Notes |
|------|---------|-----------|-------|
| Tradeify | Select Flex 25K | ⚠️ ~$170 | One-time |
| Tradeify | Growth 25K | ⚠️ ~$97-$150/mo | Monthly sub; re-check |
| Apex | EOD Trailing 25K | ⚠️ ~$147 | Frequent 80-90% promos → ~$15-30 effective |
| Apex | Static 25K | ⚠️ ~$130 | Same promo policy |
| Topstep | 50K | ⚠️ ~$165 | Monthly sub (not one-time) |
| MFFU | Core 25K | ⚠️ ~$150 | One-time |
| Phidias | — | ⚠️ PLACEHOLDER | phidiaspropfirm.com |

> Apex promotions can reduce cost to ~$15-30 — verify current pricing before purchase.
