# PropFirms — Propfirm Rules Documentation

## Purpose
Authoritative source for propfirm rules used in sizing analysis and challenge planning.
CLAUDE.md must reference this directory for all propfirm-specific numbers.

## Conventions
- `last_verified`: Date rules were confirmed against official help center
- `⚠️ UNVERIFIED`: Figure from training data / session context, not confirmed from official URL
- `✓ CONFIRMED`: Figure confirmed from official source (URL listed in sources.md)
- All dollar amounts are in USD
- DD = maximum drawdown allowed before bust
- DLL = Daily Loss Limit

## Scope
Active propfirm accounts or candidates for future challenges:
| Firm | Status | Primary account |
|------|--------|-----------------|
| Tradeify | ACTIVE (Strategy C candidate) | Select Flex $25K |
| Apex | CANDIDATE (Topic 5 — Strategy A/D) | $25K–$100K |
| Topstep | EVALUATED (abandoned for C) | $50K–$150K |
| MFFU | CANDIDATE (reference) | $25K–$50K |
| Phidias | CANDIDATE (European) | Various |

## Key rule: FTMO does NOT support CME futures
FTMO is explicitly excluded from futures strategies (CME MNQ/ES/ZN/CL).
Pivot candidates for futures: Apex, Topstep, MFFU, Phidias.

## Files
- `comparison.md` — Side-by-side comparison table
- `<firm>/rules.md` — Full rules per firm
- `<firm>/sources.md` — URL sources + verification dates
