# Survivors-book swap sensitivity — does the NO-GO hinge on the swap proxy?

**Scope:** sensitivity only. Book construction frozen (RH deployable + TSMOM, each vol-targeted 1%/day,
equal-weight, **L=2.0 fixed**). Reused `tsmom_regen.strat` (construction validated, **corr 1.000** vs
`chosen_returns.csv`) + the audit's **monotone** first-passage engine (read-only). 90% CIs = outer
bootstrap. **This is plausible-range analysis — the real measured demo swap is still the true resolver.**

## Verdict (one paragraph)

**The NO-GO is robust to swap uncertainty; it does NOT hinge on the −3.08 proxy.** Across the entire
plausible per-night swap range (0 → 8 bps/night), including the **real per-leg directional spec** from
`ftmo_specs` and **best-case crypto inclusion**, the book's 12-month OOS p(pass) point estimate **peaks at
0.454 — at *zero* swap — and never reaches 0.50**; its 90% CI lower bound never exceeds ~0.22. The swap
proxy matters for the *magnitude* (12mo OOS moves 0.45→0.33→0.21 as swap goes 0→3.08→8 bps) but **not for
the verdict** — even costless financing leaves the book below the financiable bar, because the binding
constraints are the thin underlying Sharpe and the short (~350-day) OOS window (which makes the CI wide),
not the swap rate. Using the real per-leg swap instead of the single proxy changes 12mo OOS by ~0.01
(0.329→0.317), confirming the proxy was a sound approximation. **Breakeven swap rate to clear 0.50: none
exists in (or below) the plausible range.**

## 1. Swap sensitivity curve (`swap_sweep_table.csv`, `swap_sensitivity.png`)

No-crypto basket; non-crypto **long** swap swept, short fixed at the measured **+0.13** bps/night:

| swap (bps/night) | TSMOM Sh (2007+) | TSMOM Sh OOS | book OOS 6mo [90% CI] | book OOS 12mo [90% CI] |
|--:|--:|--:|--|--|
| **0** (swap-free, best case) | +0.62 | +1.56 | 0.317 [0.10, 0.65] | **0.454** [0.19, 0.81] |
| 1.0 | +0.44 | +1.36 | 0.293 [0.09, 0.63] | 0.423 [0.17, 0.79] |
| 2.0 | +0.25 | +1.16 | 0.270 [0.08, 0.60] | 0.391 [0.14, 0.77] |
| **2.15** (real per-leg avg) | +0.22 | +1.13 | 0.266 [0.07, 0.59] | 0.386 [0.14, 0.77] |
| **3.08** (proxy, headline) | +0.05 | +0.94 | 0.233 [0.06, 0.57] | 0.329 [0.08, 0.72] |
| 4.0 | −0.12 | +0.76 | 0.216 [0.05, 0.54] | 0.306 [0.07, 0.71] |
| 5.0 | −0.30 | +0.56 | 0.195 [0.04, 0.51] | 0.279 [0.06, 0.70] |
| 6.0 | −0.48 | +0.36 | 0.177 [0.03, 0.48] | 0.256 [0.06, 0.68] |
| 8.0 | −0.85 | −0.04 | 0.144 [0.02, 0.42] | 0.210 [0.04, 0.59] |

## 2. Breakeven

- 12mo OOS p(pass) **point** clears 0.50 anywhere in [0,8]? **NO** (max = **0.454**, at 0 bps).
- 12mo OOS p(pass) **CI lower bound** clears 0.50 anywhere? **NO** (max = **0.185**).
- → **No plausible swap (not even zero) rescues the book. NO-GO is swap-robust.**

## 3. Real per-leg directional swap (residual i resolved)

`ftmo_specs` per-leg signed bps/night (long / short), current-regime prices: US500 −3.08/+0.13 (US100.cash
proxy — US500 not separately listed), gold −3.52/−0.14, silver −6.88/+0.23, **oil +4.87/−22.42** (WTI longs
earn a carry credit; shorts pay heavily). Per-leg replication validated vs the uniform-rate construction at
**corr 1.0000**.

- Real per-leg full directional: TSMOM Sh 2007+ **−0.15**, OOS **+0.66**; **book OOS 12mo = 0.317** [0.10, 0.71],
  6mo = 0.217 [0.05, 0.52].
- ≈ the single −3.08 proxy (12mo 0.329) — slightly worse than the long-only-weighted 2.15 avg (0.386) because
  the real model also charges oil's expensive short side. **The single proxy was a good approximation; the
  verdict is unchanged whether one uses the proxy, the per-leg spec, or the notional-weighted average.**

## 4. Crypto-leg bound (residual ii bounded)

Crypto (BTC/ETH) swap is **not in `ftmo_specs`** (confirmed — spec has only US100.cash + metals/oils/softs/FX),
so it remains the genuinely unmeasured leg. Re-including the crypto TSMOM leg (full basket, non-crypto = 3.08),
crypto swap swept:

| crypto swap (bps/night) | TSMOM Sh OOS | book OOS 6mo | book OOS 12mo |
|--:|--:|--|--|
| 0 (best plausible) | +0.85 | 0.345 [0.14, 0.62] | **0.458** [0.22, 0.73] |
| 12 (mid) | +0.53 | 0.292 [0.11, 0.52] | 0.385 [0.17, 0.65] |
| 25 (worst) | +0.17 | 0.238 [0.08, 0.48] | 0.310 [0.11, 0.53] |

**Even best-case crypto inclusion (free crypto swap) caps 12mo OOS at 0.458** (CI lower 0.215) — it never lifts
the book over 0.50. Note crypto is intraday-flat-*capable*, so a flat variant would pay **zero** swap — but that
is a *different* strategy (an intraday crypto momentum sleeve, which the prior audit found weak, Sleeve B), not a
swap rescue of *this* (overnight-holding) TSMOM book.

## 5. Limitations

- Per-leg bps use **current-regime** snapshot rates (2024-25 prices/policy rate). Historical financing was lower
  in the 0-rate years (2010-2021) → the swap-net **IS** Sharpe is conservative there; the **OOS (2025-26)** window
  is exactly the high-rate regime these rates reflect, so OOS — the cell the verdict rests on — is accurate.
- Single representative price per leg for the points→bps conversion (financing % is roughly price-level
  independent; immaterial to the verdict).
- Wide OOS CIs are intrinsic to the ~350-day hold-out (as in the book). The real measured demo swap remains the
  one decisive number to retire the residual entirely — this run shows it cannot flip the verdict.
