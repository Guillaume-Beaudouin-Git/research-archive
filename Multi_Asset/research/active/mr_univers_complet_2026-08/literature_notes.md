# Literature pass — working notes (folded into RAPPORT.md §4)

Done via WebSearch/WebFetch, BEFORE reading this session's own grid results (PREREGISTRATION.md §4).

## What the literature's own conditioning menu is

- **Volume-weighted / VWAP deviation** — "VWAP reversion" is the single most commonly cited
  retail-quant construction (multiple 2024-2025 sources: crosstrade.io, quantum-algo.com,
  luxalgo.com order-flow-VWAP-deviation indicator). **[LIT: multiple retail-quant sources,
  2024-2025]** Construction: fade price stretched >=2 std from session VWAP. **Already in our
  grid**: Block 1d (`mr_intraday_grille_2026-08`, session-VWAP anchor, ATR-distance, z0 1.0-2.0)
  — mean t −1.62, 0/27 survivors.
- **Order-flow imbalance (OFI)** — genuinely NOT in our grid (no order-book data exists anywhere
  in this repo for any instrument) — but the literature's own framing is explicit that OFI is a
  **sub-second-to-minute, order-book-level signal**, not reconstructable from OHLCV bars.
  **[LIT: quantvps.com "Order Flow Imbalance Signals," susanpotter.net, 2024-2025]**
- **Volatility/volume regime conditioning** ("stronger on more volatile days, higher volume
  days") — this is explicitly the conditioning Gao-Han-Li-Zhou (JFE 2018) report for their
  (momentum, not reversal) half-hour effect. **Already in our grid**: `mr_stress_conditional_
  2026-08` (VIX/realized-vol/dispersion quintiles, 180 cells) — flat quantile profile, 0
  survivors after DSR/multiplicity.
- **Position-in-range / percentile** — **already in our grid**: Block 1g (percentile-rank
  conditioner, k∈{20,50}, thresholds 5/95 and 10/90) — mean t −1.66, 0/36 survivors.

**Conclusion on conditioning:** every conditioning variable the literature treats as load-bearing
(volume, volatility regime, position-in-range, VWAP-deviation) is already inside this repo's
1,454+70-cell grid, under a different name, and dead in every instance. The literature is not
pointing at an untried lever here — the FTMO CFD universe has already had this exact menu run
against it.

## Constructions genuinely NOT tried

1. **Gao, Han, Li, Zhou, "Market Intraday Momentum" (JFE 2018)** — first half-hour return
   predicts the LAST half-hour return, **momentum, not reversal** (driven by hedging demand /
   gamma exposure of option market makers who must trade with the trend to stay delta-neutral).
   Tested on SPY/S&P futures/10 other ETFs, 1993-2013. Predictive R² only 1.6% (2.6% combined
   with the 12th half-hour). **[LIT: Gao/Han/Li/Zhou, JFE 129(2), 2018]** — **NOT a mean-reversion
   construction** (it is the opposite sign at the bookends), so strictly out of this mandate's
   family scope, but flagged as the nearest live idea in the literature this repo hasn't run: a
   first/last-half-hour momentum sleeve. Left for a future, separately-scoped session (would need
   its own pre-registration — momentum, not reversion, is a different hard-rule family).
2. **Della Corte, Kosowski (& Wang), "Market Closure and Short-Term Reversal" / "Overnight-Intraday
   Reversal Everywhere"** — the CO-OC (close-to-open reversal, fade the overnight gap, hold
   intraday-only) construction, tested across equity, rate, commodity, and FX **futures**, reports
   an enormous in-sample gross Sharpe (24.16 vs 5.52 for conventional reversal, US stocks
   1993-2014, 100% daily turnover, no retail cost model apparent in the abstract). **[LIT: Della
   Corte/Kosowski/Wang, 2015-2017 working paper + follow-up]** — **this maps directly onto
   `yt_strategy_replications/intraday_mr_ftmo`'s already-tested "S2 gap-fade" mechanism**
   (FINDINGS.md §2: pooled gross SR −0.50, t −1.94, dead). The academic paper's SR 24 is a huge
   red flag for retail applicability by itself: (a) it is gross/idealized, no visible retail-cost
   overlay; (b) it draws its Sharpe from **cross-sectional breadth across the full US stock
   market or a multi-asset multi-future panel**, a diversification benefit no single FTMO CFD
   instrument can replicate; (c) our own single-instrument version of the identical construction
   (gap-fade) is measured dead on this exact universe. **Genuinely already answered, not merely
   assumed.**
3. **Baltussen, Da, Soebhag, "End-of-Day Reversal"** (2024/2025, Quantpedia Award) — individual
   stocks reverse in the cross-section during the last 30 minutes, driven by option market-maker
   gamma hedging. **Cross-sectional** (needs a broad universe of single names, not a single
   index/FX/metal CFD) — **not replicable in this repo's data estate** (FTMO's "Stocks" category
   is not built out as a ≥30-name panel here). The single-instrument analogue (closing-auction
   window on US indices) is **already tested**: `mr_timezone_repair_2026-08`'s B1 grid found a
   real GER40 gross effect (3.52bps, t 3.68) that lives entirely inside the 5-min Xetra auction
   and dies on a 5-min entry delay (0.56bps, t 1.00, sub-cost) — the single-instrument version of
   this exact literature finding has already been tried and killed on execution delay, not
   assumed dead.

## The tier-mediation question (does a documented edge survive retail cost?)

**No documented construction in this pass survives a retail CFD cost tier.** The through-line
across Nagel (2012, "Evaporating Liquidity") and the short-term-reversal literature broadly:
**[LIT: Nagel, NBER WP 17653, 2012]** reversal-strategy profits are framed explicitly as
compensation to LIQUIDITY PROVIDERS (market makers) for absorbing order flow — "traders resemble
market makers, who sell when the public buys and buy when the public sells." A retail CFD trader
placing a market/stop order at the CFD broker's quoted spread is, by construction, the PUBLIC
side of this trade, not the market maker — the spread this literature identifies as the reward
for liquidity provision is exactly the cost line item (0.3-2.0bps RT, measured this session) a
retail FTMO account pays away before any of that literature's gross edge could accrue. This is
the same tier-mediation shape already established in this repo for FX carry (L23b) and
flow-anchored FX (L34): **the retail/CFD tier is structurally the wrong side of this literature's
documented edge**, not merely under-capitalised relative to it. One general-web source
independently converges on the same point without being asked to
(quantifiedstrategies.com/general retail-cost surveys: "more than eight out of ten day traders
experience losses... a strategy showing 1.5 Sharpe before costs may drop to 0.8 after realistic
execution friction" — a generic, non-authoritative source, cited only as corroborating colour,
not as the basis for the tier-mediation conclusion, which rests on Nagel's structural argument).

## Net read for Chantier 3

The literature does not contain an untried MEAN-REVERSION construction this repo could still run
profitably — its conditioning menu is already inside the 1,454+70-cell grid (dead), its two most
striking documented edges (CO-OC gap reversal, end-of-day cross-sectional reversal) map onto
constructions already tested single-instrument in this repo and killed, and its own framing of
WHY reversal is profitable (liquidity-provision compensation) is a structural, not incidental,
reason the retail CFD tier cannot capture it. The one live, adjacent idea (intraday momentum,
Gao-Han-Li-Zhou) is a different family (momentum, not reversion) and is flagged for a
future, separately-pre-registered session rather than folded into this mandate's kill.
