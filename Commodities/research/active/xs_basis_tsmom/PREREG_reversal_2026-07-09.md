# Pre-Registration — Commodity XS Short-Term Reversal (characterisation)

**Date (pre-registered, before this run):** 2026-07-09
**Mission:** `Commodities/research/active/xs_basis_tsmom/`
**Origin:** by-product of the dual-momentum falsification
(`results/PHASE_B_RESULTS_dual_momentum.md`) — the momentum IC was significantly
**negative** (HAC t to −3.4), i.e. commodity XS momentum is reversal over 2005-2026.

## ⚠ Contamination statement (read first)
The reversal signal was **found in-sample** on this exact 24-contract, 2005-2026 panel.
Because the momentum IC is significantly negative here, a reversal Sharpe **will** be
positive on this sample almost by construction — **so this run is NOT independent
confirmation.** Its ONLY legitimate purpose is to **characterise** the reversal:
1. Is it **two-sided** (both long-losers and short-winners contribute), or a **one-sided
   losers-rebound** (long-losers only = beaten-down-commodity mean-reversion / beta, not a
   clean XS alpha)? — the decisive descriptor.
2. Does it **survive costs**?
3. Which **horizon** (short-term 1-3m overreaction vs the medium-term momentum window)?
4. Is it stable **pre/post-2015** (suggestive only — sample already seen)?

**Decisive go/no-go is explicitly deferred** to (a) genuine forward OOS (post-2026-07) and
(b) the economically-grounded **S_BASIS** mechanism (Erb-Harvey roll-yield), which is the
natural driver of a commodity XS reversal and is still untested (needs `fetch_front_second.py`).
A "pass" here = *consistent with a real, literature-supported effect*, not *confirmed*.

## Hypothesis (falsifiable, literature-grounded)
Short-term cross-sectional **reversal** (overreaction / liquidity provision; Jegadeesh 1990
for 1-month reversal, general) is present in commodity futures: ranking by the prior k-month
return, **long the losers / short the winners** earns a positive, two-sided, cost-surviving
premium.

**Null H0:** the reversal is one-sided (long-losers only) and/or cost-negative and/or
post-2015-dead → not a clean tradable XS edge.

## Spec (fixed)
- Universe/data/costs/rebalance/sizing: **identical** to the dual-momentum pre-reg
  (24 continuous futures, monthly, month-end T-1 → T, tercile L/S, risk-parity inverse-63d-vol
  within leg, dollar-neutral, 0.015% RT + 3× stress).
- **Signal:** rank by prior k-month return; **LONG bottom tercile (losers), SHORT top tercile
  (winners)** — implemented as `build_weights(signal = −past_k_return, dual=False)`.
- **Grid (small, to protect DSR):** `k ∈ {1, 2, 3}` months, **no skip**. → **3 configs.**
  Short-term focus, distinct from the 3–12m momentum window already tested.

## Gates (pre-registered)
1. **Two-sided (decisive):** both the long-losers leg AND the short-winners leg have positive
   Sharpe. If only long-losers is positive → HALF-VERDICT "one-sided losers-rebound", not alpha.
2. **Cost:** net (0.015% RT) Sharpe > 0 at base; report 3× stress.
3. **IC:** monthly XS reversal IC = corr(−past_return, fwd_return); HAC lag-2 t (report; N<30 → suggestive).
4. **OOS split:** pre-2015 vs post-2015 net Sharpe (suggestive — sample seen).
5. **DSR:** deflate the best reversal cell over **n_trials = 19** (16 momentum + 3 reversal =
   the full commodity XS search) — the honest AMTP for this research thread.

**Verdict logic:**
- FULL PASS (worth a forward test) = Gate 1 (two-sided) AND Gate 2 (cost) AND Gate 4 (post-2015 > 0) AND DSR meaningfully > 0.5.
- HALF (one-sided losers-rebound) = long-leg only positive → log as "beta/mean-reversion, not XS alpha", route to the S_BASIS investigation.
- FAIL = neither.

## Honest prior (before running)
From the momentum legs (long-winners +0.2..+0.4, short-losers −0.5..−0.9), I expect the
reversal to be **largely one-sided**: long-losers strongly positive, short-winners mildly
negative → **likely a losers-rebound (Gate 1 FAIL), not a two-sided alpha.** Stating this
now so a one-sided result is not spun as success.

## n_tests
Proposed (not graved): **+3** (cumulative commodity XS thread = 19). Reconcile manually.

---
*Pre-registered 2026-07-09, before the run. Deviation from the spec/grid/gates after seeing
results invalidates it. This run characterises; it does not confirm.*
