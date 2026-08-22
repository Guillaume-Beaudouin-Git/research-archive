# Intraday momentum — FTMO deep-dive (two-sided test up front)

**Mandate:** the breadth scan flagged NQ intraday momentum as the one shape-passing candidate, then the
battery exposed it as **one-sided long beta** (long +1.50 / short −0.84 bps, 8/17 yrs). This is the
depth pass on the momentum *family* with the **two-sided test enforced up front** — the moment a logic is
positive only on the long leg, it is the equity up-drift and is rejected.

**Discipline (every cell):** non-overlapping trades; per-trade bps cost (indices 1.5, EURUSD 1.0); 1-bar
delay column; **two-sided** (long-momentum vs short-momentum legs separately); N_trials for DSR.

---

## Verdict

> **Momentum is the weakest of all directional families tested — and uniformly one-sided.** Across **176 trials** (6 instruments × 4 TF-equivalents × {TS-mom, Gao first-part→rest, VWAP-distance} × 2 params × 2 exits): only **5 net-positive, 2 two-sided, best t = 0.41**. The DSR bar is ≈ **3.21**. Nothing is remotely close.
>
> - **Every cell with a meaningful t is one-sided long.** GER40 Gao: long **+4.04** / short **−1.91**; NQ TS-mom: long +0.99 / short −0.83; NQ VWAP-distance: long +0.56 / short −0.45. The winning leg is always the up-drift — the textbook beta signature, now confirmed across the full grid.
> - The 2 two-sided cells (US500 15m TS-mom) are **+0.33 bps, t=0.41** — statistically and economically nil.

Intraday momentum on liquid FTMO instruments **is** the equity risk premium harvested on the long side.
It is not a two-sided, all-regime, cost-surviving alpha. Closed at depth.

---

## Results

| summary | value |
|---|---:|
| N_trials | **176** |
| net mean > 0 | 5 |
| two-sided & net > 0 | **2** |
| best t (two-sided) | **0.41** |
| best t (any) | 0.49 (GER40 Gao — one-sided long) |
| DSR bar (expected max\|t\|, N=176) | **≈ 3.21** |

**The one-sidedness is the whole story.** TS-momentum and VWAP-distance and Gao first-half-hour
continuation all make money *only* when going long into the up-drift; the short legs lose. This is
exactly L25's purpose — a directional edge must be positive on both legs, and momentum never is. The
"edge" is long-equity beta, positive in favourable years and negative in down/chop years, just as the
overnight harvester and the intraday-momentum breadth result already showed.

## Verdict

**Is there a two-sided, delay-robust, cost- and DSR-surviving intraday momentum edge on FTMO
instruments? — No, decisively.** It is the most one-sided family of all: the long leg is the equity
premium, the short leg is dead. Momentum is beta by another name. Closed.

### Artifacts
- `code/directional_deepdive.py`, `directional_deepdive_grid.csv` (breakout + momentum, 366 trials).
