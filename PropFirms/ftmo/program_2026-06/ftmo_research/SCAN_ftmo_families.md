# SCAN_ftmo_families — L24-filtered multi-family scan of the FTMO universe
### L24 shape pre-filter applied FIRST; deep validation only for survivors. Hypothesis-matched, not blind grid.

**Verdict up front:** **no (family × instrument) tested clears both gates** — a passable L24 shape AND positive net EV across regimes. The single most important finding: the partial-TP reworking **successfully reshapes the breakout distribution** (WR 44%→51%, skew +1.64→+0.39 — no longer tail-lumpy) yet **p(funded) stays ~31%**, because **meanR ≈ 0**. **Shape reshaping fixes the distribution but cannot manufacture EV.** The missing ingredient across every family is a *positive-EV signal*, not a better shape. This is the expected, valuable "mostly rejected" result.

*Costs in bps/% from the start (L11). p(funded) = FTMO 2-step Monte-Carlo (P1 +10% → P2 +5%, daily 5% / total 10%, no time limit). Started on ready data: NQ databento 1-min 2010-2026 (cleanest), plus FX-major / crypto results carried from this arc's prior work. Dukascopy metals/extra indices still downloading — to be added.*

---

## 1. L24 pre-filter table (the sieve)

| Family × Instrument | WR | avgW / avgL (R) | skew | meanR (net) | p(funded) MC | L24 verdict |
|---|---:|---:|---:|---:|---:|---|
| **MR intraday — NQ** (z-fade) | 0.56 | +0.43 / −0.60 | **−2.08** | −0.019 gross → **−0.096 @1bps** | — | ❌ **neg-skew + neg-EV (cost-killed, L11)** |
| **Breakout ORB plain — NQ** (EOD exit) | 0.44 | +1.10 / −0.85 | **+1.64** | +0.004 @1bps | **32%** | ❌ tail-lumpy + ~0 EV |
| **Breakout ORB partial-TP — NQ** | 0.51 | +0.81 / −0.86 | **+0.39** | +0.0004 @1bps | **31%** | ❌ **shape fixed, but ~0 EV** |
| MR intraday — FX majors (EURUSD/GBPUSD/EURGBP) | ~0.54 | small | low | **≤ 0 @0.8–1.5bps** | — | ❌ cost-killed (L11, prior) |
| Stat-arb — AUD/NZD | ~0.40 | — | ~0 | ~0.00 | — | ❌ no EV (prior) |
| Carry / overnight — FX (USDJPY/AUDJPY) | high | — | **neg (crash tail)** | +EV gross | — | ❌ MaxDD −14% to −19% **> −10% floor** (prior) |
| MR / fade — crypto (ETH/SOL) | ~0.45 | — | — | **negative** | — | ❌ neg-EV (prior) |
| **Intraday momentum — NQ** (morning→close, Gao-style) | 0.51 | **+0.44** | small | **+0.42 bps @1bps** | (battery) | ✅ **passes shape sieve → to battery** |

**Two opposite shape-failures under the symmetric barrier:**
- **Breakout = positive-skew lumpy** (WR 44%, skew +1.64): the rare right-tail winner arrives *after* a string of −1R losers that drag you toward the floor.
- **Mean-reversion = negative-skew** (WR 56%, skew −2.08): many small wins, but the rare fade-run-over is a large loss that spikes the daily/total drawdown.
- **Carry = negative crash-tail**: smooth until the unwind blows past the −10% floor.

The barrier punishes **both** tails. The L24-ideal profile (high WR, **low/symmetric skew**, bounded loss, **positive net EV**) was not found in any tested family on these instruments.

---

## 2. Survivors → full battery

**One candidate reached the battery: NQ intraday momentum** (the only one with both a good shape — skew +0.44 — and naively-positive net EV, +0.42 bps @1bps). The deep battery then **rejected it**:

