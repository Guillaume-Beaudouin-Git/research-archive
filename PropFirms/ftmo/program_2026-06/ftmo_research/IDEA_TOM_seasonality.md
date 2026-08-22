# Idea TOM — Turn-of-Month index seasonality (long-only) — PRE-REGISTRATION
*Frozen 2026-06-03 BEFORE results, per `RESEARCH_PROTOCOL_statarb.md`.*

## Hypothesis (economic)
Equity-index returns are elevated around the **turn of the month** — the last ~1 trading day of a month plus the first ~3 of the next — driven by recurring, calendar-timed inflows (salary/401k/pension contributions, fund rebalancing, payment cycles). **Long the index only in the TOM window, flat (~80% in cash) otherwise.** Single instrument, single direction → FTMO-compliant.

## Why it might suit the barrier (the structural reason to test it)
Being **in cash ~80% of the time** makes total exposure — and therefore drawdown — structurally small, so the **−10% floor is rarely threatened** (the failure mode that killed every other idea). The cost is negligible (~12 round-trips/year). The open questions are (a) is the edge big enough, and (b) **has it decayed post-discovery?**

## Caveats stated UP FRONT
1. **Post-discovery decay:** TOM is a well-known effect; it may have weakened after ~2000s. **Decisive test: by-decade / post-2013 OOS.**
2. **Small edge → needs leverage** to reach +10%; leverage is capped by the 5% daily limit (index daily ~1% × L).
3. **Conditional long beta:** a TOM window inside a crashing month still loses (it is not market-neutral).

## Data
- **Primary:** NQ databento daily close (last RTH bar/day), 2010–2026 (pristine).
- **Length/breadth:** US500 / US100 daily close panel 2000–2026 — **validated** vs databento (return-corr in overlap) before use (close-to-close is reliable even where opens were noisy).

## Signal (frozen, causal — calendar is known in advance)
- Within each calendar month, label trading-day-of-month `tdom` (1..n) and reverse `rtdom` (n..1).
- **TOM window** = `tdom ≤ K_first` OR `rtdom ≤ K_last`. Baseline **K_first=3, K_last=1**.
- Position day t = LONG if t ∈ TOM window (held close[t−1]→close[t]); flat otherwise. Cost on entry/exit.

## Tests
- **Existence:** mean TOM-day return vs non-TOM-day return; t-stat; annualized contribution.
- **Decay/OOS:** by-decade (2000s / 2010s / 2020s) and pre-2013 vs post-2013.
- **Cost** (negligible, swept anyway); **multi-index √N** (NQ/US500/US100); **FTMO 2-step first-passage** (daily-MTM, leverage sweep) + **DSR**.

## Pre-registered grid
K_first ∈ {2, 3, 4}, K_last ∈ {1, 2}. Baseline (3, 1).

## Acceptance (charter Part D)
compliant · causal · effect significant · **persists post-2013 (not decayed away)** · positive across indices/regimes · survives cost · first-passage p(funded) decent with low bust · DSR-significant · reproducible.

---
*(Results appended below — never above this line.)*

---

# RESULTS & VERDICT (2026-06-03)

## VERDICT: ❌ KILL — TOM premium too weak/insignificant, and the long-only form still eats crash-window drawdowns → fails the barrier.

Data validated clean: panel US100 vs NQ databento daily-return corr **0.997**.

- **Premium weak & insignificant.** NQ databento (2010–2026): TOM-day +7.39 bps **vs** non-TOM +7.92 bps → **diff t = −0.10** (no effect on clean NQ). Panels US500/US100: TOM higher (+5.5/+8.2 bps) but **diff t only +0.75/+0.80**. Grid (6 configs) diff_t 0.51–1.43 — **never significant** (need ~2).
- **Not decayed** (stable ~6–11 bps/TOM-day, marginally stronger recently) — so it's a real-but-tiny tendency, *never* statistically strong (max t 1.74, 2010s US100). Rules out "arbitraged away"; it simply was never big enough.
- **Low-drawdown hope partially false.** In cash ~81% of the time, yet strategy **maxDD −15% (NQ) to −36% (US100)** and Sharpe **0.14–0.18** — the TOM windows landing in crash months (Oct'08, Mar'20) are still long-beta and breach the −10% floor.
- **FTMO 2-step first-passage: p(funded) 15–25%, bust 74–84%** (L=3–12); OOS 2018–2026 @L8 = 25%/74%. Fails the barrier.

**Checklist:** ✅ compliant/causal · ✅ data clean (validated) · ✅ not-decayed · ❌ **effect not significant** · ❌ drawdown breaches floor (crash-window beta) · ❌ first-passage fails. KILL.

**Why it failed (and it's instructive):** the "in-cash-80%→low-drawdown" intuition is right about *average* exposure but wrong about the *tail* — the rare TOM window inside a crash still delivers a floor-breaching loss, and the tiny edge forces leverage that amplifies it. Same barrier wall, new disguise.

