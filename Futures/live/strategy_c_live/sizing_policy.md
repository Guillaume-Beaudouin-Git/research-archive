# sizing_policy.md — Strategy C / Tradeify Select Flex 25K

_Source: Futures/research/active/nq_intraday/sizing_analysis.py_
_Canonical propfirm config: PropFirms/tradeify/rules.md_

## Current sizing: **2 MNQ**

## Justification (4 convergent arguments)

| Argument | Evidence |
|----------|----------|
| MC survival (L22) | P(pass 180d)=57.0%, P(bust)=39.7% at baseline slippage |
| Consistency cap (L22) | 4 MNQ avg winner $628 > $600 cap → cap binds (100% paths), needs execution workaround |
| DSR deflation (L20) | iter_10 N_mod=10, T=756d → SR_DSR≈1.0-1.1 from SR=1.52 |
| First deployment | N=0 live trades → maximize P(survive), not E[payout]; re-evaluate at N≥30 |

## Slippage sensitivity

| Slippage stress | P(pass 180d) | P(bust) | E[net/att] | Verdict |
|-----------------|-------------|---------|------------|---------|
| ×1.0 (baseline) | 57.0% | 39.7% | $+289 | PROPFIRM_PASS |
| ×1.5 (moderate) | 54.1% | 42.5% | $+227 | PROPFIRM_PASS |
| ×3.0 (severe)   | 44.2% | 53.1% | $+69 | PROPFIRM_PASS |

## Strategy profile (re-derived from validation)

iter_10 distribution profile (validated 2026-05-24 via sizing_analysis.py methodology check):

- **Win rate per trade: 27.75%** (NOT 53.8% — prior figure was P(eval pass, 3 MNQ) from
  SIZING_DECISION.md v1, confused with strategy win rate)
- Avg winner: $1,571.60 / 1 MNQ equivalent
- Avg loser: -$421.45 / 1 MNQ equivalent
- Win:loss ratio: 3.73:1 (1.5R TP vs losers exiting below 1R due to time stop)
- Trade frequency: 0.458/day (~87 trades/year on 252-day calendar)
- E[trade]: +$132 / 1 MNQ
- Skew profile: positive (favorable for trailing DD ratchet — infrequent large wins)

Implications for propfirm sizing:
- 72% of trades are losers → frequent intermediate drawdowns despite positive E[trade]
- Path-dependence under trailing DD is significant — Monte Carlo is the correct gate,
  not just Sharpe
- DSR deflation likely on the higher end (25-40%) for low-WR Sharpe estimation

## GUARDRAIL_TRAILING_DD_USD

**Value: 850** — internal voluntary risk-management guardrail.

> ⚠️ This is NOT a Tradeify rule. It is a hard-stop inside signal_engine.py
> that triggers before the propfirm's $1,000 eval trailing DD limit is breached.

**Justification of $850 (= 85% × $1,000 eval DD):**
- Buffer = $150
- Max expected single-day loss at 2 MNQ: avg_loser ($85) + slippage ($4) ≈ $89/day
- Buffer ≈ 1.6× max day loss: enough margin to confirm halt before propfirm breach
- Alternative: set to $920 ($80 buffer = ~1× max day loss) after live Sharpe confirmed

## Scaling rules

**Stay at 2 MNQ until**: N_live_trades ≥ 30 AND funded lock ($25,100) reached on first pass.
- After lock: trailing DD replaced by fixed floor → lower bust risk, re-evaluation justified

**Scale-up consideration** (after N≥30 live trades + funded lock):
  - Re-run sizing_analysis.py with updated live trade stats (new win_rate, avg_winner)
  - Upgrade to 3 MNQ only if P(pass 90d) at ×1.5 slippage ≥ 40%
  - If upgrading to 4 MNQ: implement winner-capping logic in signal_engine.py first

## Reversion rule

If **realized slippage > ×2.0 baseline on 3 consecutive trade days**:
  - Temporarily revert to 1 MNQ
  - Investigate: spread widening, news event, execution latency
  - Resume after confirming slippage normalized

## Re-baseline trigger

Any sizing change **requires re-run of sizing_analysis.py** first:
  - New NQ 1-min data (extending iter_10 backtest period)
  - Propfirm rules change (verify PropFirms/tradeify/rules.md current)
  - Live Sharpe after 30 trades diverges >30% from backtest (1.52 ± 0.46)
