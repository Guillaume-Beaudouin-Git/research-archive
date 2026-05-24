# Apex Trader Funding — Rules

last_verified: ⚠️ UNVERIFIED — training data pre-Aug 2025
source: training data; re-verify at https://help.apextraderfunding.com

> ⚠️ All figures from training data. Must verify from official docs before using.
> KEY CONFIRMED: Apex supports CME futures (E-mini, Micro). FTMO does NOT.

---

## Why Apex for futures

- **Supports CME futures** (NQ, ES, ZN, CL, etc.) — confirmed finding from Topic 5
- FTMO explicitly excludes CME futures → Apex is primary alternative for Strategy A / Strategy D
- Competitive DD model (static for Performance Accounts)

## Account sizes available

⚠️ UNVERIFIED — approximate from training:
$25K, $50K, $100K, $150K, $250K, $300K, $500K

## Evaluation phase ($25K account)

| Rule | Value | Source |
|------|-------|--------|
| Profit target | ⚠️ ~$1,500 (6%) | Training |
| DD model | ⚠️ Trailing EOD (Standard) or Static (Performance) | Training |
| Trailing Max DD | ⚠️ ~$1,500 (Standard) | Training |
| Static DD (Performance) | ⚠️ ~$1,500 locked | Training |
| Daily Loss Limit | ⚠️ ~$1,000 | Training |
| Min trading days | ⚠️ 7 days | Training |
| Contract limits | ⚠️ ~2 ES / 4 MNQ equivalent | Training |

## Consistency rule

⚠️ UNVERIFIED — approximately 30% rule (no single day > 30% of profit target).

## Funded phase

| Rule | Value | Source |
|------|-------|--------|
| DD (funded) | ⚠️ Static after activation | Training |
| Lock mechanism | ⚠️ Static model — no trailing after funded | Training |

## Payout

| Rule | Value | Source |
|------|-------|--------|
| Payout cadence | ⚠️ Bi-weekly initially, weekly after 3 payouts | Training |
| Payout cap | ⚠️ None specified (or high cap) | Training |
| Profit split | ⚠️ 90/10 up to ~$25K/month, then potentially higher | Training |

## News trading

⚠️ UNVERIFIED — Apex historically allows news trading (not restricted), but policies change.

## Hedging

⚠️ UNVERIFIED — generally not allowed.

## Instruments confirmed

- CME futures: YES (key differentiator from FTMO)
- Futures-only focused propfirm

## Comparison vs Tradeify for Strategy A

| Factor | Apex | Tradeify |
|--------|------|----------|
| Crypto | NO | NO |
| CME Futures | YES | YES |
| DD model | Static (Performance) | Intraday trailing |
| Lock mechanism | N/A (static) | YES (at starting balance) |
| FTMO comparison | Viable | N/A |

> For Strategy A (TSMOM BTC/ETH/SOL): neither Apex nor Tradeify supports crypto.
> Apex is the primary candidate for a dedicated futures strategy (D3/D5).
