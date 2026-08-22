# ITERATION 2 — REPORT: literature-driven attempts to reach Sharpe > 0.5, FTMO-challenge-suitable

**Date:** 2026-07-08 · Reads with `ITERATION_PLAN.md` (pre-registered angles), `CORRECTION_2026-07-08.md`
(the financing bug), `synthesis/SOURCES.md` (literature), and the per-piste `RESULTS.md`.

## Bottom line (honest)
Working from the literature, I built a stronger, DD-controlled variant for each piste. **Two of them
initially *looked* like clean wins (Connors RSI2 Sharpe 0.69; US500 factor-residual Sharpe 1.13). The
independent verification then exposed a financing sign bug that had been crediting overnight swap as
income. After the fix, both collapse — Connors → 0.37, residual → −1.09.** The honest result:

> **No piste yields a net Sharpe > 0.5 FTMO-challenge-suitable candidate after correct costs.** The
> binding constraint is the one the repo's deep-dives already named: **overnight financing** (~2 bps/night
> for long index CFDs; ~2× for a market-neutral 2-leg book) plus **intraday spread** for flat strategies.
> The closest is Piste B's gold amplitude-fade at **0.46** (two-sided, intraday-flat, bug-immune) — a real
> improvement over iteration-1, still under the bar and cost-fragile.

This is a negative result, but a *useful and now-trustworthy* one — and the verification step earned its
keep by stopping two losing strategies from being called deployable.

## Per-piste, corrected

| piste | best literature variant | corrected net Sharpe | DD ok? | why it fails the bar |
|---|---|--:|:--:|---|
| **C** | Connors RSI2<10 above SMA200, vol-filtered, intraday-stopped, 4-index, 8% VT | **0.37** | ✓ (−8.8%/−4.3%) | real gross dip-buy edge, but ~3-day overnight holds pay ~2 bps/night financing ≈ the whole gross return |
| **A** | Avellaneda-Lee factor residual (long US500 / short basket) | **−1.09** | ✗ | ~0.06 gross edge; 2-leg overnight financing (~−1.9 bps/night) turns it deeply negative |
| **A′** | gold/silver ratio, z-stop + vol-target | **−0.61** | ✗ (−82%) | drifts within the z-band over long holds; neither stop nor VT rescues it |
| **B** | Bollinger fade, low-ADX + vol-persistence + **amplitude filter** (gold) | **0.46** | scalable | two-sided & net-positive gross, but gross/cost = 2.57 < 3 → below the 0.5 net bar, cost-fragile |

## The real lesson (what the correct-cost evidence teaches)
Every family that could plausibly be decorrelated here needs **multi-day and/or multi-leg exposure**, which
means **overnight financing** — and at current rates that financing (~2 bps/night/leg) is comparable to the
whole edge. The families that avoid financing (intraday-flat range) are **spread-cost-dead**. This is
*exactly* the §4 finding and the repo's `statarb_deepdive` / `MR_deepdive` / `xauusd_rangefade` conclusions,
now reproduced independently and with the financing modelled correctly. It also explains why the book's one
validated FTMO edge (`ASIA_23_8` gold) is deliberately **swap-free by timing** — that is the structural
escape hatch, and none of these three families uses it.

## The genuinely promising next iteration (evidence-backed, not yet built)
The one direction the evidence *supports* and that structurally dodges the killer: a **swap-free overnight-
drift** sleeve. Lou-Polk-Skouras (2019) show nearly all equity-index return is overnight; the repo's
`ASIA_23_8` already monetises this on gold (Sharpe 1.07 OOS, swap-free by entering after and exiting before
the financing rollover). Porting that template to **index CFDs** — long only during the overnight drift
window, flat across the rollover so **no swap is paid** — is the highest-probability path to a Sharpe > 0.5
challenge-suitable sleeve. Caveats: it is **directional** (challenge-legal, not a §4 funded decorrelator),
and it depends on the broker's rollover time (if rollover ≥ the entry hour, the −2 bps/night swap returns
and the edge dies — the exact ASIA_23_8 condition). **Recommend this as iteration 3 if directional challenge
sleeves are acceptable.**

## Status of the goal
"Iterate until Sharpe > 0.5, challenge-suitable" — **not achieved honestly within these 3 families.** I will
not tune a cost-fragile 0.46 over the line (it would not survive DSR and would mislead). The trustworthy
paths forward are (1) the swap-free overnight-drift sleeve above, or (2) accept a lower-Sharpe *funded-phase*
role for a DD-safe directional sleeve (Connors' −8.8% MaxDD / 0.37 Sharpe is a survivable, if slow, funded
profile). Both are directional; a *decorrelated* Sharpe>0.5 sleeve is not present in these families at
retail FTMO cost.
