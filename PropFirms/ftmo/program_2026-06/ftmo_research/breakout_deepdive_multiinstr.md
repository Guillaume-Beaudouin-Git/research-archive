# Breakout deep-dive — multi-instrument corroboration

**Companion to `breakout_deepdive_ftmo.md`** (a parallel NQ-only deep-dive that concluded the breakout
edge is a *same-bar fill artefact* — 88–105 % of it collapses under 1-bar delay, no structural alpha).
This file reaches the **same verdict from an independent angle**: 6 instruments, bps costs, the
**two-sided test up front**, and DSR on the total space. Two different methods, one conclusion.

**Discipline (every cell):** non-overlapping trades; per-trade bps cost (indices 1.5, EURUSD 1.0); 1-bar
delay column; two-sided (up-break vs down-break legs separately); N_trials tracked for DSR.

---

## Verdict

> **No breakout variant clears the bar on any instrument.** Across **190 trials** (NQ/US500/US100/US30/GER40/EURUSD × 3 TF × {Donchian, ATR-thrust, ORB-N} × 2 params × 2 exits): **16 net-positive, 7 two-sided, 5 two-sided + delay-robust, best t = 1.02** vs a DSR bar ≈ **3.24**. Nothing survives.
>
> - **NQ (16-yr): 0 two-sided cells.** Best net-positive (Donchian-20, 5m) is one-sided: long +0.87 / short −0.84 bps — the long up-drift (beta). This mirrors the companion file's "long-leg-carried" finding via the cross-sectional two-sided test.
> - The only two-sided cells are **ATR-volatility-thrust + EOD on US500/US100/GER40** — t ≤ 1.02, ~1–2 bps, **3/6 years positive** (regime-fragile). Far under DSR.

Both methods converge: the breakout family has **no two-sided, delay-robust, cost- and DSR-surviving
alpha** on liquid FTMO instruments. The companion file shows *why* on NQ (the edge lives in the
same-bar fill); this file shows *that* it fails breadth-wide and the two-sided test.

---

## Results

| summary | value |
|---|---:|
| N_trials | **190** |
| net mean > 0 | 16 |
| two-sided & net > 0 | 7 |
| two-sided & net > 0 & delay-robust | 5 |
| best t (two-sided) | **1.02** |
| DSR bar (expected max\|t\|, N=190) | **≈ 3.24** |

**Best two-sided cell:** US500 5m ATR-thrust (k=2), EOD — +1.85 bps, t=1.02, delay-robust (+2.42), legs
+2.66/+1.08, but only **3/6 years positive**. **NQ best:** Donchian-20 5m EOD, +0.11 bps, t=0.13, **long
+0.87 / short −0.84** (one-sided beta), 7/17 years.

Donchian and ORB breakouts are one-sided long drift; ATR-thrust is marginally two-sided (volatility
expansions show weak two-sided continuation) but noise-level and regime-fragile. Closed at depth.

### Artifacts
- `code/directional_deepdive.py`, `directional_deepdive_grid.csv`.
- Companion: `breakout_deepdive_ftmo.md` (NQ fill-artefact deep-dive, parallel session).
