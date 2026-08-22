# CORRECTION — financing sign bug (found in verification, 2026-07-08)

## What happened
During the independent verification of the iteration-2 "winners", a fresh from-scratch recompute of the
US500 factor-residual returned **Sharpe 0.06**, versus the engine's **1.13**. Since cost can only *lower*
Sharpe, the engine was inflating it. Root cause:

```python
net = gross - tc - fin      # BUG: fin is already SIGNED (negative = cost)
```
`ftmo_costs.swap_bps_night()` returns **signed** bps (negative = you pay). Writing `- fin` therefore
**added the financing cost back as income**. The correct P&L is `gross - tc + fin` (add the signed swap).

Verified decisively on the US500 residual:
```
SHARPE gross                 = 0.06
SHARPE gross + fin (CORRECT) = -1.09     <- financing is a real cost; the residual is dead
SHARPE gross - fin (BUG)     = +1.22     <- the fake "edge"
```

## Scope & impact
The bug was in every engine that holds **overnight** (adds swap): `run_connors.py`, `run_A2.py`,
`run_statarb.py`, `run_mr_daily.py`, and `autopsy_A.py`. Intraday-flat engines (`run_range.py`,
`run_B2.py`) have **no swap term and are unaffected**. All fixed to `+ fin` / `+= swap`.

| result | as-reported (buggy) | **corrected** | verdict change |
|---|--:|--:|---|
| Iter-2 C — Connors RSI2 | Sharpe 0.69, challenge P≈0.5 | **0.37** (0/24 cells > 0.5) | ✗ **win retracted** |
| Iter-2 A — US500 residual | Sharpe 1.13, P(pass) 0.70–0.84 | **−1.09** (gross 0.06, financing kills it) | ✗ **win retracted** |
| Iter-2 A — gold/silver | Sharpe 0.41 | −0.61 | still fail (worse) |
| Iter-1 A — stat-arb pairs | best 0.97 (relative drift) | **0.27** | verdict UNCHANGED (falsified, cleaner) |
| Iter-1 C — daily MR | best 0.53 | **0.36** | verdict UNCHANGED (falsified) |
| Iter-1 B — range | causal −0.06 / oracle +2.66 | unchanged (no swap) | verdict UNCHANGED |
| Iter-2 B — amplitude range | 0.46 (two-sided XAU) | unchanged (no swap) | near-miss, unchanged |

## Consequence for the goal
After the fix, **no piste yields a net Sharpe > 0.5 FTMO-challenge-suitable candidate.** The binding
constraint is exactly the one the repo's deep-dives identified: **overnight financing** (~2 bps/night for
long index CFDs; doubled for a market-neutral 2-leg book) plus **intraday spread** for flat strategies.
The two apparent wins were the bug crediting that financing as income. The challenge Monte-Carlo files for
those candidates (`piste_C/challenge_mc.json`, `piste_A/H2_*`) are **void**.

## Why this is logged, not hidden
The verification step (independent recompute on a separate code path) is exactly what caught this. It did
its job: it prevented two losing strategies from being presented as deployable. The lesson is engraved
below and the cost-model convention is now asserted in a unit test (`lib/test_costs.py`).
