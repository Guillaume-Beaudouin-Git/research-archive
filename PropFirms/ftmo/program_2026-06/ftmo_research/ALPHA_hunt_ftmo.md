# ALPHA hunt for FTMO — L24-compatible, post-beta pivot

**Mission:** after two ~50% candidates (overnight harvester, ORB+floor_taper) both revealed
as **beta + rules-exploitation** (no per-trade alpha → mechanically capped ~50% on a symmetric
barrier), find a **real per-trade alpha** with an **L24-compatible profile** that clears **>70%
p(pass)** under real FTMO costs. Discipline: cost-gate (A) + L24 shape (B) **first**, then
alpha-vs-beta, deep validation **only** for survivors. Honesty clause: "most die at the gate,
few/no survivors" is the expected result.

---

## Verdict up front

> **No survivor. No (family × instrument) tested shows a real, two-sided, all-regime per-trade alpha that clears the gate — let alone >70% p(pass).** The most important finding is a **methodological trap, now disarmed:** a high-selectivity intraday mean-reversion fade *looks* like clean two-sided alpha in a naive screen (**+11 bps net, both legs positive**) but **collapses to t≈0.26 / negative** under **non-overlapping trades + a 1-bar execution-delay test**. The apparent edge was **overlap-counting + same-bar look-ahead**, not alpha.
>
> Across **5 instruments × selectivity × horizon**, intraday MR has **no |t| > 1.7**, is **not two-sided** (the long leg "works" only via the up-drift = beta; short legs are ~0/negative), and **dies under 1-bar delay**. Breakout (partial-TP, both-sides) reproduces the prior NQ result on US500/US100/US30: **EV ≈ 0, long-leg-carried**. This **confirms and extends** `SCAN_ftmo_families.md` — the intraday price-pattern space on liquid FTMO majors is **exhausted**.
>
> **The binding constraint is not the cost-gate — it is the absence of a positive *gross* two-sided edge.** Cost is moot when gross EV ≈ 0 or is one-sided long-beta. You cannot cost-optimize or reshape your way to alpha that isn't there.

**New lesson — proposed L26 (anti-false-positive for fade strategies):**
> Vectorized fade screens with **overlapping** forward windows and **same-bar entry** inflate intraday mean-reversion edges by counting one reversion many times and harvesting a tick that isn't tradeable. **Always validate a fade edge with (a) non-overlapping trades and (b) a 1-bar execution-delay test before believing it.** The delay test is decisive: a real edge survives it; a microstructure/look-ahead artifact collapses. (First catch: the θ=50 bps US500/US100 fade, +11 bps naive → ~0 / negative under proper execution, 2026-06-02.)

---

## 1. Pre-filter table — cost-gate (A) + L24 shape (B)

**Real FTMO round-trip costs** (bps of notional, from `eurusd_spread_profile` + commission):
indices US500/US100/US30 **~1.5 bps** (commission-free CFD, ~1–2 bps spread); EURUSD **~1.0 bps**
(~0.2 pip median spread + ~0.6 bps commission); GER40 **~1.5 bps**. Cost-gate (L11): require
**gross per-trade edge > 3× round-trip cost** (~4.5 bps indices, ~3 bps EURUSD).

All figures below use the **correct** methodology: **non-overlapping** trades, cost subtracted
**per trade**, two-sided (separate long-fade / short-fade legs), regime split by year, and a
**1-bar entry-delay** robustness column. Data: m1_panel 2020/21–2026 (US indices, EURUSD, GER40).

### 1a. Mean-reversion intraday (candidate #1 by L24 profile)
Fade deviation from the 30-min mean, exit +30 min, selectivity θ (bps from the mean):

| instrument | θ (bps) | n trades | mean net (bps) | t-stat | WR | long-leg / short-leg | yrs + | **1-bar delay** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| US500 | 40 | 345 | −2.56 | −0.98 | 45% | −2.7 / −2.4 | 4/6 | −2.57 |
| US500 | 50 | 170 | +1.10 | **0.26** | 48% | +3.3 / **−1.6** | 3/6 | **−0.25** |
| US100 | 40 | 912 | −2.91 | −1.66 | 46% | −4.2 / −1.2 | 3/6 | −3.89 |
| US100 | 50 | 444 | −1.86 | −0.64 | 46% | −3.2 / +0.1 | 3/6 | −3.04 |
| EURUSD | 25 | 223 | −1.80 | −1.33 | 46% | −1.2 / −2.3 | 2/7 | −2.65 |
| EURUSD | 40 | 49 | +0.25 | 0.07 | 49% | +1.8 / −1.4 | 3/7 | −3.60 |
| GER40 | 40 | 280 | −0.05 | −0.02 | 51% | +2.4 / **−2.9** | 1/5 | +1.44 |
| GER40 | 60 | 73 | −4.46 | −0.53 | 55% | **+8.1 / −17.3** | 0/4 | +2.31 |