| Battery test | Result | Verdict |
|---|---|---|
| **Regime (gross-vs-net by year, 2010-2026)** | only **8/17 years positive**; +0.42 bps is a blend dominated by 2022 (+12bps), 2025 (+7.4), 2020 (+6.4) | ❌ regime-fragile (escape-N fails) |
| **Split-direction (L25)** | long-signal **+1.50 bps (WR 56%)**, short-signal **−0.84 bps** | ❌ one-sided — it's the **long equity drift**, not a symmetric momentum edge |
| **Cost sensitivity (L11)** | net-positive ≤1.0 bps; **dead at 1.5 bps** | ⚠ cost-fragile |
| **p(funded) 2-step MC** | ≤ **21%** (best leverage); falls as leverage rises (vol-killed) | ❌ thin EV → low pass even with good shape |

**Interpretation:** the L24 sieve correctly *passed* it (good shape) and the deeper battery correctly *killed* it — the two-stage process works. The "edge" is really the **intraday equity risk-premium (up-mornings drift into the close)**: it appears only on the long side and only in favourable years. It is **beta, not alpha** — a long-biased equity exposure, negative in down/chop years (2013, 2015-16, 2019, 2021, 2024). Not a robust, market-neutral, all-regime edge.

The partial-TP ORB passed the *shape* sieve but was rejected at the EV gate (meanR ≈ 0) — no battery warranted.

---

## 3. Verdict & the constructive lesson

**Is there a (family × instrument) with both a passable L24 profile and a robust net edge across regimes? — No, among those tested.** Honest and expected.

But the scan produced a **clean, reusable design lesson**, not just rejections:

1. **The L24 pre-filter saved the effort it was designed to save** — MR and carry were rejected in one backtest each on *shape* + *cost*, with no wasted deep validation.
2. **Shape is necessary but not sufficient.** The partial-TP exit *did* fix the breakout's shape (skew +1.64 → +0.39) — proving the reshaping lever works — but p(funded) stayed ~31% because the underlying meanR ≈ 0. **You cannot reshape your way to a funded account from zero EV.**
3. **The binding ingredient is a positive-EV signal that survives realistic bps costs across regimes.** None of breakout / mean-reversion / carry / stat-arb provides it on liquid indices or FX majors — consistent with this arc's entire body of evidence (these markets are efficient; the ORB intrinsic edge is ~0).

**Recommendation:**
- **Stop searching the intraday price-pattern families on liquid majors** — breakout, MR, carry, stat-arb are exhausted (shape and/or EV fail). Further mining here only manufactures F1-type false positives.
- **The partial-TP exit is the right *packaging*** — keep it on the shelf. Applied to a genuinely positive-EV signal, its smoothed profile (skew ~+0.4, WR ~51%) would convert efficiently under the symmetric barrier.
- **Where positive EV plausibly lives (next, as data lands):** (a) the **already-validated crypto / delta-neutral** strategies the project intends to run once funded — if any is low-drawdown and +EV, *it* is the challenge vehicle, packaged with partial-TP sizing; (b) **Dukascopy metals / additional cash-open indices** (still downloading) for fresh independent ORB sleeves (the √N route, which raises EV-per-day via diversification rather than per-trade edge).
- **For the propfirm goal specifically:** the cheapest path remains **down-sizing a *positive-EV* edge with no time limit** (first-passage lever) — but that requires a positive-EV edge first, which this scan confirms the intraday price-pattern families do not supply.

**New finding this round (intraday momentum):** the only candidate to clear the shape sieve, but the battery exposed it as **beta, not alpha** — the intraday equity drift (long-only, +1.50 bps; short side negative), positive in just 8/17 years, dead above 1.5 bps, p(funded) ≤ 21%. *Insight for the propfirm goal:* the one consistently-directional thing in equity indices is the **long drift** — which suggests that if any vehicle passes here, it is a **long-biased equity exposure harvested in favourable (high-vol/trending) regimes, sized small under no time limit** — but that is regime-conditional beta, not a robust market-neutral edge, and it bleeds in down/chop years.

**Bottom line:** the L24 sieve + battery worked together — fast-rejecting every tail-lumpy/zero-EV candidate, then catching the one regime-fragile, one-sided survivor. The problem was never the exit shape (fixable) or costs alone — it is the **absence of a robust, two-sided, all-regime positive-EV signal** in these families on these instruments. The intraday price-pattern space on liquid majors is now exhausted; the credible positive-EV sources are **off this menu** (the project's validated crypto/delta-neutral books, or new Dukascopy instruments for √N), packaged with the L24-good exit. Find the EV first; the packaging is ready.
