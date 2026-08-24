# VERDICT — nightly US100 double-loss investigation — 2026-07-15

Post independent audit (author≠auditor, all 5 scripts reproduced exactly, funnel mirror
faithful, M0c construction clean). This verdict incorporates the audit's corrections.

## Verdict: (a) VARIANCE — do nothing to sizing — with structural context (b2-iii)

The two losses (−$354.14 @2.83 lots 07/07; −$402.65 @2.97 lots 07/14) are **ordinary variance**
of the nightly US100 sleeve. No bug, correct sizing, working breaker. **No live action on sizing.**
The monday_restamp (already deployed 2026-07-14) is the one warranted change and it addresses the
real structural issue (return-starvation), not the losses.

### Why variance — now clean on the FROZEN kill-rules
| test | result | frozen threshold | met? |
|---|---|---|---|
| **K1a** (P 2 consecutive ON-entry nights both ≥$350) | **13.76%** | ≥10% banal / <1% model≠live | ✅ banal-variance bar met |
| K1a per-ON-night big-loss rate | 20.3% | — | expected 1.2 big/6 nights ⇒ 3 ordinary |
| **K1b** exec gap (recon vs real) | **0.1% / 0.1%** | ≤25% ⇒ no bug | ✅ near-exact, no gap |
| K1b size = designed on_w·scale | ratio 1.00 / 0.99 | — | ✅ not oversized/uncapped |
| **Breaker** overshoot | 1.01× / 1.15× | ≤1.2× efficient | ✅ worked (N2 $53 M5-grid tax) |
| Leverage placement | 8.4× / 9.0× | vs p90 ~14× | ✅ near-median, not a tail |
| Losses in nightly distribution | p7.6 / p5.5 | — | body, breaker-truncated |

**Correction from audit:** the earlier K1a (5.09%) was diluted by non-ON days (0.43% big-loss);
the pre-reg specified consecutive **ON-entries** — computed correctly = **13.76% ≥ 10%**, so
strict-(a) is met by the frozen rule, not merely by the supportive percentiles. The earlier K1b
gap (5.1%/4.7%) was a mis-signed spread cost coincidentally cancelling the swap; fills are actual
transaction prices (spread embedded, slip ≤0.14bps) → swap-only recon = **0.1% gap**, cleaner.

### Structural context (b2-iii) — return-starvation, MEASURED (not "proven")
The J1-gated mono/near-mono book is return-starved: drift **0.29%/day vs 0.80%/day** full,
median t_P1 **12d → 35d**, p(pass) at the 91d wall **83.9% → 46.9%**. This is the actual evidence.
The unbounded-horizon = 100% result **corroborates** (busts are recoverable, no permanent ruin)
but does **not by itself prove** starvation — it is near-tautological for a positive-drift retry
funnel. Two honest caveats on the headline −37pt:
- It is **clock-coupled**: the 91d wall is the user's self-imposed economic horizon, NOT an FTMO
  rule (FTMO has no time limit). At 182d the FULL↔MONO2 gap is only **~−11.6pt**.
- **MONO1 (permanent US100-only) is the worst case**; the live regime is a MONO1/MONO2 blend
  (GER40 present on Tue nights, and now Mondays post-restamp), so the live cost < −37pt.

Refuted sub-hypotheses: (b2-i) cap-uncapping/oversizing — refuted 3× (cap never binds, real=designed
size, leverage near-median). (b2-ii) undamped-vol→more-breakers — refuted (mono breaks *less*).

## Remedy — ADD return engines or relax the clock (honest tradeoff, no dominance)
| lever | Δp(pass) @91d | status |
|---|---|---|
| **+GER40 (monday_restamp)** | **+12.6pt** | ✅ DEPLOYED 2026-07-14 |
| +J1 un-gated (when US/JPY exits zone) | +29.7pt | regime-gated, automatic |
| +gold (signal wakes) | +34.3pt | signal-dependent |
| extend horizon 91→182d | +25.8pt | personal-clock choice |

**Cutting US100 size is NOT recommended** — it lowers drift → lowers p(pass) against the clock
(opposite of the funded precedent where sizing was the only lever). **Honest qualifier (audit):**
"strictly worse" holds only on the *p(pass)* axis. A 4× book would have made these two nights
~$160 not ~$335 — i.e. cutting size *does* reduce the per-night drawdown that alarmed you. So
"keep the size" is a p(pass)-maximizing choice that trades comfort for speed, not a free lunch.
Given the account re-buys on bust ("fonctionnement normal") and the drawdowns stayed within the
breaker, keeping the calibrated size + adding engines is the right call.

## Notes / monitoring (not remedies)
- **Pace-governor is mildly pro-cyclical:** after loss 1 the account fell behind schedule → pace
  1.088 → scale 15.23 → loss 2 was sized *up* (9.0× vs 8.4×, 2.97 vs 2.83 lots). The book leans
  into its own drawdown. Effect is small here (+7% size) but worth watching if losses cluster;
  capping pace would cut drift (same tradeoff), so monitor rather than act.
- **3rd nightly loss surfaced (Volet 3):** 06/30→07/01 −$311 (~1.0 lot, bled overnight, closed at
  15:30 schedule, did NOT trip the breaker). Consistent with the 20.3% ON-night base rate; N tiny.

## Infra debt (separate from the strategy verdict — flagged, not fixed)
1. `fills.csv` is not a reliable position ledger (missing closes, spans the 06/24 reset).
2. US100 M1 path post-2026-06-05 not repatriated → future intra-night replay needs a read-only
   VPS MT5 pull. (This is why K1b used the endpoint-exact method, PREREG §8.)

## Bottom line
The two losses are variance; the sizing, breaker, and execution are all sound. The genuine
finding is that the J1-gated book is return-starved against a self-imposed 91d clock, which lowers
funding odds via *speed*, not risk. The fix is additive (monday_restamp banks +12.6pt; J1/gold
return automatically), not a risk cut. **No sizing action. No further live change.**