**Verdict A+B for MR: ❌ across the board.** No |t| > 1.7 (need > 2.5). Not two-sided — the long
leg is positive only because indices drift up (beta); short-fade legs are ~0 or strongly negative
(GER40: long +8.1 / short −17.3 = pure long beta). Regime-fragile (positive only in recent/up years).
**The tiny apparent positives (US500 θ50 +1.10) vanish or invert under a 1-bar delay** → look-ahead
artifact, not edge. The naive **overlapping** screen had shown US500 θ50 at **+11 bps net both-sides** —
entirely spurious.

### 1b. Breakout — partial-TP, both-sides, EOD (family #2, "reworked")
30-min opening range, both-sides breakout, partial TP at 1× range width + EOD runner:

| instrument | n | mean net (bps) | t-stat | WR | skew | long-leg / short-leg | yrs + |
|---|---:|---:|---:|---:|---:|---:|---:|
| US500 | 1216 | +0.90 | 0.65 | 56% | −0.98 | +1.4 / +0.4 | 4/6 |
| US100 | 1216 | +1.04 | 0.55 | 56% | −1.07 | +1.7 / +0.3 | 3/6 |
| US30 | 1654 | −0.38 | −0.30 | 55% | −1.79 | +1.4 / **−2.3** | 2/7 |

**Verdict: ❌ EV ≈ 0** (no |t| > 0.7), long-leg-carried (beta). Partial-TP lifts WR to 56% but
**cannot manufacture EV** — fresh confirmation, on three new instruments, of the prior NQ finding
(`SCAN_ftmo_families.md`: partial-TP fixes shape, p(funded) stays ~31%).

### 1c. Carried from the project's prior verified work (not re-run)
| family × instrument | result | source |
|---|---|---|
| MR intraday — NQ (z-fade) | meanR −0.019 **gross** → −0.096 @1bps (NQ intraday *trends*) | SCAN_ftmo_families |
| Intraday momentum — NQ (Gao-style) | one-sided: long +1.50 / short −0.84 bps; 8/17 yrs; p(funded) ≤21% = **beta** | SCAN_ftmo_families |
| Carry / overnight — FX (USDJPY/AUDJPY) | +EV gross but MaxDD −14% to −19% **> −10% floor** (crash tail) | SCAN_ftmo_families |
| Stat-arb — AUD/NZD | EV ≈ 0 | SCAN_ftmo_families |
| All crypto MR / reversal / residual-MR | genuine signal but **cost-killed at 0.34% crypto RT** | STRATEGY_RESEARCH_LOG |
| Overnight equity harvester (NQ) | beta; ~50% deployable, financing-fragile | OVERNIGHT_drift_hardening |
| ORB + floor_taper (NQ) | no per-trade alpha (DSR_p 0.08); rules-exploitation; ~46–50% | ORB_realconstraints_NQ |

---

## 2. Alpha-vs-beta test of the one "survivor"

Only the **high-selectivity MR fade (US500/US100 θ=50)** even *looked* like a survivor — in the
naive overlapping screen it showed +6 to +11 bps net with both legs positive. It was put through
the alpha-vs-beta battery and **failed every leg**:

| test | result | verdict |
|---|---|---|
| **Non-overlapping trades + per-trade cost** | +11 bps → **+1.10 bps (US500), −1.86 (US100)** | edge was overlap-counting |
| **Significance** | t = **0.26** (US500), −0.64 (US100) | indistinguishable from zero |
| **1-bar execution delay** (L: real edge survives) | +1.10 → **−0.25**; −1.86 → −3.04 | **look-ahead artifact — collapses** |
| **Split-by-direction (L25)** | long +3.3 / short **−1.6** (US500) | **one-sided = long beta, not MR alpha** |
| **Regime (by year)** | **3/6** positive, concentrated 2025–26 | regime-fragile |

