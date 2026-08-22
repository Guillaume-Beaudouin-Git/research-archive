# RESULTS — Piste B: Range trading (low-directionality regimes) on FTMO

**Run:** 2026-07-08, hourly UTC, 2007/2013→2026, intraday-flat (no swap). Protocol = frozen `PREREGISTRATION.md`. 56 trials.
**Artifacts:** `backtest_grid.csv`, `grid_<sym>.csv`, `summary.json`.

## Verdict: **FALSIFIED** — 4 of 5 triggers fired (F1, F2, F3, F4). The range edge is a look-ahead selection artefact, and what survives causally is cost-dead.

---

## 1. Causal vs oracle — the selection-artefact test (F2, the headline)

| instrument | **causal gross SR** | **oracle (look-ahead) gross SR** | net SR | gross/cost ratio | short-leg bps |
|---|--:|--:|--:|--:|--:|
| EURUSD | −0.55 | **+3.13** | −0.44 | −0.32 | −0.24 |
| GBPUSD | +0.32 | **+4.29** | −0.18 | 0.20 | −0.04 |
| GER40 | +0.01 | **+1.53** | −0.17 | 0.09 | −0.24 |
| US30 | −0.21 | **+2.48** | −0.26 | −0.16 | −0.21 |
| US500 | −0.65 | **+2.91** | −0.34 | −0.43 | −0.63 |
| US100 | −0.38 | −0.42 | −0.26 | −0.38 | −0.43 |
| XAUUSD | **+1.30** | +7.43 | +0.14 | 1.00 | +0.09 |
| **median** | **−0.06** | **+2.66** | −0.26 | — | — |

**Reading:** with a *look-ahead* range flag (regime = the next 8 bars stayed quiet), the fade prints
gross Sharpe **+2.66 median** — the strategy "works" beautifully **if you already know it's a range.**
With the **causal** flag (ADX<thr AND compressed band-width, trailing only), the median gross Sharpe is
**−0.06.** The edge is **~entirely the look-ahead**: knowing in advance that a window is a range is the
whole edge, and that is precisely the information you do not have in real time. This is the pre-registered
**F2** falsification — *range detection is a selection artefact*, exactly the trap flagged in the brief.

## 2. Cost gate & two-sidedness (F3, F1, F4)
- **F3 — cost-dead:** **0/56** cells meet the L33b intraday-flat gate (gross-per-trade ≥ 3× cost-per-trade).
  Best net Sharpe across all 56 = **0.57 < 0.7.** Intraday range amplitudes are simply too small versus
  the active-fill spread.
- **F1/F4 — one-sided:** the fade-high (short) leg is **negative on 6/7 instruments** (mean −0.24 bps).
  Gross two-sided-positive in only 8/56 cells (≈ chance). Not a symmetric range edge.

## 3. The one honest exception — XAUUSD (reported, not buried)
Gold is the **only** instrument with a genuine **causal** gross reversion tendency (gross SR +1.30, not a
look-ahead artefact — its oracle +7.43 is higher but the causal signal is real). But it is **cost-dead
net**: gross/cost ratio **1.00** (< 3), net Sharpe **0.14**, short-leg +0.09 bps. A real micro-tendency
that the active-fill spread eats — a *vehicle* failure, not an absent signal. This reconciles with the
repo's `xauusd_rangefade` NO-GO (there, Asian-session-only + hard stop showed no gross edge; here,
all-session Bollinger-fade shows a small gross edge that cost kills — both = **not net-tradeable on FTMO**).

## 4. §4 profile scorecard
| §4 axis | required | this family | |
|---|---|---|:--:|
| short-hold / intraday-m | ≤ 1.5 | ✓ (≤8-bar, breakout hard stop, intraday-flat) | ✓ |
| two-sided | both legs ≥0 | ✗ (short leg −0.24, 6/7) | ✗ |
| per-active-day edge | SR ≥ 1.5 | ✗ (causal gross ≈ 0; net < 0.57) | ✗ |
| **real-time detectable** | **causal ≈ oracle** | ✗ **causal −0.06 vs oracle +2.66** | ✗ |

Shape axes fine; the **edge and the detectability both fail.** §4 necessary, not sufficient — again.

## 5. What would have to be true to revisit
A range edge needs either (a) a **sub-spread execution venue** (market-maker tier) so the small intraday
amplitude clears cost — not retail FTMO; or (b) a **causal** regime signal that actually anticipates
low-directionality (the oracle shows the *ceiling* is high, but no trailing indicator here captures it).
The XAU micro-tendency is the only thread with a real gross signal; it would need a lower-cost vehicle,
not a better signal. **No audited-engine re-test warranted** (fails causal-detectability + cost upstream).

**Reconciliation:** deferred to `synthesis/` — reproduces the repo's range/breakout NO-GO (breakout edge =
execution rent, range-fade cost-dead), and adds the clean **causal-vs-oracle** decomposition that names
the mechanism precisely: *the detection, not the fade, was the look-ahead.*
