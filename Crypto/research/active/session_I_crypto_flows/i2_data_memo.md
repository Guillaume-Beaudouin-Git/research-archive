# Trial I-2 (post-liquidation-cascade reversal) — STOP(data): acquisition memo

*2026-06-10. Per pre-registration discipline: no adequate free source for ≥3y × hourly ×
long/short-split liquidation history ⇒ the trial is not pre-registered and consumes no registry
slot. OI-delta proxy reconstruction is not acceptable as primary evidence (task spec). This memo is
the deliverable: source, cost, EV of acquiring.*

## What the trial needs
Per-symbol hourly liquidation notional, long/short split, ≥3 years (must include the Oct-2025 and
Nov-2025 cascades as in-sample stress windows), for the ~13-symbol liquid-perp universe.

## Free sources audited (all FAIL — probes in `phase0_audit.md` §2 D3)
| Source | Result |
|---|---|
| Binance Vision bulk | No `liquidationSnapshot` data type under `futures/um/daily/` (2026-06-10 listing). `forceOrder` websocket = live-only AND throttled to 1 msg/s/symbol since 2021-04-27 (notional censoring even if recorded from now on). |
| Coinalyze REST | HTTP 401 — free tier exists but needs an account + API key (cannot register autonomously). |
| Bybit public.bybit.com | No liquidation directory. |
| Hyperliquid | No historical liquidation archive in free API (prior: `_bootstrap_v2_notes.md` §6.34). |
| Coinglass | Paid (API from ~$29/mo, liquidation history on higher tiers). |

## Recommended path (cheapest first)
1. **Coinalyze free API key** — cost $0 + ~5 min user signup. `GET /v1/liquidation-history`
   (interval=1hour, long/short split, multi-exchange aggregation). **Verify before relying on it**:
   (a) history depth ≥ 2022-06 for BTC/ETH/SOL perps (vendor docs are vague on free-tier lookback);
   (b) whether Binance-sourced rows inherit the 1-msg/s forceOrder censoring (they do for any vendor
   relaying the public stream — uniform-ish post-2021-04 so z-scores stay usable, raw $ totals
   understate; the cascade definition is z-based, so this is acceptable IF depth passes).
2. Coinglass Pro (~$29-79/mo) if Coinalyze depth fails — known multi-year pair-level history.
3. CryptoQuant / Amberdata / Laevitas — institutional tiers, overkill for one trial.

## EV of buying
The trial is a single pre-registered test with two-sided legs + matched placebo; prior literature
(post-cascade reversal) is plausible but the §6.34 crash-recovery prior (continuation, not
reversal — price-defined dips) cuts AGAINST the long-cascade leg. P(survives all gates) is modest;
at $0 (Coinalyze signup) the EV is trivially positive; at $29-79/mo one month suffices to backfill
(download once, cancel). **Recommendation: user creates a free Coinalyze key; I-2 re-enters the next
crypto session with its pre-registration unchanged from the task spec (frozen there, not here — no
paper trials).** Until then: STOP(data), +0 trials.