It is not alpha. It is the same long-equity beta seen everywhere in this arc, dressed up by a
selection-mined threshold and a non-tradeable same-bar entry.

## 3. Full battery for real survivors

**None reached it.** No candidate cleared A+B with a positive, significant, two-sided, delay-robust
gross edge, so the deep battery (walk-forward, block-bootstrap p(pass), DSR/AMTP, reconciliation)
was correctly **not** spent — exactly the effort the two-stage filter is designed to save.

---

## 4. Verdict

**Is there a (family × instrument) with REAL alpha (not beta) AND an L24-compatible profile that
clears >70% p(pass) under real costs? — No, among everything tested.** Stated plainly:

1. **Mean-reversion** (the best-*profile* candidate) has **no positive gross edge** on liquid FTMO
   majors once tested honestly (non-overlapping + delay). NQ/US tech *trends* intraday (fading loses
   gross); SPX/DAX/EURUSD fades are insignificant and one-sided. The cost-gate never even binds —
   there is nothing positive to tax.
2. **Breakout** reshapes to a nice WR-56% / low-skew profile but carries **EV ≈ 0** — confirmed now on
   US500/US100/US30. Shape ≠ EV.
3. **Momentum / carry / stat-arb** were already shown (this project) to be beta, crash-tailed, or
   EV-zero.
4. The recurring signature is **long-equity beta** masquerading as an edge: every "positive" leg is the
   long side in up-regimes; short legs and down/chop regimes kill it. That is precisely what L25
   (split-by-direction) and the regime split are built to expose — and they expose it every time.

**Why this is the honest, expected answer:** liquid index/FX-major intraday price patterns are the most
heavily arbitraged space in markets. A retail-frequency, retail-execution participant should expect
**zero** robust per-trade alpha there — and that is what 5 instruments × selectivity × the prior arc
return. The **+50% plateau is not a coincidence**: with no per-trade alpha, a symmetric +10%/−10%
barrier with no time limit pays out ~50% (no-bust math) regardless of packaging.

### Where a real edge could still live (off the intraday-price-pattern menu — not tested here)
- **The project's already-validated books** (delta-neutral funding carry B, Sharpe ~2 proxy; TSMOM A).
  If a low-drawdown, genuinely +EV one is run *on the funded account*, **it** is the vehicle — packaged
  with the partial-TP shaping (the one reusable lever this hunt confirmed). FTMO does not accept crypto,
  so this is a "what to run **after** funding" point, not a challenge strategy.
- **Cross-sectional / √N** across many *independent* instruments (Dukascopy metals, more cash indices):
  raises EV-per-day via breadth, not per-trade edge — the only price-pattern route left, and only if
  each sleeve is independently > 0.
- **Event/microstructure edges requiring sub-bp execution** (residual-MR class): real but
  **market-maker-tier only**; not retail-FTMO-accessible.

### Honest bottom line
The two-stage filter worked exactly as intended: it fast-rejected every tail-lumpy / zero-EV / beta
candidate and caught the single mined false-positive at the delay test. **There is no retail-accessible,
two-sided, all-regime intraday alpha on liquid FTMO majors in the families searched.** Stop mining this
space; further "wins" here will be L26-type artifacts. The credible path to >50% on FTMO is **not** a
new intraday signal — it is either (a) a genuinely +EV book run under the no-time-limit first-passage
lever, or (b) breadth (√N) across many independently-positive instruments. Find the EV first; the L24
packaging is ready and the anti-false-positive protocol (non-overlap + delay) is now in place.

---

### Artifacts
- `code/mr_intraday_screen.py` — vectorized fade screen **and** the non-overlapping + delay validator (the A/B pre-filter + alpha-vs-beta machinery).
- Reuses `panels/m5_indices/m1_panel.parquet` (US indices), `EURUSD_m1_panel.parquet`, `GER40_m1_panel.parquet`.

### Sources / prior work
- `SCAN_ftmo_families.md` (prior multi-family scan), `STRATEGY_RESEARCH_LOG.md` (dead-list),
  `ORB_realconstraints_NQ.md` (ORB = rules-exploitation, DSR per-trade fail),
  `OVERNIGHT_drift_hardening.md` (overnight = beta). CLAUDE.md lessons L11/L24/L25.
