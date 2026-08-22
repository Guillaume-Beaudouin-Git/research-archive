# Non-Overnight Intraday Edge Search — Findings
## Can the overnight mono-culture be escaped on gold / silver / WTI / soybean?

**Motivation:** audit weakness W1 — every validated edge is the same long-overnight-drift mechanism. This memo reports a good-faith, quant-grade search for a **structurally different** (two-sided / event-driven) intraday edge on the same four assets.
**Verdict:** ❌ **none found that is tradable net of costs.** The standard non-overnight mechanisms are absent, weak, or concentrated in windows too small to clear the spread. The overnight-drift mono-culture is a **structural property of these markets at this frequency/cost tier**, not an artefact of my method.

---

## What was tested (all gross first; winsorised; HAC t-stats)

| # | Mechanism (hypothesis) | Best result across the 4 assets | Verdict |
|---|---|---|---|
| H1 | Intraday momentum, hourly (pre-US → US session) | gold Sharpe 0.44, t **1.98** | weak, below t=2.5, cost-marginal (be 2.2 bp) |
| H1' | **Intraday momentum, 30-min (Gao first-30 → last-30)** — the canonical test | gold **−0.36** (i.e. mild reversion); WTI +0.25, t 0.86 | **absent** — the Gao effect is equity-index-specific, not commodity |
| H2 | Intraday reversion, unconditional (first-30 → rest-of-session) | ≈ 0 (gold +0.02, silver −0.30) | absent |
| H2' | **Conditional reversion** — fade a *large* US-open move | gold last-30 Sharpe **1.0–1.2** (t 2.2–2.4) on the largest opens | **real but un-tradable** (see below) |
| H3 | WTI EIA-inventory Wednesday (post-10:30 ET window) | Wednesday post-release Sharpe **−0.31** | absent / adverse |
| H4 | Cross-asset lead-lag (gold↔silver pre-US → other's US) | silver → gold Sharpe 0.38 | weak |

## The one flicker — and why it does not survive

The only signal with a pulse is an **intraday reversion of a large US-open move** in the metals: the bigger the first-30-min move, the more the **last 30 minutes** fades it (gold: Sharpe 0.36 → 0.73 → 1.03 → 1.19 as the open-move filter tightens from "all" to ">90th-pct"; silver similar but weaker). It is economically sensible (overreaction / liquidity provision around the US open).

But it is **not tradable**:
1. **Wrong window.** The reversion lives **only in the final 30 minutes**; the tradable, longer "rest-of-session" hold shows **no reversion** (Sharpe ≈ 0). So you must trade a single 30-min bar.
2. **Cost-dead.** A 30-min hold pays the full round-trip spread for a ~5–10 bp capture — the same retail intraday-flat death documented earlier (lesson L43). Net Sharpe is negative at any realistic spread.
3. **Statistically marginal.** t-stats are 2.2–2.4 **on conditioned sub-samples** (a multiple-testing red flag), and the quintile dose-response is not cleanly monotonic.

## Why these assets only offer the overnight drift (interpretation)

Gold, silver, WTI and soybean are **trending hard-asset markets** with **very low intraday return autocorrelation** (first-30 ↔ last-30 correlation ≈ −0.05 to +0.00). There is no persistent intraday momentum (informed-flow underreaction, which drives the equity-index Gao effect, is absent here) and no persistent tradable reversion (the overreaction is too fast/small). The **only** structural, repeatable intraday inefficiency is the **session-timing drift** — return concentrating in the post-rollover/overnight window — which is exactly the family already validated. This is the honest reason the search keeps returning "overnight."

## Implication for the book (resolving audit W1)

A genuinely orthogonal edge **will not come from these four instruments at intraday frequency.** To diversify the mechanism, the search must move to where the *different* anomalies actually live:

- **Equity indices (ES/NQ/DAX)** for the intraday-momentum (Gao) and pre-FOMC-drift effects (the repo's lesson L42) — a real, *different* mechanism.
- **FX / rates** for carry and the documented session/flow effects (cost-tier permitting).
- **Options** for the variance-risk-premium (already shown real, Sharpe ~0.5, just un-deployed) — a truly orthogonal payoff.
- **Alternative data** (COT positioning, order-flow imbalance, event calendars) rather than price-only OHLC on trend markets.

**Bottom line:** I tried momentum, reversion, event-day and cross-asset effects at both hourly and 30-minute granularity; on gold/silver/WTI/soybean none is a net-tradable non-overnight edge. The mono-culture is structural. The orthogonal-edge mandate should be pursued on **other asset classes / data**, not by re-mining these four — a useful negative result that redirects the research budget.

---

*Reproduce:* `python nonovernight_research/{scan,intraday_30min,conditional_reversion}.py`
*Context:* `reports/overnight_family_audit.md` (weakness W1).
