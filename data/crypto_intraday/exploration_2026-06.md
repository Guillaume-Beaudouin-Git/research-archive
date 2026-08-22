# Crypto intraday — GATE-0 (spread vs move) + 5-axis screen — crypto_intraday/
*2026-06, MEASURED. Same fil as ORB: **does the spread sweep the move?** Data: BTCUSD 1-min 2018-11..2026-05 (n=3.39M) with MT5 **floating spread** column (pt=0.01, flagged FTMO-LP-class proxy — a real floating spread: 17.6k distinct values, rises with vol). Gate uses move/spread **ratio** (point-size-robust). Cost = measured spread @ entry minute + commission 6.5 bps RT. **Intraday-FLAT → no swap** (the structural fix vs the TSMOM carry that just failed). No breakout axis (ORB-crypto already dead). Nothing frozen/merged.*

## TL;DR — 4 of 5 killed by the cheap gate; #2 is a real-but-DECAYING mechanism, not FTMO-deployable
The gate-0 spread wall is **tight in normal minutes (median 3.4 bps)** and **blows out only modestly on events/cascades (p90 ~25, p99 ~27 bps)** — so cost is not the universal killer here; the **absence of a capturable move** is. Ranked by the user's prior:

| # | axis | verdict | decisive number |
|---|---|---|---|
| 1 | FOMC/CPI reaction (top prior) | **KILL** | instant spike median **6 bps** (premise "2–5%" false at tradeable scale); delay-1 continuation **net −23 bps** @60m, hit 30%; one-sided (long-beta, L25); negative OOS both eras |
| 2 | liquidation-cascade reversion | **WEAK / DECAYING** | extreme-tail down-flush→long **net +30 bps** @120m (hit 55%, ex-2020/21) — but **one-sided** & **negative in 2025** |
| 3 | US-open risk-on flow | **KILL** | |move|/min ≈ spread at **every** UTC hour (ratio ~0.9–1.1); no US-open move edge |
| 4 | cross-asset lead-lag | **KILL (sub-cost)** | gate-implied: even FOMC spikes are 6 bps; intraday lead-lag predictive moves < 3.4-bps spread → HFT territory, non-collectable on CFD |
| 5 | funding-settlement window | **KILL (instrument)** | spot-CFD doesn't track perp funding microstructure; no move at 00/08/16 UTC (ratio ~0.9); funding families already dead |

## Gate-0 spread wall (the common denominator)
- **All minutes:** median **3.4 bps**, p90 11, p99 27, p99.9 44. By year: 13.8 (2018, illiquid) → 2.7 (2025); *2026 spread column looks truncated (median 0.1 bps) — exclude 2026 spread.*
- **Cascade proxy (top-1% |ret| minutes):** spread median 4.8, p90 **24.7** bps — it *does* blow out (the L33 risk is real) but the move blows out more (48 bps/min) → ratio ~10×. The blowout is bounded, not catastrophic.

## #1 — FOMC/CPI reaction (top prior) → KILL
128 events (51 FOMC, 77 CPI). Delay-1 entry (L26) spread is already normalized (median 3.0 bps). **The premise is false at tradeable scale: the median instant spike is 6 bps, not 2–5%** — the big moves are tail anecdotes, not a per-event edge. Capturable continuation from delay-1 is **negative at every horizon** (30m −15, 60m −23, 120m −14 bps net; hit 28–40%). Two-sided fails: up-spike +15 / down-spike −39 @120m → only the long side works = **disguised long-beta (L25)**. OOS negative both eras (pre-2023 −35, post-2023 −14). Gate ratio of *capturable* move to spread = **−1.4×**. *The spread didn't even need to be wide — there is no capturable move after the instant tick.*

## #2 — liquidation-cascade reversion → WEAK, DECAYING (the only real mechanism)
Mechanism (forced, non-price-sensitive deleveraging → overshoot → reversion) is genuine and **survives the decisive L33 test**: charging the **blown-out cascade-minute spread** (median 6–10, p90 26–38 bps) + commission, the extreme-tail (0.1%) **down-flush→long** still nets **+18 bps @60m / +30–41 bps @120m** (hit 53–56%). It is **not a crash-cluster artifact** — ex-2020/2021 it holds (+30 bps, 55%, N=722), positive every year 2019–2024.

**But three honest problems make it NOT a deployable FTMO engine:**
1. **Decaying** — 60m edge gone by 2023; 120m edge fades (+44→+18) and turns **negative in 2025 (−7 bps, hit 44%)**: the arbitraged-away signature.
2. **One-sided** — up-squeeze→short is dead (−20 to −45 bps, hit 38–44%); a clean reversion would work both ways. One-sidedness is a yellow flag (though at 60–120 min, drift is negligible, so the long edge is a genuine bounce, not pure beta).
3. **Low-frequency, modest** — only the 0.1% tail works (~130 events/yr ≈ 1–2/week, clustered → effective-N lower), hit barely >50%. Too few trades + fading edge to clear a +10% phase-1.

**Verdict #2: real mechanism, fading edge — a candidate-lesson, not an FTMO engine in 2026.** Deepen only if a vol/regime filter revives the post-2024 edge (next-step, not claimed).

## What this resolves
The crypto-intraday branch was the right structural idea — **intraday-flat sidesteps the overnight carry that killed daily TSMOM** — but the cheap gate-0 kills 4 of 5 axes outright and shows the 5th (#2) is decaying toward zero. The binding constraint flipped: for TSMOM it was *carry*; here it's the **absence of a capturable move above an already-tight spread**. BTC's scheduled-event reaction is 6 bps (not the folk "2–5%"), hour-of-day flow ≈ spread, and lead-lag/funding are sub-cost or wrong-instrument. **No new FTMO-deployable crypto-intraday engine.**

**Lesson candidates (named, not numbered):**
- **"BTC's scheduled-event spike is ~6 bps at the tradeable minute, not 2–5%"** — the macro-reaction premise dies on measurement; the big moves are tail anecdotes, and delay-1 continuation is negative + long-beta (L25).
- **"the crypto-intraday killer is no-capturable-move, not the spread"** — normal spread 3.4 bps is tight; the gate fails on the numerator (move ≈ spread at every hour), the opposite of the carry that killed TSMOM.
- **"liquidation-reversion is a real mechanism that survives the spread-blowout but is decaying + one-sided"** — extreme down-flushes bounce (+30 bps/120m ex-crash-clusters) net of the p90~30-bps cascade spread, but the edge fades to negative by 2025 and the short side is dead → not deployable.
- **"a floating-spread data column makes gate-0 self-contained"** — no demo measurement needed when the feed carries the real per-minute spread (flag the LP-class proxy + the 2026 truncation).

*Reproduce: `gate0_event_spread.py` (spread wall + #1 + #3 hour-of-day), `axis2_liquidation_reversion.py` (#2 + by-year/ex-cluster). Intraday-flat, no swap. Cost = measured floating spread (flagged) + 6.5 bps RT. Stayed in crypto_intraday/; nothing frozen/merged.*
