# Tradeify — Rules

last_verified: 2026-05-24 (official URLs 403 Forbidden — see sources.md)
source: session context for confirmed values; training data for ⚠️ unverified

> Fields without ✓ are from training data (pre-Aug 2025).
> Verify against help.tradeify.co before purchasing a new challenge.
> If URL still 403: contact Tradeify support with specific question before acting.

---

## Select Flex $25K — Evaluation phase

| Rule | Value | Source |
|------|-------|--------|
| Profit target | ✓ $1,500 | Session context |
| Trailing Max DD | ✓ $1,000 EOD trailing | Session context |
| Daily Loss Limit | ✓ NONE | Session context |
| Consistency cap | ✓ 40% of profit target = $600/day max | Session context |
| Min trading days | ✓ 3 | Session context |
| Lock in eval | ✓ NO | Session context |
| Max eval duration | ⚠️ No hard limit stated | Training data |

## Select Flex $25K — DD model

> Source: help.tradeify.co/articles/10495897 (Trailing Max Drawdowns — 403 Forbidden 2026-05-24,
> content from session context). Verbatim from article 12853966 (Flex/Daily Payout):
> _"locks when EOD balance exceeds your drawdown amount by $100;
>  floor = $100 above your starting balance"_

The DD is **EOD trailing, intraday enforced**:
- The floor updates at **end-of-day** only (based on EOD equity peak)
- But the floor is **enforced intraday**: equity dropping below floor at any point = immediate bust
- For Strategy C (hard SL cap = $400/trade), max intraday loss per day ≤ per-trade SL cost.
  Intraday bust is only possible when the floor gap is smaller than the SL — rare under normal conditions.

Starting floor: $25,000 − $1,000 = **$24,000**.
Floor trails up at each EOD with equity peak. No lock in eval phase.
Bust: equity ≤ floor at any point intraday (hard SL cap bounds intraday loss for Strat C).

## Select Flex $25K — Funded phase

| Rule | Value | Source |
|------|-------|--------|
| Trailing DD | ✓ $1,500 EOD trailing | Session context |
| Daily Loss Limit | ✓ NONE | Session context |
| Consistency | ✓ NONE (Select Flex only) | Session context |
| Lock trigger | ✓ EOD equity ≥ $26,600 **OR** first payout | Session context |
| Locked floor | ✓ $25,100 (capital + $100) | Session context |
| Lock mechanism details | floor locks at $25,100 once triggered; no longer trails | |

Lock threshold: capital + DD_funded + $100 = $25,000 + $1,500 + $100 = **$26,600**.
Once locked: bust only if EOD equity ≤ $25,100. Trailing DD stops once locked.

## Select Flex — Payout

| Rule | Value | Source |
|------|-------|--------|
| Trigger | ✓ 5 winning days (≥$100 each) since last payout | Session context |
| Amount | ✓ 50% of total profits, capped at $1,250 | Session context |
| Frequency | ⚠️ Daily (Flex feature) | Training data |
| Lock on first payout | ✓ YES — first payout triggers funded lock | Session context |

Safety: payout deducted from equity; payout capped at `equity - floor - $1` to avoid bust.

## Select Flex — Funded account scaling table

| Account size | Trailing DD | Lock trigger | Locked floor |
|-------------|-------------|--------------|--------------|
| $25K | ✓ $1,500 | ✓ $26,600 | ✓ $25,100 |
| $50K | ⚠️ PLACEHOLDER | ⚠️ PLACEHOLDER | ⚠️ PLACEHOLDER |
| $100K | ⚠️ PLACEHOLDER | ⚠️ PLACEHOLDER | ⚠️ PLACEHOLDER |
| $150K | ⚠️ PLACEHOLDER | ⚠️ PLACEHOLDER | ⚠️ PLACEHOLDER |

> Scaling values needed before considering account size upgrades. Contact support.

## Select Flex — Other rules

| Rule | Value | Source |
|------|-------|--------|
| News trading | ⚠️ Allowed (Flex differentiator) | Training data |
| Hedging | ⚠️ Not allowed | Training data |
| CME futures | ✓ YES — NQ, MNQ, ES, MES (Tradovate) | Session context |
| Platform | Tradovate | ✓ Session context |
| Eval cost ($25K) | ⚠️ ~$170 | Training data |

---

## Growth $25K — Evaluation phase (ALTERNATIVE PRODUCT)

> Growth = fixed monthly subscription; Select Flex = one-time fee. Different risk parameters.
> Growth is NOT the primary product for Strategy C. Documented for completeness.

| Rule | Value | Source |
|------|-------|--------|
| Profit target | ⚠️ ~$1,500 | Training data |
| Trailing Max DD | ⚠️ ~$1,500 EOD trailing | Training data |
| Daily Loss Limit | ⚠️ ~$500 | Training data |
| Consistency cap | ⚠️ ~30% | Training data |
| Min trading days | ⚠️ ~5 | Training data |
| Lock in eval | ⚠️ UNKNOWN | Training data |

> All Growth values ⚠️ UNVERIFIED. Do not use for simulation or sizing decisions
> without verification.

---

## Strategy C live parameters

Derived from trailing_dd_simulator.py (2026-05-24):
- Config: Select Flex 25K canonical ($1,000 eval DD, $1,500 funded DD)
- Guardrail: `GUARDRAIL_TRAILING_DD_USD = 850` ($150 buffer before $1,000 limit)
- Sizing: see `Futures/live/strategy_c_live/sizing_policy.md`
- Eval P(pass) and P(bust): see sizing_policy.md or run `sizing_analysis.py`
